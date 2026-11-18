"""Read-only production parallel-channel plan. Never creates or publishes a Release.

The old repository remains a COMPLETE compatibility origin for immutable 0.1.4.
A separate rodetoast repository has a DIFFERENT ID; it is not a Transfer alias.
"""
from pathlib import Path
import argparse
import json
from southpaw_tools.catalog_trust import CatalogVerifier
from southpaw_tools.common import LauncherError, digest

LEGACY = 'toast-source/creative-group-releases'
LEGACY_ID = 1447701732
CANONICAL = 'rodetoast/creative-group-releases'
PRODUCTION_KEY = '1efdfb848bb31e3fa5c07095f952c08d920be77253261fbf2742755341f018e0'
APPS = {'tilenamer','ase-viewer','tag-master','ps2ase','pivot-fixer','creative-group-launcher'}

def public_identity(metadata, name, identity=None):
    if (metadata.get('full_name') != name or metadata.get('visibility') != 'public'
            or metadata.get('private', False) is not False or type(metadata.get('id')) is not int
            or metadata['id'] <= 0 or identity is not None and metadata['id'] != identity):
        raise LauncherError('정확한 운영 저장소 ID·owner·Public 상태가 필요합니다.')

def prepare(assets, policy, legacy, target=None, legacy_release=None):
    """Validate inputs without writing, signing, network calls or key access."""
    assets = Path(assets)
    public_identity(legacy, LEGACY, LEGACY_ID)
    if set(policy.get('keys', {})) != {PRODUCTION_KEY} or policy.get('minimum_sequence') != 4:
        raise LauncherError('기존 운영키와 최소 순번4 정책만 사용할 수 있습니다.')
    if assets.is_symlink() or assets.is_junction():
        raise LauncherError('배포 자산 디렉터리에 링크를 사용할 수 없습니다.')
    verifier = CatalogVerifier(policy, assets.parent/'unused-parallel-verification.json')
    document, apps = verifier.verify((assets/'catalog.json').read_bytes(), (assets/'catalog.sig.json').read_bytes())
    packages = {app.package_name:app for app in apps if app.published}
    if ({app.app_id for app in apps if app.published} != APPS or len(packages) != 6
            or len(apps) != 6):
        raise LauncherError('회사앱5개와 런처의 완전한 카탈로그가 필요합니다.')
    names = {'catalog.json','catalog.sig.json',*packages}
    if {p.name for p in assets.iterdir()} != names:
        raise LauncherError('카탈로그·서명·전체 ZIP의 정확한8자산만 허용합니다.')
    rows = []
    for name in sorted(names):
        path = assets/name
        if path.is_symlink() or not path.is_file():raise LauncherError('원본 자산 링크/누락')
        sha, size = digest(path), path.stat().st_size
        if name in packages and (sha != packages[name].sha256 or size != packages[name].package_size):
            raise LauncherError('원본 ZIP이 서명 카탈로그와 다릅니다.')
        rows.append({'name':name,'size':size,'sha256':sha})
    target_id = None
    if target is not None:
        public_identity(target, CANONICAL)
        if target['id'] == LEGACY_ID:raise LauncherError('신규 병행 저장소를 Transfer alias와 혼동할 수 없습니다.')
        if target.get('permissions',{}).get('admin') is not True:
            raise LauncherError('rodetoast 신규 운영 저장소의 관리자 권한 확인이 필요합니다.')
        target_id = target['id']
    plan = {'schema_version':1,'mode':'canonical-and-permanent-complete-legacy-channel',
            'legacy_repository':LEGACY,'legacy_repository_id':LEGACY_ID,
            'canonical_repository':CANONICAL,'canonical_repository_id':target_id,
            'catalog_sequence':document['sequence'],'tag':f'production-catalog-{document["sequence"]:06d}',
            'key_id':PRODUCTION_KEY,'assets':rows,'resign_catalog':False,
            'legacy_transfer_or_rename_allowed':False,'legacy_full_assets_required':True,
            'catalog_and_signature_must_be_byte_identical_on_both':True,
            'gui_014_015_still_use_legacy_origin':True,
            'new_client_route_switch_implemented':False,
            'new_repository_binding_confirmed':target_id is not None,
            'remote_write_authorized':False,
            'prepare_action':'initial_canonical_copy_only',
            'legacy_existing_release_verified':False,
            'legacy_release_create_or_edit':False,
            'publication_order':['verify existing complete legacy Release and leave it untouched',
                                 'new canonical draft + full redownload/signature verification',
                                 'publish canonical only under separate explicit approval'],
            'failure_policy':'Keep existing legacy Latest. Never re-sign same sequence or roll trust back.'}
    if legacy_release is not None:
        if legacy_release.get('draft') is not False or legacy_release.get('prerelease') is not False:
            raise LauncherError('기존 호환 Release는 완전히 공개된 일반 Release여야 합니다.')
        verify_release_assets(plan, legacy_release)
        plan['legacy_existing_release_verified'] = True
    return plan


def verify_release_assets(plan, release):
    expected={a['name']:(a['size'],'sha256:'+a['sha256']) for a in plan['assets']}
    rows=release.get('assets',[])
    if (release.get('tag_name')!=plan['tag'] or len(rows)!=len(expected)
            or {a['name']:(a['size'],a.get('digest')) for a in rows}!=expected):
        raise LauncherError('병행 Release가 승인된 전체자산 바이트와 일치하지 않습니다.')
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--policy',type=Path,required=True)
    parser.add_argument('--legacy-metadata',type=Path,required=True)
    parser.add_argument('--target-metadata',type=Path)
    parser.add_argument('--legacy-release',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise LauncherError('기존 계획을 덮어쓰지 않습니다.')
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    policy=read(args.policy);policy=policy.get('policy',policy)
    plan=prepare(args.assets,policy,read(args.legacy_metadata),read(args.target_metadata) if args.target_metadata else None, read(args.legacy_release))
    with args.output.open('x',encoding='utf-8') as stream:json.dump(plan,stream,ensure_ascii=False,indent=2)
    print('로컬 병행 계획 검증 완료. 운영 게시/저장소 생성은 실행하지 않았습니다.')

if __name__=='__main__':main()
