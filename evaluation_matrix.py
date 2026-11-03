"""Whole-class criteria grid, with fixed student names and visible evidence."""
import tkinter as tk
from tkinter import ttk,messagebox
import customtkinter as ctk
from instrumentos import LEVELS,LEVEL_NAMES,answer_points,entered_answer,criterion_caption
from instrument_widgets import label,number
from grade_cells import PALETTE,achievement,CriterionTreeview
from escala import thresholds
from interfaz import pixel_scale,scrollbar
from widgets import prepare_destroy,scroll_area,wrap_label,Tooltip
from evaluacion_datos import grade_answers
from calculos import normalized_total
from cotejo import capacity_label,summary as checklist_summary,configuration
import textwrap


class EvaluationMatrix(ctk.CTkFrame):
    def __init__(self,master,panel):
        super().__init__(master,fg_color='transparent')
        self.panel=panel;self._preserve_theme=True;self.answers={};self.grades={};self.pending=set();self.selected=None;self.editor=None;self._syncing=False
        self.checklist=panel.tipo_inst=='Lista de Cotejo';self._layout_job=None;self._details_preference=None
        self.items=list(panel.by_id.values());self.columns=[str(i['id']) for i in self.items]
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(0,weight=1)
        body=ctk.CTkFrame(self,fg_color='transparent');body.grid(row=0,column=0,sticky='nsew');body.grid_columnconfigure(1,weight=1);body.grid_rowconfigure(1,weight=1)
        scale=pixel_scale(self)
        self.identity=ttk.Treeview(body,columns=('code','name'),show='',selectmode='browse',height=8)
        for col,text,width in [('code','Código',75),('name','Estudiante',210)]:
            self.identity.heading(col,text=text);self.identity.column(col,width=round(width*scale),minwidth=round(55*scale),stretch=False)
        self.identity.grid(row=1,column=0,sticky='nsw')
        self.table=CriterionTreeview(body,columns=(*self.columns,'progress',*(['pending'] if self.checklist else [])),show='',selectmode='browse',height=8)
        self.table.set_grade_columns(self.columns);self.table.on_double_click=self._double
        caps=list(dict.fromkeys(i['capacidad_id'] for i in self.items));counts={}
        for item,col in zip(self.items,self.columns):
            cap=item['capacidad_id'];counts[cap]=counts.get(cap,0)+1
            caption=capacity_label(item['capacidad_nombre'])
            criterion=textwrap.shorten(criterion_caption(item),width=36,placeholder='…')
            self.table.heading(col,text=caption+'\n'+criterion)
            self.table.column(col,width=round(190*scale),minwidth=round(135*scale),stretch=False,anchor='center')
        self.table.heading('progress',text='Cumple / Evaluados' if self.checklist else 'Evaluados');self.table.column('progress',width=round((155 if self.checklist else 100)*scale),stretch=False,anchor='center')
        if self.checklist:self.table.heading('pending',text='Pendientes');self.table.column('pending',width=round(100*scale),stretch=False,anchor='center')
        self.table.grid(row=1,column=1,sticky='nsew')
        self.sy=scrollbar(body,'vertical',self._yview);self.sy.grid(row=1,column=2,sticky='ns')
        sx=scrollbar(body,'horizontal',self.table.xview);sx.grid(row=2,column=1,sticky='ew')
        self._horizontal_bar=sx
        self.table.configure(xscrollcommand=self._xscroll,yscrollcommand=lambda a,b:self._scroll(self.table,self.identity,a,b))
        self.identity.configure(yscrollcommand=lambda a,b:self._scroll(self.identity,self.table,a,b))
        self.name_header=tk.Canvas(body,height=round(88*scale),highlightthickness=0,background='#1e3a8a')
        self.name_header.grid(row=0,column=0,sticky='ew')
        self.criteria_header=tk.Canvas(body,height=round(88*scale),highlightthickness=0,background='#1e3a8a')
        self.criteria_header.grid(row=0,column=1,sticky='ew')
        self.table.bind('<Configure>',self._draw_headers,add='+');self.identity.bind('<Configure>',self._draw_headers,add='+')
        self.criteria_header.bind('<Configure>',self._draw_headers,add='+')
        Tooltip(self.criteria_header,self._header_tooltip)
        self.table.on_horizontal_change=self._sync_header
        self._header_offset=0
        for student,s in panel.by_student.items():
            self.identity.insert('','end',iid=str(student),values=(s.get('Codigo_Unico',''),f"{s.get('Apellidos','')}, {s.get('Nombres','')}"))
            self.table.insert('','end',iid=str(student),values=(*['Sin evaluar']*len(self.items),f'0/{len(self.items)}',*([len(self.items)] if self.checklist else [])))
        self.table.bind('<ButtonRelease-1>',self._clicked,add='+')
        self.table.bind('<<TreeviewSelect>>',self._selected_row,add='+')
        self.identity.bind('<<TreeviewSelect>>',self._selected_name,add='+')
        self.table.bind('<Double-1>',self._double)
        self.table.bind('<Return>',lambda e:self.move_cell('down') if self.checklist else self.begin_edit())
        self.table.bind('<Tab>',lambda e:self.move_cell('next'))
        self.table.bind('<Shift-Tab>',lambda e:self.move_cell('previous'))
        self.table.bind('<F2>',lambda e:self.begin_edit())
        self.table.bind('<KeyPress>',self._typed,add='+')
        self.detail_host=ctk.CTkFrame(self,width=300,corner_radius=8);self.detail_host.grid_propagate(False)
        detail=scroll_area(self.detail_host,auto_hide=True);detail.pack(fill='both',expand=True);detail.grid_columnconfigure(0,weight=1)
        label(detail,'Criterio seleccionado').grid(row=0,column=0,sticky='ew',padx=10,pady=8)
        self.descriptor_title=label(detail,'');self.descriptor_title.grid(row=1,column=0,sticky='ew',padx=10,pady=5)
        self.value=ctk.CTkEntry(self,width=95,height=30)
        self.value.bind('<Return>',lambda e:self.apply_value())
        self.title=label(self,'Seleccione un criterio de la tabla.');self.title.grid(row=1,column=0,columnspan=2,sticky='ew',padx=8,pady=(5,2))
        self.note=label(self,'');self.note.grid(row=2,column=0,columnspan=2,sticky='ew',padx=8,pady=2)
        self.hint=label(self,'S: cumple · N: no cumple · Supr: pendiente · Enter: siguiente estudiante · Tab: siguiente criterio.' if self.checklist else 'Doble clic: escribir · Enter: siguiente estudiante · Tab: siguiente criterio · Supr: pendiente.');self.hint.grid(row=3,column=0,columnspan=2,sticky='ew',padx=8,pady=2)
        self.descriptors=ctk.CTkFrame(detail,fg_color='transparent');self.descriptors.grid(row=2,column=0,sticky='ew',padx=6,pady=3)
        self.level_boxes=[]
        for col in range(4):
            box=ctk.CTkFrame(self.descriptors,corner_radius=4);box.pack(fill='x',padx=2,pady=4)
            button=ctk.CTkButton(box,text='',height=29,command=lambda n=col:self.choose_level(n));button.pack(fill='x',padx=5,pady=(5,2))
            text=label(box,'');text.configure(font=ctk.CTkFont(size=12));text.pack(fill='x',padx=7,pady=(0,6))
            self.level_boxes.append((box,button,text))
        if self.items and panel.by_student:self.select(next(iter(panel.by_student)),self.items[0]['id'])
        self._draw_headers()
        self.bind('<Configure>',self._queue_layout,add='+');self._queue_layout()

    def _header_tooltip(self):
        x=self.criteria_header.winfo_pointerx()-self.criteria_header.winfo_rootx()+self._header_offset;offset=0
        for item,col in zip(self.items,self.columns):
            offset+=self.table.column(col,'width')
            if x<offset:return item['capacidad_nombre']+' · '+criterion_caption(item)
        return 'Avance de las observaciones'

    def _xscroll(self,first,last):
        self._horizontal_bar.set(first,last)
        if hasattr(self,'criteria_header'):self._sync_header()

    def _sync_header(self):
        total=sum(self.table.column(col,'width') for col in self.table['columns'])
        offset=round(float(self.table.xview()[0])*total)
        self.criteria_header.move('all',getattr(self,'_header_offset',0)-offset,0)
        self._header_offset=offset

    def _draw_headers(self,event=None):
        if getattr(self,'_destroying',False):return
        scale=pixel_scale(self);height=round(88*scale);font=('Segoe UI',-round(12*scale));bold=(*font,'bold')
        self.name_header.delete('all');offset=0
        for col,text in [('code','Código'),('name','Estudiante')]:
            width=self.identity.column(col,'width');self.name_header.create_rectangle(offset,0,offset+width,height,outline='#cbd5e1',fill='#1e3a8a')
            self.name_header.create_text(offset+width/2,height/2,text=text,fill='white',font=bold,width=width-8);offset+=width
        self.name_header.configure(width=offset)
        self.criteria_header.delete('all');offset=0
        for col in self.table['columns']:
            width=self.table.column(col,'width');self.criteria_header.create_rectangle(offset,0,offset+width,height,outline='#cbd5e1',fill='#1e3a8a')
            if col in self.columns:
                item=self.items[self.columns.index(col)]
                self.criteria_header.create_text(offset+7,6*scale,anchor='nw',text=capacity_label(item['capacidad_nombre']),fill='white',font=bold,width=width-14)
                self.criteria_header.create_text(offset+7,40*scale,anchor='nw',text=textwrap.shorten(criterion_caption(item),width=66,placeholder='…'),fill='#dbeafe',font=font,width=width-14)
            else:self.criteria_header.create_text(offset+width/2,height/2,text=self.table.heading(col,'text'),fill='white',font=bold,width=width-14)
            offset+=width
        self._header_offset=0;self._sync_header()

    def _queue_layout(self,event=None):
        if getattr(self,'_destroying',False):return
        if self._layout_job:self.after_cancel(self._layout_job)
        self._layout_job=self.after(90,self._layout)

    def _layout(self):
        self._layout_job=None
        opened=not self.checklist and (self._details_preference if self._details_preference is not None else self.winfo_width()/pixel_scale(self)>=1050)
        if opened:self.detail_host.grid(row=0,column=1,sticky='nsew',padx=(8,0))
        else:self.detail_host.grid_remove()

    def toggle_details(self):
        self._details_preference=not self.detail_host.winfo_ismapped();self._layout()

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
            if 0<=index<len(self.items):
                self.select(int(row),self.items[index]['id'])
                if self.checklist:self.apply_value('No' if self.answers.get(self.selected)=='Sí' else 'Sí')

    def select(self,student,indicator):
        self.selected=(student,indicator)
        for tree in (self.table,self.identity):
            if tree.selection()!=(str(student),):tree.selection_set(str(student))
            tree.focus(str(student))
        self.panel.current_student=student;self._detail()
        if getattr(self.panel,'matrix',None) is self:self.panel._refresh()

    def refresh(self,answers):
        self.answers=dict(answers);limits=thresholds(self.panel.app._db_path)
        self.grades,self.pending=({},set()) if self.checklist else grade_answers(self.items,self.answers)
        self.summary=checklist_summary(self.items,self.answers,self.panel.by_student) if self.checklist else {}
        for student in self.panel.by_student:
            values=[];filled=0
            for item in self.items:
                raw=answers.get((student,item['id']))
                if raw is None:values.append('Sin evaluar' if self.checklist else 'Pendiente');continue
                if self.checklist:filled+=1;values.append('Sí' if str(raw) in ('Sí','True','1') else 'No');continue
                filled+=1;points=answer_points(item['tipo'],raw,item['puntaje_maximo'],item['puntajes'])
                level=achievement(normalized_total(points,item['puntaje_maximo']),limits)
                values.append(f'{number(points)} ({level})')
            if self.checklist:
                states=[v for (s,c),v in self.summary.items() if s==student]
                yes=sum(v['cumplidos'] for v in states);evaluated=sum(v['evaluados'] for v in states)
                self.table.item(str(student),values=(*values,f'{yes}/{evaluated}',len(self.items)-evaluated))
            else:self.table.item(str(student),values=(*values,f'{filled}/{len(self.items)}'))
        self._detail()

    def _detail(self):
        if not self.selected:return
        student,identity=self.selected;item=self.panel.by_id[identity];s=self.panel.by_student[student]
        context=f"{s.get('Apellidos','')}, {s.get('Nombres','')} · {item['capacidad_nombre']}\n{criterion_caption(item)}"
        self.title.configure(text=context if self.checklist else context+f" · Máximo: {number(item['puntaje_maximo'])}")
        self.descriptor_title.configure(text=f"{item['capacidad_nombre']}\n{criterion_caption(item)}")
        if self.checklist:
            state=getattr(self,'summary',{}).get((student,item['capacidad_id']),dict(cumplidos=0,evaluados=0,pendientes=len(self.items)))
            rule=getattr(self.panel.app,'_cotejo_pending_rule',None) or configuration(self.panel.sesion['id'],self.panel.app._db_path)[0]
            suffix='Solo orientación; no genera notas.' if rule['tipo']=='orientacion' else 'Hay notas confirmadas; convertir para actualizar su evaluación.'
            self.note.configure(text=f"Esta capacidad: cumple {state['cumplidos']} de {state['evaluados']} evaluados · {state['pendientes']} pendientes. {suffix}")
            return
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
            token=LEVELS[n]
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
        self.hint.configure(text='S: cumple · N: no cumple · Supr: pendiente · Enter: siguiente estudiante · Tab: siguiente criterio.' if self.checklist else 'Doble clic: escribir · Enter: siguiente estudiante · Tab: siguiente criterio.',text_color=('#475569','#cbd5e1'))
        return True

    def _double(self,event):
        if self.checklist:return 'break'
        self._clicked(event);return self.begin_edit()

    def _typed(self,event):
        if event.state&4:return
        if self.selected and event.keysym in ('Delete','BackSpace'):self.apply_value(None);return 'break'
        if self.checklist:
            if event.char.lower() in ('s','n') and event.char:self.apply_value('Sí' if event.char.lower()=='s' else 'No');return 'break'
            if event.keysym=='space':self.apply_value('No' if self.answers.get(self.selected)=='Sí' else 'Sí');return 'break'
            return
        if event.char and event.char in '0123456789.,cCbBaAdDsSnN':return self.begin_edit(initial=event.char)

    def move_cell(self,move):
        if not self.selected:return 'break'
        student,identity=self.selected;students=list(self.panel.by_student)
        row=students.index(student);col=self.columns.index(str(identity))
        if move=='down':row=min(row+1,len(students)-1)
        else:
            index=max(0,min(len(students)*len(self.items)-1,row*len(self.items)+col+(1 if move=='next' else -1)))
            row,col=divmod(index,len(self.items))
        self.select(students[row],self.items[col]['id']);self.table.see(str(students[row]));return 'break'

    def begin_edit(self,student=None,indicator=None,initial=None):
        if self.checklist:return 'break'
        if not self.panel.app.verificar_permiso_edicion():return 'break'
        if self.editor is not None:self.cancel_edit()
        if student is not None:self.select(student,indicator)
        if not self.selected:return 'break'
        student,identity=self.selected;col=str(identity);self.table.see(str(student));bounds=self.table.bbox(str(student),col)
        if not bounds:return 'break'
        x,y,w,h=bounds;self.editor=tk.Entry(self.table,justify='center',font=('Segoe UI',-round(14*pixel_scale(self))))
        self.table.editor=self.editor
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
            editor=self.editor;self.editor=None;self.table.editor=None;editor.destroy()
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
        self._destroying=True
        if self._layout_job:
            try:self.after_cancel(self._layout_job)
            except tk.TclError:pass
        self.cancel_edit();prepare_destroy(self);super().destroy()
