"""Read-only preflight for the exclusive access needed to replace a forecast DSS."""
import os
from pathlib import Path


def check_forecast_access(filename):
    path = Path(filename)
    if not path.is_file():
        raise FileNotFoundError('Forecast DSS does not exist: ' + str(path))
    try:
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            create = kernel.CreateFileW
            create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                               ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
            create.restype = wintypes.HANDLE
            close = kernel.CloseHandle
            close.argtypes = [wintypes.HANDLE]
            close.restype = wintypes.BOOL
            # Read/write/delete access, no sharing, OPEN_EXISTING. Never write,
            # truncate, rename, delete, or take another process's handle.
            handle = create(str(path.resolve()), 0x80000000 | 0x40000000 | 0x00010000,
                            0, None, 3, 0x80, None)
            if handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            close(handle)
        else:
            with path.open('r+b') as handle:
                handle.read(1)
    except OSError as error:
        message = ('Forecast DSS is locked or inaccessible: ' + str(path) + '. '
                   'Finish any compute, close DSSVue/results windows, and close the forecast in RTS. '
                   'Leave RTS and the workflow GUI running. Select "Use this displayed forecast after closing it in RTS", '
                   'then retry Process and Load Releases. Do not re-extract. No calculation or loading was started.')
        print('WORKFLOW_ERROR: ' + message, flush=True)
        raise PermissionError(message) from error
