"""Visible evaluation tools, readable template actions and responsive side panel."""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from colores import button as sky_button,tabs as sky_tabs
import db,reportes
from widgets import scroll_area,wrap_label,Tooltip
from interfaz import pixel_scale
from grade_cells import PALETTE
from rendimiento import TextBuffer


class EvaluationTools:
    def crear_panel_calificaciones(self):
        page=self.tab_calificar;page.grid_columnconfigure(0,weight=1);page.grid_rowconfigure(1,weight=1)
        bar=ctk.CTkFrame(page,fg_color='transparent');bar.grid(row=0,column=0,sticky='ew',padx=10,pady=8)
        bar.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(bar,text='Calificaciones',font=ctk.CTkFont(size=20,weight='bold')).grid(row=0,column=0,sticky='w',padx=(0,12))
        self.calif_combo_actividad=ctk.CTkComboBox(bar,state='readonly',width=240,height=36,command=self._al_cambiar_actividad_en_calificar)
        self.calif_combo_actividad.grid(row=0,column=1,sticky='ew',padx=6)
        Tooltip(self.calif_combo_actividad,lambda:self.calif_combo_actividad.get())
        self._save_grades=ctk.CTkButton(bar,**sky_button(),text='Guardar notas',height=36,width=130,command=self.accion_guardar_planilla_calificacion_completa)
        self._save_grades.grid(row=0,column=3,padx=(8,0))
        self._tools_toggle=ctk.CTkButton(bar,**sky_button(),text='Herramientas',height=34,width=135,command=self.alternar_herramientas)
        self._tools_toggle.grid(row=0,column=2,padx=6)
        Tooltip(self._tools_toggle,'Evaluación y plantillas Excel')
        self._table_export=ctk.CTkButton(bar,**sky_button(),text='Exportar tabla',height=34,width=125,command=self.exportar_tabla_actual)
        self._table_export.grid(row=0,column=4,padx=(8,0))
        self._grade_bar=bar
        self._competency_label=ctk.CTkLabel(bar,text='Competencia: seleccione una actividad',anchor='w',justify='left',font=ctk.CTkFont(size=16,weight='bold'))
        self._competency_label.grid(row=2,column=0,columnspan=5,sticky='ew',padx=2,pady=(7,0));wrap_label(self._competency_label)
        self.grade_workspace=ctk.CTkFrame(page,fg_color='transparent')
        self.grade_workspace.grid(row=1,column=0,sticky='nsew',padx=8,pady=(0,8))
        self.grade_workspace.grid_rowconfigure(0,weight=1);self.grade_workspace.grid_columnconfigure(0,weight=1)
        self.f_tabla_planilla=ctk.CTkFrame(self.grade_workspace,corner_radius=8)
        self.f_tabla_planilla.grid(row=0,column=0,sticky='nsew')
        self.f_tabla_planilla.grid_columnconfigure(0,weight=1);self.f_tabla_planilla.grid_rowconfigure(1,weight=1)
        host=scroll_area(self.grade_workspace,width=270,auto_hide=True)
        host.container.grid_propagate(False)
        self._evaluation_panel=host;host.grid_columnconfigure(0,weight=1)
        self._tools_open=False;self._tools_resize_job=None
        self._tools_close=ctk.CTkButton(host,**sky_button(),text='Volver a las notas',height=34,command=self.alternar_herramientas)
        self._tools_close.grid(row=0,column=0,sticky='ew',padx=12,pady=8)
        def title(text,row):
            ctk.CTkLabel(host,text=text,anchor='w',font=ctk.CTkFont(size=15,weight='bold')).grid(row=row,column=0,sticky='ew',padx=12,pady=(12,4))
        def button(text,row,callback):
            value=ctk.CTkButton(host,**sky_button(),text=text,height=38,command=callback,font=ctk.CTkFont(size=14))
            value.grid(row=row,column=0,sticky='ew',padx=12,pady=4);return value
        title('Cómo evaluar',1)
        mode_host=ctk.CTkFrame(host,fg_color='transparent');mode_host.grid(row=2,column=0,sticky='ew',padx=12,pady=4);mode_host.grid_columnconfigure(0,weight=1)
        self.calif_combo_modo_inst=ctk.CTkComboBox(mode_host,values=['Nota global','Nota directa','Lista de Cotejo','Rúbrica'],state='readonly',height=36,
            command=self.cambiar_metodo_evaluacion)
        self.calif_combo_modo_inst.set('Nota directa');self.calif_combo_modo_inst.grid(row=0,column=0,sticky='ew')
        self._instrument_status=ctk.CTkLabel(mode_host,text='',justify='left',anchor='w',wraplength=220,font=ctk.CTkFont(size=14))
        self._instrument_status.grid(row=1,column=0,sticky='ew',pady=6);wrap_label(self._instrument_status)
        self.btn_evaluar=button('Ingresar notas',3,self.evaluar_desde_barra)
        templates=ctk.CTkFrame(host,fg_color='transparent');templates.grid(row=4,column=0,sticky='ew',padx=12,pady=4)
        templates.grid_columnconfigure((0,1),weight=1,uniform='plantillas')
        self._templates_group=templates
        self._design_button=ctk.CTkButton(templates,**sky_button(),text='Diseñar',height=36,width=100,command=self.configurar_instrumento,font=ctk.CTkFont(size=14))
        self._design_button.grid(row=0,column=0,sticky='ew',padx=(0,4))
        self._export_button=ctk.CTkButton(templates,**sky_button(),text='Plantilla Excel',height=36,width=110,command=lambda:self.exportar_modelo_actual(self.calif_combo_modo_inst.get()),font=ctk.CTkFont(size=14))
        self._export_button.grid(row=0,column=1,sticky='ew',padx=(4,0))
        Tooltip(self._design_button,'Diseñar o editar el instrumento aquí')
        Tooltip(self._export_button,'Crear y descargar una plantilla para completar en Excel')
        self._summary_export=button('Exportar con resumen por capacidad',5,lambda:self.exportar_tabla_actual(True))
        self._import_button=button('Importar Excel',6,self.accion_importar_rubrica_cotejo_en_calificacion)
        button('Ver actividad e instrumento',7,self.detalles_calificacion)
        title('Actividad',8)
        button('Asistencia de todos',9,self.accion_marcar_asistencia_todos)
        line=ctk.CTkFrame(host,fg_color='transparent');line.grid(row=10,column=0,sticky='ew',padx=12,pady=6);line.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(line,text='Peso relativo',font=ctk.CTkFont(size=14)).grid(row=0,column=0,padx=(0,8))
        self.calif_entry_peso=ctk.CTkEntry(line,width=90,height=36);self.calif_entry_peso.grid(row=0,column=1,sticky='ew')
        Tooltip(self.calif_entry_peso,'1: igual importancia; 2: doble dentro del mismo rubro. El porcentaje se define en Ponderaciones.')
        self.calif_combo_orden=ctk.CTkComboBox(host,values=['Apellidos (A-Z)','Código (Ej. 4A01)','Apellidos (Z-A)','Nombres (A-Z)'],
            state='readonly',height=36,command=lambda _:self.dibujar_planilla_calificacion())
        self.calif_combo_orden.set('Apellidos (A-Z)');self.calif_combo_orden.grid(row=11,column=0,sticky='ew',padx=12,pady=6)
        self._evaluation_steps=ctk.CTkLabel(host,text='',anchor='w',justify='left',font=ctk.CTkFont(size=14),wraplength=220)
        self._evaluation_steps.grid(row=12,column=0,sticky='ew',padx=12,pady=10);wrap_label(self._evaluation_steps)
        legend=ctk.CTkFrame(host,fg_color='transparent');legend.grid(row=13,column=0,sticky='ew',padx=12,pady=8)
        legend.grid_columnconfigure((0,1,2,3),weight=1)
        for col,(letter,(bg,fg)) in enumerate(PALETTE.items()):
            ctk.CTkLabel(legend,text=letter,fg_color=bg,text_color=fg,corner_radius=5,width=40,font=ctk.CTkFont(size=14,weight='bold')).grid(row=0,column=col,padx=2,sticky='ew')
        button('Guía paso a paso',15,lambda:self.abrir_instrucciones('Rúbrica y cotejo paso a paso'))
        self.lbl_detalle_actividad_calificar=ctk.CTkLabel(page,text='')
        self.caja_ref_rubrica=TextBuffer()
        self.planilla_nativa=None
        self.grade_workspace.bind('<Configure>',self._programar_herramientas,add='+')
        self._programar_herramientas()
        self.actualizar_herramientas_evaluacion()

    def _programar_herramientas(self,event=None):
        if getattr(self,'_closing_ui',False):return
        if self._tools_resize_job:self.after_cancel(self._tools_resize_job)
        self._tools_resize_job=self.after(90,self._disponer_herramientas)

    def _disponer_herramientas(self):
        self._tools_resize_job=None
        if getattr(self,'_closing_ui',False):return
        width=self.grade_workspace.winfo_width()/pixel_scale(self)
        panel=self._evaluation_panel.container
        docked=False
        narrow=self._grade_bar.winfo_width()/pixel_scale(self)<800
        state=(docked,narrow,self._tools_open)
        if state==getattr(self,'_grade_layout_state',None):
            if not self._tools_open and panel.winfo_manager():panel.place_forget();panel.grid_forget()
            return
        self._grade_layout_state=state
        if docked:
            panel.place_forget();panel.grid();self._tools_toggle.grid_remove();self._tools_close.grid_remove()
        else:
            panel.grid_forget();self._tools_toggle.grid();self._tools_close.grid()
            if self._tools_open:
                panel.place(relx=1,rely=0,relheight=1,anchor='ne');panel.lift()
            else:panel.place_forget()
        self._tools_toggle.configure(text='Ocultar' if self._tools_open else 'Herramientas')
        if narrow:
            self.calif_combo_actividad.grid(row=1,column=0,columnspan=4,pady=6)
            self._tools_toggle.grid(row=1,column=4,pady=6)
        else:
            self.calif_combo_actividad.grid(row=0,column=1,columnspan=1,pady=0)
            self._tools_toggle.grid(row=0,column=2,pady=0)
        if docked:self._tools_toggle.grid_remove()

    def alternar_herramientas(self):
        self._tools_open=not self._tools_open;self._disponer_herramientas()

    def actualizar_herramientas_evaluacion(self):
        kind=self.calif_combo_modo_inst.get()
        selected=getattr(self,'actividades_creadas_map',{}).get(getattr(self,'id_actividad_calificando',None))
        self._competency_label.configure(text='Competencia: '+selected['competencia_nombre'] if selected else 'Competencia: seleccione una actividad')
        self._save_grades.configure(text=('Guardar cambios' if getattr(self,'_cotejo_pending_rule',None) else 'Guardar observaciones') if kind=='Lista de Cotejo' else 'Guardar notas')
        has_data=bool(getattr(self,'_datos_estudiantes',[]))
        activity=bool(getattr(self,'actividades_creadas_map',{}).get(getattr(self,'id_actividad_calificando',None)))
        loaded=getattr(self,'_loaded_instrument_kind',None)
        ready=loaded==kind and bool(getattr(self,'_loaded_ind_count',0))
        direct=kind in ('Nota directa','Nota global')
        self._instrument_status.configure(text='Una nota se aplica a las capacidades seleccionadas de esta actividad.' if kind=='Nota global' else 'Escriba la nota final de cada capacidad.' if direct else f"{getattr(self,'_loaded_ind_count',0)} criterios · Una respuesta por criterio" if ready else 'Empiece con una plantilla Excel o diseñe el instrumento aquí.')
        self.btn_evaluar.configure(text='Ingresar notas' if direct else 'Evaluar criterios',state='normal' if has_data and (direct or ready) else 'disabled')
        for widget in (self._templates_group,self._import_button):
            if direct:widget.grid_remove()
            else:widget.grid()
        if kind=='Rúbrica' and ready:self._summary_export.grid()
        else:self._summary_export.grid_remove()
        self._design_button.configure(text='Editar' if ready else 'Diseñar',state='normal' if activity else 'disabled')
        self._export_button.configure(state='normal' if activity else 'disabled')
        self._evaluation_steps.configure(text='1. Haga doble clic en una nota.\n2. Escriba de 0 a 20.\n3. Pulse Guardar notas.' if direct else
            'Marque Sí / No con un clic o S / N. Supr deja pendiente. Guarde las observaciones; convertir a nota es opcional.' if kind=='Lista de Cotejo' else
            'Escriba puntos en la tabla. La nota de capacidad se calcula. Pulse Guardar notas para confirmar.')
        self._sincronizar_vistas_evaluacion(ready and not direct)

    def cambiar_metodo_evaluacion(self,value):
        embedded=getattr(self,'_embedded_evaluation',None)
        if embedded and embedded.winfo_exists() and embedded.matrix.editor is not None:
            self.calif_combo_modo_inst.set(embedded.tipo_inst);embedded.matrix.commit_edit()
            if embedded.matrix.editor is not None:return
        self.calif_combo_modo_inst.set(value)
        panel=getattr(self,'_global_grade_panel',None)
        if panel and panel.winfo_exists() and panel.editor is not None and not panel.commit():self.calif_combo_modo_inst.set('Nota global');return
        self._evaluation_view=None
        self.dibujar_planilla_calificacion()
        ready=value in ('Nota directa','Nota global') or (getattr(self,'_loaded_instrument_kind',None)==value and getattr(self,'_loaded_ind_count',0))
        if ready and getattr(self,'edicion_desbloqueada',False) and getattr(self,'id_actividad_calificando',None):self.marcar_planilla_pendiente()

    def configurar_instrumento(self):
        if not self.verificar_permiso_edicion():return
        session=self.id_actividad_calificando
        kind=self.calif_combo_modo_inst.get()
        if not session or kind=='Nota directa':return
        from evaluacion_datos import get_indicators,activity
        from instrument_design import InstrumentEditor
        items=get_indicators(session,self._db_path)
        if items and items[0]['tipo']!=kind:items=[]
        def saved(origins):
            rows=get_indicators(session,self._db_path)
            self.reconciliar_respuestas_pendientes(items,rows)
            self._loaded_instrument_kind=kind;self._loaded_ind_count=len(rows)
            self.actividades_creadas_map[session]=activity(session,self._db_path)
            self.recargar_tabla_actividades_creadas()
            self.calif_combo_modo_inst.set(kind);self.actualizar_herramientas_evaluacion()
            self.lbl_estado.configure(text='Instrumento guardado · Revise la evaluación si cambió sus puntajes.')
        InstrumentEditor(self,session,items,saved,kind=kind)

    def reconciliar_respuestas_pendientes(self,previous,current):
        from instrumentos import rescale_answer
        old={i['id']:i for i in previous};new={i['id']:i for i in current}
        def reconcile(answers):
            return {(s,i):rescale_answer(v,old[i],new[i]) if i in old else v
                    for (s,i),v in answers.items() if i in new}
        self._instrument_pending=reconcile(getattr(self,'_instrument_pending',{}))
        for state in getattr(self,'_undo',[])+getattr(self,'_redo',[]):
            state['answers']=reconcile(state.get('answers',{}))

    def exportar_tabla_actual(self,include_summary=False):
        context=getattr(self,'actividades_creadas_map',{}).get(self.id_actividad_calificando)
        if not context:
            messagebox.showinfo('Seleccione una actividad','Abra la actividad que desea exportar.');return
        if getattr(self.planilla_nativa,'_entry',None):self.planilla_nativa._entry.event_generate('<FocusOut>')
        panel=getattr(self,'_embedded_evaluation',None)
        if panel and panel.winfo_exists() and panel.matrix.editor is not None:
            panel.matrix.commit_edit()
            if panel.matrix.editor is not None:return
        path=self.elegir_destino(title='Exportar la tabla con notas y observaciones',defaultextension='.xlsx',initialfile='Calificaciones.xlsx',filetypes=[('Excel','*.xlsx')])
        if not path:return
        panel=getattr(self,'_global_grade_panel',None)
        if panel and panel.winfo_exists() and panel.editor is not None and not panel.commit():return
        from excel_tablas import export_activity
        from grade_cells import grade_number
        grades={}
        for row in self._filas_planilla():
            for index,cap in enumerate(context['capacidades'],4):grades[(int(row[0]),cap['capacidad_id'])]=grade_number(row[index])
        count=export_activity(path,self.id_actividad_calificando,self._db_path,answers=getattr(self,'_instrument_pending',{}),grades=grades,roster=self._datos_estudiantes,include_summary=include_summary)
        self.archivo_guardado(path,f'Tabla exportada con {count} estudiantes, notas y observaciones. Puede editarla e importarla aquí.')

    def exportar_modelo_actual(self,kind):
        activity=getattr(self,'actividades_creadas_map',{}).get(self.id_actividad_calificando)
        if not activity:
            messagebox.showinfo('Seleccione una actividad','Cree y guarde una actividad antes de descargar su modelo.');return
        from excel_ui import TemplateOptions
        from evaluacion_datos import get_indicators
        import re
        indicators=[i for i in get_indicators(activity['id'],self._db_path) if i['tipo']==kind]
        options=TemplateOptions(self,activity,kind,indicators);self.wait_window(options)
        if options.result is None:return
        title=re.sub(r'[<>:"/\\|?*]','_',activity['titulo_tema']).strip(' .')[:75] or 'Actividad'
        path=self.elegir_destino(title='Guardar plantilla de '+kind,defaultextension='.xlsx',initialfile=f'{"Cotejo" if kind=="Lista de Cotejo" else "Rubrica"}_{title}_{activity["grado"]}{activity["seccion"]}.xlsx',filetypes=[('Excel','*.xlsx')])
        if not path:return
        db.exportar_plantilla_rubrica_o_cotejo_excel(path,self.combo_curso_global.get(),activity['grado'],activity['seccion'],activity['titulo_tema'],
            activity['competencia_nombre'],[(c['capacidad_id'],c['capacidad_nombre'],c['criterio_precisado']) for c in activity['capacidades']],
            kind,db_path=self._db_path,sesion_id=activity['id'],**options.result)
        reportes.decorate_workbook(path,self.insignia_exportacion())
        self.archivo_guardado(path,'Plantilla lista: complete Instrumento y Registro. Los nombres quedan vacíos salvo que elija incluir el alumnado del aula.')

    def _sincronizar_vistas_evaluacion(self,ready):
        if getattr(self,'_closing_ui',False) or not getattr(self,'planilla_nativa',None):return
        if not hasattr(self,'_results_pane') or not self._results_pane.winfo_exists():return
        global_panel=getattr(self,'_global_grade_panel',None)
        global_mode=self.calif_combo_modo_inst.get()=='Nota global'
        if global_panel and global_panel.winfo_exists() and (not global_mode or global_panel.session!=self.id_actividad_calificando):global_panel.grid_remove()
        if global_mode:
            bar=getattr(self,'_criteria_view_bar',None)
            if bar and bar.winfo_exists():bar.grid_remove()
            embedded=getattr(self,'_embedded_evaluation',None)
            if embedded and embedded.winfo_exists():embedded.grid_remove()
            if not global_panel or not global_panel.winfo_exists() or global_panel.session!=self.id_actividad_calificando:
                if global_panel and global_panel.winfo_exists():global_panel.destroy()
                from nota_global_ui import GlobalGradePanel
                global_panel=GlobalGradePanel(self.f_tabla_planilla,self);self._global_grade_panel=global_panel
            else:global_panel.refresh()
            self._results_pane.grid_remove();global_panel.grid(row=1,column=0,columnspan=3,sticky='nsew');self._evaluation_view='global';self._programar_herramientas();return
        if not ready:
            bar=getattr(self,'_criteria_view_bar',None)
            if bar and bar.winfo_exists():bar.grid_remove()
            panel=getattr(self,'_embedded_evaluation',None)
            if panel and panel.winfo_exists():panel.grid_remove()
            self._results_pane.grid();self._evaluation_view='results';self._programar_herramientas();return
        if not hasattr(self,'_criteria_view_bar') or not self._criteria_view_bar.winfo_exists():
            self._criteria_view_bar=ctk.CTkFrame(self.f_tabla_planilla,fg_color='transparent')
            self._criteria_view_bar.grid_columnconfigure(1,weight=1)
            self._criteria_tabs=ctk.CTkSegmentedButton(self._criteria_view_bar,**sky_tabs(),values=['Criterios','Resultados y asistencia'],command=self.cambiar_vista_evaluacion,height=34)
            self._criteria_tabs.grid(row=0,column=0,padx=8,pady=5)
            caption=ctk.CTkLabel(self._criteria_view_bar,text='Puntajes editables · Nota provisional si quedan criterios pendientes',font=ctk.CTkFont(size=13),anchor='w')
            caption.grid(row=0,column=1,sticky='ew',padx=8);wrap_label(caption)
            self._criteria_view_caption=caption
        if self.tabview.get()!='Ingresar Calificativos':return
        self._criteria_view_caption.configure(text='Clic o S/N: marcar · Flechas: moverse · Supr: pendiente' if self.calif_combo_modo_inst.get()=='Lista de Cotejo' else 'Flechas: moverse · F2: editar · Esc: cancelar')
        self._criteria_view_bar.grid(row=0,column=0,columnspan=3,sticky='ew')
        if getattr(self,'_evaluation_view',None) not in ('criteria','results'):self._evaluation_view='criteria'
        self._mostrar_vista_evaluacion()

    def cambiar_vista_evaluacion(self,caption):
        self._evaluation_view='criteria' if caption=='Criterios' else 'results'
        self._mostrar_vista_evaluacion()

    def _mostrar_vista_evaluacion(self,student=None,capacity=None):
        from evaluacion_datos import get_indicators
        from evaluation_panel import EvaluationPanel
        view=self._evaluation_view
        self._criteria_tabs.set('Criterios' if view=='criteria' else 'Resultados y asistencia')
        panel=getattr(self,'_embedded_evaluation',None)
        if view=='criteria':
            items=get_indicators(self.id_actividad_calificando,self._db_path)
            signature=repr(items)
            if not panel or not panel.winfo_exists() or getattr(self,'_embedded_signature',None)!=(self.id_actividad_calificando,signature):
                if panel and panel.winfo_exists():panel.destroy()
                activity=self.actividades_creadas_map[self.id_actividad_calificando]
                panel=EvaluationPanel(self.f_tabla_planilla,self,activity,self._datos_estudiantes,items)
                self._embedded_evaluation=panel;self._embedded_signature=(self.id_actividad_calificando,signature)
            else:panel.reload_from_root()
            self._results_pane.grid_remove();panel.grid(row=1,column=0,columnspan=3,sticky='nsew')
            panel._queue_layout()
            if student is not None:panel.select_student(student,capacity)
        else:
            if panel and panel.winfo_exists():panel.grid_remove();panel._queue_layout()
            self._results_pane.grid()
        self._programar_herramientas()

    def abrir_evaluacion_por_criterios(self,student=None,capacity=None):
        kind=self.calif_combo_modo_inst.get()
        if kind=='Nota directa':return
        if getattr(self,'_loaded_instrument_kind',None)!=kind or not getattr(self,'_loaded_ind_count',0):
            self.lbl_estado.configure(text='Descargue una plantilla Excel o diseñe los criterios para esta actividad.');return
        self._evaluation_view='criteria';self._tools_open=False
        self._mostrar_vista_evaluacion(student,capacity)

    def recargar_evaluacion_guardada(self):
        global_panel=getattr(self,'_global_grade_panel',None)
        if global_panel and global_panel.winfo_exists():global_panel.refresh()
        panel=getattr(self,'_embedded_evaluation',None)
        if panel and panel.winfo_exists():panel.reload_from_root(saved=True)

