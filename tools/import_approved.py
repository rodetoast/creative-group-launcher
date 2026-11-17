"""Register only the five explicitly approved baseline releases, without rebuilding."""
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from dataclasses import replace
from pathlib import Path

from southpaw_tools.admin import publish
from southpaw_tools.catalog import AppRelease, catalog_document, load_catalog
from southpaw_tools.common import LauncherError, atomic_json, digest

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = Path.home() / "Desktop"

SPECS = [
    dict(app_id="tilenamer", display_name="TileNamer", category="타일 제작", version="0.1.6 RC3",
         release_id="0.1.6-rc3-8ba7a1e", build_id="8ba7a1e47d84888c06ea3913482c79db9b72eb02",
         description="타일 영역을 지정하고, 배치 미리보기로 확인한 뒤 규칙에 맞는 PNG로 내보냅니다.",
         source="TileNamer/release/TileNamer_v0.1.6_RC3_win64.zip", executable="TileNamer.exe", cwd=".",
         sha="aac38dc3a47dffe1a1cb7c2de3048922c4e45240df84ba6a6347107d67b9c3b4",
         exe_sha="0d8f758fa17b821b1add4d4259aa98f3f30f06a1bd4d0ba17c1a236835dc2349",
         required=[], preserve=[], package_type="onefile", icon="tilenamer.png",
         note="RELEASE_v0.1.6_RC3.md"),
    dict(app_id="ase-viewer", display_name="ase_viewer", category="애니메이션 검수", version="0.5.8.3",
         release_id="0.5.8.3-team-7841e60", build_id="7841e60fe3d4bb908a0c5f1b488049f9fa2ba63f",
         description="Aseprite 애니메이션을 액션·물리·전투 환경에서 확인하는 팀용 뷰어입니다.",
         source="AI/ase_viewer_v0.5.8.3_with_examples.zip", executable="ase_viewer.exe", cwd=".",
         sha="7f5d7b75014cc355d5dc7d06499429b3be7a3342fe8514871c4ce57622dd05b8",
         exe_sha="299ef579a110c76c85a4122a6363b81e9360a41957e2d2ad7efe001f877d0dbf",
         required=["resources/examples/README.md", "resources/examples/shared/sources/Cailin_00_Public.aseprite",
                   "resources/examples/shared/sources/Nisariel_00_Public_02.aseprite",
                   "resources/examples/ex1/backgrounds/로비 컨셉94 (1).png",
                   "resources/examples/ex2/parallax/# 2번_완성본.png",
                   "resources/examples/ex2/parallax/# 3번_완성본.png",
                   "resources/examples/ex2/parallax/# 4번_완성본.png",
                   "resources/examples/ex2/parallax/00.png", "resources/examples/ex2/parallax/01.png",
                   "resources/examples/ex2/parallax/레이어 3.png"],
         preserve=["config.json", "ase_settings.json", "ase_project.json", "ase_debug.log"],
         package_type="onefile", icon="ase-viewer.png", note="RELEASE_v0.5.8.3.md"),
    dict(app_id="tag-master", display_name="AsepriteTagMaster", category="태그 관리", version="0.4.0",
         release_id="0.4.0-team-7263f8d", build_id="7263f8d6107be76363d329c6962cd46dd15d4068",
         description="Aseprite 태그 이름과 반복 속성을 검수하고, 리포트를 확인한 뒤 일괄 수정합니다.",
         source="AsepriteTagMaster_v0.4.0_20260710_7263f8d.zip", executable="AsepriteTagMaster.exe", cwd=".",
         sha="80865038ddab9a1b9050d04cbb48cb777edf4e6419caafb05b8b51c0f6962299",
         exe_sha="5b55cff02880d5c02ac7f1c2c323b8125273f056f8a774beb246cc0d4dd0aee6",
         required=["custom_dictionary.json", "VERSION.txt"],
         preserve=["custom_dictionary.json", "settings.json", "aseprite_tag_master_error.log"],
         package_type="onefile", icon="", note=""),
    dict(app_id="ps2ase", display_name="Ase-PS Bridge Pro", category="제작 연동", version="0.3.6",
         release_id="0.3.6-team-6e84645", build_id="6e846459cb240ab5942e2ffa65d3b51d64648972",
         description="Photoshop과 Aseprite 사이에서 레이어를 복사하고 프레임·정렬을 관리합니다.",
         source="AI TS/dist/Ase-PS-Bridge-Pro_v0.3.6_Windows.zip", executable="bridge_ui.exe", cwd=".",
         sha="1945520ea353e584520f0984de65b4de0dbd4e3c206087fa5741ee74282a53d9",
         exe_sha="203c7fffe32726b7851edf0ad3e20d1bf1963f10124deb976992895dd21584fe",
         required=[], preserve=["temp"], package_type="onefile", icon="bridge.ico", note="RELEASE_v0.3.6.md"),
    dict(app_id="pivot-fixer", display_name="Pivot_Fixer", category="이미지 보정", version="0.3.3",
         release_id="0.3.3-team-80b84c9", build_id="80b84c99f6e9865beb26d8b184e8d400781e9d07",
         description="PNG의 피봇·여백을 맞추고 Aseprite 레이어 이동과 보정 복사본을 만듭니다.",
         source="Pivot Fixer/dist/Pivot_Fixer_v0.3.3.zip",
         executable="Pivot_Fixer_v0.3.3/Pivot_Fixer_v0.3.3.exe", cwd="Pivot_Fixer_v0.3.3",
         sha="214c966925e9def3aeebeb0245359e355606bf3627c47b29d956a78e5ec37361",
         exe_sha="620c7dffb32810fc6427b57ed467ba042b6e2893afc21b03b70a79f1218c295b",
         required=["Pivot_Fixer_v0.3.3/_internal/tkinterdnd2"],
         preserve=["pivot_fixer_settings.json", "_internal/pivot_fixer_settings.json"],
         package_type="onedir", icon="", note=""),
]


