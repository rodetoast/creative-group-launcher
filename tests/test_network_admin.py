from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from southpaw_tools.admin import publish
from southpaw_tools.catalog import catalog_document, load_catalog
from southpaw_tools.common import Cancelled, LauncherError, atomic_json
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from southpaw_tools.providers import HttpProvider, InternetProvider
from southpaw_tools.server import Distribution, ServerController, make_handler
from tests.support import FakeProcesses, package, repository, temporary, TestSigner


class NetworkAdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary("southpaw-network-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source, self.app = package(self.root / "source")
        self.repo = self.root / "repo"
        repository(self.repo, self.source, self.app)
        self.signer = TestSigner(self.root)
        self.signer.publish(self.repo, [self.app], 1)
        self.verifier = self.signer.verifier(self.root / "trust/catalog-trust.json")
        self.controller = ServerController(self.repo, {"server_enabled": True, "port": 0,
                                                     "lan_enabled": False, "internet_enabled": False})
        self.controller.start()
        self.addCleanup(self.controller.stop)
        port = self.controller.servers[0].server_address[1]
        self.url = f"http://127.0.0.1:{port}"
        self.provider = HttpProvider(self.url, verifier=self.verifier)

    def test_health_catalog_version_notes_and_read_only_routes(self):
        health = self.provider.health()
        self.assertTrue(health["server_enabled"])
        self.assertFalse(health["lan_enabled"])
        self.assertFalse(health["internet_enabled"])
        self.assertEqual(self.provider.catalog(), [self.app])
        for endpoint in ("/api/apps/dummy", "/api/apps/dummy/notes"):
            with urllib.request.urlopen(self.url + endpoint) as response:
                self.assertIn("app_id", json.load(response))
        request = urllib.request.Request(self.url + "/api/publish", data=b"{}", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request)
        self.assertEqual(raised.exception.code, 405)
        for endpoint in ("/catalog.json", "/../catalog.json", "/packages/%2e%2e%2fcatalog.json"):
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(self.url + endpoint)

    def test_download_installs_then_server_off_still_launches(self):
        paths = AppPaths(self.root / "client")
        processes = FakeProcesses()
        engine = Installer(paths, processes)
        engine.install(self.app, self.provider)
        self.controller.stop()
        self.assertEqual(engine.launch("dummy"), "dummy-process")
        with self.assertRaises(LauncherError):
            self.provider.catalog()

    def test_missing_package_and_changed_server_file_rejected(self):
        file = self.repo / "packages" / self.app.package_name
        file.unlink()
        with self.assertRaises(LauncherError):
            self.provider.download(self.app, self.root / "missing.zip")
        file.write_bytes(b"wrong")
        with self.assertRaises(LauncherError):
            self.provider.download(self.app, self.root / "tampered.zip")
        self.assertFalse((self.root / "tampered.zip").exists())

    def test_unpublished_package_cannot_be_downloaded(self):
        atomic_json(self.repo / "catalog.json", catalog_document([replace(self.app, published=False)]))
        with self.assertRaises(LauncherError):
            self.provider.download(self.app, self.root / "unpublished.zip")

    def test_interrupted_http_response_cleans_partial_and_keeps_old(self):
        engine = Installer(AppPaths(self.root / "client"), FakeProcesses())
        engine.install(self.app, self.provider)
        source, new = package(self.root / "source", "r2")
        raw, signature = self.signer.pair([new], 2)
        class Truncated(BaseHTTPRequestHandler):
            def do_GET(inner):
                if inner.path in {"/api/catalog", "/api/catalog.sig"}:
                    body = raw if inner.path == "/api/catalog" else json.dumps(signature).encode()
                    inner.send_response(200)
                    inner.send_header("Content-Length", str(len(body)))
                    inner.end_headers()
                    inner.wfile.write(body)
                    return
                inner.send_response(200)
                inner.send_header("Content-Length", str(new.package_size))
                inner.end_headers()
                inner.wfile.write(source.read_bytes()[:15])
                inner.close_connection = True
            def log_message(inner, *_):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Truncated)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            bad_provider = HttpProvider(f"http://127.0.0.1:{server.server_port}", verifier=self.verifier)
            with self.assertRaises(LauncherError):
                engine.install(new, bad_provider)
            self.assertEqual(engine.installed("dummy"), self.app)
            self.assertEqual(list(engine.paths.downloads.glob("*.zip")), [])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_http_cancel_discards_download(self):
        event = threading.Event()
        with self.assertRaises(Cancelled):
            self.provider.download(self.app, self.root / "cancel.zip", lambda *_: event.set(), event)
        self.assertFalse((self.root / "cancel.zip").exists())

    def test_redirect_cannot_change_distribution_origin(self):
        class Redirect(BaseHTTPRequestHandler):
            def do_GET(inner):
                inner.send_response(302)
                inner.send_header("Location", "http://127.0.0.1:1/stolen")
                inner.end_headers()
            def log_message(inner, *_):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(LauncherError):
                HttpProvider(f"http://127.0.0.1:{server.server_port}").health()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_server_off_opens_no_listener(self):
        controller = ServerController(self.repo, {"server_enabled": False})
        controller.start()
        self.assertEqual(controller.servers, [])
        self.assertFalse(controller.status["server_enabled"])

    def test_internet_and_wildcard_bind_rejected(self):
        for config in ({"internet_enabled": True},
                       {"lan_enabled": True, "lan_host": "0.0.0.0", "lan_token": "x" * 32},
                       {"lan_enabled": True, "lan_host": "192.168.1.2", "lan_token": "short"}):
            controller = ServerController(self.repo, {"server_enabled": True, **config})
            with self.assertRaises(LauncherError):
                controller.start()
            self.assertEqual(controller.servers, [])
        with self.assertRaises(LauncherError):
            InternetProvider()
        for url in ("http://8.8.8.8:8765", "https://example.com", "http://127.0.0.1/x",
                    "http://user:pass@127.0.0.1", "http://192.168.1.2:8765"):
            with self.assertRaises(LauncherError):
                HttpProvider(url)

    def test_lan_bind_failure_rolls_back_local_listener(self):
        config = {"server_enabled": True, "port": 0, "lan_enabled": True,
                  "lan_host": "192.168.1.2", "lan_token": "x" * 32}
        controller = ServerController(self.repo, config)
        original = ThreadingHTTPServer
        created = []
        def bind(address, handler):
            if address[0] != "127.0.0.1":
                raise OSError("LAN address unavailable")
            server = original(address, handler)
            created.append(server)
            return server
        with patch("southpaw_tools.server.ThreadingHTTPServer", side_effect=bind):
            with self.assertRaises(OSError):
                controller.start()
        self.assertEqual(controller.servers, [])
        self.assertFalse(controller.status["server_enabled"])
        self.assertFalse(controller.status["lan_enabled"])
        self.assertEqual(created[0].fileno(), -1)

    def test_lan_policy_requires_token_without_opening_lan_interface(self):
        status = {"server_enabled": True, "lan_enabled": True, "internet_enabled": False}
        handler = make_handler(Distribution(self.repo), lan=True, token="x" * 32, status=status)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/health"
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(url)
            self.assertEqual(raised.exception.code, 403)
            request = urllib.request.Request(url, headers={"Authorization": "Bearer " + "x" * 32})
            with urllib.request.urlopen(request) as response:
                self.assertTrue(json.load(response)["lan_enabled"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_local_publish_requires_approval_and_is_immutable(self):
        unpublished = replace(self.app, published=False)
        atomic_json(self.repo / "catalog.json", catalog_document([unpublished]))
        (self.repo / "packages" / self.app.package_name).unlink()
        kwargs = dict(version="1.0.0", release_id="release-1", executable="Dummy.exe",
                      expected_sha256=self.app.sha256, expected_exe_sha256=self.app.executable_sha256,
                      signing_key=self.signer.path, sequence=2)
        with self.assertRaises(LauncherError):
            publish(self.repo, "dummy", self.source, approved=False, **kwargs)
        app = publish(self.repo, "dummy", self.source, approved=True, **kwargs)
        self.assertEqual(load_catalog(self.repo / "catalog.json"), [app])
        self.assertTrue((self.repo / "packages" / app.package_name).is_file())
        with self.assertRaises(LauncherError):
            publish(self.repo, "dummy", self.source, approved=True, **kwargs)

    def test_failed_catalog_publication_leaves_no_exposed_package(self):
        atomic_json(self.repo / "catalog.json", catalog_document([replace(self.app, published=False)]))
        before = (self.repo / "catalog.json").read_bytes()
        with patch("southpaw_tools.admin.atomic_json", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                publish(self.repo, "dummy", self.source, version="1.0.0", release_id="new-release",
                        executable="Dummy.exe", expected_sha256=self.app.sha256,
                        expected_exe_sha256=self.app.executable_sha256, approved=True,
                        signing_key=self.signer.path, sequence=2)
        self.assertEqual((self.repo / "catalog.json").read_bytes(), before)
        self.assertFalse((self.repo / "packages/dummy--new-release.zip").exists())


if __name__ == "__main__":
    unittest.main()
