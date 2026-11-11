"""Install twice over the same location and verify that user data survives."""
from contextlib import closing
from pathlib import Path
import hashlib,os,sqlite3,subprocess,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from tools.smoke_windows import run_case


def main():
    installer=Path(sys.argv[1]).resolve();commercial='--commercial' in sys.argv
    with tempfile.TemporaryDirectory(prefix='registro-upgrade-') as name:
        root=Path(name);program=root/'programa';data=root/'datos';data.mkdir()
        command=[str(installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/NOICONS','/TASKS=',f'/DIR={program}']
        subprocess.run(command,check=True,timeout=120)
        os.environ['REGISTRO_DATA_DIR']=str(data);os.environ['REGISTRO_DB_PATH']=str(data/'registro.db')
        import db
        from licencias import OfflineLicensing
        path=data/'registro.db';db.inicializar_db(path)
        course=db.obtener_cursos(db_path=path)[0][0];comp=db.obtener_competencias_por_curso(course,path)[0][0];cap=db.obtener_capacidades_por_competencia(comp,path)[0][0]
        student=db.agregar_estudiante('Alumno','Conservado','3°','A',db_path=path)
        session=db.crear_o_actualizar_sesion_clase(None,course,comp,'3°','A','Tema conservado','Propósito conservado',1,[(cap,'Criterio')],db_path=path)
        db.guardar_calificaciones_y_asistencia_sesion(session,[dict(estudiante_id=student,notas_por_capacidad={cap:12.5},comentario='Comentario conservado')],db_path=path)
        public=(Path(__file__).resolve().parent.parent/'license_public_key.pem').read_bytes()
        account=OfflineLicensing(data,public,registry=False);account.register('Titular prueba','test@example.com','titular','ClavePrueba123','secundaria:matematica')
        identity=account.state['account_id'];trial=account.state['trial_started']
        settings=data/'settings.json';settings.write_text('{"active_database":"registro.db"}')
        library=data/'biblioteca'/'instrumentos.db';library.parent.mkdir()
        with closing(sqlite3.connect(library)) as conn,conn:conn.execute('CREATE TABLE upgrade_fixture(nombre TEXT)');conn.execute("INSERT INTO upgrade_fixture VALUES('Modelo conservado')")
        tracked=[path,account.path,settings,library];before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}
        subprocess.run(command,check=True,timeout=120)
        assert all(hashlib.sha256(p.read_bytes()).hexdigest()==digest for p,digest in before.items()),'El instalador alteró los datos del usuario.'
        run_case(program/'RegistroDocente.exe',path,data,12.5,commercial=commercial,expect_activation=False)
        restored=OfflineLicensing(data,public,registry=False)
        assert restored.state['account_id']==identity and restored.state['trial_started']==trial
        with closing(sqlite3.connect(path)) as conn:
            assert conn.execute('SELECT titulo_tema FROM Sesiones_Clase WHERE id=?',(session,)).fetchone()[0]=='Tema conservado'
        print('PASS: reinstalación conserva base, notas 12.5, tema, biblioteca, configuración y cuenta sin reiniciar la demo.',flush=True)


if __name__=='__main__':main()
