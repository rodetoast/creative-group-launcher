from __future__ import annotations

import hashlib
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path

from southpaw_tools.archive import extract_checked
from southpaw_tools.catalog import AppRelease, load_catalog, parse_catalog
from southpaw_tools.common import LauncherError, digest
from tests.support import package, temporary


class CatalogArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary("southpaw-catalog-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source, self.app = package(self.root)

    def test_exact_five_display_names_and_exclusions(self):
        apps = load_catalog(Path(__file__).parents[1] / "southpaw_tools/data/catalog.json")
        self.assertEqual([a.display_name for a in apps], ["TileNamer", "ase_viewer", "AsepriteTagMaster", "Ase-PS Bridge Pro", "Pivot_Fixer"])
        self.assertEqual(apps[1].version, "0.5.8.3")
        self.assertFalse(apps[2].published)
        self.assertEqual(len({a.app_id for a in apps}), 5)

    def test_catalog_rejects_bad_versions_identity_hash_and_type(self):
        for change in ({"version": "latest"}, {"app_id": "../escape"}, {"sha256": "bad"},
                       {"package_size": True}, {"published": "true"}, {"published_at": "today"},
                       {"executable_relative_path": "C:/bad.exe"}, {"package_name": "../evil.zip"}):
            with self.subTest(change=change), self.assertRaises(LauncherError):
                AppRelease.parse({**self.app.to_dict(), **change})

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(LauncherError):
            parse_catalog({"schema_version": 1, "apps": [self.app.to_dict()] * 2})

    def test_release_identity_does_not_depend_on_version_string(self):
        self.assertTrue(replace(self.app, release_id="r2").is_new_release(self.app))
        with self.assertRaises(LauncherError):
            replace(self.app, sha256="f" * 64).is_new_release(self.app)

    def test_nested_onedir_paths_and_resources_preserved(self):
        source, app = package(self.root, "nested", nested=True)
        result = extract_checked(source, self.root / "extract", app)
        self.assertIn("Dummy/Dummy.exe", result)
        self.assertTrue((self.root / "extract/Dummy/asset.json").is_file())

    def test_legacy_windows_zip_backslashes_work(self):
        contents = {"Dummy\\Dummy.exe": b"MZ legacy", "Dummy\\asset.json": b"{}"}
        source, app = package(self.root, "legacy", nested=True, contents=contents)
        app = replace(app, executable_sha256=hashlib.sha256(b"MZ legacy").hexdigest())
        extract_checked(source, self.root / "legacy-out", app)
        self.assertTrue((self.root / "legacy-out/Dummy/Dummy.exe").is_file())

    def test_path_escape_and_windows_special_names_rejected(self):
        bad_names = ["../escape.txt", "..\\escape.txt", "/root.txt", "\\\\host\\share.txt",
                     "C:/escape.txt", "file:stream", "CON.txt", "a/../evil", "a./file", "a /file"]
        for index, name in enumerate(bad_names):
            source, app = package(self.root, f"bad{index}", contents={name: b"MZ test"})
            with self.subTest(name=name), self.assertRaises(LauncherError):
                extract_checked(source, self.root / f"out{index}", app)
        self.assertFalse((self.root.parent / "escape.txt").exists())

    def test_case_collision_file_parent_and_symlink_rejected(self):
        for index, contents in enumerate((
            {"A.txt": b"a", "a.txt": b"b"}, {"folder": b"a", "folder/file": b"b"},
        )):
            source, app = package(self.root, f"collision{index}", contents=contents)
            with self.assertRaises(LauncherError):
                extract_checked(source, self.root / f"collision-out{index}", app)
        info = zipfile.ZipInfo("link")
        info.create_system = 3
        info.external_attr = (0o120777 << 16)
        source = self.root / "link.zip"
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr(info, "../other")
        app = replace(self.app, package_size=source.stat().st_size, sha256=digest(source))
        with self.assertRaises(LauncherError):
            extract_checked(source, self.root / "links-out", app)

    def test_embedded_nul_path_rejected_before_zip_truncation(self):
        source, app = package(self.root, "nul-test", contents={"badname.txt": b"MZ test"})
        source.write_bytes(source.read_bytes().replace(b"badname.txt", b"bad\x00ame.txt"))
        app = replace(app, package_size=source.stat().st_size, sha256=digest(source))
        with self.assertRaises(LauncherError):
            extract_checked(source, self.root / "nul-out", app)

    def test_wrong_zip_hash_exe_hash_and_missing_resource_rejected(self):
        for index, app in enumerate((replace(self.app, sha256="f" * 64),
                                     replace(self.app, executable_sha256="f" * 64),
                                     replace(self.app, required_paths=["missing.json"]))):
            with self.subTest(index=index), self.assertRaises(LauncherError):
                extract_checked(self.source, self.root / f"invalid{index}", app)


if __name__ == "__main__":
    unittest.main()
