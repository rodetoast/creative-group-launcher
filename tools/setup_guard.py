"""Private NSIS helper. Never launches a company application."""
import argparse
import json
from pathlib import Path
import sys

from southpaw_tools.common import LauncherError
from southpaw_tools.setup_support import check, shortcut, stamp, verify_payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["check", "uninstall-check", "stamp", "shortcut", "check-shortcut", "remove-shortcut", "verify", "verify-removed"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--link", type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads((Path(sys._MEIPASS) / "setup-manifest.json").read_bytes())
        if args.action in {"check", "uninstall-check"}:
            if args.data is None:
                raise LauncherError("사용자 데이터 경로가 없습니다.")
            check(args.root, args.data, manifest, uninstall=args.action == "uninstall-check")
        elif args.action == "stamp":
            if args.data is None:
                raise LauncherError("사용자 데이터 경로가 없습니다.")
            stamp(args.root, args.data, manifest)
        elif args.action in {"verify", "verify-removed"}:
            verify_payload(args.root, manifest, removed=args.action == "verify-removed")
        else:
            if args.link is None:
                raise LauncherError("바로가기 경로가 없습니다.")
            shortcut(args.link, args.root, remove=args.action == "remove-shortcut", check_only=args.action == "check-shortcut")
        print("완료")
        return 0
    except (LauncherError, OSError, ValueError, TypeError) as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
