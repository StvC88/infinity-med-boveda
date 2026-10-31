"""Apertura de origen con compartición de sólo lectura en Windows.

Sin promesa de snapshot frente a drivers, mappings ya existentes o un SO hostil.
"""
from contextlib import contextmanager
import os
from pathlib import Path


@contextmanager
def stable_source(path, allow_delete=False):
    path = Path(os.path.abspath(path))
    if os.name != 'nt':
        if allow_delete:
            raise OSError('La eliminación por identidad sólo está habilitada en Windows.')
        with path.open('rb') as f:
            yield f
        return
    import ctypes
    from ctypes import wintypes
    import msvcrt
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateFileW.argtypes = [wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    api.CreateFileW.restype = wintypes.HANDLE
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    api.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD,wintypes.DWORD]
    api.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    class AttributeTag(ctypes.Structure):
        _fields_ = [('attributes',wintypes.DWORD),('tag',wintypes.DWORD)]
    api.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    api.GetFileInformationByHandleEx.restype = wintypes.BOOL
    handle = api.CreateFileW(str(path),0x80000000 | (0x10000 if allow_delete else 0),1,None,3,0x00200000 | 0x08000000,None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    owned = True
    try:
        info = AttributeTag()
        if not api.GetFileInformationByHandleEx(handle,9,ctypes.byref(info),ctypes.sizeof(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        if info.attributes & (0x400 | 0x10):
            raise OSError('El origen no es un archivo regular sin reparse points.')
        buffer = ctypes.create_unicode_buffer(32768)
        size = api.GetFinalPathNameByHandleW(handle,buffer,len(buffer),0)
        if size == 0 or size >= len(buffer):
            raise OSError('No se pudo validar la identidad del origen abierto.')
        final = buffer.value
        if final.startswith('\\\\?\\UNC\\'):
            final = '\\\\' + final[8:]
        elif final.startswith('\\\\?\\'):
            final = final[4:]
        if os.path.normcase(final) != os.path.normcase(str(path)):
            raise OSError('La ruta abierta no coincide con el origen seleccionado.')
        fd = msvcrt.open_osfhandle(int(handle),os.O_RDONLY | os.O_BINARY)
        owned = False
        with os.fdopen(fd,'rb') as f:
            yield f
    finally:
        if owned:
            api.CloseHandle(handle)


def delete_recorded_partial(path, identity):
    """Borra el archivo ABIERTO y validado, sin resolver de nuevo su ruta al borrar."""
    import ctypes
    from ctypes import wintypes
    import msvcrt
    with stable_source(path, allow_delete=True) as f:
        info = os.fstat(f.fileno())
        if [info.st_dev, info.st_ino] != list(identity):
            raise OSError('El archivo cambió de identidad; se conserva.')
        api = ctypes.WinDLL('kernel32',use_last_error=True)
        api.SetFileInformationByHandle.argtypes = [wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        api.SetFileInformationByHandle.restype = wintypes.BOOL
        flag = wintypes.BOOL(True)
        if not api.SetFileInformationByHandle(msvcrt.get_osfhandle(f.fileno()),4,ctypes.byref(flag),ctypes.sizeof(flag)):
            raise ctypes.WinError(ctypes.get_last_error())
