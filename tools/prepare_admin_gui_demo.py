"""Prepare a NEW dummy-only admin GUI fixture; never touch real app packages."""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import zipfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from southpaw_tools.admin_gui_model import APP_NAMES, PROJECT, TEST_MARKER
from southpaw_tools.catalog import load_catalog
from southpaw_tools.catalog_trust import CATALOG_ID, b64, catalog_bytes, key_id, sign
from southpaw_tools.common import LauncherError, atomic_bytes, atomic_json, digest


def prepare(root: Path):
    root = root.resolve()
    if not root.is_relative_to((PROJECT/'.test-results').resolve()) or root == PROJECT/'.test-results':
        raise LauncherError("새 시험 환경은 프로젝트 .test-results 하위에만 만들 수 있습니다.")
    if root.exists():
        raise LauncherError("기존 시험 환경은 덮어쓰지 않습니다.")
    root.mkdir(parents=True)
    repo=root/'repository'
    repo.mkdir()
    (repo/'packages').mkdir()
    inputs=root/'inputs'
    inputs.mkdir()
    packages=[]
    for release in ('r1','r2'):
        source=inputs/f'admin-dummy-{release}.zip'
        with zipfile.ZipFile(source,'x',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('Demo.exe',b'MZ harmless admin GUI dummy fixture '+release.encode())
            archive.writestr('asset.json','{"dummy":true}')
        packages.append(digest(source))
    private=Ed25519PrivateKey.generate()
    key=root/'test-only-signing.pem'
    with key.open('xb') as stream:
        stream.write(private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
    public=private.public_key().public_bytes_raw()
    atomic_json(root/'TEST_ONLY_TRUST.json',{'schema_version':1,'catalog_id':CATALOG_ID,
                'minimum_sequence':1,'keys':{key_id(public):b64(public)}})
    apps=[replace(a,display_name=APP_NAMES[a.app_id],description='관리자 GUI 전용 더미 · 실제 프로그램 아님',
                  version='0.0.0',release_id='not-published',published=False,published_at=None,
                  package_name='',package_size=0,sha256='',executable_relative_path='Demo.exe',
                  executable_sha256='',working_directory_relative_path='.',required_paths=['asset.json'],
                  preserve_paths=[],release_notes='',build_id='',icon='')
          for a in load_catalog(PROJECT/'southpaw_tools/data/catalog.json')]
    raw=catalog_bytes(apps,1)
    atomic_json(repo/'catalog.sig.json',sign(raw,private))
    atomic_bytes(repo/'catalog.json',raw)
    atomic_json(root/'admin-gui-test.json',{'purpose':TEST_MARKER,'dummy_package_sha256':packages})
    return repo,key


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        repo,_=prepare(args.root)
        print(f'새 더미 GUI 시험 환경 준비 완료: {repo}')
        return 0
    except (LauncherError,OSError):
        print('더미 GUI 환경 준비 실패. 기존 경로를 덮어쓰거나 자동 재시도하지 않습니다.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
