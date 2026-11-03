"""Build a harmless .NET console fixture; never start a LAN listener.

Requires the Windows .NET Framework compiler already installed on this PC.
Creates a NEW isolated directory only. Does not run the generated executable.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import zipfile

from southpaw_tools.catalog import AppRelease, catalog_document
from southpaw_tools.common import atomic_json, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    compiler = Path(os.environ.get("WINDIR", "C:/Windows")) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    if not compiler.is_file():
        parser.error("Existing .NET Framework compiler not found; no SDK is installed automatically.")
    root.mkdir(parents=True, exist_ok=False)
    for number in (1, 2):
        build = f"lan-smoke-r{number}"
        source = root / f"Fixture{number}.cs"
        source.write_text('using System; class Fixture { static int Main() { '
                          f'Console.WriteLine("Southpaw harmless LAN fixture: {build}; offline OK"); '
                          'return 0; } }', encoding="utf-8")
        exe = root / f"Fixture{number}.exe"
        subprocess.run([str(compiler), "/nologo", "/target:exe", f"/out:{exe}", str(source)], check=True)
        repo = root / f"r{number}"
        packages = repo / "packages"
        packages.mkdir(parents=True)
        archive = packages / f"{build}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
            handle.write(exe, "LanSmoke.exe")
            handle.writestr("asset.json", '{"purpose":"isolated LAN audit only"}')
        app = AppRelease.parse(dict(
            app_id="lan-smoke", display_name="LAN Smoke Test (dummy)", category="Audit",
            description="Harmless console fixture; no existing production tool is included.",
            version="0.0.1", release_id=build, published=True,
            published_at="2026-11-03T00:00:00+00:00", package_name=archive.name,
            package_size=archive.stat().st_size, sha256=digest(archive),
            executable_relative_path="LanSmoke.exe", executable_sha256=digest(exe),
            working_directory_relative_path=".", required_paths=["asset.json"],
            preserve_paths=["settings.json"], release_notes=f"# Dummy LAN test\n\nBuild {number}; version unchanged."))
        atomic_json(repo / "catalog.json", catalog_document([app]))
        atomic_json(repo / "server.json", dict(server_enabled=True, port=8765,
                                              lan_enabled=False, lan_host="", lan_token="", internet_enabled=False))
        print(f"{build}: ZIP SHA-256 {app.sha256}; EXE SHA-256 {app.executable_sha256}")
    print(f"Prepared only (no server started; no fixture executed): {root}")


if __name__ == "__main__":
    main()
