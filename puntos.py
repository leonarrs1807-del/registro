"""Short practices accumulated into one explicit exam grade per competency."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json
from db_safety import connection, valid_number


def ensure_schema(conn):
    statements = [
        '''CREATE TABLE IF NOT EXISTS Puntos_Bloques (
            id INTEGER PRIMARY KEY AUTOINCREMENT, curso_id INTEGER NOT NULL,
            competencia_id INTEGER NOT NULL, grado TEXT NOT NULL, seccion TEXT NOT NULL,
            tema TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'abierto' CHECK(estado IN ('abierto','consolidado')),
            sesion_id INTEGER UNIQUE, creado TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(curso_id) REFERENCES Cursos(id) ON DELETE CASCADE,
            FOREIGN KEY(competencia_id) REFERENCES Competencias(id) ON DELETE CASCADE,
            FOREIGN KEY(sesion_id) REFERENCES Sesiones_Clase(id) ON DELETE SET NULL)''',
        '''CREATE TABLE IF NOT EXISTS Puntos_Capacidades (
            bloque_id INTEGER NOT NULL, capacidad_id INTEGER NOT NULL,
            PRIMARY KEY(bloque_id,capacidad_id),
            FOREIGN KEY(bloque_id) REFERENCES Puntos_Bloques(id) ON DELETE CASCADE,
            FOREIGN KEY(capacidad_id) REFERENCES Capacidades(id) ON DELETE CASCADE)''',
        '''CREATE TABLE IF NOT EXISTS Puntos_Practicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, bloque_id INTEGER NOT NULL,
            titulo TEXT NOT NULL, fecha TEXT NOT NULL, minutos INTEGER NOT NULL CHECK(minutos BETWEEN 1 AND 480),
            activa INTEGER NOT NULL DEFAULT 1 CHECK(activa IN (0,1)),
            FOREIGN KEY(bloque_id) REFERENCES Puntos_Bloques(id) ON DELETE CASCADE)''',
        '''CREATE TABLE IF NOT EXISTS Puntos_Ejercicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT, practica_id INTEGER NOT NULL,
            numero INTEGER NOT NULL, descripcion TEXT NOT NULL,
            maximo REAL NOT NULL CHECK(maximo>0 AND maximo<=10000),
            UNIQUE(practica_id,numero),
            FOREIGN KEY(practica_id) REFERENCES Puntos_Practicas(id) ON DELETE CASCADE)''',
        '''CREATE TABLE IF NOT EXISTS Puntos_Registro (
            ejercicio_id INTEGER NOT NULL, estudiante_id INTEGER NOT NULL, obtenido REAL,
            PRIMARY KEY(ejercicio_id,estudiante_id),
            FOREIGN KEY(ejercicio_id) REFERENCES Puntos_Ejercicios(id) ON DELETE CASCADE,
            FOREIGN KEY(estudiante_id) REFERENCES Estudiantes(ID) ON DELETE CASCADE)''',
        '''CREATE TABLE IF NOT EXISTS Puntos_Historial (
            id INTEGER PRIMARY KEY, fecha TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            bloque_id INTEGER, accion TEXT NOT NULL, detalle TEXT NOT NULL, usuario TEXT NOT NULL)'''
    ]
    for sql in statements:
        conn.execute(sql)
    for operation in ('INSERT','UPDATE'):
        conn.execute(f'''CREATE TRIGGER IF NOT EXISTS validar_puntos_{operation}
            BEFORE {operation} ON Puntos_Registro
            WHEN NEW.obtenido IS NOT NULL AND (typeof(NEW.obtenido) NOT IN ('integer','real')
              OR NEW.obtenido<0 OR NEW.obtenido>(SELECT maximo FROM Puntos_Ejercicios WHERE id=NEW.ejercicio_id))
            BEGIN SELECT RAISE(ABORT,'Puntos fuera del máximo del ejercicio'); END''')


def _audit(conn, block, action, detail):
    user = conn.execute('SELECT usuario FROM Docente_Config WHERE id=1').fetchone()[0]
    conn.execute('INSERT INTO Puntos_Historial(bloque_id,accion,detalle,usuario) VALUES(?,?,?,?)',
                 (block, action, json.dumps(detail, ensure_ascii=False), user))


def _editable(conn, block_id):
    row = conn.execute('SELECT * FROM Puntos_Bloques WHERE id=?', (block_id,)).fetchone()
    if row is None:
        raise ValueError('Seleccione un bloque de prácticas existente.')
    names = [r[1] for r in conn.execute('PRAGMA table_info(Puntos_Bloques)')]
    block = dict(zip(names, row))
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name='Estado_Periodo'").fetchone():
        closed = conn.execute('SELECT cerrado FROM Estado_Periodo WHERE id=1').fetchone()
        if closed and closed[0]:
            raise ValueError('El periodo está cerrado. Reábralo antes de modificar puntos.')
    if block['estado'] != 'abierto':
        raise ValueError('El bloque ya fue consolidado. Reábralo para corregir sus prácticas.')
    return block


def list_blocks(path, course, grade, section):
    with connection(path) as conn:
        conn.row_factory = __import__('sqlite3').Row
        return [dict(r) for r in conn.execute('''SELECT b.*, c.nombre AS competencia,
            (SELECT COUNT(*) FROM Puntos_Practicas p WHERE p.bloque_id=b.id AND p.activa=1) AS practicas
            FROM Puntos_Bloques b JOIN Competencias c ON c.id=b.competencia_id
            WHERE b.curso_id=? AND b.grado=? AND b.seccion=? ORDER BY b.id DESC''', (course,grade,section))]


def create_block(path, course, competency, grade, section, topic, capacities):
    topic = topic.strip()
    if not topic or not grade.strip() or not section.strip():
        raise ValueError('Indique tema, grado y sección.')
    capacities = list(dict.fromkeys(capacities))
    if not capacities:
        raise ValueError('Marque al menos una capacidad para la nota acumulada.')
    with connection(path) as conn:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name='Estado_Periodo'").fetchone():
            row = conn.execute('SELECT cerrado FROM Estado_Periodo WHERE id=1').fetchone()
            if row and row[0]: raise ValueError('El periodo está cerrado.')
        if not conn.execute('SELECT 1 FROM Competencias WHERE id=? AND curso_id=?', (competency,course)).fetchone():
            raise ValueError('La competencia no pertenece al curso.')
        allowed = {r[0] for r in conn.execute('SELECT id FROM Capacidades WHERE competencia_id=?',(competency,))}
        if not set(capacities) <= allowed:
            raise ValueError('Las capacidades deben pertenecer a la competencia elegida.')
        block = conn.execute('''INSERT INTO Puntos_Bloques(curso_id,competencia_id,grado,seccion,tema)
            VALUES(?,?,?,?,?)''', (course,competency,grade.strip(),section.strip().upper(),topic)).lastrowid
        conn.executemany('INSERT INTO Puntos_Capacidades VALUES(?,?)', [(block,c) for c in capacities])
        _audit(conn, block, 'Crear bloque', {'tema':topic,'capacidades':capacities})
        return block


def add_practice(path, block, title, exercises, minutes=20, when=None):
    if not title.strip(): raise ValueError('La práctica necesita un nombre.')
    if not isinstance(minutes,int) or not 1<=minutes<=480: raise ValueError('La duración debe estar entre 1 y 480 minutos.')
    if not 1<=len(exercises)<=20: raise ValueError('Incluya entre 1 y 20 ejercicios.')
    parsed = [(description.strip() or f'Ejercicio {i+1}',valid_number(maximum,.01,10000,'Puntaje máximo'))
              for i,(description,maximum) in enumerate(exercises)]
    when = date.fromisoformat(when or date.today().isoformat()).isoformat()
    with connection(path) as conn:
        _editable(conn,block)
        practice = conn.execute('INSERT INTO Puntos_Practicas(bloque_id,titulo,fecha,minutos) VALUES(?,?,?,?)',
                                (block,title.strip(),when,minutes)).lastrowid
        conn.executemany('INSERT INTO Puntos_Ejercicios(practica_id,numero,descripcion,maximo) VALUES(?,?,?,?)',
                         [(practice,i+1,description,maximum) for i,(description,maximum) in enumerate(parsed)])
        _audit(conn,block,'Agregar práctica',{'practica':practice,'titulo':title,'ejercicios':parsed,'minutos':minutes})
        return practice


def details(path, block):
    import sqlite3
    with connection(path) as conn:
        conn.row_factory=sqlite3.Row
        b=conn.execute('SELECT * FROM Puntos_Bloques WHERE id=?',(block,)).fetchone()
        if not b:raise ValueError('El bloque ya no existe.')
        b=dict(b)
        practices=[dict(r) for r in conn.execute('SELECT * FROM Puntos_Practicas WHERE bloque_id=? ORDER BY fecha,id',(block,))]
        exercises=[dict(r) for r in conn.execute('''SELECT e.*,p.titulo AS practica,p.fecha,p.minutos,p.activa
            FROM Puntos_Ejercicios e JOIN Puntos_Practicas p ON p.id=e.practica_id
            WHERE p.bloque_id=? ORDER BY p.fecha,p.id,e.numero''',(block,))]
        students=[dict(r) for r in conn.execute('''SELECT e.ID,e.Codigo_Unico,e.Apellidos,e.Nombres FROM Estudiantes e
            JOIN Cursos c ON c.nivel=e.nivel AND c.id=? WHERE e.Grado=? AND e.Seccion=?
            AND COALESCE(e.Estado,'ACTIVO')='ACTIVO' ORDER BY e.Apellidos,e.Nombres,e.ID''',
            (b['curso_id'],b['grado'],b['seccion']))]
        scores={(r['ejercicio_id'],r['estudiante_id']):r['obtenido'] for r in conn.execute('''
            SELECT r.* FROM Puntos_Registro r JOIN Puntos_Ejercicios e ON e.id=r.ejercicio_id
            JOIN Puntos_Practicas p ON p.id=e.practica_id WHERE p.bloque_id=?''',(block,))}
        capacities=[r[0] for r in conn.execute('SELECT capacidad_id FROM Puntos_Capacidades WHERE bloque_id=?',(block,))]
        return {'block':b,'practices':practices,'exercises':exercises,'students':students,'scores':scores,'capacities':capacities}


def save_scores(path, block, values):
    """Validate every cell before applying the batch; empty values stay unevaluated."""
    with connection(path) as conn:
        _editable(conn,block)
        data=details(path,block)
        allowed_ex={e['id']:e for e in data['exercises'] if e['activa']}
        students={s['ID'] for s in data['students']}
        parsed=[];seen=set()
        for exercise,student,value in values:
            if (exercise,student) in seen:raise ValueError('Hay una celda de puntos repetida.')
            seen.add((exercise,student))
            if exercise not in allowed_ex or student not in students:
                raise ValueError('El ejercicio o estudiante no corresponde al bloque y salón.')
            number=None if value is None or str(value).strip()=='' else valid_number(str(value).replace(',','.'),0,allowed_ex[exercise]['maximo'],'Puntos obtenidos')
            parsed.append((exercise,student,number))
        for exercise,student,number in parsed:
            previous=data['scores'].get((exercise,student))
            if previous==number:continue
            conn.execute('''INSERT INTO Puntos_Registro VALUES(?,?,?) ON CONFLICT(ejercicio_id,estudiante_id)
                DO UPDATE SET obtenido=excluded.obtenido''',(exercise,student,number))
            _audit(conn,block,'Cambiar puntos',{'ejercicio':exercise,'estudiante':student,'anterior':previous,'nuevo':number})
        return len(parsed)


def summary(path, block):
    data=details(path,block)
    exercises=[e for e in data['exercises'] if e['activa']]
    maximum=sum((Decimal(str(e['maximo'])) for e in exercises),Decimal(0))
    rows=[]
    for student in data['students']:
        total=Decimal(0);pending=0
        for exercise in exercises:
            value=data['scores'].get((exercise['id'],student['ID']))
            if value is None:pending+=1
            else:total+=Decimal(str(value))
        grade=None if pending or not maximum else float((20*total/maximum).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
        rows.append({**student,'obtenido':float(total),'maximo':float(maximum),'pendientes':pending,'nota':grade})
    return rows


def toggle_practice(path, practice):
    with connection(path) as conn:
        row=conn.execute('SELECT bloque_id,activa FROM Puntos_Practicas WHERE id=?',(practice,)).fetchone()
        if not row:raise ValueError('La práctica no existe.')
        _editable(conn,row[0])
        conn.execute('UPDATE Puntos_Practicas SET activa=? WHERE id=?',(int(not row[1]),practice))
        _audit(conn,row[0],'Cambiar inclusión de práctica',{'practica':practice,'activa':not bool(row[1])})


def consolidate(path, block):
    """Create/update exactly one exam session. No course weights are changed."""
    import db
    with connection(path) as conn:
        b=_editable(conn,block)
        data=details(path,block);rows=summary(path,block)
        if not rows:raise ValueError('No hay estudiantes activos en el salón del bloque.')
        if not any(e['activa'] for e in data['exercises']):raise ValueError('Agregue al menos una práctica activa.')
        pending=[f"{r['Apellidos']}, {r['Nombres']} ({r['pendientes']})" for r in rows if r['pendientes']]
        if pending:raise ValueError('Hay ejercicios sin calificar. Complete los puntos o registre 0 si corresponde:\n'+'\n'.join(pending[:15]))
        if not data['capacities']:raise ValueError('El bloque no tiene capacidades válidas.')
        weight=1.0
        if b['sesion_id']:
            previous=conn.execute('SELECT peso_clase FROM Sesiones_Clase WHERE id=?',(b['sesion_id'],)).fetchone()
            if previous:weight=previous[0]
        sid=db.crear_o_actualizar_sesion_clase(b['sesion_id'],b['curso_id'],b['competencia_id'],b['grado'],b['seccion'],
            'Prácticas acumuladas · '+b['tema'],'Nota sobre 20 obtenida sumando los puntos de las prácticas del tema.',
            weight,[(c,'Calificación global de prácticas acumuladas: '+b['tema']) for c in data['capacities']],
            categoria='Exámenes',db_path=path)
        db.guardar_calificaciones_y_asistencia_sesion(sid,[{
            'estudiante_id':r['ID'],'preservar_asistencia':True,
            'notas_por_capacidad':{c:r['nota'] for c in data['capacities']}} for r in rows],db_path=path)
        conn.execute("UPDATE Puntos_Bloques SET estado='consolidado',sesion_id=? WHERE id=?",(sid,block))
        _audit(conn,block,'Consolidar examen',{'sesion':sid,'notas':[{k:r[k] for k in ('ID','obtenido','maximo','nota')} for r in rows]})
        return sid


def reopen(path, block):
    with connection(path) as conn:
        # Reuse the period guard without changing data when validation fails.
        row=conn.execute('SELECT estado FROM Puntos_Bloques WHERE id=?',(block,)).fetchone()
        if not row:raise ValueError('El bloque no existe.')
        conn.execute("UPDATE Puntos_Bloques SET estado='abierto' WHERE id=?",(block,))
        _editable(conn,block)
        _audit(conn,block,'Reabrir bloque',{'nota_publicada':'se conserva hasta volver a consolidar'})
