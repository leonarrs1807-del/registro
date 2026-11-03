import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from app_storage import database_path
from app_security import hash_password, verify_password
from db_safety import connection, atomic, valid_number, migrate, backed_up

DB_PATH = database_path()

# Catálogo oficial de 10 Áreas Curriculares de Secundaria (CNEB)
CATALOGO_INICIAL: Dict[str, Dict[str, List[str]]] = {
    "Matemática": {
        "Resuelve problemas de cantidad": [
            "Traduce cantidades a expresiones numéricas",
            "Comunica su comprensión sobre los números y las operaciones",
            "Usa estrategias y procedimientos de estimación y cálculo",
            "Argumenta afirmaciones sobre las relaciones numéricas y las operaciones",
        ],
        "Resuelve problemas de regularidad, equivalencia y cambio": [
            "Traduce datos y condiciones a expresiones algebraicas y gráficas",
            "Comunica su comprensión sobre las relaciones algebraicas",
            "Usa estrategias y procedimientos para encontrar equivalencias y reglas generales",
            "Argumenta afirmaciones sobre relaciones de cambio y equivalencia",
        ],
        "Resuelve problemas de forma, movimiento y localización": [
            "Modela objetos con formas geométricas y sus transformaciones",
            "Comunica su comprensión sobre las formas y relaciones geométricas",
            "Usa estrategias y procedimientos para medir y orientarse en el espacio",
            "Argumenta afirmaciones sobre relaciones geométricas",
        ],
        "Resuelve problemas de gestión de datos e incertidumbre": [
            "Representa datos con gráficos y medidas estadísticas o probabilísticas",
            "Comunica su comprensión de los conceptos estadísticos y probabilísticos",
            "Usa estrategias y procedimientos para recopilar y procesar datos",
            "Sustenta conclusiones o decisiones con base en la información obtenida",
        ],
    },
    "Comunicación": {
        "Se comunica oralmente en su lengua materna": [
            "Obtiene información del texto oral",
            "Infiere e interpreta información del texto oral",
            "Adecúa, organiza y desarrolla las ideas de forma coherente y cohesionada",
            "Utiliza recursos no verbales y paraverbales de forma estratégica",
            "Interactúa estratégicamente con distintos interlocutores",
            "Reflexiona y evalúa la forma, el contenido y contexto del texto oral",
        ],
        "Lee diversos tipos de textos escritos en lengua materna": [
            "Obtiene información del texto escrito",
            "Infiere e interpreta información del texto",
            "Reflexiona y evalúa la forma, el contenido y contexto del texto",
        ],
        "Escribe diversos tipos de textos en lengua materna": [
            "Adecúa el texto a la situación comunicativa",
            "Organiza y desarrolla las ideas de forma coherente y cohesionada",
            "Utiliza convenciones del lenguaje escrito de forma pertinente",
            "Reflexiona y evalúa la forma, el contenido y contexto del texto escrito",
        ],
    },
    "Ciencia y Tecnología": {
        "Indaga mediante métodos científicos para construir conocimientos": [
            "Problematiza situaciones para hacer indagación",
            "Diseña estrategias para hacer indagación",
            "Genera y registra datos e información",
            "Analiza datos e información",
            "Evalúa y comunica el proceso y resultados de su indagación",
        ],
        "Explica el mundo físico basándose en conocimientos sobre los seres vivos, materia y energía": [
            "Comprende y usa conocimientos sobre los seres vivos, materia y energía, biodiversidad, Tierra y universo",
            "Evalúa las implicancias del saber y del quehacer científico y tecnológico",
        ],
        "Diseña y construye soluciones tecnológicas para resolver problemas de su entorno": [
            "Determina una alternativa de solución tecnológica",
            "Diseña la alternativa de solución tecnológica",
            "Implementa y valida la alternativa de solución tecnológica",
            "Evalúa y comunica el funcionamiento y los impactos de su alternativa de solución tecnológica",
        ],
    },
    "Ciencias Sociales": {
        "Construye interpretaciones históricas": [
            "Interpreta críticamente fuentes diversas",
            "Comprende el tiempo histórico",
            "Elabora explicaciones sobre procesos históricos",
        ],
        "Gestiona responsablemente el espacio y el ambiente": [
            "Comprende las relaciones entre los elementos naturales y sociales",
            "Maneja fuentes de información para comprender el espacio geográfico y el ambiente",
            "Genera acciones para conservar el ambiente local y global",
        ],
        "Gestiona responsablemente los recursos económicos": [
            "Comprende las relaciones entre los elementos del sistema económico y financiero",
            "Toma decisiones económicas y financieras",
        ],
    },
    "Desarrollo Personal, Ciudadanía y Cívica (DPCC)": {
        "Construye su identidad": [
            "Se valora a sí mismo",
            "Autorregula sus emociones",
            "Reflexiona y argumenta éticamente",
            "Vive su sexualidad de manera integral y responsable",
        ],
        "Convive y participa democráticamente en la búsqueda del bien común": [
            "Interactúa con todas las personas",
            "Construye normas y asume acuerdos y leyes",
            "Maneja conflictos de manera constructiva",
            "Delibera sobre asuntos públicos",
            "Participa en acciones que promueven el bienestar común",
        ],
    },
    "Inglés como Lengua Extranjera": {
        "Se comunica oralmente en inglés como lengua extranjera": [
            "Obtiene información de textos orales",
            "Infiere e interpreta información de textos orales",
            "Adecúa, organiza y desarrolla las ideas de forma coherente y cohesionada",
            "Utiliza recursos no verbales y paraverbales de forma estratégica",
            "Interactúa estratégicamente con distintos interlocutores",
            "Reflexiona y evalúa la forma, el contenido y el contexto del texto oral",
        ],
        "Lee diversos tipos de textos escritos en inglés como lengua extranjera": [
            "Obtiene información del texto escrito",
            "Infiere e interpreta información del texto escrito",
            "Reflexiona y evalúa la forma, el contenido y el contexto del texto escrito",
        ],
        "Escribe diversos tipos de textos en inglés como lengua extranjera": [
            "Adecúa el texto a la situación comunicativa",
            "Organiza y desarrolla las ideas de forma coherente y cohesionada",
            "Utiliza convenciones del lenguaje escrito de forma pertinente",
            "Reflexiona y evalúa la forma, el contenido y el contexto del texto escrito",
        ],
    },
    "Educación para el Trabajo (EPT)": {
        "Gestiona proyectos de emprendimiento económico o social": [
            "Crea propuestas de valor",
            "Aplica habilidades técnicas",
            "Trabaja cooperativamente para lograr objetivos y metas",
            "Evalúa los resultados del proyecto de emprendimiento",
        ],
    },
    "Arte y Cultura": {
        "Aprecia de manera crítica manifestaciones artístico-culturales": [
            "Percibe manifestaciones artístico-culturales",
            "Contextualiza manifestaciones artístico-culturales",
            "Reflexiona creativa y críticamente sobre manifestaciones artístico-culturales",
        ],
        "Crea proyectos desde los lenguajes artísticos": [
            "Explora y experimenta los lenguajes artísticos",
            "Aplica procesos creativos",
            "Evalúa y comunica sus procesos y proyectos",
        ],
    },
    "Educación Física": {
        "Se desenvuelve de manera autónoma a través de su motricidad": [
            "Comprende su cuerpo",
            "Se expresa corporalmente",
        ],
        "Asume una vida saludable": [
            "Comprende las relaciones entre la actividad física, alimentación, postura e higiene y la salud",
            "Incorpora prácticas que mejoran su calidad de vida",
        ],
        "Interactúa a través de sus habilidades sociomotrices": [
            "Se relaciona utilizando sus habilidades sociomotrices",
            "Crea y aplica estrategias y tácticas de juego",
        ],
    },
    "Educación Religiosa": {
        "Construye su identidad como persona humana, amada por Dios, digna, libre y trascendente": [
            "Conoce a Dios y asume su identidad religiosa y espiritual como persona digna, libre y trascendente",
            "Cultiva y valora las manifestaciones religiosas de su entorno argumentando su fe",
        ],
        "Asume la experiencia del encuentro personal y comunitario con Dios en su proyecto de vida": [
            "Transforma su entorno desde el encuentro personal y comunitario con Dios y desde la fe que profesa",
            "Actúa coherentemente en razón de su fe según los principios de su conciencia moral",
        ],
    },
}


def obtener_conexion(db_path: Path = DB_PATH):
    return connection(db_path)


def nota_a_literal(nota: Optional[float], db_path: Path = DB_PATH) -> str:
    if nota is None:
        return "-"
    from escala import thresholds
    b,a,ad=thresholds(db_path)
    if nota >= ad:
        return "AD"
    if nota >= a:
        return "A"
    if nota >= b:
        return "B"
    return "C"


def _limpiar_grado_prefijo(grado: str) -> str:
    solo_num = re.sub(r"[^0-9A-Za-z]", "", grado or "3")
    return solo_num if solo_num else "3"


def sincronizar_codigos_por_seccion(db_path: Path = DB_PATH) -> None:
    """
    Actualiza el `Codigo_Unico` de cada estudiante según su Grado, Sección
    y ubicación en la lista de esa sección (ej. 4A01, 4A02, 3B01).
    """
    with obtener_conexion(db_path) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE Estudiantes SET Codigo_Unico = 'TMP-' || ID")
        salones = cur.execute(
            "SELECT DISTINCT Grado, Seccion, nivel FROM Estudiantes ORDER BY nivel, Grado ASC, Seccion ASC"
        ).fetchall()
        for grado, seccion, nivel in salones:
            prefijo_g = _limpiar_grado_prefijo(str(grado))
            prefijo_s = re.sub(r"[^A-Za-z0-9]", "", str(seccion or "A")).upper() or "A"
            alumnos = cur.execute(
                """
                SELECT ID FROM Estudiantes
                WHERE Grado = ? AND Seccion = ? AND nivel = ?
                ORDER BY Apellidos ASC, Nombres ASC, ID ASC
                """,
                (grado, seccion, nivel),
            ).fetchall()
            for idx, (est_id,) in enumerate(alumnos, start=1):
                cur.execute(
                    "UPDATE Estudiantes SET Codigo_Unico = ? WHERE ID = ?",
                    (f"{'P' if nivel=='Primaria' else ''}{prefijo_g}{prefijo_s}{idx:02d}", est_id),
                )
        conn.commit()


