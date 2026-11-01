"""Adaptive desktop navigation, adjustable dividers and usable scrollbars."""
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from widgets import scroll_area, wrap_label


def pixel_scale(widget):
    try:return ctk.ScalingTracker.get_widget_scaling(widget)
    except (KeyError,AttributeError):return 1


def scrollbar(master,orient,command):
    return tk.Scrollbar(master,orient=orient,command=command,width=max(22,round(22*pixel_scale(master))),
                        relief='flat',borderwidth=1,elementborderwidth=1)


def split(master,key,orient='horizontal'):
    root=master.winfo_toplevel()
    pane=tk.PanedWindow(master,orient=orient,sashwidth=max(12,round(12*pixel_scale(master))),
                        sashrelief='raised',showhandle=True,handlesize=max(10,round(10*pixel_scale(master))),
                        borderwidth=0,relief='flat',bg='#94a3b8')
    if not hasattr(root,'_split_panes'):root._split_panes={}
    root._split_panes[key]=pane
    return pane


def flow_toolbar(frame):
    """Wrap related controls onto another row when the available width shrinks."""
    controls=[w for w in frame.winfo_children() if w.winfo_manager() in ('grid','pack')]
    for widget in controls:
        if isinstance(widget,ctk.CTkButton):
            font=widget.cget('font')
            if isinstance(font,ctk.CTkFont):
                if font.cget('size')<14:font.configure(size=14)
                widget.configure(width=max(widget.cget('width'),font.measure(widget.cget('text'))+28))
    columns=frame.grid_size()[0]
    for col in range(columns):frame.grid_columnconfigure(col,weight=0,minsize=0)
    frame.grid_columnconfigure(0,weight=1)
    groups=[]
    index=0
    while index<len(controls):
        group=ctk.CTkFrame(frame,fg_color='transparent',corner_radius=0)
        related=[controls[index]]
        if (isinstance(controls[index],ctk.CTkLabel) and index+1<len(controls)
                and isinstance(controls[index+1],(ctk.CTkComboBox,ctk.CTkEntry))):
            related.append(controls[index+1]);index+=1
        for col,widget in enumerate(related):
            if widget.winfo_manager()=='pack':widget.pack_forget()
            else:widget.grid_forget()
            widget.grid(in_=group,row=0,column=col,padx=4,pady=3,sticky='w')
            widget.lift()
        groups.append(group);index+=1
    rows=[];last=None;timer=None
    def arrange():
        nonlocal last,timer
        timer=None
        if not frame.winfo_exists():return
        available=max(160,frame.winfo_width()-12)
        lines=[];line=[];used=0
        for group in groups:
            width=group.winfo_reqwidth()+8
            if line and used+width>available:lines.append(line);line=[];used=0
            line.append(group);used+=width
        if line:lines.append(line)
        layout=tuple(tuple(str(g) for g in line) for line in lines)
        if layout==last:return
        last=layout
        while len(rows)<len(lines):
            rows.append(ctk.CTkFrame(frame,fg_color='transparent',corner_radius=0))
        for row in rows:row.grid_remove()
        for index,line in enumerate(lines):
            host=rows[index];host.grid(row=index,column=0,sticky='w')
            for col,group in enumerate(line):
                group.grid(in_=host,row=0,column=col,padx=2,pady=1,sticky='w')
                group.lift()
        for widget in controls:widget.lift()
    def changed(event=None):
        nonlocal timer
        if timer:frame.after_cancel(timer)
        timer=frame.after(80,arrange)
    frame.bind('<Configure>',changed,add='+')
    changed()
    return frame


