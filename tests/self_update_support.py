from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import shutil
import urllib.parse
import zipfile

from southpaw_tools.catalog import AppRelease
from southpaw_tools.catalog_trust import CatalogVerifier
from southpaw_tools.common import digest, inside
from southpaw_tools.providers import HttpProvider
from southpaw_tools.self_update import APP_ID, MANIFEST, SelfUpdater
from tests.support import TestSigner


class FileHttpProvider(HttpProvider):
    """Real signed metadata/download validation, disk transport only; no sockets."""
    def __init__(self, repo, verifier):
        super().__init__('http://127.0.0.1:8765',verifier=verifier)
        self.repo=repo
        self.partial=False

    def _open(self,path):
        if path=='/api/catalog':
            file=self.repo/'catalog.json'
        elif path=='/api/catalog.sig':
            file=self.repo/'catalog.sig.json'
        elif path.startswith('/packages/'):
            file=inside(self.repo/'packages',urllib.parse.unquote(path.removeprefix('/packages/')))
        else:
            raise AssertionError('Unexpected request; no network is permitted')
        body=file.read_bytes()
        response=io.BytesIO(body[:10] if self.partial and path.startswith('/packages/') else body)
        response.headers={'Content-Length':str(len(body))}
        return response


def package(root: Path, release, version='1.0.0', *, extra=False, forbidden=False, executable='Launcher.exe'):
    root.mkdir(parents=True,exist_ok=True)
    files={executable:b'MZ dummy launcher '+release.encode(), 'assets/layout.json':b'{"dummy":true}'}
    if forbidden:
        files['settings.json']=b'{"should_not_be_program_data":true}'
    manifest={'schema_version':1,'app_id':APP_ID,'release_id':release,'version':version,
              'files':{name:hashlib.sha256(body).hexdigest() for name,body in files.items()}}
    if extra:
        files['unexpected.bin']=b'unlisted extra file'
    source=root/f'{release}.zip'
    with zipfile.ZipFile(source,'x',zipfile.ZIP_DEFLATED) as z:
        for name,body in files.items():
            z.writestr(name,body)
        z.writestr(MANIFEST,json.dumps(manifest))
    app=AppRelease.parse(dict(app_id=APP_ID,display_name='Creative Group Launcher (dummy)',
        category='Tests',description='Harmless self-update fixture',version=version,release_id=release,
        package_name=source.name,package_size=source.stat().st_size,sha256=digest(source),
        executable_relative_path=executable,executable_sha256=hashlib.sha256(files[executable]).hexdigest(),
        working_directory_relative_path='.',required_paths=[MANIFEST,'assets/layout.json'],preserve_paths=[],
        package_type='onedir',published=True,published_at='2026-11-05T00:00:00+00:00'))
    return source,app


class Fixture:
    def __init__(self,root):
        self.root=root
        root.mkdir(parents=True,exist_ok=True)
        self.data=root/'user-data'
        (self.data/'apps/tilenamer').mkdir(parents=True)
        (self.data/'settings.json').write_text('{"user":"keep"}')
        (self.data/'apps/tilenamer/active.json').write_text('{"other_app":"keep"}')
        (self.data/'work.txt').write_text('user work must survive')
        self.signer=TestSigner(root)
        self.repo=root/'repository'
        (self.repo/'packages').mkdir(parents=True)
        self.updater=SelfUpdater.create(root/'launcher-home',self.data,self.signer.policy)
        self.provider=FileHttpProvider(self.repo,self.updater.verifier)
        self.r1_source,self.r1=package(root/'inputs','launcher-r1')
        self.publish(self.r1_source,self.r1,1)
        self.updater.bootstrap(self.provider)
        self.r2_source,self.r2=package(root/'inputs','launcher-r2','1.1.0')

    def publish(self,source,app,sequence):
        target=self.repo/'packages'/app.package_name
        if not target.exists():
            shutil.copyfile(source,target)
        self.signer.publish(self.repo,[app],sequence)

    def prepare(self):
        self.publish(self.r2_source,self.r2,2)
        return self.updater.prepare(self.provider)
