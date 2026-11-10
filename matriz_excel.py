"""Final matrix with selectable numeric/literal display and exact round trips."""
import json,re
import openpyxl
from openpyxl.styles import Font,PatternFill,Alignment
from excel_tablas import put,_meta,_table_style,metadata,grade_display,read_grade,find_or_create,student_id,text
from escala import thresholds
from instrumentos import normalized
from db_safety import connection


class MatrixImportResult(tuple):
    def __new__(cls,students,notes,changes):
        result=super().__new__(cls,(students,notes));result.changes=changes;return result


def safe_filename(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(name))[:160]+'.xlsx'


def export_matrix(destination,course,grade,section,structure,rows,path,presentation,unidad_id="all",alcance="Periodo completo"):
    limits=thresholds(path);wb=openpyxl.Workbook();ws=wb.active;ws.title='Matriz final';columns=[];col=3
    import periodos
    context=periodos.info(path)
    put(ws,1,1,f"{context['school_name']} · {context['label']} · {alcance}\nRegistro general · {course} · {grade} {section}")
    put(ws,2,1,'N°');put(ws,2,2,'Apellidos y nombres');ws.merge_cells('A2:A3');ws.merge_cells('B2:B3')
    for comp in structure:
        first=col
        for cap in comp['capacidades']:
            put(ws,3,col,cap['capacidad_nombre']);columns.append(dict(col=col,competency=comp['competencia_nombre'],capacity=cap['capacidad_nombre'],cap_id=cap['capacidad_id'],comp_id=comp['competencia_id'],role='cap'));col+=1
        put(ws,3,col,'Promedio de competencia');columns.append(dict(col=col,comp_id=comp['competencia_id'],role='comp'));col+=1
        if col-1>first:ws.merge_cells(start_row=2,start_column=first,end_row=2,end_column=col-1)
        put(ws,2,first,comp['competencia_nombre'])
    final_col=col;put(ws,2,final_col,'Promedio final');ws.merge_cells(start_row=2,start_column=final_col,end_row=3,end_column=final_col)
    originals={}
    for index,row in enumerate(rows,4):
        name=f"{row['apellidos']}, {row['nombres']}";put(ws,index,1,f'{index-3:02}');put(ws,index,2,name)
        originals[name]={}
        for item in columns:
            value=row['notas_capacidad'].get(item['cap_id']) if item['role']=='cap' else row['notas_competencia'].get(item['comp_id'])
            shown=grade_display(value,presentation,limits);put(ws,index,item['col'],shown)
            if item['role']=='cap':originals[name][str(item['col'])]=[value,shown]
        put(ws,index,final_col,grade_display(row.get('promedio_general'),presentation,limits))
    _table_style(ws,{1,2,3},4,max(4,ws.max_row),limits,range(3,final_col+1));ws.freeze_panes='C4'
    ws.row_dimensions[2].height=58;ws.row_dimensions[3].height=90;ws.auto_filter.ref=f'A3:{openpyxl.utils.get_column_letter(final_col)}{max(4,ws.max_row)}'
    ws.merge_cells(start_row=1,start_column=1,end_row=1,end_column=final_col)
    with connection(path) as conn:level=conn.execute('SELECT nivel_educativo FROM Docente_Config WHERE id=1').fetchone()[0]
    _meta(wb,dict(format='registro-matriz',version=2,course=course,level=level,grade=grade,section=section,presentation=presentation,columns=columns,originals=originals,school_id=context['school_id'],year=context['year'],period=context['number'],scheme=context['scheme'],unit_scope=unidad_id,scope_name=alcance))
    from institucion import decorate
    decorate(wb,path)
    wb.save(destination);wb.close()


def import_matrix(wb,path,default_grade,default_section):
    import db
    meta=metadata(wb);changes=[];ws=wb['Matriz final'] if 'Matriz final' in wb else wb.active
    import periodos
    context=periodos.info(path)
    if meta.get('school_id') and meta['school_id']!=context['school_id']:raise ValueError('La matriz pertenece a otro colegio. Seleccione ese colegio antes de importar sus notas.')
    if meta.get('year') and (meta['year'],meta.get('period'),meta.get('scheme'))!=(context['year'],context['number'],context['scheme']):raise ValueError('La matriz pertenece a otro periodo. Seleccione su bimestre o trimestre.')
    if 'unit_scope' in meta and meta['unit_scope']!='all':raise ValueError('Esta plantilla resume una unidad. Importe las notas en las plantillas de sus actividades para conservar el cálculo del periodo.')
    grade=meta.get('grade') or default_grade;section=meta.get('section') or default_section
    if (default_grade not in ('Todos',grade) or default_section not in ('Todas',section)):raise ValueError('La matriz pertenece a otro salón.')
    with connection(path) as conn:
        level=db.obtener_docente_config(path)['nivel_educativo']
        if meta.get('level')!=level:raise ValueError('Seleccione el nivel educativo de la matriz antes de importarla.')
        courses=[r[0] for r in conn.execute('SELECT id,nombre FROM Cursos WHERE nivel=?',(level,)) if normalized(r[1])==normalized(meta.get('course'))]
        if len(courses)!=1:raise ValueError('Seleccione o cree primero el curso de la matriz: '+str(meta.get('course')))
        course=courses[0];columns=json.loads(meta['columns']);originals=json.loads(meta.get('originals','{}'));mapped={};competencies={}
        for item in columns:
            if item['role']!='cap':continue
            # Stored names remain complete even when competency headers are merged.
            comp_name=item['competency'];cap_name=text(ws.cell(3,item['col']).value) or item['capacity']
            competency=find_or_create(conn,'Competencias','curso_id',course,comp_name,changes)
            cap=find_or_create(conn,'Capacidades','competencia_id',competency,cap_name,changes);mapped[item['col']]=cap;competencies[cap]=competency
        used=set();students=0;notes=0
        for row in range(4,ws.max_row+1):
            name=text(ws.cell(row,2).value)
            if not name:continue
            sid=student_id(conn,name,grade,section,path,changes)
            if sid in used:raise ValueError('Estudiante repetido en la matriz: '+name)
            used.add(sid);students+=1
            for col,cap in mapped.items():
                value=ws.cell(row,col).value;prior=originals.get(name,{}).get(str(col),[None,None])
                try:note=read_grade(value,*prior)
                except ValueError as exc:raise ValueError(f'Fila {row}, columna {col}: {exc}') from exc
                if note is None:continue
                conn.execute('''INSERT INTO Notas_Manuales_Capacidad(estudiante_id,capacidad_id,nota_manual) VALUES(?,?,?)
                    ON CONFLICT(estudiante_id,capacidad_id) DO UPDATE SET nota_manual=excluded.nota_manual''',(sid,cap,note));notes+=1
        return MatrixImportResult(students,notes,changes)
