# Spec 010 — Estudio del notebook: Resumen, Informe, Mapa mental y Notas
Estado: en implementación (09/11/2026). Andrés pidió empezar a programar sin pasar antes por `/sdd-clarify`, el plan ni las tareas (poco tiempo); la migración de la tabla de resultados la aprobó él mismo ese día. Valores provisionales que se miden después: 20 partes y 900 s por generación (`ESTUDIO_PARTES_MAXIMAS`, `ESTUDIO_TIEMPO_MAXIMO_SEGUNDOS`).; cambio «ancho de las columnas ajustable» (JJ1, Andrés, 12/11/2026): aprobado por Andrés el 12/11/2026 con mis propuestas; plan y tarea en `plan.md` y `tasks.md`

## Contexto y objetivo
- Petición de Andrés (09/11/2026): que NotebookServIA se parezca más a Google NotebookLM, todo en local: un panel «Estudio» donde, con las fuentes que el usuario deje marcadas, se genere un **Resumen**, un **Informe** o un **Mapa mental**, y donde todo lo generado quede guardado en el notebook, a mano.
- Hoy el notebook solo ofrece la lista de fuentes y el chat, y el chat responde a una pregunta con los pocos fragmentos más relevantes. No puede responder «resume todo lo que tengo», porque no lee todo el contenido.
- Marcar o desmarcar fuentes, cambiar su nombre y quitarlas ya existe (spec 009b) y **no se repite aquí**: el Estudio reutiliza la selección de fuentes marcadas.
- Función nueva del módulo NotebookServIA (testing.md, paso 3): las pruebas existentes de crear, cargar, vista previa, quitar, casilla, renombrar y chat del notebook siguen pasando.
- Decisiones de Andrés incorporadas (entrevista del 09/11/2026): cobertura de todo el contenido por partes (P3), topes de tamaño y de tiempo (P4), una generación a la vez y el chat espera (P5), salir de la pantalla cancela (P6), Resumen breve / Informe estructurado / Mapa mental en árbol (P7), solo el botón, sin campo de enfoque (P8), resultados que se conservan con aviso si se quitó una fuente (P9), copiar el texto (P10), «Guardar en notas» incluido (P13, P14), pestañas a 616 px (P11), un reintento ante salida inválida (P12), quitar con baja lógica solo si el usuario lo desea (P1, P2).

## Trazabilidad
- ERS (V1.13 en Word; el índice de texto de los agentes aún es V1.11): RF-11, RF-12, RF-14, RF-17, RF-19, RF-21, RNF-03, RNF-04, RNF-07, RNF-09, RNF-10, RN-01, RN-03, RT-06, RT-07.
- Historias de usuario: HU-11, HU-12, HU-17, HU-19 (base) · Casos de uso: CU-09, CU-11 (FA-02 «Trabajar dentro del notebook»), CU-18.
- Nada de esto existe en el ERS: todo es `[NUEVO]`. Propuesta para la documentación: un caso de uso nuevo (CU-19 «Generar y consultar resultados de estudio»), tres historias nuevas (HU-NUEVA-5, 6 y 7), requisitos de numeración **.120+** sobre los RF existentes (la 009b usó .100–.110) y los tipos de acción nuevos de la bitácora.
- «Estado actual» del ERS que cierra: ninguno.

## Usuarios
- **Usuario Gubernamental**: dueño del notebook y de sus resultados.
- **Administrador**: no entra a NotebookServIA (RN-03).

## Historias de usuario
- HU-NUEVA-5. Como Usuario Gubernamental, quiero generar un resumen, un informe o un mapa mental de las fuentes que dejé marcadas en mi notebook, para entender y presentar su contenido sin leerlo todo.
- HU-NUEVA-6. Como Usuario Gubernamental, quiero que lo que se genere quede guardado en mi notebook y poder reabrirlo, copiarlo o quitarlo de mi lista, para tenerlo a mano sin volver a generarlo.
- HU-NUEVA-7. Como Usuario Gubernamental, quiero guardar una respuesta del chat como nota, con su pregunta y sus citas, para conservar lo que me sirvió.

