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


class TestSigner:
    """Ephemeral test-only key, outside the served repository and never bundled."""
    __test__ = False

    def __init__(self, root):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        from southpaw_tools.catalog_trust import b64, key_id, CATALOG_ID
        self.private = Ed25519PrivateKey.generate()
        self.path = root / "test-only-signing.pem"
        self.path.write_bytes(self.private.private_bytes(serialization.Encoding.PEM,
                              serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        public = self.private.public_key().public_bytes_raw()
        self.policy = {"schema_version":1, "catalog_id":CATALOG_ID, "minimum_sequence":1,
                       "keys":{key_id(public):b64(public)}}

    def pair(self, apps, sequence):
        from southpaw_tools.catalog_trust import catalog_bytes, sign
        return (raw := catalog_bytes(apps, sequence)), sign(raw, self.private)

    def publish(self, root, apps, sequence):
        from southpaw_tools.common import atomic_bytes
        raw, signature = self.pair(apps, sequence)
        atomic_json(root / "catalog.sig.json", signature)
        atomic_bytes(root / "catalog.json", raw)

    def verifier(self, state):
        from southpaw_tools.catalog_trust import CatalogVerifier
        return CatalogVerifier(self.policy, state)
