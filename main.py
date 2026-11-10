import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Dict, List, Optional, Tuple
import customtkinter as ctk
import logging
from pathlib import Path
import app_storage
from app_security import license_public_key, commercial_edition
from db_safety import valid_number
from desktop_ui import DesktopTools
from widgets import scroll_area, wrap_label, Tooltip, SafeDialog
from ui_icons import icon
from grade_cells import GradeTreeview
from instrumentos import normalized_grade
from rendimiento import TextBuffer,visible_when
from nombres_ui import activity_labels
from interfaz import PageBook, split, grade_panels, pixel_scale, scrollbar, flow_toolbar
from db import actualizar_pesos_actividades

from db import (
    actualizar_datos_estudiante,
    actualizar_peso_actividad,
    agregar_estudiante,
    calcular_matriz_competencias_y_capacidades,
    crear_capacidad,
    crear_competencia,
    crear_curso,
    crear_o_actualizar_sesion_clase,
    eliminar_estudiante,
    eliminar_sesion_clase,
    exportar_matriz_completa_excel,
    exportar_plantilla_rubrica_o_cotejo_excel,
    generar_plantilla_excel_estudiantes,
    guardar_calificaciones_y_asistencia_sesion,
    guardar_docente_config,
    guardar_indicadores_instrumento_sesion,
    guardar_nota_manual_capacidad,
    guardar_pesos_rubros_curso,
    guardar_tema_visual_preferido,
    guardar_tamano_letra_preferido,
    importar_estudiantes_desde_excel,
    importar_matriz_notas_desde_excel,
    importar_rubrica_o_cotejo_desde_excel,
    inicializar_db,
    nota_a_literal,
    obtener_capacidades_por_competencia,
    obtener_competencias_por_curso,
    obtener_cursos,
    obtener_docente_config,
    obtener_estadisticas_frecuencia_evaluacion,
    obtener_estado_planilla_sesion,
    obtener_estudiantes_filtrados,
    obtener_grados_y_secciones,
    obtener_indicadores_instrumento_sesion,
    obtener_pesos_rubros_curso,
    obtener_sesiones_clase,
    obtener_tabla_notas_por_cada_clase_sin_promediar,
    obtener_historial_vertical_estudiantes,
    verificar_credenciales_docente,
)

# Definición de las 3 Interfaces / Temas Visuales solicitados
TEMAS_INTERFAZ: Dict[str, Dict[str, str]] = {
    "Oscuro Noche": {
        "appearance": "Dark",
        "bg_main": "#0f172a",
        "bg_card": "#1e293b",
        "fg_text": "#f8fafc",
        "tree_bg": "#1e293b",
        "tree_fg": "#f8fafc",
        "tree_head_bg": "#0f172a",
        "tree_head_fg": "#e2e8f0",
        "tree_sel": "#2563eb",
        "accent": "#38bdf8",
    },
    "Gris Profesional": {
        "appearance": "Light",
        "bg_main": "#f4f6fa",
        "bg_card": "#ffffff",
        "fg_text": "#111827",
        "tree_bg": "#ffffff",
        "tree_fg": "#1f2937",
        "tree_head_bg": "#eaf0f7",
        "tree_head_fg": "#334155",
        "tree_sel": "#2563eb",
        "accent": "#2563eb",
    },
    "Claro Institucional": {
        "appearance": "Light",
        "bg_main": "#f0f9ff",
        "bg_card": "#ffffff",
        "fg_text": "#0f172a",
        "tree_bg": "#ffffff",
        "tree_fg": "#0f172a",
        "tree_head_bg": "#e0f2fe",
        "tree_head_fg": "#075985",
        "tree_sel": "#bae6fd",
        "accent": "#38bdf8",
    },
    "Esmeralda Docente": {
        "appearance": "Dark",
        "bg_main": "#042f2e",
        "bg_card": "#064e3b",
        "fg_text": "#ecfdf5",
        "tree_bg": "#064e3b",
        "tree_fg": "#ecfdf5",
        "tree_head_bg": "#022c22",
        "tree_head_fg": "#6ee7b7",
        "tree_sel": "#0d9488",
        "accent": "#34d399",
    },
}

PALETA_COLORES = [
    "#3b82f6",
    "#10b981",
    "#f59e0b",
    "#8b5cf6",
    "#ec4899",
    "#06b6d4",
    "#ef4444",
    "#84cc16",
]