## Definiciones
- **Resultado de estudio**: lo que el Estudio guarda en un notebook. Tiene un **tipo**: Resumen, Informe, Mapa mental o Nota.
- **Fuentes marcadas**: las fuentes del notebook con la casilla activa (spec 009b). **Selección efectiva**: las marcadas que están Procesado; solo ellas alimentan una generación.
- **Resumen**: texto breve con las ideas principales de las fuentes. **Informe**: documento más largo y estructurado, con título, secciones y conclusiones. **Mapa mental**: un árbol con un tema central y ramas y sub-ramas, de hasta tres niveles bajo el tema central, dibujado en pantalla. **Nota**: una pregunta del chat con su respuesta y sus citas, guardada tal como se vio.
- **Parte**: tramo del contenido de las fuentes que cabe en la ventana de entrada del modelo (RF-11). Una generación recorre todas las partes y luego une lo obtenido.
- **Generación**: el proceso completo, desde pulsar el botón hasta guardar el resultado o terminar sin guardar.
- **Baja lógica**: el resultado desaparece de la lista pero su registro se conserva (RN-01, RNF-10).
- **Fecha y hora** de un resultado: la de Costa Rica, como en el resto de la interfaz.

## Requisitos funcionales

### A. Panel «Estudio» y distribución de la pantalla (RF-17, RNF-04)
- **RF-17.120** `[NUEVO]`: EL SISTEMA muestra el notebook abierto en tres paneles: «Fuentes» a la izquierda, el chat al centro y «Estudio» a la derecha.
  - El panel «Fuentes» conserva sin cambios lo de la 009b (casilla, vista previa, menú ⋮, cargar documentos).
- **RF-17.121** `[NUEVO]`: EL SISTEMA muestra en «Estudio» los botones «Resumen», «Informe» y «Mapa mental» y, debajo, la lista de los resultados guardados del notebook, del más reciente al más antiguo.
  - Cada fila muestra el tipo (con su ícono), el título y la fecha y hora.
  - SI el notebook no tiene resultados, ENTONCES la lista muestra «Todavía no hay resultados. Genere uno con las fuentes marcadas.».
- **RNF-04.120** `[NUEVO]`: MIENTRAS la pantalla es pequeña (verificada a 616 px de ancho), EL SISTEMA muestra un solo panel a la vez, con las pestañas «Fuentes», «Chat» y «Estudio», sin elementos superpuestos ni inaccesibles.
  - A 1366 px los tres paneles se ven a la vez.
  - MIENTRAS una generación está en curso y se ve otra pestaña, la pestaña «Estudio» indica que hay una generación en curso.
- **RNF-04.121** `[NUEVO]`: la lista de resultados, el resultado abierto y el mapa mental se leen y se manejan en ambos anchos, sin desplazamiento horizontal de la página.

### B. Generar un resultado (RF-11, RF-12)
- **RF-11.120** `[NUEVO]` (HU-NUEVA-5): CUANDO el Usuario Gubernamental pulsa «Resumen», «Informe» o «Mapa mental», EL SISTEMA genera ese tipo de resultado a partir de la selección efectiva del notebook abierto, con el motor de lenguaje local.
  - No usa fuentes desmarcadas, en Pendiente o en Error, ni documentos de otros notebooks o temas.
- **RF-11.121** `[NUEVO]`: MIENTRAS ninguna fuente Procesado está marcada, EL SISTEMA desactiva los tres botones y muestra «Marque al menos una fuente para generar un resultado.».
  - SI la solicitud llega igual al servidor, ENTONCES la rechaza con ese mismo mensaje, sin llamar al modelo ni guardar nada.
- **RF-11.122** `[NUEVO]` (P7): EL SISTEMA da a cada tipo la forma que le corresponde:
  - Resumen: texto breve con las ideas principales.
  - Informe: título, secciones y conclusiones.
  - Mapa mental: un tema central y sus ramas, hasta tres niveles bajo el tema central.
    - Cambio (10/11/2026, Andrés): las líneas del mapa son tramos rectos (horizontales y verticales): salen del borde derecho de cada caja con ramas y llegan al borde izquierdo de cada rama, sin líneas sueltas. Prueba: e2e de RF-11.122 (conector de salida por caja con ramas y de llegada por rama, alineados con sus cajas).
