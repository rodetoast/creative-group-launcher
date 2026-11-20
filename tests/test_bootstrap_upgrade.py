from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from southpaw_tools import bootstrap_upgrade as upgrade
from southpaw_tools.common import LauncherError, atomic_json, digest, read_json


class BootstrapUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.stage = self.root / upgrade.STAGE
        self.stage.mkdir()
        self.entry = self.root / upgrade.ENTRY
        self.entry.write_bytes(b"new")
        self.backup = self.stage / "previous.exe"
        self.backup.write_bytes(b"previous")
        self.state = {"generation": 2, "nonce": "c" * 32, "phase": "switching",
                      "old_sha256": digest(self.backup), "release_id": "candidate",
                      "kind": "bridge", "worker": {"pid": 42}}
        self.spec = {"files": {upgrade.ENTRY: digest(self.entry)},
                     "old_entry": {"bridge": [self.state["old_sha256"]]}}
        atomic_json(self.stage / "transaction.json", self.state)

    def test_restore_keeps_legacy_runtime_and_rod_store_intact(self):
        runtime = self.root / "_internal"
        runtime.mkdir()
        (runtime / "library.dll").write_bytes(b"keep")
        home = upgrade._home(self.root, "bridge")
        home.mkdir(parents=True)
        (home / "current.json").write_bytes(b"keep")
        upgrade._restore(self.root, self.stage, self.state, self.spec)
        self.assertEqual(self.entry.read_bytes(), b"previous")
        self.assertEqual((runtime / "library.dll").read_bytes(), b"keep")
        self.assertEqual((home / "current.json").read_bytes(), b"keep")
        self.assertEqual(read_json(self.stage / "transaction.json")["phase"], "restored")

    def test_restore_rejects_corrupt_backup_and_unknown_entry(self):
        self.backup.write_bytes(b"tampered")
        with self.assertRaises(LauncherError):
            upgrade._restore(self.root, self.stage, self.state, self.spec)
        self.assertEqual(self.entry.read_bytes(), b"new")
        self.backup.write_bytes(b"previous")
        self.entry.write_bytes(b"unknown")
        with self.assertRaises(LauncherError):
            upgrade._restore(self.root, self.stage, self.state, self.spec)
        self.assertEqual(self.entry.read_bytes(), b"unknown")

    def test_bridged_trial_uses_existing_home_and_requires_nonce(self):
        with (patch("sys.executable", str(self.entry)),
              patch.object(upgrade, "still_same", return_value=True),
              patch.object(upgrade, "identity", return_value={"pid": 43, "image": str(self.entry)})):
            with self.assertRaises(LauncherError):
                upgrade.entry_route("not-authorized")
            with self.assertRaises(LauncherError):
                upgrade.entry_route(None)
            home, confirm, _ = upgrade.entry_route(self.state["nonce"])
            self.assertEqual(home, self.root / "launcher-home" / "rod" / "launcher-home")
            with self.assertRaises(LauncherError):
                confirm(SimpleNamespace(app=SimpleNamespace(release_id="unapproved")))
            self.assertFalse((self.stage / "confirmed.json").exists())
            confirm(SimpleNamespace(app=SimpleNamespace(release_id="candidate")))
        ack = read_json(self.stage / "confirmed.json")
        self.assertEqual(ack["nonce"], self.state["nonce"])
        self.assertEqual(ack["release_id"], "candidate")
        self.assertEqual(read_json(self.stage / "transaction.json")["phase"], "switching")

    def test_worker_error_returns_to_supervisor_without_unhandled_dialog(self):
        from southpaw_tools.startup_splash import frozen_bootstrap

        with (patch("sys.argv", ["CGLBootstrap.exe", "--bootstrap-swap"]),
              patch.object(upgrade, "worker", side_effect=LauncherError("trial failed")),
              patch("builtins.print") as printed):
            self.assertEqual(frozen_bootstrap(self.root, upgrade_entry=True), 1)
        printed.assert_called_once()
