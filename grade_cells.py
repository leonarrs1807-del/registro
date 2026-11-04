"""Per-cell achievement colors without changing Treeview data or editing APIs."""
import re
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from escala import thresholds

PALETTE={
    'C':('#fee2e2','#991b1b'), 'B':('#fef3c7','#854d0e'),
    'A':('#dcfce7','#166534'), 'AD':('#dbeafe','#1e40af')}


def grade_number(value):
    match=re.match(r'^\s*(?:✎\s*)?(-?\d+(?:[.,]\d+)?)\s*(?:\([A-Z]+\))?\s*$',str(value))
    if not match:return None
    number=float(match[1].replace(',','.'))
    return number if 0<=number<=20 else None


def achievement(value,limits):
    number=grade_number(value)
    if number is None:return None
    b,a,ad=limits
    return 'C' if number<b else 'B' if number<a else 'A' if number<ad else 'AD'


class GradeTreeview(ttk.Treeview):
    def __init__(self,master,**kwargs):
        super().__init__(master,**kwargs)
        self.grade_columns=();self._color_job=None;self._cell_pool=[]
        for event in ('<Configure>','<Expose>','<<TreeviewSelect>>','<KeyRelease>','<B1-Motion>','<ButtonRelease-1>'):
            self.bind(event,self.queue_colors,add='+')
        self.bind('<Destroy>',self._close_colors,add='+')

    def set_grade_columns(self,columns):
        self.grade_columns=tuple(columns);self.queue_colors()

    def queue_colors(self,event=None):
        if not self.grade_columns or self._color_job or not self.winfo_exists() or getattr(self.winfo_toplevel(),'_closing_ui',False):return
        self._color_job=self.after(35,self.paint_grades)

    def _close_colors(self,event):
        if event.widget is self and self._color_job:
            try:self.after_cancel(self._color_job)
            except tk.TclError:pass
            self._color_job=None

    def item(self,*args,**kwargs):
        result=super().item(*args,**kwargs)
        if kwargs:self.queue_colors()
        return result

    def set(self,item,column=None,value=None):
        result=super().set(item,column,value)
        if value is not None:self.queue_colors()
        return result

    def insert(self,*args,**kwargs):
        result=super().insert(*args,**kwargs);self.queue_colors();return result

    def delete(self,*args):
        result=super().delete(*args);self.queue_colors();return result

    def xview(self,*args):
        result=super().xview(*args)
        if args:self.queue_colors()
        return result

    def yview(self,*args):
        result=super().yview(*args)
        if args:self.queue_colors()
        return result

    def xview_moveto(self,*args):super().xview_moveto(*args);self.queue_colors()
    def yview_moveto(self,*args):super().yview_moveto(*args);self.queue_colors()
    def see(self,*args):super().see(*args);self.queue_colors()

    def _forward(self,label,sequence,event):
        self.event_generate(sequence,x=label.winfo_x()+event.x,y=label.winfo_y()+event.y,
                            **({'delta':event.delta} if sequence=='<MouseWheel>' else {}))
        return 'break'

    def paint_grades(self):
        self._color_job=None
        if not self.winfo_exists() or not self.winfo_ismapped():return
        root=self.winfo_toplevel()
        from db import DB_PATH
        limits=thresholds(getattr(root,'_db_path',DB_PATH))
        style=ttk.Style(self);font=style.lookup('Treeview','font')
        native=getattr(root,'_native_table_font_size',-16)
        key=(font,native)
        if key!=getattr(self,'_cell_font_key',None):
            self._cell_font=tkfont.Font(root=self,family='Segoe UI',size=native,weight='bold');self._cell_font_key=key
        minimum=self._cell_font.measure('20.00 (AD)')+18
        for column in self.grade_columns:
            if self.column(column,'width')<minimum:self.column(column,width=minimum,minwidth=minimum)
        used=0;width=self.winfo_width();height=self.winfo_height()
        visible=[]
        # Inspect only rows occupying the viewport; large rosters remain cheap.
        rowheight=max(1,int(style.lookup('Treeview','rowheight') or 30))
        for y in range(0,height+rowheight,rowheight//2 or 1):
            row=self.identify_row(y)
            if row and row not in visible:visible.append(row)
        selected=set(self.selection())
        for row in visible:
            for column in self.grade_columns:
                bounds=self.bbox(row,column)
                if not bounds:continue
                x,y,w,h=bounds
                if x+w<=0 or x>=width or y<1 or y>=height:continue
                value=self.set(row,column);appearance=self.cell_appearance(value,column,limits)
                if appearance is None:continue
                if used==len(self._cell_pool):
                    label=tk.Label(self,borderwidth=0,padx=0,pady=0,justify='center',takefocus=False)
                    for sequence in ('<Button-1>','<ButtonRelease-1>','<B1-Motion>','<Button-3>','<MouseWheel>','<Button-4>','<Button-5>'):
                        label.bind(sequence,lambda e,s=sequence,l=label:self._forward(l,s,e))
                    def double(event,l=label):
                        handler=getattr(self,'on_double_click',None) or getattr(self,'edit_cell',None)
                        if handler:
                            from types import SimpleNamespace
                            handler(SimpleNamespace(x=l.winfo_x()+event.x,y=l.winfo_y()+event.y,widget=self))
                        return 'break'
                    label.bind('<Double-1>',double)
                    self._cell_pool.append(label)
                label=self._cell_pool[used];used+=1
                background,foreground,text=appearance
                label.configure(text=text,background=background,foreground=foreground,font=self._cell_font,
                    highlightthickness=2 if getattr(self,'active_cell',None)==(row,column) else 1 if row in selected else 0,highlightbackground='#2563eb')
                label.place(x=x+1,y=y+1,width=max(1,w-2),height=max(1,h-2))
        for label in self._cell_pool[used:]:label.place_forget()
        editor=getattr(self,'_entry',None) or getattr(self,'editor',None)
        if editor is not None and editor.winfo_exists():editor.lift()

    def cell_appearance(self,value,column,limits):
        level=achievement(value,limits)
        if level is None:return None
        background,foreground=PALETTE[level]
        return background,foreground,str(value).split('(')[0].strip()+f' ({level})'


class CriterionTreeview(GradeTreeview):
    """Cotejo states and rubric points use their own cell appearance."""
    def xview(self,*args):
        result=super().xview(*args)
        if args and callable(getattr(self,'on_horizontal_change',None)):self.on_horizontal_change()
        return result

    def xview_moveto(self,*args):
        super().xview_moveto(*args)
        if callable(getattr(self,'on_horizontal_change',None)):self.on_horizontal_change()

    def cell_appearance(self,value,column,limits):
        if value in ('Sí','No','Sin evaluar','Pendiente'):
            return {'Sí':('#dcfce7','#166534','✓ Sí'),'No':('#fee2e2','#991b1b','✕ No'),
                    'Sin evaluar':('#f1f5f9','#64748b','—'),'Pendiente':('#f1f5f9','#64748b','Pendiente')}[value]
        match=re.search(r'\((C|B|A|AD)\)$',str(value))
        if match:
            bg,fg=PALETTE[match[1]];return bg,fg,str(value)
        return None

