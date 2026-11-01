"""A dedicated settings area, separate from classroom evaluation."""
import re
import customtkinter as ctk
import db
from widgets import scroll_area,wrap_label
from instrument_widgets import label


class ConfigurationTools:
    def crear_configuracion(self,page):
        page.grid_columnconfigure(0,weight=1);page.grid_rowconfigure(1,weight=1)
        ctk.CTkLabel(page,text='Configuración',font=ctk.CTkFont(size=22,weight='bold')).grid(row=0,column=0,sticky='w',padx=16,pady=12)
        self.config_tabs=ctk.CTkTabview(page);self.config_tabs.grid(row=1,column=0,sticky='nsew',padx=10,pady=(0,10))
        general=self.config_tabs.add('General');courses=self.config_tabs.add('Cursos');data=self.config_tabs.add('Datos')
        body=scroll_area(general,auto_hide=True);body.pack(fill='both',expand=True);body.grid_columnconfigure(0,weight=1)
        def card(title,row):
            frame=ctk.CTkFrame(body);frame.grid(row=row,column=0,sticky='ew',padx=12,pady=8);frame.grid_columnconfigure(1,weight=1)
            ctk.CTkLabel(frame,text=title,font=ctk.CTkFont(size=17,weight='bold')).grid(row=0,column=0,columnspan=2,sticky='w',padx=14,pady=10)
            return frame
        teacher=card('Perfil e institución',0)
        self.config_teacher=label(teacher,'');self.config_teacher.grid(row=1,column=0,columnspan=2,sticky='ew',padx=14,pady=6)
        ctk.CTkButton(teacher,text='Editar perfil docente',height=36,command=self.editar_perfil_docente).grid(row=2,column=0,sticky='w',padx=14,pady=10)
        ctk.CTkButton(teacher,text='Insignia del colegio',height=36,command=self.cargar_insignia).grid(row=2,column=1,sticky='w',padx=14,pady=10)
        view=card('Lectura y apariencia',1)
        from main import TEMAS_INTERFAZ
        for row,title in [(1,'Apariencia'),(2,'Letra de las tablas'),(3,'Zoom')]:
            ctk.CTkLabel(view,text=title,font=ctk.CTkFont(size=14)).grid(row=row,column=0,sticky='w',padx=14,pady=8)
        self.config_theme=ctk.CTkComboBox(view,values=list(TEMAS_INTERFAZ),state='readonly',height=36,command=self.cambiar_interfaz_visual)
        self.config_theme.grid(row=1,column=1,sticky='ew',padx=14,pady=8)
        self.config_font=ctk.CTkComboBox(view,values=['16','18','20','24'],state='readonly',height=36,command=lambda value:self.cambiar_tamano_letra(f'Personalizado ({value})'))
        self.config_font.grid(row=2,column=1,sticky='ew',padx=14,pady=8)
        self.config_zoom=ctk.CTkComboBox(view,values=['100 %','125 %','150 %','175 %'],state='readonly',height=36,command=lambda value:self.cambiar_zoom(int(value.split()[0])/100))
        self.config_zoom.grid(row=3,column=1,sticky='ew',padx=14,pady=8)
        ctk.CTkButton(view,text='Restablecer distribución',height=36,command=self.restaurar_vista).grid(row=4,column=0,columnspan=2,sticky='w',padx=14,pady=12)
        scale=card('Evaluación y niveles de logro',2)
        label(scale,'Defina los límites de C, B, A y AD por nivel educativo. Las notas numéricas se conservan.').grid(row=1,column=0,columnspan=2,sticky='ew',padx=14,pady=6)
        ctk.CTkButton(scale,text='Configurar escala de logro',height=36,command=self.configurar_escala).grid(row=2,column=0,columnspan=2,sticky='w',padx=14,pady=12)
        records=scroll_area(data,auto_hide=True);records.pack(fill='both',expand=True);records.grid_columnconfigure(0,weight=1)
        actions=[('Guardar documento completo',self.guardar_documento),('Abrir documento',self.abrir_documento),
            ('Crear respaldo',self.crear_respaldo),('Restaurar respaldo',self.restaurar_respaldo),('Historial de notas',self.mostrar_historial),
            ('Año escolar y periodo',self.seleccionar_periodo),('Bloqueo por inactividad',self.configurar_inactividad)]
        for row,(text,command) in enumerate(actions):
            ctk.CTkButton(records,text=text,height=40,command=command).grid(row=row,column=0,sticky='ew',padx=18,pady=8)
        licensing=self.config_tabs.add('Licencia')
        text='Cuenta, cursos comprados y activación para esta computadora.' if self._license_required else (
            'Edición personal de revisión para Leonardo. Esta edición funciona sin activar licencias. '
            'La importación de archivos .licencia se habilita en el instalador comercial, que se prepara con tu clave pública de vendedor.')
        label(licensing,text).pack(fill='x',padx=18,pady=18)
        self.config_import_license=ctk.CTkButton(licensing,text='Importar licencia (.licencia)',height=40,
            state='normal' if self._license_required else 'disabled',command=self.importar_licencia_configuracion)
        self.config_import_license.pack(anchor='w',padx=18,pady=8)
        if self._license_required:
            ctk.CTkButton(licensing,text='Mi cuenta y cursos',height=38,command=self.mostrar_licencia).pack(anchor='w',padx=18,pady=8)
            label(licensing,'Crea primero tu usuario en esta computadora. Después guarda la solicitud para el vendedor e importa la licencia que recibas.').pack(fill='x',padx=18,pady=10)
        else:
            label(licensing,'Para preparar la edición de venta: abre RegistroLicencias, pulsa Crear mis claves y comparte únicamente license_public_key.pem. Conserva registro_privada.pem y su contraseña para emitir las licencias de tus compradores.').pack(fill='x',padx=18,pady=10)
        return courses

    def importar_licencia_configuracion(self):
        if not self._license_required:return
        self.mostrar_licencia()
        window=getattr(self,'_account_dialog',None)
        if window and window.winfo_exists() and self.licensing and self.licensing.state:window.activate()

    def actualizar_configuracion(self):
        if not hasattr(self,'config_teacher'):return
        config=db.obtener_docente_config()
        self.config_teacher.configure(text=f"{config.get('nombres_docente','')}\n{config.get('institucion','')}")
        self.config_theme.set(self.tema_actual_nombre)
        match=re.search(r'\((\d+)\)',self.tamano_letra_actual)
        self.config_font.set(str(max(16,int(match[1]) if match else 16)))
        self.config_zoom.set(f"{round(getattr(self,'_zoom',1)*100)} %")

    def abrir_configuracion(self,tab='General'):
        self.tabview.set('Config. Cursos');self.config_tabs.set(tab);self.actualizar_configuracion()
