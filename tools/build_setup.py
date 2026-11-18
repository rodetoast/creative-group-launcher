"""Build a per-user NSIS setup around the immutable official v0.1.1 seed."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from southpaw_tools.archive import checked_members
from southpaw_tools.catalog_trust import CatalogVerifier
from southpaw_tools.common import LauncherError, digest
from tools.build_windows import build_environment
from southpaw_tools.branding import DISPLAY_NAME
from southpaw_tools.github_channels import canonical_channel

PROJECT = Path(__file__).resolve().parents[1]
OFFICIAL_SHA = "605afa20380a80e4fb5646b7b714a424b0ab9257c81076edacd8aea4b942365d"
SETUP_VERSION = "0.1.4.0"


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def nsis(value):
    text = str(value)
    if "\n" in text or "\r" in text:
        raise LauncherError("NSIS 경로에 줄바꿈을 사용할 수 없습니다.")
    return text.replace("$", "$$").replace('"', '$\\"')


def compile_setup(root, compiler, *, test_registration=False, registration_suffix="", output_directory=None):
    name = "test-installer" if test_registration else "installer"
    if output_directory and (Path(output_directory).name != output_directory or output_directory in {'.', '..'}):
        raise LauncherError('설치 출력 폴더 이름이 올바르지 않습니다.')
    output = root / (output_directory or name)
    output.mkdir()
    if registration_suffix and not registration_suffix.isalnum():
        raise LauncherError('시험 설치 등록 접미사는 영문/숫자만 허용합니다.')
    manifest = json.loads((root / 'setup-manifest.json').read_bytes())
    config = {
        "SETUP_VERSION": manifest.get('setup_version', SETUP_VERSION),
        "PRODUCT_NAME": DISPLAY_NAME,
        "PRODUCT_VERSION": manifest['launcher']['version'],
        "SETUP_OUTPUT": output / ("SouthpawToolsLauncherSetup-DEV.exe" if test_registration else "SouthpawToolsLauncherSetup.exe"),
        "GUARD_EXE": root / "guard-dist/CGLSetupGuard.exe",
        "LAUNCHER_ICON": root / "payload/launcher.ico",
        "PREF_KEY": "Software\\SouthpawGames\\SetupCheck20261111"+registration_suffix if test_registration else "Software\\SouthpawGames\\ToolsLauncherSetup",
        "UNINSTALL_KEY": "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\" +
                         ("SouthpawToolsLauncherSetupCheck20261111"+registration_suffix if test_registration else "SouthpawToolsLauncher"),
        "SHORTCUT_NAME": DISPLAY_NAME+" 설치 시험"+registration_suffix if test_registration else DISPLAY_NAME,
        "MUTEX_NAME": "SouthpawToolsLauncherSetupCheck"+registration_suffix if test_registration else "SouthpawToolsLauncherSetup",
    }
    (output / "config.nsh").write_text("".join(f'!define {key} "{nsis(value)}"\n' for key, value in config.items()), encoding="utf-8-sig")
    template = PROJECT / "packaging/windows/setup.nsi"
    if canonical_channel(manifest.get("channel", {})):
        text = template.read_text(encoding="utf-8")
        old_install = 'InstallDir "$PROFILE\\CGL"'
        old_data = 'StrCpy $DataRoot "$LOCALAPPDATA\\SouthpawGames\\ToolsLauncher"'
        if text.count(old_install) != 1 or text.count(old_data) != 1:
            raise LauncherError("신규 채널 Setup 경로 치환 기준이 변경됐습니다.")
        text = text.replace(old_install, 'InstallDir "$PROFILE\\CGL-Rodetoast"')
        text = text.replace(old_data, 'StrCpy $DataRoot "$LOCALAPPDATA\\SouthpawGames\\ToolsLauncherRodetoast"')
        (output / "setup.nsi").write_text(text, encoding="utf-8")
    else:
        shutil.copyfile(template, output / "setup.nsi")
    manifest = json.loads((root / "setup-manifest.json").read_bytes())
    lines = []
    directories = set()
    for relative in sorted(manifest["files"]):
        file = Path(relative)
        parent = str(file.parent).replace("/", "\\")
        destination = "$INSTDIR" if parent == "." else "$INSTDIR\\" + nsis(parent)
        lines.extend([f'SetOutPath "{destination}"', f'File "/oname={nsis(file.name)}" "{nsis(root / "payload" / file)}"'])
        directories.update(p for p in file.parents if p != Path("."))
    (output / "payload.nsh").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    removal = [f'Delete "$INSTDIR\\{nsis(Path(name))}"' for name in sorted(manifest["files"])]
    removal.extend(f'RMDir "$INSTDIR\\{nsis(directory)}"' for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True))
    (output / "remove-payload.nsh").write_text("\n".join(removal) + "\n", encoding="utf-8-sig")
    with (output / "compile.log").open("xb") as log:
        result = subprocess.run([str(compiler), "/V3", "/INPUTCHARSET", "UTF8", str(output / "setup.nsi")],
                                cwd=output, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    if result.returncode:
        raise LauncherError(f"NSIS 컴파일 실패. {name}/compile.log를 확인하세요.")
    return Path(config["SETUP_OUTPUT"])


def prepare(root, official_zip, compiler):
    root = root.resolve()
    if not root.is_relative_to((PROJECT / ".test-results").resolve()) or root.exists():
        raise LauncherError("새 격리 .test-results 출력 폴더가 필요합니다.")
    if digest(official_zip) != OFFICIAL_SHA:
        raise LauncherError("공식 직원용 ZIP의 SHA-256이 다릅니다.")
    root.mkdir(parents=True)
    payload = root / "payload"
    with zipfile.ZipFile(official_zip) as archive:
        checked_members(archive)
        if archive.testzip() is not None:
            raise LauncherError("공식 ZIP CRC 오류")
        archive.extractall(payload)
    # Rebuild only the stable Bootstrap for window identity and a console-free start.
    source = root / "bootstrap-source"
    source.mkdir()
    shutil.copytree(PROJECT / "southpaw_tools", source / "southpaw_tools", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(PROJECT / "tools", source / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    policy_folder = payload / "_internal/southpaw_tools/data"
    for name in ("managed-channel.json", "trusted_catalog_keys.json"):
        shutil.copyfile(policy_folder / name, source / "southpaw_tools/data" / name)
    branding = json.loads((PROJECT / 'packaging/windows/branding.json').read_bytes())
    icon = PROJECT / branding['windows_ico']
    if not icon.is_file() or icon.suffix.lower() != '.ico':
        raise LauncherError('Setup 빌드에 사용할 Windows ICO가 없습니다.')
    build_root = source / ".test-results/build"
    command = [sys.executable, "-B", "-m", "tools.build_windows", "--root", str(build_root),
               "--roles", "bootstrap", "--bootstrap-windowed", "--bootstrap-icon", str(icon)]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(source), *sys.path])
    with (root / "bootstrap-build.log").open("xb") as log:
        result = subprocess.run(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    if result.returncode:
        raise LauncherError("설치용 Bootstrap 빌드 실패")
    shutil.copytree(build_root / "dist/CGLBootstrap", payload, dirs_exist_ok=True)
    shutil.copyfile(icon, payload / "launcher.ico")
    save(payload / "setup-shell.json", {"schema_version": 1, "app_id": "SouthpawGames.ToolsLauncher"})
    policy = json.loads((policy_folder / "trusted_catalog_keys.json").read_bytes())
    verifier = CatalogVerifier(policy, root / "unused-trust.json")
    seed = payload / "seed"
    _, apps = verifier.verify((seed / "catalog.json").read_bytes(), (seed / "catalog.sig.json").read_bytes())
    launcher = next(app for app in apps if app.app_id == "creative-group-launcher")
    source_zip = seed / launcher.package_name
    assert launcher.version == "0.1.1" and digest(source_zip) == launcher.sha256
    with zipfile.ZipFile(source_zip) as archive:
        checked_members(archive)
        members = [member.filename for member in archive.infolist() if not member.is_dir()]
    manifest = {"product": "SouthpawGames.ToolsLauncher.Setup", "setup_version": SETUP_VERSION,
                "official_zip_sha256": OFFICIAL_SHA, "launcher": launcher.to_dict(), "launcher_files": members,
                "files": {p.relative_to(payload).as_posix(): digest(p) for p in payload.rglob("*") if p.is_file()}}
    save(root / "setup-manifest.json", manifest)
    # The helper is embedded in Setup and its uninstaller, not installed as a background agent.
    helper_command = [sys.executable, "-B", "-m", "PyInstaller", "--onefile", "--console", "--noupx",
        "--name", "CGLSetupGuard", "--distpath", str(root / "guard-dist"), "--workpath", str(root / "guard-work"),
        "--specpath", str(root), "--paths", str(PROJECT), "--icon", str(icon),
        "--add-data", f'{root / "setup-manifest.json"}:.',
        "--add-data", f"{policy_folder}:southpaw_tools/data",
        "--exclude-module", "PySide6", "--exclude-module", "tests", str(PROJECT / "tools/setup_guard.py")]
    with (root / "guard-build.log").open("xb") as log:
        result = subprocess.run(helper_command, cwd=PROJECT, env=build_environment(root),
                                stdout=log, stderr=subprocess.STDOUT, timeout=300)
    if result.returncode:
        raise LauncherError("설치 검증 도구 빌드 실패")
    setup = compile_setup(root, compiler)
    test_setup = compile_setup(root, compiler, test_registration=True)
    save(root / "setup-result.json", {"setup": str(setup), "sha256": digest(setup), "size": setup.stat().st_size,
        "test_setup": str(test_setup), "setup_version": SETUP_VERSION, "launcher_version": launcher.version,
        "official_seed_preserved": True, "bootstrap_sha256": digest(payload / "CGLBootstrap.exe"),
        "nsis_version": subprocess.check_output([str(compiler), "/VERSION"], text=True).strip()})
    return setup


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--nsis", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(prepare(args.root, args.zip, args.nsis.resolve()))
        return 0
    except (LauncherError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
