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

    def test_close_with_pending_instrument_layout_does_not_reenter_redraw(self):
        self.app.edicion_desbloqueada=True
        act=db.obtener_sesiones_clase(self.course,'3°','A')[0]
        dialog=self.main.DialogoEvaluarInstrumentoMasivo(self.app,act,db.obtener_estudiantes_filtrados('3°','A'),'Rúbrica')
        dialog.abrir_editor()
        # Leave Configure events pending, as when closing just after opening.
        self.app.destroy()
        self.assertFalse(self.errors)

    def test_closed_dialog_cancels_its_callbacks_and_keeps_parent_callbacks(self):
        from widgets import SafeDialog
        called=[];dialog=SafeDialog(self.app)
        own=dialog.after(100,lambda:called.append('diálogo cerrado'))
        self.app.after(100,lambda:called.append('principal'))
        dialog.destroy()
        self.assertNotIn(own,self.app.tk.splitlist(self.app.tk.call('after','info')))
        self.app.after(180,self.app.quit);self.app.mainloop()
        self.assertEqual(called,['principal']);self.assertFalse(self.errors)

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
        for indicator in dialog.indicadores_db:
            dialog.set_answer(self.student,indicator['id'],15)
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
        # A real restart uses a fresh Tcl interpreter/process, just like _reiniciar.
        import subprocess,sys
        code="import main; app=main.VentanaPrincipal(); print('FONT_PREF='+app.tamano_letra_actual,flush=True); app.destroy()"
        result=subprocess.run([sys.executable,'-X','faulthandler','-c',code],capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('FONT_PREF=Grande (15)',result.stdout)

    def test_import_cancel_does_not_write(self):
        file = app_storage.data_dir() / 'preview.xlsx'
        db.generar_plantilla_excel_estudiantes(str(file))
        from tests import populate_student_template
        populate_student_template(file)
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
        self.app.fig_actual.canvas.draw()
        renderer=self.app.fig_actual.canvas.get_renderer();width=self.app.fig_actual.bbox.width
        for axis in self.app.fig_actual.axes:
            for label in axis.get_yticklabels()+axis.get_xticklabels():
                if label.get_visible() and label.get_text():
                    bounds=label.get_window_extent(renderer)
                    self.assertGreaterEqual(bounds.x0,-1)
                    self.assertLessEqual(bounds.x1,width+1)
        out = app_storage.data_dir() / 'test.pdf'
        self.app.fig_actual.savefig(out)
        self.assertGreater(out.stat().st_size, 1000)
        self.assertFalse(self.errors)

    def test_confirmed_import_writes_and_creates_backup(self):
        from tkinter import ttk
        file = app_storage.data_dir() / 'confirm.xlsx'
        db.generar_plantilla_excel_estudiantes(str(file))
        from tests import populate_student_template
        populate_student_template(file)
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
        from cotejo import capacity_label
        self.assertEqual(self.app.planilla_nativa.heading('Cap 1','text'),capacity_label(db.obtener_capacidades_por_competencia(self.comp)[0][1]))
        self.assertTrue(self.app.planilla_nativa.full_headers['Cap 1'])

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

    def test_import_purchase_after_demo_unlocks_only_the_bought_course(self):
        from datetime import datetime,timedelta,timezone
        import json
        from licencias import OfflineLicensing,course_key
        from licencias_emisor import create_keys,sign_request
        from licencias_ui import AccountDialog
        folder=app_storage.data_dir()/'compra-gui';folder.mkdir()
        public=create_keys(folder/'privada.pem',folder/'publica.pem','ClaveVendedorTemporal123')
        now=datetime.now(timezone.utc)
        service=OfflineLicensing(folder,public,device='a'*64,clock=lambda:now,registry=False)
        first=course_key(self.course_name,'Secundaria')
        service.register('Docente de Prueba','prueba@example.com','comprador','ClaveCliente123',first)
        other,other_name,_=db.obtener_cursos()[1];second=course_key(other_name,'Secundaria')
        now+=timedelta(days=40)
        self.app.licensing=service;self.app._license_required=True
        self.assertFalse(self.app.licencia_permite(other,show=False))
        request=service.request(self.app.catalogo_licencias())
        document=sign_request(request,(folder/'privada.pem').read_bytes(),'ClaveVendedorTemporal123',[second],now=now)
        file=folder/'compra.licencia';file.write_text(json.dumps(document))
        with patch('tkinter.filedialog.askopenfilename',return_value=str(file)),patch('tkinter.messagebox.showinfo'):
            self.app.importar_licencia_configuracion()
        self.assertTrue(self.app.licencia_permite(other,show=False))
        self.assertFalse(self.app.licencia_permite(self.course,show=False))
        self.assertFalse(self.errors)

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
        self.assertEqual(self.app.puntos_panel.identity.set(row,'nota'),'16.00')
        self.assertEqual(self.app.puntos_panel.identity.heading('alumno','text'),'Estudiante')
        with db.obtener_conexion() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM Sesiones_Clase').fetchone()[0],1)

    def test_icon_menu_expands_without_losing_current_grade_data(self):
        self.app.tabview.set_expanded(False)
        self.app.update_idletasks()
        narrow=self.app.tabview.sidebar.container.winfo_width()
        rows=self.app._filas_planilla()
        self.app.tabview.toggle();self.app.update_idletasks()
        self.assertGreater(self.app.tabview.sidebar.container.winfo_width(),narrow)
        self.assertEqual(self.app.tabview.get(),'Ingresar Calificativos')
        self.assertEqual(rows,self.app._filas_planilla())
        self.app.tabview.toggle();self.assertFalse(self.app.tabview.expanded)

    def test_criteria_reference_is_in_details_and_does_not_take_table_space(self):
        db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Resolver con sustento',20)])
        self.app.calif_combo_modo_inst.set('Rúbrica');self.app.dibujar_planilla_calificacion(forzar=True)
        self.app.update_idletasks()
        self.assertFalse(self.app.caja_ref_rubrica.winfo_ismapped())
        popup=self.app.detalles_calificacion()
        self.assertEqual(popup.instrument_grid.indicators[0]['criterio'],'Resolver con sustento')
        self.assertEqual(set(popup.instrument_grid.indicators[0]['descriptores']),{'C','B','A','AD'})
        popup.destroy()
        self.app.alternar_herramientas();self.app.update_idletasks()
        self.assertTrue(self.app.btn_evaluar.winfo_ismapped())

    def test_changing_evaluation_mode_keeps_pending_edits_and_reuses_grid(self):
        self.app.edicion_desbloqueada=True
        tree=self.app.planilla_nativa;item=tree.get_children()[0];tree._update_value(item,4,'18.75')
        with patch.object(self.app,'confirmar_descartar',side_effect=AssertionError('No debe descartar')):
            with patch.object(self.main,'obtener_estado_planilla_sesion',side_effect=AssertionError('No debe reconstruir')):
                for mode in ['Rúbrica','Lista de Cotejo','Nota directa']:
                    self.app.calif_combo_modo_inst.set(mode);self.app.dibujar_planilla_calificacion()
                    self.assertIs(self.app.planilla_nativa,tree)
                    self.assertEqual(tree.item(item,'values')[4],'18.75')
                self.app.cambiar_tamano_letra('Personalizado (20)')
                self.assertIs(self.app.planilla_nativa,tree)
                self.assertEqual(tree.item(item,'values')[4],'18.75')
        self.assertTrue(self.app._planilla_pendiente)
        self.assertFalse(self.errors)

    def test_selected_grade_cells_keep_independent_colors_and_allow_editing(self):
        from grade_cells import PALETTE
        from types import SimpleNamespace
        self.app.edicion_desbloqueada=True
        tree=self.app.planilla_nativa;item=tree.get_children()[0]
        self.app.update_idletasks()
        for value,level in [('0','C'),('11','B'),('15','A'),('19','AD')]:
            tree.set(item,'Cap 1',value);tree.selection_set(item);tree.paint_grades()
            label=next(l for l in tree._cell_pool if l.winfo_manager()=='place')
            self.assertEqual(label.cget('background'),PALETTE[level][0])
            self.assertIn(f'({level})',label.cget('text'))
        x,y,w,h=tree.bbox(item,'Cap 1');tree.on_double_click(SimpleNamespace(x=x+w//2,y=y+h//2))
        self.assertIsNotNone(tree._entry)
        self.app.update();tree._entry.focus_force()
        tree.paint_grades();tree._entry.delete(0,'end');tree._entry.insert(0,'12.75')
        tree._entry.event_generate('<Return>');self.app.update()
        from grade_cells import grade_number
        self.assertEqual(grade_number(tree.set(item,'Cap 1')),12.75)
        self.assertFalse(self.errors)

    def test_activity_title_has_no_internal_id_prefix(self):
        self.assertEqual(self.app.calif_combo_actividad.get(),'Prueba')

    def test_student_description_wraps_when_opening_page(self):
        self.app.tabview.set('Estudiantes');self.app.after(350,self.app.quit);self.app.mainloop()
        def labels(widget):
            for child in widget.winfo_children():
                if isinstance(child,self.main.ctk.CTkLabel):yield child
                yield from labels(child)
        intro=next(w for w in labels(self.app.tab_estudiantes) if w.cget('text').startswith('El código'))
        self.assertGreater(int(intro.cget('wraplength')),0)
        self.assertLess(intro.winfo_width(),intro.master.winfo_width())
        self.assertFalse(self.errors)

    def test_mass_checklist_preserves_no_without_automatic_grade(self):
        self.app.edicion_desbloqueada=True
        act=db.obtener_sesiones_clase(self.course,'3°','A')[0]
        dialog=self.main.DialogoEvaluarInstrumentoMasivo(self.app,act,db.obtener_estudiantes_filtrados('3°','A'),'Lista de Cotejo')
        self.assertFalse(dialog.answers)
        for indicator in dialog.indicadores_db:dialog.set_answer(self.student,indicator['id'],'No')
        dialog._aplicar_calculo()
        tree=self.app.planilla_nativa;self.assertEqual(tree.item(tree.get_children()[0],'values')[4],'')
        with patch('tkinter.messagebox.showinfo'):self.app.accion_guardar_planilla_calificacion_completa()
        with db.obtener_conexion() as conn:
            self.assertFalse(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad WHERE nota IS NOT NULL').fetchall())

    def test_editing_instrument_keeps_entered_answers(self):
        self.app.edicion_desbloqueada=True
        act=db.obtener_sesiones_clase(self.course,'3°','A')[0]
        dialog=self.main.DialogoEvaluarInstrumentoMasivo(self.app,act,db.obtener_estudiantes_filtrados('3°','A'),'Rúbrica')
        dialog.set_answer(self.student,dialog.indicadores_db[0]['id'],'12.75')
        dialog.abrir_editor();self.app.update()
        editor=next(w for w in dialog.winfo_children() if isinstance(w,self.main.DialogoEditarInstrumento))
        editor.rows[0]['text'].insert('end',' Aclaración');editor.save()
        reopened=next(w for w in self.app.winfo_children() if isinstance(w,self.main.DialogoEvaluarInstrumentoMasivo))
        self.assertEqual(float(reopened.answers[(self.student,reopened.indicadores_db[0]['id'])]),12.75)
        self.assertFalse(self.errors)

    def test_personal_workspace_keeps_header_short_and_has_no_trial_banner(self):
        from interfaz import pixel_scale
        # Two compact rows now include the requested period and unit selectors.
        self.assertLess(self.app.barra_top.winfo_height()/pixel_scale(self.app),110)
        self.assertTrue(self.app.period_button.winfo_ismapped())
        self.assertFalse(self.app._license_required)
        self.assertFalse(hasattr(self.app,'_license_label'))

    def test_saved_level_answers_reopen_and_undo_with_their_grades(self):
        from evaluacion_datos import get_answers
        self.app.edicion_desbloqueada=True
        db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Explica',20)])
        act=db.obtener_sesiones_clase(self.course,'3°','A')[0]
        dialog=self.main.DialogoEvaluarInstrumentoMasivo(self.app,act,db.obtener_estudiantes_filtrados('3°','A'),'Rúbrica')
        identity=dialog.indicadores_db[0]['id'];dialog.set_answer(self.student,identity,'A');dialog._aplicar_calculo()
        tree=self.app.planilla_nativa;iid=tree.get_children()[0]
        self.assertEqual(float(tree.item(iid,'values')[4]),15.5)
        self.app.deshacer_planilla();self.assertFalse(self.app._instrument_pending)
        self.assertEqual(tree.item(iid,'values')[4],'')
        self.app.deshacer_planilla(redo=True)
        self.assertEqual(self.app._instrument_pending[(self.student,identity)],'A')
        self.app.autoguardar_borrador();self.app._instrument_pending={};self.app._planilla_pendiente=False
        self.app.recuperar_borrador()
        self.assertEqual(self.app._instrument_pending[(self.student,identity)],'A')
        with patch('tkinter.messagebox.showinfo'):self.app.accion_guardar_planilla_calificacion_completa()
        self.assertEqual(get_answers(self.session,self.app._db_path)[(self.student,identity)],'A')
        reopened=self.main.DialogoEvaluarInstrumentoMasivo(self.app,act,db.obtener_estudiantes_filtrados('3°','A'),'Rúbrica')
        self.assertEqual(reopened.answers[(self.student,identity)],'A');self.assertFalse(self.errors)

    def test_metadata_refresh_preserves_pending_notes_and_defers_hidden_views(self):
        self.app.edicion_desbloqueada=True
        tree=self.app.planilla_nativa;iid=tree.get_children()[0]
        values=list(tree.item(iid,'values'));values[4]='12.75';tree.item(iid,values=values);self.app.marcar_planilla_pendiente()
        with patch('db.calcular_matriz_competencias_y_capacidades',side_effect=AssertionError('La vista oculta no debe calcular')):
            self.app.recargar_tabla_actividades_creadas();self.app.recargar_matriz_completa()
        self.assertIs(self.app.planilla_nativa,tree);self.assertEqual(tree.item(iid,'values')[4],'12.75')
        self.assertIn('recargar_matriz_completa',self.app._view_pending)
        self.app.tabview.set('Matriz General');self.app.after(200,self.app.quit);self.app.mainloop()
        self.assertNotIn('recargar_matriz_completa',self.app._view_pending);self.assertFalse(self.errors)

    def test_instrument_import_preview_uses_boxes_and_cancel_keeps_live_data(self):
        import openpyxl
        from instrumentos_excel import RAW
        from instrument_design import InstrumentPreview
        file=app_storage.data_dir()/'evaluacion-previa.xlsx'
        db.exportar_plantilla_rubrica_o_cotejo_excel(str(file),self.course_name,'3°','A','Prueba','Competencia',[(self.cap,'Capacidad','Explica')],'Rúbrica',sesion_id=self.session,formato=3)
        wb=openpyxl.load_workbook(file);wb[RAW]['D2']='AD';wb.save(file);wb.close()
        inspected=[]
        def decide(confirm):
            for widget in self.app.winfo_children():
                if isinstance(widget,InstrumentPreview) and widget.ready:
                    inspected.append(widget.instrument_grid.indicators[0]['descriptores']['AD'])
                    widget.confirmed=confirm;widget.destroy();return
            self.app.after(50,lambda:decide(confirm))
        self.app.after(50,lambda:decide(False))
        self.assertIsNone(self.app._importar_con_vista_previa(db.importar_rubrica_o_cotejo_desde_excel,self.session,str(file),'3°','A'))
        self.assertFalse(db.obtener_indicadores_instrumento_sesion(self.session))
        self.app.after(50,lambda:decide(True))
        self.assertEqual(self.app._importar_con_vista_previa(db.importar_rubrica_o_cotejo_desde_excel,self.session,str(file),'3°','A'),(1,1))
        with db.obtener_conexion() as conn:self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],20)
        self.assertEqual(len(inspected),2);self.assertFalse(self.errors)

    def test_search_loads_without_ids_and_filters_fit_a_small_window(self):
        self.app.geometry('1024x740');self.app.tabview.set('Buscador')
        self.app.after(350,self.app.quit);self.app.mainloop()
        self.assertEqual(self.app.busc_combo_ir_clase.get(),'Prueba')
        self.assertEqual(len(self.app.tree_buscador_alumnos.get_children()),1)
        frame=self.app.busc_combo_ir_clase.master
        for widget in frame.winfo_children():
            if widget.winfo_manager()=='place':
                self.assertLessEqual(widget.winfo_x()+widget.winfo_width(),frame.winfo_width()+2)
                self.assertLessEqual(widget.winfo_y()+widget.winfo_height(),frame.winfo_height()+2)
        self.assertFalse(self.errors)

    def test_excel_first_download_import_and_individual_criteria_in_main_page(self):
        import json,openpyxl
        from excel_ui import TemplateOptions
        from instrument_design import InstrumentPreview
        from plantilla_simple import REGISTRO as EVALUAR,INSTRUMENTO as IND
        from instrumentos_excel import META
        self.app.edicion_desbloqueada=True
        self.app.calif_combo_modo_inst.set('Rúbrica');self.app.cambiar_metodo_evaluacion('Rúbrica')
        self.assertEqual(self.app._export_button.cget('state'),'normal')
        file=app_storage.data_dir()/'Rubrica_Prueba.xlsx'
        def choose_counts():
            for window in self.app.winfo_children():
                if isinstance(window,TemplateOptions) and window.ready:
                    window.counts[self.cap].set('2');window.confirm();return
            self.app.after(50,choose_counts)
        self.app.after(50,choose_counts)
        with patch.object(self.app,'elegir_destino',return_value=str(file)),patch.object(self.app,'insignia_exportacion',return_value=None),patch.object(self.app,'archivo_guardado'):
            self.app.exportar_modelo_actual('Rúbrica')
        self.assertFalse(db.obtener_indicadores_instrumento_sesion(self.session))
        wb=openpyxl.load_workbook(file);meta={r[0].value:r[1].value for r in wb[META]}
        for n,entry in enumerate(json.loads(meta['layout_rows']),1):
            row=entry['row'];wb[IND].cell(row,3,f'Criterio {n} de esta sesión')
            for col,text in enumerate(['Con apoyo','Parcialmente','Autónomamente','Justifica y comprueba'],4):wb[IND].cell(row,col,text)
        wb[EVALUAR]['D2']='Prueba, Ana';wb[EVALUAR]['E2']=6;wb[EVALUAR]['F2']=8;wb.save(file);wb.close()
        def approve():
            for window in self.app.winfo_children():
                if isinstance(window,InstrumentPreview) and window.ready:window.confirmed=True;window.destroy();return
            self.app.after(50,approve)
        self.app.after(50,approve)
        with patch('tkinter.filedialog.askopenfilename',return_value=str(file)),patch('tkinter.messagebox.showinfo'):
            self.app._subir_excel_instrumento_a_sesion(self.session)
        panel=self.app._embedded_evaluation
        self.assertEqual(len(panel.grid_view.variables),2)
        tree=self.app.planilla_nativa;iid=tree.get_children()[0]
        self.assertEqual(float(tree.item(iid,'values')[4]),14)
        self.assertEqual(self.app._evaluation_view,'criteria')
        self.app.after(200,self.app.quit);self.app.mainloop()
        self.app.cambiar_vista_evaluacion('Resultados y asistencia')
        tree._start_entry_edit(iid,'Cap 1',4,'14')
        self.assertIsNone(tree._entry);self.assertEqual(self.app._evaluation_view,'criteria')
        self.assertFalse(self.errors)

    def test_main_page_grades_each_criterion_and_undo_restores_its_answer(self):
        from evaluacion_datos import get_answers
        self.app.edicion_desbloqueada=True
        values=[dict(capacidad_id=self.cap,criterio=f'Criterio {n}',puntaje_maximo=10,puntajes=dict(C=2,B=6,A=8,AD=10)) for n in (1,2)]
        first,second=db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',values)
        self.app.recargar_tabla_actividades_creadas();self.app.abrir_actividad_en_pestana_calificar(self.session)
        panel=self.app._embedded_evaluation
        panel.set_answer(self.student,first,'B');panel.set_answer(self.student,second,'A')
        tree=self.app.planilla_nativa;iid=tree.get_children()[0]
        self.assertEqual(float(tree.item(iid,'values')[4]),14)
        self.app.deshacer_planilla()
        self.assertEqual(panel.answers[(self.student,first)],'B');self.assertNotIn((self.student,second),panel.answers)
        self.assertEqual(float(tree.item(iid,'values')[4]),12)
        self.app.deshacer_planilla(redo=True)
        self.assertEqual(panel.answers[(self.student,second)],'A')
        self.app.cambiar_interfaz_visual('Gris Profesional')
        from grade_cells import PALETTE
        self.assertEqual(panel.grid_view.cells[(first,'C')].cget('fg_color'),PALETTE['C'][0])
        with patch('tkinter.messagebox.showinfo'):self.app.accion_guardar_planilla_calificacion_completa()
        self.assertEqual(get_answers(self.session,self.app._db_path),{(self.student,first):'B',(self.student,second):'A'})
        self.assertFalse(self.app._planilla_pendiente);self.assertFalse(self.errors)

    def test_license_section_explains_why_personal_preview_has_no_activation(self):
        self.app.abrir_configuracion('Licencia');self.app.update_idletasks()
        self.assertEqual(self.app.config_tabs.get(),'Licencia')
        self.assertEqual(self.app.config_import_license.cget('state'),'disabled')
        self.assertFalse(self.errors)

    def test_group_matrix_manual_points_navigation_and_partial_save(self):
        from evaluacion_datos import get_answers
        other=db.agregar_estudiante('Beto','Segundo','3°','A')
        self.app.edicion_desbloqueada=True
        rows=[dict(capacidad_id=self.cap,criterio=f'Evidencia {n}',puntaje_maximo=10) for n in (1,2)]
        first,second=db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',rows)
        self.app.recargar_tabla_actividades_creadas();self.app.abrir_actividad_en_pestana_calificar(self.session)
        panel=self.app._embedded_evaluation;matrix=panel.matrix
        self.app.update();self.assertEqual(panel._panel_view,'Grupo')
        self.assertEqual(len(matrix.table.get_children()),2)
        matrix.begin_edit(self.student,first);matrix.editor.delete(0,'end');matrix.editor.insert(0,'7,25');matrix.commit_edit('down')
        self.assertEqual(matrix.selected,(other,first));matrix.cancel_edit()
        self.assertEqual(matrix.table.set(str(self.student),str(first)),'7.25 (A)')
        matrix.select(self.student,first)
        self.assertIn('provisional',matrix.note.cget('text'));self.assertIn('14.5 / 20 (A)',matrix.note.cget('text'))
        matrix.begin_edit(other,first);matrix.editor.delete(0,'end');matrix.editor.insert(0,'0');matrix.commit_edit('next')
        self.assertEqual(matrix.selected,(other,second));matrix.cancel_edit()
        self.assertEqual(matrix.table.set(str(other),str(first)),'0 (C)')
        self.assertEqual(matrix.table.set(str(other),str(second)),'Pendiente')
        matrix.select(self.student,first)
        matrix.apply_value('5.2495')
        self.assertEqual(matrix.table.set(str(self.student),str(first)),'5.2495 (B)')
        self.assertIn('10.5 / 20 (B)',matrix.note.cget('text'))
        matrix.apply_value('7.25')
        with patch('tkinter.messagebox.showwarning'):
            self.assertFalse(matrix.apply_value('11'))
        self.assertEqual(panel.answers[(self.student,first)],'7.25')
        with patch('tkinter.messagebox.showinfo'):self.app.accion_guardar_planilla_calificacion_completa()
        self.assertEqual(get_answers(self.session,self.app._db_path),{(self.student,first):'7.25',(other,first):'0'})
        with db.obtener_conexion() as conn:
            self.assertEqual(dict(conn.execute('SELECT estudiante_id,nota FROM Notas_Sesion_Capacidad')),{self.student:14.5,other:0})
        self.assertFalse(self.errors)

    def test_individual_rubric_accepts_manual_points_and_zero(self):
        self.app.edicion_desbloqueada=True
        first,=db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Explica la evidencia',10)])
        self.app.recargar_tabla_actividades_creadas();self.app.abrir_actividad_en_pestana_calificar(self.session)
        panel=self.app._embedded_evaluation;panel._change_view('Individual');self.app.update()
        entry=panel.grid_view.numeric_entries[first];entry.insert(0,'8,25')
        self.assertTrue(panel.grid_view._manual(first));self.assertEqual(panel.answers[(self.student,first)],'8.25')
        self.assertIn('Nivel A',panel.grid_view.badges[first].cget('text'))
        entry.delete(0,'end');entry.insert(0,'5.2495');panel.grid_view._manual(first)
        self.assertIn('Nivel B',panel.grid_view.badges[first].cget('text'))
        entry.delete(0,'end');entry.insert(0,'0');panel.grid_view._manual(first)
        tree=self.app.planilla_nativa
        self.assertEqual(float(tree.item(tree.get_children()[0],'values')[4]),0)
        self.assertFalse(self.errors)

    def test_group_selection_keeps_capacity_context_and_cancels_uncommitted_edit(self):
        self.app.edicion_desbloqueada=True
        other=db.obtener_capacidades_por_competencia(self.comp)[1][0]
        db.crear_o_actualizar_sesion_clase(self.session,self.course,self.comp,'3°','A','Dos capacidades','',1,[(self.cap,'Representa'),(other,'Explica')])
        first,second=db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Representa',10),(other,'Explica',20)])
        self.app.recargar_tabla_actividades_creadas();self.app.abrir_actividad_en_pestana_calificar(self.session)
        panel=self.app._embedded_evaluation;self.app.update()
        panel.matrix.select(self.student,second)
        self.assertEqual(panel.grid_view.capacities[panel.grid_view.choice.get()],other)
        self.assertIn('Explica',panel.matrix.title.cget('text'))
        panel.matrix.begin_edit(self.student,second);panel.matrix.editor.insert(0,'18');panel.matrix.cancel_edit()
        self.assertNotIn((self.student,second),panel.answers)
        self.app.abrir_evaluacion_por_criterios(self.student,self.cap)
        self.assertEqual(panel.matrix.selected,(self.student,first))
        panel.matrix.begin_edit(self.student,first);panel.matrix.editor.insert(0,'9')
        self.app.destroy();self.assertFalse(self.errors)

    def _checklist_panel(self,count=2):
        self.app.edicion_desbloqueada=True
        values=[dict(capacidad_id=self.cap,criterio=f'Evidencia observable {n}',puntaje_maximo=1) for n in range(count)]
        ids=db.guardar_indicadores_instrumento_sesion(self.session,'Lista de Cotejo',values)
        self.app.recargar_tabla_actividades_creadas();self.app.abrir_actividad_en_pestana_calificar(self.session)
        # Wait for the real debounced layout before using native cell coordinates.
        self.app.after(450,self.app.quit);self.app.mainloop();self.app.update_idletasks()
        return self.app._embedded_evaluation,ids

    def test_fast_checklist_click_keyboard_undo_and_save_without_grades(self):
        from types import SimpleNamespace
        from evaluacion_datos import get_answers
        panel,ids=self._checklist_panel();matrix=panel.matrix
        box=matrix.table.bbox(str(self.student),str(ids[0]));self.assertTrue(box)
        x,y,w,h=box;matrix._clicked(SimpleNamespace(x=x+w//2,y=y+h//2))
        self.assertEqual(panel.answers[(self.student,ids[0])],'Sí')
        matrix.move_cell('next');matrix._typed(SimpleNamespace(char='n',keysym='n',state=0))
        self.assertEqual(panel.answers[(self.student,ids[1])],'No')
        self.assertTrue(self.app._is_grade_widget(matrix.table))
        self.app.deshacer_planilla();self.assertNotIn((self.student,ids[1]),panel.answers)
        self.app.deshacer_planilla(True);self.assertEqual(panel.answers[(self.student,ids[1])],'No')
        self.assertEqual(self.app.planilla_nativa.item(self.app.planilla_nativa.get_children()[0],'values')[4],'')
        with patch('tkinter.messagebox.showinfo'):self.app.accion_guardar_planilla_calificacion_completa()
        self.assertEqual(get_answers(self.session,self.app._db_path),{(self.student,ids[0]):'Sí',(self.student,ids[1]):'No'})
        with db.obtener_conexion() as conn:self.assertFalse(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad WHERE nota IS NOT NULL').fetchall())
        matrix._typed(SimpleNamespace(char='',keysym='Delete',state=0));self.assertIsNone(panel.answers[(self.student,ids[1])])
        self.assertFalse(self.errors)

    def test_checklist_conversion_is_reviewed_undoable_and_saved_explicitly(self):
        from cotejo_ui import ChecklistConversion
        from cotejo import configuration
        panel,ids=self._checklist_panel();panel.set_answer(self.student,ids[0],'Sí');panel.set_answer(self.student,ids[1],'No')
        dialog=ChecklistConversion(panel);self.app.update_idletasks()
        dialog.choice.set('Proporcional: cumplimiento × 20');self.assertTrue(dialog.review())
        with db.obtener_conexion() as conn:self.assertFalse(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchall())
        dialog.confirm()
        self.assertEqual(float(self.app.planilla_nativa.item(self.app.planilla_nativa.get_children()[0],'values')[4]),10)
        panel.set_answer(self.student,ids[1],'Sí')
        with patch('tkinter.messagebox.showwarning') as warning:
            self.app.accion_guardar_planilla_calificacion_completa();warning.assert_called_once()
        with db.obtener_conexion() as conn:self.assertFalse(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchall())
        self.app.deshacer_planilla()
        self.app.deshacer_planilla();self.assertEqual(self.app.planilla_nativa.item(self.app.planilla_nativa.get_children()[0],'values')[4],'')
        self.app.deshacer_planilla(True)
        with patch('tkinter.messagebox.showinfo'):self.app.accion_guardar_planilla_calificacion_completa()
        self.assertEqual(configuration(self.session,self.app._db_path),({'tipo':'proporcional'},False))
        with db.obtener_conexion() as conn:self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad').fetchone()[0],10)
        self.assertFalse(self.errors)

    def test_wide_criteria_scroll_keeps_names_fixed_and_sidebar_collapses(self):
        panel,ids=self._checklist_panel(count=12);matrix=panel.matrix
        before=matrix.identity.winfo_rootx();values=matrix.identity.item(str(self.student),'values')
        matrix.table.xview_moveto(1);self.app.update_idletasks()
        self.assertGreater(matrix.table.xview()[0],0)
        first_header=matrix.criteria_header.find_all()[0]
        self.assertLess(matrix.criteria_header.coords(first_header)[0],0)
        self.assertEqual(matrix.criteria_header.winfo_rootx(),matrix.table.winfo_rootx())
        self.assertFalse(self.app._evaluation_panel.container.winfo_ismapped())
        self.assertEqual(matrix.identity.winfo_rootx(),before);self.assertEqual(matrix.identity.item(str(self.student),'values'),values)
        state=self.app.tabview.expanded;self.app.tabview.toggle();self.app.update_idletasks()
        self.assertEqual(self.app.tabview.expanded,not state)
        self.app._guardar_ventana();self.assertEqual(self.app._preferencias()['nav_expanded'],not state)
        self.assertIn('Competencia:',self.app._competency_label.cget('text'))
        self.assertFalse(self.errors)

    def test_selected_capacities_two_three_four_keep_real_names_and_competency(self):
        from cotejo import capacity_label
        caps=db.obtener_capacidades_por_competencia(self.comp)[1:4]
        self.assertEqual(len(caps),3)
        db.crear_o_actualizar_sesion_clase(self.session,self.course,self.comp,'3°','A','Prueba','',1,[(c[0],'Evidencia propia') for c in caps])
        db.guardar_indicadores_instrumento_sesion(self.session,'Lista de Cotejo',[dict(capacidad_id=c[0],criterio='Evidencia '+c[1],puntaje_maximo=1) for c in caps])
        self.app.recargar_tabla_actividades_creadas();self.app.abrir_actividad_en_pestana_calificar(self.session)
        self.app.after(450,self.app.quit);self.app.mainloop();self.app.update_idletasks()
        matrix=self.app._embedded_evaluation.matrix
        self.assertEqual([i['capacidad_id'] for i in matrix.items],[c[0] for c in caps])
        for n,c in enumerate(caps,1):self.assertEqual(self.app.planilla_nativa.heading(f'Cap {n}','text'),capacity_label(c[1]))
        texts=[matrix.criteria_header.itemcget(i,'text') for i in matrix.criteria_header.find_all() if matrix.criteria_header.type(i)=='text']
        for cap in caps:self.assertIn(capacity_label(cap[1]),texts)
        self.assertIn(db.obtener_competencias_por_curso(self.course)[0][1],self.app._competency_label.cget('text'))
        self.assertFalse(self.errors)

    def test_matrix_number_name_resize_arrows_and_compact_footer(self):
        from types import SimpleNamespace
        for n in range(28):db.agregar_estudiante(f'Alumno {n:02}',f'Apellido {n:02}','3°','A')
        panel,ids=self._checklist_panel(count=12);matrix=panel.matrix
        self.assertEqual(matrix.identity.heading('code','text'),'N°')
        self.assertEqual(matrix.identity.item(matrix.identity.get_children()[0],'values')[0],'01')
        self.assertFalse(matrix.title.winfo_ismapped());self.assertFalse(matrix.hint.winfo_ismapped())
        before=matrix.identity.column('name','width');matrix._start_resize(SimpleNamespace(x_root=400),'name')
        matrix._resize_identity(SimpleNamespace(x_root=480));matrix._finish_resize()
        self.assertGreater(matrix.identity.column('name','width'),before)
        self.assertEqual(self.app._preferencias()['criteria_name_width'],self.app._criteria_name_width)
        first=next(iter(panel.by_student));matrix.select(first,ids[0]);matrix.table.focus_force();self.app.update()
        matrix.table.event_generate('<Right>');self.app.update();self.assertEqual(matrix.selected,(first,ids[1]))
        matrix.table.event_generate('<Left>');self.app.update();self.assertEqual(matrix.selected,(first,ids[0]))
        for _ in range(11):matrix.move_cell('right')
        self.assertGreater(matrix.table.xview()[0],0)
        for _ in range(28):matrix.move_cell('down')
        self.app.update_idletasks();self.assertGreater(matrix.identity.yview()[0],0)
        self.assertEqual(matrix.identity.selection(),matrix.table.selection());self.assertFalse(self.errors)

    def test_rubric_arrows_cancel_and_undo_restore_incorrect_entry(self):
        self.app.edicion_desbloqueada=True
        first,second=db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Explica',10),(self.cap,'Comprueba',10)])
        self.app.recargar_tabla_actividades_creadas();self.app.abrir_actividad_en_pestana_calificar(self.session)
        self.app.after(450,self.app.quit);self.app.mainloop();matrix=self.app._embedded_evaluation.matrix
        matrix.begin_edit(self.student,first);matrix.editor.insert(0,'8');matrix.commit_edit('right')
        self.assertEqual(matrix.selected,(self.student,second));self.assertIsNotNone(matrix.editor)
        matrix.editor.insert(0,'999');matrix.cancel_edit()
        self.assertNotIn((self.student,second),matrix.panel.answers)
        self.app.deshacer_planilla();self.assertNotIn((self.student,first),matrix.panel.answers)
        self.app.deshacer_planilla(True);self.assertEqual(float(matrix.panel.answers[(self.student,first)]),8)
        self.assertEqual(matrix.descriptor_title.cget('font').cget('weight'),'bold')
        self.assertFalse(self.errors)

    def test_filled_table_export_and_adapted_import_preview_cancel_then_confirm(self):
        import openpyxl
        from excel_dialogs import TableImportPreview
        panel,ids=self._checklist_panel();panel.set_answer(self.student,ids[0],'Sí')
        with patch('tkinter.messagebox.showinfo'):self.app.accion_guardar_planilla_calificacion_completa()
        file=app_storage.data_dir()/'tabla_completa.xlsx'
        with patch.object(self.app,'elegir_destino',return_value=str(file)),patch.object(self.app,'archivo_guardado'):
            self.app.exportar_tabla_actual()
        wb=openpyxl.load_workbook(file);self.assertEqual(wb['Registro']['C7'].value,'Sí');wb['Instrumento']['B3']='Competencia nueva importada';wb.save(file);wb.close()
        with db.obtener_conexion() as conn:before=conn.execute('SELECT COUNT(*) FROM Competencias').fetchone()[0]
        def answer(accept):
            for window in self.app.winfo_children():
                if isinstance(window,TableImportPreview) and window.ready:
                    window.confirm() if accept else window.destroy();return
            self.app.after(60,lambda:answer(accept))
        for accept in (False,True):
            self.app.after(60,lambda chosen=accept:answer(chosen))
            with patch('tkinter.filedialog.askopenfilename',return_value=str(file)),patch('tkinter.messagebox.showinfo'):
                self.app._subir_excel_instrumento_a_sesion(self.session)
            with db.obtener_conexion() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM Competencias').fetchone()[0],before+int(accept))
        self.assertNotEqual(self.app.id_actividad_calificando,self.session)
        self.assertIn('Competencia nueva importada',[name for identity,name in self.app.competencias_curso_actual])
        self.assertIn('Competencia nueva importada',self.app._competency_label.cget('text'));self.assertFalse(self.errors)

    def test_final_matrix_export_lets_teacher_choose_number_and_letter(self):
        import openpyxl
        from excel_dialogs import GradeDisplayOptions
        db.guardar_calificaciones_y_asistencia_sesion(self.session,[dict(estudiante_id=self.student,notas_por_capacidad={self.cap:17})])
        self.app.tabview.set('Matriz General');self.app.recargar_matriz_completa();file=app_storage.data_dir()/'matriz_ambos.xlsx'
        def choose():
            for window in self.app.winfo_children():
                if isinstance(window,GradeDisplayOptions) and window.ready:window.choice.set('ambos');window.confirm();return
            self.app.after(60,choose)
        self.app.after(60,choose)
        with patch.object(self.app,'elegir_destino',return_value=str(file)),patch.object(self.app,'insignia_exportacion',return_value=None),patch('tkinter.messagebox.showinfo'):
            self.app.accion_exportar_matriz_excel()
        wb=openpyxl.load_workbook(file);self.addCleanup(wb.close)
        self.assertEqual(wb.active['A2'].value,'N°');self.assertEqual(wb.active['C4'].value,'17 (A)');self.assertFalse(self.errors)

    def test_global_grade_five_applies_to_selected_capacities_and_supports_undo_save(self):
        self.app.edicion_desbloqueada=True
        caps=db.obtener_capacidades_por_competencia(self.comp)
        sid=db.crear_o_actualizar_sesion_clase(None,self.course,self.comp,'3°','A','Ficha de ecuaciones','Explicar una solución',1,[(c[0],'') for c in caps],categoria='Trabajos',tipo_actividad='Ficha de trabajo',metodo='Nota global')
        self.app.recargar_tabla_actividades_creadas();self.app.abrir_actividad_en_pestana_calificar(sid)
        self.app.after(450,self.app.quit);self.app.mainloop()
        self.assertEqual(self.app.calif_combo_modo_inst.get(),'Nota global');self.assertEqual(self.app._evaluation_view,'global')
        panel=self.app._global_grade_panel;iid=panel.table.get_children()[0]
        self.assertEqual(panel.table['displaycolumns'],('Asistencia','Nota global','Comentario'))
        panel.edit(iid);panel.editor.insert(0,'5');self.assertTrue(panel.commit())
        self.assertEqual(self.app.planilla_nativa.item(iid,'values')[4:-1],tuple('5' for c in caps))
        self.app.deshacer_planilla();self.assertEqual(panel.table.set(iid,'Nota global'),'')
        self.app.deshacer_planilla(True);self.assertEqual(panel.table.set(iid,'Nota global'),'5')
        with patch('tkinter.messagebox.showinfo'):self.app.accion_guardar_planilla_calificacion_completa()
        with db.obtener_conexion() as conn:
            self.assertEqual(conn.execute('SELECT DISTINCT nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',(sid,)).fetchall(),[(5.0,)])
            self.assertEqual(conn.execute('SELECT modo_ingreso FROM Sesiones_Clase WHERE id=?',(sid,)).fetchone()[0],'global')
        self.app.dibujar_planilla_calificacion(forzar=True)
        self.assertEqual(self.app._global_grade_panel.table.set(self.app._global_grade_panel.table.get_children()[0],'Nota global'),'5')
        self.assertFalse(self.errors)

    def test_create_worksheet_in_trabajos_with_any_evaluation_method(self):
        self.app.edicion_desbloqueada=True;self.app.tabview.set('Crear Actividad')
        self.app.crear_combo_tipo.set('Ficha de trabajo');self.app.al_elegir_tipo_actividad('Ficha de trabajo')
        self.assertEqual(self.app.crear_combo_categoria.get(),'Trabajos')
        self.app.crear_entry_titulo.insert(0,'Ficha 1');self.app.crear_combo_metodo.set('Nota global')
        self.app.crear_txt_proposito.insert('1.0','Resolver ecuaciones justificando cada paso')
        with patch('tkinter.messagebox.showinfo'),patch('tkinter.messagebox.askyesno',return_value=False):self.app.accion_guardar_nueva_actividad()
        with db.obtener_conexion() as conn:
            row=conn.execute("SELECT categoria,tipo_actividad,modo_ingreso,proposito FROM Sesiones_Clase WHERE titulo_tema='Ficha 1'").fetchone()
        self.assertEqual(row,('Trabajos','Ficha de trabajo','global','Resolver ecuaciones justificando cada paso'))
        self.assertEqual(self.app.crear_combo_metodo.cget('values'),['Nota global','Nota directa','Rúbrica','Lista de Cotejo'])
        self.assertFalse(self.errors)

    def test_grade_fonts_match_names_and_practice_list_is_readable(self):
        import tkinter.font as tkfont
        from tkinter import ttk
        self.app.edicion_desbloqueada=True
        tree=self.app.planilla_nativa;iid=tree.get_children()[0];tree._update_value(iid,4,'15');tree.paint_grades()
        expected=getattr(self.app,'_native_table_font_size')
        self.assertEqual(tree._cell_font.cget('size'),expected)
        base=tkfont.Font(root=self.app,font=ttk.Style(self.app).lookup('Treeview','font'))
        self.assertLessEqual(tree._cell_font.metrics('linespace'),base.metrics('linespace')+3)
        self.app.actualizar_lista_practicas()
        font=tkfont.Font(root=self.app,font=self.app.puntos_panel.listing.cget('font'))
        descriptor=self.app.tk.splitlist(self.app.puntos_panel.listing.cget('font'))
        self.assertEqual(int(descriptor[1]),expected)
        self.assertGreaterEqual(font.metrics('linespace'),base.metrics('linespace')-2)
        self.assertFalse(self.errors)

    def test_switch_to_global_commits_active_rubric_cell_and_keeps_selected_method(self):
        self.app.edicion_desbloqueada=True
        identity=db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Explica',10)])[0]
        self.app.recargar_tabla_actividades_creadas();self.app.abrir_actividad_en_pestana_calificar(self.session)
        self.app.after(450,self.app.quit);self.app.mainloop()
        matrix=self.app._embedded_evaluation.matrix;matrix.begin_edit(self.student,identity);matrix.editor.insert(0,'8')
        self.app.calif_combo_modo_inst.set('Nota global');self.app.cambiar_metodo_evaluacion('Nota global')
        self.assertEqual(self.app.calif_combo_modo_inst.get(),'Nota global')
        panel=self.app._global_grade_panel;self.assertEqual(panel.table.set(panel.table.get_children()[0],'Nota global'),'16')
        self.assertFalse(self.errors)

    def test_period_units_filter_activities_and_preserve_period_notes(self):
        import periodos
        unit=periodos.save_unit(db.DB_PATH,self.course,'3°','A','Unidad: fracciones')
        other=db.crear_o_actualizar_sesion_clase(None,self.course,self.comp,'3°','A','Otra unidad','',1,[(self.cap,'Criterio')],unidad_id=unit)
        self.app.actualizar_contexto_academico()
        caption=next(k for k,v in self.app._unit_labels.items() if v==unit)
        self.app.unit_filter.set(caption);self.app.filtrar_unidad()
        self.assertEqual(self.app.tree_actividades.get_children(),(str(other),))
        self.app.unit_filter.set('Todas las unidades');self.app.filtrar_unidad()
        self.assertEqual(len(self.app.tree_actividades.get_children()),2)
        self.app.seleccionar_periodo();self.app.update()
        self.assertTrue(self.app.period_button.cget('text'));self.assertFalse(self.errors)

    def test_global_clipboard_preview_applies_one_undoable_block(self):
        self.app.edicion_desbloqueada=True
        self.app.calif_combo_modo_inst.set('Nota global');self.app.actualizar_herramientas_evaluacion();self.app.update()
        panel=self.app._global_grade_panel;panel.table.selection_set(panel.table.get_children()[0])
        before=self.app._filas_planilla();self.app.clipboard_clear();self.app.clipboard_append('5')
        self.app.pegar_planilla();self.app.update();self.assertEqual(self.app._filas_planilla(),before)
        self.app._paste_apply();self.app.update()
        self.assertEqual(float(self.app._filas_planilla()[0][4]),5)
        self.app.deshacer_planilla();self.assertEqual(self.app._filas_planilla(),before)
        self.assertFalse(self.errors)

    def test_rubric_clipboard_preserves_levels_and_undo(self):
        self.app.edicion_desbloqueada=True
        db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Argumenta',20)])
        self.app.recargar_tabla_actividades_creadas();self.app.abrir_actividad_en_pestana_calificar(self.session)
        self.app.calif_combo_modo_inst.set('Rúbrica');self.app.actualizar_herramientas_evaluacion();self.app.cambiar_vista_evaluacion('Criterios');self.app.update()
        panel=self.app._embedded_evaluation;panel.matrix.table.selection_set(str(self.student))
        self.app.clipboard_clear();self.app.clipboard_append('A');self.app.pegar_planilla();self.app.update();self.app._paste_apply();self.app.update()
        self.assertIn('A',self.app._instrument_pending.values())
        self.app.deshacer_planilla();self.assertNotIn('A',self.app._instrument_pending.values())
        self.assertFalse(self.errors)

    def test_school_identity_and_report_preview_open_with_uploaded_badge(self):
        import institucion,reportes
        from PIL import Image
        self.app.edicion_desbloqueada=True
        for key,value in [('nombre','IE de ejemplo'),('codigo','1234567'),('ugel','UGEL de ejemplo')]:
            entry=self.app._institution_entries[key];entry.delete(0,'end');entry.insert(0,value)
        self.assertTrue(self.app.guardar_identidad())
        self.assertEqual(institucion.profile(db.DB_PATH)['codigo'],'1234567')
        path=app_storage.data_dir()/'insignia-test.png';Image.new('RGB',(80,100),'blue').save(path)
        reportes.save_logo(path,db.DB_PATH);self.app.actualizar_insignia()
        self.app.abrir_configuracion('Institución');self.app.vista_previa_informe();self.app.update()
        self.assertIsNotNone(self.app._institution_image)
        self.assertFalse(self.errors)

    def test_fill_selected_grade_rows_is_undoable(self):
        self.app.edicion_desbloqueada=True
        tree=self.app.planilla_nativa;tree.selection_set(tree.get_children()[0]);before=self.app._filas_planilla()
        with patch('tkinter.simpledialog.askstring',return_value='16'),patch('tkinter.messagebox.askyesno',return_value=True):self.app.rellenar_seleccion()
        self.assertEqual(float(self.app._filas_planilla()[0][4]),16)
        self.app.deshacer_planilla();self.assertEqual(self.app._filas_planilla(),before)
        self.assertFalse(self.errors)

    def test_school_manager_edits_general_units_and_removes_without_losing_notes(self):
        import periodos
        periodos.identify(db.DB_PATH,2031,2,'Trimestres')
        self.app.edicion_desbloqueada=True;self.app.seleccionar_periodo();self.app.update()
        manager=self.app._organization_manager;manager.edit_unit(True);self.app.update()
        manager._unit_fields['nombre'].insert(0,'Unidad general de ejemplo');manager._unit_save();self.app.update()
        unit=next(iter(manager.units.values()));self.assertEqual(unit['general'],1)
        with db.obtener_conexion() as conn:periodos.assign_unit(conn,self.session,unit['id'])
        db.guardar_notas_globales_sesion(self.session,{self.student:17})
        manager.unit_tree.selection_set(str(unit['id']));manager.edit_unit();manager._unit_fields['nombre'].delete(0,'end');manager._unit_fields['nombre'].insert(0,'Unidad editada');manager._unit_save()
        manager.unit_tree.selection_set(str(unit['id']))
        with patch('tkinter.messagebox.askyesno',return_value=True):manager.delete_unit()
        self.assertEqual(periodos.units(db.DB_PATH),[])
        with db.obtener_conexion() as conn:
            self.assertIsNone(conn.execute('SELECT unidad_id FROM Sesiones_Clase WHERE id=?',(self.session,)).fetchone()[0])
            self.assertEqual(conn.execute('SELECT nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',(self.session,)).fetchone()[0],17)
        self.assertFalse(self.errors)

    def test_period_manager_edits_year_scheme_and_name_in_place(self):
        import periodos
        self.app.edicion_desbloqueada=True;self.app.seleccionar_periodo();self.app.update()
        manager=self.app._organization_manager;manager.edit_period();self.app.update()
        for key,value in [('year','2032'),('name','Periodo editado')]:
            field=manager._period_fields[key];field.delete(0,'end');field.insert(0,value)
        manager._period_fields['scheme'].set('Trimestres');manager._period_fields['number'].set('3');manager._period_save();self.app.update()
        current=periodos.info(db.DB_PATH);self.assertEqual((current['year'],current['number'],current['scheme'],current['name']),(2032,3,'Trimestres','Periodo editado'))
        self.assertFalse(self.errors)

    def test_school_picker_keeps_students_separate(self):
        import colegios
        self.app.edicion_desbloqueada=True;self.app.seleccionar_periodo();manager=self.app._organization_manager
        with patch('tkinter.simpledialog.askstring',return_value='Segundo colegio de prueba'):manager.add_school()
        row=manager.schools[manager.school.get()];self.assertNotEqual(row['id'],self.app._school_id)
        with db.obtener_conexion(row['records'][0]['path']) as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM Estudiantes').fetchone()[0],0)
        manager.finish();self.app.actualizar_contexto_academico()
        choice=next(k for k,r in self.app._school_choices.items() if r['id']==row['id'])
        with patch.object(self.app,'_reiniciar') as restart:self.app.cambiar_colegio(choice)
        restart.assert_called_once_with(row['records'][-1]['path'])
        with db.obtener_conexion() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM Estudiantes').fetchone()[0],1)
        self.assertFalse(self.errors)

    def test_rubric_cards_show_ranges_and_classify_exact_numeric_values(self):
        self.app.edicion_desbloqueada=True
        db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Argumenta',20)])
        self.app.recargar_tabla_actividades_creadas();self.app.abrir_actividad_en_pestana_calificar(self.session)
        self.app.calif_combo_modo_inst.set('Rúbrica');self.app.actualizar_herramientas_evaluacion();self.app.cambiar_vista_evaluacion('Criterios');self.app.update()
        matrix=self.app._embedded_evaluation.matrix
        self.assertEqual(matrix.level_boxes[1][1].cget('text'),'B · 10.5 a < 13.5')
        matrix.apply_value('12.7');self.app.update()
        self.assertEqual(matrix.level_boxes[1][0].cget('border_width'),2)
        matrix.apply_value('13.5');self.app.update();self.assertEqual(matrix.level_boxes[2][0].cget('border_width'),2)
        self.assertFalse(self.errors)

    def test_general_matrix_changes_with_unit_filter(self):
        import periodos
        self.app.edicion_desbloqueada=True
        first=periodos.save_unit(db.DB_PATH,None,None,None,'Primera unidad')
        second=periodos.save_unit(db.DB_PATH,None,None,None,'Segunda unidad')
        with db.obtener_conexion() as conn:periodos.assign_unit(conn,self.session,first)
        db.guardar_notas_globales_sesion(self.session,{self.student:20})
        other=db.crear_o_actualizar_sesion_clase(None,self.course,self.comp,'3°','A','Otra unidad','',1,[(self.cap,'Criterio')],unidad_id=second)
        db.guardar_notas_globales_sesion(other,{self.student:4})
        self.app.actualizar_contexto_academico();self.app.tabview.set('Matriz General')
        caption=next(k for k,v in self.app._unit_labels.items() if v==first)
        self.app.unit_filter.set(caption);self.app.filtrar_unidad();self.app.update()
        self.assertEqual(self.app.datos_matriz_actual[1][0]['promedio_general'],20)
        self.app.unit_filter.set('Todas las unidades');self.app.filtrar_unidad();self.app.update()
        self.assertEqual(self.app.datos_matriz_actual[1][0]['promedio_general'],12)
        self.assertFalse(self.errors)

    def test_unit_export_sanitizes_filename_and_keeps_full_unit_title(self):
        import periodos,re,openpyxl
        from excel_dialogs import GradeDisplayOptions
        unit=periodos.save_unit(db.DB_PATH,None,None,None,'Unidad 1: razones / proporciones')
        self.app.actualizar_contexto_academico();self.app.tabview.set('Matriz General')
        self.app.unit_filter.set(next(k for k,v in self.app._unit_labels.items() if v==unit));self.app.filtrar_unidad();self.app.update()
        file=app_storage.data_dir()/'unidad-exportada.xlsx'
        def choose():
            for window in self.app.winfo_children():
                if isinstance(window,GradeDisplayOptions) and window.ready:window.confirm();return
            self.app.after(50,choose)
        self.app.after(50,choose)
        with patch.object(self.app,'elegir_destino',return_value=str(file)) as destination,patch('tkinter.messagebox.showinfo'):
            self.app.accion_exportar_matriz_excel()
        self.assertIsNone(re.search(r'[<>:"/\\|?*]',destination.call_args.kwargs['initialfile']))
        with __import__('contextlib').closing(openpyxl.load_workbook(file)) as wb:self.assertIn('Unidad 1: razones / proporciones',wb['Matriz final']['A1'].value)
        self.assertFalse(self.errors)
