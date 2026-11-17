from __future__ import annotations

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from southpaw_tools import common
from southpaw_tools.common import LauncherError, atomic_json, read_json
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from tests.support import FakeProcesses, LocalProvider, package, temporary


@unittest.skipUnless(os.name == "nt", "Windows file sharing semantics")
class JournalSharingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary("southpaw-journal-sharing-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_held_read_handle_rejects_replace_without_changing_old_json(self):
        target = self.root / "journal.json"
        atomic_json(target, {"phase": "downloading"})
        with target.open("rb"):
            with self.assertRaises(PermissionError) as error:
                atomic_json(target, {"phase": "download_verified"})
            self.assertEqual(error.exception.winerror, 5)
            self.assertEqual(read_json(target), {"phase": "downloading"})
        self.assertFalse(list(self.root.glob(".pending-*.json")))
        atomic_json(target, {"phase": "retry_after_close"})
        self.assertEqual(read_json(target), {"phase": "retry_after_close"})

    def test_real_winerror5_during_journal_replace_preserves_active_and_retry(self):
        engine = Installer(AppPaths(self.root / "client"), FakeProcesses())
        source1, app1 = package(self.root / "packages")
        source2, app2 = package(self.root / "packages", "r2")
        engine.install(app1, LocalProvider(source1))
        _, cwd = engine.resolve_launch(app1)
        (cwd / "settings.json").write_text("user settings")
        pointer = (engine.paths.app("dummy") / "active.json").read_bytes()
        replace = os.replace
        observed = []
        def blocked(source, target):
            path = Path(target)
            if (not observed and path.parent.name == "transactions" and path.exists()
                    and json.loads(Path(source).read_text(encoding="utf-8")).get("phase") == "download_verified"):
                # This exact test-owned handle intentionally excludes SHARE_DELETE.
                with path.open("rb"):
                    try:
                        return replace(source, target)
                    except OSError as exc:
                        observed.append(exc.winerror)
                        self.assertEqual(read_json(path)["phase"], "downloading")
                        raise
            return replace(source, target)
        with patch.object(common.os, "replace", blocked):
            with self.assertRaises(LauncherError):
                engine.install(app2, LocalProvider(source2))
        self.assertEqual(observed, [5])
        self.assertEqual((engine.paths.app("dummy") / "active.json").read_bytes(), pointer)
        self.assertEqual((cwd / "settings.json").read_text(), "user settings")
        engine.resolve_launch(app1)
        self.assertFalse(list(engine.paths.app("dummy").rglob(".pending-*.json")))
        self.assertFalse(engine.paths.release("dummy", "r2").exists())
        Installer(engine.paths, FakeProcesses()).install(app2, LocalProvider(source2))
        self.assertEqual(engine.installed("dummy"), app2)

    def test_persistent_lock_preserves_journal_then_recovers_after_release(self):
        engine = Installer(AppPaths(self.root / "client"), FakeProcesses())
        source1, app1 = package(self.root / "packages")
        source2, app2 = package(self.root / "packages", "r2")
        engine.install(app1, LocalProvider(source1))
        replace = os.replace
        held = []
        def blocked(source, target):
            path = Path(target)
            if path.parent.name == "transactions" and path.exists() and not held:
                held.append(path.open("rb"))
            return replace(source, target)
        try:
            with patch.object(common.os, "replace", blocked):
                with self.assertRaisesRegex(LauncherError, "복구 필요"):
                    engine.install(app2, LocalProvider(source2))
            self.assertEqual(engine.installed("dummy"), app1)
            engine.resolve_launch(app1)
            journals = list(engine.paths.app("dummy").glob("transactions/*.json"))
            self.assertEqual(len(journals), 1)
            self.assertEqual(read_json(journals[0])["phase"], "downloading")
            self.assertTrue(engine.pending_recovery("dummy"))
        finally:
            for stream in held:
                stream.close()
        restarted = Installer(engine.paths, FakeProcesses())
        self.assertEqual(restarted.recover("dummy"), app1)
        restarted.install(app2, LocalProvider(source2))
        self.assertEqual(restarted.installed("dummy"), app2)


if __name__ == "__main__":
    unittest.main()
