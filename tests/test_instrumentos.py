"""Real XLSX round trips, scoring and atomic rejection of unsafe imports."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
import openpyxl
import db
from instrumentos_excel import IND, FINAL, RAW, META


class InstrumentWorkbookTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'datos.db';db.inicializar_db(self.path)
        self.course,self.course_name,_=db.obtener_cursos(db_path=self.path)[0]
        self.comp,self.comp_name=db.obtener_competencias_por_curso(self.course,self.path)[0]
        self.cap,self.cap_name=db.obtener_capacidades_por_competencia(self.comp,self.path)[0]
        self.student=db.agregar_estudiante('Ana María','Roque','3°','A',db_path=self.path)
        self.session=self.new_session()

    def new_session(self):
        return db.crear_o_actualizar_sesion_clase(None,self.course,self.comp,'3°','A','Resolver ecuaciones','',1,
            [(self.cap,'Justifica cada paso')],db_path=self.path)

    def read(self,sql):
        with closing(sqlite3.connect(self.path)) as conn:return conn.execute(sql).fetchall()

    def model(self,kind='Rúbrica',indicators=None):
        if indicators:db.guardar_indicadores_instrumento_sesion(self.session,kind,indicators,self.path)
        self.file=Path(self.temp.name)/'modelo.xlsx'
        activity=next(s for s in db.obtener_sesiones_clase(self.course,'3°','A',db_path=self.path) if s['id']==self.session)
        capacities=[(c['capacidad_id'],c['capacidad_nombre'],c['criterio_precisado']) for c in activity['capacidades']]
        db.exportar_plantilla_rubrica_o_cotejo_excel(str(self.file),self.course_name,'3°','A','Resolver ecuaciones',self.comp_name,
            capacities,kind,self.path,sesion_id=self.session)
        wb=openpyxl.load_workbook(self.file);self.addCleanup(wb.close);return wb

    def apply(self,wb,session=None):
        wb.save(self.file)
        return db.importar_rubrica_o_cotejo_desde_excel(session or self.session,str(self.file),'3°','A',self.path)

    def saved(self,grade=17):
        db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,
            asistio=False,comentario='Entrega pendiente',notas_por_capacidad={self.cap:grade})],self.path)

    def test_rubric_points_use_sum_of_maxima_and_preserve_descriptors(self):
        wb=self.model(indicators=[(self.cap,'Explica',6),(self.cap,'Resuelve',14)])
        wb[IND]['D4']='Necesita guía';wb[IND]['G4']='Justifica y generaliza'
        wb[RAW]['D2']=3;wb[RAW]['E2']=10
        self.assertEqual(self.apply(wb),(2,1))
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(13.0,)])
        wb=self.model()
        self.assertEqual(wb[IND]['D4'].value,'Necesita guía')
        self.assertEqual(wb[IND]['G4'].value,'Justifica y generaliza')
        self.assertEqual([wb[IND]['H4'].value,wb[IND]['H5'].value],[6,14])
        self.assertEqual(wb[META].sheet_state,'veryHidden')
        self.assertIn('Instrucciones',wb.sheetnames)

    def test_checklist_uses_weighted_yes_no_and_zero_is_a_grade(self):
        wb=self.model('Lista de Cotejo',[(self.cap,'Muestra el procedimiento',6),(self.cap,'Comprueba',4)])
        wb[RAW]['D2']='Sí';wb[RAW]['E2']='No';self.apply(wb)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(12.0,)])
        wb[RAW]['D2']='No';self.apply(wb)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(0.0,)])

    def test_blank_import_preserves_notes_attendance_and_comments(self):
        self.saved();wb=self.model('Lista de Cotejo')
        self.assertEqual(self.apply(wb),(2,0))
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(17.0,)])
        self.assertEqual(self.read('SELECT asistio,comentario FROM Asistencia_Y_Comentarios_Clase'),[(0,'Entrega pendiente')])

    def test_manual_final_note_and_comment_preserve_absence(self):
        self.saved();wb=self.model();wb[FINAL]['D2']=0;wb[FINAL]['F2']='Ya entregó'
        self.assertEqual(self.apply(wb),(1,1))
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(0.0,)])
        self.assertEqual(self.read('SELECT asistio,comentario FROM Asistencia_Y_Comentarios_Clase'),[(0,'Ya entregó')])

    def test_partial_indicators_reject_entire_import(self):
        self.saved();wb=self.model('Lista de Cotejo');wb[IND]['C4']='Cambio no confirmado';wb[RAW]['D2']='Sí'
        with self.assertRaisesRegex(ValueError,'todos los indicadores'):self.apply(wb)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(17.0,)])
        self.assertEqual(self.read('SELECT criterio_precisado FROM Sesion_Capacidades'),[('Justifica cada paso',)])
        self.assertEqual(db.obtener_indicadores_instrumento_sesion(self.session,self.path),[])

    def test_manual_and_indicator_answers_cannot_overwrite_each_other(self):
        wb=self.model();wb[FINAL]['D2']=18;wb[RAW]['D2']=12
        with self.assertRaisesRegex(ValueError,'hojas 2 y 3'):self.apply(wb)
        self.assertFalse(self.read('SELECT nota FROM Notas_Sesion_Capacidad'))

    def test_different_capacities_can_use_final_notes_and_indicator_points(self):
        other=db.obtener_capacidades_por_competencia(self.comp,self.path)[1][0]
        db.crear_o_actualizar_sesion_clase(self.session,self.course,self.comp,'3°','A','Resolver ecuaciones','',1,
            [(self.cap,'Justifica cada paso'),(other,'Comprueba')],db_path=self.path)
        wb=self.model(indicators=[(self.cap,'Justifica',20),(other,'Comprueba',10)])
        wb[FINAL]['D2']=18;wb[RAW]['E2']=7
        self.assertEqual(self.apply(wb),(2,1))
        self.assertEqual(self.read('SELECT capacidad_id,nota FROM Notas_Sesion_Capacidad ORDER BY capacidad_id'),[(self.cap,18.0),(other,14.0)])

    def test_identity_checks_reject_changed_name_code_or_permanent_id(self):
        for cell,value in [('A2','3A99'),('B2','Otro apellido'),('C2','Otro nombre'),('E2',999)]:
            with self.subTest(cell=cell):
                wb=self.model();wb[FINAL]['D2']=15;wb[FINAL][cell]=value
                with self.assertRaises(ValueError):self.apply(wb)
                self.assertFalse(self.read('SELECT nota FROM Notas_Sesion_Capacidad'))

    def test_duplicate_student_rows_reject_without_losing_saved_grade(self):
        self.saved();wb=self.model();wb[FINAL]['D2']=12
        wb[FINAL].append([c.value for c in wb[FINAL][2]])
        with self.assertRaisesRegex(ValueError,'código repetido'):self.apply(wb)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(17.0,)])

    def test_grade_from_another_activity_is_rejected_but_blank_instrument_is_reusable(self):
        wb=self.model();other=self.new_session();wb[RAW]['D2']=15
        with self.assertRaisesRegex(ValueError,'otra actividad'):self.apply(wb,other)
        self.assertFalse(db.obtener_indicadores_instrumento_sesion(other,self.path))
        wb[RAW]['D2']=None;self.assertEqual(self.apply(wb,other),(1,0))

    def test_indicator_id_mapping_cannot_be_silently_changed(self):
        for cell,value in [('I4','I999'),('A4',999999),('H4',0),('D4',None)]:
            with self.subTest(cell=cell):
                wb=self.model();wb[IND][cell]=value;wb[RAW]['D2']=12
                with self.assertRaises(ValueError):self.apply(wb)
                self.assertFalse(self.read('SELECT nota FROM Notas_Sesion_Capacidad'))

    def test_formula_without_calculated_result_is_rejected(self):
        wb=self.model();wb[FINAL]['D2']='=10+5'
        with self.assertRaisesRegex(ValueError,'fórmula sin resultado'):self.apply(wb)
        self.assertFalse(self.read('SELECT nota FROM Notas_Sesion_Capacidad'))

    def test_missing_permanent_identity_column_is_rejected(self):
        wb=self.model();wb[FINAL]['E1']='';wb[FINAL]['D2']=15
        with self.assertRaisesRegex(ValueError,'EST_ID'):self.apply(wb)
        self.assertFalse(self.read('SELECT nota FROM Notas_Sesion_Capacidad'))

    def test_late_invalid_student_rolls_back_all_changes(self):
        db.agregar_estudiante('Beto','Zeta','3°','A',db_path=self.path)
        self.saved();wb=self.model();wb[FINAL]['D2']=11;wb[FINAL]['D3']=99;wb[IND]['C4']='No aplicar'
        with self.assertRaises(ValueError):self.apply(wb)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(17.0,)])
        self.assertEqual(self.read('SELECT criterio_precisado FROM Sesion_Capacidades'),[('Justifica cada paso',)])

    def test_secondary_model_rejects_primary_context(self):
        wb=self.model()
        with db.obtener_conexion(self.path) as conn:conn.execute("UPDATE Docente_Config SET nivel_educativo='Primaria' WHERE id=1")
        with self.assertRaisesRegex(ValueError,'nivel activo'):self.apply(wb)

    def test_maximum_validation_tracks_indicator_definition(self):
        wb=self.model(indicators=[(self.cap,'Sustenta',5)]);wb[RAW]['D2']=6
        with self.assertRaises(ValueError):self.apply(wb)
        wb[RAW]['D2']=2.5;self.apply(wb)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(10.0,)])

    def test_model_with_school_logo_keeps_ids_and_imports_answers(self):
        import io,reportes
        from PIL import Image
        wb=self.model();wb[RAW]['D2']=16;wb.save(self.file)
        logo=io.BytesIO();Image.new('RGB',(70,70),'green').save(logo,format='PNG')
        reportes.decorate_workbook(self.file,logo.getvalue())
        decorated=openpyxl.load_workbook(self.file);self.addCleanup(decorated.close)
        self.assertEqual(len(decorated[IND]._images),1)
        self.assertFalse(decorated[RAW]._images)
        self.assertEqual(decorated[FINAL]['A1'].value,'Código')
        self.assertEqual(self.apply(decorated),(1,1))
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(16.0,)])

    def test_human_headers_level_answers_and_stable_criteria_round_trip(self):
        from evaluacion_datos import get_answers
        wb=self.model(indicators=[(self.cap,'Explica',6),(self.cap,'Comprueba',14)])
        identities=[i['id'] for i in db.obtener_indicadores_instrumento_sesion(self.session,self.path)]
        self.assertNotIn('CAP_ID',wb[FINAL]['D1'].value);self.assertNotIn('IND_ID',wb[RAW]['D1'].value)
        self.assertTrue(wb[IND].column_dimensions['A'].hidden);self.assertTrue(wb[IND].column_dimensions['I'].hidden)
        wb[RAW]['D2']='A';wb[RAW]['E2']='AD';wb[IND]['C4']='Explica y sustenta'
        self.assertEqual(self.apply(wb),(2,1))
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(18.65,)])
        self.assertEqual(get_answers(self.session,self.path),{(self.student,identities[0]):'A',(self.student,identities[1]):'AD'})
        self.assertEqual([i['id'] for i in db.obtener_indicadores_instrumento_sesion(self.session,self.path)],identities)

    def test_modified_visible_column_mapping_is_rejected_atomically(self):
        wb=self.model(indicators=[(self.cap,'Explica',6),(self.cap,'Comprueba',14)])
        wb[RAW]['D1'],wb[RAW]['E1']=wb[RAW]['E1'].value,wb[RAW]['D1'].value
        wb[RAW]['D2']='AD';wb[RAW]['E2']='A'
        with self.assertRaisesRegex(ValueError,'encabezados'):self.apply(wb)
        self.assertFalse(self.read('SELECT nota FROM Notas_Sesion_Capacidad'))

    def test_legacy_version_two_still_imports_numeric_answers(self):
        wb=self.model()
        for row in wb[META]:
            if row[0].value=='version':row[1].value=2
        wb[FINAL]['D1']=f'Capacidad\n[CAP_ID:{self.cap}]'
        identity=wb[IND]['I4'].value
        wb[RAW]['D1']=f'Explica\n[IND_ID:{identity}] [CAP_ID:{self.cap}]'
        wb[RAW]['D2']=13.25
        self.assertEqual(self.apply(wb),(1,1))
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(13.25,)])
