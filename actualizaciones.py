"""Signed update manifests, verified downloads and data snapshots before installing."""
from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
import base64,hashlib,json,os,re,shutil,sqlite3,subprocess,sys,tempfile
from urllib.request import Request,build_opener,HTTPRedirectHandler
from cryptography.hazmat.primitives.serialization import load_pem_public_key

MAX_INSTALLER=512*1024*1024


def canonical(payload):return json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()


def https_url(value):
    parsed=urlsplit(value)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('Se requiere una dirección HTTPS sin usuario ni contraseña.')
    return value


def version(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{1,6}\.\d{1,6}\.\d{1,6}',value):raise ValueError('Versión no válida: use mayor.menor.corrección.')
    return tuple(int(part) for part in value.split('.'))


def validate_manifest(payload,app_id='registro'):
    if not isinstance(payload,dict) or payload.get('schema')!=1 or payload.get('app_id')!=app_id:
        raise ValueError('La actualización no corresponde a esta aplicación.')
    if payload.get('edicion')!='comercial' or payload.get('plataforma')!='windows-x64':raise ValueError('Actualización de otra edición o plataforma.')
    version(payload.get('version'));https_url(payload.get('url',''))
    if not re.fullmatch(r'[a-f0-9]{64}',payload.get('sha256','')):raise ValueError('Falta la huella SHA-256 del instalador.')
    if type(payload.get('bytes')) is not int or not 0<payload['bytes']<=MAX_INSTALLER:raise ValueError('Tamaño de instalador no válido.')
    if not isinstance(payload.get('notas',''),str) or len(payload.get('notas',''))>5000:raise ValueError('Notas de versión demasiado extensas.')
    return payload


def sign_manifest(payload,key):
    payload={'schema':1,**payload};validate_manifest(payload,payload.get('app_id'))
    return {'payload':payload,'signature':base64.b64encode(key.sign(canonical(payload))).decode()}


def verify_manifest(document,public_key,current,app_id='registro'):
    try:
        payload=document['payload'];load_pem_public_key(public_key).verify(base64.b64decode(document['signature'],validate=True),canonical(payload))
        validate_manifest(payload,app_id)
    except Exception:raise ValueError('La firma o los datos de la actualización no son válidos. Se conserva la instalación actual.') from None
    return payload if version(payload['version'])>version(current) else None


class SecureRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        https_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def open_https(url):
    return build_opener(SecureRedirect()).open(Request(https_url(url),headers={'User-Agent':'RegistroDocente-Updater/1'}),timeout=30)


def check_update(url,public_key,current):
    with open_https(url) as stream:
        raw=stream.read(32769)
        if len(raw)>32768:raise ValueError('Respuesta de actualización demasiado grande.')
    return verify_manifest(json.loads(raw),public_key,current)


def verify_installer(path,manifest):
    path=Path(path)
    if path.stat().st_size!=manifest['bytes']:raise ValueError('La descarga del instalador está incompleta.')
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=manifest['sha256']:raise ValueError('El instalador no coincide con la versión publicada. No se ejecutará.')
    return path


def download_installer(manifest,folder,progress=None):
    validate_manifest(manifest)
    root=Path(folder)/'updates';root.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix=manifest['version']+'-',dir=root))
    path=temporary/'RegistroDocente-Setup.exe';partial=path.with_suffix('.part')
    try:
        total=0
        with open_https(manifest['url']) as stream,partial.open('xb') as target:
            while chunk:=stream.read(1024*256):
                total+=len(chunk)
                if total>manifest['bytes']:raise ValueError('El instalador supera el tamaño publicado.')
                target.write(chunk)
                if progress:progress(total/manifest['bytes'])
        verify_installer(partial,manifest);partial.replace(path);return path
    except BaseException:shutil.rmtree(temporary,ignore_errors=True);raise


def backup_before_update(folder,active_database,target_version):
    """Copies SQLite consistently, including a global model library and activation files."""
    import app_storage
    root=Path(folder).resolve();version(target_version)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    backup=root/'backups'/('antes-actualizar-'+target_version+'-'+stamp);backup.mkdir(parents=True)
    sources={p.resolve() for p in root.rglob('*.db') if not any(part in ('backups','updates') for part in p.relative_to(root).parts)}
    active=Path(active_database).resolve()
    if active.is_file():sources.add(active)
    records=[]
    try:
        for n,source in enumerate(sorted(sources)):
            try:relative=source.relative_to(root)
            except ValueError:relative=Path('externos')/f'{n}-{source.name}'
            target=backup/relative;target.parent.mkdir(parents=True,exist_ok=True);app_storage.copy_database(source,target)
            with closing(sqlite3.connect(target)) as conn:
                if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('No se pudo verificar un respaldo de datos.')
            records.append({'origen':str(source),'copia':str(relative)})
        for pattern in ('*.json','*.activacion'):
            for source in root.glob(pattern):shutil.copy2(source,backup/source.name)
        (backup/'contenido.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        return backup
    except BaseException:shutil.rmtree(backup,ignore_errors=True);raise


def launch_installer(path,manifest):
    if sys.platform!='win32':raise ValueError('La instalación automática está disponible en Windows.')
    verify_installer(path,manifest)
    return subprocess.Popen([str(path),'/SP-','/SILENT','/NORESTART','/CLOSEAPPLICATIONS','/REINICIAR=1'],close_fds=True)
