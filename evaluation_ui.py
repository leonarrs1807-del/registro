"""Visible evaluation tools, readable template actions and responsive side panel."""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import db,reportes
from widgets import scroll_area,wrap_label,Tooltip
from interfaz import pixel_scale
from grade_cells import PALETTE


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
            command=lambda _:self.dibujar_planilla_calificacion())
        self.calif_combo_modo_inst.set('Nota directa');self.calif_combo_modo_inst.grid(row=0,column=0,sticky='ew')
        self._instrument_status=ctk.CTkLabel(mode_host,text='',justify='left',anchor='w',wraplength=220,font=ctk.CTkFont(size=14))
        self._instrument_status.grid(row=1,column=0,sticky='ew',pady=6);wrap_label(self._instrument_status)
        self.btn_evaluar=button('Ingresar notas',3,self.evaluar_desde_barra)
        title('Plantillas Excel',4)
        button('Modelo de rúbrica',5,lambda:self.exportar_modelo_actual('Rúbrica'))
        button('Modelo de cotejo',6,lambda:self.exportar_modelo_actual('Lista de Cotejo'))
        button('Importar instrumento',7,self.accion_importar_rubrica_cotejo_en_calificacion)
        button('Ver criterios y detalles',8,self.detalles_calificacion)
        title('Actividad',9)
        button('Asistencia de todos',10,self.accion_marcar_asistencia_todos)
        line=ctk.CTkFrame(host,fg_color='transparent');line.grid(row=11,column=0,sticky='ew',padx=12,pady=6);line.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(line,text='Peso',font=ctk.CTkFont(size=14)).grid(row=0,column=0,padx=(0,8))
        self.calif_entry_peso=ctk.CTkEntry(line,width=90,height=36);self.calif_entry_peso.grid(row=0,column=1,sticky='ew')
        self.calif_combo_orden=ctk.CTkComboBox(host,values=['Apellidos (A-Z)','Código (Ej. 4A01)','Apellidos (Z-A)','Nombres (A-Z)'],
            state='readonly',height=36,command=lambda _:self.dibujar_planilla_calificacion())
        self.calif_combo_orden.set('Apellidos (A-Z)');self.calif_combo_orden.grid(row=12,column=0,sticky='ew',padx=12,pady=6)
        self._evaluation_steps=ctk.CTkLabel(host,text='',anchor='w',justify='left',font=ctk.CTkFont(size=14),wraplength=220)
        self._evaluation_steps.grid(row=13,column=0,sticky='ew',padx=12,pady=10);wrap_label(self._evaluation_steps)
        legend=ctk.CTkFrame(host,fg_color='transparent');legend.grid(row=14,column=0,sticky='ew',padx=12,pady=8)
        legend.grid_columnconfigure((0,1,2,3),weight=1)
        for col,(letter,(bg,fg)) in enumerate(PALETTE.items()):
            ctk.CTkLabel(legend,text=letter,fg_color=bg,text_color=fg,corner_radius=5,width=40,font=ctk.CTkFont(size=14,weight='bold')).grid(row=0,column=col,padx=2,sticky='ew')
        button('Configurar niveles',15,self.configurar_escala)
        button('Guía paso a paso',16,lambda:self.abrir_instrucciones('Rúbrica y cotejo paso a paso'))
        self.lbl_detalle_actividad_calificar=ctk.CTkLabel(page,text='')
        self.caja_ref_rubrica=ctk.CTkTextbox(page)
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
        mode=self.calif_combo_modo_inst.get()
        has_data=bool(getattr(self,'_datos_estudiantes',[]))
        kind='Rúbrica' if 'Rúbrica' in mode else 'Lista de Cotejo' if 'Cotejo' in mode else 'Nota directa'
        loaded=getattr(self,'_loaded_instrument_kind',None)
        mismatch=loaded and kind!='Nota directa' and loaded!=kind
        status=f"{getattr(self,'_loaded_ind_count',0)} indicadores de {loaded}" if loaded else 'Sin instrumento importado'
        if mismatch:status+=f'. Importe un modelo de {kind} para usar esta opción.'
        self._instrument_status.configure(text=status)
        self.btn_evaluar.configure(text='Evaluar rúbrica' if kind=='Rúbrica' else 'Evaluar cotejo' if kind=='Lista de Cotejo' else 'Ingresar notas',state='normal' if has_data and not mismatch else 'disabled')
        if kind=='Nota directa':text='1. Haga doble clic en una nota.\n2. Escriba un valor de 0 a 20.\n3. Pulse Guardar notas.'
        else:text='1. Descargue un modelo Excel.\n2. Personalice los indicadores.\n3. Importe y revise las notas.\n4. O evalúe aquí y guarde.'
        self._evaluation_steps.configure(text=text)

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

