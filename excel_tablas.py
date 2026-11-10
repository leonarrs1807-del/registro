"""Readable, editable classroom tables with portable curriculum names."""
import json,re,textwrap
from pathlib import Path
import openpyxl
from openpyxl.styles import Alignment,Border,Font,PatternFill,Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from db_safety import connection,valid_number
from instrumentos import normalized,definition,validate_definition,answer_points,LEVELS
from evaluacion_datos import activity,get_indicators,get_answers,grade_answers
from grade_cells import achievement,PALETTE
from escala import thresholds
from colores import HEADER,HEADER_TEXT,BORDER

META='Registro_Meta'
GLOBAL='Desempeño global de esta capacidad'

class ImportResult(tuple):
    def __new__(cls,criteria,students,session,changes):
        result=super().__new__(cls,(criteria,students));result.session_id=session;result.changes=changes;return result


def text(value):
    return str(value or '').strip()


def put(ws,row,col,value):
    cell=ws.cell(row,col,value)
    if isinstance(value,str):cell.data_type='s'
    return cell


def grade_display(value,style,limits):
    if value is None:return None
    number=valid_number(value);level=achievement(number,limits)
    if style=='numero':return number
    if style=='letra':return level
    if style=='ambos':return f'{number:g} ({level})'
    raise ValueError('Elija números, letras o ambos.')


def read_grade(value,original=None,display=None):
    if value is None or normalized(value) in ('','pendiente','sin evaluar','falta','-'):return None
    if isinstance(value,str) and value.strip().upper() in LEVELS:
        if original is not None and text(value).upper()==text(display).upper():return valid_number(original)
        raise ValueError('Una letra no determina una nota numérica exacta. Escriba el número o número (letra) para cambiarla.')
    match=re.fullmatch(r'\s*(\d+(?:[.,]\d+)?)\s*(?:\((?:C|B|A|AD)\))?\s*',str(value),re.I)
    if not match:raise ValueError('Escriba una nota entre 0 y 20.')
    return valid_number(match[1].replace(',','.'))


def metadata(wb):
    return {row[0]:row[1] for row in wb[META].iter_rows(max_col=2,values_only=True)} if META in wb else {}


def _meta(wb,values):
    ws=wb.create_sheet(META)
    for row,(key,value) in enumerate(values.items(),1):
        put(ws,row,1,key);put(ws,row,2,json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else value)
    ws.sheet_state='veryHidden'


def _table_style(ws,header_rows,start,last,limits,grade_cols=()):
    ws.sheet_view.showGridLines=False;ws.sheet_view.zoomScale=100
    ws.freeze_panes=f'C{start}';ws.sheet_view.topLeftCell='A1'
    edge=Side(style='thin',color='CBD5E1')
    for row in ws:
        for c in row:
            c.alignment=Alignment(vertical='center',wrap_text=True,horizontal='left' if c.column==2 else 'center')
            c.font=Font(name='Calibri',size=11,bold=c.column in grade_cols)
            if c.row in header_rows:
                c.fill=PatternFill('solid',fgColor=HEADER[1:]);c.font=Font(name='Calibri',size=11,bold=True,color=HEADER_TEXT[1:])
            elif c.row>=start:
                c.border=Border(left=edge,right=edge,top=edge,bottom=edge)
                if c.row%2==0:c.fill=PatternFill('solid',fgColor='F8FAFC')
                if c.column in grade_cols and c.value is not None:
                    try:level=str(c.value) if str(c.value) in LEVELS else achievement(read_grade(c.value),limits)
                    except ValueError:level=None
                    if level:
                        bg,fg=PALETTE[level];c.fill=PatternFill('solid',fgColor=bg[1:]);c.font=Font(name='Calibri',size=11,bold=True,color=fg[1:])
    for col in range(1,ws.max_column+1):ws.column_dimensions[get_column_letter(col)].width=6 if col==1 else 34 if col==2 else 26
    for row in header_rows:ws.row_dimensions[row].height=56 if row>1 else 30
    for row in range(start,last+1):ws.row_dimensions[row].height=27
    ws.print_options.horizontalCentered=True;ws.sheet_properties.pageSetUpPr.fitToPage=True
    ws.page_setup.orientation='landscape';ws.page_setup.paperSize=ws.PAPERSIZE_A3;ws.page_setup.fitToWidth=1;ws.page_setup.fitToHeight=0
    ws.print_title_rows=f'1:{start-1}';ws.print_area=f'A1:{get_column_letter(ws.max_column)}{max(start,last)}'


