import json
from pathlib import Path
import struct
import unittest

from PySide6.QtWidgets import QApplication, QLabel
from southpaw_tools.branding import DISPLAY_NAME, DESCRIPTION, ICON_FILENAME
from southpaw_tools import __version__
from southpaw_tools.paths import AppPaths
from southpaw_tools.ui import ASSETS, MainWindow
from southpaw_tools.windows_shell import APP_ID, DISPLAY_NAME as SHELL_NAME
from tests.support import temporary
from tools.build_windows import product_version_resource

APPLICATION = QApplication.instance() or QApplication([])
PROJECT = Path(__file__).resolve().parents[1]


class BrandingTests(unittest.TestCase):
    def test_fixed_public_name_preserves_internal_ids(self):
        self.assertEqual(DISPLAY_NAME, 'Southpaw 도구 런처')
        self.assertEqual(SHELL_NAME, DISPLAY_NAME)
        self.assertEqual(APP_ID, 'SouthpawGames.ToolsLauncher')
        config = json.loads((PROJECT/'packaging/windows/branding.json').read_bytes())
        self.assertEqual(config['current_display_name'], DISPLAY_NAME)
        self.assertEqual(config['app_id'], 'creative-group-launcher')
        self.assertEqual(Path(config['windows_ico']).name, ICON_FILENAME)

    def test_ico_has_seven_exact_resolutions_and_png_has_alpha(self):
        raw = (ASSETS/ICON_FILENAME).read_bytes()
        self.assertEqual(struct.unpack_from('<HHH', raw), (0, 1, 7))
        sizes = set()
        for index in range(7):
            width, height = struct.unpack_from('<BB', raw, 6+index*16)
            sizes.add((width or 256, height or 256))
        self.assertEqual(sizes, {(n, n) for n in (16,24,32,48,64,128,256)})
        png = (ASSETS/'southpaw-launcher.png').read_bytes()
        self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(png[25], 6)  # RGBA color type in IHDR.

    def test_gui_title_header_description_and_window_icon_at_minimum_size(self):
        with temporary('brand-') as folder:
            window = MainWindow(AppPaths(Path(folder)/'data'), auto_connect=False)
            try:
                window.resize(980, 700)
                window.show()
                APPLICATION.processEvents()
                self.assertEqual(window.windowTitle(), DISPLAY_NAME)
                brand = window.findChild(QLabel, 'brand')
                self.assertEqual(brand.text(), '도구 런처')
                self.assertFalse(brand.wordWrap())
                self.assertTrue(any(label.text() == 'SOUTHPAW' for label in window.findChildren(QLabel)))
                self.assertIn(DESCRIPTION, brand.toolTip())
                self.assertFalse(window.windowIcon().isNull())
                self.assertEqual(window.list.count(), 5)
                self.assertGreaterEqual(brand.width(), brand.fontMetrics().horizontalAdvance(brand.text()))
            finally:
                window.close()
                window.deleteLater()
                APPLICATION.processEvents()

    def test_windows_metadata_uses_public_name_and_keeps_exe_filename(self):
        with temporary('brand-meta-') as folder:
            resource = Path(folder)/'version.txt'
            product_version_resource(resource, 'CreativeGroupLauncher.exe')
            text = resource.read_text(encoding='utf-8')
            self.assertIn(DISPLAY_NAME, text)
            self.assertIn('CreativeGroupLauncher.exe', text)
            self.assertIn(__version__, text)
