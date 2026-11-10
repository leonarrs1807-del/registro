## Full personal 2.0.0

- Selector visible de bimestres o trimestres y unidades didácticas por curso y aula.
- Pegado desde Excel con vista previa y relleno de estudiantes seleccionados, con deshacer.
- Instrumentos reutilizables en Excel por grado, competencia y tema, sin datos del alumnado.
- Historial de archivos por fecha: abre una copia independiente y conserva el registro actual.
- Cierre de periodo con bloqueo de datos y registro de reaperturas.
- Datos de la IE e insignia guardados con el documento; informes PDF y registros Excel institucionales.
- Ventana de preparación visible; todas las secciones se construyen al iniciar. Los módulos de gráficos se anticipan durante esa preparación para reducir la espera al cambiar de pantalla.

## Full personal 1.11.0

Fichas por nombre dentro de Trabajos, sin adjuntos. Entrada de una nota global por
estudiante para las capacidades seleccionadas, o nota por capacidad, rúbrica y cotejo.
Conserva los porcentajes de los rubros y sus pesos relativos. Exporta el propósito
de la clase con encabezados compactos y un resumen de capacidades opcional.
Corrige la escala de las notas y de la lista de temas en Prácticas.

## Full personal 1.10.0

Tablas celestes con N°, nombre ajustable y fijo al deslizar, flechas para recorrer
celdas, controles de deshacer y más filas visibles. El criterio se concentra en
el panel lateral con texto en negrita. Exportación de tablas completas e importación
con vista previa que agrega el currículo faltante. La matriz final se descarga en
números, letras o ambos y conserva las notas exactas para reimportar.

## Versión 1.9.0 Full personal

Entrega para Leonardo con todos los cursos y módulos, sin activación comercial.
Cotejo rápido de orientación, conversión opcional revisada, competencia y capacidades
identificadas por nombre, barra lateral contraíble y nombres fijos al deslizar criterios.
Las nuevas plantillas muestran solo Instrumento y Registro, sin alumnado de ejemplo.
Archivo → Nuevo registro vacío permite empezar limpio conservando un respaldo.
La compilación Windows verifica todas las pruebas, el ejecutable y una base anterior.

# Registro Docente

Aplicación de escritorio para estudiantes, sesiones, rúbricas, asistencia y
evaluación por competencias. Funciona con Python 3.12, Tkinter y SQLite, sin
servidor ni conexión permanente a Internet.

## Revisión 1.8.1: puntajes manuales y vista del grupo

La vista **Grupo** compara estudiantes en filas y criterios en columnas, con sus
nombres fijos y los descriptores del criterio seleccionado debajo. Doble clic
permite escribir puntos, C/B/A/AD o Sí/No; Enter avanza de estudiante y Tab de
criterio. La vista Individual conserva la rúbrica completa y añade puntaje manual.
Las letras se calculan con la escala configurada, normalizando los puntos del
criterio a veinte. Un cero cuenta como respuesta y una celda vacía queda pendiente.

Se pueden guardar e importar avances parciales. La nota provisional divide los
puntos obtenidos entre los máximos de los criterios evaluados y multiplica por
veinte; los pendientes se señalan y no cuentan como cero. Al completar los criterios
se obtiene la nota completa. Excel incluye el avance y una vista de paneles sin
selecciones repetidas. Las notas ya guardadas se recalculan solo al evaluar o al
pulsar Recalcular resultados.

Los cambios en mejoras-escritorio generan una revisión personal de Windows. La
compilación comercial queda para una acción manual o una etiqueta de versión.

## Versión 1.8: Excel desde el inicio y evaluación por criterio

En Calificaciones, **Herramientas → Plantilla Excel** está disponible sin diseñar
antes el instrumento. Elija cuántos criterios necesita cada capacidad; la plantilla
usa el tema y las capacidades de la actividad y permite redactar los descriptores
directamente en Excel. Si ya hay un instrumento, puede conservarlo o empezar uno nuevo.

La hoja de evaluación tiene una columna por criterio. El resumen de capacidades
calcula las notas; no sustituye esas respuestas por una nota manual. La rúbrica
alinea los cuatro descriptores y sus puntos en bloques de dos filas, con un ancho
y zoom que permiten ver sus niveles juntos. La importación mantiene la identidad
de estudiantes y criterios, valida toda la operación y calcula las notas desde
las respuestas, sin depender de la caché de fórmulas del resumen.

