# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['mountain-time-sync.py'],
    pathex=[],
    binaries=[('/usr/lib64/libusb-1.0.so.0', '.')],
    datas=[],
    hiddenimports=['PIL', 'psutil', 'obsws_python', 'usb', 'usb.core', 'usb.util', 'usb.backend.libusb1'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='basecamp-controller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
