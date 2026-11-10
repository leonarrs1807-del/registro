"""Independent school documents; stable identities travel with .registro files."""
from contextlib import closing
from pathlib import Path
import hashlib,sqlite3,time,uuid
from db_safety import connection


def legacy_id(name):
    return 'ie-'+hashlib.sha256(str(name).strip().casefold().encode()).hexdigest()[:20]


def migrate(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS Colegio_Info(id INTEGER PRIMARY KEY CHECK(id=1),identificador TEXT NOT NULL)')
    name=conn.execute('SELECT institucion FROM Docente_Config WHERE id=1').fetchone()
    if name:conn.execute('INSERT OR IGNORE INTO Colegio_Info VALUES(1,?)',(legacy_id(name[0]),))


def info(path):
    with closing(sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro',uri=True)) as conn:
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'Cursos','Estudiantes','Docente_Config'}<=tables:raise ValueError('No es un registro escolar.')
        name=conn.execute('SELECT institucion FROM Docente_Config WHERE id=1').fetchone()[0]
        row=conn.execute('SELECT identificador FROM Colegio_Info WHERE id=1').fetchone() if 'Colegio_Info' in tables else None
    return dict(school_id=row[0] if row else legacy_id(name),school_name=name or 'Mi colegio')


def catalog(root,current=None):
    import periodos
    groups={}
    for row in periodos.catalog(root,current):
        group=groups.setdefault(row['school_id'],dict(id=row['school_id'],name=row['school_name'],records=[]))
        group['records'].append(row)
        if current and row['path'].resolve()==Path(current).resolve():group['name']=row['school_name']
    return sorted(groups.values(),key=lambda r:r['name'].casefold())


def labels(rows):
    result={}
    for row in rows:
        name=row['name'];label=name;index=2
        while label in result:label=f'{name} ({index})';index+=1
        result[label]=row
    return result


def trash(root):
    result=[]
    import periodos
    for path in (Path(root)/'papelera').glob('*/*.db'):
        try:result.append(dict(path=path,date=path.stat().st_mtime,**periodos.info(path)))
        except (OSError,ValueError,sqlite3.Error):continue
    return sorted(result,key=lambda r:r['date'],reverse=True)


def blank_copy(source,root,name,identity=None):
    """Keep the teacher/curriculum; never copy pupils, grades or the other crest."""
    import app_storage
    name=str(name).strip()
    if not name or len(name)>300:raise ValueError('Escriba un nombre de colegio de hasta 300 caracteres.')
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    target=root/f'colegio-{uuid.uuid4().hex}.db'
    try:
        app_storage.copy_database(source,target)
        with closing(sqlite3.connect(target)) as conn,conn:
            conn.execute('PRAGMA foreign_keys=ON')
            tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ['Puntos_Bloques','Sesiones_Clase','Notas_Manuales_Capacidad','Estudiantes','Unidades_Didacticas']:
                if table in tables:conn.execute(f'DELETE FROM {table}')
            for table in tables:
                if table.startswith('Historial_') or table in ('Periodo_Info','Calendario_Escolar','Cierres_Periodo','Colegio_Datos','Colegio_Insignia','Biblioteca_Instrumentos','Puntos_Historial'):
                    conn.execute('DELETE FROM "'+table.replace('"','""')+'"')
            if 'Estado_Periodo' in tables:conn.execute('UPDATE Estado_Periodo SET cerrado=0')
            conn.execute('CREATE TABLE IF NOT EXISTS Colegio_Info(id INTEGER PRIMARY KEY CHECK(id=1),identificador TEXT NOT NULL)')
            conn.execute('INSERT OR REPLACE INTO Colegio_Info VALUES(1,?)',(identity or uuid.uuid4().hex,))
            conn.execute('UPDATE Docente_Config SET institucion=? WHERE id=1',(name,))
        with closing(sqlite3.connect(target)) as conn:conn.execute('VACUUM')
        app_storage.validate_database(target)
    except Exception:
        target.unlink(missing_ok=True);raise
    return target


def rename(root,identity,name,current=None):
    name=str(name).strip()
    if not name or len(name)>300:raise ValueError('Escriba un nombre de colegio de hasta 300 caracteres.')
    import periodos
    for row in periodos.catalog(root,current):
        if row['school_id']!=identity:continue
        with connection(row['path']) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS Colegio_Info(id INTEGER PRIMARY KEY CHECK(id=1),identificador TEXT NOT NULL)')
            conn.execute('INSERT OR REPLACE INTO Colegio_Info VALUES(1,?)',(identity,))
            conn.execute('UPDATE Docente_Config SET institucion=? WHERE id=1',(name,))
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name='Colegio_Datos'").fetchone():
                conn.execute("UPDATE Colegio_Datos SET valor=? WHERE campo='nombre'",(name,))


def sync_identity(source,root):
    """School branding is shared by its periods, never by another school."""
    import institucion,reportes,periodos
    school=info(source);values=institucion.profile(source);logo=reportes.logo_bytes(source)
    shared={k:v for k,v in values.items() if k!='docente'}
    for row in periodos.catalog(root,source):
        if row['school_id']!=school['school_id'] or row['path'].resolve()==Path(source).resolve():continue
        with connection(row['path']) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS Colegio_Info(id INTEGER PRIMARY KEY CHECK(id=1),identificador TEXT NOT NULL)')
            conn.execute('INSERT OR REPLACE INTO Colegio_Info VALUES(1,?)',(school['school_id'],))
            conn.execute('CREATE TABLE IF NOT EXISTS Colegio_Datos(campo TEXT PRIMARY KEY,valor TEXT NOT NULL)')
            conn.executemany('INSERT OR REPLACE INTO Colegio_Datos VALUES(?,?)',shared.items())
            conn.execute('UPDATE Docente_Config SET institucion=? WHERE id=1',(values['nombre'],))
            conn.execute('CREATE TABLE IF NOT EXISTS Colegio_Insignia(id INTEGER PRIMARY KEY CHECK(id=1),imagen BLOB NOT NULL)')
            if logo:conn.execute('INSERT OR REPLACE INTO Colegio_Insignia VALUES(1,?)',(logo,))
            else:conn.execute('DELETE FROM Colegio_Insignia')


def archive(path):
    """A removable item remains recoverable as a complete dated document."""
    import app_storage
    path=Path(path);app_storage.validate_database(path)
    folder=path.parent/'papelera'/str(time.time_ns());folder.mkdir(parents=True)
    target=folder/path.name
    app_storage.copy_database(path,target);app_storage.validate_database(target)
    path.unlink()
    path.with_suffix('.borrador.json').unlink(missing_ok=True)
    return target


def remove_period(path,root):
    import periodos
    path=Path(path);school=info(path)
    others=[r['path'] for r in periodos.catalog(root,path) if r['school_id']==school['school_id'] and r['path'].resolve()!=path.resolve()]
    replacement=others[-1] if others else blank_copy(path,root,school['school_name'],school['school_id'])
    saved=archive(path)
    return replacement,saved


def archive_school(records,current=None):
    """Validate every recovery copy before removing any school document."""
    import app_storage
    paths=[Path(r['path']) for r in records]
    if not paths:return []
    folder=paths[0].parent/'papelera'/str(time.time_ns());folder.mkdir(parents=True)
    copies=[]
    for source in paths:
        app_storage.validate_database(source)
        target=folder/source.name
        app_storage.copy_database(source,target);app_storage.validate_database(target);copies.append(target)
    paths.sort(key=lambda p:bool(current and p.resolve()==Path(current).resolve()))
    for source in paths:
        source.unlink();source.with_suffix('.borrador.json').unlink(missing_ok=True)
    return copies
