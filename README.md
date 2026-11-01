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