class DialogoPerfilDocente(SafeDialog):
    def __init__(self, master: "VentanaPrincipal") -> None:
        super().__init__(master)
        self.app = master
        self.title("Datos Generales del Docente y Configuración del Candado")
        self.geometry("600x600")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        body=scroll_area(self)
        body.pack(fill="both",expand=True)
        self.after(100,lambda:self.app._fuentes_legibles(body))
        cfg = obtener_docente_config()

        ctk.CTkLabel(
            body,
            text="👤 Perfil del Docente y Usuario de Seguridad",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(padx=20, pady=(16, 4), anchor="w")

        ctk.CTkLabel(
            body,
            text="Configure sus datos generales y el usuario/contraseña para desbloquear el candado de edición:",
            font=ctk.CTkFont(size=11),
            text_color=("gray35", "gray75"),
            wraplength=420,
            justify="left",
        ).pack(padx=20, pady=(0, 10), anchor="w")

        ctk.CTkLabel(body, text="Nombres y Apellidos del Docente:", font=ctk.CTkFont(weight="bold")).pack(
            padx=20, pady=(2, 1), anchor="w"
        )
        self.ent_nombres = ctk.CTkEntry(body)
        self.ent_nombres.insert(0, cfg["nombres_docente"])
        self.ent_nombres.pack(padx=20, pady=(0, 8), fill="x")

        ctk.CTkLabel(body, text="Institución Educativa / Colegio:", font=ctk.CTkFont(weight="bold")).pack(
            padx=20, pady=(2, 1), anchor="w"
        )
        self.ent_institucion = ctk.CTkEntry(body)
        self.ent_institucion.insert(0, cfg["institucion"])
        self.ent_institucion.pack(padx=20, pady=(0, 8), fill="x")

        ctk.CTkLabel(body, text="Especialidad / Nivel:", font=ctk.CTkFont(weight="bold")).pack(
            padx=20, pady=(2, 1), anchor="w"
        )
        self.ent_esp = ctk.CTkEntry(body)
        self.ent_esp.insert(0, cfg["especialidad"])
        self.ent_esp.pack(padx=20, pady=(0, 8), fill="x")

        f_cred = ctk.CTkFrame(body, fg_color="transparent")
        f_cred.pack(padx=20, pady=4, fill="x")
        f_cred.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(f_cred, text="Usuario para Desbloquear:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.ent_usuario = ctk.CTkEntry(f_cred)
        self.ent_usuario.insert(0, cfg["usuario"])
        self.ent_usuario.grid(row=1, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkLabel(f_cred, text="Contraseña / PIN:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=1, sticky="w"
        )
        self.ent_clave = ctk.CTkEntry(f_cred, show="*")
        self.ent_clave.configure(placeholder_text="Nueva clave (vacío: conservar)")
        self.ent_clave.grid(row=1, column=1, padx=(6, 0), sticky="ew")

        ctk.CTkButton(
            body,
            text="💾 Guardar Datos del Docente y Desbloquear Candado",
            height=38,
            fg_color="#15803d",
            hover_color="#166534",
            font=ctk.CTkFont(weight="bold"),
            command=self._guardar,
        ).pack(padx=20, pady=(18, 12), fill="x")

    def _guardar(self) -> None:
        nom = self.ent_nombres.get().strip() or "Docente"
        inst = self.ent_institucion.get().strip() or "I.E."
        esp = self.ent_esp.get().strip() or "Secundaria"
        usr = self.ent_usuario.get().strip() or "docente"
        clv = self.ent_clave.get()
        try:
            guardar_docente_config(nom, inst, esp, usr, clv)
            if self.app.licensing and self.app.licensing.state:
                self.app.licensing.update_profile(nom,usr,clv)
        except ValueError as exc:
            messagebox.showwarning("Contraseña", str(exc), parent=self)
            return
        self.app.edicion_desbloqueada = True
        self.app.actualizar_visual_candado_y_docente()
        messagebox.showinfo("Perfil Guardado", f"Datos actualizados.\nUsuario activo: {usr}")
        self.destroy()


class DialogoDesbloquearCandado(SafeDialog):
    def __init__(self, master: "VentanaPrincipal") -> None:
        super().__init__(master)
        self.app = master
        self.title("🔓 Desbloquear Edición")
        self.geometry("460x360")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        cfg = obtener_docente_config()

        ctk.CTkLabel(
            self,
            text="🔒 Modo Protegido contra Borrado Accidental",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=20, pady=(16, 4), anchor="w")

        ctk.CTkLabel(
            self,
            text=f"Ingrese su usuario ({cfg['usuario']}) y contraseña para habilitar la edición y borrado:",
            font=ctk.CTkFont(size=11),
            text_color=("gray35", "gray75"),
            wraplength=340,
            justify="left",
        ).pack(padx=20, pady=(0, 10), anchor="w")

        ctk.CTkLabel(self, text="Usuario:").pack(padx=20, anchor="w")
        self.ent_usr = ctk.CTkEntry(self)
        self.ent_usr.insert(0, self.app.credenciales_actuales())
        self.ent_usr.pack(padx=20, pady=(0, 8), fill="x")

        ctk.CTkLabel(self, text="Contraseña / PIN:").pack(padx=20, anchor="w")
        self.ent_clv = ctk.CTkEntry(self, show="*")
        self.ent_clv.pack(padx=20, pady=(0, 12), fill="x")
        self.ent_clv.focus_set()
        self.ent_clv.bind("<Return>", lambda _e: self._intentar_desbloqueo())

        ctk.CTkButton(
            self,
            text="🔓 Desbloquear Candado",
            fg_color="#15803d",
            font=ctk.CTkFont(weight="bold"),
            command=self._intentar_desbloqueo,
        ).pack(padx=20, fill="x")

    def _intentar_desbloqueo(self) -> None:
        if self.app.autenticar(self.ent_usr.get(), self.ent_clv.get()):
            self.destroy()
            if obtener_docente_config().get("requiere_cambio_clave"):
                DialogoPerfilDocente(self.app)
            else:
                self.app.edicion_desbloqueada = True
                self.app.actualizar_visual_candado_y_docente()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.")


from instrument_design import InstrumentEditor as DialogoEditarInstrumento
from instrument_evaluate import InstrumentEvaluator as DialogoEvaluarInstrumentoMasivo


class PlanillaNativaTreeview(GradeTreeview):
    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.bind("<Double-1>", self.on_double_click)
        self._entry = None
        self.on_edit_complete = None
        self.bind("<Up>", self._move_up)
        self.bind("<Down>", self._move_down)

    def _move_up(self, event):
        focus = self.focus()
        if focus:
            prev_item = self.prev(focus)
            if prev_item:
                self.selection_set(prev_item)
                self.focus(prev_item)
        return "break"

    def _move_down(self, event):
        focus = self.focus()
        if focus:
            next_item = self.next(focus)
            if next_item:
                self.selection_set(next_item)
                self.focus(next_item)
        return "break"

    def on_double_click(self, event: tk.Event) -> None:
        if not self.winfo_toplevel().verificar_permiso_edicion():
            return
        item = self.identify_row(event.y)
        column = self.identify_column(event.x)
        if not item or not column:
            return

        col_index = list(self["columns"]).index(self.column(column, "id"))
        # 0: Codigo, 1: Alumno, 2: Asistencia, 3+: Notas, Last: Comentario
        
        cols = self["columns"]
        col_name = cols[col_index]

        if col_index < 3:
            return

        value = self.item(item, 'values')[col_index]

        if col_name == "Asistencia":
            new_val = "No (F)" if "S" in value or "V" in value else "Sí (V)"
            self._update_value(item, col_index, new_val)
            return

        if col_name == "Comentario":
            self._open_text_popup(item, col_index, value)
            return

        # It's a note cell
        self._start_entry_edit(item, column, col_index, value)

    def _update_value(self, item: str, col_index: int, new_val: str) -> None:
        self.winfo_toplevel().recordar_planilla()
        vals = list(self.item(item, 'values'))
        vals[col_index] = new_val
        self.item(item, values=vals)
        if self.on_edit_complete:
            self.on_edit_complete()

    def _start_entry_edit(self, item: str, column: str, col_index: int, value: str) -> None:
        app=self.winfo_toplevel()
        if getattr(app,'calif_combo_modo_inst',None) and app.calif_combo_modo_inst.get()!='Nota directa':
            if str(self['columns'][col_index]).startswith('Cap '):
                student=int(self.item(item,'values')[0])
                cap=app._capacidades_actividad[col_index-4]['capacidad_id']
                app.abrir_evaluacion_por_criterios(student,cap)
                return
        self.see(item)
        bounds=self.bbox(item,column)
        if not bounds:
            columns=list(self["displaycolumns"])
            name=self.column(column,"id") if str(column).startswith("#") else column
            if name in columns:
                widths=[self.column(c,"width") for c in columns]
                self.xview_moveto(sum(widths[:columns.index(name)])/max(sum(widths),1))
                self.update_idletasks();bounds=self.bbox(item,column)
        if not bounds:return
        x,y,width,height=bounds
        if self._entry:
            self._entry.destroy()

        self._entry = tk.Entry(self, justify="center", font=ttk.Style(self).lookup("Treeview","font") or ("Segoe UI",16))
        self._entry.place(x=x, y=y, width=width, height=height)
        if value and not any(c.isdigit() for c in value):
             self._entry.insert(0, "") 
        else:
             self._entry.insert(0, value.split()[0] if value else "")
             
        self._entry.focus_set()
        self._entry.selection_range(0, tk.END)

        def save_edit(e: tk.Event = None) -> None:
            if self._entry is None:
                return
            new_val = self._entry.get().strip()
            if new_val:
                try:
                    num = valid_number(new_val.replace(",", "."))
                    new_val = f"{str(num).removesuffix('.0')} ({nota_a_literal(num)})"
                except ValueError:
                    messagebox.showwarning("Nota inválida", "Ingrese una nota entre 0 y 20.")
                    return False
            self._update_value(item, col_index, new_val)
            editor, self._entry = self._entry, None
            editor.destroy()
            return True

        def cancel_edit(e: tk.Event = None) -> None:
            if self._entry is not None:
                editor, self._entry = self._entry, None
                editor.destroy()

        self._entry.bind("<Return>", save_edit)
        self._entry.bind("<FocusOut>", save_edit)
        self._entry.bind("<Escape>", cancel_edit)
        
        # Add arrow up/down inside entry to save and move
        def move_up(e):
            if not save_edit():
                return "break"
            prev_item = self.prev(item)
            if prev_item:
                self.selection_set(prev_item)
                self.focus(prev_item)
                self._start_entry_edit(prev_item, column, col_index, self.item(prev_item, 'values')[col_index])
            return "break"
            
        def move_down(e):
            if not save_edit():
                return "break"
            next_item = self.next(item)
            if next_item:
                self.selection_set(next_item)
                self.focus(next_item)
                self._start_entry_edit(next_item, column, col_index, self.item(next_item, 'values')[col_index])
            return "break"
            
        def move_left(e):
            if self._entry and self._entry.index(tk.INSERT) != 0 and e.keysym == "Left": return
            if not save_edit():
                return "break"
            cols = self["columns"]
            if col_index > 4: # Can move left up to Cap 1 (index 4)
                new_col_index = col_index - 1
                new_col = self["columns"][new_col_index]
                self._start_entry_edit(item, new_col, new_col_index, self.item(item, 'values')[new_col_index])
            return "break"

        def move_right(e):
            if self._entry and self._entry.index(tk.INSERT) != len(self._entry.get()) and e.keysym == "Right": return
            if not save_edit():
                return "break"
            cols = self["columns"]
            if col_index < len(cols) - 2: # Last is Comentario, don't move into it with right arrow
                new_col_index = col_index + 1
                new_col = self["columns"][new_col_index]
                self._start_entry_edit(item, new_col, new_col_index, self.item(item, 'values')[new_col_index])
            return "break"

        self._entry.bind("<Up>", move_up)
        self._entry.bind("<Down>", move_down)
        self._entry.bind("<Return>", move_down)
        self._entry.bind("<Tab>", move_right)
        self._entry.bind("<Shift-Tab>", move_left)
        self._entry.bind("<Right>", move_right)
        self._entry.bind("<Left>", move_left)

    def _open_text_popup(self, item: str, col_index: int, current_text: str) -> None:
        top = SafeDialog(self)
        top.title("Editar Comentario")
        top.geometry("500x350")
        top.transient(self.winfo_toplevel())
        top.grab_set()

        lbl = ctk.CTkLabel(top, text="Retroalimentación / Comentario del Estudiante:", font=ctk.CTkFont(weight="bold"))
        lbl.pack(padx=20, pady=(20, 5), anchor="w")

        txt = ctk.CTkTextbox(top, width=460, height=200, wrap="word")
        txt.pack(padx=20, pady=5)
        
        if "Click para editar" not in current_text and current_text != "-":
             txt.insert("1.0", current_text)

        def save_text() -> None:
            new_val = txt.get("1.0", "end-1c").strip()
            self._update_value(item, col_index, new_val)
            top.destroy()

        original_text = txt.get("1.0", "end-1c")
        def close_text():
            if txt.get("1.0", "end-1c") == original_text or messagebox.askyesno("Comentario sin guardar", "¿Descartar los cambios del comentario?", parent=top):
                top.destroy()
        top.protocol("WM_DELETE_WINDOW", close_text)
        btn_guardar = ctk.CTkButton(top, text="Pasar comentario a planilla", command=save_text)
        btn_guardar.pack(pady=10)


class PlanillaScrollXY(ctk.CTkFrame):
    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, bg="#0f172a", highlightthickness=0)
        self.scroll_y = scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_x = scrollbar(self, orient="horizontal", command=self.canvas.xview)

        self.interior = ctk.CTkFrame(self.canvas, fg_color="#0f172a", corner_radius=0)
        self.interior_id = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scroll_y.grid(row=0, column=1, sticky="ns")
        self.scroll_x.grid(row=1, column=0, sticky="ew")

        self.interior.bind("<Configure>", self._actualizar_region_scroll)
        self.canvas.bind("<Enter>", self._vincular_rueda_raton)
        self.canvas.bind("<Leave>", self._desvincular_rueda_raton)

    def aplicar_color_fondo(self, color_hex: str) -> None:
        self.canvas.configure(bg=color_hex)
        self.interior.configure(fg_color=color_hex)

    def _actualizar_region_scroll(self, _event: Optional[tk.Event] = None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _vincular_rueda_raton(self, _event: tk.Event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._al_girar_rueda)
        self.canvas.bind_all("<Shift-MouseWheel>", self._al_girar_rueda_horizontal)

    def _desvincular_rueda_raton(self, _event: tk.Event) -> None:
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Shift-MouseWheel>")

    def _al_girar_rueda(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _al_girar_rueda_horizontal(self, event: tk.Event) -> None:
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")


class VentanaPrincipal(DesktopTools, ctk.CTk):
    def __init__(self, licensing=None, license_required=False, license_error="") -> None:
        super().__init__()
        from rendimiento import preparar_graficos
        self._graphics_loader=preparar_graficos()
        self.licensing=licensing
        self._license_required=license_required
        self._license_error=license_error
        if licensing and licensing.state:self.sincronizar_cuenta()

        self.title("Sistema Docente de Evaluación por Competencias, Capacidades y Rúbricas (Secundaria)")
        self.ajustar_pantalla(reset=True)
        self.dev_mode = False

        self.edicion_desbloqueada: bool = False
        cfg_ini = obtener_docente_config()
        self.tema_actual_nombre: str = cfg_ini.get("tema_visual", "Oscuro Noche")
        self.tamano_letra_actual: str = cfg_ini.get("tamano_letra", "Personalizado (18)")
        if self.tema_actual_nombre not in TEMAS_INTERFAZ:
            self.tema_actual_nombre = "Oscuro Noche"

        self.cursos_map: Dict[str, int] = {}
        self.competencias_curso_actual: List[Tuple[int, str]] = []
        self.id_estudiante_sel: Optional[int] = None
        self.id_actividad_editando: Optional[int] = None
        self.id_actividad_calificando: Optional[int] = None

        self.widgets_caps_creacion: List[Dict[str, Any]] = []
        self.widgets_planilla_calificacion: List[Dict[str, Any]] = []
        self.entries_pesos_individuales_cat: List[Tuple[int, ctk.CTkEntry]] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self.iniciar_cubierta_arranque()
        self._construir_barra_contexto()
        self._construir_pestanas()

        self.actualizar_visual_candado_y_docente()
        self.recargar_cursos_y_contexto()
        self.iniciar_herramientas()
        self.iniciar_contexto_academico()
        self._startup_cover.destroy()

    # ==========================================================================
    # GESTIÓN DE LAS 3 INTERFACES / TEMAS VISUALES
    # ==========================================================================

    def cambiar_tamano_letra(self, tamano: str) -> None:
        self.tamano_letra_actual = tamano
        guardar_tamano_letra_preferido(tamano)
        self.cambiar_interfaz_visual(self.tema_actual_nombre)
        self.dibujar_planilla_calificacion()
        if self.planilla_nativa:self.planilla_nativa.queue_colors()

    def cambiar_interfaz_visual(self, nombre_tema: str) -> None:
        if nombre_tema not in TEMAS_INTERFAZ:
            return
        self.tema_actual_nombre = nombre_tema
        guardar_tema_visual_preferido(nombre_tema)
        cfg_t = TEMAS_INTERFAZ[nombre_tema]

        ctk.set_appearance_mode(cfg_t["appearance"])
        self.configure(fg_color=cfg_t["bg_main"])
        if hasattr(self,"tabview"):self.estilizar_workspace()
        if hasattr(self,"tabview"):
            self.tabview.content.configure(fg_color=cfg_t["bg_main"])
        for area in getattr(self,"_scroll_areas",[]):
            if area.winfo_exists():
                area.configure(fg_color=cfg_t["bg_card"])
                area.viewport.configure(bg=cfg_t["bg_card"])
                area.container.configure(fg_color=cfg_t["bg_card"])

        estilo = ttk.Style()
        estilo.theme_use("clam")
        
        f_size = {"Normal (12)": 12, "Grande (15)": 15, "Muy Grande (18)": 18}.get(self.tamano_letra_actual, 12)
        import re
        match = re.search(r"\((\d+)\)", self.tamano_letra_actual)
        f_size = max(16, int(match.group(1)) if match else 18)
        f_size = round(f_size * getattr(self, "_zoom", 1))
        import tkinter.font as tkfont
        native_size=-round(f_size*self._get_window_scaling())
        self._native_table_font_size=native_size
        table_font=tkfont.Font(root=self,family="Segoe UI",size=native_size)
        r_height=table_font.metrics("linespace")+round(8*self._get_window_scaling())
                
        estilo.configure(
            "Treeview",
            background=cfg_t["tree_bg"],
            foreground=cfg_t["tree_fg"],
            fieldbackground=cfg_t["tree_bg"],
            rowheight=r_height,
            font=("Segoe UI", native_size),
            borderwidth=1,
        )
        estilo.configure(
            "Treeview.Heading",
            background=cfg_t["tree_head_bg"],
            foreground=cfg_t["tree_head_fg"],
            font=("Segoe UI", -round((f_size-1)*self._get_window_scaling()), "bold"),
            relief="raised",
        )
        estilo.map(
            "Treeview",
            background=[("selected", cfg_t["tree_sel"])],
            foreground=[("selected", "#075985" if nombre_tema=="Claro Institucional" else "#ffffff")],
        )
        # Configure alternating row colors for subtle grid
        stripe_color = "#334155" if "Oscuro" in nombre_tema else "#f3f4f6"
        estilo.configure("Treeview", rowheight=r_height, font=("Segoe UI", native_size))
        estilo.map("Treeview", background=[("selected", cfg_t["tree_sel"])])
        self.stripe_color = stripe_color
        self.actualizar_lista_practicas()
        
        # Actualizar colores de las filas intercaladas en todas las tablas
        if hasattr(self, 'planilla_nativa') and self.planilla_nativa:
            self.planilla_nativa.tag_configure("odd", background=stripe_color)
        if hasattr(self, 'tree_buscador_alumnos') and self.tree_buscador_alumnos:
            self.tree_buscador_alumnos.tag_configure("odd", background=stripe_color)
        if hasattr(self, 'tree_matriz') and self.tree_matriz:
            self.tree_matriz.tag_configure("odd", background=stripe_color)


        if hasattr(self, "planilla_xy"):
            self.planilla_xy.aplicar_color_fondo(cfg_t["bg_main"])
        if hasattr(self, "graficos_tabs"):
            self.dibujar_graficos_estadisticos()

    def editar_perfil_docente(self):
        if self.verificar_permiso_edicion():
            DialogoPerfilDocente(self)

    def verificar_permiso_edicion(self, curso=None) -> bool:
        if not self.licencia_permite(curso):return False
        if hasattr(self, "lbl_estado") and self.periodo_cerrado():
            messagebox.showinfo("Periodo cerrado", "Reabra el periodo desde Trabajo docente para modificar los datos.")
            return False
        if self.edicion_desbloqueada:
            return True
        dialog = DialogoDesbloquearCandado(self)
        self.wait_window(dialog)
        return self.edicion_desbloqueada

    def alternar_candado(self) -> None:
        if self.edicion_desbloqueada:
            self.edicion_desbloqueada = False
            self.actualizar_visual_candado_y_docente()

        else:
            DialogoDesbloquearCandado(self)
            
    def activar_dev_mode(self) -> None:
        if self.dev_mode:
            self.dev_mode = False
            self.btn_toggle_curso.grid_remove()
            self.btn_eliminar_curso.grid_remove()
            messagebox.showinfo("Cursos", "Administración de cursos desactivada.")
            self.recargar_cursos_y_contexto()
            return
            
        import tkinter.simpledialog as simpledialog
        pwd = simpledialog.askstring("Administrar cursos", "Ingrese su contraseña docente para administrar cursos:", show="*")
        if pwd and self.autenticar(self.credenciales_actuales(), pwd) and self.licencia_permite():
            self.dev_mode = True
            self.btn_toggle_curso.grid()
            self.btn_eliminar_curso.grid()
            messagebox.showinfo("Cursos", "Administración de cursos habilitada.")
            self.recargar_cursos_y_contexto()
        else:
            messagebox.showerror("Error", "Clave incorrecta.")

    def actualizar_visual_candado_y_docente(self) -> None:
        cfg = obtener_docente_config()
        self.lbl_docente_info.configure(text=f"👤 {cfg['nombres_docente']}")
        if hasattr(self,'actualizar_configuracion'):self.actualizar_configuracion()
        self.btn_candado.configure(text="",image=icon("unlock" if self.edicion_desbloqueada else "lock",master=self),
            fg_color=("#dcfce7","#14532d") if self.edicion_desbloqueada else "transparent")
        if hasattr(self,"lbl_estado"):
            self.lbl_estado.configure(text="Edición activa" if self.edicion_desbloqueada else "Edición bloqueada")

    # ==========================================================================
    # BARRA SUPERIOR GLOBAL CON SELECTOR DE 3 INTERFACES + CANDADO + CURSO/SECCIÓN
    # ==========================================================================

    def _construir_barra_contexto(self) -> None:
        self.crear_cabecera_compacta()

    # ==========================================================================
    # CONSTRUCCIÓN DE LAS PESTAÑAS
    # ==========================================================================

    def _construir_pestanas(self) -> None:
        self.tabview = PageBook(self, corner_radius=12)
        self.tabview.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="nsew")

        self.tab_curriculo = self.tabview.add("Config. Cursos")
        self.tab_estudiantes = self.tabview.add("Estudiantes")
        self.tab_crear = self.tabview.add("Crear Actividad")
        self.tab_calificar = self.tabview.add("Ingresar Calificativos")
        self.tab_buscador = self.tabview.add("Buscador")
        self.tab_graficos = self.tabview.add("Porcentajes de Actividades",label="Pesos del promedio")
        self.tab_matriz = self.tabview.add("Matriz General")
        self.tab_estadisticas = self.tabview.add("Estadísticas")

        self.tab_configuracion=self.tab_curriculo
        self.tab_curriculo=self.crear_configuracion(self.tab_configuracion)
        self.avance_arranque("Cursos y competencias",0.1)
        self._construir_tab_curriculo()
        self.avance_arranque("Estudiantes",0.2)
        self._construir_tab_estudiantes()
        self.avance_arranque("Actividades y unidades",0.3)
        self._construir_tab_crear_actividad()
        self.avance_arranque("Ingreso de calificaciones",0.4)
        self._construir_tab_calificar_actividad()
        self.avance_arranque("Búsqueda",0.5)
        self._construir_tab_buscador_alumnos()
        self.avance_arranque("Ponderaciones",0.6)
        self._construir_tab_pesos_y_graficos()
        self.avance_arranque("Registro final",0.7)
        self._construir_tab_matriz_capacidades()
        self.avance_arranque("Estadísticas",0.8)
        self._construir_tab_estadisticas()
        from puntos_ui import PointsPanel
        from instrucciones import Tutorial
        self.tab_puntos=self.tabview.add("Prácticas y puntos")
        self.puntos_panel=PointsPanel(self.tab_puntos,self)
        self.puntos_panel.pack(fill="both",expand=True)
        self.tab_instrucciones=self.tabview.add("Instrucciones")
        self.tutorial=Tutorial(self.tab_instrucciones);self.tutorial.pack(fill="both",expand=True)

    # --------------------------------------------------------------------------
    # PESTAÑA 1: CURSOS, COMPETENCIAS Y CAPACIDADES
    # --------------------------------------------------------------------------
    def _construir_tab_curriculo(self) -> None:
        self.tab_curriculo.grid_columnconfigure((0, 1, 2), weight=1)
        self.tab_curriculo.grid_rowconfigure(2, weight=1)

        # --- NUEVO: BARRA DE CONFIGURACIÓN GLOBAL ---
        ctk.CTkLabel(self.tab_curriculo,text="Cursos y capacidades",font=ctk.CTkFont(size=18,weight="bold")).grid(row=0,column=0,columnspan=3,sticky="w",padx=12,pady=10)
        f_cur = ctk.CTkFrame(self.tab_curriculo, corner_radius=10)
        f_cur.grid(row=2, column=0, padx=(8, 5), pady=6, sticky="nsew")
        f_cur.grid_rowconfigure(1, weight=1)
        f_cur.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f_cur, text="Áreas", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=8, sticky="w"
        )
        self.tree_cursos = ttk.Treeview(f_cur, columns=("ID", "Curso"), show="headings", selectmode="browse", displaycolumns=("Curso",))
        self.tree_cursos.heading("ID", text="ID")
        self.tree_cursos.heading("Curso", text="Curso / Área Curricular")
        self.tree_cursos.column("ID", width=45, anchor="center")
        self.tree_cursos.column("Curso", width=250, anchor="w")
        self.tree_cursos.grid(row=1, column=0, padx=10, pady=4, sticky="nsew")
        self.tree_cursos.bind("<<TreeviewSelect>>", self._al_seleccionar_tree_curso)
        ctk.CTkButton(f_cur, text="+ Agregar Nuevo Curso", height=32, command=self._dialogo_nuevo_curso).grid(
            row=2, column=0, padx=10, pady=(8,4), sticky="ew"
        )
        self.btn_toggle_curso = ctk.CTkButton(f_cur, text="Activar / desactivar", height=32, command=self._toggle_curso_activo, fg_color="#b91c1c", hover_color="#991b1b")
        self.btn_toggle_curso.grid(row=3, column=0, padx=10, pady=2, sticky="ew")
        self.btn_toggle_curso.grid_remove()
        
        self.btn_eliminar_curso = ctk.CTkButton(f_cur, text="Eliminar curso", height=32, command=self._eliminar_curso, fg_color="#ef4444", hover_color="#dc2626")
        self.btn_eliminar_curso.grid(row=4, column=0, padx=10, pady=(2,8), sticky="ew")
        self.btn_eliminar_curso.grid_remove()

        f_comp = ctk.CTkFrame(self.tab_curriculo, corner_radius=10)
        f_comp.grid(row=2, column=1, padx=5, pady=6, sticky="nsew")
        f_comp.grid_rowconfigure(1, weight=1)
        f_comp.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f_comp, text="Competencias", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=8, sticky="w"
        )
        self.tree_competencias = ttk.Treeview(
            f_comp, columns=("ID", "Competencia"), show="headings", selectmode="browse", displaycolumns=("Competencia",)
        )
        self.tree_competencias.heading("ID", text="N°")
        self.tree_competencias.heading("Competencia", text="Competencia")
        self.tree_competencias.column("ID", width=40, anchor="center")
        self.tree_competencias.column("Competencia", width=310, anchor="w")
        self.tree_competencias.grid(row=1, column=0, padx=10, pady=4, sticky="nsew")
        self.tree_competencias.bind("<<TreeviewSelect>>", self._al_seleccionar_tree_competencia)
        ctk.CTkButton(
            f_comp, text="+ Agregar Competencia", height=32, fg_color="#0f766e", command=self._dialogo_nueva_competencia
        ).grid(row=2, column=0, padx=10, pady=8, sticky="ew")

        f_cap = ctk.CTkFrame(self.tab_curriculo, corner_radius=10)
        f_cap.grid(row=2, column=2, padx=(5, 8), pady=6, sticky="nsew")
        f_cap.grid_rowconfigure(1, weight=1)
        f_cap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f_cap, text="Capacidades", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=8, sticky="w"
        )
        self.tree_capacidades = ttk.Treeview(f_cap, columns=("ID", "Capacidad"), show="headings", selectmode="browse", displaycolumns=("Capacidad",))
        self.tree_capacidades.heading("ID", text="N°")
        self.tree_capacidades.heading("Capacidad", text="Capacidad")
        self.tree_capacidades.column("ID", width=40, anchor="center")
        self.tree_capacidades.column("Capacidad", width=330, anchor="w")
        self.tree_capacidades.grid(row=1, column=0, padx=10, pady=4, sticky="nsew")
        ctk.CTkButton(
            f_cap, text="+ Agregar Capacidad", height=32, fg_color="#4338ca", command=self._dialogo_nueva_capacidad
        ).grid(row=2, column=0, padx=10, pady=8, sticky="ew")

    # --------------------------------------------------------------------------
    # PESTAÑA 2: ESTUDIANTES (4A01 / EXCEL)
    # --------------------------------------------------------------------------
    def _construir_tab_estudiantes(self) -> None:
        self.tab_estudiantes.grid_columnconfigure(0, weight=0)
        self.tab_estudiantes.grid_columnconfigure(1, weight=1)
        self.tab_estudiantes.grid_rowconfigure(0, weight=1)

        pane=split(self.tab_estudiantes,"formulario_alumnos")
        pane.grid(row=0,column=0,columnspan=2,sticky="nsew",padx=6,pady=6)
        panel_izq = ctk.CTkFrame(pane, width=360, corner_radius=10)
        pane.add(panel_izq,width=round(300*pixel_scale(self)),minsize=round(240*pixel_scale(self)),stretch="never")

        ctk.CTkLabel(
            panel_izq, text="Estudiantes", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(padx=14, pady=(12, 2), anchor="w")
        ctk.CTkLabel(
            panel_izq,
            text="El código se asigna automáticamente. Identifica a cada estudiante en sus reportes.",
            font=ctk.CTkFont(size=11),
            justify="left",
        ).pack(padx=14, pady=(0, 8), fill="x", anchor="w")

        ctk.CTkButton(
            panel_izq,
            text="Importar estudiantes",
            height=36,
            fg_color="#15803d",
            hover_color="#166534",
            font=ctk.CTkFont(weight="bold"),
            command=self.accion_importar_excel_estudiantes,
        ).pack(padx=14, pady=(0, 6), fill="x")

        ctk.CTkButton(
            panel_izq,
            text="Modelo de estudiantes",
            height=30,
            fg_color="transparent",
            border_width=1,
            command=self.accion_descargar_plantilla_excel,
        ).pack(padx=14, pady=(0, 10), fill="x")

        ctk.CTkLabel(panel_izq, text="Apellidos:").pack(padx=14, pady=(2, 1), anchor="w")
        self.est_entry_apellidos = ctk.CTkEntry(panel_izq, placeholder_text="Ej. Alvarado Pérez")
        self.est_entry_apellidos.pack(padx=14, pady=(0, 6), fill="x")

        ctk.CTkLabel(panel_izq, text="Nombres:").pack(padx=14, pady=(2, 1), anchor="w")
        self.est_entry_nombres = ctk.CTkEntry(panel_izq, placeholder_text="Ej. Lucía Fernanda")
        self.est_entry_nombres.pack(padx=14, pady=(0, 6), fill="x")

        f_gs = ctk.CTkFrame(panel_izq, fg_color="transparent")
        f_gs.pack(padx=14, pady=(2, 6), fill="x")
        f_gs.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(f_gs, text="Grado:").grid(row=0, column=0, sticky="w")
        self.est_entry_grado = ctk.CTkComboBox(f_gs, values=["1°", "2°", "3°", "4°", "5°"], width=80)
        self.est_entry_grado.set("4°")
        self.est_entry_grado.grid(row=1, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkLabel(f_gs, text="Sección:").grid(row=0, column=1, sticky="w")
        self.est_entry_seccion = ctk.CTkComboBox(f_gs, values=["A", "B", "C", "D", "E"], width=80)
        self.est_entry_seccion.set("A")
        self.est_entry_seccion.grid(row=1, column=1, padx=4, sticky="ew")

        ctk.CTkLabel(f_gs, text="Estado:").grid(row=0, column=2, sticky="w")
        self.est_combo_estado = ctk.CTkComboBox(f_gs, values=["ACTIVO", "RETIRADO"], width=110)
        self.est_combo_estado.set("ACTIVO")
        self.est_combo_estado.grid(row=1, column=2, padx=(4, 0), sticky="ew")

        ctk.CTkButton(
            panel_izq, text="Registrar estudiante", command=self.accion_guardar_estudiante
        ).pack(padx=14, pady=(8, 5), fill="x")

        self.btn_est_actualizar = ctk.CTkButton(
            panel_izq,
            text="Guardar cambios",
            fg_color="#0f766e",
            state="disabled",
            command=self.accion_actualizar_estudiante,
        )
        self.btn_est_actualizar.pack(padx=14, pady=(0, 5), fill="x")

        self.btn_est_eliminar = ctk.CTkButton(
            panel_izq,
            text="Eliminar Registro",
            fg_color="#b91c1c",
            state="disabled",
            command=self.accion_eliminar_estudiante,
        )
        self.btn_est_eliminar.pack(padx=14, pady=(0, 6), fill="x")

        panel_der = ctk.CTkFrame(pane, corner_radius=10)
        pane.add(panel_der,minsize=round(260*pixel_scale(self)),stretch="always")
        panel_der.grid_columnconfigure(0, weight=1)
        panel_der.grid_rowconfigure(1, weight=1)

        barra_f = ctk.CTkFrame(panel_der, fg_color="transparent")
        barra_f.grid(row=0, column=0, padx=12, pady=8, sticky="ew")
        barra_f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(barra_f, text="Buscar:").grid(row=0, column=0, padx=(0, 6))
        self.entry_buscar_est = ctk.CTkEntry(barra_f, placeholder_text="Código 4A01, apellidos o nombres...")
        self.entry_buscar_est.grid(row=0, column=1, padx=(0, 8), sticky="ew")
        self.entry_buscar_est.bind("<KeyRelease>", lambda _e: self.recargar_tabla_estudiantes())

        ctk.CTkLabel(barra_f, text="Ordenar por:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=2, padx=(4, 4)
        )
        self.est_combo_orden = ctk.CTkComboBox(
            barra_f,
            values=["Apellidos (A-Z)", "Apellidos (Z-A)", "Código (Ej. 4A01)", "Nombres (A-Z)", "Sección y Apellidos"],
            width=155,
            command=lambda _v: self.recargar_tabla_estudiantes(),
        )
        self.est_combo_orden.set("Apellidos (A-Z)")
        self.est_combo_orden.grid(row=0, column=3, padx=(0, 8))

        self.chk_ver_retirados = ctk.CTkCheckBox(
            barra_f, text="Ver RETIRADOS", command=self.recargar_tabla_estudiantes
        )
        self.chk_ver_retirados.select()
        self.chk_ver_retirados.grid(row=0, column=4, padx=6)

        self.lbl_total_estudiantes = ctk.CTkLabel(barra_f, text="0 estudiantes", font=ctk.CTkFont(weight="bold"))
        self.lbl_total_estudiantes.grid(row=0, column=5, padx=(6, 0))

        self.tree_estudiantes = ttk.Treeview(
            panel_der,
            columns=("ID", "Codigo", "Apellidos", "Nombres", "Grado", "Seccion", "Estado"),
            show="headings",
            selectmode="browse",
            displaycolumns=("Codigo", "Apellidos", "Nombres", "Grado", "Seccion", "Estado")
        )
        for col, txt, w, al in [
            ("ID", "ID", 45, "center"),
            ("Codigo", "Código (Ej. 4A01)", 120, "center"),
            ("Apellidos", "Apellidos", 210, "w"),
            ("Nombres", "Nombres", 210, "w"),
            ("Grado", "Grado", 70, "center"),
            ("Seccion", "Sección", 70, "center"),
            ("Estado", "Estado", 100, "center"),
        ]:
            self.tree_estudiantes.heading(col, text=txt)
            self.tree_estudiantes.column(col, width=w, anchor=al)
        self.tree_estudiantes.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.tree_estudiantes.bind("<<TreeviewSelect>>", self._al_seleccionar_estudiante_tabla)
        flow_toolbar(barra_f)

    # --------------------------------------------------------------------------
    # PESTAÑA 3: CREAR ACTIVIDAD + EXPORTAR/IMPORTAR PLANTILLA DE RÚBRICA O LISTA DE COTEJO
    # --------------------------------------------------------------------------
    def _construir_tab_crear_actividad(self) -> None:
        self.tab_crear.grid_columnconfigure(0, weight=1)
        self.tab_crear.grid_columnconfigure(1, weight=0)
        self.tab_crear.grid_rowconfigure(0, weight=1)

        pane=split(self.tab_crear,"formulario_actividad")
        pane.grid(row=0,column=0,columnspan=2,sticky="nsew",padx=6,pady=6)
        panel_form = scroll_area(pane, width=600, corner_radius=10, auto_hide=True)
        pane.add(panel_form.container,width=round(480*pixel_scale(self)),minsize=round(240*pixel_scale(self)),stretch="never")
        panel_form.grid_columnconfigure(0, weight=1)
        panel_form.grid_rowconfigure(4, weight=0)

        f_head = ctk.CTkFrame(panel_form, fg_color="transparent")
        f_head.grid(row=0, column=0, padx=14, pady=(8, 2), sticky="ew")
        f_head.grid_columnconfigure(0, weight=1)

        self.lbl_modo_creacion = ctk.CTkLabel(
            f_head,
            text="Actividad",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.lbl_modo_creacion.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            f_head,
            text="Nueva",
            width=110,
            height=28,
            fg_color="transparent",
            border_width=1,
            command=self.accion_limpiar_formulario_actividad,
        ).grid(row=0, column=1)

        f_datos1 = ctk.CTkFrame(panel_form, fg_color="transparent")
        f_datos1.grid(row=1, column=0, padx=14, pady=2, sticky="ew")
        f_datos1.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            f_datos1, text="Rubro", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        self.crear_combo_categoria = ctk.CTkComboBox(
            f_datos1,
            values=["Clases", "Exámenes", "Trabajos", "Prácticas / Otros"],
            command=self.al_elegir_rubro_actividad,
        )
        self.crear_combo_categoria.set("Clases")
        self.crear_combo_categoria.grid(row=1, column=0, padx=(0, 6), pady=(0, 4), sticky="ew")

        ctk.CTkLabel(
            f_datos1, text="Peso relativo", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=1, sticky="w")
        self.crear_combo_peso = ctk.CTkComboBox(
            f_datos1,
            values=["1", "1.5", "2", "3"],
        )
        self.crear_combo_peso.set("1")
        self.crear_combo_peso.grid(row=1, column=1, pady=(0, 4), sticky="ew")

        ctk.CTkLabel(
            f_datos1, text="Tema", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=2, column=0, sticky="w")
        ctk.CTkLabel(
            f_datos1, text="Fecha", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=4, column=0, sticky="w")
        
        self.crear_entry_titulo = ctk.CTkEntry(
            f_datos1, placeholder_text="Nombre de la clase, prueba, trabajo o ficha"
        )
        self.crear_entry_titulo.grid(row=3, column=0,columnspan=2, pady=(0, 8), sticky="ew")

        import datetime
        self.crear_ent_fecha = ctk.CTkEntry(f_datos1, width=120)
        self.crear_ent_fecha.insert(0, datetime.date.today().isoformat())
        self.crear_ent_fecha.grid(row=4, column=1, pady=(0, 4), sticky="ew")

        ctk.CTkLabel(f_datos1,text='Tipo de actividad',font=ctk.CTkFont(size=12,weight='bold')).grid(row=5,column=0,columnspan=2,sticky='w')
        self.crear_combo_tipo=ctk.CTkComboBox(f_datos1,values=['Actividad','Prueba','Trabajo','Ficha de trabajo'],state='readonly',command=self.al_elegir_tipo_actividad)
        self.crear_combo_tipo.set('Actividad');self.crear_combo_tipo.grid(row=6,column=0,columnspan=2,sticky='ew',pady=(0,6))
        ctk.CTkLabel(f_datos1,text='Cómo evaluar',font=ctk.CTkFont(size=12,weight='bold')).grid(row=7,column=0,columnspan=2,sticky='w')
        self.crear_combo_metodo=ctk.CTkComboBox(f_datos1,values=['Nota global','Nota directa','Rúbrica','Lista de Cotejo'],state='readonly',command=lambda _:self.mostrar_capacidades_actividad())
        self.crear_combo_metodo.set('Nota global');self.crear_combo_metodo.grid(row=8,column=0,columnspan=2,sticky='ew')
        self.crear_peso_ayuda=ctk.CTkLabel(f_datos1,text='Peso 1: igual importancia dentro del rubro. El porcentaje se elige en Ponderaciones.',anchor='w',justify='left',wraplength=310,font=ctk.CTkFont(size=13))
        self.crear_peso_ayuda.grid(row=9,column=0,columnspan=2,sticky='ew',pady=4);wrap_label(self.crear_peso_ayuda)
        ctk.CTkLabel(f_datos1,text='Unidad didáctica',font=ctk.CTkFont(size=13,weight='bold')).grid(row=10,column=0,columnspan=2,sticky='w',pady=(8,2))
        self.crear_combo_unidad=ctk.CTkComboBox(f_datos1,values=['Sin unidad'],state='readonly')
        self.crear_combo_unidad.set('Sin unidad');self.crear_combo_unidad.grid(row=11,column=0,columnspan=2,sticky='ew',pady=(0,6))
        self.crear_txt_proposito = TextBuffer()

        f_comp_c = ctk.CTkFrame(panel_form, fg_color="transparent")
        f_comp_c.grid(row=3, column=0, padx=14, pady=2, sticky="ew")
        f_comp_c.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            f_comp_c, text="Competencia", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        self.crear_combo_comp = ctk.CTkComboBox(
            f_comp_c, state="readonly", command=self._al_cambiar_comp_en_creacion
        )
        self.crear_combo_comp.grid(row=1, column=0, pady=(0, 4), sticky="ew")
        self.lbl_comp_completa = ctk.CTkLabel(f_comp_c, text="", wraplength=480, justify="left", anchor="w")
        Tooltip(self.crear_combo_comp,lambda:self.lbl_comp_completa.cget("text"))
        self.lbl_comp_completa.grid(row=2,column=0,sticky="ew",pady=8)
        wrap_label(self.lbl_comp_completa)

        self.crear_btn_capacidades=ctk.CTkButton(f_comp_c,text='Ver / cambiar capacidades',height=30,command=self.alternar_capacidades_actividad)
        self.crear_btn_capacidades.grid(row=3,column=0,sticky='ew',pady=4)
        self._caps_expanded=False
        self.scroll_caps_creacion = ctk.CTkFrame(panel_form)
        self.scroll_caps_creacion.grid(row=4, column=0, padx=14, pady=4, sticky="nsew")
        self.scroll_caps_creacion.grid_columnconfigure(0, weight=1)

        f_btns_c=ctk.CTkFrame(panel_form,fg_color="transparent")
        f_btns_c.grid(row=5,column=0,padx=14,pady=10,sticky="ew")
        f_btns_c.grid_columnconfigure((0,1),weight=1)
        ctk.CTkButton(f_btns_c,text="Guardar actividad",height=34,fg_color="#2563eb",
            command=self.accion_guardar_nueva_actividad).grid(row=0,column=0,sticky="ew",padx=(0,4))
        self.btn_actualizar_act=ctk.CTkButton(f_btns_c,text="Actualizar",height=34,state="disabled",
            command=self.accion_actualizar_actividad_existente)
        self.btn_actualizar_act.grid(row=0,column=1,sticky="ew",padx=4)
        ctk.CTkButton(f_btns_c,text="Propósito de la clase",height=34,command=lambda:self.editar_texto_actividad(self.crear_txt_proposito,"Propósito de la clase")).grid(row=1,column=0,sticky="ew",padx=(0,4),pady=6)
        ctk.CTkLabel(f_btns_c,text="El instrumento se configura en Calificaciones.",font=ctk.CTkFont(size=13),wraplength=300,justify="left").grid(row=2,column=0,columnspan=2,sticky="ew",pady=6)

        panel_lista = ctk.CTkFrame(pane, corner_radius=10)
        pane.add(panel_lista,minsize=round(260*pixel_scale(self)),stretch="always")
        panel_lista.grid_columnconfigure(0, weight=1)
        panel_lista.grid_rowconfigure(1, weight=1)

        barra_l = ctk.CTkFrame(panel_lista, fg_color="transparent")
        barra_l.grid(row=0, column=0, padx=12, pady=(10, 6), sticky="ew")
        barra_l.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            barra_l, text="Filtrar por Categoría:", font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, padx=(0, 6))
        self.filtro_cat_creacion = ctk.CTkComboBox(
            barra_l,
            values=["Todas", "Clases", "Exámenes", "Trabajos", "Prácticas / Otros"],
            width=155,
            command=lambda _v: self.recargar_tabla_actividades_creadas(),
        )
        self.filtro_cat_creacion.set("Todas")
        self.filtro_cat_creacion.grid(row=0, column=1, sticky="w")

        ctk.CTkButton(
            barra_l,
            text="🗑 Eliminar",
            width=90,
            fg_color="#b91c1c",
            command=self.accion_eliminar_actividad_seleccionada,
        ).grid(row=0, column=2, padx=6)

        ctk.CTkButton(
            barra_l,
            text="Ingresar notas",
            height=36,
            fg_color="#1d4ed8",
            font=ctk.CTkFont(weight="bold"),
            command=self.accion_ir_a_calificar_seleccionada,
        ).grid(row=0, column=3, padx=(4, 0))

        self.tree_actividades = ttk.Treeview(
            panel_lista,
            columns=("ID", "Categoria", "Peso", "Titulo", "Competencia", "Capacidades", "Instrumento"),
            show="headings",
            selectmode="browse",
            displaycolumns=("Titulo", "Categoria", "Peso", "Instrumento")
        )
        for col, txt, w, al in [
            ("ID", "ID", 42, "center"),
            ("Categoria", "Categoría", 110, "center"),
            ("Peso", "Peso", 65, "center"),
            ("Titulo", "Actividad", 300, "w"),
            ("Competencia", "Competencia", 180, "w"),
            ("Capacidades", "Capacidades y Criterios Evaluados", 235, "w"),
            ("Instrumento", "Evaluación", 150, "center"),
        ]:
            self.tree_actividades.heading(col, text=txt)
            self.tree_actividades.column(col, width=w, anchor=al)
        self.tree_actividades.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.tree_actividades.bind("<<TreeviewSelect>>", self._al_seleccionar_actividad_en_tabla)
        self.tree_actividades.bind("<Double-1>", lambda _e: self.accion_ir_a_calificar_seleccionada())
        flow_toolbar(barra_l)

    # --------------------------------------------------------------------------
    # PESTAÑA 4: INGRESAR / EDITAR NOTAS (MODO NORMAL O CON LISTA DE COTEJO / RÚBRICA)
    # --------------------------------------------------------------------------
    def _construir_tab_calificar_actividad(self) -> None:
        self.crear_panel_calificaciones()

    # --------------------------------------------------------------------------
    # PESTAÑA 5: BUSCADOR GENERAL (MUESTRA LA NOTA PUESTA EN CADA CLASE SIN PROMEDIAR)
    # --------------------------------------------------------------------------
    def _construir_tab_buscador_alumnos(self) -> None:
        self.tab_buscador.grid_columnconfigure(0, weight=1)
        self.tab_buscador.grid_rowconfigure(1, weight=1)

        f_filtros = ctk.CTkFrame(self.tab_buscador, corner_radius=10)
        f_filtros.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        f_filtros.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

        ctk.CTkLabel(
            f_filtros, text="Alumno", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, padx=8, pady=(8, 2), sticky="w")
        self.busc_entry_alumno = ctk.CTkEntry(
            f_filtros, placeholder_text="Escriba apellido, nombre o código 4A01..."
        )
        self.busc_entry_alumno.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")
        self.busc_entry_alumno.bind("<KeyRelease>", lambda _e: self.recargar_buscador_alumnos())

        ctk.CTkLabel(
            f_filtros, text="Competencia", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=1, padx=6, pady=(8, 2), sticky="w")
        self.busc_combo_comp = ctk.CTkComboBox(
            f_filtros,
            values=["Todas las Competencias"],
            state="readonly",
            command=lambda _v: self.recargar_buscador_alumnos(),
        )
        self.busc_combo_comp.set("Todas las Competencias")
        self.busc_combo_comp.grid(row=1, column=1, padx=6, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(
            f_filtros, text="Tipo", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=2, padx=6, pady=(8, 2), sticky="w")
        self.busc_combo_cat = ctk.CTkComboBox(
            f_filtros,
            values=["Todas", "Clases", "Exámenes", "Trabajos", "Prácticas / Otros"],
            state="readonly",
            command=lambda _v: self.recargar_buscador_alumnos(),
        )
        self.busc_combo_cat.set("Todas")
        self.busc_combo_cat.grid(row=1, column=2, padx=6, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(
            f_filtros, text="Alcance", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=3, padx=6, pady=(8, 2), sticky="w")
        self.busc_combo_alcance = ctk.CTkComboBox(
            f_filtros,
            values=["Salón Actual", "Todas las Secciones y Grados"],
            state="readonly",
            command=lambda _v: self.recargar_buscador_alumnos(),
        )
        self.busc_combo_alcance.set("Salón Actual")
        self.busc_combo_alcance.grid(row=1, column=3, padx=6, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(
            f_filtros, text="Orden", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=4, padx=6, pady=(8, 2), sticky="w")
        self.busc_combo_orden = ctk.CTkComboBox(
            f_filtros,
            values=[
                "Apellidos (A-Z)",
                "Apellidos (Z-A)",
                "Notas (Mayor a Menor)",
                "Notas (Menor a Mayor)",
                "Código (Ej. 4A01)",
                "Sección y Código",
            ],
            state="readonly",
            command=lambda _v: self.recargar_buscador_alumnos(),
        )
        self.busc_combo_orden.set("Apellidos (A-Z)")
        self.busc_combo_orden.grid(row=1, column=4, padx=6, pady=(0, 8), sticky="ew")

        self.busc_chk_retirados = ctk.CTkCheckBox(
            f_filtros, 
            text="Ver Retirados", 
            command=self.recargar_buscador_alumnos,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.busc_chk_retirados.grid(row=0, column=6, padx=10, pady=(8, 2))

        # Selector directo para elegir cuál de las clases mostradas se desea editar en la Pestaña 4
        self.busc_combo_ir_clase = ctk.CTkComboBox(
            f_filtros, values=["Elegir clase a editar..."], width=190, state="readonly"
        )
        self.busc_combo_ir_clase.grid(row=0, column=5, padx=(6, 10), pady=(8, 2))

        ctk.CTkButton(
            f_filtros,
            text="Abrir calificaciones",
            height=32,
            fg_color="#1d4ed8",
            font=ctk.CTkFont(weight="bold"),
            command=self.accion_editar_clase_desde_buscador,
        ).grid(row=1, column=5, padx=(6, 10), pady=(0, 8))

        ctk.CTkButton(
            f_filtros,
            text="Exportar estudiante",
            height=32,
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(weight="bold"),
            command=self.accion_descargar_reporte_estudiante,
        ).grid(row=1, column=6, padx=(0, 10), pady=(0, 8))

        f_tabla_b = ctk.CTkFrame(self.tab_buscador, corner_radius=8)
        f_tabla_b.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        f_tabla_b.grid_columnconfigure(0, weight=1)
        f_tabla_b.grid_rowconfigure(0, weight=1)

        self.tree_buscador_alumnos = ttk.Treeview(f_tabla_b, show="headings", selectmode="browse")
        sb_y = scrollbar(f_tabla_b, orient="vertical", command=self.tree_buscador_alumnos.yview)
        sb_x = scrollbar(f_tabla_b, orient="horizontal", command=self.tree_buscador_alumnos.xview)
        self.tree_buscador_alumnos.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        self.tree_buscador_alumnos.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        
        f_detalle = ctk.CTkFrame(f_tabla_b, corner_radius=8, fg_color="transparent")
        f_detalle.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        f_detalle.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(f_detalle, text="Comentario y retroalimentación", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="ew")
        self.busc_txt_comentario_detalle = ctk.CTkTextbox(f_detalle, height=80, wrap="word", state="disabled")
        self.busc_txt_comentario_detalle.grid(row=1, column=0, sticky="ew")
        
        self.tree_buscador_alumnos.bind("<<TreeviewSelect>>", self._al_seleccionar_fila_buscador)
        flow_toolbar(f_filtros)

    # --------------------------------------------------------------------------
    # PESTAÑA 6: PORCENTAJES (%) + VER Y MODIFICAR PESOS DE CADA ITEM POR CATEGORÍA + GRÁFICOS
    # --------------------------------------------------------------------------
    def _construir_tab_pesos_y_graficos(self) -> None:
        self.tab_graficos.grid_columnconfigure(0, weight=0)
        self.tab_graficos.grid_columnconfigure(1, weight=1)
        self.tab_graficos.grid_rowconfigure(0, weight=1)

        pane=split(self.tab_graficos,"ponderaciones")
        pane.grid(row=0,column=0,columnspan=2,sticky="nsew",padx=6,pady=6)
        panel_izq = ctk.CTkFrame(pane, width=455, corner_radius=10)
        pane.add(panel_izq,width=round(370*pixel_scale(self)),minsize=round(240*pixel_scale(self)),stretch="never")
        panel_izq.grid_columnconfigure(0, weight=1)
        panel_izq.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            panel_izq,
            text="Pesos elegidos para el promedio",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=14, pady=(10, 4), sticky="w")

        f_grid_pct = ctk.CTkFrame(panel_izq, corner_radius=8)
        f_grid_pct.grid(row=1, column=0, padx=14, pady=2, sticky="ew")
        f_grid_pct.grid_columnconfigure((0, 1), weight=1)

        explanation=ctk.CTkLabel(f_grid_pct,text="Usted elige los pesos; no cambian al importar. Deben sumar 100%.",wraplength=290,justify="left")
        explanation.grid(row=4,column=0,columnspan=2,padx=8,pady=6,sticky="ew")
        wrap_label(explanation)
        self.entries_pct_rubros: Dict[str, ctk.CTkEntry] = {}
        for idx, (etiqueta, clave) in enumerate(
            [
                ("📘 Clases (%)", "Clases"),
                ("📗 Exámenes (%)", "Exámenes"),
                ("📙 Trabajos (%)", "Trabajos"),
                ("📕 Prácticas (%)", "Prácticas / Otros"),
            ]
        ):
            ctk.CTkLabel(f_grid_pct, text=etiqueta, font=ctk.CTkFont(size=14, weight="bold")).grid(
                row=(idx//2)*2, column=idx%2, padx=4, pady=(6, 2)
            )
            ent = ctk.CTkEntry(f_grid_pct, width=85, font=ctk.CTkFont(size=15, weight="bold"), justify="center")
            ent.grid(row=(idx//2)*2+1, column=idx%2, padx=4, pady=(0, 8), sticky="ew")
            self.entries_pct_rubros[clave] = ent

        ctk.CTkButton(
            panel_izq,
            text="Guardar porcentajes",
            height=38,
            fg_color="#1d4ed8",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.accion_guardar_porcentajes_rubros,
        ).grid(row=2, column=0, padx=14, pady=(4, 8), sticky="ew")

        # SECCIÓN SOLICITADA: Al seleccionar una categoría (Clases, Exámenes, Trabajos o Prácticas),
        # aparecen todas las actividades de esa categoría para ver y modificar sus pesos ahí mismo.
        f_sel_cat = ctk.CTkFrame(panel_izq, fg_color="transparent")
        f_sel_cat.grid(row=3, column=0, padx=14, pady=(4, 2), sticky="ew")
        f_sel_cat.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            f_sel_cat,
            text="Pesos de actividades por categoría", wraplength=370,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self.graf_combo_categoria_pesos = ctk.CTkComboBox(
            f_sel_cat,
            values=["Exámenes", "Trabajos", "Clases", "Prácticas / Otros"],
            state="readonly",
            font=ctk.CTkFont(size=14),
            height=32,
            command=lambda _v: self.cargar_lista_pesos_por_categoria_en_graficos(),
        )
        self.graf_combo_categoria_pesos.set("Exámenes")
        self.graf_combo_categoria_pesos.grid(row=1, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(
            f_sel_cat,
            text="Guardar pesos",
            fg_color="#15803d",
            hover_color="#166534",
            height=32,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.accion_guardar_pesos_individuales_categoria,
        ).grid(row=1, column=1, sticky="ew")

        self.scroll_pesos_categoria = scroll_area(panel_izq)
        self.scroll_pesos_categoria.grid(row=4, column=0, padx=14, pady=(4, 10), sticky="nsew")
        self.scroll_pesos_categoria.grid_columnconfigure(0, weight=1)

        # Panel derecho: Lienzo de Gráficos
        panel_der = ctk.CTkFrame(pane, corner_radius=10)
        pane.add(panel_der,minsize=round(260*pixel_scale(self)),stretch="always")
        panel_der.grid_columnconfigure(0, weight=1)
        panel_der.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            panel_der,
            text="Ponderaciones y cobertura curricular", wraplength=550,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=14, pady=(10, 4), sticky="w")

        self.graficos_tabs = ctk.CTkTabview(panel_der, command=self._render_current_plot)
        self.graficos_tabs.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.graficos_hosts = []
        for title in ("Ponderaciones", "Competencias", "Capacidades"):
            tab = self.graficos_tabs.add(title)
            host = scroll_area(tab, horizontal=True, min_width=480, auto_hide=True)
            host.pack(fill="both", expand=True)
            self.graficos_hosts.append(host)
            host.bind("<Configure>",lambda event,i=len(self.graficos_hosts)-1:self._programar_grafico(i),add="+")
        self.figuras_porcentajes = []

    # --------------------------------------------------------------------------
    # PESTAÑA 7: MATRIZ GENERAL + EXPORTAR E IMPORTAR EXCEL CON NOTAS
    # --------------------------------------------------------------------------
    def _construir_tab_matriz_capacidades(self) -> None:
        self.tab_matriz.grid_columnconfigure(0, weight=1)
        self.tab_matriz.grid_rowconfigure(1, weight=1)

        barra_m = ctk.CTkFrame(self.tab_matriz, fg_color="transparent")
        barra_m.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        barra_m.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            barra_m,
            text="Promedios por competencia y capacidad",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(barra_m, text="Ordenar por:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=1, padx=(6, 4)
        )
        self.matriz_combo_orden = ctk.CTkComboBox(
            barra_m,
            values=[
                "Apellidos (A-Z)",
                "Código (Ej. 4A01)",
                "Notas (Mayor a Menor)",
                "Notas (Menor a Mayor)",
                "Apellidos (Z-A)",
            ],
            width=160,
            command=lambda _v: self.recargar_matriz_completa(),
        )
        self.matriz_combo_orden.set("Apellidos (A-Z)")
        self.matriz_combo_orden.grid(row=0, column=2, padx=(0, 8))

        ctk.CTkButton(
            barra_m,
            text="Nota manual",
            fg_color="#0f766e",
            command=self.accion_colocar_nota_manual_capacidad,
        ).grid(row=0, column=3, padx=4)

        ctk.CTkButton(
            barra_m,
            text="Exportar matriz Excel",
            fg_color="#15803d",
            hover_color="#166534",
            font=ctk.CTkFont(weight="bold"),
            command=self.accion_exportar_matriz_excel,
        ).grid(row=0, column=4, padx=4)

        ctk.CTkButton(
            barra_m,
            text="Importar matriz Excel",
            fg_color="#1d4ed8",
            font=ctk.CTkFont(weight="bold"),
            command=self.accion_importar_matriz_excel_con_notas,
        ).grid(row=0, column=5, padx=(4, 0))

        f_tree_m = ctk.CTkFrame(self.tab_matriz, corner_radius=8)
        f_tree_m.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        f_tree_m.grid_columnconfigure(0, weight=1)
        f_tree_m.grid_rowconfigure(0, weight=1)

        self.tree_matriz = GradeTreeview(f_tree_m, show="headings", selectmode="browse")
        scroll_x = scrollbar(f_tree_m, orient="horizontal", command=self.tree_matriz.xview)
        scroll_y = scrollbar(f_tree_m, orient="vertical", command=self.tree_matriz.yview)
        self.tree_matriz.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)

        self.tree_matriz.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        flow_toolbar(barra_m)

    def _construir_tab_estadisticas(self) -> None:
        self.tab_estadisticas.grid_columnconfigure(0, weight=1)
        self.tab_estadisticas.grid_rowconfigure(1, weight=1)

        f_controles = ctk.CTkFrame(self.tab_estadisticas, corner_radius=10)
        f_controles.grid(row=0, column=0, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(f_controles, text="Competencia:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=4, pady=4)
        self.stats_combo_comp = ctk.CTkComboBox(f_controles, width=200, state="readonly")
        self.stats_combo_comp.grid(row=0, column=1, padx=4, pady=4)

        ctk.CTkLabel(f_controles, text="Estudiante:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=4, pady=4)
        self.stats_combo_estudiante = ctk.CTkComboBox(f_controles, width=200, state="readonly")
        self.stats_combo_estudiante.grid(row=0, column=3, padx=4, pady=4)
        
        ctk.CTkLabel(f_controles, text="Tipo de Gráfico:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=4, pady=4)
        self.stats_combo_tipo = ctk.CTkComboBox(f_controles, values=["Dashboard Completo (Todos)", "Histograma de Notas (Numéricas)", "Gráfico de Barras (Literales)", "Polígono de Frecuencias (Evolución)", "Desempeño por Capacidades", "Comparativa de Secciones"], width=230, state="readonly")
        self.stats_combo_tipo.set("Histograma de Notas (Numéricas)")
        self.stats_combo_tipo.grid(row=0, column=5, padx=4, pady=4)

        f_btns = ctk.CTkFrame(f_controles, fg_color="transparent")
        f_btns.grid(row=1, column=0, columnspan=6, pady=(0, 8))
        
        ctk.CTkButton(f_btns, text="📊 Generar Gráficos", fg_color="#1d4ed8", font=ctk.CTkFont(weight="bold"), command=self.accion_generar_grafico_estadisticas).pack(side="left", padx=10)
        ctk.CTkButton(f_btns, text="📥 Exportar Reporte a PDF", fg_color="#b91c1c", hover_color="#991b1b", font=ctk.CTkFont(weight="bold"), command=self.accion_exportar_reporte_pdf).pack(side="left", padx=10)

        self.f_grafico = scroll_area(self.tab_estadisticas, corner_radius=8, fg_color="white", horizontal=True, min_width=600, auto_hide=True)
        self.f_grafico.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        flow_toolbar(f_controles)
        self.f_grafico.bind('<Configure>',self._programar_estadisticas,add='+')

    def _programar_estadisticas(self,event=None):
        if getattr(self,'_closing_ui',False) or not hasattr(self,'fig_actual') or self.tabview.get()!='Estadísticas':return
        width=max(600,self.f_grafico.winfo_width()/pixel_scale(self))
        if abs(width-getattr(self,'_stats_plot_width',0))<50:return
        job=getattr(self,'_stats_resize_job',None)
        if job:self.after_cancel(job)
        self._stats_resize_job=self.after(220,self.accion_generar_grafico_estadisticas)

    def accion_generar_grafico_estadisticas(self) -> None:
        if getattr(self,"_closing_ui",False):return
        self.update_idletasks()
        curso_id = self.obtener_curso_activo_id()
        if not curso_id: return
        grado = self.combo_grado_global.get()
        seccion = self.combo_seccion_global.get()
        
        comp_str = self.stats_combo_comp.get()
        if not comp_str: return
        
        comp_id_filtro = None
        if comp_str != "Todas las Competencias":
            comp_id_filtro = self._obtener_comp_id_desde_texto(comp_str)
            
        est_nombre = self.stats_combo_estudiante.get()
        est_filtro = None if est_nombre == "Todo el Aula" else est_nombre
        
        tipo = self.stats_combo_tipo.get()
        
        for widget in self.f_grafico.winfo_children():
            widget.destroy()
            
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import numpy as np
        
        # Modo Comparativa usa "Todas" las secciones
        sec_filtro = "Todas" if tipo == "Comparativa de Secciones" else seccion
        filas = obtener_historial_vertical_estudiantes(curso_id, grado, sec_filtro, competencia_id_filtro=comp_id_filtro)
        if est_filtro:
            filas = [f for f in filas if f["alumno_nombre"] == est_filtro]
            
        if not filas:
            ctk.CTkLabel(self.f_grafico, text="No hay datos suficientes.", text_color="black").pack(pady=40)
            return

        self._stats_resize_job=None
        is_dash = "Dashboard" in tipo
        if hasattr(self, "fig_actual"):
            self.fig_actual.clear()
        plot_width=max(600,self.f_grafico.winfo_width()/pixel_scale(self))
        self._stats_plot_width=plot_width
        cap_count=len({i['id'] for row in filas for i in row.get('notas_detalle',[]) if i['nota'] is not None})
        plot_height=((900 if plot_width<950 else 620)+max(180,cap_count*66+60)) if is_dash else max(360,cap_count*66+100) if "Capacidades" in tipo else max(360,min(520,plot_width*.52))
        fig = Figure(figsize=(plot_width/100,plot_height/100), dpi=100*pixel_scale(self),layout="constrained")
        fig.set_layout_engine("constrained",w_pad=.15,h_pad=.15,hspace=.1,wspace=.12)
        
        # Info for PDF export
        curso_nom = self.combo_curso_global.get()
        sec_info = "Todas las Secciones" if tipo == "Comparativa de Secciones" else f"'{seccion}'"
        info_txt = f"Reporte de {curso_nom} | {grado} {sec_info}\nFiltro: {comp_str} | {est_nombre}"
        import textwrap
        fig.suptitle("\n".join(textwrap.fill(line,max(45,int(plot_width/8))) for line in info_txt.splitlines()),fontsize=12,fontweight="bold")
        
        axes = []
        if is_dash:
            if plot_width<950:
                layout=fig.add_gridspec(4,1,height_ratios=[260,260,240,max(180,cap_count*66+60)])
                axes=[fig.add_subplot(layout[i,0]) for i in range(4)]
            else:
                layout=fig.add_gridspec(3,2,height_ratios=[260,240,max(180,cap_count*66+60)])
                axes=[fig.add_subplot(layout[0,0]),fig.add_subplot(layout[0,1]),fig.add_subplot(layout[1,:]),fig.add_subplot(layout[2,:])]
            tipos_a_graficar = ["Histograma", "Barras", "Polígono", "Capacidades"]
        else:
            axes = [fig.add_subplot(111)]
            tipos_a_graficar = [tipo]
            
        for i, ax_tipo in enumerate(tipos_a_graficar):
            ax = axes[i]
            if "Histograma" in ax_tipo:
                notas = [float(f["promedio"]) for f in filas if f["promedio"] is not None]
                ax.hist(notas, bins=range(0, 22, 2), color="#3b82f6", edgecolor="black")
                ax.set_title("Histograma de Notas Numéricas")
                ax.set_xlabel("Rango de Notas (0-20)")
                ax.set_ylabel("Frecuencia")
                ax.set_xticks(range(0, 21, 2))
                
            elif "Barras" in ax_tipo:
                notas = [float(f["promedio"]) for f in filas if f["promedio"] is not None]
                from escala import thresholds
                from db import DB_PATH
                b_min,a_min,ad_min=thresholds(DB_PATH)
                labels={level:level for level in ("C","B","A","AD")}
                rangos={label:0 for label in labels.values()}
                for n in notas:rangos[labels[nota_a_literal(n)]]+=1
                ax.bar(rangos.keys(), rangos.values(), color=["#ef4444", "#f59e0b", "#22c55e", "#3b82f6"])
                ax.set_title("Distribución de Notas Literales")
                ax.set_xlabel(f"C: <{b_min:g} · B: {b_min:g}–<{a_min:g}\nA: {a_min:g}–<{ad_min:g} · AD: {ad_min:g}–20",fontsize=10)
                ax.set_ylabel("Frecuencia")
                
            elif "Polígono" in ax_tipo:
                if est_filtro:
                    datos = [(f["fecha"], float(f["promedio"])) for f in filas if f["promedio"] is not None]
                    datos.sort(key=lambda x: x[0])
                    ax.plot([d[0] for d in datos], [d[1] for d in datos], marker="o", color="#8b5cf6")
                    ax.set_title(f"Evolución de {est_filtro}")
                else:
                    fechas = {}
                    for f in filas:
                        if f["promedio"] is not None: fechas.setdefault(f["fecha"], []).append(float(f["promedio"]))
                    fechas_ordenadas = sorted(fechas.keys())
                    if fechas_ordenadas:
                        promedios = [sum(fechas[k])/len(fechas[k]) for k in fechas_ordenadas]
                        ax.plot(fechas_ordenadas, promedios, marker="s", color="#10b981")
                        ax.fill_between(fechas_ordenadas, promedios, alpha=0.2, color="#10b981")
                    ax.set_title("Evolución Promedio del Aula")
                ax.set_ylim(0, 20)
                ax.tick_params(axis='x', rotation=45)
                
            elif "Capacidades" in ax_tipo:
                import textwrap
                cap_notas = {}; cap_names = {}
                for row in filas:
                    for item in row.get("notas_detalle",[]):
                        if item["nota"] is not None:
                            cap_notas.setdefault(item["id"],[]).append(item["nota"])
                            cap_names[item["id"]]=item["nombre"]
                if not cap_notas:
                    ax.set_title("No hay notas por capacidad")
                else:
                    ids=list(cap_notas)
                    labels=[textwrap.fill(cap_names[i],max(18,int(min(280,plot_width*.38)/6.5))) for i in ids]
                    vals=[sum(cap_notas[i])/len(cap_notas[i]) for i in ids]
                    ax.barh(range(len(ids)),vals,color="#2563eb")
                    ax.set_yticks(range(len(ids)),labels,fontsize=9)
                    ax.invert_yaxis();ax.set_xlim(0,20);ax.set_xlabel("Nota promedio por actividad")
                    ax.set_title("Promedios por capacidad")


            elif "Comparativa" in ax_tipo:
                sec_comp_notas = {}
                for f in filas:
                    if f["promedio"] is not None:
                        cod = f.get("seccion", "")
                        if cod:
                            s = cod
                            comp = f.get("competencia", "General")
                            sec_comp_notas.setdefault(s, {}).setdefault(comp, []).append(float(f["promedio"]))
                
                if not sec_comp_notas:
                    ax.set_title("Se requieren Códigos de estudiante (ej. 4A01).")
                else:
                    secs = sorted(sec_comp_notas.keys())
                    comps = set()
                    for s in secs:
                        comps.update(sec_comp_notas[s].keys())
                    comps = sorted(comps)
                    
                    x = np.arange(len(secs))
                    width = 0.8 / max(len(comps), 1)
                    colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6"]
                    
                    for i, c in enumerate(comps):
                        vals = []
                        for s in secs:
                            arr = sec_comp_notas[s].get(c, [])
                            vals.append(sum(arr)/len(arr) if arr else 0)
                        
                        offset = i * width - (len(comps) * width) / 2 + width / 2
                        ax.bar(x + offset, vals, width, label=c[:15]+"..", color=colors[i % len(colors)])
                        
                    ax.set_xticks(x)
                    ax.set_xticklabels([f"Sec. {s}" for s in secs])
                    ax.legend(fontsize=8)
                    ax.set_title("Comparativa por Sección y Competencia")
                    ax.set_ylim(0, 20)
            
        from matplotlib.ticker import MaxNLocator
        for axis,kind in zip(axes,tipos_a_graficar):
            if "Histograma" in kind or "Barras" in kind:axis.yaxis.set_major_locator(MaxNLocator(integer=True))
        canvas = FigureCanvasTkAgg(fig, master=self.f_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", expand=False)
        
        self.fig_actual = fig

    def accion_exportar_reporte_pdf(self) -> None:
        if not hasattr(self, "fig_actual"):
            messagebox.showwarning("Aviso", "Genere un gráfico primero.")
            return
        
        from tkinter import filedialog
        ruta = self.elegir_destino(defaultextension=".pdf", filetypes=[("PDF Document", "*.pdf")])
        if ruta:
            try:
                import reportes
                reportes.save_figure(self.fig_actual, ruta, self.insignia_exportacion())
                messagebox.showinfo("Éxito", f"Reporte PDF guardado en:\n{ruta}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar:\n{e}")

    # ==========================================================================
    # LÓGICA DE SINCRONIZACIÓN
    # ==========================================================================

    def obtener_curso_activo_id(self) -> Optional[int]:
        return self.cursos_map.get(self.combo_curso_global.get())

    def recargar_cursos_y_contexto(self) -> None:
        cursos = obtener_cursos(solo_activos=not self.dev_mode)
        self.cursos_map = {nombre: cid for cid, nombre, act in cursos}
        nombres = list(self.cursos_map.keys())
        self.combo_curso_global.configure(values=nombres)
        if nombres and self.combo_curso_global.get() not in self.cursos_map:
            self.combo_curso_global.set(nombres[0])

        grados, secciones = obtener_grados_y_secciones()
        self.combo_grado_global.configure(values=grados)
        if self.combo_grado_global.get() not in grados: self.combo_grado_global.set(grados[0])
        self.combo_seccion_global.configure(values=secciones)

        # Configurar columnas del treeview segun dev_mode
        if self.dev_mode:
            self.tree_cursos.configure(columns=("ID", "Curso", "Activo"), displaycolumns=("Curso", "Activo"))
            self.tree_cursos.heading("Activo", text="Activo")
            self.tree_cursos.column("Activo", width=50, anchor="center")
        else:
            self.tree_cursos.configure(columns=("ID", "Curso"), displaycolumns=("Curso",))

        for item in self.tree_cursos.get_children():
            self.tree_cursos.delete(item)
            
        for cid, nom, act in cursos:
            if self.dev_mode:
                self.tree_cursos.insert("", "end", values=(cid, nom, "Sí" if act else "No"))
            else:
                self.tree_cursos.insert("", "end", values=(cid, nom))

        self._al_cambiar_curso_global(self.combo_curso_global.get())

    def _al_cambiar_curso_global(self, _nombre_curso: str) -> None:
        if hasattr(self, "_contexto_guardado") and not self.confirmar_descartar(include_points=(self._contexto_guardado!=(self.combo_curso_global.get(),self.combo_grado_global.get(),self.combo_seccion_global.get()))):
            for widget, value in zip((self.combo_curso_global, self.combo_grado_global, self.combo_seccion_global), self._contexto_guardado):
                widget.set(value)
            return
        self._contexto_guardado = (self.combo_curso_global.get(), self.combo_grado_global.get(), self.combo_seccion_global.get())
        curso_id = self.obtener_curso_activo_id()
        if curso_id is None:
            return

        self.competencias_curso_actual = obtener_competencias_por_curso(curso_id)

        for item in self.tree_competencias.get_children():
            self.tree_competencias.delete(item)
        for idx, (cid, cnom) in enumerate(self.competencias_curso_actual, start=1):
            self.tree_competencias.insert("", "end", iid=str(cid), values=(idx, cnom))

        if self.competencias_curso_actual:
            primer_id = str(self.competencias_curso_actual[0][0])
            self.tree_competencias.selection_set(primer_id)
            self._cargar_tree_capacidades(self.competencias_curso_actual[0][0])

        opciones_comp = [nom for _id, nom in self.competencias_curso_actual]
        self.crear_comp_map={f'Competencia {i}':cid for i,(cid,name) in enumerate(self.competencias_curso_actual,1)}
        self.crear_combo_comp.configure(values=list(self.crear_comp_map))

        self.busc_comp_map: Dict[str, Optional[int]] = {"Todas las Competencias": None}
        opciones_busc_comp = ["Todas las Competencias"]
        for i, (cid, nom) in enumerate(self.competencias_curso_actual, start=1):
            opciones_busc_comp.append(nom)
            self.busc_comp_map[nom] = cid
        self.busc_combo_comp.configure(values=opciones_busc_comp)
        self.busc_combo_comp.set("Todas las Competencias")

        if opciones_comp:
            self.crear_combo_comp.set(next(iter(self.crear_comp_map)))
            self._al_cambiar_comp_en_creacion(self.crear_combo_comp.get())
            
        if hasattr(self, "stats_combo_comp"):
            opciones_stats = ["Todas las Competencias"] + opciones_comp
            self.stats_combo_comp.configure(values=opciones_stats)
            self.stats_combo_comp.set("Todas las Competencias")
            
            grado = self.combo_grado_global.get()
            seccion = self.combo_seccion_global.get()
            ests = obtener_estudiantes_filtrados(grado, seccion, "", True)
            opcs_est = ["Todo el Aula"] + [f"{e['Apellidos']}, {e['Nombres']}" for e in ests]
            self.stats_combo_estudiante.configure(values=opcs_est)
            self.stats_combo_estudiante.set("Todo el Aula")

        pesos = obtener_pesos_rubros_curso(curso_id)
        for clave, ent in self.entries_pct_rubros.items():
            ent.delete(0, "end")
            ent.insert(0, f"{pesos.get(clave, 25.0):.1f}".rstrip("0").rstrip("."))

        self.actualizar_contexto_academico()
        self.recargar_tabla_estudiantes()
        self.recargar_tabla_actividades_creadas()
        self.recargar_buscador_alumnos()
        self.cargar_lista_pesos_por_categoria_en_graficos()
        self.dibujar_graficos_estadisticos()
        self.recargar_matriz_completa()

        if hasattr(self,"puntos_panel"):self.puntos_panel.refresh()

    def _al_cambiar_salon_global(self) -> None:
        if not self.confirmar_descartar():
            for widget, value in zip((self.combo_curso_global, self.combo_grado_global, self.combo_seccion_global), self._contexto_guardado):
                widget.set(value)
            return
        self.est_entry_grado.set(self.combo_grado_global.get())
        self.est_entry_seccion.set(self.combo_seccion_global.get())
        self._al_cambiar_curso_global(self.combo_curso_global.get())

    def _al_seleccionar_tree_curso(self, _event: tk.Event) -> None:
        sel = self.tree_cursos.selection()
        if sel:
            nom = self.tree_cursos.item(sel[0], "values")[1]
            if nom != self.combo_curso_global.get():
                self.combo_curso_global.set(nom)
                self._al_cambiar_curso_global(nom)

    def _al_seleccionar_tree_competencia(self, _event: tk.Event) -> None:
        sel = self.tree_competencias.selection()
        if sel:
            self._cargar_tree_capacidades(int(sel[0]))

    def _cargar_tree_capacidades(self, comp_id: int) -> None:
        for item in self.tree_capacidades.get_children():
            self.tree_capacidades.delete(item)
        for idx, (_id, nom) in enumerate(obtener_capacidades_por_competencia(comp_id), start=1):
            self.tree_capacidades.insert("", "end", values=(idx, nom))

    def _obtener_comp_id_desde_texto(self, texto: str) -> Optional[int]:
        if not texto:
            return None
        if texto in getattr(self,'crear_comp_map',{}):return self.crear_comp_map[texto]
        for cid, nombre in self.competencias_curso_actual:
            if texto == nombre:
                return cid
        numero, separador, nombre = texto.partition(". ")
        if separador and numero.isdigit():
            for cid, candidato in self.competencias_curso_actual:
                if nombre == candidato:
                    return cid
        return None


    # ==========================================================================
    # ACCIONES PESTAÑA 1 Y PESTAÑA 2
    # ==========================================================================

    def _dialogo_nuevo_curso(self) -> None:
        if not self.licencia_permite(all_courses=True) or not self.verificar_permiso_edicion():
            return
        nom = simpledialog.askstring("Nuevo Curso", "Ingrese el nombre del Curso / Área Curricular:")
        if nom and nom.strip():
            crear_curso(nom.strip())
            self.combo_curso_global.set(nom.strip())
            self.recargar_cursos_y_contexto()

    def _toggle_curso_activo(self) -> None:
        if not self.dev_mode or not self.verificar_permiso_edicion(): return
        sel = self.tree_cursos.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un curso de la lista.")
            return
        cid = int(self.tree_cursos.item(sel[0], "values")[0])
        import db
        db.alternar_curso_activo(cid)
        self.recargar_cursos_y_contexto()

    def _eliminar_curso(self) -> None:
        if not self.dev_mode or not self.verificar_permiso_edicion(): return
        sel = self.tree_cursos.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un curso para eliminar.")
            return
        nom = self.tree_cursos.item(sel[0], "values")[1]
        if messagebox.askyesno("Confirmar", f"¿Seguro que desea eliminar el curso '{nom}' por completo?\nSe borrarán todas sus competencias y notas."):
            cid = int(self.tree_cursos.item(sel[0], "values")[0])
            import db
            db.eliminar_curso(cid)
            self.recargar_cursos_y_contexto()

    def _dialogo_nueva_competencia(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        cid = self.obtener_curso_activo_id()
        if cid:
            nom = simpledialog.askstring("Nueva Competencia", "Nombre de la Competencia:")
            if nom and nom.strip():
                crear_competencia(cid, nom.strip())
                self._al_cambiar_curso_global(self.combo_curso_global.get())

    def _dialogo_nueva_capacidad(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        sel = self.tree_competencias.selection()
        if sel:
            comp_id = int(sel[0])
            nom = simpledialog.askstring("Nueva Capacidad", "Nombre de la Capacidad:")
            if nom and nom.strip():
                crear_capacidad(comp_id, nom.strip())
                self._cargar_tree_capacidades(comp_id)
                self._al_cambiar_comp_en_creacion(self.crear_combo_comp.get())

    def recargar_tabla_estudiantes(self) -> None:
        for item in self.tree_estudiantes.get_children():
            self.tree_estudiantes.delete(item)
        estudiantes = obtener_estudiantes_filtrados(
            self.combo_grado_global.get(),
            self.combo_seccion_global.get(),
            self.entry_buscar_est.get(),
            bool(self.chk_ver_retirados.get()),
            orden_por=self.est_combo_orden.get(),
        )
        for e in estudiantes:
            self.tree_estudiantes.insert(
                "",
                "end",
                values=(
                    e["ID"],
                    e["Codigo_Unico"],
                    e["Apellidos"],
                    e["Nombres"],
                    e["Grado"],
                    e["Seccion"],
                    e["Estado"],
                ),
            )
        self.lbl_total_estudiantes.configure(text=f"{len(estudiantes)} estudiante(s)")

    def accion_importar_excel_estudiantes(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        ruta = filedialog.askopenfilename(filetypes=[("Archivos Excel", "*.xlsx")])
        if ruta:
            try:
                cant = self._importar_con_vista_previa(importar_estudiantes_desde_excel,
                    ruta, self.combo_grado_global.get(), self.combo_seccion_global.get()
                )
                if cant is None:
                    return
                self.recargar_cursos_y_contexto()
                messagebox.showinfo(
                    "Importación Exitosa",
                    f"Se importaron {cant} estudiante(s) con sus códigos de sección (ej. 4A01, 4A02).",
                )
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo importar el Excel:\n{e}")

    def accion_descargar_plantilla_excel(self) -> None:
        ruta = self.elegir_destino(
            defaultextension=".xlsx",
            initialfile="Plantilla_Estudiantes_Seccion.xlsx",
            filetypes=[("Archivo Excel", "*.xlsx")],
        )
        if ruta:
            generar_plantilla_excel_estudiantes(ruta)
            messagebox.showinfo("Plantilla lista", f"Guardada en:\n{ruta}")

    def accion_guardar_estudiante(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        ape = self.est_entry_apellidos.get().strip()
        nom = self.est_entry_nombres.get().strip()
        if not ape or not nom:
            messagebox.showwarning("Atención", "Ingrese apellidos y nombres.")
            return
        agregar_estudiante(
            nom,
            ape,
            self.est_entry_grado.get(),
            self.est_entry_seccion.get(),
            "",
            self.est_combo_estado.get(),
        )
        self._formularios_pendientes.discard(str(self.tab_estudiantes))
        self.est_entry_apellidos.delete(0, "end")
        self.est_entry_nombres.delete(0, "end")
        self.recargar_tabla_estudiantes()
        self.dibujar_planilla_calificacion(forzar=True)
        self.recargar_buscador_alumnos()
        self.recargar_matriz_completa()

    def _al_seleccionar_estudiante_tabla(self, _event: tk.Event) -> None:
        if str(self.tab_estudiantes) in self._formularios_pendientes and not self.confirmar_descartar():
            return
        sel = self.tree_estudiantes.selection()
        if sel:
            vals = self.tree_estudiantes.item(sel[0], "values")
            self.id_estudiante_sel = int(vals[0])
            self.est_entry_apellidos.delete(0, "end")
            self.est_entry_apellidos.insert(0, vals[2])
            self.est_entry_nombres.delete(0, "end")
            self.est_entry_nombres.insert(0, vals[3])
            self.est_entry_grado.set(vals[4])
            self.est_entry_seccion.set(vals[5])
            self.est_combo_estado.set(vals[6])
            self.btn_est_actualizar.configure(state="normal")
            self.btn_est_eliminar.configure(state="normal")

    def accion_actualizar_estudiante(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        if self.id_estudiante_sel is not None:
            actualizar_datos_estudiante(
                self.id_estudiante_sel,
                self.est_entry_nombres.get(),
                self.est_entry_apellidos.get(),
                self.est_entry_grado.get(),
                self.est_entry_seccion.get(),
                self.est_combo_estado.get(),
            )
            self._formularios_pendientes.discard(str(self.tab_estudiantes))
            self.recargar_tabla_estudiantes()
            self.dibujar_planilla_calificacion(forzar=True)
            self.recargar_buscador_alumnos()
            self.recargar_matriz_completa()

    def accion_eliminar_estudiante(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        if self.id_estudiante_sel is not None and messagebox.askyesno(
            "Confirmar Eliminación", "¿Está seguro de eliminar el registro de este estudiante?"
        ):
            eliminar_estudiante(self.id_estudiante_sel)
            self.id_estudiante_sel = None
            self.recargar_tabla_estudiantes()
            self.dibujar_planilla_calificacion(forzar=True)
            self.recargar_buscador_alumnos()
            self.recargar_matriz_completa()

    # ==========================================================================
    # ACCIONES PESTAÑA 3: CREAR ACTIVIDAD + PLANTILLA DE RÚBRICA / LISTA DE COTEJO
    # ==========================================================================

    def _al_cambiar_comp_en_creacion(self, texto_comp: str) -> None:
        if str(self.tab_crear) in getattr(self, "_formularios_pendientes", set()) and not self.confirmar_descartar():
            self.crear_combo_comp.set(getattr(self, "_comp_form_actual", texto_comp))
            return
        self._comp_form_actual = texto_comp
        for w in self.scroll_caps_creacion.winfo_children():
            w.destroy()
        self.widgets_caps_creacion.clear()

        comp_id = self._obtener_comp_id_desde_texto(texto_comp)
        if comp_id is None:
            return
        if hasattr(self,'lbl_comp_completa'):
            self.lbl_comp_completa.configure(text=next((name for cid,name in self.competencias_curso_actual if cid==comp_id),texto_comp))
        caps = obtener_capacidades_por_competencia(comp_id)
        for idx, (cap_id, cap_nom) in enumerate(caps, start=1):
            f_item = ctk.CTkFrame(self.scroll_caps_creacion, corner_radius=8)
            f_item.grid(row=idx - 1, column=0, padx=4, pady=5, sticky="ew")
            f_item.grid_columnconfigure(1, weight=1)

            chk = ctk.CTkCheckBox(f_item, text="", width=26)
            chk.select()
            chk.grid(row=0, column=0, padx=(8, 4), pady=(8, 2), sticky="nw")

            lbl_cap = ctk.CTkLabel(
                f_item,
                text=f"{idx}. {cap_nom}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#1e3a8a", "#93c5fd"),
                wraplength=480,
                justify="left",
                anchor="w",
            )
            lbl_cap.grid(row=0, column=1, padx=(2, 8), pady=(6, 2), sticky="ew")
            wrap_label(lbl_cap)

            txt_crit = TextBuffer()
            criterion=ctk.CTkButton(f_item,text="Criterio",width=70,height=26,fg_color="transparent",
                text_color=("#475569","#cbd5e1"),hover_color=("#e2e8f0","#334155"),
                command=lambda target=txt_crit,title=cap_nom:self.editar_texto_actividad(target,"Criterio · "+title))
            criterion.grid(row=1,column=1,sticky="w",padx=2,pady=(0,6))

            self.widgets_caps_creacion.append(
                {
                    "capacidad_id": cap_id,
                    "indice": idx,
                    "nombre": cap_nom,
                    "checkbox": chk,
                    "txt_criterio": txt_crit,
                }
            )

        self.mostrar_capacidades_actividad()

    def _extraer_peso_creacion(self) -> float:
        raw = self.crear_combo_peso.get().strip().split()[0].replace("x", "").replace("%", "")
        return valid_number(raw, 0.000001, 1000000, "Peso")

    def accion_importar_rubrica_cotejo_en_calificacion(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        if self.id_actividad_calificando is None:
            messagebox.showwarning("Sin actividad", "Seleccione primero una actividad arriba.")
            return
        self._subir_excel_instrumento_a_sesion(self.id_actividad_calificando)

    def _subir_excel_instrumento_a_sesion(self, sesion_id: int) -> None:
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo Excel de Lista de Cotejo o Rúbrica",
            filetypes=[("Archivos Excel", "*.xlsx")],
        )
        if not ruta:
            return
        try:
            resultado = self._importar_con_vista_previa(importar_rubrica_o_cotejo_desde_excel,
                sesion_id, ruta, self.combo_grado_global.get(), self.combo_seccion_global.get()
            )
            if resultado is None:
                return
            if hasattr(resultado,'session_id'):
                self._planilla_pendiente=False
                self.refrescar_curriculo_importado()
                self.recargar_tabla_actividades_creadas()
                self.abrir_actividad_en_pestana_calificar(resultado.session_id)
                self.recargar_buscador_alumnos();self.recargar_matriz_completa()
                messagebox.showinfo('Tabla importada',f'Se importaron {resultado[1]} estudiantes y {resultado[0]} criterios o capacidades. Se agregaron {len(resultado.changes)} elementos que faltaban.')
                return
            ind_cant, alum_cant = resultado
            inds = obtener_indicadores_instrumento_sesion(sesion_id)
            if inds and "Rúbrica" in inds[0]["tipo"]:
                self.calif_combo_modo_inst.set("Rúbrica")
            else:
                self.calif_combo_modo_inst.set("Lista de Cotejo")
            self.recargar_tabla_actividades_creadas()
            self.dibujar_planilla_calificacion(forzar=True)
            self.recargar_buscador_alumnos()
            self.recargar_matriz_completa()
            messagebox.showinfo(
                "Rúbrica / Lista de Cotejo Cargada",
                f"Se cargaron {ind_cant} indicador(es) de evaluación para esta clase"
                + (f" y las notas de {alum_cant} estudiante(s)." if alum_cant > 0 else ".")
                + "\n\nLas notas importadas ya están guardadas. Para evaluar aquí, pulse Evaluar estudiantes, aplique a la planilla y después Guardar notas.",
            )
        except Exception as e:
            messagebox.showerror("Error al cargar instrumento", f"Detalle: {e}")

    def accion_limpiar_formulario_actividad(self) -> None:
        if str(self.tab_crear) in getattr(self, "_formularios_pendientes", set()) and not self.confirmar_descartar():
            return
        self.id_actividad_editando = None
        self.lbl_modo_creacion.configure(text="Actividad")
        self.crear_entry_titulo.delete(0, "end")
        self.crear_txt_proposito.delete("1.0", "end")
        self.crear_ent_fecha.delete(0, "end")
        import datetime
        self.crear_ent_fecha.insert(0, datetime.date.today().isoformat())
        self.crear_combo_peso.set("1")
        self.crear_combo_metodo.set("Nota global")
        self.al_elegir_rubro_actividad(self.crear_combo_categoria.get())
        self.btn_actualizar_act.configure(state="disabled")
        if self.competencias_curso_actual:
            txt = next(iter(self.crear_comp_map))
            self.crear_combo_comp.set(txt)
            self._al_cambiar_comp_en_creacion(txt)

    def accion_guardar_nueva_actividad(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        self._guardar_actividad_comun(es_actualizacion=False)

    def accion_actualizar_actividad_existente(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        if self.id_actividad_editando is not None:
            self._guardar_actividad_comun(es_actualizacion=True)

    def _guardar_actividad_comun(self, es_actualizacion: bool) -> None:
        curso_id = self.obtener_curso_activo_id()
        comp_id = self._obtener_comp_id_desde_texto(self.crear_combo_comp.get())
        if not curso_id or not comp_id:
            return

        titulo = self.crear_entry_titulo.get().strip()
        if not titulo:
            messagebox.showwarning("Falta Título", "Ingrese el nombre o tema de la Clase, Examen, Trabajo o Práctica.")
            return

        caps_seleccionadas: List[Tuple[int, str]] = []
        for w in self.widgets_caps_creacion:
            if w["checkbox"].get() == 1:
                crit = w["txt_criterio"].get("1.0", "end").strip()
                caps_seleccionadas.append((w["capacidad_id"], crit))

        if not caps_seleccionadas:
            messagebox.showwarning("Capacidades", "Seleccione al menos una Capacidad para evaluar en esta actividad.")
            return

        sid = crear_o_actualizar_sesion_clase(
            sesion_id=self.id_actividad_editando if es_actualizacion else None,
            curso_id=curso_id,
            competencia_id=comp_id,
            grado=self.combo_grado_global.get(),
            seccion=self.combo_seccion_global.get(),
            titulo_tema=titulo,
            proposito=self.crear_txt_proposito.get("1.0", "end").strip(),
            peso_clase=self._extraer_peso_creacion(),
            capacidades_y_criterios=caps_seleccionadas,
            categoria=self.crear_combo_categoria.get(),
            fecha_str=self.crear_ent_fecha.get().strip() or None,
            tipo_actividad=self.crear_combo_tipo.get(),metodo=self.crear_combo_metodo.get(),
            unidad_id=getattr(self,'_unit_labels',{}).get(self.crear_combo_unidad.get(),0),
        )
        self._formularios_pendientes.discard(str(self.tab_crear))
        self.id_actividad_calificando = sid
        self.recargar_tabla_actividades_creadas()
        self.recargar_buscador_alumnos()
        self.cargar_lista_pesos_por_categoria_en_graficos()
        self.dibujar_graficos_estadisticos()
        self.accion_limpiar_formulario_actividad()

        if messagebox.askyesno(
            "Actividad Guardada",
            f"La actividad '{titulo}' se guardó correctamente.\n\n¿Desea ir ahora a la Calificaciones para ingresar las notas?",
        ):
            self.abrir_actividad_en_pestana_calificar(sid)

    def recargar_tabla_actividades_creadas(self) -> None:
        for item in self.tree_actividades.get_children():
            self.tree_actividades.delete(item)
        curso_id = self.obtener_curso_activo_id()
        if not curso_id:
            return
        cat_filtro = self.filtro_cat_creacion.get()
        todas_sesiones = [s for s in obtener_sesiones_clase(curso_id,self.combo_grado_global.get(),self.combo_seccion_global.get()) if not s.get('archivada')]
        all_sessions=todas_sesiones
        todas_sesiones=self.sesiones_unidad(todas_sesiones)
        sesiones=[s for s in todas_sesiones if cat_filtro=='Todas' or s['categoria']==cat_filtro]
        self.actividades_creadas_map={s['id']:s for s in all_sessions}
        names=activity_labels(todas_sesiones)
        self.combo_calif_etiqueta_a_id={names[s['id']]:s['id'] for s in todas_sesiones}
        opciones_combo_calif=list(self.combo_calif_etiqueta_a_id)

        for s in sesiones:
            if s.get("archivada"):continue
            caps_str = " • ".join(
                f"{c['capacidad_nombre']}" + (f" ({c['criterio_precisado']})" if c["criterio_precisado"] else "")
                for c in s["capacidades"]
            )
            self.tree_actividades.insert(
                "",
                "end",
                iid=str(s["id"]),
                values=(
                    s["id"],
                    s["categoria"],
                    f"{s['peso_clase']:.1f}x",
                    s["titulo_tema"],
                    s["competencia_nombre"],
                    caps_str,
                    "Nota global" if s.get("modo_ingreso")=="global" else s.get("tipo_instrumento", "Normal"),
                ),
            )

        self.calif_combo_actividad.configure(values=opciones_combo_calif)
        if opciones_combo_calif:
            etiqueta_elegir = opciones_combo_calif[-1]
            for et, sid in self.combo_calif_etiqueta_a_id.items():
                if sid == self.id_actividad_calificando:
                    etiqueta_elegir = et
                    break
            self.calif_combo_actividad.set(etiqueta_elegir)
            selected=self.combo_calif_etiqueta_a_id[etiqueta_elegir]
            caps=tuple(c['capacidad_id'] for c in self.actividades_creadas_map[selected]['capacidades'])
            previous=tuple(c['capacidad_id'] for c in getattr(self,'_capacidades_actividad',[]))
            context=getattr(self,'_table_context',None)
            expected=(selected,self.obtener_curso_activo_id(),self.combo_grado_global.get(),self.combo_seccion_global.get())
            if not context or context[:4]!=expected or caps!=previous:
                self._al_cambiar_actividad_en_calificar(etiqueta_elegir)
            else:self.actualizar_herramientas_evaluacion()
        else:
            self.calif_combo_actividad.set("No hay actividades creadas aún (Créelas en la Pestaña 3)")
            self.id_actividad_calificando = None
            self.dibujar_planilla_calificacion(forzar=True)

    def _al_seleccionar_actividad_en_tabla(self, _event: tk.Event) -> None:
        if str(self.tab_crear) in self._formularios_pendientes and not self.confirmar_descartar():
            return
        sel = self.tree_actividades.selection()
        if not sel:
            return
        sid = int(sel[0])
        s = self.actividades_creadas_map.get(sid)
        if not s:
            return

        self.id_actividad_editando = sid
        self.lbl_modo_creacion.configure(text="Editar actividad")
        self.crear_combo_categoria.set(s["categoria"])
        self.crear_combo_unidad.set(next((label for label,identity in getattr(self,"_unit_labels",{}).items() if identity==s.get("unidad_id")),"Sin unidad"))
        self.crear_combo_tipo.set(s.get("tipo_actividad","Actividad"))
        self.crear_combo_metodo.set(s["tipo_instrumento"] if s["tipo_instrumento"] in ("Rúbrica","Lista de Cotejo") else "Nota global" if s.get("modo_ingreso")=="global" else "Nota directa")
        self.crear_combo_peso.set(f"{s['peso_clase']:.1f}")
        self.crear_entry_titulo.delete(0, "end")
        self.crear_entry_titulo.insert(0, s["titulo_tema"])
        self.crear_txt_proposito.delete("1.0", "end")
        self.crear_txt_proposito.insert("1.0", s["proposito"] or "")
        self.crear_ent_fecha.delete(0, "end")
        self.crear_ent_fecha.insert(0, s.get("fecha", ""))

        for idx, (cid, cnom) in enumerate(self.competencias_curso_actual, start=1):
            if cid == s["competencia_id"]:
                txt = next((label for label,identity in self.crear_comp_map.items() if identity==cid),f"{idx}. {cnom}")
                self.crear_combo_comp.set(txt)
                self._al_cambiar_comp_en_creacion(txt)
                break

        caps_guardadas = {c["capacidad_id"]: c["criterio_precisado"] for c in s["capacidades"]}
        for w in self.widgets_caps_creacion:
            cid = w["capacidad_id"]
            w["txt_criterio"].delete("1.0", "end")
            if cid in caps_guardadas:
                w["checkbox"].select()
                w["txt_criterio"].insert("1.0", caps_guardadas[cid] or "")
            else:
                w["checkbox"].deselect()

        self.mostrar_capacidades_actividad()
        self.btn_actualizar_act.configure(state="normal")

    def accion_eliminar_actividad_seleccionada(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        sel = self.tree_actividades.selection()
        if not sel:
            messagebox.showinfo("Seleccione", "Seleccione una actividad de la tabla para eliminarla.")
            return
        sid = int(sel[0])
        if messagebox.askyesno("Confirmar Eliminación", "¿Eliminar esta actividad y sus calificaciones asociadas?"):
            eliminar_sesion_clase(sid)
            self.accion_limpiar_formulario_actividad()
            self.recargar_tabla_actividades_creadas()
            self.recargar_buscador_alumnos()
            self.cargar_lista_pesos_por_categoria_en_graficos()
            self.dibujar_graficos_estadisticos()
            self.recargar_matriz_completa()

    def accion_ir_a_calificar_seleccionada(self) -> None:
        sel = self.tree_actividades.selection()
        if not sel:
            messagebox.showinfo("Seleccione", "Haga clic en una actividad de la tabla para abrir sus notas.")
            return
        self.abrir_actividad_en_pestana_calificar(int(sel[0]))

    def abrir_actividad_en_pestana_calificar(self, sesion_id: int) -> None:
        if getattr(self, "_planilla_pendiente", False) and not self.confirmar_descartar():
            return
        if sesion_id not in getattr(self,"combo_calif_etiqueta_a_id",{}).values() and hasattr(self,"unit_filter"):
            self.unit_filter.set("Todas las unidades");self.recargar_tabla_actividades_creadas()
        self.id_actividad_calificando = sesion_id
        self.tabview.set("Ingresar Calificativos")
        for et, sid in getattr(self, "combo_calif_etiqueta_a_id", {}).items():
            if sid == sesion_id:
                self.calif_combo_actividad.set(et)
                self._al_cambiar_actividad_en_calificar(et)
                break

    # ==========================================================================
    # ACCIONES PESTAÑA 4: INGRESAR NOTAS (MODO NORMAL O CON LISTA DE COTEJO / RÚBRICA)
    # ==========================================================================

    def _al_cambiar_actividad_en_calificar(self, etiqueta: str) -> None:
        if getattr(self, "_planilla_pendiente", False) and not self.confirmar_descartar():
            for label, session in getattr(self, "combo_calif_etiqueta_a_id", {}).items():
                if session == self.id_actividad_calificando:
                    self.calif_combo_actividad.set(label)
                    break
            return
        sid = getattr(self, "combo_calif_etiqueta_a_id", {}).get(etiqueta)
        self.id_actividad_calificando = sid
        if sid and sid in getattr(self, "actividades_creadas_map", {}):
            act = self.actividades_creadas_map[sid]
            t_inst = act.get("tipo_instrumento", "Normal")
            if "Cotejo" in t_inst:
                self.calif_combo_modo_inst.set("Lista de Cotejo")
            elif "brica" in t_inst:
                self.calif_combo_modo_inst.set("Rúbrica")
            else:
                self.calif_combo_modo_inst.set("Nota global" if act.get("modo_ingreso")=="global" else "Nota directa")
        self.dibujar_planilla_calificacion(forzar=True)

    def dibujar_planilla_calificacion(self, forzar: bool = False) -> None:
        modo_str=self.calif_combo_modo_inst.get()
        orden_elegido=self.calif_combo_orden.get()
        estado_actual=(self.id_actividad_calificando,modo_str,orden_elegido)
        context=(self.id_actividad_calificando,self.obtener_curso_activo_id(),self.combo_grado_global.get(),self.combo_seccion_global.get(),orden_elegido)
        tree=getattr(self,'planilla_nativa',None)
        if not forzar and tree and tree.winfo_exists() and context==getattr(self,'_table_context',None):
            # Choosing the assessment tool must preserve edited grades and scroll position.
            self._ultimo_estado_planilla=estado_actual
            self.actualizar_herramientas_evaluacion()
            return
        if getattr(self,"_planilla_pendiente",False) and not self.confirmar_descartar():
            previous=getattr(self,"_ultimo_estado_planilla",None)
            if previous:
                self.calif_combo_modo_inst.set(previous[1]);self.calif_combo_orden.set(previous[2])
            return
        self._ultimo_estado_planilla=estado_actual
        self._table_context=context
        self._evaluation_view=None
        self._instrument_pending={};self._instrument_pending_session=self.id_actividad_calificando
        self._cotejo_pending_rule=None

        for w in self.f_tabla_planilla.winfo_children():
            w.destroy()
        self.planilla_nativa = None
        self.widgets_planilla_calificacion.clear()
        self._datos_estudiantes=[]
        self._loaded_instrument_kind=None;self._loaded_ind_count=0
        self.actualizar_herramientas_evaluacion()
        self.btn_evaluar.configure(state="disabled")
        self.caja_ref_rubrica.configure(state="normal");self.caja_ref_rubrica.delete("1.0","end");self.caja_ref_rubrica.configure(state="disabled")

        if self.id_actividad_calificando is None or self.id_actividad_calificando not in getattr(self, "actividades_creadas_map", {}):
            ctk.CTkLabel(self.f_tabla_planilla, text="📝 Primero cree una Clase, Examen, Trabajo o Práctica en la Pestaña 3 y selecciónela arriba.", font=ctk.CTkFont(size=13)).pack(padx=20, pady=30, anchor="w")
            self.calif_entry_peso.delete(0, "end")
            return

        act = self.actividades_creadas_map[self.id_actividad_calificando]
        self.calif_entry_peso.delete(0, "end")
        self.calif_entry_peso.insert(0, f"{act['peso_clase']:.1f}")

        usar_instrumento = "Cotejo" in modo_str or "Rúbrica" in modo_str

        indicadores_subidos = obtener_indicadores_instrumento_sesion(act["id"])
        self._loaded_instrument_kind=indicadores_subidos[0]["tipo"] if indicadores_subidos else None
        self._loaded_ind_count=len(indicadores_subidos)

        info_inst = f"   |   📌 Instrumento activo ({len(indicadores_subidos)} indicadores cargados)" if indicadores_subidos else ""
        self.lbl_detalle_actividad_calificar.configure(
            text=f"[{act['categoria'].upper()}] {act['titulo_tema']}     Competencia: {act['competencia_nombre']}{info_inst}\nPropósito: {act['proposito'] or 'No especificado'}"
        )

        if usar_instrumento and indicadores_subidos:
            txt_ref = ""
            for idx, ind in enumerate(indicadores_subidos, start=1):
                c_nom = ind.get('capacidad_nombre', f"Cap.{idx}")
                txt_ref += f"  ✔ {c_nom}:\n     {ind['indicador_texto'].replace(' | ', '   |   ')}\n\n"
            self.caja_ref_rubrica.configure(state="normal")
            self.caja_ref_rubrica.delete("0.0", "end")
            self.caja_ref_rubrica.insert("0.0", txt_ref.strip())
            self.caja_ref_rubrica.configure(state="disabled")
            # Reference is available in Detalles, without reducing the grade table.
        else:
            self.caja_ref_rubrica.grid_forget()

        grado = self.combo_grado_global.get()
        seccion = self.combo_seccion_global.get()
        estudiantes, asist_map, notas_map = obtener_estado_planilla_sesion(act["id"], grado, seccion, orden_por=orden_elegido)

        if not estudiantes:
            ctk.CTkLabel(self.f_tabla_planilla, text=f"⚠️ No hay estudiantes activos en {grado} '{seccion}'. Suba su Excel en la Pestaña 2.", font=ctk.CTkFont(size=13), text_color="#f59e0b").pack(padx=20, pady=24, anchor="w")
            return

        headers = ["ID", "Código", "Apellidos y Nombres", "Asistencia"]
        for idx_c, cap_info in enumerate(act["capacidades"], start=1):
            headers.append(f"Cap {idx_c}")
        headers.append("Comentario")
        
        self.f_tabla_planilla.grid_columnconfigure(0, weight=1)
        self.f_tabla_planilla.grid_rowconfigure(0, weight=1)
        
        tree,identity,pane=grade_panels(self.f_tabla_planilla,headers,PlanillaNativaTreeview)
        tree.set_grade_columns([f"Cap {i}" for i in range(1,len(act["capacidades"])+1)])
        tree.on_edit_complete=self.marcar_planilla_pendiente
        self.identidad_planilla=identity;self.planilla_nativa=tree;self._results_pane=pane
        self.restaurar_divisor("nombres_notas")
        tree.tag_configure("odd", background=getattr(self, "stripe_color", ""))
        
        tree.heading("ID", text="ID")
        tree.heading("Código", text="Código")
        tree.heading("Apellidos y Nombres", text="Apellidos y Nombres")
        tree.heading("Asistencia", text="Asist.")
        for idx_c, cap_inf in enumerate(act["capacidades"], start=1):
            from cotejo import capacity_label
            tree.heading(f"Cap {idx_c}", text=capacity_label(cap_inf['capacidad_nombre']))
            tree.full_headers=getattr(tree,"full_headers",{})
            tree.full_headers[f"Cap {idx_c}"]=cap_inf["capacidad_nombre"]
        tree.heading("Comentario", text="Comentario")
        
        tree.column("ID", width=0, stretch=False)
        tree.column("Código", width=round(80*pixel_scale(tree)), anchor="center", stretch=False)
        tree.column("Apellidos y Nombres", width=round(250*pixel_scale(tree)), anchor="w", stretch=False)
        tree.column("Asistencia", width=round(85*pixel_scale(tree)), anchor="center", stretch=False)
        for idx_c in range(1, len(act["capacidades"]) + 1):
            tree.column(f"Cap {idx_c}", width=round(230*pixel_scale(tree)), minwidth=round(150*pixel_scale(tree)), anchor="center", stretch=False)
        tree.column("Comentario", width=round(220*pixel_scale(tree)), anchor="w", stretch=False)
        
        for est in estudiantes:
            est_id = est["ID"]
            asist_val = "Sí (V)" if asist_map.get(est_id, (1, ""))[0] == 1 else "No (F)"
            comentario = asist_map.get(est_id, (1, ""))[1]
            row = [est_id, est["Codigo_Unico"], f"{est['Apellidos']}, {est['Nombres']}", asist_val]
            for cap_info in act["capacidades"]:
                nota = notas_map.get((est_id, cap_info["capacidad_id"]))
                if nota is not None:
                    row.append(str(nota).removesuffix(".0"))
                else:
                    row.append("")
            row.append(comentario.replace("\n", " ") if comentario else "")
            tags = ("odd",) if len(tree.get_children()) % 2 == 0 else ("even",)
            item=tree.insert("", "end", values=row, tags=tags)
            identity.insert("", "end", iid=item,values=(f'{len(tree.get_children()):02}',row[2]))

        self._undo=[];self._redo=[]
        self._datos_estudiantes = estudiantes
        self._capacidades_actividad = act["capacidades"]
        self.actualizar_herramientas_evaluacion()

    def _abrir_dialogo_masivo_desde_nativa(self, act, estudiantes, tipo_inst):
        if not self.verificar_permiso_edicion():
            return
        loaded=getattr(self,"_loaded_instrument_kind",None)
        if loaded and loaded!=tipo_inst:
            messagebox.showinfo("Instrumento diferente",f"Esta actividad tiene {loaded}. Importe un modelo de {tipo_inst} antes de evaluarla con esa opción.");return
        DialogoEvaluarInstrumentoMasivo(self, act, estudiantes, tipo_inst)

    def accion_marcar_asistencia_todos(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        self.recordar_planilla()
        self.marcar_planilla_pendiente()
        if not hasattr(self, 'planilla_nativa') or not self.planilla_nativa:
            return
            
        children = self.planilla_nativa.get_children()
        if not children: return
        
        all_yes = all("S" in str(self.planilla_nativa.item(child, "values")[3]) for child in children)
        new_val = "No (F)" if all_yes else "Sí (V)"
        
        for child in children:
            vals = list(self.planilla_nativa.item(child, "values"))
            vals[3] = new_val
            self.planilla_nativa.item(child, values=vals)

    def accion_guardar_planilla_calificacion_completa(self) -> None:
        global_panel=getattr(self,'_global_grade_panel',None)
        if global_panel and global_panel.winfo_exists() and global_panel.editor is not None:
            if not global_panel.commit():return
        embedded=getattr(self,'_embedded_evaluation',None)
        if embedded and embedded.winfo_exists() and embedded.matrix.editor is not None:
            embedded.matrix.commit_edit()
            if embedded.matrix.editor is not None:return
        if getattr(self.planilla_nativa,"_entry",None): self.planilla_nativa._entry.event_generate("<FocusOut>")
        if not self.verificar_permiso_edicion(): return
        if not self.planilla_nativa: return
        kind=self.calif_combo_modo_inst.get()
        if kind not in ('Nota directa','Nota global') and (getattr(self,'_loaded_instrument_kind',None)!=kind or not getattr(self,'_loaded_ind_count',0)):
            messagebox.showwarning('Configure la evaluación','Diseñe el instrumento seleccionado antes de guardar. También puede elegir Nota directa para ingresar las notas finales.')
            return
        
        try:
            nuevo_peso = float(self.calif_entry_peso.get().strip() or 1.0)
            nuevo_peso = valid_number(nuevo_peso, 0.000001, 1000000, "Peso")
        except:
            messagebox.showwarning("Peso inválido", "El peso debe ser > 0.")
            return

        rule=getattr(self,'_cotejo_pending_rule',None)
        if kind=='Lista de Cotejo' and rule:
            from cotejo import review_signature
            from evaluacion_datos import get_indicators,get_answers
            answers=get_answers(self.id_actividad_calificando,self._db_path)
            answers.update(getattr(self,'_instrument_pending',{}))
            signature=review_signature(get_indicators(self.id_actividad_calificando,self._db_path),answers)
            if rule.get('_respuestas')!=signature:
                messagebox.showwarning('Revisar conversión','Cambió las observaciones o los criterios después de convertir. Abra Convertir a nota y revise nuevamente antes de guardar.')
                return

        datos_guardar = []
        for item in self.planilla_nativa.get_children():
            row = self.planilla_nativa.item(item, "values")
            est_id = int(row[0])
            asistio = "S" in str(row[3]) or "V" in str(row[3])
            comentario = str(row[-1]).strip()
            
            notas_cap = {}
            for i, cap_info in enumerate(self._capacidades_actividad):
                val = str(row[4 + i]).split()[0] if str(row[4 + i]) else ""
                if val:
                    try:
                        nv = float(val)
                        if not (0.0 <= nv <= 20.0):
                            messagebox.showwarning("Error", f"La nota ({nv}) debe estar entre 0 y 20.")
                            return
                        notas_cap[cap_info["capacidad_id"]] = nv
                    except:
                        messagebox.showwarning("Error", f"Valor inválido '{val}'")
                        return
                else:
                    notas_cap[cap_info["capacidad_id"]] = None
                    
            datos_guardar.append({
                "estudiante_id": est_id,
                "asistio": asistio,
                "comentario": comentario,
                "notas_por_capacidad": notas_cap,
                "respuestas_instrumento": {identity:value for (student,identity),value in getattr(self,'_instrument_pending',{}).items() if student==est_id}
            })
            
        guardar_calificaciones_y_asistencia_sesion(self.id_actividad_calificando, datos_guardar, nuevo_peso=nuevo_peso,nuevo_instrumento=self.calif_combo_modo_inst.get(),regla_cotejo=getattr(self,'_cotejo_pending_rule',None))
        self._cotejo_pending_rule=None
        self._instrument_pending={};self._undo=[];self._redo=[]
        self.recargar_evaluacion_guardada()
        self._planilla_pendiente = False
        self._borrador_path().unlink(missing_ok=True)
        self.lbl_estado.configure(text="Observaciones del cotejo guardadas" if kind=='Lista de Cotejo' else "Notas, comentarios y asistencia guardados correctamente")
        self.recargar_tabla_actividades_creadas()
        self.recargar_buscador_alumnos()
        self.cargar_lista_pesos_por_categoria_en_graficos()
        self.dibujar_graficos_estadisticos()
        self.recargar_matriz_completa()
        messagebox.showinfo("Guardado Exitoso", "Se guardaron las observaciones del cotejo. Solo se aplican las notas cuya conversión confirmó." if kind=='Lista de Cotejo' else "Se guardaron todas las notas, comentarios, y asistencia.")

    def _al_seleccionar_fila_buscador(self, event) -> None:
        sel = self.tree_buscador_alumnos.selection()
        self.busc_txt_comentario_detalle.configure(state="normal")
        self.busc_txt_comentario_detalle.delete("1.0", "end")
        if sel:
            vals = self.tree_buscador_alumnos.item(sel[0], "values")
            if len(vals) > 6 and vals[6]:
                self.busc_txt_comentario_detalle.insert("1.0", vals[6])
            else:
                self.busc_txt_comentario_detalle.insert("1.0", "(No hay comentario registrado para esta sesión)")
        self.busc_txt_comentario_detalle.configure(state="disabled")

    @visible_when('Buscador')
    def recargar_buscador_alumnos(self) -> None:
        if not hasattr(self, "tree_buscador_alumnos"):
            return
        for item in self.tree_buscador_alumnos.get_children():
            self.tree_buscador_alumnos.delete(item)

        curso_id = self.obtener_curso_activo_id()
        if not curso_id:
            return

        alcance = self.busc_combo_alcance.get()
        grado = self.combo_grado_global.get() if alcance == "Salón Actual" else "Todos"
        seccion = self.combo_seccion_global.get() if alcance == "Salón Actual" else "Todas"

        comp_id_filtro = getattr(self, "busc_comp_map", {}).get(self.busc_combo_comp.get())
        cat_filtro = self.busc_combo_cat.get()

        filas_verticales = obtener_historial_vertical_estudiantes(
            curso_id=curso_id,
            grado=grado,
            seccion=seccion,
            busqueda_alumno=self.busc_entry_alumno.get(),
            competencia_id_filtro=comp_id_filtro,
            categoria_filtro=cat_filtro,
            orden_por=self.busc_combo_orden.get(),
        )

        sesiones = obtener_sesiones_clase(curso_id, grado, seccion)

        # Actualizar combo para elegir qué clase ir a editar
        opciones_editar = []
        self.busc_ir_clase_map: Dict[str, int] = {}
        from nombres_ui import activity_labels
        labels=activity_labels(sesiones)
        for s in sesiones:
            et=labels[s['id']]
            opciones_editar.append(et)
            self.busc_ir_clase_map[et] = s["id"]
        self.busc_combo_ir_clase.configure(
            values=opciones_editar if opciones_editar else ["Sin clases aún"]
        )
        if opciones_editar:
            self.busc_combo_ir_clase.set(opciones_editar[-1])

        cols = ["Fecha", "Alumno", "Actividad", "Competencia", "Notas", "Promedio", "Comentario"]
        headers_cfg: List[Tuple[str, str, int]] = [
            ("Fecha", "Fecha", 115),
            ("Alumno", "Alumno", 260),
            ("Actividad", "Actividad / Clase", 240),
            ("Competencia", "Competencia", 240),
            ("Notas", "Notas por Capacidad", 290),
            ("Promedio", "Promedio", 105),
            ("Comentario", "Comentario", 220),
        ]

        self.tree_buscador_alumnos.configure(columns=cols)
        for col_id, txt_h, ancho in headers_cfg:
            self.tree_buscador_alumnos.heading(col_id, text=txt_h)
            self.tree_buscador_alumnos.column(
                col_id,
                width=round(ancho*pixel_scale(self)),minwidth=round(ancho*pixel_scale(self)),stretch=col_id=='Comentario',
                anchor="w" if col_id in ("Alumno", "Actividad", "Comentario", "Competencia") else "center",
            )

        for f in filas_verticales:
            row_vals: List[Any] = [
                f["fecha"],
                f"[{f['codigo']}] {f['alumno_nombre']}",
                f["actividad"],
                f["competencia"],
                f["notas_str"],
                f["promedio"],
                f["comentario"]
            ]
            self.tree_buscador_alumnos.insert("", "end", values=row_vals)

    def accion_editar_clase_desde_buscador(self) -> None:
        et = self.busc_combo_ir_clase.get()
        sid = getattr(self, "busc_ir_clase_map", {}).get(et)
        if sid is not None:
            self.abrir_actividad_en_pestana_calificar(sid)
        elif self.id_actividad_calificando is not None:
            self.abrir_actividad_en_pestana_calificar(self.id_actividad_calificando)
        else:
            messagebox.showinfo("Atención", "Primero cree una actividad en la Pestaña 3.")
    def accion_descargar_reporte_estudiante(self) -> None:
        if not hasattr(self, "tree_buscador_alumnos"):
            return
        items = self.tree_buscador_alumnos.get_children()
        if not items:
            messagebox.showwarning("Sin datos", "No hay datos para exportar. Busque a un estudiante primero.")
            return
            
        ruta = self.elegir_destino(
            defaultextension=".xlsx",
            filetypes=[("Archivo Excel", "*.xlsx")],
            title="Exportar Reporte del Estudiante",
            initialfile="Reporte_Estudiante_Vertical.xlsx",
        )
        if not ruta:
            return
            
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Reporte_Estudiante"
        
        # Headers
        cols = [self.tree_buscador_alumnos.heading(c)["text"] for c in self.tree_buscador_alumnos["columns"]]
        ws.append(cols)
        
        for col_i in range(1, len(cols) + 1):
            cel = ws.cell(row=1, column=col_i)
            cel.font = Font(bold=True, color="FFFFFF")
            cel.fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
            cel.alignment = Alignment(horizontal="center")
            ws.column_dimensions[get_column_letter(col_i)].width = 25

        # Data
        for item in items:
            vals = self.tree_buscador_alumnos.item(item, "values")
            ws.append(vals)
            
        wb.save(ruta)
        messagebox.showinfo("Exportación Exitosa", f"El reporte vertical fue guardado en:\n{ruta}")

    # ==========================================================================
    # ACCIONES PESTAÑA 6: PORCENTAJES (%) + VER/MODIFICAR PESOS POR CATEGORÍA + GRÁFICOS
    # ==========================================================================

    @visible_when('Porcentajes de Actividades')
    def cargar_lista_pesos_por_categoria_en_graficos(
        self, categoria_seleccionada: str | None = None
    ) -> None:
        """
        Cuando el docente selecciona una categoría en la Pestaña 6 (ej. 'Exámenes', 'Trabajos', 'Clases' o 'Prácticas / Otros'),
        muestra todos los elementos creados en esa categoría y permite ver y modificar sus pesos ahí mismo.
        """
        if not hasattr(self, "scroll_pesos_categoria"):
            return
        for w in self.scroll_pesos_categoria.winfo_children():
            w.destroy()
        self.entries_pesos_individuales_cat.clear()

        curso_id = self.obtener_curso_activo_id()
        if not curso_id:
            return

        if categoria_seleccionada:
            self.graf_combo_categoria_pesos.set(categoria_seleccionada)
        cat_elegida = self.graf_combo_categoria_pesos.get()
        actividades = obtener_sesiones_clase(
            curso_id,
            self.combo_grado_global.get(),
            self.combo_seccion_global.get(),
            None,
            cat_elegida,
        )

        if not actividades:
            ctk.CTkLabel(
                self.scroll_pesos_categoria,
                text=f"No hay actividades registradas en '{cat_elegida}'.\nPuede crearlas en la Pestaña 3.",
                font=ctk.CTkFont(size=12),
            ).grid(row=0, column=0, padx=10, pady=16, sticky="w")
            return

        for idx, act in enumerate(actividades):
            f_row = ctk.CTkFrame(self.scroll_pesos_categoria, corner_radius=6)
            f_row.grid(row=idx, column=0, padx=4, pady=4, sticky="ew")
            f_row.grid_columnconfigure(0, weight=1)

            activity_label=ctk.CTkLabel(
                f_row,
                text=f"{act['titulo_tema']}\n({act['competencia_nombre']})",
                font=ctk.CTkFont(size=11, weight="bold"),
                justify="left",
                anchor="w",
            )
            activity_label.grid(row=0, column=0, columnspan=3, padx=8, pady=6, sticky="ew")
            wrap_label(activity_label)

            ctk.CTkLabel(f_row, text="Peso:", font=ctk.CTkFont(size=11)).grid(
                row=1, column=1, padx=(4, 2), pady=6
            )
            ent_p = ctk.CTkEntry(f_row, width=68, justify="center")
            ent_p.insert(0, f"{act['peso_clase']:.1f}")
            ent_p.grid(row=1, column=2, padx=(0, 8), pady=6)

            self.entries_pesos_individuales_cat.append((act["id"], ent_p))

    def accion_guardar_pesos_individuales_categoria(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        if not self.entries_pesos_individuales_cat:
            return

        try:
            changes = [(sid, valid_number(ent.get().strip(), 0.000001, 1000000, "Peso"))
                       for sid, ent in self.entries_pesos_individuales_cat]
            actualizar_pesos_actividades(changes)
            self._formularios_pendientes.discard(str(self.tab_graficos))
        except ValueError as exc:
            messagebox.showwarning("Peso inválido", str(exc))
            return

        self.recargar_tabla_actividades_creadas()
        self.recargar_buscador_alumnos()
        self.dibujar_graficos_estadisticos()
        self.recargar_matriz_completa()
        messagebox.showinfo(
            "Pesos Actualizados",
            f"Se actualizaron correctamente los pesos individuales de '{self.graf_combo_categoria_pesos.get()}'.",
        )

    def accion_guardar_porcentajes_rubros(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        curso_id = self.obtener_curso_activo_id()
        if not curso_id:
            return
        try:
            p_clases = float(self.entries_pct_rubros["Clases"].get().strip() or 0)
            p_exam = float(self.entries_pct_rubros["Exámenes"].get().strip() or 0)
            p_trab = float(self.entries_pct_rubros["Trabajos"].get().strip() or 0)
            p_prac = float(self.entries_pct_rubros["Prácticas / Otros"].get().strip() or 0)
        except ValueError:
            messagebox.showwarning("Valores inválidos", "Los porcentajes deben ser valores numéricos.")
            return

        try:
            guardar_pesos_rubros_curso(curso_id, p_clases, p_exam, p_trab, p_prac)
        except ValueError as exc:
            messagebox.showwarning("Porcentajes inválidos", str(exc))
            return
        self._formularios_pendientes.discard(str(self.tab_graficos))
        self.dibujar_graficos_estadisticos()
        self.recargar_matriz_completa()
        suma = p_clases + p_exam + p_trab + p_prac
        messagebox.showinfo(
            "Porcentajes Guardados",
            f"Se actualizaron los porcentajes de evaluación (Suma total: {suma:.1f}%).",
        )

    @visible_when('Porcentajes de Actividades')
    def dibujar_graficos_estadisticos(self) -> None:
        if not hasattr(self, "graficos_hosts"):
            return
        course = self.obtener_curso_activo_id()
        if not course:
            return
        from graficos import category_figure, frequency_figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        weights = obtener_pesos_rubros_curso(course)
        comps, caps = obtener_estadisticas_frecuencia_evaluacion(course, self.combo_grado_global.get(), self.combo_seccion_global.get())
        state=(course,self.combo_grado_global.get(),self.combo_seccion_global.get(),tuple(weights.items()),tuple(comps),tuple(caps),pixel_scale(self))
        if getattr(self,"_graph_state",None)==state:return
        self._graph_state=state
        self._plot_data=(weights,comps,caps)
        self._plot_widths={}
        for fig in getattr(self,"figuras_porcentajes",[]):fig.clear()
        self.figuras_porcentajes = [category_figure(weights), frequency_figure(comps, "Actividades por competencia"), frequency_figure([(name, count) for name,count,_ in caps], "Actividades por capacidad")]
        for host in self.graficos_hosts:
            for child in host.winfo_children():child.destroy()
        self._render_current_plot()

    def _programar_grafico(self,index):
        if getattr(self,"_closing_ui",False) or not getattr(self,"_plot_data",None):return
        current=("Ponderaciones","Competencias","Capacidades").index(self.graficos_tabs.get())
        if index!=current:return
        width=max(480,self.graficos_hosts[index].winfo_width()/pixel_scale(self))
        if abs(width-getattr(self,"_plot_widths",{}).get(index,0))<45:return
        pending=getattr(self,"_plot_resize_job",None)
        if pending:self.after_cancel(pending)
        self._plot_resize_job=self.after(180,lambda:self._render_current_plot(resize=True))

    def _render_current_plot(self,resize=False):
        if not getattr(self,"figuras_porcentajes",[]) or not getattr(self,"_plot_data",None):return
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from graficos import category_figure,frequency_figure
        index=("Ponderaciones","Competencias","Capacidades").index(self.graficos_tabs.get())
        host=self.graficos_hosts[index]
        width=max(480,host.winfo_width()/pixel_scale(self))
        if host.winfo_children() and not resize:return
        for child in host.winfo_children():child.destroy()
        weights,comps,caps=self._plot_data
        if index==0:figure=category_figure(weights,width)
        elif index==1:figure=frequency_figure(comps,"Actividades por competencia",width)
        else:figure=frequency_figure([(name,count) for name,count,_ in caps],"Actividades por capacidad",width)
        self.figuras_porcentajes[index].clear();self.figuras_porcentajes[index]=figure
        self._plot_widths[index]=width
        figure.set_dpi(100*pixel_scale(self))
        canvas=FigureCanvasTkAgg(figure,master=host)
        canvas.draw();canvas.get_tk_widget().pack(fill="x",expand=False)


    # ==========================================================================
    # ACCIONES PESTAÑA 7: MATRIZ GENERAL + EXPORTAR E IMPORTAR EXCEL
    # ==========================================================================

    @visible_when('Matriz General')
    def recargar_matriz_completa(self) -> None:
        curso_id = self.obtener_curso_activo_id()
        if not curso_id:
            return
        grado = self.combo_grado_global.get()
        seccion = self.combo_seccion_global.get()
        orden = self.matriz_combo_orden.get() if hasattr(self, "matriz_combo_orden") else "Apellidos (A-Z)"

        estructura_comp, filas_matriz = calcular_matriz_competencias_y_capacidades(
            curso_id, grado, seccion, orden_por=orden
        )
        self.datos_matriz_actual = (estructura_comp, filas_matriz)

        cols = ["ID", "Codigo", "Estado", "Estudiante"]
        encabezados_cfg: List[Tuple[str, str, int]] = [
            ("ID", "ID", 42),
            ("Codigo", "N°", 38),
            ("Estado", "Estado", 80),
            ("Estudiante", "Apellidos y Nombres", 220),
        ]

        self.mapa_opciones_capacidades_manual: List[Tuple[int, str]] = []
        for comp in estructura_comp:
            c_idx = comp["indice"]
            for cap in comp["capacidades"]:
                cap_idx = cap["indice_cap"]
                col_id = f"C{c_idx}_Cap{cap_idx}"
                cols.append(col_id)
                encabezados_cfg.append(
                    (col_id, f"[C{c_idx}] {cap['capacidad_nombre'].split()[0]}", 115)
                )
                self.mapa_opciones_capacidades_manual.append(
                    (cap["capacidad_id"], f"C{c_idx}.Cap{cap_idx} - {cap['capacidad_nombre']}")
                )
            col_prom_c = f"PROM_C{c_idx}"
            cols.append(col_prom_c)
            encabezados_cfg.append((col_prom_c, f"★ PROM. C{c_idx}", 105))

        cols.extend(["PROM_FINAL", "LOGRO", "ALERTA"])
        encabezados_cfg.extend(
            [
                ("PROM_FINAL", "PROMEDIO CURSO", 120),
                ("LOGRO", "LOGRO", 70),
                ("ALERTA", "Estado Capacidades", 150),
            ]
        )

        self.tree_matriz.set_grade_columns([c for c in cols if "_Cap" in c or c.startswith("PROM")])
        self.tree_matriz.configure(columns=cols,displaycolumns=[c for c in cols if c not in ("ID","Estado")])
        for col_id, texto_h, ancho in encabezados_cfg:
            self.tree_matriz.heading(col_id, text=texto_h)
            self.tree_matriz.column(
                col_id,
                width=ancho,
                anchor="w" if col_id == "Estudiante" else "center",
                stretch=False,
            )

        for item in self.tree_matriz.get_children():
            self.tree_matriz.delete(item)

        for row_number,f in enumerate(filas_matriz,1):
            row_vals: List[Any] = [
                f["estudiante_id"],
                f'{row_number:02}',
                f["estado"],
                f"{f['apellidos']}, {f['nombres']}",
            ]
            for comp in estructura_comp:
                cid = comp["competencia_id"]
                for cap in comp["capacidades"]:
                    cap_id = cap["capacidad_id"]
                    val_cap = f["notas_capacidad"].get(cap_id)
                    es_man = f["es_manual_cap"].get(cap_id, False)
                    if val_cap is None:
                        row_vals.append("⚠️ FALTA")
                    else:
                        marca = " ✎" if es_man else ""
                        row_vals.append(f"{val_cap:.2f}{marca}")
                val_comp = f["notas_competencia"].get(cid)
                row_vals.append(f"{val_comp:.2f} ({nota_a_literal(val_comp)})" if val_comp is not None else "-")

            alerta_txt = (
                "✅ Completo"
                if f["faltan_capacidades"] == 0
                else f"⚠️ Faltan {f['faltan_capacidades']} cap."
            )
            row_vals.extend(
                [
                    f"{f['promedio_general']:.2f}" if f["promedio_general"] is not None else "-",
                    f["literal_general"],
                    alerta_txt,
                ]
            )
            tags = ("odd",) if len(self.tree_matriz.get_children()) % 2 == 0 else ("even",)
            self.tree_matriz.insert("", "end", values=row_vals, tags=tags)

    def accion_colocar_nota_manual_capacidad(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        sel = self.tree_matriz.selection()
        if not sel:
            messagebox.showwarning(
                "Seleccione un estudiante",
                "Haga clic primero en un estudiante dentro de la Tabla Matriz.",
            )
            return

        vals = self.tree_matriz.item(sel[0], "values")
        est_id = int(vals[0])
        nom_est = f"{vals[1]} - {vals[3]}"

        if not self.mapa_opciones_capacidades_manual:
            return

        menu_txt = "\n".join(
            f"{idx+1} = {etiqueta}"
            for idx, (_cap_id, etiqueta) in enumerate(self.mapa_opciones_capacidades_manual)
        )
        num_str = simpledialog.askstring(
            "Elegir Capacidad",
            f"Estudiante: {nom_est}\n\nIndique el número de la Capacidad a completar o modificar manualmente:\n\n{menu_txt}",
            initialvalue="1",
        )
        if not num_str:
            return
        try:
            idx_elegido = int(num_str.strip()) - 1
            cap_id, cap_etiqueta = self.mapa_opciones_capacidades_manual[idx_elegido]
        except Exception:
            messagebox.showwarning("Opción inválida", "Número de capacidad no válido.")
            return

        nota_str = simpledialog.askstring(
            "Ingresar Nota Manual",
            f"Estudiante: {nom_est}\nCapacidad: {cap_etiqueta}\n\n"
            "Ingrese la nota (0 a 20) o deje vacío para restaurar el cálculo automático:",
        )
        if nota_str is None:
            return

        if nota_str.strip() == "":
            guardar_nota_manual_capacidad(est_id, cap_id, None)
        else:
            try:
                nv = float(nota_str.strip())
                if not (0.0 <= nv <= 20.0):
                    raise ValueError
                guardar_nota_manual_capacidad(est_id, cap_id, nv)
            except ValueError:
                messagebox.showwarning("Nota inválida", "Ingrese un valor numérico entre 0 y 20.")
                return

        self.recargar_matriz_completa()

    def accion_exportar_matriz_excel(self) -> None:
        if not hasattr(self, "datos_matriz_actual"):
            return
        estructura_comp, filas_matriz = self.datos_matriz_actual
        curso = self.combo_curso_global.get()
        grado = self.combo_grado_global.get()
        seccion = self.combo_seccion_global.get()

        from excel_dialogs import GradeDisplayOptions
        options=GradeDisplayOptions(self);self.wait_window(options)
        if options.result is None:return
        ruta = self.elegir_destino(
            title="Exportar matriz final a Excel",
            defaultextension=".xlsx",
            initialfile=f"Registro_Detallado_{curso}_{grado}_{seccion}.xlsx",
            filetypes=[("Archivo Excel", "*.xlsx")],
        )
        if not ruta:
            return

        exportar_matriz_completa_excel(ruta, curso, grado, seccion, estructura_comp, filas_matriz,presentacion=options.result,db_path=self._db_path)
        import reportes
        reportes.decorate_workbook(ruta, self.insignia_exportacion())
        messagebox.showinfo(
            "Excel con Colores Exportado",
            f"Se exportó la matriz con N°, nombres y el formato elegido de notas:\n{ruta}",
        )

    def accion_importar_matriz_excel_con_notas(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        ruta = filedialog.askopenfilename(
            title="Seleccionar el archivo Excel con Notas de Estudiantes",
            filetypes=[("Archivos Excel", "*.xlsx")],
        )
        if not ruta:
            return
        try:
            resultado = self._importar_con_vista_previa(importar_matriz_notas_desde_excel,
                ruta, self.combo_grado_global.get(), self.combo_seccion_global.get()
            )
            if resultado is None:
                return
            est_proc, notas_proc = resultado
            self.recargar_cursos_y_contexto()
            messagebox.showinfo(
                "Excel con Notas Cargado",
                f"Se procesaron {est_proc} estudiante(s) y se cargaron/actualizaron {notas_proc} calificaciones por capacidad.",
            )
        except Exception as e:
            messagebox.showerror("Error al cargar Excel", f"Detalle: {e}")


def main() -> None:
    import json
    from db import DB_PATH
    app_storage.configure_logging()
    try:
        app_storage.prepare_storage(DB_PATH,backup=False)
        inicializar_db()
    except Exception as exc:
        logging.getLogger("registro").exception("Error al preparar la base de datos")
        root=tk.Tk();root.withdraw()
        select=messagebox.askyesno("Abrir base de calificativos", f"No se pudo abrir la base seleccionada. Sus archivos se conservan.\n\n{exc}\n\n¿Desea seleccionar otra base .db o documento .registro?")
        if select:
            selected=filedialog.askopenfilename(filetypes=[("Datos de Registro", "*.db *.registro")])
            if selected:
                try:
                    import time, os, subprocess, sys, documento
                    target=app_storage.data_dir()/f"recuperado-{time.time_ns()}.db"
                    if selected.endswith(".registro"):documento.open_document(selected,target)
                    else:
                        app_storage.validate_database(selected,current=False)
                        app_storage.copy_database(selected,target)
                    args=[sys.executable] if getattr(sys,"frozen",False) else [sys.executable,str(Path(__file__))]
                    subprocess.Popen(args,env={**os.environ,"REGISTRO_DB_PATH":str(target)})
                except Exception as recovery_error:
                    messagebox.showerror("Recuperación",str(recovery_error))
        root.destroy()
        return
    from licencias import OfflineLicensing
    from db_safety import set_license_policy
    commercial=commercial_edition()
    licensing=None;license_error=""
    if commercial:
        try:
            licensing=OfflineLicensing(app_storage.data_dir(),license_public_key())
        except Exception as exc:
            license_error=str(exc)
    set_license_policy(licensing,required=commercial)
    app = VentanaPrincipal(licensing,license_required=commercial,license_error=license_error)
    if commercial and (not licensing or not licensing.state):
        app.after(300, app.mostrar_licencia)
    elif not commercial and obtener_docente_config().get("requiere_cambio_clave"):
        app.after(300,lambda:DialogoPerfilDocente(app))
    app.mainloop()


if __name__ == "__main__":
    main()
