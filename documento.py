"""Versioned internal document: complete SQLite state with integrity metadata."""
from pathlib import Path
import hashlib,json,tempfile,zipfile
from app_storage import copy_database,validate_database

MAX_DOCUMENT_BYTES=256*1024*1024


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
