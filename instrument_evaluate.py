"""Evaluate by student and observable criterion, without rebuilding a huge grid."""
from copy import deepcopy
from tkinter import ttk,messagebox
import customtkinter as ctk
import db
from evaluacion_datos import activity,get_indicators,get_answers,grade_answers
from instrumentos import definition,answer_points,LEVELS,rescale_answer
from instrument_widgets import InstrumentGrid,label,number
from instrument_design import InstrumentEditor,fit,header
from widgets import SafeDialog
from interfaz import split,scrollbar,pixel_scale
from grade_cells import grade_number


def student_id(row):return row.get('ID') or row.get('id_db') or row.get('estudiante_id')


def stage_to_grid(self,only_student=None,only_capacity=None):
    grades,pending=({},set()) if self.tipo_inst=='Lista de Cotejo' else grade_answers(self.indicadores_db,self.answers)
    tree=self.app.planilla_nativa
    for item in tree.get_children():
        row=list(tree.item(item,'values'));student=int(row[0])
        if only_student is not None and student!=only_student:continue
        for column,cap in enumerate(self.sesion['capacidades'],4):
            if only_capacity is not None and cap['capacidad_id']!=only_capacity:continue
            if self.tipo_inst=='Lista de Cotejo':continue
            key=(student,cap['capacidad_id'])
            if key in grades:row[column]=number(grades[key])
            else:
                identities=[i['id'] for i in self.indicadores_db if i['capacidad_id']==cap['capacidad_id']]
                previous=getattr(self.app,'_instrument_pending',{})
                if any((student,i) in self.original or (student,i) in previous for i in identities) and all(self.answers.get((student,i)) is None for i in identities):row[column]=''
        tree.item(item,values=row)
    self.app._instrument_pending_session=self.sesion['id']
    self.app._instrument_pending={(s,i):value for (s,i),value in self.answers.items() if i in self.by_id}
    self.app._loaded_instrument_kind=self.tipo_inst;self.app._loaded_ind_count=len(self.indicadores_db)
    self.app.calif_combo_modo_inst.set(self.tipo_inst);self.app.marcar_planilla_pendiente()
    return pending


