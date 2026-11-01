"""Readable settings and instrument editors with content that fits the window."""
from tkinter import messagebox
import customtkinter as ctk
import db,app_storage
from db_safety import valid_number
from escala import thresholds,save_thresholds
from widgets import scroll_area,wrap_label
from grade_cells import PALETTE,grade_number


def fit_dialog(window,root,width,height):
    scale=window._get_window_scaling()
    window.geometry(f'{min(width,int(root.winfo_screenwidth()/scale*.92))}x{min(height,int(root.winfo_screenheight()/scale*.85))}')
    window.transient(root)


class ScaleDialog(ctk.CTkToplevel):
    def __init__(self,app):
        super().__init__(app);self.app=app;self.title('Niveles de logro')
        fit_dialog(self,app,560,470)
        body=scroll_area(self,auto_hide=True);body.pack(fill='both',expand=True);body.grid_columnconfigure(1,weight=1)
        level=db.obtener_docente_config().get('nivel_educativo','Secundaria')
        ctk.CTkLabel(body,text=f'Escala de {level}',font=ctk.CTkFont(size=20,weight='bold')).grid(row=0,column=0,columnspan=2,padx=18,pady=14,sticky='w')
        text=ctk.CTkLabel(body,text='Defina desde qué nota empiezan B, A y AD. C corresponde a las notas inferiores a B. Las notas numéricas se conservan.',justify='left',wraplength=470,font=ctk.CTkFont(size=15))
        text.grid(row=1,column=0,columnspan=2,padx=18,pady=6,sticky='ew');wrap_label(text)
        self.entries=[]
        for row,(name,value) in enumerate(zip(('B','A','AD'),thresholds(app._db_path)),2):
            bg,fg=PALETTE[name]
            ctk.CTkLabel(body,text=f'{name} empieza en',fg_color=bg,text_color=fg,corner_radius=6,font=ctk.CTkFont(size=15)).grid(row=row,column=0,padx=18,pady=9,sticky='ew')
            entry=ctk.CTkEntry(body,height=38,font=ctk.CTkFont(size=16));entry.insert(0,str(value));entry.grid(row=row,column=1,padx=(0,18),pady=9,sticky='ew');self.entries.append(entry)
        ctk.CTkButton(body,text='Guardar escala',height=38,font=ctk.CTkFont(size=15),command=self.save).grid(row=6,column=0,columnspan=2,padx=18,pady=18,sticky='ew')
        self.grab_set()

    def save(self):
        try:
            values=[valid_number(e.get().replace(',','.'),0,20,'Límite') for e in self.entries]
            if not values[0]<values[1]<values[2]:raise ValueError('Los límites deben cumplir B < A < AD.')
        except ValueError as exc:messagebox.showwarning('Revise la escala',str(exc),parent=self);return
        app_storage.backup_database(self.app._db_path,'antes-cambiar-escala');save_thresholds(self.app._db_path,values)
        tree=getattr(self.app,'planilla_nativa',None)
        if tree:
            for item in tree.get_children():
                row=list(tree.item(item,'values'))
                for i in range(4,len(row)-1):
                    if '(' in str(row[i]):
                        number=grade_number(row[i])
                        if number is not None:row[i]=f"{str(number).removesuffix('.0')} ({db.nota_a_literal(number)})"
                tree.item(item,values=row)
            tree.queue_colors()
        self.app.recargar_matriz_completa()
        if getattr(self.app.puntos_panel,'grid_view',None):self.app.puntos_panel.identity.queue_colors()
        self.destroy()


class InstrumentEditor(ctk.CTkToplevel):
    def __init__(self,master,session,indicators,callback):
        super().__init__(master);self.app=getattr(master,'app',master)
        self.title('Editar indicadores');fit_dialog(self,self.app,850,650)
        self.session=session;self.callback=callback;self.kind=indicators[0]['tipo'] if indicators else getattr(master,'tipo_inst','Rúbrica')
        with db.obtener_conexion() as conn:
            self.capacities={name:cid for cid,name in conn.execute('SELECT a.id,a.nombre FROM Capacidades a JOIN Sesion_Capacidades s ON s.capacidad_id=a.id WHERE s.sesion_id=?',(session,))}
        self.rows=[]
        bar=ctk.CTkFrame(self,fg_color='transparent');bar.pack(fill='x',padx=14,pady=12)
        ctk.CTkButton(bar,text='Añadir indicador',height=36,command=lambda:self.add_row()).pack(side='left')
        ctk.CTkButton(bar,text='Guardar instrumento',height=36,command=self.save).pack(side='right')
        self.body=scroll_area(self,auto_hide=True);self.body.pack(fill='both',expand=True,padx=14,pady=(0,14));self.body.grid_columnconfigure(0,weight=1)
        for index,item in enumerate(indicators):self.add_row({**item,'source_index':index})
        self.grab_set()

    def add_row(self,item=None):
        item=item or dict(capacidad_id=next(iter(self.capacities.values())),indicador_texto='',puntaje_maximo=20 if self.kind=='Rúbrica' else 10)
        card=ctk.CTkFrame(self.body);card.grid(row=len(self.rows),column=0,sticky='ew',pady=8);card.grid_columnconfigure(0,weight=1)
        choice=ctk.CTkComboBox(card,values=list(self.capacities),state='readonly',height=36,font=ctk.CTkFont(size=14))
        choice.set(next((name for name,cid in self.capacities.items() if cid==item['capacidad_id']),next(iter(self.capacities))))
        choice.grid(row=0,column=0,columnspan=3,sticky='ew',padx=12,pady=10)
        text=ctk.CTkTextbox(card,height=110,wrap='word',font=ctk.CTkFont(size=15));text.insert('1.0',item['indicador_texto']);text.grid(row=1,column=0,columnspan=3,sticky='ew',padx=12,pady=4)
        ctk.CTkLabel(card,text='Máximo',font=ctk.CTkFont(size=14)).grid(row=2,column=0,padx=12,pady=8,sticky='w')
        maximum=ctk.CTkEntry(card,width=90,height=36,font=ctk.CTkFont(size=15));maximum.insert(0,str(item['puntaje_maximo']));maximum.grid(row=2,column=1,pady=8)
        record=dict(card=card,choice=choice,text=text,maximum=maximum,active=True,source_index=item.get('source_index'))
        def remove():record['active']=False;card.grid_remove()
        ctk.CTkButton(card,text='Quitar',width=90,height=36,command=remove).grid(row=2,column=2,padx=12,pady=8)
        self.rows.append(record)

    def save(self):
        values=[];origins=[]
        try:
            for row in self.rows:
                if row['active']:
                    text=row['text'].get('1.0','end').strip()
                    if not text:raise ValueError('Cada indicador necesita un texto.')
                    values.append((self.capacities[row['choice'].get()],text,valid_number(row['maximum'].get().replace(',','.'),.000001,20,'Máximo')))
                    origins.append((values[-1][0],len(origins),row['source_index']))
            if not values:raise ValueError('Conserve al menos un indicador.')
            app_storage.backup_database(self.app._db_path,'antes-editar-instrumento')
            db.guardar_indicadores_instrumento_sesion(self.session,self.kind,values)
        except ValueError as exc:messagebox.showwarning('Revise los indicadores',str(exc),parent=self);return
        self.destroy();self.callback([origin for cap,index,origin in sorted(origins)])
