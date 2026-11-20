"""Read-only identity checks for the exact Windows processes created by bootstrap."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path

from .common import LauncherError
from .bootstrap_diagnostics import mark


def identity(pid: int):
    if os.name != 'nt' or type(pid) is not int or pid <= 0:
        raise LauncherError('Windows 프로세스 식별자 오류')
    dll=ctypes.WinDLL('kernel32',use_last_error=True)
    dll.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    dll.OpenProcess.restype=wintypes.HANDLE
    dll.CloseHandle.argtypes=[wintypes.HANDLE]
    dll.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    dll.WaitForSingleObject.restype=wintypes.DWORD
    dll.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
    dll.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    access = 0x1000 | 0x100000
    def failure(operation, api, code=None):
        error = ctypes.WinError(ctypes.get_last_error() if code is None else code)
        mark(error, operation, api=api, pid=pid, access=access)
        return error
    handle=dll.OpenProcess(access,False,pid)
    if not handle:
        code=ctypes.get_last_error()
        if code==87:
            return None
        raise failure('process_identity_open', 'OpenProcess', code)
    try:
        waited=dll.WaitForSingleObject(handle,0)
        if waited==0:
            return None
        if waited!=258:
            raise failure('process_identity_wait', 'WaitForSingleObject')
        times=[wintypes.FILETIME() for _ in range(4)]
        if not dll.GetProcessTimes(handle,*[ctypes.byref(v) for v in times]):
            raise failure('process_identity_times', 'GetProcessTimes')
        buffer=ctypes.create_unicode_buffer(32768)
        length=wintypes.DWORD(len(buffer))
        if not dll.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(length)):
            raise failure('process_identity_image', 'QueryFullProcessImageNameW')
        created=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime
        return {'pid':pid,'created_ticks':str(created),'image':str(Path(buffer.value).resolve())}
    finally:
        dll.CloseHandle(handle)


def still_same(record):
    current=identity(record['pid'])
    return bool(current and current['created_ticks']==record['created_ticks']
                and current['image'].casefold()==record['image'].casefold())


def parent_pid(pid):
    """Return the recorded parent PID of a running Windows process."""
    class ProcessEntry(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("usage", wintypes.DWORD),
                    ("pid", wintypes.DWORD), ("heap", ctypes.c_size_t),
                    ("module", wintypes.DWORD), ("threads", wintypes.DWORD),
                    ("parent", wintypes.DWORD), ("priority", wintypes.LONG),
                    ("flags", wintypes.DWORD), ("exe", wintypes.WCHAR * 260)]

    dll = ctypes.WinDLL("kernel32", use_last_error=True)
    dll.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    dll.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    dll.CloseHandle.argtypes = [wintypes.HANDLE]
    for func in (dll.Process32FirstW, dll.Process32NextW):
        func.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
        func.restype = wintypes.BOOL
    snapshot = dll.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        item = ProcessEntry()
        item.size = ctypes.sizeof(item)
        found = dll.Process32FirstW(snapshot, ctypes.byref(item))
        while found:
            if item.pid == pid:
                return item.parent
            found = dll.Process32NextW(snapshot, ctypes.byref(item))
        return None
    finally:
        dll.CloseHandle(snapshot)
