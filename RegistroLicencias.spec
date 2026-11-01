from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH)
a = Analysis([str(root / 'vendedor.py')], pathex=[str(root)], binaries=[],
             datas=collect_data_files('customtkinter'), hiddenimports=[],
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['pytest', 'tests', 'matplotlib', 'numpy', 'openpyxl'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='RegistroLicencias',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='RegistroLicencias')