La vista **Criterios** permite evaluar todos los criterios desde la pantalla
principal. **Resultados y asistencia** muestra las notas calculadas. La nota final
de una capacidad es la suma de puntos obtenidos dividida entre la suma de máximos,
multiplicada por veinte. Deshacer, borradores y guardado incluyen las respuestas.
El editor de instrumentos sigue disponible. La escala se configura en Configuración.

**Configuración → Licencia** muestra la importación en la edición comercial y
explica su disponibilidad en la revisión personal. La edición de venta continúa
requiriendo la clave pública del vendedor. Las claves y licencias existentes
mantienen su protocolo y siguen siendo compatibles entre actualizaciones.

## Versión 1.7: evaluación por criterios y configuración

Actividades prepara el tema, la competencia y las capacidades. En **Calificaciones**
elija Nota directa, Rúbrica o Lista de Cotejo y diseñe el instrumento de esa actividad.
La rúbrica presenta cuatro columnas C/B/A/AD con descriptores y puntos editables;
el cotejo usa Sí/No. La evaluación muestra un estudiante y una capacidad por vez.

Las respuestas se conservan al guardar notas y también en deshacer y borradores.
Pendiente y cero son distintos. Editar un instrumento conserva las notas publicadas;
para actualizarlas hay que volver a aplicar la evaluación y guardar.
Excel usa encabezados legibles y columnas ocultas de identidad. La importación
muestra las casillas del instrumento y los cambios numéricos antes de confirmar.
Las plantillas anteriores siguen siendo compatibles.

**Configuración** reúne perfil, institución, apariencia, escala de logro, cursos y
respaldos; en la edición comercial también incluye la licencia. Se mantiene el menú
lateral de iconos. Las vistas costosas se actualizan al abrirlas; crear una actividad
no vuelve a dibujar los gráficos y las matrices ocultas. Los promedios usan aritmética
decimal y redondeo a dos decimales, con las mitades hacia arriba en cada etapa.

## Ejecutar desde el código

En Windows, instale Python 3.12 con Tcl/Tk y ejecute en esta carpeta:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

En Linux use `python3 -m venv .venv`, `.venv/bin/python` y asegúrese de tener
Tcl/Tk y una sesión gráfica. Para pruebas sin pantalla puede utilizar Xvfb.

La edición comercial 1.8.1 permite vender cualquier selección de cursos, o todos,
con una licencia vinculada a una cuenta y PC. La edición personal previa permite
trabajar sin demo ni activación comercial.
Si conserva la contraseña inicial, el primer arranque solicita configurar el
perfil docente y una contraseña de al menos 8 caracteres. Las bases existentes
conservan su usuario, contraseña y notas. El candado solicita autenticarse para
editar y las contraseñas se guardan con PBKDF2 y sal aleatoria. Las funciones de
licencias comerciales se describen en la guía del vendedor.

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

## Activación comercial 1.8.1

La edición comercial utiliza cuentas locales y una demo de **30 días con un solo curso
y nivel**. La demo incluye los grados y secciones de ese curso. Al vencer, se
permite consultar, guardar documentos y exportar; se bloquean las modificaciones.
Los cursos no comprados también se conservan en modo de consulta. Los controles
se aplican en la interfaz y en las conexiones SQLite de producción, incluidas las
importaciones. No hay servidor, procesador de pagos ni sincronización con Drive.

El comprador exporta una solicitud `.solicitud` con su cuenta, correo, identidad
hash de la instalación de Windows y catálogo de cursos, sin contraseña ni datos
de estudiantes. El vendedor verifica el pago y firma una `.licencia` con uno o
varios cursos, o `*` para todos. La licencia puede ser permanente o tener una fecha
de vencimiento. Las compras adicionales agregan cursos. La firma Ed25519 liga
cada licencia a la cuenta y equipo de esa solicitud; no basta copiarla a otra PC.

**Configuración de las ventas:** el repositorio no incluye la clave privada
del emisor. El instalador personal 1.5 previo funciona sin demo ni compras. Para compilar
una edición comercial se requiere incorporar la clave pública y definir
`REGISTRO_EDITION=comercial`; la compilación rechaza una edición comercial sin clave pública. Para finalizar la edición comercial, genere sus claves
con la herramienta separada **RegistroLicencias.exe**, conserve la privada cifrada
y comparta únicamente `license_public_key.pem`. Debe incorporarse al código antes
de compilar; al estar ignorada por Git se debe añadir explícitamente con
`git add -f license_public_key.pem`. Es pública y se integra en el ejecutable con
un runtime hook. Quitar un archivo PEM externo no desactiva la demo ni convierte
el programa en una edición gratuita. La privada nunca se incluye en artefactos.

