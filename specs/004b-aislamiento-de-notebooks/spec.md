# Spec 004b — Aislamiento de los notebooks entre usuarios
Estado: aprobada (19/10/2026); cambios del 19/10/2026 y del 20/10/2026 aprobados por Andrés

Historial:
- 19/10/2026 — creada a partir de los `xfail` urgentes de la 004 (fuga entre notebooks). Decisiones de Andrés 1-9: alcance C, clave `NB-` en chat por tema A, chat general y temas similares A, «ninguna vía» A, bitácora de rechazos A, restricciones A, ERS A, carpeta A, interfaz y prueba manual sí. Publicable: se redacta en términos generales.
- 19/10/2026 — dudas D1-D4 resueltas por Andrés: D1 A (todo intento ajeno o inexistente se registra solo con su motivo), D2 A (bitácora propia solo con `NB-<id>` y el id del documento), D3 B (clave no disponible en el chat por tema = tema inexistente), D4 A (único cambio de interfaz: el aviso al fallar quitar).
- 19/10/2026 — D5 A (chat del notebook ajeno o inexistente: 404 uniforme, el modelo no recibe nada) y D6 A (chat por tema con `NB-` no disponible: intento fallido más consulta general sin la clave). Se agrega RF-21.33.
- 19/10/2026 — D7 A (el trato de D6 en todas las vías de RF-17.31) y D8 A (mención en la pregunta).
- 19/10/2026 — revisión QA, bloqueantes resueltos por Andrés (todos A):
  - Q1: excepción a la decisión 6: una migración que solo agrega los tipos de acción que faltan (RF-21.34).
  - Q2: la mención de una clave `NB-` en la pregunta no se detecta (RF-17.32); **D8 queda sin efecto**.
  - Q3: modifica la decisión 2 y D3: en el chat por tema toda clave `NB-` (propia, ajena o inexistente) es tema inexistente; el chat acotado a un notebook es solo el de NotebookServIA. El listado sigue rechazando `NB-` igual para todos.
  - Q4: conversación ajena como identificador del chat (RNF-07.31).
  - Menores 5-12 resueltos por el planner (casos límite, documento no disponible, filtrado en la búsqueda, motivos, códigos, trazabilidad, cierre).
- 19/10/2026 — segunda revisión QA:
  - Se define «conversación propia» (dueño fijado al crearla, compatibilidad de lectura) y se agrega RNF-07.33.
  - Q5 (Andrés, A): los 3 tipos nuevos se muestran y filtran en la interfaz; amplía la excepción de D4.
  - Orden de las comprobaciones (antes de leer o modificar) y alcance del registro del servidor; identificador de notebook válido.
- 19/10/2026 — aprobada por Andrés («A»), con las decisiones del planner en los menores, la línea de acceso del servidor web fuera de RF-21.32 y la compatibilidad de conversaciones con `_` en el correo. Plan y tareas creados.
- 19/10/2026 — cambio tras la T5 (Andrés, «A» a las cuatro decisiones del coordinador); se implementa en la T6:
  - RNF-07.34 (nuevo): asociar o cambiar el tema de una conversación ajena no la toca y deja el intento fallido. Su respuesta, en la entrada siguiente (D9).
  - RF-17.34 (nuevo): un tema que la base iguala con la clave de un notebook se trata como esa clave. La «forma de clave» pasa a leerse en NFKC.
  - Amplían su alcance: RNF-07.33 (crear al asociar un tema) y RF-21.32 (asociar el tema; las respuestas 4xx previstas ya no se anotan como error).
- 19/10/2026 — respuestas de Andrés al cambio (todas A):
  - D9 A: asociar el tema de una conversación ajena responde lo mismo que con una inexistente (RNF-07.34).
  - Confirmado: `ＮＢ-<id propio>` se carga como `NB-<id>`; `NB-５` es no disponible, como los demás dígitos Unicode.
  - El 500 inesperado de asociar el tema da «Error interno del servidor», sin texto de excepción (RNF-07.34).
- 20/10/2026 — cambio tras la T7 (Andrés, A): RF-21.30 precisa el previsualizar fallido de un documento propio (tipo 10; «documento sin procesar», «validacion»; «archivo no encontrado», «interno»). Se implementa en la vuelta de correcciones de la revisión T6-T8.

