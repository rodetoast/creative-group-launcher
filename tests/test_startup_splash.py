"""The old Bootstrap's GUI must show startup feedback before loading its updater."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from southpaw_tools.__main__ import main
from southpaw_tools.common import LauncherError
from southpaw_tools.startup_splash import wants_session_splash


class StartupSplashTests(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(TemporaryDirectory())
        self.context = Path(folder) / "sessions" / "fixture" / "context.json"
        self.context.parent.mkdir(parents=True)

    def hint(self, **fields):
        self.context.write_text(json.dumps({"managed": True, "mode": "normal", **fields}), encoding="utf-8")

    def test_early_hint_skips_health_and_bootstrap_owned_splash(self):
        self.hint()
        self.assertTrue(wants_session_splash(self.context))
        self.hint(mode="health")
        self.assertFalse(wants_session_splash(self.context))
        self.hint(startup_splash=True)
        self.assertFalse(wants_session_splash(self.context))
        self.context.write_bytes(b" " * 16385)
        self.assertFalse(wants_session_splash(self.context))

    def test_splash_starts_before_session_validation_and_closes_on_failure(self):
        self.hint()
        seen = []

        class Splash:
            def __enter__(self):
                seen.append("splash")
                return self

            def __exit__(self, *_):
                seen.append("close")

        def invalid_session(*_):
            seen.append("validation")
            raise LauncherError("invalid session")

        with (patch("southpaw_tools.startup_splash.StartupSplash", Splash),
              patch("southpaw_tools.managed_update.ManagedSession", side_effect=invalid_session),
              patch("southpaw_tools.__main__.run_window") as window,
              patch("builtins.print")):
            self.assertEqual(main(["--session-file", str(self.context)]), 1)
        self.assertEqual(seen, ["splash", "validation", "close"])
        window.assert_not_called()

    def test_health_never_creates_a_gui_owned_splash(self):
        self.hint(mode="health")
        current = object()
        session = SimpleNamespace(mode="health", context={}, current=current,
                                  updater=SimpleNamespace(current=lambda: current))
        with (patch("southpaw_tools.startup_splash.StartupSplash") as splash,
              patch("southpaw_tools.managed_update.ManagedSession", return_value=session),
              patch("southpaw_tools.__main__.run_window", return_value=0) as window):
            self.assertEqual(main(["--session-file", str(self.context)]), 0)
        splash.assert_not_called()
        self.assertIsNone(window.call_args.kwargs["splash"])
