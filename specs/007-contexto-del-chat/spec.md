# Spec 007 — Contexto y señales del chat (corrección)
Estado: aprobada (29/10/2026). Alcance aprobado (JJJ1 = A); P1-P9, P-A a P-H, D1, Q1-Q4, R1-R5, P-α, P-β, Q-A, Q-B y D-2 resueltas. Cambio tras el plan (P-1 a P-5, RF-11.69) confirmado por Andrés (29/10/2026).

## Contexto y objetivo
- En el piloto de la 006 (30 PDF de Nexus: 27 Procesado, 3 Error) el chat general nunca mostró respuesta. Diagnóstico comprobado (solo lectura, 28-29/10/2026):
  1. **Contexto sin tope**: hasta 15 fragmentos de hasta ~7.000 caracteres, encabezados, 20 mensajes de historial e instrucciones de 13.448 caracteres, para una ventana de 8.192 tokens. El motor midió ~85.000 tokens de entrada; lo citado explica unos 40.000: el resto lo identifica el plan (RF-11.60).
  2. Si la entrada supera la ventana, el motor la recorta a 4.098 tokens conservando el final: **descarta las instrucciones**. Incumple RF-11 y RF-12 aunque llegue respuesta.
  3. La **reformulación** de la pregunta con el historial es otra llamada al motor, también sin tope. Solo la hace el chat general: el chat por tema y el notebook no usan la pregunta para buscar, sino los primeros fragmentos del tema por número (hallazgo del plan).
  4. **Sin señales antes del primer texto**: la espera real (carga del modelo 51-80 s más el procesamiento) supera los 30 s de RF-16 y la interfaz corta la consulta, que el motor termina igual. Las «etapas» visibles son una animación, no el avance real.
  5. El aviso de RF-16 está en voseo («Intentá de nuevo.»), contra el principio 7 de la constitución.
- Es una **corrección de errores** (testing.md: puede ir antes que las funciones nuevas), con prueba de regresión primero. Según el paso 3, prueba también los requisitos existentes del módulo (RF-16.40 de la 005 nunca se automatizó).

## Trazabilidad
- ERS V1.8: RF-08, RF-11, RF-12, RF-16, RF-20 (resumen con IA, Q2), RF-21, RNF-01, RNF-04, RNF-09, RNF-10, RN-01, RA-02 (RA-02.47, presupuesto e2e). Como regresión, sin cambios: RF-11.40-43 (005), RF-11.1-3 y RF-12.1 (004).
- HU-08, HU-11, HU-12, HU-16, HU-20 · CU-07 (paso 10), CU-09 (pasos 5-8, FE-01, FE-02, FE-04 nuevo), CU-14 (resumen).
- «Estado actual» que cierra: ninguno documentado (el error no figura en el ERS). Ver el «Anexo» (`plan.md`, Anexo C).
- Contradice el ERS vigente en tres puntos, que esta spec propone cambiar: RF-16 reinicia el plazo «con cada fragmento de texto» (aquí, con cualquier dato del stream); su aviso dice «Intentá»; RN-01 no admite el re-fragmentado.
- Requisitos nuevos en el bloque **.60+** (004: .1+, 004a: .20+, 004b: .30+, 005: .40+, 006: .50+).
- `[NUEVO]` marca todo requisito que exige texto nuevo o cambiado en el ERS (está en el «Anexo», hoy `plan.md`, Anexo C); sin la marca, el requisito solo detalla texto vigente (RF-12.60, RNF-04.60, RNF-09.60). RF-16.40 es de la 005; el cambio de su aviso va en RF-16.61.

## Usuarios
Usuario Gubernamental: consulta en los tres chats y carga documentos. Administrador: no consulta ni carga (RN-03); sin cambios.

## Historias de usuario
HU-08, HU-11, HU-12, HU-16, HU-20 (sin historias nuevas).

## Definiciones
- **Ventana**: 8.192 tokens de entrada más salida por llamada al motor. Sin ventana explícita, el motor usa 4.096.
- **Reserva de respuesta**: 1.024 tokens. **Presupuesto de entrada**: ventana menos reserva = **7.168 tokens**.
- **Entrada**: todo lo que recibe el motor en una llamada (instrucciones, fragmentos con sus encabezados, historial con sus marcas de rol y separadores, pregunta y cualquier otro contenido).
- **Conteo**: estimación prudente de caracteres por token, **configurable en el servidor, por omisión 3,5** (medido: 3,67 en circulares), para ajustarla sin tocar código (Q-B).
  - Un solo estimador: el que usa el código es el que usan las unitarias. Solo CF-1 y la verificación manual lo contrastan con el motor.
  - Los tokens de plantilla del modelo (cabeceras de rol y de turno que agrega el motor) no se cuentan aparte: los absorbe el margen entre el 3,5 y lo medido, no la reserva de respuesta. CF-1 lo comprueba, porque el conteo real los incluye.
