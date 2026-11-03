"""Limited lab checks: real loopback, mocked LAN binds; never opens a LAN socket."""
from __future__ import annotations

import contextlib
import argparse
import io
import json
from pathlib import Path
import socket
import threading
import urllib.error
import urllib.request
from unittest.mock import patch

from audit.lan_lab import PROJECT, prepare, publish_fixture, validate
from southpaw_tools.catalog import catalog_document, load_catalog
from southpaw_tools.common import LauncherError, atomic_json, read_json
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from southpaw_tools.providers import HttpProvider
from southpaw_tools.server import Distribution, ServerController, make_handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT / ".test-results/lan-lab-verification")
    root = parser.parse_args().root
    prepare(root)
    config = read_json(root / "server.local.json")
    engine = Installer(AppPaths(root / "client"))
    evidence = []
    def record(name, **details):
        evidence.append({"check": name, **details})
    def status(url, token=""):
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code
    forbidden = load_catalog(PROJECT / "distribution/catalog.json")  # Metadata only.
    controller = ServerController(root / "repository", config)
    try:
        controller.start()  # Prepared config is explicitly LAN OFF, port8765.
        assert [s.server_address for s in controller.servers] == [("127.0.0.1", 8765)]
        record("LAN_OFF_real_binding", address="127.0.0.1", port=8765)
        provider = HttpProvider("http://127.0.0.1:8765")
        app = provider.catalog()[0]
        assert app.app_id == "lan-smoke"
        for original in forbidden:
            assert status(f"{provider.base_url}/api/apps/{original.app_id}") == 404
            if original.package_name:
                assert status(f"{provider.base_url}/packages/{original.package_name}") != 200
        for path in ("/packages/%2e%2e%2f%2e%2e%2fdistribution/catalog.json", "/catalog.json", "/inputs/r1.zip"):
            assert status(provider.base_url + path) != 200
        record("production_apps_and_files_unreachable", app_ids_checked=5, approved_package_names_checked=4)
        engine.install(app, provider)
        _, cwd1 = engine.resolve_launch(app)
        (cwd1 / "settings.json").write_text("keep-dummy-settings")
        (cwd1 / "user-work.txt").write_text("keep-dummy-work")
    finally:
        controller.stop()
    with socket.socket() as probe:
        probe.settimeout(2)
        assert probe.connect_ex(("127.0.0.1", 8765)) != 0
    assert engine.launch("lan-smoke").wait(timeout=10) == 0
    record("v1_install_then_actual_offline_execution", exit_code=0)

    publish_fixture(root, "r2")  # Existing admin.publish; no second publisher.
    validate(root)
    leaked = root / "client-bundle/settings.json"
    leaked.write_text('{"fixture": "not a real secret"}', encoding="utf-8")
    try:
        try: validate(root)
        except LauncherError: pass
        else: raise AssertionError("Client settings were accepted")
    finally:
        leaked.unlink()
    controller = ServerController(root / "repository", config)
    try:
        controller.start()  # Proves8765 can be reused after stop.
        provider = HttpProvider("http://127.0.0.1:8765")
        app2 = provider.catalog()[0]
        assert app2.version == app.version and app2.is_new_release(app)
        engine.install(app2, provider)
    finally:
        controller.stop()
    assert engine.launch("lan-smoke").wait(timeout=10) == 0
    _, cwd2 = engine.resolve_launch(app2)
    assert (cwd2 / "settings.json").read_text() == "keep-dummy-settings"
    assert (cwd1 / "user-work.txt").read_text() == "keep-dummy-work"
    record("v2_admin_publish_update_then_actual_offline_execution", exit_code=0,
           same_version_different_release=True, settings_preserved=True, old_work_preserved=True)

    # Real token policy over LOOPBACK only; not a LAN end-to-end claim.
    logs = io.StringIO()
    handler = make_handler(Distribution(root / "repository"), lan=True,
                           token=config["lan_token"], status={"lan_enabled": True})
    from http.server import ThreadingHTTPServer
    with contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/health"
            assert status(url) == 403
            assert status(url, "invalid-dummy-token") == 403
            assert status(url, config["lan_token"]) == 200
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)
    assert config["lan_token"] not in logs.getvalue()
    record("token_policy_on_loopback", missing=403, wrong=403, valid=200, token_absent_from_logs=True)

    # Pure fake listener: capture intended addresses, with NO socket creation.
    addresses = []
    class FakeListener:
        def __init__(self, address, handler):
            self.server_address = address
            addresses.append(address)
            self.done = threading.Event()
        def serve_forever(self): self.done.wait(3)
        def shutdown(self): self.done.set()
        def server_close(self): pass
    lan_config = {**config, "lan_enabled": True, "lan_host": "192.168.50.20"}
    with patch("southpaw_tools.server.ThreadingHTTPServer", FakeListener):
        fake = ServerController(root / "repository", lan_config)
        try:
            fake.start()
            assert addresses == [("127.0.0.1", 8765), ("192.168.50.20", 8765)]
            lan_config["lan_enabled"] = False
            assert fake.status["lan_enabled"]  # Editing config is not a live toggle.
        finally:
            fake.stop()
        addresses.clear()
        fake.start()
        try:
            assert addresses == [("127.0.0.1", 8765)] and not fake.status["lan_enabled"]
        finally:
            fake.stop()
    record("LAN_ON_bind_and_restart_contract_mock_only", real_lan_listener=False)

    # Guard rejection of unexpected archive and catalog, restored in this lab only.
    rogue = root / "repository/packages/not-a-dummy.zip"
    rogue.write_bytes(b"harmless guard sentinel")
    try:
        try: validate(root)
        except LauncherError: pass
        else: raise AssertionError("Unexpected ZIP was accepted")
    finally:
        rogue.unlink()
    catalog = root / "repository/catalog.json"
    saved = read_json(catalog)
    try:
        atomic_json(catalog, catalog_document([app2, forbidden[0]]))
        try: validate(root)
        except LauncherError: pass
        else: raise AssertionError("Production app was accepted")
    finally:
        atomic_json(catalog, saved)
    validate(root)
    # LAN config alone must not start anything through the guarded entry point.
    atomic_json(root / "server.local.json", {**config, "lan_enabled": True, "lan_host": "192.168.50.20"})
    try:
        from audit.lan_lab import main as lab_main
        with patch("sys.argv", ["lan_lab", "serve", "--root", str(root)]), \
             patch("audit.lan_lab.server_main") as backend, contextlib.redirect_stdout(io.StringIO()):
            assert lab_main() == 1
            backend.assert_not_called()
    finally:
        atomic_json(root / "server.local.json", config)
    record("dummy_guard_and_separate_lan_approval_gate", rejected=True)
    report = {"passed": True, "checks": evidence, "real_lan_connection_tested": False,
              "lan_listeners_opened": 0, "existing_tools_started": 0,
              "dummy_executions": 2, "windows_use": 0, "managed_rollback_implemented": False}
    atomic_json(PROJECT / ".test-results/lan-preparation-checks.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
