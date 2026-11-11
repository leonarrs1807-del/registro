"""Create a standalone API source ZIP from an explicit list, never from secrets."""
from pathlib import Path
import zipfile


def main():
    root=Path(__file__).resolve().parent.parent;output=root/'dist'/'GeneradorLicencias-API.zip';output.parent.mkdir(exist_ok=True)
    files=[*sorted((root/'license_api').glob('*.py')),root/'license_api'/'requirements.txt',root/'license_api'/'README.md',
        root/'license_api'/'supabase.sql',root/'license_api'/'.env.example',root/'license_tokens.py',root/'actualizaciones.py',
        root/'render.yaml',root/'tools'/'prepare_license_api.py',root/'tools'/'make_update_manifest.py']
    if (root/'license_public_key.pem').exists():files.append(root/'license_public_key.pem')
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:archive.write(file,file.relative_to(root))
    print(output)


if __name__=='__main__':main()