- **Instrucciones**: el texto fijo de cada llamada (en el notebook, incluidas las reglas sobre imágenes). La lista de archivos del notebook no es instrucción: ver RF-12.62.
- **Pregunta**: la que escribe el usuario, que es la que recibe la llamada de respuesta (la reformulada solo sirve para buscar). En el notebook, la que se envía tras adaptar las referencias a imágenes.
- **Espacio mínimo de fragmento**: tamaño máximo de fragmento configurado (RF-08.60) más una estimación fija de 500 caracteres de encabezado (P-α), con el conteo (por omisión 2.000 caracteres ≈ 572 tokens).
  - En el notebook suma además una estimación fija de **300 caracteres** de la línea de su archivo en la lista (RF-12.62; cubre un nombre de hasta 255): por omisión 2.300 caracteres ≈ 658 tokens (M1).
- **Mensaje**: cada pregunta del usuario y cada respuesta del asistente se cuentan por separado, como ya guarda y limita el historial (hoy 20 mensajes = 10 turnos). «Los 2 últimos mensajes» son, en un historial normal, la última pregunta y su respuesta.
- **Página**: estimación de 2.500 caracteres por página del texto original, desde el carácter 0.
- **Dato del stream**: cualquier evento del servidor en una consulta: texto, etapa, señal de vida, fin o error.
- **Turno terminado**: la respuesta llegó completa al evento de fin.
- **Los tres chats**: chat general, chat por tema y NotebookServIA. Todo requisito aplica a los tres, salvo que diga otra cosa.
- **Resumen**: el resumen con IA de un resultado de Temas Similares (RF-20, CU-14). Solo le aplican RF-11.63 y el bloque E.

## Requisitos funcionales

### A. Contexto acotado
- **RF-11.60** (RF-11, RF-12; CU-09 p. 6, FE-01) `[NUEVO]`: EL SISTEMA arma cada llamada al motor en los tres chats (reformulación, respuesta y reintento por respuesta vacía) con una entrada que nunca supera el presupuesto de 7.168 tokens.
  - *Regresión* (unitaria, primero): el plan identifica antes qué lleva la entrada a ~85.000 tokens, y la regresión reproduce esa entrada (como mínimo 15 fragmentos de 7.000 caracteres y 20 mensajes largos).
  - El motor simulado captura **cada** llamada; hoy alguna excede el presupuesto (falla); tras la corrección, ninguna, con el conteo (Definiciones). Se repite por chat.
- **RF-11.61** (RF-11, RF-12; P4, P-A) `[NUEVO]`: EL SISTEMA nunca recorta ni omite las instrucciones ni la pregunta; las instrucciones van completas al principio, y el resto se reparte así:
  - historial: como máximo **min(20 % del presupuesto, lo que quede tras instrucciones, pregunta y espacio mínimo de fragmento)**, con los mensajes más recientes y completos; uno que no cabe entero se omite junto con los anteriores;
  - fragmentos: el espacio restante, **hasta 8**, en orden de relevancia y enteros; uno que no cabe se omite completo y se prueba el siguiente. No se garantiza que quepan los 8.
  - *Prueba*: unitarias (historial largo, fragmentos de sobra, ambos, historial corto que cede su espacio, mensaje mayor que el 20 %, fragmento grande saltado y siguiente incluido).
- **RF-11.62** (RF-11; CU-09 FE-04 nuevo; R5) `[NUEVO]`: SI las instrucciones de la respuesta, la pregunta y el espacio mínimo de fragmento superan juntos el presupuesto, ENTONCES EL SISTEMA no llama al motor (tampoco para reformular) y responde con el error «La pregunta es demasiado larga. Acórtela e intente de nuevo.».
  - Se evalúa antes de cualquier llamada y antes de emitir etapas: el stream lleva solo el error. El historial no cuenta, porque cede su espacio (RF-11.61).
  - Garantiza espacio para un fragmento de hasta el tamaño configurado (RF-08.60), no para uno antiguo mayor (Casos límite, Q-A).
  - *Prueba*: unitaria (justo bajo el límite → llama; justo sobre → el motor simulado no recibe llamadas; en el notebook, con su espacio mínimo) e integración (solo el evento de error, en español, sin etapas).
- **RF-11.63** (RF-11, RF-20, RNF-01; P1, P-H, Q2) `[NUEVO]`: EL SISTEMA envía la ventana de 8.192 y la reserva de 1.024 en cada llamada al motor (los tres chats y el resumen), y el presupuesto se calcula con esos mismos valores.
  - Toda la configuración del servidor y su ejemplo usan esos valores por omisión; no queda vigente ningún valor heredado (2.048, 4.096 ni 32.768).
  - *Prueba*: unitaria (cada llamada y el presupuesto leen la misma configuración; por omisión 8.192/1.024). *Manual*: el registro del motor no muestra ningún aviso de entrada recortada.
- **RF-11.65** (RF-11; P-G) `[NUEVO]`: EL SISTEMA recupera por omisión **8 fragmentos** por consulta en los tres chats y en la búsqueda de respaldo; el valor es configurable en el servidor, y una solicitud puede pedir menos, nunca más.
  - Una solicitud con cantidad ≤ 0 usa el valor del servidor (B1). Un valor del servidor ≤ 0 lo trata RF-08.62.
  - *Prueba*: unitaria (solicitud con más de 8 → 8; con 3 → 3; con 0 y con −1 → 8; búsqueda de respaldo ≤ 8; cada chat).
