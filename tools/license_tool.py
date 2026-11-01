"""Seller CLI alternative to RegistroLicencias.exe. Keep private keys outside Git."""
import argparse
import json
from pathlib import Path
from getpass import getpass
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from licencias_emisor import create_keys, sign_request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    keygen = subs.add_parser('keygen')
    keygen.add_argument('--private', type=Path, required=True)
    keygen.add_argument('--public', type=Path, required=True)
    issue = subs.add_parser('issue')
    issue.add_argument('--private', type=Path, required=True)
    issue.add_argument('--request', type=Path, required=True)
    issue.add_argument('--courses', nargs='+', required=True, help='SKU del curso; * habilita todos')
    issue.add_argument('--expires', help='YYYY-MM-DD; vacío = permanente')
    issue.add_argument('--reference', default='')
    issue.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    password = getpass('Contraseña de la clave privada: ')
    try:
        if args.command == 'keygen':
            if args.private.resolve().is_relative_to(Path(__file__).resolve().parent.parent):
                parser.error('Guarde la clave privada fuera del repositorio.')
            create_keys(args.private, args.public, password)
        else:
            request = json.loads(args.request.read_text(encoding='utf-8'))
            document = sign_request(request, args.private.read_bytes(), password, args.courses,
                                    expires=args.expires, reference=args.reference)
            with args.output.open('x', encoding='utf-8') as stream:
                json.dump(document, stream, ensure_ascii=False, indent=2)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
