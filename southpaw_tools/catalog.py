from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .common import LauncherError, identifier, read_json, relative_path


@dataclass(frozen=True)
class AppRelease:
    app_id: str
    display_name: str
    category: str
    description: str
    version: str
    release_id: str
    release_channel: str = "approved"
    package_name: str = ""
    package_size: int = 0
    sha256: str = ""
    executable_relative_path: str = ""
    executable_sha256: str = ""
    working_directory_relative_path: str = "."
    required_paths: list[str] = field(default_factory=list)
    preserve_paths: list[str] = field(default_factory=list)
    release_notes: str = ""
    published: bool = False
    published_at: str | None = None
    availability_reason: str = "배포 패키지 미확인"
    package_type: str = "onefile"
    build_id: str = ""
    icon: str = ""

    @classmethod
    def parse(cls, value: dict) -> "AppRelease":
        if not isinstance(value, dict):
            raise LauncherError("잘못된 프로그램 등록 정보")
        try:
            item = cls(**value)
        except TypeError as exc:
            raise LauncherError(f"카탈로그 필드 오류: {exc}") from exc
        identifier(item.app_id, "app_id")
        identifier(item.release_id, "release_id")
        for text in (item.display_name, item.category, item.description, item.version):
            if not isinstance(text, str) or not text.strip() or len(text) > 2000:
                raise LauncherError("필수 프로그램 정보가 비어 있거나 잘못되었습니다.")
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}(?:[ -][A-Za-z0-9 ._-]+)?", item.version):
            raise LauncherError("잘못된 버전 정보")
        if type(item.published) is not bool or type(item.package_size) is not int:
            raise LauncherError("잘못된 게시/크기 정보")
        if item.release_channel != "approved":
            raise LauncherError("승인 배포 채널만 지원합니다.")
        if item.package_type not in ("onefile", "onedir"):
            raise LauncherError("알 수 없는 패키지 형식")
        relative_path(item.working_directory_relative_path, allow_dot=True)
        for values in (item.required_paths, item.preserve_paths):
            if not isinstance(values, list) or any(not isinstance(p, str) for p in values):
                raise LauncherError("잘못된 리소스/보존 경로 목록")
            for path in values:
                relative_path(path)
        if not isinstance(item.release_notes, str) or len(item.release_notes) > 200_000:
            raise LauncherError("릴리즈 노트가 잘못되었습니다.")
        if item.icon:
            relative_path(item.icon)
        if item.published:
            if item.package_size <= 0 or item.package_size > 2 * 1024**3:
                raise LauncherError("잘못된 패키지 크기")
            if (not isinstance(item.package_name, str) or not item.package_name.endswith(".zip")
                    or "/" in item.package_name):
                raise LauncherError("잘못된 패키지 이름")
            relative_path(item.package_name)
            for sha in (item.sha256, item.executable_sha256):
                if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
                    raise LauncherError("SHA-256 정보가 잘못되었습니다.")
            relative_path(item.executable_relative_path)
            if not item.executable_relative_path.lower().endswith(".exe"):
                raise LauncherError("실행 파일은 EXE여야 합니다.")
            if not item.published_at:
                raise LauncherError("게시 승인 시각이 없습니다.")
            try:
                stamp = datetime.fromisoformat(item.published_at)
                if stamp.tzinfo is None:
                    raise ValueError("timezone required")
            except (TypeError, ValueError) as exc:
                raise LauncherError("게시 시각이 잘못되었습니다.") from exc
        return item

    def to_dict(self) -> dict:
        return asdict(self)

    def is_new_release(self, installed: "AppRelease") -> bool:
        if self.app_id != installed.app_id:
            raise LauncherError("다른 프로그램의 업데이트입니다.")
        if self.release_id == installed.release_id and self.sha256 != installed.sha256:
            raise LauncherError("같은 release_id의 패키지 해시가 바뀌었습니다. 게시자 확인이 필요합니다.")
        return self.published and self.release_id != installed.release_id


def parse_catalog(data: dict) -> list[AppRelease]:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise LauncherError("지원하지 않는 카탈로그 형식")
    values = data.get("apps")
    if not isinstance(values, list) or len(values) > 200:
        raise LauncherError("잘못된 프로그램 목록")
    apps = [AppRelease.parse(value) for value in values]
    if len({app.app_id for app in apps}) != len(apps):
        raise LauncherError("중복 app_id")
    return apps


def load_catalog(path: Path) -> list[AppRelease]:
    return parse_catalog(read_json(path))


def catalog_document(apps: list[AppRelease]) -> dict:
    return {"schema_version": 1, "apps": [app.to_dict() for app in apps]}
