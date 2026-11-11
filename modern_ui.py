"""Shared visual vocabulary for teacher-facing cards and readable detail panes."""
from tkinter import ttk
import customtkinter as ctk
from widgets import wrap_label
from interfaz import scrollbar


def card(parent,**kwargs):
    frame=ctk.CTkFrame(parent,fg_color=('#ffffff','#17283b'),border_width=1,
        border_color=('#dceaf3','#334155'),corner_radius=12,**kwargs)
    frame._preserve_theme=True;return frame


def caption(parent,text,large=False,muted=False):
    label=ctk.CTkLabel(parent,text=text,anchor='w',justify='left',font=ctk.CTkFont(size=21 if large else 14,weight='bold' if large else 'normal'),
        text_color=('#64748b','#cbd5e1') if muted else ('#0c4a6e','#e0f2fe'))
    wrap_label(label);return label


def metric(parent,title,value):
    frame=card(parent);caption(frame,title,muted=True).pack(fill='x',padx=15,pady=(12,3))
    label=caption(frame,value,large=True);label.pack(fill='x',padx=15,pady=(0,13))
    return frame,label


def table(parent,columns):
    frame=card(parent);frame.grid_columnconfigure(0,weight=1);frame.grid_rowconfigure(0,weight=1)
    tree=ttk.Treeview(frame,columns=[key for key,_,_ in columns],show='headings',selectmode='browse')
    for key,title,width in columns:
        tree.heading(key,text=title)
        tree.column(key,width=width,minwidth=65,stretch=True,anchor='center' if key in ('nota','promedio','avance','asistencia','criterios','estado') else 'w')
    tree.grid(row=0,column=0,sticky='nsew',padx=(6,0),pady=(6,0))
    sy=scrollbar(frame,'vertical',tree.yview);sy.grid(row=0,column=1,sticky='ns',pady=6)
    sx=scrollbar(frame,'horizontal',tree.xview);sx.grid(row=1,column=0,sticky='ew',padx=6)
    tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
    return frame,tree
