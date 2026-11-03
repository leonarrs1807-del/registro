"""Observation-only checklists, explicit conversion and clean two-sheet files."""
import hashlib,json
from pathlib import Path
import unittest
import openpyxl
import db,documento
from cotejo import summary,preview,configuration,store_rule
from evaluacion_datos import get_indicators,get_answers
from plantilla_simple import INSTRUMENTO,REGISTRO
from instrumentos_excel import META
from tests import test_instrumentos as fixtures


class SimpleChecklistTests(unittest.TestCase):
    setUp=fixtures.InstrumentWorkbookTests.setUp
    new_session=fixtures.InstrumentWorkbookTests.new_session
    read=fixtures.InstrumentWorkbookTests.read
    apply=fixtures.InstrumentWorkbookTests.apply
    saved=fixtures.InstrumentWorkbookTests.saved

    def model(self,kind='Lista de Cotejo',with_students=True):
        self.file=Path(self.temp.name)/'simple.xlsx'
        db.exportar_plantilla_rubrica_o_cotejo_excel(self.file,self.course_name,'3°','A','Fracciones',self.comp_name,
            [(self.cap,self.cap_name,'')],kind,self.path,sesion_id=self.session,criterios_por_capacidad={self.cap:2},desde_cero=True,formato=5,incluir_estudiantes=with_students)
        wb=openpyxl.load_workbook(self.file);self.addCleanup(wb.close)
        meta={r[0].value:r[1].value for r in wb[META]};self.layout=json.loads(meta['layout_rows'])
        return wb

    def complete(self,wb,rubric=False):
        for n,entry in enumerate(self.layout,1):
            wb[INSTRUMENTO].cell(entry['row'],3,f'Indicador {n}')
            if rubric:
                for col,text in enumerate(['Con apoyo','Parcial','Autónomo','Sustentado'],4):wb[INSTRUMENTO].cell(entry['row'],col,text)

    def test_blank_export_has_two_visible_sheets_and_no_student_names_anywhere(self):
        wb=self.model(with_students=False)
        self.assertEqual([s.title for s in wb if s.sheet_state=='visible'],[INSTRUMENTO,REGISTRO])
        for ws in wb:
            for row in ws:
                for cell in row:
                    self.assertNotIn('Ana María',str(cell.value));self.assertNotIn('Roque',str(cell.value))
        self.assertTrue(all(wb[REGISTRO].cell(row,4).value is None for row in range(2,23)))

    def test_checklist_import_stores_yes_no_without_creating_grades(self):
        wb=self.model();self.complete(wb);wb[REGISTRO]['E2']='Sí';wb[REGISTRO]['F2']='No'
        self.assertEqual(self.apply(wb),(2,1));self.assertFalse(self.read('SELECT nota FROM Notas_Sesion_Capacidad'))
        state=summary(get_indicators(self.session,self.path),get_answers(self.session,self.path))[(self.student,self.cap)]
        self.assertEqual((state['cumplidos'],state['evaluados'],state['pendientes']),(1,2,0))
        self.assertEqual(configuration(self.session,self.path)[0]['tipo'],'orientacion')

    def test_pending_checklist_is_not_counted_as_no_and_never_converted(self):
        wb=self.model();self.complete(wb);wb[REGISTRO]['E2']='Sí';wb[REGISTRO]['F2']='Sin evaluar';self.apply(wb)
        items=get_indicators(self.session,self.path);answers=get_answers(self.session,self.path)
        row=summary(items,answers)[(self.student,self.cap)]
        self.assertEqual((row['cumplidos'],row['evaluados'],row['pendientes']),(1,1,1))
        self.assertFalse(preview(items,answers,{'tipo':'proporcional'}))
        self.assertFalse(self.read('SELECT nota FROM Notas_Sesion_Capacidad'))

    def test_conversion_requires_an_explicit_rule_and_does_not_write_during_preview(self):
        wb=self.model();self.complete(wb);wb[REGISTRO]['E2']='Sí';wb[REGISTRO]['F2']='No';self.apply(wb)
        items=get_indicators(self.session,self.path);answers=get_answers(self.session,self.path)
        with self.assertRaises(ValueError):preview(items,answers,None)
        self.assertEqual(preview(items,answers,{'tipo':'proporcional'}),{(self.student,self.cap):10})
        custom={'tipo':'tramos','tramos':[dict(minimo=0,nota=0),dict(minimo=50,nota=14),dict(minimo=100,nota=20)]}
        self.assertEqual(preview(items,answers,custom),{(self.student,self.cap):14})
        self.assertFalse(self.read('SELECT nota FROM Notas_Sesion_Capacidad'))
        db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,notas_por_capacidad={self.cap:14})],self.path,regla_cotejo=custom)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(14.0,)])
        self.assertEqual(configuration(self.session,self.path),(custom,False))

    def test_invalid_conversion_rolls_back_grade_and_rule(self):
        wb=self.model();self.complete(wb);self.apply(wb);self.saved()
        with self.assertRaises(ValueError):
            db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,notas_por_capacidad={self.cap:12})],self.path,regla_cotejo={'tipo':'tramos','tramos':[dict(minimo=0,nota=0),dict(minimo=50,nota=21)]})
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(17.0,)])

    def test_rubric_optional_points_use_the_configured_scale_and_manual_points(self):
        wb=self.model('Rúbrica');self.complete(wb,True)
        self.assertIsNone(wb[INSTRUMENTO].cell(self.layout[0]['points_row'],4).value)
        wb[REGISTRO]['E2']='A';wb[REGISTRO]['F2']='8';self.apply(wb)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(15.75,)])

    def test_unused_new_criterion_can_be_left_blank(self):
        wb=self.model('Rúbrica');entry=self.layout[0];wb[INSTRUMENTO].cell(entry['row'],3,'Un criterio')
        for col,text in enumerate(['Apoyo','Parcial','Autónomo','Sustentado'],4):wb[INSTRUMENTO].cell(entry['row'],col,text)
        wb[REGISTRO]['E2']=6;self.assertEqual(self.apply(wb),(1,1))
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(12.0,)])

    def test_empty_template_matches_an_existing_real_student_by_visible_name(self):
        wb=self.model(with_students=False);self.complete(wb);wb[REGISTRO]['D2']='Roque, Ana María';wb[REGISTRO]['E2']='Sí'
        self.assertEqual(self.apply(wb),(2,1));self.assertEqual(list(get_answers(self.session,self.path).values()),['Sí'])

    def test_changed_visible_identity_and_invalid_points_are_rejected_atomically(self):
        wb=self.model('Rúbrica');self.complete(wb,True);wb[REGISTRO]['D2']='Nombre cambiado';wb[REGISTRO]['E2']=5
        with self.assertRaises(ValueError):self.apply(wb)
        self.assertFalse(get_indicators(self.session,self.path))
        wb[REGISTRO]['D2']='Roque, Ana María';wb[REGISTRO]['E2']=11
        with self.assertRaises(ValueError):self.apply(wb)
        self.assertFalse(self.read('SELECT nota FROM Notas_Sesion_Capacidad'))

    def test_new_empty_record_keeps_backup_credentials_and_curriculum(self):
        self.saved();before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        target=Path(self.temp.name)/'nuevo.db';backup=documento.new_empty_record(self.path,target)
        self.assertTrue(backup.is_file());self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),before)
        with db.obtener_conexion(target) as conn:
            for table in ['Estudiantes','Sesiones_Clase','Notas_Sesion_Capacidad','Instrumento_Respuestas','Historial_Notas']:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
            self.assertGreater(conn.execute('SELECT COUNT(*) FROM Capacidades').fetchone()[0],0)
        with db.obtener_conexion(target) as conn,db.obtener_conexion(self.path) as original:
            self.assertEqual(conn.execute('SELECT clave FROM Docente_Config').fetchone(),original.execute('SELECT clave FROM Docente_Config').fetchone())

    def test_student_template_does_not_include_example_people(self):
        file=Path(self.temp.name)/'alumnos.xlsx';db.generar_plantilla_excel_estudiantes(file)
        wb=openpyxl.load_workbook(file);self.addCleanup(wb.close)
        self.assertEqual(wb.active.max_row,1)