class EvaluationActions:
    def commit_direct_entries(self):
        return self.grid_view.commit_entries()

    def _student_changed(self,event=None):
        selected=self.roster.selection()
        if not selected or int(selected[0])==self.current_student:return
        if not self.commit_direct_entries():
            if self.current_student is not None:self.roster.selection_set(str(self.current_student))
            return
        self.current_student=int(selected[0]);self._refresh()

    def _capacity_changed(self):
        if not self.commit_direct_entries():self.grid_view.choice.set(self.grid_view.rendered_capacity);return
        self.grid_view.render();self._refresh()

    def _move(self,delta):
        if not self.commit_direct_entries():return
        ids=list(self.by_student)
        if self.current_student not in ids:return
        index=max(0,min(len(ids)-1,ids.index(self.current_student)+delta))
        self.roster.selection_set(str(ids[index]));self.roster.focus(str(ids[index]));self.roster.see(str(ids[index]))

    def _choose(self,identity,value):
        if self.current_student is not None:self.set_answer(self.current_student,identity,value)

    def set_answer(self,student,identity,value):
        if student not in self.by_student or identity not in self.by_id:raise ValueError('Respuesta de otro estudiante o criterio.')
        item=self.by_id[identity]
        if value is not None:answer_points(self.tipo_inst,value,item['puntaje_maximo'],item['puntajes'])
        self.answers[(student,identity)]=value;self._refresh()

    def _refresh(self):
        if self.current_student is None:return
        student=self.by_student[self.current_student]
        self.student_title.configure(text=f"{student.get('Apellidos','')}, {student.get('Nombres','')}".strip(', '))
        self.grid_view.show_answers({i:self.answers.get((self.current_student,i)) for i in self.by_id})
        if self.tipo_inst=='Lista de Cotejo':
            from cotejo import summary
            cap=self.grid_view.capacities.get(self.grid_view.choice.get())
            state=summary(self.indicadores_db,self.answers,[self.current_student]).get((self.current_student,cap))
            self.progress.configure(text=f"Cumple {state['cumplidos']} de {state['evaluados']} evaluados · {state['pendientes']} pendientes · Sin conversión automática a nota" if state else 'Sin evaluar')
            for identity in self.by_student:
                count=sum(self.answers.get((identity,i)) is not None for i in self.by_id)
                self.roster.set(str(identity),'avance',f'{count}/{len(self.by_id)}')
            return
        grades,pending=grade_answers(self.indicadores_db,self.answers)
        cap=self.grid_view.capacities.get(self.grid_view.choice.get());value=grades.get((self.current_student,cap))
        items=[i for i in self.indicadores_db if i['capacidad_id']==cap]
        filled=[(i,self.answers.get((self.current_student,i['id']))) for i in items if self.answers.get((self.current_student,i['id'])) is not None]
        total=sum(answer_points(i['tipo'],v,i['puntaje_maximo'],i['puntajes']) for i,v in filled)
        maximum=sum(i['puntaje_maximo'] for i,v in filled)
        text=f'{len(filled)}/{len(items)} criterios · {number(total)}/{number(maximum)} puntos evaluados · '
        text+=f'Nota calculada: {number(value)} / 20' if value is not None else 'Capacidad pendiente.'
        if (self.current_student,cap) in pending:text+=' · Provisional: solo incluye los criterios evaluados.'
        tree=getattr(self.app,'planilla_nativa',None)
        if tree:
            column=next((n for n,c in enumerate(self.sesion['capacidades'],4) if c['capacidad_id']==cap),None)
            for iid in tree.get_children():
                values=tree.item(iid,'values')
                if int(values[0])==self.current_student and column is not None and str(values[column]).strip() and (value is None or grade_number(values[column])!=value):
                    text+=f'   Nota en la planilla: {values[column]} / 20.';break
        self.progress.configure(text=text)
        for identity in self.by_student:
            count=sum(self.answers.get((identity,i)) is not None for i in self.by_id)
            self.roster.set(str(identity),'avance',f'{count}/{len(self.by_id)}')

    def abrir_editor(self):
        if not self.app.verificar_permiso_edicion() or not self.commit_direct_entries():return
        previous=list(self.indicadores_db);retained=dict(self.answers)
        def reload(origins):
            new=get_indicators(self.sesion['id'],self.app._db_path);answers={}
            self.app.reconciliar_respuestas_pendientes(previous,new)
            for item,origin in zip(new,origins):
                if origin is not None:
                    old=previous[origin]['id']
                    for student in self.by_student:
                        if (student,old) in retained:answers[(student,item['id'])]=rescale_answer(retained[(student,old)],previous[origin],item)
            self._applied=True;self.destroy()
            InstrumentEvaluator(self.app,self.sesion,self.filas_estudiantes,self.tipo_inst,retained=answers)
        InstrumentEditor(self,self.sesion['id'],self.indicadores_db,reload,kind=self.tipo_inst)

    def _aplicar_calculo(self):
        if not self.app.verificar_permiso_edicion() or not self.commit_direct_entries():return
        if self.app.id_actividad_calificando!=self.sesion['id']:
            messagebox.showwarning('Actividad diferente','Abra esta actividad en Calificaciones antes de aplicar.',parent=self);return
        filled=any(v is not None and str(v).strip() for v in self.answers.values())
        if not filled and self.answers==self.original:
            messagebox.showwarning('Evaluación pendiente','Ingrese un puntaje o una observación de cotejo antes de aplicar.',parent=self);return
        if self.draft:
            rows=[{k:v for k,v in item.items() if k!='id'} for item in self.indicadores_db]
            ids=db.guardar_indicadores_instrumento_sesion(self.sesion['id'],self.tipo_inst,rows,self.app._db_path)
            mapping={old['id']:new for old,new in zip(self.indicadores_db,ids)}
            self.answers={(s,mapping[i]):v for (s,i),v in self.answers.items() if i in mapping}
            self.indicadores_db=get_indicators(self.sesion['id'],self.app._db_path);self.by_id={i['id']:i for i in self.indicadores_db}
        self.app.recordar_planilla()
        pending=stage_to_grid(self)
        self.app.actualizar_herramientas_evaluacion()
        if pending:self.app.lbl_estado.configure(text='Cambios pendientes · Nota provisional calculada con los criterios evaluados; los pendientes no cuentan como cero.')
        self._applied=True;self.destroy()

    def _close_requested(self):
        if not self.commit_direct_entries():return
        if self.answers!=self.initial and not self._applied:
            choice=messagebox.askyesnocancel('Evaluación sin aplicar','¿Desea aplicar sus cambios a la planilla antes de cerrar?',parent=self)
            if choice is None:return
            if choice:self._aplicar_calculo();return
        self.destroy()


