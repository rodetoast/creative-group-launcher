import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from southpaw_tools.bootstrap import WindowsUpdater
from southpaw_tools.common import LauncherError, atomic_json, digest, read_json
from southpaw_tools.github_provider import GitHubReleasesProvider
from southpaw_tools.managed_update import initialize
from southpaw_tools.self_update import SelfUpdater
from tests.self_update_support import package
from tests.support import TestSigner, temporary
from tests.test_github_provider import FakeGitHub


class ManagedUpdateTests(unittest.TestCase):
    def setUp(self):
        tmp = temporary("managed-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.home, self.data, self.seed = (root / name for name in ("home", "data", "seed"))
        self.data.mkdir()
        self.work = self.data / "work.txt"
        self.work.write_text("preserve")
        self.seed.mkdir()
        self.signer = TestSigner(root)
        self.repo = "toast-source/creative-group-trial-releases"
        self.channel = {"repository": self.repo, "policy": self.signer.policy}
        r1_zip, self.r1 = package(root / "inputs", "launcher-r1", executable="CreativeGroupLauncher.exe")
        self.r2_zip, self.r2 = package(root / "inputs", "launcher-r2", "1.1.0")
        self.signer.publish(self.seed, [self.r1], 1)
        shutil.copyfile(r1_zip, self.seed / self.r1.package_name)

    def updater(self):
        initialize(self.home, self.data, self.seed, self.channel)
        return SelfUpdater(self.home, channel=self.channel)

    def provider(self, updater):
        provider = GitHubReleasesProvider(self.repo, verifier=updater.verifier)
        transport = FakeGitHub()
        provider.api_opener = provider.asset_opener = transport
        raw, sig = self.signer.pair([self.r2], 2)
        files = {"catalog.json": raw, "catalog.sig.json": json.dumps(sig).encode(),
                 self.r2.package_name: self.r2_zip.read_bytes()}
        assets = []
        for index, (name, body) in enumerate(files.items(), 1):
            url = f"https://github.com/{self.repo}/releases/download/next/{name}"
            transport.routes[url] = body
            assets.append({"id": index, "name": name, "state": "uploaded", "size": len(body),
                           "browser_download_url": url})
        transport.routes[provider.api_url] = json.dumps(
            {"id": 2, "tag_name": "next", "draft": False, "prerelease": False, "assets": assets}).encode()
        return provider

    def test_signed_seed_and_github_update_use_separate_program_store(self):
        updater = self.updater()
        original = digest(self.work)
        provider = self.provider(updater)
        transaction = updater.prepare(provider, expected=self.r2)
        self.assertEqual(updater.current(), self.r1)
        updater.request_apply(transaction, approved=True)
        with patch.object(updater, "_probe") as probe:
            self.assertEqual(updater.apply(transaction), self.r2)
        probe.assert_called_once()
        self.assertEqual(self.updater().current(), self.r2)
        self.assertEqual(digest(self.work), original)

    def test_signed_seed_rejects_bad_package_before_activation(self):
        (self.seed / self.r1.package_name).write_bytes(b"tampered")
        with self.assertRaisesRegex(LauncherError, "SHA-256"):
            self.updater()
        self.assertFalse((self.home / "current.json").exists())

    def test_channel_and_confirmed_candidate_are_enforced(self):
        updater = self.updater()
        provider = self.provider(updater)
        with self.assertRaisesRegex(LauncherError, "바뀌었습니다"):
            updater.prepare(provider, expected=self.r1)
        provider.repository = "toast-source/creative-group-releases"
        with self.assertRaises(LauncherError):
            updater.prepare(provider, expected=self.r2)
        self.assertEqual(updater.current(), self.r1)

    def test_failed_probe_keeps_previous_launcher_and_user_data(self):
        updater = self.updater()
        transaction = updater.prepare(self.provider(updater), expected=self.r2)
        updater.request_apply(transaction, approved=True)
        with patch.object(updater, "_probe", side_effect=LauncherError("test probe failure")):
            with self.assertRaisesRegex(LauncherError, "복구"):
                updater.apply(transaction)
        self.assertEqual(updater.current(), self.r1)
        self.assertEqual(updater.journal(transaction)["phase"], "rolled_back")
        self.assertEqual(self.work.read_text(), "preserve")

    def test_bootstrap_rejects_rewritten_payload_manifest_and_receipt(self):
        updater = self.updater()
        managed = WindowsUpdater(self.home, channel=self.channel)
        self.assertEqual(managed.current(), self.r1)
        release = updater.engine.paths.release(self.r1.app_id, self.r1.release_id)
        payload = release / "payload"
        changed = payload / "assets/layout.json"
        changed.write_text('{"tampered":true}')
        manifest_path = payload / "launcher-package.json"
        manifest = read_json(manifest_path)
        manifest["files"]["assets/layout.json"] = digest(changed)
        atomic_json(manifest_path, manifest)
        receipt_path = release / "receipt.json"
        receipt = read_json(receipt_path)
        receipt["files"]["assets/layout.json"] = digest(changed)
        receipt["files"]["launcher-package.json"] = digest(manifest_path)
        atomic_json(receipt_path, receipt)
        with self.assertRaisesRegex(LauncherError, "원본 ZIP"):
            managed.current()
