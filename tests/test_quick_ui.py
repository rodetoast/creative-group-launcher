"""Exercise the actual Quick controls against the existing Python workflow."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, QPointF, QTimer, Qt
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from southpaw_tools.catalog import catalog_document
from southpaw_tools.common import LauncherError, atomic_json
from southpaw_tools.quick_ui import QuickLauncherWindow
from tests import test_managed_update_gui, test_ui
from tests.support import LocalProvider, package


class QuickUiTests(unittest.TestCase):
    setUp = test_ui.UiTests.setUp
    close_windows = test_ui.UiTests.close_windows
    wait_task = test_ui.UiTests.wait_task

    def window(self, **options):
        window = QuickLauncherWindow(self.paths, auto_connect=False, installer=self.engine, **options)
        self.windows.append(window)
        window.show()
        QTest.qWait(50)
        self.assertTrue(window._first_frame)
        return window

    def click(self, window, name):
        root = window.quick.rootObject()
        item = root.findChild(QQuickItem, name)
        if item is None:
            # Repeater delegates are visual children of the grid.
            items = [root]
            while items:
                candidate = items.pop(0)
                if candidate.objectName() == name:
                    item = candidate
                    break
                items.extend(candidate.childItems())
        self.assertIsNotNone(item, name)
        self.assertTrue(item.isVisible() and item.isEnabled(), name)
        point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
        self.assertTrue(window.quick.rect().contains(point), name)
        QTest.mouseClick(window.quick, Qt.MouseButton.LeftButton, pos=point)
        test_ui.APPLICATION.processEvents()

    def test_five_apps_theme_persistence_and_minimum_layout(self):
        window = self.window()
        self.assertEqual(len(window.surface.rows), 5)
        window.surface.select(2)
        self.assertEqual(window.surface.view["title"]["text"], "AsepriteTagMaster")
        window.resize(800, 570)
        self.assertEqual(window.quick.rootObject().findChild(QQuickItem, "toolGrid").property("columns"), 2)
        self.click(window, "settingsAction")
        self.click(window, "themeSwitch")
        self.assertFalse(window.surface.dark)
        self.assertFalse(self.window().surface.dark)

    def test_workspace_card_addresses_app_by_id_and_opens_detail(self):
        window = self.window()
        row = window.surface.rows[1]
        with patch.object(window, "primary_action"), patch.object(window, "render") as render:
            render.side_effect = lambda: window.primary.setEnabled(True)
            window.surface.actOnApp(row["id"], "primary")
            window.primary_action.assert_called_once_with()
            self.assertEqual(window.selected().app_id, row["id"])
        self.click(window, "detailsAction")
        QTest.qWait(180)
        self.assertEqual(window.surface.view["title"]["text"], window.surface.rows[0]["title"])
        self.click(window, "notesDisclosure")
        self.assertTrue(window.surface.view["noteBlocks"])
        drawer = window.quick.rootObject().findChild(QObject, "toolDetail")
        self.assertTrue(drawer.property("visible"))
        QTest.keyClick(window.quick, Qt.Key.Key_Escape)
        QTest.qWait(180)
        self.assertFalse(drawer.property("visible"))

    def test_detail_docks_on_wide_window_and_restores_card_focus(self):
        window = self.window()
        window.resize(1510, 840)
        QTest.qWait(100)
        scene = window.quick.rootObject()
        grid = scene.findChild(QQuickItem, "toolGrid")
        dock = scene.findChild(QQuickItem, "dockedDetail")
        self.assertEqual(grid.property("columns"), 3)
        self.click(window, "detailsAction")
        QTest.qWait(180)
        self.assertTrue(dock.isVisible())
        self.assertEqual(grid.property("columns"), 3)
        self.click(window, "notesDisclosure")
        self.assertTrue(window.surface.view["noteGroups"])
        window.resize(620, 540)
        QTest.qWait(180)
        drawer = scene.findChild(QObject, "toolDetail")
        self.assertTrue(drawer.property("visible"))
        self.assertFalse(dock.isVisible())
        self.assertEqual(grid.property("columns"), 1)
        QTest.keyClick(window.quick, Qt.Key.Key_Escape)
        QTest.qWait(180)
        self.assertFalse(drawer.property("visible"))
        self.assertEqual(window.quick.quickWindow().activeFocusItem().objectName(), "detailsAction")

    def test_install_update_and_offline_launch_using_primary_control(self):
        source, app = package(self.root / "packages")
        catalog = self.root / "catalog.json"
        atomic_json(catalog, catalog_document([app]))
        window = self.window(catalog_path=catalog)
        window.provider, window.online = LocalProvider(source), True
        window.render()
        test_ui.APPLICATION.processEvents()
        # Confirm after QML has opened its real modal dialog.
        QTimer.singleShot(100, lambda: self.click(window, "confirmAction"))
        self.click(window, "primaryAction")
        self.wait_task(window)
        self.assertEqual(self.engine.installed("dummy"), app)
        source, upgraded = package(self.root / "packages", "r2", version="1.1")
        window.apps = [upgraded]
        window.provider = LocalProvider(source)
        window._populate("dummy")
        test_ui.APPLICATION.processEvents()
        QTimer.singleShot(100, lambda: self.click(window, "confirmAction"))
        self.click(window, "primaryAction")
        self.wait_task(window)
        self.assertEqual(self.engine.installed("dummy"), upgraded)
        window.online = False
        window.render()
        test_ui.APPLICATION.processEvents()
        self.click(window, "primaryAction")
        self.assertEqual(len(self.processes.calls), 1)
        self.processes.running = False
        window.render()
        test_ui.APPLICATION.processEvents()
        self.click(window, "detailsAction")
        QTest.qWait(180)
        self.click(window, "managementAction")
        QTimer.singleShot(100, lambda: self.click(window, "confirmAction"))
        self.click(window, "removeAction")
        self.wait_task(window)
        self.assertIsNone(self.engine.installed("dummy"))

    def test_refresh_button_recovers_after_failure_and_queries_again(self):
        window = self.window()
        status = window.quick.rootObject().findChild(QQuickItem, "connectionState")
        self.assertEqual(status.property("text"), "업데이트 확인 전")
        window.config = {"transport": "lan", "server_url": "http://127.0.0.1:8080"}
        failure = LauncherError("controlled offline failure")
        with patch("southpaw_tools.ui.HttpProvider.health", side_effect=failure) as request:
            for _ in range(2):
                self.click(window, "refreshAction")
                self.wait_task(window)
                test_ui.APPLICATION.processEvents()
                self.assertTrue(window.surface.view["refresh_button"]["enabled"])
                self.assertIn(str(failure), window.surface.view["message"]["text"])
                self.assertEqual(status.property("text"), "업데이트 확인 실패")
        self.assertEqual(request.call_count, 2)

    def test_launcher_approval_reaches_existing_bootstrap_handoff(self):
        managed = test_managed_update_gui.ManagedUpdateGuiTests()
        self.addCleanup(managed.doCleanups)
        with patch.object(test_managed_update_gui, "MainWindow", QuickLauncherWindow):
            managed.setUp()
        window = managed.window
        window.show()
        QTest.qWait(50)
        with (
            patch("southpaw_tools.github_provider.urllib.request.build_opener",
                  return_value=managed.transport),
            patch.object(test_ui.QApplication, "exit") as exit_app,
            managed.updater._runtime_lock(),
        ):
            QTimer.singleShot(100, lambda: self.click(window, "confirmAction"))
            self.click(window, "updateLauncherAction")
            self.wait_task(window)
            test_ui.APPLICATION.processEvents()
            exit_app.assert_called_once_with(20)
        self.assertTrue((managed.session.file.parent / "request.json").exists())
        managed.assert_preserved()
