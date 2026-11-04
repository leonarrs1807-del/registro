"""Two visible worksheets, clean student rows and observation-only checklists."""
import json,re,textwrap
from copy import copy
import openpyxl
from openpyxl.styles import Alignment,Font,PatternFill,Protection
from openpyxl.utils import get_column_letter,column_index_from_string
from openpyxl.comments import Comment
from instrumentos import LEVELS,default_scores,normalized
from cotejo import capacity_label
from colores import HEADER,HEADER_TEXT
from escala import thresholds

INSTRUMENTO='Instrumento'
REGISTRO='Registro'


def _earned(cell,row,ratios):
    value=f"'{REGISTRO}'!{cell}";token=f'UPPER(TRIM({value}))'
    maximum=f"'{INSTRUMENTO}'!$H${row}";match=f'MATCH({token},{{"C","B","A","AD"}},0)'
    points=f"INDEX('{INSTRUMENTO}'!$D${row+1}:$G${row+1},1,{match})"
    default=f'{maximum}*INDEX({{{",".join(str(v) for v in ratios)}}},1,{match})'
    level=f'IF(ISBLANK({points}),{default},{points})'
    numeric=f'NUMBERVALUE(SUBSTITUTE(TRIM({value}),",","."),"."," ")'
    chosen=f'IFERROR({level},{numeric})'
    return f'IF({value}="",0,IF(OR({token}="NE",{token}="SIN EVIDENCIA"),0,IF(AND({chosen}>=0,{chosen}<={maximum}),{chosen},NA())))'


