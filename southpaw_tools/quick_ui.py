"""Qt Quick presentation of the existing launcher workflow."""
from pathlib import Path
import re
import sys

from PySide6.QtCore import QObject, Property, QEventLoop, QSize, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QFontDatabase, QIcon, QImage
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QApplication

from . import __version__
from .branding import ICON_FILENAME
from .common import LauncherError, atomic_json, inside, read_json
from .ui import ASSETS, REFRESH_OPERATIONS, MainWindow, NotesDocument, app_icon


def _set_windows_caption(hwnd, dark):
    """Apply Windows SDK DWM attributes to the existing native frame."""
    import ctypes
    from ctypes import wintypes

    # DWMWINDOWATTRIBUTE in dwmapi.h. Probe HRESULTs on the running OS.
    immersive_dark_mode, caption_color, text_color = 20, 35, 36
    default_color = 0xFFFFFFFF
    try:
        set_attribute = ctypes.WinDLL("dwmapi").DwmSetWindowAttribute
        set_attribute.argtypes = (wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD)
        set_attribute.restype = wintypes.LONG
    except (OSError, AttributeError):
        return

    def apply(attribute, value):
        return set_attribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)) == 0

    def colorref(red, green, blue):
        return wintypes.DWORD(red | green << 8 | blue << 16)

    # Match Launcher.qml's dark header and text. The light theme restores OS colors.
    caption = colorref(0x1B, 0x1E, 0x2B) if dark else wintypes.DWORD(default_color)
    text = colorref(0xF5, 0xF3, 0xFF) if dark else wintypes.DWORD(default_color)
    if not apply(caption_color, caption):
        return
    if not apply(text_color, text):
        apply(caption_color, wintypes.DWORD(default_color))
        return
    apply(immersive_dark_mode, wintypes.BOOL(dark))


class Field:
    """Presentation-only port for the shared workflow's labels and actions."""
    def __init__(self, notify, text="", visible=True):
        self.notify = notify
        self.data = {"text": text, "visible": visible, "enabled": True, "tip": "", "value": 0}

    def _set(self, key, value):
        if self.data[key] != value:
            self.data[key] = value
            self.notify()

    def setText(self, value):
        self._set("text", value)

    def text(self):
        return self.data["text"]

    def setVisible(self, visible):
        self._set("visible", visible)

    def isVisible(self):
        return self.data["visible"]

    def hide(self):
        self.setVisible(False)

    def show(self):
        self.setVisible(True)

    def setEnabled(self, enabled):
        self._set("enabled", enabled)

    def setToolTip(self, text):
        self._set("tip", text)

    def toolTip(self):
        return self.data["tip"]

    def setValue(self, value):
        self._set("value", value)

    def show_notes(self, text):
        if text == getattr(self, "_notes_source", None):
            return
        self._notes_source = text
        source = re.sub(r'(?im)^Build source commit:\s*\n\s*`?[0-9a-f]{7,40}`?\s*\n', '', text)
        document = NotesDocument()
        document.setMarkdown(source, NotesDocument.MarkdownFeature.MarkdownDialectGitHub
                             | NotesDocument.MarkdownFeature.MarkdownNoHTML)
        blocks = []
        block = document.begin()
        while block.isValid():
            raw = block.text().replace("\ufffc", "").strip()
            if raw:
                blocks.append({"text": raw, "level": block.blockFormat().headingLevel(),
                               "bullet": block.textList() is not None})
            block = block.next()
        self.blocks = blocks
        groups = []
        for item in blocks:
            match = re.search(r"(?<![\w.])v?\d+(?:\.\d+){1,3}(?:[- ]?RC\d+)?\b",
                              item["text"], flags=re.IGNORECASE) if item["level"] else None
            if match:
                version = match.group()
                title = (item["text"][:match.start()] + item["text"][match.end():]).strip(" −–—-:·[]()")
                groups.append({"version": version, "title": title, "blocks": []})
            else:
                if not groups:
                    groups.append({"version": "", "title": "", "blocks": []})
                groups[-1]["blocks"].append(item)
        self.groups = groups
        self.setText(document.toPlainText())
        self.notify()


