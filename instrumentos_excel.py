"""Versioned, bidirectional rubric/checklist workbooks with strict identity checks."""
import re
import openpyxl
from openpyxl.styles import Font,Alignment,PatternFill,Border,Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.utils import get_column_letter
from db_safety import connection,valid_number
from instrumentos import instrument_kind,normalized,normalized_grade

IND='1_Indicadores_Instrumento'
FINAL='2_Calificar_Estudiantes'
RAW='3_Evaluar_Indicadores'
META='Registro_Meta'
LEVELS=('C','B','A','AD')
DESCRIPTORS=('Necesita apoyo para aplicar el criterio.','Aplica parcialmente el criterio.','Aplica el criterio con autonomía.','Aplica y justifica el criterio en situaciones nuevas.')


def _integer(value,label):
    try:
        number=int(str(value).strip())
    except (TypeError,ValueError):raise ValueError(label+': identificador inválido.') from None
    return number


def _split_rubric(text,fallback):
    matches=list(re.finditer(r'(?:^|\n| \| )(AD|A|B|C):\s*',text))
    values={m[1]:text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)].strip() for i,m in enumerate(matches)}
    criterion=text[:matches[0].start()].strip() if matches else text.strip() or fallback
    return criterion or fallback,[values.get(level,DESCRIPTORS[i]) for i,level in enumerate(LEVELS)]


def _format_sheet(sheet,header_row,identity_columns=()):
    sheet.freeze_panes=f'D{header_row+1}';sheet.sheet_view.showGridLines=False
    sheet.auto_filter.ref=f'A{header_row}:{get_column_letter(sheet.max_column)}{max(header_row,sheet.max_row)}'
    edge=Border(bottom=Side(style='thin',color='E2E8F0'))
    for row in sheet.iter_rows():
        for cell in row:
            cell.font=Font(name='Calibri',size=12)
            cell.alignment=Alignment(vertical='center',wrap_text=True)
            cell.border=edge
            if cell.row==header_row:
                cell.fill=PatternFill('solid',fgColor='1E3A8A');cell.font=Font(name='Calibri',size=12,bold=True,color='FFFFFF')
            elif cell.row>header_row and cell.column in identity_columns:
                cell.fill=PatternFill('solid',fgColor='F1F5F9')
        sheet.row_dimensions[row[0].row].height=36 if row[0].row>header_row else 44
    sheet.sheet_properties.pageSetUpPr.fitToPage=True
    sheet.page_setup.orientation='landscape';sheet.page_setup.paperSize=sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth=1;sheet.page_setup.fitToHeight=0
    sheet.print_title_rows=f'1:{header_row}'