def export_form(destination,course,grade,section,title,competency,capacities,kind,path,session,counts,blank,include_students):
    from plantilla_excel import export_form as old_export,EVALUAR,RESUMEN,metadata
    from instrumentos_excel import IND,META,freeze_view
    old_export(destination,course,grade,section,title,competency,capacities,kind,path,session,counts,blank)
    wb=openpyxl.load_workbook(destination)
    try:
        meta=metadata(wb);rubric=meta['kind']=='Rúbrica';design=wb[IND];raw=wb[EVALUAR];summary=wb[RESUMEN]
        layout=json.loads(meta['layout_rows']);mappings=json.loads(meta['raw_columns']);width=raw.max_column
        if not include_students:raw.delete_rows(2,raw.max_row)
        raw.insert_cols(4);raw['D1']='Estudiante'
        for dimension in raw.column_dimensions.values():dimension.hidden=False
        for row in range(2,max(22,raw.max_row)+1):
            last=raw.cell(row,2).value;first=raw.cell(row,3).value
            raw.cell(row,4,f'{last}, {first}' if last or first else None)
            for mapping in mappings:raw.cell(row,mapping['column']+1,None).value=None
            raw.cell(row,width+1,None).value=None
        names={cap:name for cap,name,text in capacities}
        header_formulas=[];per_cap={}
        for mapping in mappings:
            entry=next(e for e in layout if e['indicator']==mapping['indicator'])
            cap=mapping['cap'];per_cap[cap]=per_cap.get(cap,0)+1
            caption=capacity_label(names[cap])+'\nCriterio '+str(per_cap[cap]);mapping['header']=caption
            formula=f'="{capacity_label(names[cap])}"&CHAR(10)&IF(\'{INSTRUMENTO}\'!$C${entry["row"]}="","Criterio {per_cap[cap]}",\'{INSTRUMENTO}\'!$C${entry["row"]})'
            raw.cell(1,mapping['column']+1,formula);header_formulas.append(formula)
        for col in ('A','B','C'):raw.column_dimensions[col].hidden=True
        raw.column_dimensions['D'].width=30
        raw.column_dimensions[get_column_letter(width)].hidden=True
        raw.column_dimensions[get_column_letter(width+1)].width=28
        raw.cell(1,width+1,'Observación')
        for mapping in mappings:raw.column_dimensions[get_column_letter(mapping['column']+1)].width=25
        raw.data_validations.dataValidation[0].sqref=''
        raw.data_validations.dataValidation[0].formula1='"C,B,A,AD,Sin evidencia"' if rubric else '"Sí,No,Sin evaluar"'
        for mapping in mappings:raw.data_validations.dataValidation[0].add(f'{get_column_letter(mapping["column"]+1)}2:{get_column_letter(mapping["column"]+1)}1000')
        freeze_view(raw,'E2');raw.row_dimensions[1].height=64
        for row in range(2,max(22,raw.max_row)+1):
            for col in [4,*[m['column']+1 for m in mappings],width+1]:
                cell=raw.cell(row,col);cell.protection=Protection(locked=False);cell.alignment=Alignment(vertical='center',wrap_text=True)
                cell.font=Font(name='Calibri',size=11)
            raw.row_dimensions[row].height=27
        if rubric:
            limits=list(thresholds(path));ratios=[default_scores(20,limits)[level]/20 for level in LEVELS]
            summary.delete_rows(2,summary.max_row)
            base=max(10,summary.max_column+1)
            for index,(entry,mapping) in enumerate(zip(layout,mappings)):
                point_col=base+2*index;max_col=point_col+1
                for row in range(2,raw.max_row+1):
                    cell=f'{get_column_letter(mapping["column"]+1)}{row}'
                    summary.cell(row,point_col,'='+_earned(cell,entry['row'],ratios))
                    summary.cell(row,max_col,f'=IF(\'{REGISTRO}\'!{cell}="",0,\'{INSTRUMENTO}\'!$H${entry["row"]})')
            for mapping in json.loads(meta['final_columns']):
                col=raw.max_column+1;raw.cell(1,col,'Nota · '+capacity_label(names[mapping['cap']]))
                raw.column_dimensions[get_column_letter(col)].width=24
                indexes=[n for n,m in enumerate(mappings) if m['cap']==mapping['cap']]
                for row in range(2,raw.max_row+1):
                    points=','.join(f'{get_column_letter(base+2*n)}{row}' for n in indexes)
                    maxima=','.join(f'{get_column_letter(base+2*n+1)}{row}' for n in indexes)
                    summary.cell(row,mapping['column'],f'=IF(SUM({maxima})=0,"",IFERROR(ROUND(20*SUM({points})/SUM({maxima}),2),"Revisar"))')
                    raw.cell(row,col,f'=IF(D{row}="","",\'{RESUMEN}\'!{get_column_letter(mapping["column"])}{row})').number_format='0.00'
            if blank:
                for entry in layout:
                    for col in range(4,8):design.cell(entry['points_row'],col).value=None
                    design.cell(entry['points_row'],3,'Puntos por nivel (opcional)')
        else:
            limits=list(thresholds(path));summary.delete_rows(2,summary.max_row)
            design.column_dimensions['D'].hidden=True;design.column_dimensions['E'].hidden=True
            for heading,formula in [('Cumple / Evaluados',None),('Pendientes',None)]:
                col=raw.max_column+1;raw.cell(1,col,heading);raw.column_dimensions[get_column_letter(col)].width=22
                for row in range(2,raw.max_row+1):
                    refs=','.join(f'{get_column_letter(m["column"]+1)}{row}' for m in mappings)
                    yes='+'.join(f'COUNTIF({get_column_letter(m["column"]+1)}{row},"Sí")' for m in mappings)
                    evaluated='+'.join(f'COUNTIF({get_column_letter(m["column"]+1)}{row},"Sí")+COUNTIF({get_column_letter(m["column"]+1)}{row},"No")' for m in mappings)
                    value=f'({yes})&" / "&({evaluated})' if heading=='Cumple / Evaluados' else f'{len(mappings)}-({evaluated})'
                    raw.cell(row,col,f'=IF(D{row}="","",{value})')
        def shift(match):
            col=column_index_from_string(match[1]);return "'"+REGISTRO+"'!"+get_column_letter(col+1 if col>=4 else col)+match[2]
        for ws in wb:
            for row in ws:
                for cell in row:
                    if cell.data_type=='f':
                        cell.value=re.sub(r"'2_Evaluar_Criterios'!([A-Z]+)(\d+)",shift,cell.value).replace("'"+IND+"'!","'"+INSTRUMENTO+"'!")
        if session:
            from evaluacion_datos import activity
            purpose=activity(session,path).get('proposito') or ''
            if purpose:
                design['A2']=str(design['A2'].value or '')+'\nPropósito: '+purpose
                design['A2'].alignment=Alignment(wrap_text=True,vertical='center');design.row_dimensions[2].height=60
        for entry in layout:
            design.cell(entry['row'],3).comment=Comment('Complete el criterio de esta sesión. Los bloques nuevos que deje totalmente vacíos se omiten al importar.','Registro Docente')
        design.title=INSTRUMENTO;raw.title=REGISTRO;summary.sheet_state='hidden'
        if 'Instrucciones' in wb:wb.remove(wb['Instrucciones'])
        meta.update(version=5,raw_columns=json.dumps(mappings,ensure_ascii=False),simple_raw_width=width,orientation=not rubric,simple_headers=json.dumps(header_formulas,ensure_ascii=False),simple_limits=json.dumps(limits))
        wb[META].delete_rows(1,wb[META].max_row)
        for key,value in meta.items():wb[META].append([key,value])
        for ws in (design,raw):
            for row in ws:
                for cell in row:
                    color=cell.fill.fgColor
                    if color.type=='rgb' and str(color.rgb)[-6:].upper() in ('1E3A8A','1E293B','0F172A','2563EB','1D4ED8'):
                        cell.fill=PatternFill('solid',fgColor=HEADER[1:]);font=copy(cell.font);font.color=HEADER_TEXT[1:];cell.font=font
        wb._sheets=[design,raw,summary,wb[META]];wb.active=0;wb.save(destination)
    finally:wb.close()


