from __future__ import annotations

import os
import subprocess
from pathlib import Path
from threading import Lock

from .common import LauncherError


class Processes:
    def __init__(self):
        self.children: list[tuple[Path, subprocess.Popen]] = []
        self._children_lock = Lock()

    def start(self, executable: Path, cwd: Path):
        env = os.environ.copy()
        # A frozen launcher and the tool may be different PyInstaller applications.
        # Do not inherit the launcher's unpack directory or bootloader parent state.
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        for key in tuple(env):
            if key.startswith("_PYI_") or key == "_MEIPASS2":
                del env[key]
        try:
            process = subprocess.Popen([str(executable)], cwd=str(cwd), shell=False, env=env,
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
        except OSError as exc:
            raise LauncherError(f"프로그램 실행 실패: {exc}") from exc
        with self._children_lock:
            self.children.append((executable.resolve(), process))
        return process

    def running_images(self):
        with self._children_lock:
            self.children = [(path, p) for path, p in self.children if p.poll() is None]
            images = {p.pid: path for path, p in self.children}
        if os.name != "nt":
            return images
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
        name = ctypes.create_unicode_buffer(32768)
        for pid in pids[:used.value // ctypes.sizeof(wintypes.DWORD)]:
            handle = kernel.OpenProcess(0x1000, False, pid)
            if not handle:
                continue
            try:
                size = wintypes.DWORD(len(name))
                if kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)):
                    images[pid] = Path(name.value).resolve()
            finally:
                kernel.CloseHandle(handle)
        return images

    def is_running(self, root: Path) -> bool:
        root = root.resolve()
        return any(path.is_relative_to(root) for path in self.running_images().values())

    def activate(self, root: Path) -> bool:
        if os.name != "nt":
            return False
        from .windows_shell import activate_window
        from .windows_process import identity

        root = root.resolve()
        for pid, path in self.running_images().items():
            if path.is_relative_to(root):
                try:
                    record = identity(pid)
                except OSError:
                    continue
                if record and Path(record["image"]).is_relative_to(root) and activate_window(record):
                    return True
        return False