- **RF-11.123** `[NUEVO]` (P8): EL SISTEMA no pide ni acepta indicaciones del usuario para orientar la generación: el resultado se genera solo con las instrucciones fijas del sistema.
- **RF-11.124** `[NUEVO]` (RT-07): EL SISTEMA genera todo resultado en español.
- **RF-12.120** `[NUEVO]` (RF-12): EL SISTEMA hace que el Resumen y el Informe se basen solo en las fuentes de la selección efectiva y citen por su nombre mostrado las fuentes de las que toman sus ideas.
  - Solo pueden citar fuentes de esa selección. Se verifica sobre los nombres citados, no sobre el texto del modelo.
  - Cambio (10/11/2026, Andrés): SI el modelo no nombra ninguna fuente de la selección (pasa con texto de imágenes mal reconocido), ENTONCES EL SISTEMA no descarta el resultado: le agrega al final «**Fuentes consultadas:**» con las fuentes de la selección (como hace el chat) y no llama de nuevo al modelo. Las instrucciones del Resumen y del Informe piden además citar aunque el texto esté deformado.
- **RF-11.125** `[NUEVO]` (P12): SI el modelo devuelve una salida vacía o, en el Mapa mental, sin la estructura exigida (tema central, ramas y niveles permitidos), ENTONCES EL SISTEMA reintenta la generación una vez.
  - SI el reintento también falla, ENTONCES no guarda nada y muestra «No se pudo generar el resultado. Intente de nuevo.».
  - Nunca se guarda ni se muestra un resultado con una estructura inválida.

### C. Cobertura por partes, progreso, cancelación, topes y concurrencia (RF-11, RNF-01)
- **RF-11.126** `[NUEVO]` (P3): EL SISTEMA cubre todo el contenido de las fuentes de la selección efectiva: lo recorre por partes, procesa cada una y une lo obtenido en el resultado final.
  - La unión de resultados parciales respeta también la ventana del modelo, y las instrucciones nunca se recortan (RF-11).
- **RF-11.127** `[NUEVO]`: MIENTRAS se genera, EL SISTEMA muestra la etapa y el avance («Analizando parte 3 de 12», «Uniendo resultados») y un botón «Cancelar».
- **RF-11.128** `[NUEVO]` (P6): CUANDO el usuario pulsa «Cancelar», cierra o recarga la página, o abre otro notebook durante una generación, EL SISTEMA detiene la generación, libera el modelo y no guarda nada.
  - Con «Cancelar», la interfaz muestra «Generación cancelada.».
  - Cancelar no deja ningún resultado a medias en la lista.
- **RF-11.129** `[NUEVO]` (P4): SI las fuentes de la selección efectiva superan el tamaño máximo permitido para una generación, ENTONCES EL SISTEMA no empieza, no llama al modelo y muestra «Las fuentes marcadas son demasiado extensas. Desmarque algunas e intente de nuevo.».
- **RF-11.130** `[NUEVO]` (P4): SI una generación supera el tiempo máximo permitido, ENTONCES EL SISTEMA la detiene, no guarda nada y muestra «La generación tardó demasiado y se detuvo. Desmarque algunas fuentes e intente de nuevo.».
  - Los valores del tamaño y del tiempo máximos los fija el plan con una medición real y quedan configurables (ver «Dudas abiertas»).
- **RF-11.131** `[NUEVO]` (P5): MIENTRAS una generación del usuario está en curso, EL SISTEMA desactiva los botones de generar y el envío de preguntas del chat de ese notebook, e indica por qué.
  - SI llega al servidor una segunda generación o una pregunta del chat del mismo usuario durante una generación, ENTONCES la rechaza con «Hay una generación en curso. Espere o cancélela.», sin llamar al modelo.
  - Guardar una nota no usa el modelo y sigue disponible.
- **RF-11.132** `[NUEVO]`: SI el motor de lenguaje no está disponible, ENTONCES EL SISTEMA muestra un mensaje de error en español, sin detalles técnicos, no guarda nada y deja los botones de nuevo disponibles.

### D. Guardar, abrir, copiar y quitar resultados (RF-14, RN-01)
- **RF-14.120** `[NUEVO]` (HU-NUEVA-6): CUANDO una generación termina bien, EL SISTEMA guarda el resultado en el notebook, lo agrega al inicio de la lista y avisa «<Tipo> guardado en el notebook.».
  - Guarda: el tipo, un título por omisión (el tipo con la fecha y la hora, por ejemplo «Resumen · 09/11/2026 13:40»), la fecha y hora, el contenido y la lista de las fuentes usadas, con el nombre mostrado que tenían en ese momento.
  - Todo lo que se genera se guarda: no hay un paso aparte para guardar. Generar de nuevo crea un resultado nuevo y no reemplaza a los anteriores.
