import unittest

from southpaw_tools.common import LauncherError
from tests import test_github_ui as helpers
from tests.support import LocalProvider


class TestModeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.fixture=helpers.GitHubUiTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_all_gui_and_actual_process_entry_points_block_dummy_execution(self):
        f=self.fixture;window=f.window();f.refresh(window);f.click_install(window)
        self.assertEqual(window.channel.text(),'테스트 배포본')
        self.assertIn('EXE 실행 차단',window.message.text())
        self.assertFalse(window.primary.isEnabled())
        self.assertFalse(window.launch_current.isEnabled())
        window.launch();window.primary_action()
        with self.assertRaisesRegex(LauncherError,'실행이 차단'):
            window.installer.launch('dummy')
        self.assertEqual(f.fixture.engine.processes.calls,[])

    def test_updates_continue_with_execution_blocked(self):
        f=self.fixture;window=f.window();f.refresh(window);f.click_install(window)
        f.publish_r2();window._github_next_check=0;f.refresh(window)
        self.assertEqual(window.primary.text(),'업데이트');self.assertTrue(window.primary.isEnabled())
        self.assertFalse(window.launch_current.isVisible())
        f.click_install(window)
        self.assertEqual(window.installer.installed('dummy').release_id,'r2')
        self.assertFalse(window.primary.isEnabled())
        self.assertEqual(f.fixture.engine.processes.calls,[])

    def test_normal_mode_launch_behavior_and_label_are_unchanged(self):
        f=self.fixture
        f.fixture.engine.install(f.fixture.app,LocalProvider(f.fixture.source))
        window=f.window(keys=False)
        window.list.setCurrentRow(next(i for i,a in enumerate(window.apps) if a.app_id=='dummy'))
        self.assertEqual(window.channel.text(),'')
        self.assertTrue(window.channel.isHidden())
        window.launch()
        self.assertEqual(len(f.fixture.engine.processes.calls),1)
