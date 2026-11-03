"""Read-only implementation audit: isolated dummy fixtures, no real tool execution.

Exit zero means observations reproduced, NOT that all safety properties passed.
Run from repository root: python -B -m audit.mvp_probes
"""
from __future__ import annotations

import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from southpaw_tools.catalog import catalog_document
from southpaw_tools.common import LauncherError, app_lock, atomic_json, digest
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from southpaw_tools.providers import HttpProvider
from southpaw_tools.server import ServerController
from tests.support import FakeProcesses, LocalProvider, package, repository, temporary


def rejected(action, exception=Exception):
    try:
        action()
    except exception as exc:
        return str(exc)
    raise AssertionError("Expected rejection did not occur")


def main():
    observations = []
    def record(name, gap, **evidence):
        observations.append(dict(name=name, safety_gap=gap, **evidence))

    with temporary("mvp-audit-") as folder:
        root = Path(folder)
        first, r1 = package(root / "sources")
        second, r2 = package(root / "sources", "r2")
        def installed(name):
            engine = Installer(AppPaths(root / name), FakeProcesses())
            engine.install(r1, LocalProvider(first))
            return engine

        engine = installed("uninstall")
        exe, cwd = engine.resolve_launch(r1)
        (cwd / "settings.json").write_text("user-data", encoding="utf-8")
        unlink = Path.unlink
        def fail_asset(path, *args, **kwargs):
            if path == cwd / "asset.json":
                raise PermissionError("simulated locked asset")
            return unlink(path, *args, **kwargs)
        with patch.object(Path, "unlink", fail_asset):
            error = rejected(lambda: engine.uninstall("dummy"))
        assert engine.installed("dummy") == r1 and not exe.exists()
        assert (cwd / "settings.json").read_text(encoding="utf-8") == "user-data"
        record("partial_uninstall", True, error=error,
               launch_error=rejected(lambda: engine.resolve_launch(r1)),
               reinstall_error=rejected(lambda: engine.install(r1, LocalProvider(first))),
               active_pointer_remains=True, executable_deleted=True, user_settings_preserved=True)

        engine = installed("crash")
        with patch.object(engine, "_activate", side_effect=SystemExit("simulated abrupt exit before activation")):
            rejected(lambda: engine.install(r2, LocalProvider(second)), SystemExit)
        assert engine.installed("dummy") == r1
        engine.resolve_launch(r1)
        assert engine.paths.release("dummy", "r2").exists()
        record("orphan_after_interruption", True, previous_launch_path_valid=True,
               retry_error=rejected(lambda: engine.install(r2, LocalProvider(second))))

        engine = installed("cleanup")
        def fail_download_cleanup(path, *args, **kwargs):
            if path.parent == engine.paths.downloads:
                raise PermissionError("simulated download cleanup denial")
            return unlink(path, *args, **kwargs)
        with patch.object(Path, "unlink", fail_download_cleanup):
            error = rejected(lambda: engine.install(r2, LocalProvider(second)))
        assert engine.installed("dummy") == r2
        engine.resolve_launch(r2)
        record("post_commit_cleanup_error", True, error=error, actual_active_release="r2")

        engine = installed("rollback")
        engine.install(r2, LocalProvider(second))
        record("managed_rollback_missing", True,
               error=rejected(lambda: engine.install(r1, LocalProvider(first))),
               old_payload_retained=engine.paths.release("dummy", "r1").exists())
        with app_lock(engine.paths.lock("dummy")):
            error = rejected(lambda: engine.launch("dummy"))
        assert not engine.processes.calls
        record("launch_during_transaction_lock", False, error=error, fake_process_starts=0)

        # Real extraction failure after correct outer ZIP hash (CRC must fail).
        import hashlib
        import zipfile
        broken = root / "bad-crc.zip"
        exe_bytes = b"MZ harmless CRC fixture"
        with zipfile.ZipFile(broken, "w", zipfile.ZIP_STORED) as archive:
            archive.writestr("Dummy.exe", exe_bytes)
            archive.writestr("asset.json", b"CRC_SENTINEL_DATA")
        broken.write_bytes(broken.read_bytes().replace(b"CRC_SENTINEL_DATA", b"CRC_CORRUPTED_DAT"))
        bad = replace(r2, sha256=digest(broken), package_size=broken.stat().st_size,
                      executable_sha256=hashlib.sha256(exe_bytes).hexdigest())
        engine = installed("crc")
        error = rejected(lambda: engine.install(bad, LocalProvider(broken)))
        assert engine.installed("dummy") == r1
        engine.resolve_launch(r1)
        assert not engine.paths.release("dummy", "r2").exists()
        record("crc_extraction_failure", False, error=error, previous_release_valid=True)

        # Replace a catalog AND ZIP directly; no admin CLI or signature used.
        engine = installed("catalog")
        repository(root / "server", second, r2)
        controller = ServerController(root / "server", {"server_enabled": True, "port": 0})
        controller.start()
        try:
            port = controller.servers[0].server_address[1]
            provider = HttpProvider(f"http://127.0.0.1:{port}")
            remote = provider.catalog()[0]
            engine.install(remote, provider)
            assert engine.installed("dummy") == r2
            record("unsigned_catalog_and_package_accepted", True, transport="loopback HTTP",
                   admin_cli_used=False, new_release="r2", existing_tools_started=0)
        finally:
            controller.stop()

        # UI-only fault conditions; no Windows Use, no executable starts.
        from PySide6.QtCore import QEventLoop, QTimer
        from PySide6.QtWidgets import QApplication
        from southpaw_tools.ui import MainWindow
        application = QApplication.instance() or QApplication([])
        engine = installed("ui")
        catalog = root / "ui-catalog.json"
        atomic_json(catalog, catalog_document([r2]))
        window = MainWindow(engine.paths, catalog_path=catalog, installer=engine, auto_connect=False)
        try:
            window.online = True
            window.server_status.setText("● 서버 연결됨 · LAN OFF / 인터넷 미구성")
            def failed_download(progress, cancel):
                raise LauncherError("simulated server disconnected during download")
            window._begin("업데이트", failed_download, lambda result: None)
            loop = QEventLoop()
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            window.task.finished.connect(loop.quit)
            timer.start(8000)
            loop.exec()
            timer.stop()
            assert window.task is None and window.online
            record("ui_download_failure_retains_connected_state", True,
                   server_label=window.server_status.text(), message=window.message.text(),
                   primary_action=window.primary.text())
            window.apps = [replace(r1, sha256="f" * 64)]
            window.render()
            assert not window.primary.isEnabled()
            engine.resolve_launch(r1)
            record("ui_metadata_conflict_blocks_valid_offline_install", True,
                   displayed_installed_version=window.info["설치 버전"].text(),
                   primary_enabled=False, engine_offline_path_valid=True)
        finally:
            window.close()
            window.deleteLater()
            application.processEvents()

    report = dict(observations_reproduced=len(observations),
                  safety_gaps=sum(item["safety_gap"] for item in observations),
                  existing_tools_started=0, lan_listeners_opened=0, windows_use=0,
                  observations=observations)
    atomic_json(Path(".test-results/mvp-audit-probes.json"), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