@backed_up
@atomic
def inicializar_db(db_path: Path = DB_PATH) -> None:
    with obtener_conexion(db_path) as conn:
        cursor = conn.cursor()

        # 0. Configuración del Docente + Candado + Tema Visual
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Docente_Config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                nombres_docente TEXT NOT NULL DEFAULT 'Docente Titular',
                institucion TEXT NOT NULL DEFAULT 'Institución Educativa Secundaria',
                especialidad TEXT NOT NULL DEFAULT 'Matemática y Ciencias',
                usuario TEXT NOT NULL DEFAULT 'docente',
                clave TEXT NOT NULL DEFAULT '1234',
                tema_visual TEXT NOT NULL DEFAULT 'Claro Institucional'
            )
            """
        )
        cols_doc = {r[1] for r in cursor.execute("PRAGMA table_info(Docente_Config)").fetchall()}
        if "tema_visual" not in cols_doc:
            cursor.execute(
                "ALTER TABLE Docente_Config ADD COLUMN tema_visual TEXT NOT NULL DEFAULT 'Claro Institucional'"
            )
        if "tamano_letra" not in cols_doc:
            cursor.execute(
                "ALTER TABLE Docente_Config ADD COLUMN tamano_letra TEXT NOT NULL DEFAULT 'Normal (12)'"
            )
        cursor.execute(
            """
            INSERT OR IGNORE INTO Docente_Config (id, nombres_docente, institucion, especialidad, usuario, clave, tema_visual)
            VALUES (1, 'Docente Titular', 'I.E. Secundaria', 'Educación Secundaria', 'docente', '1234', 'Claro Institucional')
            """
        )

        # 1. Cursos, Competencias y Capacidades
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Cursos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                activo INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        cols_cursos = {r[1] for r in cursor.execute("PRAGMA table_info(Cursos)").fetchall()}
        if "activo" not in cols_cursos:
            cursor.execute("ALTER TABLE Cursos ADD COLUMN activo INTEGER NOT NULL DEFAULT 1")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Competencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                curso_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                FOREIGN KEY (curso_id) REFERENCES Cursos(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Capacidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competencia_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                FOREIGN KEY (competencia_id) REFERENCES Competencias(id) ON DELETE CASCADE
            )
            """
        )

        # 2. Estudiantes
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Estudiantes (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Codigo_Unico TEXT UNIQUE,
                Nombres TEXT NOT NULL,
                Apellidos TEXT NOT NULL,
                Grado TEXT NOT NULL DEFAULT '3°',
                Seccion TEXT NOT NULL DEFAULT 'A',
                Estado TEXT NOT NULL DEFAULT 'ACTIVO',
                Competencia_1 REAL NOT NULL DEFAULT 0.0,
                Competencia_2 REAL NOT NULL DEFAULT 0.0,
                Competencia_3 REAL NOT NULL DEFAULT 0.0,
                Promedio_Final REAL NOT NULL DEFAULT 0.0
            )
            """
        )
        cols_est = {r[1] for r in cursor.execute("PRAGMA table_info(Estudiantes)").fetchall()}
        if "Grado" not in cols_est:
            cursor.execute("ALTER TABLE Estudiantes ADD COLUMN Grado TEXT NOT NULL DEFAULT '3°'")
        if "Seccion" not in cols_est:
            cursor.execute("ALTER TABLE Estudiantes ADD COLUMN Seccion TEXT NOT NULL DEFAULT 'A'")
        if "Codigo_Unico" not in cols_est:
            cursor.execute("ALTER TABLE Estudiantes ADD COLUMN Codigo_Unico TEXT")
        if "Estado" not in cols_est:
            cursor.execute("ALTER TABLE Estudiantes ADD COLUMN Estado TEXT NOT NULL DEFAULT 'ACTIVO'")

        # 3. Sesiones_Clase (Actividades: Clases, Exámenes, Trabajos, Prácticas)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Sesiones_Clase (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                curso_id INTEGER NOT NULL,
                competencia_id INTEGER NOT NULL,
                grado TEXT NOT NULL,
                seccion TEXT NOT NULL,
                categoria TEXT NOT NULL DEFAULT 'Clases',
                titulo_tema TEXT NOT NULL,
                proposito TEXT DEFAULT '',
                peso_clase REAL NOT NULL DEFAULT 1.0,
                tipo_instrumento TEXT NOT NULL DEFAULT 'Normal',
                fecha TEXT NOT NULL,
                FOREIGN KEY (curso_id) REFERENCES Cursos(id) ON DELETE CASCADE,
                FOREIGN KEY (competencia_id) REFERENCES Competencias(id) ON DELETE CASCADE
            )
            """
        )
        cols_ses = {r[1] for r in cursor.execute("PRAGMA table_info(Sesiones_Clase)").fetchall()}
        if "categoria" not in cols_ses:
            cursor.execute("ALTER TABLE Sesiones_Clase ADD COLUMN categoria TEXT NOT NULL DEFAULT 'Clases'")
        if "tipo_instrumento" not in cols_ses:
            cursor.execute("ALTER TABLE Sesiones_Clase ADD COLUMN tipo_instrumento TEXT NOT NULL DEFAULT 'Normal'")
        if "cotejo_regla" not in cols_ses:
            cursor.execute("ALTER TABLE Sesiones_Clase ADD COLUMN cotejo_regla TEXT")
            # A migration preserves previously published grades and labels them as legacy.
            if cursor.execute("SELECT 1 FROM sqlite_master WHERE name='Notas_Sesion_Capacidad'").fetchone():
                cursor.execute("""UPDATE Sesiones_Clase SET cotejo_regla='{"tipo":"anterior"}'
                    WHERE tipo_instrumento='Lista de Cotejo' AND EXISTS(
                    SELECT 1 FROM Notas_Sesion_Capacidad n WHERE n.sesion_id=Sesiones_Clase.id AND n.nota IS NOT NULL)""")
        if "cotejo_pendiente" not in cols_ses:
            cursor.execute("ALTER TABLE Sesiones_Clase ADD COLUMN cotejo_pendiente INTEGER NOT NULL DEFAULT 0")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Sesion_Capacidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sesion_id INTEGER NOT NULL,
                capacidad_id INTEGER NOT NULL,
                criterio_precisado TEXT DEFAULT '',
                UNIQUE(sesion_id, capacidad_id),
                FOREIGN KEY (sesion_id) REFERENCES Sesiones_Clase(id) ON DELETE CASCADE,
                FOREIGN KEY (capacidad_id) REFERENCES Capacidades(id) ON DELETE CASCADE
            )
            """
        )

        # 4. Instrumento_Indicadores (Indicadores de Lista de Cotejo o Rúbrica por Capacidad en una Clase)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Instrumento_Indicadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sesion_id INTEGER NOT NULL,
                capacidad_id INTEGER NOT NULL,
                tipo TEXT NOT NULL DEFAULT 'Lista de Cotejo',
                indicador_texto TEXT NOT NULL,
                puntaje_maximo REAL NOT NULL DEFAULT 5.0,
                descriptor_ad TEXT DEFAULT 'Destacado (18-20)',
                descriptor_a TEXT DEFAULT 'Logrado (14-17)',
                descriptor_b TEXT DEFAULT 'En Proceso (11-13)',
                descriptor_c TEXT DEFAULT 'En Inicio (0-10)',
                FOREIGN KEY (sesion_id) REFERENCES Sesiones_Clase(id) ON DELETE CASCADE,
                FOREIGN KEY (capacidad_id) REFERENCES Capacidades(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Asistencia_Y_Comentarios_Clase (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sesion_id INTEGER NOT NULL,
                estudiante_id INTEGER NOT NULL,
                asistio INTEGER NOT NULL DEFAULT 1,
                comentario TEXT DEFAULT '',
                UNIQUE(sesion_id, estudiante_id),
                FOREIGN KEY (sesion_id) REFERENCES Sesiones_Clase(id) ON DELETE CASCADE,
                FOREIGN KEY (estudiante_id) REFERENCES Estudiantes(ID) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Notas_Sesion_Capacidad (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sesion_id INTEGER NOT NULL,
                capacidad_id INTEGER NOT NULL,
                estudiante_id INTEGER NOT NULL,
                nota REAL,
                UNIQUE(sesion_id, capacidad_id, estudiante_id),
                FOREIGN KEY (sesion_id) REFERENCES Sesiones_Clase(id) ON DELETE CASCADE,
                FOREIGN KEY (capacidad_id) REFERENCES Capacidades(id) ON DELETE CASCADE,
                FOREIGN KEY (estudiante_id) REFERENCES Estudiantes(ID) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Pesos_Rubros_Curso (
                curso_id INTEGER PRIMARY KEY,
                pct_clases REAL NOT NULL DEFAULT 40.0,
                pct_examenes REAL NOT NULL DEFAULT 25.0,
                pct_trabajos REAL NOT NULL DEFAULT 20.0,
                pct_practicas REAL NOT NULL DEFAULT 15.0,
                FOREIGN KEY (curso_id) REFERENCES Cursos(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Notas_Manuales_Capacidad (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                estudiante_id INTEGER NOT NULL,
                capacidad_id INTEGER NOT NULL,
                nota_manual REAL,
                UNIQUE(estudiante_id, capacidad_id),
                FOREIGN KEY (estudiante_id) REFERENCES Estudiantes(ID) ON DELETE CASCADE,
                FOREIGN KEY (capacidad_id) REFERENCES Capacidades(id) ON DELETE CASCADE
            )
            """
        )

        cursos_existentes = {
            row[0]: row[1] for row in cursor.execute("SELECT nombre, id FROM Cursos").fetchall()
        }
        for nombre_curso, comp_dict in CATALOGO_INICIAL.items():
            if nombre_curso not in cursos_existentes:
                cursor.execute("INSERT INTO Cursos (nombre) VALUES (?)", (nombre_curso,))
                cid = cursor.lastrowid
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO Pesos_Rubros_Curso (curso_id, pct_clases, pct_examenes, pct_trabajos, pct_practicas)
                    VALUES (?, 40.0, 25.0, 20.0, 15.0)
                    """,
                    (cid,),
                )
                for nombre_comp, lista_caps in comp_dict.items():
                    cursor.execute(
                        "INSERT INTO Competencias (curso_id, nombre) VALUES (?, ?)",
                        (cid, nombre_comp),
                    )
                    comp_id = cursor.lastrowid
                    for nombre_cap in lista_caps:
                        cursor.execute(
                            "INSERT INTO Capacidades (competencia_id, nombre) VALUES (?, ?)",
                            (comp_id, nombre_cap),
                        )
            else:
                cid = cursos_existentes[nombre_curso]
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO Pesos_Rubros_Curso (curso_id, pct_clases, pct_examenes, pct_trabajos, pct_practicas)
                    VALUES (?, 40.0, 25.0, 20.0, 15.0)
                    """,
                    (cid,),
                )

        conn.commit()

    with obtener_conexion(db_path) as conn:
        migrate(conn)
        from niveles import migrate_levels
        migrate_levels(conn, CATALOGO_INICIAL)
        from puntos import ensure_schema
        ensure_schema(conn)

    sincronizar_codigos_por_seccion(db_path)


