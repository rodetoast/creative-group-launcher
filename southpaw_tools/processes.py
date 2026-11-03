from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .common import LauncherError


class Processes:
    def __init__(self):
        self.children: list[tuple[Path, subprocess.Popen]] = []

    def start(self, executable: Path, cwd: Path):
        try:
            process = subprocess.Popen([str(executable)], cwd=str(cwd), shell=False)
        except OSError as exc:
            raise LauncherError(f"프로그램 실행 실패: {exc}") from exc
        self.children.append((executable.resolve(), process))
        return process

    def is_running(self, root: Path) -> bool:
        root = root.resolve()
        self.children = [(path, p) for path, p in self.children if p.poll() is None]
        if any(path.is_relative_to(root) for path, _ in self.children):
            return True
        if os.name != "nt":
            return False
        # Also detects apps launched outside this launcher, after a launcher restart,
        # and the parent/child processes of PyInstaller onefile applications.
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                    wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        pids = (wintypes.DWORD * 65536)()
        used = wintypes.DWORD()
        if not psapi.EnumProcesses(pids, ctypes.sizeof(pids), ctypes.byref(used)):
            raise LauncherError("실행 중 프로세스를 확인할 수 없어 변경을 보류합니다.")
        for pid in pids[:used.value // ctypes.sizeof(wintypes.DWORD)]:
            handle = kernel.OpenProcess(0x1000, False, pid)
            if not handle:
                continue
            try:
                name = ctypes.create_unicode_buffer(32768)
                size = wintypes.DWORD(len(name))
                if kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)):
                    if Path(name.value).resolve().is_relative_to(root):
                        return True
            finally:
                kernel.CloseHandle(handle)
        return False
