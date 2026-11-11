"""Background update checks; install only after saving and verifying data backups."""
from pathlib import Path
import json,logging,queue,sys,threading
import tkinter as tk
from tkinter import messagebox,simpledialog
import customtkinter as ctk
import app_storage
from app_security import license_public_key
from app_version import VERSION
from actualizaciones import https_url,check_update,download_installer,backup_before_update,launch_installer
from widgets import SafeDialog,wrap_label,polish_dialog
from colores import button


class UpdateDialog(SafeDialog):
    def __init__(self,app,manifest):
        super().__init__(app);self.app=app;self.manifest=manifest;self.events=queue.Queue();self.busy=False;self.installer=None
        self.title('Actualizar Registro Docente');self.protocol('WM_DELETE_WINDOW',self.close)
        self.grid_columnconfigure(0,weight=1)
        title=ctk.CTkLabel(self,text=f"Versión {manifest['version']} disponible",font=ctk.CTkFont(size=21,weight='bold'));title.grid(row=0,column=0,sticky='ew',padx=20,pady=(20,10))
        detail=ctk.CTkLabel(self,text=manifest.get('notas') or 'Esta versión actualiza el programa y conserva los datos del docente.',anchor='w',justify='left');detail.grid(row=1,column=0,sticky='ew',padx=20,pady=10);wrap_label(detail)
        self.status=ctk.CTkLabel(self,text='La descarga se comprueba con la firma del vendedor y su huella SHA-256.',anchor='w',justify='left');self.status.grid(row=2,column=0,sticky='ew',padx=20,pady=10);wrap_label(self.status)
        self.progress=ctk.CTkProgressBar(self);self.progress.grid(row=3,column=0,sticky='ew',padx=20,pady=12);self.progress.set(0)
        self.action=ctk.CTkButton(self,text='Descargar actualización',**button(),command=self.download);self.action.grid(row=4,column=0,padx=20,pady=12)
        self.cancel=ctk.CTkButton(self,text='Más adelante',**button(),command=self.close);self.cancel.grid(row=5,column=0,padx=20,pady=(0,20))
        polish_dialog(self,app,650,470);self.after(100,self.poll)

    def work(self,function):
        self.busy=True;self.action.configure(state='disabled');self.cancel.configure(state='disabled')
        def worker():
            try:self.events.put(('done',function()))
            except Exception:self.events.put(('error','No se pudo completar la actualización. Los datos y la instalación actual se conservan. Reintenta más tarde.'))
        threading.Thread(target=worker,daemon=True).start()

    def download(self):
        self.status.configure(text='Descargando y verificando el instalador…')
        self.work(lambda:('download',download_installer(self.manifest,app_storage.data_dir(),lambda value:self.events.put(('progress',value)))))

    def install(self):
        if not self.app.preparar_guardado_actualizacion():return
        self.status.configure(text='Guardando un respaldo de registros, biblioteca y cuenta antes de instalar…')
        self.work(lambda:('backup',backup_before_update(app_storage.data_dir(),self.app._db_path,self.manifest['version'])))

    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='progress':self.progress.set(value)
                elif kind=='error':
                    self.busy=False;self.action.configure(state='normal');self.cancel.configure(state='normal');self.status.configure(text=value)
                else:
                    self.busy=False;self.action.configure(state='normal');self.cancel.configure(state='normal')
                    stage,result=value
                    if stage=='download':
                        self.installer=result;self.status.configure(text='Descarga verificada. Se respaldarán los datos antes de instalar.');self.action.configure(text='Instalar y reiniciar',command=self.install)
                    else:
                        try:launch_installer(self.installer,self.manifest)
                        except Exception:messagebox.showerror('Actualización','No se pudo iniciar el instalador. Se conserva el programa actual y el respaldo.',parent=self)
                        else:self.app.destroy();return
        except queue.Empty:pass
        self.after(100,self.poll)

    def close(self):
        if not self.busy:self.destroy()


class UpdateTools:
    def update_url(self):
        path=app_storage.data_dir()/'update-server.json'
        if path.exists():return https_url(json.loads(path.read_text(encoding='utf-8'))['url'])
        value=getattr(sys,'_registro_update_url','')
        return https_url(value) if value else ''

    def iniciar_actualizaciones(self,menu):
        if not getattr(self,'_license_required',False):return
        updates=tk.Menu(menu,tearoff=False);updates.add_command(label='Buscar actualizaciones…',command=self.buscar_actualizaciones)
        updates.add_command(label='Configurar servidor de actualizaciones…',command=self.configurar_servidor_actualizaciones)
        menu.add_cascade(label='Actualizaciones',menu=updates)
        self.after(20000,lambda:self.buscar_actualizaciones(automatic=True))

    def configurar_servidor_actualizaciones(self):
        try:current=self.update_url()
        except (ValueError,OSError):current=''
        value=simpledialog.askstring('Servidor de actualizaciones','URL pública HTTPS de /actualizaciones/registro. No escriba una API_KEY ni contraseñas.',initialvalue=current,parent=self)
        if value is None:return
        try:
            url=https_url(value.strip());path=app_storage.data_dir()/'update-server.json'
            temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps({'url':url}),encoding='utf-8');temporary.replace(path)
        except (ValueError,OSError) as exc:messagebox.showerror('Servidor de actualizaciones',str(exc),parent=self);return
        self.buscar_actualizaciones()

    def buscar_actualizaciones(self,automatic=False):
        if getattr(self,'_update_checking',False) or getattr(self,'_closing_ui',False):return
        try:url=self.update_url()
        except (ValueError,OSError):
            if not automatic:messagebox.showerror('Actualizaciones','Revise la dirección del servidor de actualizaciones.',parent=self)
            return
        if not url:
            if not automatic:messagebox.showinfo('Actualizaciones','Configure primero el servidor público del vendedor. No se requiere la clave de generación de licencias.',parent=self)
            return
        self._update_checking=True;events=queue.Queue()
        def check():
            try:events.put(('ok',check_update(url,license_public_key(),VERSION)))
            except Exception:events.put(('error',None))
        def receive():
            try:kind,result=events.get_nowait()
            except queue.Empty:self.after(100,receive);return
            self._update_checking=False
            if kind=='error':
                if not automatic:messagebox.showinfo('Actualizaciones','No se pudo verificar el servidor. Puede continuar trabajando y volver a intentarlo.',parent=self)
            elif result:
                dialog=getattr(self,'_update_dialog',None)
                if dialog and dialog.winfo_exists():dialog.lift()
                else:self._update_dialog=UpdateDialog(self,result)
            elif not automatic:messagebox.showinfo('Actualizaciones','Ya tiene esta versión o una más reciente.',parent=self)
        threading.Thread(target=check,daemon=True).start();self.after(100,receive)

    def preparar_guardado_actualizacion(self):
        if not self.terminar_edicion_actual():return False
        if getattr(self,'_formularios_pendientes',set()):
            messagebox.showinfo('Guardar antes de actualizar','Guarde los cambios de los formularios antes de instalar la actualización.',parent=self);return False
        points=getattr(self,'puntos_panel',None)
        if points and not points.confirm_change():return False
        if getattr(self,'_planilla_pendiente',False):
            if not messagebox.askyesno('Guardar antes de actualizar','¿Guardar las notas pendientes antes de actualizar? Si elige No, la actualización queda pendiente.',parent=self):return False
            self.accion_guardar_planilla_calificacion_completa()
            if getattr(self,'_planilla_pendiente',False):return False
        return True
