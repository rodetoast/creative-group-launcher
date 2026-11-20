"""Reproducible onedir development builds; never executes a built product EXE."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

from southpaw_tools.common import LauncherError, atomic_json, digest
from southpaw_tools import __version__
from southpaw_tools.branding import DISPLAY_NAME

PROJECT=Path(__file__).resolve().parents[1]
NAMES={'fixture-r1':'CGLFixtureR1','fixture-r2':'CGLFixtureR2',
       'bootstrap':'CGLBootstrap','launcher':'CreativeGroupLauncher'}


def build_environment(root: Path):
    # PyInstaller resolves native dependencies through PATH. Do not collect unrelated
    # application DLLs (for example Poppler's ICU) ahead of Windows' system DLLs.
    windows=Path(os.environ['SystemRoot'])
    python=Path(sys.executable).parent
    return {**os.environ,'PATH':os.pathsep.join(map(str,(windows/'System32',windows,python,python/'Scripts'))),
            'PYINSTALLER_CONFIG_DIR':str(root/'cache'),'PYTHONHASHSEED':'0',
            'SOURCE_DATE_EPOCH':'1793836800','PYTHONIOENCODING':'utf-8'}


def add_launcher_manifest(folder: Path, release_id='windows-dev-0.1.0'):
    target=folder/'launcher-package.json'
    if target.exists():
        raise LauncherError('기존 제품 manifest를 덮어쓰지 않습니다.')
    files={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}
    atomic_json(target,{'schema_version':1,'app_id':'creative-group-launcher',
                       'release_id':release_id,'version':__version__,'files':files})


def product_version_resource(path, filename):
    """Windows display metadata, separate from the stable internal EXE name."""
    parts = tuple(int(part) for part in __version__.split('.'))
    if len(parts) != 3:
        raise LauncherError('제품 빌드에는 세 자리 숫자 버전이 필요합니다.')
    values = {'CompanyName': 'Southpaw Games', 'FileDescription': DISPLAY_NAME,
              'ProductName': DISPLAY_NAME, 'FileVersion': __version__, 'ProductVersion': __version__,
              'OriginalFilename': filename, 'InternalName': Path(filename).stem}
    strings = ','.join(f'StringStruct({key!r},{value!r})' for key, value in values.items())
    path.write_text('VSVersionInfo(ffi=FixedFileInfo(filevers='+repr(parts+(0,))+
        ',prodvers='+repr(parts+(0,))+
        ',mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),kids=['+
        "StringFileInfo([StringTable('041204b0',["+strings+"])]),VarFileInfo([VarStruct('Translation',[1042,1200])])])", encoding='utf-8')


def build(root: Path, roles, launcher_release_id='windows-dev-0.1.0', *, bootstrap_windowed=False,
          bootstrap_icon=None, product_icon=None, bootstrap_upgrade=False):
    root=root.resolve()
    if not root.is_relative_to((PROJECT/'.test-results').resolve()):
        raise LauncherError('빌드 출력은 격리 .test-results 안에만 생성합니다.')
    if sys.platform!='win32' or sys.version_info[:2]!=(3,13):
        raise LauncherError('현재 빌드 기준은 Windows x64 Python 3.13입니다.')
    versions={n:importlib.metadata.version(n) for n in ['PyInstaller','pyinstaller-hooks-contrib','PySide6','cryptography']}
    if versions!={'PyInstaller':'6.22.3','pyinstaller-hooks-contrib':'2026.9','PySide6':'6.11.0','cryptography':'50.0.2'}:
        raise LauncherError(f'고정 빌드 의존성 불일치: {versions}')
    root.mkdir(parents=True,exist_ok=True)
    if product_icon is not None:
        product_icon = product_icon.resolve()
        if not product_icon.is_file() or product_icon.suffix.lower() != '.ico':
            raise LauncherError('제품 아이콘에는 승인된 Windows ICO 파일이 필요합니다.')
    entries=root/'entries'; entries.mkdir(exist_ok=True)
    previous=json.loads((root/'artifacts.json').read_text(encoding='utf-8')) if (root/'artifacts.json').exists() else {'roles':{}}
    for existing in previous['roles'].values():
        existing.setdefault('source_hashes',previous.get('source_hashes',{}))
    env=build_environment(root)
    for role in roles:
        name=NAMES[role]
        if role in previous['roles'] or (root/'dist'/name).exists():
            raise LauncherError('기존 빌드 결과를 덮어쓰지 않습니다. 새 출력 경로를 사용하세요.')
        entry=entries/f'{role}.py'
        if role.startswith('fixture'):
            release='windows-fixture-r1' if role.endswith('r1') else 'windows-fixture-r2'
            version='1.0.0' if role.endswith('r1') else '1.1.0'
            text=(f'from pathlib import Path\nfrom southpaw_tools.runtime_protocol import fixture_main\n'
                  f'raise SystemExit(fixture_main({release!r},{version!r},Path({str(PROJECT)!r})))\n')
        elif role=='bootstrap':
            text=(f'from pathlib import Path\nfrom southpaw_tools.startup_splash import frozen_bootstrap\n'
                  f'raise SystemExit(frozen_bootstrap(Path({str(PROJECT)!r}), upgrade_entry={bootstrap_upgrade!r}))\n')
        else:
            text='from southpaw_tools.__main__ import main\nraise SystemExit(main())\n'
        text=('import sys\nfor stream in (sys.stdout,sys.stderr):\n'
              '    if stream is not None and hasattr(stream,"reconfigure"):\n'
              '        stream.reconfigure(encoding="utf-8")\n'+text)
        entry.write_text(text,encoding='utf-8')
        command=[sys.executable,'-B','-m','PyInstaller','--onedir','--noupx','--name',name,
                 '--distpath',str(root/'dist'),'--workpath',str(root/'work'/role),
                 '--specpath',str(root/'specs'),'--paths',str(PROJECT),
                 '--exclude-module','PyQt5','--exclude-module','PyQt6','--exclude-module','PySide2',
                 '--exclude-module','tkinter','--exclude-module','tests']
        if bootstrap_upgrade and role == 'bootstrap':
            from southpaw_tools.bootstrap_upgrade import RUNTIME
            command += ['--contents-directory', RUNTIME]
        if role in {'launcher', 'bootstrap'}:
            resource = entries/f'{role}-version.txt'
            product_version_resource(resource, name+'.exe')
            command+=['--version-file', str(resource)]
        if role=='launcher':
            command+=['--windowed','--add-data',f'{PROJECT / "southpaw_tools/data"}:southpaw_tools/data',
                      '--add-data',f'{PROJECT / "southpaw_tools/assets"}:southpaw_tools/assets']
            if product_icon:
                command+=['--icon',str(product_icon)]
        else:
            command+=['--windowed' if bootstrap_windowed and role=='bootstrap' else '--console']
            if role == 'bootstrap' and (product_icon or bootstrap_icon):
                command+=['--icon',str(product_icon or bootstrap_icon)]
            channel = PROJECT / 'southpaw_tools/data/managed-channel.json'
            if role == 'bootstrap' and channel.is_file():
                command+=['--add-data',f'{channel}:southpaw_tools/data']
                trust = channel.with_name('trusted_catalog_keys.json')
                command+=['--add-data',f'{trust}:southpaw_tools/data']
        command.append(str(entry))
        with (root/f'{role}-build.log').open('xb') as log:
            result=subprocess.run(command,cwd=PROJECT,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:
            raise LauncherError(f'{role} 빌드 실패. 해당 build.log를 보존하고 확인하세요.')
        folder=root/'dist'/name
        if role=='launcher':
            add_launcher_manifest(folder, launcher_release_id)
        files={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}
        exe=folder/f'{name}.exe'
        if exe.read_bytes()[:2]!=b'MZ':
            raise LauncherError('Windows PE 출력이 아닙니다.')
        if role=='launcher':
            required=['python313.dll','Qt6Core.dll','Qt6Gui.dll','Qt6Widgets.dll','qwindows.dll']
            for basename in required:
                if not any(Path(n).name.casefold()==basename.casefold() for n in files):
                    raise LauncherError(f'필수 DLL 누락: {basename}')
            if not any('_rust' in n and n.endswith('.pyd') for n in files):
                raise LauncherError('cryptography 네이티브 모듈 누락')
            if not any(n.endswith('southpaw_tools/data/trusted_catalog_keys.json') for n in files):
                raise LauncherError('고정 신뢰키 정책 리소스 누락')
        sources={str(p.relative_to(PROJECT)):digest(p) for p in (PROJECT/'southpaw_tools').rglob('*.py')}
        previous['roles'][role]={'folder':str(folder),'executable':str(exe),'sha256':digest(exe),
                                 'files':files,'file_count':len(files),'executed':False,'source_hashes':sources}
        previous['toolchain']={'python':sys.version,'packages':versions}
        previous['source_hashes']=sources
        atomic_json(root/'artifacts.json',previous)
        print(f'{role}: built {len(files)} files; EXE not executed',flush=True)
    return previous


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--roles',nargs='+',choices=list(NAMES),default=list(NAMES))
    parser.add_argument('--launcher-release-id',default='windows-dev-0.1.0')
    parser.add_argument('--bootstrap-windowed',action='store_true')
    parser.add_argument('--bootstrap-upgrade',action='store_true')
    parser.add_argument('--bootstrap-icon',type=Path)
    parser.add_argument('--product-icon',type=Path,help='승인된 ICO를 Bootstrap·런처 EXE에 공통 적용')
    args=parser.parse_args(argv)
    try:
        build(args.root,args.roles,args.launcher_release_id,bootstrap_windowed=args.bootstrap_windowed,
              bootstrap_icon=args.bootstrap_icon,product_icon=args.product_icon,bootstrap_upgrade=args.bootstrap_upgrade)
        return 0
    except (LauncherError,OSError) as exc:
        print(f'격리 빌드 실패: {exc}')
        return 1


if __name__=='__main__':
    raise SystemExit(main())
