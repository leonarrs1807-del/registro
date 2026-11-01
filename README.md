# Registro Docente

Aplicación de escritorio para estudiantes, sesiones, rúbricas, asistencia y
evaluación por competencias. Funciona con Python 3.12, Tkinter y SQLite, sin
servidor ni conexión permanente a Internet.

## Ejecutar desde el código

En Windows, instale Python 3.12 con Tcl/Tk y ejecute en esta carpeta:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

En Linux use `python3 -m venv .venv`, `.venv/bin/python` y asegúrese de tener
Tcl/Tk y una sesión gráfica. Para pruebas sin pantalla puede utilizar Xvfb.

La primera ejecución solicita establecer una contraseña docente de al menos
8 caracteres. Las instalaciones antiguas conservan su usuario y contraseña;
las contraseñas se migran a PBKDF2 con sal aleatoria. Si todavía usan la clave
inicial, deberán cambiarla. Las siguientes ejecuciones empiezan con la edición
bloqueada: el botón de candado permite autenticarse. La administración de cursos
usa la misma contraseña docente, sin una clave de desarrollador incorporada.

## Datos, migración y respaldos

Los datos se guardan separados del programa:

| Sistema | Ubicación predeterminada |
| --- | --- |
| Windows | `%LOCALAPPDATA%\RegistroDocente` |
| Linux | `$XDG_DATA_HOME/registro-docente` o `~/.local/share/registro-docente` |
| macOS | `~/Library/Application Support/RegistroDocente` |

Al ejecutar desde este repositorio por primera vez, se copia la base antigua
`registro_evaluacion.db` a esa carpeta, sin modificar el original. Para migrar
una instalación ejecutable antigua, coloque su base junto al ejecutable antes
del primer arranque, o use **Datos y seguridad → Restaurar respaldo**. No se
incluye alumnado ni una base de datos personal dentro del ejecutable distribuido.
No se sobrescribe automáticamente una base de usuario que ya exista.

Se crean respaldos verificados antes de iniciar/migrar, importar, eliminar y
restaurar. También puede crear uno manualmente desde el menú. Los respaldos
quedan en `backups`, junto a la base activa. Antes de restaurar se verifica
integridad, tablas y relaciones; se conserva una copia del estado anterior.
La restauración reinicia la aplicación y vuelve a bloquear la edición.
Los respaldos no se borran automáticamente: revise periódicamente el espacio y
guarde copias externas, especialmente al cerrar cada periodo.

Para trabajar con datos de prueba sin tocar su perfil:

```powershell
$env:REGISTRO_DATA_DIR = 'C:\ruta\datos-de-prueba'
.venv\Scripts\python main.py
```

`REGISTRO_DB_PATH` permite seleccionar explícitamente otra base. El registro de
errores `registro.log` rota al alcanzar 1 MB y conserva tres archivos anteriores.
No registra contraseñas ni variables de entorno. El menú muestra las ubicaciones.

## Nuevas funciones y correcciones

- **Años y periodos:** el menú permite crear o abrir bases independientes por
  año y periodo 1–4. Un periodo nuevo copia currículo, alumnado y configuración,
  pero no actividades, notas ni historial. Se mantiene el periodo anterior.
  Los datos originales permanecen identificados como `registro_evaluacion` hasta
  que abra otro periodo; no se les asigna un año histórico inventado.
- **Historial:** registra altas, modificaciones y eliminaciones de notas,
  usuario docente configurado y fecha UTC. Permite revertir el último cambio de
  una nota si no existen cambios posteriores. Para recuperar estudiantes o
  sesiones eliminados use un respaldo completo. Las reversiones también quedan
  registradas. El historial comienza tras la migración; no reconstruye ediciones
  antiguas.
- **Importaciones Excel:** se ejecuta primero la importación sobre una copia.
  Si hay errores, se informa el dato o fila/columna y no se escribe en la base
  activa. Una vista previa permite revisar las primeras 150 filas de cada hoja;
  la validación procesa todas. Solo al confirmar se respalda e importa el mismo
  archivo validado. Los estudiantes duplicados se rechazan; la matriz permite
  actualizar notas y comprueba que código, nombre y salón coincidan.
- **Guardado completo:** pesos, notas y asistencia se guardan juntos. Si un dato
  falla, se revierte toda la operación. Las notas se validan también en SQLite;
  no se aceptan valores fuera de 0–20, infinitos o NaN en las funciones públicas.
  Los porcentajes deben ser no negativos y sumar 100%.
