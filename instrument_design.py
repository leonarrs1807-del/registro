"""Professional instrument designer and shared, structured preview dialogs."""
from copy import deepcopy
import tkinter as tk
from tkinter import ttk,messagebox
import customtkinter as ctk
import db,app_storage
from db_safety import valid_number,connection
from escala import thresholds
from instrumentos import definition,validate_definition,LEVELS,LEVEL_NAMES
from evaluacion_datos import activity,get_indicators,get_answers
from widgets import SafeDialog,scroll_area,wrap_label
from instrument_widgets import InstrumentGrid,Multiline,label,number
from grade_cells import PALETTE
from interfaz import scrollbar
from rubric_viewer import RubricTable,TopicField


def fit(window,root,width=1150,height=760):
    scale=window._get_window_scaling()
    window.geometry(f'{min(width,int(root.winfo_screenwidth()/scale*.94))}x{min(height,int(root.winfo_screenheight()/scale*.86))}')
    window.transient(root)


def header(master,context):
    frame=ctk.CTkFrame(master,fg_color='transparent');frame.pack(fill='x',padx=16,pady=(8,2))
    title=label(frame,context['titulo_tema']);title.configure(font=ctk.CTkFont(size=20,weight='bold'));title.pack(fill='x',pady=(0,2))
    label(frame,f"{context['curso_nombre']} · {context['grado']} {context['seccion']} · {context['categoria']} · {context['fecha']} · {context['competencia_nombre']}").pack(fill='x',pady=2)


class InstrumentView(SafeDialog):
    def __init__(self,app,session):
        super().__init__(app);self.title('Detalles de la actividad y evaluación');fit(self,app)
        context=activity(session,app._db_path);items=get_indicators(session,app._db_path)
        header(self,context)
        tabs=ctk.CTkTabview(self);tabs.pack(fill='both',expand=True,padx=16,pady=(0,12))
        info=tabs.add('Actividad');body=scroll_area(info,auto_hide=True);body.pack(fill='both',expand=True)
        label(body,f"Peso de la actividad: {number(context['peso_clase'])}").pack(fill='x',padx=12,pady=8)
        if context['proposito']:label(body,context['proposito']).pack(fill='x',padx=12,pady=8)
        for cap in context['capacidades']:
            card=ctk.CTkFrame(body);card.pack(fill='x',padx=10,pady=6)
            label(card,cap['capacidad_nombre']).pack(fill='x',padx=12,pady=10)
            criterion=cap['criterio_precisado'] or ''
            if not items and criterion and criterion!=cap['capacidad_nombre']:label(card,criterion).pack(fill='x',padx=12,pady=(0,10))
        if items:
            page=tabs.add(items[0]['tipo']);grid=RubricTable(page,items);grid.pack(fill='both',expand=True);tabs.set(items[0]['tipo'])
            self.instrument_grid=grid
        ctk.CTkButton(self,text='Cerrar',width=130,height=36,command=self.destroy).pack(anchor='e',padx=16,pady=(0,12))
        self.grab_set()


