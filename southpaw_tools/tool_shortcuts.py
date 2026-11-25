"""Stable desktop links for verified managed tool releases."""
import os
from pathlib import Path
import re
import subprocess

from .common import LauncherError, identifier, inside
from .paths import AppPaths
from .self_update import APP_ID, SelfUpdater


def launch_tool(home, channel, app_id):
    from .catalog_trust import CatalogVerifier
    from .channel_bridge import BridgedAppVerifier, legacy_binding
    from .installer import Installer

    identifier(app_id)
    if app_id == APP_ID:
        raise LauncherError("런처 자체는 도구 바로가기로 실행할 수 없습니다.")
    updater = SelfUpdater(home, channel=channel)
    engine = Installer(AppPaths(updater.data_root))
    engine.catalog_verifier = CatalogVerifier(channel["policy"], updater.data_root / "catalog-trust.json")
    if legacy_binding(updater.home, updater.data_root):
        engine.catalog_verifier = BridgedAppVerifier(channel["policy"], inside(updater.home, "app-catalog-trust.json"))
    if engine.is_running(app_id):
        return ("열린 도구 창으로 이동했습니다." if engine.processes.activate(engine.paths.app(app_id))
                else "이미 실행 중입니다. 작업 표시줄에서 확인해 주세요.")
    engine.launch(app_id, verify_receipt=True)
    return None


def create_desktop_shortcut(bootstrap, app_id, display_name):
    return _create_shortcut(bootstrap, app_id, display_name)


def _create_shortcut(bootstrap, app_id, display_name, desktop=None):
    identifier(app_id)
    bootstrap = Path(bootstrap).resolve()
    if os.name != "nt" or not bootstrap.is_file():
        raise LauncherError("도구 바로가기를 지원하는 Windows Bootstrap을 확인할 수 없습니다.")
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", display_name).strip(". ")[:96] or app_id
    # The script is constant; paths and display names are data, never PowerShell source.
    env = {**os.environ, "SOUTHPAW_LINK_TARGET": str(bootstrap),
           "SOUTHPAW_LINK_ARGS": f"--launch-tool {app_id}",
           "SOUTHPAW_LINK_NAME": f"{title} (Southpaw).lnk",
           "SOUTHPAW_LINK_FOLDER": str(desktop) if desktop is not None else ""}
    script = r"""
$ErrorActionPreference = 'Stop'
$desktop = $env:SOUTHPAW_LINK_FOLDER
if (-not $desktop) { $desktop = [Environment]::GetFolderPath('DesktopDirectory') }
if (-not $desktop -or -not [IO.Directory]::Exists($desktop)) { throw 'Desktop is unavailable' }
$target = $env:SOUTHPAW_LINK_TARGET
$argsText = $env:SOUTHPAW_LINK_ARGS
$path = Join-Path $desktop $env:SOUTHPAW_LINK_NAME
$shell = New-Object -ComObject WScript.Shell
if ([IO.File]::Exists($path)) {
    if ((Get-Item -LiteralPath $path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { 'conflict'; exit }
    $existing = $shell.CreateShortcut($path)
    if ($existing.TargetPath -eq $target -and $existing.Arguments -ceq $argsText) { 'exists' } else { 'conflict' }
    exit
}
$temp = Join-Path $desktop ('.southpaw-' + [Guid]::NewGuid().ToString('N') + '.lnk')
try {
    $link = $shell.CreateShortcut($temp)
    $link.TargetPath = $target
    $link.Arguments = $argsText
    $link.WorkingDirectory = [IO.Path]::GetDirectoryName($target)
    $link.Save()
    [IO.File]::Move($temp, $path)
    'created'
} finally {
    [IO.File]::Delete($temp)
}
"""
    try:
        powershell = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        result = subprocess.run([str(powershell), "-NoProfile", "-NonInteractive", "-Command", script],
                                env=env, capture_output=True, timeout=10,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LauncherError("바탕화면 바로가기를 만들지 못했습니다.") from exc
    value = result.stdout.strip()
    if value == b"conflict":
        raise LauncherError("같은 이름의 기존 바로가기를 보존했습니다.")
    if result.returncode or value not in {b"created", b"exists"}:
        raise LauncherError("바탕화면 바로가기를 만들지 못했습니다.")
    return value == b"created"
