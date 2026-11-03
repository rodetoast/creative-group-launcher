from __future__ import annotations

import threading
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from southpaw_tools.common import LauncherError, app_lock, atomic_json, digest, read_json
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from tests.support import FakeProcesses, LocalProvider, package, temporary


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary("southpaw-recovery-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = AppPaths(self.root / "client")
        self.processes = FakeProcesses()
        self.engine = Installer(self.paths, self.processes)
        self.source, self.app = package(self.root / "packages")
        self.source2, self.app2 = package(self.root / "packages", "r2")
        self.engine.install(self.app, LocalProvider(self.source))
        self.exe, self.cwd = self.engine.resolve_launch(self.app)
        (self.cwd / "settings.json").write_text("important settings")
        (self.cwd / "user-projects").mkdir()
        (self.cwd / "user-projects/work.json").write_text("important work")
        (self.cwd / "unknown.log").write_text("user log")
        self.unlink = Path.unlink
        self.rename = Path.rename

    def restart(self):
        return Installer(self.paths, self.processes)

    def assert_old(self):
        self.assertEqual(self.engine.installed("dummy"), self.app)
        self.engine.resolve_launch(self.app)
        self.assertEqual((self.cwd / "settings.json").read_text(), "important settings")
        self.assertEqual((self.cwd / "user-projects/work.json").read_text(), "important work")
        self.assertEqual((self.cwd / "unknown.log").read_text(), "user log")

    def test_uninstall_delete_failure_restores_exe_and_allows_retry(self):
        def fail(path, *a, **kw):
            if path == self.cwd / "asset.json":
                raise PermissionError("locked asset")
            return self.unlink(path, *a, **kw)
        with patch.object(Path, "unlink", fail):
            with self.assertRaisesRegex(LauncherError, "제거 실패.*복원 완료"):
                self.engine.uninstall("dummy")
        self.assert_old()
        self.engine.uninstall("dummy")
        self.assertIsNone(self.engine.installed("dummy"))
        self.assertTrue((self.cwd / "unknown.log").exists())

    def test_uninstall_backup_failure_never_deletes_originals(self):
        with patch("southpaw_tools.installer.shutil.copy2", side_effect=PermissionError("backup denied")):
            with self.assertRaises(LauncherError):
                self.engine.uninstall("dummy")
        self.assert_old()

    def test_uninstall_restore_rename_failure_is_recoverable_next_request(self):
        def fail_delete(path, *a, **kw):
            if path == self.cwd / "asset.json":
                raise PermissionError("locked")
            return self.unlink(path, *a, **kw)
        with patch.object(Path, "unlink", fail_delete), patch.object(Path, "rename", side_effect=PermissionError("restore denied")):
            with self.assertRaisesRegex(LauncherError, "복구 필요"):
                self.engine.uninstall("dummy")
        self.assertFalse(self.exe.exists())
        restarted = self.restart()
        restarted.launch("dummy")
        self.assert_old()
        self.assertEqual(len(self.processes.calls), 1)

    def test_uninstall_crash_after_first_deletion_restores_before_launch(self):
        def crash(path, *a, **kw):
            result = self.unlink(path, *a, **kw)
            if path == self.exe:
                raise SystemExit("crash after delete")
            return result
        with patch.object(Path, "unlink", crash):
            with self.assertRaises(SystemExit):
                self.engine.uninstall("dummy")
        self.assertFalse(self.exe.exists())
        self.restart().launch("dummy")
        self.assert_old()

    def test_uninstall_pointer_delete_failure_restores_payload(self):
        pointer = self.paths.app("dummy") / "active.json"
        def fail(path, *a, **kw):
            if path == pointer:
                raise PermissionError("pointer locked")
            return self.unlink(path, *a, **kw)
        with patch.object(Path, "unlink", fail):
            with self.assertRaises(LauncherError):
                self.engine.uninstall("dummy")
        self.assert_old()

    def test_uninstall_crash_after_pointer_delete_restores_pointer_and_payload(self):
        pointer = self.paths.app("dummy") / "active.json"
        def crash(path, *a, **kw):
            result = self.unlink(path, *a, **kw)
            if path == pointer:
                raise SystemExit("crash before removal commit record")
            return result
        with patch.object(Path, "unlink", crash):
            with self.assertRaises(SystemExit):
                self.engine.uninstall("dummy")
        self.assertFalse(pointer.exists())
        self.restart().launch("dummy")
        self.assert_old()

    def test_missing_exe_same_release_repair_preserves_unknown_work(self):
        self.exe.unlink()
        with self.assertRaises(LauncherError):
            self.engine.launch("dummy")
        self.engine.install(self.app, LocalProvider(self.source))
        self.assertEqual(self.engine.installed("dummy"), self.app)
        self.engine.resolve_launch(self.app)
        self.assertEqual((self.cwd / "settings.json").read_text(), "important settings")
        self.assertEqual((self.cwd / "user-projects/work.json").read_text(), "important work")
        backups = list(self.paths.app("dummy").glob("recovery/*/previous-release/payload/unknown.log"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "user log")
        # Unknown work stays in the retained old payload, never silently merged.
        self.assertFalse((self.cwd / "unknown.log").exists())

    def test_repair_rejects_same_id_changed_package_hash(self):
        self.exe.unlink()
        with self.assertRaises(LauncherError):
            self.engine.install(replace(self.app, sha256="f" * 64), LocalProvider(self.source))
        self.assertTrue((self.cwd / "unknown.log").exists())

    def test_activation_interruption_retry_keeps_old_and_preserves_orphan(self):
        with patch.object(self.engine, "_activate", side_effect=SystemExit("before activation")):
            with self.assertRaises(SystemExit):
                self.engine.install(self.app2, LocalProvider(self.source2))
        self.assert_old()
        self.restart().install(self.app2, LocalProvider(self.source2))
        self.assertEqual(self.engine.installed("dummy"), self.app2)
        self.assertTrue(list(self.paths.app("dummy").glob("recovery/*/aborted-release/receipt.json")))

    def test_partial_download_interruption_retry_is_clean(self):
        class Interrupted:
            def download(_, app, target, progress, cancel):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"partial")
                raise SystemExit("interrupted download")
        with self.assertRaises(SystemExit):
            self.engine.install(self.app2, Interrupted())
        self.assert_old()
        self.restart().install(self.app2, LocalProvider(self.source2))
        self.assertFalse(list(self.paths.downloads.glob("*.zip")))

    def test_rename_failure_keeps_old_and_allows_retry(self):
        target = self.paths.release("dummy", "r2")
        def fail(path, destination):
            if Path(destination) == target:
                raise PermissionError("rename denied")
            return self.rename(path, destination)
        with patch.object(Path, "rename", fail):
            with self.assertRaises(LauncherError):
                self.engine.install(self.app2, LocalProvider(self.source2))
        self.assert_old()
        self.restart().install(self.app2, LocalProvider(self.source2))

    def test_activation_writes_then_raises_is_verified_success(self):
        activate = self.engine._activate
        def after_commit(app):
            activate(app)
            raise OSError("error after atomic replace")
        with patch.object(self.engine, "_activate", after_commit):
            result = self.engine.install(self.app2, LocalProvider(self.source2))
        self.assertEqual(result, self.app2)
        self.assertEqual(self.engine.installed("dummy"), self.app2)
        self.assertTrue(self.engine.warnings)

    def test_activation_new_payload_missing_restores_old_not_false_success(self):
        activate = self.engine._activate
        def invalid_commit(app):
            activate(app)
            self.engine.resolve_launch(app)[0].unlink()
            raise OSError("new EXE vanished")
        with patch.object(self.engine, "_activate", invalid_commit):
            with self.assertRaises(LauncherError):
                self.engine.install(self.app2, LocalProvider(self.source2))
        self.assert_old()

    def test_malformed_partial_pointer_restores_previous_valid_pointer(self):
        pointer = self.paths.app("dummy") / "active.json"
        def broken(app):
            pointer.write_text("broken pointer")
            raise OSError("pointer failure")
        with patch.object(self.engine, "_activate", broken):
            with self.assertRaises(LauncherError):
                self.engine.install(self.app2, LocalProvider(self.source2))
        self.assert_old()

    def test_cleanup_denial_is_warning_and_next_update_still_works(self):
        def fail(path, *a, **kw):
            if path.parent == self.paths.downloads:
                raise PermissionError("cleanup denied")
            return self.unlink(path, *a, **kw)
        with patch.object(Path, "unlink", fail):
            self.assertEqual(self.engine.install(self.app2, LocalProvider(self.source2)), self.app2)
        self.assertTrue(self.engine.warnings)
        self.assertTrue((self.paths.app("dummy") / "recovery-warnings.log").exists())
        source3, app3 = package(self.root / "packages", "r3")
        self.restart().install(app3, LocalProvider(source3))
        self.assertFalse(list(self.paths.downloads.glob("*.zip")))
        self.assertEqual(self.engine.installed("dummy"), app3)

    def test_unexpected_orphan_user_file_is_preserved(self):
        with patch.object(self.engine, "_activate", side_effect=SystemExit("crash")):
            with self.assertRaises(SystemExit):
                self.engine.install(self.app2, LocalProvider(self.source2))
        orphan = self.paths.release("dummy", "r2") / "user-added.txt"
        orphan.write_text("do not delete")
        self.restart().install(self.app2, LocalProvider(self.source2))
        saved = list(self.paths.app("dummy").glob("recovery/*/aborted-release/user-added.txt"))
        self.assertEqual(saved[0].read_text(), "do not delete")

    def test_interrupted_repair_restores_previous_folder_then_retries(self):
        self.exe.unlink()
        rename = self.rename
        def crash(path, destination):
            result = rename(path, destination)
            if Path(destination).name == "previous-release":
                raise SystemExit("interrupted repair rename")
            return result
        with patch.object(Path, "rename", crash):
            with self.assertRaises(SystemExit):
                self.engine.install(self.app, LocalProvider(self.source))
        self.restart().install(self.app, LocalProvider(self.source))
        self.engine.resolve_launch(self.app)

    def test_active_conflict_is_recovery_required_without_overwrite(self):
        with patch.object(self.engine, "_activate", side_effect=SystemExit("crash")):
            with self.assertRaises(SystemExit):
                self.engine.install(self.app2, LocalProvider(self.source2))
        other = replace(self.app, release_id="external-change")
        self.engine._activate(other)
        with self.assertRaises(LauncherError):
            self.restart().install(self.app2, LocalProvider(self.source2))
        self.assertEqual(self.engine.installed("dummy"), other)
        self.assertTrue(self.exe.exists())

    def test_all_management_requests_obey_same_app_lock(self):
        with app_lock(self.paths.lock("dummy")):
            for action in (lambda: self.restart().install(self.app2, LocalProvider(self.source2)),
                           lambda: self.restart().uninstall("dummy"),
                           lambda: self.restart().launch("dummy")):
                with self.assertRaises(LauncherError):
                    action()
        self.assert_old()

    def test_real_thread_concurrent_uninstall_update_is_blocked(self):
        entered, release = threading.Event(), threading.Event()
        errors = []
        class Paused(LocalProvider):
            def download(self, *args, **kwargs):
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("test timeout")
                return super().download(*args, **kwargs)
        def run():
            try:
                self.engine.install(self.app2, Paused(self.source2))
            except Exception as exc:
                errors.append(exc)
        worker = threading.Thread(target=run)
        worker.start()
        try:
            self.assertTrue(entered.wait(5))
            with self.assertRaises(LauncherError):
                self.restart().uninstall("dummy")
            with self.assertRaises(LauncherError):
                self.restart().install(self.app2, LocalProvider(self.source2))
        finally:
            release.set()
            worker.join(8)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(self.engine.installed("dummy"), self.app2)

    def test_each_precommit_phase_interruption_is_retryable(self):
        for phase in ("download_verified", "preparing", "ready", "switching", "activating"):
            with self.subTest(phase=phase):
                engine = Installer(AppPaths(self.root / phase), FakeProcesses())
                engine.install(self.app, LocalProvider(self.source))
                save = engine._phase
                def crash(journal, next_phase):
                    save(journal, next_phase)
                    if next_phase == phase:
                        raise SystemExit(phase)
                with patch.object(engine, "_phase", crash):
                    with self.assertRaises(SystemExit):
                        engine.install(self.app2, LocalProvider(self.source2))
                self.assertEqual(engine.installed("dummy"), self.app)
                restarted = Installer(engine.paths, FakeProcesses())
                restarted.install(self.app2, LocalProvider(self.source2))
                self.assertEqual(restarted.installed("dummy"), self.app2)

    def test_actual_child_abrupt_exit_before_and_after_activation(self):
        import subprocess
        import sys
        code = """
import os,sys
from pathlib import Path
from southpaw_tools.catalog import AppRelease
from southpaw_tools.common import read_json
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
from tests.support import FakeProcesses,LocalProvider
engine=Installer(AppPaths(Path(sys.argv[1])),FakeProcesses())
app=AppRelease.parse(read_json(Path(sys.argv[2])))
activate=engine._activate
def crash(app):
    if sys.argv[4]=='after': activate(app)
    os._exit(73)
engine._activate=crash
engine.install(app,LocalProvider(Path(sys.argv[3])))
"""
        for timing in ("before", "after"):
            with self.subTest(timing=timing):
                engine = Installer(AppPaths(self.root / ("child-" + timing)), FakeProcesses())
                engine.install(self.app, LocalProvider(self.source))
                metadata = self.root / "child-app.json"
                atomic_json(metadata, self.app2.to_dict())
                child = subprocess.run([sys.executable, "-B", "-c", code, str(engine.paths.root),
                                        str(metadata), str(self.source2), timing], timeout=15)
                self.assertEqual(child.returncode, 73)
                restarted = Installer(engine.paths, FakeProcesses())
                if timing == "before":
                    self.assertEqual(restarted.installed("dummy"), self.app)
                    restarted.install(self.app2, LocalProvider(self.source2))
                else:
                    self.assertEqual(restarted.recover("dummy"), self.app2)
                restarted.resolve_launch(self.app2)
                self.assertFalse(restarted.pending_recovery("dummy"))

    def test_second_process_cannot_acquire_app_lock(self):
        import subprocess
        import sys
        code = """
import sys
from pathlib import Path
from southpaw_tools.common import app_lock,LauncherError
try:
    with app_lock(Path(sys.argv[1])): pass
except LauncherError: sys.exit(19)
sys.exit(0)
"""
        with app_lock(self.paths.lock("dummy")):
            child = subprocess.run([sys.executable, "-B", "-c", code,
                                    str(self.paths.lock("dummy"))], timeout=10)
        self.assertEqual(child.returncode, 19)

    def test_corrupt_recovery_record_is_not_used_as_a_deletion_recipe(self):
        tx = self.paths.app("dummy") / "transactions" / ("a" * 32 + ".json")
        atomic_json(tx, {"schema_version": 1, "id": "../escape", "app": self.app.to_dict()})
        with self.assertRaises(LauncherError):
            self.restart().recover("dummy")
        self.assertTrue(tx.exists())
        self.assert_old()

    def test_uninstall_recovery_does_not_overwrite_user_edit(self):
        def crash(path, *a, **kw):
            result = self.unlink(path, *a, **kw)
            if path == self.exe:
                raise SystemExit("crash")
            return result
        with patch.object(Path, "unlink", crash):
            with self.assertRaises(SystemExit):
                self.engine.uninstall("dummy")
        self.exe.write_bytes(b"user replacement, do not overwrite")
        with self.assertRaises(LauncherError):
            self.restart().recover("dummy")
        self.assertEqual(self.exe.read_bytes(), b"user replacement, do not overwrite")
        self.assertTrue(self.engine.pending_recovery("dummy"))

    def test_verified_activation_survives_completion_record_write_failure(self):
        phase = self.engine._phase
        def fail(journal, next_phase):
            if next_phase == "activated":
                raise PermissionError("completion journal denied")
            return phase(journal, next_phase)
        with patch.object(self.engine, "_phase", fail):
            self.assertEqual(self.engine.install(self.app2, LocalProvider(self.source2)), self.app2)
        self.engine.resolve_launch(self.app2)
        self.assertTrue(self.engine.warnings)

    def test_unwritable_warning_log_does_not_hide_committed_result(self):
        from southpaw_tools.common import inside
        def checked(root, relative, **kwargs):
            if relative == "recovery-warnings.log":
                raise LauncherError("unsafe log path")
            return inside(root, relative, **kwargs)
        def fail_cleanup(path, *a, **kw):
            if path.parent == self.paths.downloads:
                raise PermissionError("cleanup denied")
            return self.unlink(path, *a, **kw)
        with patch("southpaw_tools.installer.inside", checked), patch.object(Path, "unlink", fail_cleanup):
            self.assertEqual(self.engine.install(self.app2, LocalProvider(self.source2)), self.app2)
        self.assertTrue(self.engine.warnings)
        self.engine.resolve_launch(self.app2)


if __name__ == "__main__":
    unittest.main()
