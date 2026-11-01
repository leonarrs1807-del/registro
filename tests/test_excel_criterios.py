"""Excel-first sessions, independent criteria, visible levels and derived notes."""
import json
import openpyxl
import unittest
import db,reportes
from evaluacion_datos import get_answers
from instrumentos_excel import IND,META
from plantilla_excel import EVALUAR,RESUMEN
from tests import test_instrumentos as legacy_tests


class ExcelFirstTests(unittest.TestCase):
    setUp=legacy_tests.InstrumentWorkbookTests.setUp
    new_session=legacy_tests.InstrumentWorkbookTests.new_session
    read=legacy_tests.InstrumentWorkbookTests.read
    apply=legacy_tests.InstrumentWorkbookTests.apply
    saved=legacy_tests.InstrumentWorkbookTests.saved

    def model(self,kind='Rúbrica',counts=None,blank=True):
        self.file=__import__('pathlib').Path(self.temp.name)/'excel-criterios.xlsx'
        activity=next(s for s in db.obtener_sesiones_clase(self.course,'3°','A',db_path=self.path) if s['id']==self.session)
        db.exportar_plantilla_rubrica_o_cotejo_excel(self.file,self.course_name,'3°','A','Resolver ecuaciones',self.comp_name,
            [(c['capacidad_id'],c['capacidad_nombre'],c['criterio_precisado']) for c in activity['capacidades']],kind,self.path,
            sesion_id=self.session,desde_cero=blank,criterios_por_capacidad=counts or {self.cap:2})
        wb=openpyxl.load_workbook(self.file);self.addCleanup(wb.close)
        meta={r[0].value:r[1].value for r in wb[META]};self.layout=json.loads(meta['layout_rows'])
        return wb

    def complete(self,wb):
        for n,item in enumerate(self.layout,1):
            row=item['row'];wb[IND].cell(row,3,f'Criterio de ecuaciones {n}')
            if 'points_row' in item:
                for col,text in enumerate(['Necesita apoyo para representar','Representa parte del problema','Resuelve y explica','Comprueba y sustenta'],4):wb[IND].cell(row,col,text)

    def test_blank_model_has_session_context_two_criteria_and_no_invented_descriptors(self):
        wb=self.model()
        self.assertIn('Resolver ecuaciones',wb[IND]['A1'].value)
        self.assertEqual(len(self.layout),2)
        for item in self.layout:
            self.assertEqual(wb[IND].cell(item['row'],2).value,self.cap_name)
            self.assertTrue(all(wb[IND].cell(item['row'],col).value is None for col in range(4,8)))
        self.assertFalse(db.obtener_indicadores_instrumento_sesion(self.session,self.path))
        self.assertEqual(wb.sheetnames[:3],[IND,EVALUAR,RESUMEN])
        self.assertEqual(wb[RESUMEN]['D2'].data_type,'f')

    def test_two_numeric_criteria_produce_one_capacity_note_without_formula_cache(self):
        wb=self.model();self.complete(wb);wb[EVALUAR]['D2']=6;wb[EVALUAR]['E2']=8
        self.assertEqual(self.apply(wb),(2,1))
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(14.0,)])
        self.assertEqual(sorted(get_answers(self.session,self.path).values()),['6','8'])

    def test_levels_use_each_criterion_scale_and_custom_maximum(self):
        wb=self.model();self.complete(wb)
        for entry in self.layout:
            wb[IND].cell(entry['row'],8,10)
            for col,value in enumerate([2,5,8,10],4):wb[IND].cell(entry['points_row'],col,value)
        wb[EVALUAR]['D2']='A';wb[EVALUAR]['E2']='AD';self.apply(wb)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(18.0,)])

    def test_checklist_multiple_criteria_and_weights(self):
        wb=self.model('Lista de Cotejo');self.complete(wb)
        wb[IND].cell(self.layout[0]['row'],5,6);wb[IND].cell(self.layout[1]['row'],5,4)
        wb[EVALUAR]['D2']='Sí';wb[EVALUAR]['E2']='No';self.apply(wb)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(12.0,)])

    def test_multiple_capacities_keep_separate_criteria_and_real_zero(self):
        other=db.obtener_capacidades_por_competencia(self.comp,self.path)[1][0]
        db.crear_o_actualizar_sesion_clase(self.session,self.course,self.comp,'3°','A','Dos capacidades','',1,[(self.cap,'Uno'),(other,'Dos')],db_path=self.path)
        wb=self.model(counts={self.cap:2,other:1});self.complete(wb)
        wb[EVALUAR]['D2']=6;wb[EVALUAR]['E2']=8;wb[EVALUAR]['F2']=0;self.apply(wb)
        self.assertEqual(self.read('SELECT capacidad_id,nota FROM Notas_Sesion_Capacidad ORDER BY capacidad_id'),[(self.cap,14.0),(other,0.0)])

    def test_partial_criterion_rejects_import_and_keeps_previous_grade(self):
        self.saved();wb=self.model();self.complete(wb);wb[EVALUAR]['D2']='A'
        with self.assertRaisesRegex(ValueError,'todos los indicadores'):self.apply(wb)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(17.0,)])
        self.assertFalse(db.obtener_indicadores_instrumento_sesion(self.session,self.path))

    def test_capacity_summary_cannot_replace_individual_answers(self):
        self.saved();wb=self.model();self.complete(wb);wb[RESUMEN]['D2']=19
        with self.assertRaisesRegex(ValueError,'resumen se calcula'):self.apply(wb)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'),[(17.0,)])

    def test_all_four_descriptors_stay_visible_after_school_branding(self):
        wb=self.model();self.complete(wb);wb.save(self.file);reportes.decorate_workbook(self.file)
        checked=openpyxl.load_workbook(self.file);self.addCleanup(checked.close)
        self.assertEqual(checked[IND].sheet_view.zoomScale,90)
        self.assertTrue(all(not checked[IND].column_dimensions[c].hidden for c in 'DEFG'))
        self.assertFalse(any(str(c.value).startswith('Puntos ') for c in checked[IND][3]))
        self.assertEqual(checked[IND]['D5'].number_format,'General')

    def test_changed_hidden_identity_is_rejected_without_writes(self):
        wb=self.model();self.complete(wb);wb[IND]['I4']='I999';wb[EVALUAR]['D2']='AD';wb[EVALUAR]['E2']='A'
        with self.assertRaisesRegex(ValueError,'identidad'):self.apply(wb)
        self.assertFalse(self.read('SELECT nota FROM Notas_Sesion_Capacidad'))
