"""Transactions, validation and schema extensions for legacy databases."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import inspect
import math
from pathlib import Path
import sqlite3

_connections = ContextVar('registro_connections', default={})
_license_service = None
_license_required = False


def set_license_policy(service=None, required=False):
    """Production entry point installs this policy after migration, before editing."""
    global _license_service, _license_required
    _license_service, _license_required = service, required


def _license_guards(conn):
    if not _license_required:
        return
    from licencias import course_key
    allowed = _license_service.status()['courses'] if _license_service else set()
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    courses = {r[0]: (r[1], r[2]) for r in conn.execute('SELECT id,nombre,nivel FROM Cursos')}
    lookups = {
        'competencia': 'SELECT id,curso_id FROM Competencias',
        'capacidad': 'SELECT a.id,c.curso_id FROM Capacidades a JOIN Competencias c ON c.id=a.competencia_id',
        'sesion': 'SELECT id,curso_id FROM Sesiones_Clase',
        'bloque': 'SELECT id,curso_id FROM Puntos_Bloques',
        'practica': 'SELECT p.id,b.curso_id FROM Puntos_Practicas p JOIN Puntos_Bloques b ON b.id=p.bloque_id',
        'ejercicio': 'SELECT e.id,b.curso_id FROM Puntos_Ejercicios e JOIN Puntos_Practicas p ON p.id=e.practica_id JOIN Puntos_Bloques b ON b.id=p.bloque_id',
    }
    cached = {}
    for kind, query in lookups.items():
        if kind in ('bloque', 'practica', 'ejercicio') and 'Puntos_Bloques' not in tables:
            continue
        cached[kind] = dict(conn.execute(query))

    def area(name, level):
        try:return int('*' in allowed or course_key(name, level) in allowed)
        except (ValueError, TypeError):return 0

    def scope(kind, identifier):
        if kind == 'nivel':
            return int('*' in allowed or any(c.startswith(str(identifier).casefold()+':') for c in allowed))
        course = identifier
        if kind != 'curso':
            # Live lookups include newly inserted rows. The snapshot also resolves
            # parent identities while foreign-key cascades remove their children.
            query = lookups[kind]
            row = conn.execute('SELECT curso_id FROM ('+query+') WHERE id=?',(identifier,)).fetchone()
            course = row[0] if row else cached.get(kind, {}).get(identifier)
        row = conn.execute('SELECT nombre,nivel FROM Cursos WHERE id=?', (course,)).fetchone()
        row = tuple(row) if row else courses.get(course)
        return area(*row) if row else 0

    conn.create_function('registro_area', 2, area)
    conn.create_function('registro_permiso', 2, scope)
    guards = {
        'Cursos': "registro_area({r}.nombre,{r}.nivel)",
        'Competencias': "registro_permiso('curso',{r}.curso_id)",
        'Capacidades': "registro_permiso('competencia',{r}.competencia_id)",
        'Estudiantes': "registro_permiso('nivel',{r}.nivel)",
        'Sesiones_Clase': "registro_permiso('curso',{r}.curso_id)",
        'Sesion_Capacidades': "registro_permiso('sesion',{r}.sesion_id)",
        'Instrumento_Indicadores': "registro_permiso('sesion',{r}.sesion_id)",
        'Instrumento_Respuestas': "registro_permiso('sesion',{r}.sesion_id)",
        'Asistencia_Y_Comentarios_Clase': "registro_permiso('sesion',{r}.sesion_id)",
        'Notas_Sesion_Capacidad': "registro_permiso('sesion',{r}.sesion_id)",
        'Notas_Manuales_Capacidad': "registro_permiso('capacidad',{r}.capacidad_id)",
        'Pesos_Rubros_Curso': "registro_permiso('curso',{r}.curso_id)",
        'Puntos_Bloques': "registro_permiso('curso',{r}.curso_id)",
        'Puntos_Capacidades': "registro_permiso('bloque',{r}.bloque_id)",
        'Puntos_Practicas': "registro_permiso('bloque',{r}.bloque_id)",
        'Puntos_Ejercicios': "registro_permiso('practica',{r}.practica_id)",
        'Puntos_Registro': "registro_permiso('ejercicio',{r}.ejercicio_id)",
    }
    for table, expression in guards.items():
        if table not in tables:
            continue
        for operation, refs in [('INSERT', ['NEW']), ('UPDATE', ['OLD', 'NEW']), ('DELETE', ['OLD'])]:
            condition = ' AND '.join(expression.format(r=ref) for ref in refs)
            conn.execute(f'''CREATE TEMP TRIGGER licencia_{table}_{operation} BEFORE {operation} ON main.{table}
                WHEN NOT ({condition}) BEGIN SELECT RAISE(ABORT,'Licencia: curso o nivel sin habilitar. Puede consultar y exportar sus datos.'); END''')


class _Connection(sqlite3.Connection):
    def commit(self):
        # Existing helpers call commit; the outer unit of work owns the transaction.
        pass


@contextmanager
def connection(path):
    key = str(Path(path).resolve())
    existing = _connections.get().get(key)
    if existing is not None:
        factory = existing.row_factory
        try:
            yield existing
        finally:
            existing.row_factory = factory
        return
    conn = sqlite3.connect(key, timeout=15, factory=_Connection)
    conn.execute('PRAGMA foreign_keys=ON')
    token = _connections.set({**_connections.get(), key: conn})
    try:
        conn.execute('BEGIN')
        _license_guards(conn)
        yield conn
        sqlite3.Connection.commit(conn)
    except BaseException:
        conn.rollback()
        raise
    finally:
        _connections.reset(token)
        conn.close()


def atomic(func):
    signature = inspect.signature(func)
    @wraps(func)
    def wrapped(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        with connection(bound.arguments['db_path']):
            return func(*args, **kwargs)
    return wrapped


def backed_up(func):
    signature = inspect.signature(func)
    @wraps(func)
    def wrapped(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        path = Path(bound.arguments['db_path'])
        if path.exists() and str(path.resolve()) not in _connections.get():
            from app_storage import backup_database
            backup_database(path, 'antes-' + func.__name__, current=func.__name__ != 'inicializar_db')
        return func(*args, **kwargs)
    return wrapped


def valid_number(value, minimum=0, maximum=20, label='Nota'):
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'{label}: ingrese un número válido.') from None
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f'{label}: debe estar entre {minimum} y {maximum}.')
    return number


def migrate(conn):
    from app_security import hash_password
    from evaluacion_datos import migrate as migrate_instruments
    migrate_instruments(conn)
    cols = {r[1] for r in conn.execute('PRAGMA table_info(Docente_Config)')}
    if 'requiere_cambio_clave' not in cols:
        conn.execute('ALTER TABLE Docente_Config ADD COLUMN requiere_cambio_clave INTEGER NOT NULL DEFAULT 0')
    row = conn.execute('SELECT clave FROM Docente_Config WHERE id=1').fetchone()
    if row and not row[0].startswith('pbkdf2_sha256$'):
        conn.execute('UPDATE Docente_Config SET clave=?, requiere_cambio_clave=? WHERE id=1',
                     (hash_password(row[0]), int(len(row[0].strip()) < 8)))
    conn.execute('''CREATE TABLE IF NOT EXISTS Historial_Notas (
        id INTEGER PRIMARY KEY, fecha TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
        tabla TEXT NOT NULL, sesion_id INTEGER, estudiante_id INTEGER NOT NULL,
        capacidad_id INTEGER NOT NULL, anterior REAL, nueva REAL, operacion TEXT NOT NULL,
        usuario TEXT NOT NULL, revertido INTEGER NOT NULL DEFAULT 0)''')
    for table, column, session in [('Notas_Sesion_Capacidad', 'nota', True), ('Notas_Manuales_Capacidad', 'nota_manual', False)]:
        for operation in ('INSERT', 'UPDATE'):
            conn.execute(f'''CREATE TRIGGER IF NOT EXISTS validar_{table}_{operation}
                BEFORE {operation} ON {table}
                WHEN NEW.{column} IS NOT NULL AND (typeof(NEW.{column}) NOT IN ('integer','real') OR NEW.{column} < 0 OR NEW.{column} > 20)
                BEGIN SELECT RAISE(ABORT, 'Nota fuera del intervalo 0-20'); END''')
        for operation in ('INSERT', 'UPDATE', 'DELETE'):
            ref = 'OLD' if operation == 'DELETE' else 'NEW'
            sid = f'{ref}.sesion_id' if session else 'NULL'
            previous = 'NULL' if operation == 'INSERT' else f'OLD.{column}'
            new = 'NULL' if operation == 'DELETE' else f'NEW.{column}'
            when = f'WHEN OLD.{column} IS NOT NEW.{column}' if operation == 'UPDATE' else ''
            conn.execute(f'''CREATE TRIGGER IF NOT EXISTS auditar_{table}_{operation}
                AFTER {operation} ON {table} {when}
                BEGIN INSERT INTO Historial_Notas(tabla,sesion_id,estudiante_id,capacidad_id,anterior,nueva,operacion,usuario)
                VALUES ('{table}', {sid}, {ref}.estudiante_id, {ref}.capacidad_id, {previous}, {new}, '{operation}',
                COALESCE((SELECT usuario FROM Docente_Config WHERE id=1),'docente')); END''')
    for table, condition in [
        ('Sesiones_Clase', "NEW.peso_clase > 0 AND NEW.peso_clase <= 1000000"),
        ('Pesos_Rubros_Curso', "NEW.pct_clases >= 0 AND NEW.pct_examenes >= 0 AND NEW.pct_trabajos >= 0 AND NEW.pct_practicas >= 0 AND abs(NEW.pct_clases + NEW.pct_examenes + NEW.pct_trabajos + NEW.pct_practicas - 100) < 0.000001")]:
        for operation in ('INSERT', 'UPDATE'):
            conn.execute(f'''CREATE TRIGGER IF NOT EXISTS validar_{table}_{operation}
                BEFORE {operation} ON {table} WHEN NOT ({condition})
                BEGIN SELECT RAISE(ABORT, 'Pesos o porcentajes inválidos'); END''')
    conn.execute('PRAGMA user_version=2')


def history(path, limit=500):
    with connection(path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute('''SELECT h.*, COALESCE(e.Apellidos || ', ' || e.Nombres, 'Estudiante eliminado') AS alumno,
            c.nombre AS capacidad FROM Historial_Notas h LEFT JOIN Estudiantes e ON e.ID=h.estudiante_id
            LEFT JOIN Capacidades c ON c.id=h.capacidad_id ORDER BY h.id DESC LIMIT ?''', (limit,))]


def undo_grade(path, event_id):
    with connection(path) as conn:
        conn.row_factory = sqlite3.Row
        event = conn.execute('SELECT * FROM Historial_Notas WHERE id=?', (event_id,)).fetchone()
        if not event or event['revertido']:
            raise ValueError('El cambio no existe o ya fue revertido.')
        table = event['tabla']
        if table not in ('Notas_Sesion_Capacidad', 'Notas_Manuales_Capacidad'):
            raise ValueError('Tipo de cambio no válido.')
        column = 'nota' if table == 'Notas_Sesion_Capacidad' else 'nota_manual'
        where = 'estudiante_id=? AND capacidad_id=?'
        keys = [event['estudiante_id'], event['capacidad_id']]
        if table == 'Notas_Sesion_Capacidad':
            where += ' AND sesion_id=?'
            keys.append(event['sesion_id'])
        # Do not overwrite a later edit, even when its value happens to be equal.
        later = conn.execute('''SELECT 1 FROM Historial_Notas WHERE id>? AND tabla=? AND estudiante_id=?
            AND capacidad_id=? AND sesion_id IS ? LIMIT 1''',
            (event_id, table, event['estudiante_id'], event['capacidad_id'], event['sesion_id'])).fetchone()
        if later:
            raise ValueError('Existe un cambio posterior. Revierta el último cambio o restaure un respaldo.')
        current = conn.execute(f'SELECT {column} FROM {table} WHERE {where}', keys).fetchone()
        if event['operacion'] == 'DELETE':
            raise ValueError('Para recuperar filas eliminadas, restaure el respaldo anterior a la eliminación.')
        if not current or current[0] != event['nueva']:
            raise ValueError('La nota actual no coincide con este cambio.')
        if event['operacion'] == 'INSERT':
            conn.execute(f'DELETE FROM {table} WHERE {where}', keys)
        else:
            conn.execute(f'UPDATE {table} SET {column}=? WHERE {where}', [event['anterior'], *keys])
        conn.execute('UPDATE Historial_Notas SET revertido=1 WHERE id=?', (event_id,))