# ==============================================================================
# PERFIL DEL DOCENTE, CANDADO Y TEMA VISUAL
# ==============================================================================


def obtener_docente_config(db_path: Path = DB_PATH) -> Dict[str, str]:
    with obtener_conexion(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM Docente_Config WHERE id = 1").fetchone()
        if not row:
            return {
                "nombres_docente": "Docente Titular",
                "institucion": "I.E. Secundaria",
                "especialidad": "Secundaria",
                "usuario": "docente",
                "tema_visual": "Oscuro Noche",
            }
        d = dict(row)
        d.setdefault("tema_visual", "Oscuro Noche")
        d.pop("clave", None)  # Never return password hashes to widgets.
        return d


def guardar_docente_config(
    nombres_docente: str,
    institucion: str,
    especialidad: str,
    usuario: str,
    clave: str,
    db_path: Path = DB_PATH,
) -> None:
    if not usuario.strip():
        raise ValueError("El usuario es obligatorio.")
    if clave and len(clave.strip()) < 8:
        raise ValueError("La nueva contraseña debe tener al menos 8 caracteres.")
    with obtener_conexion(db_path) as conn:
        current = conn.execute("SELECT clave, requiere_cambio_clave FROM Docente_Config WHERE id=1").fetchone()
        if not clave and current[1]:
            raise ValueError("Establezca una contraseña de al menos 8 caracteres.")
        encoded = hash_password(clave) if clave else current[0]
        conn.execute(
            """
            UPDATE Docente_Config
            SET nombres_docente = ?, institucion = ?, especialidad = ?, usuario = ?, clave = ?, requiere_cambio_clave = 0
            WHERE id = 1
            """,
            (
                nombres_docente.strip(),
                institucion.strip(),
                especialidad.strip(),
                usuario.strip(),
                encoded,
            ),
        )
        conn.commit()


def guardar_tema_visual_preferido(nombre_tema: str, db_path: Path = DB_PATH) -> None:
    with obtener_conexion(db_path) as conn:
        conn.execute("UPDATE Docente_Config SET tema_visual = ? WHERE id = 1", (nombre_tema,))
        conn.commit()


def verificar_credenciales_docente(usuario_ingresado: str, clave_ingresada: str, db_path: Path = DB_PATH) -> bool:
    with obtener_conexion(db_path) as conn:
        row = conn.execute("SELECT usuario, clave FROM Docente_Config WHERE id=1").fetchone()
    return bool(row and usuario_ingresado.strip().casefold() == row[0].strip().casefold()
                and verify_password(clave_ingresada, row[1]))


# ==============================================================================
# CURSOS, COMPETENCIAS Y CAPACIDADES
# ==============================================================================


def obtener_cursos(solo_activos: bool = False, db_path: Path = DB_PATH) -> List[Tuple[int, str, int]]:
    with obtener_conexion(db_path) as conn:
        q = "SELECT id, nombre, activo FROM Cursos WHERE nivel=(SELECT nivel_educativo FROM Docente_Config WHERE id=1)"
        if solo_activos:
            q += " AND activo = 1"
        q += " ORDER BY id ASC"
        return conn.execute(q).fetchall()
def alternar_curso_activo(curso_id: int, db_path: Path = DB_PATH) -> None:
    with obtener_conexion(db_path) as conn:
        cur = conn.cursor()
        actual = cur.execute("SELECT activo FROM Cursos WHERE id = ?", (curso_id,)).fetchone()[0]
        nuevo = 0 if actual == 1 else 1
        cur.execute("UPDATE Cursos SET activo = ? WHERE id = ?", (nuevo, curso_id))

def crear_curso(nombre: str, db_path: Path = DB_PATH) -> int:
    with obtener_conexion(db_path) as conn:
        cur = conn.cursor()
        from niveles import active_level
        level=active_level(conn)
        if level=="Primaria" and not nombre.startswith("Primaria · "):nombre="Primaria · "+nombre
        cur.execute("INSERT INTO Cursos (nombre,nivel) VALUES (?,?)", (nombre.strip(),level))
        cid = cur.lastrowid
        cur.execute("INSERT OR IGNORE INTO Pesos_Rubros_Curso (curso_id) VALUES (?)", (cid,))
        conn.commit()
        return cid

@backed_up
def eliminar_curso(curso_id: int, db_path: Path = DB_PATH) -> None:
    with obtener_conexion(db_path) as conn:
        conn.execute("DELETE FROM Cursos WHERE id = ?", (curso_id,))
        conn.commit()


def obtener_competencias_por_curso(curso_id: int, db_path: Path = DB_PATH) -> List[Tuple[int, str]]:
    with obtener_conexion(db_path) as conn:
        return conn.execute(
            "SELECT id, nombre FROM Competencias WHERE curso_id = ? ORDER BY id ASC",
            (curso_id,),
        ).fetchall()


def crear_competencia(curso_id: int, nombre: str, db_path: Path = DB_PATH) -> int:
    with obtener_conexion(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Competencias (curso_id, nombre) VALUES (?, ?)",
            (curso_id, nombre.strip()),
        )
        conn.commit()
        return cur.lastrowid


def obtener_capacidades_por_competencia(
    competencia_id: int, db_path: Path = DB_PATH
) -> List[Tuple[int, str]]:
    with obtener_conexion(db_path) as conn:
        return conn.execute(
            "SELECT id, nombre FROM Capacidades WHERE competencia_id = ? ORDER BY id ASC",
            (competencia_id,),
        ).fetchall()


def crear_capacidad(competencia_id: int, nombre: str, db_path: Path = DB_PATH) -> int:
    with obtener_conexion(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Capacidades (competencia_id, nombre) VALUES (?, ?)",
            (competencia_id, nombre.strip()),
        )
        conn.commit()
        return cur.lastrowid


# ==============================================================================
# ESTUDIANTES CON CÓDIGO POR SECCIÓN (EJ. 4A01, 4A02) Y ORDENAMIENTO
# ==============================================================================


@atomic
def agregar_estudiante(
    nombres: str,
    apellidos: str,
    grado: str = "3°",
    seccion: str = "A",
    codigo_personalizado: str = "",
    estado: str = "ACTIVO",
    db_path: Path = DB_PATH,
) -> int:
    with obtener_conexion(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO Estudiantes (Nombres, Apellidos, Grado, Seccion, Estado)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nombres.strip(), apellidos.strip(), grado.strip(), seccion.strip().upper(), estado),
        )
        nuevo_id = cur.lastrowid
        conn.commit()
    sincronizar_codigos_por_seccion(db_path)
    return nuevo_id


@atomic
def actualizar_datos_estudiante(
    id_estudiante: int,
    nombres: str,
    apellidos: str,
    grado: str,
    seccion: str,
    estado: str = "ACTIVO",
    db_path: Path = DB_PATH,
) -> None:
    with obtener_conexion(db_path) as conn:
        conn.execute(
            """
            UPDATE Estudiantes
            SET Nombres = ?, Apellidos = ?, Grado = ?, Seccion = ?, Estado = ?
            WHERE ID = ?
            """,
            (
                nombres.strip(),
                apellidos.strip(),
                grado.strip(),
                seccion.strip().upper(),
                estado.strip().upper(),
                id_estudiante,
            ),
        )
        conn.commit()
    sincronizar_codigos_por_seccion(db_path)


@backed_up
@atomic
def eliminar_estudiante(id_estudiante: int, db_path: Path = DB_PATH) -> None:
    with obtener_conexion(db_path) as conn:
        conn.execute("DELETE FROM Estudiantes WHERE ID = ?", (id_estudiante,))
        conn.commit()
    sincronizar_codigos_por_seccion(db_path)


