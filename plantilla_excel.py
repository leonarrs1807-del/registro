"""Excel-first instruments: aligned descriptors/points, one answer per criterion."""
import json
from copy import copy
import openpyxl
from openpyxl.styles import Alignment,Font,PatternFill,Protection
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties

EVALUAR='2_Evaluar_Criterios'
RESUMEN='3_Notas_Capacidades'


def metadata(workbook):
    return {row[0].value:row[1].value for row in workbook['Registro_Meta'].iter_rows(max_col=2)}


def _point_formula(cell,row,kind):
    value=f"'{EVALUAR}'!{cell}";maximum=f"'1_Indicadores_Instrumento'!$H${row}"
    text=f'UPPER(TRIM({value}))'
    if kind=='Rúbrica':
        levels=f'INDEX(\'1_Indicadores_Instrumento\'!$D${row+1}:$G${row+1},1,MATCH({text},{{"C","B","A","AD"}},0))'
        return f'IF(ISNUMBER({value}),IF(AND({value}>=0,{value}<={maximum}),{value},NA()),IF(OR({text}="NE",{text}="SIN EVIDENCIA"),0,{levels}))'
    return f'IF(OR({text}="SÍ",{text}="SI",{text}="TRUE",{text}="1"),{maximum},IF(OR({text}="NO",{text}="FALSE",{text}="0"),0,NA()))'


