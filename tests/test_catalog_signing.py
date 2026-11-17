from __future__ import annotations

import base64
import hashlib
import io
import json
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from southpaw_tools.admin import publish
from southpaw_tools.catalog_trust import CatalogVerifier, b64, catalog_bytes, sign, strict_json
from southpaw_tools.common import LauncherError, atomic_json
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from southpaw_tools.providers import HttpProvider
from tests.support import FakeProcesses, LocalProvider, TestSigner, package, repository, temporary


class CatalogSigningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary("signed-catalog-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source, self.app = package(self.root/'inputs')
        self.signer = TestSigner(self.root)
        self.state = self.root/'client/catalog-trust.json'
        self.verifier = self.signer.verifier(self.state)
        self.raw, self.signature = self.signer.pair([self.app], 10)
        self.sig = json.dumps(self.signature).encode()

    def mocked_provider(self, raw=None, sig=None, source=None):
        provider = HttpProvider('http://127.0.0.1:8765', verifier=self.verifier)
        def response(path):
            if path == '/api/catalog':
                return io.BytesIO(self.raw if raw is None else raw)
            if path == '/api/catalog.sig':
                if sig == b'':
                    raise LauncherError('missing signature')
                return io.BytesIO(self.sig if sig is None else sig)
            if path.startswith('/packages/'):
                data = (source or self.source).read_bytes()
                stream = io.BytesIO(data)
                stream.headers = {'Content-Length':str(len(data))}
                return stream
            raise AssertionError(path)
        provider._open = response
        return provider

    def test_valid_signature_and_cached_state(self):
        self.assertEqual(self.verifier.accept(self.raw,self.sig), [self.app])
        self.assertEqual(self.verifier.cached(), [self.app])

    def test_single_character_change_rejected_without_state(self):
        changed = self.raw.replace(b'Dummy Tool', b'Dummy Fool')
        with self.assertRaises(LauncherError):
            self.verifier.accept(changed,self.sig)
        self.assertFalse(self.state.exists())

    def test_missing_and_corrupt_signature_rejected(self):
        for signature in (b'', b'{}', b'not json', json.dumps({**self.signature,'signature':b64(b'x'*64)}).encode()):
            with self.subTest(signature=signature[:15]), self.assertRaises(LauncherError):
                self.verifier.accept(self.raw,signature)

    def test_wrong_public_key_rejected(self):
        folder = self.root/'other'
        folder.mkdir()
        other = TestSigner(folder)
        signature = json.dumps({**sign(self.raw,other.private), 'key_id':self.signature['key_id']}).encode()
        with self.assertRaises(LauncherError):
            self.verifier.accept(self.raw,signature)

    def test_wrong_key_id_rejected(self):
        signature = {**self.signature,'key_id':'f'*64}
        with self.assertRaises(LauncherError):
            self.verifier.accept(self.raw,json.dumps(signature).encode())

    def test_package_metadata_tampering_rejected(self):
        for changes in ({'sha256':'f'*64}, {'package_size':self.app.package_size+1},
                        {'package_name':'evil.zip'}, {'release_id':'evil'}, {'app_id':'evil'}):
            with self.subTest(changes=changes), self.assertRaises(LauncherError):
                self.verifier.accept(catalog_bytes([replace(self.app,**changes)],10),self.sig)

    def test_replay_lower_sequence_rejected_after_restart(self):
        self.verifier.accept(self.raw,self.sig)
        raw,sig=self.signer.pair([self.app],9)
        restarted=self.signer.verifier(self.state)
        with self.assertRaises(LauncherError):
            restarted.accept(raw,json.dumps(sig).encode())
        self.assertEqual(restarted.cached(),[self.app])

    def test_equal_sequence_different_contents_rejected(self):
        self.verifier.accept(self.raw,self.sig)
        raw,sig=self.signer.pair([replace(self.app,release_notes='changed')],10)
        with self.assertRaises(LauncherError):
            self.verifier.accept(raw,json.dumps(sig).encode())

    def test_equal_sequence_identical_bytes_accepted(self):
        self.verifier.accept(self.raw,self.sig)
        before=self.state.read_bytes()
        self.assertEqual(self.verifier.accept(self.raw,self.sig),[self.app])
        self.assertEqual(before,self.state.read_bytes())

    def test_first_use_minimum_sequence(self):
        policy={**self.signer.policy,'minimum_sequence':11}
        with self.assertRaises(LauncherError):
            CatalogVerifier(policy,self.state).accept(self.raw,self.sig)

    def test_mixed_publish_generations_fail_preserving_cache(self):
        self.verifier.accept(self.raw,self.sig)
        before=self.state.read_bytes()
        raw,sig=self.signer.pair([self.app],11)
        for payload,signature in ((self.raw,json.dumps(sig).encode()),(raw,self.sig)):
            with self.subTest(payload=payload[:10]), self.assertRaises(LauncherError):
                self.verifier.accept(payload,signature)
        self.assertEqual(before,self.state.read_bytes())

    def test_duplicate_json_and_bad_signature_format(self):
        raws=[self.raw.replace(b'"sequence": 10',b'"sequence": 10, "sequence": 11'),
              self.raw.replace(b'"sequence": 10',b'"sequence": true'),
              self.raw.replace(b'creative-group-launcher',b'wrong-repository')]
        for raw in raws:
            with self.subTest(raw=raw[:10]), self.assertRaises(LauncherError):
                self.verifier.accept(raw,json.dumps(sign(raw,self.signer.private)).encode())
        for changes in ({'algorithm':'RSA'},{'schema_version':True},{'signature':'@@@'},{'public_key':'network key'}):
            with self.subTest(changes=changes), self.assertRaises(LauncherError):
                self.verifier.accept(self.raw,json.dumps({**self.signature,**changes}).encode())

    def test_corrupt_local_state_never_resets(self):
        self.state.parent.mkdir(parents=True)
        self.state.write_bytes(b'broken')
        with self.assertRaises(LauncherError):
            self.verifier.accept(self.raw,self.sig)
        self.assertEqual(self.state.read_bytes(),b'broken')

    def test_no_implicit_unsigned_or_network_key_trust(self):
        blank={**self.signer.policy,'keys':{}}
        with self.assertRaises(LauncherError):
            CatalogVerifier(blank,self.state).accept(self.raw,self.sig)
        with self.assertRaises(LauncherError):
            self.mocked_provider(sig=b'').catalog()

    def test_signature_failure_precedes_install_mutation(self):
        engine=Installer(AppPaths(self.root/'installed'),FakeProcesses())
        engine.install(self.app,LocalProvider(self.source))
        root=engine.paths.root
        before={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file()}
        source,new=package(self.root/'inputs','r2')
        provider=self.mocked_provider(raw=catalog_bytes([new],11),source=source)
        with self.assertRaises(LauncherError):
            engine.install(new,provider)
        after={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file()}
        self.assertEqual(before,after)
        self.assertFalse(engine.pending_recovery('dummy'))

    def test_signed_r1_to_r2_update_and_offline_local_state(self):
        engine=Installer(AppPaths(self.root/'installed'),FakeProcesses())
        engine.install(self.app,self.mocked_provider())
        source,new=package(self.root/'inputs','r2')
        raw,sig=self.signer.pair([new],11)
        engine.install(new,self.mocked_provider(raw,json.dumps(sig).encode(),source))
        self.assertEqual(engine.installed('dummy'),new)
        self.assertFalse(engine.pending_recovery('dummy'))
        # Pure local query with no HTTP/launch call.
        self.assertEqual(Installer(engine.paths).installed('dummy'),new)
        self.assertEqual(self.verifier.cached(),[new])

    def test_caller_cannot_bypass_with_modified_app(self):
        engine=Installer(AppPaths(self.root/'installed'))
        with self.assertRaises(LauncherError):
            engine.install(replace(self.app,package_name='evil.zip'),self.mocked_provider())
        self.assertFalse(engine.paths.root.exists())

    def test_stale_provider_cannot_bypass_new_high_water(self):
        old=self.mocked_provider()
        old.catalog()
        raw,sig=self.signer.pair([self.app],11)
        self.verifier.accept(raw,json.dumps(sig).encode())
        with self.assertRaises(LauncherError):
            old.download(self.app,self.root/'forbidden.zip')
        self.assertFalse((self.root/'forbidden.zip').exists())

    def test_cache_write_failure_blocks_acceptance(self):
        with patch('southpaw_tools.catalog_trust.atomic_json',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.verifier.accept(self.raw,self.sig)

    def test_admin_requires_key_sequence_and_private_key_outside_repo(self):
        repo=self.root/'repo'
        repository(repo,self.source,replace(self.app,published=False))
        kwargs=dict(version='1.0.0',release_id='new',executable='Dummy.exe',expected_sha256=self.app.sha256,
                    expected_exe_sha256=self.app.executable_sha256,approved=True)
        for extra in ({},{'signing_key':self.signer.path},{'signing_key':repo/'key.pem','sequence':1}):
            with self.subTest(extra=str(extra)),self.assertRaises(LauncherError):
                publish(repo,'dummy',self.source,**kwargs,**extra)

    def test_admin_signed_publication_is_verifiable(self):
        repo=self.root/'repo'
        repository(repo,self.source,replace(self.app,published=False))
        app=publish(repo,'dummy',self.source,version='1.0.0',release_id='signed-r1',
                    executable='Dummy.exe',expected_sha256=self.app.sha256,expected_exe_sha256=self.app.executable_sha256,
                    approved=True,signing_key=self.signer.path,sequence=1)
        self.assertEqual(self.verifier.accept((repo/'catalog.json').read_bytes(),(repo/'catalog.sig.json').read_bytes()),[app])
        with self.assertRaises(LauncherError):
            publish(repo,'dummy',self.source,version='1.0.0',release_id='signed-r2',executable='Dummy.exe',
                    expected_sha256=self.app.sha256,expected_exe_sha256=self.app.executable_sha256,
                    approved=True,signing_key=self.signer.path,sequence=1)

    def test_byte_identity_matters_even_for_equivalent_json(self):
        with self.assertRaises(LauncherError):
            self.verifier.accept(json.dumps(json.loads(self.raw)).encode(),self.sig)

    def test_partial_publish_fails_closed_without_overwriting_old_catalog(self):
        repo=self.root/'repo'
        repository(repo,self.source,self.app)
        self.signer.publish(repo,[self.app],10)
        before=(repo/'catalog.json').read_bytes()
        with patch('southpaw_tools.admin.atomic_bytes',side_effect=OSError('catalog replacement failed')):
            with self.assertRaises(OSError):
                publish(repo,'dummy',self.source,version='1.0.0',release_id='r2',executable='Dummy.exe',
                        expected_sha256=self.app.sha256,expected_exe_sha256=self.app.executable_sha256,
                        approved=True,signing_key=self.signer.path,sequence=11)
        self.assertEqual((repo/'catalog.json').read_bytes(),before)
        self.assertFalse((repo/'packages/dummy--r2.zip').exists())
        with self.assertRaises(LauncherError):
            self.verifier.accept(before,(repo/'catalog.sig.json').read_bytes())

    def test_signature_failure_preserves_previous_trusted_cache(self):
        self.verifier.accept(self.raw,self.sig)
        before=self.state.read_bytes()
        with self.assertRaises(LauncherError):
            self.verifier.accept(self.raw+b' ',self.sig)
        self.assertEqual(self.state.read_bytes(),before)


if __name__ == '__main__':
    unittest.main()
