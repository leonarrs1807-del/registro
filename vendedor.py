"""Separate seller application for manual, per-device license issuance."""
from pathlib import Path
import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import customtkinter as ctk
from licencias import validate_request
from licencias_emisor import create_keys, sign_request
from widgets import scroll_area, wrap_label


def paragraph(master, **kwargs):
    label = ctk.CTkLabel(master, wraplength=650, **kwargs)
    wrap_label(label)
    return label


class SellerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Registro Licencias — herramienta del vendedor')
        self.geometry('850x720')
        self.minsize(650, 500)
        self.request_data = None
        self.course_vars = []
        body = scroll_area(self)
        body.pack(fill='both', expand=True)
        ctk.CTkLabel(body, text='Licencias manuales de Registro Docente', font=ctk.CTkFont(size=22, weight='bold')).pack(padx=20, pady=16)
        paragraph(body, text='Esta herramienta es solo para usted. Entregue a los clientes RegistroDocente-Setup.exe y su archivo .licencia. Conserve su clave privada y su contraseña fuera de GitHub y de las carpetas que comparta.', justify='left').pack(fill='x', padx=20, pady=8)
        ctk.CTkButton(body, text='1. Crear mis claves (solo la primera vez)', command=self.keygen, height=40).pack(fill='x', padx=20, pady=6)
        ctk.CTkButton(body, text='2. Abrir solicitud del comprador (.solicitud)', command=self.open_request, height=40).pack(fill='x', padx=20, pady=6)
        self.details = paragraph(body, text='Primero genere sus claves y compile el instalador con license_public_key.pem. Luego abra la solicitud que el comprador exportó en su propia computadora.', justify='left')
        self.details.pack(fill='x', padx=20, pady=12)
        self.all_courses = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(body, text='Paquete completo: todos los cursos de ambos niveles', variable=self.all_courses).pack(padx=20, pady=10, anchor='w')
        self.courses = ctk.CTkFrame(body)
        self.courses.pack(fill='x', padx=20, pady=6)
        ctk.CTkLabel(body, text='Vence el (AAAA-MM-DD). Dejar vacío = licencia permanente:').pack(padx=20, anchor='w')
        self.expiry = ctk.CTkEntry(body, placeholder_text='Ejemplo: 2027-12-31')
        self.expiry.pack(fill='x', padx=20, pady=6)
        ctk.CTkLabel(body, text='Referencia de venta (opcional):').pack(padx=20, anchor='w')
        self.reference = ctk.CTkEntry(body)
        self.reference.pack(fill='x', padx=20, pady=6)
        ctk.CTkButton(body, text='3. Firmar y guardar licencia del comprador', command=self.issue, height=44).pack(fill='x', padx=20, pady=16)
        paragraph(body, text='Compruebe el pago y la identidad del comprador antes de firmar. Cada solicitud identifica una cuenta y un equipo. Para cambiar de computadora tendrá que emitir otra licencia; sin servidor no se puede revocar a distancia la anterior. Haga respaldo de su clave privada cifrada: perderla impide emitir licencias para el instalador existente.', justify='left').pack(fill='x', padx=20, pady=12)

    def keygen(self):
        folder = filedialog.askdirectory(title='Carpeta privada para conservar sus claves')
        if not folder:
            return
        password = simpledialog.askstring('Proteger clave privada', 'Contraseña de al menos 12 caracteres. Consérvela: no se puede recuperar.', show='*', parent=self)
        if password is None:
            return
        confirmation = simpledialog.askstring('Confirmar contraseña', 'Repita la contraseña de su clave privada:', show='*', parent=self)
        if confirmation != password:
            messagebox.showwarning('Contraseña', 'Las contraseñas no coinciden.', parent=self)
            return
        private, public = Path(folder) / 'registro_privada.pem', Path(folder) / 'license_public_key.pem'
        try:
            create_keys(private, public, password)
        except (ValueError, OSError) as exc:
            messagebox.showerror('Claves', str(exc), parent=self)
            return
        messagebox.showinfo('Claves creadas', f'Privada (solo para usted):\n{private}\n\nPública (se puede compartir para compilar el instalador):\n{public}\n\nNo envíe la clave privada ni la contraseña. Haga una copia segura de ambas claves.', parent=self)

    def open_request(self):
        path = filedialog.askopenfilename(title='Solicitud exportada por el cliente', filetypes=[('Solicitud de Registro', '*.solicitud')])
        if not path:
            return
        try:
            request = validate_request(json.loads(Path(path).read_text(encoding='utf-8')))
        except Exception as exc:
            messagebox.showerror('Solicitud', f'No se pudo abrir la solicitud: {exc}', parent=self)
            return
        self.request_data = request
        self.details.configure(text=f"Comprador: {request['name']}\nCorreo: {request['email']}\nCuenta: {request['account_id']}\nEquipo: {request['device']}\nSeleccione únicamente lo que compró:")
        for child in self.courses.winfo_children():
            child.destroy()
        self.course_vars = []
        for item in request['catalog']:
            var = tk.BooleanVar(value=False)
            ctk.CTkCheckBox(self.courses, text=item['label'], variable=var).pack(anchor='w', padx=12, pady=5)
            self.course_vars.append((item['key'], var))

    def issue(self):
        if not self.request_data:
            messagebox.showinfo('Solicitud', 'Abra primero la solicitud del comprador.', parent=self)
            return
        courses = ['*'] if self.all_courses.get() else [key for key, var in self.course_vars if var.get()]
        if not courses:
            messagebox.showinfo('Cursos', 'Seleccione los cursos comprados.', parent=self)
            return
        private = filedialog.askopenfilename(title='Su clave privada de vendedor', filetypes=[('Clave privada PEM', '*.pem')])
        if not private:
            return
        password = simpledialog.askstring('Firmar licencia', 'Contraseña de su clave privada:', show='*', parent=self)
        if password is None:
            return
        try:
            document = sign_request(self.request_data, Path(private).read_bytes(), password, courses,
                                    expires=self.expiry.get().strip() or None, reference=self.reference.get())
        except (ValueError, OSError) as exc:
            messagebox.showerror('Licencia', str(exc), parent=self)
            return
        if not messagebox.askyesno('Emitir licencia', f"Titular: {self.request_data['name']}\nCorreo: {self.request_data['email']}\nPaquete: {', '.join(courses)}\nVigencia: {self.expiry.get().strip() or 'permanente'}\n\n¿Ya verificó la compra y desea emitir esta licencia?", parent=self):
            return
        path = filedialog.asksaveasfilename(title='Dónde guardar la licencia para entregar al cliente', initialfile='Registro_cliente.licencia', defaultextension='.licencia', filetypes=[('Licencia de Registro', '*.licencia')])
        if path:
            Path(path).write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
            messagebox.showinfo('Licencia emitida', f'Envíe este archivo al comprador:\n{Path(path).resolve()}\n\nEl comprador lo importa desde Licencia y cuenta. Solo corresponde a la cuenta y computadora de su solicitud.', parent=self)


if __name__ == '__main__':
    SellerApp().mainloop()
