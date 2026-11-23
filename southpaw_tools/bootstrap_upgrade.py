"""One-time signed Bootstrap entry upgrade for the existing Rod rollout."""
from contextlib import ExitStack
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
import zipfile

from .archive import check_cancel, checked_members, member_name
from .channel_bridge import legacy_binding
from .common import LauncherError, app_lock, atomic_json, digest, inside, plain_tree, read_json
from .github_channels import canonical_channel
from .windows_process import identity, parent_pid, still_same

ENTRY = "CGLBootstrap.exe"
# Keep the previous entry's runtime and transaction intact for restoration.
GENERATION = 3
RUNTIME = "_cgl_b3"
STAGE = ".bootstrap-v3"
SPEC = "bootstrap-upgrade.json"
PACKAGE = "bootstrap-v3.zip"
APP_ID = "creative-group-launcher"
TERMINAL = {"committed", "failed_before_swap", "restored"}


def _entry_root(updater):
    legacy = legacy_binding(updater.home, updater.data_root)
    return (legacy or updater.home).parent, "bridge" if legacy else "rod"


def _home(root, kind):
    if kind not in {"rod", "bridge"}:
        raise LauncherError("Bootstrap 설치 유형 오류")
    return inside(root, "launcher-home/rod/launcher-home" if kind == "bridge" else "launcher-home")


def _signed_candidate(home, channel):
    from .bootstrap import WindowsUpdater

    updater = WindowsUpdater(home, channel=channel)
    current = updater.current()
    payload = updater._validate_release(current)
    spec = read_json(inside(payload, SPEC))
    files = spec.get("files")
    allowed = spec.get("old_entry")
    if (not canonical_channel(channel) or spec.get("generation") != GENERATION
            or not isinstance(allowed, dict) or set(allowed) != {"rod", "bridge"}
            or not isinstance(files, dict) or ENTRY not in files
            or not all(name == ENTRY or name.startswith(RUNTIME + "/") for name in files)
            or not all(isinstance(checksum, str) and len(checksum) == 64 for checksum in files.values())
            or not all(isinstance(values, list) and values and
                       all(isinstance(checksum, str) and len(checksum) == 64 for checksum in values)
                       for values in allowed.values())):
        raise LauncherError("서명된 Bootstrap 교체 명세가 유효하지 않습니다.")
    return updater, current, payload, spec


def _approved(session, legacy):
    if any(j["phase"] == "committed" and j["new"] == session.current.to_dict()
           for p in inside(session.updater.home, "transactions").glob("*.json")
           if (j := session.updater.journal(p.stem))):
        return True
    if not legacy:
        return False
    # The already-approved Toast update can initialize Rod directly from Latest.
    from .catalog_trust import CatalogVerifier

    trust = inside(session.updater.home, "bridge-download-trust.json")
    if not trust.is_file():
        return False
    verifier = CatalogVerifier(session.channel["policy"], trust)
    return session.current in (verifier.cached() or [])


def _lineage(root):
    entry = inside(root, ENTRY)
    pid = os.getpid()
    chain = []
    for _ in range(6):
        record = identity(pid)
        if not record or not Path(record["image"]).is_relative_to(root):
            break
        chain.append(record)
        if Path(record["image"]) == entry:
            return chain
        pid = parent_pid(pid)
        if not pid:
            break
    raise LauncherError("실행 중인 기존 Bootstrap을 확인할 수 없습니다.")


def _state(stage):
    state = read_json(inside(stage, "transaction.json"))
    if (state.get("generation") != GENERATION or not isinstance(state.get("nonce"), str)
            or len(state["nonce"]) != 32 or state.get("phase") not in
            TERMINAL | {"staged", "waiting", "switching"}):
        raise LauncherError("Bootstrap 교체 기록 형식 오류")
    return state


def _phase(stage, state, phase, **details):
    updated = {**state, **details, "phase": phase}
    atomic_json(inside(stage, "transaction.json"), updated)
    return updated


def _files(base):
    return {item.relative_to(base).as_posix(): digest(item)
            for item in plain_tree(base) if item.is_file()}


def _check_files(shadow, spec):
    if _files(shadow) != spec["files"]:
        raise LauncherError("Bootstrap 준비 파일과 서명된 명세가 일치하지 않습니다.")


def _extract(payload, stage, spec, cancel):
    shadow = inside(stage, "candidate")
    with zipfile.ZipFile(inside(payload, PACKAGE)) as archive:
        entries = checked_members(archive)
        if {member_name(item) for item in entries if not item.is_dir()} != set(spec["files"]):
            raise LauncherError("Bootstrap ZIP 파일 목록이 일치하지 않습니다.")
        shadow.mkdir()
        for item in entries:
            check_cancel(cancel)
            if item.is_dir():
                continue
            name = member_name(item)
            target = inside(shadow, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item) as source, target.open("xb") as sink:
                shutil.copyfileobj(source, sink)
    _check_files(shadow, spec)
    return shadow


