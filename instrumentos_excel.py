"""Versioned rubric/checklist workbooks with human headings and stable identities."""
import json,re
import openpyxl
from openpyxl.styles import Font,Alignment,PatternFill,Border,Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.views import Selection
from db_safety import connection,valid_number
from instrumentos import instrument_kind,normalized,normalized_grade,definition,validate_definition,LEVELS,criterion_caption
from escala import thresholds

IND='1_Indicadores_Instrumento'
FINAL='2_Calificar_Estudiantes'
RAW='3_Evaluar_Indicadores'
META='Registro_Meta'
COLORS=('FDE9E7','FFF4CC','E2F3E6','E1EDFC')


def _integer(value,label):
    try:return int(str(value).strip())
    except (TypeError,ValueError):raise ValueError(label+': identificador inválido.') from None


def freeze_view(sheet,cell):
    # openpyxl inserts extra selections whenever freeze_panes is assigned again.
    # Clear the previous view first so Excel has one selection per pane.
    sheet.sheet_view.pane=None
    sheet.sheet_view.selection=[Selection(activeCell=cell,sqref=cell)]
    sheet.freeze_panes=cell
    sheet.sheet_view.topLeftCell='A1'


def _format_sheet(sheet,header_row,identity_columns=()):
    freeze_view(sheet,f'D{header_row+1}');sheet.sheet_view.showGridLines=False
    sheet.auto_filter.ref=f'A{header_row}:{get_column_letter(sheet.max_column)}{max(header_row,sheet.max_row)}'
    edge=Side(style='thin',color='CBD5E1')
    for row in sheet.iter_rows():
        for cell in row:
            cell.font=Font(name='Calibri',size=12)
            cell.alignment=Alignment(vertical='center',wrap_text=True)
            if cell.row>=header_row:cell.border=Border(left=edge,right=edge,top=edge,bottom=edge)
            if cell.row==header_row:
                cell.fill=PatternFill('solid',fgColor='1E3A8A');cell.font=Font(name='Calibri',size=12,bold=True,color='FFFFFF')
            elif cell.row>header_row and cell.column in identity_columns:cell.fill=PatternFill('solid',fgColor='F1F5F9')
        sheet.row_dimensions[row[0].row].height=36 if row[0].row>header_row else 44
    sheet.sheet_properties.pageSetUpPr.fitToPage=True
    sheet.page_setup.orientation='landscape';sheet.page_setup.paperSize=sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth=1;sheet.page_setup.fitToHeight=0
    sheet.print_title_rows=f'1:{header_row}'


def export_template(destination,course,grade,section,title,competency,capacities,kind,path,session=None,
                    *,criteria_counts=None,blank=False,format_version=4,include_students=True):
    if format_version==5:
        from plantilla_simple import export_form
        return export_form(destination,course,grade,section,title,competency,capacities,kind,path,session,criteria_counts,blank,include_students)
    if format_version==3:return _export_v3(destination,course,grade,section,title,competency,capacities,kind,path,session)
    if format_version!=4:raise ValueError('Formato de plantilla no compatible.')
    from plantilla_excel import export_form
    return export_form(destination,course,grade,section,title,competency,capacities,kind,path,session,criteria_counts,blank)


