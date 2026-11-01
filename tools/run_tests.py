"""Run the full suite and expose failures as GitHub Actions annotations."""
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
suite = unittest.defaultTestLoader.discover(str(root / 'tests'), top_level_dir=str(root))
result = unittest.TextTestRunner(verbosity=2).run(suite)
for case, traceback in result.failures + result.errors:
    message = (str(case) + '\n' + traceback).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::error title=Prueba fallida::' + message, flush=True)
raise SystemExit(0 if result.wasSuccessful() else 1)
