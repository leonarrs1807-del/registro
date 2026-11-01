"""In-application tutorial written for teachers, including worked examples."""
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from interfaz import split,scrollbar,pixel_scale

TOPICS = {
'Empezar y guardar': '''1. Seleccione Primaria o Secundaria, el curso, grado y sección.
2. Ingrese su usuario y contraseña con el candado para habilitar la edición.
3. Registre o importe a sus estudiantes.
4. Elija si evaluará actividades independientes o prácticas por tema.

Hay dos formas distintas de guardar:
• Guardar notas / Guardar puntos confirma los cambios en la base de trabajo del programa.
• El icono Guardar (.registro), en la barra superior, abre una ventana para que usted elija la carpeta y el nombre del documento. Ese archivo contiene el periodo completo y puede abrirse otra vez en Registro Docente.

Después de guardar un archivo se muestra su ubicación completa. Puede elegir Documentos, una memoria USB u otra carpeta. Exportar a Excel/PDF también le pide dónde guardar.

Los respaldos automáticos protegen el trabajo diario y se crean en la carpeta de datos. Crear respaldo… permite elegir una copia adicional en la ubicación que usted decida.''',
'Prácticas y puntitos': '''EJEMPLO: ECUACIONES, DOS PRÁCTICAS DE 20 MINUTOS

1. Abra Puntos y pulse Nuevo tema.
2. Escriba Ecuaciones. Seleccione la competencia y marque las capacidades a las que se asignará la nota global.
3. Pulse Agregar práctica. Cree Práctica 1, duración 20 minutos, con dos ejercicios de 5 puntos cada uno. Su máximo será 10.
4. Cree Práctica 2, también de 20 minutos. Puede usar tres ejercicios: 3, 3 y 4 puntos. Su máximo también será 10.
5. Haga doble clic en cada celda para ingresar los puntos por ejercicio. Pulse Guardar puntos.

Para un estudiante que obtuvo 6/10 en la primera práctica y 8/10 en la segunda:
  Puntos obtenidos = 6 + 8 = 14
  Máximo total = 10 + 10 = 20
  Nota de examen = 14 ÷ 20 × 20 = 14/20

Si las prácticas valieran 10 y 15 puntos, el máximo total sería 25. Un total de 20 puntos daría 20 ÷ 25 × 20 = 16/20. El programa suma puntos; no promedia las notas de cada práctica por separado.

6. Al terminar el tema, pulse Crear nota / 20. Se genera una sola actividad de Exámenes llamada Prácticas acumuladas · Ecuaciones. No necesita tomar un examen físico.

También puede llamar al bloque Competencia 2 · Periodo 1 y registrar allí prácticas de varios temas de esa misma competencia. Así obtiene una sola nota final que reúne todos esos temas.

Importante:
• Un campo vacío es un ejercicio pendiente, no equivale a cero. Para consolidar deben estar completos los estudiantes activos.
• Escriba 0 si el estudiante obtuvo cero; el programa no lo inventa.
• La nota global se asigna a las capacidades marcadas. Si desea calificaciones diferentes por capacidad, cree bloques separados.
• Después de consolidar, el bloque queda protegido. Reabrir tema permite corregir puntos. Al volver a consolidar se actualiza la misma actividad; no se duplica el examen.
• Incluir / excluir práctica conserva sus puntos, pero cambia el máximo usado en el acumulado. Debe reconsolidar para actualizar la nota publicada.
• Los porcentajes del curso no cambian al agregar prácticas ni al consolidar.''',
'Porcentajes del promedio': '''LOS PORCENTAJES SON PESOS QUE USTED ELIGE

No se calculan a partir de los archivos que sube. Los valores 40, 25, 20 y 15 que aparecen inicialmente son una configuración de partida:
  Clases: 40 %
  Exámenes: 25 %
  Trabajos: 20 %
  Prácticas / Otros: 15 %

Indican la importancia de cada rubro cuando se combinan calificaciones. Puede cambiarlos, pero la suma debe ser 100. Pulse Guardar porcentajes para aplicarlos.

Dentro de un rubro, el Peso de una actividad indica si vale igual que otra (1), el doble (2), etc.

El programa combina solamente los rubros que tienen notas para el estudiante y capacidad. Si solo tiene una nota de Exámenes, esa nota se usa completa; no se convierte automáticamente en el 25 % de 20.

Ejemplo: Clases 16 con peso de rubro 40 y Exámenes 14 con peso de rubro 25; sin notas en los otros rubros:
  (16 × 40 + 14 × 25) ÷ (40 + 25) = 15,23

PRÁCTICAS ACUMULADAS EN LUGAR DE EXAMEN
La nota consolidada de un tema ocupa el rubro Exámenes. Es una calificación acumulada, aunque no haya examen físico. Si ya hay otras notas de Exámenes, ambas intervienen según sus pesos. No se borran notas anteriores.

Si desea evaluar un curso únicamente con acumulados de prácticas, puede configurar Exámenes 100 y los otros rubros 0. Esto afecta a TODO el curso, no solo a una competencia. Use primero Herramientas → Vista previa de nuevas ponderaciones para revisar los cambios.

El gráfico Ponderaciones muestra los pesos guardados. Competencias y Capacidades muestran cantidades de actividades asignadas; esas cantidades no son porcentajes y no alteran los pesos.''',
'Dimensiones y barras': '''La barra lateral muestra iconos. Pase el ratón sobre uno para ver su nombre. El botón de tres líneas de la cabecera (o Ctrl+B) despliega los nombres completos; otra pulsación los oculta. Se recuerda su preferencia. Al elegir una sección en una ventana estrecha, el menú vuelve a contraerse.

Las divisiones entre los paneles de trabajo se pueden arrastrar con el ratón. Por ejemplo:
• Amplíe el panel de nombres en Calificaciones.
• Dé más espacio al formulario al crear una actividad.
• Amplíe la lista de temas o la planilla de prácticas.

Las barras de desplazamiento tienen flechas y un control móvil. La barra inferior desplaza las columnas de notas; la barra vertical desplaza los estudiantes. También puede ampliar una columna arrastrando el borde de su encabezado.

Configuración → General permite ajustar el tamaño de letra, el zoom y la apariencia. Restablecer distribución adapta la ventana a la pantalla y recupera una distribución cómoda. Los tamaños de los paneles y la ventana se recuerdan.

En Calificaciones, el panel derecho muestra la evaluación y las plantillas. Si la ventana es estrecha, pulse Evaluación y plantillas para abrirlo y Volver a las notas para cerrarlo. Sus cambios permanecen al cambiar entre Nota directa, Rúbrica y Lista de Cotejo.

Un clic derecho en una celda o encabezado permite leer el contenido completo.''',
'Actividades e instrumentos': '''Actividades sirve para evaluaciones independientes: una clase, trabajo, examen o práctica.

Seleccione una competencia y marque las capacidades. El botón Criterio… abre el editor opcional de cada capacidad. Escriba el título, elija la categoría y pulse Guardar actividad. Descripción abre el texto adicional. Diseñe la rúbrica o el cotejo y descargue sus plantillas desde Calificaciones, en la actividad correspondiente. El Peso vale 1 para actividades de igual importancia. Un peso de 2 hace que esa actividad tenga el doble de importancia dentro de su rubro.

Calificaciones permite escribir notas entre 0 y 20, registrar asistencia y comentarios. Una celda vacía sigue sin evaluar. Guardar notas confirma todo en la base de trabajo.

La rúbrica permite evaluar cada criterio con sus cuatro niveles y puntajes. La lista de cotejo registra Sí/No por indicador. Consulte Rúbrica y cotejo paso a paso para preparar el modelo y calcular las notas. La evaluación dentro de la aplicación transfiere los resultados a la planilla; después debe pulsar Guardar notas.

La biblioteca guarda criterios reutilizables; usarla en otra actividad no modifica evaluaciones antiguas. Duplicar actividad conserva la estructura y empieza sin notas.

Archivar oculta una actividad del trabajo diario y conserva sus notas históricas. Para corregir una calificación, use la actividad original o el historial.''',
'Rúbrica y cotejo paso a paso': '''1. PREPARE EL SALÓN Y LA ACTIVIDAD

Seleccione nivel, curso, grado y sección en la cabecera. Abra el candado para editar. Registre los estudiantes antes de descargar un modelo Excel.

En Actividades elija la competencia, marque las capacidades, escriba el título y pulse Guardar actividad. Abra esa actividad en Calificaciones. Los selectores muestran títulos sin numeración interna.

2. DISEÑE LA EVALUACIÓN EN CALIFICACIONES

En Cómo evaluar elija Nota directa, Rúbrica o Lista de Cotejo. Si la ventana es estrecha, abra Evaluación y plantillas.

Para rúbrica o cotejo pulse Diseñar instrumento. Seleccione una capacidad. Puede añadir criterios observables, editar sus textos y quitar filas. Los cambios de otras capacidades se conservan al pasar de una a otra.

Rúbrica: escriba un descriptor observable para C, B, A y AD en sus casillas. Defina el máximo y los puntos de cada nivel: C < B < A < AD; AD vale el máximo. Los textos iniciales son ejemplos para adaptar a su actividad.

Cotejo: cada criterio describe una evidencia verificable. Sí aporta sus puntos máximos y No aporta cero. Puede dar mayor importancia a una evidencia usando un máximo mayor. Cada máximo debe ser mayor que 0 y no superar 20.

Pulse Guardar instrumento. Esto guarda los criterios; las notas anteriores se conservan hasta que vuelva a evaluar y aplicar.

3. EVALÚE ESTUDIANTES EN LA APLICACIÓN

Pulse Evaluar estudiantes. A la izquierda elija un estudiante; a la derecha seleccione la capacidad. En la rúbrica marque la casilla C, B, A o AD que describe su evidencia. En el cotejo marque Sí o No. Use Anterior y Siguiente para avanzar.

Sin evidencia en una rúbrica registra cero. Dejar pendiente conserva el criterio sin evaluar. Una capacidad necesita todos sus criterios para calcular su nota; las respuestas incompletas pueden guardarse para continuarlas después.

La nota se calcula como puntos obtenidos ÷ puntos máximos × 20. Por ejemplo, 6/10 y 8/10 dan 14/20. En cotejo, máximos 6 y 4 con Sí y No dan 12/20; dos No dan una nota real de 0.

Pulse Aplicar a la planilla, revise las notas y pulse Guardar notas. También se guardan las respuestas de cada criterio; aparecerán al reabrir la evaluación. Deshacer y los borradores conservan las respuestas y sus notas.

Si cambia descriptores o puntajes, revise y aplique de nuevo antes de guardar nuevas notas. Cambiar el máximo mantiene la proporción de los puntos numéricos ya registrados; los niveles elegidos se conservan. Las notas publicadas no cambian por editar el instrumento.

4. TAMBIÉN PUEDE USAR EXCEL

Después de diseñar, pulse Descargar plantilla Excel. El modelo corresponde al curso, nivel, salón y capacidades de esa actividad.

Hoja 1: ajuste los criterios, descriptores y puntajes en sus columnas. Las columnas de identificación están ocultas; consérvelas. Para añadir o quitar criterios, use Editar instrumento en la aplicación y descargue un modelo nuevo.

Elija una forma de calificar por capacidad:
• Hoja 2: escriba la nota final de la capacidad, de 0 a 20; deje sus criterios de la hoja 3 vacíos.
• Hoja 3: seleccione C, B, A, AD o Sin evidencia en rúbrica; Sí o No en cotejo. La rúbrica también admite puntos numéricos entre 0 y el máximo. Deje la hoja 2 vacía para esa capacidad.

Puede usar formas diferentes para capacidades distintas. Complete todos los criterios de una capacidad antes de importarla. Las capacidades totalmente vacías conservan su nota anterior. No cambie nombres, códigos, encabezados ni columnas ocultas. Puede ordenar filas completas, manteniendo juntas identidades y notas.

5. IMPORTE Y REVISE

Guarde como XLSX y pulse Importar evaluación Excel. La vista previa muestra el instrumento con sus casillas y una pestaña Cambios de notas con los valores anteriores y nuevos. Cancelar conserva los datos actuales. Al confirmar se crea un respaldo y se guardan los criterios, las respuestas y las notas completas del libro.

Las notas importadas ya quedan guardadas. La asistencia se conserva; las notas y los comentarios vacíos no borran datos existentes. Si importa solo criterios, puede evaluar después en la aplicación.

Si hay un error, corrija la fila indicada. Las fórmulas deben tener un resultado calculado en Excel o sustituirse por valores. Un error rechaza la importación completa.

6. LEA LOS NIVELES Y GUARDE SU DOCUMENTO

C tiene fondo rojo suave; B amarillo; A verde; AD azul. Configuración → General → Configurar escala de logro permite cambiar los límites de cada nivel sin alterar las notas numéricas.

En Nota directa haga doble clic en una nota, escriba de 0 a 20 y confirme con Enter. Registre asistencia y comentarios en la planilla y pulse Guardar notas.

Use además el icono Guardar de la cabecera para elegir dónde conservar el documento completo .registro. Incluye estudiantes, actividades, instrumentos, respuestas, notas e insignia.''',
'Excel, Google Sheets y PDF': '''Exportar notas permite elegir Excel (.xlsx), CSV para Google Sheets, PDF o JSON y la carpeta donde se guardará.

Para Google Sheets:
1. Exporte el libro de notas a XLSX.
2. En Google Sheets abra Archivo → Importar → Subir.
3. Edite las notas y conserve las columnas de identificación.
4. Descargue como XLSX o CSV.
5. En el programa use Archivo → Importar notas de Google Sheets.

Los identificadores permanentes evitan mover notas entre estudiantes. Las plantillas de matriz o instrumentos se importan mediante sus botones específicos. Conserve los encabezados y las columnas ocultas de identificación de las plantillas.

CSV y JSON contienen datos sin imágenes. Los reportes XLSX y PDF pueden incluir la insignia.

Para conservar TODA la información del periodo y volver a abrirla aquí, utilice un documento .registro, no una hoja de cálculo.''',
'Insignia y perfil docente': '''Cargar insignia del colegio acepta PNG y JPEG. La imagen se conserva dentro de la base de datos y viaja en los respaldos y documentos internos.

Al exportar un reporte compatible se le pregunta si desea incluirla. Puede obtener reportes con o sin insignia sin cambiar el archivo original.

Configurar docente permite actualizar nombre, institución y contraseña. Dejar vacía la nueva contraseña conserva la existente. El candado protege la edición y la aplicación inicia bloqueada.''',
'Años, niveles y seguridad': '''Primaria y Secundaria conservan cursos y estudiantes separados. Primaria incluye seis grados. Los datos previos se mantienen en Secundaria hasta que usted seleccione otro nivel.

Cada año y periodo puede tener un documento independiente. Crear periodo copia currículo y alumnado, pero no notas ni prácticas del periodo anterior.

Crear respaldo… guarda una copia verificada en la carpeta que elija. Restaurar reemplaza los datos activos después de guardar una copia de seguridad. La aplicación se reinicia para abrir el resultado.

El historial registra cambios de notas. Deshacer/Rehacer en la planilla actúa antes de confirmar; el historial permite recuperar cambios ya guardados bajo sus condiciones de seguridad.

Cerrar periodo bloquea modificaciones. Reabrirlo requiere autenticación. Los borradores recuperables ayudan ante cierres imprevistos, pero no sustituyen Guardar archivo.

Un documento de notas no es una licencia de uso. La cuenta y activación se guardan aparte de los datos escolares.''',
'Cuenta, demo y compras': '''La edición comercial utiliza una cuenta local y una activación para una sola PC. El vendedor habilita los cursos comprados. En la edición personal no se solicita activación. El candado protege la edición de sus datos.

1. La primera vez cree su nombre, correo, usuario y contraseña. Son datos de una cuenta local; no se verifica el correo por Internet.
2. Elija un único curso y nivel para probar durante 30 días. La elección de la demo es fija; incluye sus grados y secciones. Puede consultar documentos de otros cursos, pero no modificarlos sin comprarlos.
3. Para comprar abra Licencia y cuenta → Guardar solicitud. Elija dónde guardarla y envíe el archivo .solicitud al vendedor. No contiene contraseñas ni datos de estudiantes.
4. Indique qué cursos quiere comprar: uno, dos, tres o cualquier selección personalizada; también puede elegir todos. El vendedor decide qué habilitar y la vigencia. Después de verificar el pago, entregará un archivo .licencia vinculado a una sola PC y cuenta.
5. Use Importar licencia comprada en la misma computadora en la que creó la solicitud. La firma habilita esos cursos para su cuenta y equipo.

Al vencer la demo puede seguir consultando, guardando documentos y exportando a Excel, Google Sheets o PDF. Sus datos no se borran. Para agregar o corregir notas necesita una licencia vigente del curso.

Copiar una licencia a otra computadora o cuenta no permite activarla. El archivo .registro tampoco lleva activación. Respalde su cuenta con el botón correspondiente; la protección de Windows solo permite restaurarla en el mismo equipo y usuario de Windows.

No cambie la fecha para ampliar la demo: se comprueba que no retroceda. Si el reloj quedó mal, corríjalo. Al cambiar de computadora, solicite una nueva licencia y traslade sus datos escolares con un documento .registro.

Sin servidor, las ventas y los cambios de equipo los gestiona el vendedor manualmente. No hay recuperación automática de contraseña, verificación de correo, revocación remota ni sincronización en Drive. Un formateo o una modificación deliberada del programa pueden eludir controles locales; ninguna protección offline es infalible.

EDICIÓN DE PREPARACIÓN: si Licencia y cuenta indica que falta la clave pública, solicite al vendedor el instalador comercial definitivo antes de comprar una activación.'''
}


