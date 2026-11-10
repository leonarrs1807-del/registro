"""Validate a whole clipboard range before modifying any cell."""
import csv
import io
from db_safety import valid_number


def plan(rows,text,start=0,column=0,capacities=1,global_grade=False):
    values=list(csv.reader(io.StringIO(text),delimiter='\t'))
    while values and not any(v.strip() for v in values[-1]):values.pop()
    if not values:raise ValueError('El portapapeles está vacío.')
    if start<0 or start+len(values)>len(rows):raise ValueError('El bloque supera el número de estudiantes disponibles.')
    width=len(values[0])
    if not width or any(len(line)!=width for line in values):raise ValueError('Pegue un bloque rectangular de notas, sin nombres ni encabezados.')
    limit=1 if global_grade else capacities
    if column<0 or column+width>limit:raise ValueError('El bloque supera las columnas de evaluación disponibles.')
    result=[list(row) for row in rows];preview=[]
    for offset,line in enumerate(values):
        for j,value in enumerate(line):
            try:value='' if not value.strip() else str(valid_number(value.replace(',','.'))).removesuffix('.0')
            except ValueError as exc:raise ValueError(f'Fila {offset+1}, columna {j+1}: {exc}') from exc
            targets=range(capacities) if global_grade else [column+j]
            for target in targets:result[start+offset][4+target]=value
        preview.append((start+offset+1,result[start+offset][2],line))
    return result,preview
