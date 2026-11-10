"""School periods and teaching units, with independent, portable databases."""
from pathlib import Path
from contextlib import closing
import sqlite3
from db_safety import connection,atomic,backed_up,schema_work

SCHEMES = {'Bimestres': 4, 'Trimestres': 3}


def migrate(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS Calendario_Escolar(id INTEGER PRIMARY KEY CHECK(id=1), tipo TEXT NOT NULL)")
    cols={r[1] for r in conn.execute('PRAGMA table_info(Calendario_Escolar)')}
    for name in ('nombre','inicio','fin'):
        if name not in cols:conn.execute(f"ALTER TABLE Calendario_Escolar ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
    table="""CREATE TABLE {name}(id INTEGER PRIMARY KEY,curso_id INTEGER REFERENCES Cursos(id) ON DELETE SET NULL,
        grado TEXT NOT NULL DEFAULT '*',seccion TEXT NOT NULL DEFAULT '*',nombre TEXT NOT NULL,
        proposito TEXT NOT NULL DEFAULT '',inicio TEXT NOT NULL DEFAULT '',fin TEXT NOT NULL DEFAULT '',
        general INTEGER NOT NULL DEFAULT 1,orden INTEGER NOT NULL DEFAULT 0)"""
    old={r[1] for r in conn.execute('PRAGMA table_info(Unidades_Didacticas)')}
    if not old:conn.execute(table.format(name='Unidades_Didacticas'))
    columns={r[1] for r in conn.execute('PRAGMA table_info(Sesiones_Clase)')}
    if 'unidad_id' not in columns:conn.execute('ALTER TABLE Sesiones_Clase ADD COLUMN unidad_id INTEGER REFERENCES Unidades_Didacticas(id)')
    if old and 'general' not in old:
        links=conn.execute('SELECT id,unidad_id FROM Sesiones_Clase WHERE unidad_id IS NOT NULL').fetchall()
        conn.execute('UPDATE Sesiones_Clase SET unidad_id=NULL WHERE unidad_id IS NOT NULL')
        conn.execute(table.format(name='Unidades_Nuevas'))
        used=set()
        for row in conn.execute('SELECT id,nombre,proposito,inicio,fin,grado,seccion FROM Unidades_Didacticas ORDER BY id').fetchall():
            identity,name,purpose,start,end,grade,section=row
            candidate=name
            if candidate.strip().casefold() in used:candidate=f'{name} ({grade} {section} · {identity})'
            used.add(candidate.strip().casefold())
            conn.execute('INSERT INTO Unidades_Nuevas(id,nombre,proposito,inicio,fin,orden) VALUES(?,?,?,?,?,?)',(identity,candidate,purpose,start,end,identity))
        conn.execute('DROP TABLE Unidades_Didacticas')
        conn.execute('ALTER TABLE Unidades_Nuevas RENAME TO Unidades_Didacticas')
        conn.executemany('UPDATE Sesiones_Clase SET unidad_id=? WHERE id=?',[(unit,session) for session,unit in links])
    elif old and 'orden' not in old:
        conn.execute('ALTER TABLE Unidades_Didacticas ADD COLUMN orden INTEGER NOT NULL DEFAULT 0')
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS unidad_general_nombre ON Unidades_Didacticas(lower(trim(nombre))) WHERE general=1')
    from colegios import migrate as migrate_schools
    migrate_schools(conn)


def info(path):
    """Read metadata without migrating or modifying an old document."""
    with closing(sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro',uri=True)) as conn:
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        row=conn.execute('SELECT anio,periodo FROM Periodo_Info WHERE id=1').fetchone() if 'Periodo_Info' in tables else None
        scheme=conn.execute('SELECT tipo FROM Calendario_Escolar WHERE id=1').fetchone() if 'Calendario_Escolar' in tables else None
        cols={r[1] for r in conn.execute('PRAGMA table_info(Calendario_Escolar)')}
        details=conn.execute('SELECT nombre,inicio,fin FROM Calendario_Escolar WHERE id=1').fetchone() if {'nombre','inicio','fin'}<=cols else None
        closed=conn.execute('SELECT cerrado FROM Estado_Periodo WHERE id=1').fetchone() if 'Estado_Periodo' in tables else None
    kind=scheme[0] if scheme else 'Bimestres'
    label=f'{row[0]} · {row[1]}.º {"bimestre" if kind=="Bimestres" else "trimestre"}' if row else 'Registro sin periodo asignado'
    from colegios import info as school_info
    return dict(year=row[0] if row else None,number=row[1] if row else None,scheme=kind,closed=bool(closed and closed[0]),label=label+((' · '+details[0]) if details and details[0] else ''),name=details[0] if details else '',start=details[1] if details else '',end=details[2] if details else '',**school_info(path))


def identify(path,year,number,scheme='Bimestres',name='',start='',end='',root=None):
    year,number=int(year),int(number)
    if scheme not in SCHEMES or not 2000<=year<=2100 or not 1<=number<=SCHEMES[scheme]:
        raise ValueError('Revise el año, el tipo de periodo y su número.')
    from datetime import date
    for value in (start,end):
        if value:date.fromisoformat(value)
    if start and end and start>end:raise ValueError('Revise las fechas del periodo.')
    current=info(path)
    if current['closed']:raise ValueError('Reabra el periodo antes de editarlo.')
    if root and any(r['path'].resolve()!=Path(path).resolve() and r['school_id']==current['school_id'] and (r['year'],r['number'],r['scheme'])==(year,number,scheme) for r in catalog(root,path)):
        raise ValueError('Ese periodo ya existe en este colegio.')
    with connection(path) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS Periodo_Info(id INTEGER PRIMARY KEY CHECK(id=1), anio INTEGER, periodo INTEGER)')
        conn.execute('CREATE TABLE IF NOT EXISTS Calendario_Escolar(id INTEGER PRIMARY KEY CHECK(id=1), tipo TEXT NOT NULL)')
        conn.execute('INSERT OR REPLACE INTO Periodo_Info VALUES(1,?,?)',(year,number))
        cols={r[1] for r in conn.execute('PRAGMA table_info(Calendario_Escolar)')}
        for column in ('nombre','inicio','fin'):
            if column not in cols:conn.execute(f"ALTER TABLE Calendario_Escolar ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
        conn.execute('INSERT OR REPLACE INTO Calendario_Escolar(id,tipo,nombre,inicio,fin) VALUES(1,?,?,?,?)',(scheme,name.strip(),start,end))


def catalog(root,current=None):
    paths=list(Path(root).glob('*.db'))
    if current and Path(current) not in paths:paths.append(Path(current))
    result=[]
    for path in paths:
        try:result.append(dict(path=path,**info(path)))
        except (sqlite3.Error,ValueError,OSError):continue
    return sorted(result,key=lambda p:(p['year'] or 0,p['scheme'],p['number'] or 0,p['path'].stem))


def units(path,course=None,grade=None,section=None):
    # A list refresh can inspect inactive/archived periods from older versions.
    # It must not assume that opening the active document upgraded those files.
    with closing(sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro',uri=True)) as conn:
        conn.row_factory=sqlite3.Row
        columns={r[1] for r in conn.execute('PRAGMA table_info(Unidades_Didacticas)')}
        if not columns:return []
        if {'general','orden'}<=columns:
            return [dict(r) for r in conn.execute("SELECT * FROM Unidades_Didacticas WHERE general=1 OR (curso_id=? AND grado=? AND seccion=?) ORDER BY orden,id",(course,grade,section))]
        rows=[dict(r) for r in conn.execute('SELECT * FROM Unidades_Didacticas ORDER BY id')]
        used=set()
        for row in rows:
            name=row['nombre']
            if name.strip().casefold() in used:name=f"{name} ({row.get('grado','')} {row.get('seccion','')} · {row['id']})"
            used.add(name.strip().casefold())
            row.update(nombre=name,general=1,orden=row['id'])
        return rows


def ensure_units_ready(path):
    with closing(sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro',uri=True)) as conn:
        columns={r[1] for r in conn.execute('PRAGMA table_info(Unidades_Didacticas)')}
        session_columns={r[1] for r in conn.execute('PRAGMA table_info(Sesiones_Clase)')}
    if not {'general','orden'}<=columns or 'unidad_id' not in session_columns:_upgrade_units(path)


@schema_work
@backed_up
@atomic
def _upgrade_units(db_path):
    # Only an explicit edit reaches this upgrade. Migration is separate from
    # the edit so closed-period guards remain in force for the actual changes.
    with connection(db_path) as conn:migrate(conn)


def save_unit(path,course,grade,section,name,purpose='',start='',end='',identity=None,general=True):
    from datetime import date
    name=str(name).strip()
    if not name:raise ValueError('Escriba el nombre de la unidad.')
    for value in (start,end):
        if value:date.fromisoformat(value)
    if start and end and start>end:raise ValueError('La fecha final debe ser posterior al inicio.')
    ensure_units_ready(path)
    with connection(path) as conn:
        duplicates=conn.execute('SELECT id,nombre FROM Unidades_Didacticas WHERE general=1').fetchall()
        if general and any(i!=identity and n.strip().casefold()==name.casefold() for i,n in duplicates):raise ValueError('Ya existe una unidad con ese nombre.')
        if identity is None:
            order=conn.execute('SELECT COALESCE(MAX(orden),0)+1 FROM Unidades_Didacticas').fetchone()[0]
            return conn.execute('INSERT INTO Unidades_Didacticas(curso_id,grado,seccion,nombre,proposito,inicio,fin,general,orden) VALUES(?,?,?,?,?,?,?,?,?)',
                (None if general else course,'*' if general else grade,'*' if general else section,name,purpose,start,end,int(general),order)).lastrowid
        if not conn.execute('SELECT 1 FROM Unidades_Didacticas WHERE id=?',(identity,)).fetchone():raise ValueError('La unidad ya no existe.')
        conn.execute('UPDATE Unidades_Didacticas SET nombre=?,proposito=?,inicio=?,fin=? WHERE id=?',(name,purpose,start,end,identity))
        return identity


def delete_unit(path,identity):
    import app_storage
    ensure_units_ready(path)
    saved=app_storage.backup_database(path,'eliminar-unidad')
    with connection(path) as conn:
        conn.execute('UPDATE Sesiones_Clase SET unidad_id=NULL WHERE unidad_id=?',(identity,))
        conn.execute('DELETE FROM Unidades_Didacticas WHERE id=?',(identity,))
    return saved


def move_unit(path,identity,delta):
    ensure_units_ready(path)
    with connection(path) as conn:
        rows=conn.execute('SELECT id FROM Unidades_Didacticas ORDER BY orden,id').fetchall();ids=[r[0] for r in rows]
        if identity not in ids:return
        old=ids.index(identity);new=max(0,min(old+delta,len(ids)-1));ids.insert(new,ids.pop(old))
        conn.executemany('UPDATE Unidades_Didacticas SET orden=? WHERE id=?',[(n,i) for n,i in enumerate(ids,1)])


def assign_unit(conn,session,unit):
    if unit is not None:
        row=conn.execute("""SELECT 1 FROM Sesiones_Clase s JOIN Unidades_Didacticas u
            ON (u.general=1 OR (u.curso_id=s.curso_id AND u.grado=s.grado AND u.seccion=s.seccion))
            WHERE s.id=? AND u.id=?""",(session,unit)).fetchone()
        if not row:raise ValueError('La unidad no pertenece a este periodo o salón.')
    conn.execute('UPDATE Sesiones_Clase SET unidad_id=? WHERE id=?',(unit,session))


def snapshots(path):
    result=[]
    for file in (Path(path).parent/'backups').glob('*.db'):
        if not file.name.startswith(Path(path).stem+'-'):continue
        result.append(dict(path=file,date=file.stat().st_mtime,size=file.stat().st_size))
    return sorted(result,key=lambda r:r['date'],reverse=True)


def open_snapshot(source,root):
    import time
    import app_storage
    source=Path(source)
    app_storage.validate_database(source)
    target=Path(root)/f'recuperado-{time.time_ns()}.db'
    app_storage.copy_database(source,target)
    app_storage.validate_database(target)
    return target
