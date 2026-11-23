"""Pinned channel and signed first-run seed for the managed launcher."""
from pathlib import Path
from contextlib import nullcontext
import shutil
import sys

from .catalog_trust import CatalogVerifier, strict_json
from .common import LauncherError, app_lock, atomic_json, digest, inside, read_json
from .github_provider import GitHubReleasesProvider
from .github_channels import managed_repository, canonical_channel, CANONICAL_CATALOG_ID
from .paths import AppPaths
from .channel_bridge import legacy_binding
from .runtime_protocol import PURPOSE, response
from .self_update import APP_ID, MANAGED_PURPOSE, SelfUpdater, version


def channel_policy():
    path = Path(__file__).parent / "data" / "managed-channel.json"
    channel = strict_json(path.read_bytes())
    if (set(channel) not in ({"repository", "policy"}, {"repository", "repository_id", "policy"})
            or not isinstance(channel["repository"], str)
            or not managed_repository(channel["repository"], channel.get("repository_id"))
            or not channel["policy"]["keys"]):
        raise LauncherError("관리형 런처 채널 또는 고정 신뢰키가 없습니다.")
    if "repository_id" in channel and (not canonical_channel(channel)
            or channel["policy"].get("catalog_id") != CANONICAL_CATALOG_ID
            or channel["policy"].get("minimum_sequence", 0) < 9):
        raise LauncherError("신규 채널 ID·카탈로그·최소 순번9가 일치하지 않습니다.")
    if channel["policy"].get("catalog_id") == CANONICAL_CATALOG_ID and not canonical_channel(channel):
        raise LauncherError("신규 카탈로그는 고정된 신규 저장소에서만 사용할 수 있습니다.")
    return channel


def default_data_root(channel):
    root = AppPaths.default().root
    return root.with_name("ToolsLauncherRodetoast") if canonical_channel(channel) else root


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
        self.legacy_home = (legacy_binding(self.updater.home, self.updater.data_root)
                            if canonical_channel(self.channel) else None)
        self.data_root = (self.updater.data_root if self.mode == "normal"
                          else inside(self.file.parent, "health-data"))

    def startup_lease(self):
        # The update worker already holds the runtime lock during its health probe.
        return self.updater._runtime_lock() if self.mode == "normal" else nullcontext()

    def verify_current(self):
        """Validate the active payload while the caller holds the startup lease."""
        c = self.context
        self.current = self.updater.current()
        path, _ = self.updater.engine.resolve_launch(self.current)
        if (path.resolve() != Path(sys.executable).resolve() or self.current.release_id != c["release_id"]
                or self.current.version != c["version"] or self.current.executable_sha256 != c["exe_sha256"]):
            raise LauncherError("관리형 런처 활성 버전이 시작 요청과 다릅니다.")

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
        provider = GitHubReleasesProvider(self.channel["repository"], verifier=self.updater.verifier,
                                           repository_id=self.channel.get("repository_id"))
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
