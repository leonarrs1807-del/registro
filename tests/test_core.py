import base64
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import openpyxl
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

import app_storage as storage
from app_security import hash_password, verify_password, verify_license
import db
from db_safety import history, undo_grade


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'test.db'
        db.inicializar_db(self.path)
        self.course = db.obtener_cursos(db_path=self.path)[0][0]
        self.comp = db.obtener_competencias_por_curso(self.course, self.path)[0][0]
        self.cap = db.obtener_capacidades_por_competencia(self.comp, self.path)[0][0]
        self.student = db.agregar_estudiante('Ana', 'Prueba', db_path=self.path)
        self.session = self.make_session()

    def make_session(self, **kwargs):
        args = dict(sesion_id=None, curso_id=self.course, competencia_id=self.comp, grado='3°', seccion='A',
                    titulo_tema='Prueba', proposito='', peso_clase=1, capacidades_y_criterios=[(self.cap, 'Criterio')],
                    db_path=self.path)
        args.update(kwargs)
        return db.crear_o_actualizar_sesion_clase(**args)

    def read(self, sql, args=()):
        with closing(sqlite3.connect(self.path)) as conn:
            return conn.execute(sql, args).fetchall()

    def save(self, grade, weight=None):
        db.guardar_calificaciones_y_asistencia_sesion(self.session, [dict(estudiante_id=self.student,
            notas_por_capacidad={self.cap: grade})], self.path, nuevo_peso=weight)

    def test_repeatable_initialization_and_legacy_password_migration(self):
        db.inicializar_db(self.path)
        self.assertTrue(db.verificar_credenciales_docente('docente', '1234', self.path))
        self.assertNotEqual(self.read('SELECT clave FROM Docente_Config')[0][0], '1234')
        self.assertNotIn('clave', db.obtener_docente_config(self.path))
        self.assertEqual(len(db.obtener_estudiantes_filtrados(db_path=self.path)), 1)

    def test_password_change_and_blank_preserves_hash(self):
        db.guardar_docente_config('Docente', 'IE', 'Secundaria', 'docente', 'ClaveNueva123', self.path)
        encoded = self.read('SELECT clave FROM Docente_Config')[0][0]
        db.guardar_docente_config('Otro nombre', 'IE', 'Secundaria', 'docente', '', self.path)
        self.assertEqual(encoded, self.read('SELECT clave FROM Docente_Config')[0][0])
        self.assertTrue(db.verificar_credenciales_docente('DOCENTE', 'ClaveNueva123', self.path))
        self.assertFalse(db.verificar_credenciales_docente('docente', '1234', self.path))

    def test_weak_password_rejected(self):
        with self.assertRaises(ValueError):
            db.guardar_docente_config('D', 'IE', 'S', 'docente', '123', self.path)
        with self.assertRaises(ValueError):
            db.guardar_docente_config('D', 'IE', 'S', 'docente', '', self.path)

    def test_invalid_grades_and_weight_rollback(self):
        self.save(15, 2)
        for bad in (-1, 99, float('inf'), float('nan'), 'texto'):
            with self.subTest(value=str(bad)), self.assertRaises(ValueError):
                self.save(bad, 4)
        self.assertEqual(self.read('SELECT peso_clase FROM Sesiones_Clase')[0][0], 2)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad')[0][0], 15)
        self.assertEqual(len(history(self.path)), 1)

    def test_sql_grade_constraints(self):
        with closing(sqlite3.connect(self.path)) as conn:
            for value in (-1, 21, 'texto', float('inf')):
                with self.subTest(value=value), self.assertRaises(sqlite3.IntegrityError):
                    conn.execute('INSERT INTO Notas_Manuales_Capacidad(estudiante_id, capacidad_id, nota_manual) VALUES(?,?,?)', (self.student, self.cap, value))

    def test_manual_note_range_and_null(self):
        with self.assertRaises(ValueError):
            db.guardar_nota_manual_capacidad(self.student, self.cap, 99, self.path)
        db.guardar_nota_manual_capacidad(self.student, self.cap, 0, self.path)
        db.guardar_nota_manual_capacidad(self.student, self.cap, None, self.path)
        self.assertIsNone(self.read('SELECT nota_manual FROM Notas_Manuales_Capacidad')[0][0])

    def test_batch_weights_are_atomic(self):
        second = self.make_session()
        with self.assertRaises(ValueError):
            db.actualizar_pesos_actividades([(self.session, 5), (second, -1)], self.path)
        self.assertEqual(self.read('SELECT peso_clase FROM Sesiones_Clase'), [(1.0,), (1.0,)])

    def test_percentages_require_100_and_finite(self):
        for values in [(25, 25, 25, -1), (0, 0, 0, 0), (50, 50, 50, 50), (float('nan'), 25, 25, 25)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                db.guardar_pesos_rubros_curso(self.course, *values, db_path=self.path)
        db.guardar_pesos_rubros_curso(self.course, 40, 25, 20, 15, self.path)

    def test_session_updates_date_and_classroom(self):
        self.make_session(sesion_id=self.session, grado='4°', seccion='B', fecha_str='2026-02-02')
        self.assertEqual(self.read('SELECT grado,seccion,fecha FROM Sesiones_Clase')[0], ('4°', 'B', '2026-02-02'))

    def test_cannot_move_graded_session(self):
        self.save(15)
        with self.assertRaises(ValueError):
            self.make_session(sesion_id=self.session, grado='4°')
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad'), [(15.0,)])

    def test_invalid_dates_and_foreign_capabilities(self):
        with self.assertRaises(ValueError):
            self.make_session(fecha_str='2026-02-31')
        comp2 = db.obtener_competencias_por_curso(self.course, self.path)[1][0]
        cap2 = db.obtener_capacidades_por_competencia(comp2, self.path)[0][0]
        with self.assertRaises(ValueError):
            self.make_session(capacidades_y_criterios=[(cap2, 'Ajeno')])

    def test_student_class_membership(self):
        wrong = db.agregar_estudiante('Otro', 'Salón', '4°', 'B', db_path=self.path)
        with self.assertRaises(ValueError):
            db.guardar_calificaciones_y_asistencia_sesion(self.session, [dict(estudiante_id=wrong, notas_por_capacidad={self.cap: 10})], self.path)

    def test_audit_and_undo_with_conflict_detection(self):
        self.save(10)
        first = history(self.path)[0]['id']
        self.save(15)
        second = history(self.path)[0]['id']
        with self.assertRaises(ValueError):
            undo_grade(self.path, first)
        undo_grade(self.path, second)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad')[0][0], 10)
        with self.assertRaises(ValueError):
            undo_grade(self.path, second)
        self.assertTrue(history(self.path)[0]['fecha'].endswith('Z'))

    def test_backup_and_restore_with_safety_copy(self):
        self.save(10)
        backup = storage.backup_database(self.path)
        self.save(20)
        saved = storage.restore_database(backup, self.path)
        self.assertTrue(saved.exists())
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad')[0][0], 10)
        with self.assertRaises(sqlite3.OperationalError):
            storage.restore_database(Path(self.temp.name) / 'missing.db', self.path)
        with self.assertRaises(ValueError):
            storage.restore_database(self.path, self.path)

    def test_new_period_has_roster_but_no_grades(self):
        self.save(15)
        target = storage.create_period(self.path, 2027, 2)
        self.addCleanup(target.unlink, missing_ok=True)
        with closing(sqlite3.connect(target)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM Estudiantes').fetchone()[0], 1)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM Sesiones_Clase').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM Historial_Notas').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT anio,periodo FROM Periodo_Info').fetchone(), (2027, 2))
        with self.assertRaises(ValueError):
            storage.create_period(self.path, 2027, 2)
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad')[0][0], 15)

    def test_excel_students_reject_incomplete_or_duplicate_rows_atomically(self):
        path = Path(self.temp.name) / 'est.xlsx'
        wb = openpyxl.Workbook(); ws = wb.active
        ws.append(['Apellidos', 'Nombres', 'Grado', 'Seccion'])
        ws.append(['Válido', 'Nuevo', '3°', 'A']); ws.append(['Inválido', None, '3°', 'A']); wb.save(path)
        with self.assertRaises(ValueError):
            db.importar_estudiantes_desde_excel(str(path), db_path=self.path)
        self.assertEqual(self.read('SELECT COUNT(*) FROM Estudiantes')[0][0], 1)
        ws.delete_rows(3); wb.save(path)
        self.assertEqual(db.importar_estudiantes_desde_excel(str(path), db_path=self.path), 1)
        with self.assertRaises(ValueError):
            db.importar_estudiantes_desde_excel(str(path), db_path=self.path)

    def test_matrix_import_invalid_late_grade_rolls_back_all_rows(self):
        path = Path(self.temp.name) / 'matriz.xlsx'
        wb = openpyxl.Workbook(); ws = wb.active
        ws.append(['Registro']); ws.append(['Curso'])
        ws.append(['Código', 'Apellidos', 'Nombres', 'Grado', 'Seccion', 'Estado', f'[CAP_ID:{self.cap}]'])
        ws.append(['', 'Nuevo', 'Uno', '3°', 'A', 'ACTIVO', 15])
        ws.append(['', 'Nuevo', 'Dos', '3°', 'A', 'ACTIVO', 99]); wb.save(path)
        with self.assertRaisesRegex(ValueError, 'Fila 5'):
            db.importar_matriz_notas_desde_excel(str(path), db_path=self.path)
        self.assertEqual(self.read('SELECT COUNT(*) FROM Estudiantes')[0][0], 1)
        self.assertFalse(history(self.path))

    def test_template_export_and_reimport(self):
        path = Path(self.temp.name) / 'est.xlsx'
        db.generar_plantilla_excel_estudiantes(str(path))
        self.assertEqual(db.importar_estudiantes_desde_excel(str(path), db_path=self.path), 3)

    def test_instrument_import_rolls_back_criteria_when_a_grade_is_invalid(self):
        path = Path(self.temp.name) / 'rubrica.xlsx'
        code = db.obtener_estudiantes_filtrados(db_path=self.path)[0]['Codigo_Unico']
        wb = openpyxl.Workbook(); ws = wb.active
        ws.append(['RÚBRICA']); ws.append(['Competencia'])
        ws.append(['CAP_ID', 'Capacidad', 'Criterio', 'C', 'B', 'A', 'AD'])
        ws.append([self.cap, 'Capacidad', 'Criterio nuevo', 'C', 'B', 'A', 'AD'])
        notes = wb.create_sheet('Notas')
        notes.append(['Código', 'Alumno', f'[CAP_ID:{self.cap}]', 'Comentario'])
        notes.append([code, 'Ana Prueba', 99, '']); wb.save(path)
        with self.assertRaises(ValueError):
            db.importar_rubrica_o_cotejo_desde_excel(self.session, str(path), '3°', 'A', self.path)
        self.assertEqual(self.read('SELECT criterio_precisado FROM Sesion_Capacidades')[0][0], 'Criterio')
        self.assertEqual(db.obtener_indicadores_instrumento_sesion(self.session, self.path), [])
        notes.cell(2, 3, 15); wb.save(path)
        self.assertEqual(db.importar_rubrica_o_cotejo_desde_excel(self.session, str(path), '3°', 'A', self.path), (1, 1))
        self.assertEqual(self.read('SELECT nota FROM Notas_Sesion_Capacidad')[0][0], 15)

    def test_letter_boundaries(self):
        self.assertEqual([db.nota_a_literal(n) for n in [None, 0, 10.49, 10.5, 13.2, 13.5, 17.49, 17.5, 20]],
                         ['-', 'C', 'C', 'B', 'B', 'A', 'A', 'AD', 'AD'])

    def test_font_preference_persists(self):
        db.guardar_tamano_letra_preferido('Grande (15)', self.path)
        self.assertEqual(db.obtener_docente_config(self.path)['tamano_letra'], 'Grande (15)')


