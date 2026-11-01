"""Seller-only signing functions. No private key is included in the customer app."""
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
import base64
import uuid
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, PublicFormat, BestAvailableEncryption, load_pem_private_key)
from licencias import canonical, validate_request, PRODUCT, VERSION


def create_keys(private_path, public_path, password):
    private_path, public_path = Path(private_path), Path(public_path)
    if len(password.strip()) < 12:
        raise ValueError('Proteja la clave privada con una contraseña de al menos 12 caracteres.')
    if private_path.resolve() == public_path.resolve() or private_path.exists() or public_path.exists():
        raise ValueError('Elija dos nombres nuevos y diferentes. No se reemplazan claves existentes.')
    key = Ed25519PrivateKey.generate()
    encrypted = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, BestAvailableEncryption(password.encode()))
    public = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    with private_path.open('xb') as stream:
        stream.write(encrypted)
    private_path.chmod(0o600)
    try:
        with public_path.open('xb') as stream:
            stream.write(public)
    except BaseException:
        private_path.unlink()
        raise
    return public


def sign_request(request, private_pem, password, courses, *, expires=None, reference='', now=None):
    validate_request(request)
    selected = sorted(set(courses))
    available = {item['key'] for item in request['catalog']}
    if not selected or (selected != ['*'] and not set(selected) <= available):
        raise ValueError('Seleccione los cursos comprados o el paquete de todos los cursos.')
    issued = now or datetime.now(timezone.utc)
    expires_at = None
    if expires:
        expiry = date.fromisoformat(expires)
        expires_at = datetime.combine(expiry + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        if expires_at <= issued:
            raise ValueError('El vencimiento debe ser hoy o una fecha futura.')
    try:
        key = load_pem_private_key(private_pem, password=password.encode())
    except (ValueError, TypeError):
        raise ValueError('La clave privada o su contraseña no son correctas.') from None
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError('Se requiere la clave privada Ed25519 del vendedor.')
    payload = dict(product=PRODUCT, version=VERSION, license_id=str(uuid.uuid4()),
                   request_id=request['request_id'], account_id=request['account_id'],
                   name=request['name'], email=request['email'], device=request['device'],
                   courses=selected, issued_at=issued.isoformat(),
                   expires_at=expires_at.isoformat() if expires_at else None,
                   reference=reference.strip()[:200])
    return dict(payload=payload, signature=base64.b64encode(key.sign(canonical(payload))).decode('ascii'))
