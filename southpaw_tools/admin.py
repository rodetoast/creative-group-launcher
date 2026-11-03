"""Local-only publishing: validate a completed approved ZIP, then atomically publish."""
from __future__ import annotations

import argparse
import shutil
import tempfile
import uuid
from dataclasses import replace
from pathlib import Path

from .archive import extract_checked
from .catalog import AppRelease, catalog_document, load_catalog
from .common import LauncherError, app_lock, atomic_json, digest, utc_now


def publish(root: Path, app_id: str, package: Path, *, version: str, release_id: str,
            executable: str, expected_sha256: str, expected_exe_sha256: str,
            approved: bool, build_id: str = "", notes: str | None = None,
            cwd: str | None = None, required_paths: list[str] | None = None) -> AppRelease:
    if not approved:
        raise LauncherError("명시적인 게시 승인이 필요합니다. --approve를 지정하세요.")
    with app_lock(root / ".publish.lock"):
        apps = load_catalog(root / "catalog.json")
        previous = next((app for app in apps if app.app_id == app_id), None)
        if previous is None:
            raise LauncherError("등록되지 않은 app_id")
        if previous.published and previous.release_id == release_id:
            raise LauncherError("기존 release_id는 재게시/덮어쓰지 않습니다.")
        if not package.is_file() or digest(package) != expected_sha256.lower():
            raise LauncherError("원본 승인 ZIP의 SHA-256 불일치")
        name = f"{app_id}--{release_id}.zip"
        app = AppRelease.parse(replace(
            previous, version=version, release_id=release_id, package_name=name,
            package_size=package.stat().st_size, sha256=expected_sha256.lower(),
            executable_relative_path=executable, executable_sha256=expected_exe_sha256.lower(),
            published=True, published_at=utc_now(), availability_reason="",
            build_id=build_id, release_notes=notes if notes is not None else previous.release_notes,
            working_directory_relative_path=cwd or previous.working_directory_relative_path,
            required_paths=required_paths if required_paths is not None else previous.required_paths,
        ).to_dict())
        stage_root = root / ".staging"
        stage_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="publish-", dir=stage_root) as folder:
            stage = Path(folder)
            copied = stage / "approved.zip"
            shutil.copyfile(package, copied)
            extract_checked(copied, stage / "audit", app)
            # Immutable package first, catalog pointer last. No partial ZIP is public.
            packages = root / "packages"
            packages.mkdir(parents=True, exist_ok=True)
            target = packages / app.package_name
            if target.exists():
                raise LauncherError("동일한 게시 파일이 이미 존재합니다.")
            copied.rename(target)
            try:
                atomic_json(root / "catalog.json", catalog_document([
                    app if item.app_id == app_id else item for item in apps
                ]))
            except Exception:
                target.unlink(missing_ok=True)
                raise
        return app


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "distribution")
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--exe", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--exe-sha256", required=True)
    parser.add_argument("--cwd")
    parser.add_argument("--build-id", default="")
    parser.add_argument("--notes-file", type=Path)
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args(argv)
    try:
        app = publish(args.root, args.app_id, args.zip, version=args.version,
                      release_id=args.release_id, executable=args.exe,
                      expected_sha256=args.sha256, expected_exe_sha256=args.exe_sha256,
                      approved=args.approve, build_id=args.build_id, cwd=args.cwd,
                      notes=args.notes_file.read_text(encoding="utf-8") if args.notes_file else None)
        print(f"게시 완료: {app.display_name} / {app.release_id} / {app.sha256}")
        return 0
    except (LauncherError, OSError) as exc:
        print(f"게시 실패: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
