"""Human activity labels; database identities stay in the model."""
from collections import Counter


def activity_labels(sessions):
    counts=Counter(s['titulo_tema'] for s in sessions);used=set();result={}
    for item in sessions:
        title=item['titulo_tema'];name=title
        if counts[title]>1:
            kind=item.get('tipo_instrumento','Normal')
            name+=f" · {'Nota directa' if kind=='Normal' else 'Cotejo' if 'Cotejo' in kind else kind}"
        if name in used:name+=' · '+str(item.get('fecha',''))
        base=name;n=2
        while name in used:name=f'{base} · actividad {n}';n+=1
        used.add(name);result[item['id']]=name
    return result
