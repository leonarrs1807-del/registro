"""Shared rubric/checklist rules used by Excel imports and classroom evaluation."""
import unicodedata
import json,re
from db_safety import valid_number
from calculos import decimal,normalized_total

LEVELS=('C','B','A','AD')
LEVEL_NAMES={'C':'Inicio','B':'En proceso','A':'Logro esperado','AD':'Logro destacado'}
DESCRIPTORS=(
    'Presenta una respuesta parcial y requiere apoyo frecuente para desarrollar la tarea.',
    'Desarrolla parte de la tarea; necesita apoyo puntual para corregir errores y explicar su respuesta.',
    'Desarrolla la tarea de forma autónoma y explica con claridad las decisiones y el procedimiento.',
    'Sustenta la respuesta, verifica el resultado y aplica lo aprendido en una situación nueva.')


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',str('' if text is None else text).strip().casefold()) if not unicodedata.combining(c))


def legacy_parts(text):
    text=str(text or '').strip()
    matches=list(re.finditer(r'(?:^|\n| \| )(AD|A|B|C):\s*',text))
    descriptors={m[1]:text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)].strip() for i,m in enumerate(matches)}
    return (text[:matches[0].start()].strip() if matches else text),descriptors


def clean_criterion(text,capacity=''):
    text=legacy_parts(text)[0]
    if capacity:
        repeated=capacity+': '+capacity
        if text.startswith(repeated):text=text[len(capacity)+2:]
        if re.fullmatch(re.escape(capacity)+r'\s*:\s*evidencia\s+\d+',text,flags=re.I):text=capacity
    return text.strip()


def criterion_caption(item):
    value=item['criterio']
    return 'Desempeño global de esta capacidad' if normalized(value)==normalized(item.get('capacidad_nombre','')) else value


def default_scores(maximum,limits=(10.5,13.5,17.5)):
    b,a,ad=map(decimal,limits);maximum=decimal(maximum)
    equivalents=(b/2,(b+a)/2,(a+ad)/2,decimal(20))
    return {level:float(score*maximum/20) for level,score in zip(LEVELS,equivalents)}


def definition(row,limits=(10.5,13.5,17.5)):
    item=dict(row);kind=instrument_kind(item.get('tipo','Rúbrica'))
    maximum=valid_number(item.get('puntaje_maximo',20),.000001,20,'Puntos máximos')
    text,embedded=legacy_parts(item.get('criterio',item.get('indicador_texto','')))
    criterion=clean_criterion(text,item.get('capacidad_nombre',''))
    provided=item.get('descriptores',{})
    defaults={'Destacado (18-20)','Logrado (14-17)','En Proceso (11-13)','En Inicio (0-10)'}
    descriptors={}
    for i,level in enumerate(LEVELS):
        original=item.get('descriptor_'+level.lower(),'')
        descriptors[level]=provided[level] if level in provided else embedded[level] if level in embedded else (original if original and original not in defaults else DESCRIPTORS[i])
    scores=item.get('puntajes')
    if scores is None and item.get('puntos_niveles'):
        scores=json.loads(item['puntos_niveles'])
    if scores is None:scores=default_scores(maximum,limits)
    return {**item,'tipo':kind,'criterio':criterion,'descriptores':descriptors,'puntajes':scores,'puntaje_maximo':maximum}


def validate_definition(row,limits=(10.5,13.5,17.5)):
    item=definition(row,limits)
    if not item['criterio']:raise ValueError('Escriba un criterio observable para cada fila.')
    if item['tipo']=='Rúbrica':
        scores=[]
        for level in LEVELS:
            if not str(item['descriptores'][level]).strip():raise ValueError(f'Falta el descriptor del nivel {level}.')
            scores.append(valid_number(item['puntajes'][level],0,item['puntaje_maximo'],f'Puntos de {level}'))
        if not all(a<b for a,b in zip(scores,scores[1:])):raise ValueError('Los puntos deben aumentar: C < B < A < AD.')
        if abs(scores[-1]-item['puntaje_maximo'])>1e-8:raise ValueError('El nivel AD debe valer los puntos máximos del criterio.')
        item['puntajes']=dict(zip(LEVELS,scores))
    return item


def answer_points(kind,raw,maximum,scores=None):
    if raw is None or str(raw).strip()=='':raise ValueError('Hay un criterio pendiente; vacío no equivale a cero.')
    if instrument_kind(kind)=='Lista de Cotejo':return maximum if checklist_value(raw) else 0
    token=str(raw).strip().upper()
    if token in LEVELS:return valid_number((scores or default_scores(maximum))[token],0,maximum,'Puntos del nivel')
    if normalized(raw) in ('ne','sin evidencia'):return 0
    return valid_number(str(raw).replace(',','.'),0,maximum,'Puntaje del criterio')


def rescale_answer(value,previous,current):
    """Keep the same achievement when a teacher changes the maximum points."""
    if value is None or current['tipo']!='Rúbrica':return value
    if str(value).strip().upper() in LEVELS or normalized(value) in ('ne','sin evidencia'):return value
    points=answer_points(previous['tipo'],value,previous['puntaje_maximo'],previous['puntajes'])
    return str(decimal(points)*decimal(current['puntaje_maximo'])/decimal(previous['puntaje_maximo']))


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


def normalized_grade(kind,values,*,allow_pending=False):
    """values are (entered score/answer, maximum) for one student's capacity."""
    kind=instrument_kind(kind)
    if not values:raise ValueError('La capacidad no tiene indicadores.')
    total=decimal(0);maximum=decimal(0)
    for entry in values:
        raw,limit=entry[:2];scores=entry[2] if len(entry)>2 else None
        limit=valid_number(limit,.000001,20,'Máximo del indicador')
        if raw is None or str(raw).strip()=='':
            if allow_pending:continue
            raise ValueError('Complete todos los indicadores de la capacidad; vacío no equivale a cero.')
        value=answer_points(kind,raw,limit,scores)
        total+=decimal(value);maximum+=decimal(limit)
    if not maximum:raise ValueError('La capacidad sigue pendiente; no hay criterios evaluados.')
    return normalized_total(total,maximum)


def entered_answer(item,raw):
    """Canonical editable answer; blank, zero and an achievement level stay distinct."""
    if raw is None or not str(raw).strip():return None
    if item['tipo']=='Lista de Cotejo':return 'Sí' if checklist_value(raw) else 'No'
    token=str(raw).strip().upper()
    if token in LEVELS:return token
    if normalized(raw) in ('ne','sin evidencia'):return 'NE'
    return format(answer_points(item['tipo'],raw,item['puntaje_maximo'],item['puntajes']),'.12g')

