from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch
import unittest

from PySide6.QtWidgets import QMessageBox
from southpaw_tools.catalog import catalog_document
from southpaw_tools.common import LauncherError, atomic_json
from tests import test_ui as helpers
from tests.support import LocalProvider, package


class RecoveryUiTests(unittest.TestCase):
    setUp = helpers.UiTests.setUp
    close_windows = helpers.UiTests.close_windows
    def window(self, catalog=None):
        window = helpers.UiTests.window(self,catalog)
        window.config = {'transport':'lan'}  # These fixtures exercise the preserved LAN path.
        window._connection_status()
        return window
    wait_task = helpers.UiTests.wait_task

    def installed_window(self, remote=None):
        source, app = package(self.root / "packages")
        self.engine.install(app, LocalProvider(source))
        catalog = self.root / "catalog.json"
        atomic_json(catalog, catalog_document([remote or app]))
        return self.window(catalog), source, app

    def test_initial_catalog_identity_conflict_keeps_verified_offline_launch(self):
        window, source, app = self.installed_window()
        window.apps = [replace(app, sha256="f" * 64)]
        window.render()
        self.assertEqual(window.info["설치 버전"].text(), app.version)
        self.assertIn("목록 오류", window.info["설치 상태"].text())
        self.assertEqual(window.primary.text(), "실행")
        self.assertTrue(window.primary.isEnabled())
        window.primary_action()
        self.assertEqual(len(self.processes.calls), 1)

    def test_refresh_conflict_does_not_overwrite_cache_or_local_pointer(self):
        window, source, app = self.installed_window()
        cache = self.paths.root / "catalog-cache.json"
        atomic_json(cache, catalog_document([app]))
        before = cache.read_bytes()
        pointer = (self.paths.app("dummy") / "active.json").read_bytes()
        with patch("southpaw_tools.ui.HttpProvider.health", return_value={"lan_enabled": False}), \
             patch("southpaw_tools.ui.HttpProvider.catalog", return_value=[replace(app, sha256="f" * 64)]):
            window.refresh()
            self.wait_task(window)
        self.assertFalse(window.online)
        self.assertEqual(cache.read_bytes(), before)
        self.assertEqual((self.paths.app("dummy") / "active.json").read_bytes(), pointer)
        self.assertTrue(window.primary.isEnabled())
        window.primary_action()
        self.assertEqual(len(self.processes.calls), 1)

    def test_health_success_catalog_failure_is_not_reported_as_server_offline(self):
        window, source, app = self.installed_window()
        with patch("southpaw_tools.ui.HttpProvider.health", return_value={"lan_enabled": False}), \
             patch("southpaw_tools.ui.HttpProvider.catalog", side_effect=LauncherError("bad catalog")):
            window.refresh()
            self.wait_task(window)
        self.assertIn("응답 확인", window.server_status.text())
        self.assertIn("목록: 실패", window.server_status.text())
        self.assertFalse(window.online)
        self.assertTrue(window.primary.isEnabled())

    def test_download_failure_requires_recheck_but_preserves_local_launch(self):
        window, source, app = self.installed_window()
        source2, new = package(self.root / "packages", "r2")
        window.apps, window.online = [new], True
        class Failed:
            def download(self, *args, **kwargs):
                raise LauncherError("network fixture failure")
        window.provider = Failed()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.primary_action()
            self.wait_task(window)
        self.assertFalse(window.online)
        self.assertIn("재확인 필요", window.server_status.text())
        self.assertIn("패키지: 다운로드/검증 실패", window.server_status.text())
        self.assertNotIn("오프라인", window.server_status.text())
        self.assertEqual(window.primary.text(), "실행")
        window.primary_action()
        self.assertEqual(len(self.processes.calls), 1)

    def test_lan_listener_flag_and_actual_loopback_route_are_separate(self):
        window, source, app = self.installed_window()
        with patch("southpaw_tools.ui.HttpProvider.health", return_value={"lan_enabled": True}), \
             patch("southpaw_tools.ui.HttpProvider.catalog", return_value=[app]):
            window.refresh()
            self.wait_task(window)
        self.assertIn("경로: 로컬(loopback)", window.server_status.text())
        self.assertIn("서버 LAN: ON", window.server_status.text())
        self.assertIn("마지막 조회", window.server_status.text())

    def test_missing_exe_is_recovery_state_and_repair_install_is_available(self):
        window, source, app = self.installed_window()
        self.engine.resolve_launch(app)[0].unlink()
        window.render()
        self.assertIn("복구 필요", window.info["설치 상태"].text())
        self.assertFalse(window.primary.isEnabled())
        window.online, window.provider = True, LocalProvider(source)
        window.render()
        self.assertEqual(window.primary.text(), "복구 설치")
        self.assertTrue(window.primary.isEnabled())
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.primary_action()
            self.wait_task(window)
        self.engine.resolve_launch(app)
        self.assertEqual(window.primary.text(), "실행")

    def test_invalid_server_configuration_revokes_old_install_permission(self):
        window = self.window()
        window.online = True
        window.config = {"server_url": "https://example.invalid"}
        window.refresh()
        self.assertFalse(window.online)
        self.assertFalse(window.primary.isEnabled())
        self.assertIn("설정 오류", window.server_status.text())

    def test_offline_ui_can_restore_interrupted_removal_before_executing(self):
        window, source, app = self.installed_window()
        exe = self.engine.resolve_launch(app)[0]
        unlink = type(exe).unlink
        def crash(path, *args, **kwargs):
            result = unlink(path, *args, **kwargs)
            if path == exe:
                raise SystemExit("simulated removal interruption")
            return result
        with patch.object(type(exe), "unlink", crash):
            with self.assertRaises(SystemExit):
                self.engine.uninstall("dummy")
        window.render()
        self.assertFalse(window.online)
        self.assertEqual(window.primary.text(), "복구 확인")
        self.assertTrue(window.primary.isEnabled())
        window.primary_action()
        self.wait_task(window)
        self.assertTrue(exe.exists())
        self.assertEqual(self.processes.calls, [])
        self.assertEqual(window.primary.text(), "실행")
        window.primary_action()
        self.assertEqual(len(self.processes.calls), 1)

    def test_malformed_server_catalog_does_not_block_existing_local_app(self):
        window, source, app = self.installed_window()
        from southpaw_tools.catalog import parse_catalog
        malformed = app.to_dict()
        malformed["package_name"] = []
        with self.assertRaises(LauncherError):
            parse_catalog({"schema_version": 1, "apps": [malformed]})
        with patch("southpaw_tools.ui.HttpProvider.health", return_value={"lan_enabled": False}), \
             patch("southpaw_tools.ui.HttpProvider.catalog", side_effect=LauncherError("malformed response")):
            window.refresh()
            self.wait_task(window)
        window.primary_action()
        self.assertEqual(len(self.processes.calls), 1)


if __name__ == "__main__":
    unittest.main()
