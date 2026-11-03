"""Checklist observations and an explicit, optional conversion to a grade."""
import json
from calculos import rounded
from db_safety import connection,valid_number
from instrumentos import checklist_value


def summary(indicators,answers,students=None):
    groups={}
    for item in indicators:groups.setdefault(item['capacidad_id'],[]).append(item['id'])
    result={}
    for student in (students if students is not None else sorted({s for s,i in answers})):
        for cap,ids in groups.items():
            values=[answers.get((student,i)) for i in ids]
            evaluated=[v for v in values if v is not None and str(v).strip()]
            fulfilled=sum(checklist_value(v) for v in evaluated)
            result[(student,cap)]=dict(cumplidos=fulfilled,evaluados=len(evaluated),total=len(ids),
                pendientes=len(ids)-len(evaluated),porcentaje=100*fulfilled/len(evaluated) if evaluated else None)
    return result


def validate_rule(rule):
    if not isinstance(rule,dict):raise ValueError('Seleccione una regla de conversión.')
    kind=rule.get('tipo')
    if kind in ('orientacion','proporcional'):return {'tipo':kind}
    if kind!='tramos':raise ValueError('Seleccione Proporcional o defina su propia tabla de cumplimiento.')
    rows=rule.get('tramos',[])
    if not 2<=len(rows)<=10:raise ValueError('Defina entre 2 y 10 tramos.')
    rows=[{'minimo':valid_number(r['minimo'],0,100,'Cumplimiento mínimo'),
           'nota':valid_number(r['nota'],0,20,'Nota del tramo')} for r in rows]
    if rows[0]['minimo']!=0 or any(a['minimo']>=b['minimo'] or a['nota']>b['nota'] for a,b in zip(rows,rows[1:])):
        raise ValueError('Empiece en 0 % y ordene los tramos y sus notas de menor a mayor.')
    return {'tipo':kind,'tramos':rows}


def preview(indicators,answers,rule,students=None):
    rule=validate_rule(rule);result={}
    if rule['tipo']=='orientacion':return result
    for key,state in summary(indicators,answers,students).items():
        if state['pendientes'] or not state['evaluados']:continue
        percent=state['porcentaje']
        value=percent/5 if rule['tipo']=='proporcional' else next(r['nota'] for r in reversed(rule['tramos']) if percent>=r['minimo'])
        result[key]=rounded(value)
    return result


def configuration(session,path):
    with connection(path) as conn:
        row=conn.execute('SELECT cotejo_regla,cotejo_pendiente FROM Sesiones_Clase WHERE id=?',(session,)).fetchone()
        legacy=conn.execute('SELECT 1 FROM Notas_Sesion_Capacidad WHERE sesion_id=? AND nota IS NOT NULL LIMIT 1',(session,)).fetchone()
    return (json.loads(row[0]) if row and row[0] else {'tipo':'anterior' if legacy else 'orientacion'},bool(row and row[1]))


def store_rule(session,rule,path):
    rule=validate_rule(rule)
    with connection(path) as conn:
        row=conn.execute('SELECT tipo_instrumento FROM Sesiones_Clase WHERE id=?',(session,)).fetchone()
        if not row or row[0]!='Lista de Cotejo':raise ValueError('La actividad no utiliza lista de cotejo.')
        conn.execute('UPDATE Sesiones_Clase SET cotejo_regla=?,cotejo_pendiente=0 WHERE id=?',(json.dumps(rule),session))


def capacity_label(name):
    """Use a meaningful stable name, never the position of a selected capacity."""
    for start,caption in [('Comunica','Comunica su comprensión'),('Usa estrategias','Usa estrategias'),
                          ('Argumenta','Argumenta afirmaciones'),('Traduce','Traduce cantidades'),
                          ('Modela','Modela objetos'),('Representa','Representa'),('Explica','Explica')]:
        if name.startswith(start):return caption
    return name if len(name)<=38 else name[:35].rstrip()+'…'


def review_signature(indicators,answers):
    return json.dumps([sorted((i["id"],i["capacidad_id"],i["criterio"]) for i in indicators),sorted((s,i,str(v)) for (s,i),v in answers.items() if v is not None)],ensure_ascii=False)
