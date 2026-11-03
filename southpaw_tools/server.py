"""Read-only developer-PC distribution API. No publishing endpoint exists."""
from __future__ import annotations

import argparse
import hmac
import ipaddress
import json
import signal
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .catalog import catalog_document, load_catalog
from .common import LauncherError, digest, inside, read_json
from .providers import private_address

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Distribution:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self._cache = {}

    def apps(self):
        return load_catalog(self.root / "catalog.json")

    def package(self, name: str):
        app = next((a for a in self.apps() if a.published and a.package_name == name), None)
        if app is None:
            raise LauncherError("게시된 패키지가 아닙니다.")
        file = inside(self.root / "packages", name)
        if not file.is_file():
            raise LauncherError("배포 패키지 미확인")
        status = file.stat()
        stamp = (status.st_size, status.st_mtime_ns, status.st_ctime_ns)
        cached = self._cache.get(name)
        if cached != (stamp, app.sha256):
            if status.st_size != app.package_size or digest(file) != app.sha256:
                raise LauncherError("게시 파일과 카탈로그가 불일치합니다.")
            self._cache[name] = (stamp, app.sha256)
        return file, app


def make_handler(distribution: Distribution, *, lan: bool, token: str, status: dict):
    class Handler(BaseHTTPRequestHandler):
        server_version = "SouthpawTools/0.1.0"
        sys_version = ""

        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def log_message(self, format, *args):
            # Never log Authorization headers, query tokens or user paths.
            pass

        def _json(self, value, code=200):
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self):
            address = self.client_address[0]
            if lan:
                allowed = private_address(address)
                header = self.headers.get("Authorization", "")
                allowed = allowed and bool(token) and hmac.compare_digest(header, f"Bearer {token}")
            else:
                allowed = ipaddress.ip_address(address).is_loopback
            if not allowed:
                self._json({"error": "접근 권한 없음"}, 403)
            return allowed

        def do_POST(self):
            self._json({"error": "읽기 전용 서버"}, 405)

        do_PUT = do_POST
        do_DELETE = do_POST
        do_PATCH = do_POST

        def do_GET(self):
            if not self._authorized():
                return
            url = urllib.parse.urlsplit(self.path)
            if url.query or url.fragment or len(self.path) > 512:
                self._json({"error": "잘못된 요청"}, 400)
                return
            path = urllib.parse.unquote(url.path)
            try:
                if path == "/api/health":
                    self._json({"service": "southpaw-tools", "api_version": 1, **status})
                elif path == "/api/catalog":
                    self._json(catalog_document(distribution.apps()))
                elif path.startswith("/api/apps/"):
                    parts = path.split("/")
                    if len(parts) not in {4, 5} or (len(parts) == 5 and parts[4] != "notes"):
                        self._json({"error": "찾을 수 없음"}, 404)
                        return
                    app = next((a for a in distribution.apps() if a.app_id == parts[3]), None)
                    if app is None:
                        self._json({"error": "찾을 수 없음"}, 404)
                    elif len(parts) == 5:
                        self._json({"app_id": app.app_id, "release_id": app.release_id,
                                    "release_notes": app.release_notes})
                    else:
                        self._json(app.to_dict())
                elif path.startswith("/packages/") and path.count("/") == 2:
                    file, app = distribution.package(path.removeprefix("/packages/"))
                    with file.open("rb") as stream:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/zip")
                        self.send_header("Content-Length", str(app.package_size))
                        self.send_header("X-Content-Type-Options", "nosniff")
                        self.end_headers()
                        while chunk := stream.read(256 * 1024):
                            self.wfile.write(chunk)
                else:
                    self._json({"error": "찾을 수 없음"}, 404)
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                return
            except (LauncherError, OSError, ValueError):
                self._json({"error": "배포 파일 또는 등록 정보 확인 실패"}, 409)

    return Handler


class ServerController:
    def __init__(self, root: Path, config: dict):
        self.distribution = Distribution(root)
        self.config = config
        self.servers: list[ThreadingHTTPServer] = []
        self.threads: list[threading.Thread] = []
        self.status = {"server_enabled": False, "lan_enabled": False,
                       "internet_enabled": False, "internet_status": "미구성"}

    def start(self):
        if self.servers:
            raise LauncherError("서버가 이미 실행 중입니다.")
        for field in ("server_enabled", "lan_enabled", "internet_enabled"):
            if type(self.config.get(field, False)) is not bool:
                raise LauncherError("서버 토글은 true/false여야 합니다.")
        if self.config.get("internet_enabled", False):
            raise LauncherError("인터넷 배포 미구성: 외부 공개를 활성화할 수 없습니다.")
        if not self.config.get("server_enabled", True):
            return
        self.distribution.apps()  # Validate before opening any listener.
        port = self.config.get("port", 8765)
        if type(port) is not int or not 0 <= port <= 65535:
            raise LauncherError("잘못된 서버 포트")
        endpoints = [("127.0.0.1", False, "")]
        if self.config.get("lan_enabled", False):
            host, token = self.config.get("lan_host", ""), self.config.get("lan_token", "")
            try:
                ip = ipaddress.ip_address(host)
            except ValueError as exc:
                raise LauncherError("LAN에 바인딩할 개발 PC의 사설 IPv4를 지정하세요.") from exc
            if (ip.version != 4 or ip.is_loopback or not private_address(host)
                    or not isinstance(token, str) or len(token) < 24
                    or any(ord(c) < 33 or ord(c) > 126 for c in token)):
                raise LauncherError("LAN에는 정확한 사설 IPv4와 24자 이상의 토큰이 필요합니다.")
            endpoints.append((host, True, token))
        try:
            for host, lan, token in endpoints:
                handler = make_handler(self.distribution, lan=lan, token=token, status=self.status)
                server = ThreadingHTTPServer((host, port), handler)
                server.daemon_threads = True
                server.block_on_close = False
                self.servers.append(server)
            self.status.update(server_enabled=True, lan_enabled=len(endpoints) == 2)
            for server in self.servers:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                self.threads.append(thread)
        except Exception:
            for server in self.servers:
                server.server_close()
            self.servers.clear()
            self.status.update(server_enabled=False, lan_enabled=False)
            raise

    def stop(self):
        for server in self.servers:
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join(timeout=2)
        self.servers.clear()
        self.threads.clear()
        self.status.update(server_enabled=False, lan_enabled=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT / "distribution")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    try:
        config = read_json(args.config or args.root / "server.json")
        controller = ServerController(args.root, config)
        controller.start()
        if not controller.servers:
            print("서버 OFF — 열린 배포 포트 없음")
            return 0
        for server in controller.servers:
            print(f"Southpaw Tools: http://{server.server_address[0]}:{server.server_address[1]}", flush=True)
        print("인터넷 OFF / 미구성. 종료: Ctrl+C", flush=True)
        stop = threading.Event()
        def request_stop(*_):
            stop.set()
        signal.signal(signal.SIGINT, request_stop)
        signal.signal(signal.SIGTERM, request_stop)
        try:
            stop.wait()
        finally:
            controller.stop()
        return 0
    except (LauncherError, OSError) as exc:
        print(f"서버 시작 실패: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
