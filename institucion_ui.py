"""Editable school identity and a preview made by the real report renderer."""
import io,tempfile
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image
import institucion,reportes,periodos
from widgets import SafeDialog,scroll_area,wrap_label,polish_dialog
from colores import button


class InstitutionTools:
    def crear_identidad_institucional(self,page):
        body=scroll_area(page,auto_hide=True);body.pack(fill='both',expand=True);body.grid_columnconfigure(1,weight=1)
        title=ctk.CTkLabel(body,text='Identidad de la institución',font=ctk.CTkFont(size=22,weight='bold'));title.grid(row=0,column=0,columnspan=2,sticky='w',padx=18,pady=16)
        hint=ctk.CTkLabel(body,text='Carga tu insignia y completa los datos que aparecerán en los informes y registros descargados. Se conservan con el documento y sus respaldos.',anchor='w',justify='left');hint.grid(row=1,column=0,columnspan=2,sticky='ew',padx=18,pady=8);wrap_label(hint)
        self._institution_entries={};data=institucion.profile(self._db_path)
        for n,(key,caption) in enumerate(institucion.FIELDS.items(),2):
            ctk.CTkLabel(body,text=caption,anchor='w').grid(row=n,column=0,sticky='w',padx=18,pady=7)
            entry=ctk.CTkEntry(body,height=36);entry.insert(0,data[key]);entry.grid(row=n,column=1,sticky='ew',padx=18,pady=7);self._institution_entries[key]=entry
        self.institution_logo=ctk.CTkLabel(body,text='Sin insignia',width=110,height=110)
        self.institution_logo.grid(row=8,column=0,padx=18,pady=14)
        actions=ctk.CTkFrame(body,fg_color='transparent');actions.grid(row=8,column=1,sticky='ew',padx=18,pady=14)
        ctk.CTkButton(actions,text='Cargar insignia PNG / JPG',**button(),command=self.cargar_insignia).pack(anchor='w',pady=5)
        ctk.CTkButton(actions,text='Quitar insignia',**button(),command=self.quitar_insignia).pack(anchor='w',pady=5)
        actions=ctk.CTkFrame(body,fg_color='transparent');actions.grid(row=9,column=0,columnspan=2,sticky='ew',padx=18,pady=14)
        ctk.CTkButton(actions,text='Guardar datos de la IE',**button(),command=self.guardar_identidad).pack(side='left',padx=(0,8))
        ctk.CTkButton(actions,text='Vista previa del informe',**button(),command=self.vista_previa_informe).pack(side='left')
        self.actualizar_insignia()

    def actualizar_insignia(self):
        if not hasattr(self,'institution_logo'):return
        logo=reportes.logo_bytes(self._db_path)
        if logo:
            image=Image.open(io.BytesIO(logo));image.load();image.thumbnail((100,100))
            self._institution_image=ctk.CTkImage(light_image=image,dark_image=image,size=image.size)
            self.institution_logo.configure(text='',image=self._institution_image)
        else:self.institution_logo.configure(text='Sin insignia',image=None)

    def quitar_insignia(self):
        if not self.verificar_permiso_edicion():return
        import db
        with db.obtener_conexion() as conn:
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name='Colegio_Insignia'").fetchone():conn.execute('DELETE FROM Colegio_Insignia')
        import colegios,app_storage
        colegios.sync_identity(self._db_path,app_storage.data_dir())
        self.actualizar_insignia()

    def guardar_identidad(self):
        if not self.verificar_permiso_edicion():return False
        try:
            institucion.save(self._db_path,{k:e.get() for k,e in self._institution_entries.items()})
            import colegios,app_storage
            school=colegios.info(self._db_path)
            colegios.sync_identity(self._db_path,app_storage.data_dir())
            self.actualizar_contexto_academico()
            self.actualizar_configuracion();self.actualizar_visual_candado_y_docente()
            self._formularios_pendientes.discard(str(self.config_tabs.tab('Institución')))
            self.lbl_estado.configure(text='Datos de la institución guardados');return True
        except ValueError as exc:messagebox.showerror('Institución',str(exc));return False

    def vista_previa_informe(self):
        course=self.obtener_curso_activo_id()
        rows=reportes.grade_rows(self._db_path,course,self.combo_grado_global.get(),self.combo_seccion_global.get()) if course else []
        data={k:e.get() for k,e in self._institution_entries.items()};data['periodo']=periodos.info(self._db_path)['label']
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'vista.png';institucion.export_pdf(path,rows,data,reportes.logo_bytes(self._db_path))
            with Image.open(path) as opened:
                opened.load();image=opened.copy()
        window=SafeDialog(self);window.title('Vista previa del informe institucional');window.geometry('1100x790')
        body=scroll_area(window,horizontal=True,auto_hide=True,min_width=850);body.pack(fill='both',expand=True,padx=10,pady=10)
        width=min(1000,max(720,self.winfo_screenwidth()-100));height=round(width*image.height/image.width)
        window._preview_image=ctk.CTkImage(light_image=image,dark_image=image,size=(width,height))
        ctk.CTkLabel(body,text='',image=window._preview_image).pack()
        ctk.CTkLabel(window,text='Vista previa con los datos escritos. Guarda los datos de la IE para utilizarlos en las descargas.').pack(pady=8)
        ctk.CTkButton(window,text='Cerrar',**button(),command=window.destroy).pack(pady=(0,12))
        polish_dialog(window,self,1100,790)