## Contexto y objetivo
Regla general (Andrés, literal): «A cada usuario deberían aparecer solamente sus notebooks de tal manera que se le sea imposible ver los otros notebooks».

La red de seguridad (004) dejó en `xfail` que el contenido de un notebook llega a otros usuarios (chat, temas similares, carga) y que una conversación ajena se distingue de una inexistente.
Objetivo: cerrar esos fallos y el resto de los hallazgos del módulo NotebookServIA (quitar con fallo, bitácora, mensajes, capas), **sin romper** el uso de los notebooks propios ni los temas de nombre libre.

## Trazabilidad
- ERS V1.7: RF-11, RF-12, RF-13, RF-14, RF-17, RF-18, RF-19, RF-20, RF-21, RF-22, RNF-07 (RNF-07.24), RN-01, RNF-10, RT-07. Constitución, principio 3. RF-17.3 y RF-17.4 son `[NUEVO]` (de la 004).
- HU: 05, 11, 12, 13, 14, 17, 18, 19, 20, 21 (HU-21 es de RF-21: confirmado en la matriz del PDF del ERS V1.7). CU: 07 (FA-01), 09 (FA-05), 11, 12, 13, 14, 15.
- «Estado actual» que cierra: en RNF-07, la frase del 403 de la conversación ajena; en RF-19, el fallo de eliminación sin mensaje y el archivo que no se borra. Al cierre, el ERS V1.8 escribe como regla cumplida lo que el borrador T14 de la 004 dejaba como «Estado actual» de RF-11, RF-12, RF-17 y RF-20 (revisión del tutor).
- Requisitos de la 004 que se cumplen aquí (se quita su `xfail`): RF-11.3, RF-17.3, RF-17.4, RNF-07.6, RF-19.2. Los nuevos usan el bloque **.30+** (la 004 usa .1+, la 004a .20+).
- Criterio de la 004 que esta spec ajusta (D1): RNF-07.6 en «base sin cambios», que ahora admite la fila del intento fallido. RF-11.3 conserva su criterio de la 004.

## Usuarios
Usuario Gubernamental (dueño o no de un notebook); Administrador (no usa estas funciones, RN-03; ve los intentos fallidos en la bitácora, CU-15).

## Definiciones
- **Forma de clave de notebook**: tema que, sin espacios al inicio y al final, en su forma de compatibilidad Unicode (NFKC: `ＮＢ－5` se lee `NB-5`) y sin distinguir mayúsculas, empieza por `NB-`.
- **Notebook disponible**: forma de clave cuyo resto (lo que sigue al prefijo, en cualquier grafía), tal como se escribió, es un número en dígitos ASCII, sin ceros a la izquierda, de un notebook existente del propio usuario. Cualquier otra (ajena, inexistente, `NB-05`, dígitos Unicode, número fuera de rango, espacios internos) es **no disponible**, con el mismo trato en todos los casos.
- **Identificador de notebook válido** (chat del notebook): solo dígitos ASCII, sin signo, espacios ni ceros a la izquierda. Cualquier otro (`+5`, ` 5 `, `05`, dígitos Unicode, vacío) es **no numérico**.
- **Conversación propia**: la que tiene como dueño al usuario autenticado que la pide.
  - El dueño se fija al crearla con ese usuario, también en el chat de un notebook; nunca se deduce del identificador.
  - Comprobar el dueño solo consulta ese dato, no los mensajes, el título ni la fecha.
  - Ya guardadas antes de esta spec (sin dueño fijado): se leen sin reescribirlas. Son propias si su dueño registrado es el usuario o si el usuario coincide completo y exacto con el tramo de usuario del identificador:
    - chat general: entre `session_` y el último `_`; chat de notebook: entre `session_notebook_<número>_` y el último `_`.
  - **Ajena**: guardada y no propia. **Inexistente**: no guardada.
