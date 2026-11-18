from dataclasses import replace
from pathlib import Path
import copy,json,unittest
from unittest.mock import patch
from tools import prepare_parallel_release as p
from southpaw_tools.common import LauncherError
from tests.support import temporary,TestSigner,package

class ParallelReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=temporary('parallel-release-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.assets=self.root/'assets';self.assets.mkdir()
        self.signer=TestSigner(self.root);self.signer.policy['minimum_sequence']=4
        self.key=next(iter(self.signer.policy['keys']));self.patcher=patch.object(p,'PRODUCTION_KEY',self.key);self.patcher.start();self.addCleanup(self.patcher.stop)
        apps=[]
        for app_id in sorted(p.APPS):
            src,app=package(self.root/app_id)
            app=replace(app,app_id=app_id,package_name=app_id+'--r1.zip')
            (self.assets/app.package_name).write_bytes(src.read_bytes());apps.append(app)
        self.apps=apps;self.signer.publish(self.assets,apps,8)
        self.legacy={'id':p.LEGACY_ID,'full_name':p.LEGACY,'visibility':'public','private':False}
        self.target={'id':999999,'full_name':p.CANONICAL,'visibility':'public','private':False,'permissions':{'admin':True}}
    def plan(self,target=None):return p.prepare(self.assets,self.signer.policy,self.legacy,target)
    def test_prepare_without_target_records_real_blocker_and_keeps_old_channel(self):
        before={f.name:f.read_bytes() for f in self.assets.iterdir()};plan=self.plan()
        self.assertIsNone(plan['canonical_repository_id']);self.assertFalse(plan['remote_write_authorized'])
        self.assertFalse(plan['legacy_transfer_or_rename_allowed']);self.assertEqual(len(plan['assets']),8)
        self.assertEqual(before,{f.name:f.read_bytes() for f in self.assets.iterdir()})
    def test_new_identity_is_separate_and_does_not_change_signatures(self):
        plan=self.plan(self.target);self.assertEqual(plan['canonical_repository_id'],999999)
        self.assertTrue(plan['gui_014_015_still_use_legacy_origin']);self.assertFalse(plan['resign_catalog'])
    def test_wrong_legacy_identity_rejected(self):
        self.legacy['id']+=1
        with self.assertRaises(LauncherError):self.plan()
    def test_old_id_cannot_be_disguised_as_parallel_target(self):
        self.target['id']=p.LEGACY_ID
        with self.assertRaises(LauncherError):self.plan(self.target)
    def test_other_owner_private_or_no_admin_rejected(self):
        for changes in [{'full_name':'attacker/creative-group-releases'},{'visibility':'private','private':True},{'permissions':{'push':True}}]:
            target={**self.target,**changes}
            with self.subTest(changes=changes),self.assertRaises(LauncherError):self.plan(target)
    def test_wrong_key_or_changed_minimum_rejected(self):
        for changes in [{'keys':{'wrong':'value'}},{'minimum_sequence':1}]:
            with self.subTest(changes=changes),self.assertRaises(LauncherError):p.prepare(self.assets,{**self.signer.policy,**changes},self.legacy)
    def test_tampered_zip_and_missing_complete_replica_rejected(self):
        file=self.assets/self.apps[0].package_name;file.write_bytes(b'changed')
        with self.assertRaises(LauncherError):self.plan()
        file.unlink()
        with self.assertRaises(LauncherError):self.plan()
    def test_unknown_asset_rejected(self):
        (self.assets/'secret.txt').write_text('synthetic')
        with self.assertRaises(LauncherError):self.plan()
    def test_invalid_signature_rejected(self):
        f=self.assets/'catalog.sig.json';sig=json.loads(f.read_bytes());sig['signature']='A'*len(sig['signature']);f.write_text(json.dumps(sig))
        with self.assertRaises(LauncherError):self.plan()
    def test_release_replica_requires_every_exact_asset(self):
        plan=self.plan(self.target);release={'tag_name':plan['tag'],'assets':[{'name':r['name'],'size':r['size'],'digest':'sha256:'+r['sha256']} for r in plan['assets']]}
        self.assertTrue(p.verify_release_assets(plan,release));release['assets'].pop()
        with self.assertRaises(LauncherError):p.verify_release_assets(plan,release)
    def test_replica_rejects_same_name_different_bytes_or_sequence(self):
        plan=self.plan();release={'tag_name':plan['tag'],'assets':[{'name':r['name'],'size':r['size'],'digest':'sha256:'+r['sha256']} for r in plan['assets']]}
        bad=copy.deepcopy(release);bad['assets'][0]['digest']='sha256:'+'0'*64
        with self.assertRaises(LauncherError):p.verify_release_assets(plan,bad)
        release['tag_name']='production-catalog-000009'
        with self.assertRaises(LauncherError):p.verify_release_assets(plan,release)

    def test_initial_copy_never_creates_or_edits_existing_legacy_release(self):
        plan=self.plan();release={'tag_name':plan['tag'],'draft':False,'prerelease':False,
            'assets':[{'name':r['name'],'size':r['size'],'digest':'sha256:'+r['sha256']} for r in plan['assets']]}
        actual=p.prepare(self.assets,self.signer.policy,self.legacy,self.target,release)
        self.assertTrue(actual['legacy_existing_release_verified'])
        self.assertFalse(actual['legacy_release_create_or_edit'])
        self.assertEqual(actual['prepare_action'],'initial_canonical_copy_only')
        release['draft']=True
        with self.assertRaises(LauncherError):p.prepare(self.assets,self.signer.policy,self.legacy,self.target,release)

if __name__=='__main__':unittest.main()
