"""Structured instrument definitions and saved evidence; no implicit grade writes."""
import json,sqlite3
from db_safety import connection,valid_number
from escala import thresholds
from instrumentos import definition,validate_definition,instrument_kind,normalized,LEVELS,answer_points,normalized_grade,rescale_answer


def activity(session,path):
    with connection(path) as conn:
        conn.row_factory=sqlite3.Row
        row=conn.execute('''SELECT s.*,c.nombre AS curso_nombre,p.nombre AS competencia_nombre
            FROM Sesiones_Clase s JOIN Cursos c ON c.id=s.curso_id JOIN Competencias p ON p.id=s.competencia_id
            WHERE s.id=?''',(session,)).fetchone()
        if not row:raise ValueError('La actividad no existe.')
        result=dict(row)
        result['capacidades']=[dict(r) for r in conn.execute('''SELECT s.capacidad_id,c.nombre AS capacidad_nombre,s.criterio_precisado
            FROM Sesion_Capacidades s JOIN Capacidades c ON c.id=s.capacidad_id WHERE s.sesion_id=? ORDER BY c.id''',(session,))]
        return result


def migrate(conn):
    columns={r[1] for r in conn.execute('PRAGMA table_info(Instrumento_Indicadores)')}
    for name,sql in [('puntos_niveles',"TEXT NOT NULL DEFAULT ''"),('activo','INTEGER NOT NULL DEFAULT 1'),('orden','INTEGER NOT NULL DEFAULT 0')]:
        if name not in columns:conn.execute(f'ALTER TABLE Instrumento_Indicadores ADD COLUMN {name} {sql}')
    conn.execute('''CREATE TABLE IF NOT EXISTS Instrumento_Respuestas(
        sesion_id INTEGER NOT NULL, estudiante_id INTEGER NOT NULL, indicador_id INTEGER NOT NULL,
        respuesta TEXT NOT NULL,
        PRIMARY KEY(sesion_id,estudiante_id,indicador_id),
        FOREIGN KEY(sesion_id) REFERENCES Sesiones_Clase(id) ON DELETE CASCADE,
        FOREIGN KEY(estudiante_id) REFERENCES Estudiantes(ID) ON DELETE CASCADE,
        FOREIGN KEY(indicador_id) REFERENCES Instrumento_Indicadores(id) ON DELETE CASCADE)''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_instrumento_sesion ON Instrumento_Indicadores(sesion_id,activo)')


def get_indicators(session,path):
    limits=thresholds(path)
    with connection(path) as conn:
        conn.row_factory=sqlite3.Row
        rows=conn.execute('''SELECT i.*,c.nombre AS capacidad_nombre FROM Instrumento_Indicadores i
            JOIN Capacidades c ON c.id=i.capacidad_id WHERE i.sesion_id=? AND i.activo=1
            ORDER BY i.capacidad_id,i.orden,i.id''',(session,)).fetchall()
    return [definition(dict(row),limits) for row in rows]


def save_indicators(session,kind,items,path):
    kind=instrument_kind(kind);limits=thresholds(path)
    with connection(path) as conn:
        allowed={r[0]:r[1] for r in conn.execute('''SELECT c.id,c.nombre FROM Sesion_Capacidades s
            JOIN Capacidades c ON c.id=s.capacidad_id WHERE s.sesion_id=?''',(session,))}
        if not allowed:raise ValueError('La actividad no tiene capacidades.')
        original={i['id']:i for i in get_indicators(session,path)}
        definitions=[];used=set()
        for raw in items:
            row=dict(raw) if isinstance(raw,dict) else dict(capacidad_id=raw[0],indicador_texto=raw[1],puntaje_maximo=raw[2])
            cap=row['capacidad_id']
            if cap not in allowed:raise ValueError('La capacidad no pertenece a la actividad.')
            row.update(tipo=kind,capacidad_nombre=allowed[cap])
            row=validate_definition(row,limits)
            identity=row.get('id')
            if identity is None:
                identity=next((i for i,old in original.items() if i not in used and old['tipo']==kind and old['capacidad_id']==cap and old['criterio']==row['criterio']),None)
            if identity is not None:
                if identity not in original or identity in used:raise ValueError('Criterio repetido o perteneciente a otra actividad.')
                old=original[identity]
                if old['tipo']!=kind:raise ValueError('El criterio pertenece a otro tipo de instrumento. Cree uno nuevo para conservar la evaluación anterior.')
                if old['capacidad_id']!=cap and conn.execute('SELECT 1 FROM Instrumento_Respuestas WHERE indicador_id=? LIMIT 1',(identity,)).fetchone():
                    raise ValueError('Este criterio ya tiene respuestas. Cree otro para cambiar de capacidad; las evaluaciones anteriores se conservan.')
                used.add(identity)
            row['id']=identity;definitions.append(row)
        if not definitions:raise ValueError('Conserve al menos un criterio.')
        result=[]
        for order,item in enumerate(definitions):
            data=(session,item['capacidad_id'],kind,item['criterio'],item['puntaje_maximo'],
                *(item['descriptores'][l] for l in ('AD','A','B','C')),json.dumps(item['puntajes']),order)
            if item['id'] is None:
                identity=conn.execute('''INSERT INTO Instrumento_Indicadores(sesion_id,capacidad_id,tipo,indicador_texto,
                    puntaje_maximo,descriptor_ad,descriptor_a,descriptor_b,descriptor_c,puntos_niveles,orden)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)''',data).lastrowid
            else:
                identity=item['id']
                old=original[identity]
                if old['puntaje_maximo']!=item['puntaje_maximo']:
                    responses=conn.execute('SELECT estudiante_id,respuesta FROM Instrumento_Respuestas WHERE sesion_id=? AND indicador_id=?',(session,identity)).fetchall()
                    for student,value in responses:
                        scaled=rescale_answer(value,old,item)
                        conn.execute('UPDATE Instrumento_Respuestas SET respuesta=? WHERE sesion_id=? AND estudiante_id=? AND indicador_id=?',(scaled,session,student,identity))
                conn.execute('''UPDATE Instrumento_Indicadores SET sesion_id=?,capacidad_id=?,tipo=?,indicador_texto=?,
                    puntaje_maximo=?,descriptor_ad=?,descriptor_a=?,descriptor_b=?,descriptor_c=?,puntos_niveles=?,orden=?,activo=1 WHERE id=?''',(*data,identity))
            result.append(identity)
        for identity in set(original)-used:
            if conn.execute('SELECT 1 FROM Instrumento_Respuestas WHERE indicador_id=? LIMIT 1',(identity,)).fetchone():
                conn.execute('UPDATE Instrumento_Indicadores SET activo=0 WHERE id=?',(identity,))
            else:conn.execute('DELETE FROM Instrumento_Indicadores WHERE id=?',(identity,))
        conn.execute('UPDATE Sesiones_Clase SET tipo_instrumento=? WHERE id=?',(kind,session))
        return result


def get_answers(session,path):
    with connection(path) as conn:
        return {(r[0],r[1]):r[2] for r in conn.execute('''SELECT r.estudiante_id,r.indicador_id,r.respuesta
            FROM Instrumento_Respuestas r JOIN Instrumento_Indicadores i ON i.id=r.indicador_id
            WHERE r.sesion_id=? AND i.activo=1''',(session,))}


def save_answers(session,rows,path):
    indicators={i['id']:i for i in get_indicators(session,path)}
    with connection(path) as conn:
        students={r[0] for r in conn.execute('''SELECT e.ID FROM Estudiantes e JOIN Sesiones_Clase s
            ON s.grado=e.Grado AND s.seccion=e.Seccion AND s.nivel=e.nivel WHERE s.id=?''',(session,))}
        used=set();prepared=[]
        for row in rows:
            student=row['estudiante_id'];identity=row['indicador_id'];value=row.get('respuesta')
            if student not in students or identity not in indicators:raise ValueError('Respuesta de otro estudiante, actividad o criterio.')
            if (student,identity) in used:raise ValueError('Hay respuestas repetidas para un mismo criterio.')
            used.add((student,identity))
            item=indicators[identity]
            if value is not None and str(value).strip():
                points=answer_points(item['tipo'],value,item['puntaje_maximo'],item['puntajes'])
                if item['tipo']=='Lista de Cotejo':value='Sí' if points else 'No'
                elif str(value).strip().upper() in LEVELS:value=str(value).strip().upper()
                elif normalized(value) in ('ne','sin evidencia'):value='NE'
                else:value=str(points).removesuffix('.0')
            else:value=None
            prepared.append((student,identity,value))
        for student,identity,value in prepared:
            if value is None:conn.execute('DELETE FROM Instrumento_Respuestas WHERE sesion_id=? AND estudiante_id=? AND indicador_id=?',(session,student,identity))
            else:conn.execute('''INSERT INTO Instrumento_Respuestas VALUES(?,?,?,?)
                ON CONFLICT(sesion_id,estudiante_id,indicador_id) DO UPDATE SET respuesta=excluded.respuesta''',(session,student,identity,value))


def grade_answers(indicators,answers):
    capacities={i['capacidad_id'] for i in indicators};students={s for s,i in answers}
    grades={};pending=set()
    for student in students:
        for cap in capacities:
            items=[i for i in indicators if i['capacidad_id']==cap]
            values=[(answers.get((student,i['id'])),i['puntaje_maximo'],i['puntajes']) for i in items]
            filled=[v for v,m,p in values if v is not None and str(v).strip()]
            if not filled:continue
            if len(filled)<len(values):pending.add((student,cap))
            grades[(student,cap)]=normalized_grade(items[0]['tipo'],values,allow_pending=True)
    return grades,pending
