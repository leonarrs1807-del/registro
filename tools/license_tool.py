"""Issuer-only CLI. Store private keys outside the application and Git checkout."""
import argparse
import base64
import json
from pathlib import Path
from datetime import date
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, BestAvailableEncryption, load_pem_private_key
from getpass import getpass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    keygen = subs.add_parser('keygen')
    keygen.add_argument('--private', type=Path, required=True)
    keygen.add_argument('--public', type=Path, required=True)
    issue = subs.add_parser('issue')
    issue.add_argument('--private', type=Path, required=True)
    issue.add_argument('--licensee', required=True)
    issue.add_argument('--expires', required=True, help='YYYY-MM-DD')
    issue.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    password = getpass('Contraseña de la clave privada (mínimo 12 caracteres): ').encode()
    if len(password) < 12:
        parser.error('La contraseña debe tener al menos 12 caracteres.')
    if args.command == 'keygen':
        if args.private.resolve().is_relative_to(Path(__file__).resolve().parent.parent):
            parser.error('Guarde la clave privada fuera del repositorio.')
        if args.private.exists() or args.public.exists():
            parser.error('No se sobrescriben claves existentes.')
        key = Ed25519PrivateKey.generate()
        with args.private.open('xb') as out:
            out.write(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, BestAvailableEncryption(password)))
        args.private.chmod(0o600)
        with args.public.open('xb') as out:
            out.write(key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
    else:
        expiration = date.fromisoformat(args.expires)
        if expiration < date.today() or not args.licensee.strip():
            parser.error('Indique un titular y una fecha de vencimiento vigente.')
        key = load_pem_private_key(args.private.read_bytes(), password=password)
        if not isinstance(key, Ed25519PrivateKey):
            parser.error('Se requiere una clave Ed25519.')
        payload = dict(product='registro', licensee=args.licensee, expires=expiration.isoformat())
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        document = dict(payload=payload, signature=base64.b64encode(key.sign(canonical)).decode())
        with args.output.open('x', encoding='utf-8') as out:
            json.dump(document, out, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
