"""Optional achievement thresholds; numeric grades and weights stay unchanged."""
from contextlib import closing
from functools import lru_cache
from pathlib import Path
import sqlite3

DEFAULT=(10.5,13.5,17.5)


@lru_cache(maxsize=32)
def _read(path,modified,size):
    try:
        with closing(sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro',uri=True)) as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='Escala_Logro'").fetchone():return DEFAULT
            row=conn.execute('SELECT b,a,ad FROM Escala_Logro WHERE nivel=(SELECT nivel_educativo FROM Docente_Config WHERE id=1)').fetchone()
            return tuple(row) if row else DEFAULT
    except sqlite3.DatabaseError:return DEFAULT


def thresholds(path):
    path=Path(path)
    if not path.exists():return DEFAULT
    stat=path.stat();return _read(str(path),stat.st_mtime_ns,stat.st_size)


def save_thresholds(path,values):
    import json
    from db_safety import connection,valid_number
    values=tuple(valid_number(v,0,20,'Límite de logro') for v in values)
    if not values[0]<values[1]<values[2]:raise ValueError('Los límites B, A y AD deben estar en orden creciente.')
    previous=thresholds(path)
    with connection(path) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS Escala_Logro(nivel TEXT PRIMARY KEY,b REAL,a REAL,ad REAL)')
        conn.execute('CREATE TABLE IF NOT EXISTS Historial_Reglas(id INTEGER PRIMARY KEY,fecha TEXT DEFAULT CURRENT_TIMESTAMP,nivel TEXT,usuario TEXT,anterior TEXT,nueva TEXT)')
        level,user=conn.execute('SELECT nivel_educativo,usuario FROM Docente_Config WHERE id=1').fetchone()
        conn.execute('INSERT OR REPLACE INTO Escala_Logro VALUES(?,?,?,?)',(level,*values))
        conn.execute('INSERT INTO Historial_Reglas(nivel,usuario,anterior,nueva) VALUES(?,?,?,?)',(level,user,json.dumps(previous),json.dumps(values)))
    _read.cache_clear()


def range_caption(level,limits=DEFAULT,maximum=20):
    levels=('C','B','A','AD');index=levels.index(level)
    edges=(0,*limits,20);low=edges[index]*float(maximum)/20;high=edges[index+1]*float(maximum)/20
    return f'{level} · {low:g} a {"" if level=="AD" else "< "}{high:g}'
