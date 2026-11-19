"""One signed candidate trial on Windows. Requires a disposable Toast 0.1.5 fixture."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

BUNDLE_SHA = "248f2d2f841807befec810bb9cdb601f837cd6acbdcd4030139e15636b760f92"
BOOT_SHA = "c15f48a0d72dd0a8bdc1ad909a75ae3327a91a2f136170dc4c3713651df6cb19"
TOAST = "toast-source/creative-group-releases"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class Response(io.BytesIO):
    status = 200

    def __init__(self, body):
        super().__init__(body)
        self.headers = {"Content-Length": str(len(body))}


class CandidateTransport:
    """Fixture response source only. The real provider still verifies all metadata and bytes."""

    def __init__(self, provider, catalog, seed):
        self.api_url = provider.api_url
        self.urls = {}
        assets = []
        for asset_id, (name, info) in enumerate(catalog["assets"].items(), 1):
            url = f"https://github.com/{TOAST}/releases/download/{catalog['tag']}/{name}"
            assets.append({"id": asset_id, "name": name, "size": info["size"], "state": "uploaded",
                           "digest": "sha256:" + info["sha256"], "browser_download_url": url})
            if (seed / name).is_file():
                self.urls[url] = seed / name
        self.body = json.dumps({"id": 1, "tag_name": catalog["tag"], "draft": False,
                                "prerelease": False, "assets": assets}).encode()

    def open(self, request, timeout):
        if request.full_url == self.api_url:
            return Response(self.body)
        return Response(self.urls[request.full_url].read_bytes())


def click_update(args, scope, seed, catalog, program, data, channel):
    # Use the published Toast 0.1.5 Python sources, with the pinned policy from its
    # official Bootstrap. The fixture substitutes only for the missing release.
    assert args.legacy_source is not None
    sys.path.insert(0, str(args.legacy_source.resolve()))
    from unittest.mock import patch
    from PySide6.QtWidgets import QApplication
    from southpaw_tools import __version__
    from southpaw_tools.catalog_trust import CatalogVerifier
    from southpaw_tools.github_provider import GitHubReleasesProvider
    from southpaw_tools.paths import AppPaths
    from southpaw_tools.self_update import SelfUpdater
    from southpaw_tools.ui import MainWindow

    assert __version__ == "0.1.5"
    home = program / "launcher-home"
    updater = SelfUpdater(home, channel=channel)
    current = updater.current()
    assert current.version == "0.1.5"

    def provider(repository, *, verifier):
        assert repository == TOAST
        bound = GitHubReleasesProvider(repository, verifier=verifier)
        bound.api_opener = bound.asset_opener = CandidateTransport(bound, catalog, seed)
        return bound

    approved = []

    class TrialSession:
        def __init__(self):
            self.current = current
            self.file = scope / "source-ui" / "fixture.json"

        def newer(self, app):
            from southpaw_tools.managed_update import ManagedSession
            return ManagedSession.newer(self, app)

        def prepare(self, expected, cancel):
            return updater.prepare(provider(TOAST, verifier=updater.verifier), expected=expected, cancel=cancel)

        def handoff(self, transaction):
            # The fixture has no old native GUI PID. Preserve the real approval
            # journal and let the unchanged native Bootstrap worker apply it.
            updater.request_apply(transaction, approved=True)
            approved.append(transaction)

    app = QApplication([])
    with patch("southpaw_tools.ui.GitHubReleasesProvider", side_effect=provider), patch.object(
        CatalogVerifier, "bundled", side_effect=lambda p: CatalogVerifier(channel["policy"], p)
    ):
        window = MainWindow(AppPaths(data), catalog_path=seed / "catalog.json", auto_connect=False,
                            github_repository=TOAST, managed_session=TrialSession())
        window.setWindowTitle("SPENT03 fixture | Toast 0.1.5 | " + window.windowTitle())
        window.show()
        window.refresh()
        with updater._runtime_lock():
            result = app.exec()
    if result != 20 or len(approved) != 1:
        raise SystemExit("No update approved. Candidate did not apply.")
    marker = scope / "bridge-approval.json"
    with marker.open("x", encoding="utf-8") as stream:
        json.dump({"transaction": approved[0], "source_gui_exit": result}, stream)
    subprocess.run([str(program / "CGLBootstrap.exe"), "worker", "--managed", "--home",
                    str(home), "--transaction", approved[0]], cwd=program, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["button", "stage-rod"])
    parser.add_argument("--scope", type=Path, required=True, help="Dedicated preexisting SPENT03 fixture root, containing P and D")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--legacy-source", type=Path, help="Checked out v0.1.5 published launcher sources for the button phase")
    args = parser.parse_args()
    if os.name != "nt" or os.environ.get("COMPUTERNAME", "").upper() != "SPENT03":
        raise SystemExit("Run only on SPENT03, using its approved isolated Windows fixture.")
    scope = args.scope.absolute()
    if scope != scope.resolve() or scope.parent != Path("C:/Dev").resolve() or not scope.name.startswith("BRIDGE-"):
        raise SystemExit("Use a dedicated C:/Dev/BRIDGE-* root.")
    program, data = scope / "P", scope / "D"
    home = program / "launcher-home"
    if any(p != p.resolve() or not p.is_dir() for p in (program, data, home)):
        raise SystemExit("Prepare isolated P, D and Toast launcher-home before running.")
    if digest(program / "CGLBootstrap.exe") != BOOT_SHA or digest(args.bundle) != BUNDLE_SHA:
        raise SystemExit("Official Bootstrap or transport SHA-256 mismatch.")
    mapping = json.loads((home / "layout.json").read_bytes())
    if Path(mapping["user_data_root"]).resolve() != data:
        raise SystemExit("The fixture must target its own D directory.")
    channel = json.loads((program / "_internal/southpaw_tools/data/managed-channel.json").read_bytes())
    if channel["repository"] != TOAST:
        raise SystemExit("The original bootstrap fixture must use Toast.")
    with zipfile.ZipFile(args.bundle) as archive:
        plan = json.loads(archive.read("candidate-plan.json"))
        label = "toast" if args.phase == "button" else "rod"
        catalog = plan[label]
        seed = scope / f"verified-{label}"
        seed.mkdir()
        for name in ("catalog.json", "catalog.sig.json", catalog["launcher"]["package_name"]):
            assert Path(name).name == name
            body = archive.read(f"{label}/{name}")
            assert {"size": len(body), "sha256": hashlib.sha256(body).hexdigest()} == catalog["assets"][name]
            (seed / name).write_bytes(body)
    if args.phase == "button":
        click_update(args, scope, seed, catalog, program, data, channel)
    else:
        # Only the unpublished Rod candidate's delivery is pre-staged. The
        # actual Toast launcher (now Bridge) must still spawn its Rod Bootstrap.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from southpaw_tools.bootstrap import WindowsUpdater
        from southpaw_tools.channel_bridge import prepare_runtime
        from southpaw_tools.managed_update import initialize

        bridge = WindowsUpdater(home, channel=channel)
        candidate = bridge.current()
        assert candidate.release_id == "toast-bridge-0.1.6"
        payload = bridge._validate_release(candidate)
        runtime = prepare_runtime(payload, home)
        rod_channel = json.loads((payload / "rod-channel.json").read_bytes())
        initialize(runtime / "launcher-home", data, seed, rod_channel)
        assert WindowsUpdater(runtime / "launcher-home", channel=rod_channel).current().to_dict() == catalog["launcher"]


if __name__ == "__main__":
    main()
