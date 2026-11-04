"""A global score counts once per selected capacity, with worksheets inside Trabajos."""
from pathlib import Path
import unittest,openpyxl
import db
from evaluacion_datos import activity
from excel_tablas import export_activity
from tests import test_instrumentos as fixtures


class GlobalWorksheetTests(unittest.TestCase):
    setUp=fixtures.InstrumentWorkbookTests.setUp
    new_session=fixtures.InstrumentWorkbookTests.new_session
    read=fixtures.InstrumentWorkbookTests.read

    def make(self,category='Exámenes',kind='Prueba',method='Nota global'):
        self.caps=db.obtener_capacidades_por_competencia(self.comp,self.path)
        return db.crear_o_actualizar_sesion_clase(None,self.course,self.comp,'3°','A','Prueba de ecuaciones','Explicar y comprobar una solución',1,[(c[0],'') for c in self.caps],categoria=category,db_path=self.path,tipo_actividad=kind,metodo=method)

    def test_five_repeats_only_on_selected_capacities_and_competency_average_is_five(self):
        sid=self.make();db.guardar_notas_globales_sesion(sid,{self.student:5},self.path)
        self.assertEqual(self.read(f'SELECT capacidad_id,nota FROM Notas_Sesion_Capacidad WHERE sesion_id={sid}'),[(c[0],5.0) for c in self.caps])
        structure,rows=db.calcular_matriz_competencias_y_capacidades(self.course,'3°','A',db_path=self.path)
        self.assertEqual(rows[0]['notas_competencia'][self.comp],5)
        self.assertEqual(rows[0]['promedio_general'],5)
        other=db.obtener_competencias_por_curso(self.course,self.path)[1][0]
        self.assertIsNone(rows[0]['notas_competencia'][other])
        self.assertEqual(activity(sid,self.path)['modo_ingreso'],'global')

    def test_worksheet_in_trabajos_uses_its_rubro_percentage_without_extra_category(self):
        exam=self.make();sheet=self.make('Trabajos','Ficha de trabajo')
        db.guardar_pesos_rubros_curso(self.course,0,40,60,0,self.path)
        db.guardar_notas_globales_sesion(exam,{self.student:5},self.path);db.guardar_notas_globales_sesion(sheet,{self.student:15},self.path)
        structure,rows=db.calcular_matriz_competencias_y_capacidades(self.course,'3°','A',db_path=self.path)
        self.assertEqual(rows[0]['promedio_general'],11)
        self.assertEqual(activity(sheet,self.path)['categoria'],'Trabajos');self.assertEqual(activity(sheet,self.path)['tipo_actividad'],'Ficha de trabajo')
        self.assertEqual(len(db.obtener_pesos_rubros_curso(self.course,self.path)),4)

    def test_global_zero_and_pending_are_different_and_failed_batch_rolls_back(self):
        sid=self.make();other=db.agregar_estudiante('Otro','Alumno','3°','A',db_path=self.path)
        db.guardar_notas_globales_sesion(sid,{self.student:0,other:None},self.path)
        self.assertEqual(self.read(f'SELECT DISTINCT nota FROM Notas_Sesion_Capacidad WHERE estudiante_id={self.student}'),[(0.0,)])
        before=self.read('SELECT * FROM Notas_Sesion_Capacidad')
        with self.assertRaises(ValueError):db.guardar_notas_globales_sesion(sid,{self.student:18,other:21},self.path)
        self.assertEqual(before,self.read('SELECT * FROM Notas_Sesion_Capacidad'))

    def test_worksheet_accepts_each_instrument_and_other_category_is_rejected(self):
        for method in ['Nota global','Nota directa','Rúbrica','Lista de Cotejo']:
            sid=self.make('Trabajos','Ficha de trabajo',method)
            expected=method if method in ('Rúbrica','Lista de Cotejo') else 'Normal'
            self.assertEqual(activity(sid,self.path)['tipo_instrumento'],expected)
        with self.assertRaises(ValueError):self.make('Exámenes','Ficha de trabajo')

    def test_export_has_purpose_compact_headers_and_optional_summary(self):
        sid=self.make('Trabajos','Ficha de trabajo','Rúbrica')
        db.guardar_indicadores_instrumento_sesion(sid,'Rúbrica',[(c[0],'Resuelve y comprueba',20) for c in self.caps],self.path)
        file=Path(self.temp.name)/'rubrica.xlsx';export_activity(file,sid,self.path)
        wb=openpyxl.load_workbook(file);self.addCleanup(wb.close)
        self.assertEqual(wb['Instrumento']['B4'].value,'Explicar y comprobar una solución')
        self.assertIn('Explicar y comprobar',wb['Registro']['A3'].value)
        self.assertNotIn('resumen',[wb['Registro'].cell(6,c).value for c in range(1,wb['Registro'].max_column+1)])
        self.assertLessEqual(wb['Registro'].row_dimensions[4].height,64)
        export_activity(file,sid,self.path,include_summary=True)
        other=openpyxl.load_workbook(file);self.addCleanup(other.close)
        self.assertIn('resumen',[other['Registro'].cell(6,c).value for c in range(1,other['Registro'].max_column+1)])

    def test_importing_worksheet_to_another_competency_preserves_trabajos_and_global_mode(self):
        sid=self.make('Trabajos','Ficha de trabajo');db.guardar_notas_globales_sesion(sid,{self.student:5},self.path)
        file=Path(self.temp.name)/'ficha.xlsx';export_activity(file,sid,self.path)
        wb=openpyxl.load_workbook(file);self.addCleanup(wb.close);wb['Instrumento']['B3']='Competencia de la ficha importada';wb.save(file)
        result=db.importar_rubrica_o_cotejo_desde_excel(self.session,file,'3°','A',self.path)
        target=activity(result.session_id,self.path)
        self.assertEqual((target['categoria'],target['tipo_actividad'],target['modo_ingreso']),('Trabajos','Ficha de trabajo','global'))
        self.assertEqual(target['proposito'],'Explicar y comprobar una solución')