El flujo **Registro Docente comercial - Windows** se ejecuta al actualizar la
rama de mejoras. Si todavía falta la clave pública, informa que está pendiente
y no publica un instalador comercial. Cuando está incorporada, valida que el
archivo contenga únicamente una clave pública Ed25519, ejecuta todas las pruebas
y verifica el ejecutable comercial en Windows con bases nuevas y anteriores.
El artefacto para los clientes es **RegistroDocente-Comercial-Windows**.
Las solicitudes nuevas identifican la clave del instalador; el emisor rechaza
una clave privada de otro vendedor. La herramienta limpia los permisos de la
venta anterior al abrir otra solicitud y permite seleccionar cualquier cantidad
de cursos. La edición personal solo se compila si el propietario la elige
expresamente en el flujo manual **Compilar Registro Docente - Windows**.

La [guía del vendedor](docs/LEEME-VENDEDOR.txt) explica los pasos completos.
RegistroLicencias se compila por separado con `RegistroLicencias.spec` y se
entrega en el artefacto **RegistroLicencias-SoloVendedor**. Al cliente solo se
entrega **RegistroDocente-Setup.exe** y su licencia comprada.

También existe una alternativa por consola:

```powershell
.venv\Scripts\python tools\license_tool.py keygen --private C:\claves-privadas\registro_privada.pem --public license_public_key.pem
.venv\Scripts\python tools\license_tool.py issue --private C:\claves-privadas\registro_privada.pem --request cliente.solicitud --courses secundaria:matematica --output cliente.licencia
```

La contraseña de la privada se solicita por entrada oculta. Nunca distribuya ni
suba la privada o su contraseña. Perderlas impide emitir nuevas licencias para
ese instalador. Haga un respaldo privado y seguro.

Windows protege la cuenta local con DPAPI del usuario actual y conserva una
copia en HKCU para recordar la demo tras una reinstalación del programa. Se
detectan retrocesos del reloj. Las cuentas y licencias no viajan en el documento
`.registro`; el respaldo `.activacion` corresponde al mismo equipo y perfil de
Windows. Linux usa una protección local para desarrollo y pruebas, sin equivaler
a las garantías DPAPI de la edición Windows. El instalador no cifra las notas.

Sin servidor no hay revocación remota, verificación de correo, recuperación de
contraseña por correo ni prueba de identidad de la persona. El vendedor gestiona
manualmente cambios de equipo y reemisiones: no puede desactivar a distancia la
licencia antigua. Formatear, clonar una máquina o modificar deliberadamente el
programa puede eludir controles offline; no se promete protección absoluta.

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

## Versión 1.3: prácticas acumuladas, pantalla y tutorial

**Prácticas y puntos** organiza temas por curso, salón y competencia. Cada práctica
registra fecha, duración y ejercicios con máximos propios. La nota se calcula
como `20 × suma de obtenidos / suma de máximos`, redondeada a dos decimales.
6/10 + 8/10 produce 14/20. Los vacíos permanecen pendientes; un cero explícito
sí se evalúa. No se consolida hasta completar los estudiantes activos.

**Crear nota de examen** genera una sola actividad de Exámenes por tema y asigna
su nota global a las capacidades elegidas. No modifica porcentajes ni borra otras
notas. Reabrir permite corregir puntos; volver a consolidar actualiza la misma
actividad y conserva la asistencia/comentarios. Excluir una práctica conserva sus
puntos y cambia el denominador. Un documento .registro incluye los puntos; un
periodo nuevo empieza sin ellos.

La navegación lateral se desplaza verticalmente. Las divisiones de nombres/notas,
formularios, temas y gráficos son anchas y se pueden arrastrar. Las barras de
desplazamiento son más anchas y los controles se distribuyen en varias filas al
reducir la ventana. **Restablecer vista** recupera la distribución. Se guardan
las proporciones de los paneles y el último directorio de exportación.

