"""Browse, preview, recover and reuse instruments without carrying student grades."""
import json
from pathlib import Path
from tkinter import messagebox,filedialog,ttk
import customtkinter as ctk
import biblioteca
from colores import button
from widgets import SafeDialog,scroll_area,wrap_label,polish_dialog
from modern_ui import card,caption,table
from interfaz import split,pixel_scale,flow_toolbar
from rubric_viewer import RubricTable,RubricViewer,TopicField


def model_text(model):
    lines=[f"{model['nivel']} · {model['curso']} · {model['grado'] or 'Varios grados'}",'Competencia: '+model['competencia'],
        'Propósito: '+(model['proposito'] or 'Por completar en la actividad'),'']
    for n,item in enumerate(model['criterios'],1):
        lines.extend([f"{n:02} · {item['capacidad_nombre']}",item['criterio'],f"Máximo: {item['puntaje_maximo']:g}"])
        if model['tipo']=='Rúbrica':
            for level in ('C','B','A','AD'):lines.append(f"{level}: {item['descriptores'][level]}")
        lines.append('')
    return '\n'.join(lines)


class LibraryPanel(ctk.CTkFrame):
    def __init__(self,parent,app):
        super().__init__(parent,fg_color='transparent');self.app=app;self.rows={};self.selected=None;self._search_job=None;self.limit=30
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(3,weight=1)
        header=card(self);header.grid(row=0,column=0,sticky='ew',padx=10,pady=(10,6));header.grid_columnconfigure(0,weight=1)
        caption(header,'Biblioteca de rúbricas y cotejos',large=True).grid(row=0,column=0,sticky='ew',padx=18,pady=(14,2))
        caption(header,'Tus modelos para otros colegios, periodos y actividades. Cada evaluación utiliza su propia copia.',muted=True).grid(row=1,column=0,sticky='ew',padx=18,pady=(0,14))
        actions=ctk.CTkFrame(self,fg_color='transparent');actions.grid(row=1,column=0,sticky='ew',padx=10,pady=5)
        for text,command in [('Guardar actividad actual',app.guardar_modelo_biblioteca),('Del registro actual',self.import_current),('Importar base / Excel…',self.import_source),('Respaldar biblioteca…',self.backup)]:
            ctk.CTkButton(actions,text=text,**button(),height=35,command=command).pack(side='left',padx=4)
        flow_toolbar(actions)
        filters=ctk.CTkFrame(self,fg_color='transparent');filters.grid(row=2,column=0,sticky='ew',padx=12,pady=8);filters.grid_columnconfigure(0,weight=1)
        self.search=ctk.CTkEntry(filters,placeholder_text='Buscar por tema, competencia o nombre…',height=36);self.search.grid(row=0,column=0,sticky='ew',padx=(0,7));self.search.bind('<KeyRelease>',self.search_changed)
        self.course=ctk.CTkComboBox(filters,values=['Todos los cursos'],state='readonly',width=195,command=lambda v:self.refresh());self.course.grid(row=0,column=1,padx=4)
        self.grade=ctk.CTkComboBox(filters,values=['Todos los grados'],state='readonly',width=140,command=lambda v:self.refresh());self.grade.grid(row=0,column=2,padx=4)
        self.kind=ctk.CTkComboBox(filters,values=['Todos los instrumentos','Rúbrica','Lista de Cotejo'],state='readonly',width=178,command=lambda v:self.refresh());self.kind.grid(row=0,column=3,padx=4)
        self.kind.set('Todos los instrumentos')
        self.archived=ctk.BooleanVar(value=False);ctk.CTkCheckBox(filters,text='Archivados',variable=self.archived,width=115,command=self.refresh).grid(row=1,column=0,sticky='w',padx=5,pady=(8,0))
        self.history=ctk.BooleanVar(value=False);ctk.CTkCheckBox(filters,text='Versiones anteriores',variable=self.history,width=180,command=self.refresh).grid(row=1,column=1,columnspan=2,sticky='w',padx=5,pady=(8,0))
        self.pane=split(self,'biblioteca_modelos');self.pane.grid(row=3,column=0,sticky='nsew',padx=10,pady=5)
        left=card(self.pane);left.grid_columnconfigure(0,weight=1);left.grid_rowconfigure(1,weight=1)
        self.count=caption(left,'Abre la biblioteca para consultar tus modelos.',muted=True);self.count.grid(row=0,column=0,sticky='ew',padx=6,pady=4)
        self.cards=scroll_area(left,auto_hide=True);self.cards.grid(row=1,column=0,sticky='nsew');self.cards.grid_columnconfigure(0,weight=1)
        right=card(self.pane);right.grid_columnconfigure(0,weight=1);right.grid_rowconfigure(2,weight=1)
        self.title=caption(right,'Elige un modelo',large=True);self.title.grid(row=0,column=0,sticky='ew',padx=16,pady=13)
        ctk.CTkButton(right,text='Ampliar tabla',width=105,**button(),command=self.expand).grid(row=0,column=1,padx=(0,12),pady=10)
        self.summary=caption(right,'',muted=True);self.summary.grid(row=1,column=0,columnspan=2,sticky='ew',padx=16,pady=(0,8))
        self.detail=RubricTable(right);self.detail.grid(row=2,column=0,columnspan=2,sticky='nsew',padx=10,pady=4)
        bottom=ctk.CTkFrame(right,fg_color='transparent');bottom.grid(row=3,column=0,columnspan=2,sticky='ew',padx=14,pady=12)
        self.use_button=ctk.CTkButton(bottom,text='Usar en una actividad',**button(),command=self.use,state='disabled');self.use_button.pack(fill='x',pady=4)
        self.export_button=ctk.CTkButton(bottom,text='Descargar modelo Excel',**button(),command=self.export,state='disabled');self.export_button.pack(fill='x',pady=4)
        self.archive_button=ctk.CTkButton(bottom,text='Archivar modelo',**button(),command=self.archive,state='disabled');self.archive_button.pack(fill='x',pady=4)
        self.pane.add(left,width=round(440*pixel_scale(self)),minsize=260,stretch='never');self.pane.add(right,minsize=300,stretch='always')

    def search_changed(self,event=None):
        if self._search_job:self.after_cancel(self._search_job)
        self._search_job=self.after(180,self.refresh)

    def refresh(self,select=None):
        self._search_job=None
        all_rows=biblioteca.list_models(archived=self.archived.get(),include_data=False)
        courses=['Todos los cursos']+sorted({r['curso'] for r in all_rows})
        self.course.configure(values=courses)
        if self.course.get() not in courses:self.course.set(courses[0])
        grades=['Todos los grados']+sorted({r['grado'] for r in all_rows if r['grado']})
        self.grade.configure(values=grades)
        if self.grade.get() not in grades:self.grade.set(grades[0])
        rows=biblioteca.list_models(search=self.search.get(),course='' if self.course.get()==courses[0] else self.course.get(),
            grade='' if self.grade.get()==grades[0] else self.grade.get(),kind='' if self.kind.get()=='Todos los instrumentos' else self.kind.get(),
            archived=self.archived.get(),history=self.history.get(),include_data=False)
        self.rows={r['id']:r for r in rows};self.count.configure(text=f'{len(rows)} modelos · compartidos entre tus registros')
        for child in self.cards.winfo_children():child.destroy()
        if not rows:caption(self.cards,'Tu biblioteca está lista. Guarda un instrumento de una actividad o importa tus modelos anteriores.',muted=True).grid(row=0,column=0,sticky='ew',padx=15,pady=30)
        for n,row in enumerate(rows[:self.limit]):
            row['modelo']=biblioteca.get_model(row['id'])
            frame=card(self.cards);frame.grid(row=n,column=0,sticky='ew',padx=5,pady=5);frame.grid_columnconfigure(0,weight=1)
            ctk.CTkButton(frame,text=row['nombre'],anchor='w',height=37,fg_color='transparent',text_color=('#075985','#bae6fd'),hover_color=('#eff9ff','#1e3a50'),
                font=ctk.CTkFont(size=16,weight='bold'),command=lambda identity=row['id']:self.select(identity)).grid(row=0,column=0,sticky='ew',padx=10,pady=(8,0))
            info=f"{row['nivel']} · {row['curso']} · {row['grado'] or 'Varios grados'}\n{row['tipo']} · {len(row['modelo']['criterios'])} criterios · Versión {row['version']}"
            caption(frame,info,muted=True).grid(row=1,column=0,sticky='ew',padx=18,pady=(3,12))
        if len(rows)>self.limit:ctk.CTkButton(self.cards,text='Mostrar más modelos',**button(),command=self.more).grid(row=self.limit,column=0,pady=12)
        identity=select if select in self.rows else self.selected if self.selected in self.rows else next(iter(self.rows),None)
        self.select(identity)

    def more(self):self.limit+=30;self.refresh()

    def select(self,identity):
        self.selected=identity;row=self.rows.get(identity)
        if row and 'modelo' not in row:row['modelo']=biblioteca.get_model(identity)
        self.title.configure(text=row['nombre'] if row else 'Elige un modelo')
        model=row['modelo'] if row else None
        self.summary.configure(text=f"{model['nivel']} · {model['curso']} · {model['grado'] or 'Varios grados'}\nCompetencia: {model['competencia']}\nPropósito: {model['proposito'] or 'Por completar'}" if model else '')
        self.detail.set_indicators([{**item,'tipo':model['tipo']} for item in model['criterios']] if model else [])
        for widget in (self.use_button,self.export_button,self.archive_button):widget.configure(state='normal' if row else 'disabled')
        self.archive_button.configure(text='Recuperar modelo' if self.archived.get() else 'Archivar modelo')

    def import_source(self):
        path=filedialog.askopenfilename(title='Importar modelos de una base anterior o Excel reutilizable',initialdir=self.app._db_path.parent,filetypes=[('Bases e instrumentos','*.db *.sqlite *.sqlite3 *.registro *.xlsx')])
        if not path:return
        self.import_path(path)

    def import_current(self):self.import_path(self.app._db_path)

    def import_path(self,path):
        try:
            models,warnings=biblioteca.read_source(path)
            if not models:messagebox.showinfo('Biblioteca','No hay instrumentos compatibles con criterios en ese archivo.'+('\n\n'+'\n'.join(warnings[:4]) if warnings else ''),parent=self);return
            dialog=ImportModelsDialog(self.app,models,Path(path).name,warnings);self.app.wait_window(dialog)
            if dialog.selected:
                ids=biblioteca.save_models(dialog.selected,origin=Path(path).name);self.refresh(ids[0] if ids else None)
                self.app.lbl_estado.configure(text=f'Biblioteca actualizada · {len(ids)} modelos procesados')
        except Exception as exc:messagebox.showerror('Importar modelos',str(exc),parent=self)

    def backup(self):
        path=self.app.elegir_destino(title='Guardar copia de toda la biblioteca',initialfile='Mi_biblioteca.biblioteca.db',defaultextension='.db',filetypes=[('Biblioteca SQLite','*.db')])
        if not path:return
        try:biblioteca.backup(path);self.app.archivo_guardado(path,'Biblioteca completa guardada. Para recuperarla use Importar base / Excel; sus modelos se combinarán.')
        except Exception as exc:messagebox.showerror('Biblioteca',str(exc),parent=self)

    def archive(self):
        if self.selected:biblioteca.archive(self.selected,archived=not self.archived.get());self.refresh()

    def export(self):
        if not self.selected:return
        model=self.rows[self.selected]['modelo']
        import re
        filename=re.sub(r'[<>:"/\\|?*]','_',model['nombre'])+'.xlsx'
        path=self.app.elegir_destino(title='Guardar modelo reutilizable en Excel',initialfile=filename,defaultextension='.xlsx',filetypes=[('Modelo Excel','*.xlsx')])
        if path:
            try:biblioteca.export_excel(path,model);self.app.archivo_guardado(path,'Modelo Excel guardado con su estructura y el registro de estudiantes vacío.')
            except Exception as exc:messagebox.showerror('Modelo Excel',str(exc),parent=self)

    def use(self):
        if self.selected:return ApplyModelDialog(self.app,self.rows[self.selected]['modelo'])

    def expand(self):
        if self.selected:return RubricViewer(self.app,self.rows[self.selected]['modelo'])


