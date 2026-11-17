import os
import unittest
from dataclasses import replace
from pathlib import Path, PureWindowsPath

from southpaw_tools.common import digest
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from southpaw_tools.windows_paths import WindowsPathBudget, WindowsPathError
from tests.support import FakeProcesses, LocalProvider, package, temporary


class WindowsPathBudgetTests(unittest.TestCase):
    def test_utf16_volume_components_and_parent_directory(self):
        budget = WindowsPathBudget()
        prefix = PureWindowsPath("C:/") / ("a" * 235)
        budget.check(prefix / ("😀" * 10), "시험")
        with self.assertRaisesRegex(WindowsPathError, "261단위"):
            budget.check(prefix / ("😀" * 11), "시험")
        budget.check(PureWindowsPath("C:/") / ("a" * 245), "시험", directory=True)
        with self.assertRaisesRegex(WindowsPathError, "상위 폴더.*249단위"):
            budget.check(PureWindowsPath("C:/") / ("a" * 246) / "b", "시험")
        with self.assertRaisesRegex(WindowsPathError, "이름 한 부분 17단위"):
            WindowsPathBudget(16).check(PureWindowsPath("//server/share") / ("a" * 17), "시험")


@unittest.skipUnless(os.name == "nt", "Windows installation path budget")
class WindowsInstallPathTests(unittest.TestCase):
    def setUp(self):
        temp = temporary("path-budget-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.paths = AppPaths(self.root / "client")
        self.engine = Installer(self.paths, FakeProcesses())

    def member(self, release, length):
        backup = self.paths.app("dummy") / f"recovery/{'0' * 32}/files/releases/{release}/payload"
        count = length - len(str(backup)) - 1 - len(".txt")
        self.assertGreater(count, 0)
        return "x" * count + ".txt"

    def package(self, release, name):
        return package(self.root / "packages", release,
                       contents={"Dummy.exe": b"MZ fixture", "asset.json": b"{}", name: b"payload"})

    def snapshot(self):
        return {p.relative_to(self.paths.root).as_posix(): digest(p)
                for p in self.paths.root.rglob("*") if p.is_file()}

    def test_exact_boundary_installs_and_uninstalls(self):
        source, app = self.package("r1", self.member("r1", 259))
        self.engine.install(app, LocalProvider(source))
        self.assertEqual(self.engine.installed("dummy"), app)
        self.assertEqual(self.engine.uninstall("dummy")["removed_files"], 3)
        self.assertIsNone(self.engine.installed("dummy"))

    def test_future_release_backup_rejected_before_extract_and_preserves_install(self):
        source, app = self.package("r1", "short.txt")
        self.engine.install(app, LocalProvider(source))
        payload = self.paths.release("dummy", "r1") / "payload"
        (payload / "settings.json").write_text("settings", encoding="utf-8")
        (payload / "work.txt").write_text("work", encoding="utf-8")
        before = self.snapshot()
        long_id = "r2-" + "x" * 24
        source, app = self.package(long_id, self.member(long_id, 260))
        with self.assertRaisesRegex(WindowsPathError, "제거 전 복구 사본.*260단위") as error:
            self.engine.install(app, LocalProvider(source))
        self.assertNotIn(str(self.root), str(error.exception))
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.paths.release("dummy", long_id).exists())

    def test_migrated_data_path_checked_before_extraction(self):
        source, app = self.package("r1", "short.txt")
        self.engine.install(app, LocalProvider(source))
        projects = self.paths.release("dummy", "r1") / "payload/user-projects"
        projects.mkdir()
        # Existing file fits the old release. The recovery path of its future
        # migrated copy is longer than the Win32 budget.
        length = 245 - len(str(projects)) - 1 - len(".txt")
        self.assertGreater(length, 0)
        (projects / ("w" * length + ".txt")).write_text("work", encoding="utf-8")
        before = self.snapshot()
        source, new = self.package("r2", "short.txt")
        with self.assertRaisesRegex(WindowsPathError, "사용자 데이터"):
            self.engine.install(new, LocalProvider(source))
        self.assertEqual(self.snapshot(), before)

    def test_legacy_release_with_overlong_backup_is_left_intact(self):
        from unittest.mock import patch

        source, app = self.package("r1", self.member("r1", 260))
        # Emulate an install made before the guard existed.
        with patch("southpaw_tools.installer.windows_path_budget", return_value=None):
            self.engine.install(app, LocalProvider(source))
        before = self.snapshot()
        with self.assertRaisesRegex(WindowsPathError, "제거 전 복구 사본.*260단위"):
            self.engine.uninstall("dummy")
        self.assertEqual(self.snapshot(), before)