- **RF-11.66** (RF-11, CU-09 p. 8; P-B, P-1) `[NUEVO]`: CUANDO la pregunta llega con historial, en cualquiera de los tres chats, EL SISTEMA la reformula con solo los **2 últimos mensajes** y un único texto de reformulación, común a los tres y no más largo que las instrucciones de respuesta de ningún chat; su tiempo cuenta dentro del tope de RF-16.62.
  - Si la llamada no cabe, omite el mensaje más antiguo; si no cabe ninguno, no reformula y busca con la pregunta original. Nunca recorta la pregunta (cabe siempre, por RF-11.62).
  - La reformulada solo sirve para buscar (Definiciones, «Pregunta»). En el notebook se reformula la pregunta ya adaptada en sus referencias a imágenes.
  - El texto nuevo se muestra a Andrés en el plan antes de aplicarlo.
  - *Prueba*: unitaria con el motor simulado en cada uno de los tres chats: ≤ 2 mensajes y dentro del presupuesto; mensajes enormes → 1 o 0 mensajes, y con 0 no hay llamada de reformulación; sin historial, no hay llamada de reformulación.
- **RF-11.69** (RF-11, CU-09 p. 5; P-1) `[NUEVO]`: EL SISTEMA recupera los fragmentos del chat por tema y del notebook por búsqueda semántica con la pregunta (la reformulada, si la hay), restringida a ese tema o notebook, en orden de relevancia y hasta la cantidad de RF-11.65.
  - Devuelve los más cercanos aunque su similitud sea baja (sin umbral mínimo), para que una pregunta general sobre el tema reciba fragmentos (P-5).
  - Nunca devuelve fragmentos de otro tema o notebook; un tema o notebook sin fragmentos devuelve ninguno (Casos límite).
  - *Regresión* (integración, primero): tema `PRUEBA` con más de 8 fragmentos donde el único que contiene un término inventado tiene el número de fragmento más alto: hoy no se recupera (falla); tras la corrección, va primero. Lo mismo en un notebook `PRUEBA`.
  - *Prueba*: integración: un fragmento casi idéntico de otro tema no aparece; pregunta sin relación con el tema → 8 fragmentos del tema.
- **RF-12.60** (RF-12; HU-12): EL SISTEMA incluye en el encabezado de cada fragmento enviado su nombre de archivo, su tema y su ruta de descarga, y ningún nombre ni ruta de un fragmento omitido aparece en la entrada.
  - Así el enlace de descarga solo puede apuntar a archivos de fragmentos enviados.
  - *Prueba*: unitaria sobre la entrada capturada; RF-11.40 (cita descargable en el chat general, e2e) sigue pasando.
- **RF-12.61** (RF-12; P3, P-C) `[NUEVO]`: EL SISTEMA usa **tres textos de instrucciones** (general, tema, notebook), cada uno de **≤ 20 % del presupuesto** (~1.430 tokens, ~5.000 caracteres), en español neutro sin voseo, con todas las reglas de RF-12:
  - responder solo con los fragmentos enviados, sin conocimiento general; decir cuando el contexto no alcanza;
  - citar el archivo de origen de cada afirmación relevante, sin inventar nombres ni atribuir a otro documento;
  - pedir aclaración ante una referencia ambigua a un documento; responder en español.
  - Cada texto conserva lo propio de su chat (en el tema, la redacción de documentos; en el notebook, el uso de su lista de archivos y el tratamiento de las imágenes).
  - Los textos se muestran a Andrés en el plan antes de aplicarlos («cambiar prompts»).
  - *Prueba*: unitaria de estructura por texto (tamaño máximo, presencia de cada regla, sin «Intentá», «vos» ni otras formas de voseo), sin texto exacto.
- **RF-12.62** (RF-12; P-C) `[NUEVO]`: EL SISTEMA arma la lista de archivos del notebook solo con los fragmentos enviados en esa llamada, sin una búsqueda aparte; tiene a lo sumo 8 archivos.
  - Cada línea de la lista cuenta en el espacio de fragmentos, junto con el primer fragmento de su archivo: un fragmento cabe solo si caben él, su encabezado y, si su archivo es nuevo, su línea.
  - El espacio mínimo de fragmento del notebook incluye esa línea (Definiciones, M1); el título fijo de la lista cuenta con las instrucciones.
  - *Prueba*: unitaria (archivo de un fragmento omitido → ausente de la lista; entrada con la lista ≤ presupuesto; pregunta justo bajo el límite de RF-11.62 en el notebook → cabe un fragmento con su línea).

### B. Fragmentación (P2, P6, P-E)
- **RF-08.60** (RF-08; HU-08; P2) `[NUEVO]`: EL SISTEMA divide el texto en fragmentos de tamaño máximo y solapamiento configurables, en toda carga (Ingesta, notebooks, imágenes y audio). Por omisión: **1.500 caracteres** y **200 de solapamiento**.
  - *Regresión* (unitaria, primero): con un tamaño configurado distinto, ningún fragmento lo supera y dos consecutivos comparten el solapamiento (hoy falla: tamaño fijo).
  - *Prueba*: integración: un documento `PRUEBA` cargado deja en Qdrant fragmentos de ≤ 1.500 caracteres, con tema, archivo y página.
