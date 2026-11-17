from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import nullcontext
from pathlib import Path

from . import __version__
from .branding import DISPLAY_NAME


def main(argv=None):
    parser = argparse.ArgumentParser(description=DISPLAY_NAME)
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--check", action="store_true", help="Isolated offscreen UI smoke check; no tool starts")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--github-repository", help="Explicit OWNER/REPO; bundled trust policy still applies")
    parser.add_argument("--github-test-policy", type=Path, help="Explicit public test policy; isolated .test-results paths only")
    parser.add_argument("--session-file", type=Path)
    args = parser.parse_args(argv)
    if args.github_test_policy and (args.data_dir is None or not args.github_repository):
        parser.error("시험 공개키에는 --data-dir와 --github-repository를 명시해야 합니다.")
    if args.session_file and any((args.version, args.check, args.data_dir, args.catalog, args.screenshot,
                                  args.github_repository, args.github_test_policy)):
        parser.error("Bootstrap 세션에는 별도 실행 옵션을 지정할 수 없습니다.")
    if args.version:
        print(f"{DISPLAY_NAME} v{__version__}")
        return 0
    if args.check:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from .common import LauncherError
    try:
        session = None
        if args.session_file:
            from .managed_update import ManagedSession
            session = ManagedSession(args.session_file, __version__)
        lease = session.updater._runtime_lock() if session and session.mode == "normal" else nullcontext()
        with lease:
            if session and session.updater.current() != session.current:
                raise LauncherError("시작 직전 활성 런처가 바뀌었습니다.")
            return run_window(args, session)
    except (LauncherError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"런처 시작 실패: {exc}")
        return 1


def run_window(args, session):
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication
    from .ui import DATA, ASSETS, MainWindow
    from .branding import ICON_FILENAME
    from .paths import AppPaths
    from .common import LauncherError

    app = QApplication([sys.argv[0]])
    app.setOrganizationName("SouthpawGames")
    app.setApplicationName("SouthpawToolsLauncher")
    app.setApplicationDisplayName(DISPLAY_NAME)
    app.setWindowIcon(QIcon(str(ASSETS / ICON_FILENAME)))
    import tempfile
    # Diagnostics never read/write the real user's launcher state.
    temporary = None
    if args.check and not args.data_dir:
        check_root = Path(__file__).resolve().parents[1] / ".test-results" / "ui"
        check_root.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="check-", dir=check_root)
    root = session.data_root if session else args.data_dir or (Path(temporary.name) if temporary else AppPaths.default().root)
    health = session and session.mode == "health"
    window = MainWindow(AppPaths(root), catalog_path=args.catalog or DATA, auto_connect=not args.check and not session,
                        github_repository=session.channel["repository"] if session else args.github_repository,
                        github_test_policy=args.github_test_policy, managed_session=session)
    if not health:
        window.show()
    if session:
        if window.catalog_verifier.policy != session.channel["policy"]:
            raise LauncherError("런처 공개키가 Bootstrap 채널과 일치하지 않습니다.")
        window.winId()
        confirmed = False
        timer = QTimer(window)
        def poll():
            nonlocal confirmed
            try:
                if not confirmed and session.command("confirm"):
                    session.acknowledge("confirmed")
                    confirmed = True
                    if not health:
                        QTimer.singleShot(0, window.refresh)
                if session.command("stop") and not window.task:
                    session.acknowledge("stopped")
                    app.exit(0)
            except (LauncherError, OSError, ValueError, TypeError):
                app.exit(11)
        timer.timeout.connect(poll)
        timer.start(80)
        QTimer.singleShot(0, lambda: session.acknowledge("ready"))
    def capture():
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            if not window.grab().save(str(args.screenshot)):
                raise LauncherError("화면 이미지 저장 실패")
        if args.check:
            print(json.dumps({"version": __version__, "apps": window.list.count(),
                              "ui": "created", "tools_started": 0,
                              "device_pixel_ratio": window.devicePixelRatioF(),
                              "size": [window.width(), window.height()]}, ensure_ascii=False))
            app.quit()
    if args.check or args.screenshot:
        QTimer.singleShot(250, capture)
    result = app.exec()
    if temporary:
        temporary.cleanup()
    return result

if __name__ == "__main__":
    raise SystemExit(main())