class Tutorial(ctk.CTkFrame):
    def __init__(self,master):
        super().__init__(master,fg_color='transparent')
        self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(1,weight=1)
        ctk.CTkLabel(self,text='Instrucciones · Guía paso a paso',font=ctk.CTkFont(size=20,weight='bold')).grid(row=0,column=0,sticky='w',padx=12,pady=10)
        pane=split(self,'tutorial');pane.grid(row=1,column=0,sticky='nsew',padx=8,pady=6)
        left=ctk.CTkFrame(pane);left.grid_rowconfigure(0,weight=1);left.grid_columnconfigure(0,weight=1)
        listing=tk.Listbox(left,font=('Segoe UI',-round(14*pixel_scale(self))),exportselection=False,width=23)
        listing.grid(row=0,column=0,sticky='nsew',padx=4,pady=4)
        side=scrollbar(left,'vertical',listing.yview);side.grid(row=0,column=1,sticky='ns');listing.configure(yscrollcommand=side.set)
        right=ctk.CTkFrame(pane);right.grid_columnconfigure(0,weight=1);right.grid_rowconfigure(0,weight=1)
        self.text=tk.Text(right,wrap='word',font=('Segoe UI',-round(15*pixel_scale(self))),padx=18,pady=14,relief='flat',background='#ffffff',foreground='#0f172a')
        self.text.grid(row=0,column=0,sticky='nsew')
        bar=scrollbar(right,'vertical',self.text.yview);bar.grid(row=0,column=1,sticky='ns');self.text.configure(yscrollcommand=bar.set)
        pane.add(left,width=round(250*pixel_scale(self)),minsize=round(150*pixel_scale(self)),stretch='never');pane.add(right,minsize=round(230*pixel_scale(self)),stretch='always')
        self.listing=listing;self.names=list(TOPICS)
        for name in self.names:listing.insert('end',name)
        listing.bind('<<ListboxSelect>>',lambda e:self.open(self.names[listing.curselection()[0]]) if listing.curselection() else None)
        self.open(self.names[0])

    def open(self,topic):
        if topic not in TOPICS:topic=self.names[0]
        index=self.names.index(topic);self.listing.selection_clear(0,'end');self.listing.selection_set(index);self.listing.see(index)
        self.text.configure(state='normal');self.text.delete('1.0','end');self.text.insert('1.0',topic.upper()+'\n\n'+TOPICS[topic]);self.text.configure(state='disabled');self.text.yview_moveto(0)
