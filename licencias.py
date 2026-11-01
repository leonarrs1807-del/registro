"""Manual offline activation. Academic documents never carry activation state."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import base64
import ctypes
import hashlib
import json
import math
import os
import re
import sys
import unicodedata
import uuid

from app_security import hash_password, verify_password

PRODUCT = 'registro'
VERSION = 2
TRIAL_DAYS = 30
REGISTRY_PATH = r'Software\RegistroDocente\ActivacionV2'


def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def course_key(name, level):
    name = re.sub(r'\s*\(Primaria\)\s*$', '', name, flags=re.I)
    plain = ''.join(c for c in unicodedata.normalize('NFKD', name) if not unicodedata.combining(c))
    slug = re.sub(r'[^a-z0-9]+', '-', plain.casefold()).strip('-')
    if level not in ('Primaria', 'Secundaria') or not slug:
        raise ValueError('Curso o nivel no válido.')
    return level.casefold() + ':' + slug


def device_id():
    """Hash stable OS installation identity; expose neither serials nor MachineGuid."""
    if sys.platform == 'win32':
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography',
                            0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            identity = winreg.QueryValueEx(key, 'MachineGuid')[0]
    else:
        identity = ''
        for file in ('/etc/machine-id', '/var/lib/dbus/machine-id'):
            try:
                identity = Path(file).read_text().strip()
                break
            except OSError:
                pass
        if not identity:
            raise ValueError('No se pudo identificar este equipo para la activación.')
    return hashlib.sha256(('registro-device-v2:' + identity).encode()).hexdigest()


def _dpapi(data, decrypt=False):
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_ubyte))]

    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    entropy_buffer = ctypes.create_string_buffer(b'RegistroDocente.ActivacionV2')
    entropy = Blob(len(entropy_buffer.raw), ctypes.cast(entropy_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    crypt = ctypes.windll.crypt32
    operation = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    operation.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob),
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    operation.restype = wintypes.BOOL
    if not operation(ctypes.byref(source), None, ctypes.byref(entropy), None, None, 1, ctypes.byref(output)):
        raise ValueError('El registro de activación no pertenece a esta cuenta de Windows o está dañado.')
    kernel = ctypes.windll.kernel32
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel.LocalFree(output.pbData)


def _utc(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Fecha de activación no válida.')
    return result.astimezone(timezone.utc)


def validate_request(request):
    if not isinstance(request, dict) or request.get('product') != PRODUCT or request.get('version') != VERSION:
        raise ValueError('La solicitud no corresponde a esta versión de Registro Docente.')
    for field in ('account_id', 'request_id'):
        uuid.UUID(request[field])
    if not re.fullmatch(r'[a-f0-9]{64}', request.get('device', '')):
        raise ValueError('Identificador de computadora no válido.')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', request.get('email', '')) or not request.get('name', '').strip():
        raise ValueError('La solicitud no contiene un titular y correo válidos.')
    catalog = request.get('catalog', [])
    if not isinstance(catalog, list) or len(catalog) > 500:
        raise ValueError('Catálogo no válido.')
    for item in catalog:
        if not isinstance(item, dict) or not re.fullmatch(r'(primaria|secundaria):[a-z0-9-]+', item.get('key', '')):
            raise ValueError('Curso de la solicitud no válido.')
    return request


def verify_activation(document, public_key, account, device, now):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    if not public_key:
        raise ValueError('Este instalador todavía necesita la clave pública del vendedor. Solicite el instalador comercial definitivo.')
    try:
        payload = document['payload']
        key = load_pem_public_key(public_key)
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError('Clave pública no válida.')
        key.verify(base64.b64decode(document['signature'], validate=True), canonical(payload))
        if payload.get('product') != PRODUCT or payload.get('version') != VERSION:
            raise ValueError('Licencia de otro producto o versión.')
        uuid.UUID(payload['license_id'])
        if (payload.get('device') != device or payload.get('account_id') != account['account_id']
                or payload.get('email') != account['email']):
            raise ValueError('Esta licencia pertenece a otra cuenta o computadora.')
        courses = payload['courses']
        if not isinstance(courses, list) or not courses or len(courses) > 500:
            raise ValueError('La licencia no contiene cursos.')
        if any(c != '*' and not re.fullmatch(r'(primaria|secundaria):[a-z0-9-]+', c) for c in courses):
            raise ValueError('Paquete de cursos no válido.')
        issued = _utc(payload['issued_at'])
        if issued > now + timedelta(minutes=5):
            raise ValueError('Compruebe la fecha y hora de la computadora.')
        if payload.get('expires_at') and now >= _utc(payload['expires_at']):
            raise ValueError('La licencia ha vencido.')
        return payload
    except ValueError:
        raise
    except Exception:
        raise ValueError('La firma de la licencia no es válida o el archivo fue modificado.') from None


class OfflineLicensing:
    def __init__(self, folder, public_key=b'', *, device=None, clock=None, registry=None):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / 'cuenta.activacion'
        self.public_key = public_key
        self.device = device or device_id()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.registry = sys.platform == 'win32' if registry is None else registry
        self.state = self._load()

    def _seal(self, raw, decrypt=False):
        if sys.platform == 'win32':
            return _dpapi(raw, decrypt)
        # Development/Linux fallback. The commercial Windows edition uses DPAPI.
        from cryptography.fernet import Fernet
        key_file = self.folder / '.activacion.key'
        if not key_file.exists():
            if decrypt:
                raise ValueError('Falta la protección de la cuenta local. Restaure su respaldo de activación.')
            fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(Fernet.generate_key())
        cipher = Fernet(key_file.read_bytes())
        return cipher.decrypt(raw) if decrypt else cipher.encrypt(raw)

    def _registry_read(self):
        if not self.registry:
            return None
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
                return winreg.QueryValueEx(key, 'Estado')[0]
        except FileNotFoundError:
            return None

    def _load(self):
        states = []
        values = [self.path.read_bytes() if self.path.exists() else None, self._registry_read()]
        for raw in values:
            if raw is None:
                continue
            try:
                state = json.loads(self._seal(raw, decrypt=True))
                if state['version'] != VERSION or state['device'] != self.device:
                    raise ValueError('Cuenta de otra computadora.')
                uuid.UUID(state['account_id'])
                _utc(state['trial_started'])
                _utc(state['last_seen'])
                if not isinstance(state['licenses'], list) or not state['password'].startswith('pbkdf2_sha256$'):
                    raise ValueError('Registro incompleto.')
                states.append(state)
            except Exception:
                raise ValueError('No se puede leer la activación de esta cuenta. No se reinicia la demo. Restaure cuenta.activacion en esta misma cuenta de Windows o contacte al vendedor.') from None
        if not states:
            return None
        if len({s['account_id'] for s in states}) != 1:
            raise ValueError('Los registros de cuenta no coinciden. Contacte al vendedor antes de reemplazarlos.')
        state = max(states, key=lambda s: s['revision']).copy()
        state['trial_started'] = min(s['trial_started'] for s in states)
        state['last_seen'] = max(s['last_seen'] for s in states)
        return state

    def _save(self):
        self.state['revision'] += 1
        raw = self._seal(canonical(self.state))
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('wb') as stream:
            stream.write(raw)
        if sys.platform != 'win32':
            temporary.chmod(0o600)
        temporary.replace(self.path)
        if self.registry:
            import winreg
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
                winreg.SetValueEx(key, 'Estado', 0, winreg.REG_BINARY, raw)

    def register(self, name, email, username, password, trial_course):
        if self.state is not None:
            raise ValueError('Ya hay una cuenta en este perfil. La demo no se puede reiniciar.')
        name, email, username = name.strip(), email.strip().casefold(), username.strip()
        if not name or not username or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise ValueError('Complete nombre, correo y usuario. El correo identifica al comprador; no se verifica por Internet.')
        if len(password.strip()) < 8:
            raise ValueError('Use una contraseña de al menos 8 caracteres.')
        if not re.fullmatch(r'(primaria|secundaria):[a-z0-9-]+', trial_course):
            raise ValueError('Elija el único curso de la demo.')
        now = self.clock().isoformat()
        self.state = dict(version=VERSION, revision=0, device=self.device, account_id=str(uuid.uuid4()),
                          name=name, email=email, username=username, password=hash_password(password),
                          trial_course=trial_course, trial_started=now, last_seen=now, licenses=[])
        self._save()

    def authenticate(self, username, password):
        return bool(self.state and self.state['username'].casefold() == username.strip().casefold()
                    and verify_password(password, self.state['password']))

    def update_profile(self, name, username, password=''):
        if not self.state or not name.strip() or not username.strip():
            raise ValueError('Indique nombre y usuario.')
        if password and len(password.strip()) < 8:
            raise ValueError('La nueva contraseña debe tener al menos 8 caracteres.')
        self.state.update(name=name.strip(), username=username.strip())
        if password:
            self.state['password'] = hash_password(password)
        self._save()

    def request(self, catalog):
        if not self.state:
            raise ValueError('Cree primero su cuenta.')
        return validate_request(dict(product=PRODUCT, version=VERSION, request_id=str(uuid.uuid4()),
                                     account_id=self.state['account_id'], name=self.state['name'],
                                     email=self.state['email'], device=self.device, catalog=catalog))

    def import_license(self, document):
        if not self.state:
            raise ValueError('Cree primero su cuenta en esta computadora.')
        payload = verify_activation(document, self.public_key, self.state, self.device, self.clock())
        current = [d for d in self.state['licenses'] if d['payload']['license_id'] != payload['license_id']]
        self.state['licenses'] = current + [document]
        self._save()
        return payload

    def status(self):
        if not self.state:
            return dict(mode='sin_cuenta', days=0, courses=set(), message='Cree su cuenta para iniciar la demo.')
        now = self.clock()
        seen = _utc(self.state['last_seen'])
        if now < seen - timedelta(minutes=5):
            return dict(mode='reloj', days=0, courses=set(), message='La fecha del equipo retrocedió. Corrija la fecha y hora para volver a editar. Puede consultar y exportar sus datos.')
        if now > seen + timedelta(minutes=1):
            self.state['last_seen'] = now.isoformat()
            self._save()
        remaining = _utc(self.state['trial_started']) + timedelta(days=TRIAL_DAYS) - now
        days = max(0, math.ceil(remaining.total_seconds() / 86400))
        courses = set()
        for document in self.state['licenses']:
            try:
                payload = verify_activation(document, self.public_key, self.state, self.device, now)
                courses.update(payload['courses'])
            except (ValueError, KeyError):
                continue
        if courses:
            return dict(mode='licencia', days=days, courses=courses,
                        message='Licencia activa · ' + ('todos los cursos' if '*' in courses else f'{len(courses)} curso(s) comprados'))
        if days:
            return dict(mode='demo', days=days, courses={self.state['trial_course']},
                        message=f'Demo: {days} día(s) restantes · un curso habilitado')
        return dict(mode='vencida', days=0, courses=set(), message='Demo vencida · Solo consulta y exportación. Importe una licencia para volver a editar.')

    def can_edit(self, course):
        status = self.status()
        return '*' in status['courses'] or course in status['courses']

    def backup_account(self, destination):
        if not self.state:
            raise ValueError('No hay una cuenta registrada.')
        if Path(destination).resolve() == self.path.resolve():
            raise ValueError('Elija otra ubicación para la copia de la cuenta.')
        self._save()
        Path(destination).write_bytes(self.path.read_bytes())
