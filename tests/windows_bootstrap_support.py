"""Native onedir fixtures, signed local packages and isolated bootstrap homes."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile

from southpaw_tools.catalog import AppRelease
from southpaw_tools.common import atomic_json, digest
from southpaw_tools.self_update import APP_ID, MANIFEST, SelfUpdater
from tests.self_update_support import FileHttpProvider
from tests.support import TestSigner


def artifacts():
    return json.loads(Path(os.environ['CGL_WINDOWS_ARTIFACTS']).read_text(encoding='utf-8'))


def bundle(root,role,release,version,builds):
    if role not in {'fixture-r1','fixture-r2'}:
        raise ValueError('Only approved harmless fixtures may become executable test packages')
    record=builds['roles'][role]
    folder=Path(record['folder'])
    files={p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}
    if files!=record['files']:
        raise ValueError('Built fixture file inventory changed')
    source=root/f'{release}.zip'
    manifest={'schema_version':1,'app_id':APP_ID,'release_id':release,'version':version,'files':files}
    with zipfile.ZipFile(source,'x',zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files):
            z.write(folder/name,name)
        z.writestr(MANIFEST,json.dumps(manifest))
    exe=Path(record['executable']).name
    app=AppRelease.parse(dict(app_id=APP_ID,display_name='Windows Bootstrap Fixture',category='Tests',
        description='Approved harmless frozen Windows process fixture',version=version,release_id=release,
        package_name=source.name,package_size=source.stat().st_size,sha256=digest(source),
        executable_relative_path=exe,executable_sha256=files[exe],working_directory_relative_path='.',
        required_paths=[MANIFEST,'_internal/python313.dll'],preserve_paths=[],package_type='onedir',
        published=True,published_at='2026-11-05T00:00:00+00:00'))
    return source,app


class NativeFixture:
    def __init__(self,root,builds,*,wrong_release=False):
        self.root=root
        root.mkdir(parents=True,exist_ok=True)
        self.data=root/'user-data'
        (self.data/'apps/tilenamer').mkdir(parents=True)
        (self.data/'settings.json').write_text('{"keep":true}')
        (self.data/'apps/tilenamer/active.json').write_text('{"other_app":"keep"}')
        self.signer=TestSigner(root)
        self.repo=root/'repository'
        (self.repo/'packages').mkdir(parents=True)
        inputs=root/'inputs'; inputs.mkdir()
        self.r1_source,self.r1=bundle(inputs,'fixture-r1','wrong-release' if wrong_release else 'windows-fixture-r1','1.0.0',builds)
        self.r2_source,self.r2=bundle(inputs,'fixture-r2','windows-fixture-r2','1.1.0',builds)
        self.updater=SelfUpdater.create(root/'launcher-home',self.data,self.signer.policy)
        atomic_json(self.updater.home/'windows-fixture-policy.json',{
            'purpose':'approved-harmless-windows-fixtures-v1',
            'exe_sha256':[builds['roles'][name]['sha256'] for name in ('fixture-r1','fixture-r2')]})
        self.provider=FileHttpProvider(self.repo,self.updater.verifier)
        self.publish(self.r1_source,self.r1,1)
        self.updater.bootstrap(self.provider)

    def publish(self,source,app,sequence):
        shutil.copyfile(source,self.repo/'packages'/app.package_name)
        self.signer.publish(self.repo,[app],sequence)

    def request(self):
        self.publish(self.r2_source,self.r2,2)
        transaction=self.updater.prepare(self.provider)
        self.updater.request_apply(transaction,approved=True)
        return transaction