class ImportModelsDialog(SafeDialog):
    def __init__(self,app,models,origin,warnings):
        super().__init__(app);self.title('Revisar modelos de '+origin);self.selected=[];self.models=models
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(2,weight=1)
        caption(self,'Elige las rúbricas y cotejos que deseas conservar',large=True).grid(row=0,column=0,sticky='ew',padx=18,pady=14)
        caption(self,'Se importan criterios y descriptores. Ctrl o Mayús permite elegir varios modelos; las notas y estudiantes del origen permanecen en su registro.',muted=True).grid(row=1,column=0,sticky='ew',padx=18,pady=6)
        frame,self.tree=table(self,[('nombre','Modelo',260),('curso','Curso y grado',220),('tipo','Instrumento',160),('criterios','Criterios',85)])
        frame.grid(row=2,column=0,sticky='nsew',padx=16,pady=8);self.tree.configure(selectmode='extended')
        for n,model in enumerate(models):self.tree.insert('','end',iid=str(n),values=(model['nombre'],model['curso']+' · '+model['grado'],model['tipo'],len(model['criterios'])))
        self.tree.selection_set(self.tree.get_children())
        if warnings:caption(self,f'{len(warnings)} modelos necesitan adaptación: '+'; '.join(warnings[:2]),muted=True).grid(row=3,column=0,sticky='ew',padx=18,pady=5)
        actions=ctk.CTkFrame(self,fg_color='transparent');actions.grid(row=4,column=0,sticky='ew',padx=18,pady=14)
        ctk.CTkButton(actions,text='Cancelar',**button(),command=self.destroy).pack(side='left')
        ctk.CTkButton(actions,text='Importar seleccionados',**button(),command=self.confirm).pack(side='right')
        polish_dialog(self,app,980,620)

    def confirm(self):self.selected=[self.models[int(i)] for i in self.tree.selection()];self.destroy()