- **RF-14.121** `[NUEVO]`: CUANDO el usuario pulsa un resultado de la lista, EL SISTEMA lo abre en el panel «Estudio», con su contenido (con formato en Resumen, Informe y Nota; dibujado en el Mapa mental), su fecha y las fuentes con que se generó, sin llamar al modelo.
  - Los resultados siguen ahí al recargar, cerrar sesión y volver a entrar.
- **RF-14.122** `[NUEVO]` (P10): CUANDO el usuario pulsa «Copiar» en un resultado abierto, EL SISTEMA copia su texto al portapapeles y lo confirma de forma visible.
  - En un Mapa mental copia su contenido como lista de ideas anidada.
- **RF-14.123** `[NUEVO]` (P9): MIENTRAS una o más fuentes con que se generó un resultado ya no están en el notebook (RF-19), EL SISTEMA conserva el resultado sin cambios y muestra el aviso «Una o más fuentes de este resultado ya no están en el notebook.», con la lista de las fuentes con que se generó.
- **RF-14.124** `[NUEVO]` (P1, P2): CUANDO el usuario elige «Quitar resultado» y confirma, EL SISTEMA lo da de baja lógica: desaparece de la lista y su registro se conserva.
  - La confirmación tiene «Quitar» y «Cancelar»; cancelar no cambia nada, y un doble clic en «Quitar» envía una sola solicitud.
  - El usuario no tiene en la interfaz una función para recuperarlo.
- **RF-14.125** `[NUEVO]`: EL SISTEMA no trata un resultado como fuente: ningún resultado se recupera en el chat del notebook, en el chat general, en el chat por tema, en temas similares ni en un resumen, ni cuenta como documento del notebook.
- **RN-01.120** (RN-01, RNF-10): EL SISTEMA no ofrece ninguna función que elimine físicamente un resultado de estudio; generar, guardar y quitar un resultado no son una excepción nueva a RN-01 ni a RNF-10.
  - Los resultados de un notebook dado de baja (spec 009) se conservan con él.

### E. Guardar una respuesta del chat como nota (RF-14, RF-12)
- **RF-14.126** `[NUEVO]` (HU-NUEVA-7, P13, P14): EL SISTEMA muestra «Guardar en notas» bajo cada respuesta terminada del asistente en el chat del notebook.
  - No lo muestra en una respuesta que se está transmitiendo, cancelada o terminada en error.
- **RF-14.127** `[NUEVO]`: CUANDO el usuario pulsa «Guardar en notas», EL SISTEMA guarda una Nota con la pregunta, la respuesta y las fuentes citadas, tal como se vieron, con el título por omisión «Nota · <fecha y hora>», y la agrega al inicio de la lista de resultados.
  - Un doble clic guarda una sola nota.
  - Guardar no vuelve a llamar al modelo, y las citas no se recalculan.
  - Una nota se abre, se copia y se quita como los demás resultados.
- **RF-14.128** `[NUEVO]`: DESPUÉS de guardarse, EL SISTEMA muestra el botón de esa respuesta como «Guardada» y desactivado, para que no se guarde dos veces por accidente.

### F. Aislamiento y bitácora (RNF-07, RF-21)
- **RNF-07.120** `[NUEVO]` (RNF-07, RF-17): EL SISTEMA muestra, abre, copia, genera y quita resultados solo al dueño del notebook.
  - SI el notebook es ajeno, no existe, está dado de baja o su identificador no es válido, ENTONCES responde igual que hoy (404 uniforme, sin revelar si existe) y no llama al modelo.
  - SI el resultado no pertenece a ese notebook, ENTONCES se rechaza igual.
- **RNF-07.121** `[NUEVO]`: EL SISTEMA no incluye nunca documentos ni resultados de otros usuarios en una generación.
- **RF-21.120** `[NUEVO]` (RF-21): CUANDO una generación termina, EL SISTEMA la registra en la bitácora (tipo «Generar Resultado de Estudio») con la clave del notebook, el número del resultado, el tipo de resultado y el número de fuentes usadas.
  - SI la generación falla (error del motor, tope de tiempo, rechazo por tamaño, salida inválida), ENTONCES la registra igual, con un motivo fijo y sin resultado.
  - Cancelar o abandonar la generación no se registra (como una consulta abandonada, RF-21).
