import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.launcher_diagnostics import collect
from tests.support import temporary, TestSigner, package
from southpaw_tools.common import atomic_json, digest
from southpaw_tools.catalog_trust import CatalogVerifier


class DiagnosticsTests(unittest.TestCase):
    def test_missing_paths_remain_missing(self):
        with temporary('diag-') as folder:
            root = Path(folder)/'missing'
            result = collect(root)
            self.assertFalse(root.exists())
            self.assertTrue(result['read_only'])
            self.assertFalse(result['network_requested'])
            self.assertEqual(result['apps'], [])

    def test_signed_cache_and_versions_are_read_without_changes_or_secret_output(self):
        with temporary('diag-') as folder:
            root = Path(folder); data = root/'data'; data.mkdir()
            signer = TestSigner(root)
            source, app = package(root, 'r2')
            raw, sig = signer.pair([app], 2)
            verifier = CatalogVerifier(signer.policy, data/'catalog-trust.json')
            verifier.accept(raw, json.dumps(sig).encode('utf-8'))
            atomic_json(data/'settings.json', {'github_repository': 'owner/repo', 'lan_token': 'SECRET-NEVER-PRINT'})
            atomic_json(data/'apps/dummy/active.json', {'app': app.to_dict()})
            atomic_json(data/'apps/dummy/releases/r2/receipt.json', {'app': app.to_dict()})
            before = {str(p): digest(p) for p in root.rglob('*') if p.is_file()}
            with patch.object(CatalogVerifier, 'bundled', return_value=verifier):
                report = collect(data)
            self.assertEqual(report['catalog']['status'], 'cached_signature_verified')
            self.assertEqual(report['catalog']['sequence'], 2)
            self.assertFalse(report['apps'][0]['update_available'])
            self.assertTrue(report['apps'][0]['active_matches_receipt'])
            self.assertNotIn('SECRET', json.dumps(report))
            self.assertEqual(before, {str(p): digest(p) for p in root.rglob('*') if p.is_file()})

    def test_corrupt_json_is_reported_without_raw_error_contents(self):
        with temporary('diag-') as folder:
            root = Path(folder)
            (root/'settings.json').write_text('{SECRET', encoding='utf-8')
            report = collect(root)
            self.assertTrue(report['issues'])
            self.assertNotIn('SECRET', json.dumps(report))

    def test_malformed_active_and_session_do_not_prevent_diagnosis(self):
        with temporary('diag-') as folder:
            root = Path(folder); data = root/'data'; home = root/'launcher-home'
            atomic_json(data/'apps/dummy/active.json', {'app': 'wrong type'})
            atomic_json(home/'sessions/example/process.json', {'missing': 'identity'})
            report = collect(data, home)
            self.assertIsNone(report['apps'][0]['version'])
            self.assertIsNone(report['launcher']['sessions'][0]['running'])

    def test_untrusted_cache_is_never_reported_as_verified(self):
        with temporary('diag-') as folder:
            root = Path(folder)
            atomic_json(root/'catalog-trust.json', {'catalog': 'invalid', 'signature': 'invalid'})
            self.assertEqual(collect(root)['catalog']['status'], 'cache_unverified')

    def test_recent_gui_snapshot_preserves_failure_and_hides_unexpected_fields(self):
        with temporary('diag-') as folder:
            root = Path(folder)
            atomic_json(root/'diagnostics/gui-123.json', {'version': '0.1.4',
                'updated_at_utc': '2026-11-12T01:00:00+00:00', 'last_operation': 'GitHub 업데이트 확인',
                'result': 'failed', 'token': 'SECRET',
                'last_catalog_check': {'at_utc': '2026-11-12T01:00:00+00:00', 'result': 'failed'}})
            report = collect(root)
            self.assertEqual(report['recent_gui']['last_catalog_check']['result'], 'failed')
            self.assertIsNotNone(report['recent_gui']['last_catalog_check']['at_utc'])
            self.assertNotIn('SECRET', json.dumps(report))

    def test_sessions_and_errors_hide_nonce_and_raw_stderr(self):
        with temporary('diag-') as folder:
            root = Path(folder); home = root/'launcher-home'; data = root/'data'
            atomic_json(home/'sessions/SECRET-NONCE/process.json', {'pid': 0})
            (home/'sessions/SECRET-NONCE/stderr.log').write_text('SECRET-TOKEN', encoding='utf-8')
            atomic_json(home/'bootstrap-errors/test.json', {'error_type': 'PermissionError', 'error': 'SECRET-USER-PATH'})
            with patch('southpaw_tools.windows_process.still_same', return_value=False):
                report = collect(data, home)
            self.assertNotIn('SECRET', json.dumps(report))
            self.assertEqual(report['launcher']['recent_error_types'], ['PermissionError'])

