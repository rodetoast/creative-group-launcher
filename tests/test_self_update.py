from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from southpaw_tools.common import LauncherError, atomic_json, digest, read_json
from southpaw_tools.self_update import APP_ID, PROJECT, SelfUpdater
from tests.self_update_support import Fixture, package
from tests.support import temporary, LocalProvider


def tree(path):
    return {str(p.relative_to(path)):digest(p) for p in path.rglob('*') if p.is_file()}


class SelfUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=temporary('self-update-')
        self.addCleanup(self.tmp.cleanup)
        self.fixture=Fixture(Path(self.tmp.name)/'fixture')
        self.u=self.fixture.updater
        self.original_data=tree(self.fixture.data)

    def worker(self,action,transaction=None,*extra):
        command=[sys.executable,'-B','-m','southpaw_tools.self_update_worker',action,'--home',str(self.u.home)]
        if transaction:
            command+=['--transaction',transaction]
        return subprocess.run(command+list(extra),cwd=PROJECT,capture_output=True,text=True,encoding='utf-8',timeout=15)

    def request(self):
        transaction=self.fixture.prepare()
        self.u.request_apply(transaction,approved=True)
        return transaction

    def assert_preserved(self):
        self.assertEqual(tree(self.fixture.data),self.original_data)
        self.assertEqual(self.u._validate_release(self.fixture.r1).joinpath('Launcher.exe').read_bytes(),
                         b'MZ dummy launcher launcher-r1')

    def holder(self,target):
        command=[sys.executable,'-B','-m','southpaw_tools.self_update_worker','hold','--home',str(self.u.home),
                 '--hold-target',target]
        process=subprocess.Popen(command,cwd=PROJECT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                 text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def stop():
            if process.poll() is None:
                process.communicate('stop\n',timeout=5)
            else:
                process.communicate(timeout=5)
        self.addCleanup(stop)
        self.assertEqual(process.stdout.readline().strip(),'READY')
        return process

    def test_signed_prepare_detects_new_release_without_changing_current(self):
        transaction=self.fixture.prepare()
        self.assertEqual(self.u.current(),self.fixture.r1)
        self.assertEqual(self.u.journal(transaction)['phase'],'prepared')
        self.assertEqual(self.u._validate_release(self.fixture.r2).name,'payload')
        self.assert_preserved()

    def test_separate_worker_updates_pointer_and_confirms_dummy_start(self):
        transaction=self.request()
        result=self.worker('apply',transaction)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(self.u.current(),self.fixture.r2)
        self.assertEqual(self.u.journal(transaction)['phase'],'committed')
        self.assert_preserved()

    def test_signature_tampering_does_not_create_transaction(self):
        self.fixture.publish(self.fixture.r2_source,self.fixture.r2,2)
        catalog=self.fixture.repo/'catalog.json'
        catalog.write_bytes(catalog.read_bytes()+b' ')
        with self.assertRaises(LauncherError):
            self.u.prepare(self.fixture.provider)
        self.assertFalse((self.u.home/'transactions').exists())
        self.assertEqual(self.u.current(),self.fixture.r1)

    def test_package_hash_mismatch_preserves_old_version(self):
        self.fixture.publish(self.fixture.r2_source,self.fixture.r2,2)
        (self.fixture.repo/'packages'/self.fixture.r2.package_name).write_bytes(b'wrong ZIP')
        with self.assertRaises(LauncherError):
            self.u.prepare(self.fixture.provider)
        self.assertEqual(self.u.current(),self.fixture.r1)
        self.assert_preserved()

    def test_version_downgrade_rejected_even_with_new_signed_sequence(self):
        source,app=package(self.fixture.root/'inputs','older','0.9.0')
        self.fixture.publish(source,app,3)
        with self.assertRaises(LauncherError):
            self.u.prepare(self.fixture.provider)
        self.assertFalse((self.u.home/'transactions').exists())

    def test_same_version_distinct_signed_build_is_allowed(self):
        source,app=package(self.fixture.root/'inputs','same-version-build','1.0.0')
        self.fixture.publish(source,app,2)
        transaction=self.u.prepare(self.fixture.provider)
        self.u.request_apply(transaction,approved=True)
        self.assertEqual(self.worker('apply',transaction).returncode,0)
        self.assertEqual(self.u.current(),app)

    def test_cancel_apply_keeps_old_pointer_and_prepared_files(self):
        transaction=self.fixture.prepare()
        self.assertFalse(self.u.request_apply(transaction,approved=False))
        self.assertEqual(self.u.current(),self.fixture.r1)
        self.assertEqual(self.u.journal(transaction)['phase'],'cancelled')
        self.assertNotEqual(self.worker('apply',transaction).returncode,0)
        self.u._validate_release(self.fixture.r2)
        self.assert_preserved()

    def test_partial_download_rejected_and_retry_is_explicit(self):
        self.fixture.publish(self.fixture.r2_source,self.fixture.r2,2)
        self.fixture.provider.partial=True
        with self.assertRaises(LauncherError):
            self.u.prepare(self.fixture.provider)
        self.assertEqual(self.u.current(),self.fixture.r1)
        self.assertFalse(list(self.u.engine.paths.downloads.glob('*.zip')))
        self.fixture.provider.partial=False
        transaction=self.u.prepare(self.fixture.provider)
        self.assertEqual(self.u.journal(transaction)['phase'],'prepared')

    def test_missing_confirmation_prevents_activation(self):
        transaction=self.fixture.prepare()
        self.assertNotEqual(self.worker('apply',transaction).returncode,0)
        self.assertEqual(self.u.current(),self.fixture.r1)

    def test_running_launcher_lease_blocks_worker_until_normal_exit(self):
        transaction=self.request()
        child=self.holder('runtime')
        self.assertNotEqual(self.worker('apply',transaction).returncode,0)
        self.assertEqual(self.u.current(),self.fixture.r1)
        child.communicate('stop\n',timeout=5)
        result=self.worker('apply',transaction)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assert_preserved()

    @unittest.skipUnless(os.name=='nt','Actual Windows share/delete behavior')
    def test_real_pointer_lock_failure_and_explicit_retry_after_release(self):
        transaction=self.request()
        child=self.holder('pointer')
        result=self.worker('apply',transaction)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.u.current(),self.fixture.r1)
        self.assertIn('WinError=5',self.u.journal(transaction)['error'])
        child.communicate('stop\n',timeout=5)
        second=self.u.prepare(self.fixture.provider)
        self.u.request_apply(second,approved=True)
        self.assertEqual(self.worker('apply',second).returncode,0)
        self.assert_preserved()

    @unittest.skipUnless(os.name=='nt','Actual Windows file handle replacement behavior')
    def test_locked_old_dummy_exe_is_never_replaced_by_updater(self):
        transaction=self.request()
        child=self.holder('exe')
        exe,_=self.u.engine.resolve_launch(self.fixture.r1)
        replacement=self.fixture.root/'replacement-dummy.exe'
        replacement.write_bytes(exe.read_bytes())
        with self.assertRaises(OSError) as error:
            os.replace(replacement,exe)
        self.assertIn(error.exception.winerror,(5,32))
        result=self.worker('apply',transaction)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(self.u.current(),self.fixture.r2)
        child.communicate('stop\n',timeout=5)
        self.assert_preserved()

    def test_real_worker_crash_before_and_after_pointer_recovers_old(self):
        for phase in ('switching','pointed','probing'):
            with self.subTest(phase=phase):
                transaction=self.u.prepare(self.fixture.provider) if phase!='switching' else self.fixture.prepare()
                self.u.request_apply(transaction,approved=True)
                result=self.worker('apply',transaction,'--interrupt-after',phase)
                self.assertEqual(result.returncode,74,result.stdout+result.stderr)
                recovery=self.worker('recover')
                self.assertEqual(recovery.returncode,0,recovery.stdout+recovery.stderr)
                self.assertEqual(self.u.current(),self.fixture.r1)
                self.assertEqual(self.u.journal(transaction)['phase'],'rolled_back')
                self.assert_preserved()

    def test_failed_start_and_bad_ack_roll_back(self):
        for behavior in ('fail','bad-ack','timeout'):
            with self.subTest(behavior=behavior):
                transaction=self.fixture.prepare() if behavior=='fail' else self.u.prepare(self.fixture.provider)
                self.u.request_apply(transaction,approved=True)
                limit='0.3' if behavior=='timeout' else '5'
                result=self.worker('apply',transaction,'--probe-result',behavior,'--timeout',limit)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(self.u.current(),self.fixture.r1)
                self.assertEqual(self.u.journal(transaction)['phase'],'rolled_back')
                self.assert_preserved()

    def test_unlisted_or_user_files_in_payload_rejected(self):
        for label,kwargs in (('unlisted',{'extra':True}),('userdata',{'forbidden':True})):
            with self.subTest(label=label):
                source,app=package(self.fixture.root/'inputs',label,'1.2.0',**kwargs)
                self.fixture.publish(source,app,3 if label=='unlisted' else 4)
                with self.assertRaises(LauncherError):
                    self.u.prepare(self.fixture.provider)
                self.assertEqual(self.u.current(),self.fixture.r1)

    def test_changed_candidate_before_apply_never_changes_current(self):
        transaction=self.request()
        payload=self.u.engine.paths.release(APP_ID,self.fixture.r2.release_id)/'payload'
        (payload/'unexpected.bin').write_bytes(b'not approved')
        self.assertNotEqual(self.worker('apply',transaction).returncode,0)
        self.assertEqual(self.u.current(),self.fixture.r1)

    def test_recovery_failure_preserves_both_versions_and_can_retry(self):
        transaction=self.request()
        self.assertEqual(self.worker('apply',transaction,'--interrupt-after','pointed').returncode,74)
        original=atomic_json
        def fail_pointer(path,value):
            if Path(path)==self.u.home/'current.json':
                raise PermissionError('test pointer restore denied')
            return original(path,value)
        with patch('southpaw_tools.self_update.atomic_json',side_effect=fail_pointer):
            with self.assertRaises(OSError):
                self.u.recover()
        self.u._validate_release(self.fixture.r1)
        self.u._validate_release(self.fixture.r2)
        self.assertEqual(self.u.journal(transaction)['phase'],'rollback_required')
        self.assertEqual(self.worker('recover').returncode,0)
        self.assertEqual(self.u.current(),self.fixture.r1)

    def test_corrupt_journal_is_not_automatically_deleted(self):
        transaction=self.fixture.prepare()
        path=self.u._journal_path(transaction)
        path.write_text('broken')
        self.assertNotEqual(self.worker('recover').returncode,0)
        self.assertEqual(path.read_text(),'broken')
        self.assertEqual(self.u.current(),self.fixture.r1)

    def test_unsigned_provider_and_real_home_are_rejected(self):
        with self.assertRaises(LauncherError):
            self.u.prepare(LocalProvider(self.fixture.r2_source))
        with self.assertRaises(LauncherError):
            SelfUpdater(PROJECT/'distribution')
        with self.assertRaises(LauncherError):
            SelfUpdater.create(self.fixture.data/'overlap',self.fixture.data,self.fixture.signer.policy)

    def test_commit_record_failure_is_conservatively_rolled_back(self):
        transaction=self.request()
        original=atomic_json
        def fail_commit(path,value):
            if Path(path)==self.u._journal_path(transaction) and value.get('phase')=='committed':
                raise PermissionError('commit record denied')
            return original(path,value)
        with patch('southpaw_tools.self_update.atomic_json',side_effect=fail_commit):
            with self.assertRaises(LauncherError):
                self.u.apply(transaction)
        self.assertEqual(self.u.current(),self.fixture.r1)
        self.assert_preserved()

    def test_preparing_journal_recovery_preserves_current(self):
        transaction=self.fixture.prepare()
        journal=self.u.journal(transaction)
        self.u._phase(journal,'preparing')
        self.assertEqual(self.worker('recover').returncode,0)
        self.assertEqual(self.u.journal(transaction)['phase'],'preparation_failed')
        self.assertEqual(self.u.current(),self.fixture.r1)

    def test_bad_saved_signature_proof_prevents_activation(self):
        transaction=self.request()
        journal=self.u.journal(transaction)
        journal['proof']['signature']='not base64'
        atomic_json(self.u._journal_path(transaction),journal)
        self.assertNotEqual(self.worker('apply',transaction).returncode,0)
        self.assertEqual(self.u.current(),self.fixture.r1)

    def test_unknown_pointer_is_preserved_on_recovery(self):
        transaction=self.request()
        self.assertEqual(self.worker('apply',transaction,'--interrupt-after','pointed').returncode,74)
        path=self.u.home/'current.json'
        value=read_json(path)
        value['unexpected']=True
        atomic_json(path,value)
        before=path.read_bytes()
        self.assertNotEqual(self.worker('recover').returncode,0)
        self.assertEqual(before,path.read_bytes())
        self.u._validate_release(self.fixture.r1)
        self.u._validate_release(self.fixture.r2)

    def test_apply_rechecks_version_even_for_signed_journal_candidate(self):
        transaction=self.request()
        source,older=package(self.fixture.root/'inputs','older-journal','0.9.0')
        self.fixture.publish(source,older,3)
        self.fixture.provider.catalog()
        self.u.engine.install(older,self.fixture.provider)
        journal=self.u.journal(transaction)
        journal['new']=older.to_dict()
        journal['proof']=self.u._proof(older)
        atomic_json(self.u._journal_path(transaction),journal)
        self.assertNotEqual(self.worker('apply',transaction).returncode,0)
        self.assertEqual(self.u.current(),self.fixture.r1)


if __name__=='__main__':
    unittest.main()
