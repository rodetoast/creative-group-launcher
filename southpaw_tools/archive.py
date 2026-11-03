from __future__ import annotations

import os
import stat
import threading
import zipfile
from pathlib import Path

from .catalog import AppRelease
from .common import Cancelled, LauncherError, digest, inside, relative_path

MAX_FILES = 20_000
MAX_EXPANDED = 4 * 1024**3


def member_name(member: zipfile.ZipInfo) -> str:
    # Legacy Windows ZIP producers use backslashes. Canonicalize BEFORE checking
    # traversal/UNC/drive paths, rather than changing any original package bytes.
    return member.orig_filename.replace("\\", "/").rstrip("/")


def check_cancel(event: threading.Event | None) -> None:
    if event is not None and event.is_set():
        raise Cancelled("작업을 취소했습니다. 기존 설치는 유지됩니다.")


def checked_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    if not members or len(members) > MAX_FILES:
        raise LauncherError("압축 파일 항목 수가 허용 범위를 벗어났습니다.")
    if sum(member.file_size for member in members) > MAX_EXPANDED:
        raise LauncherError("압축 해제 용량이 제한을 초과합니다.")
    names: dict[str, bool] = {}
    for member in members:
        # orig_filename retains embedded NULs that ZipInfo.filename would truncate.
        name = member_name(member)
        relative_path(name)
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}):
            raise LauncherError("ZIP 링크 또는 특수 파일은 허용하지 않습니다.")
        if member.flag_bits & 1:
            raise LauncherError("암호화 ZIP은 지원하지 않습니다.")
        key = name.casefold()
        if key in names:
            raise LauncherError("중복되거나 대소문자가 충돌하는 ZIP 경로")
        names[key] = member.is_dir()
        if member.file_size > max(1, member.compress_size) * 2000:
            raise LauncherError("비정상적인 ZIP 압축 비율")
    for name in names:
        parts = name.split("/")
        if any(names.get("/".join(parts[:i])) is False for i in range(1, len(parts))):
            raise LauncherError("파일과 디렉터리의 ZIP 경로 충돌")
    return members


def extract_checked(package: Path, destination: Path, app: AppRelease,
                    cancel: threading.Event | None = None) -> dict[str, str]:
    if package.stat().st_size != app.package_size or digest(package) != app.sha256:
        raise LauncherError("배포 패키지 크기 또는 SHA-256 불일치")
    hashes = {}
    try:
        with zipfile.ZipFile(package) as archive:
            members = checked_members(archive)
            destination.mkdir(parents=True, exist_ok=False)
            for member in members:
                check_cancel(cancel)
                name = member_name(member)
                target = inside(destination, name)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("xb") as output:
                    written = 0
                    while chunk := source.read(1024 * 1024):
                        check_cancel(cancel)
                        written += len(chunk)
                        if written > member.file_size:
                            raise LauncherError("ZIP 크기 정보가 실제 데이터와 다릅니다.")
                        output.write(chunk)
                hashes[name] = digest(target)
            executable = inside(destination, app.executable_relative_path)
            if not executable.is_file() or digest(executable) != app.executable_sha256:
                raise LauncherError("실행 파일 누락 또는 EXE SHA-256 불일치")
            with executable.open("rb") as stream:
                if stream.read(2) != b"MZ":
                    raise LauncherError("올바른 Windows 실행 파일이 아닙니다.")
            cwd = inside(destination, app.working_directory_relative_path, allow_dot=True)
            if not cwd.is_dir() or executable.parent != cwd:
                raise LauncherError("실행 파일과 작업 디렉터리 정보가 맞지 않습니다.")
            for required in app.required_paths:
                if not inside(destination, required).exists():
                    raise LauncherError(f"필수 리소스 누락: {required}")
        check_cancel(cancel)
        return hashes
    except (zipfile.BadZipFile, RuntimeError, OSError, NotImplementedError) as exc:
        raise LauncherError(f"패키지 검증/압축 해제 실패: {exc}") from exc
