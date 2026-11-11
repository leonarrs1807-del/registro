"""Instrument portability, old schemas and isolation from saved evaluations."""
from contextlib import closing
import json,sqlite3
from pathlib import Path
import unittest

import biblioteca,db
from evaluacion_datos import get_indicators,get_answers
from tests import test_instrumentos as fixtures


class LibraryTests(unittest.TestCase):
    setUp=fixtures.InstrumentWorkbookTests.setUp
    new_session=fixtures.InstrumentWorkbookTests.new_session

    def model(self):
        db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Justifica',20)],self.path)
        self.library=Path(self.temp.name)/'biblioteca'/'instrumentos.db'
        return biblioteca.from_session(self.session,self.path)

    def test_global_model_contains_no_students_answers_or_ledger_identities(self):
        model=self.model();model['estudiantes']=[dict(nombre='Dato privado')]
        model['criterios'][0]['id']=99;model['criterios'][0]['capacidad_id']=self.cap
        before=self.path.read_bytes();identity=biblioteca.save_models([model],self.library)[0]
        saved=biblioteca.get_model(identity,self.library)
        self.assertNotIn('estudiantes',saved);self.assertNotIn('capacidad_id',saved['criterios'][0])
        self.assertNotIn('id',saved['criterios'][0]);self.assertNotIn('Dato privado',json.dumps(saved))
        self.assertEqual(self.path.read_bytes(),before)

    def test_identical_imports_are_deduplicated_and_edits_create_reusable_versions(self):
        model=self.model();first=biblioteca.save_models([model],self.library)[0]
        self.assertEqual(biblioteca.save_models([model],self.library),[first])
        model['criterios'][0]['criterio']='Comprueba la respuesta'
        second=biblioteca.save_models([model],self.library)[0]
        self.assertNotEqual(first,second);self.assertEqual(len(biblioteca.list_models(self.library)),1)
        self.assertEqual(len(biblioteca.list_models(self.library,history=True)),2)
        self.assertEqual(biblioteca.get_model(first,self.library)['criterios'][0]['criterio'],'Justifica')

    def test_legacy_database_and_internal_library_are_read_without_migration(self):
        model=self.model();items=get_indicators(self.session,self.path)
        with closing(sqlite3.connect(self.path)) as conn,conn:
            conn.execute('CREATE TABLE Biblioteca_Instrumentos(nombre TEXT PRIMARY KEY,datos TEXT)')
            conn.execute('INSERT INTO Biblioteca_Instrumentos VALUES(?,?)',('Rúbrica anterior',json.dumps(items)))
            conn.execute('DROP INDEX idx_instrumento_sesion')
            conn.execute('ALTER TABLE Instrumento_Indicadores DROP COLUMN activo')
            conn.execute('ALTER TABLE Instrumento_Indicadores DROP COLUMN orden')
            conn.execute('ALTER TABLE Instrumento_Indicadores DROP COLUMN puntos_niveles')
        before=self.path.read_bytes();models,warnings=biblioteca.read_source(self.path)
        self.assertFalse(warnings);self.assertEqual(len(models),2)
        self.assertEqual(self.path.read_bytes(),before)
        self.assertTrue(any(m['nombre']=='Rúbrica anterior' for m in models))

    def test_applying_to_a_graded_activity_creates_a_copy_and_preserves_notes(self):
        model=self.model();old=get_indicators(self.session,self.path)[0]['id']
        db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,
            notas_por_capacidad={self.cap:12.5},respuestas_instrumento={old:12.5})],self.path)
        self.assertTrue(biblioteca.preview_model(model,self.session,self.path)['new_activity'])
        target=biblioteca.apply_model(model,self.session,self.path)
        self.assertNotEqual(target,self.session);self.assertEqual(get_answers(target,self.path),{})
        self.assertEqual(get_answers(self.session,self.path)[self.student,old],'12.5')
        with closing(sqlite3.connect(self.path)) as conn:
            self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',(self.session,)).fetchone()[0],12.5)

    def test_apply_to_an_empty_activity_adds_missing_capacity_by_name(self):
        model=self.model();model['criterios'][0]['capacidad_nombre']='Capacidad nueva del modelo'
        target=biblioteca.apply_model(model,self.session,self.path)
        self.assertEqual(target,self.session)
        items=get_indicators(target,self.path);self.assertEqual(items[0]['capacidad_nombre'],'Capacidad nueva del modelo')
        self.assertEqual(get_answers(target,self.path),{})

    def test_wrong_course_and_closed_period_do_not_change_the_ledger(self):
        model=self.model();model['curso']='Otro curso'
        with self.assertRaises(ValueError):biblioteca.apply_model(model,self.session,self.path)
        model['curso']=self.course_name
        with closing(sqlite3.connect(self.path)) as conn,conn:
            conn.execute('CREATE TABLE IF NOT EXISTS Estado_Periodo(id INTEGER PRIMARY KEY,cerrado INTEGER)')
            conn.execute('INSERT OR REPLACE INTO Estado_Periodo VALUES(1,1)')
        before=self.path.read_bytes()
        with self.assertRaises(ValueError):biblioteca.apply_model(model,self.session,self.path)
        self.assertEqual(self.path.read_bytes(),before)

    def test_library_backup_can_be_merged_without_overwriting_school_databases(self):
        model=self.model();biblioteca.save_models([model],self.library)
        target=Path(self.temp.name)/'copia.biblioteca.db';biblioteca.backup(target,self.library)
        restored,warnings=biblioteca.read_source(target);self.assertFalse(warnings)
        self.assertEqual(biblioteca.save_models(restored,self.library),biblioteca.save_models([model],self.library))
        with self.assertRaises(ValueError):biblioteca.backup(self.path,self.library)

    def test_invalid_second_model_never_partially_imports_first(self):
        model=self.model();bad={**model,'criterios':[]}
        with self.assertRaises(ValueError):biblioteca.save_models([model,bad],self.library)
        self.assertEqual(biblioteca.list_models(self.library),[])

    def test_old_models_without_explicit_points_keep_the_source_achievement_scale(self):
        from escala import save_thresholds
        from instrumentos import default_scores
        self.model();limits=(9.5,12.5,16.5);save_thresholds(self.path,limits)
        with closing(sqlite3.connect(self.path)) as conn,conn:conn.execute("UPDATE Instrumento_Indicadores SET puntos_niveles=''")
        before=self.path.read_bytes();models,warnings=biblioteca.read_source(self.path)
        self.assertFalse(warnings);self.assertEqual(models[0]['criterios'][0]['puntajes'],default_scores(20,limits))
        self.assertEqual(self.path.read_bytes(),before)

    def test_archiving_can_be_reversed_and_search_handles_accents(self):
        model=self.model();model['nombre']='Rúbrica de ecuaciones'
        identity=biblioteca.save_models([model],self.library)[0]
        self.assertEqual(len(biblioteca.list_models(self.library,search='rubrica ecuaciones')),1)
        biblioteca.archive(identity,self.library);self.assertEqual(biblioteca.list_models(self.library),[])
        biblioteca.archive(identity,self.library,False);self.assertEqual(len(biblioteca.list_models(self.library)),1)
