# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec para ADB Forensic Helper
# Compilar con:  pyinstaller build.spec
#
# Genera: dist/ADB_Forensic_Helper/ADB_Forensic_Helper.exe

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Archivos adicionales a incluir en el bundle
added_files = [
    # Incluir adb.exe y sus DLLs si existen en assets/adb/
    ('assets/adb/adb.exe',          'assets/adb'),
    ('assets/adb/AdbWinApi.dll',    'assets/adb'),
    ('assets/adb/AdbWinUsbApi.dll', 'assets/adb'),
]

# Filtrar solo los que existen
added_files = [(src, dst) for src, dst in added_files if os.path.exists(src)]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'wmi',
        'win32api',
        'win32con',
        'win32com',
        'win32com.client',
        'pythoncom',
        'pywintypes',
        'winsound',
        'webbrowser',
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'core.history_manager',
        'core.update_checker',
        'core.avilla_compat',
    ] + collect_submodules('win32'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'PIL',
        'scipy', 'IPython', 'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ADB_Forensic_Helper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # Sin ventana de consola negra
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',  # Descomentar si tienes un icono
    uac_admin=True,           # Solicitar elevación a administrador al ejecutar
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ADB_Forensic_Helper',
)
