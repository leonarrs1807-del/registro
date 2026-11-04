"""Fast single-grade entry while preserving the existing per-capacity save/undo data."""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from grade_cells import GradeTreeview,grade_number
from interfaz import grade_panels,pixel_scale
from widgets import wrap_label,prepare_destroy
from colores import button
from db_safety import valid_number


class GlobalGradePanel(ctk.CTkFrame):
    def __init__(self,master,app):
        super().__init__(master,fg_color='transparent');self.app=app;self.editor=None;self.session=app.id_actividad_calificando
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(1,weight=1)
        bar=ctk.CTkFrame(self,fg_color='transparent');bar.grid(row=0,column=0,columnspan=3,sticky='ew',padx=8,pady=5);bar.grid_columnconfigure(0,weight=1)
        context=app.actividades_creadas_map[self.session]
        names=' · '.join(c['capacidad_nombre'] for c in context['capacidades'])
        info=ctk.CTkLabel(bar,text=f"Una nota por estudiante → {len(context['capacidades'])} capacidades seleccionadas",anchor='w',font=ctk.CTkFont(size=14,weight='bold'))
        info.grid(row=0,column=0,sticky='ew');wrap_label(info)
        from widgets import Tooltip
        Tooltip(info,names)
        ctk.CTkButton(bar,**button(),text='Deshacer',width=85,height=30,command=app.deshacer_planilla).grid(row=0,column=1,padx=4)
        ctk.CTkButton(bar,**button(),text='Rehacer',width=85,height=30,command=lambda:app.deshacer_planilla(True)).grid(row=0,column=2,padx=4)
        headers=('ID','Código','Apellidos y Nombres','Asistencia','Nota global','Comentario')
        self.table,self.identity,self.pane=grade_panels(self,headers,GradeTreeview,key='nombres_nota_global')
        self.pane.paneconfigure(self.identity.master,width=round(350*pixel_scale(self)))
        app.restaurar_divisor('nombres_nota_global')
        self.table.set_grade_columns(['Nota global']);self.table.on_double_click=self._double
        for col,caption,width in [('Asistencia','Asist.',85),('Nota global','Nota global / 20',170),('Comentario','Comentario',300)]:
            self.table.heading(col,text=caption);self.table.column(col,width=round(width*pixel_scale(self)),stretch=col=='Comentario')
        self.table.bind('<Double-1>',self._double)
        self.table.bind('<F2>',lambda e:self.edit())
        self.table.bind('<Return>',lambda e:self.edit())
        self.table.bind('<KeyPress>',self._typed,add='+')
        hint=ctk.CTkLabel(self,text='Enter: siguiente estudiante · F2 o doble clic: editar · Supr: pendiente · Ctrl+Z: deshacer',anchor='w',font=ctk.CTkFont(size=13))
        hint.grid(row=2,column=0,columnspan=3,sticky='ew',padx=8,pady=3);wrap_label(hint)
        self.refresh()

    def refresh(self):
        if self.editor is not None:return
        source=self.app.planilla_nativa;ids=source.get_children()
        if tuple(ids)!=self.table.get_children():
            for tree in (self.table,self.identity):
                for iid in tree.get_children():tree.delete(iid)
            for n,iid in enumerate(ids,1):
                row=source.item(iid,'values');self.identity.insert('','end',iid=iid,values=(f'{n:02}',row[2]));self.table.insert('','end',iid=iid,values=row[:4]+('',row[-1]))
        for iid in ids:
            row=source.item(iid,'values');notes=[grade_number(v) for v in row[4:-1]]
            value='' if all(n is None for n in notes) else str(notes[0]).removesuffix('.0') if len(set(notes))==1 else 'Diferentes'
            self.table.item(iid,values=(*row[:4],value,row[-1]))
        if ids and not self.table.selection():self.table.selection_set(ids[0]);self.table.focus(ids[0])

    def _double(self,event):
        iid=self.table.identify_row(event.y);col=self.table.identify_column(event.x)
        if not iid or not col:return 'break'
        column=self.table['displaycolumns'][int(col[1:])-1]
        self.table.selection_set(iid);self.table.focus(iid)
        if column=='Asistencia':self.stage(iid,column,'No (F)' if 'Sí' in self.table.set(iid,column) else 'Sí (V)')
        else:self.edit(iid,column)
        return 'break'

    def _typed(self,event):
        if event.state&4:return
        if event.keysym in ('Delete','BackSpace') and self.table.selection():self.stage(self.table.selection()[0],'Nota global','');return 'break'
        if event.char and event.char in '0123456789.,':return self.edit(initial=event.char)

    def edit(self,iid=None,column='Nota global',initial=None):
        if not self.app.verificar_permiso_edicion():return 'break'
        if self.editor is not None and not self.commit():return 'break'
        selected=self.table.selection();iid=iid or (selected[0] if selected else None)
        if iid is None or column not in ('Nota global','Comentario'):return 'break'
        self.table.see(iid);box=self.table.bbox(iid,column)
        if not box:return 'break'
        self.target=(iid,column);self.editor=tk.Entry(self.table,font=('Segoe UI',getattr(self.app,'_native_table_font_size',-16)),justify='center' if column=='Nota global' else 'left')
        self.table.editor=self.editor;x,y,w,h=box;self.editor.place(x=x,y=y,width=w,height=h)
        old=self.table.set(iid,column);self.original_value=old;old='' if old=='Diferentes' else old
        self.editor.insert(0,old if initial is None else initial);self.editor.focus_set()
        if initial is None:self.editor.select_range(0,'end')
        for key,move in [('Return',1),('Down',1),('Up',-1)]:self.editor.bind('<'+key+'>',lambda e,m=move:self._commit_move(m))
        self.editor.bind('<Escape>',lambda e:self.cancel());self.editor.bind('<Control-z>',lambda e:self.cancel())
        self.editor.bind('<FocusOut>',lambda e:self.commit());return 'break'

    def stage(self,iid,column,value):
        if not self.app.verificar_permiso_edicion():return False
        if column=='Nota global' and str(value).strip():value=str(valid_number(str(value).replace(',','.'))).removesuffix('.0')
        row=list(self.app.planilla_nativa.item(iid,'values'));self.app.recordar_planilla()
        if column=='Nota global':
            for col in range(4,len(row)-1):row[col]=value
        elif column=='Asistencia':row[3]=value
        else:row[-1]=value
        self.app.planilla_nativa.item(iid,values=row);self.app.marcar_planilla_pendiente();self.refresh();return True

    def commit(self):
        if self.editor is None:return True
        iid,column=self.target;value=self.editor.get()
        if column=='Nota global' and self.original_value=='Diferentes' and not value.strip():self.cancel();return True
        try:
            if column=='Nota global' and value.strip():valid_number(value.replace(',','.'))
        except ValueError as exc:
            self.app.lbl_estado.configure(text=str(exc));self.editor.focus_set();return False
        self.cancel();return self.stage(iid,column,value)

    def _commit_move(self,delta):
        iid,col=self.target
        if not self.commit():return 'break'
        rows=self.table.get_children();index=max(0,min(rows.index(iid)+delta,len(rows)-1));self.table.selection_set(rows[index]);self.table.focus(rows[index]);self.edit(rows[index],col);return 'break'

    def cancel(self):
        if self.editor is not None:
            editor=self.editor;self.editor=None;self.table.editor=None;editor.destroy()
        return 'break'

    def destroy(self):
        self.cancel();prepare_destroy(self);super().destroy()
