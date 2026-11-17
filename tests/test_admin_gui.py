from __future__ import annotations

import hashlib
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from tests.test_ui import APPLICATION
from tests.support import temporary, TestSigner
from tools.prepare_admin_gui_demo import prepare
from southpaw_tools.admin_gui import AdminWindow
from southpaw_tools.admin_gui_model import APP_NAMES, AdminSession, PROJECT
from southpaw_tools.common import LauncherError, digest


def tree(root):
    return {str(p.relative_to(root)):digest(p) for p in root.rglob('*') if p.is_file()}


class AdminGuiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=temporary('admin-gui-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'demo'
        self.repo,self.key=prepare(self.root)
        self.source=self.root/'inputs/admin-dummy-r1.zip'
        self.session=AdminSession(self.repo,test_mode=True)
        self.windows=[]
        self.addCleanup(self.close_windows)

    def close_windows(self):
        for window in self.windows:
            self.wait(window)
            window.close()
        APPLICATION.processEvents()

    def wait(self, window):
        end=time.monotonic()+8
        while window.task and time.monotonic()<end:
            APPLICATION.processEvents()
            if window.task:
                window.task.wait(5)
        APPLICATION.processEvents()
        self.assertIsNone(window.task, 'GUI worker did not finish')

    def window(self,test_mode=True):
        window=AdminWindow(self.repo,test_mode=test_mode)
        self.windows.append(window)
        return window

    def inspect(self,**overrides):
        values=dict(source=self.source,app_id='tilenamer',version='0.0.1',release_id='gui-r1',
                    executable='Demo.exe',notes='시험 릴리스 노트')
        values.update(overrides)
        return self.session.inspect(**values)

    def plan(self):
        return self.session.review(self.inspect(),'2',self.key,True)

    def fill(self,window):
        window.version.setText('0.0.1')
        window.release_id.setText('gui-r1')
        window.executable.setText('Demo.exe')
        window.notes.setPlainText('시험 릴리스 노트')
        window.zip_path=self.source
        window.key_path=self.key
        window.approved.setChecked(True)
        window.inspect_selected()
        self.wait(window)
        self.assertIsNotNone(window.inspection,window.result.toPlainText())

    def test_five_names_and_tag_master_remain_locked(self):
        window=self.window()
        self.assertEqual([window.apps.itemText(i) for i in range(window.apps.count())],
                         ['TileNamer','ase_viewer','AsepriteTagMaster','Ase-PS Bridge Pro','Pivot_Fixer'])
        window.apps.setCurrentIndex(window.apps.findData('tag-master'))
        self.assertFalse(window.zip_button.isEnabled())
        self.assertFalse(window.publish_button.isEnabled())
        with self.assertRaises(LauncherError):
            self.inspect(app_id='tag-master')

    def test_default_gui_never_enables_production_publication(self):
        window=self.window(False)
        self.fill(window)
        self.assertFalse(window.publish_button.isEnabled())
        with self.assertRaises(LauncherError):
            window.session.review(window.inspection,'2',self.key,True)

    def test_invalid_zip_rejected_without_repository_changes(self):
        source=self.root/'broken.zip'
        source.write_bytes(b'not a zip')
        self.session.allowed_packages.add(digest(source))
        before=tree(self.repo)
        with self.assertRaises(LauncherError):
            self.inspect(source=source)
        self.assertEqual(before,tree(self.repo))

    def test_missing_and_invalid_fields_rejected(self):
        for changes in ({'version':''},{'release_id':''},{'executable':''},
                        {'version':'latest'},{'release_id':'../evil'},{'executable':'../Demo.exe'},
                        {'app_id':'unknown'}):
            with self.subTest(changes=changes),self.assertRaises(LauncherError):
                self.inspect(**changes)

    def test_duplicate_release_rejected(self):
        self.session.publish(self.plan())
        with self.assertRaises(LauncherError):
            self.inspect()

    def test_invalid_sequence_rejected(self):
        inspection=self.inspect()
        for sequence in ('','not-int','0','1','-1',str(2**63)):
            with self.subTest(sequence=sequence),self.assertRaises(LauncherError):
                self.session.review(inspection,sequence,self.key,True)

    def test_missing_key_and_approval_rejected(self):
        inspection=self.inspect()
        for key,approved in ((None,True),(self.root/'missing.pem',True),(self.key,False)):
            with self.subTest(key=str(key),approved=approved),self.assertRaises(LauncherError):
                self.session.review(inspection,'2',key,approved)

    def test_public_repository_private_key_rejected(self):
        inside=self.repo/'key.pem'
        inside.write_bytes(self.key.read_bytes())
        with self.assertRaises(LauncherError):
            self.session.review(self.inspect(),'2',inside,True)

    def test_cancel_final_review_does_not_call_engine(self):
        window=self.window()
        self.fill(window)
        before=tree(self.repo)
        with patch.object(window,'confirm',return_value=False),patch('southpaw_tools.admin.publish') as engine:
            window.request_publish()
            self.wait(window)
        engine.assert_not_called()
        self.assertEqual(before,tree(self.repo))
        self.assertIn('취소',window.result.toPlainText())

    def test_complete_gui_publication_and_original_zip_preserved(self):
        window=self.window()
        self.fill(window)
        original=(digest(self.source),self.source.stat().st_mtime_ns)
        key_bytes=self.key.read_bytes()
        with patch.object(window,'confirm',return_value=True):
            window.request_publish()
            self.wait(window)
        self.assertIn('게시 성공',window.result.toPlainText())
        state=self.session.state()
        self.assertTrue(state.signature_ok)
        self.assertEqual(state.sequence,2)
        self.assertEqual(next(a for a in state.apps if a.app_id=='tilenamer').release_id,'gui-r1')
        self.assertEqual(original,(digest(self.source),self.source.stat().st_mtime_ns))
        self.assertEqual(key_bytes,self.key.read_bytes())
        logs=list((self.root/'gui-logs').glob('*.json'))
        self.assertEqual(len(logs),1)
        for log in logs:
            text=log.read_text(encoding='utf-8')
            self.assertNotIn(str(self.key),text)
            self.assertNotIn('PRIVATE KEY',text)
        self.assertFalse((self.root/'settings.json').exists())

    def test_engine_failure_shows_actual_state_and_preserves_catalog(self):
        window=self.window()
        self.fill(window)
        before=(self.repo/'catalog.json').read_bytes()
        with patch.object(window,'confirm',return_value=True), \
             patch('southpaw_tools.admin.publish',side_effect=OSError('disk full')) as engine:
            window.request_publish()
            self.wait(window)
        self.assertEqual(engine.call_count,1)
        self.assertNotIn('게시 성공',window.result.toPlainText())
        self.assertIn('실패',window.result.toPlainText())
        self.assertEqual(before,(self.repo/'catalog.json').read_bytes())
        self.assertTrue(self.session.state().signature_ok)
        self.assertTrue(list((self.root/'gui-logs').glob('*.json')))

    def test_partial_signature_publication_is_not_success_or_auto_rollback(self):
        window=self.window()
        self.fill(window)
        before=(self.repo/'catalog.json').read_bytes()
        with patch.object(window,'confirm',return_value=True), \
             patch('southpaw_tools.admin.atomic_bytes',side_effect=OSError('catalog replacement failed')):
            window.request_publish()
            self.wait(window)
        self.assertNotIn('게시 성공',window.result.toPlainText())
        self.assertEqual(before,(self.repo/'catalog.json').read_bytes())
        self.assertFalse(self.session.state().signature_ok)
        self.assertIn('실제 순번',window.catalog_status.text())
        self.assertFalse(window.publish_button.isEnabled())

    def test_changed_zip_after_inspection_is_rejected(self):
        inspection=self.inspect()
        self.source.write_bytes(b'changed dummy')
        before=tree(self.repo)
        with self.assertRaises(LauncherError):
            self.session.review(inspection,'2',self.key,True)
        self.assertEqual(before,tree(self.repo))

    def test_changed_catalog_after_inspection_is_rejected(self):
        inspection=self.inspect()
        path=self.repo/'catalog.json'
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(LauncherError):
            self.session.review(inspection,'2',self.key,True)

    def test_test_mode_cannot_target_real_distribution(self):
        with self.assertRaises(LauncherError):
            AdminSession(PROJECT/'distribution',test_mode=True)
        source=self.root/'unapproved.zip'
        source.write_bytes(self.source.read_bytes()+b'not approved dummy')
        with self.assertRaises(LauncherError):
            self.inspect(source=source)

    def test_input_changes_invalidate_inspection(self):
        window=self.window()
        self.fill(window)
        window.release_id.setText('different')
        self.assertIsNone(window.inspection)
        self.assertFalse(window.publish_button.isEnabled())

    def test_inspection_worker_keeps_event_loop_responsive(self):
        window=self.window()
        window.version.setText('0.0.1')
        window.release_id.setText('gui-r1')
        window.executable.setText('Demo.exe')
        window.zip_path=self.source
        gate=threading.Event()
        original=window.session.inspect
        def waiting(*args):
            if not gate.wait(2):
                raise LauncherError('event loop did not release worker')
            return original(*args)
        with patch.object(window.session,'inspect',side_effect=waiting):
            QTimer.singleShot(0,gate.set)
            window.inspect_selected()
            self.wait(window)
        self.assertTrue(gate.is_set())
        self.assertIsNotNone(window.inspection)

    def test_cancel_zip_selection_never_auto_selects_payload(self):
        window=self.window()
        with patch('southpaw_tools.admin_gui.QFileDialog.getOpenFileName',return_value=('','')):
            window.select_zip()
        self.assertIsNone(window.zip_path)
        self.assertEqual(window.zip_label.text(),'선택하지 않음')

    def test_wrong_signing_key_rejected_before_engine(self):
        other=self.root/'other'
        other.mkdir()
        signer=TestSigner(other)
        with self.assertRaises(LauncherError):
            self.session.review(self.inspect(),'2',signer.path,True)

    def test_log_write_failure_never_hides_published_state(self):
        window=self.window()
        self.fill(window)
        with patch.object(window,'confirm',return_value=True), \
             patch('southpaw_tools.admin_gui_model.atomic_json',side_effect=OSError('log disk full')):
            window.request_publish()
            self.wait(window)
        self.assertNotIn('게시 성공',window.result.toPlainText())
        self.assertIn('로그',window.result.toPlainText())
        self.assertIn('gui-r1',window.current.toPlainText())
        self.assertTrue(self.session.state().signature_ok)


if __name__=='__main__':
    unittest.main()
