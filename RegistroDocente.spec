# Build on each target OS. Do not bundle user databases or private signing keys.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH)
datas = collect_data_files('customtkinter')
binaries = []
# Standalone Python distributions can keep Tcl/Tk outside ldconfig's search path.
# Include their own libraries rather than silently producing a broken executable.
if sys.platform.startswith('linux'):
    for pattern in ('libtcl*.so', 'libtk*.so'):
        binaries.extend((str(path), '.') for path in (Path(sys.base_prefix) / 'lib').glob(pattern))
key_file = root / 'license_public_key.pem'
public_key = key_file.read_bytes() if key_file.exists() else b''
# Embed the edition policy and public key in the executable's runtime hook.
# Deleting a loose PEM file must not turn a commercial build into a free build.
license_hook = root / 'build' / 'registro_license_hook.py'
license_hook.parent.mkdir(parents=True, exist_ok=True)
license_hook.write_text('import sys\nsys._registro_license_public_key = ' + repr(public_key) + '\n', encoding='utf-8')
a = Analysis([str(root / 'main.py')], pathex=[str(root)], binaries=binaries, datas=datas,
             hiddenimports=['matplotlib.backends.backend_tkagg', 'cryptography.hazmat.primitives.asymmetric.ed25519'],
             hookspath=[], hooksconfig={}, runtime_hooks=[str(license_hook)], excludes=['pytest', 'tests'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='RegistroDocente',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='RegistroDocente')
