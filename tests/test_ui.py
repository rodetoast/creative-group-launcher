from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QEventLoop, QTimer, Qt
from PySide6.QtGui import QFontDatabase, QRawFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from southpaw_tools.catalog import catalog_document
from southpaw_tools.common import LauncherError, atomic_json
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from southpaw_tools.ui import MainWindow
from tests.support import FakeProcesses, LocalProvider, package, temporary

APPLICATION = QApplication.instance() or QApplication([])


class UiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary("southpaw-ui-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = AppPaths(self.root / "client")
        self.processes = FakeProcesses()
        self.engine = Installer(self.paths, self.processes)
        self.windows = []
        self.addCleanup(self.close_windows)

    def close_windows(self):
        for window in self.windows:
            if window.task:
                window.task.cancel.set()
                self.wait_task(window)
            window.close()
            window.deleteLater()
        APPLICATION.processEvents()

    def window(self, catalog=None):
        kwargs = {"catalog_path": catalog} if catalog else {}
        window = MainWindow(self.paths, auto_connect=False, installer=self.engine, **kwargs)
        self.windows.append(window)
        window.show()
        QTest.qWait(30)
        return window

    def wait_task(self, window):
        if window.task is not None:
            # A real Qt event loop releases Python's GIL to the worker. Repeated
            # QTest.qWait calls can starve a Python QThread under the full suite.
            loop = QEventLoop()
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            window.task.finished.connect(loop.quit)
            timer.start(8000)
            loop.exec()
            timer.stop()
        self.assertIsNone(window.task, "background task did not complete")

    def test_five_apps_missing_package_and_responsive_layout(self):
        window = self.window()
        self.assertEqual(window.list.count(), 5)
        window.list.setCurrentRow(2)
        APPLICATION.processEvents()
        self.assertEqual(window.title.text(), "AsepriteTagMaster")
        self.assertFalse(window.primary.isEnabled())
        self.assertIn("승인 ZIP 미확인", window.message.text())
        for width, height in ((980, 700), (1240, 820), (1600, 1000)):
            window.resize(width, height)
            APPLICATION.processEvents()
            button = window.primary
            position = button.mapTo(window.centralWidget(), button.rect().bottomRight())
            self.assertTrue(window.centralWidget().rect().contains(position))
            self.assertGreaterEqual(button.width(), 160)
        self.assertTrue(QFontDatabase.families())
        self.assertTrue(QRawFont.fromFont(window.title.font()).supportsCharacter(ord("A")))
        self.assertTrue(QRawFont.fromFont(window.title.font()).supportsCharacter(ord("설")))

    def test_minimum_window_keeps_info_text_visible_with_wrapped_github_error(self):
        window = self.window()
        window.config = {'transport':'github','github_repository':'toast-source/creative-group-releases'}
        window.list.setCurrentRow(2)
        window.catalog_error = '알 수 없는 카탈로그 서명 키 — 운영 신뢰키 승인이 필요합니다.'
        window.server_state = '서명 검증 실패'
        window.render()
        window.resize(980,700)
        APPLICATION.processEvents()
        from PySide6.QtWidgets import QLabel
        card = window.info['설치 상태'].parentWidget()
        for label in card.findChildren(QLabel):
            self.assertGreaterEqual(label.height(),label.minimumSizeHint().height(),label.text())
        self.assertTrue(window.centralWidget().rect().contains(
            window.primary.mapTo(window.centralWidget(),window.primary.rect().bottomRight())))

    def test_ui_install_update_running_and_offline_launch_with_dummy(self):
        source, app = package(self.root / "packages")
        catalog = self.root / "catalog.json"
        atomic_json(catalog, catalog_document([app]))
        window = self.window(catalog)
        self.assertFalse(window.primary.isEnabled())  # no server, not installed
        window.provider, window.online = LocalProvider(source), True
        window.render()
        self.assertTrue(window.primary.isEnabled())
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            QTest.mouseClick(window.primary, Qt.MouseButton.LeftButton)
            self.wait_task(window)
        self.assertEqual(self.engine.installed("dummy"), app)
        self.assertEqual(window.primary.text(), "실행")
        source2, app2 = package(self.root / "packages", "r2", version=app.version)
        window.apps = [app2]
        window.provider = LocalProvider(source2)
        window.render()
        self.assertEqual(window.primary.text(), "업데이트")
        self.assertTrue(window.launch_current.isVisible())
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            QTest.mouseClick(window.primary, Qt.MouseButton.LeftButton)
            self.wait_task(window)
        self.assertEqual(self.engine.installed("dummy"), app2)
        window.online = False
        window.provider = None
        window.render()
        QTest.mouseClick(window.primary, Qt.MouseButton.LeftButton)
        self.assertEqual(len(self.processes.calls), 1)
        self.assertEqual(window.primary.text(), "실행 중")
        self.assertFalse(window.remove_button.isEnabled())

    def test_network_failure_keeps_offline_launch_available(self):
        source, app = package(self.root / "packages")
        self.engine.install(app, LocalProvider(source))
        catalog = self.root / "catalog.json"
        atomic_json(catalog, catalog_document([app]))
        window = self.window(catalog)
        window.config = {'transport':'lan'}  # Keep this explicit legacy Provider regression.
        with patch("southpaw_tools.ui.HttpProvider.health", side_effect=LauncherError("offline fixture")):
            window.refresh()
            self.wait_task(window)
        self.assertFalse(window.online)
        self.assertIn("오프라인", window.server_status.text())
        self.assertIn("offline fixture", window.message.text())
        self.assertTrue(window.primary.isEnabled())
        self.assertEqual(window.primary.text(), "실행")

    def test_corrupt_connection_settings_does_not_hide_installed_app(self):
        source, app = package(self.root / "packages")
        self.engine.install(app, LocalProvider(source))
        (self.paths.root / "settings.json").write_text("broken")
        window = self.window()
        self.assertIn("dummy", {item.app_id for item in window.apps})
        window.list.setCurrentRow(next(i for i, a in enumerate(window.apps) if a.app_id == "dummy"))
        self.assertTrue(window.primary.isEnabled())
        self.assertEqual(window.primary.text(), "실행")


if __name__ == "__main__":
    unittest.main()
