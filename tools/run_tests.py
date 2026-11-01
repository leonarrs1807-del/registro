"""Run the full suite and expose failures as GitHub Actions annotations."""
from pathlib import Path
import os
import subprocess
import sys
import traceback
import unittest

for stream in (sys.stdout,sys.stderr):
    if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',errors='backslashreplace')

def report(text):
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a',encoding='utf-8') as file:file.write(text+'\n')

if '--child' not in sys.argv:
    # A native Tcl/Tk crash cannot be caught by Python. Keep the reporter outside
    # the GUI process so Windows failures still include the active test/stack.
    try:
        completed=subprocess.run([sys.executable,'-X','faulthandler',str(Path(__file__).resolve()),'--child'],
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace',timeout=600)
        output=completed.stdout;code=completed.returncode
    except subprocess.TimeoutExpired as exc:
        output=exc.stdout or b''
        if isinstance(output,bytes):output=output.decode('utf-8',errors='replace')
        output+='\nLas pruebas no terminaron en 600 segundos.';code=1
    sys.stdout.write(output);sys.stdout.flush()
    if code:
        details=f'Proceso de pruebas terminó con código {code}.\n'+output[-24000:]
        report('```text\n'+details+'\n```')
        message=details.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
        print('::error title=Diagnóstico del proceso de pruebas::'+message,flush=True)
    raise SystemExit(0 if code==0 else 1)

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
