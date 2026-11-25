from __future__ import annotations

import json
import threading
import ipaddress
import urllib.parse
import time
import re
import os
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QIcon, QPainter, QPixmap, QTextDocument, QTextCursor
from .branding import DISPLAY_NAME, DESCRIPTION, ICON_FILENAME
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPlainTextEdit, QTextBrowser, QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from . import __version__
from .catalog import AppRelease, catalog_document, load_catalog, parse_catalog
from .common import LauncherError, atomic_json, read_json, inside
from .installer import Installer
from .windows_paths import WindowsPathError
from .paths import AppPaths
from .providers import HttpProvider
from .github_provider import GitHubReleasesProvider
from .catalog_trust import CatalogVerifier

DATA = Path(__file__).resolve().parent / "data" / "catalog.json"
ASSETS = Path(__file__).resolve().parent / "assets"
GITHUB_AUTO_MIN_REFRESH = 300
GITHUB_AUTO_REFRESH_MS = 60 * 60 * 1000
GITHUB_RATE_WAIT = 3600
REFRESH_OPERATIONS = {"서버 연결과 업데이트 확인", "GitHub 업데이트 확인"}


class NotesDocument(QTextDocument):
    def loadResource(self, kind, name):
        # Override the document itself: QTextBrowser's hook alone still allows
        # QTextDocument to fall back to opening a local file.
        return None


class ReleaseNotes(QTextBrowser):
    """Formatting only: no remote/local resources and no automatic navigation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDocument(NotesDocument(self))
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.source_text = None

    def loadResource(self, kind, name):
        return None

    def show_notes(self, text):
        if text != self.source_text:
            # Keep the complete signed text in the details dialog. A known
            # build-commit preamble is not useful in the everyday notes view.
            preview = re.sub(r'(?im)^Build source commit:\s*\n\s*`?[0-9a-f]{7,40}`?\s*\n', '', text)
            self.document().setMarkdown(preview, QTextDocument.MarkdownFeature.MarkdownDialectGitHub
                                       | QTextDocument.MarkdownFeature.MarkdownNoHTML)
            self.moveCursor(QTextCursor.MoveOperation.Start)
            self.verticalScrollBar().setValue(0)
            self.source_text = text


class FeedbackLabel(QLabel):
    def setText(self, text):
        super().setText(text)
        self.setVisible(bool(text))


class _TestNoLaunchProcesses:
    """Defense at the actual process boundary, without changing Installer."""
    def __init__(self, processes):
        self.processes = processes

    def __getattr__(self, name):
        return getattr(self.processes, name)

    def start(self, *args, **kwargs):
        raise LauncherError("격리 시험 모드에서는 EXE 실행이 차단됩니다.")


class Task(QThread):
    progress = Signal(int, int)

    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.action = action
        self.cancel = threading.Event()
        self.result = None
        self.error = ""
        self.path_error = False

    def run(self):
        try:
            self.result = self.action(self.progress.emit, self.cancel)
        except Exception as exc:
            self.error = str(exc) or type(exc).__name__
            self.path_error = isinstance(exc, WindowsPathError)


def connection_defaults(config: dict, *, default_repository=""):
    """Infer old LAN settings in memory; never migrate a user's settings on startup."""
    if not isinstance(config,dict):
        raise LauncherError('연결 설정 파일의 형식이 잘못되었습니다. 기존 파일을 자동 변경하지 않습니다.')
    value = dict(config)
    if 'transport' not in value:
        value['transport'] = ('lan' if any(k in value for k in ('server_url','lan_token','lan_enabled'))
                              else 'github')
    if value['transport'] == 'github':
        value.setdefault('github_repository', default_repository)
    return value


