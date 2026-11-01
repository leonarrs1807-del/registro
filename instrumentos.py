"""Shared rubric/checklist rules used by Excel imports and classroom evaluation."""
import unicodedata
from db_safety import valid_number


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(text or '').strip().casefold()) if not unicodedata.combining(c))


def instrument_kind(value):
    value=normalized(value)
    if value=='rubrica':return 'Rúbrica'
    if value in ('lista de cotejo','cotejo'):return 'Lista de Cotejo'
    raise ValueError('Seleccione Rúbrica o Lista de Cotejo.')


def checklist_value(value):
    text=normalized(value)
    if text in ('si','true','1'):return True
    if text in ('no','false','0'):return False
    raise ValueError('Cotejo: seleccione Sí o No. Una celda vacía queda sin evaluar.')


def normalized_grade(kind,values):
    """values are (entered score/answer, maximum) for one student's capacity."""
    kind=instrument_kind(kind)
    if not values:raise ValueError('La capacidad no tiene indicadores.')
    total=0.;maximum=0.
    for raw,limit in values:
        limit=valid_number(limit,.000001,20,'Máximo del indicador')
        if raw is None or str(raw).strip()=='':raise ValueError('Complete todos los indicadores de la capacidad; vacío no equivale a cero.')
        if kind=='Lista de Cotejo':value=limit if checklist_value(raw) else 0
        else:value=valid_number(str(raw).replace(',','.'),0,limit,'Puntaje del indicador')
        total+=value;maximum+=limit
    return round(20*total/maximum,2)

