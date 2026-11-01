"""Run the full suite and expose failures as GitHub Actions annotations."""
from pathlib import Path
import os
import sys
import traceback
import unittest

for stream in (sys.stdout,sys.stderr):
    if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',errors='backslashreplace')

def report(text):
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a',encoding='utf-8') as file:file.write(text+'\n')

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
try:
    suite = unittest.defaultTestLoader.discover(str(root / 'tests'), top_level_dir=str(root))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
except BaseException:
    details=traceback.format_exc()
    report('La ejecución de pruebas no terminó.\n\n```text\n'+details+'\n```')
    message=details.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
    print('::error title=Ejecución de pruebas::'+message,flush=True)
    raise
report(f'Pruebas: {result.testsRun}; fallos: {len(result.failures)}; errores: {len(result.errors)}; omitidas: {len(result.skipped)}.')
for case, details in result.failures + result.errors:
    report('```text\n'+str(case)+'\n'+details+'\n```')
    message = (str(case) + '\n' + details).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::error title=Prueba fallida::' + message, flush=True)
raise SystemExit(0 if result.wasSuccessful() else 1)