class InstrumentPreview(SafeDialog):
    def __init__(self,app,staged,session,result):
        self.ready=False
        super().__init__(app);self.title('Revisar evaluación antes de importar');fit(self,app)
        self.confirmed=False;context=activity(session,staged);items=get_indicators(session,staged)
        header(self,context)
        self.topic=TopicField(self,context['titulo_tema']);self.topic.pack(fill='x',padx=18,pady=5)
        label(self,f"{items[0]['tipo']} · {result[0]} criterios · {result[1]} estudiantes con datos para importar").pack(fill='x',padx=18,pady=5)
        tabs=ctk.CTkTabview(self);tabs.pack(fill='both',expand=True,padx=16,pady=8)
        page=tabs.add('Instrumento');self.instrument_grid=RubricTable(page,items);self.instrument_grid.pack(fill='both',expand=True)
        notes=tabs.add('Cambios de notas');notes.grid_rowconfigure(1,weight=1);notes.grid_columnconfigure(0,weight=1)
        def values(path):
            with connection(path) as conn:return {(r[0],r[1]):r[2] for r in conn.execute('SELECT estudiante_id,capacidad_id,nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',(session,))}
        before=values(app._db_path);after=values(staged)
        with connection(staged) as conn:
            students={r[0]:(r[1],r[2]+', '+r[3]) for r in conn.execute('SELECT ID,Codigo_Unico,Apellidos,Nombres FROM Estudiantes')}
        capacities={c['capacidad_id']:c['capacidad_nombre'] for c in context['capacidades']}
        columns=('codigo','estudiante','capacidad','anterior','nueva')
        tree=ttk.Treeview(notes,columns=columns,show='headings')
        for col,text,width in zip(columns,('Código','Estudiante','Capacidad','Antes','Después'),(95,240,380,95,95)):
            tree.heading(col,text=text);tree.column(col,width=width,stretch=col in ('estudiante','capacidad'))
        count=0
        for (student,cap),value in after.items():
            if value==before.get((student,cap)):continue
            code,name=students[student];old=before.get((student,cap))
            tree.insert('','end',values=(code,name,capacities[cap],number(old) if old is not None else 'Pendiente',number(value) if value is not None else 'Pendiente'));count+=1
        label(notes,f'{count} notas cambiarán al confirmar.' if count else 'No hay cambios numéricos. Se actualizarán el instrumento y sus observaciones.').grid(row=0,column=0,sticky='ew',pady=8)
        tree.grid(row=1,column=0,sticky='nsew')
        sy=scrollbar(notes,'vertical',tree.yview);sy.grid(row=1,column=1,sticky='ns')
        sx=scrollbar(notes,'horizontal',tree.xview);sx.grid(row=2,column=0,sticky='ew')
        tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        observations=tabs.add('Observaciones');observations.grid_rowconfigure(0,weight=1);observations.grid_columnconfigure(0,weight=1)
        observed=ttk.Treeview(observations,columns=('student','criterion','before','after'),show='headings')
        for col,title,width in [('student','Estudiante',240),('criterion','Criterio',420),('before','Antes',130),('after','Después',130)]:
            observed.heading(col,text=title);observed.column(col,width=width,stretch=col in ('student','criterion'))
        previous=get_answers(session,app._db_path);current=get_answers(session,staged);by_id={i['id']:i for i in items}
        for key in sorted(set(previous)|set(current)):
            student,identity=key
            if identity not in by_id or previous.get(key)==current.get(key):continue
            observed.insert('','end',values=(students[student][1],by_id[identity]['criterio'],previous.get(key) or 'Pendiente',current.get(key) or 'Pendiente'))
        observed.grid(row=0,column=0,sticky='nsew');sy=scrollbar(observations,'vertical',observed.yview);sy.grid(row=0,column=1,sticky='ns')
        sx=scrollbar(observations,'horizontal',observed.xview);sx.grid(row=1,column=0,sticky='ew');observed.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        bar=ctk.CTkFrame(self,fg_color='transparent');bar.pack(fill='x',padx=16,pady=12)
        ctk.CTkButton(bar,text='Cancelar',height=38,fg_color='transparent',border_width=1,text_color=('#334155','#e2e8f0'),command=self.destroy).pack(side='left')
        ctk.CTkButton(bar,text='Confirmar importación',height=38,command=self.confirm).pack(side='right')
        self.grab_set()
        self.ready=True

    def confirm(self):
        try:self.topic_name=self.topic.value()
        except ValueError as exc:messagebox.showwarning('Tema de la actividad',str(exc),parent=self);return
        self.confirmed=True;self.destroy()


