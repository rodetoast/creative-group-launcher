import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from southpaw_tools.common import LauncherError, atomic_json, digest
from southpaw_tools.setup_support import check, shortcut, shortcut_target, stamp, verify_payload
from southpaw_tools.windows_paths import WindowsPathError
from southpaw_tools.windows_shell import APP_ID, GUID, _check, _method, shortcut_app_id
from tests.self_update_support import package


@unittest.skipUnless(os.name == "nt", "Windows installer and Shell integration")
class SetupSupportTests(unittest.TestCase):
    def test_console_free_entry_keeps_initial_failure_in_file(self):
        from southpaw_tools.bootstrap import main
        from southpaw_tools.common import read_json
        home = self.folder / "failed-bootstrap"
        with patch('southpaw_tools.bootstrap.Bootstrap', side_effect=LauncherError('startup failure')):
            with patch.object(sys, 'stdout', None), patch.object(sys, 'stderr', None):
                self.assertEqual(main(['--home', str(home)]), 1)
        logs = list((home / 'bootstrap-errors').glob('*.json'))
        self.assertEqual(len(logs), 1)
        value = read_json(logs[0])
        self.assertEqual(value['error_type'], 'LauncherError')
        self.assertIn('LauncherError', value['error'])
        self.assertEqual(value['diagnostics']['schema_version'], 1)
        self.assertEqual(value['diagnostics']['failure']['exception_class'], 'LauncherError')
        self.assertTrue(value['diagnostics']['failure']['traceback'])

    def test_incomplete_copy_or_incomplete_removal_is_not_success(self):
        self.installed()
        verify_payload(self.root, self.manifest)
        with self.assertRaises(LauncherError):
            verify_payload(self.root, self.manifest, removed=True)
        (self.root / "CGLBootstrap.exe").unlink()
        with self.assertRaises(LauncherError):
            verify_payload(self.root, self.manifest)
        verify_payload(self.root, self.manifest, removed=True)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="cgl-setup-", dir="C:/Dev")
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)
        self.root, self.data = self.folder / "program", self.folder / "data"
        self.data.mkdir()
        self.work = self.data / "work.txt"
        self.work.write_text("keep")
        _, app = package(self.folder / "input", "launcher-r1")
        self.manifest = {"setup_version": "0.1.1.1", "launcher": app.to_dict(),
                         "launcher_files": ["Launcher.exe", "assets/layout.json"],
                         "files": {"CGLBootstrap.exe": digest(self.folder / "input/launcher-r1.zip")}}

    def installed(self):
        check(self.root, self.data, self.manifest, inspect_processes=False)
        self.root.mkdir()
        shutil.copyfile(self.folder / "input/launcher-r1.zip", self.root / "CGLBootstrap.exe")
        (self.root / "Uninstall.exe").write_bytes(b"owned-uninstaller")
        stamp(self.root, self.data, self.manifest)

    def test_same_version_reinstall_and_uninstall_check_preserve_state_and_user_files(self):
        self.installed()
        unknown = self.root / "user-note.txt"
        unknown.write_text("preserve")
        versions = self.root / "launcher-home/store/current-version.txt"
        versions.parent.mkdir(parents=True)
        versions.write_text("newer-runtime")
        before = {p: digest(p) for p in self.folder.rglob("*") if p.is_file()}
        check(self.root, self.data, self.manifest, inspect_processes=False)
        check(self.root, self.data, self.manifest, uninstall=True, inspect_processes=False)
        self.assertEqual({p: digest(p) for p in self.folder.rglob("*") if p.is_file()}, before)

    def test_changed_owned_file_is_rejected_without_overwrite(self):
        self.installed()
        (self.root / "CGLBootstrap.exe").write_bytes(b"changed")
        with self.assertRaisesRegex(LauncherError, "변경"):
            check(self.root, self.data, self.manifest, inspect_processes=False)
        self.assertEqual((self.root / "CGLBootstrap.exe").read_bytes(), b"changed")
        self.assertEqual(self.work.read_text(), "keep")

    def test_foreign_nonempty_directory_and_overlapping_data_are_rejected(self):
        self.root.mkdir()
        (self.root / "foreign.txt").write_text("preserve")
        with self.assertRaisesRegex(LauncherError, "비어 있는"):
            check(self.root, self.data, self.manifest, inspect_processes=False)
        with self.assertRaises(LauncherError):
            check(self.data, self.data / "child", self.manifest, inspect_processes=False)
        self.assertEqual((self.root / "foreign.txt").read_text(), "preserve")

    def test_long_install_path_is_rejected_before_file_creation(self):
        long_root = self.folder / ("a" * 120)
        with self.assertRaises((WindowsPathError, OSError)):
            check(long_root, self.data, self.manifest, inspect_processes=False)
        self.assertFalse(long_root.exists())

    def test_running_check_prevents_install_or_uninstall(self):
        self.installed()
        with patch("southpaw_tools.setup_support._running", side_effect=LauncherError("실행 중")):
            with self.assertRaisesRegex(LauncherError, "실행 중"):
                check(self.root, self.data, self.manifest, uninstall=True)
        self.assertEqual(self.work.read_text(), "keep")

    def make_link(self, path, target):
        ole = ctypes.OleDLL("ole32")
        _check(ole.CoInitializeEx(None, 2))
        link, persist = ctypes.c_void_p(), ctypes.c_void_p()
        try:
            clsid = GUID.parse("00021401-0000-0000-c000-000000000046")
            iid = GUID.parse("000214f9-0000-0000-c000-000000000046")
            ole.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD,
                                            ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
            _check(ole.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(link)))
            _check(_method(link, 20, wintypes.LPCWSTR)(link, str(target)))
            pid = GUID.parse("0000010b-0000-0000-c000-000000000046")
            _check(_method(link, 0, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))(
                link, ctypes.byref(pid), ctypes.byref(persist)))
            _check(_method(persist, 6, wintypes.LPCWSTR, wintypes.BOOL)(persist, str(path), True))
        finally:
            if persist:
                _method(persist, 2)(persist)
            if link:
                _method(link, 2)(link)
            ole.CoUninitialize()

    def test_real_shortcut_identity_and_only_owned_shortcut_removal(self):
        self.installed()
        path = self.folder / "한글 바로가기.lnk"
        self.make_link(path, self.root / "CGLBootstrap.exe")
        self.assertEqual(shortcut_target(path), self.root / "CGLBootstrap.exe")
        shortcut(path, self.root)
        self.assertEqual(shortcut_app_id(path), APP_ID)
        shortcut(path, self.root, remove=True)
        self.assertFalse(path.exists())
        self.make_link(path, self.folder / "other.exe")
        shortcut(path, self.root, remove=True)
        self.assertTrue(path.exists())

    def test_install_does_not_overwrite_a_foreign_same_name_shortcut(self):
        self.installed()
        path = self.folder / 'existing.lnk'
        self.make_link(path, self.folder / 'other.exe')
        before = path.read_bytes()
        with self.assertRaises(LauncherError):
            shortcut(path, self.root, check_only=True)
        self.assertEqual(path.read_bytes(), before)
        self.make_link(path, self.root / 'CGLBootstrap.exe')
        with self.assertRaises(LauncherError):
            shortcut(path, self.root, check_only=True)
        shortcut(path, self.root)
        shortcut(path, self.root, check_only=True)