- **Respuesta uniforme**: la misma (código, cuerpo, aviso en español) que el sistema da ante el mismo recurso inexistente, **salvo el identificador pedido** cuando la respuesta lo repite; sin contenido, nombres, rutas ni texto de excepción.
- **Vía**: toda función que devuelve, cita, resume o usa contenido de documentos: chat general, por tema y de notebook; temas similares (resultados, resumen IA, descarga); listado de archivos de un tema; descarga y previsualización.
- **Contenido ajeno**: frases, nombres de archivo, nombre y clave de los notebooks de otros usuarios, salvo el texto que el propio usuario escribió (su pregunta o la clave que envió). Los temas generales (fuera de notebooks) no son contenido ajeno.
- **Fragmento de notebook**: el de un tema con forma de clave de notebook, en cualquier grafía; solo es visible para el dueño del notebook disponible con ese número, y para nadie si ese notebook no existe.

## Requisitos funcionales

### A. Aislamiento (sin fuga por ninguna vía)
- **RF-17.3** (RF-17, RF-11, RF-12, RF-20) `[NUEVO]`: EL SISTEMA nunca entrega, cita, resume ni envía al modelo contenido ajeno, por **ninguna vía**; los notebooks propios siguen apareciendo en el chat general y en temas similares. La exclusión se aplica en la búsqueda misma, no después de recuperar.
  - *Comprobación*: usuarios A y B `PRUEBA`, cada uno con su notebook y su frase; un tema general con otra frase. B consulta la frase de A en cada vía: contexto del modelo, resultados, resumen y listado sin nada de A; sí traen lo de B y el tema general.
  - *Comprobación* (búsqueda): con muchos fragmentos ajenos mejor puntuados que los propios, B recibe la misma cantidad de resultados que sin ellos. Fragmentos con la clave en otra grafía (`nb-<id>`) o de un notebook sin registro tampoco llegan a B.
  - *Para el plan*: demostrar cómo la exclusión cubre grafías desconocidas aunque la búsqueda compare la clave exacta, sin modificar los fragmentos guardados.
- **RF-17.31** (RF-17.3, RF-20): SI un usuario usa una forma de clave de notebook en el chat por tema, como tema de referencia de temas similares o en el resumen IA, ENTONCES el sistema responde igual que con un tema inexistente, sin contenido ajeno. El listado y la descarga por tema la rechazan como hoy (formato inválido, igual para todos).
  - *Comprobación*: cada vía con la clave del notebook de A (`NB-<id>`, `nb-<id>`), con una inexistente y con la propia de B: respuestas idénticas entre ajena e inexistente; el modelo no recibe contenido ajeno. Bitácora según RF-21.33.
- **RF-11.31** (RF-11, RF-17.31; decisión 2 y D3 modificadas, Q3): SI en el chat **por tema** el tema tiene forma de clave de notebook (propia, ajena o inexistente), ENTONCES EL SISTEMA lo trata como tema inexistente y responde con el chat general del usuario (que excluye el contenido ajeno, RF-17.3). El chat acotado a un notebook es solo el de NotebookServIA.
  - *Comprobación*: B pregunta lo mismo en el chat general y en el chat por tema con la clave de A, con una inexistente y con la propia: el contexto que recibe el modelo es igual al del chat general, sin contenido ajeno; mismo código y estructura de respuesta.
- **RF-17.32** (RF-13, RF-17.3; Q2): CUANDO la pregunta menciona una clave de notebook, EL SISTEMA no la detecta como tema (la detección solo reconoce el formato de tema heredado) y responde como el chat general del usuario, sin contenido ajeno.
  - *Comprobación*: B escribe en la pregunta la clave del notebook de A: no se detecta tema y el modelo no recibe nada de A (frases, nombre de archivo, nombre del notebook).
- **RF-11.3** (RF-11, RF-12; CU-09 FA-05): CUANDO pregunta en el chat de **su** notebook, EL SISTEMA envía al modelo solo fragmentos de ese notebook.
- **RF-11.32** (RF-11.3, RNF-07.6; D5): SI pregunta en el chat **del notebook** con un notebook ajeno, inexistente o con identificador no numérico, ENTONCES EL SISTEMA responde 404 uniforme (mismo código y cuerpo) sin llamar al modelo.
  - La comprobación del notebook va antes de leer o modificar la conversación o cualquier otro dato.
  - *Comprobación* (RF-11.3 y RF-11.32): dos notebooks del mismo usuario y un tema general, cada uno con su frase: preguntando por la de otro, el contexto solo trae el notebook consultado.
  - Con el notebook de A, uno inexistente y los no numéricos (`+5`, ` 5 `, `05`, dígitos Unicode): 404 idéntico, el modelo no se llama y la conversación enviada queda igual (fecha incluida).
