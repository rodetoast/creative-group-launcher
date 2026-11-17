"""Path budget for the launcher's ordinary Win32 filesystem operations."""
from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath

from .common import LauncherError


class WindowsPathError(LauncherError):
    pass


def utf16_length(value: str) -> int:
    return len(value.encode("utf-16-le", errors="surrogatepass")) // 2


class WindowsPathBudget:
    # Use the compatible Win32 budget across extraction, recovery and shell access.
    # The registry alone does not opt every process/API into extended paths.
    file_limit = 259  # MAX_PATH includes the terminator.
    directory_limit = 248  # CreateDirectory reserves room for an 8.3 name.

    def __init__(self, component_limit: int = 255):
        self.component_limit = component_limit

    def check(self, path: Path, phase: str, *, directory: bool = False):
        path = PureWindowsPath(path)
        length = utf16_length(str(path))
        component = max((utf16_length(part) for part in path.parts[1:]), default=0)
        if not path.is_absolute() or path.drive.startswith(("\\\\?\\", "\\\\.\\")):
            reason = "일반 드라이브 또는 UNC 절대 경로가 필요합니다."
        elif component > self.component_limit:
            reason = f"이름 한 부분 {component}단위, 파일 시스템 한도 {self.component_limit}"
        elif length > (limit := self.directory_limit if directory else self.file_limit):
            reason = f"경로 {length}단위, 한도 {limit}"
        elif not directory and (parent_length := utf16_length(str(path.parent))) > self.directory_limit:
            reason = f"상위 폴더 경로 {parent_length}단위, 한도 {self.directory_limit}"
        else:
            return
        # A leaf identifies the failing file without printing the profile path.
        label = path.name if path.name else "설치 위치"
        raise WindowsPathError(
            f"설치 경로가 너무 길거나 지원되지 않아 작업을 중단했습니다. "
            f"{phase} · {label} · {reason}\n"
            "설치 위치와 프로그램 파일 경로를 확인해 주세요."
        )


def windows_path_budget(root: Path) -> WindowsPathBudget | None:
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    get_volume = kernel.GetVolumePathNameW
    get_volume.argtypes = (wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD)
    get_volume.restype = wintypes.BOOL
    get_info = kernel.GetVolumeInformationW
    get_info.argtypes = (wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
                         wintypes.LPDWORD, wintypes.LPDWORD, wintypes.LPDWORD,
                         wintypes.LPWSTR, wintypes.DWORD)
    get_info.restype = wintypes.BOOL
    # The install root may not exist yet. Use the nearest existing ancestor,
    # including when the root is inside a mounted volume or a UNC share.
    ancestor = root
    while ancestor != ancestor.parent and not ancestor.is_dir():
        ancestor = ancestor.parent
    volume = ctypes.create_unicode_buffer(32768)
    component = wintypes.DWORD()
    if (get_volume(str(ancestor), volume, len(volume))
            and get_info(volume.value, None, 0, None, ctypes.byref(component), None, None, 0)
            and component.value):
        return WindowsPathBudget(component.value)
    return WindowsPathBudget()
