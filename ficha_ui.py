"""A readable student profile with unit progress and saved evaluation evidence."""
from tkinter import messagebox
import customtkinter as ctk
import db,ficha_estudiante
from presentacion import MODES,format_grade
from colores import button
from modern_ui import card,caption,metric,table
from widgets import SafeDialog,polish_dialog


class StudentProfile(SafeDialog):
    def __init__(self,app,student=None):
        super().__init__(app);self.app=app;self.path=app._db_path;self.course=app.obtener_curso_activo_id();self.data=None
        self.title('Ficha del estudiante');self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(3,weight=1)
        header=card(self);header.grid(row=0,column=0,sticky='ew',padx=16,pady=(16,8));header.grid_columnconfigure(0,weight=1)
        caption(header,'Ficha del estudiante',large=True).grid(row=0,column=0,sticky='ew',padx=18,pady=(13,3))
        self.context=caption(header,'Resultados del periodo con datos guardados',muted=True);self.context.grid(row=1,column=0,sticky='ew',padx=18,pady=(0,13))
        selectors=ctk.CTkFrame(self,fg_color='transparent');selectors.grid(row=1,column=0,sticky='ew',padx=18,pady=8);selectors.grid_columnconfigure(0,weight=1)
        students=db.obtener_estudiantes_filtrados(app.combo_grado_global.get(),app.combo_seccion_global.get(),incluir_retirados=True,db_path=self.path)
        self.students={f"{n:02} · {s['Apellidos']}, {s['Nombres']}":s['ID'] for n,s in enumerate(students,1)}
        self.choice=ctk.CTkComboBox(selectors,values=list(self.students) or ['No hay estudiantes en este salón'],state='readonly',command=lambda v:self.refresh(),height=37)
        self.choice.grid(row=0,column=0,sticky='ew',padx=(0,10))
        self.choice.set(next((k for k,v in self.students.items() if v==student),next(iter(self.students),'No hay estudiantes en este salón')))
        self.display=ctk.CTkComboBox(selectors,values=list(MODES),state='readonly',width=145,command=lambda v:self.refresh());self.display.grid(row=0,column=1,padx=5)
        self.display.set(next(k for k,v in MODES.items() if v==getattr(app,'_grade_display','ambos')))
        self.metrics=ctk.CTkFrame(self,fg_color='transparent');self.metrics.grid(row=2,column=0,sticky='ew',padx=13,pady=7);self.metrics.grid_columnconfigure((0,1,2),weight=1,uniform='ficha')
        self.values=[]
        for n,title in enumerate(('Resultado del curso','Actividades con evidencias','Asistencias registradas')):
            frame,value=metric(self.metrics,title,'—');frame.grid(row=0,column=n,sticky='nsew',padx=5);self.values.append(value)
        tabs=ctk.CTkTabview(self,fg_color=('#ffffff','#17283b'),segmented_button_fg_color=('#e0f2fe','#0c4a6e'),
            segmented_button_selected_color=('#7dd3fc','#0369a1'),segmented_button_selected_hover_color=('#38bdf8','#0284c7'),
            segmented_button_unselected_color=('#e0f2fe','#0c4a6e'),text_color=('#075985','#f0f9ff'))
        tabs.grid(row=3,column=0,sticky='nsew',padx=16,pady=8)
        units=tabs.add('Progreso por unidad');grades=tabs.add('Evaluaciones');attendance=tabs.add('Asistencia y comentarios')
        self.units=self.add_table(units,[('unidad','Unidad',350),('promedio','Resultado',150),('avance','Actividades con evidencias',200)])
        self.grades=self.add_table(grades,[('fecha','Fecha',100),('actividad','Actividad',250),('unidad','Unidad',180),('capacidad','Capacidad',360),('nota','Resultado',135)])
        self.attendance=self.add_table(attendance,[('fecha','Fecha',100),('actividad','Actividad',260),('asistencia','Asistencia',135),('comentario','Comentario',500)])
        self.grades.bind('<Double-1>',lambda e:self.open_activity())
        actions=ctk.CTkFrame(self,fg_color='transparent');actions.grid(row=4,column=0,sticky='ew',padx=18,pady=14)
        ctk.CTkButton(actions,text='Abrir evaluación seleccionada',**button(),command=self.open_activity,width=230).pack(side='left',padx=4)
        self.export_button=ctk.CTkButton(actions,text='Descargar ficha Excel',**button(),command=self.export);self.export_button.pack(side='right',padx=4)
        self.refresh();polish_dialog(self,app,1190,790);app._student_profile=self

    def add_table(self,parent,columns):
        parent.grid_columnconfigure(0,weight=1);parent.grid_rowconfigure(0,weight=1)
        frame,tree=table(parent,columns);frame.grid(row=0,column=0,sticky='nsew');return tree

    def refresh(self):
        for tree in (self.units,self.grades,self.attendance):tree.delete(*tree.get_children())
        identity=self.students.get(self.choice.get());self.activity_rows={}
        if not identity or not self.course:self.export_button.configure(state='disabled');return
        self.export_button.configure(state='normal');self.data=ficha_estudiante.snapshot(self.path,identity,self.course)
        data=self.data;pupil=data['estudiante'];mode=MODES[self.display.get()]
        shown=lambda value:format_grade(value,mode,self.path)
        self.context.configure(text=f"{data['contexto']['school_name']} · {data['contexto']['label']} · {data['curso']} · {pupil['Grado']} {pupil['Seccion']} · Datos guardados")
        evaluated=sum(bool(a['criterios_evaluados']) or any(n['nota'] is not None for n in a['notas']) for a in data['actividades'])
        self.values[0].configure(text=shown(data['matriz']['promedio_general']))
        self.values[1].configure(text=f"{evaluated} de {len(data['actividades'])}")
        self.values[2].configure(text=f"{data['asistencias']} de {data['asistencias_registradas']}")
        for unit in data['unidades']:self.units.insert('','end',values=(unit['nombre'],shown(unit['promedio']),f"{unit['evaluadas']} de {unit['actividades']}"))
        for activity in data['actividades']:
            for note in activity['notas'] or [dict(capacidad='Criterios observados' if activity['criterios_evaluados'] else 'Sin calificar',nota=None)]:
                row=self.grades.insert('','end',values=(activity['fecha'],activity['titulo_tema'],activity['unidad'],note['capacidad'],shown(note['nota'])))
                self.activity_rows[row]=activity['id']
            attendance='Sin registrar' if activity['asistio'] is None else 'Presente' if activity['asistio'] else 'Ausente'
            self.attendance.insert('','end',values=(activity['fecha'],activity['titulo_tema'],attendance,activity['comentario'] or ''))

    def open_activity(self):
        selected=self.grades.selection()
        if not selected:return
        target=self.activity_rows[selected[0]]
        if not self.app.confirmar_descartar(include_points=True):return
        self.destroy();self.app.abrir_actividad_en_pestana_calificar(target)

    def export(self):
        if not self.data:return
        pupil=self.data['estudiante']
        import re
        name=re.sub(r'[<>:"/\\|?*]','_',pupil['Apellidos']+' '+pupil['Nombres'])
        path=self.app.elegir_destino(title='Guardar ficha del estudiante',initialfile='Ficha - '+name+'.xlsx',defaultextension='.xlsx',filetypes=[('Ficha Excel','*.xlsx')])
        if not path:return
        try:
            ficha_estudiante.export_excel(path,self.data,self.path,MODES[self.display.get()])
            import reportes
            reportes.decorate_workbook(path,self.app.insignia_exportacion());self.app.archivo_guardado(path,'Ficha con resultados, progreso por unidad y asistencia.')
        except Exception as exc:messagebox.showerror('Ficha del estudiante',str(exc),parent=self)
