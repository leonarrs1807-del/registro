"""Shared readable, boxed instruments for viewing, editing and evaluation."""
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from widgets import scroll_area,wrap_label,SafeDialog
from interfaz import pixel_scale,scrollbar
from instrumentos import LEVELS,LEVEL_NAMES,criterion_caption,normalized,answer_points
from grade_cells import PALETTE


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
        self.indicators=indicators;self.on_choice=on_choice;self.variables={};self.cells={};self.badges={}
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(1,weight=1)
        self.capacity_names={i['capacidad_id']:i['capacidad_nombre'] for i in indicators}
        self.capacities={f'{n} de {len(self.capacity_names)}':identity for n,identity in enumerate(self.capacity_names,1)}
        bar=ctk.CTkFrame(self,fg_color='transparent');bar.grid(row=0,column=0,sticky='ew',pady=(0,8));bar.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(bar,text='Capacidad',font=ctk.CTkFont(size=14,weight='bold')).grid(row=0,column=0,padx=(0,8))
        self.choice=ctk.CTkComboBox(bar,values=list(self.capacities),state='readonly',width=140,height=36,command=lambda _:self.render())
        self.choice.grid(row=0,column=1,sticky='w');self.choice.set(next(iter(self.capacities),''))
        self.content=scroll_area(self,auto_hide=True,horizontal=True,min_width=940 if indicators and indicators[0]['tipo']=='Rúbrica' else 640)
        self.content.grid(row=1,column=0,sticky='nsew');self.content.grid_columnconfigure(0,weight=1)
        self.answers={};self.render()

    def render(self):
        for child in self.content.winfo_children():child.destroy()
        self.variables={};self.cells={};self.badges={}
        capacity=self.capacities.get(self.choice.get())
        items=[i for i in self.indicators if i['capacidad_id']==capacity]
        if not items:return
        title=label(self.content,self.capacity_names[capacity]);title.configure(font=ctk.CTkFont(size=16,weight='bold'))
        title.grid(row=0,column=0,sticky='ew',padx=10,pady=10)
        table=ctk.CTkFrame(self.content,fg_color='#cbd5e1',corner_radius=0);table.grid(row=1,column=0,sticky='ew',padx=6,pady=(0,12))
        rubric=items[0]['tipo']=='Rúbrica';choices=LEVELS if rubric else ('Sí','No')
        table.grid_columnconfigure(0,weight=2,minsize=240 if rubric else 320)
        for col,token in enumerate(choices,1):table.grid_columnconfigure(col,weight=1,minsize=175 if rubric else 140)
        headers=['Criterio y puntos máximos']+[f'{LEVEL_NAMES[c]} ({c})' if rubric else 'Cumple' if c=='Sí' else 'No cumple' for c in choices]
        for col,text in enumerate(headers):
            cell=ctk.CTkFrame(table,fg_color='#e2e8f0',corner_radius=0);cell.grid(row=0,column=col,sticky='nsew',padx=1,pady=1)
            head=label(cell,text,text_color='#0f172a');head.configure(font=ctk.CTkFont(size=14,weight='bold'))
            head.pack(fill='x',padx=10,pady=10)
        for row,item in enumerate(items,1):
            identity=item['id'];variable=tk.StringVar(master=self,value='');self.variables[identity]=variable
            criterion=ctk.CTkFrame(table,fg_color='#ffffff',corner_radius=0)
            criterion.grid(row=row,column=0,sticky='nsew',padx=1,pady=1)
            label(criterion,criterion_caption(item),text_color='#0f172a').pack(fill='x',padx=10,pady=(10,5))
            label(criterion,f"Máximo: {number(item['puntaje_maximo'])} puntos",text_color='#475569').pack(fill='x',padx=10,pady=5)
            self.badges[identity]=label(criterion,'',text_color='#1d4ed8');self.badges[identity].pack(fill='x',padx=10,pady=3)
            if self.on_choice:
                if rubric:
                    ctk.CTkRadioButton(criterion,text='Sin evidencia · 0',variable=variable,value='NE',
                        command=lambda i=identity:self._choose(i,'NE'),font=ctk.CTkFont(size=13),text_color='#475569').pack(anchor='w',padx=10,pady=6)
                ctk.CTkButton(criterion,text='Dejar pendiente',height=28,width=135,fg_color='transparent',border_width=1,
                    text_color='#475569',command=lambda i=identity:self._choose(i,None)).pack(anchor='w',padx=10,pady=(3,10))
            for col,token in enumerate(choices,1):
                bg,fg=PALETTE[token] if rubric else ('#dcfce7','#166534') if token=='Sí' else ('#fee2e2','#991b1b')
                cell=ctk.CTkFrame(table,fg_color=bg,corner_radius=0,border_width=1,border_color=bg)
                cell.grid(row=row,column=col,sticky='nsew',padx=1,pady=1);self.cells[(identity,token)]=cell
                points=item['puntajes'][token] if rubric else item['puntaje_maximo'] if token=='Sí' else 0
                text=f'{token} · {number(points)} puntos'
                if self.on_choice:
                    ctk.CTkRadioButton(cell,text=text,variable=variable,value=token,
                        command=lambda i=identity,t=token:self._choose(i,t),font=ctk.CTkFont(size=14,weight='bold'),text_color=fg).pack(anchor='w',padx=10,pady=10)
                else:label(cell,text,text_color=fg).pack(fill='x',padx=10,pady=10)
                if rubric:label(cell,item['descriptores'][token],text_color=fg).pack(fill='x',padx=10,pady=(0,14))
                if self.on_choice:
                    def bind_choice(widget,i=identity,t=token):
                        if not isinstance(widget,ctk.CTkRadioButton):widget.bind('<Button-1>',lambda e:self._choose(i,t),add='+')
                        for child in widget.winfo_children():
                            if not isinstance(widget,ctk.CTkRadioButton):bind_choice(child,i,t)
                    bind_choice(cell)
        self.show_answers(self.answers)

    def _choose(self,identity,value):
        self.on_choice(identity,value)

    def show_answers(self,answers):
        self.answers=dict(answers)
        if not self.on_choice:return
        for identity,var in self.variables.items():
            value=answers.get(identity);token=str(value) if value is not None else ''
            var.set(token)
            item=next(i for i in self.indicators if i['id']==identity)
            if value is None:caption='Pendiente'
            elif token in LEVELS or token in ('Sí','No','NE'):caption='Sin evidencia: 0 puntos' if token=='NE' else ''
            else:caption=f'Puntaje registrado: {number(answer_points(item["tipo"],value,item["puntaje_maximo"],item["puntajes"]))}'
            self.badges[identity].configure(text=caption)
            for (key,choice),cell in self.cells.items():
                if key==identity:cell.configure(border_width=3 if token==choice else 1,border_color='#2563eb' if token==choice else cell.cget('fg_color'))