- **RF-11.30** (RF-11, decisión 2): EL SISTEMA no cambia el chat por tema con temas de nombre libre ni con temas en formato heredado.
  - *Comprobación*: las pruebas existentes del chat por tema siguen pasando y RF-06.2 sigue en `xfail` (sin XPASS).

### B. Recursos ajenos
- **RF-17.4** (RF-17, RF-05; CU-07 FA-01) `[NUEVO]`: SI sube archivos con una forma de clave de notebook no disponible (incluidas `NB-05` y las demás grafías no canónicas), ENTONCES respuesta uniforme 404, sin guardar, encolar, crear el tema ni crear documentos o fragmentos.
  - *Comprobación*: B sube al notebook de A, a uno inexistente y a `NB-0<id de B>`: 404 idéntico; carpeta temporal, base (salvo la fila de RF-21.32), Qdrant y tareas sin cambios.
- **RF-17.34** (RF-17.4, RF-17.31, RF-11.31) `[NUEVO]`: SI un tema, aunque no tenga forma de clave, coincide con el tema de un notebook según la comparación con que el sistema busca un tema guardado, ENTONCES EL SISTEMA lo trata como esa clave.
  - Carga: la del notebook propio se guarda como `NB-<id>`; cualquier otra da el 404 de RF-17.4 y el intento de RF-21.32.
  - Vías de RF-17.31: como tema inexistente (RF-11.31, RF-21.33).
  - Ningún documento entra en un notebook ajeno por una grafía equivalente, conocida o no.
  - *Comprobación*: la primera prueba confirma o descarta que la base iguale `ＮＢ-<id>` (letras de ancho completo) con la clave; en ambos casos queda como protección.
  - B sube con `ＮＢ-<id de A>` y `ＮＢ－<id de A>`: 404 idéntico al de una inexistente, una fila de intento, nada en el notebook de A; con la suya, el documento queda en `NB-<id de B>`. En el chat por tema, el contexto es igual al del general.
- **RNF-07.6** (RNF-07, RF-14, RF-18, RF-19): SI pide un recurso ajeno (listar, previsualizar o quitar documentos de un notebook ajeno, su chat; ver, restaurar o eliminar una conversación ajena), ENTONCES respuesta uniforme 404, sin leer, cargar, modificar ni entregar nada. Restaurar comprueba el dueño antes de leer o cargar.
  - *Comprobación*: cada operación con el token del otro y con un id inexistente: respuestas idénticas (salvo el identificador pedido); Qdrant, archivos, conversaciones en memoria y guardadas y base sin cambios, salvo una fila de intento fallido por petición (RF-21.32).
  - *Ajuste a la 004 (D1)*: la prueba deja de exigir la bitácora intacta; exige exactamente esa fila por petición, igual para ajeno e inexistente.
- **RNF-07.31** (RNF-07, RF-14; Q4): SI el chat recibe como conversación el identificador de una conversación ajena, ENTONCES EL SISTEMA responde como con una conversación nueva (historial vacío), sin cargar, leer ni modificar la ajena, y registra el intento fallido de RF-21.32.
  - Se elige el historial vacío, no un 404: hoy un identificador inexistente abre una conversación nueva y la interfaz crea así cada conversación; un 404 la rompería.
  - El intercambio no se guarda en la conversación ajena ni aparece en la lista de conversaciones del usuario.
  - La comprobación del dueño va antes de cualquier lectura o modificación de la conversación, incluida la fecha de su última actividad.
  - *Comprobación*: B pregunta con el identificador de una conversación de A (general y de notebook, nueva y ya guardada): el modelo no recibe ningún mensaje de A; la de A queda igual (mensajes, título, fecha); la lista de B no la muestra; una fila de intento fallido.
