# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Collecter tous les fichiers templates et static
added_files = [
    ('templates', 'templates'),
    ('static', 'static'),
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.cell._writer',
        'openpyxl.worksheet',
        'openpyxl.worksheet._writer',
        'openpyxl.styles',
        'openpyxl.styles.stylesheet',
        'openpyxl.xml.functions',
        'openpyxl.chartsheet',
        'openpyxl.packaging.manifest',
        'werkzeug',
        'flask',
        'jinja2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FusionMMECSV',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # PAS DE FENÊTRE CMD !
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'  # Icône Xbox verte
)
