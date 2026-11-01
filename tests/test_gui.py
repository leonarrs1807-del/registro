import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

import db
import app_storage


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Requiere pantalla o Xvfb')
class DesktopTests(unittest.TestCase):
    def setUp(self):
        import main
        self.main = main
        Path(db.DB_PATH).unlink(missing_ok=True)
        db.inicializar_db()
        self.course, self.course_name, _ = db.obtener_cursos()[0]
        self.comp = db.obtener_competencias_por_curso(self.course)[0][0]
        self.cap = db.obtener_capacidades_por_competencia(self.comp)[0][0]
        self.student = db.agregar_estudiante('Ana', 'Prueba', '3°', 'A')
        self.session = db.crear_o_actualizar_sesion_clase(None, self.course, self.comp, '3°', 'A', 'Prueba', '', 1, [(self.cap, 'Criterio')])
        self.app = main.VentanaPrincipal()
        self.addCleanup(self.app.destroy)
        self.errors = []
        self.app.report_callback_exception = lambda *args: self.errors.append(args)
        self.app.combo_curso_global.set(self.course_name)
        self.app.combo_grado_global.set('3°')
        self.app._al_cambiar_curso_global(self.course_name)
        self.app.abrir_actividad_en_pestana_calificar(self.session)
        self.app.update()

    def test_startup_is_locked_and_event_loop_runs(self):
        self.assertFalse(self.app.edicion_desbloqueada)
        self.app.after(100, self.app.quit)
        self.app.mainloop()
        self.assertFalse(self.errors)

    def test_create_activity_uses_selected_competence_not_first_one(self):
        self.app.edicion_desbloqueada = True
        comp, name = db.obtener_competencias_por_curso(self.course)[1]
        label = f'2. {name}'
        self.app.crear_combo_comp.set(label)
        self.app._al_cambiar_comp_en_creacion(label)
        expected_caps = {item[0] for item in db.obtener_capacidades_por_competencia(comp)}
        self.assertTrue(all(w['capacidad_id'] in expected_caps for w in self.app.widgets_caps_creacion))
        self.app.widgets_caps_creacion[0]['checkbox'].select()
        self.app.crear_entry_titulo.insert(0, 'Actividad segunda competencia')
        with patch('tkinter.messagebox.askyesno', return_value=False):
            self.app._guardar_actividad_comun(False)
        sessions = db.obtener_sesiones_clase(self.course, '3°', 'A')
        created = next(s for s in sessions if s['titulo_tema'] == 'Actividad segunda competencia')
        self.assertEqual(created['competencia_id'], comp)

    def test_mass_rubric_writes_native_grid_then_saves(self):
        self.app.edicion_desbloqueada = True
        db.guardar_indicadores_instrumento_sesion(self.session, 'Rúbrica', [(self.cap, 'Primero', 20), (self.cap, 'Segundo', 20)])
        act = db.obtener_sesiones_clase(self.course, '3°', 'A')[0]
        students = db.obtener_estudiantes_filtrados('3°', 'A')
        dialog = self.main.DialogoEvaluarInstrumentoMasivo(self.app, act, students, 'Rúbrica')
        for control in dialog.controles[self.student]:
            control['ent'].insert(0, '15')
        dialog._aplicar_calculo()
        tree = self.app.planilla_nativa
        row = tree.item(tree.get_children()[0], 'values')
        self.assertEqual(float(row[4]), 15)
        self.assertTrue(self.app._planilla_pendiente)
        with patch('tkinter.messagebox.showinfo'):
            self.app.accion_guardar_planilla_calificacion_completa()
        with db.obtener_conexion() as conn:
            self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0], 15)
        self.assertFalse(self.app._planilla_pendiente)

    def test_mass_editor_opens_without_missing_method(self):
        self.app.edicion_desbloqueada = True
        act = db.obtener_sesiones_clase(self.course, '3°', 'A')[0]
        dialog = self.main.DialogoEvaluarInstrumentoMasivo(self.app, act, db.obtener_estudiantes_filtrados('3°', 'A'), 'Rúbrica')
        dialog.abrir_editor()
        self.app.update()
        self.assertTrue(any(isinstance(w, self.main.DialogoEditarInstrumento) for w in dialog.winfo_children()))
        self.assertFalse(self.errors)

    def test_blank_rubric_keeps_grid_unchanged(self):
        self.app.edicion_desbloqueada = True
        act = db.obtener_sesiones_clase(self.course, '3°', 'A')[0]
        dialog = self.main.DialogoEvaluarInstrumentoMasivo(self.app, act, db.obtener_estudiantes_filtrados('3°', 'A'), 'Rúbrica')
        before = self.app.planilla_nativa.item(self.app.planilla_nativa.get_children()[0], 'values')
        with patch('tkinter.messagebox.showwarning') as warning:
            dialog._aplicar_calculo()
        self.assertTrue(warning.called)
        self.assertEqual(before, self.app.planilla_nativa.item(self.app.planilla_nativa.get_children()[0], 'values'))
        self.assertTrue(dialog.winfo_exists())

    def test_cancel_activity_switch_retains_session_and_grid(self):
        second = db.crear_o_actualizar_sesion_clase(None, self.course, self.comp, '3°', 'A', 'Segunda', '', 1, [(self.cap, 'Criterio')])
        self.app.recargar_tabla_actividades_creadas()
        self.app.abrir_actividad_en_pestana_calificar(self.session)
        self.app.marcar_planilla_pendiente()
        label = next(label for label, sid in self.app.combo_calif_etiqueta_a_id.items() if sid == second)
        with patch('tkinter.messagebox.askyesno', return_value=False):
            self.app._al_cambiar_actividad_en_calificar(label)
        self.assertEqual(self.app.id_actividad_calificando, self.session)
        self.assertTrue(self.app._planilla_pendiente)

    def test_font_setting_survives_restart(self):
        self.app.cambiar_tamano_letra('Grande (15)')
        self.assertEqual(db.obtener_docente_config()['tamano_letra'], 'Grande (15)')
        # A second window reads the preference from storage.
        other = self.main.VentanaPrincipal()
        try:
            self.assertEqual(other.tamano_letra_actual, 'Grande (15)')
        finally:
            other.destroy()

    def test_import_cancel_does_not_write(self):
        file = app_storage.data_dir() / 'preview.xlsx'
        db.generar_plantilla_excel_estudiantes(str(file))
        def cancel_window():
            for widget in self.app.winfo_children():
                if widget.winfo_class() == 'Toplevel':
                    widget.destroy()
        self.app.after(200, cancel_window)
        result = self.app._importar_con_vista_previa(db.importar_estudiantes_desde_excel, str(file), '3°', 'A')
        self.assertIsNone(result)
        self.assertEqual(len(db.obtener_estudiantes_filtrados()), 1)

    def test_graph_and_pdf_render(self):
        self.app.edicion_desbloqueada = True
        db.guardar_calificaciones_y_asistencia_sesion(self.session, [dict(estudiante_id=self.student, notas_por_capacidad={self.cap: 13.2})])
        self.app.stats_combo_tipo.set('Dashboard Completo (Todos)')
        self.app.accion_generar_grafico_estadisticas()
        out = app_storage.data_dir() / 'test.pdf'
        self.app.fig_actual.savefig(out)
        self.assertGreater(out.stat().st_size, 1000)
        self.assertFalse(self.errors)

    def test_confirmed_import_writes_and_creates_backup(self):
        from tkinter import ttk
        file = app_storage.data_dir() / 'confirm.xlsx'
        db.generar_plantilla_excel_estudiantes(str(file))
        def confirm_window():
            for widget in self.app.winfo_children():
                if widget.winfo_class() == 'Toplevel':
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Button) and child.cget('text').startswith('Importar todos'):
                            child.invoke()
                            return
        self.app.after(200, confirm_window)
        result = self.app._importar_con_vista_previa(db.importar_estudiantes_desde_excel, str(file), '3°', 'A')
        self.assertEqual(result, 3)
        self.assertEqual(len(db.obtener_estudiantes_filtrados()), 4)
        self.assertTrue(list((self.app._db_path.parent / 'backups').glob('*antes-importar.db')))

    def test_native_grid_keeps_identity_columns_fixed(self):
        self.assertEqual(tuple(self.app.planilla_nativa['displaycolumns'])[:1],('Asistencia',))
        self.assertEqual(len(self.app.identidad_planilla.get_children()),1)
        self.assertGreaterEqual(self.app.planilla_nativa.column('Cap 1','width'),180)

    def test_undo_and_redo_do_not_write_until_confirmed(self):
        self.app.edicion_desbloqueada=True
        tree=self.app.planilla_nativa;item=tree.get_children()[0]
        tree._update_value(item,4,'18')
        self.app.deshacer_planilla();self.assertEqual(tree.item(item,'values')[4],'')
        self.app.deshacer_planilla(True);self.assertEqual(tree.item(item,'values')[4],'18')
        with db.obtener_conexion() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM Notas_Sesion_Capacidad').fetchone()[0],0)

    def test_primary_selector_includes_sixth_grade(self):
        self.app.cambiar_nivel('Primaria')
        self.assertIn('6°',self.app.combo_grado_global.cget('values'))
        self.assertTrue(all('Primaria' in name for name in self.app.cursos_map))
        self.app.cambiar_nivel('Secundaria');self.assertIn(self.course_name,self.app.cursos_map)

    def test_draft_survives_restart_and_is_removed_after_save(self):
        self.app.edicion_desbloqueada=True
        tree=self.app.planilla_nativa;item=tree.get_children()[0];tree._update_value(item,4,'17')
        self.app.autoguardar_borrador();file=self.app._borrador_path();self.assertTrue(file.exists())
        with patch('tkinter.messagebox.showinfo'):self.app.accion_guardar_planilla_calificacion_completa()
        self.assertFalse(file.exists())

    def test_closed_period_blocks_writes(self):
        self.app.periodo_cerrado()
        with db.obtener_conexion() as conn:conn.execute('INSERT OR REPLACE INTO Estado_Periodo VALUES(1,1)')
        self.app.edicion_desbloqueada=True
        with patch('tkinter.messagebox.showinfo'):self.assertFalse(self.app.verificar_permiso_edicion())

    def test_names_divider_can_be_dragged_and_is_remembered(self):
        import json
        pane=self.app._split_panes['nombres_notas']
        old=pane.sash_coord(0)[0]
        pane.sash_place(0,old+65,0)
        self.app.update_idletasks()
        self.assertGreater(pane.sash_coord(0)[0],old+30)
        self.app._guardar_ventana()
        saved=json.loads((app_storage.data_dir()/'vista.json').read_text())
        self.assertGreater(saved['panes']['nombres_notas'],0)

    def test_compact_window_keeps_grade_actions_within_view(self):
        self.app.geometry('1024x740')
        self.app.after(300,self.app.quit);self.app.mainloop()
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        buttons=[w for w in descendants(self.app.tab_calificar) if isinstance(w,self.main.ctk.CTkButton)]
        save=next(w for w in buttons if w.cget('text')=='Guardar notas')
        self.assertTrue(save.winfo_ismapped())
        self.assertLessEqual(save.winfo_rootx()+save.winfo_width(),self.app.winfo_rootx()+self.app.winfo_width())
        self.assertFalse(self.errors)

    def test_default_window_fits_small_screen_with_two_hundred_percent_dpi(self):
        from vista import ViewTools
        from types import SimpleNamespace
        sizes=[]
        screen=SimpleNamespace(_get_window_scaling=lambda:2,winfo_screenwidth=lambda:1366,winfo_screenheight=lambda:768,
                               minsize=lambda *size:None,geometry=lambda value:sizes.append(value))
        ViewTools.ajustar_pantalla(screen,reset=True)
        width,height=map(int,sizes[0].split('+')[0].split('x'))
        self.assertLessEqual(width*2,1366)
        self.assertLessEqual(height*2,768)

    def test_signup_creates_local_account_and_selects_only_demo_course(self):
        from licencias import OfflineLicensing,course_key
        from licencias_ui import AccountDialog
        service=OfflineLicensing(app_storage.data_dir()/'cuenta-gui',device='a'*64,registry=False)
        self.app.licensing=service;self.app._license_required=True
        dialog=AccountDialog(self.app)
        for label,value in [('Nombre y apellidos','Docente de Prueba'),('Correo de compra','prueba@example.com'),('Usuario','docente-prueba'),('Contraseña','TemporalPrueba123'),('Repetir contraseña','TemporalPrueba123')]:
            dialog.entries[label].insert(0,value)
        label=next(label for label,key in dialog.course_map.items() if key==course_key(self.course_name,'Secundaria'))
        dialog.course_choice.set(label)
        with patch('tkinter.messagebox.askyesno',return_value=True):dialog.register()
        self.assertTrue(service.authenticate('docente-prueba','TemporalPrueba123'))
        self.assertTrue(self.app.licencia_permite(show=False))
        other=db.obtener_cursos()[1][0]
        self.assertFalse(self.app.licencia_permite(other,show=False))
        self.assertEqual(service.status()['days'],30)

    def test_points_ui_shows_normalized_total_without_publishing_early(self):
        import puntos
        block=puntos.create_block(self.app._db_path,self.course,self.comp,'3°','A','Ecuaciones',[self.cap])
        puntos.add_practice(self.app._db_path,block,'Primera',[('E1',10)])
        puntos.add_practice(self.app._db_path,block,'Segunda',[('E1',15)])
        self.app.tabview.set('Prácticas y puntos');self.app.puntos_panel.refresh(select=block)
        tree=self.app.puntos_panel.grid_view
        row=tree.get_children()[0]
        tree.set(row,tree['columns'][3],'10');tree.set(row,tree['columns'][4],'10')
        self.app.puntos_panel._changed()
        self.assertEqual(tree.item(row,'values')[-2],'16.00')
        with db.obtener_conexion() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM Sesiones_Clase').fetchone()[0],1)
