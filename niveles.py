"""Separate primary and secondary records, preserving the existing secondary IDs."""


def migrate_levels(conn, secondary_catalog):
    for table in ('Cursos','Estudiantes','Sesiones_Clase'):
        cols={r[1] for r in conn.execute(f'PRAGMA table_info({table})')}
        if 'nivel' not in cols:conn.execute(f"ALTER TABLE {table} ADD COLUMN nivel TEXT NOT NULL DEFAULT 'Secundaria'")
    cols={r[1] for r in conn.execute('PRAGMA table_info(Docente_Config)')}
    if 'nivel_educativo' not in cols:conn.execute("ALTER TABLE Docente_Config ADD COLUMN nivel_educativo TEXT NOT NULL DEFAULT 'Secundaria'")
    primary={name:data for name,data in secondary_catalog.items() if name not in ('Ciencias Sociales','Desarrollo Personal, Ciudadanía y Cívica (DPCC)')}
    primary['Personal Social']={**secondary_catalog['Desarrollo Personal, Ciudadanía y Cívica (DPCC)'],**secondary_catalog['Ciencias Sociales']}
    for name,competences in primary.items():
        name='Primaria · '+name
        if conn.execute('SELECT 1 FROM Cursos WHERE nombre=?',(name,)).fetchone():continue
        course=conn.execute("INSERT INTO Cursos(nombre,nivel) VALUES(?,'Primaria')",(name,)).lastrowid
        conn.execute('INSERT INTO Pesos_Rubros_Curso VALUES(?,40,25,20,15)',(course,))
        for title,capacities in competences.items():
            comp=conn.execute('INSERT INTO Competencias(curso_id,nombre) VALUES(?,?)',(course,title)).lastrowid
            for capacity in capacities:conn.execute('INSERT INTO Capacidades(competencia_id,nombre) VALUES(?,?)',(comp,capacity))
    cols={r[1] for r in conn.execute('PRAGMA table_info(Sesiones_Clase)')}
    if 'archivada' not in cols:conn.execute('ALTER TABLE Sesiones_Clase ADD COLUMN archivada INTEGER NOT NULL DEFAULT 0')
    conn.execute('''CREATE TRIGGER IF NOT EXISTS estudiante_nivel_insert AFTER INSERT ON Estudiantes
        BEGIN UPDATE Estudiantes SET nivel=(SELECT nivel_educativo FROM Docente_Config WHERE id=1) WHERE ID=NEW.ID; END''')
    conn.execute('''CREATE TRIGGER IF NOT EXISTS sesion_nivel_insert AFTER INSERT ON Sesiones_Clase
        BEGIN UPDATE Sesiones_Clase SET nivel=(SELECT nivel FROM Cursos WHERE id=NEW.curso_id) WHERE id=NEW.id; END''')


def active_level(conn):
    row=conn.execute('SELECT nivel_educativo FROM Docente_Config WHERE id=1').fetchone()
    return row[0] if row else 'Secundaria'
