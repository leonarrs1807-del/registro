"""Visible evaluation tools, readable template actions and responsive side panel."""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
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
        self._save_grades=ctk.CTkButton(bar,text='Guardar notas',height=36,width=130,command=self.accion_guardar_planilla_calificacion_completa)
        self._save_grades.grid(row=0,column=2,padx=(8,0))
        self._tools_toggle=ctk.CTkButton(bar,text='Evaluación y plantillas',height=34,width=200,command=self.alternar_herramientas)
        self._tools_toggle.grid(row=1,column=0,columnspan=3,sticky='w',pady=(8,0))
        self._grade_bar=bar
        self.grade_workspace=ctk.CTkFrame(page,fg_color='transparent')
        self.grade_workspace.grid(row=1,column=0,sticky='nsew',padx=8,pady=(0,8))
        self.grade_workspace.grid_rowconfigure(0,weight=1);self.grade_workspace.grid_columnconfigure(0,weight=1)
        self.f_tabla_planilla=ctk.CTkFrame(self.grade_workspace,corner_radius=8)
        self.f_tabla_planilla.grid(row=0,column=0,sticky='nsew')
        self.f_tabla_planilla.grid_columnconfigure(0,weight=1);self.f_tabla_planilla.grid_rowconfigure(1,weight=1)
        host=scroll_area(self.grade_workspace,width=270,auto_hide=True)
        host.container.grid(row=0,column=1,sticky='ns',padx=(10,0));host.container.grid_propagate(False)
        self._evaluation_panel=host;host.grid_columnconfigure(0,weight=1)
        self._tools_open=False;self._tools_resize_job=None
        self._tools_close=ctk.CTkButton(host,text='Volver a las notas',height=34,command=self.alternar_herramientas)
        self._tools_close.grid(row=0,column=0,sticky='ew',padx=12,pady=8)
        def title(text,row):
            ctk.CTkLabel(host,text=text,anchor='w',font=ctk.CTkFont(size=15,weight='bold')).grid(row=row,column=0,sticky='ew',padx=12,pady=(12,4))
        def button(text,row,callback):
            value=ctk.CTkButton(host,text=text,height=38,command=callback,font=ctk.CTkFont(size=14))
            value.grid(row=row,column=0,sticky='ew',padx=12,pady=4);return value
        title('Cómo evaluar',1)
        mode_host=ctk.CTkFrame(host,fg_color='transparent');mode_host.grid(row=2,column=0,sticky='ew',padx=12,pady=4);mode_host.grid_columnconfigure(0,weight=1)
        self.calif_combo_modo_inst=ctk.CTkComboBox(mode_host,values=['Nota directa','Lista de Cotejo','Rúbrica'],state='readonly',height=36,
            command=self.cambiar_metodo_evaluacion)
        self.calif_combo_modo_inst.set('Nota directa');self.calif_combo_modo_inst.grid(row=0,column=0,sticky='ew')
        self._instrument_status=ctk.CTkLabel(mode_host,text='',justify='left',anchor='w',wraplength=220,font=ctk.CTkFont(size=14))
        self._instrument_status.grid(row=1,column=0,sticky='ew',pady=6);wrap_label(self._instrument_status)
        self.btn_evaluar=button('Ingresar notas',3,self.evaluar_desde_barra)
        self._design_button=button('Diseñar instrumento',4,self.configurar_instrumento)
        self._export_button=button('Descargar plantilla Excel',5,lambda:self.exportar_modelo_actual(self.calif_combo_modo_inst.get()))
        self._import_button=button('Importar evaluación Excel',6,self.accion_importar_rubrica_cotejo_en_calificacion)
        button('Ver actividad e instrumento',7,self.detalles_calificacion)
        title('Actividad',8)
        button('Asistencia de todos',9,self.accion_marcar_asistencia_todos)
        line=ctk.CTkFrame(host,fg_color='transparent');line.grid(row=10,column=0,sticky='ew',padx=12,pady=6);line.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(line,text='Peso',font=ctk.CTkFont(size=14)).grid(row=0,column=0,padx=(0,8))
        self.calif_entry_peso=ctk.CTkEntry(line,width=90,height=36);self.calif_entry_peso.grid(row=0,column=1,sticky='ew')
        self.calif_combo_orden=ctk.CTkComboBox(host,values=['Apellidos (A-Z)','Código (Ej. 4A01)','Apellidos (Z-A)','Nombres (A-Z)'],
            state='readonly',height=36,command=lambda _:self.dibujar_planilla_calificacion())
        self.calif_combo_orden.set('Apellidos (A-Z)');self.calif_combo_orden.grid(row=11,column=0,sticky='ew',padx=12,pady=6)
        self._evaluation_steps=ctk.CTkLabel(host,text='',anchor='w',justify='left',font=ctk.CTkFont(size=14),wraplength=220)
        self._evaluation_steps.grid(row=12,column=0,sticky='ew',padx=12,pady=10);wrap_label(self._evaluation_steps)
        legend=ctk.CTkFrame(host,fg_color='transparent');legend.grid(row=13,column=0,sticky='ew',padx=12,pady=8)
        legend.grid_columnconfigure((0,1,2,3),weight=1)
        for col,(letter,(bg,fg)) in enumerate(PALETTE.items()):
            ctk.CTkLabel(legend,text=letter,fg_color=bg,text_color=fg,corner_radius=5,width=40,font=ctk.CTkFont(size=14,weight='bold')).grid(row=0,column=col,padx=2,sticky='ew')
        button('Configuración de la escala',14,lambda:self.abrir_configuracion('General'))
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
        docked=width>=1080
        narrow=self._grade_bar.winfo_width()/pixel_scale(self)<650
        state=(docked,narrow,self._tools_open)
        if state==getattr(self,'_grade_layout_state',None):return
        self._grade_layout_state=state
        if docked:
            panel.place_forget();panel.grid();self._tools_toggle.grid_remove();self._tools_close.grid_remove()
        else:
            panel.grid_remove();self._tools_toggle.grid();self._tools_close.grid()
            if self._tools_open:
                panel.place(relx=1,rely=0,relheight=1,anchor='ne');panel.lift()
            else:panel.place_forget()
        self._tools_toggle.configure(text='Ocultar herramientas' if self._tools_open else 'Evaluación y plantillas')
        if narrow:self.calif_combo_actividad.grid(row=1,column=0,columnspan=3,pady=6);self._tools_toggle.grid_configure(row=2)
        else:self.calif_combo_actividad.grid(row=0,column=1,columnspan=1,pady=0);self._tools_toggle.grid_configure(row=1)
        if docked:self._tools_toggle.grid_remove()

    def alternar_herramientas(self):
        self._tools_open=not self._tools_open;self._disponer_herramientas()

    def actualizar_herramientas_evaluacion(self):
        kind=self.calif_combo_modo_inst.get()
        has_data=bool(getattr(self,'_datos_estudiantes',[]))
        activity=bool(getattr(self,'actividades_creadas_map',{}).get(getattr(self,'id_actividad_calificando',None)))
        loaded=getattr(self,'_loaded_instrument_kind',None)
        ready=loaded==kind and bool(getattr(self,'_loaded_ind_count',0))
        direct=kind=='Nota directa'
        self._instrument_status.configure(text='Escriba la nota final de cada capacidad.' if direct else f"{getattr(self,'_loaded_ind_count',0)} criterios listos" if ready else 'Diseñe los criterios y niveles para esta actividad.')
        self.btn_evaluar.configure(text='Ingresar notas' if direct else 'Evaluar estudiantes',state='normal' if has_data and (direct or ready) else 'disabled')
        for widget in (self._design_button,self._export_button,self._import_button):
            if direct:widget.grid_remove()
            else:widget.grid()
        self._design_button.configure(text='Editar instrumento' if ready else 'Diseñar instrumento',state='normal' if activity else 'disabled')
        self._export_button.configure(state='normal' if ready else 'disabled')
        self._evaluation_steps.configure(text='1. Haga doble clic en una nota.\n2. Escriba de 0 a 20.\n3. Pulse Guardar notas.' if direct else
            '1. Defina criterios y puntajes.\n2. Evalúe aquí o use Excel.\n3. Aplique a la planilla.\n4. Pulse Guardar notas.')

    def cambiar_metodo_evaluacion(self,value):
        self.dibujar_planilla_calificacion()
        if getattr(self,'edicion_desbloqueada',False) and getattr(self,'id_actividad_calificando',None):self.marcar_planilla_pendiente()

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

    def exportar_modelo_actual(self,kind):
        activity=getattr(self,'actividades_creadas_map',{}).get(self.id_actividad_calificando)
        if not activity:
            messagebox.showinfo('Seleccione una actividad','Cree y guarde una actividad antes de descargar su modelo.');return
        path=self.elegir_destino(title='Guardar modelo de '+kind,defaultextension='.xlsx',initialfile=f'Modelo_{kind}.xlsx',filetypes=[('Excel','*.xlsx')])
        if not path:return
        db.exportar_plantilla_rubrica_o_cotejo_excel(path,self.combo_curso_global.get(),activity['grado'],activity['seccion'],activity['titulo_tema'],
            activity['competencia_nombre'],[(c['capacidad_id'],c['capacidad_nombre'],c['criterio_precisado']) for c in activity['capacidades']],
            kind,db_path=self._db_path,sesion_id=activity['id'])
        reportes.decorate_workbook(path,self.insignia_exportacion())
        self.archivo_guardado(path,'Modelo listo. La hoja Instrucciones explica cómo completarlo e importarlo.')