def seed_app(spec):
    notes = (f"팀 승인 기준: {spec['display_name']} {spec['version']}\n\n"
             "이 카탈로그는 승인된 완성 빌드만 사용합니다. 이후 개발 소스는 포함하지 않습니다.\n"
             "설치에는 개발자 PC의 배포 서버 연결이 필요합니다. 설치 후에는 오프라인 실행이 가능합니다.")
    return AppRelease.parse(dict(
        app_id=spec["app_id"], display_name=spec["display_name"], category=spec["category"],
        description=spec["description"], version=spec["version"], release_id=spec["release_id"],
        build_id=spec["build_id"], package_type=spec["package_type"], icon=spec["icon"],
        working_directory_relative_path=spec["cwd"], required_paths=spec["required"],
        preserve_paths=spec["preserve"], release_notes=notes, published=False,
        availability_reason="배포 패키지 미확인 — 지정 버전의 승인 ZIP이 필요합니다.",
    ))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve", action="store_true", help="Explicit approval for these exact baseline packages")
    parser.add_argument("--seed-only", action="store_true")
    parser.add_argument("--signing-key", type=Path)
    parser.add_argument("--sequence", type=int)
    args = parser.parse_args(argv)
    data = ROOT / "southpaw_tools/data/catalog.json"
    dist = ROOT / "distribution"
    if args.seed_only:
        for path in (data, dist / "catalog.json"):
            if path.exists():
                raise LauncherError("기존 카탈로그를 초기화하지 않습니다.")
            atomic_json(path, catalog_document([seed_app(spec) for spec in SPECS]))
        print("5개 미게시 카탈로그 생성")
        return 0
    if not args.approve:
        parser.error("--approve required")
    if args.signing_key is None or args.sequence is None:
        parser.error("--signing-key and --sequence required; unsigned publishing is disabled")
    sequence = args.sequence
    report = []
    for spec in SPECS:
        source = DESKTOP / spec["source"]
        if not source.is_file():
            report.append({"app_id": spec["app_id"], "source": str(source), "result": "배포 패키지 미확인"})
            continue
        if digest(source) != spec["sha"]:
            raise LauncherError(f"승인 원본 ZIP 해시 불일치: {spec['app_id']}")
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
            # Explicit full CRC read, in addition to ZIP and executable SHA checks.
            bad = archive.testzip()
            if bad:
                raise LauncherError(f"ZIP CRC 불일치: {bad}")
            notes = archive.read(spec["note"]).decode("utf-8-sig") if spec["note"] else seed_app(spec).release_notes
        existing = next(a for a in load_catalog(dist / "catalog.json") if a.app_id == spec["app_id"])
        if existing.published:
            if (existing.release_id != spec["release_id"] or existing.sha256 != spec["sha"]
                    or digest(source) != spec["sha"]
                    or digest(dist / "packages" / existing.package_name) != spec["sha"]):
                raise LauncherError("기존 등록을 임의로 덮어쓰지 않습니다.")
            app = existing
        else:
            app = publish(dist, spec["app_id"], source, version=spec["version"], release_id=spec["release_id"],
                          executable=spec["executable"], expected_sha256=spec["sha"],
                          expected_exe_sha256=spec["exe_sha"], approved=True, build_id=spec["build_id"], notes=notes,
                          signing_key=args.signing_key, sequence=sequence)
            sequence += 1
        report.append({"app_id": app.app_id, "source": str(source), "result": "verified-copy",
                       "package": app.package_name, "zip_sha256": app.sha256,
                       "exe_sha256": app.executable_sha256, "size": app.package_size,
                       "executable": app.executable_relative_path, "cwd": app.working_directory_relative_path,
                       "entries": len(names), "required_paths": app.required_paths,
                       "preserve_paths": app.preserve_paths, "package_type": app.package_type})
    # Ship catalog metadata, not original development paths, with the launcher.
    icons = {spec["app_id"]: spec["icon"] for spec in SPECS}
    atomic_json(dist / "catalog.json", catalog_document([
        replace(app, icon=icons[app.app_id]) for app in load_catalog(dist / "catalog.json")
    ]))
    shutil.copyfile(dist / "catalog.json", data)
    assets = ROOT / "southpaw_tools/assets"
    assets.mkdir(parents=True, exist_ok=True)
    for source, name in [(DESKTOP / "TileNamer/icon.png", "tilenamer.png"),
                         (DESKTOP / "AI/Icon.png", "ase-viewer.png"),
                         (DESKTOP / "AI TS/bridge_icon.ico", "bridge.ico")]:
        if source.is_file():
            shutil.copyfile(source, assets / name)
    atomic_json(ROOT / "docs/package-audit.local.json", {"packages": report})
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
