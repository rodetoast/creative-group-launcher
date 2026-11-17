"""Local admin GUI adapter. Publication remains in admin.publish."""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from pathlib import Path
import tempfile
import uuid
import zipfile

from . import admin
from .archive import checked_members, extract_checked, member_name
from .catalog import AppRelease, parse_catalog
from .catalog_trust import CatalogVerifier, key_id, load_private, strict_json
from .common import LauncherError, atomic_json, digest, utc_now

PROJECT = Path(__file__).resolve().parents[1]
APP_NAMES = {"tilenamer": "TileNamer", "ase-viewer": "ase_viewer",
             "tag-master": "AsepriteTagMaster", "ps2ase": "Ase-PS Bridge Pro",
             "pivot-fixer": "Pivot_Fixer"}
TEST_MARKER = "creative-group-launcher-admin-gui-dummy-v1"


@dataclass(frozen=True)
class RepositoryState:
    apps: tuple[AppRelease, ...]
    sequence: int
    catalog_sha256: str
    signature_ok: bool
    signature_message: str


@dataclass(frozen=True)
class Inspection:
    app: AppRelease
    source: Path
    members: tuple[str, ...]
    expanded_size: int
    catalog_sha256: str


@dataclass(frozen=True)
class Review:
    inspection: Inspection
    sequence: int
    key_path: Path
    key_id: str
    previous_release: str
    previous_version: str
    previous_sha256: str
    repository: Path