- **RF-08.61** (RF-08; R4) `[NUEVO]`: EL SISTEMA asigna a cada fragmento su página de inicio y de fin, calculadas con la posición real de su primer y último carácter en el texto original, sin volver a dividir el texto por separado.
  - *Prueba*: unitaria con un texto de 7.000 caracteres y posiciones conocidas (fragmentos que empiezan y terminan a ambos lados de 2.500 y 5.000): cada página coincide con la calculada a mano.
- **RF-08.62** (RF-08, RF-11; B1) `[NUEVO]`: SI al arrancar la configuración es incoherente, ENTONCES EL SISTEMA escribe un aviso con el motivo en el registro y usa **todos** los valores por omisión de esta spec, no solo el incoherente. Es incoherente:
  - tamaño de fragmento ≤ 0, o solapamiento < 0 o ≥ tamaño;
  - cantidad recuperada ≤ 0, o caracteres por token ≤ 0;
  - ventana ≤ 0, reserva ≤ 0 o reserva ≥ ventana (presupuesto ≤ 0);
  - intervalo de la señal de vida (RF-16.60) ≤ 0, tope (RF-16.62) ≤ 0, o intervalo ≥ tope (P-3);
  - cualquier valor no numérico;
  - presupuesto menor que el mínimo: el espacio mínimo de fragmento del notebook (el mayor) supera el 60 % del presupuesto (lo que dejan instrucciones e historial en su máximo de 20 % cada uno).
  - Todos y no solo el incoherente: una mezcla de valores propios y por omisión puede seguir siendo incoherente; los valores por omisión lo son entre sí y se verifican de una vez.
  - *Prueba*: unitaria por cada caso (aviso y todos los valores por omisión) y una coherente sin aviso.
- **RF-08.63** (RF-08, RN-01; P6, P-E) `[NUEVO]`: EL SISTEMA ofrece un procedimiento interno, sin pantalla ni ruta de la API, que vuelve a fragmentar desde su archivo guardado los documentos Procesado de los temas indicados.
  - Lo ejecuta a mano el desarrollador (o el agente, en la verificación manual aprobada) en el servidor; exige la lista explícita de temas, sin opción «todos».
  - Tiene un modo de **simulación** que solo informa cuántos documentos y fragmentos tocaría; el modo real informa lo mismo al terminar.
  - Por documento: inserta primero los fragmentos nuevos y después borra los anteriores. SI falla la extracción, falta el archivo o falla la inserción, ENTONCES el documento conserva sus fragmentos anteriores (sin restos de los nuevos), se informa y sigue con el siguiente.
  - Conserva la fila, el tema, el archivo, el estado y los metadatos de cada fragmento (incluidos identificador del documento y fecha de carga originales).
  - **Idempotente**: repetirlo deja el mismo número de fragmentos, sin duplicados; también limpia los duplicados de una corrida que falló al borrar.
  - No toca documentos de otros temas ni en otro estado.
  - Uso aprobado en desarrollo: solo los 27 Procesado de NEXUS-Avisos-Corte, NEXUS-Circulares-DE y NEXUS-Circulares-SC; la simulación debe informar 27 antes de la corrida real.
  - *Prueba*: integración en el entorno aislado con documentos `PRUEBA` en dos temas: el indicado queda con fragmentos ≤ 1.500 y las mismas filas y metadatos; el otro, intacto; archivo faltante e inserción fallida conservan los anteriores; dos corridas, mismo resultado; la simulación no cambia nada.

### C. Señales del stream y turno (P5, P9, P-D, P-F, D1)
- **RF-11.64** (RF-11; CU-09 p. 5) `[NUEVO]`: CUANDO el Usuario Gubernamental envía una pregunta, EL SISTEMA emite las etapas «Procesando consulta», «Analizando documentos» y «Generando respuesta», en ese orden y antes del primer texto.
  - La interfaz muestra la etapa que informa el servidor (sustituye a la animación); al llegar el primer texto o un error, el indicador de etapa desaparece.
  - Orden ante un error: el rechazo de RF-11.62 llega sin etapas; un error del motor (CU-09 FE-03) llega después de las etapas ya emitidas, sin emitir las que faltan.
  - *Regresión* (unitaria del stream con el motor simulado, primero): hoy no hay eventos de etapa (falla). *Unitaria*: motor que falla tras «Analizando documentos» → dos etapas y el error. *E2e*: con el motor retenido, las tres etapas aparecen en orden (matriz en RNF-04.60).