class SecurityTests(unittest.TestCase):
    def test_commercial_build_policy_is_embedded_and_ignores_customer_environment(self):
        import os,sys
        from unittest.mock import patch
        from app_security import commercial_edition
        with patch.object(sys,'frozen',True,create=True),patch.object(sys,'_registro_edition','comercial',create=True):
            with patch.dict(os.environ,{'REGISTRO_EDITION':'personal'}):self.assertTrue(commercial_edition())
        with patch.object(sys,'frozen',True,create=True),patch.object(sys,'_registro_edition','personal',create=True):
            with patch.dict(os.environ,{'REGISTRO_EDITION':'comercial'}):self.assertFalse(commercial_edition())

    def test_frozen_edition_is_not_determined_by_a_loose_key_file(self):
        import sys
        from unittest.mock import patch
        from app_security import license_public_key
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_registro_license_public_key', b'public-build-key', create=True):
            self.assertEqual(license_public_key(), b'public-build-key')

    def test_password_hash_uses_random_salt_and_rejects_wrong_password(self):
        first = hash_password('Prueba123')
        self.assertNotEqual(first, hash_password('Prueba123'))
        self.assertTrue(verify_password('Prueba123', first))
        self.assertFalse(verify_password('Otra', first))
        self.assertFalse(verify_password('Prueba123', '1234'))

    def test_signed_license_tampering_expiry_and_legacy_boolean(self):
        key = Ed25519PrivateKey.generate()
        pub = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        def sign(payload):
            raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
            return dict(payload=payload, signature=base64.b64encode(key.sign(raw)).decode())
        payload = dict(product='registro', licensee='Prueba', expires='2099-12-31')
        document = sign(payload.copy())
        self.assertEqual(verify_license(document, pub)['licensee'], 'Prueba')
        document['payload']['licensee'] = 'Otro'
        with self.assertRaises(Exception):
            verify_license(document, pub)
        with self.assertRaises(ValueError):
            verify_license(sign(dict(product='registro', licensee='Prueba', expires='2000-01-01')), pub)
        with self.assertRaises(KeyError):
            verify_license({'activado': True}, pub)