class InstrumentEvaluator(EvaluationActions,SafeDialog):
    def __init__(self,app,session,students,kind,retained=None):
        super().__init__(app);self.app=app;self.sesion=session;self.filas_estudiantes=students;self.tipo_inst=kind
        self.title('Evaluar '+kind);fit(self,app,1260,780)
        self.context=activity(session['id'],app._db_path)
        self.indicadores_db=get_indicators(session['id'],app._db_path)
        self.draft=not self.indicadores_db
        if self.draft:
            for cap in self.context['capacidades']:
                texts=[cap['criterio_precisado'] or cap['capacidad_nombre']]
                if kind=='Lista de Cotejo':texts.append('Explica su respuesta usando la evidencia solicitada.')
                for text in texts:
                    identity=-(len(self.indicadores_db)+1)
                    self.indicadores_db.append(definition(dict(id=identity,capacidad_id=cap['capacidad_id'],capacidad_nombre=cap['capacidad_nombre'],tipo=kind,indicador_texto=text,puntaje_maximo=20 if kind=='Rúbrica' else 10)))
        if any(i['tipo']!=kind for i in self.indicadores_db):
            self.destroy();raise ValueError('Configure el instrumento del tipo seleccionado antes de evaluar.')
        self.original=get_answers(session['id'],app._db_path)
        self.answers=dict(self.original)
        if getattr(app,'_instrument_pending_session',None)==session['id']:self.answers.update(getattr(app,'_instrument_pending',{}))
        if retained is not None:self.answers.update(retained)
        self.initial=deepcopy(self.answers);self._applied=False
        self.by_id={i['id']:i for i in self.indicadores_db};self.by_student={student_id(s):s for s in students}
        self.current_student=next(iter(self.by_student),None)
        header(self,self.context)
        bar=ctk.CTkFrame(self,fg_color='transparent');bar.pack(fill='x',padx=16,pady=6)
        label(bar,'Escribe el puntaje directamente. Enter o Tab: confirmar y continuar. Vacío: pendiente; cero: sin evidencia.' if kind=='Rúbrica' else 'Seleccione un estudiante y marque la evidencia observada. Pendiente y cero se conservan como valores distintos.').pack(side='left',fill='x',expand=True)
        ctk.CTkButton(bar,text='Editar instrumento',height=36,command=self.abrir_editor).pack(side='right',padx=(12,0))
        pane=split(self,'evaluar_instrumento');pane.pack(fill='both',expand=True,padx=16,pady=8)
        left=ctk.CTkFrame(pane);left.grid_rowconfigure(0,weight=1);left.grid_columnconfigure(0,weight=1)
        self.roster=ttk.Treeview(left,columns=('codigo','nombre','avance'),show='headings',selectmode='browse')
        scale=pixel_scale(self)
        for key,text,width in [('codigo','Código',75),('nombre','Estudiante',170),('avance','Avance',75)]:
            self.roster.heading(key,text=text);self.roster.column(key,width=round(width*scale),minwidth=round((110 if key=='nombre' else width)*scale),stretch=key=='nombre')
        self.roster.grid(row=0,column=0,sticky='nsew');sy=scrollbar(left,'vertical',self.roster.yview);sy.grid(row=0,column=1,sticky='ns');self.roster.configure(yscrollcommand=sy.set)
        sx=scrollbar(left,'horizontal',self.roster.xview);sx.grid(row=1,column=0,sticky='ew');self.roster.configure(xscrollcommand=sx.set)
        right=ctk.CTkFrame(pane,fg_color='transparent');right.grid_rowconfigure(1,weight=1);right.grid_columnconfigure(0,weight=1)
        self.student_title=label(right,'');self.student_title.configure(font=ctk.CTkFont(size=18,weight='bold'));self.student_title.grid(row=0,column=0,sticky='ew',padx=10,pady=8)
        self.grid_view=InstrumentGrid(right,self.indicadores_db,on_choice=self._choose)
        self.grid_view.grid(row=1,column=0,sticky='nsew')
        self.grid_view.choice.configure(command=lambda _:self._capacity_changed())
        self.progress=label(right,'');self.progress.grid(row=2,column=0,sticky='ew',padx=10,pady=8)
        pane.add(left,width=round(350*scale),minsize=round(210*scale),stretch='never');pane.add(right,minsize=round(400*scale),stretch='always')
        for identity,student in self.by_student.items():
            name=f"{student.get('Apellidos','')}, {student.get('Nombres','')}".strip(', ') or student.get('nombre','')
            self.roster.insert('','end',iid=str(identity),values=(student.get('Codigo_Unico',''),name,''))
        self.roster.bind('<<TreeviewSelect>>',self._student_changed)
        footer=ctk.CTkFrame(self,fg_color='transparent');footer.pack(fill='x',padx=16,pady=(0,12))
        ctk.CTkButton(footer,text='Anterior',height=36,width=100,command=lambda:self._move(-1)).pack(side='left',padx=(0,6))
        ctk.CTkButton(footer,text='Siguiente',height=36,width=100,command=lambda:self._move(1)).pack(side='left')
        ctk.CTkButton(footer,text='Aplicar a la planilla',height=38,command=self._aplicar_calculo).pack(side='right')
        label(footer,'Después pulse Guardar notas.').pack(side='right',padx=12)
        if self.current_student is not None:self.roster.selection_set(str(self.current_student));self.roster.focus(str(self.current_student))
        self._refresh();self.protocol('WM_DELETE_WINDOW',self._close_requested);self.grab_set()
