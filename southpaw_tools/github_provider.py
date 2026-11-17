"""Unauthenticated public GitHub Release transport; trust remains in CatalogVerifier."""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
from copy import deepcopy
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .archive import check_cancel
from .catalog_trust import CatalogVerifier, MAX_CATALOG, MAX_SIGNATURE, strict_json
from .common import LauncherError
from .github_channels import latest_api_url, repository_aliases
from .paths import AppPaths
from .providers import HttpProvider, NoRedirect

MAX_API = 2 * 1024 * 1024
CDN_HOSTS = {"release-assets.githubusercontent.com", "objects.githubusercontent.com"}


def https_url(url: str):
    try:
        parts = urllib.parse.urlsplit(url)
        if (parts.scheme != "https" or not parts.hostname or parts.port not in (None, 443)
                or parts.username or parts.password or parts.fragment
                or any(ord(c) <= 32 or c == "\\" for c in url)):
            raise ValueError()
        return parts
    except (ValueError, TypeError) as exc:
        raise LauncherError("GitHub 다운로드는 정상적인 HTTPS 주소만 허용합니다.") from exc


class AssetRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 4
    max_repeats = 2

    def __init__(self, repository=None):
        super().__init__()
        self.repositories = repository_aliases(repository) if repository else ()

    def _asset_prefix(self, repository):
        return f"https://github.com/{repository}/releases/download/"

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = https_url(newurl)
        if self.repositories:
            source = https_url(req.full_url)
            source_asset = any(req.full_url.startswith(self._asset_prefix(repo))
                               for repo in self.repositories)
            if source_asset and source.query:
                raise LauncherError("GitHub 자산 주소에 예상하지 않은 쿼리가 있습니다.")
            source_cdn = (source.hostname in CDN_HOSTS and source.path.startswith(
                ("/github-production-release-asset/", "/github-production-release-asset-2e65be/")))
            if not (source_asset or source_cdn):
                raise LauncherError("승인되지 않은 GitHub 자산 리다이렉트 출발점입니다.")
            if len(self.repositories) == 2:
                old, new = map(self._asset_prefix, self.repositories)
                # One-way owner change, same channel/tag/asset, no added query.
                if req.full_url.startswith(old) and newurl == new + req.full_url[len(old):]:
                    return super().redirect_request(req, fp, code, msg, headers, newurl)
        if (parts.hostname not in CDN_HOSTS
                or not parts.path.startswith(("/github-production-release-asset/",
                                               "/github-production-release-asset-2e65be/"))):
            raise LauncherError("승인되지 않은 GitHub 자산 리다이렉트입니다.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class GitHubReleasesProvider(HttpProvider):
    """No token argument, login, network key enrollment, or unsigned fallback.

    Inherits only the existing engine-boundary validate_release check. HTTP transport,
    catalog lookup and download are specialized for HTTPS GitHub assets.
    """
    def __init__(self, repository: str, *, verifier: CatalogVerifier | None = None):
        if (not isinstance(repository, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}", repository)
                or repository.split('/')[1] in {'.', '..'} or repository.endswith('.git')):
            raise LauncherError("GitHub 저장소는 OWNER/REPO 형식이어야 합니다.")
        self.repository = repository
        self.api_url = latest_api_url(repository)
        self.verifier = verifier or CatalogVerifier.bundled(
            AppPaths.default().root / "catalog-trust.json")
        self.api_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.asset_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), AssetRedirect(repository))
        self._assets = {}
        self._release = None
        self._install_snapshot = None
        self._verified_bytes = None

    @staticmethod
    def _verify_bindings(apps, bound):
        for app in apps:
            if app.published:
                asset = bound.get(app.package_name)
                if asset is None or asset['size'] != app.package_size:
                    raise LauncherError("서명된 ZIP 이름·크기와 GitHub 자산이 일치하지 않습니다.")
                digest = asset.get('digest')
                if digest is not None and digest != 'sha256:' + app.sha256:
                    raise LauncherError("서명된 SHA-256과 GitHub 자산 digest 불일치")

    @contextmanager
    def installation_session(self, app):
        """One fresh network check per explicit install; no cross-operation trust cache.

        Every engine validation still verifies raw signatures, asset bindings and
        persistent sequence state. The UI serializes use of this provider.
        """
        if self._install_snapshot is not None:
            raise LauncherError("중복 GitHub 설치 작업은 허용하지 않습니다.")
        self.validate_release(app)
        self._install_snapshot = (*self._verified_bytes, deepcopy(self._assets), deepcopy(self._release))
        try:
            yield self
        finally:
            self._install_snapshot = None
            self._verified_bytes = None
            self._assets = {}
            self._release = None

    def _request(self, url: str, *, api=False):
        https_url(url)
        headers = {"User-Agent": "CreativeGroupLauncher/0.1.0", "Accept-Encoding": "identity"}
        if api:
            headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"})
        else:
            headers["Accept"] = "application/octet-stream"
        try:
            response = (self.api_opener if api else self.asset_opener).open(
                urllib.request.Request(url, headers=headers), timeout=10)
            if response.status != 200 or response.headers.get('Content-Encoding', 'identity') != 'identity':
                response.close()
                raise LauncherError("GitHub 응답 상태 또는 전송 인코딩이 잘못되었습니다.")
            return response
        except urllib.error.HTTPError as exc:
            status = exc.code
            error_headers = exc.headers or {}
            limited = status == 429 or status == 403 and (
                error_headers.get('X-RateLimit-Remaining') == '0' or error_headers.get('Retry-After') is not None)
            if limited:
                message = f"GitHub API 호출 제한(HTTP {status}) — 자동 재시도하지 않습니다."
            elif status == 404:
                message = "GitHub HTTP 404 — 공개 저장소·정식 Release·자산을 찾을 수 없습니다."
            elif status == 403:
                message = "GitHub HTTP 403 — 접근 거부입니다. 클라이언트 인증정보는 추가하지 않습니다."
            else:
                message = f"GitHub HTTP {status} 오류"
            exc.close()
            raise LauncherError(message) from exc
        except (urllib.error.URLError, OSError, ValueError) as exc:
            # Do not expose redirected signed query strings in errors/logs.
            raise LauncherError("GitHub 네트워크 또는 HTTPS 연결 실패") from exc

    def _bytes(self, asset, limit):
        if not 0 < asset['size'] <= limit:
            raise LauncherError("GitHub 카탈로그·서명 크기 제한 초과")
        with self._request(asset['browser_download_url']) as response:
            raw = response.read(limit + 1)
        if len(raw) != asset['size'] or len(raw) > limit:
            raise LauncherError("GitHub 카탈로그·서명 다운로드 크기 불일치")
        return raw

    def catalog(self):
        if self._install_snapshot is not None:
            raw, signature, bound, release = self._install_snapshot
            _, apps = self.verifier.verify(raw, signature)
            self._verify_bindings(apps, bound)
            apps = self.verifier.accept(raw, signature)
            self._assets, self._release = deepcopy(bound), deepcopy(release)
            return apps
        # Clear stale transport bindings on EVERY refresh, including failed refreshes.
        self._assets = {}; self._release = None
        self._verified_bytes = None
        try:
            with self._request(self.api_url, api=True) as response:
                release = strict_json(response.read(MAX_API + 1), MAX_API)
            if (release.get('draft') is not False or release.get('prerelease') is not False
                    or type(release.get('id')) is not int or release['id'] <= 0
                    or not isinstance(release.get('tag_name'), str) or not release['tag_name']):
                raise LauncherError("최신 정식 GitHub Release 형식이 아닙니다.")
            assets = release.get('assets')
            if not isinstance(assets, list) or not 2 <= len(assets) <= 100:
                raise LauncherError("GitHub 자산 목록 누락 또는 1단계 지원 범위(100개) 초과")
            bound = {}; ids = set()
            for asset in assets:
                if not isinstance(asset, dict):
                    raise LauncherError("GitHub 자산 형식 오류")
                name = asset.get('name')
                if (not isinstance(name, str) or not name or name in bound
                        or type(asset.get('id')) is not int or asset['id'] <= 0 or asset['id'] in ids
                        or asset.get('state') != 'uploaded' or type(asset.get('size')) is not int
                        or not 0 < asset['size'] < 2 * 1024**3):
                    raise LauncherError("GitHub 자산 이름·ID·크기·업로드 상태 오류")
                expected = {
                    f"https://github.com/{repo}/releases/download/"
                    f"{urllib.parse.quote(release['tag_name'], safe='')}/{urllib.parse.quote(name, safe='')}"
                    for repo in repository_aliases(self.repository)
                }
                if asset.get('browser_download_url') not in expected:
                    raise LauncherError("GitHub 자산이 지정 저장소·Release와 일치하지 않습니다.")
                bound[name] = asset; ids.add(asset['id'])
            raw = self._bytes(bound['catalog.json'], MAX_CATALOG)
            signature = self._bytes(bound['catalog.sig.json'], MAX_SIGNATURE)
            # Validate all asset bindings BEFORE advancing the persistent high-water mark.
            _, apps = self.verifier.verify(raw, signature)
            self._verify_bindings(apps, bound)
            apps = self.verifier.accept(raw, signature)
            self._assets = bound; self._release = release
            self._verified_bytes = (raw, signature)
            return apps
        except (KeyError, TypeError, ValueError) as exc:
            raise LauncherError("GitHub Release 또는 필수 카탈로그 자산 누락·형식 오류") from exc

    def health(self):
        self.catalog()
        return {"service": "southpaw-tools", "api_version": 1, "transport": "github-releases",
                "repository": self.repository, "release_id": self._release['id']}

    def download(self, app, target: Path, progress=lambda done, total: None,
                 cancel: threading.Event | None = None):
        self.validate_release(app)
        asset = self._assets[app.package_name]
        check_cancel(cancel)
        target.parent.mkdir(parents=True, exist_ok=True)
        owned = False
        try:
            with self._request(asset['browser_download_url']) as response:
                length = response.headers.get('Content-Length')
                if length is not None and (not length.isdecimal() or int(length) != app.package_size):
                    raise LauncherError("GitHub 패키지 Content-Length 불일치")
                done = 0; digest = hashlib.sha256(); started = time.monotonic()
                with target.open('xb') as output:
                    owned = True
                    while True:
                        check_cancel(cancel)
                        if time.monotonic() - started > 600:
                            raise LauncherError("GitHub 다운로드 제한 시간 초과")
                        chunk = response.read(min(256 * 1024, app.package_size - done + 1))
                        if not chunk:
                            break
                        done += len(chunk)
                        if done > app.package_size:
                            raise LauncherError("GitHub 패키지 크기 초과")
                        output.write(chunk); digest.update(chunk); progress(done, app.package_size)
            check_cancel(cancel)
            if done != app.package_size or digest.hexdigest() != app.sha256:
                raise LauncherError("GitHub 다운로드 중단 또는 SHA-256 불일치")
        except Exception as exc:
            if owned:
                target.unlink(missing_ok=True)
            if isinstance(exc, LauncherError):
                raise
            raise LauncherError("GitHub 패키지 다운로드 실패") from exc
