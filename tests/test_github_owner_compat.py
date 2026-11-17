"""Owner migration fixtures use real signatures/ZIPs, no sockets or EXE execution."""
import copy
import hashlib
import io
import json
import unittest
import urllib.request
import urllib.response
from email.message import Message
from pathlib import Path
from unittest.mock import patch

from southpaw_tools import managed_update
from southpaw_tools.common import LauncherError, atomic_json, digest
from southpaw_tools.github_channels import latest_api_url, managed_repository, repository_aliases
from southpaw_tools.github_provider import AssetRedirect, GitHubReleasesProvider
from southpaw_tools.providers import NoRedirect
from southpaw_tools.setup_support import PRODUCT, check as setup_check
from tests import test_github_provider as fixtures
from tests import test_managed_update as managed_fixtures
from tests.support import package


OLD = "toast-source/creative-group-releases"
NEW = "rodetoast/creative-group-releases"


class OwnerCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.f = f = fixtures.GitHubProviderTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.engine.catalog_verifier = f.verifier
        self.provider = self.provider_for(OLD)

    def provider_for(self, repository):
        p = GitHubReleasesProvider(repository, verifier=self.f.verifier)
        p.api_opener = p.asset_opener = self.f.transport
        return p

    def publish(self, owner, sequence, app=None, source=None):
        f = self.f
        release = copy.deepcopy(f.publish(app or f.app, source or f.source, sequence))
        for asset in release['assets']:
            old_url = asset['browser_download_url']
            asset['browser_download_url'] = old_url.replace('example/creative-group-releases', owner)
            f.transport.routes[asset['browser_download_url']] = f.transport.routes[old_url]
        self.save(release)
        return release

    def save(self, release):
        self.f.transport.routes[self.provider.api_url] = json.dumps(release).encode()

    def test_only_four_exact_channels_use_fixed_repository_identity(self):
        for name, identity in [('creative-group-releases', 1447701732),
                               ('creative-group-trial-releases', 1452413703)]:
            for owner in ('toast-source', 'rodetoast'):
                repo = owner + '/' + name
                self.assertTrue(managed_repository(repo))
                self.assertEqual(latest_api_url(repo),
                                 f'https://api.github.com/repositories/{identity}/releases/latest')
        for repo in ('attacker/creative-group-releases', 'rodetoast/other', 'example/creative-group-releases'):
            self.assertFalse(managed_repository(repo))
            self.assertEqual(repository_aliases(repo), (repo,))
            self.assertEqual(latest_api_url(repo), f'https://api.github.com/repos/{repo}/releases/latest')

    def test_old_and_new_configurations_accept_both_signed_owner_asset_sets(self):
        for config in (OLD, NEW):
            for owner in (OLD, NEW):
                with self.subTest(config=config, owner=owner):
                    self.provider = self.provider_for(config)
                    self.publish(owner, 1)
                    self.assertEqual(self.provider.catalog(), [self.f.app])
                    self.assertIs(self.provider.verifier, self.f.verifier)
        self.assertTrue(all(not r.has_header('Authorization') for r in self.f.transport.calls))

    def test_signed_old_to_new_install_update_and_offline_rollback_preserve_data(self):
        f = self.f
        self.publish(OLD, 1)
        f.engine.install(self.provider.catalog()[0], self.provider)
        _, old_payload = f.engine.resolve_launch(f.app)
        (old_payload / 'settings.json').write_text('synthetic setting')
        original_hash = digest(old_payload / f.app.executable_relative_path)
        source, r2 = package(f.root / 'inputs', 'r2', version='1.1.0')
        self.publish(NEW, 2, r2, source)
        f.engine.install(self.provider.catalog()[0], self.provider)
        self.assertEqual(f.engine.installed('dummy'), r2)
        self.assertEqual(digest(old_payload / f.app.executable_relative_path), original_hash)
        _, new_payload = f.engine.resolve_launch(r2)
        self.assertEqual((new_payload / 'settings.json').read_text(), 'synthetic setting')
        (new_payload / 'user-projects').mkdir(exist_ok=True)
        work = new_payload / 'user-projects/work.txt'
        work.write_text('synthetic work')
        high_water = f.verifier.state_path.read_bytes()
        calls = len(f.transport.calls)
        f.transport.routes.clear()
        for target in (f.app, r2):
            f.engine.select_release('dummy', target.release_id, expected_current=f.engine.installed('dummy'),
                                    expected_release=target)
            self.assertEqual(f.engine.installed('dummy'), target)
        self.assertEqual(work.read_text(), 'synthetic work')
        self.assertEqual(f.verifier.state_path.read_bytes(), high_water)
        self.assertEqual(len(f.transport.calls), calls)
        self.assertEqual(f.engine.processes.calls, [])

    def test_new_owner_does_not_reset_sequence_or_accept_replay(self):
        self.publish(OLD, 1)
        self.provider.catalog()
        self.publish(NEW, 2)
        self.provider.catalog()
        state = self.f.verifier.state_path.read_bytes()
        self.provider = self.provider_for(NEW)
        self.provider.verifier = self.f.signer.verifier(self.f.verifier.state_path)
        self.publish(NEW, 1)
        with self.assertRaisesRegex(LauncherError, '재전송'):
            self.provider.catalog()
        self.assertEqual(self.f.verifier.state_path.read_bytes(), state)

    def test_tampered_signature_after_owner_change_preserves_old_installation(self):
        f = self.f
        self.publish(OLD, 1)
        f.engine.install(self.provider.catalog()[0], self.provider)
        before = f.tree()
        source, app = package(f.root / 'inputs', 'r2')
        release = self.publish(NEW, 2, app, source)
        url = release['assets'][0]['browser_download_url']
        f.transport.routes[url] = f.transport.routes[url].replace(b'Harmless', b'HarmlesX')
        with self.assertRaisesRegex(LauncherError, '서명'):
            f.engine.install(app, self.provider)
        self.assertEqual(f.tree(), before)

    def test_changed_zip_after_owner_change_cannot_replace_active_release(self):
        f = self.f
        self.publish(OLD, 1)
        f.engine.install(self.provider.catalog()[0], self.provider)
        pointer = f.engine.paths.app('dummy') / 'active.json'
        active = pointer.read_bytes()
        receipt = f.engine.paths.release('dummy', f.app.release_id) / 'receipt.json'
        receipt_bytes = receipt.read_bytes()
        source, app = package(f.root / 'inputs', 'r2')
        release = self.publish(NEW, 2, app, source)
        url = release['assets'][-1]['browser_download_url']
        body = f.transport.routes[url]
        f.transport.routes[url] = bytes([body[0] ^ 1]) + body[1:]
        with self.assertRaisesRegex(LauncherError, 'SHA-256'):
            f.engine.install(app, self.provider)
        self.assertEqual(pointer.read_bytes(), active)
        self.assertEqual(receipt.read_bytes(), receipt_bytes)
        self.assertEqual(f.engine.installed('dummy'), f.app)

    def test_foreign_owner_cross_channel_tag_and_query_rejected_before_trust_write(self):
        for replacement in ('attacker/creative-group-releases', 'rodetoast/creative-group-trial-releases',
                            'rodetoast/creative-group-releases-extra'):
            release = self.publish(NEW, 1)
            release['assets'][-1]['browser_download_url'] = release['assets'][-1]['browser_download_url'].replace(NEW, replacement)
            self.save(release)
            with self.subTest(replacement=replacement), self.assertRaisesRegex(LauncherError, '지정 저장소'):
                self.provider.catalog()
            self.assertFalse(self.f.verifier.state_path.exists())
        for tail in ('?unexpected=1', '#fragment'):
            release = self.publish(NEW, 1)
            release['assets'][-1]['browser_download_url'] += tail
            self.save(release)
            with self.assertRaisesRegex(LauncherError, '지정 저장소'):
                self.provider.catalog()
            self.assertFalse(self.f.verifier.state_path.exists())

    def test_redirects_preserve_exact_tag_asset_and_channel_and_are_one_way(self):
        handler = AssetRedirect(OLD)
        old = f'https://github.com/{OLD}/releases/download/t/a.zip'
        new = old.replace(OLD, NEW)
        redirected = handler.redirect_request(urllib.request.Request(old), None, 301, '', {}, new)
        self.assertEqual(redirected.full_url, new)
        bad = [new.replace('/t/', '/other/'), new.replace('a.zip', 'b.zip'),
               new.replace(NEW, 'rodetoast/creative-group-trial-releases'),
               new.replace('github.com', 'evil.example'), new + '?unexpected=1',
               new.replace('https:', 'http:'), new.replace('github.com', 'github.com:444')]
        for url in bad:
            with self.subTest(url=url), self.assertRaises(LauncherError):
                handler.redirect_request(urllib.request.Request(old), None, 301, '', {}, url)
        for source, target in [(new, old),
                               ('https://objects.githubusercontent.com/github-production-release-asset/1/x', new),
                               (old + '?unexpected=1', new + '?unexpected=1')]:
            with self.assertRaises(LauncherError):
                handler.redirect_request(urllib.request.Request(source), None, 301, '', {}, target)
        with self.assertRaises(LauncherError):
            AssetRedirect('example/creative-group-releases').redirect_request(
                urllib.request.Request(old), None, 301, '', {}, new)

    def test_real_urllib_redirect_pipeline_follows_owner_then_cdn_without_socket(self):
        old = f'https://github.com/{OLD}/releases/download/t/a.zip'
        new = old.replace(OLD, NEW)
        cdn = 'https://release-assets.githubusercontent.com/github-production-release-asset/1/x?fixture=only'
        calls = []

        class HTTPSFixture(urllib.request.HTTPSHandler):
            def https_open(inner, request):
                self.assertFalse(request.has_header('Authorization'))
                calls.append(request.full_url)
                headers = Message()
                if request.full_url in (old, new):
                    headers['Location'] = new if request.full_url == old else cdn
                    response = urllib.response.addinfourl(io.BytesIO(b''), headers, request.full_url, 302)
                else:
                    self.assertEqual(request.full_url, cdn)
                    response = urllib.response.addinfourl(io.BytesIO(b'fixture'), headers, cdn, 200)
                response.msg = 'fixture'
                return response

        self.provider.asset_opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), AssetRedirect(OLD), HTTPSFixture())
        with self.provider._request(old) as response:
            self.assertEqual(response.read(), b'fixture')
        self.assertEqual(calls, [old, new, cdn])

    def test_api_redirects_and_lan_redirect_policy_still_fail_closed(self):
        for url in (latest_api_url(NEW), 'https://evil.example/x'):
            with self.assertRaises(LauncherError):
                NoRedirect().redirect_request(urllib.request.Request(latest_api_url(OLD)), None, 301, '', {}, url)

    def test_managed_channel_accepts_only_fixed_aliases_without_changing_keys(self):
        fake_module = self.f.root / 'module/managed_update.py'
        data = fake_module.parent / 'data/managed-channel.json'
        data.parent.mkdir(parents=True)
        for name in ('creative-group-releases', 'creative-group-trial-releases'):
            for owner in ('toast-source', 'rodetoast'):
                channel = {'repository': owner + '/' + name, 'policy': self.f.signer.policy}
                atomic_json(data, channel)
                with patch.object(managed_update, '__file__', str(fake_module)):
                    self.assertEqual(managed_update.channel_policy(), channel)
        for repo, policy in [('attacker/creative-group-releases', self.f.signer.policy),
                             ('rodetoast/other', self.f.signer.policy),
                             (NEW, {**self.f.signer.policy, 'keys': {}})]:
            atomic_json(data, {'repository': repo, 'policy': policy})
            with patch.object(managed_update, '__file__', str(fake_module)), self.assertRaises(LauncherError):
                managed_update.channel_policy()

    def test_legacy_named_managed_channel_prepares_new_owner_signed_launcher(self):
        fixture = managed_fixtures.ManagedUpdateTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        updater = fixture.updater()
        provider = fixture.provider(updater)
        transport = provider.api_opener
        release = json.loads(transport.routes[provider.api_url])
        for asset in release['assets']:
            previous = asset['browser_download_url']
            asset['browser_download_url'] = previous.replace('toast-source/', 'rodetoast/')
            transport.routes[asset['browser_download_url']] = transport.routes[previous]
        transport.routes[provider.api_url] = json.dumps(release).encode()
        pointer = (fixture.home / 'current.json').read_bytes()
        work = digest(fixture.work)
        transaction = updater.prepare(provider, expected=fixture.r2)
        self.assertTrue(transaction)
        self.assertEqual((fixture.home / 'current.json').read_bytes(), pointer)
        self.assertEqual(digest(fixture.work), work)
        self.assertEqual(provider.repository, fixture.channel['repository'])
        self.assertEqual(provider.verifier.policy, updater.policy)
        self.assertEqual(provider.verifier.state_path, updater.verifier.state_path)

    def test_current_setup_guard_does_not_silently_replace_a_different_bootstrap(self):
        root, data = self.f.root / 'program', self.f.root / 'userdata'
        root.mkdir()
        data.mkdir()
        executable = root / 'CGLBootstrap.exe'
        executable.write_bytes(b'old harmless fixture, never executed')
        work = data / 'work.txt'
        work.write_text('preserve')
        atomic_json(root / 'setup-state.json', {'product': PRODUCT, 'data_root': str(data.resolve())})
        before = {p: digest(p) for p in self.f.root.rglob('*') if p.is_file()}
        incoming = {'files': {'CGLBootstrap.exe': hashlib.sha256(b'new harmless fixture').hexdigest()}}
        with self.assertRaisesRegex(LauncherError, '변경'):
            setup_check(root, data, incoming, inspect_processes=False)
        self.assertEqual({p: digest(p) for p in self.f.root.rglob('*') if p.is_file()}, before)

    def test_new_seed_does_not_force_existing_current_or_reset_trust(self):
        fixture = managed_fixtures.ManagedUpdateTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        updater = fixture.updater()
        pointer = (fixture.home / 'current.json').read_bytes()
        trust = updater.verifier.state_path.read_bytes()
        fixture.signer.publish(fixture.seed, [fixture.r2], 2)
        (fixture.seed / fixture.r2.package_name).write_bytes(fixture.r2_zip.read_bytes())
        managed_update.initialize(fixture.home, fixture.data, fixture.seed, fixture.channel)
        self.assertEqual((fixture.home / 'current.json').read_bytes(), pointer)
        self.assertEqual(updater.verifier.state_path.read_bytes(), trust)
        self.assertEqual(updater.current(), fixture.r1)
        self.assertEqual(fixture.work.read_text(), 'preserve')