def export_activity(destination,session,path,answers=None,grades=None,roster=None,include_summary=False,library=False):
    import db
    context=activity(session,path);items=get_indicators(session,path);kind=context['tipo_instrumento'];raw=kind!='Normal' and bool(items)
    if library:roster=[]
    if roster is None:roster=db.obtener_estudiantes_filtrados(context['grado'],context['seccion'],'',db_path=path)
    saved=get_answers(session,path)
    if answers is not None:saved.update(answers)
    with connection(path) as conn:
        course,level=conn.execute('SELECT nombre,nivel FROM Cursos WHERE id=?',(context['curso_id'],)).fetchone()
        notes={(s,c):n for s,c,n in conn.execute('SELECT estudiante_id,capacidad_id,nota FROM Notas_Sesion_Capacidad WHERE sesion_id=?',(session,))}
        comments=dict(conn.execute('SELECT estudiante_id,comentario FROM Asistencia_Y_Comentarios_Clase WHERE sesion_id=?',(session,)))
    if grades is not None:notes.update(grades)
    wb=openpyxl.Workbook();ws=wb.active;ws.title='Registro';design=wb.create_sheet('Instrumento');limits=thresholds(path)
    if not raw:items=[definition(dict(capacidad_id=c['capacidad_id'],capacidad_nombre=c['capacidad_nombre'],criterio=c['criterio_precisado'] or GLOBAL,tipo='Rúbrica',puntaje_maximo=20),limits) for c in context['capacidades']]
    put(design,1,1,('Rúbrica' if kind=='Rúbrica' else 'Lista de cotejo' if kind=='Lista de Cotejo' else 'Notas de la actividad')+' · '+context['titulo_tema']);put(design,2,1,'Curso / aula / fecha');put(design,2,2,f"{course} · {context['grado']} {context['seccion']} · {context['fecha']}")
    put(design,3,1,'Competencia');put(design,3,2,context['competencia_nombre']);put(design,4,1,'Propósito de la clase');put(design,4,2,context.get('proposito') or '')
    headers=['Capacidad','Criterio','Máximo','C · Descriptor','B · Descriptor','A · Descriptor','AD · Descriptor','C · Puntos','B · Puntos','A · Puntos','AD · Puntos']
    design.append([])
    for col,value in enumerate(headers,1):put(design,6,col,value)
    for n,item in enumerate(items,7):
        row=[item['capacidad_nombre'],item['criterio'],item['puntaje_maximo'],*[item['descriptores'][l] for l in LEVELS],*[item['puntajes'][l] for l in LEVELS]]
        for col,value in enumerate(row,1):put(design,n,col,value)
        put(design,n,12,'i'+str(n-7))
    _table_style(design,{1,6},7,design.max_row,limits)
    design.merge_cells('A1:K1');design.merge_cells('B2:K2');design.merge_cells('B3:K3');design.merge_cells('B4:K4')
    design.row_dimensions[2].height=27;design.row_dimensions[3].height=36
    design.column_dimensions['C'].width=10
    for col in 'HIJK':design.column_dimensions[col].hidden=True
    design.column_dimensions['L'].hidden=True
    design.freeze_panes='C7';design.column_dimensions['A'].width=35;design.column_dimensions['B'].width=46
    if kind!='Rúbrica':
        for col in range(3,12):design.column_dimensions[get_column_letter(col)].hidden=True
    put(ws,1,1,context['titulo_tema']);put(ws,2,1,'Competencia: '+context['competencia_nombre'])
    put(ws,3,1,'Propósito: '+(context.get('proposito') or ''))
    put(ws,4,1,'N°');put(ws,4,2,'Apellidos y nombres');keys=[]
    for n,item in enumerate(items):
        col=3+n;key='i'+str(n);keys.append(key)
        put(ws,4,col,item['capacidad_nombre']);put(ws,5,col,('Desempeño global' if normalized(item['criterio'])==normalized(item['capacidad_nombre']) else item['criterio']) if raw else 'Nota final / 20');put(ws,6,col,key)
    count_col=3+len(items)
    put(ws,4,count_col,'Evaluados' if kind!='Lista de Cotejo' else 'Cumple / Evaluados');put(ws,6,count_col,'avance')
    final_cols={}
    if raw and kind=='Rúbrica' and include_summary:
        for cap in context['capacidades']:
            col=count_col+1+len(final_cols);final_cols[cap['capacidad_id']]=col
            put(ws,4,col,cap['capacidad_nombre']);put(ws,5,col,'Nota de capacidad / 20');put(ws,6,col,'resumen')
    comment_col=ws.max_column+1;put(ws,4,comment_col,'Observación');put(ws,6,comment_col,'comentario')
    calculated,pending=grade_answers(items,saved) if raw and kind=='Rúbrica' else ({},set())
    for row_index,student in enumerate(roster,7):
        sid=student['ID'];put(ws,row_index,1,f'{row_index-6:02}');put(ws,row_index,2,f"{student['Apellidos']}, {student['Nombres']}")
        filled=0;yes=0
        for n,item in enumerate(items,3):
            value=saved.get((sid,item.get('id'))) if raw else notes.get((sid,item['capacidad_id']))
            if value is not None:filled+=1;yes+=int(normalized(value)=='si')
            put(ws,row_index,n,value)
        put(ws,row_index,count_col,f'{yes}/{filled}' if kind=='Lista de Cotejo' else f'{filled}/{len(items)}')
        for cap,col in final_cols.items():put(ws,row_index,col,calculated.get((sid,cap)))
        put(ws,row_index,comment_col,comments.get(sid,''))
    ws.row_dimensions[6].hidden=True
    _table_style(ws,{1,2,4,5},7,max(7,ws.max_row),limits,range(3,comment_col))
    for row in (1,2,3):ws.merge_cells(start_row=row,start_column=1,end_row=row,end_column=comment_col)
    ws.row_dimensions[3].height=28
    if raw:
        dv=DataValidation(type='list',formula1='"C,B,A,AD,Sin evidencia"' if kind=='Rúbrica' else '"Sí,No"',allow_blank=True);dv.showErrorMessage=False;ws.add_data_validation(dv)
        for col in range(3,3+len(items)):dv.add(f'{get_column_letter(col)}7:{get_column_letter(col)}2000')
    for row in (1,2,3):ws.cell(row,1).alignment=Alignment(horizontal='left',vertical='center',wrap_text=True)
    ws.row_dimensions[1].height=26;ws.row_dimensions[2].height=32
    ws.row_dimensions[3].height=min(60,max(24,14*len(textwrap.wrap(context.get('proposito') or '',110))+8))
    for row in (4,5):ws.row_dimensions[row].height=min(64,max(28,max(len(textwrap.wrap(str(ws.cell(row,c).value or ''),26)) for c in range(3,ws.max_column+1))*13+8))
    ws.merge_cells('A4:A5');ws.merge_cells('B4:B5')
    design.row_dimensions[1].height=26;design.row_dimensions[4].height=min(70,max(26,14*len(textwrap.wrap(context.get('proposito') or '',100))+8));design.row_dimensions[5].height=5;design.row_dimensions[6].height=32
    for row in range(7,design.max_row+1):design.row_dimensions[row].height=min(110,max(38,max(len(textwrap.wrap(str(design.cell(row,c).value or ''),28)) for c in range(1,8))*13+8))
    _meta(wb,dict(format='registro-tabla',version=6,mode='criterios' if raw else 'notas',kind=kind,course=course,level=level,grade=context['grado'],section=context['seccion'],purpose=context.get('proposito') or '',activity_type=context.get('tipo_actividad','Actividad'),category=context['categoria'],entry_mode=context.get('modo_ingreso','capacidades'),library=bool(library),theme=context['titulo_tema']))
    from institucion import decorate
    decorate(wb,path)
    wb.active=0;wb.save(destination);wb.close();return len(roster)


