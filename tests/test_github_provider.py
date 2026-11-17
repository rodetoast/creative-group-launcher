from __future__ import annotations

import io
import json
import threading
import unittest
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from southpaw_tools.catalog_trust import MAX_CATALOG
from southpaw_tools.common import Cancelled, LauncherError, digest, read_json
from southpaw_tools.github_provider import AssetRedirect, GitHubReleasesProvider
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from tests.support import FakeProcesses, TestSigner, package, temporary


class Response(io.BytesIO):
    status = 200

    def __init__(self, data, headers=None):
        super().__init__(data)
        self.headers = headers if headers is not None else {'Content-Length': str(len(data))}


class FakeGitHub:
    """In-memory HTTPS responses. Never opens a socket or runs downloaded files."""
    def __init__(self):
        self.routes = {}; self.calls = []

    def open(self, request, timeout):
        self.calls.append(request)
        if request.has_header('Authorization'):
            raise AssertionError('Client credentials must never be sent')
        result = self.routes[request.full_url]
        if isinstance(result, Exception):
            raise result
        if isinstance(result, tuple):
            return Response(*result)
        return Response(result)


class GitHubProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary('github-provider-'); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.signer = TestSigner(self.root)
        self.verifier = self.signer.verifier(self.root/'trust/catalog-trust.json')
        self.provider = GitHubReleasesProvider('example/creative-group-releases', verifier=self.verifier)
        self.transport = FakeGitHub()
        self.provider.api_opener = self.provider.asset_opener = self.transport
        self.source, self.app = package(self.root/'inputs')
        self.release = self.publish(self.app, self.source, 1)
        self.engine = Installer(AppPaths(self.root/'client'), FakeProcesses())

    def publish(self, app, source, sequence, *, signer=None, tag=None):
        raw, sig = (signer or self.signer).pair([app], sequence)
        tag = tag or f'bundle-{sequence}'
        assets = []
        for i, (name, body) in enumerate([('catalog.json', raw), ('catalog.sig.json', json.dumps(sig).encode()),
                                         (app.package_name, source.read_bytes())], 1):
            url = f'https://github.com/example/creative-group-releases/releases/download/{tag}/{name}'
            asset = {'id': sequence*10+i, 'name':name, 'state':'uploaded', 'size':len(body),
                     'browser_download_url':url}
            if name.endswith('.zip'):
                asset['digest'] = 'sha256:' + app.sha256
            assets.append(asset); self.transport.routes[url] = body
        release = {'id':sequence, 'tag_name':tag, 'draft':False, 'prerelease':False, 'assets':assets}
        self.transport.routes[self.provider.api_url] = json.dumps(release).encode()
        return release

    def save_release(self):
        self.transport.routes[self.provider.api_url] = json.dumps(self.release).encode()

    def install_r1(self):
        self.engine.install(self.provider.catalog()[0], self.provider)

    def tree(self):
        return {str(p.relative_to(self.engine.paths.root)):digest(p)
                for p in self.engine.paths.root.rglob('*') if p.is_file()}

    def test_signed_r1_to_r2_and_offline_state_preserve_data(self):
        self.install_r1()
        _, payload = self.engine.resolve_launch(self.app)
        (payload/'settings.json').write_text('synthetic settings')
        (payload/'trial-work-note.txt').write_text('synthetic work')
        before = {p.name:digest(p) for p in payload.iterdir() if p.is_file()}
        source2, app2 = package(self.root/'inputs', 'r2', version='1.1.0')
        self.publish(app2, source2, 2)
        candidate = self.provider.catalog()[0]
        self.assertTrue(candidate.is_new_release(self.engine.installed('dummy')))
        self.engine.install(candidate, self.provider)
        self.assertTrue(self.engine.download_verified)
        self.assertEqual(self.engine.installed('dummy'), app2)
        self.assertEqual(read_json(self.engine.paths.release('dummy','r2')/'receipt.json')['app'],app2.to_dict())
        _, new_payload = self.engine.resolve_launch(app2)
        self.assertEqual((new_payload/'settings.json').read_text(), 'synthetic settings')
        self.assertFalse((new_payload/'trial-work-note.txt').exists())
        self.assertEqual({p.name:digest(p) for p in payload.iterdir() if p.is_file()},before)
        self.assertFalse(self.engine.pending_recovery('dummy'))
        self.assertFalse(list(self.engine.paths.app('dummy').glob('transactions/*.json')))
        calls = len(self.transport.calls)
        self.transport.routes.clear()
        self.assertEqual(Installer(self.engine.paths).installed('dummy'),app2)
        self.assertEqual(len(self.transport.calls),calls)
        self.assertEqual(self.engine.processes.calls,[])

    def test_latest_endpoint_only_no_release_list_fallback(self):
        with patch.object(AppPaths,'default',return_value=AppPaths(self.root/'default-client')):
            default = GitHubReleasesProvider('example/creative-group-releases')
            self.assertEqual(default.verifier.state_path,self.root/'default-client/catalog-trust.json')
        self.assertEqual(self.provider.catalog(),[self.app])
        api_calls = [r for r in self.transport.calls if r.full_url.startswith('https://api.github.com')]
        self.assertEqual([r.full_url for r in api_calls],[self.provider.api_url])
        self.assertFalse(self.app.is_new_release(self.app))

    def test_draft_rejected(self):
        self.release['draft']=True; self.save_release()
        with self.assertRaisesRegex(LauncherError,'정식'): self.provider.catalog()

    def test_prerelease_rejected(self):
        self.release['prerelease']=True; self.save_release()
        with self.assertRaisesRegex(LauncherError,'정식'): self.provider.catalog()

    def test_old_catalog_replay_after_restart_rejected(self):
        old = dict(self.transport.routes)
        self.provider.catalog()
        self.publish(self.app,self.source,2); self.provider.catalog()
        self.transport.routes=old
        self.provider.verifier=self.signer.verifier(self.verifier.state_path)
        with self.assertRaisesRegex(LauncherError,'재전송'): self.provider.catalog()

    def test_equal_sequence_different_catalog_rejected(self):
        self.provider.catalog()
        self.publish(replace(self.app,release_notes='changed'),self.source,1)
        with self.assertRaisesRegex(LauncherError,'재전송'): self.provider.catalog()

    def test_tampered_signature_preserves_installed_files(self):
        self.install_r1(); before=self.tree()
        url=self.release['assets'][0]['browser_download_url']
        self.transport.routes[url]=self.transport.routes[url].replace(b'Harmless',b'HarmlesX')
        with self.assertRaisesRegex(LauncherError,'서명'): self.engine.install(self.app,self.provider)
        self.assertEqual(self.tree(),before)

    def test_wrong_key_rejected(self):
        self.publish(self.app,self.source,2,signer=TestSigner(self.root))
        with self.assertRaisesRegex(LauncherError,'알 수 없는'): self.provider.catalog()

    def test_modified_signature_bytes_rejected(self):
        import base64
        url=self.release['assets'][1]['browser_download_url']
        signature=json.loads(self.transport.routes[url])
        signature['signature']=base64.b64encode(b'X'*64).decode()
        self.transport.routes[url]=json.dumps(signature).encode()
        with self.assertRaisesRegex(LauncherError,'서명'): self.provider.catalog()

    def test_missing_signature_rejected(self):
        self.release['assets'].pop(1); self.save_release()
        with self.assertRaisesRegex(LauncherError,'누락'): self.provider.catalog()

    def test_mixed_catalog_signature_generations_rejected(self):
        old_sig=self.transport.routes[self.release['assets'][1]['browser_download_url']]
        release=self.publish(self.app,self.source,2)
        self.transport.routes[release['assets'][1]['browser_download_url']]=old_sig
        release['assets'][1]['size']=len(old_sig)
        self.transport.routes[self.provider.api_url]=json.dumps(release).encode()
        with self.assertRaisesRegex(LauncherError,'서명'): self.provider.catalog()

    def test_missing_zip_does_not_advance_trust_state(self):
        self.release['assets'].pop(); self.save_release()
        with self.assertRaises(LauncherError): self.provider.catalog()
        self.assertFalse(self.verifier.state_path.exists())

    def test_wrong_asset_size_rejected(self):
        self.release['assets'][-1]['size']+=1; self.save_release()
        with self.assertRaisesRegex(LauncherError,'크기'): self.provider.catalog()

    def test_asset_digest_disagrees_with_signature_rejected(self):
        self.release['assets'][-1]['digest']='sha256:'+'0'*64; self.save_release()
        with self.assertRaisesRegex(LauncherError,'digest'): self.provider.catalog()

    def test_bad_zip_hash_preserves_old_install(self):
        self.install_r1(); before=self.tree()
        source2,app2=package(self.root/'inputs','r2')
        release=self.publish(app2,source2,2)
        body=source2.read_bytes(); self.transport.routes[release['assets'][-1]['browser_download_url']]=b'X'+body[1:]
        with self.assertRaisesRegex(LauncherError,'SHA-256'): self.engine.install(app2,self.provider)
        self.assertEqual(self.engine.installed('dummy'),self.app)
        self.assertEqual(self.tree(),before)

    def test_repository_or_release_asset_substitution_rejected(self):
        for url in ['https://example.com/evil.zip','http://github.com/example/creative-group-releases/r1.zip',
                    'https://github.com/other/repo/releases/download/bundle-1/r1.zip',
                    'https://github.com/example/creative-group-releases/releases/download/old/r1.zip']:
            with self.subTest(url=url):
                self.release['assets'][-1]['browser_download_url']=url; self.save_release()
                with self.assertRaisesRegex(LauncherError,'일치'): self.provider.catalog()

    def test_duplicate_asset_rejected(self):
        self.release['assets'].append(self.release['assets'][-1]); self.save_release()
        with self.assertRaises(LauncherError): self.provider.catalog()

    def test_oversized_catalog_rejected_before_fetch(self):
        self.release['assets'][0]['size']=MAX_CATALOG+1; self.save_release()
        with self.assertRaisesRegex(LauncherError,'제한'): self.provider.catalog()

    def test_http_errors_distinguished_without_retry(self):
        for code,headers,word in [(404,{},'404'),(403,{},'접근 거부'),
                (403,{'X-RateLimit-Remaining':'0'},'호출 제한'),(429,{'Retry-After':'10'},'호출 제한')]:
            with self.subTest(code=code,headers=headers):
                before=len(self.transport.calls)
                self.transport.routes[self.provider.api_url]=urllib.error.HTTPError(self.provider.api_url,code,'',headers,None)
                with self.assertRaisesRegex(LauncherError,word): self.provider.catalog()
                self.assertEqual(len(self.transport.calls),before+1)

    def test_network_error_preserves_offline_install(self):
        self.install_r1(); before=self.tree()
        self.transport.routes[self.provider.api_url]=urllib.error.URLError('unavailable')
        with self.assertRaisesRegex(LauncherError,'네트워크'): self.provider.catalog()
        self.assertEqual(self.tree(),before)
        self.assertEqual(self.engine.installed('dummy'),self.app)

    def test_cancel_cleans_partial_download(self):
        event=threading.Event(); target=self.root/'download.zip'
        with self.assertRaises(Cancelled):
            self.provider.download(self.app,target,lambda *_:event.set(),event)
        self.assertFalse(target.exists())

    def test_existing_download_target_not_deleted(self):
        target=self.root/'existing.zip'; target.write_bytes(b'keep')
        with self.assertRaises(LauncherError): self.provider.download(self.app,target)
        self.assertEqual(target.read_bytes(),b'keep')

    def test_content_length_mismatch_and_oversize_stream_rejected(self):
        url=self.release['assets'][-1]['browser_download_url']; raw=self.source.read_bytes()
        for result in [(raw,{'Content-Length':'1'}),(raw+b'X',{})]:
            self.transport.routes[url]=result
            target=self.root/'download.zip'
            with self.assertRaises(LauncherError): self.provider.download(self.app,target)
            self.assertFalse(target.exists())

    def test_redirect_allows_only_https_github_asset_cdn(self):
        handler=AssetRedirect(); request=urllib.request.Request('https://github.com/example/repo/releases/download/t/r.zip')
        url='https://release-assets.githubusercontent.com/github-production-release-asset/1/fixture?token=temporary'
        redirected=handler.redirect_request(request,None,302,'',{},url)
        self.assertEqual(redirected.full_url,url)
        for url in ['http://release-assets.githubusercontent.com/github-production-release-asset/1/x',
                    'https://evil.example/x','https://127.0.0.1/x',
                    'https://release-assets.githubusercontent.com.evil.example/github-production-release-asset/1/x',
                    'https://release-assets.githubusercontent.com/other/path',
                    'https://user@release-assets.githubusercontent.com/github-production-release-asset/1/x']:
            with self.subTest(url=url):
                with self.assertRaises(LauncherError): handler.redirect_request(request,None,302,'',{},url)

    def test_invalid_repository_and_empty_operational_keys_rejected(self):
        for repo in ['https://github.com/a/b','a/b/../../x','a/b.git','a/..']:
            with self.assertRaises(LauncherError): GitHubReleasesProvider(repo)
        from southpaw_tools.catalog_trust import CatalogVerifier, CATALOG_ID
        self.provider.verifier=CatalogVerifier({'schema_version':1,'catalog_id':CATALOG_ID,
            'minimum_sequence':1,'keys':{}},self.root/'untrusted.json')
        with self.assertRaisesRegex(LauncherError,'알 수 없는'): self.provider.catalog()


if __name__=='__main__':
    unittest.main()
