from pathlib import Path
import sqlite3,unittest
from unittest.mock import patch
import openpyxl
import db,app_storage,periodos,institucion
from ingreso_masivo import plan
from tests import test_instrumentos as fixtures
from excel_tablas import export_activity
from PIL import Image


class AcademicTests(unittest.TestCase):
    setUp=fixtures.InstrumentWorkbookTests.setUp
    new_session=fixtures.InstrumentWorkbookTests.new_session

    def make_session(self,section='A',unit=None):
        return db.crear_o_actualizar_sesion_clase(None,self.course,self.comp,'3°',section,'Fracciones','Argumentar una solución',1,[(self.cap,'Explica')],db_path=self.path,unidad_id=unit)

    def test_three_terms_and_four_bimesters_start_clean_keep_roster_and_school(self):
        unit=periodos.save_unit(self.path,self.course,'3°','A','Unidad 1')
        sid=self.make_session(unit=unit);db.guardar_notas_globales_sesion(sid,{self.student:17},self.path)
        institucion.save(self.path,dict(nombre='IE de ejemplo',docente='Docente'))
        with patch('app_storage.data_dir',return_value=Path(self.temp.name)):
            target=app_storage.create_period(self.path,2028,3,'Trimestres')
            with self.assertRaises(ValueError):app_storage.create_period(self.path,2028,4,'Trimestres')
            with self.assertRaises(ValueError):app_storage.create_period(self.path,2028,3,'Trimestres')
            bimestre=app_storage.create_period(self.path,2028,4,'Bimestres')
        self.assertEqual(periodos.info(target)['scheme'],'Trimestres')
        self.assertEqual(periodos.info(bimestre)['number'],4)
        self.assertEqual(db.obtener_sesiones_clase(self.course,'3°','A',db_path=target),[])
        self.assertEqual(periodos.units(target,self.course,'3°','A'),[])
        self.assertEqual(institucion.profile(target)['nombre'],'IE de ejemplo')
        self.assertEqual(len(db.obtener_estudiantes_filtrados('3°','A',db_path=target)),1)
        self.assertEqual(self.read_note(sid),17)

    def read_note(self,sid):
        with sqlite3.connect(self.path) as conn:return conn.execute('SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',(sid,)).fetchone()[0]

    def test_unit_scope_validation_rolls_back_whole_activity(self):
        unit=periodos.save_unit(self.path,self.course,'3°','B','Otra sección')
        with self.assertRaises(ValueError):self.make_session(unit=unit)
        self.assertEqual(db.obtener_sesiones_clase(self.course,'3°','A',db_path=self.path),[s for s in db.obtener_sesiones_clase(self.course,'3°','A',db_path=self.path) if s['titulo_tema']!='Fracciones'])
        with self.assertRaises(ValueError):periodos.save_unit(self.path,self.course,'3°','A','Unidad',start='2028-04-01',end='2028-03-01')

    def test_reading_legacy_metadata_preserves_file_and_assigning_keeps_grades(self):
        before=self.path.read_bytes();self.assertIsNone(periodos.info(self.path)['year']);self.assertEqual(before,self.path.read_bytes())
        sid=self.make_session();db.guardar_notas_globales_sesion(sid,{self.student:12},self.path)
        periodos.identify(self.path,2028,2,'Trimestres');self.assertEqual(self.read_note(sid),12)

    def test_closed_period_blocks_backend_and_still_opens_after_migration(self):
        sid=self.make_session();db.guardar_notas_globales_sesion(sid,{self.student:12},self.path)
        with db.obtener_conexion(self.path) as conn:
            conn.execute('CREATE TABLE Estado_Periodo(id INTEGER PRIMARY KEY,cerrado INTEGER)');conn.execute('INSERT INTO Estado_Periodo VALUES(1,1)')
        with self.assertRaisesRegex(ValueError,'Periodo cerrado'):db.guardar_notas_globales_sesion(sid,{self.student:19},self.path)
        with self.assertRaisesRegex(ValueError,'Periodo cerrado'):periodos.save_unit(self.path,self.course,'3°','A','Unidad')
        db.inicializar_db(self.path);self.assertEqual(self.read_note(sid),12);self.assertTrue(periodos.info(self.path)['closed'])

    def test_dated_recovery_opens_an_independent_document(self):
        sid=self.make_session();db.guardar_notas_globales_sesion(sid,{self.student:12},self.path)
        saved=app_storage.backup_database(self.path,'prueba-fecha');original=saved.read_bytes()
        db.guardar_notas_globales_sesion(sid,{self.student:18},self.path)
        opened=periodos.open_snapshot(saved,Path(self.temp.name))
        self.assertEqual(self.read_note(sid),18);self.assertEqual(saved.read_bytes(),original)
        with sqlite3.connect(opened) as conn:self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',(sid,)).fetchone()[0],12)
        self.assertIn(saved,[r['path'] for r in periodos.snapshots(self.path)])

    def test_excel_library_has_no_names_or_notes_and_imports_into_another_section(self):
        sid=self.make_session();db.guardar_indicadores_instrumento_sesion(sid,'Rúbrica',[(self.cap,'Explica',20)],self.path)
        db.guardar_notas_globales_sesion(sid,{self.student:17},self.path)
        with db.obtener_conexion(self.path) as conn:conn.execute("UPDATE Sesiones_Clase SET tipo_instrumento='Rúbrica' WHERE id=?",(sid,))
        file=Path(self.temp.name)/'3-Fracciones.xlsx';export_activity(file,sid,self.path,library=True)
        wb=openpyxl.load_workbook(file);self.addCleanup(wb.close)
        self.assertIsNone(wb['Registro']['B7'].value)
        self.assertIn('Explica',[c.value for row in wb['Instrumento'] for c in row])
        other=self.make_session('B');result=db.importar_rubrica_o_cotejo_desde_excel(other,file,'3°','B',self.path)
        self.assertEqual(result[1],0);self.assertEqual(self.read_note(sid),17)
        self.assertTrue(db.obtener_indicadores_instrumento_sesion(result.session_id,self.path))

    def test_branded_workbook_round_trip_keeps_title_purpose_and_notes(self):
        sid=self.make_session();db.guardar_notas_globales_sesion(sid,{self.student:17},self.path)
        institucion.save(self.path,dict(nombre='IE de ejemplo',codigo='1234567',docente='Docente'))
        logo=Path(self.temp.name)/'logo.png';Image.new('RGB',(30,60),'blue').save(logo)
        import reportes
        reportes.save_logo(logo,self.path)
        file=Path(self.temp.name)/'registro.xlsx';export_activity(file,sid,self.path)
        wb=openpyxl.load_workbook(file);self.addCleanup(wb.close)
        self.assertIn('IE de ejemplo',wb['Registro']['A1'].value);self.assertEqual(len(wb['Registro']._images),1)
        self.assertEqual(wb['Institución']['C6'].value,'1234567')
        result=db.importar_rubrica_o_cotejo_desde_excel(sid,file,'3°','A',self.path)
        ctx=db.obtener_sesiones_clase(self.course,'3°','A',db_path=self.path)
        self.assertEqual(next(r for r in ctx if r['id']==result.session_id)['titulo_tema'],'Fracciones')
        self.assertEqual(self.read_note(sid),17)

    def test_clipboard_validates_every_cell_before_touching_original(self):
        rows=[['1','code','Alumno 1','Sí','','',''],['2','code','Alumno 2','Sí','','','']]
        with self.assertRaises(ValueError):plan(rows,'15\t16\n18\t21',capacities=2)
        self.assertEqual(rows[0][4],'')
        result,_=plan(rows,'0\n5,5',capacities=2,global_grade=True)
        self.assertEqual(result[0][4:6],['0','0']);self.assertEqual(result[1][4:6],['5.5','5.5'])
        with self.assertRaises(ValueError):plan(rows,'1\t2',capacities=2,global_grade=True)

    def test_new_period_can_be_created_after_closing_current_one(self):
        periodos.identify(self.path,2028,1,'Trimestres')
        with db.obtener_conexion(self.path) as conn:
            conn.execute('CREATE TABLE Estado_Periodo(id INTEGER PRIMARY KEY,cerrado INTEGER)');conn.execute('INSERT INTO Estado_Periodo VALUES(1,1)')
        with patch('app_storage.data_dir',return_value=Path(self.temp.name)):
            new=app_storage.create_period(self.path,2028,2,'Trimestres')
        self.assertTrue(periodos.info(self.path)['closed']);self.assertFalse(periodos.info(new)['closed'])

    def test_startup_keeps_one_verified_backup_before_migration(self):
        previous=set((self.path.parent/'backups').glob('*.db'))
        app_storage.prepare_storage(self.path,backup=False);db.inicializar_db(self.path)
        created=set((self.path.parent/'backups').glob('*.db'))-previous
        self.assertEqual(len(created),1)
        app_storage.validate_database(next(iter(created)))
