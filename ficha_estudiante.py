"""A student snapshot uses saved grades from one school document only."""
import sqlite3
from db_safety import connection
import db,periodos


def snapshot(path,student,course):
    with connection(path) as conn:
        conn.row_factory=sqlite3.Row
        row=conn.execute('SELECT * FROM Estudiantes WHERE ID=?',(student,)).fetchone()
        area=conn.execute('SELECT nombre,nivel FROM Cursos WHERE id=?',(course,)).fetchone()
        if not row or not area or row['nivel']!=area['nivel']:raise ValueError('Seleccione un estudiante del nivel y curso actuales.')
        pupil=dict(row)
        activities=[dict(r) for r in conn.execute('''SELECT s.id,s.fecha,s.titulo_tema,s.categoria,s.unidad_id,
            COALESCE(u.nombre,'Sin unidad') AS unidad,p.nombre AS competencia,
            a.asistio,a.comentario FROM Sesiones_Clase s JOIN Competencias p ON p.id=s.competencia_id
            LEFT JOIN Unidades_Didacticas u ON u.id=s.unidad_id
            LEFT JOIN Asistencia_Y_Comentarios_Clase a ON a.sesion_id=s.id AND a.estudiante_id=?
            WHERE s.curso_id=? AND s.grado=? AND s.seccion=? AND s.nivel=?
            ORDER BY s.fecha,s.id''',(student,course,pupil['Grado'],pupil['Seccion'],pupil['nivel']))]
        notes={}
        for r in conn.execute('''SELECT n.sesion_id,c.nombre,n.nota FROM Notas_Sesion_Capacidad n
            JOIN Capacidades c ON c.id=n.capacidad_id WHERE n.estudiante_id=?''',(student,)):
            notes.setdefault(r[0],[]).append(dict(capacidad=r[1],nota=r[2]))
        criteria={r[0]:r[1] for r in conn.execute('''SELECT r.sesion_id,COUNT(*) FROM Instrumento_Respuestas r
            JOIN Instrumento_Indicadores i ON i.id=r.indicador_id WHERE r.estudiante_id=? AND i.activo=1 GROUP BY r.sesion_id''',(student,))}
    structure,matrix=db.calcular_matriz_competencias_y_capacidades(course,pupil['Grado'],pupil['Seccion'],db_path=path)
    result=next(r for r in matrix if r['estudiante_id']==student)
    units=[]
    for unit in periodos.units(path)+[dict(id=None,nombre='Sin unidad')]:
        if not any(a['unidad_id']==unit['id'] for a in activities):continue
        _,rows=db.calcular_matriz_competencias_y_capacidades(course,pupil['Grado'],pupil['Seccion'],db_path=path,unidad_id=unit['id'])
        summary=next(r for r in rows if r['estudiante_id']==student)
        related=[a for a in activities if a['unidad_id']==unit['id']]
        units.append(dict(id=unit['id'],nombre=unit['nombre'],promedio=summary['promedio_general'],
            actividades=len(related),evaluadas=sum(any(n['nota'] is not None for n in notes.get(a['id'],[])) or bool(criteria.get(a['id'])) for a in related)))
    for activity in activities:
        activity['notas']=notes.get(activity['id'],[]);activity['criterios_evaluados']=criteria.get(activity['id'],0)
    attendance=[a['asistio'] for a in activities if a['asistio'] is not None]
    return dict(estudiante=pupil,curso=area['nombre'],contexto=periodos.info(path),matriz=result,estructura=structure,
        unidades=units,actividades=activities,asistencias=sum(bool(v) for v in attendance),asistencias_registradas=len(attendance))


def export_excel(destination,data,path,mode='ambos'):
    from pathlib import Path
    if Path(destination).suffix.lower()!='.xlsx':raise ValueError('Guarde la ficha con extensión .xlsx.')
    from openpyxl import Workbook
    from openpyxl.styles import Font,PatternFill,Alignment
    from presentacion import format_grade
    from colores import HEADER,HEADER_TEXT
    wb=Workbook();pupil=data['estudiante'];ws=wb.active;ws.title='Ficha del estudiante'
    shown=lambda note:note if mode=='numero' and note is not None else format_grade(note,mode,path)
    ws.append([data['contexto']['school_name']]);ws.append([pupil['Apellidos']+', '+pupil['Nombres']])
    ws.append([data['contexto']['label'],data['curso'],pupil['Grado']+' '+pupil['Seccion']])
    ws.append(['Unidad','Resultado','Actividades evaluadas','Actividades registradas'])
    for unit in data['unidades']:ws.append([unit['nombre'],shown(unit['promedio']),unit['evaluadas'],unit['actividades']])
    detail=wb.create_sheet('Evaluaciones');detail.append(['Fecha','Actividad','Unidad','Competencia','Capacidad','Resultado','Asistencia','Comentario'])
    for activity in data['actividades']:
        attendance='Sin registrar' if activity['asistio'] is None else 'Presente' if activity['asistio'] else 'Ausente'
        for note in activity['notas'] or [dict(capacidad='Evidencias observadas',nota=None)]:
            detail.append([activity['fecha'],activity['titulo_tema'],activity['unidad'],activity['competencia'],note['capacidad'],
                shown(note['nota']),attendance,activity['comentario'] or ''])
    for sheet,header in ((ws,4),(detail,1)):
        sheet.freeze_panes=f'B{header+1}';sheet.auto_filter.ref=f'A{header}:{sheet.cell(sheet.max_row,sheet.max_column).coordinate}'
        for cell in sheet[header]:cell.fill=PatternFill('solid',fgColor=HEADER.lstrip('#'));cell.font=Font(bold=True,color=HEADER_TEXT.lstrip('#'))
        for cells in sheet:
            for cell in cells:
                cell.alignment=Alignment(vertical='top',wrap_text=True)
                if isinstance(cell.value,str):cell.data_type='s'
        for col in range(1,sheet.max_column+1):sheet.column_dimensions[sheet.cell(1,col).column_letter].width=42 if col in (1,2,4,5,8) else 22
    wb.save(destination);wb.close()
