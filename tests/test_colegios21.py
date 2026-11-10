from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import sqlite3,unittest
import openpyxl
import db,periodos,colegios,app_storage,institucion,reportes
from escala import range_caption,save_thresholds,thresholds
from tests import test_instrumentos as fixtures
from excel_tablas import export_activity
from matriz_excel import export_matrix
from PIL import Image


class SchoolOrganizationTests(unittest.TestCase):
    setUp=fixtures.InstrumentWorkbookTests.setUp
    new_session=fixtures.InstrumentWorkbookTests.new_session

    def make(self,unit=None,grade=12):
        sid=db.crear_o_actualizar_sesion_clase(None,self.course,self.comp,'3°','A','Actividad de unidad','',1,[(self.cap,'Criterio')],db_path=self.path,unidad_id=unit)
        db.guardar_notas_globales_sesion(sid,{self.student:grade},self.path);return sid

    def read(self,path,sql,*args):
        with closing(sqlite3.connect(path)) as conn:return conn.execute(sql,args).fetchall()

    def test_new_school_starts_empty_and_can_use_same_period_number(self):
        root=Path(self.temp.name);sid=self.make()
        logo=root/'logo.png';Image.new('RGB',(30,30),'blue').save(logo);reportes.save_logo(logo,self.path)
        other=colegios.blank_copy(self.path,root,'Segundo colegio')
        self.assertNotEqual(colegios.info(self.path)['school_id'],colegios.info(other)['school_id'])
        self.assertEqual(self.read(other,'SELECT COUNT(*) FROM Estudiantes'),[(0,)])
        self.assertEqual(self.read(other,'SELECT COUNT(*) FROM Sesiones_Clase'),[(0,)])
        self.assertIsNone(reportes.logo_bytes(other));self.assertEqual(institucion.profile(other)['nombre'],'Segundo colegio')
        with patch('app_storage.data_dir',return_value=root):
            a=app_storage.create_period(self.path,2029,2,'Bimestres');b=app_storage.create_period(other,2029,2,'Bimestres')
        self.assertNotEqual(a,b)
        self.assertEqual(self.read(self.path,'SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',sid),[(12.0,)])

    def test_units_are_shared_by_all_courses_and_deleting_keeps_grades(self):
        unit=periodos.save_unit(self.path,None,None,None,'Unidad común')
        sid=self.make(unit,16)
        other_course=db.obtener_cursos(db_path=self.path)[1][0]
        self.assertEqual(periodos.units(self.path,other_course,'5°','B')[0]['id'],unit)
        periodos.save_unit(self.path,None,None,None,'Unidad editada',identity=unit)
        saved=periodos.delete_unit(self.path,unit);app_storage.validate_database(saved)
        self.assertEqual(self.read(self.path,'SELECT unidad_id FROM Sesiones_Clase WHERE id=?',sid),[(None,)])
        self.assertEqual(self.read(self.path,'SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',sid),[(16.0,)])

    def test_legacy_unit_migration_keeps_links_scores_and_disambiguates_names(self):
        sid=self.make(grade=15)
        with closing(sqlite3.connect(self.path)) as conn,conn:
            conn.execute('DROP TABLE Unidades_Didacticas')
            conn.execute('CREATE TABLE Unidades_Didacticas(id INTEGER PRIMARY KEY,curso_id INTEGER,grado TEXT,seccion TEXT,nombre TEXT,proposito TEXT,inicio TEXT,fin TEXT)')
            conn.execute("INSERT INTO Unidades_Didacticas VALUES(10,?,'3°','A','Unidad 1','','','')",(self.course,))
            conn.execute("INSERT INTO Unidades_Didacticas VALUES(20,?,'4°','B','Unidad 1','','','')",(self.course,))
            conn.execute('UPDATE Sesiones_Clase SET unidad_id=10 WHERE id=?',(sid,))
        db.inicializar_db(self.path);app_storage.validate_database(self.path)
        units=periodos.units(self.path)
        self.assertEqual([r['id'] for r in units],[10,20]);self.assertNotEqual(units[0]['nombre'],units[1]['nombre'])
        self.assertEqual(self.read(self.path,'SELECT unidad_id FROM Sesiones_Clase WHERE id=?',sid),[(10,)])
        self.assertEqual(self.read(self.path,'SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',sid),[(15.0,)])

    def test_period_can_be_edited_and_removed_as_a_recoverable_document(self):
        root=Path(self.temp.name);sid=self.make(grade=13)
        periodos.identify(self.path,2029,1,'Bimestres',root=root)
        periodos.identify(self.path,2029,3,'Trimestres','Cierre del año','2029-09-01','2029-12-15',root=root)
        data=periodos.info(self.path);self.assertEqual((data['number'],data['name']),(3,'Cierre del año'))
        replacement,saved=colegios.remove_period(self.path,root)
        self.assertFalse(self.path.exists());self.assertTrue(replacement.exists())
        self.assertEqual(self.read(saved,'SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',sid),[(13.0,)])
        self.assertEqual(len(colegios.trash(root)),1)
        restored=periodos.open_snapshot(saved,root);self.assertEqual(periodos.info(restored)['number'],3)

    def test_renaming_school_leaves_other_school_separate(self):
        root=Path(self.temp.name);other=colegios.blank_copy(self.path,root,'Otro colegio')
        with patch('app_storage.data_dir',return_value=root):period=app_storage.create_period(self.path,2029,1)
        identity=colegios.info(self.path)['school_id'];colegios.rename(root,identity,'Colegio renombrado',self.path)
        self.assertEqual(colegios.info(period)['school_name'],'Colegio renombrado')
        self.assertEqual(colegios.info(other)['school_name'],'Otro colegio')
        self.assertEqual(colegios.info(self.path)['school_id'],identity)

    def test_period_duplicate_check_is_scoped_to_school_and_dates_are_atomic(self):
        root=Path(self.temp.name)
        with patch('app_storage.data_dir',return_value=root):target=app_storage.create_period(self.path,2029,2)
        with self.assertRaises(ValueError):periodos.identify(self.path,2029,2,root=root)
        with self.assertRaises(ValueError):periodos.identify(target,2029,4,'Trimestres',root=root)
        with self.assertRaises(ValueError):periodos.identify(target,2029,3,start='2029-12-01',end='2029-01-01',root=root)
        self.assertEqual(periodos.info(target)['number'],2)

    def test_unit_matrix_uses_only_selected_evidence_and_exports_its_scope(self):
        first=periodos.save_unit(self.path,None,None,None,'Unidad 1');second=periodos.save_unit(self.path,None,None,None,'Unidad 2')
        self.make(first,20);self.make(second,4)
        structure,rows=db.calcular_matriz_competencias_y_capacidades(self.course,'3°','A',self.path,unidad_id=first)
        self.assertEqual(rows[0]['promedio_general'],20)
        self.assertEqual(db.calcular_matriz_competencias_y_capacidades(self.course,'3°','A',self.path)[1][0]['promedio_general'],12)
        db.guardar_nota_manual_capacidad(self.student,self.cap,18,self.path)
        self.assertEqual(db.calcular_matriz_competencias_y_capacidades(self.course,'3°','A',self.path,unidad_id=first)[1][0]['promedio_general'],20)
        file=Path(self.temp.name)/'unidad.xlsx';export_matrix(file,self.course_name,'3°','A',structure,rows,self.path,'ambos',unidad_id=first,alcance='Unidad 1')
        wb=openpyxl.load_workbook(file);self.addCleanup(wb.close)
        self.assertIn('Unidad 1',wb['Matriz final']['A1'].value)
        from matriz_excel import import_matrix
        with self.assertRaisesRegex(ValueError,'resume una unidad'):import_matrix(wb,self.path,'3°','A')

    def test_filled_school_workbook_is_isolated_but_design_library_is_portable(self):
        root=Path(self.temp.name);other=colegios.blank_copy(self.path,root,'Segundo colegio')
        target=db.crear_o_actualizar_sesion_clase(None,self.course,self.comp,'3°','A','Destino','',1,[(self.cap,'Criterio')],db_path=other)
        sid=self.make();file=root/'origen.xlsx';export_activity(file,sid,self.path)
        with self.assertRaisesRegex(ValueError,'otro colegio'):db.importar_rubrica_o_cotejo_desde_excel(target,file,'3°','A',other)
        export_activity(file,sid,self.path,library=True)
        result=db.importar_rubrica_o_cotejo_desde_excel(target,file,'3°','A',other)
        self.assertEqual(result[1],0);self.assertEqual(self.read(other,'SELECT COUNT(*) FROM Estudiantes'),[(0,)])

    def test_ranges_follow_thresholds_and_grade_boundaries(self):
        self.assertEqual(range_caption('B'),'B · 10.5 a < 13.5')
        self.assertEqual(range_caption('AD'),'AD · 17.5 a 20')
        self.assertEqual(range_caption('B',maximum=10),'B · 5.25 a < 6.75')
        self.assertEqual(db.nota_a_literal(13.5,self.path),'A')
        save_thresholds(self.path,(10,14,18))
        self.assertEqual(range_caption('B',thresholds(self.path)),'B · 10 a < 14')

    def test_school_archive_copies_every_period_before_removing_any_original(self):
        root=Path(self.temp.name)
        with patch('app_storage.data_dir',return_value=root):other=app_storage.create_period(self.path,2029,1)
        records=[dict(path=self.path),dict(path=other)]
        original=app_storage.copy_database;calls=[]
        def fail_second(source,target):
            calls.append(source)
            if len(calls)==2:raise OSError('Fallo simulado de disco')
            return original(source,target)
        with patch('app_storage.copy_database',side_effect=fail_second):
            with self.assertRaises(OSError):colegios.archive_school(records,self.path)
        self.assertTrue(self.path.exists());self.assertTrue(other.exists())

    def test_school_branding_is_shared_with_its_periods_only(self):
        root=Path(self.temp.name);other=colegios.blank_copy(self.path,root,'Otro colegio')
        with patch('app_storage.data_dir',return_value=root):period=app_storage.create_period(self.path,2029,1)
        with db.obtener_conexion(period) as conn:conn.execute('DROP TABLE Colegio_Info')
        institucion.save(self.path,dict(nombre='Mi colegio',codigo='12345',docente='Docente'))
        logo=root/'escudo.png';Image.new('RGB',(50,30),'blue').save(logo);reportes.save_logo(logo,self.path)
        colegios.sync_identity(self.path,root)
        self.assertEqual(colegios.info(period)['school_id'],colegios.info(self.path)['school_id'])
        self.assertEqual(institucion.profile(period)['codigo'],'12345');self.assertEqual(reportes.logo_bytes(period),reportes.logo_bytes(self.path))
        self.assertEqual(institucion.profile(other)['nombre'],'Otro colegio');self.assertIsNone(reportes.logo_bytes(other))