class ApplyModelDialog(SafeDialog):
    def __init__(self,app,model):
        super().__init__(app);self.app=app;self.model=model;self.title('Usar modelo de la biblioteca');self.plan=None
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(4,weight=1)
        caption(self,model['nombre'],large=True).grid(row=0,column=0,sticky='ew',padx=18,pady=14)
        self.labels={label:sid for label,sid in getattr(app,'combo_calif_etiqueta_a_id',{}).items()}
        self.target=ctk.CTkComboBox(self,values=list(self.labels) or ['Crea primero una actividad'],state='readonly',command=self.preview)
        self.target.grid(row=1,column=0,sticky='ew',padx=18,pady=8)
        self.target.set(next((k for k,v in self.labels.items() if v==app.id_actividad_calificando),next(iter(self.labels),'Crea primero una actividad')))
        self.topic=TopicField(self);self.topic.grid(row=2,column=0,sticky='ew',padx=18,pady=7);self._suggested_topic=None
        self.status=caption(self,'',muted=True);self.status.grid(row=3,column=0,sticky='ew',padx=18,pady=8)
        self.detail=RubricTable(self,[{**item,'tipo':model['tipo']} for item in model['criterios']]);self.detail.grid(row=4,column=0,sticky='nsew',padx=18,pady=8)
        self.apply_button=ctk.CTkButton(self,text='Aplicar modelo',**button(),command=self.apply);self.apply_button.grid(row=5,column=0,sticky='e',padx=18,pady=14)
        self.preview();polish_dialog(self,app,1300,780)

    def preview(self,value=None):
        self.plan=None;session=self.labels.get(self.target.get())
        try:
            if not session:raise ValueError('Crea una actividad en el colegio, periodo, curso y salón donde vas a evaluar.')
            self.plan=biblioteca.preview_model(self.model,session,self.app._db_path)
            context=self.plan['context'];suggested=context['titulo_tema']+(' · '+self.model['nombre'] if self.plan['new_activity'] else '')
            if self.topic.get() in ('',self._suggested_topic):self.topic.set(suggested)
            self._suggested_topic=suggested
            self.status.configure(text=f"{len(self.model['criterios'])} criterios · {len(self.plan['capacities'])} capacidades. "+
                ('Se creará una actividad nueva para conservar la evaluación anterior.' if self.plan['new_activity'] else 'Se copiará la estructura a esta actividad.')+
                (f" Se incorporarán {len(self.plan['missing'])} capacidades del modelo." if self.plan['missing'] else ''))
        except ValueError as exc:self.status.configure(text=str(exc))
        self.apply_button.configure(state='normal' if self.plan else 'disabled')

    def apply(self):
        if not self.plan or not self.app.verificar_permiso_edicion() or not self.app.confirmar_descartar(include_points=True):return
        try:
            target=biblioteca.apply_model(self.model,self.labels[self.target.get()],self.app._db_path,topic=self.topic.value())
            self.app.refrescar_curriculo_importado();self.app.recargar_tabla_actividades_creadas()
            self.destroy();self.app.abrir_actividad_en_pestana_calificar(target)
            self.app.lbl_estado.configure(text='Modelo aplicado · Listo para evaluar al grupo')
        except Exception as exc:messagebox.showerror('Aplicar modelo',str(exc),parent=self)
