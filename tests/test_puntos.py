from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import db
import puntos
import documento
import app_storage
from db_safety import connection


class PointsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'practicas.db'
        db.inicializar_db(self.path)
        self.course = db.obtener_cursos(db_path=self.path)[0][0]
        self.comp = db.obtener_competencias_por_curso(self.course, self.path)[0][0]
        self.caps = [r[0] for r in db.obtener_capacidades_por_competencia(self.comp, self.path)]
        self.student = db.agregar_estudiante('Ana', 'Prueba', '3°', 'A', db_path=self.path)
        self.block = puntos.create_block(self.path, self.course, self.comp, '3°', 'A', 'Ecuaciones', self.caps)

    def exercises(self):
        return puntos.details(self.path, self.block)['exercises']

    def add_two(self):
        puntos.add_practice(self.path, self.block, 'Primera', [('Uno', 5), ('Dos', 5)])
        puntos.add_practice(self.path, self.block, 'Segunda', [('Uno', 3), ('Dos', 3), ('Tres', 4)])

    def scores(self, values):
        puntos.save_scores(self.path, self.block, [(e['id'], self.student, value) for e, value in zip(self.exercises(), values)])

    def test_two_short_practices_accumulate_one_exam_and_keep_weights(self):
        weights = db.obtener_pesos_rubros_curso(self.course, self.path)
        self.add_two()
        self.scores([3, 3, 3, 2, 3])
        result = puntos.summary(self.path, self.block)[0]
        self.assertEqual((result['obtenido'], result['maximo'], result['nota']), (14, 20, 14))
        sid = puntos.consolidate(self.path, self.block)
        with connection(self.path) as conn:
            self.assertEqual(conn.execute('SELECT categoria FROM Sesiones_Clase WHERE id=?', (sid,)).fetchone()[0], 'Exámenes')
            notes = conn.execute('SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?', (sid,)).fetchall()
        self.assertEqual(notes, [(14,)] * len(self.caps))
        self.assertEqual(weights, db.obtener_pesos_rubros_curso(self.course, self.path))
        with self.assertRaises(ValueError):
            puntos.consolidate(self.path, self.block)

    def test_normalizes_total_instead_of_averaging_practice_grades(self):
        puntos.add_practice(self.path, self.block, 'Primera', [('Uno', 10)])
        puntos.add_practice(self.path, self.block, 'Segunda', [('Uno', 15)])
        self.scores([10, 10])
        self.assertEqual(puntos.summary(self.path, self.block)[0]['nota'], 16)

    def test_missing_is_pending_and_zero_is_a_real_grade(self):
        self.add_two()
        self.scores([0, 0, 0, 0, ''])
        self.assertIsNone(puntos.summary(self.path, self.block)[0]['nota'])
        with self.assertRaisesRegex(ValueError, 'sin calificar'):
            puntos.consolidate(self.path, self.block)
        self.scores([0, 0, 0, 0, 0])
        self.assertEqual(puntos.summary(self.path, self.block)[0]['nota'], 0)
        puntos.consolidate(self.path, self.block)

    def test_invalid_batch_rolls_back_all_cells(self):
        self.add_two()
        self.scores([1, 1, 1, 1, 1])
        for bad in (6, -1, 'nan', 'inf', 'texto'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.scores([2, bad, 2, 2, 2])
            self.assertEqual(puntos.summary(self.path, self.block)[0]['obtenido'], 5)

    def test_reopening_updates_same_exam_preserving_attendance(self):
        self.add_two(); self.scores([3, 3, 3, 2, 3])
        sid = puntos.consolidate(self.path, self.block)
        db.guardar_calificaciones_y_asistencia_sesion(sid, [dict(estudiante_id=self.student, asistio=False,
            comentario='Conservar', notas_por_capacidad={self.caps[0]: 14})], db_path=self.path)
        puntos.reopen(self.path, self.block)
        self.scores([4, 3, 3, 2, 3])
        self.assertEqual(puntos.consolidate(self.path, self.block), sid)
        with connection(self.path) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM Sesiones_Clase').fetchone()[0], 1)
        _, state, _ = db.obtener_estado_planilla_sesion(sid, '3°', 'A', db_path=self.path)
        self.assertEqual(puntos.summary(self.path, self.block)[0]['nota'], 15)
        self.assertIn(self.student, state)
        self.assertFalse(state[self.student][0])
        self.assertEqual(state[self.student][1], 'Conservar')

    def test_failed_publication_is_atomic(self):
        self.add_two(); self.scores([3, 3, 3, 2, 3])
        with patch('db.guardar_calificaciones_y_asistencia_sesion', side_effect=ValueError('interrumpido')):
            with self.assertRaises(ValueError):puntos.consolidate(self.path, self.block)
        with connection(self.path) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM Sesiones_Clase').fetchone()[0], 0)
        self.assertEqual(puntos.details(self.path, self.block)['block']['estado'], 'abierto')

    def test_excluding_practice_preserves_scores_and_changes_denominator(self):
        self.add_two(); self.scores([3, 3, 3, 2, 3])
        practice = puntos.details(self.path, self.block)['practices'][1]['id']
        puntos.toggle_practice(self.path, practice)
        self.assertEqual(puntos.summary(self.path, self.block)[0]['nota'], 12)
        puntos.toggle_practice(self.path, practice)
        self.assertEqual(puntos.summary(self.path, self.block)[0]['nota'], 14)

    def test_wrong_class_or_level_cannot_receive_points(self):
        self.add_two()
        other = db.agregar_estudiante('Otro', 'Alumno', '4°', 'A', db_path=self.path)
        with self.assertRaises(ValueError):
            puntos.save_scores(self.path, self.block, [(self.exercises()[0]['id'], other, 1)])
        with connection(self.path) as conn:conn.execute("UPDATE Docente_Config SET nivel_educativo='Primaria'")
        primary = db.obtener_cursos(db_path=self.path)[0][0]
        comp = db.obtener_competencias_por_curso(primary, self.path)[0][0]
        cap = db.obtener_capacidades_por_competencia(comp, self.path)[0][0]
        block = puntos.create_block(self.path, primary, comp, '3°', 'A', 'Sumas', [cap])
        self.assertEqual(puntos.details(self.path, block)['students'], [])

    def test_closed_period_blocks_reopening_and_points(self):
        self.add_two(); self.scores([3, 3, 3, 2, 3]); puntos.consolidate(self.path, self.block)
        with connection(self.path) as conn:
            conn.execute('CREATE TABLE Estado_Periodo(id INTEGER PRIMARY KEY,cerrado INTEGER)')
            conn.execute('INSERT INTO Estado_Periodo VALUES(1,1)')
        with self.assertRaises(ValueError):puntos.reopen(self.path, self.block)
        self.assertEqual(puntos.details(self.path, self.block)['block']['estado'], 'consolidado')

    def test_native_document_preserves_points_but_new_period_starts_empty(self):
        self.add_two(); self.scores([3, 3, 3, 2, 3])
        document = Path(self.temp.name) / 'copia.registro'
        target = Path(self.temp.name) / 'reabierto.db'
        documento.save_document(document, self.path)
        documento.open_document(document, target)
        self.assertEqual(puntos.summary(target, self.block)[0]['nota'], 14)
        with patch('app_storage.data_dir', return_value=Path(self.temp.name)):
            period = app_storage.create_period(self.path, 2027, 1)
        self.assertEqual(puntos.list_blocks(period, self.course, '3°', 'A'), [])
        self.assertEqual(puntos.summary(self.path, self.block)[0]['nota'], 14)