- **RF-16.60** (RF-16, RNF-01; HU-16; P5, P-D) `[NUEVO]`: MIENTRAS la consulta sigue en curso sin enviar otro dato (incluida la espera en cola del motor), EL SISTEMA emite una señal de vida al menos cada 10 s; la interfaz reinicia el plazo de 30 s con cualquier dato del stream.
  - La señal de vida no se muestra, no cambia la etapa visible y no se guarda.
  - El intervalo es configurable; en la instancia e2e se programa por prueba (p. ej. 1 s).
  - *Prueba*: unitaria (reloj simulado) e integración con el motor simulado retenido. *E2e*: **motor lento con señal de vida** que tarda más que el plazo en dar el primer texto: la respuesta llega sin aviso de conexión perdida.
- **RF-16.40** (de la 005, se automatiza aquí; RF-16, CU-09 FE-02; P9): SI pasan 30 s sin ningún dato del stream, ENTONCES la interfaz libera el control de envío, conserva el texto recibido y muestra «Se perdió la conexión con el servidor. Intente de nuevo.».
  - *E2e*: **servidor completamente mudo** (ni etapas ni señal de vida); antes de 30 s el control sigue bloqueado.
- **RF-16.61** (RF-16; constitución, principio 7) `[NUEVO]`: los avisos de error que esta spec define o toca (RF-16.40, RF-16.62 y RF-11.62) están en español neutro, sin voseo.
  - *Prueba*: en cada una de sus tres e2e, el texto mostrado es el exacto del requisito y no contiene «Intentá».
- **RF-16.62** (RF-16, RNF-01; P5, P-D, D1, P-2) `[NUEVO]`: SI la consulta supera el tope total de **180 s** (cola, reformulación y respuesta incluidas), ENTONCES EL SISTEMA deja de generar, libera el motor y envía el error «La consulta tardó demasiado. Intente de nuevo.»; la interfaz conserva el texto recibido y libera el control de envío.
  - El reintento por respuesta vacía (CU-09 FE-01) lo hace la interfaz como una consulta nueva: tiene su propio presupuesto (RF-11.60) y su propio tope de 180 s, sin descontar el tiempo de la primera (P-2).
  - SI el usuario cierra la conexión, incluso antes del primer texto, ENTONCES EL SISTEMA lo detecta en a lo sumo un intervalo de señal de vida, deja de generar y libera el motor.
  - El tope es configurable; en la instancia e2e se programa por prueba (p. ej. 5 s).
  - *Prueba*: integración con el motor simulado retenido (tope reducido) y con desconexión antes y después del primer texto: el motor recibe la cancelación y la siguiente consulta se atiende. *E2e*: tope reducido → aviso y control libre.
- **RF-11.67** (RF-11, RF-16; CU-09 FE-02, FE-03, FE-04) `[NUEVO]`: CUANDO llega un evento de error (RF-11.62, RF-16.62 o error del motor), la interfaz quita el indicador de etapa, conserva el texto recibido y libera el control de envío.
  - Para los errores de RF-11.62 y RF-16.62 muestra en la conversación el texto que envía el servidor; el texto del error del motor queda fuera de alcance (FE-03).
  - Un tipo de evento desconocido se ignora sin romper la conversación.
  - *Prueba*: e2e para los dos errores (pregunta larga; tope reducido), con el indicador ausente; el evento desconocido va inyectado en la e2e de RF-11.64 del chat general: la respuesta se completa. El error del motor usa el mismo manejo de evento de error: sin e2e propia (presupuesto e2e); lo cubre la unitaria de RF-11.64.
- **RF-11.68** (RF-11, CU-09 p. 7; P-F, Q3) `[NUEVO]`: EL SISTEMA guarda en el historial solo los turnos terminados; un turno rechazado (RF-11.62), detenido por el tope (RF-16.62), terminado en error del motor (CU-09 FE-03) o abandonado porque el usuario cerró la pestaña o la conexión, antes o después del primer texto, no se guarda.
  - *Prueba*: integración (cada caso → el historial no crece; turno terminado → crece en pregunta y respuesta).
- **RF-21.60** (RF-21, CU-09 p. 7; P-F, Q3, R2, D-2) `[NUEVO]`: CUANDO un turno termina, EL SISTEMA registra la consulta en la bitácora con el tipo existente de consulta (`CONSULTA_RAG`), en los tres chats; hoy la registra al crear la respuesta, antes de generarla.
  - CUANDO rechaza la pregunta (RF-11.62), la detiene por el tope (RF-16.62) o el turno termina en error del motor (CU-09 FE-03), EL SISTEMA registra el mismo tipo con el motivo fijo «pregunta demasiado larga», «tiempo máximo agotado» o «error del motor» en la información adicional. Sin tipo nuevo ni migración.
  - El turno con error del motor no se registra además como terminado, ni se guarda en el historial (RF-11.68).
  - SI el usuario cierra la pestaña o la conexión a mitad de la consulta, ENTONCES EL SISTEMA no registra nada.
  - *Prueba*: integración por chat (turno terminado, rechazo, tope y error del motor: un registro cada uno con su motivo, ninguno doble; desconexión antes y después del primer texto: ninguno).

### D. Requisitos existentes del módulo (testing.md, paso 3)
- RF-11.1-3, RF-12.1 (004) y RF-11.40-43 (005): sus pruebas siguen pasando; la de etapas de la 005 se ajusta solo si mostraba la animación (sin borrarla ni desactivarla).

