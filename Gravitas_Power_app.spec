# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Gravitas Power App
Bundles app.py with all dependencies and assets
"""

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'dash', 'dash_bootstrap_components', 'plotly', 'plotly.express', 'plotly.graph_objects',
        'plotly.subplots', 'seaborn', 'pandas', 'flask', 'werkzeug', 'jinja2', 'click',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludedimports=['matplotlib.backends.backend_qt5agg'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Gravitas_Power_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
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
    upx=True,
    upx_exclude=[],
    name='Gravitas_Power_app',
)
