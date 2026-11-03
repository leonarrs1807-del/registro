"""Published grades, saved evidence and weighted results through real SQLite APIs."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import db
from evaluacion_datos import get_answers,get_indicators,grade_answers
from instrumentos import default_scores,normalized_grade


class EvaluationDataTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'evaluacion.db';db.inicializar_db(self.path)
        self.course=db.obtener_cursos(db_path=self.path)[0][0]
        self.comp=db.obtener_competencias_por_curso(self.course,self.path)[0][0]
        self.cap=db.obtener_capacidades_por_competencia(self.comp,self.path)[0][0]
        self.student=db.agregar_estudiante('Ana','Roque','3°','A',db_path=self.path)
        self.session=db.crear_o_actualizar_sesion_clase(None,self.course,self.comp,'3°','A','Evaluación','',1,[(self.cap,'Explica')],db_path=self.path)

    def indicators(self,kind='Rúbrica'):
        ids=db.guardar_indicadores_instrumento_sesion(self.session,kind,[(self.cap,'Explica',10),(self.cap,'Comprueba',10)],self.path)
        return ids

    def save(self,answers,grade=14):
        db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,
            notas_por_capacidad={self.cap:grade},respuestas_instrumento=answers)],self.path)

    def test_levels_survive_reopen_and_reproduce_the_published_grade(self):
        first,second=self.indicators();self.save({first:'A',second:'AD'},17.75)
        answers=get_answers(self.session,self.path)
        self.assertEqual(answers,{(self.student,first):'A',(self.student,second):'AD'})
        grades,pending=grade_answers(get_indicators(self.session,self.path),answers)
        self.assertFalse(pending);self.assertEqual(grades[(self.student,self.cap)],17.75)

    def test_renaming_keeps_identity_and_answers_and_archiving_keeps_history(self):
        first,second=self.indicators();self.save({first:'B',second:'A'})
        rows=get_indicators(self.session,self.path);rows[0]['criterio']='Explica y sustenta'
        self.assertEqual(db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',rows,self.path),[first,second])
        self.assertEqual(get_answers(self.session,self.path)[(self.student,first)],'B')
        db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',rows[:1],self.path)
        self.assertEqual(get_answers(self.session,self.path),{(self.student,first):'B'})
        with db.obtener_conexion(self.path) as conn:
            self.assertEqual(conn.execute('SELECT activo FROM Instrumento_Indicadores WHERE id=?',(second,)).fetchone()[0],0)
            self.assertEqual(conn.execute('SELECT respuesta FROM Instrumento_Respuestas WHERE indicador_id=?',(second,)).fetchone()[0],'A')
            self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],14)

    def test_changing_maximum_rescales_numeric_evidence_without_publishing_notes(self):
        first,second=self.indicators();self.save({first:7.5,second:'A'},15.25)
        rows=get_indicators(self.session,self.path);rows[0]['puntaje_maximo']=4;rows[0]['puntajes']=default_scores(4)
        db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',rows,self.path)
        self.assertEqual(float(get_answers(self.session,self.path)[(self.student,first)]),3)
        with db.obtener_conexion(self.path) as conn:self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],15.25)

    def test_late_foreign_answer_rolls_back_grades_responses_and_method(self):
        first,second=self.indicators();self.save({first:'A'},16)
        other=db.agregar_estudiante('Beto','Otro','4°','A',db_path=self.path)
        with self.assertRaises(ValueError):
            db.guardar_calificaciones_y_asistencia_sesion(self.session,[
                dict(estudiante_id=self.student,notas_por_capacidad={self.cap:0},respuestas_instrumento={first:'NE'}),
                dict(estudiante_id=other,respuestas_instrumento={second:'A'})],self.path,nuevo_instrumento='Nota directa')
        self.assertEqual(get_answers(self.session,self.path),{(self.student,first):'A'})
        with db.obtener_conexion(self.path) as conn:
            self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],16)
            self.assertEqual(conn.execute('SELECT tipo_instrumento FROM Sesiones_Clase').fetchone()[0],'Rúbrica')

    def test_checklist_false_and_numeric_zero_are_real_answers(self):
        first,second=self.indicators('Lista de Cotejo');self.save({first:False,second:0},0)
        answers=get_answers(self.session,self.path)
        self.assertEqual(set(answers.values()),{'No'})
        grades,pending=grade_answers(get_indicators(self.session,self.path),answers)
        self.assertEqual(grades[(self.student,self.cap)],0);self.assertFalse(pending)
        self.save({second:None},0)
        grades,pending=grade_answers(get_indicators(self.session,self.path),get_answers(self.session,self.path))
        self.assertEqual(grades[(self.student,self.cap)],0);self.assertEqual(pending,{(self.student,self.cap)})

    def test_decimal_half_is_rounded_up_and_unevaluated_is_not_zero(self):
        self.assertEqual(normalized_grade('Rúbrica',[('1.2345',2)]),12.35)
        with self.assertRaises(ValueError):normalized_grade('Lista de Cotejo',[('Sí',10),(None,10)])

    def test_partial_weighted_grade_uses_only_answered_maxima_including_zero(self):
        self.assertEqual(normalized_grade('Rúbrica',[(3,4),(None,10),(0,6)],allow_pending=True),6)
        self.assertEqual(normalized_grade('Rúbrica',[(3,4),(None,10)],allow_pending=True),15)
        with self.assertRaises(ValueError):normalized_grade('Rúbrica',[(None,10)],allow_pending=True)
        with self.assertRaises(ValueError):normalized_grade('Rúbrica',[(5,4),(None,10)],allow_pending=True)

    def test_partial_answers_protect_their_class_and_capacity(self):
        first,second=self.indicators();self.save({first:'B'},None)
        other=db.obtener_capacidades_por_competencia(self.comp,self.path)[1][0]
        with self.assertRaisesRegex(ValueError,'respuestas'):
            db.crear_o_actualizar_sesion_clase(self.session,self.course,self.comp,'3°','A','No aplicar','',1,[(other,'Otro criterio')],db_path=self.path)
        self.assertEqual(get_answers(self.session,self.path),{(self.student,first):'B'})

    def test_search_average_uses_saved_numbers_and_keeps_two_decimals(self):
        other=db.obtener_capacidades_por_competencia(self.comp,self.path)[1][0]
        db.crear_o_actualizar_sesion_clase(self.session,self.course,self.comp,'3°','A','Dos capacidades','',1,[(self.cap,'Uno'),(other,'Dos')],db_path=self.path)
        db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,notas_por_capacidad={self.cap:12.75,other:0})],self.path)
        rows=db.obtener_historial_vertical_estudiantes(self.course,'3°','A',db_path=self.path)
        self.assertEqual(rows[0]['promedio'],'6.38')


class WeightedGradeTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'promedios.db';db.inicializar_db(self.path)
        self.course=db.obtener_cursos(db_path=self.path)[0][0]
        comps=db.obtener_competencias_por_curso(self.course,self.path)
        self.comp,self.comp2=comps[0][0],comps[1][0]
        self.a,self.b=[r[0] for r in db.obtener_capacidades_por_competencia(self.comp,self.path)[:2]]
        self.c=db.obtener_capacidades_por_competencia(self.comp2,self.path)[0][0]
        self.student=db.agregar_estudiante('Ana','Pérez','3°','A',db_path=self.path)

    def activity(self,kind,weight,notes):
        sid=db.crear_o_actualizar_sesion_clase(None,self.course,self.comp,'3°','A',kind,'',weight,[(self.a,''),(self.b,'')],categoria=kind,db_path=self.path)
        db.guardar_calificaciones_y_asistencia_sesion(sid,[dict(estudiante_id=self.student,notas_por_capacidad=notes)],self.path)
        return sid

    def result(self):return db.calcular_matriz_competencias_y_capacidades(self.course,'3°','A',self.path)[1][0]

    def test_weighted_categories_capacities_competencies_and_final_half_cent(self):
        self.activity('Clases',1,{self.a:10,self.b:20})
        self.activity('Clases',3,{self.a:18,self.b:None})
        self.activity('Exámenes',1.5,{self.a:14,self.b:0})
        self.activity('Trabajos',1,{self.b:16})
        self.activity('Prácticas / Otros',1,{self.a:0})
        db.guardar_nota_manual_capacidad(self.student,self.c,17.25,self.path)
        row=self.result()
        # Independent hand calculation: class A=16; A=(16*40+14*25)/80.
        # B=(20*40+0*25+16*20)/85. Competency=(12.38+13.18)/2.
        self.assertEqual(row['notas_capacidad'][self.a],12.38)
        self.assertEqual(row['notas_capacidad'][self.b],13.18)
        self.assertEqual(row['notas_competencia'][self.comp],12.78)
        self.assertEqual(row['promedio_general'],15.02)

    def test_missing_values_zero_category_and_manual_override(self):
        self.activity('Clases',1.5,{self.a:12})
        self.activity('Clases',.5,{self.a:0})
        self.activity('Exámenes',1,{self.a:20})
        db.guardar_pesos_rubros_curso(self.course,100,0,0,0,self.path)
        row=self.result();self.assertEqual(row['notas_capacidad'][self.a],9)
        self.assertIsNone(row['notas_capacidad'][self.b]);self.assertEqual(row['promedio_general'],9)
        db.guardar_nota_manual_capacidad(self.student,self.a,0,self.path)
        self.assertEqual(self.result()['promedio_general'],0)
        db.guardar_nota_manual_capacidad(self.student,self.a,None,self.path)
        self.assertEqual(self.result()['promedio_general'],9)

