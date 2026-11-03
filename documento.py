"""Versioned internal document: complete SQLite state with integrity metadata."""
from pathlib import Path
import hashlib,json,tempfile,zipfile
from app_storage import copy_database,validate_database

MAX_DOCUMENT_BYTES=256*1024*1024


def new_empty_record(source,destination):
    """Create a genuinely empty school record, keeping teacher and curriculum."""
    from contextlib import closing
    import sqlite3
    import db,app_storage
    source=Path(source);destination=Path(destination)
    if destination.exists() or source.resolve()==destination.resolve():raise ValueError('Seleccione un destino nuevo para el registro vacío.')
    saved=app_storage.backup_database(source,'antes-registro-vacio')
    with tempfile.TemporaryDirectory(dir=destination.parent) as folder:
        staged=Path(folder)/'vacio.db';app_storage.copy_database(source,staged)
        with closing(sqlite3.connect(staged)) as target,target:
            target.execute('PRAGMA foreign_keys=ON')
            tables={r[0] for r in target.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ['Puntos_Bloques','Sesiones_Clase','Estudiantes']:
                if table in tables:target.execute(f'DELETE FROM "{table}"')
            for table in tables:
                if (table.startswith('Historial_') and table!='Historial_Reglas') or 'papelera' in table.casefold():
                    target.execute('DELETE FROM "'+table.replace('"','""')+'"')
        app_storage.validate_database(staged)
        reserved=False
        try:
            with destination.open('xb'):pass
            reserved=True
            app_storage.copy_database(staged,destination);app_storage.validate_database(destination)
        except Exception:
            if reserved:destination.unlink(missing_ok=True)
            raise
    return saved


def save_document(destination,db_path):
    if Path(destination).suffix.lower()!='.registro' or Path(destination).resolve()==Path(db_path).resolve():
        raise ValueError('Guarde el documento con extensión .registro, separado de la base de datos.')
    with tempfile.TemporaryDirectory() as folder:
        staged=Path(folder)/'registro.db';copy_database(db_path,staged);validate_database(staged)
        if staged.stat().st_size>MAX_DOCUMENT_BYTES:raise ValueError('La base supera el límite de 256 MB del documento; utilice un respaldo .db.')
        digest=hashlib.sha256(staged.read_bytes()).hexdigest()
        manifest={'format':'registro-docente','version':1,'database':'registro.db','sha256':digest}
        target=Path(destination);temp=target.with_name(target.name+'.tmp')
        try:
            with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('manifest.json',json.dumps(manifest));archive.write(staged,'registro.db')
            temp.replace(target)
        finally:temp.unlink(missing_ok=True)


def open_document(source,destination):
    """Never extract arbitrary paths or overwrite a user's existing database."""
    target=Path(destination)
    if target.exists():raise ValueError('El destino ya existe. Seleccione un documento nuevo.')
    with zipfile.ZipFile(source) as archive:
        if sorted(archive.namelist())!=['manifest.json','registro.db']:
            raise ValueError('El documento no tiene una estructura válida.')
        if archive.getinfo('manifest.json').file_size>16384 or archive.getinfo('registro.db').file_size>MAX_DOCUMENT_BYTES:
            raise ValueError('Documento demasiado grande.')
        manifest=json.loads(archive.read('manifest.json'))
        if manifest.get('format')!='registro-docente' or manifest.get('version')!=1:
            raise ValueError('Versión de documento no compatible.')
        data=archive.read('registro.db')
        if hashlib.sha256(data).hexdigest()!=manifest.get('sha256'):
            raise ValueError('El documento está incompleto o fue alterado.')
        with tempfile.TemporaryDirectory() as folder:
            staged=Path(folder)/'validar.db';staged.write_bytes(data);validate_database(staged)
            with target.open('xb') as out:out.write(data)
    return target
