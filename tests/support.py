from __future__ import annotations

import hashlib
import shutil
import zipfile
import tempfile
from pathlib import Path

from southpaw_tools.archive import check_cancel
from southpaw_tools.catalog import AppRelease, catalog_document
from southpaw_tools.common import atomic_json, digest


def temporary(prefix="southpaw-test-"):
    root = Path(__file__).resolve().parents[1] / ".test-results" / "tmp"
    root.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(prefix=prefix, dir=root)


def package(root: Path, release="r1", *, version="1.0.0", nested=False, contents=None):
    root.mkdir(parents=True, exist_ok=True)
    exe = "Dummy/Dummy.exe" if nested else "Dummy.exe"
    cwd = "Dummy" if nested else "."
    data = {exe: b"MZ harmless dummy fixture " + release.encode(),
            ("Dummy/" if nested else "") + "asset.json": b'{"fixture": true}'}
    if contents is not None:
        data = contents
    source = root / f"{release}.zip"
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, body in data.items():
            archive.writestr(name, body)
    exe_bytes = data.get(exe, b"MZ missing")
    app = AppRelease.parse(dict(
        app_id="dummy", display_name="Dummy Tool", category="Tests", description="Harmless fixture",
        version=version, release_id=release, package_name=f"{release}.zip",
        package_size=source.stat().st_size, sha256=digest(source),
        executable_relative_path=exe, executable_sha256=hashlib.sha256(exe_bytes).hexdigest(),
        working_directory_relative_path=cwd,
        required_paths=[("Dummy/" if nested else "") + "asset.json"],
        preserve_paths=["settings.json", "user-projects"], release_notes="Fixture release",
        published=True, published_at="2026-11-03T00:00:00+00:00",
    ))
    return source, app


class LocalProvider:
    def __init__(self, source: Path):
        self.source = source

    def download(self, app, target, progress, cancel=None):
        check_cancel(cancel)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.source, target)
        progress(target.stat().st_size, app.package_size)
        check_cancel(cancel)


class FakeProcesses:
    def __init__(self):
        self.running = False
        self.calls = []

    def is_running(self, root):
        return self.running

    def start(self, executable, cwd):
        self.calls.append((executable, cwd))
        self.running = True
        return "dummy-process"


def repository(root, source, app):
    (root / "packages").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, root / "packages" / app.package_name)
    atomic_json(root / "catalog.json", catalog_document([app]))
