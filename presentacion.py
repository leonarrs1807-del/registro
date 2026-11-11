"""Switch between numerical, literal and combined views without changing grades."""
from decimal import Decimal,InvalidOperation
import re
from escala import thresholds

MODES={'Ambos':'ambos','Números / 20':'numero','Letras':'letra'}


def format_grade(value,mode='ambos',path=None,limits=None,letter=None):
    if value is None or str(value).strip() in ('','-','--','Pendiente','Sin evaluar'):return 'Pendiente'
    raw=str(value).strip();manual=raw.startswith('✎')
    match=re.match(r'^\s*(?:✎\s*)?(-?\d+(?:[.,]\d+)?)\s*(?:\([A-Z]+\))?\s*$',raw)
    if not match:return raw
    try:note=Decimal(match[1].replace(',','.'))
    except InvalidOperation:return raw
    if not note.is_finite() or not 0<=note<=20:return raw
    b,a,ad=limits or (thresholds(path) if path else (10.5,13.5,17.5))
    level=letter or ('C' if note<Decimal(str(b)) else 'B' if note<Decimal(str(a)) else 'A' if note<Decimal(str(ad)) else 'AD')
    number=format(note,'f').rstrip('0').rstrip('.') if '.' in format(note,'f') else format(note,'f')
    text=level if mode=='letra' else number if mode=='numero' else f'{number} ({level})'
    return ('✎ ' if manual else '')+text
