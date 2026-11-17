"""Windows shortcut and taskbar identity for the stable Bootstrap entry point."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import uuid

from .common import LauncherError
from .branding import DISPLAY_NAME

APP_ID = "SouthpawGames.ToolsLauncher"
_window_icon = None


class GUID(ctypes.Structure):
    _fields_ = [("bytes", ctypes.c_ubyte * 16)]

    @classmethod
    def parse(cls, value):
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


class PropertyKey(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", wintypes.DWORD)]


class Variant(ctypes.Structure):
    _fields_ = [("vt", wintypes.WORD), ("reserved", wintypes.WORD * 3),
                ("value", ctypes.c_void_p), ("padding", ctypes.c_void_p)]


def _check(result):
    if result < 0:
        raise LauncherError(f"Windows 바로가기 속성 처리 실패: HRESULT 0x{result & 0xffffffff:08x}")


def _method(pointer, index, *arguments):
    table = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *arguments)(table[index])


def _properties(path=None, window=None):
    shell = ctypes.WinDLL("shell32")
    iid = GUID.parse("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99")
    pointer = ctypes.c_void_p()
    if path is not None:
        fn = shell.SHGetPropertyStoreFromParsingName
        fn.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, wintypes.DWORD,
                       ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        fn.restype = ctypes.c_long
        _check(fn(str(path), None, 2, ctypes.byref(iid), ctypes.byref(pointer)))
    else:
        fn = shell.SHGetPropertyStoreForWindow
        fn.argtypes = [wintypes.HWND, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        fn.restype = ctypes.c_long
        _check(fn(window, ctypes.byref(iid), ctypes.byref(pointer)))
    return pointer


def _set(pointer, values):
    fmtid = GUID.parse("9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3")
    try:
        for pid, text in values.items():
            buffer = ctypes.create_unicode_buffer(text)
            key = PropertyKey(fmtid, pid)
            value = Variant()
            value.vt = 31  # VT_LPWSTR. The property store copies the string.
            value.value = ctypes.cast(buffer, ctypes.c_void_p)
            _check(_method(pointer, 6, ctypes.POINTER(PropertyKey), ctypes.POINTER(Variant))(
                pointer, ctypes.byref(key), ctypes.byref(value)))
        _check(_method(pointer, 7)(pointer))
    finally:
        _method(pointer, 2)(pointer)


def shortcut_identity(path):
    ole = ctypes.OleDLL("ole32")
    result = ole.CoInitializeEx(None, 2)
    _check(result)
    try:
        _set(_properties(path=path), {5: APP_ID})
    finally:
        ole.CoUninitialize()


def shortcut_app_id(path):
    ole = ctypes.OleDLL("ole32")
    _check(ole.CoInitializeEx(None, 2))
    pointer = None
    value = Variant()
    try:
        pointer = _properties(path=path)
        key = PropertyKey(GUID.parse("9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3"), 5)
        _check(_method(pointer, 5, ctypes.POINTER(PropertyKey), ctypes.POINTER(Variant))(
            pointer, ctypes.byref(key), ctypes.byref(value)))
        return ctypes.wstring_at(value.value) if value.vt == 31 else None
    finally:
        ole.PropVariantClear(ctypes.byref(value))
        if pointer:
            _method(pointer, 2)(pointer)
        ole.CoUninitialize()


def configure_launcher_window(pid, bootstrap, data_root):
    """Apply identity to this session's actual GUI, retaining a stable relaunch path."""
    bootstrap = Path(bootstrap).resolve()
    marker = bootstrap.parent / "setup-shell.json"
    if not marker.is_file():
        return
    from .common import read_json
    if read_json(marker) != {"schema_version": 1, "app_id": APP_ID}:
        raise LauncherError("설치 프로그램의 작업표시줄 표식이 다릅니다.")
    user = ctypes.WinDLL("user32", use_last_error=True)
    global _window_icon
    if _window_icon is None:
        user.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                                   ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user.LoadImageW.restype = wintypes.HANDLE
        _window_icon = user.LoadImageW(None, str(bootstrap.parent / "launcher.ico"), 1, 0, 0, 0x10)
        if not _window_icon:
            raise ctypes.WinError(ctypes.get_last_error())
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    windows = []
    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback
    def collect(hwnd, unused):
        actual = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(actual))
        if actual.value == pid and user.IsWindowVisible(hwnd):
            windows.append(hwnd)
        return True

    user.EnumWindows.argtypes = [callback, wintypes.LPARAM]
    if not user.EnumWindows(collect, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    if not windows:
        raise LauncherError("런처의 작업표시줄 창을 확인할 수 없습니다.")
    ole = ctypes.OleDLL("ole32")
    result = ole.CoInitializeEx(None, 2)
    _check(result)
    try:
        command = subprocess.list2cmdline([str(bootstrap), "--data-dir", str(data_root)])
        for hwnd in windows:
            _set(_properties(window=hwnd), {5: APP_ID, 2: command,
                3: str(bootstrap.parent / "launcher.ico") + ",0", 4: DISPLAY_NAME})
            user.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user.SendMessageW.restype = wintypes.LPARAM
            user.SendMessageW(hwnd, 0x80, 0, _window_icon)
            user.SendMessageW(hwnd, 0x80, 1, _window_icon)
    finally:
        ole.CoUninitialize()
