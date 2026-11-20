"""Qt Quick frontend experiment. Uses sample app data and has no installer or network."""
import argparse
import json
from pathlib import Path
import sys

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow


class CatalogPreview(QObject):
    changed = Signal()
    APPS = [
        {"name": "TileNamer", "description": "타일 영역을 지정하고 배치 이름을 내보냅니다.",
         "installed": "0.1.5", "latest": "0.1.6 RC3"},
        {"name": "ase_viewer", "description": "스프라이트의 프레임, 태그와 레이어를 살펴봅니다.",
         "installed": "0.5.8.4", "latest": "0.5.8.4"},
        {"name": "AsepriteTagMaster", "description": "Aseprite 애니메이션 태그를 편집합니다.",
         "installed": "", "latest": "0.4.0"},
        {"name": "Ase-PS Bridge Pro", "description": "Photoshop과 Aseprite 사이에서 작업을 전달합니다.",
         "installed": "0.3.6", "latest": "0.3.6"},
        {"name": "Pivot_Fixer", "description": "스프라이트의 피벗 위치를 확인하고 조정합니다.",
         "installed": "", "latest": "0.3.3"},
    ]

    def __init__(self):
        super().__init__()
        self._busy = False
        self._status = "샘플 데이터 · 확인 전"

    @Property("QVariantList", constant=True)
    def apps(self):
        return self.APPS

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def status(self):
        return self._status

    @Slot()
    def refresh(self):
        if self._busy:
            return
        self._busy = True
        self._status = "샘플 목록 확인 중"
        self.changed.emit()
        QTimer.singleShot(0, self._finish)

    def _finish(self):
        self._busy = False
        self._status = "샘플 목록 확인 완료"
        self.changed.emit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", type=Path, help="Write a marker on the first frame with the detail view ready")
    args = parser.parse_args()
    app = QGuiApplication([sys.argv[0]])
    engine = QQmlApplicationEngine()
    catalog = CatalogPreview()
    engine.rootContext().setContextProperty("catalog", catalog)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().with_name("Launcher.qml"))))
    if not engine.rootObjects():
        return 1
    view = engine.rootObjects()[0]
    if not isinstance(view, QQuickWindow):
        return 1

    def frame():
        if args.check and view.property("contentReady") and not args.check.exists():
            args.check.write_text(json.dumps({"apps": len(catalog.apps), "content_ready": True}), encoding="utf-8")
            app.quit()

    if args.check:
        view.frameSwapped.connect(frame)
        QTimer.singleShot(10000, lambda: app.exit(2))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
