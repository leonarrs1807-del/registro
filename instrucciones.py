"""Searchable step-by-step help, shared with the installed text manual."""
import tkinter as tk
import unicodedata
import customtkinter as ctk
from interfaz import split,scrollbar,pixel_scale
from colores import button
from ayuda_contenido import TOPICS


def searchable(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.casefold()) if not unicodedata.combining(c))


class Tutorial(ctk.CTkFrame):
    def __init__(self,master):
        super().__init__(master,fg_color='transparent')
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(2,weight=1)
        ctk.CTkLabel(self,text='Ayuda · Guía paso a paso',font=ctk.CTkFont(size=22,weight='bold')).grid(row=0,column=0,sticky='w',padx=16,pady=(12,4))
        tools=ctk.CTkFrame(self,fg_color='transparent');tools.grid(row=1,column=0,sticky='ew',padx=12,pady=6);tools.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(tools,text='Buscar ayuda',font=ctk.CTkFont(size=14,weight='bold')).grid(row=0,column=0,padx=(0,8))
        self.query=ctk.StringVar()
        self.search=ctk.CTkEntry(tools,textvariable=self.query,placeholder_text='Buscar: bimestres, unidades, rúbricas, Excel…',height=36)
        self.search.grid(row=0,column=1,sticky='ew',padx=(0,8))
        ctk.CTkButton(tools,text='Ver todo',width=85,**button(),command=lambda:self.query.set('')).grid(row=0,column=2,padx=3)
        self.previous=ctk.CTkButton(tools,text='Anterior',width=90,**button(),command=lambda:self.move(-1));self.previous.grid(row=0,column=3,padx=3)
        self.next=ctk.CTkButton(tools,text='Siguiente',width=90,**button(),command=lambda:self.move(1));self.next.grid(row=0,column=4,padx=3)
        pane=split(self,'tutorial');pane.grid(row=2,column=0,sticky='nsew',padx=8,pady=6)
        left=ctk.CTkFrame(pane);left.grid_rowconfigure(1,weight=1);left.grid_columnconfigure(0,weight=1)
        self.count=ctk.CTkLabel(left,text='',anchor='w',font=ctk.CTkFont(size=13,weight='bold'));self.count.grid(row=0,column=0,columnspan=2,sticky='ew',padx=10,pady=7)
        self.listing=tk.Listbox(left,font=('Segoe UI',-round(14*pixel_scale(self))),exportselection=False,width=29,borderwidth=0,highlightthickness=0,background='#f0f9ff',foreground='#075985',selectbackground='#bae6fd',selectforeground='#0c4a6e')
        self.listing.grid(row=1,column=0,sticky='nsew',padx=4,pady=4)
        side=scrollbar(left,'vertical',self.listing.yview);side.grid(row=1,column=1,sticky='ns');self.listing.configure(yscrollcommand=side.set)
        right=ctk.CTkFrame(pane);right.grid_columnconfigure(0,weight=1);right.grid_rowconfigure(0,weight=1)
        self.text=tk.Text(right,wrap='word',font=('Segoe UI',-round(16*pixel_scale(self))),padx=22,pady=18,relief='flat',background='#ffffff',foreground='#0f172a',spacing3=5)
        self.text.grid(row=0,column=0,sticky='nsew')
        self.text.tag_configure('title',foreground='#075985',font=('Segoe UI',-round(21*pixel_scale(self)),'bold'),spacing3=10)
        self.text.tag_configure('heading',foreground='#075985',font=('Segoe UI',-round(16*pixel_scale(self)),'bold'),spacing1=10,spacing3=8)
        bar=scrollbar(right,'vertical',self.text.yview);bar.grid(row=0,column=1,sticky='ns');self.text.configure(yscrollcommand=bar.set)
        pane.add(left,width=round(290*pixel_scale(self)),minsize=round(160*pixel_scale(self)),stretch='never');pane.add(right,minsize=round(230*pixel_scale(self)),stretch='always')
        self.current=None;self.names=list(TOPICS)
        self.listing.bind('<<ListboxSelect>>',self.select)
        self.search.bind('<Return>',lambda e:self.open(self.names[0]) if self.names else None)
        self.text.bind('<Control-f>',self.focus_search);self.listing.bind('<Control-f>',self.focus_search)
        self.query.trace_add('write',lambda *args:self.filter())
        self.filter()

    def focus_search(self,event=None):
        self.search.focus_set();self.search.select_range(0,'end');return 'break'

    def filter(self):
        words=searchable(self.query.get()).split()
        self.names=[name for name,body in TOPICS.items() if all(word in searchable(name+' '+body) for word in words)]
        self.listing.delete(0,'end')
        for name in self.names:self.listing.insert('end',name)
        self.count.configure(text=f'{len(self.names)} apartados'+(' encontrados' if words else ' · elija una tarea'))
        if self.names:self.open(self.current if self.current in self.names else self.names[0])
        else:
            self.current=None
            self.text.configure(state='normal');self.text.delete('1.0','end')
            self.text.insert('1.0','No se encontraron instrucciones.\n\nPruebe con una palabra como colegio, periodo, unidad, nota, Excel o respaldo.')
            self.text.configure(state='disabled');self.previous.configure(state='disabled');self.next.configure(state='disabled')

    def select(self,event=None):
        selected=self.listing.curselection()
        if selected:self.open(self.names[selected[0]])

    def move(self,delta):
        if not self.names:return
        index=self.names.index(self.current) if self.current in self.names else 0
        self.open(self.names[max(0,min(len(self.names)-1,index+delta))])

    def open(self,topic):
        if topic not in TOPICS:topic=next(iter(TOPICS))
        if topic not in self.names:self.query.set('')
        index=self.names.index(topic);self.current=topic
        self.listing.selection_clear(0,'end');self.listing.selection_set(index);self.listing.see(index)
        self.text.configure(state='normal');self.text.delete('1.0','end')
        self.text.insert('end',topic+'\n','title');self.text.insert('end','\n','body')
        for line in TOPICS[topic].splitlines():
            self.text.insert('end',line+'\n','heading' if line.isupper() else '')
        self.text.configure(state='disabled');self.text.yview_moveto(0)
        self.previous.configure(state='normal' if index>0 else 'disabled')
        self.next.configure(state='normal' if index<len(self.names)-1 else 'disabled')
