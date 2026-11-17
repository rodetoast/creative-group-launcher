"""Installer checks for the owned Bootstrap files; user data is never removed."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path

from .common import LauncherError, atomic_json, atomic_temp_example, digest, inside, read_json
from .catalog import AppRelease
from .installer import Installer
from .paths import AppPaths
from .self_update import APP_ID, MANAGED_PURPOSE
from .windows_paths import windows_path_budget
from .windows_process import identity
from .windows_shell import APP_ID as SHELL_APP_ID, GUID, _check, _method, shortcut_app_id, shortcut_identity

PRODUCT = "SouthpawGames.ToolsLauncher.Setup"
STATE = "setup-state.json"


def _running(root, state):
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    pids = (wintypes.DWORD * 65536)()
    used = wintypes.DWORD()
    if not psapi.EnumProcesses(pids, ctypes.sizeof(pids), ctypes.byref(used)):
        raise ctypes.WinError(ctypes.get_last_error())
    for pid in pids[:used.value // ctypes.sizeof(wintypes.DWORD)]:
        if pid in (0, os.getpid()):
            continue
        try:
            info = identity(pid)
        except OSError as exc:
            if exc.winerror == 5:
                continue
            raise
        if not info:
            continue
        image = Path(info["image"]).resolve()
        if image.is_relative_to(root):
            if (image == root / "Uninstall.exe" and state
                    and state.get("uninstaller_sha256") == digest(image)):
                continue
            raise LauncherError("런처가 실행 중입니다. 정상 종료한 뒤 다시 시도해 주세요.")


def check(root, data, manifest, *, uninstall=False, inspect_processes=True):
    root, data = Path(root).absolute(), Path(data).absolute()
    if (root.resolve() != root or data.resolve() != data or root == root.parent
            or root.is_relative_to(data) or data.is_relative_to(root)):
        raise LauncherError("설치 폴더와 사용자 데이터 폴더를 별도로 지정해 주세요.")
    state_path = inside(root, STATE)
    state = read_json(state_path) if state_path.exists() else None
    if state and (state.get("product") != PRODUCT or state.get("data_root") != str(data)):
        raise LauncherError("기존 설치 표식 또는 사용자 데이터 경로가 다릅니다.")
    if not state and root.exists() and any(root.iterdir()):
        raise LauncherError("처음 설치할 때는 비어 있는 새 폴더를 선택해 주세요.")
    layout = inside(root, "launcher-home/layout.json")
    if layout.exists():
        value = read_json(layout)
        if (value.get("purpose") != MANAGED_PURPOSE
                or Path(value.get("user_data_root", "")).resolve() != data):
            raise LauncherError("보존된 런처 저장소의 사용자 데이터 경로가 다릅니다.")
    for name, sha in manifest["files"].items():
        file = inside(root, name)
        if file.exists() and (not file.is_file() or digest(file) != sha):
            raise LauncherError(f"설치 관리 파일이 변경됐습니다. 원본을 보존하고 확인해 주세요: {file.name}")
    if inspect_processes:
        _running(root, state)
    limits = windows_path_budget(root)
    if limits and not uninstall:
        for name in manifest["files"]:
            limits.check(root / name, "최초 설치")
        app = AppRelease.parse(manifest["launcher"])
        store = root / "launcher-home/store"
        engine = Installer(AppPaths(store), plan_uninstall=False)
        tx = "0" * 32
        app_root = engine.paths.app(APP_ID)
        engine._check_control_paths(limits, app_root, tx)
        quarantine = app_root / "recovery" / tx
        destinations = ((store / "staging" / tx, "준비"),
                        (engine.paths.release(APP_ID, app.release_id), "버전 설치"),
                        (quarantine / "aborted-stage", "중단된 준비 보존"),
                        (quarantine / "aborted-release", "중단된 버전 보존"),
                        (quarantine / "previous-release", "이전 버전 보존"))
        for base, phase in destinations:
            for name in manifest["launcher_files"]:
                limits.check(base / "payload" / name, phase)
            for name in ("receipt.json", "catalog-proof.json", "original.zip"):
                limits.check(base / name, phase)
                if name != "original.zip":
                    limits.check(atomic_temp_example(base / name), phase + " 기록")
        limits.check(root / "Uninstall.exe", "제거 프로그램")
    return state


def stamp(root, data, manifest):
    root, data = Path(root).resolve(), Path(data).resolve()
    uninstaller = inside(root, "Uninstall.exe")
    if not uninstaller.is_file():
        raise LauncherError("제거 프로그램이 없습니다.")
    atomic_json(inside(root, STATE), {"product": PRODUCT, "setup_version": manifest["setup_version"],
        "data_root": str(data), "uninstaller_sha256": digest(uninstaller)})


def verify_payload(root, manifest, *, removed=False):
    for name, sha in manifest["files"].items():
        file = inside(Path(root), name)
        if removed:
            if file.exists():
                raise LauncherError(f"프로그램 파일을 제거하지 못했습니다: {file.name}")
        elif not file.is_file() or digest(file) != sha:
            raise LauncherError(f"설치 파일이 없거나 해시가 다릅니다: {file.name}")


def shortcut_target(path):
    ole = ctypes.OleDLL("ole32")
    _check(ole.CoInitializeEx(None, 2))
    link = ctypes.c_void_p()
    persist = ctypes.c_void_p()
    try:
        clsid = GUID.parse("00021401-0000-0000-c000-000000000046")
        iid = GUID.parse("000214f9-0000-0000-c000-000000000046")
        ole.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD,
                                        ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        _check(ole.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(link)))
        persist_iid = GUID.parse("0000010b-0000-0000-c000-000000000046")
        _check(_method(link, 0, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))(
            link, ctypes.byref(persist_iid), ctypes.byref(persist)))
        _check(_method(persist, 5, wintypes.LPCWSTR, wintypes.DWORD)(persist, str(path), 0))
        buffer = ctypes.create_unicode_buffer(32768)
        _check(_method(link, 3, wintypes.LPWSTR, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)(
            link, buffer, len(buffer), None, 4))
        return Path(buffer.value).resolve()
    finally:
        if persist:
            _method(persist, 2)(persist)
        if link:
            _method(link, 2)(link)
        ole.CoUninitialize()


def shortcut(path, root, *, remove=False, check_only=False):
    path, root = Path(path), Path(root).resolve()
    if path.suffix.lower() != ".lnk":
        raise LauncherError("런처 바로가기 파일만 처리할 수 있습니다.")
    if not path.exists():
        return
    if shortcut_target(path) != inside(root, "CGLBootstrap.exe"):
        if remove:
            print("다른 대상으로 변경된 바로가기를 보존했습니다.")
            return
        raise LauncherError("바로가기의 실행 대상이 다릅니다.")
    if check_only:
        if shortcut_app_id(path) != SHELL_APP_ID:
            raise LauncherError("같은 이름의 기존 바로가기가 있습니다. 원본을 보존하고 확인해 주세요.")
        return
    if remove:
        if shortcut_app_id(path) == SHELL_APP_ID:
            path.unlink()
        else:
            print("다른 앱 식별자의 바로가기를 보존했습니다.")
    else:
        shortcut_identity(path)
