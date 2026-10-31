# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import re
from PyInstaller.utils.hooks import collect_all

datas = [(str(Path(SPECPATH) / 'assets'), 'assets')]
binaries = []
hiddenimports = ['_cffi_backend']
tmp_ret = collect_all('nacl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    [str(Path(SPECPATH) / 'terabox_local.py')],
    pathex=[SPECPATH],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# Usar ICU del sistema Windows, no una DLL ajena descubierta en PATH.
a.binaries = [item for item in a.binaries if not re.fullmatch(r'icu(?:uc|dt|in)[0-9]*[.]dll', item[0].lower())]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='InfinityMedBoveda-v2.1',
    icon=str(Path(SPECPATH) / 'assets' / 'infinity-med.ico'),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