- **RF-21.121** `[NUEVO]`: CUANDO el usuario guarda una nota o quita un resultado, EL SISTEMA lo registra en la bitácora (tipos «Guardar Nota» y «Quitar Resultado de Estudio») con la clave del notebook y el número del resultado.
- **RF-21.122** `[NUEVO]` (RF-21, RNF-07.24): EL SISTEMA no guarda en la bitácora el contenido de un resultado, su título, el nombre de las fuentes ni el del notebook.
  - Un intento sobre un notebook o resultado ajeno o inexistente se registra solo como error de acceso con su motivo, sin clave ni identificador.
  - Abrir y copiar un resultado no se registran.
- **RF-21.123** (RF-21): SI el registro en la bitácora falla, ENTONCES la acción se completa de todas formas.

### G. Columnas de `/notebooks`: plegar y ajustar el ancho (RNF-04, RF-17) — cambio JJ1 (12/11/2026)
Motivo (Andrés): con el notebook abierto hay cuatro columnas (la lista de notebooks, «Fuentes», el chat y «Estudio»); hoy se pueden plegar, pero no cambiar su ancho. Quiere agrandarlas o achicarlas arrastrando la línea que las divide, como las columnas de Excel. El plegado ya existe (10/11/2026) y aquí se documenta; lo nuevo es el ajuste del ancho. Todo es de interfaz y de escritorio: sin servidor, base de datos ni bitácora, y sin librerías nuevas (se hace con eventos de puntero y Tailwind).
- **RNF-04.123** (RNF-04; ya implementado el 10/11/2026, documentado aquí): MIENTRAS la pantalla es de escritorio (desde 1024 px), EL SISTEMA permite plegar y mostrar de nuevo la lista de notebooks, «Fuentes» y «Estudio», cada una con su botón («Plegar lista de notebooks» / «Mostrar lista de notebooks», «Plegar Fuentes» / «Mostrar Fuentes», «Plegar Estudio» / «Mostrar Estudio»); el chat ocupa todo el ancho que dejan las demás, y la decisión se recuerda en el navegador.
- **RNF-04.124** `[NUEVO]` (RNF-04; JJ1): MIENTRAS la pantalla es de escritorio (desde 1024 px) y la columna no está plegada, EL SISTEMA muestra en el borde que separa la lista de notebooks de «Fuentes», «Fuentes» del chat y el chat de «Estudio» una línea divisoria que se puede arrastrar con el mouse (o el dedo) para cambiar el ancho de la columna que la lleva: la lista de notebooks, «Fuentes» o «Estudio»; el chat ocupa el resto.
  - Arrastrar hacia la derecha agranda la lista de notebooks y «Fuentes», y achica «Estudio»; hacia la izquierda, al revés.
  - El puntero cambia a `col-resize` sobre la línea y mientras se arrastra no se selecciona texto de la página.
  - El ancho cambia mientras se arrastra, no solo al soltar, sin perder la posición del chat ni de lo que se está escribiendo.
- **RNF-04.125** `[NUEVO]` (JJ1): CADA columna ajustable tiene un ancho mínimo y uno máximo, y el chat tiene un mínimo:
  - lista de notebooks: de fábrica 224 px, mínimo 180 px, máximo 400 px;
  - «Fuentes»: de fábrica 240 px, mínimo 200 px, máximo 480 px;
  - «Estudio»: de fábrica 256 px, mínimo 220 px, máximo 560 px;
  - el chat: nunca menos de 280 px, medido en el área de contenido (la pantalla menos el menú lateral de ServIA si está abierto). SI agrandar una columna dejaría al chat por debajo, ENTONCES la columna se detiene en el ancho que deja al chat en 280 px.
  - SI el área es tan angosta que ni con las tres columnas en su ancho mínimo (600 px en total) el chat llega a 280 px, ENTONCES las columnas quedan en su mínimo y el chat toma lo que reste.
  - Arrastrar más allá de un límite deja la columna en ese límite, sin error ni salto.