def export_template(destination,course,grade,section,title,competency,capacities,kind,path,session=None):
    import db
    kind=instrument_kind(kind)
    ids=[c[0] for c in capacities]
    if not ids or len(ids)!=len(set(ids)):raise ValueError('Seleccione capacidades válidas, sin repetir.')
    with connection(path) as conn:
        allowed={r[0]:(r[1],r[2],r[3]) for r in conn.execute('SELECT a.id,c.id,u.id,u.nivel FROM Capacidades a JOIN Competencias c ON c.id=a.competencia_id JOIN Cursos u ON u.id=c.curso_id')}
        if any(i not in allowed for i in ids) or len({allowed[i] for i in ids})!=1:
            raise ValueError('Las capacidades deben pertenecer a una misma competencia y curso.')
        comp_id,course_id,level=allowed[ids[0]]
        active=conn.execute('SELECT nivel_educativo FROM Docente_Config WHERE id=1').fetchone()[0]
        if active!=level:raise ValueError('Seleccione el nivel de la actividad antes de exportar.')
        if session:
            current=conn.execute('SELECT competencia_id,grado,seccion FROM Sesiones_Clase WHERE id=?',(session,)).fetchone()
            if not current or tuple(current)!=(comp_id,grade,section):raise ValueError('La actividad no coincide con el modelo solicitado.')
    existing=db.obtener_indicadores_instrumento_sesion(session,path) if session else []
    existing=[i for i in existing if i['capacidad_id'] in ids and i['tipo']==kind]
    definitions=[]
    for cap_id,name,criterion in capacities:
        rows=[i for i in existing if i['capacidad_id']==cap_id]
        if not rows:
            count=1 if kind=='Rúbrica' else 2
            rows=[dict(indicador_texto=criterion or f'{name}: evidencia {n+1}',puntaje_maximo=20 if kind=='Rúbrica' else 10) for n in range(count)]
        for row in rows:
            crit=criterion or f'Demuestra la capacidad: {name}'
            if kind=='Rúbrica':crit,descriptors=_split_rubric(row['indicador_texto'],crit)
            else:descriptors=[]
            definitions.append(dict(id=f'I{len(definitions)+1:03}',cap=cap_id,name=name,criterion=crit,
                text=row['indicador_texto'],maximum=row['puntaje_maximo'],descriptors=descriptors))
    wb=openpyxl.Workbook();sheet=wb.active;sheet.title=IND
    last='I' if kind=='Rúbrica' else 'G'
    sheet.merge_cells(f'A1:{last}1');sheet['A1']=f'MODELO DE {kind.upper()} · {title}'
    sheet.merge_cells(f'A2:{last}2');sheet['A2']=f'{course} · {grade} {section} · {competency}'
    headers=['CAP_ID','Capacidad','Criterio']+(['Inicio (C)','Proceso (B)','Logro (A)','Destacado (AD)','Máximo','IND_ID'] if kind=='Rúbrica' else ['Indicador observable','Máximo','Tipo','IND_ID'])
    sheet.append(headers)
    for item in definitions:
        sheet.append([item['cap'],item['name'],item['criterion']]+(item['descriptors']+[item['maximum'],item['id']] if kind=='Rúbrica' else [item['text'],item['maximum'],kind,item['id']]))
    _format_sheet(sheet,3,(1,len(headers)))
    for column,width in [('A',10),('B',36),('C',40)]:sheet.column_dimensions[column].width=width
    for col in range(4,len(headers)+1):sheet.column_dimensions[get_column_letter(col)].width=34 if col<=7 else 14
    if kind=='Lista de Cotejo':sheet.column_dimensions['D'].width=48;sheet.column_dimensions['E'].width=14
    for row in range(4,sheet.max_row+1):sheet.row_dimensions[row].height=90 if kind=='Rúbrica' else 60
    students=db.obtener_estudiantes_filtrados(grade,section,'',incluir_retirados=False,db_path=path)
    final=wb.create_sheet(FINAL)
    final.append(['Código','Apellidos','Nombres']+[f'{name}\n[CAP_ID:{cap_id}]' for cap_id,name,_ in capacities]+['EST_ID','Comentario'])
    raw=wb.create_sheet(RAW)
    raw.append(['Código','Apellidos','Nombres']+[f"{i['text'] if kind!='Rúbrica' else i['criterion']}\n[IND_ID:{i['id']}] [CAP_ID:{i['cap']}]" for i in definitions]+['EST_ID','Comentario'])
    for student in students:
        identity=[student['Codigo_Unico'],student['Apellidos'],student['Nombres']]
        final.append(identity+['']*len(capacities)+[student['ID'],''])
        raw.append(identity+['']*len(definitions)+[student['ID'],''])
    for ws,quantity in ((final,len(capacities)),(raw,len(definitions))):
        _format_sheet(ws,1,(1,2,3,quantity+4))
        for col in range(1,ws.max_column+1):ws.column_dimensions[get_column_letter(col)].width=26
        ws.column_dimensions['A'].width=14;ws.column_dimensions['B'].width=28;ws.column_dimensions['C'].width=26
        ws.column_dimensions[get_column_letter(quantity+4)].hidden=True
        ws.row_dimensions[1].height=100
    final_dv=DataValidation(type='decimal',operator='between',formula1=0,formula2=20,allow_blank=True)
    final_dv.showErrorMessage=True;final_dv.errorTitle='Nota de 0 a 20';final_dv.error='Ingrese un número entre 0 y 20.'
    final.add_data_validation(final_dv)
    for col in range(4,len(capacities)+4):final_dv.add(f'{get_column_letter(col)}2:{get_column_letter(col)}1000')
    for index,item in enumerate(definitions,4):
        column=get_column_letter(index);ind_row=index
        if kind=='Lista de Cotejo':
            dv=DataValidation(type='list',formula1='"Sí,No"',allow_blank=True);dv.error='Seleccione Sí o No; deje vacío si aún no evaluó.'
        else:
            name='MAX_'+item['id']
            wb.defined_names.add(DefinedName(name,attr_text=f"'{IND}'!$H${ind_row}"))
            dv=DataValidation(type='decimal',operator='between',formula1=0,formula2=name,allow_blank=True);dv.error='El puntaje debe estar entre 0 y el máximo del indicador.'
        dv.showErrorMessage=True;dv.errorTitle='Valor inválido';raw.add_data_validation(dv);dv.add(f'{column}2:{column}1000')
    instructions=wb.create_sheet('Instrucciones')
    steps=[
        f'MODELO DE {kind.upper()}',
        '1. En 1_Indicadores_Instrumento personalice el criterio y los indicadores/descriptores. Máximo: mayor que 0 y hasta 20 por indicador.',
        '2. Elija una forma de calificar: hoja 2 para notas finales de capacidades (0–20), O hoja 3 para evaluar cada indicador. No complete ambas para la misma capacidad.',
        '3. Rúbrica (hoja 3): escriba puntos de 0 al máximo. La aplicación calcula suma de puntos / suma de máximos × 20 para cada capacidad.',
        '4. Cotejo (hoja 3): seleccione Sí si cumple o No si no cumple. La aplicación calcula máximos cumplidos / máximos totales × 20 para cada capacidad.',
        '5. Vacío significa sin evaluar y 0 es una nota real. Complete todos los indicadores de una capacidad antes de importarla; las capacidades totalmente vacías conservan su nota anterior.',
        '6. Conserve CAP_ID, IND_ID, EST_ID, nombres y códigos. Para añadir indicadores, edite el instrumento en la aplicación y vuelva a exportar el modelo.',
        '7. Guarde como XLSX. En Calificaciones pulse Importar instrumento, revise la vista previa y confirme. Se crea un respaldo antes de aplicar.',
        '8. Si importó solo criterios, pulse Evaluar rúbrica/cotejo, complete las respuestas y después Guardar notas.',
        'Ejemplo rúbrica: 6/10 + 8/10 = 14/20. Ejemplo cotejo con máximos 6 y 4: Sí + No = 6/10 × 20 = 12/20.',
        'La importación no cambia asistencias. Los comentarios vacíos y las notas vacías no borran datos existentes.',
        'Los descriptores iniciales son un ejemplo: adáptelos al grado, competencia y propósito de su actividad.'
    ]
    for text in steps:instructions.append([text])
    instructions.column_dimensions['A'].width=110
    for row in instructions:
        row[0].font=Font(size=13);row[0].alignment=Alignment(wrap_text=True,vertical='center');instructions.row_dimensions[row[0].row].height=55
    meta=wb.create_sheet(META)
    for key,value in dict(format='registro-instrumento',version=2,kind=kind,course_id=course_id,competency_id=comp_id,level=level,grade=grade,section=section,session_id=session or '').items():meta.append([key,value])
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
    modern=bool(meta)
    if modern and (meta.get('format')!='registro-instrumento' or meta.get('version')!=2):raise ValueError('Versión de plantilla no compatible.')
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
                    text=(criterion+'\n' if criterion else '')+' | '.join(f'{level}: {desc}' for level,desc in zip(LEVELS,descriptors) if desc)
                    text=text.strip() or criterion
                    maximum=row[7] if modern else row[7] if len(row)>7 and row[7] is not None and any('maximo' in h for h in header[7:8]) else 20
                    ident=str(row[8]).strip() if modern and len(row)>8 and row[8] else f'I{len(definitions)+1:03}'
                else:
                    text=str(row[3] or '').strip() or (criterion if not modern else '')
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
                seen.add(ident);definitions.append(dict(id=ident,cap=cap,text=text,criterion=criterion,maximum=maximum))
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
                    values=[(editable_value(ws,row,columns[d['id']]),d['maximum']) for d in definitions if d['cap']==cap]
                    if not any(v is not None and str(v).strip() for v,_ in values):continue
                    if cap in data['notas_por_capacidad']:raise ValueError('No complete las hojas 2 y 3 para la misma capacidad; elija notas finales o indicadores.')
                    try:data['notas_por_capacidad'][cap]=normalized_grade(kind,values)
                    except ValueError as exc:raise ValueError(f'Hoja {ws.title}, fila {row}: {exc}') from exc
        changing=[d for d in updates.values() if d['notas_por_capacidad'] or d.get('comentario')]
        if modern and meta.get('session_id') and meta['session_id']!=session and changing:raise ValueError('Las notas pertenecen a otra actividad. Para reutilizar el instrumento deje las hojas de calificaciones vacías.')
        # Definitions and grades are one atomic operation, including late validation failures.
        db.guardar_indicadores_instrumento_sesion(session,kind,[(d['cap'],d['text'],d['maximum']) for d in definitions],path)
        for definition in definitions:conn.execute('UPDATE Sesion_Capacidades SET criterio_precisado=? WHERE sesion_id=? AND capacidad_id=?',(definition['criterion'],session,definition['cap']))
        if changing:db.guardar_calificaciones_y_asistencia_sesion(session,changing,db_path=path)
        return len(definitions),len(changing)