def obtener_estudiantes_filtrados(
    grado: str = "Todos",
    seccion: str = "Todas",
    busqueda: str = "",
    incluir_retirados: bool = True,
    orden_por: str = "Apellidos (A-Z)",
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    query = """
        SELECT ID, COALESCE(Codigo_Unico, '') AS Codigo_Unico,
               Apellidos, Nombres, Grado, Seccion, COALESCE(Estado, 'ACTIVO') AS Estado
        FROM Estudiantes
        WHERE 1=1
    """
    query += " AND nivel=(SELECT nivel_educativo FROM Docente_Config WHERE id=1)"
    params: List[Any] = []
    if not incluir_retirados:
        query += " AND COALESCE(Estado, 'ACTIVO') = 'ACTIVO'"
    if grado and grado != "Todos":
        query += " AND Grado = ?"
        params.append(grado)
    if seccion and seccion != "Todas":
        query += " AND Seccion = ?"
        params.append(seccion)
    if busqueda.strip():
        p = f"%{busqueda.strip()}%"
        query += " AND (Nombres LIKE ? OR Apellidos LIKE ? OR Codigo_Unico LIKE ?)"
        params.extend([p, p, p])

    if orden_por == "Apellidos (Z-A)":
        query += " ORDER BY Apellidos DESC, Nombres DESC"
    elif orden_por == "Código (Ej. 4A01)":
        query += " ORDER BY Codigo_Unico ASC"
    elif orden_por == "Sección y Apellidos":
        query += " ORDER BY Grado ASC, Seccion ASC, Apellidos ASC, Nombres ASC"
    elif orden_por == "Nombres (A-Z)":
        query += " ORDER BY Nombres ASC, Apellidos ASC"
    else:
        query += " ORDER BY Apellidos ASC, Nombres ASC, ID ASC"

    with obtener_conexion(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def obtener_grados_y_secciones(db_path: Path = DB_PATH) -> Tuple[List[str], List[str]]:
    grados_base = [f"{i}°" for i in range(1,7 if obtener_docente_config(db_path).get("nivel_educativo")=="Primaria" else 6)]
    secciones_base = ["A", "B", "C", "D", "E"]
    with obtener_conexion(db_path) as conn:
        g_db = [r[0] for r in conn.execute("SELECT DISTINCT Grado FROM Estudiantes WHERE nivel=(SELECT nivel_educativo FROM Docente_Config WHERE id=1)").fetchall() if r[0]]
        s_db = [r[0] for r in conn.execute("SELECT DISTINCT Seccion FROM Estudiantes WHERE nivel=(SELECT nivel_educativo FROM Docente_Config WHERE id=1)").fetchall() if r[0]]
    return sorted(set(grados_base + g_db)), sorted(set(secciones_base + s_db))


def generar_plantilla_excel_estudiantes(ruta_destino: str) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Estudiantes"
    encabezados = ["Codigo_Seccion (Auto: 4A01)", "Apellidos", "Nombres", "Grado", "Seccion", "Estado"]
    ws.append(encabezados)
    fill_h = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    font_h = Font(color="FFFFFF", bold=True)
    for idx in range(1, len(encabezados) + 1):
        c = ws.cell(row=1, column=idx)
        c.fill = fill_h
        c.font = font_h
        c.alignment = Alignment(horizontal="center")

    for col in ["A", "B", "C", "D", "E", "F"]:
        ws.column_dimensions[col].width = 22
    wb.save(ruta_destino)


@atomic
def importar_estudiantes_desde_excel(
    ruta_archivo: str, grado_def: str = "3°", seccion_def: str = "A", db_path: Path = DB_PATH
) -> int:
    wb = openpyxl.load_workbook(ruta_archivo, data_only=True)
    ws = wb.active
    filas = list(ws.iter_rows(values_only=True))
    if not filas:
        return 0

    primera = [str(c).strip().lower() if c is not None else "" for c in filas[0]]
    idx_ape, idx_nom, idx_gra, idx_sec, idx_completo = -1, -1, -1, -1, -1

    for i, name in enumerate(primera):
        if "apellido" in name and "nombre" in name:
            idx_completo = i
        elif "apellido" in name:
            idx_ape = i
        elif "nombre" in name or "estudiante" in name or "alumno" in name:
            idx_nom = i
        elif "grado" in name or "año" in name:
            idx_gra = i
        elif "secci" in name:
            idx_sec = i

    tiene_header = any(x != -1 for x in (idx_ape, idx_nom, idx_completo))
    inicio = 1 if tiene_header else 0
    if not tiene_header:
        idx_ape, idx_nom, idx_gra, idx_sec = 0, 1, 2, 3

    insertados = 0
    with obtener_conexion(db_path) as conn:
        cur = conn.cursor()
        for row_number, fila in enumerate(filas[inicio:], inicio + 1):
            if not fila or all(c is None or str(c).strip() == "" for c in fila):
                continue
            if idx_completo != -1 and idx_ape == -1 and idx_nom == -1:
                comp = str(fila[idx_completo] or "").strip()
                if not comp:
                    raise ValueError(f"Fila {row_number}: falta el nombre completo.")
                if "," in comp:
                    p = comp.split(",", 1)
                    ape, nom = p[0].strip(), p[1].strip()
                else:
                    p = comp.split()
                    ape = " ".join(p[:2]) if len(p) >= 3 else p[0]
                    nom = " ".join(p[2:]) if len(p) >= 3 else " ".join(p[1:])
            else:
                ape = str(fila[idx_ape]).strip() if idx_ape != -1 and idx_ape < len(fila) and fila[idx_ape] is not None else ""
                nom = str(fila[idx_nom]).strip() if idx_nom != -1 and idx_nom < len(fila) and fila[idx_nom] is not None else ""

            if not nom or not ape:
                raise ValueError(f"Fila {row_number}: se requieren nombres y apellidos.")
            gra = str(fila[idx_gra]).strip() if idx_gra != -1 and idx_gra < len(fila) and fila[idx_gra] is not None else grado_def
            sec = str(fila[idx_sec]).strip().upper() if idx_sec != -1 and idx_sec < len(fila) and fila[idx_sec] is not None else seccion_def

            if cur.execute("SELECT 1 FROM Estudiantes WHERE Nombres=? AND Apellidos=? AND Grado=? AND Seccion=? AND nivel=(SELECT nivel_educativo FROM Docente_Config WHERE id=1)",
                           (nom, ape, gra or grado_def, sec or seccion_def)).fetchone():
                raise ValueError(f"Estudiante duplicado: {ape}, {nom}.")
            cur.execute(
                "INSERT INTO Estudiantes (Nombres, Apellidos, Grado, Seccion, Estado) VALUES (?, ?, ?, ?, 'ACTIVO')",
                (nom or "-", ape or "-", gra or grado_def, sec or seccion_def),
            )
            insertados += 1
        conn.commit()

    sincronizar_codigos_por_seccion(db_path)
    return insertados


# ==============================================================================
# PLANTILLAS E IMPORTACIÓN DE RÚBRICAS Y LISTAS DE COTEJO PARA UNA CLASE / ACTIVIDAD
# ==============================================================================


def obtener_indicadores_instrumento_sesion(sesion_id:int,db_path:Path=DB_PATH):
    from evaluacion_datos import get_indicators
    return get_indicators(sesion_id,db_path)


@atomic
def guardar_indicadores_instrumento_sesion(sesion_id,tipo_instrumento,lista_indicadores,db_path=DB_PATH):
    from evaluacion_datos import save_indicators
    return save_indicators(sesion_id,tipo_instrumento,lista_indicadores,db_path)


def exportar_plantilla_rubrica_o_cotejo_excel(
    ruta_destino: str, nombre_curso: str, grado: str, seccion: str, titulo_actividad: str,
    competencia_nombre: str, capacidades_y_criterios: List[Tuple[int,str,str]],
    tipo_instrumento: str = "Lista de Cotejo", db_path: Path = DB_PATH, *, sesion_id=None,
    criterios_por_capacidad=None,desde_cero=False,formato=4,incluir_estudiantes=True,
) -> None:
    from instrumentos_excel import export_template
    export_template(ruta_destino,nombre_curso,grado,seccion,titulo_actividad,competencia_nombre,
                    capacidades_y_criterios,tipo_instrumento,db_path,sesion_id,
                    criteria_counts=criterios_por_capacidad,blank=desde_cero,format_version=formato,include_students=incluir_estudiantes)


@atomic
def importar_rubrica_o_cotejo_desde_excel(
    sesion_id: int,ruta_archivo: str,grado: str,seccion: str,db_path: Path = DB_PATH,
) -> Tuple[int,int]:
    from instrumentos_excel import import_template
    return import_template(sesion_id,ruta_archivo,grado,seccion,db_path)


# ==============================================================================
# CREAR Y GESTIONAR ACTIVIDADES EVALUATIVAS (CLASES, EXÁMENES, TRABAJOS, PRÁCTICAS)
# ==============================================================================


@atomic
def crear_o_actualizar_sesion_clase(
    sesion_id: Optional[int],
    curso_id: int,
    competencia_id: int,
    grado: str,
    seccion: str,
    titulo_tema: str,
    proposito: str,
    peso_clase: float,
    capacidades_y_criterios: List[Tuple[int, str]],
    categoria: str = "Clases",
    fecha_str: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> int:
    fecha_final = date.fromisoformat(fecha_str or date.today().isoformat()).isoformat()
    peso_clase = valid_number(peso_clase, 0.000001, 1000000, "Peso")
    if not titulo_tema.strip() or not grado.strip() or not seccion.strip():
        raise ValueError("El título, grado y sección son obligatorios.")
    if not capacidades_y_criterios or len({c[0] for c in capacidades_y_criterios}) != len(capacidades_y_criterios):
        raise ValueError("Seleccione capacidades distintas para la sesión.")
    with obtener_conexion(db_path) as conn:
        cur = conn.cursor()
        if not cur.execute("SELECT 1 FROM Competencias WHERE id=? AND curso_id=?", (competencia_id, curso_id)).fetchone():
            raise ValueError("La competencia no pertenece al curso.")
        for cap_id, _ in capacidades_y_criterios:
            if not cur.execute("SELECT 1 FROM Capacidades WHERE id=? AND competencia_id=?", (cap_id, competencia_id)).fetchone():
                raise ValueError("La capacidad no pertenece a la competencia.")
        if sesion_id is None:
            cur.execute(
                """
                INSERT INTO Sesiones_Clase (
                    curso_id, competencia_id, grado, seccion, categoria, titulo_tema, proposito, peso_clase, fecha
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    curso_id,
                    competencia_id,
                    grado,
                    seccion,
                    categoria.strip(),
                    titulo_tema.strip(),
                    proposito.strip(),
                    float(peso_clase),
                    fecha_final,
                ),
            )
            sid = cur.lastrowid
        else:
            sid = sesion_id
            previous = cur.execute("SELECT curso_id, competencia_id, grado, seccion FROM Sesiones_Clase WHERE id=?", (sid,)).fetchone()
            if not previous:
                raise ValueError("La sesión ya no existe.")
            evaluated = {r[0] for r in cur.execute("SELECT DISTINCT capacidad_id FROM Notas_Sesion_Capacidad WHERE sesion_id=? AND nota IS NOT NULL", (sid,))}
            evaluated.update(r[0] for r in cur.execute("SELECT DISTINCT i.capacidad_id FROM Instrumento_Respuestas r JOIN Instrumento_Indicadores i ON i.id=r.indicador_id WHERE r.sesion_id=?",(sid,)))
            if evaluated and (tuple(previous) != (curso_id, competencia_id, grado.strip(), seccion.strip().upper()) or not evaluated <= {c[0] for c in capacidades_y_criterios}):
                raise ValueError("La sesión tiene notas o respuestas de criterios. No cambie su salón, competencia ni elimine capacidades calificadas; cree una nueva sesión.")
            cur.execute(
                """
                UPDATE Sesiones_Clase
                SET competencia_id = ?, categoria = ?, titulo_tema = ?, proposito = ?, peso_clase = ?, curso_id = ?, grado = ?, seccion = ?, fecha = ?
                WHERE id = ?
                """,
                (
                    competencia_id,
                    categoria.strip(),
                    titulo_tema.strip(),
                    proposito.strip(),
                    float(peso_clase),
                    curso_id, grado.strip(), seccion.strip().upper(), fecha_final,
                    sid,
                ),
            )
            selected_caps = [c[0] for c in capacidades_y_criterios]
            placeholders = ",".join("?" for _ in selected_caps)
            cur.execute(f"DELETE FROM Instrumento_Indicadores WHERE sesion_id=? AND capacidad_id NOT IN ({placeholders})", (sid, *selected_caps))
            cur.execute("DELETE FROM Sesion_Capacidades WHERE sesion_id = ?", (sid,))

        for cap_id, criterio in capacidades_y_criterios:
            cur.execute(
                """
                INSERT INTO Sesion_Capacidades (sesion_id, capacidad_id, criterio_precisado)
                VALUES (?, ?, ?)
                """,
                (sid, cap_id, criterio.strip()),
            )
        conn.commit()
        return sid


def actualizar_peso_actividad(sesion_id: int, nuevo_peso: float, db_path: Path = DB_PATH) -> None:
    nuevo_peso = valid_number(nuevo_peso, 0.000001, 1000000, "Peso")
    with obtener_conexion(db_path) as conn:
        conn.execute(
            "UPDATE Sesiones_Clase SET peso_clase = ? WHERE id = ?",
            (float(nuevo_peso), sesion_id),
        )
        conn.commit()


@backed_up
def eliminar_sesion_clase(sesion_id: int, db_path: Path = DB_PATH) -> None:
    with obtener_conexion(db_path) as conn:
        conn.execute("DELETE FROM Sesiones_Clase WHERE id = ?", (sesion_id,))
        conn.commit()


def obtener_sesiones_clase(
    curso_id: int,
    grado: str,
    seccion: str,
    competencia_id: Optional[int] = None,
    categoria: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    query = """
        SELECT s.id, s.curso_id, s.competencia_id, c.nombre AS competencia_nombre,
               s.grado, s.seccion, COALESCE(s.categoria, 'Clases') AS categoria,
               s.titulo_tema, s.proposito, s.peso_clase, s.archivada,
               COALESCE(s.tipo_instrumento, 'Normal') AS tipo_instrumento, s.fecha
        FROM Sesiones_Clase s
        JOIN Competencias c ON s.competencia_id = c.id
        WHERE s.curso_id = ? AND s.grado = ? AND s.seccion = ?
    """
    params: List[Any] = [curso_id, grado, seccion]
    if competencia_id is not None:
        query += " AND s.competencia_id = ?"
        params.append(competencia_id)
    if categoria and categoria != "Todas":
        query += " AND COALESCE(s.categoria, 'Clases') = ?"
        params.append(categoria)
    query += " ORDER BY s.id ASC"

    with obtener_conexion(db_path) as conn:
        conn.row_factory = sqlite3.Row
        sesiones = [dict(r) for r in conn.execute(query, params).fetchall()]
        by_id={s['id']:s for s in sesiones}
        for s in sesiones:s['capacidades']=[]
        caps=conn.execute(f"""SELECT sc.sesion_id,sc.capacidad_id,cap.nombre AS capacidad_nombre,sc.criterio_precisado
            FROM Sesion_Capacidades sc JOIN Capacidades cap ON cap.id=sc.capacidad_id
            JOIN ({query}) selected ON selected.id=sc.sesion_id ORDER BY sc.sesion_id,sc.capacidad_id""",params).fetchall()
        for row in caps:
            value=dict(row);session=value.pop('sesion_id');by_id[session]['capacidades'].append(value)
        return sesiones


@atomic
def guardar_calificaciones_y_asistencia_sesion(
    sesion_id: int,
    datos_estudiantes: List[Dict[str, Any]],
    db_path: Path = DB_PATH,
    nuevo_peso: Optional[float] = None,
    nuevo_instrumento=None,
    regla_cotejo=None,
) -> None:
    with obtener_conexion(db_path) as conn:
        cur = conn.cursor()
        if nuevo_peso is not None:
            actualizar_peso_actividad(sesion_id, nuevo_peso, db_path)
        if nuevo_instrumento is not None:
            from instrumentos import instrument_kind
            kind='Normal' if nuevo_instrumento=='Nota directa' else instrument_kind(nuevo_instrumento)
            cur.execute('UPDATE Sesiones_Clase SET tipo_instrumento=? WHERE id=?',(kind,sesion_id))
            if kind!='Lista de Cotejo':cur.execute('UPDATE Sesiones_Clase SET cotejo_regla=NULL,cotejo_pendiente=0 WHERE id=?',(sesion_id,))
        session = cur.execute("SELECT grado, seccion FROM Sesiones_Clase WHERE id=?", (sesion_id,)).fetchone()
        if not session:
            raise ValueError("La sesión no existe.")
        allowed = {r[0] for r in cur.execute("SELECT capacidad_id FROM Sesion_Capacidades WHERE sesion_id=?", (sesion_id,))}
        for item in datos_estudiantes:
            est_id = item["estudiante_id"]
            if not cur.execute("SELECT 1 FROM Estudiantes WHERE ID=? AND Grado=? AND Seccion=? AND nivel=(SELECT nivel FROM Sesiones_Clase WHERE id=?)", (est_id, *session, sesion_id)).fetchone():
                raise ValueError("El estudiante no pertenece al salón de la sesión.")
            asistio = 1 if item.get("asistio", True) else 0
            comentario = item.get("comentario", "").strip()

            if not item.get("preservar_asistencia",False):
                cur.execute(
                    """
                    INSERT INTO Asistencia_Y_Comentarios_Clase (sesion_id, estudiante_id, asistio, comentario)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(sesion_id, estudiante_id)
                    DO UPDATE SET asistio = excluded.asistio, comentario = excluded.comentario
                    """,
                    (sesion_id, est_id, asistio, comentario),
                )

            elif "comentario" in item and not item.get("preservar_comentario",False):
                cur.execute("""INSERT INTO Asistencia_Y_Comentarios_Clase(sesion_id,estudiante_id,asistio,comentario)
                    VALUES(?,?,1,?) ON CONFLICT(sesion_id,estudiante_id) DO UPDATE SET comentario=excluded.comentario""",(sesion_id,est_id,comentario))

            notas_cap: Dict[int, Optional[float]] = item.get("notas_por_capacidad", {})
            for cap_id, nota_val in notas_cap.items():
                if cap_id not in allowed:
                    raise ValueError("La capacidad no está incluida en la sesión.")
                if nota_val is not None:
                    nota_val = valid_number(nota_val)
                cur.execute(
                    """
                    INSERT INTO Notas_Sesion_Capacidad (sesion_id, capacidad_id, estudiante_id, nota)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(sesion_id, capacidad_id, estudiante_id)
                    DO UPDATE SET nota = excluded.nota
                    """,
                    (sesion_id, cap_id, est_id, nota_val),
                )
        answers=[dict(estudiante_id=item['estudiante_id'],indicador_id=int(identity),respuesta=value)
                 for item in datos_estudiantes for identity,value in item.get('respuestas_instrumento',{}).items()]
        if answers:
            from evaluacion_datos import save_answers
            save_answers(sesion_id,answers,db_path)
            cur.execute("UPDATE Sesiones_Clase SET cotejo_pendiente=1 WHERE id=? AND cotejo_regla IS NOT NULL AND tipo_instrumento='Lista de Cotejo'",(sesion_id,))
        if regla_cotejo is not None:
            from cotejo import store_rule
            store_rule(sesion_id,regla_cotejo,db_path)
        conn.commit()


def obtener_estado_planilla_sesion(
    sesion_id: int,
    grado: str,
    seccion: str,
    orden_por: str = "Apellidos (A-Z)",
    db_path: Path = DB_PATH,
) -> Tuple[List[Dict[str, Any]], Dict[int, Tuple[int, str]], Dict[Tuple[int, int], float]]:
    estudiantes = obtener_estudiantes_filtrados(
        grado, seccion, "", incluir_retirados=False, orden_por=orden_por, db_path=db_path
    )
    with obtener_conexion(db_path) as conn:
        asist_rows = conn.execute(
            "SELECT estudiante_id, asistio, comentario FROM Asistencia_Y_Comentarios_Clase WHERE sesion_id = ?",
            (sesion_id,),
        ).fetchall()
        asist_map = {r[0]: (int(r[1]), r[2] or "") for r in asist_rows}

        notas_rows = conn.execute(
            "SELECT estudiante_id, capacidad_id, nota FROM Notas_Sesion_Capacidad WHERE sesion_id = ?",
            (sesion_id,),
        ).fetchall()
        notas_map = {(r[0], r[1]): float(r[2]) for r in notas_rows if r[2] is not None}

    return estudiantes, asist_map, notas_map


# ==============================================================================
# BUSCADOR GENERAL SIN PROMEDIAR: MUESTRA LAS NOTAS PUESTAS EN CADA CLASE/ACTIVIDAD
# ==============================================================================


def obtener_tabla_notas_por_cada_clase_sin_promediar(
    curso_id: int,
    grado: str,
    seccion: str,
    busqueda_alumno: str = "",
    competencia_id_filtro: Optional[int] = None,
    categoria_filtro: str = "Todas",
    orden_por: str = "Apellidos (A-Z)",
    db_path: Path = DB_PATH,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Retorna `(lista_clases_columnas, filas_estudiantes_con_notas_de_cada_clase)`:
    - NO promedia las clases entre sí: crea una columna por cada Clase, Examen, Trabajo o Práctica
      para que el docente vea exactamente qué nota se puso en cada una de las clases y en cada capacidad.
    """
    sesiones = obtener_sesiones_clase(
        curso_id,
        grado if grado != "Todos" else "4°",
        seccion if seccion != "Todas" else "A",
        competencia_id_filtro,
        categoria_filtro,
        db_path,
    )
    if grado == "Todos" or seccion == "Todas":
        with obtener_conexion(db_path) as conn:
            conn.row_factory = sqlite3.Row
            q = """
                SELECT s.id, s.curso_id, s.competencia_id, c.nombre AS competencia_nombre,
                       s.grado, s.seccion, COALESCE(s.categoria, 'Clases') AS categoria,
                       s.titulo_tema, s.proposito, s.peso_clase, s.fecha
                FROM Sesiones_Clase s
                JOIN Competencias c ON s.competencia_id = c.id
                WHERE s.curso_id = ?
            """
            p: List[Any] = [curso_id]
            if competencia_id_filtro is not None:
                q += " AND s.competencia_id = ?"
                p.append(competencia_id_filtro)
            if categoria_filtro and categoria_filtro != "Todas":
                q += " AND COALESCE(s.categoria, 'Clases') = ?"
                p.append(categoria_filtro)
            q += " ORDER BY s.id ASC"
            sesiones = [dict(r) for r in conn.execute(q, p).fetchall()]

    estudiantes = obtener_estudiantes_filtrados(grado, seccion, busqueda_alumno, incluir_retirados=True, db_path=db_path)

    with obtener_conexion(db_path) as conn:
        # Traer todas las notas individuales puestas en cada clase y capacidad
        notas_raw = conn.execute(
            """
            SELECT nsc.sesion_id, nsc.estudiante_id, nsc.capacidad_id, cap.nombre, nsc.nota
            FROM Notas_Sesion_Capacidad nsc
            JOIN Capacidades cap ON nsc.capacidad_id = cap.id
            WHERE nsc.nota IS NOT NULL
            ORDER BY nsc.capacidad_id ASC
            """
        ).fetchall()

        # Mapa `(sesion_id, estudiante_id) -> lista de (nombre_cap, nota)`
        mapa_notas_sesion: Dict[Tuple[int, int], List[Tuple[str, float]]] = {}
        for sid, eid, _cap_id, cap_nom, n_val in notas_raw:
            mapa_notas_sesion.setdefault((int(sid), int(eid)), []).append((str(cap_nom), float(n_val)))

        asist_raw = conn.execute(
            "SELECT sesion_id, estudiante_id, asistio, comentario FROM Asistencia_Y_Comentarios_Clase"
        ).fetchall()
        mapa_asist_com: Dict[Tuple[int, int], Tuple[int, str]] = {
            (int(r[0]), int(r[1])): (int(r[2]), str(r[3] or "")) for r in asist_raw
        }

    filas_resultado: List[Dict[str, Any]] = []
    for est in estudiantes:
        eid = est["ID"]
        notas_por_sesion_texto: Dict[int, str] = {}
        todas_notas_alumno: List[float] = []
        comentarios_alumno: List[str] = []

        for idx_s, s in enumerate(sesiones, start=1):
            sid = s["id"]
            lista_n = mapa_notas_sesion.get((sid, eid), [])
            asist_info = mapa_asist_com.get((sid, eid))
            asist_marca = ""
            if asist_info and asist_info[0] == 0:
                asist_marca = " [Faltó]"
            if asist_info and asist_info[1]:
                comentarios_alumno.append(f"[{s['titulo_tema']}]: {asist_info[1]}")

            if lista_n:
                # Mostrar exactamente cada nota colocada en esa clase sin ocultarlas: ej. "16 | 18"
                str_notas = " / ".join(
                    f"C.{i+1}:{val:.1f}".rstrip("0").rstrip(".") for i, (_cn, val) in enumerate(lista_n)
                )
                notas_por_sesion_texto[sid] = f"{str_notas}{asist_marca}"
                todas_notas_alumno.extend(val for _cn, val in lista_n)
            else:
                notas_por_sesion_texto[sid] = f"S/N{asist_marca}"

        nota_orden_ref = max(todas_notas_alumno) if todas_notas_alumno else -1.0

        filas_resultado.append(
            {
                "estudiante_id": eid,
                "codigo_unico": est["Codigo_Unico"],
                "apellidos": est["Apellidos"],
                "nombres": est["Nombres"],
                "salon": f"{est['Grado']}{est['Seccion']}",
                "grado": est["Grado"],
                "seccion": est["Seccion"],
                "estado": est["Estado"],
                "notas_por_sesion": notas_por_sesion_texto,
                "nota_orden_ref": nota_orden_ref,
                "comentarios_concat": "  |  ".join(comentarios_alumno),
            }
        )

    if orden_por == "Apellidos (Z-A)":
        filas_resultado.sort(key=lambda x: (x["apellidos"].lower(), x["nombres"].lower()), reverse=True)
    elif orden_por == "Notas (Mayor a Menor)":
        filas_resultado.sort(key=lambda x: (x["nota_orden_ref"], x["apellidos"].lower()), reverse=True)
    elif orden_por == "Notas (Menor a Mayor)":
        filas_resultado.sort(
            key=lambda x: (999.0 if x["nota_orden_ref"] < 0 else x["nota_orden_ref"], x["apellidos"].lower())
        )
    elif orden_por == "Código (Ej. 4A01)":
        filas_resultado.sort(key=lambda x: x["codigo_unico"])
    elif orden_por == "Sección y Código":
        filas_resultado.sort(key=lambda x: (x["grado"], x["seccion"], x["codigo_unico"]))
    else:
        filas_resultado.sort(key=lambda x: (x["apellidos"].lower(), x["nombres"].lower()))

    return sesiones, filas_resultado


# ==============================================================================
# PORCENTAJES POR RUBRO Y ESTADÍSTICAS DE FRECUENCIA
# ==============================================================================


def obtener_pesos_rubros_curso(curso_id: int, db_path: Path = DB_PATH) -> Dict[str, float]:
    with obtener_conexion(db_path) as conn:
        row = conn.execute(
            "SELECT pct_clases, pct_examenes, pct_trabajos, pct_practicas FROM Pesos_Rubros_Curso WHERE curso_id = ?",
            (curso_id,),
        ).fetchone()
        if not row:
            return {"Clases": 40.0, "Exámenes": 25.0, "Trabajos": 20.0, "Prácticas / Otros": 15.0}
        return {
            "Clases": float(row[0]),
            "Exámenes": float(row[1]),
            "Trabajos": float(row[2]),
            "Prácticas / Otros": float(row[3]),
        }


def guardar_pesos_rubros_curso(
    curso_id: int,
    pct_clases: float,
    pct_examenes: float,
    pct_trabajos: float,
    pct_practicas: float,
    db_path: Path = DB_PATH,
) -> None:
    percentages = [valid_number(v, 0, 100, "Porcentaje") for v in (pct_clases, pct_examenes, pct_trabajos, pct_practicas)]
    if abs(sum(percentages) - 100) > 0.000001:
        raise ValueError("Los porcentajes deben sumar 100%.")
    with obtener_conexion(db_path) as conn:
        conn.execute(
            """
            INSERT INTO Pesos_Rubros_Curso (curso_id, pct_clases, pct_examenes, pct_trabajos, pct_practicas)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(curso_id)
            DO UPDATE SET
                pct_clases = excluded.pct_clases,
                pct_examenes = excluded.pct_examenes,
                pct_trabajos = excluded.pct_trabajos,
                pct_practicas = excluded.pct_practicas
            """,
            (curso_id, float(pct_clases), float(pct_examenes), float(pct_trabajos), float(pct_practicas)),
        )
        conn.commit()


def obtener_estadisticas_frecuencia_evaluacion(
    curso_id: int, grado: str, seccion: str, db_path: Path = DB_PATH
) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int, int]]]:
    competencias = obtener_competencias_por_curso(curso_id, db_path)
    freq_comp: Dict[int, int] = {cid: 0 for cid, _ in competencias}
    nombres_comp: Dict[int, str] = {cid: nom for cid, nom in competencias}

    freq_cap: Dict[int, int] = {}
    nombres_cap: Dict[int, str] = {}
    for idx_c, (cid, _) in enumerate(competencias, start=1):
        for idx_cap, (cap_id, cap_nom) in enumerate(obtener_capacidades_por_competencia(cid, db_path), start=1):
            freq_cap[cap_id] = 0
            nombres_cap[cap_id] = (f"Cap{idx_cap}: {cap_nom}", idx_c)

    with obtener_conexion(db_path) as conn:
        for (cid,) in conn.execute(
            "SELECT competencia_id FROM Sesiones_Clase WHERE curso_id = ? AND grado = ? AND seccion = ?",
            (curso_id, grado, seccion),
        ).fetchall():
            if cid in freq_comp:
                freq_comp[cid] += 1

        for (cap_id,) in conn.execute(
            """
            SELECT sc.capacidad_id
            FROM Sesion_Capacidades sc
            JOIN Sesiones_Clase s ON sc.sesion_id = s.id
            WHERE s.curso_id = ? AND s.grado = ? AND s.seccion = ?
            """,
            (curso_id, grado, seccion),
        ).fetchall():
            if cap_id in freq_cap:
                freq_cap[cap_id] += 1

    lista_comp = [(f"C{i+1}: {nombres_comp[cid]}", freq_comp[cid]) for i, (cid, _) in enumerate(competencias)]
    lista_cap = [(nombres_cap[cap_id][0], cuenta, nombres_cap[cap_id][1]) for cap_id, cuenta in freq_cap.items()]
    return lista_comp, lista_cap


# ==============================================================================
# MATRIZ DETALLADA DE COMPETENCIAS Y CAPACIDADES + EXPORTACIÓN / IMPORTACIÓN EXCEL
# ==============================================================================


def guardar_nota_manual_capacidad(
    estudiante_id: int, capacidad_id: int, nota_manual: Optional[float], db_path: Path = DB_PATH
) -> None:
    if nota_manual is not None:
        nota_manual = valid_number(nota_manual)
    with obtener_conexion(db_path) as conn:
        conn.execute(
            """
            INSERT INTO Notas_Manuales_Capacidad (estudiante_id, capacidad_id, nota_manual)
            VALUES (?, ?, ?)
            ON CONFLICT(estudiante_id, capacidad_id)
            DO UPDATE SET nota_manual = excluded.nota_manual
            """,
            (estudiante_id, capacidad_id, nota_manual),
        )
        conn.commit()


def calcular_matriz_competencias_y_capacidades(
    curso_id: int,
    grado: str,
    seccion: str,
    db_path: Path = DB_PATH,
    orden_por: str = "Apellidos (A-Z)",
    incluir_retirados: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    pesos_rubros = obtener_pesos_rubros_curso(curso_id, db_path)
    competencias_raw = obtener_competencias_por_curso(curso_id, db_path)
    estructura_comp: List[Dict[str, Any]] = []
    for idx_c, (cid, cnom) in enumerate(competencias_raw, start=1):
        caps = obtener_capacidades_por_competencia(cid, db_path)
        estructura_comp.append(
            {
                "indice": idx_c,
                "competencia_id": cid,
                "competencia_nombre": cnom,
                "capacidades": [
                    {"indice_cap": idx_cap, "capacidad_id": cap_id, "capacidad_nombre": cap_nom}
                    for idx_cap, (cap_id, cap_nom) in enumerate(caps, start=1)
                ],
            }
        )

    estudiantes = obtener_estudiantes_filtrados(
        grado, seccion, "", incluir_retirados=incluir_retirados, orden_por=orden_por, db_path=db_path
    )

    with obtener_conexion(db_path) as conn:
        filas_notas = conn.execute(
            """
            SELECT nsc.estudiante_id, nsc.capacidad_id, nsc.nota, s.peso_clase, COALESCE(s.categoria, 'Clases') AS categoria
            FROM Notas_Sesion_Capacidad nsc
            JOIN Sesiones_Clase s ON nsc.sesion_id = s.id
            WHERE s.curso_id = ? AND s.grado = ? AND s.seccion = ? AND nsc.nota IS NOT NULL
            """,
            (curso_id, grado, seccion),
        ).fetchall()

        notas_por_cat_cap: Dict[Tuple[int, int, str], List[Tuple[float, float]]] = {}
        for est_id, cap_id, nota, peso, cat in filas_notas:
            notas_por_cat_cap.setdefault((est_id, int(cap_id), cat), []).append(
                (float(nota), float(peso if peso > 0 else 1.0))
            )

        manuales_rows = conn.execute(
            "SELECT estudiante_id, capacidad_id, nota_manual FROM Notas_Manuales_Capacidad WHERE nota_manual IS NOT NULL"
        ).fetchall()
        manuales_map: Dict[Tuple[int, int], float] = {(r[0], r[1]): float(r[2]) for r in manuales_rows}

    def _prom_lista(pares: List[Tuple[float, float]]) -> Optional[float]:
        from calculos import weighted_average
        return weighted_average(pares)

    filas_matriz: List[Dict[str, Any]] = []
    for est in estudiantes:
        est_id = est["ID"]
        notas_capacidad: Dict[int, Optional[float]] = {}
        es_manual_cap: Dict[int, bool] = {}
        notas_competencia: Dict[int, Optional[float]] = {}
        faltan_capacidades = 0

        from calculos import rounded,weighted_average
        for comp in estructura_comp:
            cid = comp["competencia_id"]
            valores_caps_de_comp: List[float] = []

            for cap in comp["capacidades"]:
                cap_id = cap["capacidad_id"]
                if (est_id, cap_id) in manuales_map:
                    val_man = rounded(manuales_map[(est_id, cap_id)])
                    notas_capacidad[cap_id] = val_man
                    es_manual_cap[cap_id] = True
                    valores_caps_de_comp.append(val_man)
                    continue

                es_manual_cap[cap_id] = False
                rubric_averages=[]

                for rubro_key in ("Clases", "Exámenes", "Trabajos", "Prácticas / Otros"):
                    prom_r = _prom_lista(notas_por_cat_cap.get((est_id, cap_id, rubro_key), []))
                    if prom_r is not None:
                        pct = float(pesos_rubros.get(rubro_key, 0.0))
                        if pct > 0:
                            rubric_averages.append((prom_r,pct))

                nota_final_cap=weighted_average(rubric_averages)
                if nota_final_cap is not None:
                    notas_capacidad[cap_id] = nota_final_cap
                    valores_caps_de_comp.append(nota_final_cap)
                else:
                    notas_capacidad[cap_id] = None
                    faltan_capacidades += 1

            if valores_caps_de_comp:
                notas_competencia[cid] = weighted_average([(v,1) for v in valores_caps_de_comp])
            else:
                notas_competencia[cid] = None

        vals_comp_validos = [v for v in notas_competencia.values() if v is not None]
        promedio_general = (
            weighted_average([(v,1) for v in vals_comp_validos])
        )

        filas_matriz.append(
            {
                "estudiante_id": est_id,
                "codigo_unico": est["Codigo_Unico"],
                "apellidos": est["Apellidos"],
                "nombres": est["Nombres"],
                "grado": est["Grado"],
                "seccion": est["Seccion"],
                "estado": est["Estado"],
                "notas_capacidad": notas_capacidad,
                "es_manual_cap": es_manual_cap,
                "notas_competencia": notas_competencia,
                "promedio_general": promedio_general,
                "literal_general": nota_a_literal(promedio_general,db_path),
                "faltan_capacidades": faltan_capacidades,
            }
        )

    if orden_por == "Notas (Mayor a Menor)":
        filas_matriz.sort(key=lambda x: (x["promedio_general"] if x["promedio_general"] is not None else -1.0), reverse=True)
    elif orden_por == "Notas (Menor a Mayor)":
        filas_matriz.sort(key=lambda x: (x["promedio_general"] if x["promedio_general"] is not None else 999.0))

    return estructura_comp, filas_matriz


def exportar_matriz_completa_excel(
    ruta_destino: str,
    nombre_curso: str,
    grado: str,
    seccion: str,
    estructura_comp: List[Dict[str, Any]],
    filas_matriz: List[Dict[str, Any]],
) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Registro_{grado}_{seccion}"
    ws.views.sheetView[0].showGridLines = True

    temas_colores = [
        {"header": "1E3A8A", "cap_head": "2563EB", "cap_cell": "EFF6FF", "prom_head": "1D4ED8", "prom_cell": "DBEAFE"},
        {"header": "065F46", "cap_head": "059669", "cap_cell": "ECFDF5", "prom_head": "047857", "prom_cell": "D1FAE5"},
        {"header": "92400E", "cap_head": "D97706", "cap_cell": "FFFBEB", "prom_head": "B45309", "prom_cell": "FEF3C7"},
        {"header": "4C1D95", "cap_head": "7C3AED", "cap_cell": "F5F3FF", "prom_head": "6D28D9", "prom_cell": "EDE9FE"},
    ]

    side_thin = Side(style="thin", color="475569")
    side_medium = Side(style="medium", color="0F172A")

    borde_celda = Border(left=side_thin, right=side_thin, top=side_thin, bottom=side_thin)
    borde_cierre_bloque = Border(left=side_thin, right=side_medium, top=side_thin, bottom=side_thin)
    borde_header_cierre = Border(left=side_thin, right=side_medium, top=side_medium, bottom=side_medium)
    borde_header_normal = Border(left=side_thin, right=side_thin, top=side_medium, bottom=side_medium)

    headers_f2 = ["Código", "Apellidos", "Nombres", "Grado", "Sección", "Estado"]
    headers_f3 = ["Código", "Apellidos", "Nombres", "Grado", "Sección", "Estado"]

    col_cursor = 7
    rangos_merge_f2: List[Tuple[int, int, str, Dict[str, str]]] = []
    meta_columnas: List[Dict[str, Any]] = []

    for idx_t, comp in enumerate(estructura_comp):
        tema = temas_colores[idx_t % len(temas_colores)]
        caps = comp["capacidades"]
        inicio_col = col_cursor
        for cap in caps:
            headers_f2.append("")
            headers_f3.append(
                f"C{comp['indice']}.Cap{cap['indice_cap']}:\n{cap['capacidad_nombre']}\n[CAP_ID:{cap['capacidad_id']}]"
            )
            meta_columnas.append({"tipo": "cap", "cap_id": cap["capacidad_id"], "tema": tema, "cierre": False})
            col_cursor += 1

        headers_f2.append("")
        headers_f3.append(f"PROMEDIO\nCOMPETENCIA {comp['indice']}")
        meta_columnas.append({"tipo": "prom_comp", "comp_id": comp["competencia_id"], "tema": tema, "cierre": True})
        fin_col = col_cursor
        col_cursor += 1
        rangos_merge_f2.append(
            (inicio_col, fin_col, f"COMPETENCIA {comp['indice']}: {comp['competencia_nombre'].upper()}", tema)
        )

    headers_f2.extend(["PROMEDIO FINAL", "NIVEL DE LOGRO"])
    headers_f3.extend(["PROMEDIO FINAL", "NIVEL DE LOGRO"])

    total_cols = len(headers_f3)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
    c_tit = ws.cell(
        row=1,
        column=1,
        value=f"REGISTRO OFICIAL DETALLADO POR COMPETENCIAS Y CAPACIDADES - {nombre_curso.upper()} ({grado} '{seccion}')",
    )
    c_tit.font = Font(size=13, bold=True, color="FFFFFF")
    c_tit.fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    c_tit.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.append(headers_f2)
    ws.append(headers_f3)

    fill_datos_est = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    for c_idx in range(1, 7):
        ws.merge_cells(start_row=2, start_column=c_idx, end_row=3, end_column=c_idx)
        for r_idx in (2, 3):
            cel = ws.cell(row=r_idx, column=c_idx)
            cel.fill = fill_datos_est
            cel.font = Font(color="FFFFFF", bold=True, size=10)
            cel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cel.border = borde_header_cierre if c_idx == 6 else borde_header_normal

    for ini_c, fin_c, texto_comp, tema in rangos_merge_f2:
        ws.merge_cells(start_row=2, start_column=ini_c, end_row=2, end_column=fin_c)
        for col_i in range(ini_c, fin_c + 1):
            cel2 = ws.cell(row=2, column=col_i)
            cel2.fill = PatternFill(start_color=tema["header"], end_color=tema["header"], fill_type="solid")
            cel2.font = Font(color="FFFFFF", bold=True, size=10)
            cel2.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cel2.border = borde_header_cierre if col_i == fin_c else borde_header_normal
        ws.cell(row=2, column=ini_c, value=texto_comp)

    for offset, meta in enumerate(meta_columnas):
        col_i = 7 + offset
        tema = meta["tema"]
        color_h3 = tema["prom_head"] if meta["tipo"] == "prom_comp" else tema["cap_head"]
        cel3 = ws.cell(row=3, column=col_i)
        cel3.fill = PatternFill(start_color=color_h3, end_color=color_h3, fill_type="solid")
        cel3.font = Font(color="FFFFFF", bold=True, size=9)
        cel3.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cel3.border = borde_header_cierre if meta["cierre"] else borde_header_normal

    fill_final = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    for c_idx in (total_cols - 1, total_cols):
        ws.merge_cells(start_row=2, start_column=c_idx, end_row=3, end_column=c_idx)
        for r_idx in (2, 3):
            cel = ws.cell(row=r_idx, column=c_idx)
            cel.fill = fill_final
            cel.font = Font(color="FFFFFF", bold=True, size=10)
            cel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cel.border = borde_header_cierre

    ws.row_dimensions[2].height = 28
    ws.row_dimensions[3].height = 54

    fill_falta = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    font_falta = Font(color="991B1B", bold=True, size=9)

    for idx_f, fila in enumerate(filas_matriz, start=4):
        row_vals: List[Any] = [
            fila["codigo_unico"],
            fila["apellidos"],
            fila["nombres"],
            fila["grado"],
            fila["seccion"],
            fila["estado"],
        ]
        from calculos import rounded,weighted_average
        for comp in estructura_comp:
            cid = comp["competencia_id"]
            for cap in comp["capacidades"]:
                cap_id = cap["capacidad_id"]
                val_cap = fila["notas_capacidad"].get(cap_id)
                row_vals.append(val_cap if val_cap is not None else "FALTA")
            val_comp = fila["notas_competencia"].get(cid)
            row_vals.append(val_comp if val_comp is not None else "-")

        row_vals.extend(
            [
                fila["promedio_general"] if fila["promedio_general"] is not None else "-",
                fila["literal_general"],
            ]
        )
        ws.append(row_vals)
        ws.row_dimensions[idx_f].height = 22

        for col_i in range(1, 7):
            c = ws.cell(row=idx_f, column=col_i)
            c.border = borde_cierre_bloque if col_i == 6 else borde_celda
            c.alignment = Alignment(horizontal="left" if col_i in (2, 3) else "center", vertical="center")
            if col_i == 1:
                c.font = Font(bold=True, color="1E293B")

        for offset, meta in enumerate(meta_columnas):
            col_i = 7 + offset
            c = ws.cell(row=idx_f, column=col_i)
            tema = meta["tema"]
            c.border = borde_cierre_bloque if meta["cierre"] else borde_celda
            c.alignment = Alignment(horizontal="center", vertical="center")
            if str(c.value) == "FALTA":
                c.fill = fill_falta
                c.font = font_falta
            elif meta["tipo"] == "prom_comp":
                c.fill = PatternFill(start_color=tema["prom_cell"], end_color=tema["prom_cell"], fill_type="solid")
                c.font = Font(bold=True, color="0F172A")
            else:
                c.fill = PatternFill(start_color=tema["cap_cell"], end_color=tema["cap_cell"], fill_type="solid")

        for col_i in (total_cols - 1, total_cols):
            c = ws.cell(row=idx_f, column=col_i)
            c.border = borde_cierre_bloque
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.font = Font(bold=True, color="0F172A")
            c.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 9
    ws.column_dimensions["E"].width = 9
    ws.column_dimensions["F"].width = 12
    for col_i in range(7, total_cols + 1):
        letra = openpyxl.utils.get_column_letter(col_i)
        ws.column_dimensions[letra].width = 18

    wb.save(ruta_destino)


@atomic
def importar_matriz_notas_desde_excel(
    ruta_archivo: str, grado_def: str = "3°", seccion_def: str = "A", db_path: Path = DB_PATH
) -> Tuple[int, int]:
    wb = openpyxl.load_workbook(ruta_archivo, data_only=True)
    ws = wb.active
    filas = list(ws.iter_rows(values_only=True))
    if len(filas) < 3:
        raise ValueError("La matriz no contiene encabezados y datos.")

    fila_header_idx = 2
    for r_idx in range(min(5, len(filas))):
        texto_fila = " ".join(str(c or "") for c in filas[r_idx])
        if "[CAP_ID:" in texto_fila:
            fila_header_idx = r_idx
            break

    encabezados = [str(c or "").strip() for c in filas[fila_header_idx]]
    mapa_col_cap: Dict[int, int] = {}
    for col_i, texto_h in enumerate(encabezados):
        if "[CAP_ID:" in texto_h:
            try:
                parte = texto_h.split("[CAP_ID:")[1].split("]")[0].strip()
                mapa_col_cap[col_i] = int(parte)
            except (ValueError, IndexError) as exc:
                raise ValueError(f"Encabezado de capacidad inválido en columna {col_i+1}.") from exc

    if not mapa_col_cap:
        raise ValueError("No hay columnas [CAP_ID:...] en la matriz. Use la plantilla exportada.")
    est_procesados = 0
    notas_cargadas = 0

    with obtener_conexion(db_path) as conn:
        cur = conn.cursor()
        allowed = {r[0] for r in conn.execute("SELECT a.id FROM Capacidades a JOIN Competencias c ON c.id=a.competencia_id JOIN Cursos u ON u.id=c.curso_id WHERE u.nivel=(SELECT nivel_educativo FROM Docente_Config WHERE id=1)")}
        if not set(mapa_col_cap.values()) <= allowed:
            raise ValueError("La matriz contiene capacidades que no pertenecen al nivel activo.")
        for row_number, fila in enumerate(filas[fila_header_idx + 1 :], fila_header_idx + 2):
            if not fila or all(c is None or str(c).strip() == "" for c in fila):
                continue

            if len(fila) < 6:
                raise ValueError("La matriz necesita las seis columnas de identificación.")
            codigo = str(fila[0] or "").strip()
            apellidos = str(fila[1] or "").strip()
            nombres = str(fila[2] or "").strip()
            grado = str(fila[3] or grado_def).strip()
            seccion = str(fila[4] or seccion_def).strip().upper()
            estado = str(fila[5] or "ACTIVO").strip().upper()

            if not apellidos and not nombres:
                continue

            row_est = None
            if codigo:
                row_est = cur.execute(
                    "SELECT ID FROM Estudiantes WHERE Codigo_Unico = ? AND nivel=(SELECT nivel_educativo FROM Docente_Config WHERE id=1)", (codigo,)
                ).fetchone()
            if row_est:
                identity = cur.execute("SELECT Apellidos, Nombres, Grado, Seccion FROM Estudiantes WHERE ID=?", (row_est[0],)).fetchone()
                if tuple(identity) != (apellidos, nombres, grado, seccion):
                    raise ValueError(f"Fila {row_number}: el código no coincide con el estudiante y salón. Exporte una matriz actualizada.")
            if not row_est:
                row_est = cur.execute(
                    "SELECT ID FROM Estudiantes WHERE Apellidos = ? AND Nombres = ? AND Grado = ? AND Seccion = ? AND nivel=(SELECT nivel_educativo FROM Docente_Config WHERE id=1)",
                    (apellidos, nombres, grado, seccion),
                ).fetchone()

            if row_est:
                est_id = int(row_est[0])
                cur.execute(
                    "UPDATE Estudiantes SET Apellidos = ?, Nombres = ?, Grado = ?, Seccion = ?, Estado = ? WHERE ID = ?",
                    (apellidos, nombres, grado, seccion, estado, est_id),
                )
            else:
                cur.execute(
                    "INSERT INTO Estudiantes (Nombres, Apellidos, Grado, Seccion, Estado,nivel) VALUES (?, ?, ?, ?, ?,(SELECT nivel_educativo FROM Docente_Config WHERE id=1))",
                    (nombres, apellidos, grado, seccion, estado),
                )
                est_id = cur.lastrowid

            est_procesados += 1

            for col_i, cap_id in mapa_col_cap.items():
                if col_i < len(fila):
                    celda_val = fila[col_i]
                    if celda_val is not None and str(celda_val).strip() not in ("", "-", "FALTA", "⚠️ FALTA"):
                        try:
                            nota_f = valid_number(str(celda_val).replace("✎", "").strip())
                            if 0.0 <= nota_f <= 20.0:
                                cur.execute(
                                    """
                                    INSERT INTO Notas_Manuales_Capacidad (estudiante_id, capacidad_id, nota_manual)
                                    VALUES (?, ?, ?)
                                    ON CONFLICT(estudiante_id, capacidad_id)
                                    DO UPDATE SET nota_manual = excluded.nota_manual
                                    """,
                                    (est_id, cap_id, nota_f),
                                )
                                notas_cargadas += 1
                        except ValueError as exc:
                            raise ValueError(f"Fila {row_number}, columna {col_i+1}: {exc}") from exc

        conn.commit()

    sincronizar_codigos_por_seccion(db_path)
    return est_procesados, notas_cargadas

def obtener_historial_vertical_estudiantes(
    curso_id: int,
    grado: str,
    seccion: str,
    busqueda_alumno: str = "",
    competencia_id_filtro: Optional[int] = None,
    categoria_filtro: str = "Todas",
    orden_por: str = "Apellidos (A-Z)",
    incluir_retirados: bool = True,
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    # Para la Pestaña 5: Diseño vertical
    estudiantes = obtener_estudiantes_filtrados(grado, seccion, busqueda_alumno, incluir_retirados=incluir_retirados, db_path=db_path)
    if orden_por == "Código (4A01...)":
        estudiantes.sort(key=lambda x: x["Codigo_Unico"])
    elif orden_por == "Nombres":
        estudiantes.sort(key=lambda x: x["Nombres"])
    else:
        estudiantes.sort(key=lambda x: x["Apellidos"])

    # Traer sesiones filtradas
    with obtener_conexion(db_path) as conn:
        conn.row_factory = sqlite3.Row
        q_s = '''SELECT s.id, s.titulo_tema, COALESCE(s.categoria, 'Clases') as categoria, s.fecha, c.nombre as comp_nom 
                 FROM Sesiones_Clase s
                 JOIN Competencias c ON s.competencia_id = c.id
                 WHERE s.curso_id = ?'''
        p_s: List[Any] = [curso_id]
        if grado != "Todos":
            q_s += " AND s.grado = ?"
            p_s.append(grado)
        if seccion != "Todas":
            q_s += " AND s.seccion = ?"
            p_s.append(seccion)
        if competencia_id_filtro:
            q_s += " AND s.competencia_id = ?"
            p_s.append(competencia_id_filtro)
        if categoria_filtro != "Todas":
            q_s += " AND COALESCE(s.categoria, 'Clases') = ?"
            p_s.append(categoria_filtro)
        q_s += " ORDER BY s.fecha ASC, s.id ASC"
        sesiones = [dict(r) for r in conn.execute(q_s, p_s).fetchall()]

        if not sesiones or not estudiantes:
            return []

        s_ids = [s["id"] for s in sesiones]
        e_ids = [e["ID"] for e in estudiantes]
        placeholders_s = ",".join("?" * len(s_ids))
        placeholders_e = ",".join("?" * len(e_ids))

        notas_raw = conn.execute(
            f'''SELECT nsc.sesion_id, nsc.estudiante_id, cap.id as capacidad_id, cap.nombre, nsc.nota
                FROM Notas_Sesion_Capacidad nsc
                JOIN Capacidades cap ON nsc.capacidad_id = cap.id
                WHERE nsc.sesion_id IN ({placeholders_s}) AND nsc.estudiante_id IN ({placeholders_e})''',
            (*s_ids, *e_ids)
        ).fetchall()

        asist_raw = conn.execute(
            f'''SELECT sesion_id, estudiante_id, comentario, asistio
                FROM Asistencia_Y_Comentarios_Clase
                WHERE sesion_id IN ({placeholders_s}) AND estudiante_id IN ({placeholders_e})''',
            (*s_ids, *e_ids)
        ).fetchall()

    notas_detalle = {}
    mapa_notas: Dict[int, Dict[int, List[str]]] = {}
    for r in notas_raw:
        sid, eid, cap_nom, nota = r["sesion_id"], r["estudiante_id"], r["nombre"], r["nota"]
        notas_detalle.setdefault((eid,sid), []).append({"id":r["capacidad_id"],"nombre":cap_nom,"nota":nota})
        if eid not in mapa_notas: mapa_notas[eid] = {}
        if sid not in mapa_notas[eid]: mapa_notas[eid][sid] = []
        mapa_notas[eid][sid].append(f"{cap_nom[:6]}: {nota if nota is not None else '--'}")

    mapa_coment: Dict[int, Dict[int, str]] = {}
    for r in asist_raw:
        sid, eid, com, asist = r["sesion_id"], r["estudiante_id"], r["comentario"], r["asistio"]
        if eid not in mapa_coment: mapa_coment[eid] = {}
        mapa_coment[eid][sid] = com or ""

    # Construir filas verticales
    filas = []
    for e in estudiantes:
        for s in sesiones:
            sid = s["id"]
            eid = e["ID"]
            notas_arr = mapa_notas.get(eid, {}).get(sid, [])
            coment = mapa_coment.get(eid, {}).get(sid, "")
            
            promedio = ""
            if notas_arr:
                from calculos import weighted_average
                values=[d['nota'] for d in notas_detalle.get((eid,sid),[]) if d['nota'] is not None]
                if values:promedio=f"{weighted_average([(v,1) for v in values]):.2f}"
            
            if True:
                filas.append({
                    "estudiante_id": eid,
                    "seccion": e["Seccion"],
                    "notas_detalle": notas_detalle.get((eid,sid),[]),
                    "sesion_id": sid,
                    "codigo": e["Codigo_Unico"],
                    "alumno_nombre": f"{e['Apellidos']}, {e['Nombres']}",
                    "fecha": s["fecha"],
                    "actividad": f"[{s['categoria']}] {s['titulo_tema']}",
                    "competencia": s["comp_nom"],
                    "notas_str": " | ".join(notas_arr) if notas_arr else "Sin Calificar",
                    "promedio": promedio,
                    "comentario": coment
                })
    return filas

def guardar_tamano_letra_preferido(tamano: str, db_path: Path = DB_PATH) -> None:
    with obtener_conexion(db_path) as conn:
        conn.execute("UPDATE Docente_Config SET tamano_letra = ? WHERE id = 1", (tamano,))
        conn.commit()


@atomic
def actualizar_pesos_actividades(pesos, db_path: Path = DB_PATH):
    for sid, value in pesos:
        actualizar_peso_actividad(sid, value, db_path)