- **RNF-04.126** `[NUEVO]` (JJ1): EL SISTEMA recuerda el ancho elegido de cada columna en este navegador (como el plegado) y lo aplica al volver a abrir `/notebooks`, al recargar y al abrir otro notebook.
  - Es de ese navegador y no de la cuenta ni del notebook: no se guarda en el servidor.
  - SI no se puede leer o guardar (almacenamiento bloqueado o un valor dañado o fuera de los límites), ENTONCES se usa el ancho de fábrica (o el límite más cercano) y la pantalla funciona igual; el valor dañado nunca rompe la pantalla.
- **RNF-04.127** `[NUEVO]` (JJ1): CUANDO el usuario hace doble clic en una línea divisoria, EL SISTEMA devuelve esa columna a su ancho de fábrica, y lo recuerda como cualquier otro ancho.
- **RNF-04.128** `[NUEVO]` (RNF-04, accesibilidad; JJ1): cada línea divisoria se puede usar con el teclado: es enfocable, con rol `separator` y orientación vertical, y su texto accesible dice qué columna cambia («Cambiar el ancho de la lista de notebooks», «…de Fuentes», «…de Estudio»); las flechas izquierda y derecha cambian el ancho en 16 px y, con Mayús, en 64 px, dentro de los mismos límites; Inicio la devuelve al ancho de fábrica.
- **RNF-04.129** `[NUEVO]` (JJ1): CONSERVA lo ya hecho: una columna plegada sigue ocupando el ancho de su riel (como hoy) y no muestra línea divisoria; al mostrarla de nuevo vuelve al último ancho elegido, no al de fábrica. La pantalla pequeña (menos de 1024 px, verificada a 616 px) no cambia: un solo panel a la vez con sus pestañas (RNF-04.120) y sin líneas divisorias.
  - MIENTRAS la pantalla es pequeña (menos de 1024 px), EL SISTEMA ignora los anchos elegidos, muestra cada panel a todo el ancho y no muestra líneas divisorias; los anchos guardados se conservan y se aplican de nuevo al pasar a una pantalla de escritorio (por ejemplo, al girar una tableta o ensanchar la ventana).
  - La línea se arrastra con el mouse y con el dedo (eventos de puntero), en pantallas táctiles de 1024 px o más.
  - MIENTRAS la ventana se hace más angosta (o se abre el menú lateral), EL SISTEMA reduce el ancho mostrado de las columnas ajustadas lo necesario para que el chat conserve su mínimo (RNF-04.125), sin perder el ancho guardado: al ensanchar la ventana vuelve a verse.

## Requisitos no funcionales
- **RNF-09.120** `[NUEVO]` (RNF-09): TODA la generación (análisis, unión, estructura del mapa mental) corre en la infraestructura local; no se hace ninguna solicitud saliente a servicios de IA externos ni se carga ningún recurso externo para dibujar el mapa mental.
- **RNF-03.120** `[NUEVO]` (RNF-03): EL SISTEMA muestra un mensaje visible en español para cada resultado posible de una acción del Estudio: guardado, error, cancelación, tope de tiempo, rechazo por tamaño, sin fuentes marcadas.
- **RT-07.120** (RT-06, RT-07): EL SISTEMA muestra todo el texto nuevo en español y con «tema» y «Usuario Gubernamental»; ninguna pantalla nueva dice «expediente».
- **RNF-04.122** `[NUEVO]` (RNF-04): la interfaz del Estudio se verifica a 1366 px y a 616 px de ancho, con la consola sin errores.
- **RNF-04.130** `[NUEVO]` (JJ1): arrastrar una línea divisoria no genera errores en la consola ni desplazamiento horizontal de la página, a 1366 px y a 1024 px.
- La calidad del texto que produce el modelo no se mide (principio 4 de la constitución): se prueba su estructura (secciones del Informe, estructura válida del Mapa mental, fuentes citadas dentro de la selección, español), no su redacción.

