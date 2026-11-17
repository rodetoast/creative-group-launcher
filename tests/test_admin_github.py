import json
from pathlib import Path
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QMessageBox

from southpaw_tools.admin_gui import AdminWindow
from southpaw_tools.admin_gui_model import AdminSession
from southpaw_tools.admin_github import GhCliTransport,GitHubPublication,REPOSITORY,PREFIX
from southpaw_tools.common import LauncherError,digest
from tests import test_admin_gui as helpers
from tests.admin_github_support import FakeGh


class AdminGitHubTests(unittest.TestCase):
    def setUp(self):
        self.fixture=helpers.AdminGuiTests();self.fixture.setUp()
        self.tmp=self.fixture.tmp;self.addCleanup(self.fixture.doCleanups)
        self.backend=FakeGh();self.transport=GhCliTransport(runner=self.backend)

    def prepared(self):
        return GitHubPublication(self.fixture.session,self.transport).prepare(self.fixture.plan())

    def uploaded(self):
        job=self.prepared();job.create_draft(True);job.upload();return job

    def verified(self):
        job=self.uploaded();job.verify();return job

    def window(self):
        window=AdminWindow(self.fixture.repo,test_mode=True,github_transport=self.transport)
        self.fixture.windows.append(window)
        with patch('southpaw_tools.admin_gui.QFileDialog.getOpenFileName',return_value=(str(self.fixture.source),'ZIP')):
            window.select_zip()
        with patch('southpaw_tools.admin_gui.QFileDialog.getOpenFileName',return_value=(str(self.fixture.key),'PEM')):
            window.select_key()
        self.fixture.fill(window)
        window.github_mode.setChecked(True)
        return window

    def prepare_window(self):
        window=self.window()
        with patch.object(window,'confirm',return_value=True):
            window.request_publish();self.fixture.wait(window)
        self.assertIsNotNone(window.github_job,window.result.toPlainText())
        return window

    def test_bundle_reuses_existing_publisher_and_original_zip_is_read_only(self):
        f=self.fixture;before=helpers.tree(f.repo);original=(digest(f.source),f.source.stat().st_mtime_ns)
        job=self.prepared()
        self.assertEqual({a.name for a in job.assets},{'catalog.json','catalog.sig.json','tilenamer--gui-r1.zip'})
        self.assertEqual(before,helpers.tree(f.repo))
        self.assertEqual(original,(digest(f.source),f.source.stat().st_mtime_ns))
        self.assertEqual(self.transport.calls,[])

    def test_whole_current_bundle_preserves_unchanged_zip_bytes(self):
        f=self.fixture
        inspection=f.session.inspect(f.root/'inputs/admin-dummy-r2.zip','ase-viewer','0.0.2','old-r2','Demo.exe','previous dummy')
        f.session.publish(f.session.review(inspection,'2',f.key,True))
        before=helpers.tree(f.repo)
        review=f.session.review(f.inspect(),'3',f.key,True)
        job=GitHubPublication(f.session,self.transport).prepare(review)
        self.assertEqual(len(job.assets),4)
        self.assertEqual(digest(job.directory/'ase-viewer--old-r2.zip'),digest(f.repo/'packages/ase-viewer--old-r2.zip'))
        self.assertEqual(before,helpers.tree(f.repo))

    def test_source_changed_after_preparation_blocks_external_steps(self):
        job=self.prepared();self.fixture.source.write_bytes(b'changed')
        with self.assertRaises(LauncherError):job.create_draft(True)
        self.assertEqual(self.transport.calls,[])

    def test_staged_asset_change_is_detected_before_draft(self):
        job=self.prepared();(job.directory/'catalog.json').write_bytes(b'changed')
        with self.assertRaises(LauncherError):job.create_draft(True)
        self.assertEqual(self.backend.calls,[])

    def test_existing_release_is_never_overwritten(self):
        job=self.prepared()
        self.backend.releases[99]={'id':99,'tag_name':job.tag,'draft':False,'assets':[]}
        with self.assertRaisesRegex(LauncherError,'이미 존재'):job.create_draft(True)
        self.assertFalse(any(method=='POST' for method,_ in self.backend.calls))
        self.assertFalse(self.backend.releases[99]['draft'])

    def test_existing_draft_assets_are_not_overwritten(self):
        job=self.prepared();job.create_draft(True)
        self.backend.releases[job.draft_id]['assets']=[{'name':'existing'}]
        before=len(self.backend.calls)
        with self.assertRaisesRegex(LauncherError,'이미 있습니다'):job.upload()
        self.assertFalse(any(method=='POST' for method,_ in self.backend.calls[before:]))

    def test_draft_creation_failure_checks_exit_code(self):
        job=self.prepared();self.backend.fail=lambda method,url:method=='POST'
        with self.assertRaisesRegex(LauncherError,'종료 코드 7'):job.create_draft(True)
        self.assertEqual(job.phase,'failed');self.assertEqual(self.backend.releases,{})
        self.assertTrue((job.work/'publication-state.json').exists())

    def test_partial_upload_failure_preserves_draft_without_publication(self):
        job=self.prepared();job.create_draft(True)
        self.backend.fail=lambda method,url:method=='POST' and '.zip' in url
        with self.assertRaises(LauncherError):job.upload()
        self.assertTrue(self.backend.releases[job.draft_id]['draft'])
        self.assertEqual(len(self.backend.releases[job.draft_id]['assets']),2)
        self.assertEqual(job.phase,'failed');self.assertTrue(job.work.exists())
        with self.assertRaises(LauncherError):job.publish(True)

    def test_redownload_hash_failure_blocks_publication(self):
        job=self.uploaded();self.backend.corrupt_download=True
        with self.assertRaisesRegex(LauncherError,'재다운로드'):job.verify()
        with self.assertRaises(LauncherError):job.publish(True)
        self.assertFalse(any(method=='PATCH' for method,_ in self.backend.calls))

    def test_changed_remote_asset_after_verification_blocks_publication(self):
        job=self.verified();self.backend.releases[job.draft_id]['assets'][0]['id']+=10000
        with self.assertRaisesRegex(LauncherError,'ID 변경'):job.publish(True)
        self.assertTrue(self.backend.releases[job.draft_id]['draft'])

    def test_publication_requires_separate_confirmation(self):
        job=self.verified();before=len(self.backend.calls)
        with self.assertRaises(LauncherError):job.publish(False)
        self.assertEqual(len(self.backend.calls),before)
        job.publish(True);self.assertEqual(job.phase,'published')

    def test_production_and_actual_cli_writes_remain_locked(self):
        f=self.fixture;production=AdminSession(f.repo)
        with self.assertRaises(LauncherError):GitHubPublication(production,self.transport).prepare(f.plan())
        real=GhCliTransport('gh.exe')
        with patch('subprocess.run') as process:
            with self.assertRaises(LauncherError):real.request('POST',PREFIX+'/releases',payload={})
            with self.assertRaises(LauncherError):GitHubPublication(f.session,real).prepare(f.plan())
            process.assert_not_called()
        with self.assertRaises(LauncherError):self.transport.request('GET','repos/other/repository/releases')

    def test_latest_failure_after_publication_is_uncertain_not_success(self):
        job=self.verified()
        self.backend.fail=lambda method,url:url.endswith('/releases/latest')
        with self.assertRaisesRegex(LauncherError,'반영됐을 수'):
            job.publish(True)
        self.assertEqual(job.phase,'failed');self.assertTrue(job.publication_uncertain)
        self.assertFalse(self.backend.releases[job.draft_id]['draft'])
        self.assertEqual(sum(method=='PATCH' for method,_ in self.backend.calls),1)

    def test_cancel_review_and_draft_have_no_external_changes(self):
        window=self.window();before=helpers.tree(self.fixture.repo)
        with patch.object(window,'confirm',return_value=False):
            window.request_publish();self.fixture.wait(window)
        self.assertEqual(self.backend.calls,[]);self.assertEqual(before,helpers.tree(self.fixture.repo))
        window=self.prepare_window()
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No):
            window.request_github_draft()
        self.assertEqual(self.backend.calls,[])

    def test_gui_complete_dry_run_flow_shows_assets_and_checks_responses(self):
        before=helpers.tree(self.fixture.repo);window=self.prepare_window()
        self.assertIn(REPOSITORY,window.github_assets.toPlainText())
        self.assertIn('catalog.sig.json',window.github_assets.toPlainText())
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):
            window.request_github_draft();self.fixture.wait(window)
            window.github_upload.click();self.fixture.wait(window)
            self.assertFalse(window.github_public.isEnabled())
            window.github_verify.click();self.fixture.wait(window)
            self.assertTrue(window.github_public.isEnabled())
            window.request_github_public();self.fixture.wait(window)
        self.assertEqual(window.github_job.phase,'published')
        self.assertIn('실제 GitHub 미변경',window.result.toPlainText())
        self.assertEqual(before,helpers.tree(self.fixture.repo))
        self.assertTrue(all(c['exit_code']==0 and c['http_status'] in (200,201) for c in self.transport.calls))
        log=(window.github_job.work/'publication-state.json').read_text(encoding='utf-8')
        self.assertNotIn('PRIVATE KEY',log);self.assertNotIn(str(self.fixture.key),log)

    def test_gui_public_cancel_keeps_verified_draft(self):
        window=self.prepare_window();job=window.github_job
        job.create_draft(True);job.upload();job.verify();window._github_buttons()
        before=len(self.backend.calls)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No):
            window.request_github_public()
        self.assertEqual(len(self.backend.calls),before);self.assertEqual(job.phase,'verified')

    def test_gui_changed_sequence_invalidates_prepared_bundle(self):
        window=self.prepare_window();window.sequence.setText('3')
        self.assertIsNone(window.github_job);self.assertFalse(window.github_draft.isEnabled())


if __name__=='__main__':unittest.main()
