"""Local startup handshake and harmless frozen fixture; no GUI or updater engine."""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys

from .common import LauncherError, app_lock, atomic_json, digest, inside, read_json

PURPOSE='creative-group-launcher-windows-session-v1'


def response(context,stage,release_id,version,exe_hash):
    return {'session':context['session'],'nonce':context['nonce'],'pid':os.getpid(),
            'release_id':release_id,'version':version,'exe_sha256':exe_hash,'stage':stage}


def fixture_main(release_id: str, version: str, scope: Path, argv=None):
    parser=argparse.ArgumentParser(description='Harmless Windows startup fixture')
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--session-file',type=Path)
    args=parser.parse_args(argv)
    if args.self_test:
        print(json.dumps({'fixture':True,'release_id':release_id,'version':version,
                          'frozen':bool(getattr(sys,'frozen',False)),'exe_sha256':digest(Path(sys.executable))}))
        return 0
    try:
        file=args.session_file.resolve()
        base=(scope/'.test-results').resolve()
        if not file.is_relative_to(base):
            raise LauncherError('시험 세션 경로가 아닙니다.')
        context=read_json(file)
        home=Path(context['home']).resolve()
        if (context.get('purpose')!=PURPOSE or not home.is_relative_to(base)
                or file!=inside(home,f"sessions/{context['session']}/context.json")
                or read_json(inside(home,'layout.json')).get('purpose')!='creative-group-launcher-self-update-dummy-v1'):
            raise LauncherError('격리 시작 세션 표식 오류')
        executable=Path(sys.executable).resolve()
        exe_hash=digest(executable)
        if (executable!=Path(context['executable']).resolve() or exe_hash!=context['exe_sha256']
                or release_id!=context['release_id'] or version!=context['version']):
            raise LauncherError('실제 EXE와 기대 릴리스/해시가 다릅니다.')
        mode=context['mode']
        if mode not in {'normal','health'}:
            raise LauncherError('시작 모드 오류')
        lease=app_lock(inside(home,'locks/running.lock')) if mode=='normal' else nullcontext()
        with lease:
            active=read_json(inside(home,'current.json'))['app']
            if active['release_id']!=release_id or active['executable_sha256']!=exe_hash:
                raise LauncherError('생명주기 잠금 후 활성 버전 불일치')
            scenario=context.get('scenario','ok')
            ack=response(context,'ready',release_id,version,exe_hash)
            if scenario=='wrong-nonce':
                ack['nonce']='incorrect-fixture-nonce'
            if scenario!='timeout':
                atomic_json(file.parent/'ready.json',ack)
            if scenario=='immediate-exit':
                return 0
            for line in sys.stdin:
                command=json.loads(line)
                if command.get('nonce')!=context['nonce']:
                    raise LauncherError('제어 요청 nonce 불일치')
                if command.get('action')=='confirm':
                    atomic_json(file.parent/'confirmed.json',response(context,'confirmed',release_id,version,exe_hash))
                elif command.get('action')=='stop':
                    atomic_json(file.parent/'stopped.json',response(context,'stopped',release_id,version,exe_hash))
                    return 0
                elif command.get('action')=='request-update' and mode=='normal':
                    transaction=command.get('transaction')
                    if transaction!=context.get('approved_transaction'):
                        raise LauncherError('승인된 업데이트 요청과 다릅니다.')
                    request=response(context,'closing',release_id,version,exe_hash)
                    request['transaction']=transaction
                    atomic_json(file.parent/'request.json',request)
                    return 20
                else:
                    raise LauncherError('알 수 없는 정상 종료/확인 요청')
            return 0  # Bootstrap pipe closed; release only this fixture's own lease.
    except (LauncherError,OSError,ValueError,KeyError,TypeError) as exc:
        print(f'시험 EXE 시작 실패: {exc}',file=sys.stderr)
        return 11