### E. Resumen con IA de Temas Similares (RF-20; Q2, Q4)
- **Orden actual** del resumen: el que produce hoy su formateador: los primeros **20** fragmentos obtenidos (tope que se mantiene), agrupados por documento con un encabezado por documento, y dentro de cada uno por número de fragmento.
- **RF-20.60** (RF-20; HU-20, CU-14) `[NUEVO]`: EL SISTEMA arma cada llamada al motor para el resumen, incluido cada reintento, con una entrada que nunca supera el presupuesto de 7.168 tokens.
  - Las instrucciones del resumen (con el identificador del tema) van completas; los fragmentos y los encabezados por documento ocupan el espacio restante.
  - *Regresión* (unitaria, primero): con un tema `PRUEBA` de más de 20 fragmentos de 7.000 caracteres, hoy la entrada capturada excede el presupuesto (falla); tras la corrección, en ningún intento.
- **RF-20.61** (RF-20; Q4) `[NUEVO]`: SI el contenido no cabe entero, ENTONCES EL SISTEMA genera el resumen con los fragmentos enteros que quepan, en el orden actual, sin aviso en la interfaz.
  - Recorre ese orden: un fragmento que no cabe entero (con el encabezado de su documento, si es el primero) se omite y se prueba el siguiente, como en RF-11.61. Ninguno se corta.
  - *Regresión* (unitaria, con el tema de RF-20.60): cada fragmento de la entrada es idéntico al original; su orden relativo es el orden actual; la entrada ≤ 7.168 (hoy falla: cortados a 7.000 y entrada excedida).
  - *Prueba*: unitaria con un tema corto que cabe entero (todos sus fragmentos en la entrada) y sin texto nuevo en la respuesta.
- **RF-20.62** (RF-20) `[NUEVO]`: SI las instrucciones del resumen superan por sí solas el presupuesto, ENTONCES EL SISTEMA no llama al motor y responde con el error interno que ya existe para el resumen, sin texto nuevo:
  - servidor (HTTP 500): «Error interno del servidor al generar el resumen» (`backend/app/routes/similarity.py:299`);
  - interfaz: «Error interno del servidor. Intente nuevamente en unos momentos.» (`frontend/services/similarityService.js:367`);
  - la bitácora registra el resumen fallido como hoy (RF-21).
  - *Prueba*: unitaria (el motor simulado no recibe llamadas) e integración (500 con el texto literal del servidor).
- Las instrucciones del resumen no cambian de texto; si el plan concluye que deben acortarse, para y pregunta.

## Requisitos no funcionales
- **RN-01.60** (RN-01, RNF-10; P-E) `[NUEVO]`: ningún cambio borra documentos, filas, archivos ni temas. En desarrollo, solo se reemplazan los fragmentos de los 27 documentos de RF-08.63, y solo después de aplicar la primera parte del «Anexo» (principio 5, «Datos» de `CLAUDE.md`, RN-01 y RNF-10 del ERS).
- **RNF-09.60** (RNF-09): todo sigue local; sin modelo nuevo (principio 6). El ejemplo de configuración del servidor apunta al motor local con el modelo vigente (`llama3.1:8b`), no a un servicio en la nube como hoy.
  - *Verificación*: revisión del ejemplo en la tarea de cierre (sin prueba automatizada: es un archivo de ejemplo que el servidor no lee).
- **RNF-04.60** (RNF-04; B3): matriz de e2e nuevas (chat × ancho). El chat por tema usa la misma interfaz del stream que el general; el notebook tiene su propia página.

  | Prueba | General | Tema | Notebook |
  |---|---|---|---|
  | RF-11.64 etapas (+ evento desconocido de RF-11.67 en el general) | 1366 y 616 | — | 1366 |
  | RF-16.60 motor lento con señal de vida | 1366 y 616 | — | — |
  | RF-16.40 servidor mudo | 1366 y 616 | — | — |
  | RF-16.62 tope (y RF-11.67) | 1366 y 616 | — | — |
  | RF-11.62 pregunta larga (y RF-11.67) | 1366 y 616 | — | 1366 |

  - 12 ejecuciones. Lo de cada chat en el servidor (etapas, rechazo, tope, historial, bitácora) lo cubren las integraciones por chat.
- **Presupuesto e2e** (RA-02.47): lo nuevo suma como máximo **40 s** a la «suite» sobre la línea base: la media de dos corridas de `npm run e2e` antes de la primera tarea de la 007.
  - Estimación: 12 ejecuciones × ~3 s ≈ 36 s (media actual ~3,4 s por prueba; las nuevas, con plazos programados cortos).
  - Las e2e con plazos usan el reloj controlado del navegador (005) y los intervalos programables, sin esperas reales de 30 s.
  - El margen de 40 s es del orden de la variación entre corridas (475-501 s en la 006): un exceso se confirma con una segunda corrida antes de parar y preguntar.
- Sin esquema nuevo, migración ni dependencia.

