"""Launch the real Windows executable on empty and legacy temporary databases."""
from contextlib import closing
from pathlib import Path
import ctypes,os,sqlite3,subprocess,sys,tempfile,time
from ctypes import wintypes


def visible_application(pid,prefix='Registro Docente 1.5'):
    user32=ctypes.windll.user32
    found=[]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user32.GetWindowThreadProcessId.argtypes=(wintypes.HWND,ctypes.POINTER(wintypes.DWORD))
    user32.IsWindowVisible.argtypes=(wintypes.HWND,)
    user32.GetWindowTextLengthW.argtypes=(wintypes.HWND,)
    user32.GetWindowTextW.argtypes=(wintypes.HWND,wintypes.LPWSTR,ctypes.c_int)
    user32.EnumWindows.argtypes=(callback_type,wintypes.LPARAM)
    def inspect(hwnd,param):
        owner=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
        if owner.value==pid and user32.IsWindowVisible(hwnd):
            size=user32.GetWindowTextLengthW(hwnd)
            text=ctypes.create_unicode_buffer(size+1);user32.GetWindowTextW(hwnd,text,size+1)
            if text.value.startswith(prefix):found.append(True)
        return True
    user32.EnumWindows(callback_type(inspect),0)
    return bool(found)


def run_case(executable,database,folder,expected_note=None):
    env={**os.environ,'REGISTRO_DATA_DIR':str(folder),'REGISTRO_DB_PATH':str(database)}
    env.pop('PYTHONPATH',None)
    log=folder/'arranque.log'
    with log.open('w',encoding='utf-8') as stream:
        process=subprocess.Popen([str(executable)],cwd=folder,env=env,stdout=stream,stderr=stream)
        try:
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                if process.poll() is not None:raise RuntimeError('El ejecutable terminó al iniciar: '+log.read_text(errors='replace')[-3000:])
                if visible_application(process.pid):
                    with closing(sqlite3.connect(database)) as conn:
                        assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                        assert conn.execute("SELECT 1 FROM sqlite_master WHERE name='Historial_Notas'").fetchone()
                        if expected_note is not None:assert conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0]==expected_note
                    print('PASS: ejecutable visible y base íntegra:',database.name,flush=True)
                    return
                time.sleep(.2)
            raise RuntimeError('El ejecutable no mostró la ventana principal.')
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()


def main():
    if sys.argv[1]=='--seller':
        with tempfile.TemporaryDirectory(prefix='registro-vendedor-exe-') as folder:
            process=subprocess.Popen([str(Path(sys.argv[2]).resolve())],cwd=folder)
            try:
                deadline=time.monotonic()+45
                while time.monotonic()<deadline:
                    if process.poll() is not None:raise RuntimeError('La herramienta del vendedor terminó al iniciar.')
                    if visible_application(process.pid,'Registro Licencias'):
                        print('PASS: herramienta del vendedor visible; no se generan claves sin acción del vendedor.',flush=True)
                        return
                    time.sleep(.2)
                raise RuntimeError('La herramienta del vendedor no mostró su ventana.')
            finally:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
        return
    exe=Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix='registro-windows-exe-') as folder:
        root=Path(folder);fresh=root/'nuevo';fresh.mkdir()
        run_case(exe,fresh/'registro.db',fresh)
        legacy=root/'anterior';legacy.mkdir();path=legacy/'registro.db'
        os.environ['REGISTRO_DATA_DIR']=str(legacy);os.environ['REGISTRO_DB_PATH']=str(path)
        sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
        import db
        db.inicializar_db(path)
        course=db.obtener_cursos(db_path=path)[0][0];comp=db.obtener_competencias_por_curso(course,path)[0][0];cap=db.obtener_capacidades_por_competencia(comp,path)[0][0]
        student=db.agregar_estudiante('Prueba','Migración',db_path=path)
        session=db.crear_o_actualizar_sesion_clase(None,course,comp,'3°','A','Prueba','',1,[(cap,'Criterio')],db_path=path)
        db.guardar_calificaciones_y_asistencia_sesion(session,[dict(estudiante_id=student,notas_por_capacidad={cap:12.5})],db_path=path)
        with closing(sqlite3.connect(path)) as conn,conn:conn.execute('DROP TABLE Docente_Config')
        run_case(exe,path,legacy,12.5)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        message=str(exc).replace('%','%25').replace('\n','%0A').replace('\r','%0D')
        print('::error title=Arranque del ejecutable::'+message,flush=True)
        raise
