# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the everest60-controller standalone binary."""

a = Analysis(
    ['everest60_entry.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=['hid', 'devices.everest60.controller'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['_overlay_bootstrap.py'],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='everest60-controller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