class AppImages(QQuickImageProvider):
    def __init__(self, window):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.window = window

    def requestImage(self, name, size, requested):
        app = next((a for a in self.window.apps if a.app_id == name), None)
        width = max(20, min(requested.width(), 192)) if requested.width() > 0 else 72
        icon = app_icon(app, width) if app else QIcon(str(ASSETS / ICON_FILENAME))
        image = icon.pixmap(QSize(width, width)).toImage()
        if image.isNull():
            image = QImage(width, width, QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.transparent)
        if size is not None:
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image


class LauncherSurface(QObject):
    rowsChanged = Signal()
    viewChanged = Signal()
    selectionChanged = Signal()
    appearanceChanged = Signal()
    promptChanged = Signal()

    ACTIONS = {
        "refresh": ("refresh", "refresh_button"),
        "launcher": ("update_launcher", "launcher_update_button"),
        "primary": ("primary_action", "primary"),
        "launch": ("launch", "launch_current"),
        "remove": ("remove", "remove_button"),
        "versions": ("choose_version", "versions_button"),
        "folder": ("open_folder", "folder_button"),
        "configure": ("configure", "connection_button"),
        "cancel": ("cancel_task", "cancel_button"),
        "details": ("show_details", None),
    }

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self._rows = []
        self._selected = -1
        self._prompt = {}
        self._reply = None
        self._loop = None
        font_id = QFontDatabase.addApplicationFont(str(ASSETS / "fonts" / "PretendardVariable.ttf"))
        bundled_families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        if bundled_families:
            self._font = bundled_families[0]
        else:
            families = QFontDatabase.families()
            self._font = next((name for name in ("Segoe UI Variable", "Segoe UI",
                                                 "Malgun Gothic") if name in families), "sans-serif")
        self._flush = QTimer(self)
        self._flush.setSingleShot(True)
        self._flush.timeout.connect(self.viewChanged)
        self._dark = True
        try:
            self._prefs = inside(window.paths.root, "ui-preferences.json")
            if self._prefs.is_file() and self._prefs.stat().st_size < 2048:
                self._dark = read_json(self._prefs).get("theme") != "light"
        except (LauncherError, OSError, AttributeError):
            self._prefs = None

    def invalidate(self):
        if not self._flush.isActive():
            self._flush.start(0)

    @Property("QVariantList", notify=rowsChanged)
    def rows(self):
        return self._rows

    @Property(int, notify=selectionChanged)
    def selectedIndex(self):
        return self._selected

    @Property(str, constant=True)
    def brandIcon(self):
        return QUrl.fromLocalFile(str(ASSETS / "southpaw-launcher.png")).toString()

    @Property(bool, notify=appearanceChanged)
    def dark(self):
        return self._dark

    @Property(str, constant=True)
    def uiFont(self):
        return self._font

    @Property(str, constant=True)
    def productVersion(self):
        return __version__

    @Property("QVariantMap", notify=viewChanged)
    def view(self):
        w = self.window
        result = {name: dict(getattr(w, name).data) for name in w.FIELDS}
        result.update({name: field.text() for name, field in w.info.items()})
        app = w.selected()
        selected_installed = any(row["id"] == app.app_id and row["installed"] for row in self._rows) if app else False
        result.update(selectedInstalled=selected_installed, online=w.online, busy=w.task is not None or w._launcher_handoff,
                      catalogError=bool(w.catalog_error), hasSelection=app is not None,
                      selectedId=app.app_id if app else "", connectedRepo=w.config.get("github_repository", ""),
                      testing=w.github_test_mode, knownProgress=w.known_progress,
                      bridgeBusy=getattr(w, "bridge_in_progress", False),
                      activeApp=w.active_app if w.task else "",
                      checking=w.task is not None and w.operation in REFRESH_OPERATIONS,
                      lastCheck=w._last_catalog_check.get("result", "") if w._last_catalog_check else "",
                      latestVerified=w.launcher_verified_version == __version__,
                      verifiedVersion=w.launcher_target or w.launcher_verified_version or "",
                      issues=dict(w.app_issues), noteBlocks=getattr(w.notes, "blocks", []),
                      noteGroups=getattr(w.notes, "groups", []))
        return result

    @Property("QVariantMap", notify=promptChanged)
    def prompt(self):
        return self._prompt

    def sync_rows(self):
        rows = []
        for app in self.window.apps:
            installed = None
            pending = update = problem = False
            try:
                installed = self.window.installer.installed(app.app_id)
                pending = self.window.installer.pending_recovery(app.app_id)
                update = bool(installed and app.is_new_release(installed))
            except (LauncherError, OSError):
                problem = True
            rows.append({"id": app.app_id, "title": app.display_name, "category": app.category,
                         "description": app.description, "version": installed.version if installed else "",
                         "providedVersion": app.version,
                         "pending": pending, "problem": problem, "update": update, "published": app.published,
                         "installed": installed is not None})
        if rows != self._rows:
            self._rows = rows
            self.rowsChanged.emit()

    def populate(self, selected_id):
        self.sync_rows()
        position = next((i for i, row in enumerate(self._rows) if row["id"] == selected_id), 0)
        self.select(position if self._rows else -1)

    @Slot(int)
    def select(self, position):
        if self._loop is not None or not -1 <= position < len(self._rows):
            return
        if position != self._selected:
            self._selected = position
            self.selectionChanged.emit()
        self.window.render()

    @Slot(str, result=bool)
    def selectApp(self, app_id):
        if self._loop is not None:
            return False
        position = next((index for index, entry in enumerate(self.window.apps)
                         if entry.app_id == app_id), -1)
        if position < 0:
            return False
        self.select(position)
        return True

    @Slot(str, str)
    def actOnApp(self, app_id, command):
        if (command in {"primary", "launch"} and not self.window.task
                and not self.window._launcher_handoff
                and not getattr(self.window, "bridge_in_progress", False)
                and self.selectApp(app_id)):
            self.act(command)

    @Slot(str)
    def act(self, command):
        if self._loop is not None or getattr(self.window, "bridge_in_progress", False):
            return
        methods = self.ACTIONS.get(command)
        if not methods:
            return
        action, field = methods
        if field:
            state = getattr(self.window, field).data
            if not state["visible"] or not state["enabled"]:
                return
        getattr(self.window, action)()
        self.invalidate()

    @Slot(result=str)
    def versionNotice(self):
        app = self.window.selected()
        if app is None:
            return ""
        installer = self.window.installer
        try:
            current = installer.installed(app.app_id)
            if current and any(item != current for item in installer.retained_versions(app.app_id)):
                return ""
        except (LauncherError, OSError):
            return "보관된 버전을 확인할 수 없습니다."
        return "전환 가능한 보관 버전이 없습니다."

    @Slot(bool)
    def setDark(self, dark):
        if self._dark == dark:
            return
        try:
            if self._prefs is None:
                raise LauncherError("테마 설정 경로를 사용할 수 없습니다.")
            atomic_json(self._prefs, {"theme": "dark" if dark else "light"})
        except (LauncherError, OSError):
            self.window.message.setText("테마를 저장하지 못했습니다. 환경 설정 파일을 확인해 주세요.")
            return
        self._dark = dark
        self.appearanceChanged.emit()

    def ask(self, title, text, choices=(), *, information=False):
        if self._loop is not None:
            return None
        loop = self._loop = QEventLoop(self)
        self._reply = None
        self._prompt = {"title": title, "text": text, "choices": list(choices), "information": information}
        self.promptChanged.emit()
        try:
            if self._prompt:
                loop.exec()
            return self._reply
        finally:
            self._prompt = {}
            self._loop = None
            self.promptChanged.emit()
            loop.deleteLater()

    @Slot(bool, int)
    def reply(self, accepted, index):
        if self._loop is None or not self._prompt:
            return
        choices = self._prompt["choices"]
        if accepted:
            self._reply = choices[index] if choices and 0 <= index < len(choices) else (True if not choices else None)
        self._prompt = {}
        self._loop.quit()


