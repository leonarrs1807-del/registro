"""Portable grade exports and institutional branding, with no database writes."""
import csv
import io
import json
from pathlib import Path
from contextlib import closing
import sqlite3
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from PIL import Image


def save_logo(source, db_path):
    # Store the actual image in the database, so backups/period copies keep it.
    with Image.open(source) as original:
        if original.format not in ('PNG','JPEG') or max(original.size)>4096:
            raise ValueError('Seleccione una imagen PNG o JPEG de hasta 4096 píxeles por lado.')
        original.load()
        image = original.convert('RGBA')
        image.thumbnail((512, 512))
        stream = io.BytesIO(); image.save(stream, format='PNG')
    from db import obtener_conexion
    with obtener_conexion(db_path) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS Colegio_Insignia (id INTEGER PRIMARY KEY CHECK(id=1), imagen BLOB NOT NULL)')
        conn.execute('INSERT OR REPLACE INTO Colegio_Insignia VALUES(1,?)', (stream.getvalue(),))


def logo_bytes(db_path):
    from db import obtener_conexion
    with obtener_conexion(db_path) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='Colegio_Insignia'").fetchone():
            return None
        row = conn.execute('SELECT imagen FROM Colegio_Insignia WHERE id=1').fetchone()
        return row[0] if row else None


def decorate_workbook(path, logo=None):
    wb = openpyxl.load_workbook(path)
    for ws in wb:
        ws.sheet_view.zoomScale = 110
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.paperSize = ws.PAPERSIZE_A3
        ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0
        ws.print_options.horizontalCentered = True
        if ws.max_row >= 3:
            ws.print_title_rows = '1:3'
        for row in ws:
            for cell in row:
                if cell.value is not None:
                    cell.alignment = Alignment(horizontal=cell.alignment.horizontal or 'left', vertical='center', wrap_text=True)
        if logo:
            from openpyxl.drawing.image import Image as ExcelImage
            picture = ExcelImage(io.BytesIO(logo))
            factor=min(65/picture.width,65/picture.height);picture.width*=factor;picture.height*=factor
            ws.add_image(picture, 'A1')
            ws.row_dimensions[1].height = max(ws.row_dimensions[1].height or 0, 56)
            # Preserve template cells and CAP_ID headers; reserve room in the title.
            if isinstance(ws['A1'].value, str):
                ws['A1'].alignment=Alignment(horizontal='left',vertical='center',wrap_text=True,indent=5)
    wb.save(path)


def grade_rows(db_path, course, grade, section):
    """Long format preserves permanent IDs and full names without merged cells."""
    from db import obtener_conexion
    with obtener_conexion(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute('''SELECT e.ID AS estudiante_id, e.Codigo_Unico AS codigo,
            e.Apellidos AS apellidos, e.Nombres AS nombres, e.Grado AS grado, e.Seccion AS seccion,
            c.nombre AS curso, co.nombre AS competencia, ca.id AS capacidad_id, ca.nombre AS capacidad,
            s.id AS actividad_id, s.titulo_tema AS actividad, s.fecha, s.categoria, s.peso_clase AS peso,
            n.nota, CASE WHEN a.asistio=1 THEN 'Presente' WHEN a.asistio=0 THEN 'Ausente' ELSE 'Sin registrar' END AS asistencia,
            COALESCE(a.comentario,'') AS comentario
            FROM Sesiones_Clase s JOIN Cursos c ON c.id=s.curso_id
            JOIN Competencias co ON co.id=s.competencia_id
            JOIN Sesion_Capacidades sc ON sc.sesion_id=s.id JOIN Capacidades ca ON ca.id=sc.capacidad_id
            JOIN Estudiantes e ON e.Grado=s.grado AND e.Seccion=s.seccion AND e.nivel=s.nivel
            LEFT JOIN Notas_Sesion_Capacidad n ON n.sesion_id=s.id AND n.estudiante_id=e.ID AND n.capacidad_id=ca.id
            LEFT JOIN Asistencia_Y_Comentarios_Clase a ON a.sesion_id=s.id AND a.estudiante_id=e.ID
            WHERE s.curso_id=? AND (?='Todos' OR s.grado=?) AND (?='Todas' OR s.seccion=?)
            ORDER BY e.Apellidos,e.Nombres,s.fecha,s.id,ca.id''', (course,grade,grade,section,section))]