def find_or_create(conn,table,parent_col,parent,name,changes):
    name=text(name)
    if not name:raise ValueError('Falta el nombre de '+table.lower()+'.')
    matches=[r[0] for r in conn.execute(f'SELECT id,nombre FROM {table} WHERE {parent_col}=?',(parent,)) if normalized(r[1])==normalized(name)]
    if len(matches)>1:raise ValueError('El nombre es ambiguo: '+name)
    if matches:return matches[0]
    identity=conn.execute(f'INSERT INTO {table}({parent_col},nombre) VALUES(?,?)',(parent,name)).lastrowid
    changes.append(('Competencia' if table=='Competencias' else 'Capacidad')+' nueva: '+name);return identity


def student_id(conn,name,grade,section,path,changes):
    import db
    level=db.obtener_docente_config(path)['nivel_educativo']
    rows=[r[0] for r in conn.execute('SELECT ID,Apellidos,Nombres FROM Estudiantes WHERE Grado=? AND Seccion=? AND nivel=?',(grade,section,level)) if normalized(f'{r[1]}, {r[2]}')==normalized(name)]
    if len(rows)>1:raise ValueError('Hay estudiantes con el mismo nombre. No se puede asignar la nota automáticamente: '+name)
    if rows:return rows[0]
    if ',' not in name:raise ValueError('Para agregar un estudiante, use Apellidos, Nombres: '+name)
    last,first=[v.strip() for v in name.split(',',1)]
    if not last or not first:raise ValueError('Complete apellidos y nombres: '+name)
    identity=db.agregar_estudiante(first,last,grade,section,db_path=path);changes.append('Estudiante nuevo: '+name);return identity


