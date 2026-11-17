import json
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QMessageBox
from southpaw_tools.admin_github import DraftTransferGrant,GhCliTransport,GitHubPublication,PREFIX
from southpaw_tools.admin_gui import AdminWindow
from southpaw_tools.admin_gui_model import AdminSession,APP_NAMES,TEST_MARKER
from southpaw_tools.common import LauncherError,atomic_json,digest
from tests.support import temporary,package,TestSigner
from tests.admin_github_support import FakeGh
from tests import test_admin_gui as helpers


class AdminLiveDraftBoundaryTests(unittest.TestCase):
    wait=helpers.AdminGuiTests.wait

    def setUp(self):
        self.tmp=temporary('admin-live-boundary-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.repo=self.root/'repository'
        (self.repo/'packages').mkdir(parents=True)
        self.signer=TestSigner(self.root)
        old,self.app=package(self.root/'inputs','trial-r2',version='0.0.2')
        self.source,self.new=package(self.root/'inputs','trial-r3',version='0.0.3')
        shutil.copyfile(old,self.repo/'packages'/self.app.package_name)
        self.signer.publish(self.repo,[self.app],2)
        atomic_json(self.root/'TEST_ONLY_TRUST.json',self.signer.policy)
        atomic_json(self.root/'admin-gui-test.json',{'purpose':TEST_MARKER,'app_profile':'github-dummy-v1',
            'dummy_package_sha256':[self.app.sha256,self.new.sha256]})
        self.session=AdminSession(self.repo,test_mode=True)
        self.grant=DraftTransferGrant(self.repo,'catalog-000003',3,next(iter(self.signer.policy['keys'])),
                                      self.new.sha256,'trial-r3')
        self.transport=GhCliTransport('existing-gh.exe',draft_grant=self.grant)
        self.backend=FakeGh()
        def call(args,**kwargs):return self.backend(args,kwargs.get('input'))
        process=patch('southpaw_tools.admin_github.subprocess.run',side_effect=call)
        self.process=process.start();self.addCleanup(process.stop)

    def job(self):
        inspection=self.session.inspect(self.source,'dummy','0.0.3','trial-r3','Dummy.exe','test notes')
        review=self.session.review(inspection,'3',self.signer.path,True)
        return GitHubPublication(self.session,self.transport).prepare(review)

    def test_dummy_profile_is_isolated_and_company_names_unchanged(self):
        self.assertEqual(self.session.app_names,{'dummy':'Dummy Tool'})
        self.assertEqual(len(APP_NAMES),5);self.assertNotIn('dummy',APP_NAMES)
        with self.assertRaises(LauncherError):AdminSession(self.repo).state()

    def test_grant_rejects_external_paths_and_mismatched_sequence(self):
        for root,tag in [(Path('C:/outside/repository'),'catalog-000003'),(self.repo,'catalog-000004')]:
            with self.assertRaises(LauncherError):
                DraftTransferGrant(root,tag,3,self.grant.key_id,self.new.sha256,'trial-r3')

    def test_real_boundary_executes_draft_upload_verify_but_never_publish(self):
        job=self.job();job.create_draft(True);job.upload();job.verify()
        self.assertFalse(self.transport.dry_run);self.assertEqual(job.phase,'verified')
        self.assertTrue(self.backend.releases[job.draft_id]['draft'])
        with self.assertRaises(LauncherError):job.publish(True)
        with self.assertRaises(LauncherError):self.transport.request('PATCH',PREFIX+'/releases/1',payload={'draft':False})
        self.assertFalse(any(method=='PATCH' for method,_ in self.backend.calls))

    def test_unapproved_tag_publication_and_latest_are_blocked_before_cli(self):
        self.job()
        for values in [{'tag_name':'other','draft':True,'prerelease':False,'make_latest':'false'},
                       {'tag_name':self.grant.tag,'draft':False,'prerelease':False,'make_latest':'false'},
                       {'tag_name':self.grant.tag,'draft':True,'prerelease':False,'make_latest':'true'}]:
            with self.assertRaises(LauncherError):self.transport.request('POST',PREFIX+'/releases',payload=values)
        self.process.assert_not_called()

    def test_existing_release_or_unapproved_asset_upload_is_blocked(self):
        job=self.job();job.create_draft(True);before=self.process.call_count
        with self.assertRaises(LauncherError):
            self.transport.request('POST','https://uploads.github.com/'+PREFIX+'/releases/435981675/assets?name=catalog.json',source=job.directory/'catalog.json')
        self.assertEqual(self.process.call_count,before)

    def test_changed_asset_is_blocked_at_transport_boundary(self):
        job=self.job();job.create_draft(True)
        (job.directory/'catalog.json').write_bytes(b'changed')
        before=self.process.call_count
        with self.assertRaises(LauncherError):
            self.transport.request('POST','https://uploads.github.com/'+PREFIX+f'/releases/{job.draft_id}/assets?name=catalog.json',source=job.directory/'catalog.json')
        self.assertEqual(self.process.call_count,before)

    def test_create_and_upload_cannot_be_retried_or_overwritten(self):
        job=self.job();job.create_draft(True);job.upload()
        before=self.process.call_count
        with self.assertRaises(LauncherError):
            self.transport.request('POST',PREFIX+'/releases',payload={'tag_name':job.tag,'draft':True,'prerelease':False,'make_latest':'false'})
        with self.assertRaises(LauncherError):
            self.transport.request('POST','https://uploads.github.com/'+PREFIX+f'/releases/{job.draft_id}/assets?name=catalog.json',source=job.directory/'catalog.json')
        self.assertEqual(self.process.call_count,before)

    def test_ungranted_real_transport_and_wrong_key_are_blocked(self):
        inspection=self.session.inspect(self.source,'dummy','0.0.3','trial-r3','Dummy.exe','notes')
        review=self.session.review(inspection,'3',self.signer.path,True)
        with self.assertRaises(LauncherError):GitHubPublication(self.session,GhCliTransport()).prepare(review)
        wrong=DraftTransferGrant(self.repo,self.grant.tag,3,'0'*64,self.new.sha256,'trial-r3')
        with self.assertRaises(LauncherError):GitHubPublication(self.session,GhCliTransport(draft_grant=wrong)).prepare(review)
        self.process.assert_not_called()

    def test_cli_timeout_records_uncertain_remote_state_without_retry(self):
        job=self.job()
        original=self.process.side_effect
        def timeout(args,**kwargs):
            if '--method' in args and args[args.index('--method')+1]=='POST':
                raise subprocess.TimeoutExpired('gh',60)
            return original(args,**kwargs)
        self.process.side_effect=timeout
        with self.assertRaisesRegex(LauncherError,'원격 상태'):job.create_draft(True)
        self.assertEqual(job.phase,'failed')
        self.assertEqual(self.transport.calls[-1]['error_type'],'TimeoutExpired')
        self.assertEqual(sum(c['method']=='POST' for c in self.transport.calls),1)

    def test_gui_real_draft_flow_labels_results_and_keeps_public_button_locked(self):
        window=AdminWindow(self.repo,test_mode=True,github_transport=self.transport)
        self.addCleanup(window.close)
        self.assertEqual(window.apps.count(),1);self.assertEqual(window.apps.itemText(0),'Dummy Tool')
        window.version.setText('0.0.3');window.release_id.setText('trial-r3');window.executable.setText('Dummy.exe')
        window.zip_path=self.source;window.key_path=self.signer.path;window.approved.setChecked(True)
        window.inspect_selected();self.wait(window);window.github_mode.setChecked(True)
        with patch.object(window,'confirm',return_value=True):window.request_publish();self.wait(window)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):
            window.request_github_draft();self.wait(window)
            window.github_upload.click();self.wait(window)
            window.github_verify.click();self.wait(window)
        self.assertEqual(window.github_job.phase,'verified',window.result.toPlainText())
        self.assertIn('실제 Draft',window.result.toPlainText())
        self.assertFalse(window.github_public.isEnabled())
        window.request_github_public()
        self.assertIn('차단',window.result.toPlainText())
        self.assertTrue(self.backend.releases[window.github_job.draft_id]['draft'])