class ConnectionDialog(QDialog):
    def __init__(self, config: dict, parent=None, *, legacy=False):
        super().__init__(parent)
        self.original = dict(config)
        self.legacy = legacy
        self.setWindowTitle("배포 연결")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        title = QLabel("팀 도구를 받는 방법")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        intro = QLabel("연결할 수 없어도 이미 설치한 도구는 실행할 수 있습니다.\nGitHub 연결에는 승인된 저장소와 사전 신뢰 공개키가 필요합니다.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.transport = QComboBox()
        if legacy:
            self.transport.addItem("기존 로컬/LAN", "lan")
        self.transport.addItem("GitHub Releases", "github")
        if legacy:
            self.transport.setCurrentIndex(1 if connection_defaults(config)['transport'] == 'github' else 0)
        self.repository = QLineEdit(config.get("github_repository", ""))
        self.repository.setPlaceholderText("OWNER/REPO · 운영 배포 승인 후 지정")
        if legacy:
            form.addRow("배포 방식", self.transport)
        else:
            self.transport.hide()
            form.addRow("배포 방식", QLabel("GitHub Releases"))
            if connection_defaults(config)['transport'] != 'github':
                notice = QLabel("기존 개발용 연결 설정은 유지 중입니다. 저장하면 GitHub 방식으로 전환합니다.")
                notice.setWordWrap(True)
                layout.addWidget(notice)
        form.addRow("GitHub 저장소", self.repository)
        if legacy:
            self.url = QLineEdit(config.get("server_url", "http://127.0.0.1:8765"))
            self.lan = QCheckBox("LAN 연결 사용 (회사 내부의 개발자 PC)")
            self.lan.setChecked(config.get("lan_enabled", False) is True)
            self.token = QLineEdit(config.get("lan_token", ""))
            self.token.setEchoMode(QLineEdit.EchoMode.Password)
            form.addRow("서버 주소", self.url)
            form.addRow("", self.lan)
            form.addRow("LAN 배포 토큰", self.token)
        self.transport.currentIndexChanged.connect(self._route_fields)
        self._route_fields()
        layout.addLayout(form)
        internet = QLabel("GitHub는 HTTPS·카탈로그 전자서명을 사용하며 로그인하지 않습니다.\n운영 신뢰키 미채택 상태에서는 설치·업데이트가 차단됩니다.")
        internet.setWordWrap(True)
        internet.setObjectName("muted")
        layout.addWidget(internet)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _route_fields(self):
        github = self.transport.currentData() == "github"
        self.repository.setEnabled(github)
        if self.legacy:
            for field in (self.url, self.lan, self.token):
                field.setEnabled(not github)

    def values(self):
        value = {**self.original,"transport": self.transport.currentData(),
                 "github_repository": self.repository.text().strip()}
        if self.legacy:
            value.update(server_url=self.url.text().strip(),lan_enabled=self.lan.isChecked(),
                         lan_token=self.token.text())
        if value["transport"] == "github":
            if not value['github_repository']:
                raise LauncherError("운영 배포 저장소가 아직 지정되지 않았습니다. 담당자에게 승인된 GitHub 저장소를 확인하세요.")
            GitHubReleasesProvider(value["github_repository"])
        else:
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
QLabel#brand { color: #faf8ff; font-size: 21px; font-weight: 800; letter-spacing: 2px; background: transparent; }
QLabel#eyebrow { color: #a39bc5; font-size: 11px; letter-spacing: 2px; background: transparent; }
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
QPlainTextEdit, QTextBrowser { background: #171c2e; border: none; color: #cad1e5; padding: 8px; selection-background-color: #6753a4; }
QProgressBar { border: 1px solid #39415a; background: #191e30; border-radius: 6px; min-height: 14px; text-align: center; }
QProgressBar::chunk { background: #8b6be1; border-radius: 5px; }
QLineEdit { padding: 9px; background: #1d2437; border: 1px solid #454e68; border-radius: 5px; }
QDialog { background: #141a2c; }
QToolTip { background: #2d3450; color: #ffffff; border: 1px solid #61547d; padding: 5px; }
"""


class MainWindow(QMainWindow):
    def __init__(self, paths: AppPaths | None = None, *, catalog_path: Path = DATA,
                 auto_connect: bool = True, installer: Installer | None = None,
                 github_repository: str | None = None, github_test_policy: Path | None = None,
                 managed_session=None):
        super().__init__()
        # Qt's offscreen Windows platform has an empty font database. Explicitly
        # load an installed system font for diagnostic renders; don't redistribute it.
        if not QFontDatabase.families():
            for filename in ("C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/segoeui.ttf"):
                if Path(filename).is_file():
                    QFontDatabase.addApplicationFont(filename)
        self.paths = paths or AppPaths.default()
        self.managed_session = managed_session
        self.launcher_candidate = None
        self.launcher_target = None
        self.launcher_verified_version = None
        self._launcher_handoff = False
        self.github_test_mode = github_test_policy is not None
        if self.github_test_mode:
            test_root = Path(__file__).resolve().parents[1] / ".test-results"
            if (paths is None or not paths.root.resolve().is_relative_to(test_root.resolve())
                    or not github_test_policy.resolve().is_relative_to(test_root.resolve())
                    or github_repository != "toast-source/creative-group-releases"
                    or installer is not None and installer.paths.root.resolve() != paths.root.resolve()):
                raise LauncherError("GitHub 시험 키는 명시한 격리 시험 경로와 시험 저장소에서만 사용합니다.")
        self.installer = installer or Installer(self.paths)
        if self.github_test_mode:
            self.installer = Installer(self.paths, _TestNoLaunchProcesses(self.installer.processes))
        self.apps = load_catalog(catalog_path)
        self.verified_catalog_app_ids = set()
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
        self._github_next_check = 0.0
        self._last_catalog_check = None
        self._diagnostic_write_error = ""
        self.catalog_verifier = (CatalogVerifier(read_json(github_test_policy), self.paths.root / "catalog-trust.json")
                                 if self.github_test_mode else CatalogVerifier.bundled(self.paths.root / "catalog-trust.json"))
        from .channel_bridge import BridgedAppVerifier
        legacy_home = getattr(managed_session, "legacy_home", None)
        if legacy_home:
            state_root = managed_session.file.parent if managed_session.mode == "health" else managed_session.updater.home
            self.catalog_verifier = BridgedAppVerifier(
                self.catalog_verifier.policy, inside(state_root, "app-catalog-trust.json"))
        self.installer.catalog_verifier = self.catalog_verifier
        default_repository = ("toast-source/creative-group-releases"
                              if not self.github_test_mode and self.catalog_verifier.policy["keys"] else "")
        self.config = connection_defaults({}, default_repository=default_repository)
        try:
            if (self.paths.root / "settings.json").exists():
                self.config = connection_defaults(read_json(self.paths.root / "settings.json"),
                                                  default_repository=default_repository)
            cached = self.catalog_verifier.cached()
            if cached is not None:
                self.apps = cached
                self.verified_catalog_app_ids = {app.app_id for app in cached}
        except LauncherError as exc:
            self._load_warning = str(exc)
        if github_repository is not None:
            self.config = {**self.config, "transport": "github", "github_repository": github_repository}
        self.apps = [app for app in self.apps if app.app_id != "creative-group-launcher"]
        self._merge_installed()
        self.setWindowTitle(DISPLAY_NAME)
        self.setWindowIcon(QIcon(str(ASSETS / ICON_FILENAME)))
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
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(GITHUB_AUTO_REFRESH_MS)
        self.update_timer.timeout.connect(self._automatic_refresh)
        self.update_timer.start()
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
        wordmark = QLabel("SOUTHPAW")
        wordmark.setObjectName("eyebrow")
        side.addWidget(wordmark)
        brand = QLabel("도구 런처")
        brand.setWordWrap(False)
        brand.setObjectName("brand")
        side.addWidget(brand)
        brand.setToolTip(DISPLAY_NAME + " · " + DESCRIPTION)
        side.addSpacing(32)
        label = QLabel("라이브러리")
        label.setObjectName("muted")
        side.addWidget(label)
        self.list = QListWidget()
        from PySide6.QtCore import QSize
        self.list.setIconSize(QSize(32, 32))
        self.list.currentRowChanged.connect(self.render)
        side.addWidget(self.list, 1)
        footer = QLabel(f"v{__version__}")
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
        if self.managed_session:
            self.connection_button.hide()
        self.launcher_update_button = QPushButton("런처 업데이트")
        self.launcher_update_button.clicked.connect(self.update_launcher)
        self.launcher_update_button.hide()
        top.addWidget(self.launcher_update_button)
        main.addLayout(top)
        self.launcher_versions = QLabel(f"런처 설치 버전 v{__version__} · 최신 버전 미확인")
        self.launcher_versions.setObjectName("muted")
        self.launcher_versions.setWordWrap(True)
        main.addWidget(self.launcher_versions)

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
        self.channel = QLabel("테스트 배포본" if self.github_test_mode else "")
        self.channel.setObjectName("badge")
        self.channel.setVisible(self.github_test_mode)
        note_title.addWidget(self.channel)
        note_layout.addLayout(note_title)
        self.notes = ReleaseNotes()
        note_layout.addWidget(self.notes, 1)
        center.addWidget(notes_card, 1)

        info_card = QFrame()
        info_card.setObjectName("card")
        info_card.setFixedWidth(236)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(18, 20, 18, 20)
        info_layout.setSpacing(2)
        info_title = QLabel("프로그램 정보")
        info_title.setObjectName("sectionTitle")
        info_layout.addWidget(info_title)
        self.info = {}
        for key in ("설치 상태", "설치 버전", "승인 버전", "다운로드", "배포 식별자"):
            label = QLabel("프로그램 최신 버전" if key == "승인 버전" else key)
            if key == "승인 버전":
                self.latest_app_label = label
            label.setObjectName("muted")
            info_layout.addWidget(label)
            value = QLabel("—")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.info[key] = value
            info_layout.addWidget(value)
            if key == "배포 식별자":
                label.hide()
                value.hide()
            info_layout.addSpacing(2)
        info_layout.addStretch()
        self.details_button = QPushButton("상세 정보")
        self.details_button.clicked.connect(self.show_details)
        info_layout.addWidget(self.details_button)
        center.addWidget(info_card)
        main.addLayout(center, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()
        main.addWidget(self.progress)
        self.message = FeedbackLabel()
        self.message.setText(self._load_warning)
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
        self.versions_button = QPushButton("설치된 버전 선택")
        self.versions_button.clicked.connect(self.choose_version)
        actions.addWidget(self.versions_button)
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

    def _github(self):
        return self.config.get("transport") == "github"

    def _automatic_refresh(self):
        if self._github() and time.monotonic() >= self._github_next_check:
            self.refresh()

    def _github_failure(self, message, *, installing=False):
        detail = message
        if "호출 제한" in message or "429" in message:
            state = "GitHub 호출 제한"
            detail = f"GitHub 요청이 제한되었습니다. 잠시 후 다시 확인하세요. {message}"
            self._github_next_check = max(self._github_next_check, time.monotonic() + GITHUB_RATE_WAIT)
        elif '404' in message:
            state = '저장소 또는 Release를 찾을 수 없음'
        elif not self.catalog_verifier.policy['keys'] and '알 수 없는 카탈로그 서명 키' in message:
            state = '운영 키 미채택'
            detail = '현재 배포물을 설치할 수 없습니다. 운영 신뢰키 승인이 필요합니다.'
        elif any(word in message for word in ("서명", "공개키", "순번", "재전송")):
            state = "서명 검증 실패"
            detail = f"신뢰할 수 없는 배포 정보입니다. 설치·업데이트를 중단했습니다. {message}"
        elif "403" in message:
            state = "GitHub 접근 거부"
        elif any(word in message for word in ("네트워크", "HTTPS")):
            state = "인터넷 연결 실패"
            detail = f"인터넷 또는 네트워크 연결을 확인하세요. {message}"
        elif installing:
            state = "패키지 검증 실패" if any(word in message for word in ("SHA-256", "크기", "ZIP")) else "설치 실패"
        else:
            state = "목록 확인 실패"
        self.online = False
        self.server_state = state
        if not installing:
            self.catalog_state, self.catalog_error = state, detail
        self.message.setText(f"{state}: {detail}")

    def render(self, *_):
        busy = self.task is not None or self._launcher_handoff
        self.refresh_button.setEnabled(not busy)
        self.connection_button.setEnabled(not busy)
        self.launcher_update_button.setEnabled(not busy and self.online)
        app = self.selected()
        if not app:
            return
        self.title.setText(app.display_name)
        self.description.setText(app.description)
        self._show_app_icon(app)
        text = app.release_notes or "등록된 릴리즈 노트가 없습니다."
        self.notes.show_notes(text)
        self.latest_app_label.setText("프로그램 최신 버전" if self.online else "프로그램 등록 버전")
        self.info["승인 버전"].setText(app.version)
        self.info["다운로드"].setText(f"{app.package_size / 1024**2:.1f} MB" if app.published else "배포 패키지 미확인")
        self.info["배포 식별자"].setText(app.release_id)
        error, catalog_error = "", self.catalog_error
        installed, running, update = None, False, False
        pending, pinned = False, False
        try:
            pending = self.installer.pending_recovery(app.app_id)
            installed = self.installer.installed(app.app_id)
            running = bool(installed) and self._app_running(app.app_id)
            if installed:
                pinned = self.installer.selection_pinned(app.app_id)
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
        self.info["설치 버전"].setToolTip(installed.release_id if installed else "")
        can_install = self.online and app.published and not catalog_error
        repair = bool(installed and error)
        can_repair = can_install and bool(update or app == installed)
        running_status = "실행 중 · 업데이트 보류" if update else "실행 중"
        status = running_status if running else "복구 필요" if error or pending else "설치 완료 · 목록 오류(업데이트 차단)" if installed and catalog_error else "업데이트 가능" if update else "설치 완료" if installed else "미설치"
        if self._github() and not (running or error or pending or catalog_error):
            if busy and self.operation in REFRESH_OPERATIONS:
                status = "업데이트 확인 중"
            elif not installed:
                status = "설치 필요"
            elif self.online and not update:
                status = "최신 버전"
        if pinned and update and not (running or error or pending or catalog_error):
            status = "이전 버전 사용 중 · 업데이트 가능"
        self.info["설치 상태"].setText(status)
        self.primary.setText("작업 중…" if busy else "실행 중" if running else "복구 확인" if pending else "복구 설치" if repair else "업데이트" if installed and update and can_install else "실행" if installed else "설치" if app.published else "패키지 미확인")
        self.primary.setEnabled(not busy and not running and (pending or (can_repair if error else bool(installed or can_install))))
        self.primary.setToolTip("" if app.published else app.availability_reason)
        self.folder_button.setEnabled(not busy and self.paths.app(app.app_id).exists())
        self.remove_button.setEnabled(not busy and bool(installed) and not running)
        self.versions_button.setEnabled(not busy and bool(installed) and not running and not pending)
        self.launch_current.setVisible(bool(installed and update and can_install and not error))
        self.launch_current.setEnabled(not busy and not running and not error)
        if self.github_test_mode:
            self.launch_current.hide()
            self.launch_current.setEnabled(False)
            if installed and not (pending or repair or update and can_install):
                self.primary.setText("시험 실행 차단")
                self.primary.setEnabled(False)
        if error:
            self.message.setText(f"복구 필요: {error}")
        elif catalog_error:
            self.message.setText(f"목록 오류 — 설치/업데이트 차단, 로컬 실행 가능: {catalog_error}")
        elif not app.published and not installed and not busy:
            self.message.setText(app.availability_reason or "배포 패키지 미확인")

    def _app_running(self, app_id):
        return self.installer.is_running(app_id)

    def _show_app_icon(self, app):
        self.hero_icon.setPixmap(app_icon(app, 72).pixmap(72, 72))

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
        failed = bool(task.error)
        if task.error:
            self.message.setText(task.error)
            if self.operation in REFRESH_OPERATIONS:
                self.online = False
                self.server_state = "오프라인 · 접속 실패"
                if self._github():
                    self._github_failure(task.error)
            elif task.path_error:
                self.package_state = "설치 경로 제한"
            elif self.operation.startswith(("설치:", "업데이트:", "복구 설치:")):
                self.package_state = "수신 검증 성공 · 설치 실패" if self.installer.download_verified else "다운로드/검증 실패"
                self.server_state = "재확인 필요"
                self.online = False  # Require fresh catalog validation for the next install.
                if self._github():
                    self._github_failure(task.error, installing=True)
        else:
            try:
                success(task.result)
            except Exception as exc:
                failed = True
                self.message.setText(str(exc))
                if self.operation in REFRESH_OPERATIONS:
                    self.online = False
                    self.catalog_state = "오류"
                    self.catalog_error = str(exc)
                    if self._github():
                        self._github_failure(str(exc))
        if self.operation.startswith(("설치:", "업데이트:", "복구 설치:")) and not task.error:
            self.package_state = "다운로드·검증 성공"
        if self.installer.warnings and self.operation not in REFRESH_OPERATIONS:
            self.message.setText(self.message.text() + "\n경고: " + " / ".join(self.installer.warnings))
        self._connection_status()
        if self.operation in REFRESH_OPERATIONS:
            self._last_catalog_check = {'at_utc': datetime.now(timezone.utc).isoformat(),
                                        'result': 'verified' if self.online and not self.catalog_error else 'failed'}
        # A bounded, sanitized snapshot for offline CLI diagnostics. Diagnostic
        # write failures never change install results or suppress their errors.
        try:
            diagnostic_path = (inside(self.managed_session.file.parent, 'gui-status.json')
                               if self.managed_session else
                               inside(self.paths.root, f'diagnostics/gui-{os.getpid()}.json'))
            atomic_json(diagnostic_path, {
                'schema_version': 1, 'version': __version__,
                'updated_at_utc': datetime.now(timezone.utc).isoformat(),
                'last_catalog_check': self._last_catalog_check,
                'last_operation': self.operation.split(':', 1)[0],
                'result': 'failed' if failed or self.catalog_error else 'completed',
            })
        except (OSError, LauncherError) as exc:
            self._diagnostic_write_error = type(exc).__name__
        task.deleteLater()
        self.render()

    def cancel_task(self):
        if self.task:
            self.task.cancel.set()
            self.cancel_button.setEnabled(False)
            self.message.setText("현재 전송 종료 후 취소합니다. 기존 설치는 유지됩니다.")

    def _github_provider(self):
        repository = self.config.get("github_repository", "")
        binding = (self.managed_session.channel.get("repository_id")
                   if self.managed_session and repository == self.managed_session.channel["repository"] else None)
        return GitHubReleasesProvider(repository, verifier=self.catalog_verifier, repository_id=binding)

    def refresh(self):
        if getattr(self, "bridge_fallback", False):
            self.message.setText("런처를 다시 열면 Rod 연결을 재시도합니다.")
            return
        if self.task or self._launcher_handoff:
            return
        self.launcher_candidate = None
        self.launcher_target = None
        self.launcher_verified_version = None
        self.launcher_update_button.hide()
        self.launcher_versions.setText(f"런처 설치 버전 v{__version__} · 최신 버전 미확인")
        github = self._github()
        repository = self.config.get('github_repository')
        if github and (repository is None or isinstance(repository,str) and not repository.strip()):
            self.online = False
            self.provider = None
            self.server_state = '배포 설정 대기'
            self.catalog_state = '운영 저장소 미지정'
            self.catalog_error = '운영 배포 저장소가 아직 지정되지 않았습니다. 담당자에게 승인된 GitHub 저장소를 확인하세요.'
            self._connection_status()
            self.render()
            return
        try:
            if github:
                provider = self._github_provider()
                self._github_next_check = max(self._github_next_check, time.monotonic() + GITHUB_AUTO_MIN_REFRESH)
            else:
                provider = HttpProvider(self.config.get("server_url", "http://127.0.0.1:8765"),
                                        self.config.get("lan_token", ""),
                                        lan_enabled=self.config.get("lan_enabled", False) is True,
                                        verifier=self.catalog_verifier)
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
            if github:
                try:
                    apps = provider.catalog()
                except OSError:
                    return {"transport": "github-releases"}, None, "GitHub 네트워크 응답을 읽지 못했습니다.", None
                except (LauncherError, ValueError) as exc:
                    return {"transport": "github-releases"}, None, str(exc) or "GitHub 목록 확인 실패", None
                launcher = next((a for a in apps if a.app_id == "creative-group-launcher"), None)
                return {"transport": "github-releases"}, apps, "", self._rod_target(launcher)
            health = provider.health()
            try:
                return health, provider.catalog(), "", None
            except Exception as exc:
                return health, None, str(exc) or "네트워크 응답 시간 초과", None

        def connected(result):
            health, apps, catalog_error, target = result
            self.health = health
            self.last_checked = datetime.now().strftime("%H:%M:%S")
            self.server_state = "응답 확인(마지막 조회)"
            if catalog_error:
                self.catalog_state, self.catalog_error = "실패", catalog_error
                self.online = False
                self.message.setText(f"카탈로그 조회 실패: {catalog_error}")
                if github:
                    self._github_failure(catalog_error)
                return
            selected = self.selected().app_id if self.selected() else None
            launcher = next((app for app in apps if app.app_id == "creative-group-launcher"), None)
            apps = [app for app in apps if app.app_id != "creative-group-launcher"]
            # Reject immutable-release identity changes before accepting the catalog.
            old = {app.app_id: app for app in self.apps}
            for app in apps:
                if app.app_id in old and old[app.app_id].published and app.published:
                    app.is_new_release(old[app.app_id])
                installed = self.installer.installed(app.app_id)
                if installed and app.published:
                    app.is_new_release(installed)
            self.health, self.apps, self.provider, self.online = health, apps, provider, True
            self.verified_catalog_app_ids = {app.app_id for app in apps}
            self.catalog_state, self.catalog_error = "전자서명·순번 검증 성공", ""
            self._merge_installed()
            self.message.setText("")
            self._populate(selected)
            if self.managed_session and launcher and launcher.published:
                newer = self.managed_session.newer(launcher)
                if self._is_bridge_update(launcher):
                    destination = f"Rod 최신 v{target}" if target else "Rod 최신 버전 미확인"
                    latest = f"{destination} · 전환 단계 v{launcher.version}"
                else:
                    latest = f"런처 최신 버전 v{launcher.version}"
                    self.launcher_verified_version = launcher.version
                self.launcher_versions.setText(f"런처 설치 버전 v{__version__} · {latest}")
                if newer:
                    self.launcher_candidate = launcher
                    self.launcher_target = target
                    label = "Rod 채널로 업데이트" if self._is_bridge_update(launcher) else "런처 업데이트"
                    self.launcher_update_button.setText(label)
                    self.launcher_update_button.show()

        self.online = False
        self.server_state = "업데이트 확인 중" if github else "확인 중"
        self._connection_status()
        self._begin("GitHub 업데이트 확인" if github else "서버 연결과 업데이트 확인", fetch, connected)

    def _is_bridge_update(self, launcher):
        from .channel_bridge import TOAST
        return (self._github() and self.managed_session and self.managed_session.channel["repository"] == TOAST
                and self.config.get("github_repository") == TOAST
                and launcher is not None and launcher.published
                and launcher.release_id.startswith("toast-bridge-"))

    def _rod_target(self, launcher):
        if not self._is_bridge_update(launcher):
            return None
        from .channel_bridge import MINIMUM_BRIDGE_SEQUENCE
        from .github_channels import CANONICAL_CATALOG_ID, CANONICAL_REPOSITORY, CANONICAL_REPOSITORY_ID
        from .self_update import version
        policy = {**self.managed_session.channel["policy"], "catalog_id": CANONICAL_CATALOG_ID,
                  "minimum_sequence": MINIMUM_BRIDGE_SEQUENCE}
        try:
            preview = inside(self.managed_session.updater.home, "rod-preview-trust.json")
            verifier = CatalogVerifier(policy, preview)
            provider = GitHubReleasesProvider(CANONICAL_REPOSITORY, repository_id=CANONICAL_REPOSITORY_ID,
                                              verifier=verifier)
            target = next((a for a in provider.catalog() if a.app_id == "creative-group-launcher" and a.published), None)
            if target and version(target.version) >= (0, 1, 7):
                return target.version
        except (LauncherError, OSError, ValueError):
            # The preview is informational; the actual Bridge verifies again.
            pass
        return None

    def _ask(self, title, message, *, default_no=False):
        buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        default = QMessageBox.StandardButton.No if default_no else QMessageBox.StandardButton.Yes
        return QMessageBox.question(self, title, message, buttons, default) == QMessageBox.StandardButton.Yes

    def _choose_item(self, title, message, choices):
        label, accepted = QInputDialog.getItem(self, title, message, choices, 0, False)
        return label if accepted else None

    def update_launcher(self):
        session, candidate = self.managed_session, self.launcher_candidate
        if not session or not candidate or not self.online or self.task or self._launcher_handoff:
            return
        if self._is_bridge_update(candidate):
            target = f"Rod v{self.launcher_target}" if self.launcher_target else "Rod 채널 · 최신 버전 확인 필요"
            change = f"설치 v{session.current.version} → {target}\n전환 단계 v{candidate.version}을 자동 적용합니다."
        else:
            change = f"설치 v{session.current.version} → 최신 v{candidate.version}"
        if not self._ask("런처 업데이트",
                         f"{change}\n업데이트를 검증한 후 런처를 재시작합니다. 설치 앱과 사용자 데이터는 유지됩니다."):
            return

        def prepared(transaction):
            session.handoff(transaction)
            self._launcher_handoff = True
            from PySide6.QtWidgets import QApplication
            QTimer.singleShot(0, lambda: QApplication.instance().exit(20))

        self._begin("런처 업데이트 준비", lambda progress, cancel: session.prepare(candidate, cancel), prepared)

    def _connection_status(self):
        if self._github():
            mode = " · 격리 시험 모드" if self.github_test_mode else ""
            state = "업데이트 확인 완료" if self.online and not self.catalog_error else self.server_state
            self.server_status.setText(f"{state}{mode}")
            self.server_status.setToolTip(f"GitHub · {self.config.get('github_repository') or '운영 저장소 미지정'}\n"
                                          f"확인 {self.last_checked} · {self.catalog_state}\n"
                                          f"패키지: {self.package_state} · 자동 1시간 / 수동 확인 시 다시 조회")
            return
        try:
            host = urllib.parse.urlsplit(self.config.get("server_url", "http://127.0.0.1:8765")).hostname
            route = "로컬(loopback)" if host == "localhost" or ipaddress.ip_address(host).is_loopback else f"LAN({host})"
        except (ValueError, TypeError):
            route = "미확인"
        lan = ("ON" if self.health.get("lan_enabled") else "OFF") if self.health else "미확인"
        self.server_status.setText(f"서버: {self.server_state} · 경로: {route} · 확인 {self.last_checked}\n"
                                   f"목록: {self.catalog_state} · 패키지: {self.package_state} · 서버 LAN: {lan}(마지막 조회) / 인터넷 미구성")

    def show_details(self):
        app = self.selected()
        if not app:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("프로그램 상세 정보")
        dialog.resize(560, 400)
        layout = QVBoxLayout(dialog)
        details = QPlainTextEdit()
        details.setReadOnly(True)
        details.setPlainText(f"{app.display_name}\n앱 ID: {app.app_id}\n릴리스 ID: {app.release_id}\n"
                             f"패키지 SHA-256: {app.sha256}\n\n"
                             f"연결: {self.server_status.text()}\n{self.server_status.toolTip()}\n"
                             f"목록: {self.catalog_state}\n패키지: {self.package_state}\n\n"
                             f"진단 기록 쓰기: {self._diagnostic_write_error or '정상'}\n\n"
                             f"릴리스 노트 원문\n{app.release_notes}")
        layout.addWidget(details)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dialog.reject)
        layout.addWidget(close)
        dialog.exec()

    def configure(self):
        if getattr(self, "bridge_fallback", False):
            return
        if self.managed_session and self.managed_session.channel.get("repository_id") is not None:
            self.message.setText("Rod 운영 채널이 관리하는 연결입니다.")
            return
        dialog = ConnectionDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                config = dialog.values()
                if self.github_test_mode and (config.get("transport") != "github" or config.get("github_repository") != "toast-source/creative-group-releases"):
                    raise LauncherError("격리 시험 모드의 저장소는 변경할 수 없습니다.")
                atomic_json(self.paths.root / "settings.json", config)
                self.config = config
                self._github_next_check = 0.0
                self.provider = None
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
                raise LauncherError("GitHub 연결과 서명된 배포 목록을 확인하세요." if self._github()
                                    else "서버 연결과 승인 배포 패키지를 확인하세요.")
            retained_latest = bool(update and app in self.installer.retained_versions(app.app_id))
            title = "설치된 최신 버전으로 전환" if retained_latest else "복구 설치" if local_error else "업데이트" if installed else "설치"
            text = f"{app.display_name} {app.version}을(를) {title}할까요?"
            if retained_latest:
                text += "\n선택한 버전은 그 폴더에 보존된 기존 설정과 작업 파일을 사용합니다."
            elif installed:
                text += "\n기존 버전은 보존하고, 등록된 사용자 설정을 새 버전으로 복사합니다."
            if not self._ask(title, text, default_no=True):
                return
            provider = self.provider
            self.cancel_button.setEnabled(True)
            def install(progress, cancel):
                if retained_latest:
                    return self.installer.select_release(app.app_id, app.release_id, pinned=False,
                                                         expected_current=installed, expected_release=app,
                                                         cancel=cancel)
                if isinstance(provider, GitHubReleasesProvider):
                    with provider.installation_session(app):
                        return self.installer.install(app, provider, progress, cancel)
                return self.installer.install(app, provider, progress, cancel)
            self._begin(f"{title}: {app.display_name}",
                        install,
                        lambda result: self.message.setText(f"{result.display_name} {title} 완료. " +
                            ("시험 모드에서는 EXE 실행 차단을 유지합니다." if self.github_test_mode
                             else "실행 버튼으로 시작하세요.")))
        except LauncherError as exc:
            self.message.setText(str(exc))

    def choose_version(self):
        app = self.selected()
        if app is None or self.task is not None:
            return
        try:
            current = self.installer.installed(app.app_id)
            if current is None or self.installer.is_running(app.app_id):
                return
            choices = [item for item in self.installer.retained_versions(app.app_id) if item != current]
            if not choices:
                self.message.setText("전환할 수 있는 설치 버전이 없습니다. 설치 시 보관된 서명 목록과 원본 ZIP이 필요합니다.")
                return
            labels = [f"{item.version} · {item.release_id}" for item in choices]
            label = self._choose_item("설치된 버전 선택",
                                      f"현재 버전: {current.version} · {current.release_id}", labels)
            if label is None:
                return
            target = choices[labels.index(label)]
            if self._ask("버전 전환",
                f"{label}로 전환할까요?\n각 버전의 작업 파일과 설정은 현재 위치에 보존됩니다. "
                "선택한 버전은 그 폴더의 기존 데이터를 사용합니다.\n"
                "공용 작업 파일은 그대로 유지됩니다. 버전 간 호환성을 확인한 뒤 여세요.", default_no=True):
                self._begin("버전 전환", lambda progress, cancel: self.installer.select_release(
                    app.app_id, target.release_id, pinned=not app.published or target != app,
                    expected_current=current, expected_release=target, cancel=cancel),
                    lambda result: self.message.setText(f"활성 버전: {result.version} · {result.release_id}"))
        except (LauncherError, OSError) as exc:
            self.message.setText(str(exc))

    def launch(self):
        if self.github_test_mode:
            self.message.setText("격리 시험 모드에서는 EXE 실행이 차단됩니다.")
            return
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
        if not self._ask("프로그램 제거", text, default_no=True):
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
        if getattr(self, "bridge_in_progress", False):
            event.ignore()
            return
        if self.task:
            self.task.cancel.set()
            self.message.setText("작업 취소/정리가 끝난 뒤 닫아 주세요. 기존 프로그램은 종료하지 않습니다.")
            event.ignore()
        else:
            self.timer.stop()
            self.update_timer.stop()
            event.accept()
