"""Readable settings and instrument editors with content that fits the window."""
from tkinter import messagebox
import customtkinter as ctk
import db,app_storage
from db_safety import valid_number
from escala import thresholds,save_thresholds
from widgets import scroll_area,wrap_label,SafeDialog
from grade_cells import PALETTE,grade_number


def fit_dialog(window,root,width,height):
    scale=window._get_window_scaling()
    window.geometry(f'{min(width,int(root.winfo_screenwidth()/scale*.92))}x{min(height,int(root.winfo_screenheight()/scale*.85))}')
    window.transient(root)


class ScaleDialog(SafeDialog):
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


from instrument_design import InstrumentEditor