**Guardar archivo** abre siempre un selector de carpeta/nombre y muestra la ruta
completa al terminar. Guardar notas/puntos confirma datos en la base de trabajo;
guardar .registro crea un documento transportable. Los respaldos manuales también
permiten elegir ubicación. **Instrucciones** incorpora tutoriales con ejemplos de
prácticas, porcentajes, formatos, seguridad, cuenta y compras. Los pesos los elige
el docente: los valores iniciales no se deducen de los archivos importados.

## Versión 1.5: evaluación visible, modelos y lectura

El instalador y las propiedades del ejecutable identifican a **Leonardo Roque**
como propietario. La edición sigue siendo personal mientras se prepara la
comercialización.

Calificaciones conserva el menú lateral de iconos. Muestra un panel derecho con
Nota directa, Rúbrica, Cotejo, modelos Excel, importación, asistencia, peso y
criterios. En ventanas estrechas se abre con **Evaluación y plantillas**. Cambiar
el modo reutiliza la tabla y conserva las notas pendientes. Los títulos de
actividades omiten la numeración interna. Cada nota tiene fondo suave C rojo,
B amarillo, A verde o AD azul, incluso al seleccionar la fila. Los menús y
diálogos usan fuentes ajustadas al zoom y a la escala de Windows.

Los modelos incluyen criterios/indicadores, notas finales por capacidad,
respuestas por indicador e instrucciones. Rúbrica usa puntos y máximos; cotejo
usa **Sí/No** ponderado por el máximo de cada indicador. Ambos calculan
`suma obtenida / suma de máximos × 20`. Puede completar notas finales O
indicadores para una misma capacidad. Vacío conserva la nota anterior; cero se
guarda como una nota. La importación conserva la asistencia y los comentarios
vacíos; valida nombres, códigos, IDs, curso, nivel, salón y actividad antes de
aplicar criterios y notas en una transacción. Incluye vista previa y respaldo.

**Ayuda → Rúbrica y cotejo paso a paso** explica el recorrido completo con
ejemplos. El instalador también contiene `GUIA-USO.txt`. Los gráficos ajustan
ancho, alto y texto a sus datos y al espacio disponible; los paneles permiten
desplazar gráficos largos. La escala C/B/A/AD se configura en una sola ventana.

La herramienta del vendedor permite seleccionar uno, dos, tres o cualquier
conjunto de cursos, o todos. Las licencias comerciales firmadas corresponden a
una cuenta y PC, requieren la clave pública del propietario al compilar, y se
mantienen separadas de los registros escolares.

## Versión 1.4: espacio de trabajo compacto (antecedente)

Esta entrega es una **edición personal de trabajo**, sin demo, límite de cursos
ni solicitud de cuenta comercial. Conserva el candado docente y las contraseñas
existentes; no borra archivos de activación. El generador y la verificación de
licencias se mantienen para retomarlos más adelante. No distribuya esta edición
personal como instalador comercial con restricciones.

La cabecera ocupa una fila: nivel, curso, grado y sección. Guardar, candado y
opciones se representan con iconos y ayudas al pasar el ratón. En ventanas
estrechas, el nivel también se puede elegir en el menú ⋯. Ctrl+S guarda el
.registro; Ctrl+B despliega u oculta los nombres del menú lateral; F1 abre Ayuda.
La navegación empieza contraída y recuerda su estado. Elegir una página con una
ventana estrecha contrae el menú para dejar espacio al contenido.

Calificaciones muestra los controles de uso diario y una tabla con encabezados
cortos. **Detalles** conserva descripción, competencia, capacidades, criterios e
indicadores. **⋯** reúne asistencia, peso e importación de instrumentos. Las
columnas siguen separadas por una división ajustable. Un clic derecho en cada
encabezado permite leer la capacidad completa. Las barras se ocultan cuando todo
cabe en el panel.

Actividades elimina títulos repetidos y abre los criterios opcionales desde
**Criterio…**. **Descripción** abre el texto adicional; los instrumentos y sus plantillas se preparan desde Calificaciones. Los textos
existentes se conservan. Puntos mantiene la **Nota / 20** junto al estudiante,
incluso mientras se desplazan los ejercicios. **Crear nota / 20** publica el
acumulado en una actividad de Exámenes; guardar puntos por sí solo no lo publica.

Para retomar una edición comercial, el propietario debe configurar la clave
pública y compilar con `REGISTRO_EDITION=comercial`. La política se integra en el
ejecutable; una variable del equipo del comprador no permite desactivarla. El
compilador rechaza una edición comercial sin clave pública. La edición personal
es la predeterminada mientras el usuario mantiene pausada la comercialización.
