# -*- mode: python ; coding: utf-8 -*-
import os, glob


def _find_libusb():
    """Locate libusb-1.0 across distros (Fedora /usr/lib64, Debian multiarch …)
    so this spec builds on any of them."""
    cands = ["/usr/lib64/libusb-1.0.so.0",
             "/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0",
             "/usr/lib/libusb-1.0.so.0"]
    cands += glob.glob("/usr/lib*/**/libusb-1.0.so.0", recursive=True)
    for p in cands:
        if os.path.exists(p):
            return [(p, '.')]
    return []


a = Analysis(
    ['emax_entry.py'],
    pathex=['.'],
    binaries=_find_libusb(),
    datas=[],
    hiddenimports=['PIL', 'psutil', 'obsws_python', 'usb', 'usb.core', 'usb.util', 'usb.backend.libusb1',
                   'emax_controller', 'shared.ipc', 'shared.macros', 'shared.config'],
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