## Casos límite
- Ancho de columnas (JJ1): arrastrar y soltar fuera de la ventana termina el arrastre sin dejar la línea «pegada»; hacer clic en la línea sin moverla no cambia el ancho; un doble clic cuenta como restablecer y no como un arrastre.
- Ancho de columnas (JJ1): con las tres columnas en su ancho de fábrica (720 px en total) el chat mide lo que reste del área de contenido: en una pantalla ancha sobra, y en una angosta o con el menú lateral abierto las columnas se muestran reducidas hacia su mínimo (RNF-04.129) para que el chat conserve 280 px mientras sea posible.
- Ancho de columnas (JJ1): el ancho guardado fuera de los límites, no numérico o de otra versión se corrige al límite o al de fábrica; el almacenamiento bloqueado (ventana privada) no impide ajustar el ancho en esa sesión.
- Ancho de columnas (JJ1): dos pestañas del navegador abiertas guardan cada una su último ancho; al cargar manda el último guardado, sin sincronizarse en vivo.
- Ancho de columnas (JJ1): plegar una columna mientras se arrastra otra no rompe el arrastre; durante una generación del Estudio o una respuesta del chat en curso, cambiar los anchos no la interrumpe.
- Una sola fuente marcada y corta: genera con una sola parte, sin paso de unión visible.
- Fuentes marcadas en Pendiente o Error junto con otras Procesado: solo cuentan las Procesado.
- Se desmarca una fuente mientras se genera: no afecta la generación en curso (usa la selección con que empezó); sí afecta a la siguiente.
- Se quita una fuente mientras se genera con ella: la generación puede terminar sin ese contenido; el resultado lista las fuentes que realmente usó. [Por confirmar en el plan.]
- Pulsar un botón de generar dos veces seguidas: una sola generación.
- El notebook no tiene fuentes Procesado: botones desactivados (RF-11.121).
- Se recarga la página con un resultado abierto: el resultado sigue en la lista; no se reabre solo.
- Dos pestañas del mismo usuario: la segunda generación se rechaza mientras la primera está en curso (RF-11.131).
- Resultado de un notebook al que se le cambia el nombre o se le cambia el nombre a una fuente: el resultado conserva los nombres de las fuentes de cuando se generó.
- Un Resumen o un Informe sin citas válidas dentro de la selección: se guarda con la sección «Fuentes consultadas» agregada por el sistema (RF-12.120); solo una salida vacía es inválida (RF-11.125).
- Quitar la última fuente del notebook: los resultados quedan con el aviso de RF-14.123; los botones de generar se desactivan.
- Una nota con una respuesta que citó una fuente que ya no existe: se muestra igual, con el aviso de RF-14.123.

## Fuera de alcance
- Ancho de columnas (JJ1): reordenar o intercambiar columnas, cambiar la altura de un panel, ajustar el menú de navegación lateral de ServIA, anchos distintos por notebook, sincronizarlos entre dispositivos o con la cuenta, y plegar con doble clic.
- Ancho de columnas (JJ1): arrastrar en pantalla pequeña (menos de 1024 px): allí se ve un solo panel a la vez (RNF-04.120).
- Campo de enfoque o indicaciones del usuario (P8); cambiar el título de un resultado; descargar un resultado como archivo o imagen (P10).
- Las demás salidas de NotebookLM: tarjetas didácticas, cuestionario, infografía, tabla de datos, resumen en audio o en video (P13).
- Compartir resultados con otros usuarios (RN-03, RF-17).
- Generar en segundo plano con la página cerrada, y una cola de varias generaciones (P5, P6).
- Convertir un resultado en una fuente del notebook, o conversar sobre un resultado.
- Recuperar un resultado quitado desde la interfaz; editar, reordenar o buscar dentro de los resultados.
- Persistir la selección de fuentes marcadas (sigue como en la 009b, RF-11.103).
- Marcar o desmarcar resultados; el Estudio en el chat general, el chat por tema o temas similares.
- Que una generación cubra fuentes de varios notebooks.