- **RNF-07.33** (RNF-07, RF-14, RNF-07.31): CUANDO se crea una conversación (chat general, por tema o de notebook, o al asociarle un tema, RNF-07.34), EL SISTEMA fija como dueño al usuario autenticado, aunque el identificador contenga a otro usuario. Las del chat de un notebook siguen sin aparecer en la lista de conversaciones, como hoy.
  - *Comprobación* (escritura cruzada): B crea una conversación con un identificador que contiene el usuario de A: no aparece en la lista de A ni A puede verla, restaurarla, eliminarla o usarla; B sí.
  - *Comprobación* (historial): conversaciones propias ya guardadas y nuevas, generales y de notebook, también de un usuario con `_` en su correo: el historial que recibe el modelo y la lista son los de antes del cambio; los datos guardados no se reescriben.
  - Único efecto visible: las ya guardadas de un usuario con `_` en su correo pasan a ser propias al verlas, restaurarlas o eliminarlas (hoy se le rechazan); su lista no cambia.
- **RNF-07.34** (RNF-07.6, RNF-07.31, RNF-07.33, RF-14) `[NUEVO]`: SI se pide asociar o cambiar el tema de una conversación ajena, ENTONCES EL SISTEMA responde lo mismo que con una conversación inexistente (D9 A), no lee ni modifica la ajena (mensajes, tema, fecha) y registra el intento fallido «conversación no disponible» (RF-21.32).
  - Con una inexistente, como hoy: crea la conversación, con su dueño (RNF-07.33), guarda el aviso del tema y responde éxito (200) con un cuerpo que solo repite lo enviado (conversación, tema y acción); la interfaz lo hace así al elegir el primer tema.
  - Con la ajena: ese mismo código y cuerpo, sin crear ni guardar nada a nombre de nadie; las listas del usuario y del dueño no cambian.
  - La comprobación del dueño va antes de cualquier lectura, modificación o mensaje de la aplicación.
  - SI asociar el tema falla por un error inesperado, ENTONCES 500 «Error interno del servidor», sin texto de excepción (como RF-17.30).
  - *Comprobación*: B asocia y cambia el tema en una conversación de A (general y de notebook): código y cuerpo idénticos a los de una inexistente; la de A queda igual; las listas de A y de B sin cambios; una fila de intento; los mensajes de la aplicación sin el identificador.
  - *Comprobación* (error): fallo simulado con una ruta inventada en el mensaje → 500 con el mensaje exacto y sin la ruta.
- **RNF-07.32** (RNF-07.6, RF-18, RF-19): SI en un notebook propio pide previsualizar o quitar un documento ajeno o inexistente, ENTONCES respuesta uniforme 404 (la de hoy, «Documento no encontrado en este notebook») y el intento fallido de RF-21.32 con el motivo «documento no disponible».
  - *Comprobación*: con un documento del notebook de A y con un id inexistente, desde el notebook propio de B: respuestas y filas idénticas; nada cambia en Qdrant, archivos ni base.

### C. Quitar un documento
- **RF-19.2** (RF-19): SI falla alguna de las tres eliminaciones (fragmentos, archivo, registro), ENTONCES responde 500 con «No se pudo quitar el documento. Intente de nuevo.», sin texto de excepción; el documento **sigue listado** y un nuevo intento completa lo que faltó y termina con éxito.
  - Un archivo o unos fragmentos que ya no existen cuentan como eliminados (éxito); solo es error lo que existe y no se pudo borrar.
  - *Comprobación*: fallo provocado en fragmentos y, aparte, en archivo: 500 con ese mensaje y documento listado; un segundo intento deja las tres capas en cero. Archivo ya borrado a mano: éxito.
- **RF-19.30** (RF-19.2, RT-07; D4): SI quitar un documento falla, ENTONCES la interfaz muestra un aviso con el mensaje en español del servidor y el documento sigue en la lista.
  - *Comprobación*: manual, en escritorio y a 616 px, con el fallo provocado: aviso con el mensaje del servidor y documento listado; consola sin errores; `npm run build` y `npm run lint` sin errores.

### D. Bitácora (RF-21)
- **RF-21.34** (RF-21, RF-22; Q1): EL SISTEMA agrega al catálogo de tipos de acción, sin tocar ningún otro dato, «Crear Notebook», «Quitar Documento de Notebook» y «Gestionar Conversación». Se pueden consultar y filtrar como los existentes, también en el historial propio.
  - Previsualizar usa el tipo existente «Descargar Archivo» (descarga o visualización); los intentos fallidos usan el tipo de la acción intentada (consulta, carga, listado, descarga, quitar o conversación).
  - Q5: la consulta de la bitácora del Administrador y el historial propio aceptan filtrar por los 3 tipos nuevos; la interfaz los muestra con su nombre y los ofrece en el filtro.
  - *Comprobación*: tras migrar, el catálogo tiene los 15 tipos previos intactos más los 3 nuevos; filtrar por cada tipo nuevo, en la bitácora y en el historial propio, devuelve sus filas.
  - *Comprobación* (manual): la bitácora muestra los nombres de los tipos nuevos (no «Acción 16») y el filtro los ofrece.
