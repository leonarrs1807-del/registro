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

Vista permite ajustar el tamaño de letra y el zoom. El menú ⋯ → Restablecer vista adapta la ventana a la pantalla y recupera una distribución cómoda. Los tamaños de los paneles y la ventana se recuerdan.

Un clic derecho en una celda o encabezado permite leer el contenido completo.''',
'Actividades e instrumentos': '''Actividades sirve para evaluaciones independientes: una clase, trabajo, examen o práctica.

Seleccione una competencia y marque las capacidades. El botón Criterio… abre el editor opcional de cada capacidad; el texto no se muestra repetido en el formulario. Más… permite editar la descripción y exportar o importar instrumentos. El Peso vale 1 para actividades de igual importancia. Un peso de 2 hace que esa actividad tenga el doble de importancia dentro de su rubro.

Calificaciones permite escribir notas entre 0 y 20, registrar asistencia y comentarios. Una celda vacía sigue sin evaluar. Guardar notas confirma todo en la base de trabajo.

La rúbrica permite evaluar indicadores con su puntaje máximo. La lista de cotejo utiliza los niveles configurados por el instrumento. Evaluación masiva transfiere los resultados a la planilla; después debe guardarlos.

La biblioteca guarda criterios reutilizables; usarla en otra actividad no modifica evaluaciones antiguas. Duplicar actividad conserva la estructura y empieza sin notas.

Archivar oculta una actividad del trabajo diario y conserva sus notas históricas. Para corregir una calificación, use la actividad original o el historial.''',
'Excel, Google Sheets y PDF': '''Exportar notas permite elegir Excel (.xlsx), CSV para Google Sheets, PDF o JSON y la carpeta donde se guardará.

Para Google Sheets:
1. Exporte el libro de notas a XLSX.
2. En Google Sheets abra Archivo → Importar → Subir.
3. Edite las notas y conserve las columnas de identificación.
4. Descargue como XLSX o CSV.
5. En el programa use Archivo → Importar notas de Google Sheets.

Los identificadores permanentes evitan mover notas entre estudiantes. Las plantillas de matriz o instrumentos se importan mediante sus botones específicos. No cambie los encabezados CAP_ID de las plantillas.

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
'Cuenta, demo y compras': '''La edición personal 1.4 funciona sin demo ni activación comercial. El candado docente sigue protegiendo sus datos. Las funciones siguientes se conservaron para una futura edición comercial; no es necesario configurarlas ahora.

1. La primera vez cree su nombre, correo, usuario y contraseña. Son datos de una cuenta local; no se verifica el correo por Internet.
2. Elija un único curso y nivel para probar durante 30 días. La elección de la demo es fija; incluye sus grados y secciones. Puede consultar documentos de otros cursos, pero no modificarlos sin comprarlos.
3. Para comprar abra Licencia y cuenta → Guardar solicitud. Elija dónde guardarla y envíe el archivo .solicitud al vendedor. No contiene contraseñas ni datos de estudiantes.
4. Indique qué cursos quiere comprar o si desea el paquete completo. Después de verificar el pago, el vendedor entregará un archivo .licencia.
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
        listing=tk.Listbox(left,font=('Segoe UI',14),exportselection=False,width=23)
        listing.grid(row=0,column=0,sticky='nsew',padx=4,pady=4)
        side=scrollbar(left,'vertical',listing.yview);side.grid(row=0,column=1,sticky='ns');listing.configure(yscrollcommand=side.set)
        right=ctk.CTkFrame(pane);right.grid_columnconfigure(0,weight=1);right.grid_rowconfigure(0,weight=1)
        self.text=tk.Text(right,wrap='word',font=('Segoe UI',14),padx=18,pady=14,relief='flat',background='#ffffff',foreground='#0f172a')
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
