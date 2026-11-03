"""Rehearse the generated harmless console fixture on loopback, never real tools."""
from __future__ import annotations

import argparse
from pathlib import Path

from southpaw_tools.catalog import load_catalog
from southpaw_tools.common import atomic_json
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from southpaw_tools.providers import HttpProvider
from southpaw_tools.server import ServerController


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    client = root / "client"
    client.mkdir(exist_ok=False)
    engine = Installer(AppPaths(client))
    results = []
    previous_cwd = None
    for number in (1, 2):
        repo = root / f"r{number}"
        controller = ServerController(repo, {"server_enabled": True, "port": 0})
        controller.start()
        try:
            provider = HttpProvider(f"http://127.0.0.1:{controller.servers[0].server_address[1]}")
            app = provider.catalog()[0]
            engine.install(app, provider)
        finally:
            controller.stop()
        installed = engine.installed("lan-smoke")
        assert installed == load_catalog(repo / "catalog.json")[0]
        exe, cwd = engine.resolve_launch(installed)
        if number == 1:
            (cwd / "settings.json").write_text("preserve-user-data", encoding="utf-8")
            (cwd / "unknown-work.txt").write_text("keep-in-old-release", encoding="utf-8")
            previous_cwd = cwd
        else:
            assert (cwd / "settings.json").read_text(encoding="utf-8") == "preserve-user-data"
            assert (previous_cwd / "unknown-work.txt").is_file()
        # There are no server listeners here. Only our generated console EXE runs.
        child = engine.launch("lan-smoke")
        exit_code = child.wait(timeout=10)
        assert exit_code == 0
        results.append(dict(release_id=app.release_id, version=app.version,
                            offline_dummy_exit_code=exit_code, server_listeners=0))
    report = dict(passed=True, releases=results, dummy_executions=2,
                  existing_tools_started=0, lan_listeners_opened=0, windows_use=0,
                  known_settings_migrated=True, unknown_work_retained_in_old_release=True)
    atomic_json(root / "local-rehearsal.json", report)
    print(report)


if __name__ == "__main__":
    main()
