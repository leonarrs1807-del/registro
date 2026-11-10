"""Visible academic context and safe, dated document recovery."""
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk,messagebox
import customtkinter as ctk
import app_storage as storage
import periodos
from widgets import SafeDialog,wrap_label,scroll_area,polish_dialog
from colores import button


class AcademicTools:
    def iniciar_contexto_academico(self):
        strip=ctk.CTkFrame(self.barra_top,fg_color=('#eff9ff','#102c40'),corner_radius=6)
        strip.grid(row=1,column=0,columnspan=9,sticky='ew',padx=6,pady=(0,6));strip.grid_columnconfigure(3,weight=1)
        self.period_button=ctk.CTkButton(strip,text='',height=30,width=260,**button(),command=self.seleccionar_periodo)
        self.period_button.grid(row=0,column=0,padx=6,pady=5)
        self.period_state=ctk.CTkLabel(strip,text='',font=ctk.CTkFont(size=13,weight='bold'))
        self.period_state.grid(row=0,column=1,padx=6)
        ctk.CTkLabel(strip,text='Unidad',font=ctk.CTkFont(size=13)).grid(row=0,column=2,padx=(12,4))
        self.unit_filter=ctk.CTkComboBox(strip,values=['Todas las unidades'],state='readonly',height=30,width=220,fg_color=('#ffffff','#1e293b'),border_color=('#cbd5e1','#475569'),border_width=1,button_color=('#e0f2fe','#075985'),font=ctk.CTkFont(size=14),command=self.filtrar_unidad)
        self.unit_filter.set('Todas las unidades');self.unit_filter.grid(row=0,column=3,sticky='ew',padx=4,pady=5)
        ctk.CTkButton(strip,text='Gestionar',width=86,height=30,**button(),command=self.gestionar_unidades).grid(row=0,column=4,padx=6)
        self.actualizar_contexto_academico()

    def actualizar_contexto_academico(self):
        if not hasattr(self,'period_button'):return
        current=periodos.info(self._db_path)
        self.period_button.configure(text=current['label']+' ▾')
        self.period_state.configure(text='Cerrado' if current['closed'] else 'Abierto',text_color=('#9a3412','#fdba74') if current['closed'] else ('#047857','#6ee7b7'))
        course=self.obtener_curso_activo_id()
        units=periodos.units(self._db_path,course,self.combo_grado_global.get(),self.combo_seccion_global.get()) if course else []
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

    def sesiones_unidad(self,sessions):
        selection=self.unit_filter.get() if hasattr(self,'unit_filter') else 'Todas las unidades'
        if selection=='Todas las unidades':return sessions
        target=getattr(self,'_unit_labels',{}).get(selection)
        return [s for s in sessions if s.get('unidad_id')==target]

    def gestionar_unidades(self):
        course=self.obtener_curso_activo_id();grade=self.combo_grado_global.get();section=self.combo_seccion_global.get()
        window=SafeDialog(self);window.title('Unidades del periodo');window.geometry('700x580');window.transient(self)
        window.grid_columnconfigure(0,weight=1);window.grid_rowconfigure(1,weight=1)
        title=ctk.CTkLabel(window,text=periodos.info(self._db_path)['label']+f' · {grade} {section}',font=ctk.CTkFont(size=18,weight='bold'))
        title.grid(row=0,column=0,sticky='ew',padx=18,pady=14);wrap_label(title)
        area=scroll_area(window,auto_hide=True);area.grid(row=1,column=0,sticky='nsew',padx=16);area.grid_columnconfigure(0,weight=1)
        existing=periodos.units(self._db_path,course,grade,section)
        choices={'Nueva unidad':None,**{u['nombre']:u for u in existing}}
        combo=ctk.CTkComboBox(area,values=list(choices),state='readonly');combo.grid(row=0,column=0,sticky='ew',pady=6)
        entries={}
        for n,(key,label) in enumerate([('nombre','Nombre de la unidad'),('proposito','Propósito'),('inicio','Inicio (AAAA-MM-DD, opcional)'),('fin','Fin (AAAA-MM-DD, opcional)')]):
            ctk.CTkLabel(area,text=label,anchor='w').grid(row=1+n*2,column=0,sticky='ew',pady=(8,2))
            entries[key]=ctk.CTkEntry(area,height=36);entries[key].grid(row=2+n*2,column=0,sticky='ew')
        def choose(value):
            row=choices[value] or {}
            for key,entry in entries.items():entry.delete(0,'end');entry.insert(0,row.get(key,''))
        combo.configure(command=choose);combo.set('Nueva unidad')
        def save():
            if not self.verificar_permiso_edicion():return
            try:
                row=choices[combo.get()]
                periodos.save_unit(self._db_path,course,grade,section,*(entries[k].get() for k in ('nombre','proposito','inicio','fin')),identity=row['id'] if row else None)
                self.actualizar_contexto_academico();self.recargar_tabla_actividades_creadas();window.destroy()
            except Exception as exc:messagebox.showerror('Unidad',str(exc),parent=window)
        ctk.CTkButton(window,text='Guardar unidad',**button(),height=38,command=save).grid(row=2,column=0,padx=18,pady=18,sticky='e')
        polish_dialog(window,self,700,580)

    def seleccionar_periodo(self):
        window=SafeDialog(self);window.title('Año escolar y periodos');window.geometry('830x650');window.transient(self)
        window.grid_columnconfigure(0,weight=1);window.grid_rowconfigure(1,weight=1)
        title=ctk.CTkLabel(window,text='Organiza tu año escolar',font=ctk.CTkFont(size=22,weight='bold'))
        title.grid(row=0,column=0,sticky='w',padx=20,pady=14)
        body=scroll_area(window,auto_hide=True);body.grid(row=1,column=0,sticky='nsew',padx=18);body.grid_columnconfigure(0,weight=1)
        desc=ctk.CTkLabel(body,text='Cada periodo conserva sus notas y unidades. Al crear uno nuevo se copian los cursos y el alumnado; las evaluaciones empiezan vacías.',anchor='w',justify='left')
        desc.grid(row=0,column=0,sticky='ew',pady=8);wrap_label(desc)
        records=periodos.catalog(storage.data_dir(),self._db_path);self._period_records=records
        labels={f"{r['label']} · {'Cerrado' if r['closed'] else 'Abierto'} · {r['path'].stem}":r for r in records}
        selector=ctk.CTkComboBox(body,values=list(labels),state='readonly',height=38);selector.grid(row=1,column=0,sticky='ew',pady=8)
        current=next((label for label,row in labels.items() if row['path'].resolve()==self._db_path.resolve()),next(iter(labels),''));selector.set(current)
        def open_selected():
            row=labels.get(selector.get())
            if not row or row['path'].resolve()==self._db_path.resolve():window.destroy();return
            if not self.confirmar_descartar(include_points=True):return
            if row['path'].parent.resolve()==storage.data_dir().resolve():storage.activate_period(row['path'])
            self._reiniciar(row['path'])
        ctk.CTkButton(body,text='Abrir periodo seleccionado',**button(),command=open_selected).grid(row=2,column=0,sticky='e',pady=6)
        ctk.CTkLabel(body,text='Crear o identificar un periodo',font=ctk.CTkFont(size=18,weight='bold')).grid(row=3,column=0,sticky='w',pady=(24,10))
        form=ctk.CTkFrame(body);form.grid(row=4,column=0,sticky='ew');form.grid_columnconfigure((0,1,2),weight=1)
        meta=periodos.info(self._db_path)
        for n,text in enumerate(['Año escolar','Organización','Periodo']):ctk.CTkLabel(form,text=text).grid(row=0,column=n,padx=8,pady=6,sticky='w')
        year=ctk.CTkEntry(form);year.insert(0,str(meta['year'] or datetime.now().year));year.grid(row=1,column=0,sticky='ew',padx=8,pady=8)
        scheme=ctk.CTkComboBox(form,values=list(periodos.SCHEMES),state='readonly');scheme.set(meta['scheme']);scheme.grid(row=1,column=1,sticky='ew',padx=8,pady=8)
        number=ctk.CTkComboBox(form,values=[str(i) for i in range(1,periodos.SCHEMES[meta['scheme']]+1)],state='readonly');number.set(str(meta['number'] or 1));number.grid(row=1,column=2,sticky='ew',padx=8,pady=8)
        def change(value):number.configure(values=[str(i) for i in range(1,periodos.SCHEMES[value]+1)]);number.set('1')
        scheme.configure(command=change)
        def create(identify=False):
            if not self.licencia_permite() or not self.confirmar_descartar(include_points=True):return
            if identify and not self.verificar_permiso_edicion():return
            try:
                if identify:
                    if meta['year'] is not None:raise ValueError('Este documento ya tiene un periodo asignado. Cree otro para las nuevas notas.')
                    storage.backup_database(self._db_path,'asignar-periodo')
                    periodos.identify(self._db_path,year.get(),number.get(),scheme.get());self.actualizar_contexto_academico();window.destroy()
                else:
                    path=storage.create_period(self._db_path,year.get(),number.get(),scheme.get());storage.activate_period(path);self._reiniciar(path)
            except Exception as exc:messagebox.showerror('Periodo',str(exc),parent=window)
        actions=ctk.CTkFrame(body,fg_color='transparent');actions.grid(row=5,column=0,sticky='ew',pady=12)
        if meta['year'] is None:ctk.CTkButton(actions,text='Asignar al registro actual',**button(),command=lambda:create(True)).pack(side='left',padx=4)
        ctk.CTkButton(actions,text='Crear periodo vacío',**button(),command=create).pack(side='right',padx=4)
        ctk.CTkButton(body,text='Cerrar / reabrir el periodo actual',**button(),command=lambda:(window.destroy(),self.alternar_periodo())).grid(row=6,column=0,sticky='w',pady=12)
        ctk.CTkButton(window,text='Listo',**button(),command=window.destroy).grid(row=2,column=0,sticky='e',padx=18,pady=14)
        polish_dialog(window,self,830,540)

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
