import copy,json,shutil,unittest,urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from southpaw_tools.catalog_trust import CatalogVerifier,catalog_bytes,sign
from southpaw_tools.common import LauncherError,digest
from southpaw_tools.github_channels import CANONICAL_REPOSITORY as REPO,CANONICAL_REPOSITORY_ID as ID,CANONICAL_CATALOG_ID as CID,latest_api_url
from southpaw_tools.github_provider import GitHubReleasesProvider,AssetRedirect
from southpaw_tools.managed_update import initialize,default_data_root,channel_policy
from southpaw_tools.self_update import SelfUpdater
from southpaw_tools.paths import AppPaths
from southpaw_tools.setup_support import check
from tests.support import temporary,TestSigner
from tests.self_update_support import package
from tests.test_github_provider import FakeGitHub

class CanonicalChannelTests(unittest.TestCase):
    def setUp(self):
        self.tmp=temporary('canonical-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.signer=TestSigner(self.root);self.policy={**self.signer.policy,'catalog_id':CID,'minimum_sequence':9}
        self.channel={'repository':REPO,'repository_id':ID,'policy':self.policy};self.v=CatalogVerifier(self.policy,self.root/'trust.json')
        self.zip,self.app=package(self.root/'inputs','rod-r1','0.1.6',executable='CreativeGroupLauncher.exe')
        self.raw=catalog_bytes([self.app],9,catalog_id=CID);self.sig=sign(self.raw,self.signer.private)
    def provider(self):return GitHubReleasesProvider(REPO,repository_id=ID,verifier=self.v)
    def route(self,p,raw=None,sig=None,asset_owner=REPO):
        transport=FakeGitHub();rows=[]
        for i,(name,body) in enumerate([('catalog.json',raw or self.raw),('catalog.sig.json',json.dumps(sig or self.sig).encode()),(self.app.package_name,self.zip.read_bytes())],1):
            url=f'https://github.com/{asset_owner}/releases/download/rod-catalog-000009/{name}';transport.routes[url]=body;rows.append({'id':i,'name':name,'state':'uploaded','size':len(body),'browser_download_url':url})
        transport.routes[p.api_url]=json.dumps({'id':99,'tag_name':'rod-catalog-000009','draft':False,'prerelease':False,'assets':rows}).encode();p.api_opener=p.asset_opener=transport;return transport
    def test_explicit_new_id_and_implicit_legacy_id_are_distinct(self):
        self.assertIn('/1462539740/',self.provider().api_url)
        self.assertIn('/1447701732/',latest_api_url(REPO))
        self.assertIn('/1447701732/',latest_api_url('toast-source/creative-group-releases'))
    def test_wrong_ids_or_owners_rejected(self):
        for repo,identity in [(REPO,1447701732),(REPO,True),('toast-source/creative-group-releases',ID),('attacker/creative-group-releases',ID)]:
            with self.subTest(repo=repo,identity=identity),self.assertRaises(LauncherError):GitHubReleasesProvider(repo,repository_id=identity,verifier=self.v)
    def test_new_policy_cannot_use_implicit_old_endpoint_or_vice_versa(self):
        with self.assertRaises(LauncherError):GitHubReleasesProvider(REPO,verifier=self.v)
        old=self.signer.verifier(self.root/'old.json')
        with self.assertRaises(LauncherError):GitHubReleasesProvider(REPO,repository_id=ID,verifier=old)
    def test_old_catalog_even_same_key_or_higher_sequence_cannot_cross_namespace(self):
        raw=catalog_bytes([self.app],99)
        with self.assertRaises(LauncherError):self.v.accept(raw,json.dumps(sign(raw,self.signer.private)).encode())
        self.assertFalse(self.v.state_path.exists())
        old=self.signer.verifier(self.root/'old.json')
        with self.assertRaises(LauncherError):old.verify(self.raw,json.dumps(self.sig).encode())
    def test_copied8_below_new_minimum_cannot_be_accepted(self):
        raw=catalog_bytes([self.app],8,catalog_id=CID)
        with self.assertRaises(LauncherError):self.v.accept(raw,json.dumps(sign(raw,self.signer.private)).encode())
    def test_catalog9_and_zip_use_exact_new_assets(self):
        p=self.provider();t=self.route(p);self.assertEqual(p.catalog(),[self.app]);target=self.root/'download.zip'
        with p.installation_session(self.app):p.download(self.app,target)
        self.assertEqual(digest(target),self.app.sha256)
        self.assertTrue(all(not req.has_header('Authorization') for req in t.calls))
    def test_new_channel_rejects_legacy_asset_urls_without_trust_write(self):
        p=self.provider();self.route(p,asset_owner='toast-source/creative-group-releases')
        with self.assertRaises(LauncherError):p.catalog()
        self.assertFalse(self.v.state_path.exists())
    def test_canonical_redirect_cannot_fall_back_to_legacy_owner(self):
        h=AssetRedirect(REPO,repository_id=ID);new=f'https://github.com/{REPO}/releases/download/t/a.zip';old=new.replace('rodetoast','toast-source')
        with self.assertRaises(LauncherError):h.redirect_request(urllib.request.Request(new),None,301,'',{},old)
    def test_namespace9_to_10_accepts_rollback9_rejected_and_hash_preserved(self):
        self.v.accept(self.raw,json.dumps(self.sig).encode());new=catalog_bytes([self.app],10,catalog_id=CID);self.v.accept(new,json.dumps(sign(new,self.signer.private)).encode());before=self.v.state_path.read_bytes()
        with self.assertRaises(LauncherError):self.v.accept(self.raw,json.dumps(self.sig).encode())
        self.assertEqual(self.v.state_path.read_bytes(),before)
    def test_default_data_root_is_separate_without_changing_old_default(self):
        self.assertEqual(default_data_root(self.channel).name,'ToolsLauncherRodetoast')
        self.assertEqual(default_data_root({'repository':'toast-source/creative-group-releases'}),AppPaths.default().root)
    def test_first_setup_rejects_existing_data_before_creating_files(self):
        data=self.root/'existing-data';data.mkdir();(data/'work.txt').write_text('keep');home=self.root/'program'
        with self.assertRaises(LauncherError):check(home,data,{'channel':self.channel},inspect_processes=False)
        self.assertFalse(home.exists());self.assertEqual((data/'work.txt').read_text(),'keep')
    def test_seed_initialization_and_provider_identity_check(self):
        seed=self.root/'seed';seed.mkdir();(seed/'catalog.json').write_bytes(self.raw);(seed/'catalog.sig.json').write_text(json.dumps(self.sig));shutil.copyfile(self.zip,seed/self.app.package_name);data=self.root/'data';data.mkdir();home=self.root/'home';initialize(home,data,seed,self.channel);u=SelfUpdater(home,channel=self.channel);self.assertEqual(u.current(),self.app)
        p=GitHubReleasesProvider(REPO,repository_id=ID,verifier=u.verifier);u._provider(p);p.repository_id=1447701732
        with self.assertRaises(LauncherError):u._provider(p)
    def test_ui_factory_passes_explicit_binding_without_creating_qt_window(self):
        from southpaw_tools.ui import MainWindow
        view=SimpleNamespace(config={'github_repository':REPO},managed_session=SimpleNamespace(channel=self.channel),catalog_verifier=self.v)
        self.assertEqual(MainWindow._github_provider(view).repository_id,ID)
    def test_channel_file_requires_explicit_pair_namespace_and_minimum(self):
        for change in [{'repository_id':None},{'repository_id':1447701732},{'policy':{**self.policy,'minimum_sequence':4}},{'policy':self.signer.policy}]:
            value={**self.channel,**change}
            with self.subTest(change=change),patch('southpaw_tools.managed_update.strict_json',return_value=value),patch.object(Path,'read_bytes',return_value=b'{}'),self.assertRaises(LauncherError):channel_policy()
        with patch('southpaw_tools.managed_update.strict_json',return_value=self.channel),patch.object(Path,'read_bytes',return_value=b'{}'):
            self.assertEqual(channel_policy(),self.channel)

if __name__=='__main__':unittest.main()
