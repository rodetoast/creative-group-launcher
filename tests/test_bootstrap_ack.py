"""Actual Windows read sharing conflicts within the startup acknowledgement wait."""
import ctypes
from ctypes import wintypes
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

from southpaw_tools.bootstrap import Session
from southpaw_tools.common import LauncherError, atomic_json, read_json
from tests.support import temporary


@contextmanager
def deny_read(path):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateFileW(str(path), 0x80000000, 0, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        kernel.CloseHandle(handle)


@unittest.skipUnless(os.name == "nt", "Windows file sharing semantics")
class BootstrapAckTests(unittest.TestCase):
    def setUp(self):
        tmp = temporary("bootstrap-ack-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.session = Session.__new__(Session)
        self.session.folder = self.root
        self.session.timeout = 1
        self.session.context = {"session": "test", "nonce": "nonce", "release_id": "r1",
                                "version": "1.0.0", "exe_sha256": "a" * 64}
        self.session.created = {"image": "test-only"}
        self.session.process = Mock(pid=123)
        self.session.process.poll.return_value = None
        self.path = self.root / "ready.json"
        self.value = {**self.session.context, "pid": 123, "stage": "ready"}
        atomic_json(self.path, self.value)

    def test_existing_file_can_deny_read_and_be_accepted_only_after_handle_closes(self):
        before = self.path.read_bytes()
        held = deny_read(self.path)
        held.__enter__()
        self.addCleanup(held.__exit__, None, None, None)
        self.assertTrue(self.path.exists())
        with self.assertRaises(LauncherError) as raised:
            read_json(self.path)
        self.assertIsInstance(raised.exception.__cause__, PermissionError)

        def wait(timeout):
            held.__exit__(None, None, None)
            raise subprocess.TimeoutExpired("test-only", timeout)

        self.session.process.wait.side_effect = wait
        with patch("southpaw_tools.bootstrap.identity", return_value=self.session.created):
            self.session.wait_ack("ready")
        self.session.process.wait.assert_called_once()
        self.assertEqual(self.path.read_bytes(), before)

    def test_persistent_read_denial_reaches_original_deadline_and_fails(self):
        with deny_read(self.path), patch("southpaw_tools.bootstrap.time.monotonic", side_effect=[0, 1]):
            with self.assertRaisesRegex(LauncherError, "ready.json.*접근 거부") as raised:
                self.session.wait_ack("ready")
        self.assertIsInstance(raised.exception.__cause__.__cause__, PermissionError)
        self.session.process.wait.assert_not_called()
        self.assertEqual(read_json(self.path), self.value)

    def test_malformed_or_wrong_nonce_ack_is_not_polled_until_success(self):
        for content in (b"{", json.dumps({**self.value, "nonce": "wrong"}).encode()):
            with self.subTest(content=content):
                self.path.write_bytes(content)
                with self.assertRaises(LauncherError):
                    self.session.wait_ack("ready")
                self.session.process.wait.assert_not_called()

    def test_process_exit_or_identity_change_is_not_accepted(self):
        self.session.process.poll.return_value = 1
        with self.assertRaisesRegex(LauncherError, "종료"):
            self.session.wait_ack("ready")
        self.session.process.poll.return_value = None
        with patch("southpaw_tools.bootstrap.identity", return_value={"image": "other"}):
            with self.assertRaisesRegex(LauncherError, "신원"):
                self.session.wait_ack("ready")

    def test_confirmed_ack_and_publication_gap_use_the_same_deadline(self):
        target = self.root / "confirmed.json"
        value = {**self.value, "stage": "confirmed"}

        def wait(timeout):
            atomic_json(target, value)
            raise subprocess.TimeoutExpired("test-only", timeout)

        self.session.process.wait.side_effect = wait
        with patch("southpaw_tools.bootstrap.identity", return_value=self.session.created):
            self.session.wait_ack("confirmed")
        self.session.process.wait.assert_called_once()