## Casos límite (los demás están en su requisito)
- Fragmentos antiguos de hasta ~7.000 caracteres fuera de Nexus: entran enteros mientras quepan; los demás se omiten sin dejar su nombre (RF-11.61, RF-12.60, RF-12.62).
- Si todos los fragmentos recuperados son antiguos y grandes y ninguno cabe, se acepta (Q-A): se responde sin fragmentos y la respuesta dice que el contexto no alcanza. La garantía de RF-11.62 vale solo para fragmentos dentro del tamaño configurado.
- Sin fragmentos recuperados: instrucciones, historial y pregunta; la respuesta dice que el contexto no alcanza (RF-12).
- Dos usuarios a la vez con el motor atendiendo una consulta por vez: el segundo recibe señales de vida y su espera cuenta contra los 180 s (RF-16.60, RF-16.62).
- Respuesta de 1.024 tokens con modelo frío y reformulación: debe terminar antes de 180 s (se mide en la verificación manual; si no, se para y se pregunta).

## Fuera de alcance
- El recargador de desarrollo que muere por memoria (`--reload`: «Pregunta antes») y el reinicio espontáneo del motor: hallazgos para `MEMORY.md`.
- Un RNF de tiempo máximo de respuesta; cambiar de modelo; re-puntuar o reordenar los resultados de la búsqueda semántica (la recuperación por relevancia en el chat por tema y el notebook sí entra: RF-11.69).
- La lectura de fragmentos del resumen (RF-20): sigue tomando los primeros 20 en el orden actual.
- Re-fragmentar fuera de los tres temas de Nexus; una pantalla para hacerlo.
- La respuesta de relleno ante un modelo sin texto, el texto técnico del error de conexión (Estado actual de RF-11, FE-03) y RF-06.2.
- Los demás avisos con voseo (p. ej. «Preguntale algo a…» del notebook, CU-09 FA-05): a la spec de mejoras del notebook.
- La causa de fondo de los 3 Error por Tika (P7): sin código; solo su recarga.
- Del resumen: la búsqueda, el formato de su respuesta, los reintentos y el texto de sus instrucciones (salvo RF-20.60-62).

## ⚠️ Pregunta antes (CLAUDE.md) que tocará el plan
- Prompts (RF-12.61, RF-11.66, mostrados antes); `docker-compose.yml` si lo exige RF-11.63; reemplazar los 27 de RF-08.63 tras aplicar la excepción.
- Archivos nuevos (pruebas, CF-1, procedimiento interno); commit y push al cierre. No se tocan esquema, migraciones ni modelos.

## Criterios de finalización
- Cada requisito con su prueba vista en rojo antes del código y luego en verde; las regresiones (RF-11.60, RF-08.60, RF-11.64, RF-20.60) primero.
- `pytest` y `--orden-inverso`: 0 fallos, 0 XPASS, sin `xfail` nuevos. `npm run e2e`: «CORRECTO» dentro del presupuesto e2e.
- **CF-1. Prueba contra el motor real** (antes RNF-01.61; RF-11.60, RF-20.60; Q1): fuera del comando por omisión de pytest (marcador propio excluido, como `infraestructura`); el plan fija marcador y comando.
  - Cubre, con las entradas más grandes que arma el sistema (15 fragmentos largos, 20 mensajes, tema largo), la reformulación y la respuesta de los tres chats y el resumen, con un texto narrativo y otro **denso** (números, siglas, tablas).
  - Las unitarias verifican el presupuesto con el mismo estimador que usa el código; solo CF-1, corrida a mano, lo contrasta con el motor.
  - Por llamada lee el conteo real de entrada del motor (incluye los tokens de plantilla) y falla si hay recorte (conteo > 7.168, o 4.098 con una entrada estimada mayor) o si el conteo real supera el estimado.
  - SI el conteo real supera al estimado (p. ej. con el texto denso), ENTONCES se para y se pregunta a Andrés (Q-B); el ajuste posible es la configuración de caracteres por token, sin tocar código.
  - El plan fija cómo obtener un conteo que no descuente la caché de prefijos del motor y lo comprueba en la versión instalada (Ollama 0.32.14).
  - Se ejecuta a mano en el contenedor del backend (servidor en marcha, GPU libre, modelo descargado), solo con el entorno aislado y datos `PRUEBA`, limpiando lo que crea. Pasa al menos una vez antes del cierre, con su salida (conteo real y estimado por llamada) en la evidencia.
- Verificación manual en desarrollo con el motor real, ambos anchos (Andrés inicia la sesión del Usuario Gubernamental en la ventana del MCP; el agente nunca recibe contraseñas):
  - simulación del procedimiento con los tres temas de Nexus = 27 documentos; tras la corrida real, mismas filas, fragmentos ≤ 1.500 caracteres y el resto de la colección intacto (mismo número de puntos fuera de esos temas);
  - tras reiniciar el motor (modelo frío), una pregunta sobre Nexus en cada chat muestra las etapas, sin aviso de conexión perdida, termina en < 180 s y cita el archivo;
  - el motor informa en cada llamada un conteo ≤ 7.168 y ningún aviso de recorte, también con una conversación de 20 mensajes;
  - el resumen de un resultado de Temas Similares sobre un tema de Nexus se genera, con conteo ≤ 7.168 y sin aviso de recorte;
  - al cerrar la pestaña a mitad de una respuesta: el motor queda libre y ni el historial ni la bitácora tienen un registro nuevo;
  - el Administrador no entra al chat; consola sin errores.
