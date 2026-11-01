"""Scrollable content using native ttk scrollbars (no recursive idle redraw)."""
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk


def scroll_area(master, **kwargs):
    outer=ctk.CTkFrame(master,**kwargs)
    color=outer._apply_appearance_mode(outer.cget('fg_color'))
    canvas=tk.Canvas(outer,highlightthickness=0,bg=color)
    scrollbar=ttk.Scrollbar(outer,orient='vertical',command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.grid(row=0,column=0,sticky='nsew',padx=4,pady=4)
    scrollbar.grid(row=0,column=1,sticky='ns',padx=(0,4))
    outer.grid_rowconfigure(0,weight=1);outer.grid_columnconfigure(0,weight=1)
    inner=ctk.CTkFrame(canvas,fg_color='transparent')
    window=canvas.create_window((0,0),window=inner,anchor='nw')
    inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')),add='+')
    canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=max(e.width,1)))
    # Callers lay out the outer viewport and place their children in inner.
    inner.grid=outer.grid;inner.pack=outer.pack;inner.place=outer.place
    inner.viewport=canvas;inner.container=outer
    root=master.winfo_toplevel()
    if not hasattr(root,'_scroll_areas'):root._scroll_areas=[]
    root._scroll_areas.append(inner)
    def wheel(event):
        canvas.yview_scroll(-int(event.delta/120) if event.delta else (-1 if event.num==4 else 1),'units')
        return 'break'
    def bind_children(widget):
        widget.bind('<MouseWheel>',wheel,add='+')
        widget.bind('<Button-4>',wheel,add='+');widget.bind('<Button-5>',wheel,add='+')
        for child in widget.winfo_children():bind_children(child)
    inner.after(500,lambda:bind_children(inner))
    return inner


def wrap_label(label):
    """Debounce wrapping after geometry settles; never recurse through idle drawing."""
    def on_size(event):
        width=max(120,int(label.winfo_width()/label._get_widget_scaling())-12)
        if abs(float(label.cget('wraplength') or 0)-width)<4:return
        pending=getattr(label,'_wrap_job',None)
        if pending:label.after_cancel(pending)
        def apply():
            label._wrap_job=None
            if label.winfo_exists():label.configure(wraplength=width)
        label._wrap_job=label.after(100,apply)
    label.bind('<Configure>',on_size,add='+')
