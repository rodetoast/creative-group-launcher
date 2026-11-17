"""Local-only administrator UI. Production publication is deliberately locked."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFontDatabase
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget)

from .admin_gui_model import APP_NAMES, PROJECT, AdminSession, Inspection, Review
from .common import LauncherError
from .ui import STYLE, Task
from .admin_github import GhCliTransport, GitHubPublication, REPOSITORY


class ReviewDialog(QDialog):
    def __init__(self, review: Review, parent=None):
        super().__init__(parent)
        self.setWindowTitle("더미 릴리스 최종 확인")
        self.resize(740, 600)
        layout = QVBoxLayout(self)
        box = QPlainTextEdit()
        box.setReadOnly(True)
        item = review.inspection.app
        box.setPlainText(
            f"격리 시험 저장소에만 게시합니다. EXE는 실행하지 않습니다.\n\n"
            f"저장소: {review.repository}\nZIP 파일: {review.inspection.source.name}\n\n"
            f"앱: {item.display_name} ({item.app_id})\n"
            f"이전 릴리스: {review.previous_release} / {review.previous_version}\n"
            f"이전 ZIP SHA256: {review.previous_sha256 or '미게시'}\n새 릴리스: {item.release_id}\n"
            f"표시 버전: {item.version}\n카탈로그 순번: {review.sequence}\n"
            f"ZIP 크기: {item.package_size:,} 바이트\nZIP SHA256: {item.sha256}\n"
            f"EXE: {item.executable_relative_path}\nEXE SHA256: {item.executable_sha256}\n"
            f"서명 공개키 ID: {review.key_id}\n\n릴리스 노트:\n{item.release_notes}")
        layout.addWidget(box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("확인한 더미 릴리스 게시")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("취소")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class AdminWindow(QMainWindow):
    def __init__(self, root: Path = PROJECT / "distribution", *, test_mode=False, github_transport=None):
        super().__init__()
        if not QFontDatabase.families():
            for filename in ("C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/segoeui.ttf"):
                if Path(filename).is_file():
                    QFontDatabase.addApplicationFont(filename)
        self.session = AdminSession(root, test_mode=test_mode)
        self.app_names = self.session.app_names
        self.github_transport = github_transport or GhCliTransport()
        self.github_job = None
        self.inspection: Inspection | None = None
        self.key_path: Path | None = None
        self.task: Task | None = None
        self.setWindowTitle("Creative Group Launcher · 관리자 배포")
        self.resize(1180, 880)
        self.setMinimumSize(900, 650)
        self.setStyleSheet(STYLE)
        outer = QWidget()
        layout = QVBoxLayout(outer)
        self.banner = QLabel("격리 더미 시험 모드 · 실제 프로그램 게시 금지" if test_mode
                             else "운영 키 미채택 · 실제 운영 게시 잠금 · 저장소 조회와 ZIP 검사만 가능")
        self.banner.setWordWrap(True)
        layout.addWidget(self.banner)
        row = QHBoxLayout()
        self.repository = QLineEdit(str(self.session.root))
        self.repository.setReadOnly(True)
        self.repository.setCursorPosition(0)
        self.repository.setToolTip(str(self.session.root))
        self.choose_root = QPushButton("저장소 선택")
        self.choose_root.setEnabled(not test_mode)
        self.choose_root.clicked.connect(self.select_root)
        self.refresh_button = QPushButton("상태 새로고침")
        self.refresh_button.clicked.connect(self.reload)
        row.addWidget(self.repository, 1)
        row.addWidget(self.choose_root)
        row.addWidget(self.refresh_button)
        layout.addLayout(row)
        self.catalog_status = QLabel()
        self.catalog_status.setWordWrap(True)
        layout.addWidget(self.catalog_status)
        splitter = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.apps = QComboBox()
        for identity, name in self.app_names.items():
            self.apps.addItem(name, identity)
        left_layout.addWidget(QLabel("등록 프로그램"))
        left_layout.addWidget(self.apps)
        self.current = QPlainTextEdit()
        self.current.setReadOnly(True)
        self.current.setMaximumHeight(210)
        left_layout.addWidget(self.current)
        splitter.addWidget(left)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        panel = QWidget()
        body = QVBoxLayout(panel)
        release = QGroupBox("새 릴리스 · 완성 ZIP만 선택")
        form = QFormLayout(release)
        self.app_id = QLineEdit()
        self.app_id.setReadOnly(True)
        self.version = QLineEdit()
        self.release_id = QLineEdit()
        self.executable = QLineEdit()
        self.sequence = QLineEdit()
        self.zip_label = QLineEdit("선택하지 않음")
        self.zip_label.setReadOnly(True)
        self.zip_path: Path | None = None
        self.zip_button = QPushButton("승인된 완성 ZIP 선택")
        self.zip_button.clicked.connect(self.select_zip)
        self.key_label = QLabel("개인키 선택 안 됨 · 저장하지 않음")
        self.key_button = QPushButton("외부 서명키 선택")
        self.key_button.clicked.connect(self.select_key)
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText("이번 릴리스의 변경 내용을 입력하세요.")
        self.notes.setMaximumHeight(140)
        for title, control in [("앱 ID",self.app_id),("표시 버전",self.version),
                               ("새 릴리스 ID",self.release_id),("EXE 상대 경로",self.executable),
                               ("새 카탈로그 순번",self.sequence),("ZIP 파일",self.zip_label),
                               ("",self.zip_button),("서명키",self.key_label),("",self.key_button),
                               ("릴리스 노트",self.notes)]:
            form.addRow(title,control)
        body.addWidget(release)
        self.approved = QCheckBox("선택한 ZIP이 승인된 완성본임을 확인했습니다.")
        self.approved.setToolTip("자동 계산한 해시만으로 승인 여부를 판단하지 않습니다.")
        body.addWidget(self.approved)
        actions = QHBoxLayout()
        self.inspect_button = QPushButton("ZIP 검사")
        self.inspect_button.clicked.connect(self.inspect_selected)
        self.publish_button = QPushButton("게시 전 최종 확인")
        self.publish_button.clicked.connect(self.request_publish)
        actions.addWidget(self.inspect_button)
        actions.addWidget(self.publish_button)
        body.addLayout(actions)
        self.github_mode = QCheckBox("GitHub Releases 시험 흐름 · " + ("모의 CLI" if self.github_transport.dry_run else "초안 전송만"))
        self.github_mode.setEnabled(test_mode and self.github_transport.draft_enabled)
        self.github_mode.setToolTip("모의 어댑터 또는 명시적으로 승인된 Dummy Draft 전송만 허용합니다. 정식 공개는 잠겨 있습니다.")
        self.github_mode.toggled.connect(self._github_mode_changed)
        body.addWidget(self.github_mode)
        scope = "승인된 Draft만 · 정식 공개 잠금" if self.github_transport.draft_grant else "실제 외부 게시 잠금"
        body.addWidget(QLabel(f"고정 대상: {REPOSITORY} · {scope}"))
        self.github_assets = QPlainTextEdit()
        self.github_assets.setReadOnly(True)
        self.github_assets.setMaximumHeight(110)
        self.github_assets.setPlaceholderText("서명 묶음 준비 후 전체 자산 이름·크기·SHA-256을 확인합니다.")
        body.addWidget(self.github_assets)
        github_actions = QHBoxLayout()
        self.github_draft = QPushButton("1. 초안 생성")
        self.github_upload = QPushButton("2. 자산 업로드")
        self.github_verify = QPushButton("3. 재다운로드 검증")
        self.github_public = QPushButton("4. 공개 최종 확인")
        for button in (self.github_draft,self.github_upload,self.github_verify,self.github_public):
            github_actions.addWidget(button)
        body.addLayout(github_actions)
        self.github_draft.clicked.connect(self.request_github_draft)
        self.github_upload.clicked.connect(lambda:self._github_step('자산 업로드',lambda:self.github_job.upload()))
        self.github_verify.clicked.connect(lambda:self._github_step('재다운로드 검증',lambda:self.github_job.verify()))
        self.github_public.clicked.connect(self.request_github_public)
        self.inspection_text = QPlainTextEdit()
        self.inspection_text.setReadOnly(True)
        self.inspection_text.setMinimumHeight(180)
        left_layout.addWidget(QLabel("ZIP 검사 결과"))
        left_layout.addWidget(self.inspection_text,1)
        scroll.setWidget(panel)
        splitter.addWidget(scroll)
        splitter.setSizes([280,800])
        layout.addWidget(splitter,1)
        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        self.result.setMaximumHeight(140)
        layout.addWidget(self.result)
        self.busy = QProgressBar()
        self.busy.setRange(0,0)
        self.busy.hide()
        layout.addWidget(self.busy)
        self.setCentralWidget(outer)
        self.panel = panel
        self.apps.currentIndexChanged.connect(self.select_app)
        for field in (self.version,self.release_id,self.executable):
            field.textChanged.connect(self.invalidate)
        self.notes.textChanged.connect(self.invalidate)
        self.sequence.textChanged.connect(self._clear_github)
        self.approved.toggled.connect(self._clear_github)
        self.reload()

    def invalidate(self, *_):
        self.inspection = None
        self.publish_button.setEnabled(False)
        self._clear_github()

    def _clear_github(self, *_):
        self.github_job = None
        self._github_buttons()

    def _github_mode_changed(self, *_):
        self._clear_github()
        self.publish_button.setText("서명 묶음 준비" if self.github_mode.isChecked() else "게시 전 최종 확인")

    def _github_buttons(self):
        phase = self.github_job.phase if self.github_job else 'empty'
        for button,expected in ((self.github_draft,'prepared'),(self.github_upload,'draft'),
                                (self.github_verify,'uploaded'),(self.github_public,'verified')):
            button.setEnabled(bool(self.github_mode.isChecked() and self.session.test_mode
                                   and self.github_transport.draft_enabled and phase==expected
                                   and (button is not self.github_public or self.github_transport.dry_run)))

    def reload(self):
        self.invalidate()
        try:
            self.state = self.session.state()
            self.catalog_status.setText(f"현재 순번 {self.state.sequence} · {self.state.signature_message}")
            self.select_app()
        except Exception as exc:
            self.state = None
            self.catalog_status.setText("카탈로그 읽기 실패 · 게시 차단")
            self.current.setPlainText("이 저장소의 카탈로그를 읽을 수 없습니다.")
            self.result.setPlainText(self.session.safe_error(exc))
            self.inspect_button.setEnabled(False)

    def select_app(self, *_):
        self.invalidate()
        identity = self.apps.currentData()
        self.app_id.setText(identity)
        item = next((a for a in self.state.apps if a.app_id == identity),None) if self.state else None
        self.current.setPlainText((f"{self.app_names[identity]}\n현재 릴리스: {item.release_id}\n"
                                  f"표시 버전: {item.version}\n게시: {'예' if item.published else '아니오'}\n"
                                  f"ZIP SHA256: {item.sha256 or '없음'}") if item else "저장소에 등록되지 않은 앱")
        self.version.setText(item.version if item else "")
        self.release_id.clear()
        self.executable.setText(item.executable_relative_path if item else "")
        self.sequence.setText(str(self.state.sequence+1) if self.state else "")
        self.notes.clear()
        self.approved.setChecked(False)
        self.zip_path = None
        self.zip_label.setText("선택하지 않음")
        self.inspection_text.clear()
        blocked = identity == "tag-master"
        self.zip_button.setEnabled(bool(item) and not blocked)
        self.inspect_button.setEnabled(bool(item) and not blocked)
        if blocked:
            self.inspection_text.setPlainText("원본 승인 ZIP 미확인: AsepriteTagMaster 실제 배포는 비활성화돼 있습니다.")

    def select_root(self):
        value = QFileDialog.getExistingDirectory(self,"배포 저장소 선택")
        if value:
            self.session = AdminSession(Path(value))
            self.repository.setText(str(self.session.root))
            self.repository.setCursorPosition(0)
            self.repository.setToolTip(str(self.session.root))
            self.key_path = None
            self.key_label.setText("개인키 선택 안 됨 · 저장하지 않음")
            self.reload()

    def select_zip(self):
        value,_ = QFileDialog.getOpenFileName(self,"승인된 완성 ZIP 선택","","ZIP (*.zip)")
        if value:
            self.zip_path = Path(value)
            self.zip_label.setText(self.zip_path.name)
            self.approved.setChecked(False)
            self.invalidate()

    def select_key(self):
        value,_ = QFileDialog.getOpenFileName(self,"공개 저장소 밖의 서명 개인키 선택","","PEM (*.pem);;모든 파일 (*)")
        if value:
            self.key_path = Path(value)
            self.key_label.setText("개인키 선택됨 · 메모리에서만 사용")
            self._clear_github()

    def _start(self, title, action, success):
        if self.task:
            return
        self.result.setPlainText(title)
        self.panel.setEnabled(False)
        self.apps.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.choose_root.setEnabled(False)
        self.busy.show()
        task = Task(lambda progress,cancel: action(),self)
        self.task = task
        def finished():
            self.task = None
            self.panel.setEnabled(True)
            self.apps.setEnabled(True)
            self.refresh_button.setEnabled(True)
            self.choose_root.setEnabled(not self.session.test_mode)
            self.busy.hide()
            if task.error:
                self.invalidate()
                self.result.setPlainText(f"{title} 실패: {self.session.safe_error(task.error)}")
                try:
                    self.state = self.session.state()
                    self.catalog_status.setText(f"실제 순번 {self.state.sequence} · {self.state.signature_message}")
                    current=next((a for a in self.state.apps if a.app_id==self.apps.currentData()),None)
                    if current:
                        self.current.setPlainText(f"{self.app_names[current.app_id]}\n실제 릴리스: {current.release_id}\n"
                            f"표시 버전: {current.version}\n게시: {'예' if current.published else '아니오'}\n"
                            f"ZIP SHA256: {current.sha256 or '없음'}")
                except Exception:
                    self.catalog_status.setText("실제 카탈로그 재조회 실패 · 수동 확인 필요")
            else:
                success(task.result)
            self._github_buttons()
            task.deleteLater()
        task.finished.connect(finished)
        task.start()

    def inspect_selected(self):
        if self.task:
            return
        if self.zip_path is None:
            self.result.setPlainText("승인된 완성 ZIP을 먼저 선택하세요.")
            return
        values=(self.zip_path,self.apps.currentData(),self.version.text().strip(),
                self.release_id.text().strip(),self.executable.text().strip(),self.notes.toPlainText())
        def accepted(inspection):
            self.inspection = inspection
            item = inspection.app
            listing = "\n".join(inspection.members[:200])
            self.inspection_text.setPlainText(f"ZIP 검사 통과 · {len(inspection.members)}개 항목\n"
                f"압축 크기 {item.package_size:,} / 해제 크기 {inspection.expanded_size:,} 바이트\n"
                f"ZIP SHA256: {item.sha256}\nEXE SHA256: {item.executable_sha256}\n"
                f"경로·CRC·MZ·필수 리소스 검사 통과\n\n{listing}")
            self.result.setPlainText("검사 완료. 승인 확인·키·순번을 확인한 뒤 최종 확인을 진행하세요.")
            self.publish_button.setEnabled(self.session.test_mode)
        self._start("ZIP 읽기 전용 검사",lambda:self.session.inspect(*values),accepted)

    def confirm(self, review):
        return ReviewDialog(review,self).exec() == QDialog.DialogCode.Accepted

    def request_publish(self):
        if self.task:
            return
        try:
            if self.inspection is None:
                raise LauncherError("현재 입력으로 ZIP 검사를 먼저 완료하세요.")
            values=(self.inspection,self.sequence.text().strip(),self.key_path,self.approved.isChecked())
            def reviewed(review):
                if not self.confirm(review):
                    self.result.setPlainText("게시를 취소했습니다. 저장소는 변경하지 않았습니다.")
                    return
                if self.github_mode.isChecked():
                    job = GitHubPublication(self.session,self.github_transport)
                    def prepared(result):
                        self.github_job = result
                        mode = "DRY-RUN" if self.github_transport.dry_run else "실제 Draft 전용 · 정식 공개 금지"
                        self.github_assets.setPlainText(f"{mode} · {REPOSITORY} · {result.tag}\n" + '\n'.join(
                            f"{a.name} · {a.size:,} 바이트 · SHA-256 {a.sha256}" for a in result.assets))
                        self.result.setPlainText("서명 묶음 준비 완료. 원본 카탈로그·GitHub는 변경하지 않았습니다.")
                    self._start("GitHub 서명 묶음 준비",lambda:job.prepare(review),prepared)
                    return
                def accepted(state):
                    self.reload()
                    self.result.setPlainText(f"게시 성공 · 실제 카탈로그 순번 {state.sequence}\n전자서명·릴리스·패키지 해시 확인 완료")
                self._start("서명된 더미 릴리스 게시",lambda:self.session.publish(review),accepted)
            self._start("게시 전 검사",lambda:self.session.review(*values),reviewed)
        except Exception as exc:
            self.result.setPlainText(self.session.safe_error(exc))

    def _github_step(self, title, action):
        if self.task or not self.github_job:
            return
        def done(_):
            mode = "모의" if self.github_transport.dry_run else "실제 Draft"
            suffix = "실제 GitHub 미변경" if self.github_transport.dry_run else f"초안 ID {self.github_job.draft_id} · 정식 공개하지 않음"
            self.result.setPlainText(f"{mode} {title} 완료 · 단계 {self.github_job.phase} · {suffix}")
        self._start('GitHub '+title,action,done)

    def request_github_draft(self):
        if self.task or not self.github_job:
            return
        if QMessageBox.question(self,"모의 초안 생성 확인" if self.github_transport.dry_run else "승인된 실제 초안 생성 확인",
                f"{REPOSITORY}\n{self.github_job.tag}\n표시된 자산만 사용하는 {'모의' if self.github_transport.dry_run else '실제'} 초안을 생성할까요?\n정식 공개는 하지 않습니다.",
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
            return
        self._github_step('초안 생성',lambda:self.github_job.create_draft(True))

    def request_github_public(self):
        if not self.github_transport.dry_run:
            self.result.setPlainText("실제 정식 공개·Latest 지정은 승인 범위 밖이므로 차단합니다.")
            return
        if self.task or not self.github_job or self.github_job.phase!='verified':
            return
        if QMessageBox.question(self,"모의 공개 최종 확인",
                f"{REPOSITORY}\n{self.github_job.tag}\n모든 자산의 재다운로드·서명 검증을 완료했습니다. 모의 공개할까요?\n실제 GitHub에는 쓰지 않습니다.",
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
            return
        self._github_step('공개',lambda:self.github_job.publish(True))

    def closeEvent(self, event: QCloseEvent):
        if self.task:
            self.result.setPlainText("검사/게시 작업 종료 후 창을 닫으세요. 작업을 강제 종료하지 않습니다.")
            event.ignore()
        else:
            super().closeEvent(event)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=PROJECT/'distribution',help='조회할 배포 저장소')
    parser.add_argument('--test-mode',action='store_true',help='표식이 있는 .test-results 더미 저장소만 게시 허용')
    parser.add_argument('--github-cli',type=Path,help='개발자 PC의 기존 gh 실행 파일; 실제 쓰기 잠금 유지')
    args=parser.parse_args(argv)
    app=QApplication.instance() or QApplication([sys.argv[0]])
    try:
        window=AdminWindow(args.root,test_mode=args.test_mode,
                           github_transport=GhCliTransport(args.github_cli) if args.github_cli else None)
        window.show()
        return app.exec()
    except (LauncherError,OSError,ValueError):
        print('관리자 GUI 시작 실패: 저장소와 격리 시험 표식을 확인하세요.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
