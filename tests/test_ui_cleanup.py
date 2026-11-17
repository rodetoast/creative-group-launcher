import unittest
from PySide6.QtGui import QTextDocument
from PySide6.QtCore import QUrl
from tests import test_ui as helpers


class UiCleanupTests(unittest.TestCase):
    setUp = helpers.UiTests.setUp
    close_windows = helpers.UiTests.close_windows
    window = helpers.UiTests.window

    def test_normal_screen_has_no_approval_badge_or_constant_footer_and_hides_release_id(self):
        window = self.window()
        self.assertTrue(window.channel.isHidden())
        self.assertTrue(window.message.isHidden())
        self.assertTrue(window.info['배포 식별자'].isHidden())
        self.assertEqual(window.details_button.text(), '상세 정보')
        window.message.setText('서명 검증 실패')
        self.assertFalse(window.message.isHidden())
        window.message.setText('')
        self.assertTrue(window.message.isHidden())

    def test_markdown_formats_notes_without_navigating_or_loading_resources(self):
        window = self.window()
        notes = window.notes
        notes.show_notes('# 변경 사항\n\n## 개선\n`code`와 **강조**\n\n![x](file:///private.png)')
        text = notes.toPlainText()
        self.assertIn('변경 사항', text)
        self.assertNotIn('# 변경 사항', text)
        self.assertNotIn('`code`', text)
        self.assertIn('code', text)
        self.assertFalse(notes.openLinks())
        self.assertFalse(notes.openExternalLinks())
        self.assertIsNone(notes.loadResource(QTextDocument.ResourceType.ImageResource, QUrl('file:///private.png')))
        self.assertIsNone(notes.loadResource(QTextDocument.ResourceType.ImageResource, QUrl('https://example.com/image.png')))
        # Exercise the actual document lookup with a real, existing local image.
        from southpaw_tools.ui import ASSETS
        url = QUrl.fromLocalFile(str((ASSETS/'southpaw-launcher.png').resolve()))
        notes.show_notes('![private](' + url.toString() + ')')
        self.assertIsNone(notes.document().resource(QTextDocument.ResourceType.ImageResource, url))
        original = '# 개선\nBuild source commit:\n\n`8ba7a1e47d84888c06ea3913482c79db9b72eb02`\n\n기능 개선'
        notes.show_notes(original)
        self.assertEqual(notes.source_text, original)
        self.assertIn('기능 개선', notes.toPlainText())
        self.assertNotIn('8ba7a1e', notes.toPlainText())

    def test_refresh_summary_retains_technical_details_and_signature_failure(self):
        window = self.window()
        window.online = True
        window.catalog_state = '전자서명·순번 검증 성공'
        window._connection_status()
        self.assertEqual(window.server_status.text(), '업데이트 확인 완료')
        self.assertIn('전자서명', window.server_status.toolTip())
        window._github_failure('카탈로그 전자서명 불일치')
        window._connection_status()
        self.assertIn('서명 검증 실패', window.server_status.text())
        self.assertIn('신뢰할 수 없는', window.message.text())

