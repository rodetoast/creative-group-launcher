import json
from unittest.mock import patch
import unittest

from PySide6.QtWidgets import QLabel,QLineEdit
from southpaw_tools.ui import ConnectionDialog,connection_defaults,DATA
from southpaw_tools.common import atomic_json,LauncherError
from tests import test_ui as helpers
from tests.support import package,LocalProvider


class EmployeeSettingsTests(unittest.TestCase):
    setUp=helpers.UiTests.setUp
    close_windows=helpers.UiTests.close_windows
    window=helpers.UiTests.window
    wait_task=helpers.UiTests.wait_task

    def test_new_profile_defaults_to_unconfigured_github_without_network_or_disk_write(self):
        window=self.window()
        self.assertEqual(window.config,{'transport':'github','github_repository':''})
        with patch('southpaw_tools.ui.HttpProvider') as lan,patch('southpaw_tools.ui.GitHubReleasesProvider') as github:
            window.refresh()
        lan.assert_not_called();github.assert_not_called()
        self.assertIn('배포 설정 대기',window.server_status.text())
        self.assertIn('운영 저장소 미지정',window.server_status.toolTip())
        self.assertFalse(window.primary.isEnabled())
        self.assertFalse((self.paths.root/'settings.json').exists())
        self.assertEqual(window.catalog_verifier.policy['keys'],{})

    def test_existing_explicit_and_inferred_lan_settings_are_not_rewritten(self):
        for config in [{'transport':'lan','server_url':'http://127.0.0.1:8765','lan_token':'test-only'},
                       {'server_url':'http://127.0.0.1:8765','lan_enabled':False},
                       {'transport':'github','github_repository':'owner/approved-releases'}]:
            with self.subTest(config=config):
                target=self.paths.root/'settings.json';atomic_json(target,config);before=target.read_bytes()
                window=self.window()
                self.assertEqual(window.config,connection_defaults(config))
                self.assertEqual(target.read_bytes(),before)

    def test_bundled_production_key_enables_repo_default_without_replacing_saved_repo(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from southpaw_tools.catalog_trust import CATALOG_ID, CatalogVerifier, b64, key_id

        public = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        verifier = CatalogVerifier(
            {"schema_version": 1, "catalog_id": CATALOG_ID, "minimum_sequence": 4,
             "keys": {key_id(public): b64(public)}}, self.paths.root / "catalog-trust.json")
        with patch.object(CatalogVerifier, "bundled", return_value=verifier):
            window = self.window()
            self.assertEqual(window.config["github_repository"], "toast-source/creative-group-releases")
            target = self.paths.root / "settings.json"
            config = {"transport": "github", "github_repository": "owner/existing"}
            atomic_json(target, config)
            self.assertEqual(self.window().config, config)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), config)

    def test_general_dialog_hides_lan_and_preserves_original_until_explicit_save(self):
        original={'transport':'lan','server_url':'http://127.0.0.1:8765','lan_token':'test-only','extra':28}
        dialog=ConnectionDialog(original);self.addCleanup(dialog.close)
        dialog.show();helpers.APPLICATION.processEvents()
        self.assertEqual(dialog.transport.currentData(),'github')
        self.assertFalse(hasattr(dialog,'url'));self.assertFalse(hasattr(dialog,'token'))
        self.assertEqual(len(dialog.findChildren(QLineEdit)),1)
        dialog.repository.setText('owner/approved-releases')
        self.assertEqual(dialog.values(),{**original,'transport':'github','github_repository':'owner/approved-releases'})
        dialog.reject();self.assertEqual(original['transport'],'lan')

    def test_legacy_dialog_is_explicit_and_keeps_old_provider_validation(self):
        dialog=ConnectionDialog({'server_url':'http://127.0.0.1:8765'},legacy=True)
        self.addCleanup(dialog.close)
        self.assertEqual(dialog.transport.currentData(),'lan')
        self.assertEqual(dialog.values()['server_url'],'http://127.0.0.1:8765')
        self.assertTrue(hasattr(dialog,'token'))

    def test_missing_repo_cannot_be_saved_or_replace_old_settings(self):
        dialog=ConnectionDialog({'transport':'lan','lan_token':'test-only'})
        self.addCleanup(dialog.close)
        with self.assertRaisesRegex(LauncherError,'운영 배포 저장소'):
            dialog.values()

    def test_error_categories_are_distinct_and_keep_local_launch(self):
        source,app=package(self.root/'inputs')
        self.engine.install(app,LocalProvider(source))
        pointer=self.paths.app('dummy')/'active.json';before=pointer.read_bytes()
        window=self.window()
        window.list.setCurrentRow(next(i for i,a in enumerate(window.apps) if a.app_id=='dummy'))
        window.config={'transport':'github','github_repository':'owner/repo'}
        cases=[('GitHub HTTP 404','저장소 또는 Release를 찾을 수 없음'),
               ('GitHub API 호출 제한(HTTP 403)','GitHub 호출 제한'),
               ('GitHub HTTP 429','GitHub 호출 제한'),('GitHub HTTP 403','GitHub 접근 거부'),
               ('GitHub 네트워크 또는 HTTPS 연결 실패','인터넷 연결 실패'),
               ('카탈로그 전자서명 불일치','서명 검증 실패'),
               ('알 수 없는 카탈로그 서명 키 — 운영 신뢰키 승인이 필요합니다.','운영 키 미채택')]
        for error,state in cases:
            with self.subTest(error=error):
                window._github_failure(error);window.render()
                self.assertEqual(window.server_state,state)
                self.assertTrue(window.primary.isEnabled())
                self.assertEqual(window.primary.text(),'실행')
                self.assertEqual(pointer.read_bytes(),before)
                if '404' in error or '서명' in error:
                    self.assertNotIn('인터넷',window.server_state)

    def test_tag_master_metadata_limits_and_notes_remain_explicit(self):
        app=next(a for a in json.loads(DATA.read_text(encoding='utf-8'))['apps'] if a['app_id']=='tag-master')
        self.assertEqual(app['display_name'],'AsepriteTagMaster')
        self.assertEqual(app['release_id'],'0.4.0-team-7263f8d')
        self.assertFalse(app['published']);self.assertEqual(app['package_name'],'')
        self.assertIn('승인',app['release_notes']);self.assertNotIn('개발자 PC',app['release_notes'])

    def test_invalid_settings_object_is_reported_without_overwriting(self):
        target=self.paths.root/'settings.json';atomic_json(target,['not','a','settings','object'])
        before=target.read_bytes();window=self.window()
        self.assertEqual(window.config['transport'],'github');self.assertEqual(target.read_bytes(),before)
        self.assertIn('settings.json',window._load_warning)
