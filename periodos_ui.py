"""Visible academic context and safe, dated document recovery."""
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk,messagebox
import customtkinter as ctk
import app_storage as storage
import periodos
from widgets import SafeDialog,wrap_label,scroll_area,polish_dialog,Tooltip
from colores import button


class AcademicTools:
    def iniciar_contexto_academico(self):
        strip=ctk.CTkFrame(self.barra_top,fg_color=('#eff9ff','#102c40'),corner_radius=6)
        strip.grid(row=1,column=0,columnspan=9,sticky='ew',padx=6,pady=(0,6));strip.grid_columnconfigure(3,weight=1)
        self.school_choice=ctk.CTkComboBox(strip,values=[],state='readonly',width=200,height=30,fg_color=('#ffffff','#1e293b'),border_color=('#cbd5e1','#475569'),border_width=1,button_color=('#e0f2fe','#075985'),font=ctk.CTkFont(size=14),command=self.cambiar_colegio)
        self.school_choice.grid(row=0,column=0,sticky='ew',padx=5,pady=5)
        Tooltip(self.school_choice,lambda:self.school_choice.get())
        self.period_button=ctk.CTkButton(strip,text='',height=30,width=190,**button(),command=self.seleccionar_periodo)
        self.period_button.grid(row=0,column=1,padx=6,pady=5)
        Tooltip(self.period_button,lambda:periodos.info(self._db_path)['label'])
        self.period_state=ctk.CTkLabel(strip,text='',font=ctk.CTkFont(size=13,weight='bold'))
        self.period_state.grid(row=0,column=2,padx=6)
        self.unit_filter=ctk.CTkComboBox(strip,values=['Todas las unidades'],state='readonly',height=30,width=220,fg_color=('#ffffff','#1e293b'),border_color=('#cbd5e1','#475569'),border_width=1,button_color=('#e0f2fe','#075985'),font=ctk.CTkFont(size=14),command=self.filtrar_unidad)
        self.unit_filter.set('Todas las unidades');self.unit_filter.grid(row=0,column=3,sticky='ew',padx=4,pady=5)
        ctk.CTkButton(strip,text='Organizar',width=86,height=30,**button(),command=self.gestionar_unidades).grid(row=0,column=4,padx=6)
        self.actualizar_contexto_academico()

    def actualizar_contexto_academico(self):
        if not hasattr(self,'period_button'):return
        import colegios
        current=periodos.info(self._db_path)
        schools=colegios.catalog(storage.data_dir(),self._db_path)
        self._school_id=current['school_id'];self._school_choices=colegios.labels(schools)
        self.school_choice.configure(values=list(self._school_choices))
        self.school_choice.set(next((k for k,r in self._school_choices.items() if r['id']==self._school_id),''))
        self.period_button.configure(text=current['label']+' ▾')
        self.period_state.configure(text='Cerrado' if current['closed'] else 'Abierto',text_color=('#9a3412','#fdba74') if current['closed'] else ('#047857','#6ee7b7'))
        units=periodos.units(self._db_path)
        self._unit_labels={f"{n+1:02} · {u['nombre']}":u['id'] for n,u in enumerate(units)}
        values=['Todas las unidades','Sin unidad']+list(self._unit_labels)
        self.unit_filter.configure(values=values)
        if self.unit_filter.get() not in values:self.unit_filter.set(values[0])
        if hasattr(self,'crear_combo_unidad'):
            values=['Sin unidad']+list(self._unit_labels);old=self.crear_combo_unidad.get()
            self.crear_combo_unidad.configure(values=values)
            if old not in values:self.crear_combo_unidad.set('Sin unidad')

    def filtrar_unidad(self,value=None):
        if not self.confirmar_descartar():
            self.unit_filter.set(getattr(self,'_last_unit_filter','Todas las unidades'));return
        self._last_unit_filter=self.unit_filter.get()
        if self._last_unit_filter in self._unit_labels:self.crear_combo_unidad.set(self._last_unit_filter)
        self.recargar_tabla_actividades_creadas()
        self.recargar_matriz_completa()

    def sesiones_unidad(self,sessions):
        selection=self.unit_filter.get() if hasattr(self,'unit_filter') else 'Todas las unidades'
        if selection=='Todas las unidades':return sessions
        target=getattr(self,'_unit_labels',{}).get(selection)
        return [s for s in sessions if s.get('unidad_id')==target]

    def gestionar_unidades(self):
        from organizacion_ui import OrganizationManager
        return OrganizationManager(self,units_only=True)

    def seleccionar_periodo(self):
        from organizacion_ui import OrganizationManager
        return OrganizationManager(self)

    def cambiar_colegio(self,value):
        row=getattr(self,'_school_choices',{}).get(value)
        if row is None or row['id']==self._school_id:return
        if not self.confirmar_descartar(include_points=True):self.actualizar_contexto_academico();return
        path=row['records'][-1]['path'];storage.activate_period(path);self._reiniciar(path)

    def alcance_unidad(self):
        choice=self.unit_filter.get() if hasattr(self,'unit_filter') else 'Todas las unidades'
        return 'all' if choice=='Todas las unidades' else getattr(self,'_unit_labels',{}).get(choice)

    def nombre_alcance(self):
        return self.unit_filter.get() if hasattr(self,'unit_filter') else 'Todas las unidades'

    def abrir_historial_archivos(self):
        window=SafeDialog(self);window.title('Recuperar un registro por fecha');window.geometry('850x560');window.transient(self)
        window.grid_columnconfigure(0,weight=1);window.grid_rowconfigure(2,weight=1)
        ctk.CTkLabel(window,text='Abre una copia de una fecha anterior',font=ctk.CTkFont(size=21,weight='bold')).grid(row=0,column=0,sticky='w',padx=18,pady=14)
        hint=ctk.CTkLabel(window,text='Se creará un documento independiente. Tu registro actual y el respaldo original se conservarán.',anchor='w',justify='left');hint.grid(row=1,column=0,sticky='ew',padx=18);wrap_label(hint)
        frame=ctk.CTkFrame(window);frame.grid(row=2,column=0,sticky='nsew',padx=18,pady=12);frame.grid_columnconfigure(0,weight=1);frame.grid_rowconfigure(0,weight=1)
        tree=ttk.Treeview(frame,columns=('fecha','motivo','tamano'),show='headings',selectmode='browse')
        for key,title,width in [('fecha','Fecha y hora',175),('motivo','Archivo / motivo',460),('tamano','Tamaño',90)]:tree.heading(key,text=title);tree.column(key,width=width)
        tree.grid(row=0,column=0,sticky='nsew');sy=ttk.Scrollbar(frame,command=tree.yview);sy.grid(row=0,column=1,sticky='ns');tree.configure(yscrollcommand=sy.set)
        items=periodos.snapshots(self._db_path)
        for n,row in enumerate(items):tree.insert('','end',iid=str(n),values=(datetime.fromtimestamp(row['date']).strftime('%d/%m/%Y %H:%M'),row['path'].stem,f"{row['size']/1024:.0f} KB"))
        def open_copy():
            if not tree.selection() or not self.confirmar_descartar(include_points=True):return
            try:
                target=periodos.open_snapshot(items[int(tree.selection()[0])]['path'],storage.data_dir());storage.activate_period(target);self._reiniciar(target)
            except Exception as exc:messagebox.showerror('Recuperación',str(exc),parent=window)
        ctk.CTkButton(window,text='Abrir como otro documento',**button(),command=open_copy).grid(row=3,column=0,sticky='e',padx=18,pady=14)
        polish_dialog(window,self,850,560)
