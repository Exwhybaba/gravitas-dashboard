# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Gravitas Power App (One-file version)
Faster build - bundles everything into a single executable
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
        'itsdangerous', 'markupsafe', 'typing_extensions', 'six', 'retrying', 'nest_asyncio',
        'decorator', 'executing', 'asttokens', 'colorama', 'certifi', 'charset_normalizer',
        'idna', 'requests', 'urllib3', 'blinker', 'cycler', 'fonttools', 'kiwisolver',
        'numpy', 'packaging', 'pillow', 'pyparsing', 'python_dateutil', 'pytz', 'scipy',
        'contourpy', 'networkx',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
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
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
