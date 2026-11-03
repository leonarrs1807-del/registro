"""Adaptive desktop navigation, adjustable dividers and usable scrollbars."""
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from widgets import scroll_area, wrap_label, Tooltip
from ui_icons import icon
from grade_cells import GradeTreeview


def pixel_scale(widget):
    try:return ctk.ScalingTracker.get_widget_scaling(widget)
    except (KeyError,AttributeError):return 1


def scrollbar(master,orient,command):
    return tk.Scrollbar(master,orient=orient,command=command,width=max(22,round(22*pixel_scale(master))),
                        relief='flat',borderwidth=1,elementborderwidth=1)


def split(master,key,orient='horizontal'):
    root=master.winfo_toplevel()
    pane=tk.PanedWindow(master,orient=orient,sashwidth=max(6,round(6*pixel_scale(master))),
                        sashrelief='flat',showhandle=False,
                        borderwidth=0,relief='flat',bg='#94a3b8')
    if not hasattr(root,'_split_panes'):root._split_panes={}
    root._split_panes[key]=pane
    return pane


def flow_toolbar(frame):
    """Wrap direct children without nested geometry masters or resize cycles."""
    root=frame.winfo_toplevel()
    controls=[w for w in frame.winfo_children() if w.winfo_manager() in ('grid','pack')]
    for widget in controls:
        if widget.winfo_manager()=='pack':widget.pack_forget()
        else:widget.grid_forget()
        if isinstance(widget,ctk.CTkButton):
            font=widget.cget('font')
            if isinstance(font,ctk.CTkFont):
                widget.configure(width=max(widget.cget('width'),font.measure(widget.cget('text'))+28))
    groups=[];index=0
    while index<len(controls):
        group=[controls[index]]
        if isinstance(controls[index],ctk.CTkLabel) and index+1<len(controls) and isinstance(controls[index+1],(ctk.CTkComboBox,ctk.CTkEntry)):
            group.append(controls[index+1]);index+=1
        groups.append(group);index+=1
    natural={w:max(float(w.cget('width')),w.winfo_reqwidth()/pixel_scale(w)) for w in controls}
    timer=None;last=None
    def arrange():
        nonlocal timer,last
        timer=None
        if getattr(root,'_closing_ui',False) or not frame.winfo_exists() or frame.winfo_width()<2:return
        scale=pixel_scale(frame);available=max(100,frame.winfo_width()/scale-12)
        x=6;y=6;row_height=0;layout=[]
        for group in groups:
            widths=[max(natural[w],w.winfo_reqwidth()/scale) for w in group]
            width=sum(widths)+10*(len(group)-1)
            if x>6 and x+width>available:y+=row_height+8;x=6;row_height=0
            if width>available-6 and isinstance(group[-1],(ctk.CTkComboBox,ctk.CTkEntry)):
                widths[-1]=max(70,available-6-sum(widths[:-1])-10*(len(group)-1))
            for widget,width in zip(group,widths):
                height=max(28,widget.winfo_reqheight()/scale)
                layout.append((widget,x,y,width));row_height=max(row_height,height);x+=width+10
        height=y+row_height+6
        key=tuple((str(w),round(x),round(y),round(width)) for w,x,y,width in layout)+(round(height),)
        if key==last:return
        last=key
        # Each row has its own positions. Shared grid columns would force narrow
        # rows to inherit the widths of unrelated controls on other rows.
        frame.configure(height=height)
        for widget,x,y,width in layout:
            if isinstance(widget,(ctk.CTkComboBox,ctk.CTkEntry)) and abs(float(widget.cget('width'))-width)>1:widget.configure(width=width)
            widget.place(x=x,y=y)
    def changed(event=None):
        nonlocal timer
        if getattr(root,'_closing_ui',False):return
        if timer:frame.after_cancel(timer)
        timer=frame.after(60,arrange)
    def cleanup(event):
        if event.widget is frame and timer:
            try:frame.after_cancel(timer)
            except tk.TclError:pass
    frame.bind('<Configure>',changed,add='+');tk.Misc.bind(frame,'<Destroy>',cleanup,add='+');changed()
    return frame