def _value(ws,formulas,row,col):
    value=ws.cell(row,col).value
    if formulas.cell(row,col).data_type=='f' and value is None:raise ValueError(f'Fila {row}: fórmula sin resultado. Recalcule en Excel o pegue valores.')
    return value


def import_activity(wb,formulas,session,grade,section,path):
    import db
    context=activity(session,path);meta=metadata(wb);modern=meta.get('format')=='registro-tabla';changes=[]
    with connection(path) as conn:
        course,level=conn.execute('SELECT nombre,nivel FROM Cursos WHERE id=?',(context['curso_id'],)).fetchone()
        if modern and (normalized(meta.get('course'))!=normalized(course) or meta.get('level')!=level or meta.get('grade')!=grade or (not meta.get('library') and meta.get('section')!=section)):raise ValueError('La tabla pertenece a otro curso, nivel o salón.')
        if (context['grado'],context['seccion'])!=(grade,section):raise ValueError('Seleccione el salón de la actividad.')
        ws=wb['Registro'] if 'Registro' in wb else wb.active;fw=formulas[ws.title]
        mode=meta.get('mode','notas')
        if mode not in ('criterios','notas'):raise ValueError('El formato de la tabla no es válido.')
        kind=meta.get('kind','Normal') if mode=='criterios' else 'Normal'
        if kind not in ('Normal','Rúbrica','Lista de Cotejo'):raise ValueError('Tipo de instrumento no válido.')
        comp_name=text(wb['Instrumento']['B3'].value) if modern and 'Instrumento' in wb else context['competencia_nombre']
        title=text(ws['A1'].value) if modern else context['titulo_tema']
        if modern and title==text(meta.get('branded_title')):title=text(meta.get('source_title'))
        purpose=context.get('proposito','')
        if modern and 'Instrumento' in wb and normalized(wb['Instrumento']['A4'].value).startswith('proposito'):purpose=text(wb['Instrumento']['B4'].value)
        if not comp_name:raise ValueError('Escriba el nombre de la competencia en Instrumento, B3.')
        competency=find_or_create(conn,'Competencias','curso_id',context['curso_id'],comp_name,changes)
        designs=[]
        if modern and 'Instrumento' in wb:
            for row in wb['Instrumento'].iter_rows(min_row=7,values_only=True):
                if row[0]:designs.append(list(row)+[None]*11)
        if modern:
            header=4;start=7;name_col=2
            columns=[]
            for col in range(3,ws.max_column+1):
                key=text(ws.cell(6,col).value);cap=text(ws.cell(4,col).value);criterion=text(ws.cell(5,col).value)
                if key in ('avance','resumen','comentario') or not cap:continue
                if key.startswith('i') and any(text(r[11])==key for r in designs):design=next(r for r in designs if text(r[11])==key)
                else:design=next((r for r in designs if normalized(r[0])==normalized(cap) and normalized(r[1])==normalized(criterion)),[cap,criterion or GLOBAL,20]+[None]*8)
                design=list(design);design[0]=text(design[0]) or cap;design[1]=text(design[1]) or (criterion if mode=='criterios' else '') or GLOBAL
                columns.append((col,design))
        else:
            header=next((r for r in range(1,min(11,ws.max_row+1)) if any(normalized(c.value) in ('estudiante','apellidos y nombres','alumno') for c in ws[r])),None)
            if header is None:raise ValueError('No se encontró la columna Estudiante o Apellidos y nombres. Use la tabla exportada o esos encabezados.')
            name_col=next(c.column for c in ws[header] if normalized(c.value) in ('estudiante','apellidos y nombres','alumno'));start=header+1
            ignored={'n°','nº','nro','numero','codigo','observacion','comentario','asistencia','evaluados','pendientes'}
            columns=[(c.column,[text(c.value),GLOBAL,20]+[None]*8) for c in ws[header] if c.column!=name_col and text(c.value) and normalized(c.value) not in ignored]
            for row in range(1,header):
                for c in ws[row]:
                    if normalized(c.value).rstrip(':')=='competencia' and ws.cell(row,c.column+1).value:comp_name=text(ws.cell(row,c.column+1).value)
                    elif normalized(c.value).startswith('competencia:'):comp_name=text(c.value).split(':',1)[1].strip()
            competency=find_or_create(conn,'Competencias','curso_id',context['curso_id'],comp_name,changes)
        if not columns or len(columns)>100:raise ValueError('La tabla necesita entre 1 y 100 columnas de evaluación.')
        if ws.max_row>2006:raise ValueError('El registro permite hasta 2000 filas por importación.')
        capacity_ids={};definitions=[];column_caps={};used=set()
        for col,design in columns:
            cap_name,criterion=map(text,design[:2]);criterion=criterion or GLOBAL
            cap=find_or_create(conn,'Capacidades','competencia_id',competency,cap_name,changes);capacity_ids[cap]=criterion;column_caps[col]=cap
            if mode=='criterios':
                key=(cap,normalized(criterion))
                if key in used:raise ValueError('Hay dos columnas con el mismo criterio: '+criterion)
                used.add(key)
                item=dict(capacidad_id=cap,criterio=criterion,tipo=kind,puntaje_maximo=20 if design[2] is None or text(design[2])=='' else design[2])
                if kind=='Rúbrica':
                    base=definition(item,thresholds(path));item['descriptores']={l:text(design[3+n]) or base['descriptores'][l] for n,l in enumerate(LEVELS)}
                    item['puntajes']={l:design[7+n] if design[7+n] is not None else base['puntajes'][l] for n,l in enumerate(LEVELS)}
                definitions.append(validate_definition(item,thresholds(path)))
        source_category=meta.get('category',context['categoria'])
        source_type=meta.get('activity_type',context.get('tipo_actividad','Actividad')) if 'category' in meta else context.get('tipo_actividad','Actividad')
        source_mode=meta.get('entry_mode',context.get('modo_ingreso','capacidades'))
        source_method=kind if kind in ('Rúbrica','Lista de Cotejo') else 'Nota global' if source_mode=='global' else 'Nota directa'
        target=session
        incompatible=source_category!=context['categoria']
        incompatible=incompatible or mode=='criterios' and any(i['tipo']!=kind for i in get_indicators(session,path))
        if competency!=context['competencia_id'] or kind!=context['tipo_instrumento'] and context['tipo_instrumento']!='Normal' or incompatible:
            matches=conn.execute('SELECT id FROM Sesiones_Clase WHERE curso_id=? AND competencia_id=? AND grado=? AND seccion=? AND titulo_tema=? AND tipo_instrumento=? AND categoria=? AND tipo_actividad=?',(context['curso_id'],competency,grade,section,title,kind,source_category,source_type)).fetchall()
            if len(matches)>1:raise ValueError('Hay varias actividades con ese nombre. Seleccione la que desea importar.')
            target=matches[0][0] if matches else db.crear_o_actualizar_sesion_clase(None,context['curso_id'],competency,grade,section,title or context['titulo_tema'],purpose,context['peso_clase'],list(capacity_ids.items()),categoria=source_category,db_path=path,tipo_actividad=source_type,metodo=source_method,unidad_id=context.get('unidad_id') or 0)
            if not matches:changes.append('Actividad nueva: '+title)
        conn.execute('UPDATE Sesiones_Clase SET proposito=? WHERE id=?',(purpose,target))
        for cap,criterion in capacity_ids.items():conn.execute('INSERT OR IGNORE INTO Sesion_Capacidades(sesion_id,capacidad_id,criterio_precisado) VALUES(?,?,?)',(target,cap,criterion))
        if mode=='criterios':
            old=get_indicators(target,path);matching={(i['capacidad_id'],normalized(i['criterio'])):i for i in old if i['tipo']==kind}
            merged=list(old)
            for item in definitions:
                prior=matching.get((item['capacidad_id'],normalized(item['criterio'])))
                if prior:
                    item['id']=prior['id'];merged=[i for i in merged if i['id']!=prior['id']]
                else:changes.append('Criterio nuevo: '+item['criterio'])
                merged.append(item)
            db.guardar_indicadores_instrumento_sesion(target,kind,merged,path)
            items=get_indicators(target,path);ids={(i['capacidad_id'],normalized(i['criterio'])):i['id'] for i in items}
        else:
            conn.execute("UPDATE Sesiones_Clase SET tipo_instrumento='Normal',cotejo_regla=NULL,cotejo_pendiente=0 WHERE id=?",(target,))
        updates=[];seen_students=set()
        for row in range(start,ws.max_row+1):
            name=text(ws.cell(row,name_col).value)
            if not name:
                if any(_value(ws,fw,row,c) is not None for c,_ in columns):raise ValueError(f'Fila {row}: complete el nombre del estudiante.')
                continue
            sid=student_id(conn,name,grade,section,path,changes)
            if sid in seen_students:raise ValueError('Estudiante repetido: '+name)
            seen_students.add(sid);answers={};notes={}
            for (col,design) in columns:
                value=_value(ws,fw,row,col)
                if mode=='criterios':
                    cap=column_caps[col];identity=ids[(cap,normalized(design[1]) or normalized(GLOBAL))]
                    if value is not None and normalized(value) not in ('','pendiente','sin evaluar'):
                        item=next(i for i in items if i['id']==identity);answer_points(kind,value,item['puntaje_maximo'],item['puntajes']);answers[identity]=value
                    else:answers[identity]=None
                elif value is not None:notes[column_caps[col]]=read_grade(value)
            if kind=='Rúbrica' and answers:
                all_answers=get_answers(target,path);all_answers.update({(sid,i):v for i,v in answers.items()})
                computed,_=grade_answers(items,all_answers);notes={c:v for (s,c),v in computed.items() if s==sid}
            data=dict(estudiante_id=sid,preservar_asistencia=True,notas_por_capacidad=notes,respuestas_instrumento=answers)
            comment_col=next((c for c in range(1,ws.max_column+1) if text(ws.cell(6,c).value)=='comentario'),None) if modern else None
            if comment_col and ws.cell(row,comment_col).value is not None:data['comentario']=text(ws.cell(row,comment_col).value)
            updates.append(data)
        db.guardar_calificaciones_y_asistencia_sesion(target,updates,path)
        return ImportResult(len(definitions) if mode=='criterios' else len(capacity_ids),len(updates),target,changes)
