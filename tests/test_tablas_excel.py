"""Filled classroom tables and portable, selectable final matrix exports."""
from pathlib import Path
import json,unittest
import openpyxl
import db
from db_safety import connection
from evaluacion_datos import get_answers,get_indicators
from excel_tablas import export_activity,META,ImportResult
from tests import test_instrumentos as fixtures


class TableExcelTests(unittest.TestCase):
    setUp=fixtures.InstrumentWorkbookTests.setUp
    new_session=fixtures.InstrumentWorkbookTests.new_session
    read=fixtures.InstrumentWorkbookTests.read

    def rubric(self):
        self.ids=db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Representa',10),(self.cap,'Explica',10)],self.path)
        db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,notas_por_capacidad={self.cap:13.75},respuestas_instrumento={self.ids[0]:'6',self.ids[1]:'A'})],self.path)
        self.file=Path(self.temp.name)/'tabla.xlsx';export_activity(self.file,self.session,self.path)
        wb=openpyxl.load_workbook(self.file);self.addCleanup(wb.close);return wb

    def apply(self,wb):
        wb.save(self.file);return db.importar_rubrica_o_cotejo_desde_excel(self.session,self.file,'3°','A',self.path)

    def test_filled_rubric_export_matches_table_and_round_trips(self):
        wb=self.rubric();ws=wb['Registro']
        self.assertEqual(ws['A4'].value,'N°');self.assertEqual(ws['B4'].value,'Apellidos y nombres')
        self.assertEqual(ws['A7'].value,'01');self.assertEqual(ws['B7'].value,'Roque, Ana María')
        self.assertEqual(ws['C7'].value,'6');self.assertEqual(ws['D7'].value,'A');self.assertEqual(ws.freeze_panes,'C7')
        self.assertEqual(ws['A4'].fill.fgColor.rgb[-6:],'E0F2FE')
        self.assertEqual([s.title for s in wb if s.sheet_state=='visible'],['Registro','Instrumento'])
        result=self.apply(wb);self.assertIsInstance(result,ImportResult);self.assertEqual(result.session_id,self.session)
        self.assertEqual(len(get_indicators(self.session,self.path)),2)
        self.assertEqual(get_answers(self.session,self.path),{(self.student,self.ids[0]):'6',(self.student,self.ids[1]):'A'})
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(13.75,)])

    def test_missing_competency_capacity_and_criteria_are_created_without_replacing_old_activity(self):
        wb=self.rubric();wb['Instrumento']['B3']='Competencia importada nueva';wb['Instrumento']['A7']='Capacidad nueva';wb['Registro']['C7']=8
        result=self.apply(wb);self.assertNotEqual(result.session_id,self.session)
        self.assertTrue(any('Competencia nueva' in change for change in result.changes))
        self.assertEqual(self.read(f'SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id={self.session}'),[(13.75,)])
        self.assertEqual(len(get_indicators(result.session_id,self.path)),2)
        again=self.apply(wb);self.assertEqual(again.session_id,result.session_id)
        self.assertFalse(any('Competencia nueva' in change for change in again.changes))

    def test_added_column_creates_missing_criterion(self):
        wb=self.rubric();ws=wb['Registro'];ws.insert_cols(5)
        ws['E4']=self.cap_name;ws['E5']='Comprueba su respuesta';ws['E7']=5
        self.apply(wb)
        self.assertEqual({i['criterio'] for i in get_indicators(self.session,self.path)},{'Representa','Explica','Comprueba su respuesta'})

    def test_invalid_late_score_rolls_back_all_automatically_created_items(self):
        wb=self.rubric();wb['Instrumento']['B3']='No debe guardarse';wb['Instrumento']['A7']='Tampoco guardar';wb['Registro']['D7']=999
        before=self.read('SELECT id,nombre FROM Competencias');caps=self.read('SELECT id,nombre FROM Capacidades')
        with self.assertRaises(ValueError):self.apply(wb)
        self.assertEqual(before,self.read('SELECT id,nombre FROM Competencias'));self.assertEqual(caps,self.read('SELECT id,nombre FROM Capacidades'))
        self.assertEqual(len(get_indicators(self.session,self.path)),2)
        wb['Registro']['D7']='A';wb['Instrumento']['C7']=0
        with self.assertRaises(ValueError):self.apply(wb)
        self.assertEqual(before,self.read('SELECT id,nombre FROM Competencias'))

    def test_plain_table_adapts_names_and_creates_competency_capacity_and_student(self):
        self.file=Path(self.temp.name)/'externo.xlsx';wb=openpyxl.Workbook();self.addCleanup(wb.close);ws=wb.active
        ws.append(['Competencia','Competencia externa']);ws.append(['N°','Estudiante','Capacidad externa'])
        ws.append(['01','Alumno, Nuevo','17 (A)'])
        result=self.apply(wb)
        self.assertNotEqual(result.session_id,self.session)
        self.assertTrue(any('Estudiante nuevo' in c for c in result.changes))
        self.assertEqual(self.read(f'SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id={result.session_id}'),[(17.0,)])
        self.assertFalse(get_indicators(result.session_id,self.path))

    def test_checklist_round_trip_keeps_observations_without_generating_grades(self):
        identity=db.guardar_indicadores_instrumento_sesion(self.session,'Lista de Cotejo',[(self.cap,'Entrega evidencia',1)],self.path)[0]
        db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,respuestas_instrumento={identity:'No'})],self.path)
        self.file=Path(self.temp.name)/'cotejo.xlsx';export_activity(self.file,self.session,self.path)
        wb=openpyxl.load_workbook(self.file);self.addCleanup(wb.close);self.apply(wb)
        self.assertEqual(get_answers(self.session,self.path)[(self.student,identity)],'No')
        self.assertFalse(self.read('SELECT nota FROM Notas_Sesion_Capacidad WHERE nota IS NOT NULL'))

    def test_final_matrix_offers_numbers_letters_and_both_without_losing_exact_grade(self):
        db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,notas_por_capacidad={self.cap:12.5})],self.path)
        structure,rows=db.calcular_matriz_competencias_y_capacidades(self.course,'3°','A',db_path=self.path)
        for presentation,expected in [('numero',12.5),('letra','B'),('ambos','12.5 (B)')]:
            with self.subTest(presentation=presentation):
                file=Path(self.temp.name)/(presentation+'.xlsx')
                db.exportar_matriz_completa_excel(file,self.course_name,'3°','A',structure,rows,presentacion=presentation,db_path=self.path)
                wb=openpyxl.load_workbook(file);self.addCleanup(wb.close);ws=wb.active
                self.assertEqual(ws['A2'].value,'N°');self.assertEqual(ws['A4'].value,'01');self.assertEqual(ws['B4'].value,'Roque, Ana María');self.assertEqual(ws['C4'].value,expected)
                self.assertEqual(ws.freeze_panes,'C4')
                self.assertEqual(ws['C3'].fill.fgColor.rgb[-6:],'E0F2FE')
                self.assertEqual(db.importar_matriz_notas_desde_excel(file,'3°','A',self.path)[0],1)
                self.assertEqual(self.read(f'SELECT nota_manual FROM Notas_Manuales_Capacidad WHERE capacidad_id={self.cap}'),[(12.5,)])

    def test_final_matrix_preserves_precision_and_rejects_invented_grade_for_changed_letter(self):
        db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,notas_por_capacidad={self.cap:12.5})],self.path)
        structure,rows=db.calcular_matriz_competencias_y_capacidades(self.course,'3°','A',db_path=self.path)
        file=Path(self.temp.name)/'letras.xlsx';db.exportar_matriz_completa_excel(file,self.course_name,'3°','A',structure,rows,presentacion='letra',db_path=self.path)
        wb=openpyxl.load_workbook(file);self.addCleanup(wb.close);wb.active['C4']='AD';wb.save(file)
        with self.assertRaises(ValueError):db.importar_matriz_notas_desde_excel(file,'3°','A',self.path)
        self.assertFalse(self.read('SELECT nota_manual FROM Notas_Manuales_Capacidad'))
