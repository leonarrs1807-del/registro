"""Writable user storage, verified backups and independent school periods."""
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from datetime import datetime


def data_dir():
    override = os.environ.get('REGISTRO_DATA_DIR')
    if override:
        root = Path(override)
    elif sys.platform == 'win32':
        root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'RegistroDocente'
    elif sys.platform == 'darwin':
        root = Path.home() / 'Library/Application Support/RegistroDocente'
    else:
        root = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'registro-docente'
    root.mkdir(parents=True, exist_ok=True)
    return root


def resource_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


def database_path():
    if os.environ.get('REGISTRO_DB_PATH'):
        return Path(os.environ['REGISTRO_DB_PATH']).resolve()
    name = 'registro_evaluacion.db'
    settings = data_dir() / 'settings.json'
    if settings.exists():
        name = json.loads(settings.read_text(encoding='utf-8')).get('active_database', name)
        if Path(name).name != name or not name.endswith('.db'):
            raise ValueError('Nombre de base de datos no válido.')
    return data_dir() / name


def copy_database(source, target):
    if Path(source).resolve() == Path(target).resolve():
        raise ValueError('El origen y destino deben ser bases de datos diferentes.')
    with sqlite3.connect(f'{Path(source).resolve().as_uri()}?mode=ro', uri=True) as src:
        with sqlite3.connect(target) as dst:
            src.backup(dst)


def validate_database(path):
    with sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro', uri=True) as conn:
        if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('La base de datos está dañada.')
        if conn.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('La base de datos contiene relaciones inválidas.')
        required = {'Estudiantes', 'Cursos', 'Competencias', 'Capacidades', 'Sesiones_Clase', 'Docente_Config'}
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required <= tables:
            raise ValueError('No es una base de datos de Registro Docente.')


def backup_database(path, reason='manual'):
    root = Path(path).parent / 'backups'
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    target = root / f'{Path(path).stem}-{stamp}-{reason}.db'
    copy_database(path, target)
    try:
        validate_database(target)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target


def prepare_storage(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Adopt the user's old database once, never overwrite a newer installation.
    legacy_root = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else resource_dir()
    legacy = legacy_root / 'registro_evaluacion.db'
    if not path.exists() and legacy.exists() and legacy.resolve() != path.resolve():
        copy_database(legacy, path)
    if path.exists():
        backup_database(path, 'inicio')


def restore_database(backup, target):
    validate_database(backup)
    saved = backup_database(target, 'antes-restaurar')
    # SQLite backup API also works when the source uses WAL; do not copy raw DB bytes.
    copy_database(backup, target)
    return saved


def configure_logging():
    handler = RotatingFileHandler(data_dir() / 'registro.log', maxBytes=1_000_000, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logging.getLogger('registro').addHandler(handler)
    logging.getLogger('registro').setLevel(logging.INFO)


def create_period(source, year, period):
    year, period = int(year), int(period)
    if not 2000 <= year <= 2100 or not 1 <= period <= 4:
        raise ValueError('Indique un año entre 2000 y 2100 y un periodo entre 1 y 4.')
    target = data_dir() / f'escolar-{year}-periodo-{period}.db'
    if target.exists():
        raise ValueError('Ese periodo ya existe. Ábralo desde el selector.')
    with tempfile.TemporaryDirectory(dir=data_dir()) as tmp:
        staged = Path(tmp) / 'nuevo.db'
        copy_database(source, staged)
        with sqlite3.connect(staged) as conn:
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('DELETE FROM Sesiones_Clase')
            conn.execute('DELETE FROM Notas_Manuales_Capacidad')
            conn.execute('DELETE FROM Historial_Notas')
            conn.execute('CREATE TABLE IF NOT EXISTS Periodo_Info (id INTEGER PRIMARY KEY CHECK(id=1), anio INTEGER, periodo INTEGER)')
            conn.execute('INSERT OR REPLACE INTO Periodo_Info VALUES (1, ?, ?)', (year, period))
        validate_database(staged)
        # Exclusive creation prevents overwriting an existing period on a repeated click.
        with target.open('xb') as out:
            out.write(staged.read_bytes())
    return target


def activate_period(path):
    path = Path(path).resolve()
    if path.parent != data_dir().resolve():
        raise ValueError('El periodo debe pertenecer a la carpeta de datos de la aplicación.')
    validate_database(path)
    settings = data_dir() / 'settings.json'
    temp = settings.with_suffix('.tmp')
    temp.write_text(json.dumps({'active_database': path.name}), encoding='utf-8')
    temp.replace(settings)