- **Evaluación masiva:** abre el editor de criterios y transfiere resultados a
  la planilla actual. Una rúbrica vacía no se convierte silenciosamente en cero.
  La rúbrica normaliza la suma por el máximo total de sus indicadores a una escala
  de 20; la lista de cotejo promedia los niveles seleccionados. Debe pulsar
  **Guardar** en la planilla para persistir los resultados.
- **Sesiones:** editar una sesión actualiza fecha, grado y sección. Se validan
  fechas reales y la pertenencia de capacidades al curso/competencia. Si ya tiene
  notas no se permite trasladar la sesión de salón o eliminar capacidades
  calificadas; cree otra sesión para preservar el registro anterior.
  También se corrigió la selección de competencias con prefijos como `2.`:
  ya no se sustituye silenciosamente por la primera competencia del curso.
- **Interfaz:** la preferencia del tamaño de letra se recupera al iniciar. Se
  advierte de cambios pendientes al cerrar o reemplazar el contexto/planilla.
  Los gráficos usan la misma clasificación literal que las tablas:
  C <10,5; B desde 10,5; A desde 13,5; AD desde 17,5.

La base SQLite y los respaldos no están cifrados. El candado evita modificaciones
accidentales dentro de la aplicación; no sustituye la seguridad de la cuenta del
sistema operativo ni hace inalterable una base a la que alguien tiene acceso
directo. Proteja los archivos de estudiantes y sus respaldos.

## Crear un ejecutable e instalador para Windows

La compilación se realiza **en Windows**; PyInstaller no genera ejecutables
Windows desde Linux:

```powershell
.venv\Scripts\python -m pip install -r requirements-build.txt
.venv\Scripts\python -m unittest discover -s tests -t . -v
.venv\Scripts\python -m PyInstaller --noconfirm RegistroDocente.spec
```

La aplicación queda en `dist\RegistroDocente\RegistroDocente.exe`. Distribuya
toda la carpeta, no solo el `.exe`. Para un instalador, instale Inno Setup 6 y
compile `installer\windows.iss`. Se crea
`dist\installer\RegistroDocente-Setup.exe` con accesos directos y desinstalación.
Los datos de usuario se conservan al actualizar o desinstalar.

En Linux, el paquete nativo se inicia con `./RegistroDocente` desde la carpeta
extraída. Requiere una sesión gráfica y una distribución compatible con las
bibliotecas del sistema usadas durante la compilación (Debian 13 en esta prueba).
El archivo de código fuente entregado no contiene bases personales: para migrar,
coloque su `registro_evaluacion.db` junto a `main.py` antes del primer arranque,
o restáurelo desde el menú de datos.

El flujo `.github/workflows/windows-build.yml` permite generar el instalador
manualmente desde GitHub Actions y descargarlo como artefacto. No publica una
versión ni firma el instalador con un certificado de Windows. Para distribución
comercial conviene añadir firma Authenticode y probar instalación/actualización
en un equipo Windows limpio.

## Licencias comerciales opcionales

La versión predeterminada es de uso libre, sin una activación ficticia. El antiguo
`licencia.json` con `activado: true` y la clave incrustada se han retirado del flujo.
Para una edición comercial, el emisor genera una clave Ed25519 con
`tools/license_tool.py` y compila incluyendo únicamente `license_public_key.pem`.
Su presencia activa la verificación obligatoria de licencias firmadas.

```powershell
.venv\Scripts\python tools\license_tool.py keygen --private C:\claves-privadas\registro.pem --public license_public_key.pem
.venv\Scripts\python tools\license_tool.py issue --private C:\claves-privadas\registro.pem --licensee "Titular" --expires 2027-12-31 --output licencia-cliente.json
```

La herramienta pide la contraseña de la clave privada por entrada oculta y la
guarda cifrada. Nunca distribuya ni suba la clave privada. No se han generado
claves de emisor para este proyecto. La activación comercial está implementada
y probada con claves temporales; requiere que el propietario configure su clave
pública antes de compilar. Las licencias offline no incluyen revocación remota.

## Pruebas

```shell
python -m unittest discover -s tests -t . -v
```