def _export_v3(destination,course,grade,section,title,competency,capacities,kind,path,session=None,*,criteria_counts=None,blank=False):
    import db
    kind=instrument_kind(kind);limits=thresholds(path)
    ids=[c[0] for c in capacities]
    if not ids or len(ids)!=len(set(ids)):raise ValueError('Seleccione capacidades válidas, sin repetir.')
    with connection(path) as conn:
        allowed={r[0]:(r[1],r[2],r[3]) for r in conn.execute('SELECT a.id,c.id,u.id,u.nivel FROM Capacidades a JOIN Competencias c ON c.id=a.competencia_id JOIN Cursos u ON u.id=c.curso_id')}
        if any(i not in allowed for i in ids) or len({allowed[i] for i in ids})!=1:raise ValueError('Las capacidades deben pertenecer a una misma competencia y curso.')
        comp_id,course_id,level=allowed[ids[0]]
        if conn.execute('SELECT nivel_educativo FROM Docente_Config WHERE id=1').fetchone()[0]!=level:raise ValueError('Seleccione el nivel de la actividad antes de exportar.')
        if session:
            current=conn.execute('SELECT competencia_id,grado,seccion FROM Sesiones_Clase WHERE id=?',(session,)).fetchone()
            if not current or tuple(current)!=(comp_id,grade,section):raise ValueError('La actividad no coincide con el modelo solicitado.')
    existing=db.obtener_indicadores_instrumento_sesion(session,path) if session and not blank else []
    existing=[i for i in existing if i['capacidad_id'] in ids and i['tipo']==kind];definitions=[]
    for cap_id,name,criterion in capacities:
        rows=[i for i in existing if i['capacidad_id']==cap_id]
        if not rows:
            if blank:
                count=(criteria_counts or {}).get(cap_id,2)
                if not isinstance(count,int) or not 1<=count<=20:raise ValueError('Elija entre 1 y 20 criterios por capacidad.')
                first=criterion if normalized(criterion)!=normalized(name) else ''
                rows=[dict(criterio=first if n==0 else '',puntaje_maximo=20/count,descriptores={l:'' for l in LEVELS}) for n in range(count)]
            else:
                texts=[criterion or name]
                if kind=='Lista de Cotejo':texts.append('Explica su respuesta usando la evidencia solicitada.')
                rows=[dict(criterio=text,puntaje_maximo=20 if kind=='Rúbrica' else 10) for text in texts]
        for row in rows:
            item=definition({**row,'tipo':kind,'capacidad_id':cap_id,'capacidad_nombre':name},limits)
            item['ident']=f"I{row['id']}" if row.get('id') else f'N{len(definitions)+1}'
            definitions.append(item)
    wb=openpyxl.Workbook();sheet=wb.active;sheet.title=IND;rubric=kind=='Rúbrica'
    last='M' if rubric else 'G'
    sheet.merge_cells(f'A1:{last}1');sheet['A1']=f'{kind.upper()} · {title}'
    sheet.merge_cells(f'A2:{last}2');sheet['A2']=f'{course} · {grade} {section} · {competency}'
    sheet.append(['CAP_ID','Capacidad','Criterio observable']+(['Inicio (C)','En proceso (B)','Logro esperado (A)','Logro destacado (AD)','Máximo','IND_ID','Puntos C','Puntos B','Puntos A','Puntos AD'] if rubric else ['Registro','Máximo','Evaluación','IND_ID']))
    for item in definitions:
        sheet.append([item['capacidad_id'],item['capacidad_nombre'],item['criterio']]+([item['descriptores'][l] for l in LEVELS]+[item['puntaje_maximo'],item['ident']]+[item['puntajes'][l] for l in LEVELS] if rubric else ['Sí / No',item['puntaje_maximo'],kind,item['ident']]))
    _format_sheet(sheet,3,(1,9 if rubric else 7))
    for column,width in [('A',10),('B',34),('C',42)]:sheet.column_dimensions[column].width=width
    for col in range(4,sheet.max_column+1):sheet.column_dimensions[get_column_letter(col)].width=32 if rubric and col<=7 else 14
    sheet.column_dimensions['A'].hidden=True;sheet.column_dimensions['I' if rubric else 'G'].hidden=True
    if not rubric:sheet.column_dimensions['F'].hidden=True
    for row in range(4,sheet.max_row+1):
        sheet.row_dimensions[row].height=110 if rubric else 60
        if rubric:
            for col,color in zip(range(4,8),COLORS):sheet.cell(row,col).fill=PatternFill('solid',fgColor=color)
            for col in range(10,14):sheet.cell(row,col).number_format='0.########'
    students=db.obtener_estudiantes_filtrados(grade,section,'',incluir_retirados=False,db_path=path)
    final=wb.create_sheet(FINAL);final_headers=[name for cap,name,criterion in capacities]
    raw=wb.create_sheet(RAW)
    # Each caption is short; capacity names and rubric descriptors belong to sheet 1.
    raw_headers=[f"Criterio {n+1}\n{criterion_caption(item)}" for n,item in enumerate(definitions)]
    final.append(['Código','Apellidos','Nombres']+final_headers+['EST_ID','Comentario'])
    raw.append(['Código','Apellidos','Nombres']+raw_headers+['EST_ID','Comentario'])
    for student in students:
        identity=[student['Codigo_Unico'],student['Apellidos'],student['Nombres']]
        final.append(identity+['']*len(capacities)+[student['ID'],''])
        raw.append(identity+['']*len(definitions)+[student['ID'],''])
    for ws,quantity in ((final,len(capacities)),(raw,len(definitions))):
        _format_sheet(ws,1,(1,2,3,quantity+4))
        for col in range(1,ws.max_column+1):ws.column_dimensions[get_column_letter(col)].width=30
        ws.column_dimensions['A'].width=14;ws.column_dimensions['B'].width=28;ws.column_dimensions['C'].width=26
        ws.column_dimensions[get_column_letter(quantity+4)].hidden=True;ws.row_dimensions[1].height=100
    final_dv=DataValidation(type='decimal',operator='between',formula1=0,formula2=20,allow_blank=True)
    final_dv.showErrorMessage=True;final_dv.errorTitle='Nota de 0 a 20';final_dv.error='Ingrese un número entre 0 y 20.';final.add_data_validation(final_dv)
    for col in range(4,len(capacities)+4):final_dv.add(f'{get_column_letter(col)}2:{get_column_letter(col)}1000')
    raw_dv=DataValidation(type='list',formula1='"C,B,A,AD,Sin evidencia"' if rubric else '"Sí,No"',allow_blank=True)
    raw_dv.showErrorMessage=True;raw_dv.errorTitle='Evaluación inválida'
    raw_dv.error='Seleccione un nivel; deje vacío si aún no evaluó.' if rubric else 'Seleccione Sí o No; deje vacío si aún no evaluó.'
    raw.add_data_validation(raw_dv)
    for col in range(4,len(definitions)+4):raw_dv.add(f'{get_column_letter(col)}2:{get_column_letter(col)}1000')
    instructions=wb.create_sheet('Instrucciones')
    steps=[f'{kind.upper()} · {title}',
        '1. En Calificaciones elija la actividad y diseñe su instrumento antes de descargar esta plantilla.',
        '2. En la hoja 1 puede ajustar criterios, descriptores y puntajes. Máximo: mayor que 0 y hasta 20 por criterio. En la rúbrica: C < B < A < AD; AD vale el máximo.',
        '3. Elija una forma de calificar por capacidad: hoja 2 para notas finales (0–20), O hoja 3 para evaluar criterios. No complete ambas para la misma capacidad.',
        '4. Rúbrica: seleccione C, B, A o AD según la evidencia. Sin evidencia vale 0; una celda vacía sigue pendiente. También se admiten puntos numéricos de 0 al máximo del criterio.',
        '5. Cotejo: seleccione Sí si cumple o No si no cumple. Cada Sí aporta el máximo de su criterio; No aporta 0.',
        '6. La nota de capacidad es suma de puntos obtenidos / suma de máximos × 20. Complete todos sus criterios. Las capacidades completamente vacías conservan su nota anterior.',
        '7. Conserve nombres, códigos, encabezados y las columnas ocultas. Para añadir o quitar criterios, edite el instrumento en la aplicación y descargue una nueva plantilla.',
        '8. Guarde como XLSX. En Calificaciones pulse Importar evaluación Excel, revise el instrumento y los cambios de notas y confirme. Se crea un respaldo antes de aplicar.',
        '9. Si importa solo el instrumento, pulse Evaluar estudiantes; marque las respuestas, aplique a la planilla y pulse Guardar notas.',
        'Ejemplo de puntos: 6/10 + 8/10 = 14/20. Cotejo con máximos 6 y 4: Sí + No = 6/10 × 20 = 12/20.',
        'La importación conserva asistencias. Comentarios y notas vacíos no borran los datos guardados. Adapte los descriptores al grado y al propósito de la actividad.']
    for text in steps:instructions.append([text])
    instructions.column_dimensions['A'].width=110
    for row in instructions:
        row[0].font=Font(size=13);row[0].alignment=Alignment(wrap_text=True,vertical='center');instructions.row_dimensions[row[0].row].height=55
    meta=wb.create_sheet(META)
    final_map=[dict(column=n,cap=cap,header=caption) for n,((cap,_,_),caption) in enumerate(zip(capacities,final_headers),4)]
    raw_map=[dict(column=n,indicator=i['ident'],cap=i['capacidad_id'],header=caption) for n,(i,caption) in enumerate(zip(definitions,raw_headers),4)]
    for key,value in dict(format='registro-instrumento',version=3,kind=kind,course_id=course_id,competency_id=comp_id,level=level,grade=grade,section=section,session_id=session or '',final_columns=json.dumps(final_map,ensure_ascii=False),raw_columns=json.dumps(raw_map,ensure_ascii=False)).items():meta.append([key,value])
    meta.sheet_state='veryHidden'
    try:wb.save(destination)
    finally:wb.close()


