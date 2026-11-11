"""Load another school document into the existing desktop window."""
import os
from pathlib import Path
import tkinter as tk

import app_storage as storage
import db
import institucion
import periodos
from app_version import VERSION


def _clear_document(app):
    # Numeric identities can be identical in two schools. Never reuse a model
    # merely because its student, session or course ID happens to match.
    if getattr(app,'_evaluation_expanded',False):app.set_evaluation_expanded(False)
    for name in ('_page_refresh_job','_stats_resize_job','_plot_resize_job','_tools_resize_job','_draft_offer_job'):
        timer=getattr(app,name,None)
        if timer:
            try:app.after_cancel(timer)
            except tk.TclError:pass
            setattr(app,name,None)
    for child in list(app.winfo_children()):
        if isinstance(child,(tk.Toplevel,)):
            child.destroy()
    for name in ('_embedded_evaluation','_global_grade_panel'):
        panel=getattr(app,name,None)
        if panel and panel.winfo_exists():panel.destroy()
        setattr(app,name,None)
    app.id_estudiante_sel=None
    app.id_actividad_editando=None
    app.id_actividad_calificando=None
    app._planilla_pendiente=False
    app._formularios_pendientes.clear()
    app._undo=[];app._redo=[]
    app._instrument_pending={};app._instrument_pending_session=None
    app._cotejo_pending_rule=None
    app._loaded_instrument_kind=None;app._loaded_ind_count=0
    app._embedded_signature=None;app._evaluation_view=None
    app._table_context=None;app._ultimo_estado_planilla=None
    app._graph_state=None;app._view_pending={}
    app._plot_data=None;app._plot_widths={}
    for figure in getattr(app,'figuras_porcentajes',[]):figure.clear()
    app.figuras_porcentajes=[]
    for host in getattr(app,'graficos_hosts',[]):
        for child in host.winfo_children():child.destroy()
    if hasattr(app,'fig_actual'):app.fig_actual.clear()
    if hasattr(app,'datos_matriz_actual'):del app.datos_matriz_actual
    app._datos_estudiantes=[];app._capacidades_actividad=[]
    app.actividades_creadas_map={}
    app.combo_calif_etiqueta_a_id={}
    app.entries_pesos_individuales_cat=[]
    points=getattr(app,'puntos_panel',None)
    if points:
        points.pending=False;points._context=None;points.block_id=None
        points.data=None;points._block_map={}
        for child in points.table_host.winfo_children():child.destroy()
        points.grid_view=None
        points.listing.delete(0,'end');points.status.configure(text='')
    for name in ('est_entry_nombres','est_entry_apellidos','entry_buscar_est','busc_entry_alumno'):
        getattr(app,name).delete(0,'end')
    app.busc_txt_comentario_detalle.configure(state='normal')
    app.busc_txt_comentario_detalle.delete('1.0','end')
    app.busc_txt_comentario_detalle.configure(state='disabled')
    app.btn_est_actualizar.configure(state='disabled')
    app.btn_est_eliminar.configure(state='disabled')
    app.est_combo_estado.set('Activo')
    app.unit_filter.set('Todas las unidades');app._last_unit_filter='Todas las unidades'
    app.crear_combo_unidad.set('Sin unidad')


def _reload_document(app):
    config=db.obtener_docente_config()
    app.combo_nivel.set(config.get('nivel_educativo','Secundaria'))
    if app.licensing and app.licensing.state:app.sincronizar_cuenta()
    app.edicion_desbloqueada=False
    app.actualizar_visual_candado_y_docente()
    app.recargar_cursos_y_contexto()
    app.est_entry_grado.set(app.combo_grado_global.get())
    app.est_entry_seccion.set(app.combo_seccion_global.get())
    app.accion_limpiar_formulario_actividad()
    data=institucion.profile(app._db_path)
    for key,entry in app._institution_entries.items():
        entry.delete(0,'end');entry.insert(0,data[key])
    app.actualizar_insignia();app.actualizar_configuracion()
    app.title(f'Registro Docente {VERSION} · {"Comercial" if app._license_required else "Full personal"} — {app._db_path.stem}')
    current=periodos.info(app._db_path)
    app.lbl_estado.configure(text=f"{current['school_name']} · {current['label']} · Edición bloqueada")


def open_document(app,path):
    """Validate first; keep the window, prepared pages and saved data alive."""
    if not app.confirmar_descartar(include_points=True):return False
    target=Path(path).resolve()
    previous=db.DB_PATH
    # These operations precede UI changes: an invalid file leaves the current
    # table and pending document context intact. Initialization creates a backup.
    storage.validate_database(target)
    db.inicializar_db(db_path=target)
    storage.validate_database(target)
    app.configure(cursor='watch');app.update_idletasks()
    try:
        _clear_document(app)
        db.DB_PATH=target
        os.environ['REGISTRO_DB_PATH']=str(target)
        _reload_document(app)
        if target.parent==storage.data_dir().resolve():storage.activate_period(target)
    except Exception:
        db.DB_PATH=previous
        os.environ['REGISTRO_DB_PATH']=str(previous)
        _clear_document(app)
        _reload_document(app)
        if previous.exists() and previous.parent==storage.data_dir().resolve():storage.activate_period(previous)
        raise
    finally:app.configure(cursor='')
    # Existing autosave and inactivity timers continue using the active path.
    app._draft_offer_job=app.after(250,app._ofrecer_borrador)
    return True
