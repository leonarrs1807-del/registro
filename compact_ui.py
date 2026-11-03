"""Compact teacher workspace: icon actions and details available on demand."""
import tkinter as tk
from tkinter import messagebox,simpledialog
import customtkinter as ctk
from ui_icons import icon
from widgets import Tooltip,SafeDialog
from interfaz import pixel_scale


class CompactTools:
    def estilizar_workspace(self):
        from main import TEMAS_INTERFAZ
        card=TEMAS_INTERFAZ[self.tema_actual_nombre]['bg_card']
        def visit(widget):
            if getattr(widget,'_preserve_theme',False):return
            if isinstance(widget,ctk.CTkFrame) and widget.cget('fg_color')!='transparent':
                widget.configure(fg_color=card)
            elif isinstance(widget,ctk.CTkComboBox):
                widget.configure(border_width=1,corner_radius=6,height=36,
                    font=ctk.CTkFont(size=15 if widget.master is self.barra_top else 14),
                    dropdown_font=ctk.CTkFont(size=14),
                    fg_color=('#ffffff','#1e293b'),border_color=('#cbd5e1','#475569'),
                    button_color=('#f1f5f9','#334155'),button_hover_color=('#e2e8f0','#475569'),
                    dropdown_fg_color=('#ffffff','#1e293b'))
            elif isinstance(widget,ctk.CTkEntry):
                widget.configure(border_width=1,corner_radius=6,border_color=('#cbd5e1','#475569'),height=36)
            elif isinstance(widget,ctk.CTkButton) and widget.cget('fg_color') in ('#3B8ED0','#3b8ed0','#1f6aa5','#2563eb','#1d4ed8'):
                from colores import button
                widget.configure(**button())
            elif isinstance(widget,ctk.CTkButton) and widget.cget('fg_color')=='transparent' and widget.cget('text'):
                widget.configure(text_color=('#334155','#e2e8f0'))
            for child in widget.winfo_children():visit(child)
        visit(self)
        self.fuentes_nativas()

    def crear_cabecera_compacta(self):
        self.barra_top=ctk.CTkFrame(self,corner_radius=8)
        self.barra_top.grid(row=0,column=0,sticky='ew',padx=10,pady=(8,6))
        self.barra_top.grid_columnconfigure(5,weight=1)
        def action(col,picture,hint,callback):
            button=ctk.CTkButton(self.barra_top,text='',image=icon(picture,master=self),width=32,height=32,
                fg_color='transparent',hover_color=('#e2e8f0','#334155'),corner_radius=6,command=callback)
            button.grid(row=0,column=col,padx=3,pady=6)
            Tooltip(button,hint)
            return button
        action(0,'menu','Mostrar u ocultar el menú · Ctrl+B',lambda:self.tabview.toggle())
        self.combo_nivel=ctk.CTkComboBox(self.barra_top,values=['Primaria','Secundaria'],state='readonly',
            width=126,height=36,command=self.cambiar_nivel)
        import db
        self.combo_nivel.set(db.obtener_docente_config().get('nivel_educativo','Secundaria'))
        self.combo_nivel.grid(row=0,column=1,padx=3,pady=6)
        Tooltip(self.combo_nivel,'Nivel educativo')
        self.combo_curso_global=ctk.CTkComboBox(self.barra_top,state='readonly',width=260,height=36,command=self._al_cambiar_curso_global)
        self.combo_curso_global.grid(row=0,column=2,padx=3,pady=6)
        Tooltip(self.combo_curso_global,lambda:'Curso: '+self.combo_curso_global.get())
        self.combo_grado_global=ctk.CTkComboBox(self.barra_top,values=['1°','2°','3°','4°','5°'],width=58,height=32,
            command=lambda _:self._al_cambiar_salon_global())
        self.combo_grado_global.set('4°');self.combo_grado_global.grid(row=0,column=3,padx=3,pady=6)
        Tooltip(self.combo_grado_global,'Grado')
        self.combo_seccion_global=ctk.CTkComboBox(self.barra_top,values=['A','B','C','D','E'],width=54,height=32,
            command=lambda _:self._al_cambiar_salon_global())
        self.combo_seccion_global.set('A');self.combo_seccion_global.grid(row=0,column=4,padx=3,pady=6)
        Tooltip(self.combo_seccion_global,'Sección')
        action(6,'save','Guardar documento .registro · Ctrl+S',self.guardar_documento)
        self.btn_candado=action(7,'lock',lambda:'Bloquear edición' if self.edicion_desbloqueada else 'Desbloquear edición',self.alternar_candado)
        self._header_more=action(8,'settings','Configuración',self.abrir_configuracion)
        self.lbl_docente_info=ctk.CTkLabel(self.barra_top,text='')  # Profile is shown in the menu.
        self.barra_top.bind('<Configure>',self._ajustar_cabecera,add='+')
        self.bind('<Control-b>',lambda e:self.tabview.toggle())
        self.bind('<Control-s>',lambda e:self.guardar_documento())
        self.bind('<F1>',lambda e:self.abrir_instrucciones())

    def _ajustar_cabecera(self,event=None):
        width=self.barra_top.winfo_width()/pixel_scale(self)
        narrow=width<680
        if narrow:self.combo_nivel.grid_remove()
        else:self.combo_nivel.grid()
        desired=max(140,min(300,width-(400 if narrow else 520)))
        if abs(self.combo_curso_global.cget('width')-desired)>3:self.combo_curso_global.configure(width=desired)

    def menu_cabecera(self):
        self.abrir_configuracion()

    def detalles_calificacion(self):
        if not self.id_actividad_calificando:return
        from instrument_design import InstrumentView
        return InstrumentView(self,self.id_actividad_calificando)

    def _texto_emergente(self,title,text,save=None):
        window=SafeDialog(self);window.title(title)
        scale=window._get_window_scaling()
        width=min(650,int(self.winfo_screenwidth()/scale*.9));height=min(500,int(self.winfo_screenheight()/scale*.8))
        window.geometry(f'{width}x{height}');window.transient(self)
        box=ctk.CTkTextbox(window,wrap='word',font=ctk.CTkFont(size=14))
        box.pack(fill='both',expand=True,padx=14,pady=14);box.insert('1.0',text)
        if save is None:box.configure(state='disabled')
        def finish():
            if save:save(box.get('1.0','end').strip())
            window.destroy()
        ctk.CTkButton(window,text='Guardar' if save else 'Cerrar',width=110,command=finish).pack(anchor='e',padx=14,pady=(0,14))
        window.grab_set()

    def editar_texto_actividad(self,widget,title):
        def save(value):
            widget.delete('1.0','end');widget.insert('1.0',value)
            self._formularios_pendientes.add(str(self.tab_crear))
        self._texto_emergente(title,widget.get('1.0','end').strip(),save)

    def menu_calificacion(self,button):
        menu=tk.Menu(self,tearoff=False)
        menu.add_command(label='Importar rúbrica o cotejo…',command=self.accion_importar_rubrica_cotejo_en_calificacion)
        menu.add_command(label='Marcar asistencia de todos',command=self.accion_marcar_asistencia_todos)
        menu.add_command(label='Cambiar peso…',command=self.cambiar_peso_calificacion)
        self.fuentes_menu(menu);menu.tk_popup(button.winfo_rootx(),button.winfo_rooty()+button.winfo_height())

    def cambiar_peso_calificacion(self):
        if not self.verificar_permiso_edicion() or not self.id_actividad_calificando:return
        value=simpledialog.askfloat('Peso','Peso de esta actividad:',initialvalue=float(self.calif_entry_peso.get() or 1),minvalue=.000001,maxvalue=1000000,parent=self)
        if value is not None:
            self.calif_entry_peso.delete(0,'end');self.calif_entry_peso.insert(0,f'{value:g}');self.marcar_planilla_pendiente()

    def evaluar_desde_barra(self):
        activity=getattr(self,'actividades_creadas_map',{}).get(self.id_actividad_calificando)
        if activity:
            if 'Cotejo' not in self.calif_combo_modo_inst.get() and 'Rúbrica' not in self.calif_combo_modo_inst.get():
                if not self.verificar_permiso_edicion():return
                tree=self.planilla_nativa
                if tree and tree.get_children() and activity['capacidades']:
                    item=tree.get_children()[0];tree.selection_set(item)
                    tree._start_entry_edit(item,'Cap 1',4,tree.item(item,'values')[4])
                return
            kind='Rúbrica' if 'Rúbrica' in self.calif_combo_modo_inst.get() else 'Lista de Cotejo'
            self.abrir_evaluacion_por_criterios()
