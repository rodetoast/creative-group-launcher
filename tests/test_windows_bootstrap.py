from __future__ import annotations

import json
import os
from pathlib import Path
import struct
import subprocess
import time
import unittest

from southpaw_tools.bootstrap import Session, WindowsUpdater
from southpaw_tools.common import LauncherError, atomic_json, digest, read_json
from southpaw_tools.windows_process import identity
from tests.support import temporary
from tests.windows_bootstrap_support import NativeFixture, artifacts


def tree(root):
    return {str(p.relative_to(root)):digest(p) for p in root.rglob('*') if p.is_file()}


@unittest.skipUnless(os.name=='nt' and os.environ.get('CGL_WINDOWS_ARTIFACTS'),'Requires explicit approved Windows build artifacts')
class WindowsBootstrapTests(unittest.TestCase):
    blocked=False

    def setUp(self):
        if type(self).blocked:
            self.skipTest('Native EXE execution blocked; stop further execution without policy changes')
        # Keep the real fixture's recovery paths within the Win32 budget even
        # when this checkout sits under a long Documents directory.
        self.tmp=temporary('nb-')
        self.addCleanup(self.tmp.cleanup)
        self.builds=artifacts()
        self.root=Path(self.tmp.name)
        self.f=NativeFixture(self.root/'f',self.builds)
        self.exe=self.builds['roles']['bootstrap']['executable']
        self.original_data=tree(self.f.data)

    def run_bootstrap(self,*args,home=None):
        command=[self.exe,*args,'--home',str(home or self.f.updater.home)]
        try:
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=40,
                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except OSError as exc:
            if getattr(exc,'winerror',None) in (4551,577,1260):
                type(self).blocked=True
            raise
        if any(code in result.stdout+result.stderr for code in ('4551','WinError=577','WinError=1260')):
            type(self).blocked=True
            self.fail('Windows application control blocked the fixture; no bypass or retry')
        return result

    def assert_data_preserved(self):
        self.assertEqual(tree(self.f.data),self.original_data)

    def test_build_inventory_and_product_dlls_without_executing_product(self):
        record=self.builds['roles']['launcher']
        folder=Path(record['folder'])
        files=record['files']
        for name,sha in files.items():
            self.assertEqual(digest(folder/name),sha)
            self.assertNotIn(Path(name).suffix.lower(),{'.pem','.key','.pfx'})
        for basename in ('python313.dll','Qt6Core.dll','Qt6Gui.dll','Qt6Widgets.dll','qwindows.dll'):
            self.assertTrue(any(Path(n).name.casefold()==basename.casefold() for n in files))
        key=next(folder/n for n in files if n.endswith('southpaw_tools/data/trusted_catalog_keys.json'))
        self.assertEqual(read_json(key)['keys'],{})
        manifest=read_json(folder/'launcher-package.json')
        self.assertEqual(manifest['app_id'],'creative-group-launcher')
        self.assertEqual(manifest['files'],{n:h for n,h in files.items() if n!='launcher-package.json'})
        raw=Path(record['executable']).read_bytes()
        pe=struct.unpack_from('<I',raw,0x3c)[0]
        self.assertEqual(raw[pe:pe+4],b'PE\x00\x00')
        self.assertEqual(struct.unpack_from('<H',raw,pe+4)[0],0x8664)
        self.assertEqual(struct.unpack_from('<H',raw,pe+24+68)[0],2)

    def test_frozen_bootstrap_selects_current_and_stops_normally(self):
        result=self.run_bootstrap('run','--stop-after-ready')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(result.stdout.strip())
        self.assertEqual(report['launched'],['windows-fixture-r1'])
        sessions=list((self.f.updater.home/'sessions').iterdir())
        self.assertEqual(len(sessions),1)
        ready=read_json(sessions[0]/'ready.json')
        self.assertEqual(ready['exe_sha256'],self.f.r1.executable_sha256)
        self.assertIsNone(identity(ready['pid']))
        self.assert_data_preserved()

    def test_real_exit_worker_probe_and_new_version_launch(self):
        transaction=self.f.request()
        result=self.run_bootstrap('run','--transaction',transaction,'--stop-after-ready')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(result.stdout.strip())
        self.assertEqual(report['launched'],['windows-fixture-r1','windows-fixture-r2'])
        self.assertEqual(self.f.updater.journal(transaction)['phase'],'committed')
        events=read_json(next((self.f.updater.home/'bootstrap-runs').glob('*.json')))['events']
        phases=[event['phase'] for event in events]
        self.assertLess(phases.index('old_exited'),phases.index('worker_applying'))
        for session in (self.f.updater.home/'sessions').iterdir():
            context=read_json(session/'context.json')
            if context['mode']=='health':
                self.assertEqual(read_json(session/'confirmed.json')['nonce'],context['nonce'])
                self.assertEqual(context['nonce'],self.f.updater.journal(transaction)['nonce'])
                self.assertEqual(context['update_transaction'],transaction)
                self.assertTrue((session/'stopped.json').exists())
        self.assert_data_preserved()

    def test_duplicate_bootstrap_and_update_blocked_while_real_child_runs(self):
        transaction=self.f.request()
        stop=self.f.updater.home/'control/stop.request'
        stop.parent.mkdir()
        child=subprocess.Popen([self.exe,'run','--home',str(self.f.updater.home),'--stop-file',str(stop)],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                # Opening an atomic-write temporary file can block its rename on Windows.
                records=[path for path in (self.f.updater.home/'bootstrap-runs').glob('*.json')
                         if not path.name.startswith('.pending-')]
                if records and any(e['phase']=='running' for e in read_json(records[0])['events']):
                    break
                if child.poll() is not None:
                    self.fail(str(child.communicate()))
                try: child.wait(timeout=0.05)
                except subprocess.TimeoutExpired: pass
            else:
                self.fail('Native bootstrap did not reach running state')
            self.assertNotEqual(self.run_bootstrap('run','--stop-after-ready').returncode,0)
            self.assertNotEqual(self.run_bootstrap('worker','--transaction',transaction).returncode,0)
            self.assertEqual(self.f.updater.current(),self.f.r1)
        finally:
            stop.write_text('stop',encoding='utf-8')
            out,err=child.communicate(timeout=15)
        self.assertEqual(child.returncode,0,out+err)

    def test_wrong_nonce_rejected_without_pointer_change(self):
        result=self.run_bootstrap('run','--scenario','wrong-nonce','--stop-after-ready')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.f.updater.current(),self.f.r1)

    def test_startup_timeout_rejected_without_forced_kill(self):
        result=self.run_bootstrap('run','--scenario','timeout','--stop-after-ready')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.f.updater.current(),self.f.r1)
        for folder in (self.f.updater.home/'sessions').iterdir():
            self.assertIsNone(identity(read_json(folder/'process.json')['pid']))

    def test_immediate_exit_is_not_healthy_start(self):
        result=self.run_bootstrap('run','--scenario','immediate-exit','--stop-after-ready')
        self.assertNotEqual(result.returncode,0)

    def test_compiled_release_identity_mismatch_rejected(self):
        other=NativeFixture(self.root/'w',self.builds,wrong_release=True)
        result=self.run_bootstrap('run','--stop-after-ready',home=other.updater.home)
        self.assertNotEqual(result.returncode,0)

    def test_failed_new_exe_handshake_rolls_back_and_starts_old(self):
        transaction=self.f.request()
        result=self.run_bootstrap('run','--transaction',transaction,'--probe-scenario','wrong-nonce','--stop-after-ready')
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        report=json.loads(result.stdout.strip())
        self.assertEqual(report['launched'],['windows-fixture-r1','windows-fixture-r1'])
        self.assertEqual(report['worker_exit'],1)
        self.assertEqual(self.f.updater.journal(transaction)['phase'],'rolled_back')
        self.assert_data_preserved()

    def test_duplicate_completed_update_is_rejected(self):
        transaction=self.f.request()
        self.assertEqual(self.run_bootstrap('worker','--transaction',transaction).returncode,0)
        self.assertNotEqual(self.run_bootstrap('worker','--transaction',transaction).returncode,0)
        self.assertEqual(self.f.updater.current(),self.f.r2)

    def test_orphan_probe_identity_blocks_recovery_until_normal_exit(self):
        transaction=self.f.request()
        journal=self.f.updater.journal(transaction)
        self.f.updater._phase(journal,'switching')
        self.f.updater._point(self.f.r2)
        self.f.updater._phase(journal,'probing')
        updater=WindowsUpdater(self.f.updater.home)
        session=Session(updater,self.f.r2,'health',transaction=transaction)
        try:
            session.start()
            session.confirm()
            with self.assertRaises(LauncherError):
                WindowsUpdater(self.f.updater.home).recover()
        finally:
            session.stop(require_ack=True)
        self.assertEqual(WindowsUpdater(self.f.updater.home).recover(),self.f.r1)

    def test_product_exe_hash_is_not_allowed_as_fixture(self):
        policy=self.f.updater.home/'windows-fixture-policy.json'
        atomic_json(policy,{'purpose':'approved-harmless-windows-fixtures-v1','exe_sha256':[]})
        result=self.run_bootstrap('run','--stop-after-ready')
        self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.f.updater.home/'sessions').exists())


if __name__=='__main__':
    unittest.main()