def export_form(destination,course,grade,section,title,competency,capacities,kind,path,session,counts,blank):
    from instrumentos_excel import _export_v3,IND,FINAL,RAW,META,COLORS,_format_sheet
    _export_v3(destination,course,grade,section,title,competency,capacities,kind,path,session,
               criteria_counts=counts,blank=blank)
    wb=openpyxl.load_workbook(destination)
    try:
        meta=metadata(wb);rubric=meta['kind']=='Rúbrica';sheet=wb[IND]
        definitions=list(sheet.iter_rows(min_row=4,values_only=True));layout=[]
        for region in list(sheet.merged_cells.ranges):sheet.unmerge_cells(str(region))
        sheet.delete_rows(4,sheet.max_row);sheet.delete_cols(10,4)
        last='I' if rubric else 'G'
        sheet.merge_cells(f'A1:{last}1');sheet.merge_cells(f'A2:{last}2')
        sheet['A1']=f'{meta["kind"].upper()} · {title}'
        sheet['A2']=f'{course} · {grade} {section} · {competency}'
        sheet.row_dimensions[1].height=30;sheet.row_dimensions[2].height=40
        if rubric:sheet['H3']='Máximo'
        for item in definitions:
            row=sheet.max_row+1
            # Original columns A..I remain stable for identifiers and descriptors.
            sheet.append(list(item[:9] if rubric else item[:7]))
            entry=dict(indicator=item[8] if rubric else item[6],cap=item[0],row=row)
            if rubric:
                sheet.append(['PUNTOS',None,'Puntos del nivel →',*item[9:13]])
                sheet.merge_cells(start_row=row,start_column=2,end_row=row+1,end_column=2)
                sheet.merge_cells(start_row=row,start_column=8,end_row=row+1,end_column=8)
                entry['points_row']=row+1
            layout.append(entry)
        _format_sheet(sheet,3)
        sheet.auto_filter.ref=None;sheet.freeze_panes='D4';sheet.sheet_view.zoomScale=90
        sheet.sheet_view.topLeftCell='B1';sheet.row_dimensions[3].height=42
        widths={'A':10,'B':24,'C':28,'D':22,'E':22,'F':22,'G':22,'H':10,'I':10}
        for col,width in widths.items():sheet.column_dimensions[col].width=width
        sheet.column_dimensions['A'].hidden=True
        sheet.column_dimensions['I' if rubric else 'G'].hidden=True
        if not rubric:sheet.column_dimensions['F'].hidden=True;sheet.column_dimensions['E'].width=12
        for entry in layout:
            row=entry['row'];sheet.row_dimensions[row].height=95 if rubric else 62
            for col in range(2,9 if rubric else 6):
                sheet.cell(row,col).font=Font(name='Calibri',size=11)
            editable=[3,4,5,6,7,8] if rubric else [3,5]
            for col in editable:sheet.cell(row,col).protection=Protection(locked=False)
            sheet.cell(row,3).comment=Comment('Escriba el criterio o indicador observable de esta sesión. Cada bloque representa un criterio diferente.','Registro Docente')
            if rubric:
                sheet.row_dimensions[row+1].height=25
                sheet.cell(row+1,3).font=Font(name='Calibri',size=10,bold=True,color='475569')
                for col,color in zip(range(4,8),COLORS):
                    for r in (row,row+1):sheet.cell(r,col).fill=PatternFill('solid',fgColor=color)
                    sheet.cell(row+1,col).protection=Protection(locked=False)
                    sheet.cell(row+1,col).number_format='General'
                    sheet.cell(row+1,col).font=Font(name='Calibri',size=11,bold=True)
                sheet.cell(row,8).number_format='General'
        sheet.protection.sheet=True;sheet.protection.formatColumns=False;sheet.protection.formatRows=False
        raw=wb[RAW];raw.title=EVALUAR;summary=wb[FINAL];summary.title=RESUMEN
        per_cap={};raw_map=json.loads(meta['raw_columns'])
        for entry,mapping in zip(layout,raw_map):
            cap=entry['cap'];per_cap[cap]=per_cap.get(cap,0)+1
            cap_number=next(n for n,c in enumerate(capacities,1) if c[0]==cap)
            caption=f'Capacidad {cap_number}\nCriterio {per_cap[cap]}'
            raw.cell(1,mapping['column'],caption);mapping['header']=caption
            raw.cell(1,mapping['column']).comment=Comment(f"{next(c[1] for c in capacities if c[0]==cap)}\nCriterio en la hoja 1, fila {entry['row']}. Cada columna se evalúa por separado.",'Registro Docente')
        meta['raw_columns']=json.dumps(raw_map,ensure_ascii=False)
        for ws in (raw,summary):
            ws.sheet_view.zoomScale=95;ws.row_dimensions[1].height=72
            for col in range(1,ws.max_column+1):ws.column_dimensions[get_column_letter(col)].width=18
            ws.column_dimensions['A'].width=12;ws.column_dimensions['B'].width=22;ws.column_dimensions['C'].width=20
        for row in range(2,raw.max_row+1):
            for col in [*(m['column'] for m in raw_map),raw.max_column]:raw.cell(row,col).protection=Protection(locked=False)
        raw.protection.sheet=True;raw.protection.formatColumns=False;raw.protection.formatRows=False;raw.protection.sort=False;raw.protection.autoFilter=False
        for validation in raw.data_validations.dataValidation:
            validation.errorStyle='warning'
            validation.error='Seleccione un nivel o ingrese puntos de 0 al máximo del criterio.' if rubric else 'Seleccione Sí o No.'
        for row in range(2,summary.max_row+1):
            for col in (1,2,3,summary.max_column-1,summary.max_column):
                letter=get_column_letter(col if col<=3 else raw.max_column-1 if col==summary.max_column-1 else raw.max_column)
                summary.cell(row,col,f'=IF(\'{EVALUAR}\'!{letter}{row}="","",\'{EVALUAR}\'!{letter}{row})')
            for mapping in json.loads(meta['final_columns']):
                entries=[(entry,m) for entry,m in zip(layout,raw_map) if entry['cap']==mapping['cap']]
                cells=[f'{get_column_letter(m["column"])}{row}' for entry,m in entries]
                missing=','.join(f"'{EVALUAR}'!{cell}=\"\"" for cell in cells)
                points='+'.join(_point_formula(cell,entry['row'],meta['kind']) for (entry,m),cell in zip(entries,cells))
                maxima=','.join(f"'{IND}'!$H${entry['row']}" if rubric else f"'{IND}'!$E${entry['row']}" for entry,m in entries)
                if not rubric:points=points.replace("'1_Indicadores_Instrumento'!$H$","'1_Indicadores_Instrumento'!$E$")
                formula=f'=IF(OR({missing}),"",IFERROR(ROUND(20*({points})/SUM({maxima}),2),"Revisar"))'
                summary.cell(row,mapping['column'],formula).number_format='0.00'
        summary.protection.sheet=True;summary.protection.formatColumns=False
        summary.data_validations.dataValidation=[]
        instructions=wb['Instrucciones'];instructions.delete_rows(1,instructions.max_row)
        messages=[f'{meta["kind"]} · {title}',
            '1. Complete la hoja 1 con sus criterios y descriptores de la sesión. La rúbrica muestra C, B, A y AD; debajo de cada descriptor están sus puntos editables. AD vale el máximo y C < B < A < AD.',
            '2. Cada capacidad puede tener varios criterios. Los bloques son independientes: escriba una evidencia observable por bloque. Para cambiar su cantidad, descargue una plantilla nueva y elija cuántos necesita por capacidad; puede hacerlo sin diseñar primero en el programa.',
            '3. En 2_Evaluar_Criterios cada estudiante tiene una columna POR CRITERIO. Marque C, B, A o AD (rúbrica), o Sí/No (cotejo). También puede ingresar puntos numéricos en rúbrica. Vacío significa pendiente; Sin evidencia y No valen cero.',
            '4. En 3_Notas_Capacidades se calcula el resultado de TODOS los criterios de cada capacidad. Esta hoja es de consulta: no escriba una nota única para reemplazar los criterios.',
            '5. Nota = suma de puntos obtenidos ÷ suma de máximos × 20. Dos criterios de 10 puntos, con 6 y 8 obtenidos, dan 14/20. Complete todos los criterios de una capacidad antes de importarla.',
            '6. Guarde como XLSX. En Calificaciones pulse Importar Excel, revise el instrumento y los cambios y confirme. Se guardan las respuestas de cada criterio y las notas calculadas; asistencias y comentarios vacíos se conservan.',
            '7. Puede importar solo el instrumento dejando las respuestas vacías. Después evalúe los criterios en la pantalla principal y pulse Guardar notas.',
            'Conserve las columnas ocultas, los nombres y los códigos. La aplicación vuelve a calcular las notas desde las respuestas; no depende de resultados guardados de fórmulas de Excel.']
        for message in messages:instructions.append([message])
        instructions.column_dimensions['A'].width=100
        for row in instructions:
            row[0].font=Font(name='Calibri',size=12);row[0].alignment=Alignment(wrap_text=True,vertical='center');instructions.row_dimensions[row[0].row].height=65
        meta.update(version=4,layout_rows=json.dumps(layout),kind=meta['kind'])
        wb[META].delete_rows(1,wb[META].max_row)
        for key,value in meta.items():wb[META].append([key,value])
        wb._sheets=[sheet,raw,summary,instructions,wb[META]]
        wb.calculation=CalcProperties(fullCalcOnLoad=True,forceFullCalc=True)
        wb.save(destination)
    finally:wb.close()


