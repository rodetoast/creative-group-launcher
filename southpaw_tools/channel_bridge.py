"""Run Rod from the signed Toast bridge while keeping the original entry point."""
from contextlib import ExitStack
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import uuid
import zipfile

from .archive import checked_members, member_name
from .catalog_trust import CATALOG_ID, CatalogVerifier
from .common import LauncherError, app_lock, digest, inside, plain_tree, read_json
from .github_channels import canonical_channel, CANONICAL_CATALOG_ID

TOAST = "toast-source/creative-group-releases"
RUNTIME = "rod"
HOME = "launcher-home"
MINIMUM_BRIDGE_SEQUENCE = 10


def legacy_binding(home, data):
    """The bridge's Rod home is a child of the original managed home."""
    if home.name != HOME or home.parent.name != RUNTIME or home.parent.parent.name != HOME:
        return None
    legacy_home = home.parent.parent
    if inside(legacy_home, f"{RUNTIME}/{HOME}") != home:
        raise LauncherError("Rod 전환 저장소의 경로가 일치하지 않습니다.")
    layout = read_json(inside(legacy_home, "layout.json"))
    if (layout.get("schema_version") != 1 or layout.get("purpose") != "creative-group-launcher-managed-v1"
            or Path(layout["user_data_root"]).resolve() != data
            or not inside(legacy_home, "current.json").is_file()):
        raise LauncherError("기존 Launcher 데이터 연결을 확인할 수 없습니다.")
    return legacy_home


class BridgedAppVerifier(CatalogVerifier):
    """Old signed app receipts remain usable solely as historical local proof."""
    def verify_installed_release(self, state, app):
        try:
            super().verify_installed_release(state, app)
        except LauncherError:
            if app.app_id == "creative-group-launcher":
                raise
            old = {**self.policy, "catalog_id": CATALOG_ID, "minimum_sequence": 4}
            CatalogVerifier(old, self.state_path).verify_installed_release(state, app)


def _runtime_files(folder):
    files = set()
    for entry in folder.iterdir():
        if entry.name == HOME:
            continue
        inside(folder, entry.name)
        for child in (entry, *plain_tree(entry)) if entry.is_dir() else (entry,):
            name = child.relative_to(folder).as_posix()
            inside(folder, name)
            if child.is_file():
                files.add(name)
    return files


def prepare_runtime(payload, legacy_home):
    runtime = inside(legacy_home, RUNTIME)
    manifest = read_json(inside(payload, "rod-bootstrap-files.json"))
    if "CGLBootstrap.exe" not in manifest:
        raise LauncherError("Rod Bootstrap 파일 목록이 없습니다.")
    if not runtime.exists():
        stage = inside(legacy_home, f"rod-stage-{uuid.uuid4().hex[:8]}")
        with zipfile.ZipFile(inside(payload, "rod-bootstrap.zip")) as archive:
            members = checked_members(archive)
            names = {member_name(m) for m in members if not m.is_dir()}
            if names != set(manifest) or any(n.split("/")[0].casefold() == HOME for n in names):
                raise LauncherError("Rod Bootstrap ZIP 파일 목록이 다릅니다.")
            stage.mkdir()
            for member in members:
                if member.is_dir():
                    continue
                target = inside(stage, member_name(member))
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("xb") as sink:
                    shutil.copyfileobj(source, sink)
                if digest(target) != manifest[member_name(member)]:
                    raise LauncherError("Rod Bootstrap ZIP의 파일 해시가 다릅니다.")
        stage.rename(runtime)
    if _runtime_files(runtime) != set(manifest):
        raise LauncherError("Rod Bootstrap 설치 파일 목록이 다릅니다.")
    for name, expected in manifest.items():
        if digest(inside(runtime, name)) != expected:
            raise LauncherError("Rod Bootstrap 설치 파일 해시가 다릅니다.")
    return runtime


