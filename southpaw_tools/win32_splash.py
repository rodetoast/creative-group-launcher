"""DPI-aware GDI startup card. The caller owns its independent message thread."""
import ctypes as c
from ctypes import wintypes as w
import math
from pathlib import Path
from time import monotonic

from .branding import DISPLAY_NAME, ICON_FILENAME

CLASS_NAME = "SouthpawLauncherStartup"
WIDTH, HEIGHT = 396, 156
INSET, ICON_SIZE = 24, 40
TRACK_TOP, TRACK_HEIGHT, SWEEP_WIDTH = 124, 4, 78
WM_PAINT = 0x000F
WM_ERASEBKGND = 0x0014
WM_TIMER = 0x0113
WM_DPICHANGED = 0x02E0
WNDPROC = c.WINFUNCTYPE(w.LPARAM, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
user = c.WinDLL("user32")
gdi = c.WinDLL("gdi32")
kernel = c.WinDLL("kernel32")


def api(dll, name, result, *arguments):
    function = getattr(dll, name)
    function.argtypes = arguments
    function.restype = result
    return function


class WindowClass(c.Structure):
    _fields_ = [("style", w.UINT), ("proc", WNDPROC), ("class_extra", c.c_int),
                ("window_extra", c.c_int), ("instance", w.HINSTANCE), ("icon", w.HICON),
                ("cursor", w.HANDLE), ("background", w.HBRUSH), ("menu", w.LPCWSTR),
                ("name", w.LPCWSTR)]


class Paint(c.Structure):
    _fields_ = [("dc", w.HDC), ("erase", w.BOOL), ("dirty", w.RECT),
                ("restore", w.BOOL), ("update", w.BOOL), ("reserved", w.BYTE * 32)]


class Monitor(c.Structure):
    _fields_ = [("size", w.DWORD), ("bounds", w.RECT), ("work", w.RECT), ("flags", w.DWORD)]


def rgb(value):
    return int.from_bytes(bytes.fromhex(value), "little")


set_position = api(user, "SetWindowPos", w.BOOL, w.HWND, w.HWND, c.c_int, c.c_int,
                   c.c_int, c.c_int, w.UINT)
window_dpi = api(user, "GetDpiForWindow", w.UINT, w.HWND)
invalidate = api(user, "InvalidateRect", w.BOOL, w.HWND, c.POINTER(w.RECT), w.BOOL)
rect_of = api(user, "GetClientRect", w.BOOL, w.HWND, c.POINTER(w.RECT))
def_proc = api(user, "DefWindowProcW", w.LPARAM, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
select = api(gdi, "SelectObject", w.HANDLE, w.HDC, w.HANDLE)
delete = api(gdi, "DeleteObject", w.BOOL, w.HANDLE)
brush = api(gdi, "CreateSolidBrush", w.HBRUSH, w.COLORREF)
fill = api(user, "FillRect", c.c_int, w.HDC, c.POINTER(w.RECT), w.HBRUSH)
round_rect = api(gdi, "RoundRect", w.BOOL, w.HDC, c.c_int, c.c_int, c.c_int, c.c_int,
                 c.c_int, c.c_int)
draw_text = api(user, "DrawTextW", c.c_int, w.HDC, w.LPCWSTR, c.c_int, c.POINTER(w.RECT), w.UINT)
text_color = api(gdi, "SetTextColor", w.COLORREF, w.HDC, w.COLORREF)
background_mode = api(gdi, "SetBkMode", c.c_int, w.HDC, c.c_int)
font = api(gdi, "CreateFontW", w.HANDLE, *([c.c_int] * 5), *([w.DWORD] * 8), w.LPCWSTR)
load_image = api(user, "LoadImageW", w.HANDLE, w.HINSTANCE, w.LPCWSTR, w.UINT, c.c_int,
                 c.c_int, w.UINT)
draw_icon = api(user, "DrawIconEx", w.BOOL, w.HDC, c.c_int, c.c_int, w.HICON, c.c_int,
                c.c_int, w.UINT, w.HBRUSH, w.UINT)
destroy_icon = api(user, "DestroyIcon", w.BOOL, w.HICON)

# Dark QML palette. Keep the native startup renderer independent of Qt.
BG, TRACK, INK, MUTED, ACCENT = map(rgb, ("151822", "393e51", "f5f3ff", "b7b9cb", "c5b6ff"))


def place_below(main, splash):
    # NOSIZE | NOMOVE | NOACTIVATE | NOOWNERZORDER
    set_position(main, splash, 0, 0, 0, 0, 0x0213)


def parent_splash(pid):
    find = api(user, "FindWindowExW", w.HWND, w.HWND, w.HWND, w.LPCWSTR, w.LPCWSTR)
    owner = api(user, "GetWindowThreadProcessId", w.DWORD, w.HWND, c.POINTER(w.DWORD))
    visible = api(user, "IsWindowVisible", w.BOOL, w.HWND)
    found = None
    while found := find(None, found, CLASS_NAME, DISPLAY_NAME):
        actual = w.DWORD()
        owner(found, c.byref(actual))
        if actual.value == pid and visible(found):
            return found
    return None


class Card:
    def __init__(self):
        self.started = monotonic()
        self.dpi = 0
        self.glyphs = ()
        self.icon = None
        self.proc = WNDPROC(self.dispatch)
        self.brushes = {color: brush(color) for color in (BG, TRACK, ACCENT)}

    def close(self):
        for obj in (*self.glyphs, *self.brushes.values()):
            if obj:
                delete(obj)
        if self.icon:
            destroy_icon(self.icon)

    def scale(self, value):
        return round(value * self.dpi / 96)

    def update_dpi(self, hwnd):
        dpi = window_dpi(hwnd) or 96
        if self.dpi == dpi:
            return
        for obj in self.glyphs:
            delete(obj)
        if self.icon:
            destroy_icon(self.icon)
        self.dpi = dpi
        self.glyphs = tuple(font(-self.scale(size), 0, 0, 0, weight, 0, 0, 0, 1, 0, 0, 5, 0, face)
                            for size, weight, face in ((11, 700, "Segoe UI"), (21, 700, "Malgun Gothic"),
                                                       (14, 400, "Malgun Gothic")))
        asset = Path(__file__).with_name("assets") / ICON_FILENAME
        self.icon = load_image(None, str(asset), 1, self.scale(ICON_SIZE), self.scale(ICON_SIZE), 0x10)

    def render(self, hwnd, dc):
        self.update_dpi(hwnd)
        bounds = w.RECT()
        rect_of(hwnd, c.byref(bounds))
        s = self.scale
        fill(dc, c.byref(bounds), self.brushes[BG])
        if self.icon:
            draw_icon(dc, s(INSET), s(INSET), self.icon, s(ICON_SIZE), s(ICON_SIZE), 0, None, 3)
        background_mode(dc, 1)
        for text, x, top, height, color, glyph in (
                ("SOUTHPAW GAMES", 76, 20, 18, ACCENT, self.glyphs[0]),
                ("도구 런처", 76, 38, 30, INK, self.glyphs[1]),
                ("프로그램을 준비하고 있습니다", INSET, 88, 24, MUTED, self.glyphs[2])):
            old = select(dc, glyph)
            text_color(dc, color)
            area = w.RECT(s(x), s(top), bounds.right - s(INSET), s(top + height))
            draw_text(dc, text, -1, c.byref(area), 0x824)  # Single line, vertical center, no prefixes.
            select(dc, old)

        # An indeterminate sweep traverses the track and gently reverses.
        phase = (monotonic() - self.started) % 2.6 / 2.6
        position = (1 - math.cos(phase * math.tau)) / 2
        stock_object = api(gdi, "GetStockObject", w.HANDLE, c.c_int)
        old_pen = select(dc, stock_object(8))  # NULL_PEN
        old_brush = select(dc, self.brushes[TRACK])
        top, bottom, curve = s(TRACK_TOP), s(TRACK_TOP + TRACK_HEIGHT), s(TRACK_HEIGHT)
        round_rect(dc, s(INSET), top, bounds.right - s(INSET), bottom, curve, curve)
        left = INSET + (WIDTH - 2 * INSET - SWEEP_WIDTH) * position
        select(dc, self.brushes[ACCENT])
        round_rect(dc, s(left), top, s(left + SWEEP_WIDTH), bottom, curve, curve)
        select(dc, old_brush)
        select(dc, old_pen)

    def dispatch(self, hwnd, message, wp, lp):
        if message == WM_ERASEBKGND:
            return 1
        if message == WM_TIMER:
            invalidate(hwnd, None, False)
            return 0
        if message == WM_DPICHANGED:
            bounds = c.cast(lp, c.POINTER(w.RECT)).contents
            set_position(hwnd, None, bounds.left, bounds.top, bounds.right - bounds.left,
                         bounds.bottom - bounds.top, 0x14)  # NOACTIVATE | NOZORDER
            invalidate(hwnd, None, False)
            return 0
        if message == WM_PAINT:
            self.paint(hwnd)
            return 0
        return def_proc(hwnd, message, wp, lp)

    def paint(self, hwnd):
        begin = api(user, "BeginPaint", w.HDC, w.HWND, c.POINTER(Paint))
        end = api(user, "EndPaint", w.BOOL, w.HWND, c.POINTER(Paint))
        memory_dc = api(gdi, "CreateCompatibleDC", w.HDC, w.HDC)
        bitmap = api(gdi, "CreateCompatibleBitmap", w.HBITMAP, w.HDC, c.c_int, c.c_int)
        delete_dc = api(gdi, "DeleteDC", w.BOOL, w.HDC)
        copy = api(gdi, "BitBlt", w.BOOL, w.HDC, c.c_int, c.c_int, c.c_int, c.c_int,
                   w.HDC, c.c_int, c.c_int, w.DWORD)
        state, bounds = Paint(), w.RECT()
        target = begin(hwnd, c.byref(state))
        if not target:
            return
        try:
            rect_of(hwnd, c.byref(bounds))
            back = memory_dc(target)
            pixels = bitmap(target, bounds.right, bounds.bottom)
            try:
                if back and pixels:
                    old = select(back, pixels)
                    self.render(hwnd, back)
                    copy(target, 0, 0, bounds.right, bounds.bottom, back, 0, 0, 0xCC0020)
                    select(back, old)
                else:
                    self.render(hwnd, target)
            finally:
                if pixels:
                    delete(pixels)
                if back:
                    delete_dc(back)
        finally:
            end(hwnd, c.byref(state))


def run(splash):
    context = api(user, "SetThreadDpiAwarenessContext", w.HANDLE, w.HANDLE)
    context(c.c_void_p(-4))  # Per-monitor DPI v2 on this UI thread only.
    instance = api(kernel, "GetModuleHandleW", w.HINSTANCE, w.LPCWSTR)(None)
    create = api(user, "CreateWindowExW", w.HWND, w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD,
                 c.c_int, c.c_int, c.c_int, c.c_int, w.HWND, w.HMENU, w.HINSTANCE, c.c_void_p)
    register = api(user, "RegisterClassW", w.ATOM, c.POINTER(WindowClass))
    unregister = api(user, "UnregisterClassW", w.BOOL, w.LPCWSTR, w.HINSTANCE)
    destroy = api(user, "DestroyWindow", w.BOOL, w.HWND)
    timer = api(user, "SetTimer", c.c_size_t, w.HWND, c.c_size_t, w.UINT, c.c_void_p)
    untimer = api(user, "KillTimer", w.BOOL, w.HWND, c.c_size_t)
    monitor_at = api(user, "MonitorFromPoint", w.HMONITOR, w.POINT, w.DWORD)
    monitor_info = api(user, "GetMonitorInfoW", w.BOOL, w.HMONITOR, c.POINTER(Monitor))
    peek = api(user, "PeekMessageW", w.BOOL, c.POINTER(w.MSG), w.HWND, w.UINT, w.UINT, w.UINT)
    dispatch = api(user, "DispatchMessageW", w.LPARAM, c.POINTER(w.MSG))
    card = Card()
    clazz = WindowClass(proc=card.proc, instance=instance, name=CLASS_NAME)
    window = None
    registered = register(c.byref(clazz))
    try:
        if not registered:
            return
        cursor, display = w.POINT(), Monitor(size=c.sizeof(Monitor))
        user.GetCursorPos(c.byref(cursor))
        if not monitor_info(monitor_at(cursor, 2), c.byref(display)):
            return
        work = display.work
        window = create(0x08000080, CLASS_NAME, DISPLAY_NAME, 0x80000000, cursor.x, cursor.y, 1, 1,
                        None, None, instance, None)  # NOACTIVATE | TOOLWINDOW, no system frame.
        if not window or splash._stop.is_set():
            return
        card.update_dpi(window)
        width, height = card.scale(WIDTH), card.scale(HEIGHT)
        set_position(window, None, work.left + (work.right - work.left - width) // 2,
                     work.top + (work.bottom - work.top - height) // 2, width, height, 0x14)
        try:
            attr = api(c.WinDLL("dwmapi"), "DwmSetWindowAttribute", w.LONG, w.HWND, w.DWORD,
                       c.c_void_p, w.DWORD)
            for key, value in ((33, 2), (34, rgb("34394b"))):
                setting = w.DWORD(value)
                attr(window, key, c.byref(setting), c.sizeof(setting))
        except OSError:
            pass
        api(user, "ShowWindow", w.BOOL, w.HWND, c.c_int)(window, 4)
        api(user, "UpdateWindow", w.BOOL, w.HWND)(window)
        splash._window = window
        splash._shown.set()
        timer(window, 1, 30, None)
        message = w.MSG()
        while not splash._stop.is_set():
            while peek(c.byref(message), None, 0, 0, 1):
                dispatch(c.byref(message))
            splash._stop.wait(.012)
    finally:
        splash._window = None
        if window:
            untimer(window, 1)
            destroy(window)
        if registered:
            unregister(CLASS_NAME, instance)
        card.close()
