"""One school → period → unit manager, with visible create/edit/remove actions."""
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
import customtkinter as ctk
import colegios,periodos,app_storage as storage
from widgets import SafeDialog,scroll_area,wrap_label,polish_dialog
from colores import button


class OrganizationManager(SafeDialog):
    def __init__(self,app,units_only=False):
        super().__init__(app);self.app=app;self.title('Colegios, periodos y unidades')
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(2,weight=1)
        title=ctk.CTkLabel(self,text='Colegio → Periodo → Unidades',font=ctk.CTkFont(size=22,weight='bold'))
        title.grid(row=0,column=0,sticky='w',padx=18,pady=14)
        top=ctk.CTkFrame(self,fg_color='transparent');top.grid(row=1,column=0,sticky='ew',padx=18,pady=4);top.grid_columnconfigure(0,weight=1)
        self.school=ctk.CTkComboBox(top,values=[],state='readonly',command=self.change_school,height=36);self.school.grid(row=0,column=0,sticky='ew',padx=(0,8))
        ctk.CTkButton(top,text='+ Colegio',width=100,**button(),command=self.add_school).grid(row=0,column=1,padx=4)
        ctk.CTkButton(top,text='Renombrar',width=100,**button(),command=self.rename_school).grid(row=0,column=2,padx=4)
        ctk.CTkButton(top,text='Eliminar colegio',width=120,**button(),command=self.delete_school).grid(row=0,column=3,padx=4)
        area=scroll_area(self,auto_hide=True);area.grid(row=2,column=0,sticky='nsew',padx=14,pady=8);area.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(area,text='Bimestres y trimestres',font=ctk.CTkFont(size=18,weight='bold')).grid(row=0,column=0,sticky='w',pady=5)
        self.period_tree=self.listing(area,('periodo','fechas','estado'),('Periodo','Fechas','Estado'),5);self.period_tree.master.grid(row=1,column=0,sticky='ew')
        self.period_tree.bind('<<TreeviewSelect>>',lambda e:self.refresh_units());self.period_tree.bind('<Double-1>',lambda e:self.edit_period())
        actions=ctk.CTkFrame(area,fg_color='transparent');actions.grid(row=2,column=0,sticky='ew',pady=8)
        for title,fn in [('+ Periodo',lambda:self.edit_period(True)),('Editar',self.edit_period),('Eliminar',self.delete_period),('Abrir seleccionado',self.open_period)]:ctk.CTkButton(actions,text=title,width=120,**button(),command=fn).pack(side='left',padx=3)
        self.unit_heading=ctk.CTkLabel(area,text='',font=ctk.CTkFont(size=18,weight='bold'),anchor='w');self.unit_heading.grid(row=3,column=0,sticky='ew',pady=(12,4));wrap_label(self.unit_heading)
        hint=ctk.CTkLabel(area,text='Las unidades del periodo se comparten entre todos los cursos y grados del colegio.',anchor='w');hint.grid(row=4,column=0,sticky='ew',pady=4);wrap_label(hint)
        self.unit_tree=self.listing(area,('numero','nombre','fechas'),('N°','Unidad','Fechas'),6);self.unit_tree.master.grid(row=5,column=0,sticky='ew');self.unit_tree.bind('<Double-1>',lambda e:self.edit_unit())
        actions=ctk.CTkFrame(area,fg_color='transparent');actions.grid(row=6,column=0,sticky='ew',pady=8)
        for title,fn in [('+ Unidad',lambda:self.edit_unit(True)),('Editar',self.edit_unit),('Eliminar',self.delete_unit),('↑',lambda:self.move_unit(-1)),('↓',lambda:self.move_unit(1))]:ctk.CTkButton(actions,text=title,width=50 if title in ('↑','↓') else 120,**button(),command=fn).pack(side='left',padx=3)
        ctk.CTkButton(self,text='Papelera / recuperar',**button(),command=self.open_trash).grid(row=3,column=0,sticky='w',padx=18,pady=12)
        ctk.CTkButton(self,text='Listo',**button(),command=self.finish).grid(row=3,column=0,sticky='e',padx=18,pady=12)
        self.records={};self.units={};self.refresh_schools();polish_dialog(self,app,1040,790)
        app._organization_manager=self

    def listing(self,parent,columns,headings,height):
        frame=ctk.CTkFrame(parent);frame.grid_columnconfigure(0,weight=1)
        tree=ttk.Treeview(frame,columns=columns,show='headings',height=height,selectmode='browse')
        for key,text in zip(columns,headings):tree.heading(key,text=text);tree.column(key,width=80 if key in ('numero','estado') else 280,stretch=key not in ('numero','estado'))
        tree.grid(row=0,column=0,sticky='ew');sy=ttk.Scrollbar(frame,command=tree.yview);sy.grid(row=0,column=1,sticky='ns');tree.configure(yscrollcommand=sy.set)
        return tree

    def refresh_schools(self,identity=None):
        rows=colegios.catalog(storage.data_dir(),self.app._db_path)
        self.schools=colegios.labels(rows)
        identity=identity or colegios.info(self.app._db_path)['school_id']
        self.school.configure(values=list(self.schools));self.school.set(next((k for k,r in self.schools.items() if r['id']==identity),next(iter(self.schools),'')))
        self.change_school(self.school.get())

    def change_school(self,value):
        self.period_tree.delete(*self.period_tree.get_children());self.records={}
        school=self.schools.get(value)
        if not school:return
        for n,row in enumerate(school['records']):
            key=str(n);self.records[key]=row
            self.period_tree.insert('','end',iid=key,values=(row['label'],f"{row['start']} — {row['end']}" if row['start'] or row['end'] else 'Sin fechas', 'Cerrado' if row['closed'] else 'Abierto'))
        self.app._period_records=school['records']
        selected=next((k for k,r in self.records.items() if r['path'].resolve()==self.app._db_path.resolve()),next(reversed(self.records),None))
        if selected is not None:self.period_tree.selection_set(selected);self.period_tree.focus(selected)
        self.refresh_units()

    def selected_period(self):
        selected=self.period_tree.selection();return self.records.get(selected[0]) if selected else None

    def writable(self,row):
        if not row:return False
        if row['closed']:messagebox.showinfo('Periodo cerrado','Abra y reabra este periodo para editar sus unidades o datos.',parent=self);return False
        return self.app.verificar_permiso_edicion()

    def refresh_units(self,selected=None):
        self.unit_tree.delete(*self.unit_tree.get_children());self.units={};row=self.selected_period()
        self.unit_heading.configure(text='Unidades · '+(row['label'] if row else 'Seleccione un periodo'))
        if row:
            for n,unit in enumerate(periodos.units(row['path']),1):
                key=str(unit['id']);self.units[key]=unit
                self.unit_tree.insert('','end',iid=key,values=(f'{n:02}',unit['nombre'],f"{unit['inicio']} — {unit['fin']}" if unit['inicio'] or unit['fin'] else 'Sin fechas'))
        if selected and str(selected) in self.units:self.unit_tree.selection_set(str(selected))

    def add_school(self):
        name=simpledialog.askstring('Nuevo colegio','Nombre del colegio:',parent=self)
        if not name or not self.app.confirmar_descartar(include_points=True):return
        try:
            target=colegios.blank_copy(self.app._db_path,storage.data_dir(),name)
            self.refresh_schools(colegios.info(target)['school_id'])
        except Exception as exc:messagebox.showerror('Colegio',str(exc),parent=self)

    def rename_school(self):
        row=self.schools.get(self.school.get())
        if not row or not self.app.verificar_permiso_edicion():return
        name=simpledialog.askstring('Editar colegio','Nombre del colegio:',initialvalue=row['name'],parent=self)
        if not name:return
        try:
            colegios.rename(storage.data_dir(),row['id'],name,self.app._db_path);self.refresh_schools(row['id']);self.app.actualizar_contexto_academico()
            if row['id']==self.app._school_id:
                field=self.app._institution_entries['nombre'];field.delete(0,'end');field.insert(0,name)
                self.app.actualizar_configuracion()
        except Exception as exc:messagebox.showerror('Colegio',str(exc),parent=self)

    def delete_school(self):
        school=self.schools.get(self.school.get())
        others=[r for r in self.schools.values() if r['id']!=school['id']] if school else []
        if not school or not self.app.confirmar_descartar(include_points=True) or not self.app.verificar_permiso_edicion():return
        if not others:
            messagebox.showinfo('Colegio','Agregue otro colegio antes de quitar el último. Puede eliminar sus periodos por separado.',parent=self);return
        if not messagebox.askyesno('Eliminar colegio',f"¿Quitar {school['name']} y sus {len(school['records'])} documentos?\nQuedarán completos en la papelera para recuperarlos.",parent=self):return
        try:
            colegios.archive_school(school['records'],self.app._db_path)
            if self.app._school_id==school['id']:
                target=others[0]['records'][-1]['path'];self.app._reiniciar(target)
            else:self.refresh_schools()
        except Exception as exc:messagebox.showerror('Colegio',str(exc),parent=self)

    def open_trash(self):
        window=SafeDialog(self);window.title('Recuperar colegios y periodos');window.transient(self)
        tree=self.listing(window,('school','period','date'),('Colegio','Periodo','Fecha de eliminación'),12);tree.master.pack(fill='both',expand=True,padx=16,pady=14)
        rows=colegios.trash(storage.data_dir())
        for n,row in enumerate(rows):tree.insert('','end',iid=str(n),values=(row['school_name'],row['label'],datetime.fromtimestamp(row['date']).strftime('%d/%m/%Y %H:%M')))
        def restore():
            if not tree.selection():return
            try:
                row=rows[int(tree.selection()[0])];target=periodos.open_snapshot(row['path'],storage.data_dir());window.destroy();self.refresh_schools(row['school_id']);self.grab_set()
            except Exception as exc:messagebox.showerror('Recuperar',str(exc),parent=window)
        ctk.CTkButton(window,text='Recuperar como otro documento',**button(),command=restore).pack(anchor='e',padx=16,pady=14)
        polish_dialog(window,self.app,950,500)

    def edit_period(self,new=False):
        current=self.selected_period()
        if not current:return
        if not new and not self.writable(current):return
        editor=SafeDialog(self);editor.title('Añadir periodo' if new else 'Editar periodo');editor.transient(self)
        body=scroll_area(editor,auto_hide=True);body.pack(fill='both',expand=True,padx=16,pady=12);body.grid_columnconfigure(1,weight=1)
        data={'year':str(current['year'] or datetime.now().year),'scheme':current['scheme'],'number':str(1 if new else current['number'] or 1),'name':'' if new else current['name'],'start':'' if new else current['start'],'end':'' if new else current['end']}
        entries={}
        for n,(key,caption) in enumerate([('year','Año escolar'),('scheme','Bimestres o trimestres'),('number','Número del periodo'),('name','Nombre (opcional)'),('start','Inicio (AAAA-MM-DD)'),('end','Fin (AAAA-MM-DD)')]):
            ctk.CTkLabel(body,text=caption).grid(row=n,column=0,sticky='w',padx=8,pady=8)
            entry=ctk.CTkComboBox(body,values=list(periodos.SCHEMES),state='readonly') if key=='scheme' else ctk.CTkComboBox(body,values=['1','2','3','4'],state='readonly') if key=='number' else ctk.CTkEntry(body)
            entry.grid(row=n,column=1,sticky='ew',padx=8,pady=8);entries[key]=entry
            if key in ('scheme','number'):entry.set(data[key])
            else:entry.insert(0,data[key])
        def scheme(value):
            options=[str(i) for i in range(1,periodos.SCHEMES[value]+1)];entries['number'].configure(values=options)
            if entries['number'].get() not in options:entries['number'].set(options[0])
        entries['scheme'].configure(command=scheme);scheme(entries['scheme'].get())
        def save():
            try:
                values={k:e.get() for k,e in entries.items()}
                from datetime import date
                for key in ('start','end'):
                    if values[key]:date.fromisoformat(values[key])
                if values['start'] and values['end'] and values['start']>values['end']:raise ValueError('Revise las fechas del periodo.')
                if new:
                    if not self.app.licencia_permite():return
                    path=storage.create_period(current['path'],values['year'],values['number'],values['scheme'])
                else:
                    path=current['path'];storage.backup_database(path,'editar-periodo')
                periodos.identify(path,values['year'],values['number'],values['scheme'],values['name'],values['start'],values['end'],root=storage.data_dir())
                editor.destroy();self.refresh_schools(current['school_id'])
                key=next((k for k,r in self.records.items() if r['path']==path),None)
                if key is not None:self.period_tree.selection_set(key);self.refresh_units()
                self.app.actualizar_contexto_academico()
            except Exception as exc:messagebox.showerror('Periodo',str(exc),parent=editor)
        ctk.CTkButton(editor,text='Guardar periodo',**button(),command=save).pack(anchor='e',padx=20,pady=14)
        self._period_editor=editor;self._period_fields=entries;self._period_save=save
        polish_dialog(editor,self.app,650,480)

    def edit_unit(self,new=False):
        row=self.selected_period();selected=self.unit_tree.selection()
        if not self.writable(row):return
        if row['year'] is None:
            messagebox.showinfo('Unidad','Cree o identifique primero el bimestre o trimestre.',parent=self);return
        unit=None if new else self.units.get(selected[0]) if selected else None
        if not new and not unit:return
        editor=SafeDialog(self);editor.title('Añadir unidad' if new else 'Editar unidad');editor.transient(self)
        body=scroll_area(editor,auto_hide=True);body.pack(fill='both',expand=True,padx=16,pady=12);body.grid_columnconfigure(0,weight=1)
        entries={}
        for n,(key,caption) in enumerate([('nombre','Nombre de la unidad'),('proposito','Propósito'),('inicio','Inicio (AAAA-MM-DD, opcional)'),('fin','Fin (AAAA-MM-DD, opcional)')]):
            ctk.CTkLabel(body,text=caption,anchor='w').grid(row=n*2,column=0,sticky='ew',pady=(8,2))
            entries[key]=ctk.CTkEntry(body);entries[key].grid(row=n*2+1,column=0,sticky='ew',pady=4);entries[key].insert(0,(unit or {}).get(key,''))
        def save():
            try:
                identity=periodos.save_unit(row['path'],None,None,None,*(entries[k].get() for k in ('nombre','proposito','inicio','fin')),identity=unit['id'] if unit else None)
                editor.destroy();self.refresh_units(identity);self.app.actualizar_contexto_academico();self.app.recargar_tabla_actividades_creadas()
            except Exception as exc:messagebox.showerror('Unidad',str(exc),parent=editor)
        ctk.CTkButton(editor,text='Guardar unidad',**button(),command=save).pack(anchor='e',padx=20,pady=14)
        self._unit_editor=editor;self._unit_fields=entries;self._unit_save=save
        polish_dialog(editor,self.app,650,490)

    def delete_unit(self):
        row=self.selected_period();selected=self.unit_tree.selection()
        if not selected or not self.writable(row):return
        unit=self.units[selected[0]]
        if not messagebox.askyesno('Eliminar unidad',f"¿Quitar «{unit['nombre']}»?\nLas actividades y notas se conservarán como Sin unidad.",parent=self):return
        try:
            periodos.delete_unit(row['path'],unit['id']);self.refresh_units();self.app.actualizar_contexto_academico();self.app.recargar_tabla_actividades_creadas();self.app.recargar_matriz_completa()
        except Exception as exc:messagebox.showerror('Unidad',str(exc),parent=self)

    def move_unit(self,delta):
        row=self.selected_period();selected=self.unit_tree.selection()
        if not selected or not self.writable(row):return
        identity=int(selected[0]);periodos.move_unit(row['path'],identity,delta);self.refresh_units(identity);self.app.actualizar_contexto_academico()

    def delete_period(self):
        row=self.selected_period()
        if not row or not self.app.confirmar_descartar(include_points=True) or not self.app.verificar_permiso_edicion():return
        if not messagebox.askyesno('Eliminar periodo',f"¿Quitar {row['label']} de {row['school_name']}?\nEl registro completo quedará recuperable en la carpeta papelera.",parent=self):return
        try:
            replacement,saved=colegios.remove_period(row['path'],storage.data_dir())
            if row['path'].resolve()==self.app._db_path.resolve():self.app._reiniciar(replacement)
            else:self.refresh_schools(row['school_id'])
        except Exception as exc:messagebox.showerror('Periodo',str(exc),parent=self)

    def open_period(self):
        row=self.selected_period()
        if not row or not self.app.confirmar_descartar(include_points=True):return
        if row['path'].resolve()==self.app._db_path.resolve():self.finish();return
        self.app._reiniciar(row['path'])

    def finish(self):
        self.app.actualizar_contexto_academico();self.destroy()
