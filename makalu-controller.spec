# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['makalu_entry.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=['hid', 'devices.makalu67.controller'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['_overlay_bootstrap.py'],
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
    name='makalu-controller',
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
