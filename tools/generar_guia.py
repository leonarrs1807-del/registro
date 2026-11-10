"""Keep the installed manual identical to the in-app help."""
from pathlib import Path
import sys

root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
from ayuda_contenido import TOPICS

guide='REGISTRO DOCENTE 2.1.1 - GUÍA PASO A PASO\n\n'
guide+='Abra Ayuda o pulse F1. Puede buscar por palabras, seleccionar un apartado y usar Anterior / Siguiente.\n\n'
guide+='ÍNDICE\n'+'\n'.join(f'{n}. {name}' for n,name in enumerate(TOPICS,1))+'\n\n'
guide+='\n\n'.join(name.upper()+'\n\n'+body for name,body in TOPICS.items())+'\n'
(root/'docs'/'GUIA-USO.txt').write_text(guide,encoding='utf-8')
