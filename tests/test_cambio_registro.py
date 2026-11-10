"""Changing documents must not restart the process or leak notes across schools."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import app_storage
import db
from db import agregar_estudiante,obtener_estudiantes_filtrados


class ActiveDatabaseTests(unittest.TestCase):
    def test_already_imported_helpers_follow_current_path_and_honor_explicit_path(self):
        original=db.DB_PATH
        with tempfile.TemporaryDirectory() as folder:
            first=Path(folder)/'primero.db';second=Path(folder)/'segundo.db'
            db.inicializar_db(first);db.inicializar_db(second)
            try:
                db.DB_PATH=first;agregar_estudiante('Ana','Colegio A','3°','A')
                db.DB_PATH=second;agregar_estudiante('Luis','Colegio B','3°','A')
                self.assertEqual([r['Nombres'] for r in obtener_estudiantes_filtrados('3°','A')],['Luis'])
                self.assertEqual([r['Nombres'] for r in obtener_estudiantes_filtrados('3°','A',db_path=first)],['Ana'])
                with closing(sqlite3.connect(first)) as conn:
                    self.assertEqual(conn.execute('SELECT Nombres FROM Estudiantes').fetchall(),[('Ana',)])
                db.DB_PATH=first
                self.assertEqual([r['Nombres'] for r in obtener_estudiantes_filtrados('3°','A')],['Ana'])
            finally:db.DB_PATH=original


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requiere pantalla o Xvfb')
class DocumentSwitchTests(unittest.TestCase):
    from tests.test_gui import DesktopTests as _Fixture
    setUp=_Fixture.setUp

    def target(self):
        from colegios import blank_copy
        return blank_copy(self.app._db_path,app_storage.data_dir(),'Colegio separado')

    def restore_path(self,original,env):
        db.DB_PATH=original
        if env is None:os.environ.pop('REGISTRO_DB_PATH',None)
        else:os.environ['REGISTRO_DB_PATH']=env

    def test_school_switch_keeps_root_and_isolates_same_numeric_student_ids(self):
        original=db.DB_PATH;self.addCleanup(self.restore_path,original,os.environ.get('REGISTRO_DB_PATH'))
        target=self.target();identity=self.app.winfo_id();pages=self.app.tabview
        with closing(sqlite3.connect(target)) as conn,conn:
            conn.execute("DELETE FROM sqlite_sequence WHERE name='Estudiantes'")
        db.guardar_notas_globales_sesion(self.session,{self.student:12.5})
        self.app._undo=[{'old':'document'}];self.app._instrument_pending={(self.student,99):17}
        self.app.est_entry_nombres.insert(0,'No trasladar')
        with patch('subprocess.Popen') as process,patch.object(self.app,'destroy',wraps=self.app.destroy) as close:
            self.assertTrue(self.app._reiniciar(target));self.app.update()
            self.assertEqual(self.app.winfo_id(),identity);self.assertIs(self.app.tabview,pages)
            process.assert_not_called();close.assert_not_called()
            self.assertEqual(db.DB_PATH,target.resolve());self.assertFalse(self.app.edicion_desbloqueada)
            self.assertEqual(obtener_estudiantes_filtrados('3°','A'),[])
            self.assertEqual(self.app.est_entry_nombres.get(),'');self.assertEqual(self.app._undo,[])
            self.assertEqual(self.app._instrument_pending,{})
            self.assertEqual(self.app._institution_entries['nombre'].get(),'Colegio separado')
            self.assertEqual(self.app.planilla_nativa,None)
            new_student=agregar_estudiante('Luis','Separado','3°','A')
            self.assertEqual(new_student,self.student)
            self.app.recargar_tabla_estudiantes()
            self.assertTrue(self.app._reiniciar(original));self.app.update()
            self.assertEqual([r['Nombres'] for r in obtener_estudiantes_filtrados('3°','A')],['Ana'])
            with db.obtener_conexion() as conn:self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],12.5)
            process.assert_not_called();close.assert_not_called()
        self.assertFalse(self.errors)

    def test_invalid_record_and_cancel_keep_current_document_and_window(self):
        original=db.DB_PATH;target=self.target();identity=self.app.winfo_id()
        self.app.marcar_planilla_pendiente()
        with patch('tkinter.messagebox.askyesno',return_value=False):
            self.assertFalse(self.app._reiniciar(target))
        self.assertEqual(db.DB_PATH,original);self.assertTrue(self.app._planilla_pendiente)
        self.app._planilla_pendiente=False
        with self.assertRaises((sqlite3.DatabaseError,ValueError)):
            with tempfile.TemporaryDirectory() as folder:
                bad=Path(folder)/'incorrecto.db';bad.write_bytes(b'not a database');self.app._reiniciar(bad)
        self.assertEqual(db.DB_PATH,original);self.assertEqual(self.app.winfo_id(),identity)
        self.assertFalse(self.errors)

    def test_reloading_restored_record_and_sorting_keep_the_window(self):
        original=db.DB_PATH;self.addCleanup(self.restore_path,original,os.environ.get('REGISTRO_DB_PATH'))
        identity=self.app.winfo_id()
        db.guardar_notas_globales_sesion(self.session,{self.student:18})
        with patch('subprocess.Popen') as process:
            self.assertTrue(self.app._reiniciar(original));self.app.update()
            self.assertEqual(float(self.app._filas_planilla()[0][4]),18)
            self.app.est_combo_orden.set('Apellidos (Z-A)');self.app.recargar_tabla_estudiantes()
            self.app.calif_combo_orden.set('Apellidos (Z-A)');self.app.dibujar_planilla_calificacion();self.app.update()
            self.assertEqual(self.app.winfo_id(),identity);process.assert_not_called()
        self.assertFalse(self.errors)

    def test_selecting_inactive_legacy_period_does_not_error_or_modify_file(self):
        import periodos
        from organizacion_ui import OrganizationManager
        from tests.test_registros_antiguos import legacy_period
        target=legacy_period(self.app._db_path,app_storage.data_dir()/'periodo-antiguo.db',self.course,self.session)
        before=target.read_bytes()
        dialog=OrganizationManager(self.app);self.app.update()
        key=next(k for k,r in dialog.records.items() if r['path'].resolve()==target.resolve())
        dialog.period_tree.selection_set(key);dialog.period_tree.event_generate('<<TreeviewSelect>>');self.app.update()
        self.assertEqual(len(dialog.unit_tree.get_children()),1)
        self.assertEqual(target.read_bytes(),before);self.assertFalse(self.errors)
        dialog.destroy()

    def test_help_search_and_topic_navigation_preserve_pending_grades(self):
        before=self.app._filas_planilla();self.app.marcar_planilla_pendiente()
        self.app.abrir_instrucciones('Bimestres y trimestres');self.app.update()
        guide=self.app.tutorial
        guide.query.set('rubricas');self.app.update()
        self.assertIn('Guardar y reutilizar rúbricas',guide.names)
        guide.open('Guardar y reutilizar rúbricas');guide.move(1)
        self.assertIn(guide.current,guide.names)
        guide.query.set('noexisteestaayuda');self.assertFalse(guide.names)
        guide.open('Unidades del periodo');self.app.update()
        self.assertEqual(guide.query.get(),'');self.assertEqual(guide.current,'Unidades del periodo')
        self.assertEqual(self.app._filas_planilla(),before);self.assertTrue(self.app._planilla_pendiente)
        self.assertFalse(self.errors)
