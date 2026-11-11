"""Teacher tasks across the visual organizer, focused grading and reusable models."""
import os,unittest
from unittest.mock import patch
import db,periodos,biblioteca
from tests import test_gui as fixtures


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requiere pantalla o Xvfb')
class TeacherViewTests(unittest.TestCase):
    setUp=fixtures.DesktopTests.setUp

    def test_expanded_view_keeps_pending_grades_and_escape_restores_controls(self):
        before=self.app._filas_planilla();identity=self.app.winfo_id();self.app.marcar_planilla_pendiente()
        self.app.set_evaluation_expanded(True);self.app.update()
        self.assertFalse(self.app.barra_top.winfo_ismapped());self.assertTrue(self.app._evaluation_expanded)
        self.app.salir_evaluacion_ampliada();self.app.update()
        self.assertTrue(self.app.barra_top.winfo_ismapped());self.assertEqual(self.app.winfo_id(),identity)
        self.assertEqual(self.app._filas_planilla(),before);self.assertTrue(self.app._planilla_pendiente)
        self.assertFalse(self.errors)

    def test_grade_display_changes_paint_without_changing_raw_values_or_drafts(self):
        db.guardar_notas_globales_sesion(self.session,{self.student:12.3456789})
        self.app.dibujar_planilla_calificacion(forzar=True);self.app.update()
        before=self.app._filas_planilla();self.app.marcar_planilla_pendiente()
        self.app.cambiar_presentacion_notas('Letras');self.app.update()
        tree=self.app.planilla_nativa;col=tree.grade_columns[0]
        self.assertEqual(tree.cell_appearance('12.3456789',col,(10.5,13.5,17.5))[-1],'B')
        self.app.cambiar_presentacion_notas('Números / 20');self.app.update()
        self.assertEqual(tree.cell_appearance('12.3456789',col,(10.5,13.5,17.5))[-1],'12.3456789')
        self.assertEqual(self.app._filas_planilla(),before);self.assertTrue(self.app._planilla_pendiente)
        self.assertFalse(self.errors)

    def test_library_saves_current_model_and_applies_an_independent_copy(self):
        db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Explica su procedimiento',20)])
        with patch('tkinter.simpledialog.askstring',return_value='Rúbrica reutilizable'):self.app.guardar_modelo_biblioteca()
        self.app.abrir_biblioteca();self.app.update();panel=self.app.biblioteca_panel
        self.assertEqual(len(panel.rows),1);self.assertIn('Explica su procedimiento',panel.detail.get('1.0','end'))
        identity=panel.selected;model=biblioteca.get_model(identity)
        db.guardar_notas_globales_sesion(self.session,{self.student:16})
        self.app.edicion_desbloqueada=True
        dialog=panel.use();self.app.update();self.assertTrue(dialog.plan['new_activity'])
        dialog.apply();self.app.update()
        self.assertNotEqual(self.app.id_actividad_calificando,self.session)
        self.assertEqual(biblioteca.get_model(identity),model)
        with db.obtener_conexion() as conn:self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',(self.session,)).fetchone()[0],16)
        self.assertFalse(self.errors)

    def test_student_profile_shows_unit_progress_and_keeps_saved_note(self):
        unit=periodos.save_unit(db.DB_PATH,None,None,None,'Unidad 1')
        with db.obtener_conexion() as conn:periodos.assign_unit(conn,self.session,unit)
        db.guardar_notas_globales_sesion(self.session,{self.student:15.5})
        profile=self.app.abrir_ficha_estudiante(self.student);self.app.update()
        self.assertEqual(profile.data['matriz']['promedio_general'],15.5)
        self.assertEqual(len(profile.units.get_children()),1)
        profile.display.set('Letras');profile.refresh();self.app.update()
        self.assertEqual(profile.values[0].cget('text'),'A');profile.destroy()
        self.assertFalse(self.errors)

    def test_hierarchy_selects_units_and_inline_rename_keeps_activity_links(self):
        periodos.identify(db.DB_PATH,2035,2,'Trimestres')
        unit=periodos.save_unit(db.DB_PATH,None,None,None,'Nombre inicial')
        with db.obtener_conexion() as conn:periodos.assign_unit(conn,self.session,unit)
        self.app.edicion_desbloqueada=True;self.app.seleccionar_periodo();self.app.update()
        manager=self.app._organization_manager
        key=next(k for k,r in manager._nav_rows.items() if r['kind']=='unit' and r['unit']['id']==unit)
        manager.navigation.selection_set(key);manager.navigation.event_generate('<<TreeviewSelect>>');self.app.update()
        self.assertEqual(manager.unit_tree.selection(),(str(unit),))
        manager.rename_inline();self.app.update();editor=manager._name_editor
        editor.delete(0,'end');editor.insert(0,'Unidad revisada');manager._name_save();self.app.update()
        self.assertEqual(periodos.units(db.DB_PATH)[0]['nombre'],'Unidad revisada')
        with db.obtener_conexion() as conn:self.assertEqual(conn.execute('SELECT unidad_id FROM Sesiones_Clase WHERE id=?',(self.session,)).fetchone()[0],unit)
        manager.open_period();self.app.update()
        self.assertEqual(self.app.alcance_unidad(),unit);self.assertFalse(self.errors)
