"""Read-only, offline diagnostics. No Qt, network, recovery, or install calls."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

try:
    from southpaw_tools.catalog_trust import CatalogVerifier
    from southpaw_tools.catalog import AppRelease
    from southpaw_tools.common import LauncherError
except ImportError:
    # The same script can be copied to a test PC without installing dependencies.
    # Basic state inspection remains available; signature/update claims do not.
    CatalogVerifier = AppRelease = None
    class LauncherError(Exception):
        pass


def load(path, root, issues):
    """Never follow an unexpected link or emit raw file contents/errors."""
    try:
        if path.is_symlink() or path.resolve() != path.absolute() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('linked or outside root')
        if not path.exists():
            return None
        if path.stat().st_size > 6 * 1024 * 1024:
            raise ValueError('oversized state')
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('expected object')
        return value
    except (OSError, ValueError) as exc:
        issues.append({'area': 'root_state' if path.parent == root else 'state',
                       'file_type': path.suffix, 'error_type': type(exc).__name__,
                       'winerror': getattr(exc, 'winerror', None)})
        return None


def identifier(value):
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_. -]{1,120}', value) else None


def timestamp(value):
    try:
        return datetime.fromisoformat(value).isoformat() if isinstance(value, str) and len(value) < 40 else None
    except ValueError:
        return None


def app_summary(value):
    app = (value or {}).get('app') or {}
    if not isinstance(app, dict):
        app = {}
    return {'app_id': identifier(app.get('app_id')), 'version': identifier(app.get('version')),
            'release_id': identifier(app.get('release_id'))}


def files(root, pattern, issues):
    try:
        return sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError as exc:
        issues.append({'area': 'directory_listing', 'error_type': type(exc).__name__,
                       'winerror': getattr(exc, 'winerror', None)})
        return []


def process_status(home):
    if os.name != 'nt' or home is None:
        return {'status': 'unavailable', 'processes': []}
    import ctypes
    from ctypes import wintypes
    try:
        from southpaw_tools.windows_process import identity
    except ImportError:
        return {'status': 'identity_module_unavailable', 'processes': []}
    pids = (wintypes.DWORD * 65536)()
    used = wintypes.DWORD()
    if not ctypes.WinDLL('psapi').EnumProcesses(pids, ctypes.sizeof(pids), ctypes.byref(used)):
        return {'status': 'query_failed', 'processes': []}
    result, denied = [], 0
    for pid in pids[:used.value // ctypes.sizeof(wintypes.DWORD)]:
        if not pid:
            continue
        try:
            record = identity(pid)
        except OSError:
            denied += 1
            continue
        if record and Path(record['image']).is_relative_to(home.parent):
            name = Path(record['image']).name
            if name in {'CGLBootstrap.exe', 'CreativeGroupLauncher.exe'}:
                result.append({'pid': pid, 'executable': name})
    return {'status': 'queried', 'processes': result, 'inaccessible_process_count': denied}


def setup_registration(home):
    """Both views, current user only. Registry presence is not GUI visibility."""
    if os.name != 'nt' or home is None:
        return {'status': 'unavailable'}
    import winreg
    result = {'status': 'queried', 'gui_visibility': 'not_verified', 'entries': []}
    for view, flag in [('64', winreg.KEY_WOW64_64KEY), ('32', winreg.KEY_WOW64_32KEY)]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Uninstall', 0, winreg.KEY_READ | flag) as parent:
                for index in range(winreg.QueryInfoKey(parent)[0]):
                    with winreg.OpenKey(parent, winreg.EnumKey(parent, index)) as key:
                        def value(name):
                            try:
                                return winreg.QueryValueEx(key, name)[0]
                            except FileNotFoundError:
                                return None
                        location = value('InstallLocation')
                        if not isinstance(location, str) or Path(location).absolute() != home.parent:
                            continue
                        result['entries'].append({'view': view, 'display_name': value('DisplayName'),
                            'display_version': value('DisplayVersion'), 'publisher': value('Publisher'),
                            'system_component': value('SystemComponent'), 'no_remove': value('NoRemove'),
                            'uninstall_command_present': bool(value('UninstallString')),
                            'display_icon_present': bool(value('DisplayIcon')),
                            'uninstall_points_to_owned_file': value('UninstallString') == f'"{home.parent / "Uninstall.exe"}"',
                            'display_icon_points_to_owned_file': value('DisplayIcon') == str(home.parent/'launcher.ico'),
                            'estimated_size_kb': value('EstimatedSize')})
        except FileNotFoundError:
            pass
        except OSError as exc:
            result['status'] = 'partial_or_denied'
            result['error_type'] = type(exc).__name__
    return result


def collect(data, home=None):
    data = Path(data).absolute()
    home = Path(home).absolute() if home else None
    issues = []
    settings = load(data/'settings.json', data, issues) or {}
    repository = settings.get('github_repository')
    channel = None
    if home:
        # Installed Bootstrap policy, never a key received from the network.
        policy_dir = home.parent/'_internal/southpaw_tools/data'
        channel = load(policy_dir/'managed-channel.json', home.parent, issues)
        if not repository and channel:
            repository = channel.get('repository')
    if not isinstance(repository, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        repository = None
    result = {'schema_version': 1, 'read_only': True, 'network_requested': False,
              'github_repository': repository, 'catalog': {'status': 'not_cached'},
              'launcher': {'status': 'home_not_supplied'}, 'apps': [], 'issues': issues}
    snapshots = files(data/'diagnostics', 'gui-*.json', issues)
    if home:
        snapshots.extend(files(home/'sessions', '*/gui-status.json', issues))
    snapshots.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    if snapshots:
        scope = home if home and snapshots[0].is_relative_to(home) else data
        snapshot = load(snapshots[0], scope, issues) or {}
        check = snapshot.get('last_catalog_check') or {}
        result['recent_gui'] = {'version': identifier(snapshot.get('version')),
            'updated_at_utc': timestamp(snapshot.get('updated_at_utc')),
            'last_operation': snapshot.get('last_operation') if snapshot.get('last_operation') in
                {'GitHub 업데이트 확인', '서버 연결과 업데이트 확인', '런처 업데이트 준비',
                 '설치', '업데이트', '제거', '복구 설치', '복구 확인', '버전 전환'} else 'other',
            'result': snapshot.get('result') if snapshot.get('result') in {'completed', 'failed'} else 'unknown',
            'last_catalog_check': {'at_utc': timestamp(check.get('at_utc')),
                                  'result': check.get('result') if check.get('result') in {'verified', 'failed'} else 'unknown',
                                  'status': check.get('status') if check.get('status') in {
                                      '응답 확인(마지막 조회)', '서명 검증 실패', 'GitHub 호출 제한',
                                      '인터넷 연결 실패', '저장소 또는 Release를 찾을 수 없음',
                                      'GitHub 접근 거부', '운영 키 미채택', '목록 확인 실패',
                                      '오프라인 · 접속 실패'} else 'unknown'}}
    latest = {}
    trust = data/'catalog-trust.json'
    if trust.exists():
        try:
            if CatalogVerifier is None:
                raise ImportError('signature verifier unavailable; never trust the cache')
            policy = channel.get('policy') if channel else None
            verifier = CatalogVerifier(policy, trust) if policy else CatalogVerifier.bundled(trust)
            state = load(trust, data, issues)
            if state is None:
                raise ValueError('unreadable cache')
            document, apps, _ = verifier._verify_snapshot(state)
            latest = {app.app_id: app for app in apps}
            result['catalog'] = {'status': 'cached_signature_verified', 'sequence': document['sequence'],
                                 'last_network_check': 'not_recorded',
                                 'cache_modified_utc': datetime.fromtimestamp(
                                     trust.stat().st_mtime, timezone.utc).isoformat()}
        except Exception as exc:
            result['catalog'] = {'status': 'cache_unverified', 'error_type': type(exc).__name__,
                                 'last_network_check': 'not_recorded'}
    apps_root = data/'apps'
    if apps_root.is_dir() and apps_root.resolve() == apps_root.absolute():
        for folder in files(apps_root, '*', issues):
            if not folder.is_dir() or folder.is_symlink() or not identifier(folder.name):
                continue
            active = load(folder/'active.json', data, issues)
            current = app_summary(active)
            current['app_id'] = identifier(folder.name)
            current['state'] = 'active_present' if active else 'no_readable_active'
            candidate = latest.get(folder.name)
            current['latest_version'] = candidate.version if candidate else None
            try:
                current['update_available'] = candidate.is_new_release(AppRelease.parse(active['app'])) if candidate and active else None
            except (LauncherError, ValueError, KeyError, TypeError, AttributeError):
                current['update_available'] = None
                current['comparison_error'] = True
            receipt = None
            rid = current['release_id']
            if rid and re.fullmatch(r'[A-Za-z0-9_.-]+', rid):
                receipt = load(folder/'releases'/rid/'receipt.json', data, issues)
            current['active_matches_receipt'] = (active.get('app') == receipt.get('app')
                                                 if active and receipt else None)
            current['journals'] = []
            for journal in files(folder/'transactions', '*.json', issues):
                value = load(journal, data, issues)
                if value:
                    current['journals'].append({'phase': identifier(value.get('phase'))})
            result['apps'].append(current)
    if home:
        pointer = load(home/'current.json', home, issues)
        result['launcher'] = {'status': 'pointer_present' if pointer else 'no_readable_pointer',
                              **app_summary(pointer), 'process_state': process_status(home)}
        runs = files(home/'bootstrap-runs', '*.json', issues)
        if runs:
            run = load(runs[0], home, issues) or {}
            result['launcher']['recent_bootstrap_phases'] = [identifier(e.get('phase'))
                for e in run.get('events', []) if isinstance(e, dict)][-20:]
        errors = files(home/'bootstrap-errors', '*.json', issues)
        result['launcher']['recent_error_types'] = [identifier((load(p, home, issues) or {}).get('error_type'))
                                                     for p in errors[:3]]
        result['launcher']['setup_state_present'] = (home.parent/'setup-state.json').is_file()
        result['setup_registration'] = setup_registration(home)
        result['launcher']['update_journals'] = []
        for p in files(home/'transactions', '*.json', issues):
            value = load(p, home, issues)
            if value:
                result['launcher']['update_journals'].append({'phase': identifier(value.get('phase')),
                    'error_present': bool(value.get('error'))})
        result['launcher']['log_directories'] = ['bootstrap-runs', 'bootstrap-errors', 'sessions', 'transactions']
        result['launcher']['sessions'] = []
        sessions = files(home/'sessions', '*/process.json', issues)
        for p in sessions[:3]:
            # Do not print session folder IDs, nonces, stdin commands, or stdout/stderr contents.
            value = load(p, home, issues)
            if value:
                try:
                    from southpaw_tools.windows_process import still_same
                    running = still_same(value) if os.name == 'nt' else None
                except (OSError, ImportError, KeyError, TypeError, ValueError, LauncherError):
                    running = None
                result['launcher']['sessions'].append({'running': running,
                    'ready_present': (p.parent/'ready.json').is_file(),
                    'confirmed_present': (p.parent/'confirmed.json').is_file(),
                    'stderr_bytes': (p.parent/'stderr.log').stat().st_size if (p.parent/'stderr.log').is_file() else 0})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='읽기 전용·오프라인 런처 진단 (설치/복구/네트워크 요청 없음)')
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--launcher-home', type=Path, help='설치 폴더 아래 launcher-home')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--summary', action='store_true')
    mode.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    report = collect(args.data_dir, args.launcher_home)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print('읽기 전용 진단 · 네트워크 요청 없음')
        print('GitHub:', report['github_repository'] or '확인 불가')
        print('카탈로그:', report['catalog']['status'])
        print('최근 조회:', report.get('recent_gui', {}).get('last_catalog_check') or '기록 없음')
        print('런처:', report['launcher'].get('version') or report['launcher']['status'])
        print('프로세스:', report['launcher'].get('process_state', {'status': '홈 경로 미지정'}))
        print('최근 작업:', report.get('recent_gui', {}).get('last_operation') or '기록 없음',
              report.get('recent_gui', {}).get('result', ''))
        if args.launcher_home:
            print('Bootstrap 단계:', report['launcher'].get('recent_bootstrap_phases', []))
            print('최근 오류 유형:', report['launcher'].get('recent_error_types', []))
            print('제거 등록:', report.get('setup_registration', {}))
            print('로그:', str(args.launcher_home / 'bootstrap-runs'), '/ bootstrap-errors / sessions / transactions')
        for app in report['apps']:
            print(f"- {app['app_id']}: {app['version'] or '미확인'} / 최신 {app['latest_version'] or '미확인'} / 업데이트 {app['update_available']}")
            if app['journals']:
                print('  설치/복구 기록:', app['journals'])
        print('읽기 오류:', len(report['issues']), '· 상세는 --json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
