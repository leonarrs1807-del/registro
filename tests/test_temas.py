"""Renaming a reused rubric affects only the target activity and commits atomically."""
import unittest
from pathlib import Path
from unittest.mock import patch
import db,biblioteca
from evaluacion_datos import activity,get_indicators,get_answers
from db_safety import connection
from temas import import_with_topic
from tests import test_instrumentos as fixtures


class TopicTests(unittest.TestCase):
    setUp=fixtures.InstrumentWorkbookTests.setUp
    new_session=fixtures.InstrumentWorkbookTests.new_session
    model=fixtures.InstrumentWorkbookTests.model

    def test_reusing_graded_model_renames_only_new_activity_and_preserves_library(self):
        db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Justifica',20)],self.path)
        model=biblioteca.from_session(self.session,self.path);library=Path(self.temp.name)/'biblioteca.db'
        identity=biblioteca.save_models([model],library)[0];original=biblioteca.get_model(identity,library)
        indicator=get_indicators(self.session,self.path)[0]['id']
        db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,
            notas_por_capacidad={self.cap:12.5},respuestas_instrumento={indicator:12.5})],self.path)
        target=biblioteca.apply_model(original,self.session,self.path,topic='  Proporcionalidad  ')
        self.assertNotEqual(target,self.session)
        self.assertEqual(activity(target,self.path)['titulo_tema'],'Proporcionalidad')
        self.assertEqual(activity(self.session,self.path)['titulo_tema'],'Resolver ecuaciones')
        self.assertEqual(get_answers(self.session,self.path)[self.student,indicator],'12.5')
        self.assertEqual(biblioteca.get_model(identity,library),original)

    def test_excel_import_commits_new_topic_together_with_instrument(self):
        wb=self.model(indicators=[(self.cap,'Justifica',20)]);wb.save(self.file)
        result=import_with_topic(db.importar_rubrica_o_cotejo_desde_excel,
            (self.session,str(self.file),'3°','A'),'Tema para esta clase',self.path)
        self.assertEqual(result,(1,0));self.assertEqual(activity(self.session,self.path)['titulo_tema'],'Tema para esta clase')
        self.assertEqual(get_indicators(self.session,self.path)[0]['criterio'],'Justifica')

    def test_failed_import_or_blank_topic_does_not_leave_a_rename_or_partial_data(self):
        before=activity(self.session,self.path)
        def failing(session,db_path):
            with connection(db_path) as conn:conn.execute('UPDATE Sesiones_Clase SET proposito=? WHERE id=?',('Cambio incompleto',session))
            raise ValueError('Importación rechazada')
        with self.assertRaises(ValueError):import_with_topic(failing,(self.session,),'Nombre nuevo',self.path)
        self.assertEqual(activity(self.session,self.path),before)
        with patch('temas.topic_name',side_effect=ValueError('Tema vacío')):
            with self.assertRaises(ValueError):import_with_topic(failing,(self.session,),'',self.path)
        self.assertEqual(activity(self.session,self.path),before)
