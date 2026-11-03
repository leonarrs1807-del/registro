"""Review a checklist conversion before it can affect saved grades."""
from tkinter import ttk,messagebox
import customtkinter as ctk
from widgets import SafeDialog,scroll_area
from instrument_widgets import label,number
from instrument_design import fit
from interfaz import scrollbar
from cotejo import summary,preview,configuration,validate_rule,review_signature


class ChecklistConversion(SafeDialog):
    OPTIONS={'Seleccione una regla':None,'Proporcional: cumplimiento × 20':'proporcional',
             'Tabla de cumplimiento definida por mí':'tramos','Solo orientación: retirar notas de esta actividad':'orientacion'}
    def __init__(self,panel):
        super().__init__(panel.app);self.panel=panel;self.title('Revisar conversión del cotejo');fit(self,panel.app,1080,720)
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(4,weight=1)
        label(self,'Convertir observaciones a nota es opcional. Se revisa por capacidad y se confirma antes de guardar.').grid(row=0,column=0,sticky='ew',padx=16,pady=(14,6))
        self.choice=ctk.CTkComboBox(self,values=list(self.OPTIONS),state='readonly',width=400,height=36,command=lambda _:self._change())
        self.choice.grid(row=1,column=0,sticky='ew',padx=16,pady=5);self.choice.set('Seleccione una regla')
        self.custom=ctk.CTkFrame(self);self.custom.grid(row=2,column=0,sticky='ew',padx=16,pady=5)
        label(self.custom,'Mi tabla: porcentaje mínimo de cumplimiento → nota / 20. Complete al menos dos filas.').grid(row=0,column=0,columnspan=4,sticky='ew',padx=8,pady=4)
        self.ranges=[]
        for n in range(4):
            percent=ctk.CTkEntry(self.custom,width=90,placeholder_text='% mínimo');percent.grid(row=1,column=2*n,padx=5,pady=5)
            grade=ctk.CTkEntry(self.custom,width=90,placeholder_text='Nota / 20');grade.grid(row=1,column=2*n+1,padx=5,pady=5)
            self.ranges.append((percent,grade))
        self.ranges[0][0].insert(0,'0')
        self.status=label(self,'Los pendientes se guardan como observaciones y no se convierten en cero.');self.status.grid(row=3,column=0,sticky='ew',padx=16,pady=5)
        frame=ctk.CTkFrame(self,fg_color='transparent');frame.grid(row=4,column=0,sticky='nsew',padx=16,pady=5);frame.grid_columnconfigure(0,weight=1);frame.grid_rowconfigure(0,weight=1)
        self.tree=ttk.Treeview(frame,columns=('student','cap','fulfilled','pending','grade'),show='headings')
        for key,text,width in [('student','Estudiante',230),('cap','Capacidad',350),('fulfilled','Cumple / Eval.',130),('pending','Pendientes',100),('grade','Nota propuesta',140)]:
            self.tree.heading(key,text=text);self.tree.column(key,width=width,minwidth=80,stretch=key in ('student','cap'))
        self.tree.grid(row=0,column=0,sticky='nsew');sy=scrollbar(frame,'vertical',self.tree.yview);sy.grid(row=0,column=1,sticky='ns');self.tree.configure(yscrollcommand=sy.set)
        sx=scrollbar(frame,'horizontal',self.tree.xview);sx.grid(row=1,column=0,sticky='ew');self.tree.configure(xscrollcommand=sx.set)
        bar=ctk.CTkFrame(self,fg_color='transparent');bar.grid(row=5,column=0,sticky='ew',padx=16,pady=12)
        ctk.CTkButton(bar,text='Cancelar',width=110,command=self.destroy).pack(side='left')
        ctk.CTkButton(bar,text='Ver vista previa',width=145,command=self.review).pack(side='left',padx=8)
        self.confirm_button=ctk.CTkButton(bar,text='Confirmar en planilla',state='disabled',command=self.confirm);self.confirm_button.pack(side='right')
        self.reviewed=None;self.custom.grid_remove();self._populate({});self.grab_set()

    def _change(self):
        if self.OPTIONS[self.choice.get()]=='tramos':self.custom.grid()
        else:self.custom.grid_remove()
        self.reviewed=None;self.confirm_button.configure(state='disabled');self._populate({})

    def rule(self):
        kind=self.OPTIONS[self.choice.get()]
        if kind is None:raise ValueError('Seleccione una regla. El cotejo puede mantenerse solo como orientación.')
        rows=[]
        for percent,grade in self.ranges:
            if percent.get().strip() or grade.get().strip():rows.append(dict(minimo=percent.get().replace(',','.'),nota=grade.get().replace(',','.')))
        return validate_rule(dict(tipo=kind,tramos=rows))

    def _populate(self,grades):
        self.tree.delete(*self.tree.get_children())
        state=summary(self.panel.indicadores_db,self.panel.answers,self.panel.by_student)
        caps={i['capacidad_id']:i['capacidad_nombre'] for i in self.panel.indicadores_db}
        for (student,cap),row in state.items():
            s=self.panel.by_student[student];value=grades.get((student,cap))
            self.tree.insert('','end',values=(f"{s.get('Apellidos','')}, {s.get('Nombres','')}",caps[cap],f"{row['cumplidos']}/{row['evaluados']}",row['pendientes'],number(value) if value is not None else 'Sin nota'))

    def review(self):
        try:
            rule=self.rule();grades=preview(self.panel.indicadores_db,self.panel.answers,rule,self.panel.by_student)
        except (ValueError,KeyError,TypeError) as exc:
            self.confirm_button.configure(state='disabled');messagebox.showwarning('Regla de conversión',str(exc),parent=self);return False
        self._populate(grades)
        self.status.configure(text='Se retirarán las notas de esta actividad; se conservarán todas las observaciones.' if rule['tipo']=='orientacion' else f'{len(grades)} notas propuestas. Solo se convierten las capacidades completamente evaluadas. Después pulse Guardar cambios.')
        self.reviewed=(rule,dict(self.panel.answers),grades);self.confirm_button.configure(state='normal');return True

    def confirm(self):
        if not self.panel.app.verificar_permiso_edicion():return
        try:rule=self.rule()
        except ValueError:return
        if self.reviewed is None or self.reviewed[0]!=rule or self.reviewed[1]!=self.panel.answers:
            messagebox.showwarning('Revisar cambios','Cambió la regla o las respuestas. Revise otra vez la vista previa.',parent=self);return
        grades=self.reviewed[2]
        if not grades and rule['tipo']!='orientacion':
            messagebox.showwarning('Cotejo pendiente','Complete al menos una capacidad antes de convertirla.',parent=self);return
        app=self.panel.app;app.recordar_planilla()
        for iid in app.planilla_nativa.get_children():
            row=list(app.planilla_nativa.item(iid,'values'));student=int(row[0])
            for col,cap in enumerate(self.panel.sesion['capacidades'],4):
                key=(student,cap['capacidad_id'])
                if rule['tipo']=='orientacion':row[col]=''
                elif key in grades:row[col]=number(grades[key])
            app.planilla_nativa.item(iid,values=row)
        app._cotejo_pending_rule={**rule,'_respuestas':review_signature(self.panel.indicadores_db,self.panel.answers)};app.marcar_planilla_pendiente();self.panel._refresh()
        app.actualizar_herramientas_evaluacion()
        app.lbl_estado.configure(text='Conversión revisada: pulse Guardar cambios para confirmar.' if rule['tipo']!='orientacion' else 'Solo orientación: pulse Guardar cambios para confirmar.');self.destroy()
