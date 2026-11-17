"""Stable bootstrap and real Windows fixture handoff; production EXE execution locked."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time
import uuid

from .common import LauncherError, app_lock, atomic_json, digest, inside, read_json
from .runtime_protocol import PURPOSE
from .self_update import PROJECT, SelfUpdater
from .windows_process import identity, still_same
from .bootstrap_diagnostics import call, diagnosed, report, secondary, error_summary


def validate_ack(value, context, pid, stage):
    expected={name:context[name] for name in ('session','nonce','release_id','version','exe_sha256')}
    expected.update(pid=pid,stage=stage)
    if value!=expected:
        raise LauncherError('Windows 시작 응답의 PID·릴리스·해시·nonce 또는 단계 불일치')


class WindowsUpdater(SelfUpdater):
    def __init__(self,home, *, channel=None):
        super().__init__(home, channel=channel)
        self.active_probe=None
        if channel:
            self.engine.catalog_verifier = self.verifier
            return
        policy=read_json(inside(self.home,'windows-fixture-policy.json'))
        if policy.get('purpose')!='approved-harmless-windows-fixtures-v1' or not isinstance(policy.get('exe_sha256'),list):
            raise LauncherError('승인된 무해한 Windows 시험 EXE 표식이 없습니다.')
        self.allowed_exes=set(policy['exe_sha256'])

    @diagnosed("current_verify")
    def _validate_release(self,app):
        if self.channel and (app.executable_relative_path != 'CreativeGroupLauncher.exe'
                             or app.package_type != 'onedir'):
            raise LauncherError('서명된 Windows 제품 런처 패키지만 실행할 수 있습니다.')
        if self.channel and call("retained_verify", self.engine._verify_retained, app.app_id, app.release_id, api="Installer._verify_retained") != app:
            raise LauncherError('런처 파일과 서명된 원본 ZIP의 릴리스가 다릅니다.')
        payload=super()._validate_release(app)
        if not self.channel and app.executable_sha256 not in self.allowed_exes:
            raise LauncherError('실제 제품 EXE 실행은 승인되지 않았습니다. 허용된 시험 EXE만 사용하세요.')
        return payload

    def _probe_stopped(self):
        if self.active_probe and self.active_probe.process and self.active_probe.process.poll() is None:
            raise LauncherError('시작 검사 프로세스가 아직 종료되지 않았습니다. 포인터를 변경하지 않습니다.')
        owner=inside(self.home,'probe-owner.json')
        if call('probe_owner_exists', owner.exists, target=owner, api='Path.exists'):
            record = call('probe_owner_read', read_json, owner, target=owner, api='read_json')
            if call('probe_owner_identity', still_same, record, api='still_same', pid=record.get('pid')):
                raise LauncherError('미완료 시작 검사 프로세스가 남아 있습니다. 정상 종료 후 복구하세요.')

    @contextmanager
    def _runtime_lock(self):
        with super()._runtime_lock():
            self._probe_stopped()
            yield

    def _rollback(self,journal,reason):
        self._probe_stopped()
        return super()._rollback(journal,reason)

    def _probe(self,transaction,result,timeout):
        scenario={'fail':'immediate-exit','bad-ack':'wrong-nonce'}.get(result,result)
        session=Session(self,self.current(),'health',scenario=scenario,timeout=timeout,transaction=transaction)
        self.active_probe=session
        try:
            session.start()
            session.confirm()
            session.stop(require_ack=True)
        except Exception:
            session.stop(require_ack=False)
            raise


class Session:
    def __init__(self,updater,app,mode,*,scenario='ok',timeout=10,transaction=None):
        if mode not in {'normal','health'} or scenario not in {'ok','wrong-nonce','timeout','immediate-exit'} or not 0<timeout<=30:
            raise LauncherError('Windows 시작 세션 인자 오류')
        updater._validate_release(app)
        executable,cwd=updater.engine.resolve_launch(app)
        self.updater,self.app,self.cwd=updater,app,cwd
        self.timeout=timeout
        self.process=None
        self.created=None
        nonce=secrets.token_hex(32)
        if mode=='health':
            journal=updater.journal(transaction)
            if journal['phase']!='probing' or journal['new']!=app.to_dict():
                raise LauncherError('Windows 시작 확인과 업데이트 트랜잭션이 다릅니다.')
            nonce=journal['nonce']
        name=uuid.uuid4().hex
        self.folder=inside(updater.home,f'sessions/{name}')
        call('session_mkdir', self.folder.mkdir, parents=True, exist_ok=False, target=self.folder, api='Path.mkdir')
        self.context={'purpose':PURPOSE,'session':name,'nonce':nonce,
                      'home':str(updater.home),'executable':str(executable),
                      'exe_sha256':app.executable_sha256,'release_id':app.release_id,'version':app.version,
                      'mode':mode,'scenario':scenario,'approved_transaction':transaction,
                      'update_transaction':transaction if mode=='health' else None}
        if updater.channel:
            self.context['managed'] = True
        call('session_context_write', atomic_json, self.folder/'context.json', self.context,
             target=self.folder/'context.json', api='atomic_json')

    def start(self):
        with (self.folder/'stdout.log').open('xb') as out,(self.folder/'stderr.log').open('xb') as err:
            self.process=subprocess.Popen([self.context['executable'],'--session-file',str(self.folder/'context.json')],
                cwd=self.cwd,stdin=subprocess.DEVNULL if self.updater.channel else subprocess.PIPE,
                stdout=out,stderr=err,text=True,encoding='utf-8',
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.created=identity(self.process.pid)
        if not self.created or self.created['image'].casefold()!=self.context['executable'].casefold():
            raise LauncherError('실제 생성된 Windows 프로세스 이미지가 기대 경로와 다릅니다.')
        atomic_json(self.folder/'process.json',self.created)
        if self.context['mode']=='health':
            atomic_json(inside(self.updater.home,'probe-owner.json'),self.created)
        self.wait_ack('ready')
        if self.updater.channel and self.context['mode'] == 'normal':
            from .windows_shell import configure_launcher_window
            configure_launcher_window(self.process.pid, Path(sys.executable), self.updater.data_root)

    def wait_ack(self,stage):
        deadline=time.monotonic()+self.timeout
        path=self.folder/f'{stage}.json'
        last_read_error = None
        while True:
            if self.process.poll() is not None:
                raise LauncherError('시작 확인 전에 대상 Windows 프로세스가 종료됐습니다.') from last_read_error
            try:
                value = read_json(path)
            except LauncherError as exc:
                # Presence is not readiness on Windows. Publication and a reader
                # can overlap, or another handle can temporarily deny reads.
                # Only unavailable files use the existing bounded startup wait.
                if not isinstance(exc.__cause__, (FileNotFoundError, PermissionError)):
                    raise
                last_read_error = exc
            else:
                validate_ack(value,self.context,self.process.pid,stage)
                actual=identity(self.process.pid)
                if actual!=self.created:
                    raise LauncherError('시작 응답의 실제 Windows 프로세스 신원이 바뀌었습니다.')
                return
            remaining=deadline-time.monotonic()
            if remaining<=0:
                if last_read_error and isinstance(last_read_error.__cause__, PermissionError):
                    error = last_read_error.__cause__
                    raise LauncherError(f'Windows EXE 시작 응답 제한 시간 초과: {path.name} 읽기 접근 거부 '
                                        f'(WinError={getattr(error, "winerror", None)})') from last_read_error
                raise LauncherError('Windows EXE 시작 응답 제한 시간 초과') from last_read_error
            try:
                self.process.wait(timeout=min(0.05,remaining))
            except subprocess.TimeoutExpired:
                pass

    def send(self,action,**extra):
        if self.updater.channel:
            atomic_json(self.folder / f'command-{action}.json', {'nonce': self.context['nonce'], **extra})
            return
        self.process.stdin.write(json.dumps({'action':action,'nonce':self.context['nonce'],**extra})+'\n')
        self.process.stdin.flush()

    def confirm(self):
        self.send('confirm')
        self.wait_ack('confirmed')

    def stop(self,*,require_ack=False):
        if self.process is None:
            return
        if self.process.poll() is None:
            try:
                self.send('stop')
            except (BrokenPipeError,OSError):
                pass
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired as exc:
                raise LauncherError('대상 Windows 프로세스 정상 종료를 확인하지 못했습니다. 강제 종료하지 않습니다.') from exc
        if self.process.stdin:
            self.process.stdin.close()
        if require_ack:
            if self.process.returncode!=0:
                raise LauncherError('시작 확인 후 정상 종료 코드가 아닙니다.')
            validate_ack(read_json(self.folder/'stopped.json'),self.context,self.process.pid,'stopped')


class Bootstrap:
    def __init__(self,home, *, channel=None):
        self.updater=WindowsUpdater(home, channel=channel)
        self.events=[]
        self.log=inside(self.updater.home,f'bootstrap-runs/{uuid.uuid4().hex}.json')

    def event(self,phase,**fields):
        self.events.append({'phase':phase,**fields})
        call(phase + '_log_write', atomic_json, self.log, {'events':self.events},
             target=self.log, api='atomic_json')

    def worker(self,transaction,scenario):
        if getattr(sys,'frozen',False):
            args=[sys.executable,'worker']
        else:
            args=[sys.executable,'-B','-m','southpaw_tools.bootstrap','worker']
        args+=['--home',str(self.updater.home),'--transaction',transaction,'--scenario',scenario]
        if self.updater.channel:
            args.append('--managed')
        with self.log.with_suffix('.worker.log').open('xb') as log:
            cwd = Path(sys.executable).resolve().parent if self.updater.channel else PROJECT
            process=subprocess.Popen(args,cwd=cwd,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.event('worker_applying',pid=process.pid)
            try:
                return process.wait(timeout=45)
            except subprocess.TimeoutExpired as exc:
                raise LauncherError('업데이트 작업자가 아직 실행 중입니다. 강제 종료/중복 적용하지 않고 기록을 보존합니다.') from exc

    def run(self,*,transaction=None,stop_after_ready=False,scenario='ok',probe_scenario='ok',stop_file=None):
        u=self.updater
        if stop_file is not None:
            stop_file=Path(stop_file).resolve()
            if not stop_file.is_relative_to(inside(u.home,'control')) or stop_file.exists():
                raise LauncherError('새 시험 종료 제어 파일은 launcher-home/control 아래여야 합니다.')
        with app_lock(inside(u.home,'locks/bootstrap.lock')):
            try:
                self.event('recovering')
                call('recovery', u.recover, api='SelfUpdater.recover')
                launched=[]
                worker_exit=None
                applied_transaction = None
                while True:
                    with u._lock():
                        current=call('current_verify', u.current, api='SelfUpdater.current')
                        if transaction:
                            journal=u.journal(transaction)
                            if journal['phase']!='requested' or journal['old']!=current.to_dict():
                                raise LauncherError('사용자가 승인한 현재 릴리스의 업데이트 요청이 아닙니다.')
                        session=call('session_prepare', Session, u, current, 'normal', scenario=scenario,
                                     transaction=transaction, timeout=25 if u.channel else 10, api='Session.__init__')
                        try:
                            self.event('starting',release_id=current.release_id)
                            session.start()
                            session.confirm()
                        except Exception:
                            session.stop()
                            if applied_transaction is not None:
                                with u._runtime_lock():
                                    u._rollback(u.journal(applied_transaction), 'new normal GUI failed to start')
                                self.event('apply_failed', release_id=current.release_id)
                                applied_transaction = None
                                worker_exit = 2
                                continue
                            raise
                    applied_transaction = None
                    launched.append(current.release_id)
                    self.event('running',release_id=current.release_id,pid=session.process.pid)
                    if u.channel:
                        code = session.process.wait()
                        if code == 20:
                            request = read_json(session.folder / 'request.json')
                            validate_ack({k: v for k, v in request.items() if k != 'transaction'},
                                         session.context, session.process.pid, 'closing')
                            requested = request['transaction']
                            journal = u.journal(requested)
                            if journal['phase'] != 'requested' or journal['old'] != current.to_dict():
                                raise LauncherError('현재 세션의 승인된 업데이트 요청이 아닙니다.')
                            self.event('old_exited', release_id=current.release_id, pid=session.process.pid)
                            worker_exit = self.worker(requested, 'ok')
                            self.event('applied' if worker_exit == 0 else 'apply_failed', exit_code=worker_exit)
                            if worker_exit == 0:
                                applied_transaction = requested
                            call('recovery', u.recover, api='SelfUpdater.recover')
                            continue
                        if code:
                            raise LauncherError(f'직원용 런처 종료 코드: {code}')
                        self.event('closed', release_id=current.release_id, exit_code=code)
                        return {'launched': launched, 'worker_exit': worker_exit,
                                'current': u.current().release_id, 'product_exe_executed': True}
                    if transaction:
                        self.event('user_approved',transaction=transaction)
                        session.send('request-update',transaction=transaction)
                        self.event('closing',release_id=current.release_id)
                        try:
                            code=session.process.wait(timeout=10)
                        except subprocess.TimeoutExpired as exc:
                            raise LauncherError('기존 런처가 종료 중입니다. 포인터를 전환하지 않습니다.') from exc
                        request=read_json(session.folder/'request.json')
                        expected={name:session.context[name] for name in ('session','nonce','release_id','version','exe_sha256')}
                        expected.update(pid=session.process.pid,stage='closing',transaction=transaction)
                        if code!=20 or request!=expected:
                            raise LauncherError('정상 종료된 런처의 승인 요청과 일치하지 않습니다.')
                        session.process.stdin.close()
                        self.event('old_exited',release_id=current.release_id,pid=session.process.pid)
                        worker_exit=self.worker(transaction,probe_scenario)
                        self.event('applied' if worker_exit==0 else 'apply_failed',exit_code=worker_exit)
                        call('recovery', u.recover, api='SelfUpdater.recover')
                        transaction=None  # No automatic update retry.
                        scenario='ok'
                        continue
                    if stop_after_ready:
                        session.stop(require_ack=True)
                    else:
                        while session.process.poll() is None:
                            if stop_file and stop_file.exists():
                                if stop_file.read_text(encoding='utf-8').strip()!='stop':
                                    raise LauncherError('정상 종료 제어 파일 내용 오류')
                                session.stop(require_ack=True)
                                break
                            try:
                                session.process.wait(timeout=0.1)
                            except subprocess.TimeoutExpired:
                                pass
                        session.process.stdin.close()
                    self.event('closed',release_id=current.release_id,exit_code=session.process.returncode)
                    return {'launched':launched,'worker_exit':worker_exit,'current':u.current().release_id,
                            'product_exe_executed':False}
            except Exception as exc:
                diagnostic = report(exc, home=u.home, data=getattr(u, 'data_root', None))
                try:
                    self.event('failed',error_type=type(exc).__name__,error=error_summary(exc), diagnostics=diagnostic)
                except Exception as log_error:
                    secondary(exc, log_error, 'failed_log_write')
                raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role',nargs='?',default='run',choices=['run','worker'])
    parser.add_argument('--home',type=Path)
    parser.add_argument('--managed',action='store_true')
    parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--transaction')
    parser.add_argument('--scenario',choices=['ok','wrong-nonce','timeout','immediate-exit'],default='ok')
    parser.add_argument('--stop-after-ready',action='store_true')
    parser.add_argument('--probe-scenario',choices=['ok','wrong-nonce','timeout','immediate-exit'],default='ok')
    parser.add_argument('--stop-file',type=Path,help='격리 시험에서 정상 종료를 요청할 새 control 파일')
    args=parser.parse_args(argv)
    try:
        channel = None
        managed = args.managed or args.home is None
        if managed:
            from .managed_update import channel_policy, initialize
            from .paths import AppPaths
            if not getattr(sys, 'frozen', False) or args.scenario != 'ok':
                raise LauncherError('관리형 업데이트에는 승인된 패키징 Bootstrap이 필요합니다.')
            channel = channel_policy()
            folder = Path(sys.executable).resolve().parent
            home = folder / 'launcher-home'
            if args.home is not None and args.home.resolve() != home:
                raise LauncherError('Bootstrap 옆 런처 프로그램 경로만 사용할 수 있습니다.')
            args.home = home
            if args.role == 'run':
                if args.transaction or args.stop_after_ready or args.stop_file or args.probe_scenario != 'ok':
                    raise LauncherError('관리형 GUI에서만 업데이트를 요청할 수 있습니다.')
                layout = home / 'layout.json'
                data = args.data_dir
                if data is None:
                    if layout.exists():
                        data = Path(read_json(layout)['user_data_root'])
                    elif channel['repository'].endswith('-trial-releases'):
                        raise LauncherError('시험 채널 첫 실행에는 별도 --data-dir가 필요합니다.')
                    else:
                        data = AppPaths.default().root
                if channel['repository'].endswith('-trial-releases') and data.resolve() == AppPaths.default().root.resolve():
                    raise LauncherError('시험 채널에는 운영 사용자 데이터 경로를 사용할 수 없습니다.')
                initialize(home, data, folder / 'seed', channel)
        if args.role=='worker':
            result=WindowsUpdater(args.home, channel=channel).apply(args.transaction,probe_result=args.scenario,
                                                                  timeout=20 if channel else 3)
            value={'release_id':result.release_id,'worker':True}
        else:
            value=Bootstrap(args.home, channel=channel).run(transaction=args.transaction,stop_after_ready=args.stop_after_ready,
                scenario=args.scenario,probe_scenario=args.probe_scenario,stop_file=args.stop_file)
        print(json.dumps(value))
        return 0 if value.get('worker_exit') in {None,0} else 2
    except (LauncherError,OSError,ValueError,KeyError,TypeError) as exc:
        message = 'Windows Bootstrap 실패: ' + error_summary(exc)
        if args.home is not None:
            try:
                error_log = inside(args.home, f'bootstrap-errors/{uuid.uuid4().hex}.json')
                call('error_log_write', atomic_json, error_log,
                     {'error_type': type(exc).__name__, 'error': error_summary(exc),
                      'diagnostics': report(exc, home=args.home, data=args.data_dir)},
                     target=error_log, api='atomic_json')
                message += f'\n진단 기록: {error_log}'
            except (LauncherError, OSError) as log_error:
                secondary(exc, log_error, 'error_log_write')
                message += '\n진단 기록 저장 실패: ' + error_summary(log_error)
        print(message)
        if getattr(sys, 'frozen', False) and sys.stderr is None:
            import ctypes
            from .branding import DISPLAY_NAME
            ctypes.windll.user32.MessageBoxW(None, message, DISPLAY_NAME, 0x10)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
