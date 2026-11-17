"""Pinned channel and signed first-run seed for the managed launcher."""
from pathlib import Path
import shutil
import sys

from .catalog_trust import CatalogVerifier, strict_json
from .common import LauncherError, app_lock, atomic_json, digest, inside, read_json
from .github_provider import GitHubReleasesProvider
from .runtime_protocol import PURPOSE, response
from .self_update import APP_ID, MANAGED_PURPOSE, SelfUpdater, version


def channel_policy():
    path = Path(__file__).parent / "data" / "managed-channel.json"
    channel = strict_json(path.read_bytes())
    if (set(channel) != {"repository", "policy"}
            or channel["repository"] not in {"toast-source/creative-group-releases",
                                             "toast-source/creative-group-trial-releases"}
            or not channel["policy"]["keys"]):
        raise LauncherError("관리형 런처 채널 또는 고정 신뢰키가 없습니다.")
    return channel


def initialize(home, data_root, seed, channel):
    home, data_root = home.resolve(), data_root.resolve()
    if home.is_relative_to(data_root) or data_root.is_relative_to(home):
        raise LauncherError("런처 프로그램과 사용자 데이터 경로를 분리하세요.")
    layout = inside(home, "layout.json")
    with app_lock(inside(home, "locks/layout.lock")):
        if not layout.exists():
            atomic_json(layout, {"schema_version": 1, "purpose": MANAGED_PURPOSE,
                                 "user_data_root": str(data_root)})
    updater = SelfUpdater(home, channel=channel)
    if updater.data_root != data_root:
        raise LauncherError("관리형 런처의 기존 사용자 데이터 경로와 다릅니다.")
    with updater._lock(), updater._runtime_lock():
        if inside(home, "current.json").exists():
            return
        verifier = updater.verifier
        apps = verifier.accept((seed / "catalog.json").read_bytes(), (seed / "catalog.sig.json").read_bytes())
        candidates = [app for app in apps if app.app_id == APP_ID]
        if len(candidates) != 1:
            raise LauncherError("서명된 초기 런처 항목 한 개가 필요합니다.")
        app = candidates[0]
        updater._candidate(app)

        class SignedSeed:
            def __init__(self, verifier: CatalogVerifier):
                self.verifier = verifier

            def download(self, release, target, progress, cancel):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(inside(seed, release.package_name), target)

        updater.engine.recover(APP_ID)
        if updater.engine.installed(APP_ID) != app:
            updater.engine.install(app, SignedSeed(verifier))
        updater._point(app)


class ManagedSession:
    def __init__(self, file, compiled_version):
        self.file = file.resolve()
        self.context = c = read_json(self.file)
        self.channel = channel_policy()
        self.updater = SelfUpdater(Path(c["home"]), channel=self.channel)
        executable = Path(sys.executable).resolve()
        self.mode = c["mode"]
        if (not getattr(sys, "frozen", False) or c.get("purpose") != PURPOSE
                or c.get("managed") is not True or self.mode not in {"normal", "health"}
                or self.file != inside(self.updater.home, f"sessions/{c['session']}/context.json")
                or executable != Path(c["executable"]).resolve() or digest(executable) != c["exe_sha256"]
                or compiled_version != c["version"]):
            raise LauncherError("관리형 Windows 시작 세션과 제품 EXE가 일치하지 않습니다.")
        self.current = self.updater.current()
        path, _ = self.updater.engine.resolve_launch(self.current)
        if (path.resolve() != executable or self.current.release_id != c["release_id"]
                or self.current.version != compiled_version or self.current.executable_sha256 != c["exe_sha256"]):
            raise LauncherError("관리형 런처 활성 버전이 시작 요청과 다릅니다.")
        self.data_root = (self.updater.data_root if self.mode == "normal"
                          else inside(self.file.parent, "health-data"))

    def acknowledge(self, stage, **extra):
        c = self.context
        atomic_json(self.file.parent / f"{stage}.json", {
            **response(c, stage, c["release_id"], c["version"], c["exe_sha256"]), **extra})

    def command(self, action):
        file = self.file.parent / f"command-{action}.json"
        if not file.exists():
            return False
        if read_json(file) != {"nonce": self.context["nonce"]}:
            raise LauncherError("관리형 런처 제어 요청이 일치하지 않습니다.")
        return True

    def newer(self, app):
        return (app is not None and app.published
                and version(app.version) > version(self.current.version)
                and app.is_new_release(self.current))

    def prepare(self, expected, cancel):
        provider = GitHubReleasesProvider(self.channel["repository"], verifier=self.updater.verifier)
        return self.updater.prepare(provider, cancel=cancel, expected=expected)

    def handoff(self, transaction):
        self.updater.request_apply(transaction, approved=True)
        try:
            c = self.context
            atomic_json(self.file.parent / "request.json", {
                **response(c, "closing", c["release_id"], c["version"], c["exe_sha256"]),
                "transaction": transaction})
        except OSError:
            self.updater.request_apply(transaction, approved=False)
            raise