class AdminSession:
    def __init__(self, root: Path, *, test_mode: bool = False):
        self.root = root.resolve()
        self.test_mode = test_mode
        self.policy = None
        self.allowed_packages: set[str] = set()
        self.app_names = dict(APP_NAMES)
        if test_mode:
            parent = self.root.parent
            if (self.root.name != "repository" or
                    not parent.is_relative_to((PROJECT / ".test-results").resolve())):
                raise LauncherError("시험 게시는 프로젝트 .test-results 안의 전용 repository만 허용합니다.")
            marker = strict_json((parent / "admin-gui-test.json").read_bytes())
            if (marker.get("purpose") != TEST_MARKER or
                    not isinstance(marker.get("dummy_package_sha256"), list) or
                    any(not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}",value)
                        for value in marker.get("dummy_package_sha256", []))):
                raise LauncherError("더미 시험 저장소 표식이 없습니다.")
            self.allowed_packages = set(marker["dummy_package_sha256"])
            if marker.get("app_profile") == "github-dummy-v1":
                self.app_names = {"dummy": "Dummy Tool"}
            self.policy = strict_json((parent / "TEST_ONLY_TRUST.json").read_bytes())
            # Validate local test public policy without storing a trust state.
            CatalogVerifier(self.policy, parent / "unused-trust-state.json")

    def state(self) -> RepositoryState:
        raw = (self.root / "catalog.json").read_bytes()
        document = strict_json(raw)
        apps = tuple(parse_catalog(document))
        if any(app.app_id not in self.app_names for app in apps):
            raise LauncherError("관리자 GUI는 등록된 다섯 앱의 저장소만 지원합니다.")
        sequence = document.get("sequence", 0)
        if type(sequence) is not int or not 0 <= sequence <= 2**63 - 1:
            raise LauncherError("현재 카탈로그 순번 오류")
        verified, message = False, "미서명 또는 미승인 키 · 게시 잠금"
        try:
            verifier = (CatalogVerifier(self.policy, self.root.parent / "unused-trust-state.json")
                        if self.policy else CatalogVerifier.bundled(self.root.parent / "unused-trust-state.json"))
            verifier.verify(raw, (self.root / "catalog.sig.json").read_bytes())
            verified, message = True, "전자서명 검증 성공"
        except (LauncherError, OSError):
            pass
        return RepositoryState(apps, sequence, hashlib.sha256(raw).hexdigest(), verified, message)

    def inspect(self, source: Path, app_id: str, version: str, release_id: str,
                executable: str, notes: str) -> Inspection:
        if app_id not in self.app_names:
            raise LauncherError("등록된 앱을 선택하세요.")
        if app_id == "tag-master":
            raise LauncherError("AsepriteTagMaster는 원본 승인 ZIP 미확인으로 배포가 잠겨 있습니다.")
        state = self.state()
        old = next((a for a in state.apps if a.app_id == app_id), None)
        if old is None:
            raise LauncherError("현재 저장소에 등록되지 않은 앱입니다.")
        if not all(value.strip() for value in (version, release_id, executable)):
            raise LauncherError("표시 버전·릴리스 ID·EXE 상대 경로를 입력하세요.")
        if old.published and old.release_id == release_id:
            raise LauncherError("현재 게시된 릴리스 ID와 같습니다. 새 ID를 입력하세요.")
        source = source.resolve()
        if not source.is_file() or source.suffix.lower() != ".zip":
            raise LauncherError("관리자가 선택한 완성 ZIP 파일이 필요합니다.")
        source_hash = digest(source)
        if self.test_mode and source_hash not in self.allowed_packages:
            raise LauncherError("시험 모드에서는 전용 더미 ZIP만 게시할 수 있습니다.")
        try:
            with zipfile.ZipFile(source) as archive:
                members = checked_members(archive)
                selected = next((m for m in members if member_name(m) == executable and not m.is_dir()), None)
                if selected is None:
                    raise LauncherError("입력한 EXE 상대 경로가 ZIP에 없습니다.")
                h = hashlib.sha256()
                with archive.open(selected) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        h.update(chunk)
                app = AppRelease.parse(replace(old, version=version, release_id=release_id,
                    executable_relative_path=executable,
                    working_directory_relative_path=Path(executable).parent.as_posix(),
                    package_name=f"{app_id}--{release_id}.zip", package_size=source.stat().st_size,
                    sha256=source_hash, executable_sha256=h.hexdigest(), release_notes=notes,
                    published=True, published_at=utc_now(), availability_reason="", build_id="").to_dict())
                names = tuple(member_name(m) for m in members)
                expanded = sum(m.file_size for m in members)
            work = PROJECT / ".test-results/admin-gui-inspections"
            work.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="read-only-zip-", dir=work) as folder:
                # Reuse every existing CRC/path/size/MZ/resource check. Never run the payload.
                extract_checked(source, Path(folder) / "payload", app)
            if digest(source) != source_hash:
                raise LauncherError("검사 도중 원본 ZIP이 바뀌었습니다. 게시하지 않습니다.")
            if (self.root / "packages" / app.package_name).exists():
                raise LauncherError("동일한 릴리스 패키지가 이미 있습니다. 덮어쓰지 않습니다.")
            return Inspection(app, source, names, expanded, state.catalog_sha256)
        except (zipfile.BadZipFile, RuntimeError, OSError, NotImplementedError) as exc:
            raise LauncherError("ZIP 검사 실패 — 손상·지원하지 않는 구조 또는 읽기 오류입니다.") from exc

    def review(self, inspection: Inspection, sequence_text: str, key_path: Path | None,
               approved_zip: bool) -> Review:
        if not self.test_mode:
            raise LauncherError("운영 키 미채택 상태입니다. 실제 운영 게시는 잠겨 있습니다.")
        if not approved_zip:
            raise LauncherError("선택한 파일이 승인된 완성 ZIP인지 확인하세요.")
        if inspection.app.app_id == "tag-master" or inspection.app.sha256 not in self.allowed_packages:
            raise LauncherError("시험용 더미 게시 대상이 아닙니다.")
        state = self.state()
        if not state.signature_ok:
            raise LauncherError("현재 카탈로그 서명 검증 실패 — 중간 게시 실패 여부를 확인하세요.")
        if state.catalog_sha256 != inspection.catalog_sha256:
            raise LauncherError("검사 후 카탈로그가 바뀌었습니다. 검사 결과를 갱신하세요.")
        try:
            sequence = int(sequence_text)
        except ValueError as exc:
            raise LauncherError("새 순번은 정수로 입력하세요.") from exc
        if not state.sequence < sequence <= 2**63 - 1:
            raise LauncherError("새 순번은 현재보다 큰 양의 63비트 정수여야 합니다.")
        if key_path is None or not key_path.is_file():
            raise LauncherError("외부 서명 개인키 파일을 선택하세요.")
        if key_path.resolve().is_relative_to(self.root):
            raise LauncherError("공개 저장소 내부 개인키는 사용할 수 없습니다.")
        key = load_private(key_path)
        identity = key_id(key.public_key().public_bytes_raw())
        if identity not in self.policy["keys"]:
            raise LauncherError("선택한 개인키가 이 격리 시험 저장소의 공개키와 다릅니다.")
        if digest(inspection.source) != inspection.app.sha256:
            raise LauncherError("검사 후 ZIP이 변경됐습니다. 게시하지 않습니다.")
        previous = next(a for a in state.apps if a.app_id == inspection.app.app_id)
        return Review(inspection, sequence, key_path, identity, previous.release_id,
                      previous.version, previous.sha256, self.root)

    def publish(self, review: Review) -> RepositoryState:
        if review.repository != self.root:
            raise LauncherError("최종 확인한 저장소와 현재 게시 대상이 다릅니다.")
        # Recheck after the final dialog; the engine rechecks key/sequence/ZIP again under its lock.
        if self.review(review.inspection, str(review.sequence), review.key_path, True) != review:
            raise LauncherError("최종 확인 후 서명키 또는 게시 정보가 바뀌었습니다. 다시 확인하세요.")
        item = review.inspection.app
        phase = "게시 엔진 호출"
        try:
            result = admin.publish(self.root, item.app_id, review.inspection.source,
                version=item.version, release_id=item.release_id,
                executable=item.executable_relative_path, expected_sha256=item.sha256,
                expected_exe_sha256=item.executable_sha256, approved=True,
                cwd=item.working_directory_relative_path, notes=item.release_notes,
                signing_key=review.key_path, sequence=review.sequence)
            phase = "게시 후 서명·카탈로그 확인"
            state = self.state()
            current = next(a for a in state.apps if a.app_id == item.app_id)
            if not state.signature_ok or state.sequence != review.sequence or current != result:
                raise LauncherError("게시 후 서명 또는 실제 카탈로그가 예상 결과와 다릅니다.")
            if any(current.to_dict()[name] != value for name,value in item.to_dict().items()
                   if name != "published_at"):
                raise LauncherError("최종 확인 내용과 실제 게시 메타데이터가 다릅니다.")
            if digest(self.root / "packages" / result.package_name) != result.sha256:
                raise LauncherError("게시 후 실제 패키지 해시가 다릅니다.")
            self.record(phase, "성공", review)
            return state
        except Exception as exc:
            extra = ""
            try:
                self.record(phase, "실패", review, exc)
            except Exception:
                extra = " 결과 로그 저장도 실패했습니다. 화면 오류와 실제 카탈로그 상태를 보존하세요."
            raise LauncherError(f"{phase} 실패. 서명/카탈로그/패키지 상태를 확인하세요. 자동 재시도·삭제·롤백하지 않습니다. {self.safe_error(exc, review)}{extra}") from exc

    def safe_error(self, exc, review: Review | None = None):
        text = str(exc)
        paths = [self.root, Path.home()]
        if review:
            paths += [review.key_path, review.inspection.source]
        for path in sorted(paths, key=lambda p: len(str(p)), reverse=True):
            text = text.replace(str(path), "[로컬 경로]").replace(str(path).replace('\\', '\\\\'), "[로컬 경로]")
        return text[:1500]

    def record(self, phase, outcome, review, exc=None):
        # Test logs are outside the public repository. No key path/content/token is stored.
        folder = self.root.parent / "gui-logs"
        atomic_json(folder / f"{uuid.uuid4().hex}.json", {
            "phase": phase, "outcome": outcome, "at": utc_now(),
            "app_id": review.inspection.app.app_id, "release_id": review.inspection.app.release_id,
            "sequence": review.sequence, "error_type": type(exc).__name__ if exc else "",
            "error": self.safe_error(exc, review) if exc else ""})
