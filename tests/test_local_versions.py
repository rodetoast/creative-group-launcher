import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from southpaw_tools.common import LauncherError, atomic_json, digest, read_json
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from southpaw_tools.providers import HttpProvider
from tests.support import FakeProcesses, TestSigner, package, temporary


class LocalVersionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary("local-versions-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = AppPaths(self.root / "client")
        self.processes = FakeProcesses()
        self.engine = Installer(self.paths, self.processes)
        self.signer = TestSigner(self.root)
        self.state = self.paths.root / "catalog-trust.json"
        self.verifier = self.signer.verifier(self.state)
        self.engine.catalog_verifier = self.verifier
        self.r1 = self.install("r1", 1)
        self.old_payload = self.paths.release("dummy", "r1") / "payload"
        (self.old_payload / "settings.json").write_text("older settings")
        self.r2 = self.install("r2", 2)
        self.new_payload = self.paths.release("dummy", "r2") / "payload"
        (self.new_payload / "settings.json").write_text("newer settings")
        (self.new_payload / "user-projects").mkdir()
        (self.new_payload / "user-projects" / "work.txt").write_text("newer work")
        self.pointer = self.paths.app("dummy") / "active.json"

    def install(self, release_id, sequence):
        source, app = package(self.root / "inputs", release_id)
        raw, signature = self.signer.pair([app], sequence)
        provider = HttpProvider("http://127.0.0.1:8765", verifier=self.verifier)

        def response(path):
            if path == "/api/catalog":
                return io.BytesIO(raw)
            if path == "/api/catalog.sig":
                return io.BytesIO(json.dumps(signature).encode())
            self.assertEqual(path, f"/packages/{app.package_name}")
            stream = io.BytesIO(source.read_bytes())
            stream.headers = {"Content-Length": str(source.stat().st_size)}
            return stream

        provider._open = response
        return self.engine.install(app, provider)

    def select(self, target, *, pinned=True):
        return self.engine.select_release("dummy", target.release_id, pinned=pinned,
            expected_current=self.engine.installed("dummy"), expected_release=target)

    def test_offline_round_trip_retains_data_pin_and_high_water(self):
        high_water = self.state.read_bytes()
        other = self.paths.app("other") / "active.json"
        atomic_json(other, {"synthetic": "other app"})
        other_before = other.read_bytes()
        self.assertEqual(self.engine.retained_versions("dummy"), [self.r1, self.r2])
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("network access")):
            self.assertEqual(self.select(self.r1), self.r1)
            self.assertTrue(self.engine.selection_pinned("dummy"))
            self.assertEqual(self.engine.installed("dummy"), self.r1)
            self.assertTrue(self.r2.is_new_release(self.r1))
            self.assertEqual(self.select(self.r2, pinned=False), self.r2)
        self.assertFalse(self.engine.selection_pinned("dummy"))
        self.assertEqual((self.old_payload / "settings.json").read_text(), "older settings")
        self.assertEqual((self.new_payload / "settings.json").read_text(), "newer settings")
        self.assertEqual((self.new_payload / "user-projects" / "work.txt").read_text(), "newer work")
        self.assertEqual(self.state.read_bytes(), high_water)
        self.assertEqual(other.read_bytes(), other_before)
        raw, signature = self.signer.pair([self.r1], 1)
        with self.assertRaises(LauncherError):
            self.verifier.accept(raw, json.dumps(signature).encode())
        self.assertFalse(self.processes.calls)

    def test_gui_confirms_offline_selection_and_displays_latest_separately(self):
        from PySide6.QtCore import QEventLoop, QTimer
        from PySide6.QtWidgets import QApplication, QMessageBox
        from southpaw_tools.catalog import catalog_document
        from southpaw_tools.ui import MainWindow

        gui = QApplication.instance() or QApplication([])
        catalog = self.root / "catalog.json"
        atomic_json(catalog, catalog_document([self.r2]))
        window = MainWindow(self.paths, catalog_path=catalog, auto_connect=False, installer=self.engine)
        self.addCleanup(window.close)
        self.engine.catalog_verifier = self.verifier
        with patch("southpaw_tools.ui.QInputDialog.getItem", return_value=("1.0.0 · r1", True)):
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
                window.choose_version()
                self.assertEqual(self.engine.installed("dummy"), self.r2)
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                window.choose_version()
        self.assertIsNotNone(window.task)
        loop = QEventLoop()
        window.task.finished.connect(loop.quit)
        QTimer.singleShot(8000, loop.quit)
        loop.exec()
        gui.processEvents()
        self.assertIsNone(window.task)
        self.assertEqual(self.engine.installed("dummy"), self.r1)
        self.assertEqual(window.info["설치 버전"].toolTip(), "r1")
        self.assertEqual(window.info["배포 식별자"].text(), "r2")
        self.assertIn("이전 버전 사용 중", window.info["설치 상태"].text())
        self.assertFalse(self.processes.calls)

    def test_running_app_blocks_switch(self):
        self.processes.running = True
        with self.assertRaises(LauncherError):
            self.select(self.r1)
        self.assertEqual(self.engine.installed("dummy"), self.r2)
        self.assertFalse(self.engine.pending_recovery("dummy"))

    def test_tampered_payload_and_forged_receipt_cannot_switch(self):
        asset = self.old_payload / "asset.json"
        asset.write_text("damaged")
        with self.assertRaises(LauncherError):
            self.select(self.r1)
        receipt = self.old_payload.parent / "receipt.json"
        data = read_json(receipt)
        data["files"]["asset.json"] = digest(asset)
        atomic_json(receipt, data)
        with self.assertRaisesRegex(LauncherError, "원본 ZIP"):
            self.select(self.r1)
        self.assertEqual(self.engine.installed("dummy"), self.r2)

    def test_unsigned_legacy_receipt_is_not_selectable(self):
        (self.old_payload.parent / "catalog-proof.json").unlink()
        self.assertEqual(self.engine.retained_versions("dummy"), [self.r2])
        with self.assertRaises(LauncherError):
            self.select(self.r1)

    def test_unexpected_executable_in_preserve_path_blocks_switch(self):
        projects = self.old_payload / "user-projects"
        projects.mkdir()
        unexpected = projects / "unexpected.dll"
        unexpected.write_bytes(b"dummy fixture")
        with self.assertRaises(LauncherError):
            self.select(self.r1)
        self.assertTrue(unexpected.exists())

    def test_atomic_replace_failure_preserves_previous_pointer_and_recovers(self):
        from southpaw_tools import common

        original = common.os.replace
        previous = self.pointer.read_bytes()

        def reject_pointer(source, destination):
            if Path(destination) == self.pointer:
                raise PermissionError("injected pointer failure")
            return original(source, destination)

        with patch.object(common.os, "replace", side_effect=reject_pointer), self.assertRaises(PermissionError):
            self.select(self.r1)
        self.assertEqual(self.pointer.read_bytes(), previous)
        self.assertTrue(self.engine.pending_recovery("dummy"))
        self.assertEqual(self.engine.recover("dummy"), self.r2)
        self.assertFalse(self.engine.pending_recovery("dummy"))

    def test_restart_after_pointer_commit_verifies_target(self):
        with patch.object(self.engine, "_finish", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.select(self.r1)
        self.assertTrue(self.engine.pending_recovery("dummy"))
        restarted = Installer(self.paths, self.processes)
        restarted.catalog_verifier = self.verifier
        self.assertEqual(restarted.recover("dummy"), self.r1)
        self.assertTrue(restarted.selection_pinned("dummy"))
        self.assertFalse(restarted.pending_recovery("dummy"))

    def test_restart_after_pointer_commit_restores_previous_on_corruption(self):
        with patch.object(self.engine, "_finish", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.select(self.r1)
        (self.old_payload / "asset.json").write_text("damaged")
        self.assertEqual(self.engine.recover("dummy"), self.r2)
        self.assertFalse(self.engine.selection_pinned("dummy"))
        self.assertFalse(self.engine.pending_recovery("dummy"))
