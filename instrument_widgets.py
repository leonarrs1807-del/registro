"""Shared readable, boxed instruments for viewing, editing and evaluation."""
import tkinter as tk
from tkinter import ttk,messagebox
import customtkinter as ctk
from widgets import scroll_area,wrap_label,SafeDialog
from interfaz import pixel_scale,scrollbar
from instrumentos import LEVELS,LEVEL_NAMES,criterion_caption,normalized,answer_points,entered_answer
from cotejo import capacity_label
from grade_cells import PALETTE,achievement
from escala import thresholds,DEFAULT,range_caption
from calculos import normalized_total
from colores import HEADER,HEADER_TEXT,BORDER


def number(value):return format(float(value),'.12g')


def label(master,text,**kwargs):
    widget=ctk.CTkLabel(master,text=text,justify='left',anchor='w',font=ctk.CTkFont(size=14),**kwargs)
    wrap_label(widget)
    return widget


class Multiline(ctk.CTkFrame):
    """Native text editor: avoids CTk 6 nested scrollbar idle redraws."""
    def __init__(self,master,text='',height=110):
        super().__init__(master,fg_color='#ffffff',border_width=1,border_color='#cbd5e1',corner_radius=5)
        self.grid_rowconfigure(0,weight=1);self.grid_columnconfigure(0,weight=1)
        self.configure(height=height);self.grid_propagate(False)
        self.text=tk.Text(self,wrap='word',font=('Segoe UI',-round(14*pixel_scale(self))),
            background='#ffffff',foreground='#0f172a',insertbackground='#0f172a',relief='flat',padx=7,pady=6,undo=True,width=1,height=2)
        self.text.grid(row=0,column=0,sticky='nsew',padx=4,pady=4)
        bar=scrollbar(self,'vertical',self.text.yview);bar.grid(row=0,column=1,sticky='ns',pady=4)
        self.text.configure(yscrollcommand=bar.set);self.text.insert('1.0',text)
    def get(self,*args):return self.text.get('1.0','end-1c')
    def insert(self,*args):return self.text.insert(*args)
    def delete(self,*args):return self.text.delete(*args)


