"""Run the suite and retain a machine-readable result without touching other tools."""
from __future__ import annotations

import json
import platform
import sys
import time
import unittest
from pathlib import Path

from southpaw_tools.common import atomic_json


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / ".test-results"
    output.mkdir(exist_ok=True)
    suite = unittest.defaultTestLoader.discover(str(root / "tests"), top_level_dir=str(root))
    started = time.monotonic()
    with (output / "unit-tests.log").open("w", encoding="utf-8") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    import PySide6
    from PySide6.QtCore import qVersion
    report = {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "passed": result.wasSuccessful(),
              "seconds": round(time.monotonic() - started, 3), "platform": platform.platform(),
              "python": sys.version.split()[0], "pyside6": PySide6.__version__, "qt": qVersion(),
              "existing_tools_started": 0, "windows_use": 0}
    atomic_json(output / "unit-tests.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not result.wasSuccessful():
        print((output / "unit-tests.log").read_text(encoding="utf-8")[-12000:])
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
