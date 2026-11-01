"""Local account creation, license requests and read-only expiry UI."""
from pathlib import Path
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import db
from licencias import course_key
from widgets import scroll_area, wrap_label


def paragraph(master, text):
    label = ctk.CTkLabel(master, text=text, wraplength=550, justify='left', anchor='w', font=ctk.CTkFont(size=14))
    wrap_label(label)
    label.pack(fill='x', padx=16, pady=8)
    return label


class AccountDialog(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title('Registro Docente — Licencia y cuenta')
        scale = self._get_window_scaling()
        self.geometry(f'{min(680,int(self.winfo_screenwidth()/scale*.9))}x{min(760,int(self.winfo_screenheight()/scale*.85))}')
        self.minsize(420, 400)
        self.transient(app)
        body = scroll_area(self)
        body.pack(fill='both', expand=True)
        service = app.licensing
        if service is None:
            paragraph(body, app._license_error or 'No se pudo abrir la cuenta de activación.')
            paragraph(body, 'Los datos escolares se conservan. Puede consultarlos y exportarlos. Restaure su cuenta en el mismo perfil de Windows o contacte al vendedor; no borre los archivos para intentar reiniciar la demo.')
            return
        self.service = service
        self.status_label = paragraph(body, service.status()['message'])
        if service.state is None:
            self.signup(body)
        else:
            state = service.state
            paragraph(body, f"Titular: {state['name']}\nUsuario: {state['username']}\nCorreo de compra: {state['email']}\nCuenta: {state['account_id']}\nEquipo: {service.device}")
            paragraph(body, 'Para comprar: exporte una solicitud y envíela al vendedor. Después del pago recibirá un archivo .licencia para importar aquí. Cada compra puede habilitar uno o varios cursos, o el paquete completo.')
            ctk.CTkButton(body, text='1. Guardar solicitud para el vendedor…', command=self.export_request, height=40).pack(fill='x', padx=16, pady=8)
            ctk.CTkButton(body, text='2. Importar licencia comprada…', command=self.activate, height=40).pack(fill='x', padx=16, pady=8)
            ctk.CTkButton(body, text='Respaldar mi cuenta en otra carpeta…', command=self.backup, height=40).pack(fill='x', padx=16, pady=8)
            status = service.status()
            labels = {i['key']: i['label'] for i in app.catalogo_licencias()}
            paragraph(body, 'Cursos habilitados:\n' + ('Todos los cursos de Primaria y Secundaria' if '*' in status['courses'] else '\n'.join(labels.get(c, c) for c in sorted(status['courses'])) or 'Ninguno; solo consulta y exportación.'))
            if not service.public_key:
                paragraph(body, 'Edición de preparación: funciona la demo, pero todavía falta incorporar la clave pública del vendedor al instalador definitivo para aceptar compras. No distribuya esta edición como activación comercial terminada.')
            paragraph(body, 'El respaldo de cuenta solo se puede restaurar en esta misma computadora y cuenta de Windows. No va dentro del documento de notas. Si cambia de computadora deberá solicitar otra licencia; su archivo .registro permite trasladar el trabajo escolar.')
        self.grab_set()

    def signup(self, body):
        paragraph(body, 'Cree su usuario local. Tendrá 30 días de prueba desde hoy y un solo curso de su elección, con sus grados y secciones. La elección de curso de la demo no se puede cambiar. No necesita Internet.')
        self.entries = {}
        for title in ('Nombre y apellidos', 'Correo de compra', 'Usuario', 'Contraseña', 'Repetir contraseña'):
            ctk.CTkLabel(body, text=title, anchor='w').pack(fill='x', padx=16, pady=(6, 0))
            entry = ctk.CTkEntry(body, show='*' if 'contraseña' in title.casefold() else '')
            entry.pack(fill='x', padx=16, pady=4)
            self.entries[title] = entry
        catalog = self.app.catalogo_licencias()
        self.course_map = {item['label']: item['key'] for item in catalog}
        ctk.CTkLabel(body, text='Único curso de la demo:').pack(anchor='w', padx=16, pady=6)
        self.course_choice = ctk.CTkComboBox(body, values=list(self.course_map), state='readonly', height=36)
        self.course_choice.pack(fill='x', padx=16, pady=4)
        if catalog:
            self.course_choice.set(catalog[0]['label'])
        paragraph(body, 'El correo queda ligado a las compras. Esta cuenta es local: no verifica el correo por Internet ni ofrece recuperación por correo. Conserve su usuario, contraseña y respaldo de cuenta.')
        ctk.CTkButton(body, text='Crear mi usuario e iniciar demo de 30 días', command=self.register, height=44).pack(fill='x', padx=16, pady=16)

    def register(self):
        values = {title: entry.get() for title, entry in self.entries.items()}
        if values['Contraseña'] != values['Repetir contraseña']:
            messagebox.showwarning('Contraseña', 'Las contraseñas no coinciden.', parent=self)
            return
        key = self.course_map.get(self.course_choice.get())
        if not key:
            return
        if not messagebox.askyesno('Elegir curso de demo', f"Probará durante 30 días:\n{self.course_choice.get()}\n\nSolo ese curso estará habilitado para editar durante la demo. ¿Crear la cuenta?", parent=self):
            return
        try:
            self.service.register(values['Nombre y apellidos'], values['Correo de compra'], values['Usuario'], values['Contraseña'], key)
            self.app.sincronizar_cuenta()
        except (ValueError, OSError) as exc:
            messagebox.showwarning('Cuenta', str(exc), parent=self)
            return
        level = 'Primaria' if key.startswith('primaria:') else 'Secundaria'
        self.app.cambiar_nivel(level)
        for name, cid in self.app.cursos_map.items():
            if self.app.clave_curso(cid) == key:
                self.app.combo_curso_global.set(name)
                self.app._al_cambiar_curso_global(name)
                break
        self.app.edicion_desbloqueada = True
        self.app.actualizar_visual_candado_y_docente()
        self.app.actualizar_licencia()
        self.destroy()

    def export_request(self):
        path = self.app.elegir_destino(title='Dónde guardar la solicitud para enviar al vendedor', initialfile='Mi_solicitud.solicitud', defaultextension='.solicitud', filetypes=[('Solicitud de Registro', '*.solicitud')])
        if path:
            request = self.service.request(self.app.catalogo_licencias())
            Path(path).write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding='utf-8')
            self.app.archivo_guardado(path, 'Envíe este archivo al vendedor e indique qué cursos desea comprar. No contiene su contraseña ni datos de estudiantes.')

    def activate(self):
        path = filedialog.askopenfilename(title='Licencia enviada por el vendedor', filetypes=[('Licencia de Registro', '*.licencia')], parent=self)
        if not path:
            return
        try:
            document = json.loads(Path(path).read_text(encoding='utf-8'))
            self.service.import_license(document)
        except Exception as exc:
            messagebox.showerror('No se activó la licencia', str(exc), parent=self)
            return
        self.app.actualizar_licencia()
        messagebox.showinfo('Licencia activada', 'Se habilitaron los cursos comprados para esta cuenta y computadora. Sus notas y documentos se conservan.', parent=self)
        self.destroy()

    def backup(self):
        path = self.app.elegir_destino(title='Dónde guardar el respaldo de mi cuenta', initialfile='Mi_cuenta.activacion', defaultextension='.activacion', filetypes=[('Cuenta protegida de Registro', '*.activacion')])
        if path:
            try:
                self.service.backup_account(path)
            except (ValueError, OSError) as exc:
                messagebox.showerror('Respaldo de cuenta', str(exc), parent=self)
                return
            self.app.archivo_guardado(path, 'Cuenta protegida guardada. Solo se puede restaurar en esta misma computadora y perfil de Windows.')