class PageBook(ctk.CTkFrame):
    """Small Tabview-compatible API with a vertically scrollable navigation list."""
    def __init__(self,master,**kwargs):
        super().__init__(master,**kwargs)
        self.grid_rowconfigure(0,weight=1);self.grid_columnconfigure(0,weight=1)
        self.divider=split(self,'navegacion')
        self.divider.grid(row=0,column=0,sticky='nsew')
        self.sidebar=scroll_area(self.divider,width=190)
        self.sidebar.grid_columnconfigure(0,weight=1)
        self.content=ctk.CTkFrame(self.divider,fg_color='transparent')
        self.content.grid_columnconfigure(0,weight=1);self.content.grid_rowconfigure(0,weight=1)
        scale=pixel_scale(self)
        self.divider.add(self.sidebar.container,width=round(170*scale),minsize=round(120*scale),stretch='never')
        self.divider.add(self.content,minsize=round(250*scale),stretch='always')
        self._pages={};self._buttons={};self._current=None

    def add(self,name,label=None):
        if name in self._pages:raise ValueError('Página repetida.')
        frame=ctk.CTkFrame(self.content,fg_color='transparent')
        frame.grid(row=0,column=0,sticky='nsew')
        display={'Config. Cursos':'Cursos y\ncapacidades','Ingresar Calificativos':'Ingresar\ncalificativos','Prácticas y puntos':'Prácticas y\npuntos','Porcentajes de Actividades':'Pesos del\npromedio'}.get(name,label or name)
        button=ctk.CTkButton(self.sidebar,text=display,height=46,anchor='w',
            font=ctk.CTkFont(size=14),fg_color='transparent',text_color=('#0f172a','#f8fafc'),
            command=lambda:self.set(name))
        button.grid(row=len(self._pages),column=0,sticky='ew',padx=4,pady=3)
        self._pages[name]=frame;self._buttons[name]=button
        if self._current is None:self.set(name)
        else:frame.grid_remove()
        return frame

    def set(self,name):
        if name not in self._pages:raise ValueError('La sección no existe.')
        if self._current:self._pages[self._current].grid_remove()
        self._pages[name].grid();self._pages[name].tkraise();self._current=name
        for title,button in self._buttons.items():
            button.configure(fg_color='#2563eb' if title==name else 'transparent',
                             text_color='#ffffff' if title==name else ('#0f172a','#f8fafc'))

    def get(self):return self._current
    def tab(self,name):return self._pages[name]


def grade_panels(master,headers,tree_class,key="nombres_notas"):
    """Keep names visible and let the user drag the division to widen them."""
    pane=split(master,key)
    pane.grid(row=1,column=0,columnspan=3,sticky='nsew')
    master.grid_rowconfigure(0,weight=0);master.grid_rowconfigure(1,weight=1);master.grid_columnconfigure(0,weight=1)
    left=ctk.CTkFrame(pane,fg_color='transparent');right=ctk.CTkFrame(pane,fg_color='transparent')
    for frame in (left,right):frame.grid_rowconfigure(0,weight=1);frame.grid_columnconfigure(0,weight=1)
    scale=pixel_scale(master)
    available=max(600,master.winfo_width())
    pane.add(left,width=round(min(330*scale,max(190*scale,available*.34))),minsize=round(140*scale),stretch='never');pane.add(right,minsize=round(180*scale),stretch='always')
    tree=tree_class(right,columns=headers,show='headings',displaycolumns=headers[3:])
    tree.grid(row=0,column=0,sticky='nsew')
    identity=ttk.Treeview(left,columns=('codigo','alumno'),show='headings',selectmode='browse')
    scale=pixel_scale(master)
    identity.heading('codigo',text='Código');identity.heading('alumno',text='Apellidos y nombres')
    identity.column('codigo',width=round(75*scale),minwidth=round(45*scale),stretch=False)
    identity.column('alumno',width=round(235*scale),minwidth=round(80*scale),stretch=True)
    identity.grid(row=0,column=0,sticky='nsew')
    def both(*args):tree.yview(*args);identity.yview(*args)
    sy=scrollbar(right,'vertical',both);sy.grid(row=0,column=1,sticky='ns')
    sx=scrollbar(right,'horizontal',tree.xview);sx.grid(row=1,column=0,sticky='ew')
    ix=scrollbar(left,'horizontal',identity.xview);ix.grid(row=1,column=0,sticky='ew')
    def scroll_main(first,last):
        sy.set(first,last)
        if abs(identity.yview()[0]-float(first))>.001:identity.yview_moveto(first)
    def scroll_names(first,last):
        if abs(tree.yview()[0]-float(first))>.001:tree.yview_moveto(first)
    tree.configure(yscrollcommand=scroll_main,xscrollcommand=sx.set)
    identity.configure(yscrollcommand=scroll_names,xscrollcommand=ix.set)
    def selection(source,target):
        if source.selection() and source.selection()!=target.selection():
            target.selection_set(source.selection());target.focus(source.selection()[0])
    identity.bind('<<TreeviewSelect>>',lambda e:selection(identity,tree))
    tree.bind('<<TreeviewSelect>>',lambda e:selection(tree,identity))
    tree.bind('<MouseWheel>',lambda e: (both('scroll',-1 if e.delta>0 else 1,'units'),'break')[-1])
    identity.bind('<MouseWheel>',lambda e: (both('scroll',-1 if e.delta>0 else 1,'units'),'break')[-1])
    return tree,identity,pane