def import_template(session,source,grade,section,path):
    import db
    wb=openpyxl.load_workbook(source,data_only=True)
    formulas=None
    try:
        formulas=openpyxl.load_workbook(source,data_only=False,read_only=True)
        return _import_workbook(wb,formulas,session,grade,section,path,db)
    finally:
        wb.close()
        if formulas:formulas.close()


def _import_workbook(wb,formulas,session,grade,section,path,db):
    meta={row[0].value:row[1].value for row in wb[META].iter_rows(max_col=2)} if META in wb.sheetnames else {}
    if meta.get('format')=='registro-instrumento' and meta.get('version')==5:
        from plantilla_simple import normalize_form
        converted,checked=normalize_form(wb,formulas,path)
        try:return _import_workbook(converted,checked,session,grade,section,path,db)
        finally:converted.close();checked.close()
    if meta.get('format')=='registro-instrumento' and meta.get('version')==4:
        from plantilla_excel import normalize_form
        converted,checked=normalize_form(wb,formulas)
        try:return _import_workbook(converted,checked,session,grade,section,path,db)
        finally:converted.close();checked.close()
    modern=bool(meta)
    if modern and (meta.get('format')!='registro-instrumento' or meta.get('version') not in (2,3)):raise ValueError('Versión de plantilla no compatible.')
    structured=meta.get('version')==3
    if modern and (FINAL not in wb.sheetnames or RAW not in wb.sheetnames):raise ValueError('Conserve las hojas de notas finales y evaluación del modelo.')
    limits=thresholds(path)
    with connection(path) as conn:
        target=conn.execute('SELECT s.competencia_id,s.curso_id,c.nivel,s.grado,s.seccion FROM Sesiones_Clase s JOIN Cursos c ON c.id=s.curso_id WHERE s.id=?',(session,)).fetchone()
        if not target or tuple(target[3:])!=(grade,section):raise ValueError('La actividad no pertenece al salón elegido.')
        active=conn.execute('SELECT nivel_educativo FROM Docente_Config WHERE id=1').fetchone()[0]
        if target[2]!=active:raise ValueError('El nivel activo no coincide con la actividad.')
        allowed={r[0] for r in conn.execute('SELECT capacidad_id FROM Sesion_Capacidades WHERE sesion_id=?',(session,))}
        if modern and (meta.get('course_id')!=target[1] or meta.get('competency_id')!=target[0] or meta.get('level')!=target[2] or meta.get('grade')!=grade or meta.get('section')!=section):raise ValueError('La plantilla pertenece a otro curso, competencia, nivel o salón.')
        sheet=wb[IND] if IND in wb.sheetnames else wb.worksheets[0]
        header=[normalized(c.value) for c in sheet[3]]
        if not header or header[0]!='cap_id':raise ValueError('Falta el encabezado CAP_ID en la fila 3 de indicadores.')
        kind=instrument_kind(meta['kind']) if modern else 'Rúbrica' if any('inicio' in h or 'destacado' in h for h in header) or 'rubrica' in normalized(sheet['A1'].value) else 'Lista de Cotejo'
        definitions=[];seen=set()
        for rowno,row in enumerate(sheet.iter_rows(min_row=4,values_only=True),4):
            if not any(v is not None and str(v).strip() for v in row):continue
            try:
                cap=_integer(row[0],'CAP_ID')
                if cap not in allowed:raise ValueError('La capacidad no pertenece a la actividad.')
                criterion=str(row[2] or '').strip()
                if kind=='Rúbrica':
                    descriptors=[str(row[i] or '').strip() if len(row)>i else '' for i in range(3,7)]
                    if modern and not all(descriptors):raise ValueError('Complete los cuatro descriptores C, B, A y AD.')
                    text=criterion
                    maximum=row[7] if modern else row[7] if len(row)>7 and row[7] is not None and any('maximo' in h for h in header[7:8]) else 20
                    ident=str(row[8]).strip() if modern and len(row)>8 and row[8] else f'I{len(definitions)+1:03}'
                else:
                    text=criterion if structured else str(row[3] or '').strip() or (criterion if not modern else '')
                    maximum=row[4] if len(row)>4 and row[4] is not None else 20
                    ident=str(row[6]).strip() if modern and len(row)>6 and row[6] else f'I{len(definitions)+1:03}'
                    if len(row)>5 and row[5] and instrument_kind(row[5])!=kind:raise ValueError('Hay tipos de instrumento mezclados.')
                if not text:raise ValueError('El indicador no tiene texto.')
                maximum=valid_number(str(maximum).replace(',','.'),.000001,20,'Máximo del indicador')
                if modern:
                    index=8 if kind=='Rúbrica' else 6
                    if len(row)<=index or not row[index]:raise ValueError('Conserve el IND_ID del modelo.')
                if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,31}',ident):raise ValueError('IND_ID inválido.')
                if ident in seen:raise ValueError('IND_ID repetido.')
                item=dict(capacidad_id=cap,tipo=kind,criterio=text,puntaje_maximo=maximum)
                if kind=='Rúbrica':
                    item['descriptores']=dict(zip(LEVELS,descriptors))
                    if structured:
                        if len(row)<13:raise ValueError('Conserve los puntos C, B, A y AD de cada criterio.')
                        item['puntajes']={level:valid_number(str(row[n]).replace(',','.'),0,maximum,'Puntos de '+level) for n,level in enumerate(LEVELS,9)}
                item=validate_definition(item,limits)
                seen.add(ident);definitions.append(dict(id=ident,cap=cap,text=text,criterion=criterion,maximum=maximum,item=item))
            except (ValueError,TypeError,IndexError) as exc:raise ValueError(f'Hoja {sheet.title}, fila {rowno}: {exc}') from exc
        if not definitions:raise ValueError('La plantilla no tiene indicadores válidos.')
        roster=db.obtener_estudiantes_filtrados(grade,section,'',incluir_retirados=True,db_path=path)
        by_code={s['Codigo_Unico']:s for s in roster};updates={}
        formula_positions={ws.title:{c.coordinate for row in ws.iter_rows() for c in row if c.data_type=='f'} for ws in formulas.worksheets}
        def editable_value(ws,row,col):
            value=ws.cell(row,col).value
            if ws.cell(row,col).coordinate in formula_positions[ws.title] and value is None:raise ValueError(f'Hoja {ws.title}, fila {row}: fórmula sin resultado. Recalcule en Excel o pegue valores.')
            return value
        def student_rows(ws):
            headers=[str(c.value or '') for c in ws[1]]
            combined=not modern and len(headers)>1 and normalized(headers[1]) in ('alumno','estudiante','apellidos y nombres')
            idcol=next((i+1 for i,h in enumerate(headers) if normalized(h)=='est_id'),None)
            comment=next((i+1 for i,h in enumerate(headers) if normalized(h).startswith('comentario')),None)
            if modern and (list(map(normalized,headers[:3]))!=['codigo','apellidos','nombres'] or idcol is None):
                raise ValueError(f'Hoja {ws.title}: conserve Código, Apellidos, Nombres y EST_ID del modelo.')
            codes=set()
            for row in range(2,ws.max_row+1):
                values=[c.value for c in ws[row]]
                if not any(v is not None and str(v).strip() for v in values):continue
                code=str(values[0] or '').strip();student=by_code.get(code)
                if code in codes:raise ValueError(f'Hoja {ws.title}, fila {row}: código repetido.')
                codes.add(code)
                identity_ok=bool(student)
                if student and combined:
                    names={student['Nombres']+' '+student['Apellidos'],student['Apellidos']+', '+student['Nombres'],student['Apellidos']+' '+student['Nombres']}
                    identity_ok=str(values[1] or '').strip() in names
                elif student:identity_ok=str(values[1] or '').strip()==student['Apellidos'] and str(values[2] or '').strip()==student['Nombres']
                if not identity_ok:
                    raise ValueError(f'Hoja {ws.title}, fila {row}: el código y nombre no coinciden con el estudiante. Exporte un modelo actualizado.')
                if idcol and _integer(ws.cell(row,idcol).value,'EST_ID')!=student['ID']:raise ValueError(f'Hoja {ws.title}, fila {row}: EST_ID no coincide.')
                data=updates.setdefault(student['ID'],dict(estudiante_id=student['ID'],notas_por_capacidad={},preservar_asistencia=True,preservar_comentario=True))
                comment_value=str(ws.cell(row,comment).value or '').strip() if comment else ''
                if comment_value:
                    if data.get('comentario') and data['comentario']!=comment_value:raise ValueError(f'Hay dos comentarios distintos para {code}.')
                    data['comentario']=comment_value
                    data['preservar_comentario']=False
                yield row,student,data
        if FINAL in wb.sheetnames or (not modern and len(wb.worksheets)>1):
            ws=wb[FINAL] if FINAL in wb.sheetnames else wb.worksheets[1]
            columns={};used=set()
            if structured:
                mappings=_column_mapping(meta,'final_columns',ws)
                for mapping in mappings:
                    cap=mapping['cap']
                    if cap not in allowed or cap in used:raise ValueError('Hay capacidades repetidas o ajenas a la actividad en la hoja 2.')
                    used.add(cap);columns[mapping['column']]=cap
            else:
                for col,cell in enumerate(ws[1],1):
                    text=str(cell.value or '')
                    if '[CAP_ID:' in text:
                        match=re.search(r'\[CAP_ID:(\d+)\]',text)
                        if not match:raise ValueError('Encabezado CAP_ID inválido en calificaciones.')
                        cap=int(match[1])
                        if cap not in allowed or cap in used:raise ValueError('Hay capacidades repetidas o ajenas a la actividad en la hoja 2.')
                        used.add(cap);columns[col]=cap
            if not columns:raise ValueError('La hoja de calificaciones no tiene columnas CAP_ID válidas.')
            for row,student,data in student_rows(ws):
                for col,cap in columns.items():
                    value=editable_value(ws,row,col)
                    if value is not None and str(value).strip():
                        try:data['notas_por_capacidad'][cap]=valid_number(str(value).replace(',','.'))
                        except ValueError as exc:raise ValueError(f'Hoja {ws.title}, fila {row}, columna {col}: {exc}') from exc
        if RAW in wb.sheetnames:
            ws=wb[RAW];columns={};used=set();by_id={d['id']:d for d in definitions}
            if structured:
                for mapping in _column_mapping(meta,'raw_columns',ws):
                    identity=mapping['indicator']
                    if identity not in by_id or identity in used:raise ValueError('IND_ID repetido o desconocido en la hoja 3.')
                    if mapping['cap']!=by_id[identity]['cap']:raise ValueError('La capacidad de la columna no coincide con su indicador.')
                    used.add(identity);columns[identity]=mapping['column']
            else:
                for col,cell in enumerate(ws[1],1):
                    text=str(cell.value or '')
                    if '[IND_ID:' in text:
                        match=re.search(r'\[IND_ID:([^\]]+)\]',text)
                        if not match or match[1] not in by_id or match[1] in used:raise ValueError('IND_ID repetido o desconocido en la hoja 3.')
                        cap=re.search(r'\[CAP_ID:(\d+)\]',text)
                        if not cap or int(cap[1])!=by_id[match[1]]['cap']:raise ValueError('La capacidad de la columna no coincide con su indicador.')
                        used.add(match[1]);columns[match[1]]=col
            if set(columns)!=set(by_id):raise ValueError('Los indicadores de las hojas 1 y 3 no coinciden. Exporte un modelo nuevo después de modificar el instrumento.')
            for row,student,data in student_rows(ws):
                for cap in {d['cap'] for d in definitions}:
                    selected=[d for d in definitions if d['cap']==cap]
                    values=[(editable_value(ws,row,columns[d['id']]),d['maximum'],d['item']['puntajes']) for d in selected]
                    if not any(v is not None and str(v).strip() for v,_,_ in values):continue
                    if cap in data['notas_por_capacidad']:raise ValueError('No complete las hojas 2 y 3 para la misma capacidad; elija notas finales o indicadores.')
                    try:
                        if not meta.get('orientation'):data['notas_por_capacidad'][cap]=normalized_grade(kind,values,allow_pending=True)
                        else:
                            from instrumentos import checklist_value
                            for value,maximum,scores in values:
                                if value is not None and str(value).strip():checklist_value(value)
                    except ValueError as exc:raise ValueError(f'Hoja {ws.title}, fila {row}: {exc}') from exc
                    data.setdefault('raw_answers',{}).update({d['id']:value[0] for d,value in zip(selected,values)})
        changing=[d for d in updates.values() if d['notas_por_capacidad'] or d.get('comentario') or d.get('raw_answers')]
        if modern and meta.get('session_id') and meta['session_id']!=session and changing:raise ValueError('Las notas pertenecen a otra actividad. Para reutilizar el instrumento deje las hojas de calificaciones vacías.')
        # Definitions and grades are one atomic operation, including late validation failures.
        items=[]
        for entry in definitions:
            item=dict(entry['item'])
            if structured and meta.get('session_id')==session and re.fullmatch(r'I\d+',entry['id']):item['id']=int(entry['id'][1:])
            items.append(item)
        identities=db.guardar_indicadores_instrumento_sesion(session,kind,items,path)
        by_identity={d['id']:i for d,i in zip(definitions,identities)}
        for data in changing:data['respuestas_instrumento']={by_identity[i]:v for i,v in data.pop('raw_answers',{}).items()}
        criteria={}
        for entry in definitions:criteria.setdefault(entry['cap'],entry['criterion'])
        for cap,criterion in criteria.items():conn.execute('UPDATE Sesion_Capacidades SET criterio_precisado=? WHERE sesion_id=? AND capacidad_id=?',(criterion,session,cap))
        if changing:
            db.guardar_calificaciones_y_asistencia_sesion(session,changing,db_path=path)
            if kind=='Lista de Cotejo' and not meta.get('orientation'):
                conn.execute("UPDATE Sesiones_Clase SET cotejo_regla=?,cotejo_pendiente=0 WHERE id=?",(json.dumps({'tipo':'anterior'}),session))
        return len(definitions),len(changing)


def _column_mapping(meta,key,sheet):
    try:
        mappings=json.loads(meta[key])
        if not isinstance(mappings,list) or not mappings:raise ValueError()
        columns=[entry['column'] for entry in mappings]
        if columns!=list(range(4,len(mappings)+4)):raise ValueError()
        for entry in mappings:
            if sheet.cell(1,entry['column']).value!=entry['header']:raise ValueError()
        return mappings
    except (KeyError,TypeError,ValueError,IndexError):
        raise ValueError(f'Hoja {sheet.title}: conserve el orden y los encabezados del modelo. Descargue una plantilla actualizada.') from None