- **RF-21.30** (RF-21; HU-21; D2): CUANDO crea un notebook, previsualiza un documento o lo quita (con éxito o con fallo), EL SISTEMA registra la acción con el usuario, la clave `NB-<id>` como tema y, si aplica, el número del documento y el resultado; sin nombres del notebook ni del documento, texto de excepción ni caracteres de control o NUL. SI el registro falla, ENTONCES la acción se completa igual.
  - *Comprobación*: tras cada acción, su fila con usuario, tipo, tema, número de documento y resultado (el quitar fallido con error clasificado «interno»); los nombres inventados (con un nombre de persona) no aparecen; con la bitácora simulada para fallar, la misma respuesta.
  - Previsualizar fallido (Andrés, 20/10/2026, A): con un documento propio de un notebook propio, se registra con el tipo «Descargar Archivo», resultado fallido, la clave `NB-<id>`, el número del documento y un motivo fijo:
    - «documento sin procesar» (respuesta 400), clasificado «validacion»: el usuario puede reintentar cuando termine el procesamiento.
    - «archivo no encontrado» (respuesta 404), clasificado «interno»: el archivo falta en el servidor.
    - Sin nombre del notebook, del documento ni del archivo, ruta ni texto de excepción. Las respuestas no cambian.
    - Un notebook o documento ajeno o inexistente no entra aquí: sigue siendo el intento fallido de RF-21.32 (404 uniforme, solo el motivo).
  - *Comprobación* (previsualizar fallido): un documento propio sin procesar y otro cuyo archivo se quitó del entorno aislado: una fila por petición, tipo 10, resultado fallido, `NB-<id>`, número del documento, motivo y clasificación; sin nombre ni ruta inventados; la respuesta, igual con la bitácora simulada para fallar.
- **RF-21.31** (RF-21, RF-11): CUANDO pregunta en el chat de un notebook propio, EL SISTEMA registra la consulta con alcance de notebook y su clave como tema, no como «general».
  - *Comprobación*: la fila lleva el alcance de notebook y la clave; las del chat general y por tema no cambian (salvo RF-21.33).
- **RF-21.32** (RF-21, RF-21.20, RNF-07.24; D1): CUANDO un usuario intenta usar un notebook, documento o conversación no disponibles, EL SISTEMA registra un intento fallido **solo con su motivo**, clasificado como error de acceso (la misma clasificación que la descarga rechazada de RF-21.20), sin clave, nombre, pregunta, identificador ni archivos.
  - Alcance: chat del notebook, carga, listar, previsualizar y quitar en un notebook no disponible; documento no disponible (RNF-07.32); ver, restaurar o eliminar una conversación ajena o inexistente; chat con una conversación ajena (RNF-07.31); asociar o cambiar el tema de una conversación ajena (RNF-07.34); carga con un tema equivalente (RF-17.34); vías de RF-21.33.
  - Motivos: «notebook no disponible», «documento no disponible» o «conversación no disponible»; idénticos para ajeno e inexistente.
  - Registro del servidor: en una petición que termina en intento fallido, los mensajes de la aplicación no contienen el identificador ni la clave pedidos ni contenido ajeno, tampoco los anteriores a la comprobación. Las demás peticiones registran como hoy, salvo que ninguna respuesta 4xx prevista se anota como error.
  - Queda fuera la línea de acceso del servidor web (método y ruta), igual para ajeno, inexistente y propio.
  - *Comprobación*: tras cada intento, una fila con motivo y clasificación; ningún dato pedido en la fila ni en los mensajes de la aplicación; con la bitácora simulada para fallar, respuesta idéntica.
