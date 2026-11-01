"""An embedded evaluation workspace: every criterion is answered before its total."""
from tkinter import ttk
import customtkinter as ctk
from instrument_evaluate import EvaluationActions,stage_to_grid,student_id
from instrument_widgets import InstrumentGrid,label
from evaluacion_datos import get_answers
from instrumentos import answer_points
from interfaz import split,scrollbar,pixel_scale
from widgets import prepare_destroy


class EvaluationPanel(EvaluationActions,ctk.CTkFrame):
    def __init__(self,master,app,session,students,indicators):
        super().__init__(master,fg_color='transparent')
        self.app=app;self.sesion=session;self.filas_estudiantes=students;self.indicadores_db=indicators
        self.tipo_inst=indicators[0]['tipo'];self.draft=False
        self.by_id={i['id']:i for i in indicators};self.by_student={student_id(s):s for s in students}
        self.current_student=next(iter(self.by_student),None);self.original={};self.answers={};self._resize_job=None
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(1,weight=1)
        self.students_bar=ctk.CTkFrame(app._criteria_view_bar,fg_color='transparent')
        self.students_bar.grid_columnconfigure(1,weight=1)
        label(self.students_bar,'Estudiante').grid(row=0,column=0,padx=(0,8))
        self.student_labels={f"{s.get('Codigo_Unico','')} · {s.get('Apellidos','')}, {s.get('Nombres','')}":identity for identity,s in self.by_student.items()}
        self.student_choice=ctk.CTkComboBox(self.students_bar,values=list(self.student_labels),height=36,state='readonly',command=lambda caption:self.select_student(self.student_labels[caption]))
        self.student_choice.grid(row=0,column=1,sticky='ew')
        self.pane=split(self,'criterios_principal');self.pane.grid(row=1,column=0,sticky='nsew',padx=4,pady=4)
        self.left=ctk.CTkFrame(self.pane);self.left.grid_rowconfigure(0,weight=1);self.left.grid_columnconfigure(0,weight=1)
        self.roster=ttk.Treeview(self.left,columns=('codigo','nombre','avance'),show='headings',selectmode='browse')
        scale=pixel_scale(self)
        for key,title,width in [('codigo','Código',65),('nombre','Estudiante',160),('avance','Eval.',65)]:
            self.roster.heading(key,text=title);self.roster.column(key,width=round(width*scale),minwidth=round((90 if key=='nombre' else width)*scale),stretch=key=='nombre')
        self.roster.grid(row=0,column=0,sticky='nsew')
        sy=scrollbar(self.left,'vertical',self.roster.yview);sy.grid(row=0,column=1,sticky='ns')
        sx=scrollbar(self.left,'horizontal',self.roster.xview);sx.grid(row=1,column=0,sticky='ew')
        self.roster.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        right=ctk.CTkFrame(self.pane,fg_color='transparent');right.grid_columnconfigure(0,weight=1);right.grid_rowconfigure(1,weight=1)
        self.student_title=label(right,'');self.student_title.configure(font=ctk.CTkFont(size=16,weight='bold'))
        self.student_title.grid(row=0,column=0,sticky='ew',padx=8,pady=(4,2))
        self.grid_view=InstrumentGrid(right,indicators,on_choice=self._choose);self.grid_view.grid(row=1,column=0,sticky='nsew')
        self.grid_view.choice.configure(command=lambda _:self._capacity_changed())
        self.progress=label(right,'');self.progress.grid(row=2,column=0,sticky='ew',padx=8,pady=6)
        self.pane.add(self.left,width=round(300*scale),minsize=round(210*scale),stretch='never')
        self.pane.add(right,minsize=round(360*scale),stretch='always')
        self._right=right
        for identity,student in self.by_student.items():self.roster.insert('','end',iid=str(identity),values=(student.get('Codigo_Unico',''),f"{student.get('Apellidos','')}, {student.get('Nombres','')}",''))
        self.roster.bind('<<TreeviewSelect>>',self._student_changed)
        footer=ctk.CTkFrame(self,fg_color='transparent');footer.grid(row=2,column=0,sticky='ew',padx=8,pady=5)
        ctk.CTkButton(footer,text='Anterior',width=90,height=32,command=lambda:self._move(-1)).pack(side='left',padx=(0,6))
        ctk.CTkButton(footer,text='Siguiente',width=90,height=32,command=lambda:self._move(1)).pack(side='left')
        ctk.CTkButton(footer,text='Recalcular resultados',width=165,height=32,command=self._aplicar_calculo).pack(side='right')
        self.reload_from_root(saved=True)
        if self.current_student is not None:self.select_student(self.current_student)
        self.bind('<Configure>',self._queue_layout,add='+');self._queue_layout()

    def select_student(self,student,capacity=None):
        if student not in self.by_student:return
        self.current_student=student;self.roster.selection_set(str(student));self.roster.focus(str(student));self.roster.see(str(student))
        if capacity is not None:
            caption=next((name for name,identity in self.grid_view.capacities.items() if identity==capacity),None)
            if caption and caption!=self.grid_view.choice.get():self.grid_view.choice.set(caption);self.grid_view.render()
        self._refresh()

    def _refresh(self):
        super()._refresh()
        caption=next((name for name,student in self.student_labels.items() if student==self.current_student),'')
        self.student_choice.set(caption)

    def reload_from_root(self,saved=False):
        if saved:self.original=get_answers(self.sesion['id'],self.app._db_path)
        answers=dict(self.original)
        if getattr(self.app,'_instrument_pending_session',None)==self.sesion['id']:answers.update(getattr(self.app,'_instrument_pending',{}))
        self.answers={(s,i):v for (s,i),v in answers.items() if s in self.by_student and i in self.by_id}
        self._refresh()

    def set_answer(self,student,identity,value):
        if not self.app.verificar_permiso_edicion():self._refresh();return
        if student not in self.by_student or identity not in self.by_id:raise ValueError('Respuesta de otro estudiante o criterio.')
        item=self.by_id[identity]
        if value is not None:answer_points(item['tipo'],value,item['puntaje_maximo'],item['puntajes'])
        if self.answers.get((student,identity))==value:self._refresh();return
        self.app.recordar_planilla();self.answers[(student,identity)]=value
        stage_to_grid(self,only_student=student,only_capacity=item['capacidad_id']);self._refresh()

    def _aplicar_calculo(self):
        if not self.app.verificar_permiso_edicion():return
        self.app.recordar_planilla();stage_to_grid(self);self._refresh()

    def abrir_editor(self):self.app.configurar_instrumento()

    def _queue_layout(self,event=None):
        if getattr(self,'_destroying',False) or getattr(self.app,'_closing_ui',False):return
        if self._resize_job:self.after_cancel(self._resize_job)
        self._resize_job=self.after(90,self._layout)

    def _layout(self):
        self._resize_job=None
        compact=self.winfo_width()/pixel_scale(self)<1050
        key=(compact,self.app._evaluation_view)
        if key==getattr(self,'_layout_state',None):return
        self._layout_state=key
        if key[1]!='criteria':self.students_bar.grid_remove();self.app._criteria_view_caption.grid();return
        if compact:
            self.pane.forget(self.left);self.students_bar.grid(row=0,column=1,sticky='ew',padx=8,pady=4)
            self.app._criteria_view_caption.grid_remove();self.student_title.grid_remove()
        else:
            self.pane.add(self.left,before=self._right,width=round(300*pixel_scale(self)),minsize=round(210*pixel_scale(self)),stretch='never')
            self.students_bar.grid_remove();self.app._criteria_view_caption.grid();self.student_title.grid()

    def destroy(self):
        if getattr(self,'_destroying',False):return
        self._destroying=True
        if self._resize_job:
            try:self.after_cancel(self._resize_job)
            except Exception:pass
        if self.students_bar.winfo_exists():self.students_bar.destroy()
        prepare_destroy(self);super().destroy()
