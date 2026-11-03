"""Install approved packages in isolation via real loopback HTTP. Never run their EXEs."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from southpaw_tools.common import atomic_json, digest
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from southpaw_tools.providers import HttpProvider
from southpaw_tools.server import ServerController


def main():
    root = Path(__file__).resolve().parents[1]
    results = root / ".test-results"
    results.mkdir(exist_ok=True)
    client = results / f"approved-client-{uuid.uuid4().hex[:10]}"
    engine = Installer(AppPaths(client))
    controller = ServerController(root / "distribution", {
        "server_enabled": True, "port": 0, "lan_enabled": False, "internet_enabled": False,
    })
    rows = []
    controller.start()
    try:
        provider = HttpProvider(f"http://127.0.0.1:{controller.servers[0].server_port}")
        apps = provider.catalog()
        assert len(apps) == 5
        for app in apps:
            if not app.published:
                rows.append({"app_id": app.app_id, "installed": False,
                             "reason": app.availability_reason})
                continue
            started = time.monotonic()
            engine.install(app, provider)
            executable, cwd = engine.resolve_launch(app)
            rows.append({"app_id": app.app_id, "release_id": app.release_id,
                         "installed": True, "seconds": round(time.monotonic() - started, 3),
                         "executable": str(executable.relative_to(client)),
                         "cwd": str(cwd.relative_to(client)),
                         "exe_sha256": digest(executable), "exe_started": False,
                         "required_resources_verified": len(app.required_paths)})
        # Real UI fetches the real API and displays the actual isolated installations.
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from PySide6.QtTest import QTest
        from southpaw_tools.ui import MainWindow
        application = QApplication.instance() or QApplication([])
        window = MainWindow(AppPaths(client), auto_connect=False)
        window.config = {"server_url": provider.base_url}
        window.show()
        window.refresh()
        deadline = time.monotonic() + 15
        while window.task is not None and time.monotonic() < deadline:
            application.processEvents()
            time.sleep(0.005)
        assert window.task is None and window.online, window.message.text()
        assert window.primary.text() == "실행"
        assert window.primary.isEnabled()
        screenshot = root / "docs/screenshots/launcher-installed.png"
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        assert window.grab().save(str(screenshot))
        window.close()
        application.processEvents()
    finally:
        controller.stop()
    # Resolve from saved metadata with no settings or live server.
    offline = Installer(AppPaths(client))
    for app in offline.installed_apps():
        offline.resolve_launch(app)
    report = {"installed_count": sum(row["installed"] for row in rows),
              "tools_started": 0, "client_root": str(client), "offline_resolution": "PASS",
              "network": "127.0.0.1 only; listener stopped", "packages": rows}
    atomic_json(root / "docs/approved-install-verification.local.json", report)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
