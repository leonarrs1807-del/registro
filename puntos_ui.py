"""Classroom workflow: topics → short practices → accumulated exam grade."""
from datetime import date
from decimal import Decimal, ROUND_DOWN
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog,filedialog
import customtkinter as ctk
import puntos,db,app_storage
from widgets import scroll_area,wrap_label
from interfaz import split,grade_panels,pixel_scale,flow_toolbar
from ui_icons import icon
from widgets import Tooltip


class PointsGrid(ttk.Treeview):
    def __init__(self,master,**kwargs):
        super().__init__(master,**kwargs)
        self.limits={};self.editable=False;self.on_changed=None;self.editor=None
        self.bind('<Double-1>',self.edit_cell)

    def finish(self):
        if self.editor is None:return True
        return self._commit()

    def edit_cell(self,event):
        if not self.editable or not self.winfo_toplevel().verificar_permiso_edicion():return
        row=self.identify_row(event.y);column=self.identify_column(event.x)
        if not row or not column:return
        name=self.column(column,'id')
        if name not in self.limits:return
        if not self.finish():return
        bounds=self.bbox(row,name)
        if not bounds:return
        x,y,width,height=bounds
        editor=tk.Entry(self,font=ttk.Style(self).lookup('Treeview','font') or ('Segoe UI',16),justify='center')
        editor.insert(0,self.set(row,name));editor.select_range(0,'end')
        editor.place(x=x,y=y,width=width,height=height);editor.focus_set()
        self.editor=editor
        def commit(event=None):
            if self.editor is None:return True
            if getattr(self,'_committing',False):return False
            from db_safety import valid_number
            raw=editor.get().strip()
            try:value='' if not raw else f"{valid_number(raw.replace(',','.'),0,self.limits[name],'Puntos'):g}"
            except ValueError as exc:
                self._committing=True
                try:messagebox.showwarning('Puntos no válidos',str(exc),parent=self)
                finally:self._committing=False
                editor.focus_set();return False
            self.set(row,name,value);self.editor=None;editor.destroy()
            if self.on_changed:self.on_changed()
            return True
        self._commit=commit
        def cancel(event=None):
            if self.editor is not None:
                self.editor=None;editor.destroy()
        editor.bind('<Return>',commit);editor.bind('<FocusOut>',commit);editor.bind('<Escape>',cancel)