- **RF-21.33** (RF-21, RF-17.31, RF-11.31; D6 y D7 revisadas, Q3): CUANDO un usuario usa una forma de clave de notebook en una vía de RF-17.31, EL SISTEMA registra:
  - Chat por tema: con clave ajena o inexistente, el intento fallido «notebook no disponible» y la consulta como general sin la clave; con la propia, solo la consulta general sin la clave (no es un intento sobre algo ajeno).
  - Temas similares y resumen IA: con clave ajena o inexistente, el intento fallido y su fila habitual sin la clave; con la propia, solo la fila habitual sin la clave.
  - Listado y descarga por tema: nada nuevo. El rechazo por formato ocurre antes de buscar el tema, es igual para todos y hoy no se registra para ningún formato inválido; registrarlo cambiaría ese flujo, que queda fuera.
  - Ajeno e inexistente dejan filas idénticas en número, tipo y contenido. SI el registro falla, ENTONCES la respuesta es la misma.
  - *Comprobación*: en cada vía, con `NB-<id>` y `nb-<id>` de A, una inexistente y la propia: exactamente esas filas; la clave no aparece en ningún campo, salvo el texto literal de la pregunta del propio usuario; nada del dueño aparece; con la bitácora simulada para fallar, respuesta idéntica.

### E. Mensajes y capas
- **RF-17.30** (RF-17, RNF-07.23): SI la creación de un notebook falla por un error inesperado, ENTONCES 500 «Error interno del servidor», sin texto de excepción, y el notebook no se crea; el nombre vacío conserva su mensaje (RF-17.1).
  - *Comprobación*: error simulado con una ruta inventada en el mensaje → 500 con el mensaje exacto y sin la ruta; ningún notebook nuevo.
- **RF-17.33** (RF-17, RF-18, RF-19; ERS 2.1, constitución principio 3) `[NUEVO]`: toda operación de NotebookServIA pasa por la capa de servicio de su módulo; ninguna ruta usa directamente el acceso a datos. Se propone anotarlo en el ERS (2.1) como regla de arquitectura.
  - *Comprobación*: unitaria que inspecciona las rutas del módulo; las pruebas de comportamiento de la 004 siguen pasando sin cambios.

## Requisitos no funcionales
- **RNF-07.30** (RNF-07, decisiones 9a, D4 y Q5): las respuestas uniformes de esta spec no cierran la sesión del usuario. La interfaz no cambia, salvo el aviso de RF-19.30 y los 3 tipos de acción de RF-21.34 (nombre y filtro).
  - *Comprobación*: el plan confirma en el código de la interfaz cómo trata un 404 en esas funciones; manual con los dos usuarios.
- Restricciones (principio 1; RN-01): sin dependencias, servicios ni cambios al `docker-compose.yml`; sin modificar datos guardados. Única excepción (Q1): una migración que solo agrega los 3 tipos de acción de RF-21.34, sin cambiar otro dato ni el esquema de ninguna tabla.
- Solo carpeta temporal y datos `PRUEBA` (RA-02.5, RA-02.7).

## Casos límite
- Clave en cualquier grafía (`NB-5`, `nb-5`, `Nb-5`, ` NB-5 `, `ＮＢ-5`, `ＮＢ－5`): mismo trato. `NB-05`, dígitos Unicode (incluidos `５` de ancho completo), `NB- 5` o un número enorme: no disponible, sin 500.
- Tema que la base iguala con una clave sin tener su forma: trato de esa clave (RF-17.34).
- Asociar el tema de una conversación ajena: la misma respuesta que una inexistente y la ajena intacta (RNF-07.34); de una inexistente, como hoy.
- Ajeno frente a inexistente (notebook, documento, conversación): respuestas y filas idénticas.
- Dos notebooks del mismo usuario: no se mezclan (RF-11.3). Notebook propio en chat general y temas similares: sí aparece (RF-17.3).
- Muchos fragmentos ajenos mejor puntuados: no reducen los resultados propios (RF-17.3).
- Fragmentos con otra grafía de la clave o de un notebook sin registro: no llegan a nadie más que al dueño, si existe (RF-17.3).
- Clave de notebook (propia incluida) en el chat por tema: chat general del usuario (RF-11.31). Mencionada en la pregunta: no se detecta (RF-17.32).
- Chat del notebook con id ajeno, inexistente o no numérico: 404 idéntico, el modelo no se llama (RF-11.32).
- Chat del notebook con `+5`, ` 5 `, `05` o dígitos Unicode: no numérico, 404 (RF-11.32).
- Conversación de notebook propia, o de un usuario con `_` en su correo: sigue siendo propia (RNF-07.33). Identificador con el usuario de otro: la nueva es de quien la crea, no del otro.
- Identificador de conversación ajena en el chat: historial vacío, la ajena intacta (RNF-07.31). Residuo aceptado: el intercambio con una inexistente sí queda guardado; distinguirlas exige adivinar el identificador de otro (correo y hora al milisegundo).
- Tema de nombre libre o heredado: sin cambios; RF-06.2 sigue `xfail` (RF-11.30).
- Carga desde Ingesta de Datos con una forma de clave no disponible: 404 (RF-17.4).
- Fallo en una de las tres eliminaciones, archivo ya inexistente, aviso y reintento (RF-19.2, RF-19.30).
- Nombre de notebook o documento con un nombre de persona inventado: no llega a la bitácora (RF-21.30, RF-21.32).
- Bitácora que falla en cualquier registro de esta spec: la respuesta no cambia.

