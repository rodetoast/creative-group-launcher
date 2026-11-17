import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.build_windows import build_environment


class WindowsBuildEnvironmentTests(unittest.TestCase):
    def test_unrelated_native_dll_path_does_not_enter_build_or_modify_parent(self):
        with patch.dict(os.environ,{'PATH':'C:/Unrelated/Poppler/bin','SystemRoot':'C:/Windows',
                                    'CGL_BUILD_SENTINEL':'preserved'}):
            before=dict(os.environ)
            child=build_environment(Path('isolated-build'))
            self.assertNotIn('Poppler',child['PATH'])
            self.assertEqual(Path(child['PATH'].split(os.pathsep)[0]),Path('C:/Windows/System32'))
            self.assertEqual(child['CGL_BUILD_SENTINEL'],'preserved')
            self.assertEqual(dict(os.environ),before)
