from __future__ import annotations

import json
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from southpaw_tools.common import Cancelled, LauncherError, app_lock, digest
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from southpaw_tools.processes import Processes
from tests.support import FakeProcesses, LocalProvider, TestSigner, package, temporary


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary("southpaw-install-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = AppPaths(self.root / "client")
        self.processes = FakeProcesses()
        self.engine = Installer(self.paths, self.processes)
        self.source, self.app = package(self.root / "packages")

    def install(self):
        self.engine.install(self.app, LocalProvider(self.source))
        return self.engine.resolve_launch(self.app)

    def test_install_and_offline_launch_without_settings_or_catalog(self):
        exe, cwd = self.install()
        self.assertFalse((self.paths.root / "settings.json").exists())
        self.assertFalse((self.paths.root / "catalog-cache.json").exists())
        restarted = Installer(self.paths, self.processes)
        self.assertEqual(restarted.launch("dummy"), "dummy-process")
        self.assertEqual(self.processes.calls, [(exe, cwd)])

    def test_shortcut_launch_tracks_active_release_and_requires_signed_proof(self):
        signer = TestSigner(self.root)
        verifier = signer.verifier(self.paths.root / "catalog-trust.json")
        self.engine.catalog_verifier = verifier
        source2, release2 = package(self.root / "packages", "r2", version="2.0.0")
        resolved = []
        for sequence, source, app in ((1, self.source, self.app), (2, source2, release2)):
            raw, signature = signer.pair([app], sequence)
            verifier.accept(raw, json.dumps(signature).encode())
            provider = LocalProvider(source)
            provider.verifier = verifier
            self.engine.install(app, provider)
            # A new engine instance models opening the same app ID without a GUI.
            independent = Installer(self.paths, self.processes)
            independent.catalog_verifier = verifier
            independent.launch("dummy", verify_receipt=True)
            exe, cwd = independent.resolve_launch(app)
            resolved.append(exe)
            self.assertEqual(self.processes.calls[-1], (exe, cwd))
            self.processes.running = False

        self.assertNotEqual(*resolved)
        proof = self.paths.release("dummy", release2.release_id) / "catalog-proof.json"
        proof.unlink()
        with self.assertRaises(LauncherError):
            independent.launch("dummy", verify_receipt=True)
        self.assertEqual(len(self.processes.calls), 2)

    def test_running_program_blocks_update_uninstall_and_duplicate_launch(self):
        self.install()
        self.processes.running = True
        source, new = package(self.root / "packages", "r2")
        for call in (lambda: self.engine.install(new, LocalProvider(source)),
                     lambda: self.engine.uninstall("dummy"), lambda: self.engine.launch("dummy")):
            with self.assertRaises(LauncherError):
                call()
        self.assertEqual(self.engine.installed("dummy"), self.app)

    def test_successful_update_preserves_old_version_and_migrates_known_user_data(self):
        exe, cwd = self.install()
        (cwd / "settings.json").write_text('{"user": "keep"}')
        (cwd / "user-projects").mkdir()
        (cwd / "user-projects/art.json").write_text("important art")
        (cwd / "user-projects/do-not-migrate.exe").write_bytes(b"MZ user executable")
        (cwd / "unknown-user-file.txt").write_text("unknown work")
        (cwd / "asset.json").write_text("user modified asset")
        old_hash = digest(exe)
        source, new = package(self.root / "packages", "r2", version=self.app.version)
        self.engine.install(new, LocalProvider(source))
        _, new_cwd = self.engine.resolve_launch(new)
        self.assertEqual((new_cwd / "settings.json").read_text(), '{"user": "keep"}')
        self.assertEqual((new_cwd / "user-projects/art.json").read_text(), "important art")
        self.assertFalse((new_cwd / "user-projects/do-not-migrate.exe").exists())
        self.assertEqual((cwd / "unknown-user-file.txt").read_text(), "unknown work")
        self.assertEqual((cwd / "asset.json").read_text(), "user modified asset")
        self.assertEqual(digest(exe), old_hash)
        self.assertEqual(self.engine.installed("dummy"), new)

    def test_activation_failure_keeps_original_pointer_and_files(self):
        exe, cwd = self.install()
        pointer = (self.paths.app("dummy") / "active.json").read_bytes()
        source, new = package(self.root / "packages", "r2")
        with patch.object(self.engine, "_activate", side_effect=OSError("disk failure")):
            with self.assertRaises(LauncherError):
                self.engine.install(new, LocalProvider(source))
        self.assertEqual((self.paths.app("dummy") / "active.json").read_bytes(), pointer)
        self.assertTrue(exe.is_file())
        self.assertFalse(self.paths.release("dummy", "r2").exists())

    def test_bad_update_download_keeps_old_and_removes_partial(self):
        exe, _ = self.install()
        source, new = package(self.root / "packages", "r2")
        source.write_bytes(source.read_bytes()[:20])
        with self.assertRaises(LauncherError):
            self.engine.install(new, LocalProvider(source))
        self.assertEqual(self.engine.installed("dummy"), self.app)
        self.assertTrue(exe.exists())
        self.assertEqual(list(self.paths.downloads.glob("*.zip")), [])

    def test_migration_failure_keeps_old_settings_and_active_version(self):
        _, cwd = self.install()
        (cwd / "settings.json").write_text("important")
        source, new = package(self.root / "packages", "r2")
        with patch("southpaw_tools.installer.shutil.copy2", side_effect=OSError("copy denied")):
            with self.assertRaises(LauncherError):
                self.engine.install(new, LocalProvider(source))
        self.assertEqual(self.engine.installed("dummy"), self.app)
        self.assertEqual((cwd / "settings.json").read_text(), "important")
        self.assertFalse(self.paths.release("dummy", "r2").exists())

    def test_app_starting_during_install_prevents_activation(self):
        self.install()
        source, new = package(self.root / "packages", "r2")
        with patch.object(self.processes, "is_running", side_effect=[False, True]):
            with self.assertRaises(LauncherError):
                self.engine.install(new, LocalProvider(source))
        self.assertEqual(self.engine.installed("dummy"), self.app)
        self.assertFalse(self.paths.release("dummy", "r2").exists())

    def test_cancelled_update_keeps_old(self):
        self.install()
        source, new = package(self.root / "packages", "r2")
        event = threading.Event()
        with self.assertRaises(Cancelled):
            self.engine.install(new, LocalProvider(source), lambda *_: event.set(), event)
        self.assertEqual(self.engine.installed("dummy"), self.app)
        self.assertFalse(self.paths.release("dummy", "r2").exists())

    def test_same_id_changed_hash_and_unpublished_rejected(self):
        self.install()
        for app in (replace(self.app, sha256="f" * 64), replace(self.app, published=False)):
            with self.assertRaises(LauncherError):
                self.engine.install(app, LocalProvider(self.source))

    def test_existing_release_never_overwritten(self):
        self.paths.release("dummy", "r1").mkdir(parents=True)
        sentinel = self.paths.release("dummy", "r1") / "user.txt"
        sentinel.write_text("keep")
        with self.assertRaises(LauncherError):
            self.install()
        self.assertEqual(sentinel.read_text(), "keep")

    def test_uninstall_preserves_unknown_and_modified_files(self):
        exe, cwd = self.install()
        (cwd / "settings.json").write_text("user config")
        (cwd / "unknown.txt").write_text("user work")
        (cwd / "asset.json").write_text("modified")
        result = self.engine.uninstall("dummy")
        self.assertIsNone(self.engine.installed("dummy"))
        self.assertFalse(exe.exists())
        self.assertEqual((cwd / "settings.json").read_text(), "user config")
        self.assertEqual((cwd / "unknown.txt").read_text(), "user work")
        self.assertEqual((cwd / "asset.json").read_text(), "modified")
        self.assertGreaterEqual(len(result["retained_files"]), 3)

    def test_modified_installed_exe_not_executed_or_deleted(self):
        exe, _ = self.install()
        exe.write_bytes(b"MZ user modified")
        with self.assertRaises(LauncherError):
            self.engine.launch("dummy")
        self.assertEqual(self.processes.calls, [])
        self.engine.uninstall("dummy")
        self.assertTrue(exe.exists())

    def test_cross_client_app_lock(self):
        with app_lock(self.paths.lock("dummy")):
            with self.assertRaises(LauncherError):
                self.install()
        self.install()

    def test_nested_launch_has_correct_working_directory(self):
        source, app = package(self.root / "packages", "nested", nested=True)
        self.engine.install(app, LocalProvider(source))
        self.engine.launch("dummy")
        exe, cwd = self.processes.calls[0]
        self.assertEqual(exe.parent, cwd)
        self.assertEqual(cwd.name, "Dummy")

    def test_windows_external_process_scan_sees_our_interpreter(self):
        import os
        import sys
        if os.name != "nt":
            self.skipTest("Windows process API")
        self.assertTrue(Processes().is_running(Path(sys.executable).parent))
        self.assertFalse(Processes().is_running(self.root / "never-running"))


if __name__ == "__main__":
    unittest.main()
