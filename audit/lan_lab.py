"""Prepare/guard a dummy-only LAN lab. No installer or publishing reimplementation.

All generated tokens, packages and installations stay below .test-results.
Use existing southpaw_tools.admin for publishing. Serve defaults to LAN OFF;
LAN ON additionally requires --approve-lan and is never enabled by prepare.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import secrets
import shutil

from southpaw_tools.admin import publish
from southpaw_tools.catalog import catalog_document, load_catalog
from southpaw_tools.common import LauncherError, atomic_json, digest, inside, plain_tree, read_json
from southpaw_tools.catalog_trust import CATALOG_ID, b64, key_id
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from southpaw_tools.server import main as server_main

PROJECT = Path(__file__).resolve().parents[1]
FIXTURES = PROJECT / ".test-results/lan-rehearsal"
MARKER = "southpaw-dummy-lan-lab-v1"
HASHES = {
    "r1": ("9cddb17a5a03ce5aac5241f9e1f7f2bc3296f0b7988c07abfae9a102248ccca5",
           "16bd988d83c239c525e9248db6210effe9c89a35c8ac774496ef58eb2216a79d"),
    "r2": ("9908efac1b1fecc3a23628f9370a7285c8f14249308c25a70488bb9df985ae99",
           "7a3e3a37c96ebae4f6afa366b120564949f2801012e6dc77e2a71f7ffa198dd1"),
}


def location(root: Path) -> Path:
    # Requiring the ignored test root also prevents accidentally staging secrets.
    absolute = root.absolute()
    try:
        relative = absolute.relative_to(PROJECT).as_posix()
    except ValueError as exc:
        raise LauncherError("시험 루트는 이 프로젝트의 .test-results 하위여야 합니다.") from exc
    checked = inside(PROJECT, relative)
    if not checked.is_relative_to(PROJECT / ".test-results") or checked == PROJECT / ".test-results":
        raise LauncherError("시험 루트는 .test-results 안의 독립 하위 폴더여야 합니다.")
    return checked


def fixture(build: str):
    app = load_catalog(inside(PROJECT, f".test-results/lan-rehearsal/{build}/catalog.json"))[0]
    source = inside(PROJECT, f".test-results/lan-rehearsal/{build}/packages/{app.package_name}")
    if (app.app_id != "lan-smoke" or app.release_id != f"lan-smoke-{build}"
            or (app.sha256, app.executable_sha256) != HASHES[build]
            or digest(source) != HASHES[build][0]):
        raise LauncherError("고정 감사 fixture와 불일치합니다. 재빌드/대체하지 않습니다.")
    return source, app


def publish_fixture(root: Path, build: str):
    """Delegate validation/staging/atomic publishing to the existing implementation."""
    _, app = fixture(build)
    return publish(root / "repository", "lan-smoke", root / "inputs" / f"{build}.zip",
                   version=app.version, release_id=app.release_id,
                   executable=app.executable_relative_path, expected_sha256=app.sha256,
                   expected_exe_sha256=app.executable_sha256, approved=True,
                   notes=app.release_notes, cwd=".", signing_key=root / "test-only-signing.pem",
                   sequence=read_json(root / "repository/catalog.json").get("sequence", 0) + 1)


def prepare(root: Path):
    root = location(root)
    sources = {build: fixture(build) for build in HASHES}
    root.mkdir(parents=True, exist_ok=False)
    (root / "inputs").mkdir()
    repo = root / "repository"
    repo.mkdir()
    seed = replace(sources["r1"][1], published=False)
    atomic_json(repo / "catalog.json", catalog_document([seed]))
    atomic_json(root / "lab.json", {"purpose": MARKER, "transport": "HTTP", "test_key_only": True})
    # Only new dummy environments receive a test key; never modify a historic lab.
    private = Ed25519PrivateKey.generate()
    with (root / "test-only-signing.pem").open("xb") as stream:
        stream.write(private.private_bytes(serialization.Encoding.PEM,
                     serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    public = private.public_key().public_bytes_raw()
    test_policy = {"schema_version": 1, "catalog_id": CATALOG_ID, "minimum_sequence": 1,
                   "keys": {key_id(public): b64(public)}}
    atomic_json(root / "TEST_ONLY_TRUST.json", test_policy)
    for build, (source, app) in sources.items():
        shutil.copyfile(source, root / "inputs" / f"{build}.zip")
        (root / "inputs" / f"{build}.md").write_text(app.release_notes, encoding="utf-8")
    publish_fixture(root, "r1")
    config = dict(server_enabled=True, port=8765, lan_enabled=False, lan_host="",
                  lan_token=secrets.token_hex(32), internet_enabled=False)
    atomic_json(root / "server.local.json", config)
    atomic_json(root / "server.example.json", {**config, "lan_token": ""})
    # Local source-transfer candidate only: no package archives, settings or tokens.
    bundle = root / "client-bundle"
    bundle.mkdir()
    shutil.copytree(PROJECT / "southpaw_tools", bundle / "southpaw_tools",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "assets"))
    atomic_json(bundle / "southpaw_tools/data/trusted_catalog_keys.json", test_policy)
    (bundle / "TEST_ONLY.txt").write_text("Dummy test key only. Never use for staff deployment.\n", encoding="utf-8")
    document = read_json(repo / "catalog.json")
    atomic_json(bundle / "southpaw_tools/data/catalog.json", document)
    atomic_json(bundle / "audit-catalog.json", document)
    shutil.copyfile(PROJECT / "requirements.txt", bundle / "requirements.txt")
    (bundle / "start_dummy.ps1").write_text(
        'param([Parameter(Mandatory=$true)][string]$Python,\n'
        '      [Parameter(Mandatory=$true)][string]$DataDirectory)\n'
        'Set-Location -LiteralPath $PSScriptRoot\n'
        '& $Python -B -m southpaw_tools --catalog "$PSScriptRoot/audit-catalog.json" --data-dir "$DataDirectory"\n',
        encoding="utf-8")
    return validate(root)


def validate(root: Path):
    root = location(root)
    if read_json(inside(root, "lab.json")).get("purpose") != MARKER:
        raise LauncherError("더미 시험 환경 표식이 없습니다.")
    # Reject junctions/symlinks anywhere in this small, dedicated lab.
    for file in plain_tree(root):
        if file.is_symlink() or file.is_junction():
            raise LauncherError("시험 환경에 링크/정션이 있습니다.")
    apps = load_catalog(root / "repository/catalog.json")
    if len(apps) != 1:
        raise LauncherError("더미 앱 한 개만 허용합니다.")
    app = apps[0]
    build = app.release_id.removeprefix("lan-smoke-")
    if (app.app_id != "lan-smoke" or build not in HASHES or not app.published
            or (app.sha256, app.executable_sha256) != HASHES[build]
            or app.executable_relative_path != "LanSmoke.exe"
            or app.working_directory_relative_path != "."
            or app.required_paths != ["asset.json"] or app.preserve_paths != ["settings.json"]
            or app.package_name != f"lan-smoke--lan-smoke-{build}.zip"):
        raise LauncherError("실제 프로그램/알 수 없는 배포본은 시험 서버에서 거부합니다.")
    packages = root / "repository/packages"
    allowed = {f"lan-smoke--lan-smoke-{b}.zip": hashes[0] for b, hashes in HASHES.items()}
    for file in packages.iterdir():
        if not file.is_file() or file.name not in allowed or digest(file) != allowed[file.name]:
            raise LauncherError("더미 이외 패키지 또는 변조 파일이 있습니다.")
    if not (packages / app.package_name).is_file():
        raise LauncherError("현재 더미 패키지가 없습니다.")
    for b, hashes in HASHES.items():
        if digest(root / "inputs" / f"{b}.zip") != hashes[0]:
            raise LauncherError("시험 입력 ZIP 불일치")
    for catalog in (root / "client-bundle/audit-catalog.json",
                    root / "client-bundle/southpaw_tools/data/catalog.json"):
        client_apps = load_catalog(catalog)
        if len(client_apps) != 1 or client_apps[0].app_id != "lan-smoke":
            raise LauncherError("시험 client에 실제 프로그램 목록이 있습니다.")
    token = read_json(root / "server.local.json").get("lan_token", "")
    for file in (root / "client-bundle").rglob("*"):
        if not file.is_file():
            continue
        if (file.suffix.lower() in {".zip", ".exe", ".dll"} or file.name.endswith(".local.json")
                or file.name in {"settings.json", "catalog-cache.json", "active.json", "receipt.json"}):
            raise LauncherError("시험 client에 패키지/사용자 설정을 포함할 수 없습니다.")
        if token and token.encode() in file.read_bytes():
            raise LauncherError("시험 client에 비밀 토큰이 있습니다.")
    return {"dummy_only": True, "current_release": app.release_id, "transport": "HTTP",
            "catalog_signed": (root / "repository/catalog.sig.json").is_file(),
            "server_authenticated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check", "serve"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--approve-lan", action="store_true",
                        help="Only after separate company/user LAN test approval")
    args = parser.parse_args()
    try:
        root = location(args.root)
        result = prepare(root) if args.action == "prepare" else validate(root)
        if args.action == "serve":
            config = read_json(root / "server.local.json")
            if config.get("lan_enabled") and not args.approve_lan:
                raise LauncherError("실제 LAN 시험 별도 승인 후 --approve-lan을 명시하세요. 포트를 열지 않았습니다.")
            return server_main(["--root", str(root / "repository"), "--config", str(root / "server.local.json")])
        print(result)  # Never print config/token.
        return 0
    except (LauncherError, OSError) as exc:
        print(f"시험 환경 확인 실패: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
