"""School periods and teaching units, with independent, portable databases."""
from pathlib import Path
from contextlib import closing
import sqlite3
from db_safety import connection

SCHEMES = {'Bimestres': 4, 'Trimestres': 3}


def migrate(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS Calendario_Escolar(id INTEGER PRIMARY KEY CHECK(id=1), tipo TEXT NOT NULL)')
    conn.execute('''CREATE TABLE IF NOT EXISTS Unidades_Didacticas(
        id INTEGER PRIMARY KEY, curso_id INTEGER NOT NULL REFERENCES Cursos(id),
        grado TEXT NOT NULL, seccion TEXT NOT NULL, nombre TEXT NOT NULL,
        proposito TEXT NOT NULL DEFAULT '', inicio TEXT NOT NULL DEFAULT '', fin TEXT NOT NULL DEFAULT '',
        UNIQUE(curso_id,grado,seccion,nombre))''')
    columns={r[1] for r in conn.execute('PRAGMA table_info(Sesiones_Clase)')}
    if 'unidad_id' not in columns:
        conn.execute('ALTER TABLE Sesiones_Clase ADD COLUMN unidad_id INTEGER REFERENCES Unidades_Didacticas(id)')


def info(path):
    """Read metadata without migrating or modifying an old document."""
    with closing(sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro',uri=True)) as conn:
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        row=conn.execute('SELECT anio,periodo FROM Periodo_Info WHERE id=1').fetchone() if 'Periodo_Info' in tables else None
        scheme=conn.execute('SELECT tipo FROM Calendario_Escolar WHERE id=1').fetchone() if 'Calendario_Escolar' in tables else None
        closed=conn.execute('SELECT cerrado FROM Estado_Periodo WHERE id=1').fetchone() if 'Estado_Periodo' in tables else None
    kind=scheme[0] if scheme else 'Bimestres'
    label=f'{row[0]} · {row[1]}.º {"bimestre" if kind=="Bimestres" else "trimestre"}' if row else 'Registro sin periodo asignado'
    return dict(year=row[0] if row else None,number=row[1] if row else None,scheme=kind,closed=bool(closed and closed[0]),label=label)


def identify(path,year,number,scheme='Bimestres'):
    year,number=int(year),int(number)
    if scheme not in SCHEMES or not 2000<=year<=2100 or not 1<=number<=SCHEMES[scheme]:
        raise ValueError('Revise el año, el tipo de periodo y su número.')
    with connection(path) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS Periodo_Info(id INTEGER PRIMARY KEY CHECK(id=1), anio INTEGER, periodo INTEGER)')
        conn.execute('CREATE TABLE IF NOT EXISTS Calendario_Escolar(id INTEGER PRIMARY KEY CHECK(id=1), tipo TEXT NOT NULL)')
        conn.execute('INSERT OR REPLACE INTO Periodo_Info VALUES(1,?,?)',(year,number))
        conn.execute('INSERT OR REPLACE INTO Calendario_Escolar VALUES(1,?)',(scheme,))


def catalog(root,current=None):
    paths=list(Path(root).glob('*.db'))
    if current and Path(current) not in paths:paths.append(Path(current))
    result=[]
    for path in paths:
        try:result.append(dict(path=path,**info(path)))
        except (sqlite3.Error,ValueError,OSError):continue
    return sorted(result,key=lambda p:(p['year'] or 0,p['scheme'],p['number'] or 0,p['path'].stem))


def units(path,course,grade,section):
    with connection(path) as conn:
        conn.row_factory=sqlite3.Row
        return [dict(r) for r in conn.execute('''SELECT * FROM Unidades_Didacticas
            WHERE curso_id=? AND grado=? AND seccion=? ORDER BY inicio,id''',(course,grade,section))]


def save_unit(path,course,grade,section,name,purpose='',start='',end='',identity=None):
    from datetime import date
    name=str(name).strip()
    if not name or not grade or not section or grade=='Todos' or section=='Todas':
        raise ValueError('Seleccione curso, grado y sección, y escriba el nombre de la unidad.')
    for value in (start,end):
        if value:date.fromisoformat(value)
    if start and end and start>end:raise ValueError('La fecha final debe ser posterior al inicio.')
    with connection(path) as conn:
        if identity is None:
            return conn.execute('INSERT INTO Unidades_Didacticas(curso_id,grado,seccion,nombre,proposito,inicio,fin) VALUES(?,?,?,?,?,?,?)',
                (course,grade,section,name,purpose,start,end)).lastrowid
        current=conn.execute('SELECT curso_id,grado,seccion FROM Unidades_Didacticas WHERE id=?',(identity,)).fetchone()
        if not current or tuple(current)!=(course,grade,section):raise ValueError('La unidad no pertenece a este salón.')
        conn.execute('UPDATE Unidades_Didacticas SET nombre=?,proposito=?,inicio=?,fin=? WHERE id=?',(name,purpose,start,end,identity))
        return identity


def assign_unit(conn,session,unit):
    if unit is not None:
        row=conn.execute('''SELECT 1 FROM Sesiones_Clase s JOIN Unidades_Didacticas u
            ON u.curso_id=s.curso_id AND u.grado=s.grado AND u.seccion=s.seccion
            WHERE s.id=? AND u.id=?''',(session,unit)).fetchone()
        if not row:raise ValueError('La unidad no pertenece al curso, grado y sección de la actividad.')
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
