"""Self-update foundation, deliberately restricted to isolated dummy homes."""
from __future__ import annotations

from .bootstrap_diagnostics import call, diagnosed

import base64
from contextlib import contextmanager, ExitStack
from pathlib import Path
import re
import secrets
import subprocess
import sys
import uuid

from .archive import check_cancel
from .catalog import AppRelease
from .catalog_trust import CatalogVerifier, strict_json
from .common import LauncherError, app_lock, atomic_json, digest, inside, plain_tree, read_json, utc_now
from .installer import Installer
from .paths import AppPaths
from .providers import HttpProvider
from .github_provider import GitHubReleasesProvider

PROJECT = Path(__file__).resolve().parents[1]
APP_ID = "creative-group-launcher"
MANIFEST = "launcher-package.json"
PURPOSE = "creative-group-launcher-self-update-dummy-v1"
MANAGED_PURPOSE = "creative-group-launcher-managed-v1"
TERMINAL = {"committed", "rolled_back", "cancelled", "preparation_failed"}
PHASES = TERMINAL | {"preparing", "prepared", "requested", "switching", "probing", "rollback_required"}


def version(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", value):
        raise LauncherError("자체 업데이트는 안정 버전 major.minor.patch만 지원합니다.")
    return tuple(map(int, value.split('.')))


def failure(exc):
    detail = str(exc) if isinstance(exc,LauncherError) else ""
    return f"{type(exc).__name__} (WinError={getattr(exc, 'winerror', None)}): {detail}"


def test_path(path: Path) -> Path:
    path = path.resolve()
    base = (PROJECT / ".test-results").resolve()
    if not path.is_relative_to(base) or path == base:
        raise LauncherError("이번 자체 업데이트 기반은 .test-results의 격리 경로에서만 사용할 수 있습니다.")
    return path


class LauncherInstaller(Installer):
    """Prepare an immutable new launcher release while its predecessor runs."""

    def _installation_running(self, app):
        if app.app_id != APP_ID:
            raise LauncherError("런처 전용 준비 저장소입니다.")
        return self.processes.is_running(self.paths.release(APP_ID, app.release_id))


class SelfUpdater:
    def __init__(self, home: Path, *, channel=None):
        self.channel = channel
        self.home = home.resolve() if channel else test_path(home)
        layout = read_json(inside(self.home, "layout.json"))
        if layout.get("purpose") != (MANAGED_PURPOSE if channel else PURPOSE) or layout.get("schema_version") != 1:
            raise LauncherError("격리 더미 런처 표식이 없습니다. 운영 런처는 변경하지 않습니다.")
        self.data_root = Path(layout["user_data_root"]).resolve() if channel else test_path(Path(layout["user_data_root"]))
        if self.data_root.is_relative_to(self.home) or self.home.is_relative_to(self.data_root):
            raise LauncherError("런처 프로그램과 사용자 데이터 경로가 겹칩니다.")
        self.policy = channel["policy"] if channel else strict_json(inside(self.home, "test-public-policy.json").read_bytes())
        self.verifier = CatalogVerifier(self.policy, inside(self.home, "catalog-trust.json"))
        # Bootstrap retains its releases and does not expose employee app removal.
        self.engine = LauncherInstaller(AppPaths(inside(self.home, "store")), plan_uninstall=False)

    @classmethod
    def create(cls, home: Path, data_root: Path, policy: dict):
        home, data_root = test_path(home), test_path(data_root)
        if home.exists() or not data_root.is_dir():
            raise LauncherError("새 프로그램 폴더와 별도의 기존 시험 데이터 폴더가 필요합니다.")
        if data_root.is_relative_to(home) or home.is_relative_to(data_root):
            raise LauncherError("프로그램과 사용자 데이터 폴더를 분리하세요.")
        CatalogVerifier(policy, home / "catalog-trust.json")
        home.mkdir(parents=True)
        atomic_json(home / "layout.json", {"schema_version":1, "purpose":PURPOSE,
                                          "user_data_root":str(data_root)})
        atomic_json(home / "test-public-policy.json", policy)
        return cls(home)

    def _lock(self):
        return app_lock(inside(self.home, "locks/update.lock"))

    def _runtime_lock(self):
        return app_lock(inside(self.home, "locks/running.lock"))

    def _provider(self, provider):
        expected = GitHubReleasesProvider if self.channel else HttpProvider
        if (not isinstance(provider, expected)
                or self.channel and provider.repository != self.channel["repository"]
                or provider.verifier.policy != self.policy
                or provider.verifier.state_path.resolve() != self.verifier.state_path.resolve()):
            raise LauncherError("동일한 고정 서명 정책과 격리 신뢰 상태를 사용하는 HttpProvider가 필요합니다.")

    def _candidate(self, app):
        if (app.app_id != APP_ID or not app.published or app.preserve_paths
                or MANIFEST not in app.required_paths):
            raise LauncherError("런처 자체 업데이트 전용 패키지 정보가 아닙니다.")
        version(app.version)

    def _proof(self, app):
        proof = strict_json(self.verifier.state_path.read_bytes(), 6 * 1024 * 1024)
        self._check_proof(proof, app)
        return proof

    def _check_proof(self, proof, app):
        try:
            raw = base64.b64decode(proof["catalog"], validate=True)
            signature = base64.b64decode(proof["signature"], validate=True)
            _, apps = self.verifier.verify(raw, signature)
        except (ValueError, KeyError, TypeError) as exc:
            raise LauncherError("자체 업데이트 서명 증거 오류") from exc
        if app not in apps or app not in (self.verifier.cached() or []):
            raise LauncherError("준비한 런처가 최신 로컬 신뢰 상태의 서명 목록과 다릅니다.")

    def _validate_release(self, app):
        self._candidate(app)
        release = self.engine.paths.release(APP_ID, app.release_id)
        receipt = read_json(inside(release, "receipt.json"))
        if receipt.get("app") != app.to_dict():
            raise LauncherError("런처 설치 영수증과 릴리스 정보 불일치")
        if self.channel:
            proof = strict_json(call("catalog_proof_read", inside(release, "catalog-proof.json").read_bytes,
                                     target=inside(release, "catalog-proof.json"), api="Path.read_bytes"), 6 * 1024 * 1024)
            self.verifier.verify_installed_release(proof, app)
        payload = inside(release, "payload")
        files = {}
        for path in plain_tree(payload):
            if path.is_symlink() or path.is_junction():
                raise LauncherError("런처 파일에 링크/정션이 있습니다.")
            name = path.relative_to(payload).as_posix()
            inside(payload, name)
            if name.split('/')[0].casefold() in {'.git','apps','user-data','settings.json',
                    'current.json','transactions','distribution','catalog-trust.json'}:
                raise LauncherError("런처 프로그램 영역에 사용자/관리 데이터가 포함됐습니다.")
            if path.is_file():
                files[name] = digest(path)
        manifest = strict_json(call("manifest_read", inside(payload, MANIFEST).read_bytes,
                                    target=inside(payload, MANIFEST), api="Path.read_bytes"))
        if (set(manifest) != {"schema_version","app_id","release_id","version","files"}
                or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
                or manifest["app_id"] != APP_ID or manifest["release_id"] != app.release_id
                or manifest["version"] != app.version or not isinstance(manifest["files"], dict)):
            raise LauncherError("런처 패키지 manifest 오류")
        expected = {name:sha for name,sha in files.items() if name != MANIFEST}
        if (manifest["files"] != expected or receipt.get("files") != files
                or files.get(app.executable_relative_path) != app.executable_sha256):
            raise LauncherError("런처 파일 목록/해시가 manifest 또는 영수증과 다릅니다.")
        self.engine.resolve_launch(app)  # Only checks paths/hashes; never starts an EXE.
        return payload

    @diagnosed("current_verify")
    def current(self):
        app = AppRelease.parse(self._pointer()["app"])
        self._validate_release(app)
        return app

    def _pointer(self):
        value = strict_json(call("current_read", inside(self.home,"current.json").read_bytes,
                                 target=inside(self.home,"current.json"), api="Path.read_bytes"))
        if (set(value) != {"schema_version","app"} or type(value["schema_version"]) is not int
                or value["schema_version"] != 1):
            raise LauncherError("활성 포인터 형식이 예상과 다릅니다. 자동 덮어쓰지 않습니다.")
        return value

    def _point(self, app):
        self._validate_release(app)
        atomic_json(inside(self.home, "current.json"), {"schema_version":1,"app":app.to_dict()})

    def bootstrap(self, provider):
        """Initial dummy installation only; not an upgrade or production enrollment."""
        self._provider(provider)
        with self._lock():
            if inside(self.home, "current.json").exists():
                raise LauncherError("기존 런처 초기 설치를 덮어쓰지 않습니다.")
            apps = [a for a in provider.catalog() if a.app_id == APP_ID]
            if len(apps) != 1:
                raise LauncherError("서명된 런처 항목 한 개가 필요합니다.")
            app = apps[0]
            self._candidate(app)
            self._proof(app)
            self.engine.install(app, provider)
            if self.engine.warnings:
                raise LauncherError("초기 준비 경고를 확인하세요. 활성화하지 않았습니다.")
            self._point(app)
            return app

    def _journal_path(self, transaction):
        if not isinstance(transaction,str) or not re.fullmatch(r"[a-f0-9]{32}",transaction):
            raise LauncherError("자체 업데이트 트랜잭션 ID 오류")
        return inside(self.home, f"transactions/{transaction}.json")

    def journal(self, transaction):
        value = strict_json(self._journal_path(transaction).read_bytes(), 8 * 1024 * 1024)
        if value.get("id") != transaction or value.get("phase") not in PHASES:
            raise LauncherError("자체 업데이트 journal 손상 — 자동 초기화하지 않습니다.")
        for field in ("old","new"):
            self._candidate(AppRelease.parse(value[field]))
        return value

    def _phase(self, journal, phase, error=""):
        updated = {**journal,"phase":phase,"error":error,"updated_at":utc_now()}
        atomic_json(self._journal_path(journal["id"]), updated)
        journal.update(updated)

    def _pending(self):
        folder = inside(self.home, "transactions")
        return [j for p in folder.glob('*.json') if (j:=self.journal(p.stem))["phase"] not in TERMINAL]

    def prepare(self, provider, cancel=None, *, expected=None):
        self._provider(provider)
        with self._lock():
            if self._pending():
                raise LauncherError("기존 자체 업데이트를 확인/복구/취소한 후 다시 준비하세요.")
            old = self.current()
            matches = [a for a in provider.catalog() if a.app_id == APP_ID]
            if len(matches) != 1:
                raise LauncherError("서명된 런처 항목 한 개가 필요합니다.")
            new = matches[0]
            self._candidate(new)
            if expected is not None and new != expected:
                raise LauncherError("확인한 런처 릴리스가 바뀌었습니다. 새로 조회하세요.")
            if self.channel and version(new.version) <= version(old.version):
                raise LauncherError("현재보다 높은 런처 버전만 적용할 수 있습니다.")
            if version(new.version) < version(old.version) or not new.is_new_release(old):
                raise LauncherError("이전 버전 또는 이미 설치된 런처 배포본은 적용하지 않습니다.")
            proof = self._proof(new)
            check_cancel(cancel)
            transaction = uuid.uuid4().hex
            journal = {"id":transaction,"phase":"preparing","old":old.to_dict(),
                       "new":new.to_dict(),"proof":proof,"nonce":secrets.token_hex(32),"error":"",
                       "created_at":utc_now()}
            atomic_json(self._journal_path(transaction), journal)
            try:
                if self.engine.pending_recovery(APP_ID):
                    raise LauncherError("내부 준비 저장소 복구가 필요합니다.")
                target = self.engine.paths.release(APP_ID,new.release_id)
                if not target.exists():
                    if self.channel:
                        with provider.installation_session(new):
                            self.engine.install(new,provider,cancel=cancel)
                    else:
                        self.engine.install(new,provider,cancel=cancel)
                    if self.engine.warnings:
                        raise LauncherError("준비 중 경고가 발생했습니다. 상태를 보존하고 확인하세요.")
                self._validate_release(new)
                self._check_proof(proof,new)
                check_cancel(cancel)
                self._phase(journal,"prepared")
            except Exception as exc:
                self._phase(journal,"preparation_failed",type(exc).__name__)
                raise
            return transaction

    def request_apply(self, transaction, *, approved: bool):
        with self._lock():
            journal = self.journal(transaction)
            if journal["phase"] not in {"prepared","requested"}:
                raise LauncherError("적용 가능한 준비 상태가 아닙니다.")
            self._phase(journal,"requested" if approved else "cancelled")
            return approved

    def _rollback(self, journal, reason):
        old, new = AppRelease.parse(journal["old"]), AppRelease.parse(journal["new"])
        self._validate_release(old)
        pointer = self._pointer()
        if pointer.get("app") not in (old.to_dict(),new.to_dict()):
            raise LauncherError("예상 외 활성 포인터입니다. 자동 덮어쓰지 않습니다.")
        self._phase(journal,"rollback_required",reason)
        if pointer["app"] != old.to_dict():
            self._point(old)
        self._phase(journal,"rolled_back",reason)

    @diagnosed("recovery_transactions")
    def _recover_locked(self):
        if self.engine.pending_recovery(APP_ID):
            self.engine.recover(APP_ID)
        for journal in self._pending():
            if journal["phase"] == "preparing":
                self._phase(journal,"preparation_failed","interrupted preparation")
            elif journal["phase"] in {"switching","probing","rollback_required"}:
                self._rollback(journal,"interrupted activation")
            elif self.channel and journal["phase"] in {"prepared", "requested"}:
                self._phase(journal, "cancelled", "interrupted handoff")
        return self.current()

    @diagnosed("recovery_lock")
    def recover(self):
        with self._lock(), self._runtime_lock():
            return self._recover_locked()

    @contextmanager
    def running(self):
        # Stable bootstrap must hold this lease for the entire real launcher lifetime.
        with ExitStack() as stack:
            with self._lock():
                stack.enter_context(self._runtime_lock())
                app = self._recover_locked()
            yield app

    def _probe(self, transaction, result, timeout):
        if result not in {"ok","fail","bad-ack","timeout"} or not 0 < timeout <= 30:
            raise LauncherError("더미 시작 검사 인자 오류")
        # Trusted development probe, never executable code from a downloaded ZIP.
        command = [sys.executable,"-B","-m","southpaw_tools.self_update_worker","probe",
                   "--home",str(self.home),"--transaction",transaction,"--probe-result",result]
        process = subprocess.Popen(command,cwd=PROJECT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                   creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        try:
            process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            process.kill()  # Only the exact child Popen object created above.
            process.communicate(timeout=5)
            raise LauncherError("새 더미 런처 시작 확인 시간 초과") from exc
        if process.returncode != 0:
            raise LauncherError("새 더미 런처 시작 검사 실패")
        journal = self.journal(transaction)
        health = read_json(inside(self.home,f"health/{transaction}.json"))
        expected = {"transaction":transaction,"release_id":journal["new"]["release_id"],
                    "exe_sha256":journal["new"]["executable_sha256"],"nonce":journal["nonce"]}
        if health != expected:
            raise LauncherError("새 더미 런처 시작 확인 응답 불일치")

    def apply(self, transaction, *, probe_result="ok", timeout=5, _checkpoint=None):
        with self._lock(), self._runtime_lock():
            journal = self.journal(transaction)
            if journal["phase"] != "requested":
                raise LauncherError("사용자의 명시적 적용 확인이 필요합니다.")
            old,new = AppRelease.parse(journal["old"]),AppRelease.parse(journal["new"])
            if version(new.version) < version(old.version) or not new.is_new_release(old):
                raise LauncherError("journal의 이전 버전/동일 릴리스 적용을 거부합니다.")
            if self.current() != old:
                raise LauncherError("준비 후 활성 런처가 바뀌었습니다.")
            self._check_proof(journal["proof"],new)
            self._validate_release(new)
            try:
                self._phase(journal,"switching")
                if _checkpoint:
                    _checkpoint("switching")
                self._point(new)
                if _checkpoint:
                    _checkpoint("pointed")
                self._phase(journal,"probing")
                if _checkpoint:
                    _checkpoint("probing")
                self._probe(transaction,probe_result,timeout)
                self._phase(journal,"committed")
            except Exception as exc:
                try:
                    self._rollback(journal,journal["phase"] + ": " + failure(exc))
                except Exception as recovery:
                    raise LauncherError("자체 업데이트 복구 필요 — 이전/새 파일과 journal을 보존하세요. "
                                        + failure(recovery)) from exc
                raise LauncherError("자체 업데이트 실패 — 이전 런처로 복구했습니다. " + failure(exc)) from exc
            return new
