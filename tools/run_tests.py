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

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
names=[arg for arg in sys.argv[1:] if arg not in ('--child','--isolate-gui')]

def load_suite(names):
    if names:return unittest.defaultTestLoader.loadTestsFromNames(names)
    return unittest.defaultTestLoader.discover(str(root / 'tests'), top_level_dir=str(root))

def case_ids(suite):
    for test in suite:
        if isinstance(test,unittest.TestSuite):yield from case_ids(test)
        else:yield test.id()

def run_child(batch):
    # A native Tcl/Tk crash cannot be caught by Python. Keep the reporter outside
    # the GUI process so Windows failures still include the active test/stack.
    try:
        completed=subprocess.run([sys.executable,'-X','faulthandler',str(Path(__file__).resolve()),'--child',*batch],
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
        # GitHub truncates each displayed annotation at about 4 KB. Put the
        # native stack at the front and keep each piece independently readable.
        pieces=[details[i:i+3000] for i in range(0,len(details),3000)]
        for index,piece in reversed(list(enumerate(pieces,1))):
            message=piece.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
            print(f'::error title=Diagnóstico del proceso ({index}/{len(pieces)})::'+message,flush=True)
    return code==0

if '--child' not in sys.argv:
    if os.name=='nt' or '--isolate-gui' in sys.argv:
        # Windows Tk keeps native per-process state after destroying a root.
        # Each GUI launch gets the same isolation as starting the actual app;
        # no test is omitted and native failures still fail the whole suite.
        ids=list(case_ids(load_suite(names)))
        graphical=[name for name in ids if name.startswith(('tests.test_gui.','tests.test_vendedor.'))]
        backend=[name for name in ids if name not in graphical]
        batches=([backend] if backend else [])+[[name] for name in graphical]
        success=True
        for batch in batches:
            print('Proceso de pruebas:',batch[0] if len(batch)==1 else f'{len(batch)} pruebas de datos y licencias',flush=True)
            if not run_child(batch):success=False
        report(f'Comprobaciones incluidas: {len(ids)}. Resultado: '+('correcto.' if success else 'fallido.'))
    else:success=run_child(names)
    raise SystemExit(0 if success else 1)

try:
    suite = load_suite(names)
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
