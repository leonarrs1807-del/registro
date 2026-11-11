"""Teacher workspace controls: reusable models, profiles and focused assessment."""
import tkinter as tk
from tkinter import messagebox,simpledialog
from datetime import datetime,timezone,timedelta
import customtkinter as ctk
from colores import button
from presentacion import MODES


class TeacherViewTools:
    def crear_biblioteca_docente(self):
        from biblioteca_ui import LibraryPanel
        self.tab_biblioteca=self.tabview.add('Biblioteca')
        self.biblioteca_panel=LibraryPanel(self.tab_biblioteca,self);self.biblioteca_panel.pack(fill='both',expand=True)

    def abrir_biblioteca(self):
        self.tabview.set('Biblioteca');self.biblioteca_panel.refresh()

    def guardar_modelo_biblioteca(self):
        session=getattr(self,'id_actividad_calificando',None)
        if not session:messagebox.showinfo('Biblioteca','Abre en Calificaciones la actividad que contiene el instrumento.');return
        import biblioteca
        try:model=biblioteca.from_session(session,self._db_path)
        except ValueError as exc:messagebox.showinfo('Biblioteca',str(exc));return
        name=simpledialog.askstring('Guardar en biblioteca','Nombre para reutilizar este modelo:',initialvalue=model['nombre'],parent=self)
        if not name or not name.strip():return
        model['nombre']=name.strip();identity=biblioteca.save_models([model],origin='Actividad · '+model['tema'])[0]
        self.biblioteca_panel.refresh(identity)
        self.lbl_estado.configure(text='Modelo guardado en tu biblioteca · Disponible en otros colegios y periodos')

    def abrir_ficha_estudiante(self,student=None):
        if self.obtener_curso_activo_id() is None:return
        if student is None:
            if self.tabview.get()=='Estudiantes':student=self.id_estudiante_sel
            else:
                tree=getattr(self,'planilla_nativa',None)
                if tree and tree.winfo_exists() and tree.selection():student=int(tree.item(tree.selection()[0],'values')[0])
        from ficha_ui import StudentProfile
        return StudentProfile(self,student)

    def cambiar_presentacion_notas(self,caption):
        self._grade_display=MODES[caption]
        if hasattr(self,'display_choice'):self.display_choice.set(caption)
        if hasattr(self,'config_grade_display'):self.config_grade_display.set(caption)
        from grade_cells import GradeTreeview
        def repaint(widget):
            if isinstance(widget,GradeTreeview):widget.queue_colors()
            for child in widget.winfo_children():repaint(child)
        repaint(self)
        matrix=getattr(getattr(self,'_embedded_evaluation',None),'matrix',None)
        if matrix and matrix.winfo_exists():matrix._detail()
        if hasattr(self,'lbl_estado'):
            state='Cambios pendientes' if self._planilla_pendiente else 'Edición activa' if self.edicion_desbloqueada else 'Edición bloqueada'
            self.lbl_estado.configure(text=state+' · Vista: '+caption)
        self._guardar_ventana()

    def cambiar_densidad_tablas(self,caption):
        from tkinter import ttk
        self._table_density=caption
        style=ttk.Style(self);size=abs(getattr(self,'_native_table_font_size',16))
        style.configure('Treeview',rowheight=max(28,size+(9 if caption=='Compacta' else 18)))
        self.cambiar_presentacion_notas(next(k for k,v in MODES.items() if v==self._grade_display))

    def alternar_evaluacion_ampliada(self,event=None):
        return self.set_evaluation_expanded(not getattr(self,'_evaluation_expanded',False))

    def set_evaluation_expanded(self,expanded):
        if bool(expanded)==getattr(self,'_evaluation_expanded',False):return
        self._evaluation_expanded=bool(expanded)
        if expanded:
            self.tabview.set('Ingresar Calificativos')
            self._evaluation_saved_menu=self.cget('menu');self._evaluation_saved_fullscreen=self.attributes('-fullscreen')
            self.configure(menu='');self.barra_top.grid_remove();self.tabview.sidebar.container.grid_remove()
            self.tabview.grid_configure(padx=0,pady=0)
            self._tools_open=False;self._disponer_herramientas()
            try:self.attributes('-fullscreen',True)
            except tk.TclError:pass
        else:
            self.configure(menu=getattr(self,'_evaluation_saved_menu',''))
            self.barra_top.grid();self.tabview.sidebar.container.grid();self.tabview.grid_configure(padx=12,pady=(0,10))
            try:self.attributes('-fullscreen',getattr(self,'_evaluation_saved_fullscreen',False))
            except tk.TclError:pass
        self._focus_button.configure(text='Volver · Esc' if expanded else 'Ampliar vista')
        return 'break'

    def salir_evaluacion_ampliada(self,event=None):
        if getattr(self,'_evaluation_expanded',False):self.set_evaluation_expanded(False);return 'break'

    def instalar_accesos_docentes(self):
        self.bind('<Escape>',self.salir_evaluacion_ampliada,add='+')
        self.bind('<Control-Shift-E>',self.alternar_evaluacion_ampliada,add='+')

    def indicar_hora_guardado(self):
        stamp=datetime.now(timezone(timedelta(hours=-5))).strftime('%H:%M')
        self.lbl_estado.configure(text=self.lbl_estado.cget('text')+' · Guardado '+stamp)