class InstrumentGrid(ctk.CTkFrame):
    """A capacity at a time: four aligned rubric levels, or two checklist choices."""
    def __init__(self,master,indicators,*,on_choice=None):
        super().__init__(master,fg_color='transparent')
        self._preserve_theme=True
        self.indicators=indicators;self.on_choice=on_choice;self.variables={};self.cells={};self.badges={};self.actions={};self.numeric_entries={}
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(1,weight=1)
        self.capacity_names={i['capacidad_id']:i['capacidad_nombre'] for i in indicators}
        self.capacities={name:identity for identity,name in self.capacity_names.items()}
        bar=ctk.CTkFrame(self,fg_color='transparent');bar.grid(row=0,column=0,sticky='ew',pady=(0,6));bar.grid_columnconfigure(2,weight=1)
        ctk.CTkLabel(bar,text='Capacidad',font=ctk.CTkFont(size=14,weight='bold')).grid(row=0,column=0,padx=(0,8))
        self.choice=ctk.CTkComboBox(bar,values=list(self.capacities),state='readonly',width=220,height=34,font=ctk.CTkFont(size=14),command=lambda _:self.render())
        self.choice.grid(row=0,column=1,sticky='w');self.choice.set(next(iter(self.capacities),''))
        self.capacity_title=label(bar,'');self.capacity_title.configure(font=ctk.CTkFont(size=15,weight='bold'))
        self.capacity_title.grid(row=0,column=2,sticky='ew',padx=(12,4))
        rubric=indicators and indicators[0]['tipo']=='Rúbrica'
        self.content=scroll_area(self,auto_hide=True,horizontal=True,min_width=(1060 if on_choice else 860) if rubric else 590)
        self.content.grid(row=1,column=0,sticky='nsew');self.content.grid_columnconfigure(0,weight=1)
        self.answers={};self._entry_values={};self._direct_committing=False;self._validation_active=False;self._rendering=False;self.rendered_capacity='';self.render()

    def render(self):
        self._rendering=True
        for child in self.content.winfo_children():child.destroy()
        self.variables={};self.cells={};self.badges={};self.actions={};self.numeric_entries={};self._entry_values={}
        self.rendered_capacity=self.choice.get()
        capacity=self.capacities.get(self.choice.get())
        items=[i for i in self.indicators if i['capacidad_id']==capacity]
        if not items:self._rendering=False;return
        self.capacity_title.configure(text=self.capacity_names[capacity])
        table=ctk.CTkFrame(self.content,fg_color=BORDER,corner_radius=0);table.grid(row=0,column=0,sticky='ew',padx=3,pady=(0,6))
        rubric=items[0]['tipo']=='Rúbrica';choices=LEVELS if rubric else ('Sí','No')
        table.grid_columnconfigure(0,weight=2,minsize=220 if rubric else 290)
        direct=rubric and bool(self.on_choice);first_level=2 if direct else 1
        if direct:table.grid_columnconfigure(1,weight=0,minsize=135)
        for col,token in enumerate(choices,first_level):table.grid_columnconfigure(col,weight=1,minsize=150 if rubric else 140,uniform='niveles')
        headers=['Criterio y puntos máximos']+(['Puntaje'] if direct else [])+[f'{LEVEL_NAMES[c]} ({c})' if rubric else 'Cumple' if c=='Sí' else 'No cumple' for c in choices]
        for col,text in enumerate(headers):
            cell=ctk.CTkFrame(table,fg_color=HEADER,corner_radius=0);cell.grid(row=0,column=col,sticky='nsew',padx=1,pady=1)
            head=label(cell,text,text_color=HEADER_TEXT);head.configure(font=ctk.CTkFont(size=14,weight='bold'))
            head.pack(fill='x',padx=10,pady=10)
        for row,item in enumerate(items,1):
            identity=item['id'];variable=tk.StringVar(master=self,value='');self.variables[identity]=variable
            criterion=ctk.CTkFrame(table,fg_color='#ffffff',corner_radius=0)
            criterion.grid(row=row,column=0,sticky='nsew',padx=1,pady=1)
            label(criterion,criterion_caption(item),text_color='#0f172a').pack(fill='x',padx=10,pady=(10,5))
            if rubric:label(criterion,f"Máximo: {number(item['puntaje_maximo'])} puntos",text_color='#475569').pack(fill='x',padx=10,pady=5)
            self.badges[identity]=label(criterion,'',text_color='#1d4ed8')
            if self.on_choice:
                if direct:
                    target=ctk.CTkFrame(table,fg_color='#ffffff',corner_radius=0);target.grid(row=row,column=1,sticky='nsew',padx=1,pady=1)
                else:target=criterion
                actions=ctk.CTkFrame(target,fg_color='transparent');actions.pack(fill='x',padx=10,pady=(10,8));self.actions[identity]=actions
                if rubric:
                    entry=ctk.CTkEntry(actions,width=105,height=36,font=ctk.CTkFont(size=16),placeholder_text='Escribe aquí')
                    entry.pack(fill='x',pady=(0,6));self.numeric_entries[identity]=entry
                    entry.bind('<Return>',lambda e,i=identity:self._advance_entry(i))
                    entry.bind('<Tab>',lambda e,i=identity:self._advance_entry(i))
                    entry.bind('<Shift-Tab>',lambda e,i=identity:self._advance_entry(i,-1))
                    entry.bind('<FocusOut>',lambda e,i=identity:self._focus_out(i))
                    label(actions,'Vacío: pendiente\n0: sin evidencia',text_color='#64748b').pack(fill='x')
                else:
                    ctk.CTkButton(actions,text='Dejar pendiente',height=28,width=135,fg_color='transparent',border_width=1,
                        text_color='#475569',command=lambda i=identity:self._choose(i,None)).pack(anchor='w',pady=3)
            for col,token in enumerate(choices,first_level):
                bg,fg=PALETTE[token] if rubric else ('#dcfce7','#166534') if token=='Sí' else ('#fee2e2','#991b1b')
                cell=ctk.CTkFrame(table,fg_color=bg,corner_radius=0,border_width=1,border_color=bg)
                cell.grid(row=row,column=col,sticky='nsew',padx=1,pady=1);self.cells[(identity,token)]=cell
                points=item['puntajes'][token] if rubric else item['puntaje_maximo'] if token=='Sí' else 0
                text=range_caption(token,thresholds(getattr(self.winfo_toplevel(),'app',self.winfo_toplevel())._db_path) if hasattr(getattr(self.winfo_toplevel(),'app',self.winfo_toplevel()),'_db_path') else DEFAULT,item['puntaje_maximo']) if rubric else 'Cumple' if token=='Sí' else 'No cumple'
                if self.on_choice and not rubric:
                    ctk.CTkRadioButton(cell,text=text,variable=variable,value=token,
                        command=lambda i=identity,t=token:self._choose(i,t),font=ctk.CTkFont(size=14,weight='bold'),text_color=fg).pack(anchor='w',padx=10,pady=10)
                else:label(cell,text,text_color=fg).pack(fill='x',padx=10,pady=10)
                if rubric:label(cell,item['descriptores'][token],text_color=fg).pack(fill='x',padx=10,pady=(0,14))
                if self.on_choice and not rubric:
                    def bind_choice(widget,i=identity,t=token):
                        if not isinstance(widget,ctk.CTkRadioButton):widget.bind('<Button-1>',lambda e:self._choose(i,t),add='+')
                        for child in widget.winfo_children():
                            if not isinstance(widget,ctk.CTkRadioButton):bind_choice(child,i,t)
                    bind_choice(cell)
        self._rendering=False;self.show_answers(self.answers)

    def _choose(self,identity,value):
        self.on_choice(identity,value)

    def _manual(self,identity):
        return self.commit_entries([identity])

    def commit_entries(self,identities=None):
        if self._direct_committing or self._rendering:return True
        if self._validation_active:return False
        changes=[]
        for identity in identities if identities is not None else list(self.numeric_entries):
            entry=self.numeric_entries.get(identity)
            if entry is None or not entry.winfo_exists():continue
            raw=entry.get()
            if raw==self._entry_values.get(identity,''):continue
            item=next(i for i in self.indicators if i['id']==identity)
            try:value=entered_answer(item,raw)
            except ValueError as exc:
                self._validation_active=True
                try:messagebox.showwarning('Puntaje del criterio',str(exc),parent=self)
                finally:self._validation_active=False
                if entry.winfo_exists():entry.focus_set()
                return False
            changes.append((identity,value))
        if not changes:return True
        self._direct_committing=True
        try:
            for identity,value in changes:self._choose(identity,value)
        finally:self._direct_committing=False
        self.show_answers(self.answers,force=True);return True

    def _focus_out(self,identity):
        if not self.winfo_exists() or getattr(self.master,'_destroying',False):return
        self.commit_entries([identity])

    def _advance_entry(self,identity,direction=1):
        if not self.commit_entries():return 'break'
        ids=list(self.numeric_entries);index=(ids.index(identity)+direction)%len(ids)
        entry=self.numeric_entries[ids[index]];entry.focus_set();entry.select_range(0,'end')
        return 'break'

    def show_answers(self,answers,force=False):
        self.answers=dict(answers)
        if not self.on_choice or self._direct_committing:return
        for identity,var in self.variables.items():
            value=answers.get(identity);token=str(value) if value is not None else ''
            var.set(token)
            item=next(i for i in self.indicators if i['id']==identity)
            if value is None:caption='Pendiente'
            elif token in LEVELS or token in ('Sí','No','NE'):caption='Sin evidencia: 0 puntos' if token=='NE' else ''
            else:
                points=answer_points(item['tipo'],value,item['puntaje_maximo'],item['puntajes'])
                root=self.winfo_toplevel();app=getattr(root,'app',root)
                path=getattr(app,'_db_path',None)
                level=achievement(normalized_total(points,item['puntaje_maximo']),thresholds(path) if path else DEFAULT)
                caption=f"Nota: {number(points)} · Nivel {range_caption(level,thresholds(path) if path else DEFAULT,item['puntaje_maximo'])}"
            if identity in self.numeric_entries:
                entry=self.numeric_entries[identity]
                if force or entry.get()==self._entry_values.get(identity,''):
                    text=number(answer_points(item['tipo'],value,item['puntaje_maximo'],item['puntajes'])) if value is not None else ''
                    if entry.get()!=text:entry.delete(0,'end');entry.insert(0,text)
                    self._entry_values[identity]=text
            self.badges[identity].configure(text=caption)
            if caption:self.badges[identity].pack(fill='x',padx=10,pady=2)
            else:self.badges[identity].pack_forget()
            for (key,choice),cell in self.cells.items():
                if key==identity:cell.configure(border_width=3 if token==choice else 1,border_color='#2563eb' if token==choice else cell.cget('fg_color'))
