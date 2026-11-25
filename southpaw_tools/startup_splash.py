"""Small Windows startup window, independent of Qt and the update protocol."""
from contextlib import nullcontext
import json
import sys
from threading import Event, Thread

def wants_session_splash(path):
    """Read a small presentation hint without importing the update engine."""
    if path.name != "context.json" or path.parent.parent.name != "sessions":
        return False
    try:
        with path.open("rb") as stream:
            raw = stream.read(16385)
        if len(raw) > 16384:
            return False
        info = json.loads(raw)
    except (OSError, ValueError, RecursionError):
        return False
    return (isinstance(info, dict) and info.get("managed") is True
            and info.get("mode") == "normal" and not info.get("startup_splash"))


class StartupSplash:
    def __init__(self):
        self._stop = Event()
        self._shown = Event()
        self._thread = None
        self._window = None
        self.notice = None

    def __enter__(self):
        self.show()
        return self

    def __exit__(self, *_):
        self.close()

    def show(self):
        if sys.platform != "win32" or self._thread:
            return
        self._stop.clear()
        self._shown.clear()
        self._thread = Thread(target=self._paint, name="Windows startup splash", daemon=True)
        self._thread.start()
        self._shown.wait(0.15)

    def close(self):
        if self._thread:
            self._stop.set()
            self._thread.join(1)
            if not self._thread.is_alive():
                self._thread = None

    def notify(self, text):
        if sys.platform == "win32":
            self.notice = text
            self._stop.wait(1.7)

    def keep_above(self, main_window):
        """Put the launcher below the splash without joining their input queues."""
        splash_window = self._window
        if not splash_window:
            return
        from .win32_splash import place_below

        place_below(main_window, splash_window)

    def _paint(self):
        try:
            from .win32_splash import run

            run(self)
        finally:
            self._shown.set()


def frozen_bootstrap(project, *, upgrade_entry=False):
    # The worker and developer fixtures must not create an additional window.
    args = sys.argv[1:]
    if upgrade_entry and args in (["--bootstrap-swap"], ["--restore-bootstrap"]):
        from subprocess import SubprocessError
        from .bootstrap_diagnostics import error_summary
        from .bootstrap_upgrade import worker
        from .common import LauncherError

        try:
            return worker(restore=args == ["--restore-bootstrap"])
        except (LauncherError, OSError, ValueError, KeyError, TypeError, SubprocessError) as exc:
            # The caller redirects this worker to its diagnostic log. A
            # recovery outcome must never open a PyInstaller traceback dialog.
            print(f"Bootstrap 교체 작업 종료: {error_summary(exc)}", file=sys.stderr)
            return 1
    show = (sys.platform == "win32" and "worker" not in sys.argv[1:]
            and not {"--help", "-h", "--launch-tool"}.intersection(sys.argv[1:]))
    while True:
        with (StartupSplash() if show else nullcontext()) as splash:
            from . import self_update
            from .bootstrap import main
            self_update.PROJECT = project
            if upgrade_entry:
                from .bootstrap_upgrade import entry_route
                token = args[1] if len(args) == 2 and args[0] == "--bootstrap-trial" else None
                home, confirmed, recover = entry_route(token)
                # A probationary process must return failures to its independent worker.
                result = main([] if token else args, splash=splash, managed_home=home,
                              on_confirmed=confirmed, on_initial_failure=recover)
            else:
                result = main(splash=splash)
        if result != 3:
            return result
