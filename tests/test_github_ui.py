from __future__ import annotations

import json
import time
import unittest
import urllib.error
from dataclasses import replace
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from southpaw_tools.common import LauncherError, digest
from southpaw_tools.github_channels import CANONICAL_CATALOG_ID, CANONICAL_REPOSITORY, CANONICAL_REPOSITORY_ID, latest_api_url
from southpaw_tools.paths import AppPaths
from southpaw_tools.ui import MainWindow, GITHUB_AUTO_REFRESH_MS
from tests import test_ui as ui_helpers
from tests import test_github_provider as github_helpers
from tests.support import package


class GitHubUiTests(unittest.TestCase):
    wait_task = ui_helpers.UiTests.wait_task
    close_windows = ui_helpers.UiTests.close_windows

    def setUp(self):
        self.fixture = github_helpers.GitHubProviderTests()
        self.fixture.setUp()
        self.tmp = self.fixture.tmp  # Allow the failure-only runner to preserve test evidence.
        self.addCleanup(self.fixture.doCleanups)
        self.windows = []
        self.addCleanup(self.close_windows)
        self.policy = self.fixture.root/'test-public-policy.json'
        self.policy.write_text(json.dumps(self.fixture.signer.policy),encoding='utf-8')
        self.sync_routes()
        opener = patch('southpaw_tools.github_provider.urllib.request.build_opener',return_value=self.fixture.transport)
        opener.start(); self.addCleanup(opener.stop)

    def sync_routes(self):
        old='example/creative-group-releases'; new='toast-source/creative-group-releases'
        routes={key.replace(old,new):(value.replace(old.encode(),new.encode()) if isinstance(value,bytes) else value)
                for key,value in self.fixture.transport.routes.items() if old in key}
        routes[latest_api_url(new)] = routes.pop(self.fixture.provider.api_url.replace(old,new))
        self.fixture.transport.routes.update(routes)

    def window(self, *, keys=True, auto_connect=False):
        window=MainWindow(self.fixture.engine.paths,installer=self.fixture.engine,
            auto_connect=auto_connect,github_repository='toast-source/creative-group-releases',
            github_test_policy=self.policy if keys else None)
        self.windows.append(window); window.show(); QTest.qWait(10)
        return window

    def refresh(self, window):
        window.refresh(); self.wait_task(window)

    def api_count(self):
        return sum(r.full_url.startswith('https://api.github.com') for r in self.fixture.transport.calls)

    def click_install(self, window):
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):
            QTest.mouseClick(window.primary,Qt.MouseButton.LeftButton)
            self.wait_task(window)

    def publish_r2(self):
        source,app=package(self.fixture.root/'inputs','r2',version='1.1.0')
        release=self.fixture.publish(app,source,2);self.sync_routes()
        return source,app,release

    def test_gui_buttons_install_update_latest_and_preserve_settings(self):
        window=self.window(); self.refresh(window)
        self.assertTrue(window.online)
        self.assertEqual(window.info['설치 상태'].text(),'설치 필요')
        self.assertEqual(self.api_count(),1)
        self.click_install(window)
        self.assertEqual(self.api_count(),2)  # One additional fresh API check for install.
        self.assertEqual(window.info['설치 상태'].text(),'최신 버전')
        self.assertEqual(window.primary.text(),'시험 실행 차단')
        _,payload=self.fixture.engine.resolve_launch(self.fixture.app)
        (payload/'settings.json').write_text('synthetic GUI settings')
        self.publish_r2()
        window._github_next_check=0; self.refresh(window)
        self.assertEqual(window.info['설치 상태'].text(),'업데이트 가능')
        self.assertEqual(window.primary.text(),'업데이트')
        self.assertEqual(window.info['설치 버전'].text(),'1.0.0')
        self.click_install(window)
        self.assertEqual(self.api_count(),4)
        installed=self.fixture.engine.installed('dummy')
        self.assertEqual(installed.release_id,'r2')
        self.assertEqual(window.info['설치 상태'].text(),'최신 버전')
        self.assertEqual((self.fixture.engine.resolve_launch(installed)[1]/'settings.json').read_text(),'synthetic GUI settings')
        self.assertEqual(self.fixture.engine.processes.calls,[])

    def test_startup_uses_single_catalog_request_and_hourly_timer(self):
        window=self.window(auto_connect=True)
        QTest.qWait(240);self.wait_task(window)
        self.assertEqual(self.api_count(),1)
        self.assertEqual(window.update_timer.interval(),GITHUB_AUTO_REFRESH_MS)
        window.update_timer.timeout.emit();self.assertEqual(self.api_count(),1)
        window.close()
        self.assertFalse(window.update_timer.isActive())

    def test_manual_refresh_fetches_again_and_only_blocks_while_busy(self):
        window=self.window();self.refresh(window)
        self.assertTrue(window.refresh_button.isEnabled())
        QTest.mouseClick(window.refresh_button, Qt.MouseButton.LeftButton)
        self.assertFalse(window.refresh_button.isEnabled())
        window.refresh()
        self.wait_task(window)
        self.assertEqual(self.api_count(),2)
        self.assertTrue(window.refresh_button.isEnabled())

    def test_manual_refresh_is_restored_after_catalog_body_timeout(self):
        window=self.window()
        endpoint=latest_api_url('toast-source/creative-group-releases')
        reply=self.fixture.transport.routes[endpoint]
        self.fixture.transport.routes[endpoint]=TimeoutError()
        self.refresh(window)
        self.assertFalse(window.online)
        self.assertTrue(window.refresh_button.isEnabled())
        self.fixture.transport.routes[endpoint]=reply
        self.refresh(window)
        self.assertTrue(window.online)
        self.assertTrue(window.refresh_button.isEnabled())

    def test_network_failure_keeps_local_launch_enabled(self):
        window=self.window();self.refresh(window);self.click_install(window)
        self.assertIsNotNone(self.fixture.engine.installed('dummy'),window.message.text())
        self.fixture.transport.routes[window.provider.api_url]=urllib.error.URLError('offline')
        window._github_next_check=0;self.refresh(window)
        self.assertFalse(window.online)
        self.assertIn('인터넷 연결 실패',window.server_status.text())
        self.assertEqual(window.primary.text(),'시험 실행 차단');self.assertFalse(window.primary.isEnabled())
        window.primary_action()
        self.assertEqual(len(self.fixture.engine.processes.calls),0)
        normal=self.window(keys=False)
        normal.list.setCurrentRow(next(i for i,a in enumerate(normal.apps) if a.app_id=='dummy'))
        self.assertTrue(normal.primary.isEnabled())
        normal.primary_action()  # Normal-mode behavior, FakeProcesses only.
        self.assertEqual(len(self.fixture.engine.processes.calls),1)

    def test_rate_limit_defers_automatic_refresh_but_leaves_manual_retry(self):
        window=self.window()
        for code in (403,429):
            with self.subTest(code=code):
                endpoint=latest_api_url('toast-source/creative-group-releases')
                self.fixture.transport.routes[endpoint]=urllib.error.HTTPError(endpoint,code,'',{'X-RateLimit-Remaining':'0'},None)
                window._github_next_check=0;self.refresh(window)
                self.assertIn('GitHub 호출 제한',window.server_status.text())
                self.assertGreater(window._github_next_check-time.monotonic(),3590)
                before=self.api_count()
                window._automatic_refresh()
                self.assertEqual(self.api_count(),before)
                self.assertTrue(window.refresh_button.isEnabled())
                self.refresh(window)
                self.assertEqual(self.api_count(),before+1)

    def test_toast_bridge_preview_requires_the_pinned_rod_catalog(self):
        window = self.window()
        window.managed_session = SimpleNamespace(
            channel={"repository": "toast-source/creative-group-releases", "policy": self.fixture.signer.policy},
            updater=SimpleNamespace(home=self.fixture.root))
        bridge = replace(self.fixture.app, app_id="creative-group-launcher", release_id="toast-bridge-0.1.6")
        rod = replace(bridge, release_id="rodetoast-launcher-0.1.7", version="0.1.7")
        with patch("southpaw_tools.ui.GitHubReleasesProvider") as provider:
            provider.return_value.catalog.return_value = [rod]
            self.assertEqual(window._rod_target(bridge), "0.1.7")
            args, kwargs = provider.call_args
            self.assertEqual(args, (CANONICAL_REPOSITORY,))
            self.assertEqual(kwargs["repository_id"], CANONICAL_REPOSITORY_ID)
            self.assertEqual(kwargs["verifier"].policy["catalog_id"], CANONICAL_CATALOG_ID)
            self.assertEqual(kwargs["verifier"].policy["minimum_sequence"], 10)
            provider.return_value.catalog.side_effect = LauncherError("서명 검증 실패")
            self.assertIsNone(window._rod_target(bridge))
            provider.reset_mock()
            self.assertIsNone(window._rod_target(replace(bridge, release_id="ordinary-release")))
            provider.assert_not_called()

    def test_signature_failure_preserves_installed_pointer_and_launch(self):
        window=self.window();self.refresh(window);self.click_install(window)
        pointer=self.fixture.engine.paths.app('dummy')/'active.json';before=digest(pointer)
        url=next(key for key in self.fixture.transport.routes if 'toast-source/' in key and key.endswith('/catalog.json'))
        self.fixture.transport.routes[url]=self.fixture.transport.routes[url].replace(b'Harmless',b'HarmlesX')
        window._github_next_check=0;self.refresh(window)
        self.assertIn('서명 검증 실패',window.server_status.text())
        self.assertEqual(digest(pointer),before)
        self.assertEqual(window.primary.text(),'시험 실행 차단');self.assertFalse(window.primary.isEnabled())

    def test_hash_failure_is_install_error_and_keeps_r1(self):
        window=self.window();self.refresh(window);self.click_install(window)
        self.publish_r2();window._github_next_check=0;self.refresh(window)
        url=next(key for key in self.fixture.transport.routes if 'toast-source/' in key and key.endswith('/r2.zip'))
        body=self.fixture.transport.routes[url];self.fixture.transport.routes[url]=b'X'+body[1:]
        self.click_install(window)
        self.assertEqual(self.fixture.engine.installed('dummy').release_id,'r1')
        self.assertIn('패키지 검증 실패',window.server_status.text())
        self.assertNotIn('인터넷 연결 실패',window.server_status.text())
        self.assertFalse(window.primary.isEnabled());self.assertEqual(window.primary.text(),'시험 실행 차단')

    def test_empty_bundled_keys_block_test_release_in_normal_mode(self):
        window=self.window(keys=False);self.refresh(window)
        self.assertFalse(window.online);self.assertFalse(window.primary.isEnabled())
        self.assertIn('운영 키 미채택',window.server_status.text())
        self.assertIsNone(self.fixture.engine.installed('dummy'))

    def test_test_key_policy_cannot_escape_isolated_paths(self):
        with self.assertRaises(LauncherError):
            MainWindow(AppPaths(Path('C:/NotAnIsolatedTrial')),auto_connect=False,
                github_repository='toast-source/creative-group-releases',github_test_policy=self.policy)
        with self.assertRaises(LauncherError):
            MainWindow(self.fixture.engine.paths,auto_connect=False,
                github_repository='another/repository',github_test_policy=self.policy)

    def test_persisted_test_policy_setting_does_not_enroll_a_key(self):
        paths=self.fixture.engine.paths;paths.root.mkdir(parents=True,exist_ok=True)
        (paths.root/'settings.json').write_text(json.dumps({'github_test_policy':str(self.policy)}),encoding='utf-8')
        window=self.window(keys=False);self.refresh(window)
        self.assertFalse(window.github_test_mode);self.assertFalse(window.online)

    def test_changed_release_at_install_boundary_requires_new_confirmation(self):
        window=self.window();self.refresh(window)
        self.publish_r2()
        self.click_install(window)
        self.assertIsNone(self.fixture.engine.installed('dummy'))
        self.assertFalse(window.online)

    def test_install_cancel_does_not_request_or_install(self):
        window=self.window();self.refresh(window);before=self.api_count()
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No):
            window.primary_action()
        self.assertEqual(self.api_count(),before)
        self.assertIsNone(self.fixture.engine.installed('dummy'))