- Recarga (P7), con acceso a `~\Documents\ServIA-fuentes`: Circulares SC 182, 183 y 177 por Ingesta (fila nueva; las anteriores quedan en Error, RF-07.51).
  - Luego los **128 PDF** restantes de la 006 (Asamblea 48, CONARE 30, Kimuk 19, SINALEVI 31) en sus temas, en tandas de ≤ 10; un Error nuevo va a `MEMORY.md`, sin corregirlo aquí.
- Antes de la corrida real de RF-08.63: la primera parte del «Anexo» aplicada por Andrés (principio 5, «Datos» de `CLAUDE.md`, RN-01 y RNF-10 del ERS). Sin ella, el procedimiento solo se prueba en el entorno aislado y en simulación.
- La segunda parte del «Anexo» entregada a Andrés en la última tarea (desde plan.md); la spec 005 sincronizada (RF-16.40: «Intente» y «tras el último dato»); `MEMORY.md` actualizado.

## Texto propuesto
- Los textos para la constitución, `CLAUDE.md`, el ERS y CU-09 están en `plan.md`, «Anexo C» (P-β), en dos partes:
  - primera: principio 5, «Datos» de `CLAUDE.md`, RN-01 y RNF-10; se aprobó con esta spec y Andrés la aplica antes de RF-08.63;
  - segunda: el resto; la última tarea del plan la entrega a Andrés.

## Decisiones
- Las decisiones de Andrés (28-29/10/2026) están en `plan.md`, «Anexo A» (trasladadas el 29/10/2026, P-β); el detalle de cada una sigue en su requisito.
- Tras el plan (29/10/2026): **P-1 = C** (RF-11.66, RF-11.69: relevancia y reformulación en los tres chats); **P-2 = A** (RF-16.62: el reintento por respuesta vacía es una consulta con su propio presupuesto y tope; descartado: descontar el tiempo ya usado); **P-3 = A** (RF-08.62); **P-4 = A** (los 128 PDF se cargan en la tarea de cierre de esta spec); **P-5 = A** (RF-11.69: sin umbral mínimo de similitud en el chat por tema y el notebook, siempre los más cercanos del tema; porque con el umbral del general una pregunta global como «resume el tema» o un saludo quedaría sin fragmentos; descartado: el umbral del general).

## Pistas para el plan
- Trasladadas a `plan.md`, «Anexo B» (29/10/2026).

## Dudas abiertas
- Ninguna.

## Historial
- 29/10/2026: Q1-Q4 incorporadas (prueba contra el motor real, resumen en alcance, pestaña cerrada sin registro, fragmentos enteros en el resumen); pendiente de segunda revisión QA.
- 29/10/2026: segunda revisión QA (CAMBIOS NECESARIOS) y R1-R5 incorporadas: notas a «Pistas para el plan», decisiones en una línea; bitácora con `CONSULTA_RAG` y motivo; excepción en RN-01; páginas con posición real; espacio mínimo de fragmento; RNF-01.61 pasa a CF-1; FE-04 nuevo; orden actual del resumen definido; pendiente de tercera revisión QA.
- 29/10/2026: P-α = A (encabezado fijo de 500 caracteres) y P-β = A (el «Texto propuesto» pasa literal al Anexo, para trasladarlo a plan.md; remisión de una línea); pendiente de tercera revisión QA.
- 29/10/2026: tercera revisión QA (CAMBIOS NECESARIOS menores, diseño validado): Q-A y Q-B de Andrés; M1, M3, M4, B1-B6 redactados (línea de la lista, RN-01 y RNF-10 con «Las excepciones son…», estimador único, configuración incoherente, error del motor, matriz e2e, `[NUEVO]` y «Mensaje», Anexo en dos partes, mensaje literal del resumen); D-2 abierta; pendiente de aprobación de Andrés.
- 29/10/2026: D-2 = A (error del motor registrado como `CONSULTA_RAG` con el motivo «error del motor», sin guardarlo en el historial); RF-21.60, su prueba y el texto de RF-21 del Anexo completados; sin dudas abiertas; pendiente de aprobación de Andrés.
- 29/10/2026: **aprobada por Andrés**, con el texto del principio 5 del Anexo. Anexo, Decisiones y Pistas trasladados literalmente a `plan.md` (Anexos A-C), con remisión aquí (P-β).
- 29/10/2026: cambio aprobado por Andrés tras el plan (P-1 = C, P-2 = A, P-3 = A, P-4 = A): RF-11.69 nuevo; RF-11.66 en los tres chats; RF-08.62 con señal de vida, tope y valores no numéricos; RF-16.62 sin el reintento; RNF-09.60 con el ejemplo de configuración local; «Fuera de alcance» ajustado. Pendiente de confirmar el diff.
- 29/10/2026: Andrés confirma el diff tras el plan y P-5 = A (sin umbral en tema y notebook); sin dudas abiertas. Plan y tareas aprobados.

