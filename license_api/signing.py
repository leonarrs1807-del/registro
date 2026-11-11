from calendar import monthrange
from datetime import datetime,timezone
import hashlib,json,uuid
import jwt
from license_tokens import ISSUER,SCHEMA,key_id


def expiration(issued,kind):
    if kind=='perpetua':return None
    year,month=(issued.year+issued.month//12,issued.month%12+1) if kind=='mensual' else (issued.year+1,issued.month)
    return issued.replace(year=year,month=month,day=min(issued.day,monthrange(year,month)[1]))


def request_hash(request):
    return hashlib.sha256(json.dumps(request.model_dump(),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def issue(request,settings,idempotency_key=None,now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    expiry=expiration(now,request.tipo_licencia);identity=str(uuid.uuid4());config=settings.apps[request.app_id]
    claims=dict(iss=ISSUER,aud=config['product'],schema=SCHEMA,jti=identity,iat=int(now.timestamp()),nbf=int(now.timestamp()),
        app_id=request.app_id,tipo_licencia=request.tipo_licencia,hwid=request.hwid,courses=config.get('courses',['*']))
    if expiry is not None:claims['exp']=int(expiry.timestamp())
    token=jwt.encode(claims,settings.private_key,algorithm='EdDSA',headers={'kid':key_id(settings.private_key.public_key()),'typ':'JWT'})
    return dict(id=identity,app_id=request.app_id,tipo_licencia=request.tipo_licencia,hwid=request.hwid,
        licencia_key=token,fecha_emision=now.isoformat(),fecha_expiracion=expiry.isoformat() if expiry else None,
        estado='activa',idempotency_key=idempotency_key,request_hash=request_hash(request))


def response(record):
    return dict(licencia_key=record['licencia_key'],fecha_expiracion=record['fecha_expiracion'],estado='exito')
