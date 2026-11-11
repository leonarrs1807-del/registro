"""Portable instrument models, independent of school ledgers and student data."""
from contextlib import closing
from datetime import datetime
import hashlib,json,sqlite3,tempfile,uuid
from pathlib import Path

import app_storage
from db_safety import atomic,backed_up,connection
from instrumentos import normalized,validate_definition,instrument_kind,definition
from escala import DEFAULT


def database_path():
    return app_storage.data_dir()/'biblioteca'/'instrumentos.db'


def connect(path=None):
    path=Path(path or database_path());path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path,timeout=15);conn.row_factory=sqlite3.Row
    conn.execute('''CREATE TABLE IF NOT EXISTS Modelos(
        id TEXT PRIMARY KEY,familia TEXT NOT NULL,version INTEGER NOT NULL,firma TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,nivel TEXT NOT NULL,curso TEXT NOT NULL,grado TEXT NOT NULL,
        tema TEXT NOT NULL,competencia TEXT NOT NULL,tipo TEXT NOT NULL,datos TEXT NOT NULL,
        origen TEXT NOT NULL DEFAULT '',creado TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        archivado INTEGER NOT NULL DEFAULT 0)''')
    conn.execute('CREATE INDEX IF NOT EXISTS biblioteca_busqueda ON Modelos(nivel,curso,grado,tipo,familia)')
    conn.commit();return conn


def clean_model(raw):
    """Whitelist model fields: never retain IDs, students, answers or credentials."""
    result={key:str(raw.get(key,'') or '').strip() for key in ('nombre','nivel','curso','grado','tema','competencia','proposito')}
    if not all(result[k] for k in ('nombre','nivel','curso','competencia')):
        raise ValueError('El modelo necesita nombre, nivel, curso y competencia.')
    if result['nivel'] not in ('Primaria','Secundaria'):raise ValueError('Nivel educativo no reconocido.')
    result['tipo']=instrument_kind(raw.get('tipo','Rúbrica'))
    result['criterios']=[];capacity_names={}
    for item in raw.get('criterios',[]):
        capacity=str(item.get('capacidad_nombre','')).strip()
        if not capacity:raise ValueError('Cada criterio necesita el nombre de su capacidad.')
        capacity=capacity_names.setdefault(normalized(capacity),capacity)
        row=validate_definition({**item,'tipo':result['tipo']})
        result['criterios'].append(dict(capacidad_nombre=capacity,criterio=row['criterio'],
            puntaje_maximo=row['puntaje_maximo'],descriptores=row['descriptores'],puntajes=row['puntajes']))
    if not result['criterios']:raise ValueError('La rúbrica o lista de cotejo no tiene criterios.')
    return result


def from_session(session,db_path,name=None):
    from evaluacion_datos import activity,get_indicators
    context=activity(session,db_path);items=get_indicators(session,db_path)
    if not items:raise ValueError('Diseñe o importe primero los criterios de la actividad.')
    with connection(db_path) as conn:
        course,level=conn.execute('SELECT nombre,nivel FROM Cursos WHERE id=?',(context['curso_id'],)).fetchone()
    return clean_model(dict(nombre=name or context['titulo_tema'],nivel=level,curso=course,grado=context['grado'],
        tema=context['titulo_tema'],competencia=context['competencia_nombre'],proposito=context.get('proposito',''),
        tipo=items[0]['tipo'],criterios=items))


