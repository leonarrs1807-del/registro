"""Small export choices and an explicit preview of adapted Excel tables."""
from tkinter import ttk
import customtkinter as ctk
from colores import button as sky_button,tabs as sky_tabs
from widgets import SafeDialog,wrap_label,scroll_area
from instrument_design import fit
from interfaz import scrollbar
from evaluacion_datos import activity,get_indicators,get_answers
from db_safety import connection


class GradeDisplayOptions(SafeDialog):
    def __init__(self,app):
        super().__init__(app);self.title('Cómo mostrar las notas en Excel');fit(self,app,650,470)
        self.result=None;self.ready=False
        body=scroll_area(self,auto_hide=True);body.pack(fill='both',expand=True,padx=8,pady=8)
        ctk.CTkLabel(body,text='Elija el formato de la matriz final',font=ctk.CTkFont(size=18,weight='bold')).pack(padx=20,pady=(20,12))
        self.scope_choice=ctk.StringVar(value='actual')
        if hasattr(app,'nombre_alcance'):
            ctk.CTkLabel(body,text='Selección actual: '+app.nombre_alcance(),wraplength=560).pack(padx=20,pady=4)
            if app.alcance_unidad()!='all':
                ctk.CTkRadioButton(body,text='Descargar solo la unidad seleccionada',variable=self.scope_choice,value='actual').pack(anchor='w',padx=35,pady=5)
                ctk.CTkRadioButton(body,text='Descargar todo el bimestre / trimestre',variable=self.scope_choice,value='all').pack(anchor='w',padx=35,pady=5)
        self.choice=ctk.StringVar(value=getattr(app,'_grade_display','numero'))
        for value,title in [('numero','Solo números · 17'),('letra','Solo letras · A'),('ambos','Número y letra · 17 (A)')]:
            ctk.CTkRadioButton(body,text=title,variable=self.choice,value=value).pack(anchor='w',padx=35,pady=10)
        bar=ctk.CTkFrame(self,fg_color='transparent');bar.pack(fill='x',padx=20,pady=15)
        ctk.CTkButton(bar,**sky_button(),text='Cancelar',width=100,command=self.destroy).pack(side='left')
        ctk.CTkButton(bar,**sky_button(),text='Continuar',command=self.confirm).pack(side='right');self.grab_set();self.ready=True

    def confirm(self):self.result=self.choice.get();self.destroy()


class TableImportPreview(SafeDialog):
    def __init__(self,app,staged,result):
        super().__init__(app);self.ready=False;self.confirmed=False;self.title('Revisar tabla y elementos nuevos');fit(self,app,1100,740)
        context=activity(result.session_id,staged)
        title=ctk.CTkLabel(self,text=context['titulo_tema']+'\nCompetencia: '+context['competencia_nombre'],anchor='w',justify='left',font=ctk.CTkFont(size=17,weight='bold'))
        title.pack(fill='x',padx=18,pady=10);wrap_label(title)
        ctk.CTkLabel(self,text=f'{result[1]} estudiantes · {result[0]} criterios o capacidades · {len(result.changes)} elementos nuevos').pack(anchor='w',padx=18)
        tabs=ctk.CTkTabview(self);tabs.pack(fill='both',expand=True,padx=15,pady=8)
        changes=tabs.add('Elementos que se agregarán');changes.grid_columnconfigure(0,weight=1);changes.grid_rowconfigure(0,weight=1)
        tree=ttk.Treeview(changes,columns=('detail',),show='headings');tree.heading('detail',text='Competencias, capacidades, criterios, actividades y estudiantes nuevos');tree.column('detail',width=950)
        for change in result.changes or ['No se necesitan elementos nuevos; se actualizarán las notas y observaciones.']:tree.insert('','end',values=(change,))
        tree.grid(row=0,column=0,sticky='nsew');sy=scrollbar(changes,'vertical',tree.yview);sy.grid(row=0,column=1,sticky='ns');tree.configure(yscrollcommand=sy.set)
        values=tabs.add('Notas y observaciones');values.grid_columnconfigure(0,weight=1);values.grid_rowconfigure(0,weight=1)
        table=ttk.Treeview(values,columns=('name','capacity','criterion','answer'),show='headings')
        for col,caption,width in [('name','Estudiante',240),('capacity','Capacidad',320),('criterion','Criterio',340),('answer','Respuesta / nota',150)]:table.heading(col,text=caption);table.column(col,width=width)
        table.grid(row=0,column=0,sticky='nsew');sy=scrollbar(values,'vertical',table.yview);sy.grid(row=0,column=1,sticky='ns');sx=scrollbar(values,'horizontal',table.xview);sx.grid(row=1,column=0,sticky='ew');table.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        with connection(staged) as conn:
            names={r[0]:r[1]+', '+r[2] for r in conn.execute('SELECT ID,Apellidos,Nombres FROM Estudiantes')}
            notes=conn.execute('SELECT estudiante_id,capacidad_id,nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',(result.session_id,)).fetchall()
        items={i['id']:i for i in get_indicators(result.session_id,staged)}
        for (student,identity),answer in get_answers(result.session_id,staged).items():
            item=items[identity];table.insert('','end',values=(names[student],item['capacidad_nombre'],item['criterio'],answer))
        caps={c['capacidad_id']:c['capacidad_nombre'] for c in context['capacidades']}
        for student,cap,note in notes:
            if note is not None:table.insert('','end',values=(names[student],caps[cap],'Nota de capacidad',note))
        bar=ctk.CTkFrame(self,fg_color='transparent');bar.pack(fill='x',padx=18,pady=12)
        ctk.CTkButton(bar,**sky_button(),text='Cancelar',width=120,command=self.destroy).pack(side='left')
        ctk.CTkButton(bar,**sky_button(),text='Importar y agregar lo que falta',width=260,command=self.confirm).pack(side='right');self.grab_set();self.ready=True

    def confirm(self):self.confirmed=True;self.destroy()
