# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller ToolClick.spec  (hoặc .\build_exe.ps1)

from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

datas = [
    (str(root / "desktop_app.py"), "."),
    (str(root / "main.py"), "."),
    (str(root / "open_browser.py"), "."),
    (str(root / "toolclick_paths.py"), "."),
    (str(root / "src"), "src"),
    (str(root / "config.example.env"), "."),
]

hiddenimports = [
    "pandas",
    "openpyxl",
    "dotenv",
    "playwright",
    "playwright.sync_api",
    "src.google_scraper",
    "src.job_runner",
    "src.domain_filter",
    "src.ui_common",
    "src.license_client",
    "main",
    "open_browser",
    "desktop_app",
    "tkinter",
    "tkinter.ttk",
    "tkinter.scrolledtext",
    "tkinter.messagebox",
    "tkinter.filedialog",
]

a = Analysis(
    [str(root / "toolclick_entry.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["streamlit", "altair", "pyarrow"],
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
    name="ToolClick",
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
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ToolClick",
)
