"""Hierarchical school navigation and direct editing for the academic organizer."""
import hashlib
import tkinter as tk
from tkinter import ttk,messagebox
import customtkinter as ctk
import colegios,periodos,app_storage
from db_safety import atomic,backed_up,connection
from modern_ui import card,caption
from widgets import scroll_area,SafeDialog,polish_dialog,Tooltip
from interfaz import split,scrollbar,pixel_scale
from colores import button


def move_activities(sessions,unit,db_path):
    periodos.ensure_units_ready(db_path)
    return _move_activities(sessions,unit,db_path)


@backed_up
@atomic
def _move_activities(sessions,unit,db_path):
    for session in sessions:
        with connection(db_path) as conn:
            if not conn.execute('SELECT 1 FROM Sesiones_Clase WHERE id=?',(session,)).fetchone():raise ValueError('La actividad ya no existe en este periodo.')
            periodos.assign_unit(conn,session,unit)


class VisualOrganization:
    def create_navigation(self):
        self._nav_rows={};self._nav_current=None;self._units_path=None
        pane=split(self,'organizacion_visual');pane.grid(row=2,column=0,sticky='nsew',padx=14,pady=8)
        left=card(pane);left.grid_columnconfigure(0,weight=1);left.grid_rowconfigure(1,weight=1)
        caption(left,'Tu organización escolar',large=True).grid(row=0,column=0,columnspan=2,sticky='ew',padx=14,pady=13)
        self.navigation=ttk.Treeview(left,columns=('estado',),show='tree',selectmode='browse')
        self.navigation.heading('#0',text='Colegio · Periodo · Unidad');self.navigation.column('#0',width=320,minwidth=285)
        self.navigation.heading('estado',text='Estado');self.navigation.column('estado',width=90,minwidth=70,stretch=False)
        self.navigation.grid(row=1,column=0,sticky='nsew',padx=(7,0),pady=4)
        sy=scrollbar(left,'vertical',self.navigation.yview);sy.grid(row=1,column=1,sticky='ns');self.navigation.configure(yscrollcommand=sy.set)
        sx=scrollbar(left,'horizontal',self.navigation.xview);sx.grid(row=2,column=0,sticky='ew',padx=7);self.navigation.configure(xscrollcommand=sx.set)
        caption(left,'Selecciona para consultar. F2 o doble clic para editar el nombre. Abrir seleccionado carga el periodo y su unidad.',muted=True).grid(row=3,column=0,columnspan=2,sticky='ew',padx=14,pady=12)
        Tooltip(self.navigation,lambda:self.navigation.item(self.navigation.identify_row(self.navigation.winfo_pointery()-self.navigation.winfo_rooty()),'text'))
        self.navigation.bind('<<TreeviewSelect>>',self.navigate)
        self.navigation.bind('<F2>',self.rename_inline);self.navigation.bind('<Double-1>',self.rename_inline)
        self.navigation.bind('<Button-3>',lambda e:'break')
        area=scroll_area(pane,auto_hide=True);area.grid_columnconfigure(0,weight=1)
        pane.add(left,width=round(355*pixel_scale(self)),minsize=240,stretch='never')
        pane.add(area.container,minsize=500,stretch='always')
        return area

    def period_key(self,row):return 'p'+hashlib.sha256(str(row['path'].resolve()).encode()).hexdigest()[:20]

    def refresh_hierarchy(self):
        if not hasattr(self,'navigation'):return
        nav=self.navigation
        opened=set()
        def collect(parent=''):
            for key in nav.get_children(parent):
                if nav.item(key,'open'):opened.add(key)
                collect(key)
        collect();nav.delete(*nav.get_children());self._nav_rows={}
        active=self.selected_period();selected_unit=self.unit_tree.selection()
        chosen=None
        for school in self.schools.values():
            root='s'+school['id'];is_current=school['id']==(active or {}).get('school_id')
            nav.insert('','end',iid=root,text=school['name'],values=(f"{len(school['records'])} periodos",),open=root in opened or is_current)
            self._nav_rows[root]=dict(kind='school',school=school)
            for row in school['records']:
                key=self.period_key(row);current=bool(active and row['path'].resolve()==active['path'].resolve())
                nav.insert(root,'end',iid=key,text=row['label']+(' · Cerrado' if row['closed'] else ''),values=('Cerrado' if row['closed'] else 'Abierto',),open=key in opened or current)
                self._nav_rows[key]=dict(kind='period',school=school,record=row)
                if current:chosen=key
                for n,unit in enumerate(periodos.units(row['path']),1):
                    leaf=key+'u'+str(unit['id']);nav.insert(key,'end',iid=leaf,text=f"{n:02} · {unit['nombre']}",values=('Unidad',))
                    self._nav_rows[leaf]=dict(kind='unit',school=school,record=row,unit=unit)
                    if current and selected_unit and int(selected_unit[0])==unit['id']:chosen=leaf
        if chosen:self._nav_current=chosen;nav.selection_set(chosen);nav.focus(chosen);nav.see(chosen)

    def sync_hierarchy(self,event=None):
        row=self.selected_period()
        if not row:return
        key=self.period_key(row);selected=self.unit_tree.selection()
        if selected:key+='u'+selected[0]
        if key in self._nav_rows:self._nav_current=key;self.navigation.selection_set(key);self.navigation.see(key)

    def navigate(self,event=None):
        selected=self.navigation.selection()
        if not selected or selected[0]==self._nav_current:return
        self._nav_current=selected[0];target=self._nav_rows.get(selected[0])
        if not target:return
        label=next((name for name,school in self.schools.items() if school['id']==target['school']['id']),None)
        if not label:return
        if self.school.get()!=label:self.school.set(label);self.change_school(label)
        row=target.get('record')
        if row:
            key=next((k for k,r in self.records.items() if r['path'].resolve()==row['path'].resolve()),None)
            if key is not None:
                self.period_tree.selection_set(key);self.period_tree.focus(key)
                self.refresh_units(target.get('unit',{}).get('id'))

    def rename_inline(self,event=None):
        selected=self.navigation.selection()
        if not selected:return 'break'
        target=self._nav_rows.get(selected[0]);bounds=self.navigation.bbox(selected[0],'#0')
        if not target or not bounds:return 'break'
        if target['kind']=='school':
            if not self.app.verificar_permiso_edicion():return 'break'
            value=target['school']['name']
        else:
            if not self.writable(target['record']):return 'break'
            if target['kind']=='period' and target['record']['year'] is None:self.edit_period();return 'break'
            value=target['unit']['nombre'] if target['kind']=='unit' else target['record']['name']
        if getattr(self,'_name_editor',None):self._name_editor.destroy()
        x,y,width,height=bounds;editor=ttk.Entry(self.navigation,font=('Segoe UI',14));editor.insert(0,value)
        editor.place(x=x+12,y=y,width=max(90,width-14),height=height);editor.focus_set();editor.selection_range(0,'end');self._name_editor=editor
        def close(event=None):
            editor.destroy();self._name_editor=None;return 'break'
        def save(event=None):
            name=editor.get().strip()
            try:
                if target['kind']=='school':colegios.rename(app_storage.data_dir(),target['school']['id'],name,self.app._db_path)
                elif target['kind']=='unit':
                    u=target['unit'];periodos.save_unit(target['record']['path'],None,None,None,name,u['proposito'],u['inicio'],u['fin'],identity=u['id'])
                else:
                    r=target['record'];periodos.identify(r['path'],r['year'],r['number'],r['scheme'],name,r['start'],r['end'],root=app_storage.data_dir())
                close();self.refresh_schools(target['school']['id']);self.app.actualizar_contexto_academico()
                if target['kind']=='school' and target['school']['id']==self.app._school_id:
                    from institucion import profile
                    entry=self.app._institution_entries['nombre'];entry.delete(0,'end');entry.insert(0,profile(self.app._db_path)['nombre'])
                    self.app.actualizar_configuracion()
            except Exception as exc:messagebox.showerror('Editar nombre',str(exc),parent=self);editor.focus_set()
            return 'break'
        editor.bind('<Return>',save);editor.bind('<Escape>',close);self._name_save=save
        return 'break'

    def manage_activities(self):
        row=self.selected_period()
        if not row or not self.writable(row):return
        window=SafeDialog(self);window.title('Mover actividades entre unidades');window.grid_columnconfigure(0,weight=1);window.grid_rowconfigure(1,weight=1)
        caption(window,'Elige actividades y su nueva unidad',large=True).grid(row=0,column=0,sticky='ew',padx=18,pady=14)
        from modern_ui import table
        frame,tree=table(window,[('actividad','Actividad',330),('aula','Curso y salón',280),('unidad','Unidad actual',240)])
        frame.grid(row=1,column=0,sticky='nsew',padx=16,pady=8);tree.configure(selectmode='extended')
        with connection(row['path']) as conn:
            for r in conn.execute('''SELECT s.id,s.titulo_tema,c.nombre,s.grado,s.seccion,COALESCE(u.nombre,'Sin unidad')
                FROM Sesiones_Clase s JOIN Cursos c ON c.id=s.curso_id LEFT JOIN Unidades_Didacticas u ON u.id=s.unidad_id ORDER BY s.fecha,s.id'''):
                tree.insert('','end',iid=str(r[0]),values=(r[1],f'{r[2]} · {r[3]} {r[4]}',r[5]))
        choices={'Sin unidad':None,**{u['nombre']:u['id'] for u in periodos.units(row['path'])}}
        destination=ctk.CTkComboBox(window,values=list(choices),state='readonly');destination.grid(row=2,column=0,sticky='ew',padx=18,pady=8)
        def apply():
            if not tree.selection() or not self.app.confirmar_descartar(include_points=True):return
            try:
                move_activities([int(i) for i in tree.selection()],choices[destination.get()],row['path'])
                window.destroy();self.refresh_units();self.app.recargar_tabla_actividades_creadas();self.app.recargar_matriz_completa()
            except Exception as exc:messagebox.showerror('Mover actividades',str(exc),parent=window)
        ctk.CTkButton(window,text='Mover seleccionadas',**button(),command=apply).grid(row=3,column=0,sticky='e',padx=18,pady=14)
        self._move_tree=tree;self._move_destination=destination;self._move_apply=apply
        polish_dialog(window,self.app,1000,650)
