"""Whole-class criteria grid, with fixed student names and visible evidence."""
import tkinter as tk
from tkinter import ttk,messagebox
import customtkinter as ctk
from instrumentos import LEVELS,LEVEL_NAMES,answer_points,entered_answer,criterion_caption
from instrument_widgets import label,number
from grade_cells import PALETTE,achievement
from escala import thresholds
from interfaz import pixel_scale,scrollbar
from widgets import prepare_destroy
from evaluacion_datos import grade_answers
from calculos import normalized_total


class EvaluationMatrix(ctk.CTkFrame):
    def __init__(self,master,panel):
        super().__init__(master,fg_color='transparent')
        self.panel=panel;self._preserve_theme=True;self.answers={};self.grades={};self.pending=set();self.selected=None;self.editor=None;self._syncing=False
        self.items=list(panel.by_id.values());self.columns=[str(i['id']) for i in self.items]
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(0,weight=1)
        body=ctk.CTkFrame(self,fg_color='transparent');body.grid(row=0,column=0,sticky='nsew');body.grid_columnconfigure(1,weight=1);body.grid_rowconfigure(0,weight=1)
        scale=pixel_scale(self)
        self.identity=ttk.Treeview(body,columns=('code','name'),show='headings',selectmode='browse',height=8)
        for col,text,width in [('code','Código',75),('name','Estudiante',210)]:
            self.identity.heading(col,text=text);self.identity.column(col,width=round(width*scale),minwidth=round(55*scale),stretch=False)
        self.identity.grid(row=0,column=0,sticky='nsw')
        self.table=ttk.Treeview(body,columns=(*self.columns,'progress'),show='headings',selectmode='browse',height=8)
        caps=list(dict.fromkeys(i['capacidad_id'] for i in self.items));counts={}
        for item,col in zip(self.items,self.columns):
            cap=item['capacidad_id'];counts[cap]=counts.get(cap,0)+1
            self.table.heading(col,text=f'Cap. {caps.index(cap)+1} · Criterio {counts[cap]}')
            self.table.column(col,width=round(155*scale),minwidth=round(110*scale),stretch=False,anchor='center')
        self.table.heading('progress',text='Evaluados');self.table.column('progress',width=round(100*scale),stretch=False,anchor='center')
        self.table.grid(row=0,column=1,sticky='nsew')
        self.sy=scrollbar(body,'vertical',self._yview);self.sy.grid(row=0,column=2,sticky='ns')
        sx=scrollbar(body,'horizontal',self.table.xview);sx.grid(row=1,column=1,sticky='ew')
        self.table.configure(xscrollcommand=sx.set,yscrollcommand=lambda a,b:self._scroll(self.table,self.identity,a,b))
        self.identity.configure(yscrollcommand=lambda a,b:self._scroll(self.identity,self.table,a,b))
        for student,s in panel.by_student.items():
            self.identity.insert('','end',iid=str(student),values=(s.get('Codigo_Unico',''),f"{s.get('Apellidos','')}, {s.get('Nombres','')}"))
            self.table.insert('','end',iid=str(student),values=(*['Pendiente']*len(self.items),f'0/{len(self.items)}'))
        self.table.bind('<ButtonRelease-1>',self._clicked,add='+')
        self.table.bind('<<TreeviewSelect>>',self._selected_row,add='+')
        self.identity.bind('<<TreeviewSelect>>',self._selected_name,add='+')
        self.table.bind('<Double-1>',self._double)
        self.table.bind('<Return>',lambda e:self.begin_edit())
        self.table.bind('<F2>',lambda e:self.begin_edit())
        self.table.bind('<KeyPress>',self._typed,add='+')
        detail=ctk.CTkFrame(self,fg_color='transparent');detail.grid(row=1,column=0,sticky='ew',pady=(5,0));detail.grid_columnconfigure(0,weight=1)
        self.title=label(detail,'Seleccione un criterio de la tabla para ver qué evalúa.');self.title.grid(row=0,column=0,sticky='ew',padx=8,pady=3)
        bar=ctk.CTkFrame(detail,fg_color='transparent');bar.grid(row=1,column=0,sticky='ew',padx=8,pady=3)
        label(bar,'Puntaje o nivel').pack(side='left',padx=(0,8))
        self.value=ctk.CTkEntry(bar,width=95,height=30);self.value.pack(side='left',padx=(0,5))
        self.value.bind('<Return>',lambda e:self.apply_value())
        ctk.CTkButton(bar,text='Aplicar',width=80,height=30,command=self.apply_value).pack(side='left',padx=(0,5))
        ctk.CTkButton(bar,text='Dejar pendiente',width=130,height=30,command=lambda:self.apply_value(None)).pack(side='left')
        self.note=label(detail,'');self.note.grid(row=2,column=0,sticky='ew',padx=8,pady=2)
        self.hint=label(detail,'Doble clic para escribir · Enter: siguiente estudiante · Tab: siguiente criterio.');self.hint.grid(row=3,column=0,sticky='ew',padx=8,pady=2)
        self.descriptors=ctk.CTkFrame(detail,fg_color='transparent');self.descriptors.grid(row=4,column=0,sticky='ew',padx=6,pady=3)
        self.level_boxes=[]
        for col in range(4):
            self.descriptors.grid_columnconfigure(col,weight=1,uniform='evidence')
            box=ctk.CTkFrame(self.descriptors,corner_radius=4);box.grid(row=0,column=col,sticky='nsew',padx=2)
            button=ctk.CTkButton(box,text='',height=29,command=lambda n=col:self.choose_level(n));button.pack(fill='x',padx=5,pady=(5,2))
            text=label(box,'');text.configure(font=ctk.CTkFont(size=12));text.pack(fill='x',padx=7,pady=(0,6))
            self.level_boxes.append((box,button,text))
        if self.items and panel.by_student:self.select(next(iter(panel.by_student)),self.items[0]['id'])

    def _scroll(self,source,other,first,last):
        if getattr(self,'_destroying',False) or getattr(self.panel.app,'_closing_ui',False):return
        self.sy.set(first,last)
        if self._syncing:return
        self._syncing=True
        try:other.yview_moveto(first)
        finally:self._syncing=False

    def _yview(self,*args):
        self.table.yview(*args);self.identity.yview(*args)

    def _selected_row(self,event=None):
        rows=self.table.selection()
        if rows:self.select(int(rows[0]),self.selected[1] if self.selected else self.items[0]['id'])

    def _selected_name(self,event=None):
        rows=self.identity.selection()
        if rows:self.select(int(rows[0]),self.selected[1] if self.selected else self.items[0]['id'])

    def _clicked(self,event):
        row=self.table.identify_row(event.y);col=self.table.identify_column(event.x)
        if row and col:
            index=int(col[1:])-1
            if 0<=index<len(self.items):self.select(int(row),self.items[index]['id'])

    def select(self,student,indicator):
        self.selected=(student,indicator)
        for tree in (self.table,self.identity):
            if tree.selection()!=(str(student),):tree.selection_set(str(student))
            tree.focus(str(student))
        self.panel.current_student=student;self._detail()
        if getattr(self.panel,'matrix',None) is self:self.panel._refresh()

    def refresh(self,answers):
        self.answers=dict(answers);limits=thresholds(self.panel.app._db_path)
        self.grades,self.pending=grade_answers(self.items,self.answers)
        for student in self.panel.by_student:
            values=[];filled=0
            for item in self.items:
                raw=answers.get((student,item['id']))
                if raw is None:values.append('Pendiente');continue
                filled+=1;points=answer_points(item['tipo'],raw,item['puntaje_maximo'],item['puntajes'])
                level=achievement(normalized_total(points,item['puntaje_maximo']),limits)
                values.append(f'{number(points)} ({level})')
            self.table.item(str(student),values=(*values,f'{filled}/{len(self.items)}'))
        self._detail()

    def _detail(self):
        if not self.selected:return
        student,identity=self.selected;item=self.panel.by_id[identity];s=self.panel.by_student[student]
        self.title.configure(text=f"{s.get('Apellidos','')}, {s.get('Nombres','')} · {item['capacidad_nombre']}\n{criterion_caption(item)} · Máximo: {number(item['puntaje_maximo'])}")
        key=(student,item['capacidad_id']);grade=self.grades.get(key)
        if grade is None:self.note.configure(text='Capacidad pendiente: aún no hay criterios evaluados.')
        else:
            level=achievement(grade,thresholds(self.panel.app._db_path))
            status='provisional' if key in self.pending else 'completa'
            self.note.configure(text=f'Nota calculada {status} de esta capacidad: {number(grade)} / 20 ({level})')
        self.value.delete(0,'end');raw=self.answers.get(self.selected)
        if raw is not None:self.value.insert(0,str(raw))
        rubric=item['tipo']=='Rúbrica'
        for n,(box,button,text) in enumerate(self.level_boxes):
            self.descriptors.grid_columnconfigure(n,weight=1 if rubric or n<2 else 0)
            if not rubric and n>1:box.grid_remove();continue
            box.grid();token=LEVELS[n] if rubric else ('Sí','No')[n]
            bg,fg=PALETTE[token] if rubric else ('#dcfce7','#166534') if n==0 else ('#fee2e2','#991b1b')
            points=item['puntajes'][token] if rubric else item['puntaje_maximo'] if n==0 else 0
            box.configure(fg_color=bg);button.configure(text=f'{token} · {number(points)} pt',fg_color=bg,text_color=fg,hover_color=bg)
            text.configure(text=item['descriptores'][token] if rubric else 'Cumple el criterio' if n==0 else 'No cumple el criterio',text_color=fg)

    def choose_level(self,index):
        if not self.selected:return
        item=self.panel.by_id[self.selected[1]]
        self.apply_value(LEVELS[index] if item['tipo']=='Rúbrica' else ('Sí','No')[index])

    def apply_value(self,raw=...):
        if not self.selected:return False
        item=self.panel.by_id[self.selected[1]]
        try:value=entered_answer(item,self.value.get() if raw is ... else raw)
        except ValueError as exc:
            messagebox.showwarning('Puntaje del criterio',str(exc),parent=self);return False
        self.panel.set_answer(*self.selected,value)
        self.hint.configure(text='Doble clic para escribir · Enter: siguiente estudiante · Tab: siguiente criterio.',text_color='#475569')
        return True

    def _double(self,event):
        self._clicked(event);return self.begin_edit()

    def _typed(self,event):
        if event.char and event.char in '0123456789.,cCbBaAdDsSnN':return self.begin_edit(initial=event.char)

    def begin_edit(self,student=None,indicator=None,initial=None):
        if not self.panel.app.verificar_permiso_edicion():return 'break'
        if self.editor is not None:self.cancel_edit()
        if student is not None:self.select(student,indicator)
        if not self.selected:return 'break'
        student,identity=self.selected;col=str(identity);self.table.see(str(student));bounds=self.table.bbox(str(student),col)
        if not bounds:return 'break'
        x,y,w,h=bounds;self.editor=tk.Entry(self.table,justify='center',font=('Segoe UI',-round(14*pixel_scale(self))))
        self.editor.place(x=x,y=y,width=w,height=h)
        raw=self.answers.get(self.selected)
        self.editor.insert(0,initial if initial is not None else '' if raw is None else str(raw));self.editor.focus_set()
        if initial is None:self.editor.select_range(0,'end')
        self.editor.bind('<Return>',lambda e:self.commit_edit('down'))
        self.editor.bind('<Tab>',lambda e:self.commit_edit('next'))
        self.editor.bind('<Shift-Tab>',lambda e:self.commit_edit('previous'))
        self.editor.bind('<Escape>',lambda e:self.cancel_edit())
        self.editor.bind('<FocusOut>',lambda e:self.commit_edit())
        return 'break'

    def cancel_edit(self):
        if self.editor is not None:
            editor=self.editor;self.editor=None;editor.destroy()
        return 'break'

    def commit_edit(self,move=None):
        if getattr(self,'_destroying',False) or getattr(self.panel.app,'_closing_ui',False):return self.cancel_edit()
        if self.editor is None:return 'break'
        raw=self.editor.get();student,identity=self.selected
        try:value=entered_answer(self.panel.by_id[identity],raw)
        except ValueError as exc:
            self.hint.configure(text=str(exc),text_color='#b91c1c');self.editor.focus_set();return 'break'
        self.cancel_edit();self.panel.set_answer(student,identity,value)
        if move:
            students=list(self.panel.by_student);row=students.index(student);col=self.columns.index(str(identity))
            if move=='down':row=min(row+1,len(students)-1)
            else:
                index=max(0,min(len(students)*len(self.items)-1,row*len(self.items)+col+(1 if move=='next' else -1)))
                row,col=divmod(index,len(self.items))
            self.select(students[row],self.items[col]['id']);self.begin_edit()
        return 'break'

    def destroy(self):
        if getattr(self,'_destroying',False):return
        self._destroying=True;self.cancel_edit();prepare_destroy(self);super().destroy()
