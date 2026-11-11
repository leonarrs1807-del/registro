"""Portable Excel instruments and previewed clipboard entry."""
import csv,io,re
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
import customtkinter as ctk
from widgets import SafeDialog,wrap_label,polish_dialog
from colores import button


class TeacherWorkflowTools:
    def terminar_edicion_actual(self):
        panel=getattr(self,'_global_grade_panel',None)
        if panel and panel.winfo_exists() and not panel.commit():return False
        embedded=getattr(self,'_embedded_evaluation',None)
        if embedded and embedded.winfo_exists() and not embedded.commit_direct_entries():return False
        matrix=getattr(embedded,'matrix',None)
        if matrix and matrix.winfo_exists() and matrix.editor is not None:
            matrix.commit_edit()
            if matrix.editor is not None:return False
        return True

    def rellenar_seleccion(self):
        from tkinter import simpledialog
        from db_safety import valid_number
        if not self.id_actividad_calificando or not self.verificar_permiso_edicion() or not self.terminar_edicion_actual():return
        mode=self.calif_combo_modo_inst.get();panel=getattr(self,'_embedded_evaluation',None)
        instrument=mode in ('Rúbrica','Lista de Cotejo') and panel and panel.winfo_ismapped()
        tree=panel.matrix.table if instrument else self._global_grade_panel.table if mode=='Nota global' else self.planilla_nativa
        selected=tree.selection()
        if not selected:messagebox.showinfo('Rellenar','Seleccione uno o varios estudiantes con Ctrl o Mayús.');return
        choices=[i['criterio'] for i in panel.matrix.items] if instrument else ['Nota global'] if mode=='Nota global' else [c['capacidad_nombre'] for c in self._capacidades_actividad]
        column=0
        if len(choices)>1:
            column=simpledialog.askinteger('Columna a rellenar','\n'.join(f'{i+1}. {v}' for i,v in enumerate(choices)),minvalue=1,maxvalue=len(choices),parent=self)
            if column is None:return
            column-=1
        raw=simpledialog.askstring('Rellenar selección','Valor para los estudiantes seleccionados (vacío = pendiente):',parent=self)
        if raw is None:return
        try:
            value=raw.strip() or None
            if instrument:
                from instrumentos import answer_points
                item=panel.matrix.items[column]
                if value is not None:answer_points(item['tipo'],value,item['puntaje_maximo'],item['puntajes'])
            elif value is not None:value=str(valid_number(value.replace(',','.'))).removesuffix('.0')
        except ValueError as exc:messagebox.showerror('Rellenar',str(exc));return
        if not messagebox.askyesno('Revisar selección',f"Columna: {choices[column]}\nEstudiantes seleccionados: {len(selected)}\nValor: {value if value is not None else 'Pendiente'}\n\n¿Aplicar a la selección?"):return
        self.recordar_planilla()
        if instrument:
            from instrument_evaluate import stage_to_grid
            for identity in selected:panel.answers[(int(identity),item['id'])]=value
            stage_to_grid(panel);panel._refresh()
        else:
            ids={str(self.planilla_nativa.item(identity,'values')[0]) for identity in selected}
            rows=self._filas_planilla()
            for row in rows:
                if str(row[0]) not in ids:continue
                for col in (range(len(self._capacidades_actividad)) if mode=='Nota global' else [column]):row[4+col]=value or ''
            self._poner_filas(rows);self.actualizar_herramientas_evaluacion()

    def guardar_instrumento(self):
        session=self.id_actividad_calificando
        if not session:messagebox.showinfo('Instrumento Excel','Abra primero la actividad que contiene su instrumento.');return
        if getattr(self,'_planilla_pendiente',False):
            messagebox.showinfo('Instrumento Excel','Guarde los cambios de la actividad antes de exportar su instrumento.');return
        from evaluacion_datos import activity
        from excel_tablas import export_activity
        ctx=activity(session,self._db_path)
        name=' - '.join([ctx['grado'],ctx['competencia_nombre'][:70],ctx['titulo_tema'][:65]])
        name=re.sub(r'[<>:"/\\|?*]','_',name)
        path=self.elegir_destino(title='Guardar instrumento reutilizable por grado, competencia y tema',initialfile=name+'.xlsx',defaultextension='.xlsx',filetypes=[('Instrumento Excel','*.xlsx')])
        if not path:return
        export_activity(path,session,self._db_path,roster=[],library=True)
        self.archivo_guardado(path,'Instrumento reutilizable guardado por grado, competencia y tema. Incluye propósito y criterios; la planilla de estudiantes está vacía.')

    def usar_biblioteca_anterior(self):
        from mejoras_ui import ClassroomTools
        ClassroomTools.usar_instrumento(self)

    def usar_instrumento(self):
        if not self.verificar_permiso_edicion():return
        if not self.id_actividad_calificando:
            messagebox.showinfo('Instrumento Excel','Cree o abra una actividad del grado y curso donde utilizará el instrumento.');return
        self._subir_excel_instrumento_a_sesion(self.id_actividad_calificando)

    def pegar_planilla(self,event=None):
        if event and not self._is_grade_widget(event.widget):return
        if not self.id_actividad_calificando or not self.verificar_permiso_edicion():return 'break'
        try:text=self.clipboard_get()
        except tk.TclError:messagebox.showinfo('Pegar notas','Copie primero un bloque de celdas desde Excel.');return 'break'
        mode=self.calif_combo_modo_inst.get();native=self.planilla_nativa
        global_panel=getattr(self,'_global_grade_panel',None)
        embedded=getattr(self,'_embedded_evaluation',None)
        instrument=mode in ('Rúbrica','Lista de Cotejo') and embedded and embedded.winfo_ismapped()
        tree=embedded.matrix.table if instrument else global_panel.table if mode=='Nota global' and global_panel else native
        if instrument:
            if embedded.matrix.editor is not None:
                embedded.matrix.commit_edit()
                if embedded.matrix.editor is not None:return 'break'
        elif mode=='Nota global' and global_panel and not global_panel.commit():return 'break'
        if not tree.selection():messagebox.showinfo('Pegar notas','Seleccione el primer estudiante del bloque.');return 'break'
        students=list(tree.get_children());start=students.index(tree.selection()[0]);rows=self._filas_planilla()
        choices=[i['criterio'] for i in embedded.matrix.items] if instrument else ['Nota global'] if mode=='Nota global' else [c['capacidad_nombre'] for c in self._capacidades_actividad]
        captions=[f'{n+1:02} · {name}' for n,name in enumerate(choices)]
        window=SafeDialog(self);window.title('Pegar notas desde Excel');window.geometry('860x600');window.transient(self)
        window.grid_columnconfigure(0,weight=1);window.grid_rowconfigure(3,weight=1)
        label=ctk.CTkLabel(window,text='Revisa el bloque antes de aplicarlo',font=ctk.CTkFont(size=21,weight='bold'));label.grid(row=0,column=0,sticky='w',padx=18,pady=14)
        hint=ctk.CTkLabel(window,text=f'Inicio: estudiante {start+1:02}. El bloque se aplicará en el orden visible. Las celdas vacías quedarán pendientes. Guardar notas confirmará los cambios.',anchor='w',justify='left');hint.grid(row=1,column=0,sticky='ew',padx=18);wrap_label(hint)
        selector=ctk.CTkComboBox(window,values=captions,state='readonly');selector.grid(row=2,column=0,sticky='ew',padx=18,pady=10);selector.set(captions[0])
        if instrument and embedded.matrix.selected:
            index=embedded.matrix.columns.index(str(embedded.matrix.selected[1]));selector.set(captions[index])
        frame=ctk.CTkFrame(window);frame.grid(row=3,column=0,sticky='nsew',padx=18);frame.grid_columnconfigure(0,weight=1);frame.grid_rowconfigure(0,weight=1)
        preview=ttk.Treeview(frame,columns=('n','name','values'),show='headings')
        for key,title,width in [('n','N°',45),('name','Apellidos y nombres',270),('values','Valores que se pegarán',440)]:preview.heading(key,text=title);preview.column(key,width=width)
        preview.grid(row=0,column=0,sticky='nsew');sy=ttk.Scrollbar(frame,command=preview.yview);sy.grid(row=0,column=1,sticky='ns');preview.configure(yscrollcommand=sy.set)
        state={};status=ctk.CTkLabel(window,text='',anchor='w',justify='left');status.grid(row=4,column=0,sticky='ew',padx=18,pady=8);wrap_label(status)
        def validate(value=None):
            preview.delete(*preview.get_children());state.clear();column=captions.index(selector.get())
            try:
                if not instrument:
                    from ingreso_masivo import plan
                    result,shown=plan(rows,text,start,column,len(self._capacidades_actividad),mode=='Nota global');state['rows']=result
                else:
                    from instrumentos import answer_points
                    values=list(csv.reader(io.StringIO(text),delimiter='\t'))
                    while values and not any(v.strip() for v in values[-1]):values.pop()
                    if not values or start+len(values)>len(students):raise ValueError('El bloque supera los estudiantes disponibles o está vacío.')
                    width=len(values[0])
                    if column+width>len(choices) or any(len(line)!=width for line in values):raise ValueError('Revise el número de criterios y la forma rectangular del bloque.')
                    answers=dict(embedded.answers);shown=[]
                    for offset,line in enumerate(values):
                        student=int(students[start+offset]);name=embedded.by_student[student]
                        shown.append((start+offset+1,f"{name['Apellidos']}, {name['Nombres']}",line))
                        for j,raw in enumerate(line):
                            item=embedded.matrix.items[column+j];value=raw.strip() or None
                            if value is not None:answer_points(item['tipo'],value,item['puntaje_maximo'],item['puntajes'])
                            answers[(student,item['id'])]=value
                    state['answers']=answers
                for n,name,line in shown:preview.insert('','end',values=(f'{n:02}',name,' | '.join(line)))
                status.configure(text=f'{len(shown)} estudiantes · Listo para aplicar. Puede deshacer todo el bloque con Ctrl+Z.',text_color=('#047857','#6ee7b7'))
            except ValueError as exc:status.configure(text=str(exc),text_color=('#b91c1c','#fca5a5'))
        def apply():
            validate()
            if not state or not self.verificar_permiso_edicion():return
            self.recordar_planilla()
            if 'rows' in state:self._poner_filas(state['rows']);self.actualizar_herramientas_evaluacion()
            else:
                from instrument_evaluate import stage_to_grid
                embedded.answers=state['answers'];stage_to_grid(embedded);embedded._refresh()
            window.destroy()
        selector.configure(command=validate);validate()
        actions=ctk.CTkFrame(window,fg_color='transparent');actions.grid(row=5,column=0,sticky='ew',padx=18,pady=14)
        ctk.CTkButton(actions,text='Cancelar',**button(),command=window.destroy).pack(side='left')
        ctk.CTkButton(actions,text='Aplicar bloque',**button(),command=apply).pack(side='right')
        polish_dialog(window,self,860,600)
        self._paste_preview=window;self._paste_apply=apply
        return 'break'
