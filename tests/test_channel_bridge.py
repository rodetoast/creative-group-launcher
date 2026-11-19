import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import zipfile

from southpaw_tools.catalog_trust import CatalogVerifier, catalog_bytes, sign
from southpaw_tools.channel_bridge import (
    BridgedAppVerifier, HOME, TOAST, fallback_lease, legacy_binding, run_bridge,
)
from southpaw_tools.common import LauncherError, app_lock, digest
from southpaw_tools.github_channels import CANONICAL_CATALOG_ID, CANONICAL_REPOSITORY
from southpaw_tools.github_provider import GitHubReleasesProvider
from southpaw_tools.managed_update import initialize
from southpaw_tools.self_update import SelfUpdater
from tests.self_update_support import package
from tests.support import TestSigner, temporary
from tests.test_github_provider import FakeGitHub


class ChannelBridgeTests(TestCase):
    def setUp(self):
        temp = temporary("bridge-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.signer = TestSigner(self.root)
        self.toast = {"repository": TOAST, "policy": self.signer.policy}
        self.rod = {"repository": CANONICAL_REPOSITORY, "repository_id": 1462539740,
                    "policy": {**self.signer.policy, "catalog_id": CANONICAL_CATALOG_ID, "minimum_sequence": 9}}
        self.legacy = self.root / HOME
        self.rod_home = self.legacy / "rod" / HOME
        self.data = self.root / "data"
        (self.data / "apps").mkdir(parents=True)
        (self.data / "settings.json").write_text('{"theme":"dark"}')
        for i in range(5):
            app = self.data / "apps" / str(i)
            app.mkdir()
            for name in ("active.json", "receipt.json", "catalog-proof.json", "work.txt"):
                (app / name).write_text(f"fixture {i}: {name}")
        (self.data / "catalog-trust.json").write_text("legacy trust fixture")
        self.payload = self.root / "bridge-payload"
        self.payload.mkdir()
        self.write(self.payload / "rod-channel.json", self.rod)
        stub = self.root / "CGLBootstrap.exe"
        stub.write_bytes(b"MZ test bytes")
        with zipfile.ZipFile(self.payload / "rod-bootstrap.zip", "w") as archive:
            archive.write(stub, stub.name)
        self.write(self.payload / "rod-bootstrap-files.json", {stub.name: digest(stub)})
        self.zip, self.app = package(self.root / "inputs", "rod-first", "0.1.7", executable="CreativeGroupLauncher.exe")

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def old(self, value):
        archive, app = package(self.root / "inputs", "old-" + value, value, executable="CreativeGroupLauncher.exe")
        seed = self.root / "old-seed"
        seed.mkdir()
        raw, sig = self.signer.pair([app], 8)
        (seed / "catalog.json").write_bytes(raw)
        self.write(seed / "catalog.sig.json", sig)
        (seed / app.package_name).write_bytes(archive.read_bytes())
        initialize(self.legacy, self.data, seed, self.toast)
        return SelfUpdater(self.legacy, channel=self.toast)

    def transport(self, repo, provider_url, app, archive, seq, *, catalog_id=None):
        raw = catalog_bytes([app], seq, **({"catalog_id": catalog_id} if catalog_id else {}))
        files = {"catalog.json": raw, "catalog.sig.json": json.dumps(sign(raw, self.signer.private)).encode(),
                 app.package_name: archive.read_bytes()}
        fake = FakeGitHub()
        rows = []
        for index, (name, content) in enumerate(files.items(), 1):
            url = f"https://github.com/{repo}/releases/download/fixture/{name}"
            fake.routes[url] = content
            rows.append({"id": index, "name": name, "size": len(content), "state": "uploaded", "browser_download_url": url})
        fake.routes[provider_url] = json.dumps({"id": 1, "tag_name": "fixture", "draft": False,
                                               "prerelease": False, "assets": rows}).encode()
        return fake

    def provider(self, repo, verifier, repository_id=None, *, seq=10, app=None, archive=None):
        provider = GitHubReleasesProvider(repo, verifier=verifier, repository_id=repository_id)
        fake = self.transport(repo, provider.api_url, app or self.app, archive or self.zip, seq,
                              catalog_id=CANONICAL_CATALOG_ID if repository_id else None)
        provider.api_opener = provider.asset_opener = fake
        return provider

    def bridge(self, old, **kwargs):
        session = SimpleNamespace(mode="normal", channel=self.toast, updater=old, data_root=self.data)
        def fixture(repo, **config):
            self.assertEqual((repo, config["repository_id"]), (CANONICAL_REPOSITORY, 1462539740))
            return self.provider(repo, **config, **kwargs)
        return session, patch("southpaw_tools.github_provider.GitHubReleasesProvider", side_effect=fixture)

    def snapshot(self):
        return {p.relative_to(self.data).as_posix():digest(p) for p in self.data.rglob("*") if p.is_file()}

    def test_toast_014_installs_bridge_and_first_run_then_rod_update(self):
        old = self.old("0.1.4")
        bridge_zip, bridge_app = package(self.root / "inputs", "toast-bridge", "0.1.6", executable="CreativeGroupLauncher.exe")
        provider = self.provider(TOAST, old.verifier, seq=9, app=bridge_app, archive=bridge_zip)
        tx = old.prepare(provider)
        old.request_apply(tx, approved=True)
        with patch.object(old, "_probe"):
            self.assertEqual(old.apply(tx), bridge_app)
        before = self.snapshot()
        session, fixture = self.bridge(old)
        with fixture as network, patch("southpaw_tools.channel_bridge.subprocess.run", return_value=SimpleNamespace(returncode=0)) as launch:
            run_bridge(session, self.payload, Event())
            run_bridge(session, self.payload, Event())
        self.assertEqual(network.call_count, 1)
        self.assertEqual(launch.call_count, 2)
        rod = SelfUpdater(self.rod_home, channel=self.rod)
        self.assertEqual(rod.current(), self.app)
        newer_zip, newer = package(self.root / "inputs", "rod-next", "0.1.8", executable="CreativeGroupLauncher.exe")
        provider = self.provider(CANONICAL_REPOSITORY, rod.verifier, 1462539740, seq=11, app=newer, archive=newer_zip)
        tx = rod.prepare(provider)
        rod.request_apply(tx, approved=True)
        with patch.object(rod, "_probe"):
            self.assertEqual(rod.apply(tx), newer)
        self.assertEqual(old.current(), bridge_app)
        self.assertEqual(self.snapshot(), before)

    def test_toast_015_seed9_fails_closed_then_rod10_can_resume(self):
        old = self.old("0.1.5")
        before = self.snapshot()
        session, fixture = self.bridge(old, seq=9)
        with fixture, patch("southpaw_tools.channel_bridge.subprocess.run") as launch:
            with self.assertRaises(LauncherError):
                run_bridge(session, self.payload, Event())
        launch.assert_not_called()
        self.assertFalse((self.rod_home / "current.json").exists())
        session, fixture = self.bridge(old)
        with fixture, patch("southpaw_tools.channel_bridge.subprocess.run", return_value=SimpleNamespace(returncode=0)):
            run_bridge(session, self.payload, Event())
        self.assertEqual(self.snapshot(), before)

    def test_child_failure_preserves_legacy_and_blocks_duplicate_fallback(self):
        old = self.old("0.1.5")
        before = self.snapshot()
        session, fixture = self.bridge(old)
        with fixture, patch("southpaw_tools.channel_bridge.subprocess.run", return_value=SimpleNamespace(returncode=2)):
            with self.assertRaisesRegex(LauncherError, "2"):
                run_bridge(session, self.payload, Event())
        with app_lock(self.rod_home / "locks/running.lock"):
            with self.assertRaises(LauncherError):
                fallback_lease(self.legacy)
        with fallback_lease(self.legacy):
            self.assertEqual(old.current().version, "0.1.5")
        self.assertEqual(self.snapshot(), before)
        with self.assertRaises(LauncherError):
            legacy_binding(self.rod_home, self.root / "wrong")
        (self.legacy / "rod" / "CGLBootstrap.exe").write_bytes(b"changed")
        with patch("southpaw_tools.channel_bridge.subprocess.run") as launch:
            with self.assertRaises(LauncherError):
                run_bridge(session, self.payload, Event())
            launch.assert_not_called()

    def test_historical_proof_does_not_authorize_online_or_launcher(self):
        from dataclasses import replace
        app = replace(self.app, app_id="tile-namer")
        old = CatalogVerifier(self.toast["policy"], self.root / "old-trust.json")
        raw, sig = self.signer.pair([app, self.app], 8)
        signed = json.dumps(sig).encode()
        old.accept(raw, signed)
        state = json.loads(old.state_path.read_bytes())
        verifier = BridgedAppVerifier(self.rod["policy"], self.root / "rod-trust.json")
        verifier.verify_installed_release(state, app)
        with self.assertRaises(LauncherError):
            verifier.verify_installed_release(state, self.app)
        with self.assertRaises(LauncherError):
            verifier.accept(raw, signed)
        self.assertFalse(verifier.state_path.exists())
