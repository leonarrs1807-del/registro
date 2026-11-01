"""Fail closed when a commercial build lacks the seller's public-only key."""
from pathlib import Path
import sys

root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
from licencias import public_key_id


def main():
    path=root/'license_public_key.pem'
    if not path.is_file():
        raise ValueError('Falta license_public_key.pem. El vendedor debe crear sus claves en su PC y aportar únicamente la pública.')
    fingerprint=public_key_id(path.read_bytes())
    print('Edición comercial para una cuenta y PC. Propietario: Leonardo Roque.')
    print('Identificación de la clave pública: '+fingerprint)


if __name__=='__main__':
    try:main()
    except (ValueError,OSError) as exc:
        message=str(exc).replace('%','%25').replace('\r','%0D').replace('\n','%0A')
        print('::error title=Clave pública comercial::'+message,flush=True)
        raise SystemExit(1)