class PageBook(ctk.CTkFrame):
    """Collapsible icon navigation; page IDs remain compatible with saved workflows."""
    ITEMS={
        'Config. Cursos':('Configuración','settings'), 'Estudiantes':('Estudiantes','students'),
        'Crear Actividad':('Actividades','activity'), 'Ingresar Calificativos':('Calificaciones','grades'),
        'Buscador':('Buscar','search'), 'Porcentajes de Actividades':('Ponderaciones','weights'),
        'Matriz General':('Matriz','matrix'), 'Estadísticas':('Estadísticas','stats'),
        'Prácticas y puntos':('Puntos','points'), 'Instrucciones':('Ayuda','help')}
    def __init__(self,master,**kwargs):
        super().__init__(master,fg_color='transparent',**kwargs)
        self.grid_rowconfigure(0,weight=1);self.grid_columnconfigure(1,weight=1)
        self.expanded=False
        self.sidebar=scroll_area(self,width=54,scrollbar_width=8,auto_hide=True,corner_radius=8)
        self.sidebar.container.grid(row=0,column=0,sticky='ns',padx=(0,8))
        self.sidebar.container.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0,weight=1)
        self.content=ctk.CTkFrame(self,fg_color='transparent',corner_radius=8)
        self.content.grid(row=0,column=1,sticky='nsew')
        self.content.grid_columnconfigure(0,weight=1);self.content.grid_rowconfigure(0,weight=1)
        self._pages={};self._buttons={};self._current=None

    def add(self,name,label=None):
        if name in self._pages:raise ValueError('Página repetida.')
        frame=ctk.CTkFrame(self.content,fg_color='transparent')
        frame.grid(row=0,column=0,sticky='nsew')
        title,picture=self.ITEMS[name]
        button=ctk.CTkButton(self.sidebar,text='',image=icon(picture,master=self),height=40,width=40,
            corner_radius=8,font=ctk.CTkFont(size=13),fg_color='transparent',
            hover_color=('#e2e8f0','#334155'),command=lambda:self.set(name))
        button.grid(row=len(self._pages),column=0,sticky='ew',padx=3,pady=3)
        Tooltip(button,lambda: '' if self.expanded else title)
        self._pages[name]=frame;self._buttons[name]=button
        if self._current is None:self.set(name)
        else:frame.grid_remove()
        return frame

    def toggle(self):self.set_expanded(not self.expanded)

    def set_expanded(self,expanded,save=True):
        self.expanded=bool(expanded)
        self.sidebar.container.configure(width=200 if self.expanded else 54)
        for name,button in self._buttons.items():
            button.configure(text=self.ITEMS[name][0] if self.expanded else '',
                             anchor='w' if self.expanded else 'center',width=182 if self.expanded else 40)
        root=self.winfo_toplevel()
        if save and hasattr(root,'_guardar_ventana'):root._guardar_ventana()

    def set(self,name):
        if name not in self._pages:raise ValueError('La sección no existe.')
        if self._current:self._pages[self._current].grid_remove()
        self._pages[name].grid();self._pages[name].tkraise();self._current=name
        for title,button in self._buttons.items():
            selected=title==name
            button.configure(fg_color=('#bae6fd','#075985') if selected else 'transparent',
                             image=icon(self.ITEMS[title][1],active=selected and ctk.get_appearance_mode()=="Dark",master=self),
                             text_color=('#075985','#f0f9ff') if selected else ('#334155','#e2e8f0'))
        if self.expanded and self.winfo_width()/pixel_scale(self)<1000:self.set_expanded(False)
        root=self.winfo_toplevel()
        if hasattr(root,'tabview') and hasattr(root,'al_mostrar_pagina'):root.al_mostrar_pagina(name)

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
    identity=GradeTreeview(left,columns=('codigo','alumno'),show='headings',selectmode='browse')
    scale=pixel_scale(master)
    identity.heading('codigo',text='N°');identity.heading('alumno',text='Apellidos y nombres')
    identity.column('codigo',width=round(38*scale),minwidth=round(28*scale),stretch=False)
    identity.column('alumno',width=round(235*scale),minwidth=round(80*scale),stretch=True)
    identity.grid(row=0,column=0,sticky='nsew')
    def both(*args):tree.yview(*args);identity.yview(*args)
    sy=scrollbar(right,'vertical',both);sy.grid(row=0,column=1,sticky='ns')
    sx=scrollbar(right,'horizontal',tree.xview);sx.grid(row=1,column=0,sticky='ew')
    ix=scrollbar(left,'horizontal',identity.xview);ix.grid(row=1,column=0,sticky='ew')
    def scroll_main(first,last):
        auto_bar(sy,first,last)
        if abs(identity.yview()[0]-float(first))>.001:identity.yview_moveto(first)
    def scroll_names(first,last):
        if abs(tree.yview()[0]-float(first))>.001:tree.yview_moveto(first)
    def auto_bar(bar,first,last):
        bar.set(first,last)
        if float(first)<=0 and float(last)>=1:bar.grid_remove()
        else:bar.grid()
    tree.configure(yscrollcommand=scroll_main,xscrollcommand=lambda f,l:auto_bar(sx,f,l))
    identity.configure(yscrollcommand=scroll_names,xscrollcommand=lambda f,l:auto_bar(ix,f,l))
    def selection(source,target):
        if source.selection() and source.selection()!=target.selection():
            target.selection_set(source.selection());target.focus(source.selection()[0])
    identity.bind('<<TreeviewSelect>>',lambda e:selection(identity,tree))
    tree.bind('<<TreeviewSelect>>',lambda e:selection(tree,identity))
    tree.bind('<MouseWheel>',lambda e: (both('scroll',-1 if e.delta>0 else 1,'units'),'break')[-1])
    identity.bind('<MouseWheel>',lambda e: (both('scroll',-1 if e.delta>0 else 1,'units'),'break')[-1])
    return tree,identity,pane