class QuickLauncherWindow(MainWindow):
    """Widget host retains the established window/handshake and uses a Quick scene."""
    FIELDS = (
        "title", "description", "notes", "server_status", "refresh_button", "connection_button",
        "launcher_update_button", "launcher_versions", "latest_app_label", "message",
        "folder_button", "remove_button", "cancel_button", "launch_current", "versions_button",
        "primary", "progress",
    )
    HIDDEN_FIELDS = {"launcher_update_button", "cancel_button", "launch_current", "progress"}

    def _build(self):
        self.known_progress = False
        self.active_app = ""
        self.app_issues = {}
        self.surface = LauncherSurface(self)
        self.surface.appearanceChanged.connect(self._apply_caption)
        for name in self.FIELDS:
            setattr(self, name, Field(self.surface.invalidate, visible=name not in self.HIDDEN_FIELDS))
        self.info = {key: Field(self.surface.invalidate, "—")
                     for key in ("설치 상태", "설치 버전", "승인 버전", "다운로드", "배포 식별자")}
        self.message.setText(self._load_warning)
        self.refresh_button.setText("업데이트 확인")
        self.connection_button.setText("연결 설정")
        self.connection_button.setVisible(not self.managed_session)
        self.launcher_versions.setText(f"런처 설치 버전 v{__version__} · 최신 버전 미확인")
        self._first_frame = False
        self._frame_callback = None
        self.resize(1200, 780)
        self.setMinimumSize(620, 540)
        view = self.quick = QQuickWidget(self)
        view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        view.setClearColor("#151822")
        if getattr(sys, "frozen", False):
            view.engine().addImportPath(str(Path(sys._MEIPASS) / "q"))
        view.engine().addImageProvider("southpaw", AppImages(self))
        view.rootContext().setContextProperty("launcher", self.surface)
        view.sceneGraphError.connect(self._scene_error)
        view.setSource(QUrl.fromLocalFile(str(Path(__file__).with_name("quick") / "Launcher.qml")))
        if view.status() != QQuickWidget.Status.Ready or view.rootObject() is None:
            raise LauncherError("QML 화면 준비 실패: " + " / ".join(error.toString() for error in view.errors()))
        view.quickWindow().afterRendering.connect(self._frame_rendered, Qt.ConnectionType.QueuedConnection)
        self.setCentralWidget(view)

    def showEvent(self, event):
        self._apply_caption()
        super().showEvent(event)

    def _apply_caption(self):
        if sys.platform == "win32" and QApplication.platformName() == "windows":
            _set_windows_caption(int(self.winId()), self.surface.dark)

    def _scene_error(self, _, message):
        print(f"QML 장면 초기화 실패: {message}")
        QTimer.singleShot(0, lambda: QApplication.instance().exit(11))

    def when_quick_frame(self, callback):
        self._frame_callback = callback
        if self._first_frame:
            callback()

    def _frame_rendered(self):
        if not self._first_frame:
            self._first_frame = True
            if self._frame_callback:
                self._frame_callback()

    def _populate(self, selected_id=None):
        self.surface.populate(selected_id)

    def _show_app_icon(self, app):
        pass  # Icons are provided by app_id through the Quick image provider.

    def selected(self):
        i = self.surface.selectedIndex
        return self.apps[i] if 0 <= i < len(self.apps) else None

    def render(self, *_):
        super().render()
        self.surface.invalidate()

    def _begin(self, operation, action, success):
        if self.task is None:
            self.known_progress = False
            app = self.selected()
            self.active_app = (app.app_id if app and (": " in operation or operation in
                              {"복구 확인", "버전 전환", "제거"}) else "")
            self.app_issues.pop(self.active_app, None)
        super()._begin(operation, action, success)

    def _progress(self, done, total):
        self.known_progress = total > 0
        super()._progress(done, total)
        self.surface.invalidate()

    def _finished(self):
        if self.active_app and self.task.error:
            self.app_issues[self.active_app] = self.task.error
        super()._finished()
        self.surface.sync_rows()

    def _automatic_refresh(self):
        if not self.surface.prompt:
            super()._automatic_refresh()

    def _ask(self, title, message, *, default_no=False):
        return bool(self.surface.ask(title, message))

    def _choose_item(self, title, message, choices):
        return self.surface.ask(title, message, choices)

    def show_details(self):
        app = self.selected()
        if app:
            self.surface.ask("프로그램 상세 정보",
                             f"{app.display_name}\n앱 ID: {app.app_id}\n릴리스 ID: {app.release_id}\n"
                             f"패키지 SHA-256: {app.sha256}\n\n연결: {self.server_status.text()}\n"
                             f"{self.server_status.toolTip()}\n\n진단 기록 쓰기: {self._diagnostic_write_error or '정상'}"
                             f"\n\n릴리스 노트 원문\n{app.release_notes}", information=True)

    def closeEvent(self, event):
        if self.surface.prompt:
            self.surface.reply(False, -1)
            event.ignore()
        else:
            super().closeEvent(event)