def safe_text(value):
    if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):
        return "'"+value
    return value


def export_grades(path, db_path, course, grade, section, logo=None, student=None):
    import db
    path = Path(path)
    rows = grade_rows(db_path,course,grade,section)
    if student is not None:rows=[r for r in rows if r["estudiante_id"]==student]
    fields = ['estudiante_id','codigo','apellidos','nombres','grado','seccion','curso','competencia','capacidad_id','capacidad','actividad_id','actividad','fecha','categoria','peso','nota','asistencia','comentario']
    if path.suffix.lower()=='.pdf':
        export_pdf(path,rows,db.obtener_docente_config(db_path),logo)
        return len(rows)
    if path.suffix.lower()=='.csv':
        # UTF-8 BOM and numeric columns work in Excel and Google Sheets.
        with path.open('w',encoding='utf-8-sig',newline='') as out:
            writer=csv.writer(out);writer.writerow(fields)
            writer.writerows([safe_text(row[f]) for f in fields] for row in rows)
        return len(rows)
    if path.suffix.lower()=='.json':
        path.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        return len(rows)
    if path.suffix.lower()!='.xlsx':
        raise ValueError('Seleccione XLSX, CSV, PDF o JSON.')
    wb=openpyxl.Workbook();ws=wb.active;ws.title='Calificativos'
    ws.append(fields)
    for row in rows:ws.append([safe_text(row[f]) for f in fields])
    ws.freeze_panes='G2';ws.auto_filter.ref=ws.dimensions
    for cell in ws[1]:
        cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='1E3A8A')
    for i,name in enumerate(fields,1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width=48 if name in ('competencia','capacidad','comentario') else 22
    estructura,matriz=db.calcular_matriz_competencias_y_capacidades(course,grade,section,db_path=db_path)
    summary=wb.create_sheet('Resumen')
    summary.append(['ID permanente','Código','Apellidos','Nombres','Promedio','Nivel','Capacidades pendientes'])
    for row in matriz:summary.append([row['estudiante_id'],row['codigo_unico'],row['apellidos'],row['nombres'],row['promedio_general'],row['literal_general'],row['faltan_capacidades']])
    summary.freeze_panes='E2';summary.auto_filter.ref=summary.dimensions
    for col in 'ABCDEFG':summary.column_dimensions[col].width=26
    if logo:
        branding=wb.create_sheet('Institución');branding['B1']=db.obtener_docente_config(db_path).get('institucion','Institución')
        from openpyxl.drawing.image import Image as ExcelImage
        picture=ExcelImage(io.BytesIO(logo));factor=min(96/picture.width,96/picture.height);picture.width*=factor;picture.height*=factor;branding.add_image(picture,'B3')
    wb.save(path)
    return len(rows)


def save_figure(fig,path,logo=None):
    extra=None
    if logo:
        import matplotlib.image as mpimg
        extra=fig.add_axes([.91,.92,.065,.065],label='insignia_exportacion');extra.imshow(mpimg.imread(io.BytesIO(logo)));extra.axis('off')
    try:fig.savefig(path,bbox_inches='tight',dpi=160)
    finally:
        if extra is not None:extra.remove()


def import_grades(path,db_path):
    """Reimport the long-format export by permanent IDs, atomically."""
    import db
    from db_safety import connection,valid_number
    path=Path(path)
    if path.suffix.lower()=='.csv':
        with path.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    else:
        wb=openpyxl.load_workbook(path,data_only=True,read_only=True)
        try:
            sheet=wb['Calificativos'] if 'Calificativos' in wb.sheetnames else wb.active
            raw=sheet.iter_rows(values_only=True);headers=next(raw)
            rows=[dict(zip(headers,row)) for row in raw if any(v is not None for v in row)]
        finally:wb.close()
    grouped={};seen=set()
    with connection(db_path) as conn:
        for number,row in enumerate(rows,2):
            try:
                sid,eid,cid=(int(row[k]) for k in ('actividad_id','estudiante_id','capacidad_id'))
                key=(sid,eid,cid)
                if key in seen:raise ValueError('Calificación duplicada.')
                seen.add(key)
                student=conn.execute('SELECT Nombres,Apellidos,nivel FROM Estudiantes WHERE ID=?',(eid,)).fetchone()
                active=db.obtener_docente_config(db_path).get('nivel_educativo','Secundaria')
                if not student or student[0]!=row.get('nombres') or student[1]!=row.get('apellidos') or student[2]!=active:
                    raise ValueError('El ID no coincide con el estudiante o nivel activo.')
                raw=row.get('nota');note=None if raw in (None,'') else valid_number(str(raw).replace(',','.'))
                entry=grouped.setdefault((sid,eid),dict(estudiante_id=eid,notas_por_capacidad={},asistio=row.get('asistencia')!='Ausente',preservar_asistencia=row.get('asistencia') not in ('Presente','Ausente'),comentario=row.get('comentario') or ''))
                entry['notas_por_capacidad'][cid]=note
            except (ValueError,TypeError,KeyError) as exc:raise ValueError(f'Fila {number}: {exc}') from exc
        for (sid,eid),data in grouped.items():db.guardar_calificaciones_y_asistencia_sesion(sid,[data],db_path=db_path)
    return len(rows)


def export_pdf(path,rows,config,logo=None):
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.figure import Figure
    from textwrap import fill
    columns=[('codigo',10),('apellidos',18),('nombres',18),('actividad',24),('capacidad',42),('nota',8),('asistencia',12)]
    pages=[];page=[];used=0
    for row in rows:
        cells=[fill('Sin evaluar' if key=='nota' and row[key] is None else str(row[key]),width) for key,width in columns]
        lines=max(cell.count('\n')+1 for cell in cells)
        if page and used+lines+1>28:pages.append(page);page=[];used=0
        page.append((cells,lines));used+=lines+1
    if page or not pages:pages.append(page)
    with PdfPages(path) as pdf:
        for number,page in enumerate(pages,1):
            fig=Figure(figsize=(11.7,8.3));ax=fig.add_axes([.035,.1,.93,.77]);ax.axis('off')
            fig.suptitle(config.get('institucion','Institución educativa')+'\nRegistro de calificativos',fontsize=14)
            fig.text(.04,.88,config.get('nombres_docente','Docente'),fontsize=10)
            fig.text(.5,.035,f'Página {number} de {len(pages)}',ha='center',fontsize=9)
            if logo:
                import matplotlib.image as mpimg
                image=fig.add_axes([.88,.89,.07,.08]);image.imshow(mpimg.imread(io.BytesIO(logo)));image.axis('off')
            if page:
                table=ax.table(cellText=[cells for cells,_ in page],colLabels=['Código','Apellidos','Nombres','Actividad','Capacidad','Nota','Asistencia'],colWidths=[.08,.14,.14,.18,.27,.07,.12],loc='upper center',cellLoc='left')
                table.auto_set_font_size(False);table.set_fontsize(8)
                for (i,j),cell in table.get_celld().items():
                    cell.set_height(.05 if i==0 else (page[i-1][1]+1)*.025)
                    if i==0:cell.set_facecolor('#1e3a8a');cell.get_text().set_color('white')
            else:ax.text(.5,.5,'Sin calificativos para el filtro elegido.',ha='center')
            pdf.savefig(fig)
