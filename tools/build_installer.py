"""Compile Inno Setup and preserve a readable diagnostic in Actions annotations."""
from pathlib import Path
import os,subprocess,sys


def main():
    root=Path(__file__).resolve().parent.parent
    compiler=Path(os.environ.get('ProgramFiles(x86)',r'C:\Program Files (x86)'))/'Inno Setup 6'/'ISCC.exe'
    result=subprocess.run([str(compiler),str(root/'installer'/'windows.iss')],cwd=root,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace')
    print(result.stdout,flush=True)
    if result.returncode:
        detail=result.stdout[-2800:].replace('%','%25').replace('\r','%0D').replace('\n','%0A')
        print('::error title=Compilador Inno Setup::'+detail,flush=True)
    return result.returncode


if __name__=='__main__':raise SystemExit(main())
