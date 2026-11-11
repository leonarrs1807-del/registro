"""Saved student profiles and dual grading must preserve numerical precision."""
from contextlib import closing
from pathlib import Path
import sqlite3,unittest
import openpyxl
import db,biblioteca,ficha_estudiante,periodos,reportes
from presentacion import format_grade
from tests import test_instrumentos as fixtures


class TeacherDataTests(unittest.TestCase):
    setUp=fixtures.InstrumentWorkbookTests.setUp
    new_session=fixtures.InstrumentWorkbookTests.new_session

    def test_student_profile_keeps_pending_and_absent_separate_and_filters_classroom(self):
        unit=periodos.save_unit(self.path,None,None,None,'Unidad 1')
        with db.obtener_conexion(self.path) as conn:periodos.assign_unit(conn,self.session,unit)
        other=db.agregar_estudiante('Otro','Estudiante','3°','A',db_path=self.path)
        db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,asistio=False,
            comentario='Revisar argumento',notas_por_capacidad={self.cap:12.5}),dict(estudiante_id=other,asistio=True,notas_por_capacidad={self.cap:20})],self.path)
        pending=self.new_session()
        before=self.path.read_bytes();data=ficha_estudiante.snapshot(self.path,self.student,self.course)
        self.assertEqual(data['matriz']['promedio_general'],12.5)
        self.assertEqual((data['asistencias'],data['asistencias_registradas']),(0,1))
        self.assertEqual(data['unidades'][0]['evaluadas'],1);self.assertEqual(len(data['actividades']),2)
        self.assertNotIn(20,[n['nota'] for a in data['actividades'] for n in a['notas']])
        self.assertEqual(self.path.read_bytes(),before)

    def test_presentation_keeps_exact_notes_and_boundary_letters(self):
        for value,level in [(0,'C'),(10.5,'B'),(13.5,'A'),(17.5,'AD'),(20,'AD')]:
            self.assertEqual(format_grade(value,'letra'),level)
            self.assertEqual(format_grade(value,'ambos'),format_grade(value,'numero')+f' ({level})')
        self.assertEqual(format_grade(12.3456789,'numero'),'12.3456789')
        self.assertEqual(format_grade(None,'letra'),'Pendiente')

    def test_letter_report_roundtrip_preserves_original_and_rejects_invented_number(self):
        note=12.3456789;db.guardar_notas_globales_sesion(self.session,{self.student:note},self.path)
        path=Path(self.temp.name)/'letras.xlsx'
        reportes.export_grades(path,self.path,self.course,'3°','A',presentation='letra')
        self.assertEqual(reportes.import_grades(path,self.path),1)
        with db.obtener_conexion(self.path) as conn:self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],note)
        wb=openpyxl.load_workbook(path);self.addCleanup(wb.close);ws=wb['Calificativos']
        col=next(i for i,c in enumerate(ws[1],1) if c.value=='calificativo');ws.cell(2,col,'AD');wb.save(path)
        with self.assertRaises(ValueError):reportes.import_grades(path,self.path)
        with db.obtener_conexion(self.path) as conn:self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],note)

    def test_library_excel_round_trip_is_empty_and_keeps_model_structure(self):
        db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Justifica',20)],self.path)
        model=biblioteca.from_session(self.session,self.path,'Modelo para compartir')
        destination=Path(self.temp.name)/'modelo.xlsx';biblioteca.export_excel(destination,model)
        models,warnings=biblioteca.read_source(destination);self.assertFalse(warnings)
        self.assertEqual(models,[model])
        wb=openpyxl.load_workbook(destination);self.addCleanup(wb.close)
        self.assertNotIn('Ana María',str([[c.value for c in row] for row in wb['Registro']]))

    def test_moving_activities_is_atomic_and_keeps_grades(self):
        from organizacion_visual import move_activities
        unit=periodos.save_unit(self.path,None,None,None,'Unidad destino')
        db.guardar_notas_globales_sesion(self.session,{self.student:17.25},self.path)
        with self.assertRaises(ValueError):move_activities([self.session,99999],unit,self.path)
        with db.obtener_conexion(self.path) as conn:self.assertIsNone(conn.execute('SELECT unidad_id FROM Sesiones_Clase WHERE id=?',(self.session,)).fetchone()[0])
        move_activities([self.session],unit,self.path)
        with db.obtener_conexion(self.path) as conn:
            self.assertEqual(conn.execute('SELECT unidad_id FROM Sesiones_Clase WHERE id=?',(self.session,)).fetchone()[0],unit)
            self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],17.25)
