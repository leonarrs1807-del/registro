"""User-facing export, drafts, accessible charts and reusable classroom tools."""
from pathlib import Path
import json,io,shutil,tempfile,time
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
import customtkinter as ctk
import app_storage as storage
import reportes,documento


class ClassroomTools:
    def iniciar_mejoras(self,menu):
        archive=tk.Menu(menu,tearoff=False)
        for title,callback in [('Guardar documento interno (.registro)…',self.guardar_documento),('Abrir documento interno…',self.abrir_documento),('Exportar notas: Excel / Google Sheets…',self.exportar_notas),('Reporte individual PDF…',self.reporte_individual),('Importar notas de Google Sheets…',self.importar_google),('Cargar insignia del colegio…',self.cargar_insignia),('Respaldo en otra carpeta…',self.respaldo_externo),('Exportar gráfico de porcentajes…',self.exportar_grafico_categorias)]:
            archive.add_command(label=title,command=callback)
        menu.add_cascade(label='Archivo y exportación',menu=archive)
        work=tk.Menu(menu,tearoff=False)
        for title,callback in [('Recuperar borrador de notas',self.recuperar_borrador),('Duplicar actividad seleccionada',self.duplicar_actividad),('Guardar instrumento en biblioteca',self.guardar_instrumento),('Usar instrumento de biblioteca',self.usar_instrumento),('Ver pendientes y explicación de promedios',self.ver_pendientes),('Archivar / recuperar actividades',self.archivar_actividad),('Bloqueo por inactividad',self.configurar_inactividad),('Cerrar / reabrir periodo',self.alternar_periodo),('Escala de logro por nivel',self.configurar_escala),('Vista previa de nuevas ponderaciones',self.previsualizar_pesos)]:
            work.add_command(label=title,command=callback)
        menu.add_cascade(label='Trabajo docente',menu=work)
        view=tk.Menu(menu,tearoff=False)
        for size in (16,18,20,24):view.add_command(label=f'Letra de tablas: {size}',command=lambda n=size:self.cambiar_tamano_letra(f'Personalizado ({n})'))
        for factor in (1,1.25,1.5,1.75):view.add_command(label=f'Zoom: {factor:.0%}',command=lambda n=factor:self.cambiar_zoom(n))
        menu.add_cascade(label='Lectura',menu=view)
        self.lbl_estado=ctk.CTkLabel(self,text=f'Datos: {self._db_path.name} · Edición bloqueada',anchor='w',height=25)
        self.lbl_estado.grid(row=2,column=0,sticky='ew',padx=16)
        self._undo=[];self._redo=[]
        self._lock_minutes=15;self._last_input=time.monotonic()
        self.bind('<KeyPress>',lambda e:setattr(self,'_last_input',time.monotonic()),add='+')
        self.bind('<ButtonPress>',lambda e:setattr(self,'_last_input',time.monotonic()),add='+')
        self.bind('<Button-3>',self.mostrar_celda_completa,add='+')
        self.after(15000,self.verificar_inactividad)
        import db
        self.combo_nivel=ctk.CTkComboBox(self.barra_top,values=['Primaria','Secundaria'],state='readonly',command=self.cambiar_nivel,width=180)
        self.combo_nivel.set(db.obtener_docente_config().get('nivel_educativo','Secundaria'))
        self.combo_nivel.grid(row=1,column=0,columnspan=2,sticky='w',padx=10,pady=5)
        self.bind('<Control-z>',lambda e:self.deshacer_planilla() if e.widget in (getattr(self,'planilla_nativa',None),getattr(self,'identidad_planilla',None)) else None)
        self.bind('<Control-y>',lambda e:self.deshacer_planilla(True) if e.widget in (getattr(self,'planilla_nativa',None),getattr(self,'identidad_planilla',None)) else None)
        self.bind('<Control-v>',self.pegar_planilla,add='+')
        self.bind('<Control-plus>',lambda e:self.cambiar_zoom(min(1.75,getattr(self,'_zoom',1)+.25)))
        self.bind('<Control-minus>',lambda e:self.cambiar_zoom(max(1,getattr(self,'_zoom',1)-.25)))
        self.bind('<Configure>',self._guardar_ventana,add='+')
        prefs=self._preferencias()
        if prefs.get('geometry'):self.geometry(prefs['geometry'])
        self._lock_minutes=prefs.get('lock_minutes',15)
        self.cambiar_zoom(prefs.get('zoom',1),save=False)
        self.after(15000,self.autoguardar_borrador)
        self.after(500,self._ofrecer_borrador)
        self.after(300,lambda:self._fuentes_legibles(self))

    def _fuentes_legibles(self,widget):
        try:
            font=widget.cget('font')
            if isinstance(font,ctk.CTkFont) and font.cget('size')<14:font.configure(size=14)
        except (ValueError,tk.TclError,AttributeError):pass
        for child in widget.winfo_children():self._fuentes_legibles(child)

    def cambiar_nivel(self,nivel):
        import db
        if not self.confirmar_descartar():
            self.combo_nivel.set(db.obtener_docente_config().get('nivel_educativo','Secundaria'));return
        with db.obtener_conexion() as conn:conn.execute('UPDATE Docente_Config SET nivel_educativo=? WHERE id=1',(nivel,))
        self.id_actividad_calificando=None;self.id_actividad_editando=None
        self.recargar_cursos_y_contexto()
        self.lbl_estado.configure(text=f'{nivel} · Datos y calificativos separados por nivel')

    def _preferencias(self):
        file=storage.data_dir()/'vista.json'
        try:return json.loads(file.read_text(encoding='utf-8'))
        except (OSError,ValueError):return {}

    def _guardar_ventana(self,event=None):
        if event is not None and event.widget is not self:return
        if not hasattr(self,'_zoom'):return
        file=storage.data_dir()/'vista.json'
        file.write_text(json.dumps({'zoom':self._zoom,'geometry':self.geometry(),'lock_minutes':self._lock_minutes}),encoding='utf-8')

    def cambiar_zoom(self,factor,save=True):
        self._zoom=factor;ctk.set_widget_scaling(factor)
        self.cambiar_interfaz_visual(self.tema_actual_nombre)
        if save:self._guardar_ventana()

    def cargar_insignia(self):
        if not self.verificar_permiso_edicion():return
        source=filedialog.askopenfilename(title='Insignia del colegio',filetypes=[('Imagen PNG o JPEG','*.png *.jpg *.jpeg')])
        if source:
            reportes.save_logo(source,self._db_path)
            messagebox.showinfo('Insignia guardada','La insignia quedará incluida en los respaldos y documentos internos. Al exportar podrá elegir si desea mostrarla.')

    def insignia_exportacion(self):
        image=reportes.logo_bytes(self._db_path)
        return image if image and messagebox.askyesno('Insignia del colegio','¿Incluir la insignia en este reporte?') else None

    def guardar_documento(self):
        if self._formularios_pendientes and not messagebox.askyesno('Formularios pendientes','Hay formularios sin guardar. ¿Guardar el documento solo con los datos ya confirmados?'):return
        if getattr(self,'_planilla_pendiente',False):
            if not messagebox.askyesno('Notas pendientes','El documento guardará las notas confirmadas. ¿Desea guardar primero las notas de la planilla?'):return
            self.accion_guardar_planilla_calificacion_completa()
            if self._planilla_pendiente:return
        path=filedialog.asksaveasfilename(defaultextension='.registro',filetypes=[('Documento de Registro Docente','*.registro')])
        if path:
            documento.save_document(path,self._db_path)
            messagebox.showinfo('Documento guardado','Se guardaron todos los datos del periodo, incluidos instrumentos e insignia.')

    def abrir_documento(self):
        if not self.confirmar_descartar():return
        path=filedialog.askopenfilename(filetypes=[('Documento de Registro Docente','*.registro')])
        if path:
            target=storage.data_dir()/f'documento-{time.time_ns()}.db'
            documento.open_document(path,target);storage.activate_period(target);self._reiniciar(target)

    def exportar_notas(self):
        course=self.obtener_curso_activo_id()
        if not course:return
        if self._planilla_pendiente:
            messagebox.showinfo('Notas pendientes','Guarde la planilla antes de exportar para incluir sus últimos cambios.');return
        path=filedialog.asksaveasfilename(defaultextension='.xlsx',filetypes=[('Excel y Google Sheets','*.xlsx'),('CSV para Google Sheets','*.csv'),('Reporte PDF','*.pdf'),('Datos JSON','*.json')])
        if path:
            logo=self.insignia_exportacion() if Path(path).suffix.lower() in ('.xlsx','.pdf') else None
            count=reportes.export_grades(path,self._db_path,course,self.combo_grado_global.get(),self.combo_seccion_global.get(),logo)
            messagebox.showinfo('Notas exportadas',f'Se exportaron {count} registros. En Google Sheets use Archivo → Importar → Subir. El documento .registro conserva toda la base para volver a abrirla aquí.')

    def respaldo_externo(self):
        folder=filedialog.askdirectory(title='Carpeta para el respaldo externo')
        if folder:
            source=storage.backup_database(self._db_path)
            shutil.copy2(source,Path(folder)/source.name)
            messagebox.showinfo('Respaldo guardado','Se verificó y copió el respaldo a la carpeta elegida.')

    def _filas_planilla(self):
        tree=getattr(self,'planilla_nativa',None)
        return [list(tree.item(i,'values')) for i in tree.get_children()] if tree and tree.winfo_exists() else []

    def recordar_planilla(self):
        rows=self._filas_planilla()
        if rows and (not self._undo or self._undo[-1]!=rows):self._undo.append(rows)
        self._redo.clear()
        self._undo=self._undo[-100:]

    def deshacer_planilla(self,redo=False):
        if not self.verificar_permiso_edicion():return 'break'
        origin,target=(self._redo,self._undo) if redo else (self._undo,self._redo)
        if origin:
            target.append(self._filas_planilla());self._poner_filas(origin.pop())
        return 'break'

    def _poner_filas(self,rows):
        tree=self.planilla_nativa
        if len(rows)!=len(tree.get_children()):raise ValueError('El borrador no coincide con el alumnado actual.')
        for item,row in zip(tree.get_children(),rows):
            current=tree.item(item,'values')
            if str(current[0])!=str(row[0]):raise ValueError('Cambió el alumnado. No se aplicó el borrador.')
        for item,row in zip(tree.get_children(),rows):tree.item(item,values=row)
        self.marcar_planilla_pendiente()

    def pegar_planilla(self,event=None):
        tree=getattr(self,'planilla_nativa',None)
        if event and event.widget is not tree:return
        if not tree or not tree.selection() or not self.verificar_permiso_edicion():return
        import csv,io
        from db_safety import valid_number
        values=list(csv.reader(io.StringIO(self.clipboard_get()),delimiter='\t'))
        column=simpledialog.askinteger('Pegar notas','Primera capacidad a completar (1, 2, …):',minvalue=1,maxvalue=len(self._capacidades_actividad))
        if column is None:return 'break'
        rows=self._filas_planilla();items=list(tree.get_children());start=items.index(tree.selection()[0])
        if start+len(values)>len(rows):raise ValueError('El bloque contiene más estudiantes que la planilla.')
        for offset,line in enumerate(values):
            if column-1+len(line)>len(self._capacidades_actividad):raise ValueError('El bloque supera las capacidades de la actividad.')
            for j,value in enumerate(line):rows[start+offset][3+column+j]='' if not value.strip() else str(valid_number(value.replace(',','.')))
        if messagebox.askyesno('Confirmar pegado',f'¿Aplicar el bloque a {len(values)} estudiantes?'):
            self.recordar_planilla();self._poner_filas(rows)
        return 'break'

    def _borrador_path(self):return self._db_path.with_suffix('.borrador.json')

    def autoguardar_borrador(self):
        if self._planilla_pendiente and self._filas_planilla():
            data={'session':self.id_actividad_calificando,'rows':self._filas_planilla(),'peso':self.calif_entry_peso.get(),'context':self._contexto_guardado}
            file=self._borrador_path();temp=file.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');temp.replace(file)
            self.lbl_estado.configure(text='Borrador recuperable guardado · Pulse Guardar para confirmar las notas')
        self.after(15000,self.autoguardar_borrador)

    def _ofrecer_borrador(self):
        if self._borrador_path().exists() and messagebox.askyesno('Borrador disponible','Hay un borrador sin confirmar de una sesión anterior. ¿Desea recuperarlo?'):self.recuperar_borrador()

    def recuperar_borrador(self):
        if not self.verificar_permiso_edicion():return
        file=self._borrador_path()
        if not file.exists():messagebox.showinfo('Borrador','No hay borradores pendientes.');return
        data=json.loads(file.read_text(encoding='utf-8'))
        if not self.confirmar_descartar():return
        for widget,value in zip((self.combo_curso_global,self.combo_grado_global,self.combo_seccion_global),data['context']):widget.set(value)
        self._al_cambiar_curso_global(self.combo_curso_global.get());self.abrir_actividad_en_pestana_calificar(data['session'])
        self._poner_filas(data['rows']);self.calif_entry_peso.delete(0,'end');self.calif_entry_peso.insert(0,data['peso'])

    def duplicar_actividad(self):
        if not self.verificar_permiso_edicion():return
        import db
        act=getattr(self,'actividades_creadas_map',{}).get(self.id_actividad_calificando)
        if not act:messagebox.showinfo('Actividad','Abra primero una actividad en Ingresar Calificativos.');return
        title=simpledialog.askstring('Duplicar actividad','Nombre de la nueva actividad:',initialvalue=act['titulo_tema']+' (copia)')
        if not title:return
        sid=db.crear_o_actualizar_sesion_clase(None,act['curso_id'],act['competencia_id'],act['grado'],act['seccion'],title,act['proposito'],act['peso_clase'],[(c['capacidad_id'],c['criterio_precisado']) for c in act['capacidades']],categoria=act['categoria'])
        inds=db.obtener_indicadores_instrumento_sesion(act['id'])
        if inds:db.guardar_indicadores_instrumento_sesion(sid,inds[0]['tipo'],[(i['capacidad_id'],i['indicador_texto'],i['puntaje_maximo']) for i in inds])
        self.recargar_cursos_y_contexto();self.abrir_actividad_en_pestana_calificar(sid)

    def guardar_instrumento(self):
        if not self.verificar_permiso_edicion():return
        import db
        inds=db.obtener_indicadores_instrumento_sesion(self.id_actividad_calificando)
        if not inds:messagebox.showinfo('Biblioteca','La actividad no tiene indicadores.');return
        name=simpledialog.askstring('Biblioteca','Nombre de la plantilla reutilizable:')
        if name:
            with db.obtener_conexion() as conn:
                conn.execute('CREATE TABLE IF NOT EXISTS Biblioteca_Instrumentos(nombre TEXT PRIMARY KEY, datos TEXT NOT NULL)')
                conn.execute('INSERT INTO Biblioteca_Instrumentos VALUES(?,?)',(name,json.dumps(inds,ensure_ascii=False)))
            messagebox.showinfo('Biblioteca','Plantilla guardada; modificarla en otra actividad no cambia las evaluaciones anteriores.')

    def usar_instrumento(self):
        if not self.verificar_permiso_edicion():return
        import db
        with db.obtener_conexion() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS Biblioteca_Instrumentos(nombre TEXT PRIMARY KEY, datos TEXT NOT NULL)')
            templates=conn.execute('SELECT nombre,datos FROM Biblioteca_Instrumentos ORDER BY nombre').fetchall()
        if not templates:messagebox.showinfo('Biblioteca','No hay plantillas guardadas.');return
        selection=simpledialog.askinteger('Biblioteca','Seleccione una plantilla:\n'+'\n'.join(f'{i+1}. {r[0]}' for i,r in enumerate(templates)),minvalue=1,maxvalue=len(templates))
        if selection:
            inds=json.loads(templates[selection-1][1]);db.guardar_indicadores_instrumento_sesion(self.id_actividad_calificando,inds[0]['tipo'],[(i['capacidad_id'],i['indicador_texto'],i['puntaje_maximo']) for i in inds])
            self.dibujar_planilla_calificacion(forzar=True)

    def ver_pendientes(self):
        import db
        course=self.obtener_curso_activo_id()
        if not course:return
        structure,rows=db.calcular_matriz_competencias_y_capacidades(course,self.combo_grado_global.get(),self.combo_seccion_global.get())
        text='El promedio de cada capacidad combina los rubros con notas usando sus porcentajes; dentro del rubro se aplican los pesos de actividad. Las competencias promedian sus capacidades evaluadas. Sin evaluar no equivale a cero. Las notas manuales sustituyen el cálculo de esa capacidad.\n\n'
        weights=db.obtener_pesos_rubros_curso(course);text+='Ponderaciones: '+', '.join(f'{k}: {v:g}%' for k,v in weights.items())+'\n\n'
        text+='\n'.join(f"{r['apellidos']}, {r['nombres']}: {r['faltan_capacidades']} capacidades pendientes; promedio {r['promedio_general'] if r['promedio_general'] is not None else 'sin evaluar'}" for r in rows)
        window=tk.Toplevel(self);window.title('Pendientes y cálculo del promedio');window.geometry('850x600')
        box=tk.Text(window,wrap='word',font=('Segoe UI',14));box.pack(fill='both',expand=True);box.insert('1.0',text);box.configure(state='disabled')

    def periodo_cerrado(self):
        import db
        with db.obtener_conexion() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS Estado_Periodo(id INTEGER PRIMARY KEY CHECK(id=1), cerrado INTEGER NOT NULL)')
            row=conn.execute('SELECT cerrado FROM Estado_Periodo WHERE id=1').fetchone();return bool(row and row[0])

    def alternar_periodo(self):
        import db
        from main import DialogoDesbloquearCandado
        # Always authenticate, including when reopening a closed period.
        self.edicion_desbloqueada=False
        dialog=DialogoDesbloquearCandado(self);self.wait_window(dialog)
        if not self.edicion_desbloqueada:return
        state=self.periodo_cerrado()
        if not messagebox.askyesno('Periodo',('Reabrir el periodo para editar' if state else 'Cerrar el periodo y bloquear cambios')+'?'):return
        storage.backup_database(self._db_path,'cierre-periodo')
        with db.obtener_conexion() as conn:conn.execute('INSERT OR REPLACE INTO Estado_Periodo VALUES(1,?)',(int(not state),))
        self.edicion_desbloqueada=False;self.actualizar_visual_candado_y_docente()

    def previsualizar_pesos(self):
        import db
        from db_safety import valid_number
        course=self.obtener_curso_activo_id()
        if not course:return
        values=[valid_number(e.get(),0,100,'Porcentaje') for e in self.entries_pct_rubros.values()]
        if abs(sum(values)-100)>1e-6:raise ValueError('Los porcentajes deben sumar 100%.')
        _,before=db.calcular_matriz_competencias_y_capacidades(course,self.combo_grado_global.get(),self.combo_seccion_global.get())
        with tempfile.TemporaryDirectory() as folder:
            preview=Path(folder)/'preview.db';storage.copy_database(self._db_path,preview)
            db.guardar_pesos_rubros_curso(course,*values,db_path=preview)
            _,after=db.calcular_matriz_competencias_y_capacidades(course,self.combo_grado_global.get(),self.combo_seccion_global.get(),db_path=preview)
        window=tk.Toplevel(self);window.title('Simulación de ponderaciones · no modifica notas');window.geometry('700x500')
        tree=ttk.Treeview(window,columns=('alumno','actual','propuesto'),show='headings');tree.pack(fill='both',expand=True)
        for c in tree['columns']:tree.heading(c,text=c.capitalize())
        for old,new in zip(before,after):tree.insert('','end',values=(old['apellidos']+', '+old['nombres'],old['promedio_general'],new['promedio_general']))

    def exportar_grafico_categorias(self):
        if not getattr(self,'figuras_porcentajes',None):return
        name=simpledialog.askinteger('Gráfico','1. Ponderaciones\n2. Competencias\n3. Capacidades',minvalue=1,maxvalue=3)
        if name:
            path=filedialog.asksaveasfilename(defaultextension='.pdf',filetypes=[('PDF','*.pdf'),('Imagen PNG','*.png')])
            if path:reportes.save_figure(self.figuras_porcentajes[name-1],path,self.insignia_exportacion())

    def importar_google(self):
        if not self.verificar_permiso_edicion() or not self.confirmar_descartar():return
        path=filedialog.askopenfilename(title='Notas exportadas desde Excel o Google Sheets',filetypes=[('Libro Excel','*.xlsx'),('CSV UTF-8','*.csv')])
        if not path:return
        with tempfile.TemporaryDirectory() as folder:
            preview=Path(folder)/'preview.db';storage.copy_database(self._db_path,preview)
            immutable=Path(folder)/('notas'+Path(path).suffix);shutil.copy2(path,immutable)
            count=reportes.import_grades(immutable,preview)
            if not messagebox.askyesno('Importar notas',f'Se validaron {count} calificaciones por ID permanente. ¿Aplicar estos cambios?'):return
            storage.backup_database(self._db_path,'antes-importar-google')
            reportes.import_grades(immutable,self._db_path)
        self.recargar_cursos_y_contexto();self.dibujar_planilla_calificacion(forzar=True)
        messagebox.showinfo('Importación completa',f'Se aplicaron {count} registros.')

    def archivar_actividad(self):
        if not self.verificar_permiso_edicion():return
        import db
        with db.obtener_conexion() as conn:
            cols={r[1] for r in conn.execute('PRAGMA table_info(Sesiones_Clase)')}
            if 'archivada' not in cols:conn.execute('ALTER TABLE Sesiones_Clase ADD COLUMN archivada INTEGER NOT NULL DEFAULT 0')
            rows=conn.execute('SELECT id,titulo_tema,archivada FROM Sesiones_Clase WHERE curso_id=? ORDER BY fecha DESC',(self.obtener_curso_activo_id(),)).fetchall()
        if not rows:return
        choice=simpledialog.askinteger('Archivar o recuperar actividad','\n'.join(f'{i+1}. {r[1]} ({"archivada" if r[2] else "activa"})' for i,r in enumerate(rows)),minvalue=1,maxvalue=len(rows))
        if choice:
            sid,title,state=rows[choice-1]
            storage.backup_database(self._db_path,'antes-archivar')
            with db.obtener_conexion() as conn:conn.execute('UPDATE Sesiones_Clase SET archivada=? WHERE id=?',(int(not state),sid))
            self.recargar_tabla_actividades_creadas()
            messagebox.showinfo('Actividad','El estado de la actividad cambió; sus notas siguen incluidas en el registro y en los promedios.')

    def configurar_inactividad(self):
        minutes=simpledialog.askinteger('Bloqueo automático','Minutos sin interacción antes de bloquear (0 para desactivar):',initialvalue=15,minvalue=0,maxvalue=120)
        if minutes is not None:
            self._lock_minutes=minutes;self._last_input=time.monotonic()
            self._guardar_ventana()

    def verificar_inactividad(self):
        if getattr(self,'_lock_minutes',15)>0 and time.monotonic()-self._last_input>self._lock_minutes*60:
            self.edicion_desbloqueada=False;self.dev_mode=False;self.actualizar_visual_candado_y_docente()
        self.after(15000,self.verificar_inactividad)

    def mostrar_celda_completa(self,event):
        widget=event.widget
        if not isinstance(widget,ttk.Treeview):return
        row=widget.identify_row(event.y);col=widget.identify_column(event.x)
        if col and not row:
            messagebox.showinfo('Encabezado completo',widget.heading(widget.column(col,'id'),'text'));return
        if row and col:
            name=widget.column(col,'id');value=widget.set(row,name)
            messagebox.showinfo(widget.heading(name,'text'),value or 'Sin dato')

    def configurar_escala(self):
        if not self.verificar_permiso_edicion():return
        from escala import thresholds,save_thresholds
        current=thresholds(self._db_path);values=[]
        for name,value in zip(('B','A','AD'),current):
            item=simpledialog.askfloat('Escala de logro',f'Nota mínima para {name}:',initialvalue=value,minvalue=0,maxvalue=20)
            if item is None:return
            values.append(item)
        if not messagebox.askyesno('Confirmar escala','Cambiarán los niveles de logro mostrados para el nivel educativo activo. Las notas numéricas y ponderaciones se conservarán. ¿Aplicar?'):return
        storage.backup_database(self._db_path,'antes-cambiar-escala');save_thresholds(self._db_path,values)
        self.recargar_matriz_completa()

    def reporte_individual(self):
        import db
        students=db.obtener_estudiantes_filtrados(self.combo_grado_global.get(),self.combo_seccion_global.get())
        if not students:return
        choice=simpledialog.askinteger('Reporte individual','\n'.join(f"{i+1}. {s['Apellidos']}, {s['Nombres']}" for i,s in enumerate(students)),minvalue=1,maxvalue=len(students))
        if choice:
            path=filedialog.asksaveasfilename(defaultextension='.pdf',filetypes=[('Reporte individual PDF','*.pdf')])
            if path:reportes.export_grades(path,self._db_path,self.obtener_curso_activo_id(),self.combo_grado_global.get(),self.combo_seccion_global.get(),self.insignia_exportacion(),student=students[choice-1]['ID'])
