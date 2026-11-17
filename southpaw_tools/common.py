from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .bootstrap_diagnostics import call, operation, secondary


class LauncherError(Exception):
    """An actionable error safe to present in the launcher."""


class Cancelled(LauncherError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with call("file_open", path.open, "rb", target=path, api="Path.open") as stream:
        for chunk in iter(lambda: call("file_read", stream.read, 1024 * 1024, target=path, api="file.read"), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    atomic_bytes(path, raw)


ATOMIC_TEMP_PREFIX = ".pending-"
ATOMIC_TEMP_SUFFIX = ".json"


def atomic_temp_example(path: Path) -> Path:
    # CPython mkstemp inserts an eight-character candidate name.
    return path.with_name(ATOMIC_TEMP_PREFIX + "0" * 8 + ATOMIC_TEMP_SUFFIX)


def atomic_bytes(path: Path, raw: bytes) -> None:
    call('atomic_parent_mkdir', path.parent.mkdir, parents=True, exist_ok=True, target=path.parent, api='Path.mkdir')
    fd, temp = call('atomic_temp_create', tempfile.mkstemp, prefix=ATOMIC_TEMP_PREFIX,
                    suffix=ATOMIC_TEMP_SUFFIX, dir=path.parent, target=path, api='tempfile.mkstemp')
    original = None
    try:
        with operation('atomic_temp_stream', target=temp, api='file context manager'):
            with os.fdopen(fd, "wb") as stream:
                call('atomic_temp_write', stream.write, raw, target=temp, api='file.write')
                call('atomic_temp_flush', stream.flush, target=temp, api='file.flush')
                call('atomic_temp_fsync', os.fsync, stream.fileno(), target=temp, api='os.fsync')
        call('atomic_replace', os.replace, temp, path, target=path, api='os.replace')
    except Exception as exc:
        original = exc
        raise
    finally:
        try:
            call('atomic_temp_cleanup', Path(temp).unlink, missing_ok=True, target=temp, api='Path.unlink')
        except Exception as cleanup_error:
            if original is None:
                raise
            secondary(original, cleanup_error, 'atomic_temp_cleanup')


def read_json(path: Path) -> dict:
    try:
        if call("json_stat", path.stat, target=path, api="Path.stat").st_size > 4 * 1024 * 1024:
            raise LauncherError("설정 파일이 너무 큽니다.")
        value = json.loads(call("json_read", path.read_text, encoding="utf-8", target=path, api="Path.read_text"))
        if not isinstance(value, dict):
            raise ValueError("object required")
        return value
    except (OSError, ValueError) as exc:
        raise LauncherError(f"JSON 파일을 읽을 수 없습니다: {path.name}: {exc}") from exc


def identifier(value: str, field: str = "ID") -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,95}", value):
        raise LauncherError(f"올바르지 않은 {field}")
    if value in {".", ".."} or value.endswith("."):
        raise LauncherError(f"올바르지 않은 {field}")
    if value.split(".")[0].upper() in RESERVED:
        raise LauncherError(f"예약된 {field}")
    return value


RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {
    f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
}


def relative_path(value: str, *, allow_dot: bool = False) -> str:
    if allow_dot and value == ".":
        return value
    if not isinstance(value, str) or not value or len(value) > 220:
        raise LauncherError("올바르지 않은 상대 경로")
    if "\\" in value or value.startswith("/") or any(ord(c) < 32 for c in value):
        raise LauncherError(f"허용되지 않는 경로: {value!r}")
    parts = value.split("/")
    for part in parts:
        if (part in {"", ".", ".."} or part.endswith((".", " "))
                or any(c in part for c in ':*?"<>|')
                or part.split(".")[0].upper() in RESERVED):
            raise LauncherError(f"허용되지 않는 Windows 경로: {value!r}")
    return str(PurePosixPath(value))


def inside(root: Path, relative: str, *, allow_dot: bool = False) -> Path:
    value = relative_path(relative, allow_dot=allow_dot)
    root = root.resolve()
    result = (root / value).resolve()
    if not result.is_relative_to(root):
        raise LauncherError("설치 경로를 벗어났습니다.")
    # Reject junctions/symlinks, even if they currently point inside the root.
    current = root
    for part in Path(value).parts:
        current = current / part
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise LauncherError("링크/정션을 통한 파일 접근은 허용하지 않습니다.")
    return result


def plain_tree(root: Path):
    """Enumerate without following user-created symlinks or Windows junctions."""
    for child in root.iterdir():
        yield child
        linked = child.is_symlink() or (hasattr(child, "is_junction") and child.is_junction())
        if child.is_dir() and not linked:
            yield from plain_tree(child)


def remove_transaction(root: Path, path: Path) -> None:
    """Remove only a verified private staging/release transaction, never an app root."""
    relative = path.absolute().relative_to(root.resolve()).as_posix()
    checked = inside(root, relative)
    if checked == root.resolve() or not checked.exists():
        return
    for child in plain_tree(checked):
        if child.is_symlink() or (hasattr(child, "is_junction") and child.is_junction()):
            raise LauncherError("임시 설치에 링크/정션이 발견되어 자동 정리를 중단합니다.")
    shutil.rmtree(checked)


@contextmanager
def app_lock(path: Path):
    """OS-held lock: a crashed client cannot leave a permanent busy marker."""
    call('lock_parent_mkdir', path.parent.mkdir, parents=True, exist_ok=True, target=path.parent, api='Path.mkdir')
    stream = call('lock_open', path.open, "a+b", target=path, api='Path.open')
    locked = False
    original = None
    try:
        with operation('lock_initialize', target=path, api='file.seek/write/flush'):
            stream.seek(0, 2)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                call('lock_acquire', msvcrt.locking, stream.fileno(), msvcrt.LK_NBLCK, 1,
                     target=path, api='msvcrt.locking')
            else:
                import fcntl
                call('lock_acquire', fcntl.flock, stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB,
                     target=path, api='fcntl.flock')
            locked = True
        except OSError as exc:
            raise LauncherError("다른 런처에서 이 프로그램을 관리 중입니다.") from exc
        yield
    except Exception as exc:
        original = exc
        raise
    finally:
        try:
            if locked:
                with operation('lock_release', target=path, api='file.seek/OS unlock'):
                    stream.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            call('lock_close', stream.close, target=path, api='file.close')
        except Exception as cleanup_error:
            if original is None:
                raise
            secondary(original, cleanup_error, 'lock_cleanup')
