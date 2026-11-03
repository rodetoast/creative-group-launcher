from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .common import identifier, inside


@dataclass(frozen=True)
class AppPaths:
    root: Path

    @classmethod
    def default(cls) -> "AppPaths":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return cls(base / "SouthpawGames" / "ToolsLauncher")

    def app(self, app_id: str) -> Path:
        return inside(self.root, f"apps/{identifier(app_id)}")

    def release(self, app_id: str, release_id: str) -> Path:
        return inside(self.app(app_id), f"releases/{identifier(release_id)}")

    def lock(self, app_id: str) -> Path:
        return inside(self.root, f"locks/{identifier(app_id)}.lock")

    @property
    def downloads(self) -> Path:
        return inside(self.root, "downloads")