Las pruebas crean bases temporales y no tocan la base incluida ni el perfil real.
Las pruebas gráficas utilizan el escritorio de Windows o `DISPLAY` (Xvfb en
Linux); sin pantalla se marcan como omitidas. Comprueban evaluación masiva,
selección de competencias, editor, bloqueo inicial, cambios
pendientes, cancelación de importación y exportación PDF, además de pruebas de
datos, migración, recuperación, transacciones y firmas.

## Versión 1.2: lectura, Primaria y documentos propios

En la barra superior puede elegir **Primaria** o **Secundaria**. Primaria incluye
seis grados y un catálogo inicial editable de áreas, con Personal Social. Cada
nivel tiene sus propios cursos y estudiantes. Los registros anteriores conservan
su nivel Secundaria, sus identificadores y sus notas. Los criterios precisados y
la adecuación al grado los configura el docente; el catálogo no certifica por sí
solo el cumplimiento de una programación curricular institucional.

**Archivo y exportación** incorpora:

- **Documento `.registro`**: guarda la base completa del periodo, incluyendo
  alumnos, notas, asistencias, criterios, biblioteca de instrumentos, historial,
  configuración docente e insignia. Puede volver a abrirse desde el menú; el
  instalador Windows permite abrirlo con doble clic. Al abrir un documento se
  crea una copia de trabajo nueva y se conserva el documento original. Use
  Guardar documento para actualizar el archivo que quiera transportar.
- **Excel y Google Sheets**: XLSX con notas numéricas, nombres completos, IDs
  permanentes, filtros y resumen de promedios; CSV UTF-8 para importar en Sheets.
  En Sheets use Archivo → Importar → Subir. Para volver al programa, descargue el
  libro como XLSX o CSV y utilice Importar notas de Google Sheets. La validación
  por IDs, nombres y nivel evita aplicar notas a otro alumno. Los documentos de
  un periodo distinto deben abrirse como `.registro`, no mezclarse por Excel.
- **Insignia PNG/JPEG**: se guarda dentro de la base, por lo que viaja con los
  respaldos y el documento interno. Se pregunta si incluirla en reportes XLSX,
  plantillas y gráficos PDF/PNG. CSV y JSON contienen datos, sin imágenes.
- **Respaldo externo**: permite copiar una base verificada a otra carpeta o USB.

Los gráficos de ponderaciones, competencias y capacidades se muestran en pestañas
separadas. Las ponderaciones se expresan una sola vez en porcentaje; las
frecuencias son cantidades de actividades, no porcentajes de notas. Se conservan
todas las capacidades, con etiquetas completas y desplazamiento vertical. Los
promedios por capacidad de Estadísticas usan IDs completos, evitando agrupar
capacidades distintas por tener nombres abreviados iguales.

La creación de actividades desplaza el formulario completo y permite leer todos
los criterios. La planilla mantiene códigos y nombres en un panel fijo y permite
desplazar las notas horizontalmente. Un clic derecho muestra el contenido completo
de una celda o encabezado. El menú **Lectura** ajusta letra y zoom; se recuerdan
el tamaño de ventana y las preferencias.

**Trabajo docente** permite deshacer/rehacer cambios de planilla, pegar bloques
con Ctrl+V desde la fila seleccionada, recuperar borradores automáticos cada 15
segundos, duplicar actividades sin notas, reutilizar instrumentos, revisar
pendientes, simular ponderaciones y cerrar/reabrir el periodo con autenticación.
Los borradores son recuperables, pero no sustituyen Guardar; los documentos y las
exportaciones utilizan las notas confirmadas. La biblioteca exige capacidades
compatibles con la actividad, para no trasladar criterios a otra competencia.
Archivar una actividad la oculta del trabajo diario y conserva sus notas en los
promedios históricos. El bloqueo por inactividad es configurable.

El arranque respalda bases vacías o reconocidas antes de migrarlas. Una base que
no se reconoce no se sobrescribe: se ofrece seleccionar otra base o documento.
La compilación Windows también abre el ejecutable real con una instalación nueva
y con una base anterior de prueba, y comprueba que conserva su nota antes de
crear el instalador.

La versión 1.2 añade exportación de calificativos a PDF por aula o estudiante,
con insignia opcional. El menú Trabajo docente también permite configurar los
límites B/A/AD por nivel: se conserva por defecto la escala anterior, los cambios
requieren confirmación y quedan en un historial de reglas. Cambiar la escala no
modifica notas numéricas ni ponderaciones. En una institución con criterios de
logro propios, el docente debe configurar y validar esa escala.