def normalize_form(data,formulas):
    """Validate v4 structure then feed the same atomic v3 identity/scoring importer."""
    from instrumentos_excel import IND,FINAL,RAW,META
    meta=metadata(data)
    try:
        layout=json.loads(meta['layout_rows']);raw_map=json.loads(meta['raw_columns']);final_map=json.loads(meta['final_columns'])
        if not layout or len(layout)!=len(raw_map):raise ValueError()
        if EVALUAR not in data.sheetnames or RESUMEN not in data.sheetnames:raise ValueError()
    except (KeyError,ValueError,TypeError):raise ValueError('La plantilla está incompleta. Descargue un modelo actualizado.') from None
    result=openpyxl.Workbook();flat=result.active;flat.title=IND
    source=data[IND];rubric=meta['kind']=='Rúbrica'
    flat.append([source['A1'].value]);flat.append([source['A2'].value])
    flat.append(['CAP_ID','Capacidad','Criterio','Inicio (C)','Proceso (B)','Logro (A)','Destacado (AD)','Máximo','IND_ID','Puntos C','Puntos B','Puntos A','Puntos AD'] if rubric else ['CAP_ID','Capacidad','Criterio','Registro','Máximo','Tipo','IND_ID'])
    used_rows=set()
    for entry in layout:
        row=entry['row']
        if not isinstance(row,int) or row<4 or row>source.max_row or row in used_rows:raise ValueError('Los bloques de criterios del modelo cambiaron. Descargue la cantidad de criterios que necesita.')
        used_rows.add(row)
        identity=source.cell(row,9 if rubric else 7).value
        if identity!=entry['indicator'] or source.cell(row,1).value!=entry['cap']:raise ValueError('La identidad del criterio no coincide con el modelo.')
        values=[source.cell(row,col).value for col in range(1,10 if rubric else 8)]
        if rubric:
            score_row=entry.get('points_row')
            if score_row!=row+1 or source.cell(score_row,1).value!='PUNTOS':raise ValueError('Conserve la fila de puntos de cada criterio.')
            used_rows.add(score_row);values.extend(source.cell(score_row,col).value for col in range(4,8))
        flat.append(values)
    for row in source.iter_rows(min_row=4):
        if row[0].row not in used_rows and any(c.value is not None for c in row):raise ValueError('Hay criterios fuera del modelo. Descargue una plantilla con más criterios por capacidad.')
    raw=result.create_sheet(RAW)
    for row in data[EVALUAR].iter_rows(values_only=True):raw.append(list(row))
    for mapping in final_map:
        col=mapping['column']
        if data[RESUMEN].cell(1,col).value!=mapping['header']:raise ValueError('Conserve los encabezados del resumen por capacidades.')
        for row in range(2,formulas[RESUMEN].max_row+1):
            cell=formulas[RESUMEN].cell(row,col)
            if cell.value is not None and cell.data_type!='f':raise ValueError('El resumen se calcula desde los criterios. Ingrese cada respuesta en 2_Evaluar_Criterios.')
    final=result.create_sheet(FINAL)
    final.append(['Código','Apellidos','Nombres']+[m['header'] for m in final_map]+['EST_ID','Comentario'])
    identity_col=next((c.column for c in raw[1] if c.value=='EST_ID'),None)
    if identity_col is None:raise ValueError('Conserve EST_ID en la hoja de evaluación.')
    for row in raw.iter_rows(min_row=2,values_only=True):
        if any(v is not None for v in row):final.append([*row[:3],*['']*len(final_map),row[identity_col-1],''])
    metadata_sheet=result.create_sheet(META);meta['version']=3
    for key,value in meta.items():metadata_sheet.append([key,value])
    checked=openpyxl.Workbook();checked.remove(checked.active)
    for ws in result:
        cloned=checked.create_sheet(ws.title)
        origin=formulas[EVALUAR] if ws.title==RAW else ws
        for row in origin.iter_rows(values_only=True):cloned.append(list(row))
    return result,checked
