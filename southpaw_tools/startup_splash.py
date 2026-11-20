"""Small Windows startup window, independent of Qt and the update protocol."""
from contextlib import nullcontext
import json
import sys
from threading import Event, Thread

from .branding import DISPLAY_NAME


def wants_session_splash(path):
    """Read a small presentation hint without importing the update engine."""
    if path.name != "context.json" or path.parent.parent.name != "sessions":
        return False
    try:
        with path.open("rb") as stream:
            raw = stream.read(16385)
        if len(raw) > 16384:
            return False
        info = json.loads(raw)
    except (OSError, ValueError, RecursionError):
        return False
    return (isinstance(info, dict) and info.get("managed") is True
            and info.get("mode") == "normal" and not info.get("startup_splash"))


class StartupSplash:
    def __init__(self):
        self._stop = Event()
        self._shown = Event()
        self._thread = None
        self._window = None

    def __enter__(self):
        self.show()
        return self

    def __exit__(self, *_):
        self.close()

    def show(self):
        if sys.platform != "win32" or self._thread:
            return
        self._stop.clear()
        self._shown.clear()
        self._thread = Thread(target=self._paint, name="Windows startup splash", daemon=True)
        self._thread.start()
        self._shown.wait(0.15)

    def close(self):
        if self._thread:
            self._stop.set()
            self._thread.join(1)
            if not self._thread.is_alive():
                self._thread = None

    def keep_above(self, main_window):
        """Put the launcher below the splash without joining their input queues."""
        splash_window = self._window
        if not splash_window:
            return
        import ctypes
        from ctypes import wintypes as w

        user = ctypes.WinDLL("user32")
        position = user.SetWindowPos
        position.argtypes = [w.HWND, w.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.UINT]
        # NOSIZE | NOMOVE | NOACTIVATE | NOOWNERZORDER. Reorder only the main window.
        position(main_window, splash_window, 0, 0, 0, 0, 0x0213)

    def _paint(self):
        import ctypes
        from ctypes import wintypes as w

        user = ctypes.WinDLL("user32")
        gdi = ctypes.WinDLL("gdi32")
        create = user.CreateWindowExW
        create.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_int, ctypes.c_int,
                           ctypes.c_int, ctypes.c_int, w.HWND, w.HMENU, w.HINSTANCE, ctypes.c_void_p]
        create.restype = w.HWND
        for function in (user.DestroyWindow, user.UpdateWindow):
            function.argtypes = [w.HWND]
        user.ShowWindow.argtypes = [w.HWND, ctypes.c_int]
        user.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        user.SendMessageW.restype = w.LPARAM
        gdi.GetStockObject.restype = w.HANDLE
        width, height = 340, 116
        work = w.RECT()
        if not user.SystemParametersInfoW(0x30, 0, ctypes.byref(work), 0):  # SPI_GETWORKAREA
            work.right, work.bottom = user.GetSystemMetrics(0), user.GetSystemMetrics(1)
        x = work.left + (work.right - work.left - width) // 2
        y = work.top + (work.bottom - work.top - height) // 2
        # WS_EX_NOACTIVATE | TOOLWINDOW, popup border. No topmost flag.
        window = create(0x08000080, "Static", DISPLAY_NAME, 0x80800000, x, y, width, height,
                        None, None, None, None)
        if not window:
            self._shown.set()
            return
        try:
            font = gdi.GetStockObject(17)  # DEFAULT_GUI_FONT
            for text, top in ((DISPLAY_NAME, 27), ("프로그램을 준비하고 있습니다…", 62)):
                child = create(0, "Static", text, 0x50000001, 12, top, width - 26, 24,
                               window, None, None, None)
                if child and font:
                    user.SendMessageW(child, 0x30, font, 1)  # WM_SETFONT
            if not self._stop.is_set():
                user.ShowWindow(window, 4)  # SW_SHOWNOACTIVATE
                user.UpdateWindow(window)
                self._window = window
            self._shown.set()
            msg = w.MSG()
            while not self._stop.wait(0.02):
                while user.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    user.TranslateMessage(ctypes.byref(msg))
                    user.DispatchMessageW(ctypes.byref(msg))
        finally:
            self._window = None
            user.DestroyWindow(window)


def frozen_bootstrap(project):
    # The worker and developer fixtures must not create an additional window.
    show = (sys.platform == "win32" and "worker" not in sys.argv[1:]
            and not {"--help", "-h"}.intersection(sys.argv[1:]))
    while True:
        with (StartupSplash() if show else nullcontext()) as splash:
            from . import self_update
            from .bootstrap import main
            self_update.PROJECT = project
            result = main(splash=splash)
        if result != 3:
            return result
