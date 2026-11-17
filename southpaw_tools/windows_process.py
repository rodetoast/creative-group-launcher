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