def _spawn(exe, *arguments, log=None):
    env = {**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"}
    return subprocess.Popen([str(exe), *arguments], cwd=exe.parent, env=env,
                            stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _durable_copy(source, target):
    with source.open("rb") as reader, target.open("xb") as writer:
        shutil.copyfileobj(reader, writer)
        writer.flush()
        os.fsync(writer.fileno())


def begin(session, cancel):
    """Prepare only after the existing approved GUI update or Bridge initialization."""
    payload = Path(sys.executable).resolve().parent
    if (os.name != "nt" or session.mode != "normal" or not canonical_channel(session.channel)
            or not inside(payload, SPEC).is_file()):
        return False
    root, kind = _entry_root(session.updater)
    stage = inside(root, STAGE)
    if stage.exists() or not _approved(session, kind == "bridge"):
        return False
    _, current, verified, spec = _signed_candidate(session.updater.home, session.channel)
    if current != session.current or verified != payload:
        raise LauncherError("현재 실행 중인 GUI의 서명된 교체 후보가 아닙니다.")
    entry = inside(root, ENTRY)
    old_hash = digest(entry)
    if old_hash not in spec["old_entry"][kind]:
        raise LauncherError("기존 Bootstrap 버전은 자동 교체 대상이 아닙니다.")
    chain = _lineage(root)
    stage.mkdir()
    shadow = _extract(payload, stage, spec, cancel)
    backup = inside(stage, "previous.exe")
    _durable_copy(entry, backup)
    if digest(backup) != old_hash:
        raise LauncherError("기존 Bootstrap 백업을 검증할 수 없습니다.")
    record = {"generation": GENERATION, "nonce": secrets.token_hex(16), "kind": kind,
              "old_sha256": old_hash, "release_id": current.release_id, "chain": chain}
    _phase(stage, record, "staged")
    with inside(stage, "worker.log").open("xb") as log:
        child = _spawn(inside(shadow, ENTRY), "--bootstrap-swap", log=log)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline and child.poll() is None:
        check_cancel(cancel)
        state = _state(stage)
        if state["phase"] == "waiting" and state.get("worker", {}).get("pid") == child.pid:
            atomic_json(inside(stage, "apply.json"), {"nonce": state["nonce"], "gui": chain[0]})
            return True
        time.sleep(.05)
    raise LauncherError("Bootstrap 교체 작업자를 시작하지 못했습니다.")


def _wait_processes(chain):
    deadline = time.monotonic() + 45
    while any(still_same(record) for record in chain):
        if time.monotonic() >= deadline:
            raise LauncherError("기존 Bootstrap과 GUI가 아직 종료되지 않았습니다.")
        time.sleep(.1)


def _exclusive(root, updater):
    stack = ExitStack()
    try:
        roots = (updater.home,) if updater.home.parent == root else (inside(root, "launcher-home"), updater.home)
        for home in roots:
            for lock in ("bootstrap", "update", "running"):
                stack.enter_context(app_lock(inside(home, f"locks/{lock}.lock")))
        return stack
    except BaseException:
        stack.close()
        raise


def _restore(root, stage, state, spec):
    entry = inside(root, ENTRY)
    backup = inside(stage, "previous.exe")
    if (state["old_sha256"] not in spec["old_entry"][state["kind"]]
            or digest(backup) != state["old_sha256"]):
        raise LauncherError("이전 Bootstrap의 복원 해시가 다릅니다.")
    actual = digest(entry)
    if actual == spec["files"][ENTRY]:
        pending = inside(stage, "restore.exe")
        if not pending.exists():
            _durable_copy(backup, pending)
        if digest(pending) != state["old_sha256"]:
            raise LauncherError("복원 준비 파일이 손상됐습니다.")
        os.replace(pending, entry)
    elif actual != state["old_sha256"]:
        raise LauncherError("알 수 없는 Bootstrap 파일은 덮어쓰지 않습니다.")
    _phase(stage, state, "restored")
    return entry


def _trial(stage, state, entry, expected):
    with inside(stage, "trial.log").open("ab") as log:
        child = _spawn(entry, "--bootstrap-trial", state["nonce"], log=log)
    confirmation_path = inside(stage, "confirmed.json")
    deadline = time.monotonic() + 100
    try:
        while time.monotonic() < deadline:
            try:
                result = read_json(confirmation_path)
            except LauncherError as exc:
                if not isinstance(exc.__cause__, (FileNotFoundError, PermissionError)):
                    raise
            else:
                confirmation = result.get("identity")
                if (result.get("nonce") == state["nonce"] and result.get("release_id") == expected
                        and confirmation and confirmation["pid"] == child.pid
                        and Path(confirmation["image"]) == entry and still_same(confirmation)):
                    _phase(stage, state, "committed", confirmed=confirmation, confirmed_release=expected)
                    return
                raise LauncherError("새 Bootstrap 시작 확인이 일치하지 않습니다.")
            if child.poll() is not None:
                raise LauncherError("새 Bootstrap이 확인 전에 종료됐습니다.")
            time.sleep(.1)
        raise LauncherError("새 Bootstrap 시작 확인 제한 시간 초과")
    except Exception:
        # This is the probationary process created by this worker, never a
        # pre-existing employee process. Windows releases its image on exit.
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=8)
        raise


def worker(*, restore=False):
    from .managed_update import channel_policy

    shadow = Path(sys.executable).resolve().parent
    stage = shadow.parent
    root = stage.parent
    if shadow.name != "candidate" or stage.name != STAGE or shadow != inside(root, f"{STAGE}/candidate"):
        raise LauncherError("고정된 Bootstrap 교체 작업 경로가 아닙니다.")
    with app_lock(inside(stage, "worker.lock")):
        state = _state(stage)
        updater, release, _, spec = _signed_candidate(_home(root, state["kind"]), channel_policy())
        if release.release_id != state["release_id"] or _entry_root(updater) != (root, state["kind"]):
            raise LauncherError("Bootstrap 교체 대상과 승인 릴리스가 일치하지 않습니다.")
        _check_files(shadow, spec)
        entry = inside(root, ENTRY)
        if restore:
            if state["phase"] != "switching":
                return 1
            _wait_processes([state["recovery_parent"]])
            entry = _restore(root, stage, state, spec)
            _spawn(entry)
            return 0
        if state["phase"] != "staged":
            return 1
        state = _phase(stage, state, "waiting", worker=identity(os.getpid()))
        waited = False
        swapped = False
        try:
            _wait_processes(state["chain"])
            waited = True
            with _exclusive(root, updater):
                approval = read_json(inside(stage, "apply.json"))
                if approval != {"nonce": state["nonce"], "gui": state["chain"][0]} or updater.current() != release:
                    raise LauncherError("실행 중 시작 구성 교체 승인이 취소되었거나 릴리스가 바뀌었습니다.")
                if digest(entry) != state["old_sha256"] or state["old_sha256"] not in spec["old_entry"][state["kind"]]:
                    raise LauncherError("대기 중 기존 Bootstrap이 바뀌었습니다.")
                runtime = inside(root, RUNTIME)
                if runtime.exists():
                    raise LauncherError("새 Bootstrap 런타임 폴더가 이미 있습니다.")
                staged_runtime = inside(stage, "runtime")
                shutil.copytree(inside(shadow, RUNTIME), staged_runtime)
                expected_runtime = {name.removeprefix(RUNTIME + "/"): checksum for name, checksum in spec["files"].items()
                                    if name.startswith(RUNTIME + "/")}
                if _files(staged_runtime) != expected_runtime:
                    raise LauncherError("복사한 Bootstrap 런타임 해시가 다릅니다.")
                os.replace(staged_runtime, runtime)
                pending = inside(stage, "next.exe")
                _durable_copy(inside(shadow, ENTRY), pending)
                if digest(pending) != spec["files"][ENTRY]:
                    raise LauncherError("새 진입 파일 해시가 다릅니다.")
                state = _phase(stage, state, "switching")
                os.replace(pending, entry)
                swapped = True
            _trial(stage, state, entry, release.release_id)
        except (LauncherError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            if swapped:
                _restore(root, stage, state, spec)
            else:
                _phase(stage, state, "failed_before_swap", error=type(exc).__name__)
            if waited:
                _spawn(entry)
            raise
    return 0


def entry_route(nonce):
    """Resolve the unchanged root entry's managed home and readiness callback."""
    root = Path(sys.executable).resolve().parent
    stage = inside(root, STAGE)
    state = _state(stage)
    home = _home(root, state["kind"])
    if state["phase"] == "committed" and nonce is None:
        return home, None, None
    if state["phase"] != "switching":
        raise LauncherError("새 Bootstrap에는 유효한 교체 기록이 필요합니다.")
    alive = still_same(state["worker"])
    if (nonce is not None and nonce != state["nonce"]) or (alive and nonce is None):
        raise LauncherError("Bootstrap 교체 확인이 이미 진행 중입니다.")

    def confirmed(session):
        if session.app.release_id != state["release_id"]:
            raise LauncherError("시험 부팅 GUI가 승인된 릴리스와 다릅니다.")
        confirmation = identity(os.getpid())
        if alive:
            atomic_json(inside(stage, "confirmed.json"),
                        {"nonce": state["nonce"], "identity": confirmation, "release_id": session.app.release_id})
        else:
            _phase(stage, state, "committed", confirmed=confirmation, confirmed_release=session.app.release_id)

    def recover():
        if alive:
            return True  # Return to the independent worker without a modal dialog.
        if _state(stage)["phase"] == "committed":
            return False
        from .managed_update import channel_policy
        _, _, _, spec = _signed_candidate(home, channel_policy())
        shadow = inside(stage, "candidate")
        _check_files(shadow, spec)
        _phase(stage, state, "switching", recovery_parent=identity(os.getpid()))
        _spawn(inside(shadow, ENTRY), "--restore-bootstrap")
        return True

    return home, confirmed, recover
