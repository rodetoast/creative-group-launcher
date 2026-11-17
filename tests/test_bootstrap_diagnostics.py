"""Failure provenance tests; no product/fixture EXE or existing installation used."""
import ctypes
from contextlib import nullcontext
import json
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from southpaw_tools.bootstrap import Bootstrap, WindowsUpdater, Session
from southpaw_tools import windows_process as wp
from southpaw_tools.bootstrap_diagnostics import call, operation, report, secondary, error_summary
from southpaw_tools.common import LauncherError, app_lock, atomic_json, read_json
from tests.support import temporary


class BootstrapDiagnosticTests(unittest.TestCase):
    def setUp(self):
        tmp=temporary('bd-')
        self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name)

    def bootstrap(self, recover=None):
        b=Bootstrap.__new__(Bootstrap)
        b.events=[]; b.log=self.home/'bootstrap-runs/test.json'
        b.updater=SimpleNamespace(home=self.home,data_root=self.home/'data',channel=True,
                                  recover=recover or Mock(),_lock=nullcontext,
                                  current=Mock(return_value=SimpleNamespace(release_id='r1')))
        return b

    def failure(self, b):
        with patch('southpaw_tools.bootstrap.app_lock',return_value=nullcontext()):
            with self.assertRaises(PermissionError) as caught:
                b.run()
        return caught.exception

    def native_failure(self, step):
        dll=Mock()
        dll.OpenProcess.return_value=0 if step=='open' else 123
        dll.WaitForSingleObject.return_value=0xFFFFFFFF if step=='wait' else 258
        dll.GetProcessTimes.return_value=0 if step=='times' else 1
        dll.QueryFullProcessImageNameW.return_value=0
        with patch.object(wp.ctypes,'WinDLL',return_value=dll),patch.object(wp.ctypes,'get_last_error',return_value=5):
            try:
                wp.identity(2920)
            except PermissionError as exc:
                detail=report(exc,home=self.home)['failure']
            else:
                self.fail('native failure was swallowed')
        self.assertEqual(detail['operation'],'process_identity_'+step)
        self.assertEqual(detail['operations'][0]['pid'],2920)
        self.assertEqual(detail['operations'][0]['access'],0x101000)
        self.assertEqual(detail['winerror'],5)
        self.assertTrue(detail['traceback'])
        self.assertEqual(detail['python_call']['function'],'identity')
        return dll,detail

    def test_openprocess_denied_exact_operation(self):
        dll,d=self.native_failure('open')
        self.assertEqual(d['operations'][0]['api'],'OpenProcess')
        dll.CloseHandle.assert_not_called()

    def test_wait_denied_exact_operation(self):
        dll,d=self.native_failure('wait')
        self.assertEqual(d['operations'][0]['api'],'WaitForSingleObject')
        dll.CloseHandle.assert_called_once_with(123)

    def test_times_denied_exact_operation(self):
        dll,d=self.native_failure('times')
        self.assertEqual(d['operations'][0]['api'],'GetProcessTimes')
        dll.CloseHandle.assert_called_once_with(123)

    def test_image_denied_exact_operation(self):
        dll,d=self.native_failure('image')
        self.assertEqual(d['operations'][0]['api'],'QueryFullProcessImageNameW')
        dll.CloseHandle.assert_called_once_with(123)

    def updater(self):
        u=WindowsUpdater.__new__(WindowsUpdater)
        u.home=self.home; u.active_probe=None
        atomic_json(self.home/'probe-owner.json',{'pid':2920,'created_ticks':'123','image':'unused.exe'})
        return u

    def test_owner_read_failure_preserves_chain(self):
        u=self.updater(); original=ctypes.WinError(5)
        with patch.object(Path,'read_text',side_effect=original):
            with self.assertRaises(LauncherError) as caught: u._probe_stopped()
        self.assertIs(caught.exception.__cause__,original)
        d=report(caught.exception,home=self.home)['failure']
        self.assertEqual(d['operation'],'probe_owner_read')
        self.assertEqual(d['cause']['operation'],'json_read')
        self.assertEqual(d['cause']['winerror'],5)
        self.assertEqual(d['operations'][0]['target'],'<launcher-home>/probe-owner.json')

    def test_owner_identity_denial_not_reclassified_as_stopped(self):
        u=self.updater(); before=(self.home/'probe-owner.json').read_bytes()
        with patch.object(wp,'identity',side_effect=ctypes.WinError(5)):
            with self.assertRaises(PermissionError): u._probe_stopped()
        self.assertEqual((self.home/'probe-owner.json').read_bytes(),before)

    def test_live_orphan_still_blocks_and_missing_process_keeps_marker(self):
        u=self.updater(); record=read_json(self.home/'probe-owner.json')
        with patch.object(wp,'identity',return_value=record):
            with self.assertRaises(LauncherError): u._probe_stopped()
        with patch.object(wp,'identity',return_value=None): u._probe_stopped()
        self.assertTrue((self.home/'probe-owner.json').exists())

    def test_recovering_write_is_not_recovery_failure(self):
        b=self.bootstrap(); original=ctypes.WinError(5)
        with patch('southpaw_tools.bootstrap.atomic_json',side_effect=[original,None]):
            self.assertIs(self.failure(b),original)
        b.updater.recover.assert_not_called()
        self.assertEqual(b.events[-1]['diagnostics']['failure']['operation'],'recovering_log_write')

    def test_atomic_replace_origin_and_event_boundary_are_both_kept(self):
        b=self.bootstrap()
        original=ctypes.WinError(5)
        with patch('southpaw_tools.common.os.replace',side_effect=original):
            with self.assertRaises(PermissionError) as caught: b.event('recovering')
        d=report(caught.exception,home=self.home)['failure']
        self.assertEqual(d['operation'],'atomic_replace')
        self.assertIn('recovering_log_write',[x['operation'] for x in d['operations']])
        self.assertEqual(d['operations'][0]['api'],'os.replace')

    def test_session_prepare_failure_after_recover(self):
        b=self.bootstrap(); original=ctypes.WinError(5)
        with patch('southpaw_tools.bootstrap.Session',side_effect=original):
            self.assertIs(self.failure(b),original)
        b.updater.recover.assert_called_once()
        self.assertEqual(b.events[-1]['diagnostics']['failure']['operation'],'session_prepare')
        self.assertEqual([e['phase'] for e in b.events],['recovering','failed'])

    def test_session_mkdir_exact_call_and_target(self):
        u=SimpleNamespace(home=self.home,channel=True,_validate_release=Mock(),
                          engine=SimpleNamespace(resolve_launch=Mock(return_value=(self.home/'unused.exe',self.home))))
        with patch.object(Path,'mkdir',side_effect=ctypes.WinError(5)):
            with self.assertRaises(PermissionError) as caught:
                call('session_prepare',Session,u,SimpleNamespace(),'normal',api='Session.__init__')
        d=report(caught.exception,home=self.home)['failure']
        self.assertEqual(d['operation'],'session_mkdir')
        self.assertEqual(d['operations'][0]['target'],'<launcher-home>/sessions/<id>')

    def test_lock_open_failure_not_body_failure(self):
        with patch.object(Path,'open',side_effect=ctypes.WinError(5)):
            with self.assertRaises(PermissionError) as caught:
                with app_lock(self.home/'running.lock'): self.fail('must not enter')
        self.assertEqual(report(caught.exception,home=self.home)['failure']['operation'],'lock_open')

    def test_lock_body_failure_is_not_mislabelled_lock_failure(self):
        original=ctypes.WinError(5)
        with self.assertRaises(PermissionError) as caught:
            with app_lock(self.home/'running.lock'):
                with operation('current_read',api='Path.read_bytes',target=self.home/'current.json'):
                    raise original
        self.assertIs(caught.exception,original)
        d=report(original,home=self.home)['failure']
        self.assertEqual(d['operation'],'current_read')
        self.assertNotIn('lock_release',[o['operation'] for o in d['operations']])

    def test_failed_log_write_does_not_mask_primary(self):
        original=ctypes.WinError(5); logging=OSError(28,'secret-secondary')
        b=self.bootstrap(Mock(side_effect=original))
        with patch('southpaw_tools.bootstrap.atomic_json',side_effect=[None,logging]):
            self.assertIs(self.failure(b),original)
        d=report(original,home=self.home)['failure']
        self.assertEqual(d['winerror'],5)
        self.assertEqual(d['secondary'][0]['exception_class'],'OSError')
        self.assertEqual(d['secondary'][0]['operation'],'failed_log_write')

    def test_atomic_cleanup_failure_does_not_mask_replace(self):
        original=ctypes.WinError(5); cleanup=OSError(28,'cleanup')
        with patch('southpaw_tools.common.os.replace',side_effect=original),patch.object(Path,'unlink',side_effect=cleanup):
            with self.assertRaises(PermissionError) as caught: atomic_json(self.home/'result.json',{})
        self.assertIs(caught.exception,original)
        self.assertEqual(report(original,home=self.home)['failure']['secondary'][0]['operation'],'atomic_temp_cleanup')

    def test_no_arbitrary_message_locals_nonce_or_absolute_path_serialized(self):
        secret='NEVER_PRINT_TOKEN_NONCE_OR_BODY'
        private=Path('C:/Users/private-user/Documents/secret.json')
        original=PermissionError(13,secret,str(private))
        original.arbitrary_state={'token':secret}
        try:
            with operation('json_read',api='Path.read_text',target=private): raise original
        except PermissionError: pass
        output=json.dumps(report(original,home=self.home))+error_summary(original)
        for value in (secret,'private-user',str(self.home),str(private),'arbitrary_state'):
            self.assertNotIn(value,output)
        self.assertIn('<outside-known-roots>',output)

    def test_cause_and_implicit_context_are_distinct(self):
        try:
            try: raise ctypes.WinError(5)
            except PermissionError: raise LauncherError('do not serialize')
        except LauncherError as exc:
            d=report(exc)['failure']
        self.assertNotIn('cause',d)
        self.assertEqual(d['context']['winerror'],5)

    def test_bounds_on_chain_operations_and_secondary(self):
        original=ctypes.WinError(5)
        from southpaw_tools.bootstrap_diagnostics import mark
        for i in range(100):
            mark(original,'operation_'+str(i))
            secondary(original,ValueError('private'*1000),'log_failure')
        data=report(original,home=self.home)
        self.assertLessEqual(len(data['failure']['operations']),12)
        self.assertLessEqual(len(data['failure']['secondary']),3)
        self.assertLess(len(json.dumps(data).encode()),48*1024)

    def test_normal_managed_run_preserves_events_and_return_value(self):
        b=self.bootstrap(); fake=Mock()
        fake.process.pid=999; fake.process.wait.return_value=0
        with patch('southpaw_tools.bootstrap.app_lock',return_value=nullcontext()),patch('southpaw_tools.bootstrap.Session',return_value=fake):
            result=b.run()
        self.assertEqual(result,{'launched':['r1'],'worker_exit':None,'current':'r1','product_exe_executed':True})
        self.assertEqual([e['phase'] for e in b.events],['recovering','starting','running','closed'])
        fake.start.assert_called_once(); fake.confirm.assert_called_once()
        self.assertNotIn('diagnostics',read_json(b.log)['events'][-1])

    def test_report_does_not_access_filesystem(self):
        with patch.object(Path,'resolve',side_effect=AssertionError('filesystem access')):
            # No FS calls should be needed, including source-root calculation.
            d=report(ctypes.WinError(5),home=self.home)
        self.assertIn('failure',d)

    def test_main_persists_primary_and_failed_event_secondary(self):
        from southpaw_tools.bootstrap import main
        original=ctypes.WinError(5)
        b=self.bootstrap(Mock(side_effect=original))
        event=b.event
        def fail_failed_log(phase, **fields):
            if phase == 'failed':
                raise OSError(28, 'sensitive secondary text')
            return event(phase, **fields)
        with patch('southpaw_tools.bootstrap.Bootstrap',return_value=b), patch.object(b,'event',side_effect=fail_failed_log), patch('sys.stdout',new_callable=io.StringIO):
            self.assertEqual(main(['run','--home',str(self.home)]),1)
        saved=read_json(next((self.home/'bootstrap-errors').glob('*.json')))
        self.assertEqual(saved['error_type'],'PermissionError')
        self.assertEqual(saved['diagnostics']['failure']['winerror'],5)
        self.assertEqual(saved['diagnostics']['failure']['secondary'][0]['operation'],'failed_log_write')
        self.assertNotIn('sensitive secondary text',json.dumps(saved))

    def test_recovery_lock_boundary_keeps_real_lock_origin(self):
        from southpaw_tools.self_update import SelfUpdater
        u=SelfUpdater.__new__(SelfUpdater)
        u.home=self.home
        with patch.object(Path,'open',side_effect=ctypes.WinError(5)):
            with self.assertRaises(PermissionError) as caught:
                u.recover()
        d=report(caught.exception,home=self.home)['failure']
        self.assertEqual(d['operation'],'lock_open')
        self.assertIn('recovery_lock',[x['operation'] for x in d['operations']])
