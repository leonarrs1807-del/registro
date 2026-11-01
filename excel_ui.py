"""Choose Excel criteria counts without first creating an application instrument."""
from tkinter import messagebox
import customtkinter as ctk
from widgets import SafeDialog,scroll_area
from instrument_design import fit
from instrument_widgets import label


class TemplateOptions(SafeDialog):
    def __init__(self,app,activity,kind,indicators):
        super().__init__(app);self.title('Preparar plantilla Excel');fit(self,app,760,min(650,240+78*len(activity['capacidades'])))
        self.result=None;self.ready=False;self.counts={};self.has_instrument=bool(indicators)
        label(self,activity['titulo_tema']).pack(fill='x',padx=18,pady=(14,4))
        label(self,f'{kind} · {activity["grado"]} {activity["seccion"]}').pack(fill='x',padx=18,pady=(0,8))
        self.source=ctk.StringVar(value='guardado' if indicators else 'nuevo')
        if indicators:
            ctk.CTkRadioButton(self,text='Descargar el instrumento guardado',variable=self.source,value='guardado',command=self._toggle).pack(anchor='w',padx=18,pady=6)
            ctk.CTkRadioButton(self,text='Crear una plantilla nueva para completar en Excel',variable=self.source,value='nuevo',command=self._toggle).pack(anchor='w',padx=18,pady=6)
        else:label(self,'Elija cuántos criterios necesita por capacidad. Escribirá sus indicadores y descriptores directamente en Excel.').pack(fill='x',padx=18,pady=6)
        self.body=scroll_area(self,auto_hide=True);self.body.pack(fill='both',expand=True,padx=14,pady=8)
        self.body.grid_columnconfigure(0,weight=1)
        self.help=label(self,'');self.help.pack(fill='x',padx=18,pady=4)
        for row,capacity in enumerate(activity['capacidades']):
            label(self.body,capacity['capacidad_nombre']).grid(row=row,column=0,sticky='ew',padx=8,pady=10)
            entry=ctk.CTkComboBox(self.body,values=[str(n) for n in range(1,11)],width=90,height=36)
            count=sum(i['capacidad_id']==capacity['capacidad_id'] for i in indicators)
            entry.set(str(count or 2));entry.grid(row=row,column=1,padx=8,pady=10)
            self.counts[capacity['capacidad_id']]=entry
        bar=ctk.CTkFrame(self,fg_color='transparent');bar.pack(fill='x',padx=18,pady=14)
        ctk.CTkButton(bar,text='Cancelar',height=36,command=self.destroy).pack(side='left')
        ctk.CTkButton(bar,text='Descargar Excel',height=36,command=self.confirm).pack(side='right')
        self._toggle();self.grab_set();self.ready=True

    def _toggle(self):
        new=self.source.get()=='nuevo'
        for entry in self.counts.values():entry.configure(state='normal' if new else 'disabled')
        self.help.configure(text='Cada criterio tendrá su propia respuesta y puntaje. La nota final de capacidad se calculará con todos sus criterios.' if new else 'Se conservan sus criterios, descriptores y puntajes actuales.')

    def confirm(self):
        try:
            counts={cap:int(entry.get()) for cap,entry in self.counts.items()}
            if any(not 1<=n<=20 for n in counts.values()):raise ValueError()
        except ValueError:messagebox.showwarning('Cantidad de criterios','Elija entre 1 y 20 criterios por capacidad.',parent=self);return
        self.result=dict(criterios_por_capacidad=counts,desde_cero=self.source.get()=='nuevo')
        self.destroy()
