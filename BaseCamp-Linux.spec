# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['appentry.py'],
    pathex=[],
    binaries=[],
    datas=[('lang', 'lang'), ('resources', 'resources'), ('default_presets.json', '.'), ('default_makalu_presets.json', '.'), ('default_presets_60.json', '.'), ('plugins', 'plugins')],
    hiddenimports=['PIL', 'PIL._tkinter_finder', 'PIL._imagingtk', 'psutil', 'pystray', 'obsws_python',
                   'devices.macros', 'devices.macros.panel', 'shared.macros',
                   'devices.plugins', 'devices.plugins.panel', 'shared.plugins', 'shared.plugin_api',
                   'gui'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['_overlay_bootstrap.py'],
    excludes=[],
    # noarchive=True keeps user-side .py files on disk as .pyc inside
    # _internal/, which lets the runtime hook prepend an overlay dir to
    # sys.path and have user modules resolved from there. Bundled 3rd-party
    # deps still come from PYZ for size — only user code is overlay-able.
    noarchive=True,
    optimize=0,
)

# Remove bloat: system icon themes, locales, themes bundled from Fedora
import os
a.datas = [
    (dst, src, kind)
    for dst, src, kind in a.datas
    if not dst.startswith('share/icons/')
    and not dst.startswith('share/locale/')
    and not dst.startswith('share/themes/')
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BaseCamp-Linux',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='BaseCamp-Linux',
)