## Fuera de alcance
- Datos ya guardados: fragmentos, conversaciones con contenido filtrado, los archivos huérfanos de un notebook. Solo un **inventario de solo lectura** (temas con forma de clave sin notebook, posibles choques de claves por grafía).
- Confirmación antes de quitar un documento (RF-19; queda su «Estado actual»), reintentar en el chat del notebook (RF-15).
- Otros cambios en la interfaz (solo el aviso de RF-19.30 y los tipos de RF-21.34); extremo a extremo (spec 005).
- Reescribir el dueño de las conversaciones ya guardadas o reindexar su lista (se leen con la compatibilidad de «Conversación propia»).
- Tema libre en el chat (RF-06.2), formato de clave en la detección y en temas similares (RT-06), registrar los rechazos por formato del listado, otros hallazgos de ingesta, RAG, autenticación y bitácora.
- Registrar los éxitos de ver, restaurar o eliminar conversaciones (el tipo nuevo solo se usa aquí para los intentos fallidos).
- Renombrar «expediente», cambiar prompts o modelos.

## Criterios de finalización
- Los 11 `xfail` de esta spec pasan sin la marca: RF-11.3 (2), RF-17.3 (3), RNF-07.6 (3), RF-17.4 (1), RF-19.2 (2), con el ajuste D1 de RNF-07.6; cada requisito nuevo con su prueba, vista en rojo antes.
- Suite completa y `--orden-inverso`: 0 fallos, 0 XPASS, sin residuos; quedan **45** `xfail` (56 − 11), entre ellos RF-06.2.
- Manual de punta a punta, en escritorio y a 616 px, con dos Usuarios Gubernamentales y el Administrador:
  - Andrés crea el segundo Usuario Gubernamental `PRUEBA` desde el Administrador (lo desactiva al final, sin borrado físico) e inicia cada sesión en el Chrome del MCP `chrome-devtools`; los agentes no reciben ni escriben contraseñas.
  - En esa sesión ya iniciada, el implementer o el reviewer conducen la prueba: B no ve nada de A por ninguna vía; A usa su notebook; quitar con éxito y con fallo (aviso de RF-19.30); la sesión no se cierra.
  - Bitácora: acciones (solo clave y número) e intentos fallidos (solo motivo); los tipos nuevos con su nombre (no «Acción 16») y en el filtro, también en el historial propio. Evidencia: capturas y consola sin errores.
- `npm run build` (con el servidor de desarrollo detenido) y `npm run lint` sin errores (por RF-19.30 y RF-21.34).
- Inventario de solo lectura reportado; ningún dato modificado salvo los 3 tipos de acción.
- Documentación: ERS V1.8 (RF-11, RF-12, RF-13, RF-17, RF-19, RF-20, RF-21 y RNF-07; ERS 2.1 por RF-17.33; para el tutor), CU-09 y CU-13 si hace falta, Modelo Relacional si lista el catálogo de tipos, `MEMORY.md`.

## Dudas abiertas
Ninguna.

Resueltas (19/10/2026): D1-D8 y Q1-Q5 (Historial). **D9** (RNF-07.34), A: la ajena recibe la misma respuesta que una inexistente; no se guarda nada ni cambia ninguna lista. Descartadas: B (404 para ambas; rompe el primer tema de la interfaz) y C (404 solo para la ajena; la distingue).