class InstrumentEditor(SafeDialog):
    def __init__(self,master,session,indicators,callback,kind=None):
        super().__init__(master);self.app=getattr(master,'app',master)
        self.session=session;self.callback=callback
        self.kind=kind or (indicators[0]['tipo'] if indicators else getattr(master,'tipo_inst','Rúbrica'))
        self.title('Diseñar '+self.kind);fit(self,self.app)
        self.context=activity(session,self.app._db_path);self.rows=[];self.visible=[]
        self.capacity_names={c['capacidad_id']:c['capacidad_nombre'] for c in self.context['capacidades']}
        self.capacities={name:identity for identity,name in self.capacity_names.items()}
        self.limits=thresholds(self.app._db_path)
        for index,item in enumerate(indicators):
            item=deepcopy(item)
            if item.get('id',0)<0:item.pop('id',None)
            self.rows.append(dict(item=item,source_index=index,active=True))
        if not self.rows:
            for cap in self.context['capacidades']:
                texts=[cap['criterio_precisado'] or cap['capacidad_nombre']]
                if self.kind=='Lista de Cotejo':texts.append('Explica su respuesta usando la evidencia solicitada.')
                for text in texts:
                    self.rows.append(dict(item=definition(dict(capacidad_id=cap['capacidad_id'],capacidad_nombre=cap['capacidad_nombre'],tipo=self.kind,indicador_texto=text,puntaje_maximo=20 if self.kind=='Rúbrica' else 10),self.limits),source_index=None,active=True))
        header(self,self.context)
        hint='Defina un criterio observable y un descriptor para cada nivel. AD vale el máximo. Los puntos de C, B, A y AD deben aumentar.' if self.kind=='Rúbrica' else 'Cada fila debe describir una evidencia observable. Sí aporta el máximo del criterio y No aporta cero; pendiente queda sin calificar.'
        label(self,hint).pack(fill='x',padx=18,pady=4)
        bar=ctk.CTkFrame(self,fg_color='transparent');bar.pack(fill='x',padx=16,pady=8);bar.grid_columnconfigure(0,weight=1)
        self.capacity_choice=ctk.CTkComboBox(bar,values=list(self.capacities),state='readonly',height=36,command=lambda _:self.render())
        self.capacity_choice.grid(row=0,column=0,sticky='ew',padx=(0,10));self.capacity_choice.set(next(iter(self.capacities)))
        ctk.CTkButton(bar,text='Añadir criterio',height=36,command=self.add_row).grid(row=0,column=1)
        self.capacity_title=label(bar,'');self.capacity_title.configure(font=ctk.CTkFont(size=16,weight='bold'))
        self.capacity_title.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(8,0))
        self.body=scroll_area(self,auto_hide=True,horizontal=True,min_width=880 if self.kind=='Rúbrica' else 520)
        self.body.pack(fill='both',expand=True,padx=16,pady=6);self.body.grid_columnconfigure(0,weight=1)
        bottom=ctk.CTkFrame(self,fg_color='transparent');bottom.pack(fill='x',padx=16,pady=12)
        ctk.CTkButton(bottom,text='Cancelar',height=38,fg_color='transparent',border_width=1,text_color=('#334155','#e2e8f0'),command=self.destroy).pack(side='left')
        ctk.CTkButton(bottom,text='Guardar instrumento',height=38,command=self.save).pack(side='right')
        self.render();self.grab_set()

    def capture(self):
        for row in self.visible:
            item=row['item'];item['criterio']=row['text'].get().strip();item['indicador_texto']=item['criterio']
            self.rescale(row)
            item['puntaje_maximo']=row['maximum'].get().replace(',','.')
            if self.kind=='Rúbrica':
                item['descriptores']={l:w.get().strip() for l,w in row['descriptors'].items()}
                item['puntajes']={l:w.get().replace(',','.') for l,w in row['scores'].items()}

    def rescale(self,row):
        try:new=valid_number(row['maximum'].get().replace(',','.'),.000001,20,'Máximo')
        except ValueError:return
        old=row.get('previous_maximum',new)
        if new!=old and self.kind=='Rúbrica':
            for level,entry in row['scores'].items():
                try:score=float(entry.get().replace(',','.'))*new/old
                except ValueError:continue
                entry.delete(0,'end');entry.insert(0,number(score))
        row['previous_maximum']=new

    def add_row(self):
        self.capture();cap=self.capacities[self.capacity_choice.get()]
        item=definition(dict(capacidad_id=cap,capacidad_nombre=self.capacity_names[cap],tipo=self.kind,indicador_texto='',puntaje_maximo=20 if self.kind=='Rúbrica' else 10),self.limits)
        self.rows.append(dict(item=item,source_index=None,active=True));self.render(capture=False)

    def render(self,capture=True):
        if capture:self.capture()
        for child in self.body.winfo_children():child.destroy()
        self.visible=[];cap=self.capacities[self.capacity_choice.get()]
        self.capacity_title.configure(text=self.capacity_names[cap])
        for row in [r for r in self.rows if r['active'] and r['item']['capacidad_id']==cap]:
            item=row['item'];index=len(self.visible);self.visible.append(row)
            card=ctk.CTkFrame(self.body,fg_color=('#f8fafc','#1e293b'),border_width=1,border_color='#cbd5e1')
            card.grid(row=index,column=0,sticky='ew',pady=8);card.grid_columnconfigure(0,weight=1)
            head=ctk.CTkFrame(card,fg_color='transparent');head.grid(row=0,column=0,sticky='ew',padx=12,pady=8);head.grid_columnconfigure(0,weight=1)
            label(head,'Criterio observable').grid(row=0,column=0,sticky='ew')
            label(head,'Puntos máximos').grid(row=0,column=1,padx=8)
            maximum=ctk.CTkEntry(head,width=90,height=36);maximum.insert(0,number(item['puntaje_maximo']));maximum.grid(row=0,column=2)
            row['maximum']=maximum;row['previous_maximum']=float(item['puntaje_maximo'])
            def remove(record=row):self.capture();record['active']=False;self.render(capture=False)
            ctk.CTkButton(head,text='Quitar',width=85,height=34,fg_color='#b91c1c',command=remove).grid(row=0,column=3,padx=(12,0))
            row['text']=Multiline(card,item['criterio'],height=85);row['text'].grid(row=1,column=0,sticky='ew',padx=12,pady=(0,8))
            if self.kind=='Rúbrica':
                table=ctk.CTkFrame(card,fg_color='transparent');table.grid(row=2,column=0,sticky='ew',padx=10,pady=(0,12));table.grid_columnconfigure((0,1,2,3),weight=1,uniform='niveles')
                row['descriptors']={};row['scores']={}
                for col,level in enumerate(LEVELS):
                    bg,fg=PALETTE[level];cell=ctk.CTkFrame(table,fg_color=bg,corner_radius=5);cell.grid(row=0,column=col,sticky='nsew',padx=3);cell.grid_columnconfigure(0,weight=1)
                    label(cell,f'{LEVEL_NAMES[level]} ({level})',text_color=fg).grid(row=0,column=0,sticky='ew',padx=8,pady=7)
                    text=Multiline(cell,item['descriptores'][level],height=125);text.grid(row=1,column=0,sticky='ew',padx=6,pady=4);row['descriptors'][level]=text
                    label(cell,'Puntos',text_color=fg).grid(row=2,column=0,sticky='ew',padx=8,pady=(4,0))
                    score=ctk.CTkEntry(cell,height=34,font=ctk.CTkFont(size=14));score.insert(0,number(item['puntajes'][level]));score.grid(row=3,column=0,sticky='ew',padx=8,pady=8);row['scores'][level]=score
                maximum.bind('<FocusOut>',lambda event,r=row:self.rescale(r),add='+')

    def save(self):
        self.capture()
        try:
            active=[r for r in self.rows if r['active']]
            values=[validate_definition(r['item'],self.limits) for r in active]
            app_storage.backup_database(self.app._db_path,'antes-editar-instrumento')
            ids=db.guardar_indicadores_instrumento_sesion(self.session,self.kind,values,self.app._db_path)
        except (ValueError,KeyError) as exc:messagebox.showwarning('Revise el instrumento',str(exc),parent=self);return
        origins={identity:r['source_index'] for identity,r in zip(ids,active)}
        order=[origins[i['id']] for i in get_indicators(self.session,self.app._db_path)]
        self.destroy();self.callback(order)
