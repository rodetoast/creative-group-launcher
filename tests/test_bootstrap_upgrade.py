from contextlib import nullcontext
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

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
        self.state = {"generation": upgrade.GENERATION, "nonce": "c" * 32, "phase": "switching",
                      "old_sha256": digest(self.backup), "release_id": "candidate",
                      "kind": "bridge", "worker": {"pid": 42}}
        self.spec = {"files": {upgrade.ENTRY: digest(self.entry)},
                     "old_entry": {"bridge": [self.state["old_sha256"]]}}
        atomic_json(self.stage / "transaction.json", self.state)

    def test_restore_keeps_legacy_runtime_and_rod_store_intact(self):
        runtime = self.root / "_cgl_b2"
        runtime.mkdir()
        (runtime / "library.dll").write_bytes(b"keep")
        previous_state = self.root / ".bootstrap-v2" / "transaction.json"
        atomic_json(previous_state, {"generation": 2, "phase": "committed"})
        before = previous_state.read_bytes()
        home = upgrade._home(self.root, "bridge")
        home.mkdir(parents=True)
        (home / "current.json").write_bytes(b"keep")
        upgrade._restore(self.root, self.stage, self.state, self.spec)
        self.assertEqual(self.entry.read_bytes(), b"previous")
        self.assertEqual((runtime / "library.dll").read_bytes(), b"keep")
        self.assertEqual(previous_state.read_bytes(), before)
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

    @unittest.skipUnless(os.name == "nt", "Windows Bootstrap entry")
    def test_unknown_old_image_is_rejected_before_staging(self):
        root = self.root / "another-installation"
        root.mkdir()
        entry = root / upgrade.ENTRY
        entry.write_bytes(b"unknown")
        payload = root / "payload"
        payload.mkdir()
        (payload / upgrade.SPEC).touch()
        current = object()
        session = SimpleNamespace(mode="normal", current=current, channel={}, updater=SimpleNamespace(home=root))
        with (patch("sys.executable", str(payload / "CreativeGroupLauncher.exe")),
              patch.object(upgrade, "canonical_channel", return_value=True),
              patch.object(upgrade, "_entry_root", return_value=(root, "rod")),
              patch.object(upgrade, "_approved", return_value=True),
              patch.object(upgrade, "_signed_candidate", return_value=(
                  session.updater, current, payload, {"old_entry": {"rod": [self.state["old_sha256"]]}})),
              patch.object(upgrade, "_lineage") as lineage):
            with self.assertRaisesRegex(LauncherError, "자동 교체 대상"):
                upgrade.begin(session, None)
        lineage.assert_not_called()
        self.assertEqual(entry.read_bytes(), b"unknown")
        self.assertFalse((root / upgrade.STAGE).exists())

    def test_probationary_log_failure_stops_new_gui_before_restore(self):
        from southpaw_tools.bootstrap import Bootstrap

        app = SimpleNamespace(release_id="candidate")
        boot = Bootstrap.__new__(Bootstrap)
        boot.updater = SimpleNamespace(home=self.root, channel={"repository": "fixture"},
                                      current=lambda: app, recover=lambda: None, _lock=nullcontext)
        boot.splash = None

        def event(phase, **_):
            if phase == "running":
                raise PermissionError("simulated log sharing conflict")

        boot.event = event
        confirm = Mock()
        with patch("southpaw_tools.bootstrap.Session") as session:
            with self.assertRaises(PermissionError):
                boot.run(on_confirmed=confirm)
        session.return_value.confirm.assert_called_once()
        session.return_value.stop.assert_called_once()
        confirm.assert_not_called()
