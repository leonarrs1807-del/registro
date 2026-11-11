"""Direct grades, editable reuse topics, and fixed student columns at reduced widths."""
import os,unittest
from types import SimpleNamespace
from unittest.mock import patch
import customtkinter as ctk
import db,biblioteca
from evaluacion_datos import get_answers,activity
from tests import test_gui as fixtures


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requiere pantalla o Xvfb')
class RubricWorkflowTests(unittest.TestCase):
    setUp=fixtures.DesktopTests.setUp

    def panel(self):
        self.app.edicion_desbloqueada=True
        self.other=db.agregar_estudiante('Luis','Segundo','3°','A')
        self.ids=db.guardar_indicadores_instrumento_sesion(self.session,'Rúbrica',[(self.cap,'Explica',10),(self.cap,'Comprueba',10)])
        self.app.recargar_tabla_actividades_creadas();self.app.abrir_actividad_en_pestana_calificar(self.session)
        panel=self.app._embedded_evaluation;panel._change_view('Individual');self.app.update();return panel

    def test_direct_entry_tab_student_change_save_and_undo_keep_correct_student(self):
        panel=self.panel();grid=panel.grid_view;first,second=self.ids
        def descendants(widget):
            for child in widget.winfo_children():yield child;yield from descendants(child)
        self.assertFalse(any(isinstance(w,ctk.CTkRadioButton) for w in descendants(grid)))
        self.app.geometry('1024x740');self.app.after(250,self.app.quit);self.app.mainloop()
        grid.content.viewport.xview_moveto(1);self.app.update_idletasks()
        rightmost=grid.cells[first,'AD'];viewport=grid.content.viewport
        self.assertLessEqual(rightmost.winfo_rootx()+rightmost.winfo_width(),viewport.winfo_rootx()+viewport.winfo_width()+2)
        grid.numeric_entries[first].insert(0,'8,25');grid._advance_entry(first)
        self.assertEqual(panel.answers[self.student,first],'8.25')
        grid.numeric_entries[second].insert(0,'0');panel.select_student(self.other)
        self.assertEqual(panel.answers[self.student,second],'0');self.assertEqual(grid.numeric_entries[second].get(),'')
        grid.numeric_entries[first].insert(0,'6,5')
        with patch('tkinter.messagebox.showinfo'):self.app.accion_guardar_planilla_calificacion_completa()
        saved=get_answers(self.session,db.DB_PATH)
        self.assertEqual(saved[self.other,first],'6.5');self.assertEqual(saved[self.student,first],'8.25')
        panel=self.app._embedded_evaluation;panel._change_view('Individual');panel.select_student(self.other)
        field=panel.grid_view.numeric_entries[first];field.delete(0,'end');field.insert(0,'7')
        self.app.deshacer_planilla();self.assertEqual(panel.answers[self.other,first],'6.5')
        self.app.deshacer_planilla(True);self.assertEqual(panel.answers[self.other,first],'7')
        self.assertFalse(self.errors)

    def test_invalid_direct_entry_keeps_student_and_pending_is_not_zero(self):
        panel=self.panel();first=self.ids[0];grid=panel.grid_view;entry=grid.numeric_entries[first]
        entry.insert(0,'11')
        with patch('tkinter.messagebox.showwarning') as warning:
            panel.select_student(self.other);warning.assert_called_once()
        self.assertEqual(panel.current_student,self.student);self.assertEqual(entry.get(),'11')
        self.assertNotIn((self.student,first),panel.answers)
        entry.delete(0,'end');entry.insert(0,'0');grid._focus_out(first)
        self.assertEqual(panel.answers[self.student,first],'0')
        entry.delete(0,'end');grid._focus_out(first)
        self.assertIsNone(panel.answers[self.student,first]);self.assertFalse(self.errors)

    def test_fixed_student_area_shrinks_without_gap_or_font_changes(self):
        panel=self.panel();panel._change_view('Grupo');self.app.update();matrix=panel.matrix
        fonts=[matrix.name_header.itemcget(i,'font') for i in matrix.name_header.find_all() if matrix.name_header.type(i)=='text']
        before=matrix.identity_host.winfo_width();matrix._start_resize(SimpleNamespace(x_root=600),'name')
        matrix._resize_identity(SimpleNamespace(x_root=300));matrix._finish_resize()
        self.app.after(250,self.app.quit);self.app.mainloop()
        width=sum(matrix.identity.column(c,'width') for c in ('code','name'))
        self.assertLess(matrix.identity_host.winfo_width(),before)
        self.assertLessEqual(abs(matrix.identity_host.winfo_width()-width),2)
        self.assertLessEqual(abs(matrix.name_header.winfo_width()-width),2)
        self.assertEqual(fonts,[matrix.name_header.itemcget(i,'font') for i in matrix.name_header.find_all() if matrix.name_header.type(i)=='text'])
        self.assertEqual(matrix.identity.item(str(self.student),'values')[1],'Prueba, Ana');self.assertFalse(self.errors)

    def test_reuse_dialog_keeps_custom_topic_and_table_aligns_descriptors(self):
        panel=self.panel();model=biblioteca.from_session(self.session,db.DB_PATH)
        from biblioteca_ui import ApplyModelDialog
        dialog=ApplyModelDialog(self.app,model);dialog.topic.set('Clase con tema nuevo');dialog.preview()
        self.assertEqual(dialog.topic.get(),'Clase con tema nuevo')
        table=dialog.detail;self.assertEqual(len(table.headers),7);self.assertEqual(len(table.cells),14)
        self.assertEqual(table.cells[1,1].cget('text'),'Explica');self.assertEqual(table.cells[2,1].cget('text'),'Comprueba')
        self.assertEqual(table.cells[1,3].cget('text'),model['criterios'][0]['descriptores']['C'])
        from grade_cells import PALETTE
        self.assertEqual(table.cells[1,3].master.cget('fg_color'),PALETTE['C'][0])
        dialog.apply();self.app.update()
        self.assertEqual(activity(self.app.id_actividad_calificando,db.DB_PATH)['titulo_tema'],'Clase con tema nuevo')
        self.assertFalse(self.errors)

    def test_excel_preview_renames_only_on_confirm_and_keeps_tabular_view(self):
        import app_storage
        from instrument_design import InstrumentPreview
        source=app_storage.data_dir()/'tema-reutilizado.xlsx'
        db.exportar_plantilla_rubrica_o_cotejo_excel(str(source),self.course_name,'3°','A','Prueba','Competencia',
            [(self.cap,'Capacidad','Explica')],'Rúbrica',sesion_id=self.session,formato=3)
        def decide(confirm):
            for widget in self.app.winfo_children():
                if isinstance(widget,InstrumentPreview) and widget.ready:
                    self.assertEqual(len(widget.instrument_grid.headers),7)
                    widget.topic.set('Tema importado editable')
                    if confirm:widget.confirm()
                    else:widget.destroy()
                    return
            self.app.after(40,lambda:decide(confirm))
        self.app.after(40,lambda:decide(False))
        self.assertIsNone(self.app._importar_con_vista_previa(db.importar_rubrica_o_cotejo_desde_excel,self.session,str(source),'3°','A'))
        self.assertEqual(activity(self.session,db.DB_PATH)['titulo_tema'],'Prueba')
        self.app.after(40,lambda:decide(True))
        self.app._importar_con_vista_previa(db.importar_rubrica_o_cotejo_desde_excel,self.session,str(source),'3°','A')
        self.assertEqual(activity(self.session,db.DB_PATH)['titulo_tema'],'Tema importado editable');self.assertFalse(self.errors)