def save_models(models,path=None,origin=''):
    prepared=[clean_model(m) for m in models]
    identities=[]
    with closing(connect(path)) as conn,conn:
        for model in prepared:
            data=json.dumps(model,ensure_ascii=False,sort_keys=True,separators=(',',':'))
            digest=hashlib.sha256(data.encode()).hexdigest()
            old=conn.execute('SELECT id FROM Modelos WHERE firma=?',(digest,)).fetchone()
            if old:
                conn.execute('UPDATE Modelos SET archivado=0 WHERE id=?',(old[0],));identities.append(old[0]);continue
            family=hashlib.sha256('|'.join(normalized(model[k]) for k in ('nombre','nivel','curso','grado','competencia','tipo')).encode()).hexdigest()
            version=conn.execute('SELECT COALESCE(MAX(version),0)+1 FROM Modelos WHERE familia=?',(family,)).fetchone()[0]
            identity=uuid.uuid4().hex
            conn.execute('''INSERT INTO Modelos(id,familia,version,firma,nombre,nivel,curso,grado,tema,competencia,tipo,datos,origen)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(identity,family,version,digest,*(model[k] for k in ('nombre','nivel','curso','grado','tema','competencia','tipo')),data,str(origin)))
            identities.append(identity)
    return identities


def list_models(path=None,search='',course='',grade='',kind='',archived=False,history=False,include_data=True):
    with closing(connect(path)) as conn:
        fields='*' if include_data else 'id,familia,version,nombre,nivel,curso,grado,tema,competencia,tipo,origen,creado,archivado'
        rows=[dict(r) for r in conn.execute(f'SELECT {fields} FROM Modelos WHERE archivado=? ORDER BY creado DESC,rowid DESC',(int(archived),))]
    found=[];families=set();words=normalized(search).split()
    for row in rows:
        if not history and row['familia'] in families:continue
        families.add(row['familia'])
        if course and normalized(row['curso'])!=normalized(course):continue
        if grade and row['grado']!=grade:continue
        if kind and row['tipo']!=kind:continue
        if not all(word in normalized(' '.join(str(row[k]) for k in ('nombre','nivel','curso','grado','tema','competencia','tipo'))) for word in words):continue
        if include_data:row['modelo']=clean_model(json.loads(row['datos']))
        found.append(row)
    return found


def get_model(identity,path=None):
    with closing(connect(path)) as conn:row=conn.execute('SELECT datos FROM Modelos WHERE id=?',(identity,)).fetchone()
    if not row:raise ValueError('El modelo ya no está en la biblioteca.')
    return clean_model(json.loads(row[0]))


def archive(identity,path=None,archived=True):
    with closing(connect(path)) as conn,conn:
        conn.execute('UPDATE Modelos SET archivado=? WHERE familia=(SELECT familia FROM Modelos WHERE id=?)',(int(archived),identity))


def backup(destination,path=None):
    source=Path(path or database_path());destination=Path(destination)
    with closing(connect(source)):pass
    if destination.resolve()==source.resolve():raise ValueError('Elija otra ubicación para la copia de la biblioteca.')
    if destination.exists():
        with closing(sqlite3.connect(f'{destination.resolve().as_uri()}?mode=ro',uri=True)) as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='Modelos'").fetchone():
                raise ValueError('Ese archivo contiene otros datos. Elija un nombre nuevo para la biblioteca.')
    with tempfile.TemporaryDirectory(dir=destination.parent) as folder:
        staged=Path(folder)/'biblioteca.db';app_storage.copy_database(source,staged)
        with closing(sqlite3.connect(staged)) as conn:
            if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('No se pudo verificar la copia de la biblioteca.')
        staged.replace(destination)
    return destination


def _source_models(source):
    """Inspect old schemas read-only, including their original internal library."""
    with closing(sqlite3.connect(f'{Path(source).resolve().as_uri()}?mode=ro',uri=True)) as conn:
        conn.row_factory=sqlite3.Row
        tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if conn.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('La base de origen no está íntegra.')
        if 'Modelos' in tables:
            return [clean_model(json.loads(r[0])) for r in conn.execute('SELECT datos FROM Modelos ORDER BY rowid')],[]
        if not {'Capacidades','Competencias','Cursos'}<=tables:raise ValueError('No se reconocen rúbricas en esta base de datos.')
        course_columns={r[1] for r in conn.execute('PRAGMA table_info(Cursos)')}
        caps={r['id']:dict(r) for r in conn.execute('''SELECT a.id,a.nombre AS capacidad_nombre,p.nombre AS competencia,
            c.nombre AS curso,'''+('c.nivel' if 'nivel' in course_columns else "'Secundaria'")+''' AS nivel
            FROM Capacidades a JOIN Competencias p ON p.id=a.competencia_id JOIN Cursos c ON c.id=p.curso_id''')}
        scale_columns={r[1] for r in conn.execute('PRAGMA table_info(Escala_Logro)')}
        scales={r[0]:tuple(r[1:]) for r in conn.execute('SELECT nivel,b,a,ad FROM Escala_Logro')} if {'nivel','b','a','ad'}<=scale_columns else {}
        models=[];warnings=[]
        def add(name,items,context=None):
            context=context or {};items=[dict(i) for i in items if i.get('activo',1)]
            if not items:return
            for item in items:
                metadata=caps.get(item.get('capacidad_id'),{})
                item['capacidad_nombre']=item.get('capacidad_nombre') or metadata.get('capacidad_nombre','')
            metadata=caps.get(items[0].get('capacidad_id'),{})
            try:
                items=[definition(item,scales.get(caps.get(item.get('capacidad_id'),{}).get('nivel','Secundaria'),DEFAULT)) for item in items]
                models.append(clean_model(dict(nombre=name,nivel=metadata.get('nivel','Secundaria'),curso=metadata.get('curso',''),
                    grado=context.get('grado',''),tema=context.get('titulo_tema',name),competencia=metadata.get('competencia',''),
                    proposito=context.get('proposito',''),tipo=items[0].get('tipo','Rúbrica'),criterios=items)))
            except (ValueError,TypeError,KeyError) as exc:warnings.append(f'{name}: {exc}')
        if {'Instrumento_Indicadores','Sesiones_Clase'}<=tables:
            sessions={r['id']:dict(r) for r in conn.execute('SELECT * FROM Sesiones_Clase')}
            grouped={}
            for row in conn.execute('SELECT * FROM Instrumento_Indicadores ORDER BY id'):
                item=dict(row)
                if item.get('activo',1):grouped.setdefault(item['sesion_id'],[]).append(item)
            for identity,items in grouped.items():
                context=sessions.get(identity)
                if context:add(context.get('titulo_tema') or f'Instrumento {identity}',items,context)
        if 'Biblioteca_Instrumentos' in tables:
            for row in conn.execute('SELECT nombre,datos FROM Biblioteca_Instrumentos ORDER BY nombre'):
                try:add(row[0],json.loads(row[1]))
                except (ValueError,TypeError) as exc:warnings.append(f'{row[0]}: {exc}')
        return models,warnings


def read_source(source):
    source=Path(source)
    if source.suffix.lower()=='.xlsx':
        import openpyxl
        from excel_tablas import metadata
        with closing(openpyxl.load_workbook(source,data_only=True)) as wb:
            meta=metadata(wb)
            if meta.get('format')!='registro-tabla' or 'Instrumento' not in wb:
                raise ValueError('Importe este Excel en una actividad y use Guardar en biblioteca para convertirlo en modelo.')
            sheet=wb['Instrumento'];items=[]
            for row in sheet.iter_rows(min_row=7,values_only=True):
                if row[0]:items.append(dict(capacidad_nombre=str(row[0]),criterio=str(row[1] or ''),puntaje_maximo=row[2],
                    descriptores=dict(zip(('C','B','A','AD'),row[3:7])),puntajes=dict(zip(('C','B','A','AD'),row[7:11]))))
            return [clean_model(dict(nombre=meta.get('model_name') or meta.get('theme') or sheet['A1'].value,tema=meta.get('model_theme',meta.get('theme','')),
                nivel=meta.get('level',''),curso=meta.get('course',''),grado=meta.get('grade',''),competencia=sheet['B3'].value,
                proposito=sheet['B4'].value,tipo=meta.get('kind','Rúbrica'),criterios=items))],[]
    if source.suffix.lower()=='.registro':
        import documento
        with tempfile.TemporaryDirectory() as folder:
            return _source_models(documento.open_document(source,Path(folder)/'origen.db'))
    return _source_models(source)


def export_excel(destination,model):
    import db
    from excel_tablas import export_activity
    from evaluacion_datos import save_indicators
    if Path(destination).suffix.lower()!='.xlsx':raise ValueError('Guarde el modelo con extensión .xlsx.')
    model=clean_model(model)
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'modelo.db';db.inicializar_db(path)
        with connection(path) as conn:
            conn.execute('UPDATE Docente_Config SET nivel_educativo=? WHERE id=1',(model['nivel'],))
            row=conn.execute('SELECT id FROM Cursos WHERE nombre=? AND nivel=?',(model['curso'],model['nivel'])).fetchone()
            course=row[0] if row else db.crear_curso(model['curso'],path)
        competency=db.crear_competencia(course,model['competencia'],path)
        capacities={name:db.crear_capacidad(competency,name,path) for name in dict.fromkeys(i['capacidad_nombre'] for i in model['criterios'])}
        session=db.crear_o_actualizar_sesion_clase(None,course,competency,model['grado'] or '3°','A',model['tema'] or model['nombre'],
            model['proposito'],1,[(i,'') for i in capacities.values()],db_path=path,metodo=model['tipo'])
        save_indicators(session,model['tipo'],[{**i,'capacidad_id':capacities[i['capacidad_nombre']]} for i in model['criterios']],path)
        export_activity(destination,session,path,roster=[],library=True)
        import openpyxl
        from excel_tablas import META
        with closing(openpyxl.load_workbook(destination)) as wb:
            wb[META].append(['model_name',model['nombre']]);wb[META].append(['model_theme',model['tema']]);wb.save(destination)


def preview_model(model,session,db_path):
    from evaluacion_datos import activity
    model=clean_model(model);context=activity(session,db_path)
    with connection(db_path) as conn:
        course,level=conn.execute('SELECT nombre,nivel FROM Cursos WHERE id=?',(context['curso_id'],)).fetchone()
        if normalized(course)!=normalized(model['curso']) or level!=model['nivel']:
            raise ValueError(f"Este modelo corresponde a {model['nivel']} · {model['curso']}. Abra una actividad de ese curso y nivel.")
        graded=bool(conn.execute('SELECT 1 FROM Notas_Sesion_Capacidad WHERE sesion_id=? AND nota IS NOT NULL LIMIT 1',(session,)).fetchone()
            or conn.execute('SELECT 1 FROM Instrumento_Respuestas WHERE sesion_id=? LIMIT 1',(session,)).fetchone())
        same=normalized(context['competencia_nombre'])==normalized(model['competencia'])
        names={normalized(c['capacidad_nombre']) for c in context['capacidades']} if same else set()
    capacities=list(dict.fromkeys(item['capacidad_nombre'] for item in model['criterios']))
    return dict(new_activity=graded or not same,capacities=capacities,
        missing=[name for name in capacities if normalized(name) not in names],context=context,model=model)


@backed_up
@atomic
def apply_model(model,session,db_path):
    """Copy definitions into a ledger; an evaluated activity always stays intact."""
    import db
    from evaluacion_datos import save_indicators
    plan=preview_model(model,session,db_path);model=plan['model'];ctx=plan['context']
    with connection(db_path) as conn:
        comps={normalized(r[1]):r[0] for r in conn.execute('SELECT id,nombre FROM Competencias WHERE curso_id=?',(ctx['curso_id'],))}
        competency=comps.get(normalized(model['competencia']))
        if competency is None:competency=db.crear_competencia(ctx['curso_id'],model['competencia'],db_path)
        existing={normalized(r[1]):r[0] for r in conn.execute('SELECT id,nombre FROM Capacidades WHERE competencia_id=?',(competency,))}
        capacity_ids={}
        for name in plan['capacities']:
            identity=existing.get(normalized(name))
            if identity is None:identity=db.crear_capacidad(competency,name,db_path);existing[normalized(name)]=identity
            capacity_ids[name]=identity
        title=ctx['titulo_tema']+(' · '+model['nombre'] if plan['new_activity'] else '')
        target=db.crear_o_actualizar_sesion_clase(None if plan['new_activity'] else session,ctx['curso_id'],competency,
            ctx['grado'],ctx['seccion'],title,ctx.get('proposito') or model['proposito'],ctx['peso_clase'],
            [(identity,'') for identity in capacity_ids.values()],categoria=ctx['categoria'],db_path=db_path,
            tipo_actividad=ctx.get('tipo_actividad','Actividad'),metodo=model['tipo'],unidad_id=ctx.get('unidad_id') or 0)
        save_indicators(target,model['tipo'],[{**item,'capacidad_id':capacity_ids[item['capacidad_nombre']]} for item in model['criterios']],db_path)
    return target
