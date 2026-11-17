"""Exercise the employee GUI approval callback through the managed updater."""
import unittest
import urllib.error
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox

from southpaw_tools.common import LauncherError, digest, read_json
from southpaw_tools.installer import Installer
from southpaw_tools.managed_update import ManagedSession
from southpaw_tools.paths import AppPaths
from southpaw_tools.ui import MainWindow
from tests import test_managed_update as managed_tests
from tests import test_ui as ui_tests
from tests.support import FakeProcesses, LocalProvider, package


class ManagedUpdateGuiTests(unittest.TestCase):
    wait_task = ui_tests.UiTests.wait_task
    close_windows = ui_tests.UiTests.close_windows

    def setUp(self):
        fixture = managed_tests.ManagedUpdateTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.updater = fixture.updater()
        self.windows = []
        self.addCleanup(self.close_windows)
        session = ManagedSession.__new__(ManagedSession)
        session.channel = fixture.channel
        session.updater = self.updater
        session.current = fixture.r1
        session.mode = "normal"
        session.file = self.updater.home / "sessions/gui/context.json"
        session.file.parent.mkdir(parents=True)
        session.context = {"session": "gui", "nonce": "test-only", "release_id": fixture.r1.release_id,
                           "version": fixture.r1.version, "exe_sha256": fixture.r1.executable_sha256}
        self.session = session
        self.provider = fixture.provider(self.updater)
        self.transport = self.provider.api_opener
        running_exe, _ = self.updater.engine.resolve_launch(fixture.r1)
        self.running = patch.object(self.updater.engine.processes, "is_running",
                                    side_effect=lambda root: running_exe.is_relative_to(root))
        self.running.start()
        self.addCleanup(self.running.stop)
        self.assertTrue(self.updater.engine.is_running(fixture.r1.app_id))
        self.window = MainWindow(AppPaths(fixture.data), auto_connect=False, managed_session=session)
        self.windows.append(self.window)
        self.window.online = True
        self.window.launcher_candidate = fixture.r2
        self.before = {str(p.relative_to(fixture.data)): digest(p)
                       for p in fixture.data.rglob("*") if p.is_file()}
        self.pointer = (fixture.home / "current.json").read_bytes()

    def approve(self):
        with (
            patch("southpaw_tools.github_provider.urllib.request.build_opener", return_value=self.transport),
            patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes),
            patch.object(QApplication, "exit") as exit_app,
        ):
            self.window.launcher_update_button.click()
            self.wait_task(self.window)
            QApplication.processEvents()
            return exit_app.call_args_list

    def assert_preserved(self):
        f = self.fixture
        self.assertEqual((f.home / "current.json").read_bytes(), self.pointer)
        self.assertEqual({str(p.relative_to(f.data)): digest(p) for p in f.data.rglob("*") if p.is_file()},
                         self.before)

    def test_gui_prepares_with_live_launcher_lease_then_requests_normal_exit(self):
        with self.updater._runtime_lock():
            exits = self.approve()
            self.assertEqual([call.args for call in exits], [(20,)])
            request = read_json(self.session.file.parent / "request.json")
            transaction = request["transaction"]
            self.assertEqual(self.updater.journal(transaction)["phase"], "requested")
            with self.assertRaises(LauncherError):
                self.updater.apply(transaction)
            self.assert_preserved()
        with patch.object(self.updater, "_probe"):
            self.updater.apply(transaction)
        self.assertEqual(self.updater.current(), self.fixture.r2)
        self.assertEqual(self.updater.journal(transaction)["phase"], "committed")

    def test_original_app_wide_check_reproduces_gui_reported_failure(self):
        with patch.object(self.updater.engine, "_installation_running",
                          side_effect=lambda app: self.updater.engine.is_running(app.app_id)):
            self.assertEqual(self.approve(), [])
        self.assertIn("실행 중인 프로그램", self.window.message.text())
        self.assertFalse(self.updater.engine.paths.release(self.fixture.r2.app_id, self.fixture.r2.release_id).exists())
        self.assert_preserved()

    def test_cancel_does_not_contact_server_or_create_update_request(self):
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.window.launcher_update_button.click()
        self.assertIsNone(self.window.task)
        self.assertEqual(self.transport.calls, [])
        self.assertFalse((self.session.file.parent / "request.json").exists())
        self.assert_preserved()

    def test_signature_or_download_failure_keeps_current_launcher(self):
        for failure in ("signature", "download"):
            with self.subTest(failure=failure):
                routes = dict(self.transport.routes)
                if failure == "signature":
                    name = next(url for url in routes if url.endswith("/catalog.sig.json"))
                    self.transport.routes[name] = b"{}"
                else:
                    name = next(url for url in routes if url.endswith(self.fixture.r2.package_name))
                    self.transport.routes[name] = urllib.error.URLError("controlled download failure")
                self.assertEqual(self.approve(), [])
                self.assertFalse((self.session.file.parent / "request.json").exists())
                self.assert_preserved()
                self.transport.routes = routes

    def test_handoff_write_failure_cancels_request_without_exiting(self):
        write = __import__("southpaw_tools.managed_update", fromlist=["atomic_json"]).atomic_json

        def fail_request(path, value):
            if path.name == "request.json":
                raise PermissionError("controlled handoff failure")
            return write(path, value)

        with patch("southpaw_tools.managed_update.atomic_json", side_effect=fail_request):
            self.assertEqual(self.approve(), [])
        journals = [self.updater.journal(p.stem) for p in (self.fixture.home / "transactions").glob("*.json")]
        self.assertEqual([j["phase"] for j in journals], ["cancelled"])
        self.assert_preserved()

    def test_regular_company_installer_still_rejects_a_running_app(self):
        f = self.fixture
        processes = FakeProcesses()
        installer = Installer(AppPaths(f.data / "regular-installer"), processes)
        source1, r1 = package(f.data.parent / "company-input")
        source2, r2 = package(f.data.parent / "company-input", "r2")
        installer.install(r1, LocalProvider(source1))
        processes.running = True
        with self.assertRaisesRegex(LauncherError, "실행 중인 프로그램"):
            installer.install(r2, LocalProvider(source2))
        self.assertEqual(installer.installed(r1.app_id), r1)
