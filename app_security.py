"""Local password hashing and optional offline commercial licenses."""
import base64
import hashlib
import hmac
import json
import secrets
import sys
from datetime import date


def license_public_key():
    if getattr(sys, 'frozen', False):
        # PyInstaller embeds this attribute through the build's runtime hook.
        # A missing hook is an invalid build, not permission to skip activation.
        return sys._registro_license_public_key
    from app_storage import resource_dir
    key_file = resource_dir() / 'license_public_key.pem'
    return key_file.read_bytes() if key_file.exists() else b''


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310_000)
    return 'pbkdf2_sha256$310000$%s$%s' % (salt.hex(), digest.hex())


def verify_password(password, encoded):
    try:
        algorithm, rounds, salt, expected = encoded.split('$')
        if algorithm != 'pbkdf2_sha256' or not 100_000 <= int(rounds) <= 1_000_000:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def verify_license(document, public_key_pem):
    """Only the issuer holds the private Ed25519 key; never ship it."""
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    payload = document['payload']
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    load_pem_public_key(public_key_pem).verify(base64.b64decode(document['signature'], validate=True), canonical)
    if payload.get('product') != 'registro' or not payload.get('licensee'):
        raise ValueError('La licencia no corresponde a Registro.')
    if payload.get('expires') and date.fromisoformat(payload['expires']) < date.today():
        raise ValueError('La licencia ha vencido.')
    return payload
