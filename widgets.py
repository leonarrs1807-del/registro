"""Scrollable content using native ttk scrollbars (no recursive idle redraw)."""
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk


def scroll_area(master, scrollbar_width=22, auto_hide=False, horizontal=False, min_width=0, **kwargs):
    outer=ctk.CTkFrame(master,**kwargs)
    color=outer._apply_appearance_mode(outer.cget('fg_color'))
    canvas=tk.Canvas(outer,highlightthickness=0,bg=color)
    root=master.winfo_toplevel()
    try:scale=ctk.ScalingTracker.get_widget_scaling(root)
    except KeyError:scale=1
    scrollbar=tk.Scrollbar(outer,orient='vertical',command=canvas.yview,width=max(8,round(scrollbar_width*scale)))
    def moved(first,last):
        scrollbar.set(first,last)
        if auto_hide:
            if float(first)<=0 and float(last)>=1:scrollbar.grid_remove()
            else:scrollbar.grid()
    canvas.configure(yscrollcommand=moved)
    canvas.grid(row=0,column=0,sticky='nsew',padx=4,pady=4)
    scrollbar.grid(row=0,column=1,sticky='ns',padx=(0,4))
    outer.grid_rowconfigure(0,weight=1);outer.grid_columnconfigure(0,weight=1)
    if horizontal:
        sx=tk.Scrollbar(outer,orient='horizontal',command=canvas.xview,width=max(12,round(scrollbar_width*scale)))
        sx.grid(row=1,column=0,sticky='ew')
        def moved_x(first,last):
            sx.set(first,last)
            if auto_hide:
                if float(first)<=0 and float(last)>=1:sx.grid_remove()
                else:sx.grid()
        canvas.configure(xscrollcommand=moved_x)
    inner=ctk.CTkFrame(canvas,fg_color='transparent')
    window=canvas.create_window((0,0),window=inner,anchor='nw')
    inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')),add='+')
    canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=max(e.width,round(min_width*ctk.ScalingTracker.get_widget_scaling(root)),1)))
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
    wheel_job=inner.after(500,lambda:bind_children(inner))
    def cleanup(event):
        if event.widget is inner:
            try:inner.after_cancel(wheel_job)
            except tk.TclError:pass
    inner.bind('<Destroy>',cleanup,add='+')
    return inner


class Tooltip:
    def __init__(self,widget,text):
        self.widget=widget;self.text=text;self.job=None;self.popup=None
        widget.bind('<Enter>',self.schedule,add='+')
        widget.bind('<Leave>',self.hide,add='+');widget.bind('<ButtonPress>',self.hide,add='+')
        widget.bind('<Destroy>',self.hide,add='+')
    def schedule(self,event=None):
        self.hide();self.job=self.widget.after(550,self.show)
    def show(self):
        self.job=None
        if not self.widget.winfo_exists():return
        text=self.text() if callable(self.text) else self.text
        if not text:return
        scale=ctk.ScalingTracker.get_widget_scaling(self.widget)
        self.popup=tk.Toplevel(self.widget);self.popup.withdraw();self.popup.overrideredirect(True)
        tk.Label(self.popup,text=text,background='#0f172a',foreground='white',font=('Segoe UI',-round(14*scale)),
                 padx=round(10*scale),pady=round(6*scale),
                 wraplength=min(round(480*scale),self.widget.winfo_screenwidth()-32),justify='left').pack()
        self.popup.update_idletasks()
        x=min(self.widget.winfo_pointerx()+12,self.widget.winfo_screenwidth()-self.popup.winfo_reqwidth()-12)
        y=min(self.widget.winfo_pointery()+18,self.widget.winfo_screenheight()-self.popup.winfo_reqheight()-12)
        self.popup.geometry(f'+{max(0,x)}+{max(0,y)}');self.popup.deiconify()
    def hide(self,event=None):
        if self.job:
            try:self.widget.after_cancel(self.job)
            except tk.TclError:pass
            self.job=None
        if self.popup:
            try:self.popup.destroy()
            except tk.TclError:pass
            self.popup=None


def wrap_label(label):
    """Debounce wrapping after geometry settles; never recurse through idle drawing."""
    if getattr(label,'_wrap_bound',False):return
    label._wrap_bound=True
    root=label.winfo_toplevel()
    def on_size(event):
        if getattr(root,'_closing_ui',False):return
        width=max(120,int(label.winfo_width()/label._get_widget_scaling())-12)
        if abs(float(label.cget('wraplength') or 0)-width)<4:return
        pending=getattr(label,'_wrap_job',None)
        if pending:label.after_cancel(pending)
        def apply():
            label._wrap_job=None
            if label.winfo_exists():label.configure(wraplength=width)
        label._wrap_job=label.after(100,apply)
    label.bind('<Configure>',on_size,add='+')
    on_size(None)
    def cleanup(event):
        pending=getattr(label,'_wrap_job',None)
        if event.widget is label and pending:
            try:label.after_cancel(pending)
            except tk.TclError:pass
            label._wrap_job=None
    label.bind('<Destroy>',cleanup,add='+')
