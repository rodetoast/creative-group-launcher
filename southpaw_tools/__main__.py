from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(description="Southpaw Tools Launcher")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--check", action="store_true", help="Isolated offscreen UI smoke check; no tool starts")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args(argv)
    if args.version:
        print(f"Southpaw Tools Launcher v{__version__}")
        return 0
    if args.check:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from .ui import DATA, MainWindow
    from .paths import AppPaths
    from .common import LauncherError
    try:
        app = QApplication([sys.argv[0]])
        app.setOrganizationName("SouthpawGames")
        app.setApplicationName("SouthpawToolsLauncher")
        import tempfile
        # Diagnostics never read/write the real user's launcher state.
        temporary = None
        if args.check and not args.data_dir:
            check_root = Path(__file__).resolve().parents[1] / ".test-results" / "ui"
            check_root.mkdir(parents=True, exist_ok=True)
            temporary = tempfile.TemporaryDirectory(prefix="check-", dir=check_root)
        root = args.data_dir or (Path(temporary.name) if temporary else AppPaths.default().root)
        window = MainWindow(AppPaths(root), catalog_path=args.catalog or DATA, auto_connect=not args.check)
        window.show()
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
    except (LauncherError, OSError) as exc:
        print(f"런처 시작 실패: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
