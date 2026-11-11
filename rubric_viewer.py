"""Read-only rubric matrices: every criterion shares aligned achievement columns."""
import customtkinter as ctk
from widgets import scroll_area,wrap_label,SafeDialog,polish_dialog
from colores import HEADER,HEADER_TEXT,BORDER
from grade_cells import PALETTE
from instrumentos import LEVELS,LEVEL_NAMES,criterion_caption
from temas import topic_name


class TopicField(ctk.CTkFrame):
    def __init__(self,parent,value=''):
        super().__init__(parent,fg_color='transparent')
        self.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(self,text='Tema de la actividad que vas a usar',anchor='w',font=ctk.CTkFont(size=14,weight='bold')).grid(row=0,column=0,sticky='ew',pady=(0,4))
        self.entry=ctk.CTkEntry(self,height=37,font=ctk.CTkFont(size=15));self.entry.grid(row=1,column=0,sticky='ew')
        self.set(value)

    def get(self):return self.entry.get()
    def set(self,value):self.entry.delete(0,'end');self.entry.insert(0,value)
    def value(self):return topic_name(self.get())


class RubricTable(ctk.CTkFrame):
    def __init__(self,parent,indicators=()):
        super().__init__(parent,fg_color='transparent')
        self._preserve_theme=True;self.indicators=[];self.headers=[];self.cells={}
        self.grid_rowconfigure(0,weight=1);self.grid_columnconfigure(0,weight=1)
        self.body=scroll_area(self,auto_hide=True,horizontal=True,min_width=1080)
        self.body.grid(row=0,column=0,sticky='nsew');self.body.grid_columnconfigure(0,weight=1)
        self.set_indicators(indicators)

    def _label(self,parent,text,color,bold=False):
        widget=ctk.CTkLabel(parent,text=str(text),anchor='nw',justify='left',text_color=color,
            font=ctk.CTkFont(size=14,weight='bold' if bold else 'normal'),wraplength=140)
        widget.pack(fill='both',expand=True,padx=10,pady=11);wrap_label(widget);return widget

    def set_indicators(self,indicators):
        self.indicators=list(indicators);self.cells={};self.headers=[]
        for child in self.body.winfo_children():child.destroy()
        if not self.indicators:
            self._label(self.body,'Selecciona una rúbrica para ver sus criterios y niveles en tabla.','#64748b');return
        rubric=self.indicators[0].get('tipo','Rúbrica')=='Rúbrica'
        columns=[('Capacidad',150),('Criterio',190),('Máx.',60)]+[(f'{level} · {LEVEL_NAMES[level]}',165) for level in LEVELS] if rubric else [('Capacidad',220),('Indicador observable',540),('Valor',100)]
        self.body.container.configure(width=1060 if rubric else 860)
        table=ctk.CTkFrame(self.body,fg_color=BORDER,corner_radius=0);table.grid(row=0,column=0,sticky='nsew',padx=3,pady=3)
        self.table=table
        for col,(title,width) in enumerate(columns):
            table.grid_columnconfigure(col,weight=1 if col!=2 else 0,minsize=width)
            bg,fg=PALETTE[LEVELS[col-3]] if rubric and col>=3 else (HEADER,HEADER_TEXT)
            cell=ctk.CTkFrame(table,fg_color=bg,corner_radius=0);cell.grid(row=0,column=col,sticky='nsew',padx=1,pady=1)
            self.headers.append(self._label(cell,title,fg,True))
        for row,item in enumerate(self.indicators,1):
            maximum=item.get('puntaje_maximo',20)
            values=[item.get('capacidad_nombre',''),criterion_caption(item),f'{float(maximum):g}']
            if rubric:values.extend(item.get('descriptores',{}).get(level,'') for level in LEVELS)
            for col,text in enumerate(values):
                bg,fg=PALETTE[LEVELS[col-3]] if rubric and col>=3 else ('#ffffff' if row%2 else '#f5faff','#0f172a')
                cell=ctk.CTkFrame(table,fg_color=bg,corner_radius=0);cell.grid(row=row,column=col,sticky='nsew',padx=1,pady=1)
                self.cells[row,col]=self._label(cell,text,fg,col in (0,1))

    def get(self,*args):
        return '\n'.join(str(value.cget('text')) for value in self.cells.values())


class RubricViewer(SafeDialog):
    def __init__(self,app,model):
        super().__init__(app);self.title('Rúbrica en tabla');self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(2,weight=1)
        title=ctk.CTkLabel(self,text=model['nombre'],anchor='w',justify='left',font=ctk.CTkFont(size=21,weight='bold'))
        title.grid(row=0,column=0,sticky='ew',padx=18,pady=(16,5));wrap_label(title)
        summary=ctk.CTkLabel(self,text=model['competencia']+'\nPropósito: '+(model.get('proposito') or 'Por completar'),anchor='w',justify='left',font=ctk.CTkFont(size=14))
        summary.grid(row=1,column=0,sticky='ew',padx=18,pady=5);wrap_label(summary)
        self.rubric=RubricTable(self,[{**item,'tipo':model['tipo']} for item in model['criterios']]);self.rubric.grid(row=2,column=0,sticky='nsew',padx=14,pady=10)
        from colores import button
        ctk.CTkButton(self,text='Cerrar',**button(),command=self.destroy).grid(row=3,column=0,sticky='e',padx=18,pady=12)
        polish_dialog(self,app,1320,800)
