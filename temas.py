"""Topic names belong to the reused activity, independently of the source model."""
from db_safety import atomic,connection


def topic_name(value):
    text=str(value or '').strip()
    if not text:raise ValueError('Escribe el tema de la actividad antes de continuar.')
    return text


@atomic
def import_with_topic(importer,args,title,db_path):
    title=topic_name(title)
    result=importer(*args,db_path=db_path)
    session=getattr(result,'session_id',args[0])
    with connection(db_path) as conn:
        if conn.execute('UPDATE Sesiones_Clase SET titulo_tema=? WHERE id=?',(title,session)).rowcount!=1:
            raise ValueError('No se encontró la actividad importada.')
    return result
