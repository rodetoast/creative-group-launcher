from __future__ import annotations

import hashlib
import ipaddress
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Protocol

from .archive import check_cancel
from .catalog import AppRelease, parse_catalog
from .common import LauncherError


class Provider(Protocol):
    def catalog(self) -> list[AppRelease]: ...
    def health(self) -> dict: ...
    def download(self, app: AppRelease, target: Path, progress: Callable[[int, int], None],
                 cancel: threading.Event | None = None) -> None: ...


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LauncherError("배포 서버의 리다이렉트는 허용하지 않습니다.")


def private_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return ip.is_loopback or any(ip in network for network in (
        ipaddress.ip_network("10.0.0.0/8"), ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
    ) if ip.version == network.version)


class HttpProvider:
    """Trusted local/dummy LAN transport, not publisher authentication.

    Catalogs are unsigned and HTTP does not authenticate the server. Matching
    SHA-256 values detect corruption, not a coordinated catalog/package change.
    General team distribution remains blocked pending the security design in
    docs/CATALOG_TRUST_DESIGN.md; no signing keys belong in this provider.
    """
    def __init__(self, base_url: str, token: str = "", *, lan_enabled: bool = False):
        url = urllib.parse.urlsplit(base_url)
        if (url.scheme != "http" or not url.hostname or url.path not in {"", "/"}
                or url.query or url.fragment or url.username or url.password):
            raise LauncherError("로컬/LAN 서버 주소는 http://IP:포트 형식이어야 합니다.")
        host = "127.0.0.1" if url.hostname.lower() == "localhost" else url.hostname
        if not private_address(host):
            raise LauncherError("인터넷 배포는 미구성입니다. 로컬 또는 사설 IP만 지원합니다.")
        is_loopback = ipaddress.ip_address(host).is_loopback
        if not is_loopback and not lan_enabled:
            raise LauncherError("LAN 연결을 먼저 명시적으로 활성화하세요.")
        if not is_loopback and not token:
            raise LauncherError("LAN 연결에는 배포 토큰이 필요합니다.")
        try:
            port = url.port or 8765
        except ValueError as exc:
            raise LauncherError("잘못된 서버 포트") from exc
        self.base_url = f"http://{'[' + host + ']' if ':' in host else host}:{port}"
        self.token = token
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def _open(self, path: str):
        request = urllib.request.Request(self.base_url + path, headers={
            "Authorization": f"Bearer {self.token}", "User-Agent": "SouthpawTools/0.1.0",
        })
        try:
            return self.opener.open(request, timeout=4)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise LauncherError(f"배포 서버 연결 실패: {exc}") from exc

    def _json(self, path: str) -> dict:
        try:
            with self._open(path) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise LauncherError("서버 응답이 너무 큽니다.")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError("object required")
            return result
        except (ValueError, OSError) as exc:
            raise LauncherError(f"잘못된 서버 응답: {exc}") from exc

    def health(self) -> dict:
        result = self._json("/api/health")
        if result.get("service") != "southpaw-tools" or result.get("api_version") != 1:
            raise LauncherError("호환되지 않는 배포 서버")
        return result

    def catalog(self) -> list[AppRelease]:
        return parse_catalog(self._json("/api/catalog"))

    def download(self, app: AppRelease, target: Path, progress=lambda done, total: None,
                 cancel: threading.Event | None = None) -> None:
        if not app.published:
            raise LauncherError("배포 패키지 미확인")
        done, h, started = 0, hashlib.sha256(), time.monotonic()
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            check_cancel(cancel)
            with self._open("/packages/" + urllib.parse.quote(app.package_name, safe="")) as response:
                length = response.headers.get("Content-Length")
                if length is None or not length.isdecimal() or int(length) != app.package_size:
                    raise LauncherError("서버 패키지 크기와 카탈로그가 다릅니다.")
                with target.open("xb") as output:
                    while True:
                        check_cancel(cancel)
                        if time.monotonic() - started > 600:
                            raise LauncherError("다운로드 제한 시간을 초과했습니다.")
                        chunk = response.read(256 * 1024)
                        if not chunk:
                            break
                        done += len(chunk)
                        if done > app.package_size:
                            raise LauncherError("서버 패키지 크기 초과")
                        h.update(chunk)
                        output.write(chunk)
                        progress(done, app.package_size)
            check_cancel(cancel)
            if done != app.package_size or h.hexdigest() != app.sha256:
                raise LauncherError("다운로드 중단 또는 패키지 SHA-256 불일치")
        except Exception as exc:
            target.unlink(missing_ok=True)
            if isinstance(exc, LauncherError):
                raise
            raise LauncherError(f"다운로드 실패: {exc}") from exc


class InternetProvider:
    """Reserved interface. No internet listener, tunnel, TLS or auth is claimed."""
    def __init__(self, *args, **kwargs):
        raise LauncherError("인터넷 배포 미구성 — TLS·인증·회사 네트워크 정책 검증 후 구현")
