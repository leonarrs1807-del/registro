"""Prepare public release metadata from the actual installer, without private keys."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from actualizaciones import validate_manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer',type=Path,required=True);parser.add_argument('--version',required=True)
    parser.add_argument('--url',required=True);parser.add_argument('--notes',default='Mejoras y correcciones.')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    with args.installer.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    manifest=validate_manifest(dict(schema=1,app_id='registro',version=args.version,url=args.url,
        sha256=digest,bytes=args.installer.stat().st_size,notas=args.notes,edicion='comercial',plataforma='windows-x64'))
    with args.output.open('x',encoding='utf-8') as stream:json.dump({'registro':manifest},stream,ensure_ascii=False,indent=2)
    print('Metadatos listos. Publique primero el instalador y después configure UPDATES_JSON con este JSON.')


if __name__=='__main__':main()
