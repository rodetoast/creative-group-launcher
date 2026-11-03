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


class LauncherError(Exception):
    """An actionable error safe to present in the launcher."""


class Cancelled(LauncherError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".pending-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def read_json(path: Path) -> dict:
    try:
        if path.stat().st_size > 4 * 1024 * 1024:
            raise LauncherError("설정 파일이 너무 큽니다.")
        value = json.loads(path.read_text(encoding="utf-8"))
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
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a+b")
    locked = False
    try:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError as exc:
            raise LauncherError("다른 런처에서 이 프로그램을 관리 중입니다.") from exc
        yield
    finally:
        if locked:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()