class LicenseTools:
    def catalogo_licencias(self):
        with db.obtener_conexion() as conn:
            return [dict(key=course_key(name, level), label=f'{level} · {name}')
                    for name, level in conn.execute('SELECT nombre,nivel FROM Cursos ORDER BY nivel,nombre')]

    def clave_curso(self, course=None):
        course = course or self.obtener_curso_activo_id()
        with db.obtener_conexion() as conn:
            row = conn.execute('SELECT nombre,nivel FROM Cursos WHERE id=?', (course,)).fetchone()
        return course_key(*row) if row else ''

    def credenciales_actuales(self):
        if getattr(self, 'licensing', None) and self.licensing.state:
            return self.licensing.state['username']
        return db.obtener_docente_config()['usuario']

    def autenticar(self, username, password):
        if getattr(self, '_license_required', False):
            return bool(self.licensing and self.licensing.authenticate(username, password))
        return db.verificar_credenciales_docente(username, password)

    def sincronizar_cuenta(self):
        if not self.licensing or not self.licensing.state:
            return
        state = self.licensing.state
        with db.obtener_conexion() as conn:
            conn.execute('UPDATE Docente_Config SET usuario=?,clave=?,nombres_docente=?,requiere_cambio_clave=0 WHERE id=1',
                         (state['username'], state['password'], state['name']))

    def licencia_permite(self, course=None, show=True, all_courses=False):
        if not getattr(self, '_license_required', False):
            return True
        status = self.licensing.status() if self.licensing else {'courses': set(), 'message': self._license_error}
        allowed = '*' in status['courses'] or (not all_courses and self.clave_curso(course) in status['courses'])
        if not allowed and show:
            message = status['message']
            if status['courses']:
                message += '\n\nEsta opción necesita ' + ('el paquete completo.' if all_courses else 'una licencia para el curso seleccionado. Cambie al curso habilitado o compre otro paquete.')
            messagebox.showinfo('Licencia y cuenta', message + '\n\nPuede seguir consultando y exportando sus registros.', parent=self)
            self.mostrar_licencia()
        return allowed

    def mostrar_licencia(self):
        if not getattr(self, '_license_required', False):
            return
        window = getattr(self, '_account_dialog', None)
        if window and window.winfo_exists():
            window.lift()
            return
        self._account_dialog = AccountDialog(self)

    def actualizar_licencia(self):
        if not getattr(self, '_license_required', False):
            return
        status = self.licensing.status() if self.licensing else {'message': self._license_error}
        if hasattr(self, '_license_label'):
            self._license_label.configure(text=status['message'])

    def _curso_inicial_licencia(self):
        if not self.licensing or not self.licensing.state or self.licencia_permite(show=False):
            return
        available=self.licensing.status()['courses']
        with db.obtener_conexion() as conn:
            courses=conn.execute('SELECT nombre,nivel FROM Cursos WHERE activo=1 ORDER BY id').fetchall()
        for name,level in courses:
            if course_key(name,level) in available or '*' in available:
                self.cambiar_nivel(level)
                self.combo_curso_global.set(name)
                self._al_cambiar_curso_global(name)
                return

    def iniciar_licencia_ui(self, menu):
        if not getattr(self, '_license_required', False):
            return
        menu.add_command(label='Licencia y cuenta', command=self.mostrar_licencia)
        frame = ctk.CTkFrame(self, fg_color='transparent')
        frame.grid(row=3, column=0, sticky='ew', padx=12, pady=4)
        frame.grid_columnconfigure(0, weight=1)
        self._license_label = ctk.CTkLabel(frame, text='', anchor='w', wraplength=850)
        self._license_label.grid(row=0, column=0, sticky='ew', padx=6)
        wrap_label(self._license_label)
        ctk.CTkButton(frame, text='Licencia y cuenta', command=self.mostrar_licencia, width=155).grid(row=0, column=1, padx=6)
        self.actualizar_licencia()
        self.after(250,self._curso_inicial_licencia)
        self.after(60000, self._revisar_licencia)

    def _revisar_licencia(self):
        self.actualizar_licencia()
        if not self.licencia_permite(show=False):
            self.edicion_desbloqueada = False
            self.actualizar_visual_candado_y_docente()
        self.after(60000, self._revisar_licencia)
