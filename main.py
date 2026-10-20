import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Dict, List, Optional, Tuple
import customtkinter as ctk
import tksheet

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
        "bg_main": "#e5e7eb",
        "bg_card": "#ffffff",
        "fg_text": "#111827",
        "tree_bg": "#ffffff",
        "tree_fg": "#1f2937",
        "tree_head_bg": "#374151",
        "tree_head_fg": "#f9fafb",
        "tree_sel": "#4b5563",
        "accent": "#2563eb",
    },
    "Claro Institucional": {
        "appearance": "Light",
        "bg_main": "#f1f5f9",
        "bg_card": "#ffffff",
        "fg_text": "#0f172a",
        "tree_bg": "#ffffff",
        "tree_fg": "#0f172a",
        "tree_head_bg": "#1e3a8a",
        "tree_head_fg": "#ffffff",
        "tree_sel": "#2563eb",
        "accent": "#1d4ed8",
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


class DialogoPerfilDocente(ctk.CTkToplevel):
    def __init__(self, master: "VentanaPrincipal") -> None:
        super().__init__(master)
        self.app = master
        self.title("Datos Generales del Docente y Configuración del Candado")
        self.geometry("460x440")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        cfg = obtener_docente_config()

        ctk.CTkLabel(
            self,
            text="👤 Perfil del Docente y Usuario de Seguridad",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(padx=20, pady=(16, 4), anchor="w")

        ctk.CTkLabel(
            self,
            text="Configure sus datos generales y el usuario/contraseña para desbloquear el candado de edición:",
            font=ctk.CTkFont(size=11),
            text_color=("gray35", "gray75"),
            wraplength=420,
            justify="left",
        ).pack(padx=20, pady=(0, 10), anchor="w")

        ctk.CTkLabel(self, text="Nombres y Apellidos del Docente:", font=ctk.CTkFont(weight="bold")).pack(
            padx=20, pady=(2, 1), anchor="w"
        )
        self.ent_nombres = ctk.CTkEntry(self)
        self.ent_nombres.insert(0, cfg["nombres_docente"])
        self.ent_nombres.pack(padx=20, pady=(0, 8), fill="x")

        ctk.CTkLabel(self, text="Institución Educativa / Colegio:", font=ctk.CTkFont(weight="bold")).pack(
            padx=20, pady=(2, 1), anchor="w"
        )
        self.ent_institucion = ctk.CTkEntry(self)
        self.ent_institucion.insert(0, cfg["institucion"])
        self.ent_institucion.pack(padx=20, pady=(0, 8), fill="x")

        ctk.CTkLabel(self, text="Especialidad / Nivel:", font=ctk.CTkFont(weight="bold")).pack(
            padx=20, pady=(2, 1), anchor="w"
        )
        self.ent_esp = ctk.CTkEntry(self)
        self.ent_esp.insert(0, cfg["especialidad"])
        self.ent_esp.pack(padx=20, pady=(0, 8), fill="x")

        f_cred = ctk.CTkFrame(self, fg_color="transparent")
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
        self.ent_clave = ctk.CTkEntry(f_cred)
        self.ent_clave.insert(0, cfg["clave"])
        self.ent_clave.grid(row=1, column=1, padx=(6, 0), sticky="ew")

        ctk.CTkButton(
            self,
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
        clv = self.ent_clave.get().strip() or "1234"

        guardar_docente_config(nom, inst, esp, usr, clv)
        self.app.edicion_desbloqueada = True
        self.app.actualizar_visual_candado_y_docente()
        messagebox.showinfo("Perfil Guardado", f"Datos actualizados.\nUsuario activo: {usr}")
        self.destroy()


class DialogoDesbloquearCandado(ctk.CTkToplevel):
    def __init__(self, master: "VentanaPrincipal") -> None:
        super().__init__(master)
        self.app = master
        self.title("🔓 Desbloquear Edición")
        self.geometry("380x260")
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
        self.ent_usr.insert(0, cfg["usuario"])
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
        if verificar_credenciales_docente(self.ent_usr.get(), self.ent_clv.get()):
            self.app.edicion_desbloqueada = True
            self.app.actualizar_visual_candado_y_docente()
            self.destroy()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos.")


class DialogoEditarInstrumento(ctk.CTkToplevel):
    def __init__(self, master, sesion_id, indicadores, callback):
        super().__init__(master)
        self.title("✏️ Editar Criterios de Evaluación")
        self.geometry("900x500")
        self.transient(master)
        self.grab_set()
        
        self.sesion_id = sesion_id
        self.indicadores = indicadores
        self.callback = callback
        
        f = ctk.CTkScrollableFrame(self)
        f.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.entries = []
        for i, ind in enumerate(self.indicadores):
            cap_nom = ind.get('capacidad_nombre', f"Capacidad {ind['capacidad_id']}")
            ctk.CTkLabel(f, text=cap_nom, font=ctk.CTkFont(weight="bold")).grid(row=i*2, column=0, sticky="w", pady=(10, 0))
            ent = ctk.CTkEntry(f, width=800)
            ent.insert(0, ind['indicador_texto'])
            ent.grid(row=i*2+1, column=0, pady=5)
            self.entries.append((ind, ent))
            
        btn = ctk.CTkButton(self, text="💾 Guardar Cambios", command=self.guardar)
        btn.pack(pady=10)
        
    def guardar(self):
        nuevos = []
        tipo = self.indicadores[0]['tipo'] if self.indicadores else 'Lista de Cotejo'
        for ind, ent in self.entries:
            nuevos.append((ind['capacidad_id'], ent.get(), ind['puntaje_maximo']))
        from db import guardar_indicadores_instrumento_sesion
        guardar_indicadores_instrumento_sesion(self.sesion_id, tipo, nuevos)
        self.callback()
        self.destroy()

class DialogoEvaluarInstrumentoMasivo(ctk.CTkToplevel):
    def __init__(
        self,
        master: "VentanaPrincipal",
        sesion_info: Dict[str, Any],
        filas_estudiantes: List[Dict[str, Any]],
        tipo_inst: str
    ) -> None:
        super().__init__(master)
        self.app = master
        self.sesion = sesion_info
        self.filas_estudiantes = filas_estudiantes
        self.tipo_inst = tipo_inst

        self.title(f"📋 Evaluación Masiva — {tipo_inst}")
        self.geometry("1200x700")
        self.transient(master)
        self.grab_set()

        self.indicadores_db = obtener_indicadores_instrumento_sesion(self.sesion["id"])
        if not self.indicadores_db:
            sugeridos: List[Tuple[int, str, float]] = []
            for c in self.sesion["capacidades"]:
                crit = c["criterio_precisado"] or f"Desempeño en {c['capacidad_nombre']}"
                sugeridos.append((c["capacidad_id"], f"{crit}", 10.0))
            guardar_indicadores_instrumento_sesion(self.sesion["id"], tipo_inst, sugeridos)
            self.indicadores_db = obtener_indicadores_instrumento_sesion(self.sesion["id"])

        ctk.CTkLabel(
            self,
            text=f"📋 Evaluación {tipo_inst}: {self.sesion['titulo_tema']}",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(padx=16, pady=(12, 2), anchor="w")

        f_matriz = ctk.CTkScrollableFrame(self, corner_radius=8)
        f_matriz.pack(padx=16, pady=6, fill="both", expand=True)

        ctk.CTkLabel(f_matriz, text="Estudiante", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=5)
        for col, ind in enumerate(self.indicadores_db, start=1):
            c_nom_corto = ind.get('capacidad_nombre', 'Cap').split()[0]
            if "brica" in tipo_inst:
                txt_mostrar = f"[{c_nom_corto}]\n{ind['indicador_texto'].replace(' | ', '  |  ')}"
                ancho_wrap = 350
            else:
                txt_mostrar = f"[{c_nom_corto}]\n{ind['indicador_texto']}"
                ancho_wrap = 200
                
            ctk.CTkLabel(
                f_matriz, 
                text=txt_mostrar, 
                font=ctk.CTkFont(size=11, weight="bold"),
                wraplength=ancho_wrap,
                justify="center"
            ).grid(row=0, column=col, padx=8, pady=5)

        self.controles = {}
        for row, fila_est in enumerate(self.filas_estudiantes, start=1):
            est_id = fila_est.get("ID") or fila_est.get("id_db") or fila_est.get("estudiante_id")
            
            if "Apellidos" in fila_est and "Nombres" in fila_est:
                nombre = f"{fila_est['Apellidos']}, {fila_est['Nombres']}"
            else:
                nombre = fila_est.get("nombre", "")
                
            ctk.CTkLabel(f_matriz, text=nombre[:25]).grid(row=row, column=0, sticky="w", padx=5)
            
            self.controles[est_id] = []
            for col, ind in enumerate(self.indicadores_db, start=1):
                if "brica" in tipo_inst:
                    ent = ctk.CTkEntry(f_matriz, width=60, justify="center")
                    ent.grid(row=row, column=col, padx=5, pady=2)
                    self.controles[est_id].append({"cap_id": ind["capacidad_id"], "ent": ent, "tipo": "R"})
                else:
                    cmb = ctk.CTkComboBox(f_matriz, values=["Sobresale (18)", "Logra (15)", "Proceso (12)", "No logra (08)", "No hace (05)"], width=130)
                    cmb.set("Logra (15)")
                    cmb.grid(row=row, column=col, padx=5, pady=2)
                    
                    def bind_key(c=cmb):
                        def _on_k(e):
                            char = e.char.lower() if e.char else ""
                            if char == 's': c.set("Sobresale (18)"); return "break"
                            elif char == 'l': c.set("Logra (15)"); return "break"
                            elif char == 'p': c.set("Proceso (12)"); return "break"
                            elif char == 'n': c.set("No logra (08)"); return "break"
                        if hasattr(c, "_entry"):
                            c._entry.bind("<KeyPress>", _on_k)
                            c._entry.bind("<KeyRelease>", _on_k)
                    bind_key()
                    self.controles[est_id].append({"cap_id": ind["capacidad_id"], "cmb": cmb, "tipo": "C"})

        f_bot = ctk.CTkFrame(self, fg_color="transparent")
        f_bot.pack(padx=16, pady=10, fill="x")
        
        ctk.CTkButton(f_bot, text="✏️ Editar Criterios (Rubrica/Cotejo)", fg_color="#ea580c", hover_color="#c2410c", command=self.abrir_editor).pack(side="left", padx=5)

        ctk.CTkButton(
            f_bot,
            text="✅ Calcular Notas y Pasar a Planilla",
            fg_color="#15803d",
            hover_color="#166534",
            font=ctk.CTkFont(weight="bold"),
            command=self._aplicar_calculo,
        ).pack(side="right", padx=4)

    def _aplicar_calculo(self) -> None:
        for fila_est in self.filas_estudiantes:
            est_id = fila_est.get("id_db") or fila_est.get("estudiante_id")
            conts = self.controles.get(est_id, [])
            notas_cap = {}
            for c in conts:
                if c["tipo"] == "R":
                    try:
                        val = float(c["ent"].get().strip())
                    except ValueError:
                        val = 0.0
                else:
                    v = c["cmb"].get()
                    if "18" in v: val = 18.0
                    elif "15" in v: val = 15.0
                    elif "12" in v: val = 12.0
                    elif "08" in v: val = 8.0
                    else: val = 5.0
                notas_cap.setdefault(c["cap_id"], []).append(val)
                
            for cap_id, lista in notas_cap.items():
                if self.tipo_inst == "Rúbrica":
                    prom_cap = round(sum(lista), 1)
                    if prom_cap > 20: prom_cap = 20.0
                else:
                    if lista: prom_cap = round(sum(lista)/len(lista), 1)
                    else: prom_cap = 0.0
                ent = fila_est["entries_capacidad"].get(cap_id)
                if ent is not None:
                    ent.delete(0, "end")
                    ent.insert(0, f"{prom_cap:.1f}".rstrip("0").rstrip("."))
                    ent.event_generate("<KeyRelease>")

        self.destroy()



class PlanillaNativaTreeview(ttk.Treeview):
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
        item = self.identify_row(event.y)
        column = self.identify_column(event.x)
        if not item or not column:
            return

        col_index = int(column[1:]) - 1
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
        vals = list(self.item(item, 'values'))
        vals[col_index] = new_val
        self.item(item, values=vals)
        if self.on_edit_complete:
            self.on_edit_complete()

    def _start_entry_edit(self, item: str, column: str, col_index: int, value: str) -> None:
        x, y, width, height = self.bbox(item, column)
        if self._entry:
            self._entry.destroy()

        self._entry = tk.Entry(self, justify="center", font=("Arial", 11))
        self._entry.place(x=x, y=y, width=width, height=height)
        if value and not any(c.isdigit() for c in value):
             self._entry.insert(0, "") 
        else:
             self._entry.insert(0, value.split()[0] if value else "")
             
        self._entry.focus_set()
        self._entry.selection_range(0, tk.END)

        def save_edit(e: tk.Event = None) -> None:
            new_val = self._entry.get().strip()
            if new_val:
                try:
                    num = float(new_val)
                    if 0 <= num <= 20:
                        from db import nota_a_literal
                        lit = nota_a_literal(num)
                        new_val = f"{num:.1f} ({lit})"
                except:
                    pass
            self._update_value(item, col_index, new_val)
            self._entry.destroy()
            self._entry = None

        def cancel_edit(e: tk.Event = None) -> None:
            self._entry.destroy()
            self._entry = None

        self._entry.bind("<Return>", save_edit)
        self._entry.bind("<FocusOut>", save_edit)
        self._entry.bind("<Escape>", cancel_edit)
        
        # Add arrow up/down inside entry to save and move
        def move_up(e):
            save_edit()
            prev_item = self.prev(item)
            if prev_item:
                self.selection_set(prev_item)
                self.focus(prev_item)
                self._start_entry_edit(prev_item, column, col_index, self.item(prev_item, 'values')[col_index])
            return "break"
            
        def move_down(e):
            save_edit()
            next_item = self.next(item)
            if next_item:
                self.selection_set(next_item)
                self.focus(next_item)
                self._start_entry_edit(next_item, column, col_index, self.item(next_item, 'values')[col_index])
            return "break"
            
        def move_left(e):
            if self._entry and self._entry.index(tk.INSERT) != 0 and e.keysym == "Left": return
            save_edit()
            cols = self["columns"]
            if col_index > 4: # Can move left up to Cap 1 (index 4)
                new_col_index = col_index - 1
                new_col = f"#{new_col_index + 1}"
                self._start_entry_edit(item, new_col, new_col_index, self.item(item, 'values')[new_col_index])
            return "break"

        def move_right(e):
            if self._entry and self._entry.index(tk.INSERT) != len(self._entry.get()) and e.keysym == "Right": return
            save_edit()
            cols = self["columns"]
            if col_index < len(cols) - 2: # Last is Comentario, don't move into it with right arrow
                new_col_index = col_index + 1
                new_col = f"#{new_col_index + 1}"
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
        top = ctk.CTkToplevel(self)
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

        btn_guardar = ctk.CTkButton(top, text="Guardar Comentario", command=save_text)
        btn_guardar.pack(pady=10)


class PlanillaScrollXY(ctk.CTkFrame):
    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, bg="#0f172a", highlightthickness=0)
        self.scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)

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


class VentanaPrincipal(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Sistema Docente de Evaluación por Competencias, Capacidades y Rúbricas (Secundaria)")
        self.geometry("1420x850")
        self.minsize(1060, 660)
        self.dev_mode = False

        self.edicion_desbloqueada: bool = True
        cfg_ini = obtener_docente_config()
        self.tema_actual_nombre: str = cfg_ini.get("tema_visual", "Oscuro Noche")
        self.tamano_letra_actual: str = "Muy Grande (18)"
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

        self._construir_barra_contexto()
        self._construir_pestanas()

        self.cambiar_interfaz_visual(self.tema_actual_nombre)
        self.actualizar_visual_candado_y_docente()
        self.recargar_cursos_y_contexto()

    # ==========================================================================
    # GESTIÓN DE LAS 3 INTERFACES / TEMAS VISUALES
    # ==========================================================================

    def cambiar_tamano_letra(self, tamano: str) -> None:
        self.tamano_letra_actual = tamano
        guardar_tamano_letra_preferido(tamano)
        self.cambiar_interfaz_visual(self.tema_actual_nombre)
        self.dibujar_planilla_calificacion(forzar=True)

    def cambiar_interfaz_visual(self, nombre_tema: str) -> None:
        if nombre_tema not in TEMAS_INTERFAZ:
            return
        self.tema_actual_nombre = nombre_tema
        guardar_tema_visual_preferido(nombre_tema)
        cfg_t = TEMAS_INTERFAZ[nombre_tema]

        ctk.set_appearance_mode(cfg_t["appearance"])
        self.configure(fg_color=cfg_t["bg_main"])

        estilo = ttk.Style()
        estilo.theme_use("clam")
        
        f_size = 11 # Default base
        r_height = 30
        f_size = 20  # Increased size per user request
        r_height = 46 # Increased row height
                
        estilo.configure(
            "Treeview",
            background=cfg_t["tree_bg"],
            foreground=cfg_t["tree_fg"],
            fieldbackground=cfg_t["tree_bg"],
            rowheight=r_height,
            font=("Segoe UI", f_size),
            borderwidth=1,
        )
        estilo.configure(
            "Treeview.Heading",
            background=cfg_t["tree_head_bg"],
            foreground=cfg_t["tree_head_fg"],
            font=("Segoe UI", f_size - 1, "bold"),
            relief="raised",
        )
        estilo.map(
            "Treeview",
            background=[("selected", cfg_t["tree_sel"])],
            foreground=[("selected", "#ffffff")],
        )
        # Configure alternating row colors for subtle grid
        stripe_color = "#334155" if "Oscuro" in nombre_tema else "#f3f4f6"
        estilo.configure("Treeview", rowheight=r_height, font=("Segoe UI", f_size))
        estilo.map("Treeview", background=[("selected", cfg_t["tree_sel"])])
        self.stripe_color = stripe_color
        
        # Actualizar colores de las filas intercaladas en todas las tablas
        if hasattr(self, 'planilla_nativa') and self.planilla_nativa:
            self.planilla_nativa.tag_configure("odd", background=stripe_color)
        if hasattr(self, 'tree_buscador_alumnos') and self.tree_buscador_alumnos:
            self.tree_buscador_alumnos.tag_configure("odd", background=stripe_color)
        if hasattr(self, 'tree_matriz') and self.tree_matriz:
            self.tree_matriz.tag_configure("odd", background=stripe_color)


        if hasattr(self, "planilla_xy"):
            self.planilla_xy.aplicar_color_fondo(cfg_t["bg_main"])
        if hasattr(self, "canvas_graficos"):
            self.canvas_graficos.configure(bg=cfg_t["bg_main"])
            self.dibujar_graficos_estadisticos()

    def verificar_permiso_edicion(self) -> bool:
        if self.edicion_desbloqueada:
            return True
        DialogoDesbloquearCandado(self)
        return False

    def alternar_candado(self) -> None:
        if self.edicion_desbloqueada:
            self.edicion_desbloqueada = False
            self.actualizar_visual_candado_y_docente()
            messagebox.showinfo(
                "🔒 Candado Activado",
                "Se activó el Modo Protegido (Solo Lectura).\nPara volver a editar o borrar, haga clic en el candado e ingrese su usuario y clave.",
            )
        else:
            DialogoDesbloquearCandado(self)
            
    def activar_dev_mode(self) -> None:
        if self.dev_mode:
            self.dev_mode = False
            self.btn_toggle_curso.grid_remove()
            self.btn_eliminar_curso.grid_remove()
            messagebox.showinfo("Dev Mode", "Modo Desarrollador desactivado.")
            self.recargar_cursos_y_contexto()
            return
            
        import tkinter.simpledialog as simpledialog
        pwd = simpledialog.askstring("Dev Mode", "Ingrese la clave de desarrollador:", show="*")
        if pwd == "leonarrs03050711":
            self.dev_mode = True
            self.btn_toggle_curso.grid()
            self.btn_eliminar_curso.grid()
            messagebox.showinfo("Dev Mode", "Modo Desarrollador activado. Ahora puedes bloquear/eliminar cursos.")
            self.recargar_cursos_y_contexto()
        else:
            messagebox.showerror("Error", "Clave incorrecta.")

    def actualizar_visual_candado_y_docente(self) -> None:
        cfg = obtener_docente_config()
        self.lbl_docente_info.configure(text=f"👤 {cfg['nombres_docente']}")
        if self.edicion_desbloqueada:
            self.btn_candado.configure(
                text="🔓 EDICIÓN ACTIVA (Bloquear 🔒)",
                fg_color="#15803d",
                hover_color="#166534",
            )
        else:
            self.btn_candado.configure(
                text="🔒 BLOQUEADO (Desbloquear)",
                fg_color="#b91c1c",
                hover_color="#991b1b",
            )

    # ==========================================================================
    # BARRA SUPERIOR GLOBAL CON SELECTOR DE 3 INTERFACES + CANDADO + CURSO/SECCIÓN
    # ==========================================================================

    def _construir_barra_contexto(self) -> None:
        self.barra_top = ctk.CTkFrame(self, corner_radius=10)
        self.barra_top.grid(row=0, column=0, padx=12, pady=(8, 4), sticky="ew")
        self.barra_top.grid_columnconfigure(6, weight=1)

        ctk.CTkLabel(self.barra_top, text="📚 CURSO:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, padx=(10, 4), pady=8, sticky="w"
        )
        self.combo_curso_global = ctk.CTkComboBox(
            self.barra_top,
            width=265,
            height=32,
            state="readonly",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._al_cambiar_curso_global,
        )
        self.combo_curso_global.grid(row=0, column=1, padx=(0, 8), pady=8, sticky="w")

        ctk.CTkLabel(self.barra_top, text="🎓 GRADO:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=2, padx=(2, 3), pady=8
        )
        self.combo_grado_global = ctk.CTkComboBox(
            self.barra_top,
            values=["1°", "2°", "3°", "4°", "5°"],
            width=70,
            height=32,
            command=lambda _v: self._al_cambiar_salon_global(),
        )
        self.combo_grado_global.set("4°")
        self.combo_grado_global.grid(row=0, column=3, padx=(0, 6), pady=8)

        ctk.CTkLabel(self.barra_top, text="🏫 SECCIÓN:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=4, padx=(2, 3), pady=8
        )
        self.combo_seccion_global = ctk.CTkComboBox(
            self.barra_top,
            values=["A", "B", "C", "D", "E"],
            width=65,
            height=32,
            command=lambda _v: self._al_cambiar_salon_global(),
        )
        self.combo_seccion_global.set("A")
        self.combo_seccion_global.grid(row=0, column=5, padx=(0, 8), pady=8)

        self.lbl_docente_info = ctk.CTkLabel(
            self.barra_top,
            text="👤 Docente",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.lbl_docente_info.grid(row=0, column=6, padx=16, pady=8, sticky="e")
        
        # Guardaremos referencias nulas por si otros métodos intentan cambiar su texto
        self.btn_candado = None 

    # ==========================================================================
    # CONSTRUCCIÓN DE LAS PESTAÑAS
    # ==========================================================================

    def _construir_pestanas(self) -> None:
        self.tabview = ctk.CTkTabview(self, corner_radius=12)
        self.tabview.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="nsew")

        self.tab_curriculo = self.tabview.add("Config. Cursos")
        self.tab_estudiantes = self.tabview.add("Estudiantes")
        self.tab_crear = self.tabview.add("Crear Actividad")
        self.tab_calificar = self.tabview.add("Ingresar Calificativos")
        self.tab_buscador = self.tabview.add("Buscador")
        self.tab_graficos = self.tabview.add("Porcentajes de Actividades")
        self.tab_matriz = self.tabview.add("Matriz General")
        self.tab_estadisticas = self.tabview.add("Estadísticas")

        self._construir_tab_curriculo()
        self._construir_tab_estudiantes()
        self._construir_tab_crear_actividad()
        self._construir_tab_calificar_actividad()
        self._construir_tab_buscador_alumnos()
        self._construir_tab_pesos_y_graficos()
        self._construir_tab_matriz_capacidades()
        self._construir_tab_estadisticas()

    # --------------------------------------------------------------------------
    # PESTAÑA 1: CURSOS, COMPETENCIAS Y CAPACIDADES
    # --------------------------------------------------------------------------
    def _construir_tab_curriculo(self) -> None:
        self.tab_curriculo.grid_columnconfigure((0, 1, 2), weight=1)
        self.tab_curriculo.grid_rowconfigure(2, weight=1)

        # --- NUEVO: BARRA DE CONFIGURACIÓN GLOBAL ---
        f_config = ctk.CTkFrame(self.tab_curriculo, fg_color="transparent")
        f_config.grid(row=0, column=0, columnspan=3, padx=12, pady=(6, 2), sticky="ew")

        ctk.CTkLabel(f_config, text="🎨 Interfaz:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=4)
        self.combo_tema_visual = ctk.CTkComboBox(
            f_config,
            values=list(TEMAS_INTERFAZ.keys()),
            width=155,
            state="readonly",
            command=self.cambiar_interfaz_visual,
        )
        self.combo_tema_visual.set(self.tema_actual_nombre)
        self.combo_tema_visual.pack(side="left", padx=8)

        

        ctk.CTkButton(
            f_config,
            text="⚙️ Configurar Docente Principal",
            width=200,
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: DialogoPerfilDocente(self),
        ).pack(side="left", padx=16)

        self.btn_candado = ctk.CTkButton(
            f_config,
            text="🔓 EDICIÓN ACTIVA",
            width=180,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.alternar_candado,
        )
        self.btn_candado.pack(side="left", padx=8)

        ctk.CTkButton(
            f_config,
            text="🔧 Dev Mode",
            width=100,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            command=self.activar_dev_mode,
        ).pack(side="left", padx=8)
        # --------------------------------------------

        ctk.CTkLabel(
            self.tab_curriculo,
            text="Catálogo Curricular (10 Áreas de Secundaria precargadas). Seleccione el Curso para ver sus Competencias y Capacidades.",
            font=ctk.CTkFont(size=13),
        ).grid(row=1, column=0, columnspan=3, padx=12, pady=(6, 8), sticky="w")

        f_cur = ctk.CTkFrame(self.tab_curriculo, corner_radius=10)
        f_cur.grid(row=2, column=0, padx=(8, 5), pady=6, sticky="nsew")
        f_cur.grid_rowconfigure(1, weight=1)
        f_cur.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f_cur, text="1° Cursos / Áreas (10 Incluidos)", font=ctk.CTkFont(size=14, weight="bold")).grid(
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
        self.btn_toggle_curso = ctk.CTkButton(f_cur, text="🔒 Desactivar/Activar Curso (Dev)", height=32, command=self._toggle_curso_activo, fg_color="#b91c1c", hover_color="#991b1b")
        self.btn_toggle_curso.grid(row=3, column=0, padx=10, pady=2, sticky="ew")
        self.btn_toggle_curso.grid_remove()
        
        self.btn_eliminar_curso = ctk.CTkButton(f_cur, text="🗑️ Eliminar Curso (Dev)", height=32, command=self._eliminar_curso, fg_color="#ef4444", hover_color="#dc2626")
        self.btn_eliminar_curso.grid(row=4, column=0, padx=10, pady=(2,8), sticky="ew")
        self.btn_eliminar_curso.grid_remove()

        f_comp = ctk.CTkFrame(self.tab_curriculo, corner_radius=10)
        f_comp.grid(row=1, column=1, padx=5, pady=6, sticky="nsew")
        f_comp.grid_rowconfigure(1, weight=1)
        f_comp.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f_comp, text="2° Competencias del Curso", font=ctk.CTkFont(size=14, weight="bold")).grid(
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
        f_cap.grid(row=1, column=2, padx=(5, 8), pady=6, sticky="nsew")
        f_cap.grid_rowconfigure(1, weight=1)
        f_cap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f_cap, text="3° Capacidades de la Competencia", font=ctk.CTkFont(size=14, weight="bold")).grid(
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

        panel_izq = ctk.CTkFrame(self.tab_estudiantes, width=360, corner_radius=10)
        panel_izq.grid(row=0, column=0, padx=(8, 5), pady=8, sticky="nsew")
        panel_izq.grid_propagate(False)

        ctk.CTkLabel(
            panel_izq, text="Código por Sección y Lista (Ej. 4A01)", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(padx=14, pady=(12, 2), anchor="w")
        ctk.CTkLabel(
            panel_izq,
            text="El código se asigna según su Grado, Sección y orden en lista\n(4A01, 4A02...). Las notas jamás se corren entre alumnos.",
            font=ctk.CTkFont(size=11),
            justify="left",
        ).pack(padx=14, pady=(0, 8), anchor="w")

        ctk.CTkButton(
            panel_izq,
            text="📥 Subir Excel de Estudiantes (.xlsx)",
            height=36,
            fg_color="#15803d",
            hover_color="#166534",
            font=ctk.CTkFont(weight="bold"),
            command=self.accion_importar_excel_estudiantes,
        ).pack(padx=14, pady=(0, 6), fill="x")

        ctk.CTkButton(
            panel_izq,
            text="📄 Descargar Plantilla Excel de Estudiantes",
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
            panel_izq, text="+ Registrar Nuevo Estudiante", command=self.accion_guardar_estudiante
        ).pack(padx=14, pady=(8, 5), fill="x")

        self.btn_est_actualizar = ctk.CTkButton(
            panel_izq,
            text="Guardar Cambios / Estado (Activo/Retirado)",
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

        panel_der = ctk.CTkFrame(self.tab_estudiantes, corner_radius=10)
        panel_der.grid(row=0, column=1, padx=(5, 8), pady=8, sticky="nsew")
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

    # --------------------------------------------------------------------------
    # PESTAÑA 3: CREAR ACTIVIDAD + EXPORTAR/IMPORTAR PLANTILLA DE RÚBRICA O LISTA DE COTEJO
    # --------------------------------------------------------------------------
    def _construir_tab_crear_actividad(self) -> None:
        self.tab_crear.grid_columnconfigure(0, weight=0)
        self.tab_crear.grid_columnconfigure(1, weight=1)
        self.tab_crear.grid_rowconfigure(0, weight=1)

        panel_form = ctk.CTkFrame(self.tab_crear, width=530, corner_radius=10)
        panel_form.grid(row=0, column=0, padx=(8, 6), pady=8, sticky="nsew")
        panel_form.grid_propagate(False)
        panel_form.grid_columnconfigure(0, weight=1)
        panel_form.grid_rowconfigure(4, weight=1)

        f_head = ctk.CTkFrame(panel_form, fg_color="transparent")
        f_head.grid(row=0, column=0, padx=14, pady=(8, 2), sticky="ew")
        f_head.grid_columnconfigure(0, weight=1)

        self.lbl_modo_creacion = ctk.CTkLabel(
            f_head,
            text="1° Crear Actividad (Clase, Examen, Trabajo o Práctica)",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.lbl_modo_creacion.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            f_head,
            text="Limpiar / Nueva",
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
            f_datos1, text="Categoría de la Actividad:", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        self.crear_combo_categoria = ctk.CTkComboBox(
            f_datos1,
            values=["Clases", "Exámenes", "Trabajos", "Prácticas / Otros"],
        )
        self.crear_combo_categoria.set("Clases")
        self.crear_combo_categoria.grid(row=1, column=0, padx=(0, 6), pady=(0, 4), sticky="ew")

        ctk.CTkLabel(
            f_datos1, text="Peso dentro de su categoría:", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=1, sticky="w")
        self.crear_combo_peso = ctk.CTkComboBox(
            f_datos1,
            values=["1.0 (Igual Peso)", "2.0 (Vale el Doble)", "3.0 (Vale el Triple)", "1.5 (Peso 1.5x)"],
        )
        self.crear_combo_peso.set("1.0 (Igual Peso)")
        self.crear_combo_peso.grid(row=1, column=1, pady=(0, 4), sticky="ew")

        ctk.CTkLabel(
            f_datos1, text="Nombre / Tema de la Actividad:", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=2, column=0, sticky="w")
        ctk.CTkLabel(
            f_datos1, text="Fecha (YYYY-MM-DD):", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=2, column=1, sticky="w")
        
        self.crear_entry_titulo = ctk.CTkEntry(
            f_datos1, placeholder_text="Ej. Clase 1: Ecuaciones / Examen Unidad 1"
        )
        self.crear_entry_titulo.grid(row=3, column=0, padx=(0, 6), pady=(0, 4), sticky="ew")

        import datetime
        self.crear_ent_fecha = ctk.CTkEntry(f_datos1, width=120)
        self.crear_ent_fecha.insert(0, datetime.date.today().isoformat())
        self.crear_ent_fecha.grid(row=3, column=1, pady=(0, 4), sticky="ew")

        f_prop = ctk.CTkFrame(panel_form, fg_color="transparent")
        f_prop.grid(row=2, column=0, padx=14, pady=2, sticky="ew")
        f_prop.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            f_prop, text="Propósito de la Clase / Descripción:", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        self.crear_txt_proposito = ctk.CTkTextbox(f_prop, height=42, wrap="word")
        self.crear_txt_proposito.grid(row=1, column=0, pady=(0, 4), sticky="ew")

        f_comp_c = ctk.CTkFrame(panel_form, fg_color="transparent")
        f_comp_c.grid(row=3, column=0, padx=14, pady=2, sticky="ew")
        f_comp_c.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            f_comp_c, text="Seleccione la Competencia:", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        self.crear_combo_comp = ctk.CTkComboBox(
            f_comp_c, state="readonly", command=self._al_cambiar_comp_en_creacion
        )
        self.crear_combo_comp.grid(row=1, column=0, pady=(0, 4), sticky="ew")

        self.scroll_caps_creacion = ctk.CTkScrollableFrame(
            panel_form,
            label_text="Marque las Capacidades a evaluar (El texto continúa hacia abajo) y su Criterio Precisado:",
            label_font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.scroll_caps_creacion.grid(row=4, column=0, padx=14, pady=4, sticky="nsew")
        self.scroll_caps_creacion.grid_columnconfigure(0, weight=1)

        # Botones para Guardar Actividad + Exportar/Subir Plantilla de Rúbrica o Lista de Cotejo
        f_btns_c = ctk.CTkFrame(panel_form, fg_color="transparent")
        f_btns_c.grid(row=5, column=0, padx=14, pady=(4, 8), sticky="ew")
        f_btns_c.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            f_btns_c,
            text="💾 Guardar Nueva Actividad",
            height=34,
            fg_color="#15803d",
            hover_color="#166534",
            font=ctk.CTkFont(weight="bold"),
            command=self.accion_guardar_nueva_actividad,
        ).grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="ew")

        self.btn_actualizar_act = ctk.CTkButton(
            f_btns_c,
            text="✏️ Actualizar Seleccionada",
            height=34,
            fg_color="#0f766e",
            state="disabled",
            command=self.accion_actualizar_actividad_existente,
        )
        self.btn_actualizar_act.grid(row=1, column=0, columnspan=2, pady=(0, 8), sticky="ew")

        ctk.CTkButton(
            f_btns_c,
            text="📤 Exportar Plantilla Rúbrica (Excel)",
            height=32,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            command=lambda: self.accion_exportar_plantilla_instrumento("Rúbrica"),
        ).grid(row=2, column=0, padx=(0, 4), pady=(0, 4), sticky="ew")

        ctk.CTkButton(
            f_btns_c,
            text="📤 Exportar Plantilla Lista de Cotejo (Excel)",
            height=32,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            command=lambda: self.accion_exportar_plantilla_instrumento("Lista de Cotejo"),
        ).grid(row=2, column=1, padx=(4, 0), pady=(0, 4), sticky="ew")

        ctk.CTkButton(
            f_btns_c,
            text="📥 Subir Instrumento Excel a la Actividad",
            height=32,
            fg_color="#0369a1",
            hover_color="#075985",
            command=self.accion_importar_rubrica_cotejo_excel,
        ).grid(row=3, column=0, columnspan=2, sticky="ew")

        panel_lista = ctk.CTkFrame(self.tab_crear, corner_radius=10)
        panel_lista.grid(row=0, column=1, padx=(6, 8), pady=8, sticky="nsew")
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
            text="📝 IR A INGRESAR / EDITAR NOTAS DE ESTA ACTIVIDAD →",
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
            displaycolumns=("Categoria", "Peso", "Titulo", "Competencia", "Capacidades", "Instrumento")
        )
        for col, txt, w, al in [
            ("ID", "ID", 42, "center"),
            ("Categoria", "Categoría", 110, "center"),
            ("Peso", "Peso", 65, "center"),
            ("Titulo", "Título de la Clase / Examen / Trabajo", 205, "w"),
            ("Competencia", "Competencia", 180, "w"),
            ("Capacidades", "Capacidades y Criterios Evaluados", 235, "w"),
            ("Instrumento", "Modo / Instrumento", 125, "center"),
        ]:
            self.tree_actividades.heading(col, text=txt)
            self.tree_actividades.column(col, width=w, anchor=al)
        self.tree_actividades.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.tree_actividades.bind("<<TreeviewSelect>>", self._al_seleccionar_actividad_en_tabla)
        self.tree_actividades.bind("<Double-1>", lambda _e: self.accion_ir_a_calificar_seleccionada())

    # --------------------------------------------------------------------------
    # PESTAÑA 4: INGRESAR / EDITAR NOTAS (MODO NORMAL O CON LISTA DE COTEJO / RÚBRICA)
    # --------------------------------------------------------------------------
    def _construir_tab_calificar_actividad(self) -> None:
        self.tab_calificar.grid_columnconfigure(0, weight=1)
        self.tab_calificar.grid_rowconfigure(2, weight=1)

        f_bar1 = ctk.CTkFrame(self.tab_calificar, corner_radius=8)
        f_bar1.grid(row=0, column=0, padx=8, pady=(6, 4), sticky="ew")
        f_bar1.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            f_bar1, text="📌 Actividad:", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, padx=(8, 4), pady=8, sticky="w")

        self.calif_combo_actividad = ctk.CTkComboBox(
            f_bar1,
            height=34,
            state="readonly",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._al_cambiar_actividad_en_calificar,
        )
        self.calif_combo_actividad.grid(row=0, column=1, padx=4, pady=8, sticky="ew")

        # Selector de Modo: Normal vs Lista de Cotejo / Rúbrica
        ctk.CTkLabel(
            f_bar1, text="Modo Evaluación:", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=2, padx=(6, 3), pady=8)

        self.calif_combo_modo_inst = ctk.CTkComboBox(
            f_bar1,
            values=["⚡ Normal (Nota Directa)", "📋 Evaluar con Lista de Cotejo", "📋 Evaluar con Rúbrica"],
            width=210,
            command=lambda _v: self.dibujar_planilla_calificacion(),
        )
        self.calif_combo_modo_inst.set("⚡ Normal (Nota Directa)")
        self.calif_combo_modo_inst.grid(row=0, column=3, padx=3, pady=8)

        ctk.CTkButton(
            f_bar1,
            text="📥 Subir Rúbrica/Cotejo",
            width=145,
            height=32,
            fg_color="#4338ca",
            command=self.accion_importar_rubrica_cotejo_en_calificacion,
        ).grid(row=0, column=4, padx=3, pady=8)

        ctk.CTkLabel(f_bar1, text="Peso:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=5, padx=(6, 3), pady=8
        )
        self.calif_entry_peso = ctk.CTkEntry(f_bar1, width=56, justify="center")
        self.calif_entry_peso.grid(row=0, column=6, padx=(0, 4), pady=8)

        ctk.CTkButton(
            f_bar1,
            text="☑ Asistencia Todos",
            width=125,
            height=32,
            fg_color="#0369a1",
            command=self.accion_marcar_asistencia_todos,
        ).grid(row=0, column=7, padx=3, pady=8)

        ctk.CTkButton(
            f_bar1,
            text="💾 GUARDAR NOTAS Y COMENTARIOS",
            height=36,
            fg_color="#15803d",
            hover_color="#166534",
            font=ctk.CTkFont(weight="bold"),
            command=self.accion_guardar_planilla_calificacion_completa,
        ).grid(row=0, column=8, padx=(4, 8), pady=8)

        f_bar2 = ctk.CTkFrame(self.tab_calificar, corner_radius=8)
        f_bar2.grid(row=1, column=0, padx=8, pady=(0, 4), sticky="ew")
        f_bar2.grid_columnconfigure(0, weight=1)

        self.lbl_detalle_actividad_calificar = ctk.CTkLabel(
            f_bar2,
            text="Seleccione una actividad arriba. Puede trabajar de forma normal (digitando 0-20) o activar '📋 Con Lista Cotejo / Rúbrica' para evaluar por indicadores.",
            font=ctk.CTkFont(size=12),
            justify="left",
            anchor="w",
            wraplength=1120,
        )
        self.lbl_detalle_actividad_calificar.grid(row=0, column=0, padx=12, pady=6, sticky="ew")

        self.calif_combo_orden = ctk.CTkComboBox(
            f_bar2,
            values=["Apellidos (A-Z)", "Código (Ej. 4A01)", "Apellidos (Z-A)", "Nombres (A-Z)"],
            width=145,
            command=lambda _v: self.dibujar_planilla_calificacion(),
        )
        self.calif_combo_orden.set("Apellidos (A-Z)")
        self.calif_combo_orden.grid(row=0, column=1, padx=8, pady=6)

        self.caja_ref_rubrica = ctk.CTkTextbox(
            f_bar2, height=90, fg_color="#f8fafc", text_color="#0f172a", wrap="word", font=ctk.CTkFont(size=11, weight="bold")
        )

        self.f_tabla_planilla = ctk.CTkFrame(self.tab_calificar, corner_radius=8)
        self.f_tabla_planilla.grid(row=2, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self.f_tabla_planilla.grid_columnconfigure(0, weight=1)
        self.f_tabla_planilla.grid_rowconfigure(0, weight=1)
        self.planilla_nativa = None

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
            f_filtros, text="👤 Buscar Alumno o Código (Ej. 4A01):", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, padx=8, pady=(8, 2), sticky="w")
        self.busc_entry_alumno = ctk.CTkEntry(
            f_filtros, placeholder_text="Escriba apellido, nombre o código 4A01..."
        )
        self.busc_entry_alumno.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")
        self.busc_entry_alumno.bind("<KeyRelease>", lambda _e: self.recargar_buscador_alumnos())

        ctk.CTkLabel(
            f_filtros, text="🎯 Filtrar Clases de Competencia:", font=ctk.CTkFont(size=12, weight="bold")
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
            f_filtros, text="📂 Categoría de Actividades:", font=ctk.CTkFont(size=12, weight="bold")
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
            f_filtros, text="🏫 Alcance de Sección:", font=ctk.CTkFont(size=12, weight="bold")
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
            f_filtros, text="🔃 Ordenar Alumnos por:", font=ctk.CTkFont(size=12, weight="bold")
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
            text="📝 Ir a Editar las Notas de esa Clase",
            height=32,
            fg_color="#1d4ed8",
            font=ctk.CTkFont(weight="bold"),
            command=self.accion_editar_clase_desde_buscador,
        ).grid(row=1, column=5, padx=(6, 10), pady=(0, 8))

        ctk.CTkButton(
            f_filtros,
            text="📥 Exportar Reporte de Estudiante",
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
        sb_y = ttk.Scrollbar(f_tabla_b, orient="vertical", command=self.tree_buscador_alumnos.yview)
        sb_x = ttk.Scrollbar(f_tabla_b, orient="horizontal", command=self.tree_buscador_alumnos.xview)
        self.tree_buscador_alumnos.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        self.tree_buscador_alumnos.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        
        f_detalle = ctk.CTkFrame(f_tabla_b, corner_radius=8, fg_color="transparent")
        f_detalle.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        f_detalle.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(f_detalle, text="Detalle del Comentario / Retroalimentación:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w")
        self.busc_txt_comentario_detalle = ctk.CTkTextbox(f_detalle, height=80, wrap="word", state="disabled")
        self.busc_txt_comentario_detalle.grid(row=1, column=0, sticky="ew")
        
        self.tree_buscador_alumnos.bind("<<TreeviewSelect>>", self._al_seleccionar_fila_buscador)

    # --------------------------------------------------------------------------
    # PESTAÑA 6: PORCENTAJES (%) + VER Y MODIFICAR PESOS DE CADA ITEM POR CATEGORÍA + GRÁFICOS
    # --------------------------------------------------------------------------
    def _construir_tab_pesos_y_graficos(self) -> None:
        self.tab_graficos.grid_columnconfigure(0, weight=0)
        self.tab_graficos.grid_columnconfigure(1, weight=1)
        self.tab_graficos.grid_rowconfigure(0, weight=1)

        panel_izq = ctk.CTkFrame(self.tab_graficos, width=455, corner_radius=10)
        panel_izq.grid(row=0, column=0, padx=(8, 5), pady=8, sticky="nsew")
        panel_izq.grid_propagate(False)
        panel_izq.grid_columnconfigure(0, weight=1)
        panel_izq.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            panel_izq,
            text="1° Porcentajes Generales (%) por Categoría",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=14, pady=(10, 4), sticky="w")

        f_grid_pct = ctk.CTkFrame(panel_izq, corner_radius=8)
        f_grid_pct.grid(row=1, column=0, padx=14, pady=2, sticky="ew")
        f_grid_pct.grid_columnconfigure((0, 1, 2, 3), weight=1)

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
                row=0, column=idx, padx=4, pady=(6, 2)
            )
            ent = ctk.CTkEntry(f_grid_pct, width=85, font=ctk.CTkFont(size=15, weight="bold"), justify="center")
            ent.grid(row=1, column=idx, padx=4, pady=(0, 8))
            self.entries_pct_rubros[clave] = ent

        ctk.CTkButton(
            panel_izq,
            text="💾 Guardar Porcentajes (%) y Actualizar Gráfico",
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
            text="2° Seleccione Categoría para Ver/Modificar Pesos de Actividades:",
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
            text="💾 Guardar Pesos de esta Categoría",
            fg_color="#15803d",
            hover_color="#166534",
            height=32,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.accion_guardar_pesos_individuales_categoria,
        ).grid(row=1, column=1, sticky="ew")

        self.scroll_pesos_categoria = ctk.CTkScrollableFrame(
            panel_izq,
            label_text="Actividades en la categoría seleccionada y su Peso:",
            label_font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.scroll_pesos_categoria.grid(row=4, column=0, padx=14, pady=(4, 10), sticky="nsew")
        self.scroll_pesos_categoria.grid_columnconfigure(0, weight=1)

        # Panel derecho: Lienzo de Gráficos
        panel_der = ctk.CTkFrame(self.tab_graficos, corner_radius=10)
        panel_der.grid(row=0, column=1, padx=(5, 8), pady=8, sticky="nsew")
        panel_der.grid_columnconfigure(0, weight=1)
        panel_der.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            panel_der,
            text="📊 Gráfico Circular de Porcentajes (%) y Frecuencia de Competencias / Capacidades Evaluadas",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=14, pady=(10, 4), sticky="w")

        self.canvas_graficos = tk.Canvas(panel_der, bg="#0f172a", highlightthickness=0)
        self.canvas_graficos.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.canvas_graficos.bind("<Configure>", lambda _e: self.dibujar_graficos_estadisticos())

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
            text="Matriz Competencias y Capacidades (Nota por Nota ya promediada):",
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
            text="✏️ Nota Manual en Capacidad",
            fg_color="#0f766e",
            command=self.accion_colocar_nota_manual_capacidad,
        ).grid(row=0, column=3, padx=4)

        ctk.CTkButton(
            barra_m,
            text="📤 Exportar Excel con Colores (.xlsx)",
            fg_color="#15803d",
            hover_color="#166534",
            font=ctk.CTkFont(weight="bold"),
            command=self.accion_exportar_matriz_excel,
        ).grid(row=0, column=4, padx=4)

        ctk.CTkButton(
            barra_m,
            text="📥 Cargar Ese Mismo Excel con Notas (.xlsx)",
            fg_color="#1d4ed8",
            font=ctk.CTkFont(weight="bold"),
            command=self.accion_importar_matriz_excel_con_notas,
        ).grid(row=0, column=5, padx=(4, 0))

        f_tree_m = ctk.CTkFrame(self.tab_matriz, corner_radius=8)
        f_tree_m.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        f_tree_m.grid_columnconfigure(0, weight=1)
        f_tree_m.grid_rowconfigure(0, weight=1)

        self.tree_matriz = ttk.Treeview(f_tree_m, show="headings", selectmode="browse")
        scroll_x = ttk.Scrollbar(f_tree_m, orient="horizontal", command=self.tree_matriz.xview)
        scroll_y = ttk.Scrollbar(f_tree_m, orient="vertical", command=self.tree_matriz.yview)
        self.tree_matriz.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)

        self.tree_matriz.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

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

        self.f_grafico = ctk.CTkScrollableFrame(self.tab_estadisticas, corner_radius=8, fg_color="white")
        self.f_grafico.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def accion_generar_grafico_estadisticas(self) -> None:
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
            
        import matplotlib.pyplot as plt
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

        is_dash = "Dashboard" in tipo
        fig = plt.figure(figsize=(12, 8) if is_dash else (10, 5), dpi=100)
        
        # Info for PDF export
        curso_nom = self.combo_curso_global.get()
        sec_info = "Todas las Secciones" if tipo == "Comparativa de Secciones" else f"'{seccion}'"
        info_txt = f"Reporte de {curso_nom} | {grado} {sec_info}\nFiltro: {comp_str} | {est_nombre}"
        fig.suptitle(info_txt, fontsize=12, fontweight="bold")
        
        axes = []
        if is_dash:
            axes = [fig.add_subplot(221), fig.add_subplot(222), fig.add_subplot(223), fig.add_subplot(224)]
            tipos_a_graficar = ["Histograma", "Barras", "Polígono", "Capacidades"]
        else:
            axes = [fig.add_subplot(111)]
            tipos_a_graficar = [tipo]
            
        for i, ax_tipo in enumerate(tipos_a_graficar):
            ax = axes[i]
            if "Histograma" in ax_tipo:
                notas = [float(f["promedio"]) for f in filas if f["promedio"]]
                ax.hist(notas, bins=range(0, 22, 2), color="#3b82f6", edgecolor="black")
                ax.set_title("Histograma de Notas Numéricas")
                ax.set_xlabel("Rango de Notas (0-20)")
                ax.set_ylabel("Frecuencia")
                ax.set_xticks(range(0, 21, 2))
                
            elif "Barras" in ax_tipo:
                notas = [float(f["promedio"]) for f in filas if f["promedio"]]
                rangos = {"C (0-10)": 0, "B (11-13)": 0, "A (14-17)": 0, "AD (18-20)": 0}
                for n in notas:
                    if n <= 10: rangos["C (0-10)"] += 1
                    elif n <= 13: rangos["B (11-13)"] += 1
                    elif n <= 17: rangos["A (14-17)"] += 1
                    else: rangos["AD (18-20)"] += 1
                ax.bar(rangos.keys(), rangos.values(), color=["#ef4444", "#f59e0b", "#3b82f6", "#10b981"])
                ax.set_title("Distribución de Notas Literales")
                ax.set_ylabel("Frecuencia")
                
            elif "Polígono" in ax_tipo:
                if est_filtro:
                    datos = [(f["fecha"], float(f["promedio"])) for f in filas if f["promedio"]]
                    datos.sort(key=lambda x: x[0])
                    ax.plot([d[0] for d in datos], [d[1] for d in datos], marker="o", color="#8b5cf6")
                    ax.set_title(f"Evolución de {est_filtro}")
                else:
                    fechas = {}
                    for f in filas:
                        if f["promedio"]: fechas.setdefault(f["fecha"], []).append(float(f["promedio"]))
                    fechas_ordenadas = sorted(fechas.keys())
                    if fechas_ordenadas:
                        promedios = [sum(fechas[k])/len(fechas[k]) for k in fechas_ordenadas]
                        ax.plot(fechas_ordenadas, promedios, marker="s", color="#10b981")
                        ax.fill_between(fechas_ordenadas, promedios, alpha=0.2, color="#10b981")
                    ax.set_title("Evolución Promedio del Aula")
                ax.set_ylim(0, 20)
                ax.tick_params(axis='x', rotation=45)
                
            elif "Capacidades" in ax_tipo:
                cap_notas = {}
                for f in filas:
                    if f["notas_str"] and f["notas_str"] != "Sin Calificar":
                        partes = f["notas_str"].split(" | ")
                        for p in partes:
                            if ": " in p:
                                cap_nom, nota = p.split(": ")
                                try: cap_notas.setdefault(cap_nom, []).append(float(nota))
                                except ValueError: pass
                if not cap_notas:
                    ax.set_title("No hay notas por capacidad.")
                else:
                    labels = [l[:10]+".." for l in cap_notas.keys()]
                    vals = [sum(v)/len(v) for v in cap_notas.values()]
                    ax.bar(labels, vals, color="#f43f5e")
                    ax.set_title("Promedio por Capacidades")
                    ax.set_ylim(0, 20)
                    ax.tick_params(axis='x', rotation=45)
                    
            elif "Comparativa" in ax_tipo:
                sec_comp_notas = {}
                for f in filas:
                    if f["promedio"]:
                        cod = f.get("codigo", "")
                        if cod and len(cod) >= 2:
                            s = cod[1:2]
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
            
        fig.tight_layout(rect=[0, 0.03, 1, 0.95])
        canvas = FigureCanvasTkAgg(fig, master=self.f_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        self.fig_actual = fig

    def accion_exportar_reporte_pdf(self) -> None:
        if not hasattr(self, "fig_actual"):
            messagebox.showwarning("Aviso", "Genere un gráfico primero.")
            return
        
        from tkinter import filedialog
        ruta = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Document", "*.pdf")])
        if ruta:
            try:
                self.fig_actual.savefig(ruta, format="pdf", bbox_inches="tight")
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
        self.crear_combo_comp.configure(values=opciones_comp)

        self.busc_comp_map: Dict[str, Optional[int]] = {"Todas las Competencias": None}
        opciones_busc_comp = ["Todas las Competencias"]
        for i, (cid, nom) in enumerate(self.competencias_curso_actual, start=1):
            opciones_busc_comp.append(nom)
            self.busc_comp_map[nom] = cid
        self.busc_combo_comp.configure(values=opciones_busc_comp)
        self.busc_combo_comp.set("Todas las Competencias")

        if opciones_comp:
            self.crear_combo_comp.set(opciones_comp[0])
            self._al_cambiar_comp_en_creacion(opciones_comp[0])
            
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

        self.recargar_tabla_estudiantes()
        self.recargar_tabla_actividades_creadas()
        self.recargar_buscador_alumnos()
        self.cargar_lista_pesos_por_categoria_en_graficos()
        self.dibujar_graficos_estadisticos()
        self.recargar_matriz_completa()

    def _al_cambiar_salon_global(self) -> None:
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
        if not texto or not self.competencias_curso_actual:
            return None
        for cid, nom in self.competencias_curso_actual:
            if nom == texto:
                return cid
        return self.competencias_curso_actual[0][0]

    # ==========================================================================
    # ACCIONES PESTAÑA 1 Y PESTAÑA 2
    # ==========================================================================

    def _dialogo_nuevo_curso(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        nom = simpledialog.askstring("Nuevo Curso", "Ingrese el nombre del Curso / Área Curricular:")
        if nom and nom.strip():
            crear_curso(nom.strip())
            self.combo_curso_global.set(nom.strip())
            self.recargar_cursos_y_contexto()

    def _toggle_curso_activo(self) -> None:
        if not self.dev_mode: return
        sel = self.tree_cursos.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un curso de la lista.")
            return
        cid = int(self.tree_cursos.item(sel[0], "values")[0])
        import db
        db.alternar_curso_activo(cid)
        self.recargar_cursos_y_contexto()

    def _eliminar_curso(self) -> None:
        if not self.dev_mode: return
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
                cant = importar_estudiantes_desde_excel(
                    ruta, self.combo_grado_global.get(), self.combo_seccion_global.get()
                )
                self.recargar_cursos_y_contexto()
                messagebox.showinfo(
                    "Importación Exitosa",
                    f"Se importaron {cant} estudiante(s) con sus códigos de sección (ej. 4A01, 4A02).",
                )
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo importar el Excel:\n{e}")

    def accion_descargar_plantilla_excel(self) -> None:
        ruta = filedialog.asksaveasfilename(
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
        self.est_entry_apellidos.delete(0, "end")
        self.est_entry_nombres.delete(0, "end")
        self.recargar_tabla_estudiantes()
        self.dibujar_planilla_calificacion(forzar=True)
        self.recargar_buscador_alumnos()
        self.recargar_matriz_completa()

    def _al_seleccionar_estudiante_tabla(self, _event: tk.Event) -> None:
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
        for w in self.scroll_caps_creacion.winfo_children():
            w.destroy()
        self.widgets_caps_creacion.clear()

        comp_id = self._obtener_comp_id_desde_texto(texto_comp)
        if comp_id is None:
            return
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
                text=f"Capacidad {idx}: {cap_nom}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#1e3a8a", "#93c5fd"),
                wraplength=425,
                justify="left",
                anchor="w",
            )
            lbl_cap.grid(row=0, column=1, padx=(2, 8), pady=(6, 2), sticky="ew")

            ctk.CTkLabel(
                f_item,
                text="Criterio de Evaluación Precisado (Opcional - Multilínea):",
                font=ctk.CTkFont(size=11),
            ).grid(row=1, column=1, padx=2, pady=(0, 1), sticky="w")

            txt_crit = ctk.CTkTextbox(f_item, height=42, wrap="word")
            txt_crit.grid(row=2, column=0, columnspan=2, padx=8, pady=(0, 8), sticky="ew")

            self.widgets_caps_creacion.append(
                {
                    "capacidad_id": cap_id,
                    "indice": idx,
                    "nombre": cap_nom,
                    "checkbox": chk,
                    "txt_criterio": txt_crit,
                }
            )

    def _extraer_peso_creacion(self) -> float:
        raw = self.crear_combo_peso.get().strip().split()[0].replace("x", "").replace("%", "")
        try:
            val = float(raw)
            return val if val > 0 else 1.0
        except ValueError:
            return 1.0

    def accion_exportar_plantilla_instrumento(self, tipo_instrumento: str) -> None:
        """
        Exporta una plantilla Excel de Lista de Cotejo o Rúbrica que incluye exactamente
        la Competencia elegida, las Capacidades marcadas por el docente y sus Criterios Precisados,
        además de la lista de estudiantes de la sección actual.
        """
        caps_marcadas: List[Tuple[int, str, str]] = []
        for w in self.widgets_caps_creacion:
            if w["checkbox"].get() == 1:
                crit = w["txt_criterio"].get("1.0", "end").strip()
                caps_marcadas.append((w["capacidad_id"], w["nombre"], crit))

        if not caps_marcadas:
            messagebox.showwarning("Seleccione Capacidades", "Marque al menos una capacidad para generar la plantilla.")
            return

        titulo_act = self.crear_entry_titulo.get().strip() or "Sesión_Evaluada"
        comp_nom = self.crear_combo_comp.get()
        curso = self.combo_curso_global.get()
        grado = self.combo_grado_global.get()
        seccion = self.combo_seccion_global.get()

        ruta = filedialog.asksaveasfilename(
            title=f"Guardar Plantilla Excel de {tipo_instrumento}",
            defaultextension=".xlsx",
            initialfile=f"Plantilla_{tipo_instrumento}_{curso}_{grado}{seccion}.xlsx",
            filetypes=[("Archivo Excel", "*.xlsx")],
        )
        if not ruta:
            return

        exportar_plantilla_rubrica_o_cotejo_excel(
            ruta_destino=ruta,
            nombre_curso=curso,
            grado=grado,
            seccion=seccion,
            titulo_actividad=titulo_act,
            competencia_nombre=comp_nom,
            capacidades_y_criterios=caps_marcadas,
            tipo_instrumento=tipo_instrumento,
        )
        messagebox.showinfo(
            f"Plantilla de {tipo_instrumento} Creada",
            f"Se creó la plantilla con las Capacidades y Criterios Precisados que marcó en:\n{ruta}\n\n"
            f"💡 Puede editar los indicadores (o poner notas) en ese Excel y luego subirlo con el botón '📥 Subir Instrumento Excel'.",
        )

    def accion_importar_rubrica_cotejo_excel(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        sid = self.id_actividad_editando or self.id_actividad_calificando
        if sid is None:
            messagebox.showwarning(
                "Seleccione una Actividad",
                "Primero guarde o seleccione una Clase/Actividad en la tabla derecha para asociarle la Lista de Cotejo o Rúbrica.",
            )
            return
        self._subir_excel_instrumento_a_sesion(sid)

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
            ind_cant, alum_cant = importar_rubrica_o_cotejo_desde_excel(
                sesion_id, ruta, self.combo_grado_global.get(), self.combo_seccion_global.get()
            )
            inds = obtener_indicadores_instrumento_sesion(sesion_id)
            if inds and "Rúbrica" in inds[0]["tipo"]:
                self.calif_combo_modo_inst.set("📝 Evaluar con Rúbrica")
            else:
                self.calif_combo_modo_inst.set("📋 Evaluar con Lista de Cotejo")
            self.recargar_tabla_actividades_creadas()
            self.dibujar_planilla_calificacion(forzar=True)
            self.recargar_buscador_alumnos()
            self.recargar_matriz_completa()
            messagebox.showinfo(
                "Rúbrica / Lista de Cotejo Cargada",
                f"Se cargaron {ind_cant} indicador(es) de evaluación para esta clase"
                + (f" y las notas de {alum_cant} estudiante(s)." if alum_cant > 0 else ".")
                + "\n\nEn la Pestaña 4 puede evaluar por indicadores con el botón '📋 Evaluar Indicadores' o seguir trabajando de forma normal.",
            )
        except Exception as e:
            messagebox.showerror("Error al cargar instrumento", f"Detalle: {e}")

    def accion_limpiar_formulario_actividad(self) -> None:
        self.id_actividad_editando = None
        self.lbl_modo_creacion.configure(text="1° Crear Actividad (Clase, Examen, Trabajo o Práctica)")
        self.crear_entry_titulo.delete(0, "end")
        self.crear_txt_proposito.delete("1.0", "end")
        self.crear_ent_fecha.delete(0, "end")
        import datetime
        self.crear_ent_fecha.insert(0, datetime.date.today().isoformat())
        self.crear_combo_peso.set("1.0 (Igual Peso)")
        self.btn_actualizar_act.configure(state="disabled")
        if self.competencias_curso_actual:
            txt = f"1. {self.competencias_curso_actual[0][1]}"
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
        )
        self.id_actividad_calificando = sid
        self.recargar_tabla_actividades_creadas()
        self.recargar_buscador_alumnos()
        self.cargar_lista_pesos_por_categoria_en_graficos()
        self.dibujar_graficos_estadisticos()
        self.accion_limpiar_formulario_actividad()

        if messagebox.askyesno(
            "Actividad Guardada",
            f"La actividad '{titulo}' se guardó correctamente.\n\n¿Desea ir ahora a la Pestaña 4 para ingresar las notas?",
        ):
            self.abrir_actividad_en_pestana_calificar(sid)

    def recargar_tabla_actividades_creadas(self) -> None:
        for item in self.tree_actividades.get_children():
            self.tree_actividades.delete(item)
        curso_id = self.obtener_curso_activo_id()
        if not curso_id:
            return
        cat_filtro = self.filtro_cat_creacion.get()
        sesiones = obtener_sesiones_clase(
            curso_id, self.combo_grado_global.get(), self.combo_seccion_global.get(), None, cat_filtro
        )

        self.actividades_creadas_map: Dict[int, Dict[str, Any]] = {}
        opciones_combo_calif: List[str] = []
        self.combo_calif_etiqueta_a_id: Dict[str, int] = {}

        todas_sesiones = obtener_sesiones_clase(
            curso_id, self.combo_grado_global.get(), self.combo_seccion_global.get()
        )
        for i, s in enumerate(todas_sesiones, start=1):
            self.actividades_creadas_map[s["id"]] = s
            etiqueta = f"#{i} [{s['categoria']} | Peso {s['peso_clase']:.1f}x] {s['titulo_tema']}"
            opciones_combo_calif.append(etiqueta)
            self.combo_calif_etiqueta_a_id[etiqueta] = s["id"]

        for s in sesiones:
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
                    s.get("tipo_instrumento", "Normal"),
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
            self._al_cambiar_actividad_en_calificar(etiqueta_elegir)
        else:
            self.calif_combo_actividad.set("No hay actividades creadas aún (Créelas en la Pestaña 3)")
            self.id_actividad_calificando = None
            self.dibujar_planilla_calificacion(forzar=True)

    def _al_seleccionar_actividad_en_tabla(self, _event: tk.Event) -> None:
        sel = self.tree_actividades.selection()
        if not sel:
            return
        sid = int(sel[0])
        s = self.actividades_creadas_map.get(sid)
        if not s:
            return

        self.id_actividad_editando = sid
        self.lbl_modo_creacion.configure(text=f"✏️ Editando Actividad #{sid}: {s['titulo_tema']}")
        self.crear_combo_categoria.set(s["categoria"])
        self.crear_combo_peso.set(f"{s['peso_clase']:.1f}")
        self.crear_entry_titulo.delete(0, "end")
        self.crear_entry_titulo.insert(0, s["titulo_tema"])
        self.crear_txt_proposito.delete("1.0", "end")
        self.crear_txt_proposito.insert("1.0", s["proposito"] or "")
        self.crear_ent_fecha.delete(0, "end")
        self.crear_ent_fecha.insert(0, s.get("fecha", ""))

        for idx, (cid, cnom) in enumerate(self.competencias_curso_actual, start=1):
            if cid == s["competencia_id"]:
                txt = f"{idx}. {cnom}"
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
        sid = getattr(self, "combo_calif_etiqueta_a_id", {}).get(etiqueta)
        self.id_actividad_calificando = sid
        if sid and sid in getattr(self, "actividades_creadas_map", {}):
            act = self.actividades_creadas_map[sid]
            t_inst = act.get("tipo_instrumento", "Normal")
            if "Cotejo" in t_inst:
                self.calif_combo_modo_inst.set("📋 Evaluar con Lista de Cotejo")
            elif "brica" in t_inst:
                self.calif_combo_modo_inst.set("📋 Evaluar con Rúbrica")
            else:
                self.calif_combo_modo_inst.set("📝 Normal (Nota Directa)")
        self.dibujar_planilla_calificacion(forzar=True)

    def dibujar_planilla_calificacion(self, forzar: bool = False) -> None:
        modo_str = self.calif_combo_modo_inst.get() if hasattr(self, "calif_combo_modo_inst") else ""
        orden_elegido = self.calif_combo_orden.get() if hasattr(self, "calif_combo_orden") else ""
        estado_actual = (self.id_actividad_calificando, modo_str, orden_elegido)
        
        if not forzar and getattr(self, "_ultimo_estado_planilla", None) == estado_actual:
            return
        self._ultimo_estado_planilla = estado_actual

        for w in self.f_tabla_planilla.winfo_children():
            w.destroy()
        self.planilla_nativa = None
        self.widgets_planilla_calificacion.clear() # keep for legacy just in case

        if self.id_actividad_calificando is None or self.id_actividad_calificando not in getattr(self, "actividades_creadas_map", {}):
            ctk.CTkLabel(self.f_tabla_planilla, text="📝 Primero cree una Clase, Examen, Trabajo o Práctica en la Pestaña 3 y selecciónela arriba.", font=ctk.CTkFont(size=13)).pack(padx=20, pady=30, anchor="w")
            self.calif_entry_peso.delete(0, "end")
            return

        act = self.actividades_creadas_map[self.id_actividad_calificando]
        self.calif_entry_peso.delete(0, "end")
        self.calif_entry_peso.insert(0, f"{act['peso_clase']:.1f}")

        usar_instrumento = "Cotejo" in modo_str or "Rúbrica" in modo_str
        indicadores_subidos = obtener_indicadores_instrumento_sesion(act["id"])

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
            self.caja_ref_rubrica.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="ew")
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
        
        tree = PlanillaNativaTreeview(self.f_tabla_planilla, columns=headers, show="headings")
        tree.pack(fill="both", expand=True)
        self.planilla_nativa = tree
        tree.tag_configure("odd", background=getattr(self, "stripe_color", ""))
        
        tree.heading("ID", text="ID")
        tree.heading("Código", text="Código")
        tree.heading("Apellidos y Nombres", text="Apellidos y Nombres")
        tree.heading("Asistencia", text="Asistencia (Sí/No)")
        for idx_c, cap_inf in enumerate(act["capacidades"], start=1):
            tree.heading(f"Cap {idx_c}", text=cap_inf["capacidad_nombre"].split()[0])
        tree.heading("Comentario", text="Comentario (Doble Clic)")
        
        tree.column("ID", width=0, stretch=False)
        tree.column("Código", width=80, anchor="center", stretch=False)
        tree.column("Apellidos y Nombres", width=250, anchor="w", stretch=False)
        tree.column("Asistencia", width=120, anchor="center", stretch=False)
        for idx_c in range(1, len(act["capacidades"]) + 1):
            tree.column(f"Cap {idx_c}", width=80, anchor="center", stretch=False)
        tree.column("Comentario", width=400, anchor="w", stretch=False)
        
        for est in estudiantes:
            est_id = est["ID"]
            asist_val = "Sí (V)" if asist_map.get(est_id, (1, ""))[0] == 1 else "No (F)"
            comentario = asist_map.get(est_id, (1, ""))[1]
            row = [est_id, est["Codigo_Unico"], f"{est['Apellidos']}, {est['Nombres']}", asist_val]
            for cap_info in act["capacidades"]:
                nota = notas_map.get((est_id, cap_info["capacidad_id"]))
                if nota is not None:
                    row.append(f"{nota:.1f}".rstrip("0").rstrip("."))
                else:
                    row.append("")
            row.append(comentario.replace("\n", " ") if comentario else "")
            tags = ("odd",) if len(tree.get_children()) % 2 == 0 else ("even",)
            tree.insert("", "end", values=row, tags=tags)

        self._datos_estudiantes = estudiantes
        self._capacidades_actividad = act["capacidades"]

        if usar_instrumento:
            tipo_btn = "Rúbrica" if "Rúbrica" in modo_str else "Lista de Cotejo"
            btn = ctk.CTkButton(self.f_tabla_planilla, text=f"📋 Evaluar {tipo_btn} (Masivo)", fg_color="#4338ca", hover_color="#3730a3", command=lambda: self._abrir_dialogo_masivo_desde_nativa(act, estudiantes, tipo_btn))
            btn.place(relx=0.98, rely=0.02, anchor="ne")

    def _abrir_dialogo_masivo_desde_nativa(self, act, estudiantes, tipo_inst):
        DialogoEvaluarInstrumentoMasivo(self, act, estudiantes, tipo_inst)

    def accion_marcar_asistencia_todos(self) -> None:
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
        if not self.verificar_permiso_edicion(): return
        if not self.planilla_nativa: return
        
        try:
            nuevo_peso = float(self.calif_entry_peso.get().strip() or 1.0)
            if nuevo_peso <= 0: raise ValueError
        except:
            messagebox.showwarning("Peso inválido", "El peso debe ser > 0.")
            return

        actualizar_peso_actividad(self.id_actividad_calificando, nuevo_peso)

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
                "notas_por_capacidad": notas_cap
            })
            
        guardar_calificaciones_y_asistencia_sesion(self.id_actividad_calificando, datos_guardar)
        self.recargar_tabla_actividades_creadas()
        self.recargar_buscador_alumnos()
        self.cargar_lista_pesos_por_categoria_en_graficos()
        self.dibujar_graficos_estadisticos()
        self.recargar_matriz_completa()
        messagebox.showinfo("Guardado Exitoso", "Se guardaron todas las notas, comentarios, y asistencia.")

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
        for s in sesiones:
            et = f"#{s['id']} [{s['categoria']}] {s['titulo_tema']}"
            opciones_editar.append(et)
            self.busc_ir_clase_map[et] = s["id"]
        self.busc_combo_ir_clase.configure(
            values=opciones_editar if opciones_editar else ["Sin clases aún"]
        )
        if opciones_editar:
            self.busc_combo_ir_clase.set(opciones_editar[-1])

        cols = ["Fecha", "Alumno", "Actividad", "Competencia", "Notas", "Promedio", "Comentario"]
        headers_cfg: List[Tuple[str, str, int]] = [
            ("Fecha", "Fecha", 95),
            ("Alumno", "Alumno", 190),
            ("Actividad", "Actividad / Clase", 180),
            ("Competencia", "Competencia", 130),
            ("Notas", "Notas por Capacidad", 180),
            ("Promedio", "Prom", 50),
            ("Comentario", "Comentario", 220),
        ]

        self.tree_buscador_alumnos.configure(columns=cols)
        for col_id, txt_h, ancho in headers_cfg:
            self.tree_buscador_alumnos.heading(col_id, text=txt_h)
            self.tree_buscador_alumnos.column(
                col_id,
                width=ancho,
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
            
        ruta = filedialog.asksaveasfilename(
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

            ctk.CTkLabel(
                f_row,
                text=f"#{act['id']} • {act['titulo_tema']}\n({act['competencia_nombre'][:38]}...)",
                font=ctk.CTkFont(size=11, weight="bold"),
                justify="left",
                anchor="w",
            ).grid(row=0, column=0, padx=8, pady=6, sticky="w")

            ctk.CTkLabel(f_row, text="Peso:", font=ctk.CTkFont(size=11)).grid(
                row=0, column=1, padx=(4, 2), pady=6
            )
            ent_p = ctk.CTkEntry(f_row, width=68, justify="center")
            ent_p.insert(0, f"{act['peso_clase']:.1f}")
            ent_p.grid(row=0, column=2, padx=(0, 8), pady=6)

            self.entries_pesos_individuales_cat.append((act["id"], ent_p))

    def accion_guardar_pesos_individuales_categoria(self) -> None:
        if not self.verificar_permiso_edicion():
            return
        if not self.entries_pesos_individuales_cat:
            return

        for sid, ent in self.entries_pesos_individuales_cat:
            try:
                val = float(ent.get().strip())
                if val <= 0:
                    raise ValueError
                actualizar_peso_actividad(sid, val)
            except ValueError:
                messagebox.showwarning("Peso inválido", f"El peso de la actividad #{sid} debe ser un número mayor a 0.")
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

        guardar_pesos_rubros_curso(curso_id, p_clases, p_exam, p_trab, p_prac)
        self.dibujar_graficos_estadisticos()
        self.recargar_matriz_completa()
        suma = p_clases + p_exam + p_trab + p_prac
        messagebox.showinfo(
            "Porcentajes Guardados",
            f"Se actualizaron los porcentajes de evaluación (Suma total: {suma:.1f}%).",
        )

    def dibujar_graficos_estadisticos(self) -> None:
        c = self.canvas_graficos
        c.delete("all")
        ancho = max(c.winfo_width(), 720)
        alto = max(c.winfo_height(), 520)

        cfg_t = TEMAS_INTERFAZ.get(self.tema_actual_nombre, TEMAS_INTERFAZ["Oscuro Noche"])
        color_texto = cfg_t["fg_text"]
        color_fondo = cfg_t["bg_main"]

        curso_id = self.obtener_curso_activo_id()
        if not curso_id:
            return

        pesos = obtener_pesos_rubros_curso(curso_id)
        freq_comp, freq_cap = obtener_estadisticas_frecuencia_evaluacion(
            curso_id, self.combo_grado_global.get(), self.combo_seccion_global.get()
        )

        c.create_text(
            20,
            22,
            anchor="w",
            text="1. GRÁFICO CIRCULAR DE PORCENTAJES (%) POR CATEGORÍA",
            fill=color_texto,
            font=("Segoe UI", 16, "bold"),
        )
        cx1, cy1, r1 = 140, 155, 100
        total_pct = sum(max(v, 0.0) for v in pesos.values()) or 1.0
        ang_ini = 0.0

        for idx, (rubro, val) in enumerate(pesos.items()):
            color = PALETA_COLORES[idx % len(PALETA_COLORES)]
            ext = (max(val, 0.0) / total_pct) * 360.0
            if ext > 0:
                if ext >= 359.9:
                    c.create_oval(cx1 - r1, cy1 - r1, cx1 + r1, cy1 + r1, fill=color, outline=color_fondo)
                else:
                    c.create_arc(
                        cx1 - r1,
                        cy1 - r1,
                        cx1 + r1,
                        cy1 + r1,
                        start=ang_ini,
                        extent=ext,
                        fill=color,
                        outline=color_fondo,
                        width=2,
                    )
            ly = 68 + idx * 32
            c.create_rectangle(260, ly, 278, ly + 18, fill=color, outline="")
            pct_real = (max(val, 0.0) / total_pct) * 100.0
            c.create_text(
                286,
                ly + 9,
                anchor="w",
                text=f"{rubro}: {val:.1f}% ({pct_real:.0f}%)",
                fill=color_texto,
                font=("Segoe UI", 15, "bold"),
            )
            ang_ini += ext

        mitad_x = ancho // 2 + 15
        c.create_text(
            mitad_x,
            22,
            anchor="w",
            text="2. FRECUENCIA DE COMPETENCIAS EVALUADAS",
            fill=color_texto,
            font=("Segoe UI", 16, "bold"),
        )
        cx2, cy2, r2 = mitad_x + 110, 155, 100
        total_f_comp = sum(cuenta for _, cuenta in freq_comp)

        if total_f_comp == 0:
            c.create_oval(cx2 - r2, cy2 - r2, cx2 + r2, cy2 + r2, outline="#64748b", width=2)
            c.create_text(cx2, cy2, text="Sin actividades\naún", fill="#64748b", justify="center")
        else:
            ang2 = 0.0
            for idx, (_nom_c, cuenta) in enumerate(freq_comp):
                if cuenta <= 0:
                    continue
                color = PALETA_COLORES[(idx + 2) % len(PALETA_COLORES)]
                ext = (cuenta / total_f_comp) * 360.0
                if ext >= 359.9:
                    c.create_oval(cx2 - r2, cy2 - r2, cx2 + r2, cy2 + r2, fill=color, outline=color_fondo)
                else:
                    c.create_arc(
                        cx2 - r2,
                        cy2 - r2,
                        cx2 + r2,
                        cy2 + r2,
                        start=ang2,
                        extent=ext,
                        fill=color,
                        outline=color_fondo,
                        width=2,
                    )
                ang2 += ext

        for idx, (nom_c, cuenta) in enumerate(freq_comp):
            color = PALETA_COLORES[(idx + 2) % len(PALETA_COLORES)]
            ly = 62 + idx * 28
            c.create_rectangle(cx2 + 124, ly, cx2 + 140, ly + 16, fill=color, outline="")
            c.create_text(
                cx2 + 148,
                ly + 8,
                anchor="w",
                text=f"{nom_c[:32]} → {cuenta} eval.",
                fill=color_texto if cuenta > 0 else "#ef4444",
                font=("Segoe UI", 14, "bold"),
            )

        y_base = 265
        c.create_line(20, y_base - 12, ancho - 20, y_base - 12, fill="#64748b", width=1)
        c.create_text(
            20,
            y_base + 6,
            anchor="w",
            text="3. FRECUENCIA POR CAPACIDAD (Muestra qué capacidades se evaluaron más y cuáles faltan evaluar)",
            fill=cfg_t["accent"],
            font=("Segoe UI", 15, "bold"),
        )

        max_f_cap = max([cuenta for _, cuenta, _ in freq_cap] + [1])
        espacio_disp = max(alto - (y_base + 30), 180)
        alto_fila = max(min(int(espacio_disp / max(len(freq_cap), 1)), 30), 22)

        for idx, (nom_cap, cuenta, idx_c) in enumerate(freq_cap):
            fy = y_base + 30 + idx * alto_fila
            if fy > alto - 12:
                break
            c.create_text(
                24,
                fy,
                anchor="w",
                text=(nom_cap[:20] + "...") if len(nom_cap) > 20 else nom_cap,
                fill=color_texto if cuenta > 0 else "#ef4444",
                font=("Segoe UI", 14),
            )
            x_barra_ini = 370
            ancho_max_barra = max(ancho - x_barra_ini - 115, 110)
            largo = int((cuenta / max_f_cap) * ancho_max_barra) if cuenta > 0 else 4
            color_b = PALETA_COLORES[(idx_c - 1 + 2) % len(PALETA_COLORES)] if cuenta > 0 else "#ef4444"
            c.create_rectangle(x_barra_ini, fy - 6, x_barra_ini + largo, fy + 6, fill=color_b, outline="")
            etiqueta_f = f"{cuenta} eval." if cuenta > 0 else "0 (Sin evaluar)"
            c.create_text(
                x_barra_ini + largo + 8,
                fy,
                anchor="w",
                text=etiqueta_f,
                fill=color_texto if cuenta > 0 else "#ef4444",
                font=("Segoe UI", 14, "bold"),
            )

    # ==========================================================================
    # ACCIONES PESTAÑA 7: MATRIZ GENERAL + EXPORTAR E IMPORTAR EXCEL
    # ==========================================================================

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
            ("Codigo", "Código (4A01)", 95),
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

        self.tree_matriz.configure(columns=cols)
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

        for f in filas_matriz:
            row_vals: List[Any] = [
                f["estudiante_id"],
                f["codigo_unico"],
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

        ruta = filedialog.asksaveasfilename(
            title="Exportar Registro Detallado con Colores y Divisiones a Excel",
            defaultextension=".xlsx",
            initialfile=f"Registro_Detallado_{curso}_{grado}_{seccion}.xlsx",
            filetypes=[("Archivo Excel", "*.xlsx")],
        )
        if not ruta:
            return

        exportar_matriz_completa_excel(ruta, curso, grado, seccion, estructura_comp, filas_matriz)
        messagebox.showinfo(
            "Excel con Colores Exportado",
            f"Se creó el archivo Excel con códigos por sección ({grado}{seccion}01...) y divisiones de columna a color en:\n{ruta}",
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
            est_proc, notas_proc = importar_matriz_notas_desde_excel(
                ruta, self.combo_grado_global.get(), self.combo_seccion_global.get()
            )
            self.recargar_cursos_y_contexto()
            messagebox.showinfo(
                "Excel con Notas Cargado",
                f"Se procesaron {est_proc} estudiante(s) y se cargaron/actualizaron {notas_proc} calificaciones por capacidad.",
            )
        except Exception as e:
            messagebox.showerror("Error al cargar Excel", f"Detalle: {e}")


class DialogoLicencia(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Activación del Sistema (Desarrollador)")
        self.geometry("450x250")
        self.eval('tk::PlaceWindow . center')
        
        ctk.CTkLabel(self, text="🔒 SISTEMA BLOQUEADO", font=ctk.CTkFont(size=20, weight="bold"), text_color="#ef4444").pack(pady=20)
        ctk.CTkLabel(self, text="Este software requiere activación por parte del desarrollador.\nIngrese el código de acceso:").pack(pady=5)
        
        self.entry_codigo = ctk.CTkEntry(self, show="*", width=250)
        self.entry_codigo.pack(pady=10)
        self.entry_codigo.bind("<Return>", lambda e: self.verificar())
        
        ctk.CTkButton(self, text="Desbloquear Sistema", command=self.verificar).pack(pady=10)
        
    def verificar(self) -> None:
        codigo = self.entry_codigo.get()
        if codigo == "leonarrs03050711":  # Código de desarrollador
            import json, os
            with open("licencia.json", "w") as f:
                json.dump({"activado": True}, f)
            messagebox.showinfo("Éxito", "Sistema desbloqueado permanentemente.")
            self.destroy()
        else:
            messagebox.showerror("Error", "Código incorrecto. Acceso denegado.")

def main() -> None:
    import json, os
    activado = False
    if os.path.exists("licencia.json"):
        try:
            with open("licencia.json", "r") as f:
                data = json.load(f)
                activado = data.get("activado", False)
        except:
            pass
            
    if not activado:
        app_lic = DialogoLicencia()
        app_lic.mainloop()
        
        # Volver a verificar tras cerrar el diálogo
        if os.path.exists("licencia.json"):
            try:
                with open("licencia.json", "r") as f:
                    if not json.load(f).get("activado", False):
                        return
            except:
                return
        else:
            return

    inicializar_db()
    app = VentanaPrincipal()
    app.mainloop()


if __name__ == "__main__":
    main()





