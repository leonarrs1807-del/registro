"""Desktop management dialogs kept separate from the grade entry screens."""
import logging
from pathlib import Path
import shutil
import subprocess
import sys
import os
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import app_storage as storage
from db_safety import history, undo_grade


from mejoras_ui import ClassroomTools
from vista import ViewTools
from compact_ui import CompactTools
from evaluation_ui import EvaluationTools
from licencias_ui import LicenseTools


class DesktopTools(EvaluationTools,CompactTools,ViewTools,LicenseTools,ClassroomTools):
    def iniciar_herramientas(self):
        self.protocol('WM_DELETE_WINDOW', self.cerrar_aplicacion)
        self.bind('<KeyRelease>', self._registrar_edicion, add='+')
        self.bind('<ButtonRelease-1>', self._registrar_seleccion, add='+')
        menu = tk.Menu(self)
        datos = tk.Menu(menu, tearoff=False)
        datos.add_command(label='Crear respaldo', command=self.crear_respaldo)
        datos.add_command(label='Restaurar respaldo…', command=self.restaurar_respaldo)
        datos.add_command(label='Historial de notas…', command=self.mostrar_historial)
        datos.add_separator()
        datos.add_command(label='Año escolar y periodo…', command=self.seleccionar_periodo)
        datos.add_command(label='Ubicación de datos y errores', command=lambda: messagebox.showinfo(
            'Archivos de la aplicación', f'Datos: {self._db_path}\nRespaldos: {self._db_path.parent / "backups"}\nRegistro de errores: {storage.data_dir() / "registro.log"}'))
        menu.add_cascade(label='Datos', menu=datos)
        self.configure(menu=menu)
        self._planilla_pendiente = False
        self._formularios_pendientes = set()
        self._contexto_guardado = (self.combo_curso_global.get(), self.combo_grado_global.get(), self.combo_seccion_global.get())
        self.title(f'Registro Docente 1.6 · {"Comercial" if self._license_required else "Personal"} — {self._db_path.stem}')
        self.iniciar_mejoras(menu)
        self.barra_acciones()
        self.iniciar_licencia_ui(menu)
        self.fuentes_menu(menu)

    def destroy(self):
        if getattr(self,'_closing_ui',False):return
        self._closing_ui=True
        from widgets import prepare_destroy
        prepare_destroy(self)
        # Tk timers outlive deleted child widgets unless explicitly cancelled.
        # This matters when restarting windows and for clean shutdown in tests.
        for timer in self.tk.splitlist(self.tk.call('after', 'info')):
            # Cancel the Tcl timer, leaving command deletion to its owning widget.
            self.tk.call('after', 'cancel', timer)
        if hasattr(self, 'fig_actual'):
            self.fig_actual.clear()
        super().destroy()

    @property
    def _db_path(self):
        from db import DB_PATH
        return DB_PATH

    def report_callback_exception(self, exc_type, exc, traceback):
        # Do not log frame locals, cell contents or credentials.
        logging.getLogger('registro').error('Error de interfaz', exc_info=(exc_type, exc, traceback))
        messagebox.showerror('No se pudo completar la operación', f'{exc}\n\nSus cambios no confirmados permanecen en pantalla. Consulte registro.log para soporte.')

    def _registrar_edicion(self, event):
        if event.keysym in ('Tab', 'Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Escape', 'Return', 'Left', 'Right', 'Up', 'Down'):
            return
        widget = event.widget
        # Dialogs own their state. Search controls do not represent unsaved records.
        if widget.winfo_toplevel() != self:
            return
        while widget is not self:
            if widget is getattr(self, 'entry_buscar_est', None):
                return
            if widget is getattr(self, 'tab_calificar', None):
                self.marcar_planilla_pendiente()
                return
            if widget in (getattr(self, 'tab_crear', None), getattr(self, 'tab_estudiantes', None), getattr(self, 'tab_graficos', None)):
                self._formularios_pendientes.add(str(widget))
                return
            widget = getattr(widget, 'master', self)

    def _registrar_seleccion(self, event):
        import customtkinter as ctk
        widget = event.widget
        if widget.winfo_toplevel() != self:
            return
        while widget is not self:
            if isinstance(widget, (ctk.CTkCheckBox, ctk.CTkComboBox)):
                if widget not in (getattr(self, 'calif_combo_orden', None), getattr(self, 'calif_combo_modo_inst', None),
                                  getattr(self, 'calif_combo_actividad', None), getattr(self, 'est_combo_orden', None),
                                  getattr(self, 'filtro_cat_creacion', None)):
                    self._registrar_edicion(type('EditEvent', (), {'widget': widget, 'keysym': ''})())
                return
            widget = getattr(widget, 'master', self)

    def marcar_planilla_pendiente(self):
        self._planilla_pendiente = True
        if hasattr(self,'lbl_estado'):
            self.lbl_estado.configure(text='Cambios pendientes · Notas todavía sin confirmar')

    def confirmar_descartar(self,include_points=False):
        if include_points and hasattr(self,"puntos_panel") and not self.puntos_panel.confirm_change():return False
        tree = getattr(self, 'planilla_nativa', None)
        if tree and tree.winfo_exists() and getattr(tree, '_entry', None):
            tree._entry.event_generate('<FocusOut>')
        if not getattr(self, '_planilla_pendiente', False) and not getattr(self, '_formularios_pendientes', set()):
            return True
        if not messagebox.askyesno('Cambios sin guardar', 'Hay cambios sin guardar. ¿Desea descartarlos y continuar?', parent=self):
            return False
        self._planilla_pendiente = False
        self._formularios_pendientes.clear()
        self._borrador_path().unlink(missing_ok=True)
        return True

    def cerrar_aplicacion(self):
        if self.confirmar_descartar(include_points=True):
            self.destroy()

    def crear_respaldo(self):
        from datetime import datetime
        path=self.elegir_destino(title="Elija dónde guardar el respaldo",defaultextension='.db',initialfile=f'Respaldo_{datetime.now():%Y%m%d_%H%M}.db',filetypes=[('Base de Registro','*.db')])
        if path:
            if Path(path).resolve()==self._db_path.resolve():
                messagebox.showwarning("Respaldo","Elija un archivo diferente de la base de trabajo.");return
            source=storage.backup_database(self._db_path)
            storage.copy_database(source,path)
            storage.validate_database(path)
            self.archivo_guardado(path,'Respaldo verificado.')

    def _reiniciar(self, path):
        args = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, str(Path(__file__).with_name('main.py'))]
        env = {**os.environ, 'REGISTRO_DB_PATH': str(path)}
        subprocess.Popen(args, env=env)
        self.destroy()

    def restaurar_respaldo(self):
        if not self.verificar_permiso_edicion() or not self.confirmar_descartar(include_points=True):
            return
        path = filedialog.askopenfilename(title='Seleccionar respaldo', initialdir=self._db_path.parent / 'backups', filetypes=[('Base de datos', '*.db')])
        if not path:
            return
        storage.validate_database(path)
        if messagebox.askyesno('Restaurar', 'Se reemplazarán los datos del periodo actual. Primero se guardará un respaldo de seguridad. ¿Continuar?'):
            storage.restore_database(path, self._db_path)
            self._reiniciar(self._db_path)

    def mostrar_historial(self):
        window = tk.Toplevel(self)
        window.title('Historial de notas — últimos 500 cambios (hora UTC)')
        window.geometry('1100x520')
        columns = ('fecha', 'usuario', 'alumno', 'sesion_id', 'capacidad', 'anterior', 'nueva', 'operacion')
        tree = ttk.Treeview(window, columns=columns, show='headings')
        for col in columns:
            tree.heading(col, text=col.replace('_', ' ').capitalize())
            tree.column(col, width=125)
        scroll = ttk.Scrollbar(window, orient='vertical', command=tree.yview)
        scroll.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(fill='both', expand=True)
        def refresh():
            tree.delete(*tree.get_children())
            for item in history(self._db_path):
                tree.insert('', 'end', iid=str(item['id']), values=[item[c] if item[c] is not None else '—' for c in columns])
        def revert():
            if not self.verificar_permiso_edicion() or not tree.selection() or not self.confirmar_descartar():
                return
            if not messagebox.askyesno('Revertir nota', '¿Restaurar el valor anterior de este cambio?', parent=window):
                return
            try:
                storage.backup_database(self._db_path, 'antes-revertir')
                undo_grade(self._db_path, int(tree.selection()[0]))
                refresh()
                self.recargar_cursos_y_contexto()
            except ValueError as exc:
                messagebox.showerror('No se pudo revertir', str(exc), parent=window)
        ttk.Button(window, text='Revertir cambio seleccionado', command=revert).pack(pady=8)
        refresh()

    def seleccionar_periodo(self):
        if not self.confirmar_descartar(include_points=True):
            return
        window = tk.Toplevel(self)
        window.title('Años y periodos independientes')
        window.geometry('520x380')
        tk.Label(window, text='Cada periodo conserva sus propias actividades y notas.\nLos periodos nuevos copian el alumnado y currículo, sin notas.').pack(pady=10)
        paths = sorted(storage.data_dir().glob('*.db'))
        if self._db_path not in paths:
            paths.insert(0, self._db_path)
        listing = tk.Listbox(window)
        listing.pack(fill='both', expand=True, padx=10)
        for path in paths:
            listing.insert('end', path.stem)
        def open_period():
            if listing.curselection():
                path = paths[listing.curselection()[0]]
                if path.parent.resolve() == storage.data_dir().resolve():
                    storage.activate_period(path)
                self._reiniciar(path)
        def new_period():
            if not self.verificar_permiso_edicion():
                return
            year = simpledialog.askinteger('Año escolar', 'Año (2000–2100):', minvalue=2000, maxvalue=2100, parent=window)
            if year is None:
                return
            period = simpledialog.askinteger('Periodo', 'Periodo (1–4):', minvalue=1, maxvalue=4, parent=window)
            if period is None:
                return
            try:
                path = storage.create_period(self._db_path, year, period)
                storage.activate_period(path)
                self._reiniciar(path)
            except ValueError as exc:
                messagebox.showerror('Periodo', str(exc), parent=window)
        ttk.Button(window, text='Abrir seleccionado', command=open_period).pack(side='left', padx=15, pady=10)
        ttk.Button(window, text='Crear periodo sin notas', command=new_period).pack(side='right', padx=15, pady=10)

    def _importar_con_vista_previa(self, function, *args):
        """Run the real importer on a clone; display source rows before any live write."""
        import openpyxl
        if not self.confirmar_descartar():
            return None
        with tempfile.TemporaryDirectory() as temp:
            staged_db = Path(temp) / 'preview.db'
            storage.copy_database(self._db_path, staged_db)
            copied_args = list(args)
            # Instrument importer takes session_id before the filename.
            index = 1 if function.__name__ == 'importar_rubrica_o_cotejo_desde_excel' else 0
            workbook = Path(temp) / 'entrada.xlsx'
            shutil.copyfile(args[index], workbook)
            copied_args[index] = str(workbook)
            result = function(*copied_args, db_path=staged_db)
            if function.__name__ == 'importar_estudiantes_desde_excel':
                summary = f'Estudiantes que se agregarán: {result}.'
            elif function.__name__ == 'importar_matriz_notas_desde_excel':
                summary = f'Estudiantes procesados: {result[0]}. Notas que se cargarán: {result[1]}.'
            else:
                summary = f'Indicadores: {result[0]}. Estudiantes con calificaciones: {result[1]}.'
            window = tk.Toplevel(self)
            window.title('Vista previa de importación')
            width=min(1100,int(self.winfo_screenwidth()*.94));height=min(650,int(self.winfo_screenheight()*.85))
            window.geometry(f'{width}x{height}')
            window.transient(self)
            tk.Label(window, text=f'{summary}\nRevise las primeras 150 filas de cada hoja antes de confirmar.',
                     wraplength=width-40,justify='left').pack(fill='x',padx=15,pady=10)
            frame = ttk.Frame(window)
            frame.pack(fill='both', expand=True)
            tree = ttk.Treeview(frame, columns=('hoja', 'fila', 'contenido'), show='headings')
            for col, width in [('hoja', 140), ('fila', 60), ('contenido', 2000)]:
                tree.heading(col, text=col.capitalize())
                tree.column(col, width=width, stretch=False)
            sy = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
            sx = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
            tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
            tree.grid(row=0, column=0, sticky='nsew'); sy.grid(row=0, column=1, sticky='ns'); sx.grid(row=1, column=0, sticky='ew')
            frame.grid_rowconfigure(0, weight=1); frame.grid_columnconfigure(0, weight=1)
            wb = openpyxl.load_workbook(workbook, read_only=True, data_only=True)
            try:
                for sheet in wb:
                    if sheet.sheet_state!='visible':continue
                    for rownum, row in enumerate(sheet.iter_rows(max_row=150, values_only=True), 1):
                        tree.insert('', 'end', values=(sheet.title, rownum, ' | '.join('' if c is None else str(c) for c in row)))
            finally:
                wb.close()
            confirmed = []
            ttk.Button(window, text='Cancelar', command=window.destroy).pack(side='left', padx=15, pady=10)
            ttk.Button(window, text='Importar todos los datos validados', command=lambda: (confirmed.append(True), window.destroy())).pack(side='right', padx=15, pady=10)
            window.grab_set()
            self.wait_window(window)
            if not confirmed:
                return None
            storage.backup_database(self._db_path, 'antes-importar')
            return function(*copied_args, db_path=self._db_path)