def run_bridge(session, payload, launching):
    from .github_provider import GitHubReleasesProvider
    from .managed_update import initialize
    from .self_update import version

    if session.mode != "normal" or session.channel["repository"] != TOAST:
        raise LauncherError("승인된 Toast 실행 세션에서만 Rod로 전환할 수 있습니다.")
    channel = read_json(inside(payload, "rod-channel.json"))
    if (not canonical_channel(channel) or channel["policy"]["catalog_id"] != CANONICAL_CATALOG_ID
            or channel["policy"]["minimum_sequence"] != 9
            or channel["policy"]["keys"] != session.channel["policy"]["keys"]):
        raise LauncherError("Rod 전환 설정과 운영 서명 정책이 일치하지 않습니다.")
    legacy_home = session.updater.home
    runtime = prepare_runtime(payload, legacy_home)
    home = inside(runtime, HOME)
    data = session.data_root
    if legacy_binding(home, data) != legacy_home:
        raise LauncherError("Rod 전환 저장소 위치가 다릅니다.")
    if not inside(home, "current.json").exists():
        # Persist the attempted catalog's high-water mark separately from both active stores.
        policy = {**channel["policy"], "minimum_sequence": MINIMUM_BRIDGE_SEQUENCE}
        verifier = CatalogVerifier(policy, inside(home, "bridge-download-trust.json"))
        provider = GitHubReleasesProvider(channel["repository"], repository_id=channel["repository_id"],
                                          verifier=verifier)
        candidates = [a for a in provider.catalog() if a.app_id == "creative-group-launcher" and a.published]
        if len(candidates) != 1 or version(candidates[0].version) < (0, 1, 7):
            raise LauncherError("기존 앱 데이터를 지원하는 Rod 런처 업데이트가 아직 준비되지 않았습니다.")
        app = candidates[0]
        with TemporaryDirectory(prefix="rod-seed-", dir=legacy_home) as staging:
            seed = Path(staging)
            with provider.installation_session(app):
                provider.download(app, seed / app.package_name)
                raw, signature = provider.verified_catalog_bytes()
            (seed / "catalog.json").write_bytes(raw)
            (seed / "catalog.sig.json").write_bytes(signature)
            initialize(home, data, seed, channel)
    executable = inside(runtime, "CGLBootstrap.exe")
    launching.set()
    result = subprocess.run([str(executable)], cwd=runtime, stdin=subprocess.DEVNULL)
    if result.returncode:
        raise LauncherError(f"Rod 런처가 종료 코드 {result.returncode}로 중단됐습니다.")


def fallback_lease(legacy_home):
    """Do not let a failed bridge open a second UI alongside a surviving Rod process."""
    stack = ExitStack()
    try:
        home = inside(legacy_home, f"{RUNTIME}/{HOME}")
        if not home.parent.exists():
            return stack
        for name in ("bootstrap", "running", "update"):
            stack.enter_context(app_lock(inside(home, f"locks/{name}.lock")))
        return stack
    except BaseException:
        stack.close()
        raise

def start_bridge_ui(app, window, session, payload, fallback_locks):
    from threading import Event, Thread
    from PySide6.QtCore import QTimer

    launching = Event()
    finished = Event()
    errors = []
    # Keep the existing confirmed Toast session alive as the single entry point.
    # Its OS runtime lock remains held while the Rod window is open.
    window.setEnabled(False)
    window.bridge_in_progress = True
    window.message.setText("Rod 런처 업데이트를 확인하고 있습니다.")
    app.setQuitOnLastWindowClosed(False)

    def run():
        try:
            run_bridge(session, payload, launching)
        except (LauncherError, OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
            errors.append(exc)
        finally:
            finished.set()

    timer = QTimer(window)

    def poll():
        if launching.is_set() and not finished.is_set():
            window.hide()
        if not finished.is_set():
            return
        timer.stop()
        if not errors:
            app.exit(0)
            return
        try:
            fallback_locks.enter_context(fallback_lease(session.updater.home))
        except (LauncherError, OSError):
            # An interrupted parent may have left Rod running. Never open duplicate UI.
            app.exit(0)
            return
        from .common import atomic_json
        try:
            error = errors[0]
            atomic_json(inside(session.file.parent, "bridge-status.json"),
                        {"result": "fallback", "error_type": type(error).__name__,
                         "winerror": getattr(error, "winerror", None)})
        except (LauncherError, OSError):
            pass
        window.bridge_in_progress = False
        window.bridge_fallback = True
        window.show()
        window.setEnabled(True)
        window.update_timer.stop()
        # Local fallback stays usable, without another automatic migration loop.
        window.message.setText("Rod 전환을 완료하지 못했습니다. 기존 프로그램을 계속 사용할 수 있습니다.")
        app.setQuitOnLastWindowClosed(True)

    timer.timeout.connect(poll)
    timer.start(100)
    Thread(target=run, name="Rod channel bridge").start()
