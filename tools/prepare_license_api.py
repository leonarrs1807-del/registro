"""Prepare server secrets locally without printing them or replacing vendor keys."""
import argparse,base64,json,secrets,sys
from getpass import getpass
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key,load_pem_public_key,Encoding,PublicFormat


def main():
    root=Path(__file__).resolve().parent.parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private',type=Path,required=True)
    parser.add_argument('--public',type=Path,default=root/'license_public_key.pem')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.resolve().is_relative_to(root) or args.output.exists():parser.error('Elija un archivo nuevo fuera del repositorio para guardar los secretos.')
    password=getpass('Contraseña de la clave privada original (vacío si no está cifrada): ')
    try:
        pem=args.private.read_bytes();key=load_pem_private_key(pem,password=password.encode() or None)
        public=load_pem_public_key(args.public.read_bytes())
        if not isinstance(key,Ed25519PrivateKey) or key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)!=public.public_bytes(Encoding.Raw,PublicFormat.Raw):
            raise ValueError('La clave privada no corresponde a la clave pública del instalador comercial.')
        values={'API_KEY':secrets.token_urlsafe(48),'LICENSE_PRIVATE_KEY_B64':base64.b64encode(pem).decode(),'LICENSE_PRIVATE_KEY_PASSWORD':password}
        with args.output.open('x',encoding='utf-8') as file:json.dump(values,file,indent=2)
        args.output.chmod(0o600)
        print('Secretos preparados en el archivo elegido. Cópielos a los secretos del servidor; no los suba al repositorio ni los incluya en FlutterFlow.')
    except (ValueError,OSError,TypeError):parser.error('No se pudieron preparar los secretos. Compruebe la clave original, su contraseña, la pública y la ruta de salida.')


if __name__=='__main__':main()