class PointsPanel(ctk.CTkFrame):
    def __init__(self,master,app):
        super().__init__(master,fg_color='transparent')
        self.app=app;self.block_id=None;self.pending=False;self.grid_view=None;self.data=None
        self._context=None;self._block_map={}
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(1,weight=1)
        actions=ctk.CTkFrame(self,fg_color='transparent');actions.grid(row=0,column=0,sticky='ew',padx=8,pady=6)
        ctk.CTkLabel(actions,text='Prácticas',font=ctk.CTkFont(size=18,weight='bold')).grid(row=0,column=0,padx=4)
        buttons=[('Nuevo tema',self.new_block),('Agregar práctica',self.new_practice),('Guardar',self.save),('Crear nota / 20',self.publish)]
        for col,(text,callback) in enumerate(buttons,1):
            button=ctk.CTkButton(actions,text=text,command=callback,width=105,height=32,
                fg_color='#2563eb' if col==4 else ('#e2e8f0','#334155'),text_color='white' if col==4 else ('#334155','#e2e8f0'))
            button.grid(row=0,column=col,padx=4)
        more=ctk.CTkButton(actions,text='',image=icon('more',master=self),width=32,height=32,fg_color='transparent',hover_color=('#e2e8f0','#334155'))
        more.configure(command=lambda:self.menu_more(more));more.grid(row=0,column=5,padx=4);Tooltip(more,'Incluir prácticas o reabrir tema')
        help_button=ctk.CTkButton(actions,text='',image=icon('help',master=self),width=32,height=32,fg_color='transparent',hover_color=('#e2e8f0','#334155'),
            command=lambda:app.abrir_instrucciones('Prácticas y puntitos'))
        help_button.grid(row=0,column=6,padx=4);Tooltip(help_button,'Cómo se calcula la nota final')
        flow_toolbar(actions)
        self.panel=split(self,'temas_puntos');self.panel.grid(row=1,column=0,sticky='nsew',padx=8,pady=6)
        left=ctk.CTkFrame(self.panel);left.grid_columnconfigure(0,weight=1);left.grid_rowconfigure(1,weight=1)
        ctk.CTkLabel(left,text='Temas',font=ctk.CTkFont(weight='bold')).grid(row=0,column=0,padx=8,pady=8,sticky='w')
        self.listing=tk.Listbox(left,font=('Segoe UI',getattr(app,'_native_table_font_size',-16)),exportselection=False,activestyle='dotbox',width=18,borderwidth=0,highlightthickness=0)
        self.listing.grid(row=1,column=0,sticky='nsew',padx=8,pady=4)
        from interfaz import scrollbar
        sb=scrollbar(left,'vertical',self.listing.yview);sb.grid(row=1,column=1,sticky='ns');self.listing.configure(yscrollcommand=sb.set)
        self.listing.bind('<<ListboxSelect>>',self._select)
        self.right=ctk.CTkFrame(self.panel);self.right.grid_columnconfigure(0,weight=1);self.right.grid_rowconfigure(1,weight=1)
        self.description=ctk.CTkLabel(self.right,text='Seleccione un tema',justify='left',anchor='w',wraplength=750)
        self.description.grid(row=0,column=0,sticky='ew',padx=8,pady=6);wrap_label(self.description)
        self.table_host=ctk.CTkFrame(self.right,fg_color='transparent');self.table_host.grid(row=1,column=0,sticky='nsew')
        self.panel.add(left,width=round(180*pixel_scale(self)),minsize=round(120*pixel_scale(self)),stretch='never')
        self.panel.add(self.right,minsize=round(250*pixel_scale(self)),stretch='always')
        self.status=ctk.CTkLabel(self,text='',anchor='w',height=22)
        self.status.grid(row=2,column=0,sticky='ew',padx=10,pady=2)

    def menu_more(self,button):
        menu=tk.Menu(self,tearoff=False)
        menu.add_command(label='Incluir o excluir práctica…',command=self.toggle)
        menu.add_command(label='Reabrir tema…',command=self.reopen)
        self.app.fuentes_menu(menu);menu.tk_popup(button.winfo_rootx(),button.winfo_rooty()+button.winfo_height())

    def _context_now(self):return (self.app.obtener_curso_activo_id(),self.app.combo_grado_global.get(),self.app.combo_seccion_global.get())

    def refresh(self,select=None):
        course,grade,section=self._context_now()
        if self._context==(course,grade,section) and self.pending and select is None:return
        if course is None:return
        if self._context!=(course,grade,section):self.block_id=None
        self._context=(course,grade,section)
        rows=puntos.list_blocks(self.app._db_path,course,grade,section)
        self._block_map={i:r for i,r in enumerate(rows)}
        self.listing.delete(0,'end')
        for r in rows:self.listing.insert('end',r['tema']+(' ✓' if r['estado']=='consolidado' else ''))
        target=select if select is not None else self.block_id
        index=next((i for i,r in self._block_map.items() if r['id']==target),None)
        if index is None and rows:index=0
        if index is not None:
            self.listing.selection_set(index);self.block_id=rows[index]['id'];self.load()
        else:
            self.block_id=None;self.data=None;self.grid_view=None
            for child in self.table_host.winfo_children():child.destroy()
            self.description.configure(text='Cree un tema para registrar prácticas en este curso y salón.')

    def _select(self,event=None):
        if not self.listing.curselection():return
        chosen=self._block_map[self.listing.curselection()[0]]['id']
        if chosen==self.block_id:return
        if not self.confirm_change():
            self.listing.selection_clear(0,'end')
            for i,r in self._block_map.items():
                if r['id']==self.block_id:self.listing.selection_set(i)
            return
        self.block_id=chosen;self.load()

    def confirm_change(self):
        if self.grid_view and not self.grid_view.finish():return False
        if not self.pending:return True
        answer=messagebox.askyesnocancel('Puntos sin guardar','¿Guardar los puntos de este tema antes de continuar?',parent=self)
        if answer is None:return False
        if answer:return self.save()
        self.pending=False
        return True

    def load(self):
        self.data=puntos.details(self.app._db_path,self.block_id)
        active=[e for e in self.data['exercises'] if e['activa']]
        for child in self.table_host.winfo_children():child.destroy()
        self.grid_view=None
        block=self.data['block'];maximum=sum(e['maximo'] for e in active)
        self.description.configure(text=f"{block['tema']} · {len([p for p in self.data['practices'] if p['activa']])} prácticas · {maximum:g} puntos · {block['estado']}")
        if not active:
            ctk.CTkLabel(self.table_host,text='Agregue una práctica de 20 minutos y defina sus ejercicios.').pack(padx=10,pady=20)
            self.pending=False;return
        headers=['ID','Código','Apellidos y Nombres']+[f'e{e["id"]}' for e in active]+['suma','maximo','nota','pendientes']
        tree,identity,pane=grade_panels(self.table_host,headers,PointsGrid,key="puntos_nombres")
        self.grid_view=tree;self.identity=identity;self.exercises=active
        identity.configure(columns=('codigo','alumno','nota'))
        identity.heading('codigo',text='Código');identity.heading('alumno',text='Estudiante')
        identity.set_grade_columns(('nota',))
        identity.heading('nota',text='Nota / 20');identity.column('nota',width=round(72*pixel_scale(tree)),minwidth=round(60*pixel_scale(tree)),stretch=False)
        identity.column('codigo',width=round(60*pixel_scale(tree)),minwidth=round(45*pixel_scale(tree)),stretch=False)
        identity.column('alumno',width=round(190*pixel_scale(tree)),minwidth=round(100*pixel_scale(tree)),stretch=True)
        tree.limits={f'e{e["id"]}':e['maximo'] for e in active}
        tree.editable=block['estado']=='abierto'
        tree.on_changed=self._changed
        for col in headers[3:]:tree.column(col,width=round(120*pixel_scale(tree)),minwidth=round(85*pixel_scale(tree)),stretch=False)
        practice_numbers={p['id']:i+1 for i,p in enumerate(self.data['practices'])}
        tree.full_headers={}
        for e in active:
            col=f'e{e["id"]}'
            tree.heading(col,text=f"P{practice_numbers[e['practica_id']]} · E{e['numero']} / {e['maximo']:g}")
            tree.full_headers[col]=f"{e['practica']} · {e['fecha']} · {e['minutos']} minutos\nEjercicio {e['numero']}: {e['descripcion']}\nMáximo: {e['maximo']:g} puntos"
        for col,label in [('suma','Puntos obtenidos'),('maximo','Máximo total'),('nota','Nota / 20'),('pendientes','Pendientes')]:tree.heading(col,text=label)
        for s in self.data['students']:
            values=[s['ID'],s['Codigo_Unico'],s['Apellidos']+', '+s['Nombres']]+['' if self.data['scores'].get((e['id'],s['ID'])) is None else f"{self.data['scores'][(e['id'],s['ID'])]:g}" for e in active]+['','','','']
            item=tree.insert('','end',values=values);identity.insert('','end',iid=item,values=(values[1],values[2]))
        self.pending=False;self._preview()
        self.app.restaurar_divisor('puntos_nombres')

    def _preview(self):
        from decimal import Decimal,ROUND_HALF_UP
        if not self.grid_view:return
        maximum=sum((Decimal(str(e['maximo'])) for e in self.exercises),Decimal(0))
        for item in self.grid_view.get_children():
            row=list(self.grid_view.item(item,'values'));cells=row[3:3+len(self.exercises)]
            pending=sum(not str(v).strip() for v in cells)
            total=sum((Decimal(str(v)) for v in cells if str(v).strip()),Decimal(0))
            note='Pendiente' if pending or not maximum else str((total/maximum*20).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
            row[-4:]=[f'{total:g}',f'{maximum:g}',note,str(pending)]
            self.grid_view.item(item,values=row)
            self.identity.set(item,'nota',note)

    def _changed(self):
        self.pending=True;self._preview();self.status.configure(text='Cambios sin guardar')

    def save(self):
        if not self.block_id or not self.grid_view:return True
        if not self.grid_view.finish():return False
        if not self.pending:return True
        if not self.app.verificar_permiso_edicion(curso=self.data['block']['curso_id']):return False
        values=[]
        for item in self.grid_view.get_children():
            row=self.grid_view.item(item,'values')
            for i,e in enumerate(self.exercises,3):values.append((e['id'],int(row[0]),row[i]))
        try:puntos.save_scores(self.app._db_path,self.block_id,values)
        except ValueError as exc:messagebox.showwarning('Puntos',str(exc),parent=self);return False
        self.pending=False
        self.status.configure(text='Puntos guardados')
        return True

    def new_block(self):
        if not self.app.verificar_permiso_edicion() or not self.confirm_change():return
        course=self.app.obtener_curso_activo_id()
        if not course:return
        comps=db.obtener_competencias_por_curso(course)
        window=ctk.CTkToplevel(self);window.title('Nuevo tema para acumular puntos');window.geometry('650x650');window.transient(self.app)
        body=scroll_area(window);body.pack(fill='both',expand=True);body.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(body,text='Tema, por ejemplo Ecuaciones',font=ctk.CTkFont(size=16,weight='bold')).grid(row=0,column=0,sticky='w',padx=10,pady=8)
        topic=ctk.CTkEntry(body);topic.grid(row=1,column=0,sticky='ew',padx=10)
        ctk.CTkLabel(body,text='Competencia').grid(row=2,column=0,sticky='w',padx=10,pady=(10,2))
        choices={f'{i+1}. {name}':cid for i,(cid,name) in enumerate(comps)}
        selection=ctk.CTkComboBox(body,values=list(choices),state='readonly');selection.grid(row=3,column=0,sticky='ew',padx=10)
        cap_host=ctk.CTkFrame(body);cap_host.grid(row=5,column=0,sticky='ew',padx=10,pady=8);cap_host.grid_columnconfigure(0,weight=1)
        checks=[]
        def capacities(label):
            for child in cap_host.winfo_children():child.destroy()
            checks.clear()
            for index,(cid,name) in enumerate(db.obtener_capacidades_por_competencia(choices[label])):
                frame=ctk.CTkFrame(cap_host,fg_color='transparent');frame.grid(row=index,column=0,sticky='ew',padx=5,pady=4);frame.grid_columnconfigure(1,weight=1)
                checkbox=ctk.CTkCheckBox(frame,text='',width=26);checkbox.select();checkbox.grid(row=0,column=0,sticky='nw',padx=6,pady=6)
                label=ctk.CTkLabel(frame,text=name,font=ctk.CTkFont(size=14),wraplength=480,justify='left',anchor='w');label.grid(row=0,column=1,sticky='ew',padx=4)
                from widgets import wrap_label
                wrap_label(label);checks.append((cid,checkbox))
        selection.configure(command=capacities)
        if choices:selection.set(next(iter(choices)));capacities(selection.get())
        ctk.CTkLabel(body,text='La nota global del tema se asignará a las capacidades marcadas. Si necesita notas distintas por capacidad, cree temas separados.',wraplength=570,justify='left').grid(row=6,column=0,padx=10,pady=10,sticky='ew')
        def create():
            try:
                block=puntos.create_block(self.app._db_path,course,choices[selection.get()],self.app.combo_grado_global.get(),self.app.combo_seccion_global.get(),topic.get(),[cid for cid,check in checks if check.get()])
            except (ValueError,KeyError) as exc:messagebox.showwarning('Tema',str(exc),parent=window);return
            window.destroy();self.refresh(select=block)
        ctk.CTkButton(body,text='Crear tema',command=create).grid(row=7,column=0,padx=10,pady=10,sticky='ew')
        window.grab_set()

    def new_practice(self):
        if not self.block_id:
            messagebox.showinfo('Práctica','Cree o seleccione primero un tema.');return
        if not self.app.verificar_permiso_edicion() or not self.confirm_change():return
        if self.data['block']['estado']!='abierto':messagebox.showinfo('Tema consolidado','Reabra el tema antes de agregar prácticas.');return
        window=ctk.CTkToplevel(self);window.title('Práctica corta');window.geometry('620x640');window.transient(self.app)
        body=scroll_area(window);body.pack(fill='both',expand=True);body.grid_columnconfigure(0,weight=1)
        fields={}
        for i,(name,default) in enumerate([('Nombre de la práctica',f'Práctica {len(self.data["practices"])+1}'),('Fecha',date.today().isoformat()),('Duración en minutos','20')]):
            ctk.CTkLabel(body,text=name).grid(row=i*2,column=0,sticky='w',padx=10,pady=4)
            entry=ctk.CTkEntry(body);entry.insert(0,default);entry.grid(row=i*2+1,column=0,sticky='ew',padx=10);fields[name]=entry
        ctk.CTkLabel(body,text='Ejercicios y puntaje máximo de esta práctica').grid(row=6,column=0,padx=10,pady=8,sticky='w')
        count=ctk.CTkComboBox(body,values=['2','3','1','4','5','6','8','10'],state='readonly');count.set('2');count.grid(row=7,column=0,padx=10,sticky='ew')
        host=ctk.CTkFrame(body);host.grid(row=8,column=0,padx=10,pady=8,sticky='ew');host.grid_columnconfigure(0,weight=1);rows=[]
        def rebuild(value):
            for child in host.winfo_children():child.destroy()
            rows.clear();n=int(value);base=(Decimal('10')/n).quantize(Decimal('.01'),rounding=ROUND_DOWN)
            for i in range(n):
                entry=ctk.CTkEntry(host);entry.insert(0,f'Ejercicio {i+1}');entry.grid(row=i,column=0,padx=6,pady=6,sticky='ew')
                maximum=ctk.CTkEntry(host,width=90);maximum.insert(0,str(base if i<n-1 else Decimal('10')-base*(n-1)));maximum.grid(row=i,column=1,padx=6,pady=6)
                rows.append((entry,maximum))
        count.configure(command=rebuild);rebuild('2')
        ctk.CTkLabel(body,text='Por defecto cada práctica vale 10 puntos. Puede cambiar los máximos. Dos prácticas sobre 10 sumarán un máximo de 20.',wraplength=530,justify='left').grid(row=9,column=0,padx=10,pady=8)
        def create():
            try:puntos.add_practice(self.app._db_path,self.block_id,fields['Nombre de la práctica'].get(),[(name.get(),value.get()) for name,value in rows],int(fields['Duración en minutos'].get()),fields['Fecha'].get())
            except (ValueError,KeyError) as exc:messagebox.showwarning('Práctica',str(exc),parent=window);return
            window.destroy();self.load()
        ctk.CTkButton(body,text='Agregar práctica al tema',command=create).grid(row=10,column=0,padx=10,pady=10,sticky='ew');window.grab_set()

    def publish(self):
        if not self.block_id or not self.app.verificar_permiso_edicion() or not self.save():return
        rows=puntos.summary(self.app._db_path,self.block_id)
        if any(r['pendientes'] for r in rows):
            messagebox.showwarning('Faltan puntos','Complete los ejercicios pendientes antes de crear la nota. Vacío no significa cero.');return
        if not messagebox.askyesno('Crear nota de examen','Se creará una sola actividad de Exámenes para esta competencia, usando el acumulado sobre 20 en las capacidades marcadas. Los porcentajes del curso se conservarán. ¿Continuar?'):return
        try:
            app_storage.backup_database(self.app._db_path,'antes-consolidar-puntos')
            session=puntos.consolidate(self.app._db_path,self.block_id)
        except ValueError as exc:messagebox.showwarning('Acumulado',str(exc));return
        self.load();self.app.recargar_tabla_actividades_creadas();self.app.recargar_matriz_completa();self.app.dibujar_graficos_estadisticos()
        messagebox.showinfo('Nota creada',f'Nota / 20 guardada en Exámenes, actividad #{session}. Revísela en Calificaciones.')

    def toggle(self):
        if not self.block_id or not self.app.verificar_permiso_edicion() or not self.confirm_change():return
        rows=self.data['practices']
        if not rows:return
        index=simpledialog.askinteger('Prácticas','\n'.join(f'{i+1}. {p["titulo"]} ({"incluida" if p["activa"] else "excluida"})' for i,p in enumerate(rows)),minvalue=1,maxvalue=len(rows))
        if index and messagebox.askyesno('Cambiar acumulado','Cambiará el máximo y la nota preliminar. Los puntos registrados se conservarán. ¿Continuar?'):
            try:puntos.toggle_practice(self.app._db_path,rows[index-1]['id'])
            except ValueError as exc:messagebox.showwarning('Prácticas',str(exc));return
            self.load()

    def reopen(self):
        if not self.block_id or not self.app.verificar_permiso_edicion():return
        if messagebox.askyesno('Reabrir tema','La nota de examen actual se conservará hasta volver a consolidar. Al consolidar otra vez se actualizará esa misma actividad. ¿Reabrir?'):
            puntos.reopen(self.app._db_path,self.block_id);self.load()
