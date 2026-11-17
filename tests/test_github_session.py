import unittest
from unittest.mock import patch

from southpaw_tools.common import LauncherError
from tests import test_github_provider as helpers
from tests.support import package


class GitHubSessionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=helpers.GitHubProviderTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def api_count(self):
        return sum(r.full_url.startswith('https://api.github.com') for r in self.fixture.transport.calls)

    def test_install_fetches_once_and_still_verifies_at_engine_boundaries(self):
        f=self.fixture
        with patch.object(f.verifier,'verify',wraps=f.verifier.verify) as verify:
            with f.provider.installation_session(f.app):
                f.engine.install(f.app,f.provider)
            self.assertGreaterEqual(verify.call_count,6)
        self.assertEqual(self.api_count(),1)
        self.assertIsNone(f.provider._install_snapshot)
        f.provider.catalog();self.assertEqual(self.api_count(),2)

    def test_changed_release_is_rejected_before_install_state_mutation(self):
        f=self.fixture;f.provider.catalog()
        source,app=package(f.root/'inputs','r2');f.publish(app,source,2)
        with self.assertRaises(LauncherError):
            with f.provider.installation_session(f.app):
                self.fail('Stale selection must not enter install')
        self.assertFalse(f.engine.paths.root.exists())

    def test_session_signature_is_reverified_not_blindly_cached(self):
        f=self.fixture
        with f.provider.installation_session(f.app):
            raw,sig,assets,release=f.provider._install_snapshot
            f.provider._install_snapshot=(raw+b' ',sig,assets,release)
            with self.assertRaisesRegex(LauncherError,'서명'):
                f.engine.install(f.app,f.provider)
        self.assertFalse(f.engine.paths.root.exists())

    def test_newer_persistent_trust_state_rejects_operation_snapshot(self):
        f=self.fixture
        with f.provider.installation_session(f.app):
            raw,sig=f.signer.pair([f.app],2)
            import json
            f.verifier.accept(raw,json.dumps(sig).encode())
            with self.assertRaisesRegex(LauncherError,'재전송'):
                f.engine.install(f.app,f.provider)
        self.assertFalse(f.engine.paths.root.exists())

    def test_failure_and_nested_session_never_leave_reusable_snapshot(self):
        f=self.fixture
        with self.assertRaisesRegex(RuntimeError,'trial interruption'):
            with f.provider.installation_session(f.app):
                with self.assertRaises(LauncherError):
                    with f.provider.installation_session(f.app): pass
                raise RuntimeError('trial interruption')
        self.assertIsNone(f.provider._install_snapshot)
        with f.provider.installation_session(f.app): pass
        self.assertEqual(self.api_count(),2)