## Criterios de finalización
- Cada requisito tiene al menos una prueba automatizada que pasa (o su exención justificada en el plan) y su verificación manual.
- Verificación manual de Andrés (1366 y 616 px, consola limpia, Usuario Gubernamental y comprobación de que el Administrador no entra): generar los tres tipos con varias fuentes, ver el avance, cancelar, forzar el tope, guardar una nota, reabrir tras recargar, quitar una fuente y ver el aviso, quitar un resultado, y confirmar en la base que el resultado quitado se conserva y que la bitácora no guarda contenido.
- Documentación: el desarrollo va primero (decisión de Andrés, 09/11/2026). Durante la implementación solo se mantiene esta spec al día; la actualización de la documentación de planificación (ERS, CU-19 nuevo, HU-NUEVA-5, 6 y 7, Modelo Relacional y diagramas) es una única tarea final, de texto propuesto y sin PDF, que se puede diferir a la entrega final de la documentación.
- JJ1, pruebas: e2e en `notebooks-estudio.spec.js` (solo escritorio, 1366 px; a 616 px se comprueba que no hay líneas): arrastrar cada línea cambia el ancho de la columna correcta y el chat toma el resto; los límites mínimo y máximo y el mínimo del chat; el ancho sobrevive a una recarga; el doble clic restablece; el teclado (flechas, Mayús, Inicio) y los atributos `role="separator"`; la columna plegada no tiene línea y, al mostrarla, vuelve a su ancho elegido; un valor dañado en el almacenamiento se corrige; sin errores en la consola. Sin pruebas de backend.
- JJ1, documentación: RNF-04 del ERS (una frase: las columnas del notebook son ajustables y plegables), HU-NUEVA del ancho de columnas; sin cambios en casos de uso, diagramas ni Modelo Relacional.
- La medición real de tiempos y tamaños con el modelo local (para fijar los topes) queda como entrega del plan, no de esta spec.

## Dudas abiertas
- JJ1 (aprobado por Andrés el 12/11/2026 con «sí», tomando las propuestas): (a) los límites y el ancho de fábrica de la tabla de RNF-04.125 (lista 180-400, Fuentes 200-480, Estudio 220-560, chat mínimo 280; el mínimo del chat pasó de 360 a 280 px el 12/11/2026 al implementar, porque a 1366 px el chat ya mide unos 360 px con las columnas de fábrica y 360 no dejaba margen para agrandar ninguna); (b) que el ancho se recuerde por navegador y no por cuenta ni notebook; (c) que el doble clic restablezca solo esa columna y no las tres; (d) sin librerías nuevas, solo eventos de puntero; (e) que en un área angosta las columnas se muestren reducidas (sin perder el ancho guardado) para que el chat conserve 280 px mientras sea posible.
Resueltas por omisión al implementar (09/11/2026), a confirmar con Andrés:
- Valores del tamaño y del tiempo máximo: 20 partes y 900 s, configurables por entorno; falta medirlos con el modelo real (el chat tiene 180 s).
- Longitud del Resumen (120 a 250 palabras, indicada en las instrucciones al modelo, sin prueba automática por ser calidad del LLM), del Informe (título, secciones y «Conclusiones») y del Mapa mental (hasta 8 ramas por nodo, 3 niveles y 60 nodos; lo que sobra se poda, no invalida).
- Copiar un Mapa mental como lista anidada de texto (RF-14.122): implementado así.
- La confirmación al quitar un resultado (RF-14.124) y el botón «Guardada» (RF-14.128): implementados por coherencia con «Quitar documento» (RF-19) y con el chat.
- Abrir y copiar un resultado no se registran en la bitácora (como marcar o desmarcar una fuente en la 009b).
- Sin resolver: si el modelo está ocupado con la consulta de otro usuario (atiende una a la vez), la generación espera su turno en Ollama y el tiempo de espera cuenta contra el tope de 900 s; hoy el chat tiene el mismo problema.
- Sin resolver: la marca «una generación a la vez por usuario» vive en la memoria del proceso de la API (un solo proceso la atiende); con varios procesos habría que moverla a Redis.
- ✅ Aprobado por Andrés (09/11/2026): la migración que crea la tabla de resultados. Sin dependencia nueva del frontend: el Mapa mental se dibuja con HTML y Tailwind propios.

## Decisión del cambio «ancho de las columnas ajustable» (12/11/2026, Andrés: JJ1)
- **JJ1**: las columnas de `/notebooks` (lista de notebooks, «Fuentes», «Estudio») se pueden agrandar y achicar arrastrando la línea que las divide, con límites, doble clic para restablecer, uso con teclado y el ancho recordado en el navegador; el chat ocupa el resto y el plegado existente se conserva. Motivo: el chat y las columnas se ven chicas o grandes según la pantalla y el trabajo del momento. Solo de interfaz y de escritorio; sin servidor, migración ni dependencias nuevas.
