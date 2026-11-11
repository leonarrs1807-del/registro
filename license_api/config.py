"""Server-only configuration. Fail startup if signing/authentication is incomplete."""
from dataclasses import dataclass,field
import base64,json,os,re
from urllib.parse import urlsplit
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from license_tokens import APP_PATTERN,COURSE_PATTERN


def https_origin(value):
    url=urlsplit(value)
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('','/'):
        raise ValueError('SUPABASE_URL debe ser el origen HTTPS del proyecto, sin credenciales ni rutas.')
    return value.rstrip('/')


@dataclass(frozen=True)
class Settings:
    api_key:str=field(repr=False)
    private_key:Ed25519PrivateKey=field(repr=False)
    apps:dict=field(default_factory=lambda:{'registro':{'product':'registro','courses':['*']}})
    supabase_url:str=''
    supabase_service_key:str=field(default='',repr=False)
    updates:dict=field(default_factory=dict)

    def __post_init__(self):
        if len(self.api_key)<32 or self.api_key!=self.api_key.strip():raise ValueError('API_KEY debe contener al menos 32 caracteres aleatorios, sin espacios exteriores.')
        if not isinstance(self.private_key,Ed25519PrivateKey):raise ValueError('Se requiere una clave privada Ed25519.')
        if not isinstance(self.apps,dict) or not self.apps:raise ValueError('APPS_JSON debe definir las aplicaciones que vende.')
        for app,config in self.apps.items():
            if not re.fullmatch(APP_PATTERN,app) or not isinstance(config,dict) or not re.fullmatch(APP_PATTERN,config.get('product','')):
                raise ValueError('Catálogo APPS_JSON inválido.')
            courses=config.get('courses',['*'])
            if not isinstance(courses,list) or not courses or len(courses)>500 or any(not isinstance(c,str) or (c!='*' and not re.fullmatch(COURSE_PATTERN,c)) for c in courses):
                raise ValueError('Los cursos de APPS_JSON no son válidos.')
        if bool(self.supabase_url)!=bool(self.supabase_service_key):raise ValueError('Configure SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY juntas.')
        if self.supabase_url:https_origin(self.supabase_url)
        if not isinstance(self.updates,dict):raise ValueError('UPDATES_JSON debe ser un objeto JSON.')
        from actualizaciones import validate_manifest
        for app,manifest in self.updates.items():
            if app not in self.apps or not isinstance(manifest,dict):raise ValueError('UPDATES_JSON contiene una aplicación no registrada.')
            validate_manifest({'schema':1,**manifest,'app_id':app},app)

    @classmethod
    def from_env(cls):
        try:
            pem=base64.b64decode(os.environ.get('LICENSE_PRIVATE_KEY_B64',''),validate=True)
            password=os.environ.get('LICENSE_PRIVATE_KEY_PASSWORD','').encode() or None
            key=load_pem_private_key(pem,password=password)
        except (ValueError,TypeError):raise ValueError('Configure LICENSE_PRIVATE_KEY_B64 y, si está cifrada, LICENSE_PRIVATE_KEY_PASSWORD en los secretos del servidor.') from None
        return cls(api_key=os.environ.get('API_KEY',''),private_key=key,
            apps=json.loads(os.environ.get('APPS_JSON','{"registro":{"product":"registro","courses":["*"]}}')),
            supabase_url=os.environ.get('SUPABASE_URL','').strip(),
            supabase_service_key=os.environ.get('SUPABASE_SERVICE_ROLE_KEY','').strip(),
            updates=json.loads(os.environ.get('UPDATES_JSON','{}')))