def normalize_form(data,formulas,path):
    from plantilla_excel import EVALUAR,RESUMEN,metadata,normalize_form as normalize_old
    from instrumentos_excel import IND,META
    import db
    meta=metadata(data)
    if INSTRUMENTO not in data or REGISTRO not in data:raise ValueError('Conserve las hojas Instrumento y Registro.')
    layouts=json.loads(meta['layout_rows']);mappings=json.loads(meta['raw_columns']);width=meta['simple_raw_width']
    if not isinstance(width,int) or width!=len(mappings)+5:raise ValueError('La estructura del registro no coincide con el modelo.')
    original_names=['Código','Apellidos','Nombres']+[m['header'] for m in mappings]+['EST_ID','Comentario']
    headers=json.loads(meta['simple_headers'])
    if len(headers)!=len(mappings) or any(formulas[REGISTRO].cell(1,m['column']+1).value!=h for m,h in zip(mappings,headers)):
        raise ValueError('Conserve los encabezados del Registro. Edite los criterios en Instrumento.')
    roster=db.obtener_estudiantes_filtrados(meta['grade'],meta['section'],'',incluir_retirados=True,db_path=path)
    full_names={}
    for student in roster:full_names.setdefault(normalized(f"{student['Apellidos']}, {student['Nombres']}"),[]).append(student)
    pairs=[]
    for source in (data,formulas):
        result=openpyxl.Workbook();result.remove(result.active)
        for ws in source:
            clone=result.create_sheet(IND if ws.title==INSTRUMENTO else EVALUAR if ws.title==REGISTRO else ws.title)
            if ws.title==REGISTRO:
                clone.append(original_names)
                for row_number in range(2,ws.max_row+1):
                    vals=[ws.cell(row_number,col).value for col in range(1,width+2)];display=vals.pop(3)
                    if display is not None and str(display).strip():
                        if vals[0] is None:
                            candidates=full_names.get(normalized(display),[])
                            if len(candidates)!=1:raise ValueError(f'Fila {row_number}: registre primero al alumno o exporte con el alumnado del aula para identificarlo.')
                            student=candidates[0];vals[:3]=[student['Codigo_Unico'],student['Apellidos'],student['Nombres']];vals[-2]=student['ID']
                        elif normalized(display)!=normalized(f'{vals[1]}, {vals[2]}'):raise ValueError('El nombre visible no coincide con la identidad del estudiante.')
                    elif any(v is not None and str(v).strip() for v in vals):raise ValueError('No elimine el nombre de un estudiante con respuestas.')
                    for mapping in mappings:
                        index=mapping['column']-1
                        if normalized(vals[index])=='sin evaluar':vals[index]=None
                    if any(v is not None and str(v).strip() for v in vals):clone.append(vals)
            else:
                for row in ws.iter_rows(values_only=True):clone.append(list(row))
        pairs.append(result)
    converted,checked=pairs;design=converted[IND];rubric=meta['kind']=='Rúbrica';keep=[]
    for entry in layouts:
        row=entry['row'];identity=entry['indicator'];mapping=next(m for m in mappings if m['indicator']==identity)
        if not str(design.cell(row,3).value or '').strip():
            if str(identity).startswith('I') or any(converted[EVALUAR].cell(r,mapping['column']).value is not None for r in range(2,converted[EVALUAR].max_row+1)):
                raise ValueError('Complete el criterio antes de evaluarlo. Los criterios guardados no se eliminan vaciando su texto en Excel.')
            for r in (row,row+1) if rubric else (row,):
                for col in range(1,design.max_column+1):design.cell(r,col).value=None
            continue
        if rubric:
            maximum=design.cell(row,8).value;defaults=default_scores(maximum,json.loads(meta['simple_limits']))
            for col,level in enumerate(LEVELS,4):
                if design.cell(row+1,col).value is None:design.cell(row+1,col,defaults[level])
        keep.append(entry)
    if not keep:raise ValueError('Complete al menos un criterio en Instrumento.')
    removed=[m['column'] for m in mappings if m['indicator'] not in {e['indicator'] for e in keep}]
    for wb in pairs:
        raw=wb[EVALUAR]
        for col in sorted(removed,reverse=True):raw.delete_cols(col)
    new_mapping=[]
    for m in mappings:
        if m['column'] not in removed:new_mapping.append({**m,'column':4+len(new_mapping)})
    meta.update(version=4,layout_rows=json.dumps(keep),raw_columns=json.dumps(new_mapping,ensure_ascii=False))
    for wb in pairs:
        ws=wb[META];ws.delete_rows(1,ws.max_row)
        for key,value in meta.items():ws.append([key,value])
    try:return normalize_old(converted,checked)
    finally:converted.close();checked.close()
