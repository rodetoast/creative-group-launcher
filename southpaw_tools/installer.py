from __future__ import annotations

import shutil
import threading
import uuid
import logging
import re
import json
from pathlib import Path

from .archive import check_cancel, extract_checked
from .catalog import AppRelease
from .common import LauncherError, app_lock, atomic_json, digest, inside, plain_tree, read_json, relative_path, utc_now
from .paths import AppPaths
from .processes import Processes
from .providers import Provider


class Installer:
    def __init__(self, paths: AppPaths, processes: Processes | None = None):
        self.paths = paths
        self.processes = processes or Processes()
        self.warnings: list[str] = []
        self.download_verified = False

    def installed(self, app_id: str) -> AppRelease | None:
        pointer = self.paths.app(app_id) / "active.json"
        if not pointer.exists():
            return None
        data = read_json(pointer)
        app = AppRelease.parse(data.get("app", {}))
        if app.app_id != app_id or not app.published:
            raise LauncherError("설치 상태의 프로그램 식별자가 다릅니다.")
        return app

    def installed_apps(self) -> list[AppRelease]:
        root = self.paths.root / "apps"
        result = []
        if root.exists():
            for directory in root.iterdir():
                if directory.is_dir() and (directory / "active.json").is_file():
                    app = self.installed(directory.name)
                    if app:
                        result.append(app)
        return result

    def resolve_launch(self, app: AppRelease) -> tuple[Path, Path]:
        payload = inside(self.paths.release(app.app_id, app.release_id), "payload")
        exe = inside(payload, app.executable_relative_path)
        cwd = inside(payload, app.working_directory_relative_path, allow_dot=True)
        if not exe.is_file() or not cwd.is_dir():
            raise LauncherError("설치된 실행 파일이 없습니다. 설치 상태를 확인하세요.")
        try:
            actual_hash = digest(exe)
        except OSError as exc:
            raise LauncherError(f"로컬 EXE 확인 실패: {exc}") from exc
        if actual_hash != app.executable_sha256:
            raise LauncherError("설치된 EXE가 변경되어 실행을 보류합니다. 파일을 보존하고 확인하세요.")
        for required in app.required_paths:
            if not inside(payload, required).exists():
                raise LauncherError(f"설치 리소스가 없습니다: {required}")
        return exe, cwd

    def is_running(self, app_id: str) -> bool:
        return self.processes.is_running(self.paths.app(app_id))

    def pending_recovery(self, app_id: str) -> bool:
        journals = inside(self.paths.app(app_id), "transactions")
        if not journals.exists():
            return False
        for path in journals.glob("*.json"):
            try:
                if read_json(path).get("phase") not in {"activated", "failed", "uninstalled", "removal_restored"}:
                    return True
            except LauncherError:
                return True
        return False

    def recover(self, app_id: str):
        """Explicit offline recovery, serialized with all other app operations."""
        with app_lock(self.paths.lock(app_id)):
            self.warnings.clear()
            self._recover(app_id)
            return self.installed(app_id)

    def launch(self, app_id: str):
        with app_lock(self.paths.lock(app_id)):
            self.warnings.clear()
            self._recover(app_id)
            app = self.installed(app_id)
            if not app:
                raise LauncherError("설치된 프로그램이 없습니다.")
            if self.is_running(app_id):
                raise LauncherError("이미 실행 중입니다.")
            exe, cwd = self.resolve_launch(app)
            return self.processes.start(exe, cwd)

    def install(self, app: AppRelease, provider: Provider, progress=lambda done, total: None,
                cancel: threading.Event | None = None) -> AppRelease:
        # Validate again at the engine boundary, not only in the UI.
        app = AppRelease.parse(app.to_dict())
        if not app.published:
            raise LauncherError("배포 패키지 미확인")
        with app_lock(self.paths.lock(app.app_id)):
            self.warnings.clear()
            self.download_verified = False
            self._recover(app.app_id)
            old = self.installed(app.app_id)
            if self.is_running(app.app_id):
                raise LauncherError("실행 중인 프로그램의 설치/업데이트는 보류합니다.")
            repair = False
            if old and not app.is_new_release(old):
                try:
                    self.resolve_launch(old)
                except LauncherError:
                    # Repair uses the installed metadata, not conflicting remote fields.
                    if app != old:
                        raise LauncherError("복구 패키지 정보가 설치 기록과 다릅니다.")
                    repair = True
                if not repair:
                    raise LauncherError("이미 같은 승인 배포본이 설치되어 있습니다.")
            target = self.paths.release(app.app_id, app.release_id)
            if target.exists() and not repair:
                raise LauncherError("해당 release_id 폴더가 이미 있습니다. 기존 파일은 덮어쓰지 않습니다.")
            transaction_id = uuid.uuid4().hex
            stage = inside(self.paths.root, f"staging/{transaction_id}")
            package = inside(self.paths.downloads, f"{transaction_id}.zip")
            journal = self._new_journal(app, "install", transaction_id, repair=repair)
            try:
                provider.download(app, package, progress, cancel)
                check_cancel(cancel)
                if package.stat().st_size != app.package_size or digest(package) != app.sha256:
                    raise LauncherError("배포 패키지 크기 또는 SHA-256 불일치")
                self.download_verified = True
                self._phase(journal, "download_verified")
                self._phase(journal, "preparing")
                stage.mkdir(parents=True, exist_ok=False)
                files = extract_checked(package, stage / "payload", app, cancel)
                if old:
                    self._migrate_known_data(old, app, stage / "payload", cancel)
                atomic_json(stage / "receipt.json", {
                    "schema_version": 1, "app": app.to_dict(), "installed_at": utc_now(),
                    "files": files, "transaction_id": transaction_id,
                })
                self._phase(journal, "ready")
                check_cancel(cancel)
                if self.is_running(app.app_id):
                    raise LauncherError("프로그램이 실행되어 업데이트 전환을 보류합니다.")
                target.parent.mkdir(parents=True, exist_ok=True)
                self._phase(journal, "switching")
                if repair and target.exists():
                    backup = self._quarantine(journal) / "previous-release"
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    target.rename(backup)
                    self._warn(app.app_id, f"이전 설치와 미등록 작업 파일 보존: {backup}")
                stage.rename(target)
                check_cancel(cancel)
                self._phase(journal, "activating")
                self._activate(app)
                # Read back both pointer and payload before reporting success.
                if self.installed(app.app_id) != app:
                    raise LauncherError("활성 버전 확인 실패 — 복구가 필요합니다.")
                self.resolve_launch(app)
                self._phase(journal, "activated")
                self._finish(journal)
                return app
            except Exception as exc:
                try:
                    committed = self._recover_install(journal)
                except Exception as recovery:
                    self._recovery_error(journal, recovery)
                    raise LauncherError(f"설치 복구 필요: {recovery}") from exc
                if committed:
                    self._warn(app.app_id, f"활성화 확인 완료. 사후 처리 경고: {exc}")
                    return app
                if isinstance(exc, LauncherError):
                    raise
                raise LauncherError(f"설치 실패 — 기존 버전 유지: {exc}") from exc

    def _activate(self, app: AppRelease) -> None:
        atomic_json(self.paths.app(app.app_id) / "active.json", {
            "schema_version": 1, "app": app.to_dict(), "activated_at": utc_now(),
        })

    def _migrate_known_data(self, old: AppRelease, new: AppRelease, payload: Path,
                            cancel: threading.Event | None):
        old_payload = inside(self.paths.release(old.app_id, old.release_id), "payload")
        old_cwd = inside(old_payload, old.working_directory_relative_path, allow_dot=True)
        new_cwd = inside(payload, new.working_directory_relative_path, allow_dot=True)
        if not old_cwd.exists():
            return
        # Only explicitly declared mutable data migrates. Unknown edits remain in the
        # intact previous release. Executables, DLLs and arbitrary code never migrate.
        allowed = set(old.preserve_paths) & set(new.preserve_paths)
        for relative in sorted(allowed):
            source = inside(old_cwd, relative)
            destination = inside(new_cwd, relative)
            if not source.exists():
                continue
            candidates = sorted(plain_tree(source)) if source.is_dir() else [source]
            for candidate in candidates:
                check_cancel(cancel)
                if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
                    raise LauncherError("사용자 데이터의 링크/정션은 자동 이전하지 않습니다.")
                if candidate.is_dir():
                    continue
                if candidate.suffix.lower() in {".exe", ".dll", ".py", ".pyw", ".bat", ".cmd", ".ps1", ".lua", ".jsx"}:
                    continue
                suffix = candidate.relative_to(source) if source.is_dir() else None
                output = inside(destination, suffix.as_posix()) if suffix else destination
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, output)

    def _journal_path(self, journal: dict) -> Path:
        app = AppRelease.parse(journal["app"])
        tx = journal.get("id", "")
        if not isinstance(tx, str) or not re.fullmatch(r"[a-f0-9]{32}", tx):
            raise LauncherError("복구 작업 식별자가 잘못되었습니다.")
        return inside(self.paths.app(app.app_id), f"transactions/{tx}.json")

    def _new_journal(self, app, kind, tx, **extra):
        pointer = self.paths.app(app.app_id) / "active.json"
        journal = {"schema_version": 1, "id": tx, "kind": kind,
                   "app": app.to_dict(), "previous_pointer": read_json(pointer) if pointer.exists() else None,
                   "phase": "downloading" if kind == "install" else "preparing_removal", **extra}
        self._phase(journal, journal["phase"])
        return journal

    def _phase(self, journal, phase):
        journal["phase"] = phase
        journal["updated_at"] = utc_now()
        if len(json.dumps(journal, ensure_ascii=False, indent=2).encode("utf-8")) + 1 > 4 * 1024 * 1024:
            raise LauncherError("복구 기록이 읽기 제한을 초과합니다. 원본 파일을 변경하지 않습니다.")
        atomic_json(self._journal_path(journal), journal)

    def _quarantine(self, journal):
        app = AppRelease.parse(journal["app"])
        self._journal_path(journal)  # Validate the ID before composing any path.
        return inside(self.paths.app(app.app_id), f"recovery/{journal['id']}")

    def _warn(self, app_id, message):
        self.warnings.append(message)
        logging.getLogger(__name__).warning("%s: %s", app_id, message)
        try:
            log = inside(self.paths.app(app_id), "recovery-warnings.log")
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a", encoding="utf-8") as output:
                output.write(f"{utc_now()} {message}\n")
        except (OSError, LauncherError):
            # An unwritable log must not change the verified commit result.
            pass

    def _recovery_error(self, journal, error):
        app = AppRelease.parse(journal["app"])
        self._warn(app.app_id, f"복구 필요; 파일과 작업 기록 보존: {error}")
        try:
            self._phase(journal, "recovery_required")
        except (OSError, LauncherError):
            pass

    def _finish(self, journal):
        """Best-effort post-commit cleanup; journal remains as a retry queue."""
        app = AppRelease.parse(journal["app"])
        try:
            if journal["kind"] == "install":
                inside(self.paths.downloads, f"{journal['id']}.zip").unlink(missing_ok=True)
            self._journal_path(journal).unlink(missing_ok=True)
        except (OSError, LauncherError) as exc:
            self._warn(app.app_id, f"작업 완료; 임시 파일 정리 보류(다음 작업에서 재시도): {exc}")

    def _owned_release(self, target, journal):
        try:
            receipt = read_json(inside(target, "receipt.json"))
        except LauncherError:
            return False
        return (receipt.get("transaction_id") == journal["id"]
                and receipt.get("app") == journal["app"])

    def _recover_install(self, journal):
        app = AppRelease.parse(journal["app"])
        target = self.paths.release(app.app_id, app.release_id)
        previous = journal.get("previous_pointer")
        old = AppRelease.parse(previous["app"]) if previous else None
        if old and old.app_id != app.app_id:
            raise LauncherError("복구 기록의 이전 프로그램 식별자가 다릅니다.")
        try:
            current = self.installed(app.app_id)
        except LauncherError:
            if not old:
                raise
            self.resolve_launch(old)
            atomic_json(self.paths.app(app.app_id) / "active.json", previous)
            current = old
        # Equality alone is insufficient for same-release repairs: require our receipt.
        if current == app and target.exists() and self._owned_release(target, journal):
            try:
                self.resolve_launch(app)
            except LauncherError:
                if not old or old == app:
                    raise
                self.resolve_launch(old)
                atomic_json(self.paths.app(app.app_id) / "active.json", previous)
                current = old
            else:
                try:
                    self._phase(journal, "activated")
                except (OSError, LauncherError) as exc:
                    self._warn(app.app_id, f"활성 포인터와 EXE 확인 완료; 완료 기록 저장 경고: {exc}")
                self._finish(journal)
                return True
        if current != old:
            raise LauncherError("활성 포인터가 작업 전/후 상태와 다릅니다. 자동 변경하지 않습니다.")
        if journal["phase"] not in {"failed", "activated"}:
            quarantine = self._quarantine(journal)
            previous_release = inside(quarantine, "previous-release")
            if target.exists():
                # Never move a pre-existing normal release or unknown directory.
                if self._owned_release(target, journal):
                    quarantine.mkdir(parents=True, exist_ok=True)
                    target.rename(inside(quarantine, "aborted-release"))
                elif not journal.get("repair"):
                    raise LauncherError("작업 소유권을 확인할 수 없는 release 폴더를 보존합니다.")
            if previous_release.exists():
                if target.exists():
                    raise LauncherError("복구 대상 폴더가 이미 있습니다. 백업을 보존합니다.")
                previous_release.rename(target)
            stage = inside(self.paths.root, f"staging/{journal['id']}")
            if stage.exists():
                quarantine.mkdir(parents=True, exist_ok=True)
                stage.rename(inside(quarantine, "aborted-stage"))
                self._warn(app.app_id, f"미완료 설치 파일을 보존했습니다: {quarantine}")
        self._phase(journal, "failed")
        self._finish(journal)
        return False

    def _recover(self, app_id):
        journals = inside(self.paths.app(app_id), "transactions")
        if not journals.exists():
            return
        for path in sorted(journals.glob("*.json")):
            journal = read_json(path)
            try:
                valid = (journal.get("schema_version") == 1 and self._journal_path(journal) == path
                         and journal["app"]["app_id"] == app_id)
            except (KeyError, TypeError, ValueError):
                valid = False
            if not valid:
                raise LauncherError("잘못된 복구 기록 — 파일을 보존하고 확인하세요.")
            allowed = {
                "install": {"downloading", "download_verified", "preparing", "ready", "switching", "activating", "activated", "failed", "recovery_required"},
                "uninstall": {"preparing_removal", "removing", "uninstalled", "removal_restored", "recovery_required"},
            }
            if (not isinstance(journal.get("kind"), str) or not isinstance(journal.get("phase"), str)
                    or journal["phase"] not in allowed.get(journal["kind"], set())):
                raise LauncherError("알 수 없는 복구 단계 — 자동 변경하지 않습니다.")
            if (journal.get("phase") not in {"activated", "failed", "uninstalled", "removal_restored"}
                    and self.is_running(app_id)):
                raise LauncherError("프로그램 실행 중 — 미완료 작업 복구를 보류합니다.")
            if journal.get("kind") == "install":
                # Completed journals only own cleanup, not the current active version.
                if journal["phase"] in {"activated", "failed"}:
                    self._finish(journal)
                else:
                    self._recover_install(journal)
            elif journal.get("kind") == "uninstall":
                if journal["phase"] in {"uninstalled", "removal_restored"}:
                    self._finish(journal)
                else:
                    self._restore_removal(journal)
            else:
                raise LauncherError("지원하지 않는 복구 작업입니다.")

    def _restore_removal(self, journal):
        app = AppRelease.parse(journal["app"])
        previous = journal.get("previous_pointer")
        if (not isinstance(previous, dict)
                or AppRelease.parse(previous.get("app", {})).app_id != app.app_id
                or not isinstance(journal.get("files"), dict)):
            raise LauncherError("제거 복구 기록이 잘못되었습니다. 원본을 보존합니다.")
        root = self.paths.app(app.app_id)
        backup_root = inside(self._quarantine(journal), "files")
        if journal["phase"] != "preparing_removal":
            for name, expected in journal.get("files", {}).items():
                file = inside(root, name)
                backup = inside(backup_root, name)
                if file.exists():
                    if digest(file) != expected:
                        raise LauncherError("제거 중 파일이 변경되어 덮어쓰지 않습니다. 복구 필요")
                    continue
                if not backup.is_file() or digest(backup) != expected:
                    raise LauncherError("제거 백업 검증 실패 — 복구 필요")
                file.parent.mkdir(parents=True, exist_ok=True)
                # Windows rename fails if a new destination appeared; no overwrite.
                temp = inside(root, f"recovery/{journal['id']}/restore-{uuid.uuid4().hex}")
                shutil.copy2(backup, temp)
                if digest(temp) != expected:
                    raise LauncherError("제거 복원 사본 검증 실패")
                temp.rename(file)
            pointer = root / "active.json"
            if pointer.exists() and read_json(pointer) != previous:
                raise LauncherError("제거 복원 중 활성 포인터 충돌 — 복구 필요")
            if not pointer.exists():
                atomic_json(pointer, previous)
        self._phase(journal, "removal_restored")
        self._finish(journal)

    def uninstall(self, app_id: str) -> dict:
        with app_lock(self.paths.lock(app_id)):
            self.warnings.clear()
            self._recover(app_id)
            if self.is_running(app_id):
                raise LauncherError("실행 중인 프로그램은 제거할 수 없습니다.")
            active = self.installed(app_id)
            if not active:
                raise LauncherError("설치된 프로그램이 없습니다.")
            root = self.paths.app(app_id)
            receipts = []
            for path in sorted((root / "releases").glob("*/receipt.json")):
                data = read_json(path)
                app = AppRelease.parse(data.get("app", {}))
                if app.app_id != app_id or path.parent != self.paths.release(app_id, app.release_id):
                    raise LauncherError("잘못된 설치 영수증 — 제거를 중단합니다.")
                files = data.get("files")
                if not isinstance(files, dict):
                    raise LauncherError("설치 파일 목록이 잘못되었습니다.")
                receipts.append((path, app, files))
            retained, managed = [], {}
            for receipt, app, files in receipts:
                payload = inside(receipt.parent, "payload")
                cwd = inside(payload, app.working_directory_relative_path, allow_dot=True)
                preserved = [inside(cwd, p) for p in app.preserve_paths]
                for name, expected in files.items():
                    relative_path(name)
                    if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
                        raise LauncherError("잘못된 설치 파일 해시 — 제거 중단")
                    file = inside(payload, name)
                    if not file.is_file():
                        continue
                    if (any(file == p or file.is_relative_to(p) for p in preserved)
                            or digest(file) != expected):
                        retained.append(str(file))
                        continue
                    managed[file.relative_to(root).as_posix()] = expected
            journal = self._new_journal(active, "uninstall", uuid.uuid4().hex, files=managed)
            backup_root = inside(self._quarantine(journal), "files")
            try:
                # All backups are verified before any original file is deleted.
                for name, expected in managed.items():
                    source, backup = inside(root, name), inside(backup_root, name)
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, backup)
                    if digest(backup) != expected or digest(source) != expected:
                        raise LauncherError("제거 준비 중 파일 변경 — 원본 보존")
                self._phase(journal, "removing")
                if self.is_running(app_id):
                    raise LauncherError("프로그램이 실행되어 제거를 보류합니다.")
                for name, expected in managed.items():
                    file = inside(root, name)
                    if digest(file) != expected:
                        raise LauncherError("제거 중 파일 변경 — 복구 필요")
                    file.unlink()
                if any(inside(root, name).exists() for name in managed):
                    raise LauncherError("제거 결과 확인 실패")
                (root / "active.json").unlink()
                self._phase(journal, "uninstalled")
            except Exception as exc:
                try:
                    self._restore_removal(journal)
                except Exception as recovery:
                    self._recovery_error(journal, recovery)
                    raise LauncherError(f"제거 실패; 복구 필요: {recovery}") from exc
                raise LauncherError(f"제거 실패; 기존 파일 복원 완료, 재시도 가능: {exc}") from exc
            # Backups/unknown files are retained, never recursively deleted.
            self._finish(journal)
            remaining = [str(p) for p in plain_tree(root) if not p.is_dir() or p.is_symlink()]
            return {"removed_files": len(managed), "retained_files": remaining,
                    "retained_directory": str(root)}
