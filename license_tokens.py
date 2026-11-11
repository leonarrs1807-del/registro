"""Shared SaaS JWT verification. The desktop holds only the vendor's public key."""
from datetime import datetime,timezone
import hashlib,re,uuid
import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key,Encoding,PublicFormat

ISSUER='registro-licencias-saas-v1'
SCHEMA=1
APP_PATTERN=r'[a-z0-9][a-z0-9._-]{0,63}'
COURSE_PATTERN=r'(primaria|secundaria):[a-z0-9-]+'


def key_id(public_key):
    return hashlib.sha256(public_key.public_bytes(Encoding.Raw,PublicFormat.Raw)).hexdigest()


def verify_token(token,public_pem,product,device,now=None):
    """Enforce the signature, intended app, type, dates and optional device binding."""
    now=now or datetime.now(timezone.utc)
    try:
        if not isinstance(token,str) or len(token)>20000:raise ValueError('Licencia demasiado grande o inválida.')
        key=load_pem_public_key(public_pem)
        if not isinstance(key,Ed25519PublicKey):raise ValueError('Se requiere la clave pública Ed25519 del vendedor.')
        header=jwt.get_unverified_header(token)
        if header.get('alg')!='EdDSA' or header.get('typ')!='JWT' or header.get('kid')!=key_id(key) or header.get('crit'):
            raise ValueError('Cabecera de licencia no válida para este vendedor.')
        claims=jwt.decode(token,key,algorithms=['EdDSA'],audience=product,issuer=ISSUER,
            options={'require':['iss','aud','jti','iat','nbf','app_id','tipo_licencia','schema','courses'],
                     'verify_exp':False,'verify_iat':False,'verify_nbf':False})
        if type(claims['schema']) is not int or claims['schema']!=SCHEMA:raise ValueError('Formato de licencia no compatible.')
        if not isinstance(claims['app_id'],str) or not re.fullmatch(APP_PATTERN,claims['app_id']):raise ValueError('Aplicación no válida.')
        uuid.UUID(claims['jti'])
        issued=claims['iat']
        if type(issued) is not int or type(claims['nbf']) is not int or claims['nbf']!=issued:
            raise ValueError('Fecha de emisión inválida.')
        if issued>now.timestamp()+300:raise ValueError('Compruebe la fecha y hora de la computadora.')
        kind=claims['tipo_licencia'];expiry=claims.get('exp')
        if kind not in ('mensual','anual','perpetua'):raise ValueError('Tipo de licencia no válido.')
        if kind=='perpetua':
            if expiry is not None:raise ValueError('Una licencia perpetua no debe tener vencimiento.')
        else:
            if type(expiry) is not int or expiry<=issued:raise ValueError('Falta un vencimiento válido.')
            if now.timestamp()>=expiry:raise ValueError('La licencia ha vencido.')
        hwid=claims.get('hwid')
        if hwid is not None and (not isinstance(hwid,str) or not hwid or hwid!=device):
            raise ValueError('Esta licencia pertenece a otra computadora.')
        courses=claims['courses']
        if not isinstance(courses,list) or not courses or len(courses)>500 or any(not isinstance(c,str) or (c!='*' and not re.fullmatch(COURSE_PATTERN,c)) for c in courses):
            raise ValueError('Paquete de cursos no válido.')
        return dict(product=product,version=2,license_id=claims['jti'],courses=courses,
            issued_at=datetime.fromtimestamp(issued,timezone.utc).isoformat(),
            expires_at=datetime.fromtimestamp(expiry,timezone.utc).isoformat() if expiry else None,
            app_id=claims['app_id'],tipo_licencia=kind,device=hwid,issuer_id=key_id(key))
    except ValueError:raise
    except Exception:raise ValueError('La firma de la licencia no es válida o corresponde a otra aplicación.') from None
