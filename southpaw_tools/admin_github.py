"""Test-only GitHub delivery adapter around the existing signed local publisher."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
from urllib.parse import quote

from .admin_gui_model import AdminSession, Review, PROJECT
from .archive import extract_checked
from .catalog_trust import CatalogVerifier
from .common import LauncherError, atomic_json, digest

REPOSITORY = "toast-source/creative-group-releases"
PREFIX = f"repos/{REPOSITORY}"


@dataclass(frozen=True)
class DraftTransferGrant:
    """Explicit one-tag test capability; never loaded from GUI settings."""
    root: Path
    tag: str
    sequence: int
    key_id: str
    package_sha256: str
    release_id: str

    def __post_init__(self):
        if (not self.root.resolve().is_relative_to((PROJECT/'.test-results').resolve())
                or self.root.name!='repository' or type(self.sequence) is not int or self.sequence<1
                or self.tag!=f'catalog-{self.sequence:06d}'
                or not re.fullmatch('[a-f0-9]{64}',self.key_id)
                or not re.fullmatch('[a-f0-9]{64}',self.package_sha256)):
            raise LauncherError("실제 Draft 시험 권한의 경로·tag·키·해시가 잘못되었습니다.")


class GhCliTransport:
    """An injected runner is the dry-run boundary; real CLI writes remain locked."""
    def __init__(self, executable: Path | str = "gh", *, runner=None, draft_grant: DraftTransferGrant | None=None):
        self.executable = str(executable)
        self.runner = runner
        self.dry_run = runner is not None
        self.calls = []
        self.draft_grant = draft_grant
        self._bound_assets = {}
        self._owned_draft_id = None
        self._create_attempted = False
        self._upload_attempts = set()

    @property
    def draft_enabled(self):
        return self.dry_run or self.draft_grant is not None

    def bind_bundle(self, root, tag, assets):
        grant=self.draft_grant
        expected={'catalog.json','catalog.sig.json',f'dummy--{grant.release_id}.zip'} if grant else set()
        if (grant is None or root.resolve()!=grant.root.resolve() or tag!=grant.tag
                or {a.name for a in assets}!=expected or len(assets)!=3 or self._bound_assets):
            raise LauncherError("승인된 실제 Draft 묶음과 일치하지 않습니다.")
        self._bound_assets={a.name:a for a in assets}

    def _guard_write(self, method, endpoint, payload, source):
        grant=self.draft_grant
        if (grant is None or not self._bound_assets or method!='POST'):
            raise LauncherError("실제 GitHub 쓰기는 잠겨 있습니다. 이 권한으로 공개·수정·삭제할 수 없습니다.")
        if endpoint==PREFIX+'/releases':
            if (self._create_attempted or not isinstance(payload,dict)
                    or payload.get('tag_name')!=grant.tag or payload.get('draft') is not True
                    or payload.get('prerelease') is not False or payload.get('make_latest')!='false'
                    or set(payload)-{'tag_name','target_commitish','name','body','draft','prerelease','make_latest'}):
                raise LauncherError("승인된 새 초안 한 개만 생성할 수 있습니다.")
            self._create_attempted=True
            return
        for name,asset in self._bound_assets.items():
            expected=f'https://uploads.github.com/{PREFIX}/releases/{self._owned_draft_id}/assets?name='+quote(name,safe='')
            if endpoint==expected:
                if (self._owned_draft_id is None or name in self._upload_attempts or source is None
                        or Path(source).resolve()!=asset.path.resolve() or asset.path.is_symlink()
                        or asset.path.stat().st_size!=asset.size or digest(asset.path)!=asset.sha256):
                    raise LauncherError("승인된 자산 원본만 새 초안에 한 번 업로드할 수 있습니다.")
                self._upload_attempts.add(name)
                return
        raise LauncherError("새 시험 초안 이외의 Release에는 쓸 수 없습니다.")

    def request(self, method, endpoint, *, payload=None, source=None, binary=False):
        if endpoint not in {'user',PREFIX} and not endpoint.startswith((PREFIX+'/',
                f'https://uploads.github.com/{PREFIX}/')):
            raise LauncherError("승인된 GitHub 배포 저장소만 사용할 수 있습니다.")
        if method not in {'GET', 'POST', 'PATCH'} or endpoint == 'user' and method != 'GET':
            raise LauncherError("지원하지 않는 GitHub 작업입니다.")
        if method != 'GET' and self.runner is None:
            self._guard_write(method,endpoint,payload,source)
        args=[self.executable,'api','--include','--method',method,endpoint]
        if source is not None:
            args += ['--input',str(source),'-H','Content-Type: application/octet-stream']
        elif payload is not None:
            args += ['--input','-','-H','Content-Type: application/json']
        if binary:
            args += ['-H','Accept: application/octet-stream']
        body=json.dumps(payload).encode() if payload is not None else None
        try:
            if self.runner is not None:
                response=self.runner(args,body)
            else:
                response=subprocess.run(args,input=body,capture_output=True,timeout=60,
                                        env={k:v for k,v in os.environ.items() if k!='GH_DEBUG'})
        except (OSError,subprocess.TimeoutExpired) as exc:
            self.calls.append({'method':method,'endpoint':endpoint.split('?')[0],
                               'exit_code':None,'http_status':None,'error_type':type(exc).__name__})
            raise LauncherError("GitHub CLI 실행·응답 실패. 실제 원격 상태를 확인하고 재시도하지 마세요.") from exc
        sections=re.split(br'\r?\n\r?\n',response.stdout,maxsplit=1)
        header=sections[0] if len(sections)==2 else b''
        raw=sections[1] if len(sections)==2 else response.stdout
        match=re.match(br'HTTP/\S+ (\d+)',header)
        status=int(match[1]) if match else 0
        self.calls.append({'method':method,'endpoint':endpoint.split('?')[0],
                           'exit_code':response.returncode,'http_status':status})
        if response.returncode or not 200 <= status < 300:
            raise LauncherError(f"GitHub CLI 실패: 종료 코드 {response.returncode}, HTTP {status}. 자동 재시도하지 않습니다.")
        if binary:
            return raw
        try:
            result=json.loads(raw)
        except ValueError as exc:
            raise LauncherError("GitHub CLI 응답 JSON 오류") from exc
        if self.runner is None and method=='POST' and endpoint==PREFIX+'/releases':
            if (type(result.get('id')) is not int or result['id']<=0 or result.get('draft') is not True
                    or result.get('tag_name')!=self.draft_grant.tag):
                raise LauncherError("새 Draft 응답 확인 실패. 실제 원격 상태를 확인하세요.")
            self._owned_draft_id=result['id']
        return result


@dataclass(frozen=True)
class BundleAsset:
    name: str
    path: Path
    size: int
    sha256: str


class GitHubPublication:
    def __init__(self, session: AdminSession, transport: GhCliTransport):
        self.session, self.transport = session, transport
        self.phase = 'empty'
        self.draft_id = None
        self.assets = ()
        self.events = []
        self.publication_uncertain = False

    def _step(self, name, action):
        try:
            result=action()
            self.events.append({'phase':name,'success':True})
            self._record()
            return result
        except Exception as exc:
            self.phase='failed'
            self.events.append({'phase':name,'success':False,'error_type':type(exc).__name__})
            log_error = ""
            try:
                self._record()
            except Exception:
                log_error = " 상태 로그 저장도 실패했습니다. 작업 폴더를 보존하세요."
            warning = ("공개 요청이 반영됐을 수 있습니다. 실제 Release 상태를 확인하세요. "
                       if self.publication_uncertain else "초안·작업 파일을 보존합니다. ")
            raise LauncherError(f"{name} 실패. {warning}자동 재시도·삭제하지 않습니다. "
                                + self.session.safe_error(exc) + log_error) from exc

    def _record(self):
        if hasattr(self,'work'):
            atomic_json(self.work/'publication-state.json',{'repository':REPOSITORY,'tag':getattr(self,'tag',None),
                'draft_id':self.draft_id,'phase':self.phase,'dry_run':self.transport.dry_run,
                'publication_uncertain':self.publication_uncertain,
                'events':self.events,'cli_calls':self.transport.calls})

    def _permit(self):
        if not self.session.test_mode:
            raise LauncherError("운영 키·실제 게시 권한 미승인: 격리 더미만 허용합니다.")
        if not self.transport.dry_run:
            grant=self.transport.draft_grant
            if (grant is None or self.session.root!=grant.root.resolve()
                    or self.session.app_names!={'dummy':'Dummy Tool'}
                    or set(self.session.policy['keys'])!={grant.key_id}):
                raise LauncherError("운영 키·실제 게시 권한 미승인: 승인된 Dummy Draft 시험만 허용합니다.")

    def prepare(self, review: Review):
        self._permit()
        if self.phase != 'empty':
            raise LauncherError("기존 게시 작업은 덮어쓰지 않습니다.")
        def action():
            if self.session.review(review.inspection,str(review.sequence),review.key_path,True)!=review:
                raise LauncherError("최종 확인한 게시 정보가 다릅니다.")
            self.review=review
            if not self.transport.dry_run:
                grant=self.transport.draft_grant
                if (review.sequence!=grant.sequence or review.key_id!=grant.key_id
                        or review.inspection.app.app_id!='dummy'
                        or review.inspection.app.release_id!=grant.release_id
                        or review.inspection.app.sha256!=grant.package_sha256):
                    raise LauncherError("승인된 시험 릴리스·순번·키·ZIP 해시가 아닙니다.")
            work=self.session.root.parent/'github-plans'/uuid.uuid4().hex
            work.mkdir(parents=True,exist_ok=False)
            self.work=work
            root=work/'repository';root.mkdir();(root/'packages').mkdir()
            for name in ('admin-gui-test.json','TEST_ONLY_TRUST.json'):
                shutil.copyfile(self.session.root.parent/name,work/name)
            for name in ('catalog.json','catalog.sig.json'):
                shutil.copyfile(self.session.root/name,root/name)
            for app in self.session.state().apps:
                if app.published:
                    source=self.session.root/'packages'/app.package_name
                    if app.sha256 not in self.session.allowed_packages or digest(source)!=app.sha256:
                        raise LauncherError("기존 게시 ZIP은 검증된 더미 원본이어야 합니다.")
                    shutil.copyfile(source,root/'packages'/app.package_name)
            staged=AdminSession(root,test_mode=True)
            checked=staged.review(review.inspection,str(review.sequence),review.key_path,True)
            state=staged.publish(checked)  # Reuse the existing engine; original repository stays intact.
            self.directory=work/'assets';self.directory.mkdir()
            names=['catalog.json','catalog.sig.json']
            for app in state.apps:
                if app.published:
                    if app.app_id=='tag-master' or app.sha256 not in staged.allowed_packages:
                        raise LauncherError("실제 프로그램 또는 잠긴 앱은 시험 묶음에 포함할 수 없습니다.")
                    extract_checked(root/'packages'/app.package_name,work/'preflight'/app.app_id,app)
                    names.append(app.package_name)
            if len(names)!=len(set(names)):
                raise LauncherError("중복된 묶음 자산 이름")
            for name in names:
                source=root/name if name in names[:2] else root/'packages'/name
                shutil.copyfile(source,self.directory/name)
            self.assets=tuple(BundleAsset(p.name,p,p.stat().st_size,digest(p)) for p in sorted(self.directory.iterdir()))
            self.tag=f'catalog-{review.sequence:06d}'
            self.phase='prepared'
            self._ensure()
            if not self.transport.dry_run:
                self.transport.bind_bundle(self.session.root,self.tag,self.assets)
            return self
        return self._step('서명 묶음 준비',action)

    def _ensure(self):
        self._permit()
        self.session.review(self.review.inspection,str(self.review.sequence),self.review.key_path,True)
        if {p.name for p in self.directory.iterdir()}!={a.name for a in self.assets}:
            raise LauncherError("묶음 파일 목록 변경")
        for asset in self.assets:
            if asset.path.is_symlink() or asset.path.stat().st_size!=asset.size or digest(asset.path)!=asset.sha256:
                raise LauncherError("준비 후 자산 변경")
        verifier=CatalogVerifier(self.session.policy,self.work/'unused-trust.json')
        doc,apps=verifier.verify((self.directory/'catalog.json').read_bytes(),(self.directory/'catalog.sig.json').read_bytes())
        if doc['sequence']!=self.review.sequence:
            raise LauncherError("서명 순번 변경")
        return verifier,apps

    def create_draft(self, confirmed: bool):
        self._permit()
        if not confirmed or self.phase!='prepared':
            raise LauncherError("초안 생성 확인과 준비된 묶음이 필요합니다.")
        def action():
            self._ensure()
            if self.transport.request('GET','user').get('login')!='toast-source':
                raise LauncherError("toast-source 인증 계정이 아닙니다.")
            releases=self.transport.request('GET',PREFIX+'/releases?per_page=100')
            if not isinstance(releases,list) or len(releases)>=100:
                raise LauncherError("Release 목록을 완전히 확인할 수 없습니다.")
            if any(r.get('tag_name')==self.tag for r in releases):
                raise LauncherError("동일 Release가 이미 존재합니다. 덮어쓰지 않습니다.")
            draft=self.transport.request('POST',PREFIX+'/releases',payload={
                'tag_name':self.tag,'target_commitish':'main','name':self.tag,
                'body':self.review.inspection.app.release_notes,'draft':True,'prerelease':False,'make_latest':'false'})
            if (type(draft.get('id')) is not int or draft['id']<=0 or draft.get('draft') is not True
                    or draft.get('tag_name')!=self.tag):
                raise LauncherError("실제 초안 응답 확인 실패")
            self.draft_id=draft['id'];self.phase='draft'
            return draft
        return self._step('초안 생성',action)

    def _remote(self):
        draft=self.transport.request('GET',PREFIX+f'/releases/{self.draft_id}')
        if draft.get('tag_name')!=self.tag or draft.get('draft') is not True:
            raise LauncherError("확인한 초안 상태가 아닙니다.")
        return draft

    def upload(self):
        if self.phase!='draft':raise LauncherError("빈 초안 생성 후 업로드하세요.")
        def action():
            self._ensure()
            if self._remote().get('assets'):
                raise LauncherError("초안에 자산이 이미 있습니다. 덮어쓰지 않습니다.")
            for asset in self.assets:
                endpoint=f'https://uploads.github.com/{PREFIX}/releases/{self.draft_id}/assets?name='+quote(asset.name,safe='')
                uploaded=self.transport.request('POST',endpoint,source=asset.path)
                if uploaded.get('name')!=asset.name or uploaded.get('size')!=asset.size:
                    raise LauncherError("업로드 응답 이름·크기 불일치")
            self.phase='uploaded'
        return self._step('자산 업로드',action)

    def _remote_assets(self):
        assets=self._remote().get('assets',[])
        by_name={a['name']:a for a in assets}
        if len(assets)!=len(by_name) or set(by_name)!={a.name for a in self.assets}:
            raise LauncherError("원격 자산 목록 불일치")
        for item in self.assets:
            asset=by_name[item.name]
            if (type(asset.get('id')) is not int or asset['id']<=0
                    or asset.get('state')!='uploaded' or asset.get('size')!=item.size
                    or asset.get('digest') not in (None,'sha256:'+item.sha256)):
                raise LauncherError("원격 자산 크기·해시 불일치")
        if len({a['id'] for a in assets})!=len(assets):
            raise LauncherError("중복된 원격 자산 ID")
        return by_name

    def verify(self):
        if self.phase!='uploaded':raise LauncherError("업로드 후 재다운로드 검증하세요.")
        def action():
            verifier,apps=self._ensure();assets=self._remote_assets()
            download=self.work/'redownload';download.mkdir(exist_ok=False)
            for item in self.assets:
                raw=self.transport.request('GET',PREFIX+f"/releases/assets/{assets[item.name]['id']}",binary=True)
                path=download/item.name;path.write_bytes(raw)
                if len(raw)!=item.size or digest(path)!=item.sha256:
                    raise LauncherError("재다운로드 SHA-256·크기 불일치")
            verifier.verify((download/'catalog.json').read_bytes(),(download/'catalog.sig.json').read_bytes())
            for app in apps:
                if app.published:
                    extract_checked(download/app.package_name,self.work/'audit'/app.app_id,app)
            self.verified_ids={name:asset['id'] for name,asset in assets.items()}
            self.phase='verified'
        return self._step('재다운로드·서명 검증',action)

    def publish(self, confirmed: bool):
        if not self.transport.dry_run:
            raise LauncherError("실제 정식 공개·Latest 지정은 승인되지 않았습니다. Draft만 허용합니다.")
        self._permit()
        if not confirmed or self.phase!='verified':
            raise LauncherError("검증 완료 후 별도 공개 확인이 필요합니다.")
        def action():
            self._ensure();assets=self._remote_assets()
            if {name:a['id'] for name,a in assets.items()}!=self.verified_ids:
                raise LauncherError("검증 후 자산 ID 변경")
            self.publication_uncertain=True
            result=self.transport.request('PATCH',PREFIX+f'/releases/{self.draft_id}',
                                          payload={'draft':False,'make_latest':'true'})
            latest=self.transport.request('GET',PREFIX+'/releases/latest')
            if result.get('draft') is not False or latest.get('id')!=self.draft_id:
                raise LauncherError("공개 응답·Latest 검증 실패")
            self.phase='published'
            self.publication_uncertain=False
            return result
        return self._step('최종 공개',action)
