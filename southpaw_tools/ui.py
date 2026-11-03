from __future__ import annotations

import json
import threading
import ipaddress
import urllib.parse
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from . import __version__
from .catalog import AppRelease, catalog_document, load_catalog, parse_catalog
from .common import LauncherError, atomic_json, read_json
from .installer import Installer
from .paths import AppPaths
from .providers import HttpProvider

DATA = Path(__file__).resolve().parent / "data" / "catalog.json"
ASSETS = Path(__file__).resolve().parent / "assets"


class Task(QThread):
    progress = Signal(int, int)

    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.action = action
        self.cancel = threading.Event()
        self.result = None
        self.error = ""

    def run(self):
        try:
            self.result = self.action(self.progress.emit, self.cancel)
        except Exception as exc:
            self.error = str(exc)


class ConnectionDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("배포 서버 연결")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        title = QLabel("팀 도구를 받는 방법")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        intro = QLabel("서버가 꺼져 있어도 이미 설치한 도구는 실행할 수 있습니다.\n다운로드와 업데이트는 개발자 PC가 켜져 있을 때 가능합니다.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.url = QLineEdit(config.get("server_url", "http://127.0.0.1:8765"))
        self.lan = QCheckBox("LAN 연결 사용 (회사 내부의 개발자 PC)")
        self.lan.setChecked(config.get("lan_enabled", False) is True)
        self.token = QLineEdit(config.get("lan_token", ""))
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("서버 주소", self.url)
        form.addRow("", self.lan)
        form.addRow("LAN 배포 토큰", self.token)
        layout.addLayout(form)
        internet = QLabel("인터넷 배포  ·  미구성\nTLS·인증·회사 네트워크 정책 검증 전에는 연결하지 않습니다.")
        internet.setWordWrap(True)
        internet.setObjectName("muted")
        layout.addWidget(internet)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        value = {"server_url": self.url.text().strip(), "lan_enabled": self.lan.isChecked(),
                 "lan_token": self.token.text()}
        HttpProvider(value["server_url"], value["lan_token"], lan_enabled=value["lan_enabled"])
        return value


def app_icon(app: AppRelease, size=64) -> QIcon:
    if app.icon and (ASSETS / app.icon).is_file():
        return QIcon(str(ASSETS / app.icon))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    colors = {"ase-viewer": "#386c8b", "tag-master": "#6957a0", "pivot-fixer": "#39766b"}
    painter.setBrush(QColor(colors.get(app.app_id, "#6652ad")))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 15, 15)
    painter.setPen(QColor("#f7f7ff"))
    painter.setFont(QFont("Segoe UI", max(10, size // 4), QFont.Weight.Bold))
    initials = {"ase-viewer": "AV", "tag-master": "TM", "pivot-fixer": "PF",
                "tilenamer": "TN", "ps2ase": "PS"}
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials.get(app.app_id, "SP"))
    painter.end()
    return QIcon(pixmap)


STYLE = """
QWidget { background: #101321; color: #e9eaf7; font-family: 'Malgun Gothic', 'Segoe UI'; font-size: 13px; }
QMainWindow { background: #101321; }
QFrame#sidebar { background: #141827; border-right: 1px solid #282e46; }
QLabel#brand { color: #faf8ff; font-size: 21px; font-weight: 800; letter-spacing: 2px; }
QLabel#eyebrow { color: #a39bc5; font-size: 11px; letter-spacing: 2px; }
QLabel#heroTitle { font-size: 34px; font-weight: 750; background: transparent; }
QLabel#heroDescription { color: #b5bed5; font-size: 14px; background: transparent; }
QLabel#muted { color: #9ca7c2; background: transparent; }
QLabel#badge { color: #bcb0ff; background: #292343; border: 1px solid #4c426c; border-radius: 10px; padding: 6px 10px; }
QLabel#sectionTitle { font-size: 16px; font-weight: 650; background: transparent; }
QLabel#dialogTitle { font-size: 20px; font-weight: bold; }
QFrame#hero { background: #1c2038; border: 1px solid #353653; border-radius: 16px; }
QFrame#card { background: #171c2e; border: 1px solid #2c344d; border-radius: 12px; }
QFrame#card QLabel { background: transparent; }
QListWidget { border: none; background: #141827; outline: none; }
QListWidget::item { border-radius: 9px; padding: 12px 9px; margin: 4px 0; color: #b8bfd6; }
QListWidget::item:selected { background: #302b4b; color: #f5f0ff; border: 1px solid #5d4f87; }
QListWidget::item:hover { background: #22283c; }
QPushButton { background: #242c42; border: 1px solid #3a4561; border-radius: 8px; padding: 10px 14px; }
QPushButton:hover { background: #323c58; border-color: #70638d; }
QPushButton:pressed { background: #443963; }
QPushButton:disabled { background: #1d2333; color: #77819b; border-color: #2c3347; }
QPushButton#primary { background: #8061dd; border: 1px solid #a18be7; font-size: 17px; font-weight: bold; padding: 14px 34px; }
QPushButton#primary:hover { background: #9472ef; }
QPushButton#primary:disabled { background: #303044; color: #9193ab; border-color: #41415a; }
QPlainTextEdit { background: #171c2e; border: none; color: #cad1e5; padding: 8px; selection-background-color: #6753a4; }
QProgressBar { border: 1px solid #39415a; background: #191e30; border-radius: 6px; min-height: 14px; text-align: center; }
QProgressBar::chunk { background: #8b6be1; border-radius: 5px; }
QLineEdit { padding: 9px; background: #1d2437; border: 1px solid #454e68; border-radius: 5px; }
QDialog { background: #141a2c; }
QToolTip { background: #2d3450; color: #ffffff; border: 1px solid #61547d; padding: 5px; }
"""


class MainWindow(QMainWindow):
    def __init__(self, paths: AppPaths | None = None, *, catalog_path: Path = DATA,
                 auto_connect: bool = True, installer: Installer | None = None):
        super().__init__()
        # Qt's offscreen Windows platform has an empty font database. Explicitly
        # load an installed system font for diagnostic renders; don't redistribute it.
        if not QFontDatabase.families():
            for filename in ("C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/segoeui.ttf"):
                if Path(filename).is_file():
                    QFontDatabase.addApplicationFont(filename)
        self.paths = paths or AppPaths.default()
        self.installer = installer or Installer(self.paths)
        self.apps = load_catalog(catalog_path)
        self.online = False
        self.health = {}
        self.provider = None
        self.server_state = "오프라인 · 미확인"
        self.catalog_state = "캐시/초기 목록"
        self.package_state = "미시도"
        self.catalog_error = ""
        self.last_checked = "없음"
        self.task: Task | None = None
        self.operation = ""
        self._success = None
        self._load_warning = ""
        self.config = {}
        try:
            if (self.paths.root / "settings.json").exists():
                self.config = read_json(self.paths.root / "settings.json")
            if (self.paths.root / "catalog-cache.json").exists():
                self.apps = load_catalog(self.paths.root / "catalog-cache.json")
        except LauncherError as exc:
            self._load_warning = str(exc)
        self._merge_installed()
        self.setWindowTitle(f"Southpaw Tools Launcher · v{__version__}")
        self.resize(1240, 820)
        self.setMinimumSize(980, 700)
        self.setStyleSheet(STYLE)
        self._build()
        self._populate()
        self._connection_status()
        self.timer = QTimer(self)
        self.timer.setInterval(4000)
        self.timer.timeout.connect(self.render)
        self.timer.start()
        if auto_connect:
            QTimer.singleShot(200, self.refresh)

    def _merge_installed(self):
        try:
            installed = self.installer.installed_apps()
            known = {app.app_id for app in self.apps}
            self.apps.extend(app for app in installed if app.app_id not in known)
        except LauncherError as exc:
            self._load_warning = str(exc)

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        base = QHBoxLayout(root)
        base.setContentsMargins(0, 0, 0, 0)
        base.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 28, 18, 22)
        brand = QLabel("SOUTHPAW")
        brand.setObjectName("brand")
        side.addWidget(brand)
        subtitle = QLabel("TOOLS  /  TEAM WORKSPACE")
        subtitle.setObjectName("eyebrow")
        side.addWidget(subtitle)
        side.addSpacing(32)
        label = QLabel("라이브러리")
        label.setObjectName("muted")
        side.addWidget(label)
        self.list = QListWidget()
        from PySide6.QtCore import QSize
        self.list.setIconSize(QSize(32, 32))
        self.list.currentRowChanged.connect(self.render)
        side.addWidget(self.list, 1)
        footer = QLabel(f"개발 프리뷰  ·  v{__version__}\nSouthpaw Games 내부 도구")
        footer.setObjectName("muted")
        side.addWidget(footer)
        base.addWidget(sidebar)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(30, 24, 30, 24)
        main.setSpacing(20)
        top = QHBoxLayout()
        self.server_status = QLabel("● 오프라인 · 설치된 도구 실행 가능")
        self.server_status.setObjectName("muted")
        self.server_status.setWordWrap(True)
        top.addWidget(self.server_status, 1)
        self.refresh_button = QPushButton("업데이트 확인")
        self.refresh_button.clicked.connect(self.refresh)
        top.addWidget(self.refresh_button)
        self.connection_button = QPushButton("연결 설정")
        self.connection_button.clicked.connect(self.configure)
        top.addWidget(self.connection_button)
        main.addLayout(top)

        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_layout.setSpacing(20)
        self.hero_icon = QLabel()
        self.hero_icon.setFixedSize(72, 72)
        hero_layout.addWidget(self.hero_icon)
        hero_text = QVBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("heroTitle")
        self.title.setWordWrap(True)
        hero_text.addWidget(self.title)
        self.description = QLabel()
        self.description.setObjectName("heroDescription")
        self.description.setWordWrap(True)
        hero_text.addWidget(self.description)
        hero_layout.addLayout(hero_text, 1)
        main.addWidget(hero)

        center = QHBoxLayout()
        center.setSpacing(20)
        notes_card = QFrame()
        notes_card.setObjectName("card")
        note_layout = QVBoxLayout(notes_card)
        note_layout.setContentsMargins(18, 18, 18, 18)
        note_title = QHBoxLayout()
        label = QLabel("업데이트 내역")
        label.setObjectName("sectionTitle")
        note_title.addWidget(label, 1)
        self.channel = QLabel("팀 승인 배포본")
        self.channel.setObjectName("badge")
        note_title.addWidget(self.channel)
        note_layout.addLayout(note_title)
        self.notes = QPlainTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        note_layout.addWidget(self.notes, 1)
        center.addWidget(notes_card, 1)

        info_card = QFrame()
        info_card.setObjectName("card")
        info_card.setFixedWidth(236)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(18, 20, 18, 20)
        info_title = QLabel("프로그램 정보")
        info_title.setObjectName("sectionTitle")
        info_layout.addWidget(info_title)
        self.info = {}
        for key in ("설치 상태", "설치 버전", "승인 버전", "다운로드", "배포 식별자"):
            label = QLabel(key)
            label.setObjectName("muted")
            info_layout.addWidget(label)
            value = QLabel("—")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.info[key] = value
            info_layout.addWidget(value)
            info_layout.addSpacing(10)
        info_layout.addStretch()
        info_layout.addWidget(QLabel("Windows 10 / 11"))
        center.addWidget(info_card)
        main.addLayout(center, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()
        main.addWidget(self.progress)
        self.message = QLabel(self._load_warning or "프로그램을 선택하고 승인된 도구를 설치하세요.")
        self.message.setWordWrap(True)
        self.message.setObjectName("muted")
        main.addWidget(self.message)
        actions = QHBoxLayout()
        self.folder_button = QPushButton("설치 위치 열기")
        self.folder_button.clicked.connect(self.open_folder)
        actions.addWidget(self.folder_button)
        self.remove_button = QPushButton("제거")
        self.remove_button.clicked.connect(self.remove)
        actions.addWidget(self.remove_button)
        self.cancel_button = QPushButton("다운로드 취소")
        self.cancel_button.clicked.connect(self.cancel_task)
        self.cancel_button.hide()
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        self.launch_current = QPushButton("현재 버전 실행")
        self.launch_current.clicked.connect(self.launch)
        self.launch_current.hide()
        actions.addWidget(self.launch_current)
        self.primary = QPushButton("설치")
        self.primary.setObjectName("primary")
        self.primary.setMinimumWidth(160)
        self.primary.clicked.connect(self.primary_action)
        actions.addWidget(self.primary)
        main.addLayout(actions)
        base.addWidget(content, 1)

    def _populate(self, selected_id=None):
        self.list.blockSignals(True)
        self.list.clear()
        selected = 0
        for index, app in enumerate(self.apps):
            item = QListWidgetItem(app_icon(app), app.display_name)
            item.setToolTip(app.description)
            self.list.addItem(item)
            if app.app_id == selected_id:
                selected = index
        self.list.setCurrentRow(selected)
        self.list.blockSignals(False)
        self.render()

    def selected(self) -> AppRelease | None:
        row = self.list.currentRow()
        return self.apps[row] if 0 <= row < len(self.apps) else None

    def render(self, *_):
        app = self.selected()
        if not app:
            return
        self.title.setText(app.display_name)
        self.description.setText(app.description)
        self.hero_icon.setPixmap(app_icon(app, 72).pixmap(72, 72))
        text = app.release_notes or "등록된 릴리즈 노트가 없습니다."
        if self.notes.toPlainText() != text:
            self.notes.setPlainText(text)
        self.info["승인 버전"].setText(app.version)
        self.info["다운로드"].setText(f"{app.package_size / 1024**2:.1f} MB" if app.published else "배포 패키지 미확인")
        self.info["배포 식별자"].setText(app.release_id)
        busy = self.task is not None
        error, catalog_error = "", self.catalog_error
        installed, running, update = None, False, False
        pending = False
        try:
            pending = self.installer.pending_recovery(app.app_id)
            installed = self.installer.installed(app.app_id)
            running = bool(installed) and self.installer.is_running(app.app_id)
            if installed:
                self.installer.resolve_launch(installed)
        except LauncherError as exc:
            error = str(exc)
        except OSError as exc:
            error = f"로컬 파일 확인 실패: {exc}"
        try:
            update = bool(installed) and app.is_new_release(installed)
        except LauncherError as exc:
            catalog_error = str(exc)
        self.info["설치 버전"].setText(installed.version if installed else "—")
        can_install = self.online and app.published and not catalog_error
        repair = bool(installed and error)
        can_repair = can_install and bool(update or app == installed)
        status = "실행 중 · 업데이트 보류" if running else "복구 필요" if error or pending else "설치 완료 · 목록 오류(업데이트 차단)" if installed and catalog_error else "업데이트 가능" if update else "설치 완료" if installed else "미설치"
        self.info["설치 상태"].setText(status)
        self.primary.setText("작업 중…" if busy else "실행 중" if running else "복구 확인" if pending else "복구 설치" if repair else "업데이트" if installed and update and can_install else "실행" if installed else "설치" if app.published else "패키지 미확인")
        self.primary.setEnabled(not busy and not running and (pending or (can_repair if error else bool(installed or can_install))))
        self.primary.setToolTip("" if app.published else app.availability_reason)
        self.folder_button.setEnabled(not busy and self.paths.app(app.app_id).exists())
        self.remove_button.setEnabled(not busy and bool(installed) and not running)
        self.launch_current.setVisible(bool(installed and update and can_install and not error))
        self.launch_current.setEnabled(not busy and not running and not error)
        self.refresh_button.setEnabled(not busy)
        self.connection_button.setEnabled(not busy)
        if error:
            self.message.setText(f"복구 필요: {error}")
        elif catalog_error:
            self.message.setText(f"목록 오류 — 설치/업데이트 차단, 로컬 실행 가능: {catalog_error}")
        elif not app.published and not installed and not busy:
            self.message.setText(app.availability_reason or "배포 패키지 미확인")

    def _begin(self, operation, action, success):
        if self.task is not None:
            return
        self.operation = operation
        self.message.setText(operation)
        self._success = success
        self.task = Task(action, self)
        self.task.progress.connect(self._progress)
        self.task.finished.connect(self._finished)
        self.cancel_button.setVisible(operation.startswith(("설치", "업데이트", "복구 설치")))
        self.progress.setVisible(self.cancel_button.isVisible())
        self.progress.setValue(0)
        self.render()
        self.task.start()

    def _progress(self, done, total):
        self.progress.setValue(int(done * 100 / total) if total else 0)
        self.message.setText(f"{self.operation}  ·  {done / 1024**2:.1f} / {total / 1024**2:.1f} MB")

    def _finished(self):
        task, success = self.task, self._success
        self.task = None
        self.cancel_button.hide()
        self.progress.hide()
        if task.error:
            self.message.setText(task.error)
            if self.operation == "서버 연결과 업데이트 확인":
                self.online = False
                self.server_state = "오프라인 · 접속 실패"
            elif self.operation.startswith(("설치:", "업데이트:", "복구 설치:")):
                self.package_state = "수신 검증 성공 · 설치 실패" if self.installer.download_verified else "다운로드/검증 실패"
                self.server_state = "재확인 필요"
                self.online = False  # Require fresh catalog validation for the next install.
        else:
            try:
                success(task.result)
            except Exception as exc:
                self.message.setText(str(exc))
                if self.operation == "서버 연결과 업데이트 확인":
                    self.online = False
                    self.catalog_state = "오류"
                    self.catalog_error = str(exc)
        if self.operation.startswith(("설치:", "업데이트:", "복구 설치:")) and not task.error:
            self.package_state = "다운로드·검증 성공"
        if self.installer.warnings and self.operation != "서버 연결과 업데이트 확인":
            self.message.setText(self.message.text() + "\n경고: " + " / ".join(self.installer.warnings))
        self._connection_status()
        task.deleteLater()
        self.render()

    def cancel_task(self):
        if self.task:
            self.task.cancel.set()
            self.cancel_button.setEnabled(False)
            self.message.setText("현재 전송 종료 후 취소합니다. 기존 설치는 유지됩니다.")

    def refresh(self):
        if self.task:
            return
        try:
            provider = HttpProvider(self.config.get("server_url", "http://127.0.0.1:8765"),
                                    self.config.get("lan_token", ""),
                                    lan_enabled=self.config.get("lan_enabled", False) is True)
        except LauncherError as exc:
            self.online = False
            self.catalog_error = str(exc)
            self.catalog_state = "차단"
            self.server_state = "설정 오류 · 미확인"
            self._connection_status()
            self.message.setText(str(exc))
            self.render()
            return

        def fetch(progress, cancel):
            health = provider.health()
            try:
                return health, provider.catalog(), ""
            except Exception as exc:
                return health, None, str(exc)

        def connected(result):
            health, apps, catalog_error = result
            self.health = health
            self.last_checked = datetime.now().strftime("%H:%M:%S")
            self.server_state = "응답 확인(마지막 조회)"
            if catalog_error:
                self.catalog_state, self.catalog_error = "실패", catalog_error
                self.online = False
                self.message.setText(f"카탈로그 조회 실패: {catalog_error}")
                return
            selected = self.selected().app_id if self.selected() else None
            # Reject immutable-release identity changes before accepting the catalog.
            old = {app.app_id: app for app in self.apps}
            for app in apps:
                if app.app_id in old and old[app.app_id].published and app.published:
                    app.is_new_release(old[app.app_id])
                installed = self.installer.installed(app.app_id)
                if installed and app.published:
                    app.is_new_release(installed)
            atomic_json(self.paths.root / "catalog-cache.json", catalog_document(apps))
            self.health, self.apps, self.provider, self.online = health, apps, provider, True
            self.catalog_state, self.catalog_error = "검증 성공(서명 없음)", ""
            self._merge_installed()
            self.message.setText("승인 배포 목록을 확인했습니다. 설치·업데이트는 버튼을 누른 경우에만 진행합니다.")
            self._populate(selected)

        self.online = False
        self.server_state = "확인 중"
        self._connection_status()
        self._begin("서버 연결과 업데이트 확인", fetch, connected)

    def _connection_status(self):
        try:
            host = urllib.parse.urlsplit(self.config.get("server_url", "http://127.0.0.1:8765")).hostname
            route = "로컬(loopback)" if host == "localhost" or ipaddress.ip_address(host).is_loopback else f"LAN({host})"
        except (ValueError, TypeError):
            route = "미확인"
        lan = ("ON" if self.health.get("lan_enabled") else "OFF") if self.health else "미확인"
        self.server_status.setText(f"서버: {self.server_state} · 경로: {route} · 확인 {self.last_checked}\n"
                                   f"목록: {self.catalog_state} · 패키지: {self.package_state} · 서버 LAN: {lan}(마지막 조회) / 인터넷 미구성")

    def configure(self):
        dialog = ConnectionDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                config = dialog.values()
                atomic_json(self.paths.root / "settings.json", config)
                self.config = config
                self.refresh()
            except LauncherError as exc:
                self.message.setText(str(exc))

    def primary_action(self):
        app = self.selected()
        if not app:
            return
        try:
            if self.installer.pending_recovery(app.app_id):
                self._begin("복구 확인", lambda progress, cancel: self.installer.recover(app.app_id),
                            lambda result: self.message.setText("복구 확인 완료. 설치 상태를 확인하고 실행/설치를 다시 선택하세요."))
                return
            installed = self.installer.installed(app.app_id)
            error = ""
            try:
                update = bool(installed) and app.is_new_release(installed)
            except LauncherError as exc:
                update, error = False, str(exc)
            local_error = ""
            if installed:
                try:
                    self.installer.resolve_launch(installed)
                except (LauncherError, OSError) as exc:
                    local_error = str(exc)
            if installed and not local_error and not (self.online and update and not self.catalog_error):
                self.launch()
                return
            if error or self.catalog_error:
                raise LauncherError(f"목록 충돌 — 설치/업데이트 차단: {error or self.catalog_error}")
            if not self.online or not self.provider or not app.published:
                raise LauncherError("서버 연결과 승인 배포 패키지를 확인하세요.")
            title = "복구 설치" if local_error else "업데이트" if installed else "설치"
            text = f"{app.display_name} {app.version}을(를) {title}할까요?"
            if installed:
                text += "\n기존 버전은 보존하고, 등록된 사용자 설정을 새 버전으로 복사합니다."
            if QMessageBox.question(self, title, text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
            provider = self.provider
            self.cancel_button.setEnabled(True)
            self._begin(f"{title}: {app.display_name}",
                        lambda progress, cancel: self.installer.install(app, provider, progress, cancel),
                        lambda result: self.message.setText(f"{result.display_name} {title} 완료. 실행 버튼으로 시작하세요."))
        except LauncherError as exc:
            self.message.setText(str(exc))

    def launch(self):
        app = self.selected()
        if app:
            try:
                self.installer.launch(app.app_id)
                self.message.setText(f"{app.display_name} 실행 요청 완료")
            except LauncherError as exc:
                self.message.setText(str(exc))
            self.render()

    def remove(self):
        app = self.selected()
        if not app:
            return
        text = (f"{app.display_name}의 설치 파일을 제거할까요?\n"
                "사용자 설정·작업물·변경된 파일은 설치 폴더에 보존합니다.")
        if QMessageBox.question(self, "프로그램 제거", text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        def done(result):
            count = len(result["retained_files"])
            self.message.setText(f"제거 완료. 사용자/변경 파일 {count}개 보존 · {result['retained_directory']}")
        self._begin(f"제거: {app.display_name}", lambda progress, cancel: self.installer.uninstall(app.app_id), done)

    def open_folder(self):
        app = self.selected()
        if app:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.paths.app(app.app_id))))

    def closeEvent(self, event):
        if self.task:
            self.task.cancel.set()
            self.message.setText("작업 취소/정리가 끝난 뒤 닫아 주세요. 기존 프로그램은 종료하지 않습니다.")
            event.ignore()
        else:
            self.timer.stop()
            event.accept()
