# Spec 004, T14: borrador de cambios a la documentación de planificación

Fecha: 19/10/2026 · Origen: plan §15 · Decisiones de Andrés: se acepta el paso a «Parcial» de RF-01, RF-07, RF-11, RF-12, RF-17, RF-22 y RNF-04; RNF-07 usa la redacción sin rutas (se descarta la variante con nombres).

## Nota inicial

- Los números RF-xx.y son de la spec 004. En el ERS cada párrafo va en el requisito padre (RF-xx), sin el sufijo.
- El ERS solo admite un párrafo «Estado actual» en los requisitos en estado Parcial (ERS, criterio de estados). Por eso los requisitos que reciben uno nuevo pasan de Implementado a Parcial.
- Lo derivado de RF-17.3 y RF-17.4 (aislamiento de los notebooks), que aparece en RF-11, RF-12, RF-17 y RF-20, requiere el visto bueno del tutor antes de pegarlo.
- Los textos se compararon contra `graphify-out/documentacion_texto/` (exportación de los PDF). Si el `.docx` va por delante del PDF, revisa que el párrafo no esté ya y no lo dupliques.
- Las notas «Discrepancia» u «Observación» señalan dónde el texto actual no coincide tal cual o dónde conviene revisar el resultado al pegar.

---

## ERS

### RA-02 (riesgo)

Sustituir su «Estado actual» por:

> «Estado actual: la infraestructura de pruebas del backend existe y se ejecuta con un solo comando. La red de seguridad del backend cubre con pruebas automatizadas los flujos críticos: inicio de sesión y acceso por rol; carga → Procesado → chat que cita la fuente; y NotebookServIA. Lo que el sistema todavía no cumple queda marcado como fallo esperado con su requisito. El extremo a extremo llega con la spec 005.»

Texto actual verificado (coincide): «Estado actual: la infraestructura de pruebas del backend existe y se ejecuta con un solo comando; la cobertura sigue siendo progresiva y el extremo a extremo llega con la red de seguridad de los flujos críticos.»

### RF-01: Autenticación y cierre de sesión

Estado: **Implementado → Parcial**. Párrafo nuevo:

> «Estado actual: al cerrar la sesión, el servidor todavía acepta el token hasta que vence. Sin configuración, la vigencia del token es de 480 minutos en lugar de 60. Los intentos fallidos se registran con un mismo motivo genérico en lugar de su causa. Con un correo no registrado no se hace la comparación contra un hash, así que el tiempo de respuesta puede revelar ese caso. Todo esto queda pendiente de la revisión del módulo de autenticación.»

### RF-05: Carga de archivos multiformato

Estado: Parcial (sin cambio).

- **Manejo de errores**, añadir al final:

  > «Un archivo vacío, uno que no se pudo guardar o uno que provoca un error interno se rechaza con su motivo («archivo vacío», «no se pudo guardar el archivo», «error interno»), sin impedir la carga de los demás. Cada archivo rechazado deja en la bitácora un registro de rechazo con su motivo, sin su nombre ni el tema (RF-21).»

- **Salida, «En caso de éxito»**, sustituir por:

  > «Cada archivo aceptado queda almacenado y encolado para su procesamiento asíncrono con un identificador de tarea. El sistema confirma cuántos archivos se enviaron a procesamiento, contando solo los aceptados («1 archivo enviado a procesamiento» o «<n> archivos enviados a procesamiento»), y los archivos se procesan en segundo plano (RF-07). Si no se aceptó ninguno, la respuesta indica «No se aceptó ningún archivo. Revise el motivo de cada uno.» y no informa ningún envío.»

  Texto actual verificado (coincide): «Cada archivo aceptado queda almacenado y encolado para su procesamiento asíncrono con un identificador de tarea, y el sistema confirma que la carga se inició y que los archivos se procesan en segundo plano (RF-07).»

- **«Estado actual»**, añadir al párrafo existente (el de las imágenes y la advertencia de escritura a mano):

  > «El servidor todavía no valida el formato, el tipo MIME ni el tamaño de los archivos; hoy solo lo hace la interfaz (pendiente de la revisión de ingesta). El aviso con el motivo de cada archivo rechazado en Ingesta de Datos y en NotebookServIA: implementado; pendiente la verificación de extremo a extremo (spec 005).»

- Observación: la Salida «En caso de error» dice que el mensaje indica «si el problema fue el formato, el tamaño o la conexión»; con los motivos nuevos (archivo vacío, no se pudo guardar, error interno) queda incompleta. No forma parte del borrador aprobado; decide si se amplía.

### RF-06: Asociación a un tema

Estado: Parcial (sin cambio). Añadir al «Estado actual»:

> «El servidor ya acepta y crea temas de nombre libre, pero el chat acotado a uno de ellos no se limita a ese tema y consulta todos los documentos (ver RT-06).»

Observación: el «Estado actual» vigente dice que la pantalla de Ingesta de Datos todavía exige el identificador heredado. El párrafo nuevo habla del servidor, así que no lo contradice; conviene que quede justo después.

### RF-07: Procesamiento automatizado del contenido

Estado: **Implementado → Parcial**. Párrafo nuevo:

> «Estado actual: si falla la extracción del texto, el documento no queda registrado en estado Error, porque se registra después de extraer el texto. Además, el progreso del archivo que falló muestra el texto técnico del error en lugar del mensaje fijo y su causa.»

### RF-11: Consulta en lenguaje natural ⚠️ visto bueno del tutor (RF-17.3/RF-17.4)

Estado: **Implementado → Parcial**. Párrafo nuevo:

> «Estado actual:
> - si no es posible conectar con el motor de lenguaje, el mensaje de error incluye el texto técnico del fallo;
> - si el modelo no devuelve texto, el servidor entrega una respuesta de relleno en lugar de cerrarla vacía, y la interfaz no puede distinguirla para reintentar;
> - en NotebookServIA, si el notebook consultado no pertenece al usuario o no existe, el chat no se rechaza: consulta todos los documentos del sistema;
> - el chat acotado a un tema de nombre libre consulta todos los documentos (RF-06).»

### RF-12: Respuestas con cita de fuente y sin invención de información ⚠️ visto bueno del tutor

Estado: **Implementado → Parcial**. Párrafo nuevo:

> «Estado actual: el chat general y el acotado a un tema todavía pueden recuperar y citar documentos de los notebooks de otros usuarios (RF-17).»

### RF-17: Creación de notebooks ⚠️ visto bueno del tutor

Estado: **Implementado → Parcial**. Párrafo nuevo:

> «Estado actual: los documentos de un notebook todavía aparecen a otros usuarios en el chat general, en el chat acotado a un tema y en la búsqueda de temas similares; la descarga sí se rechaza. Además, el servidor acepta cargar archivos a un notebook ajeno o inexistente.»

### RF-19: Eliminación de documentos del notebook

Estado: Parcial (sin cambio). Sustituir el «Estado actual» por:

> «Estado actual: la eliminación se ejecuta sin solicitar confirmación. Si falla la eliminación de los fragmentos, el servidor responde un error sin mensaje; un nuevo intento sí completa la eliminación. Si no se puede borrar el archivo físico, el fallo se ignora: el registro se elimina y se informa éxito.»

Texto actual verificado (coincide): «Estado actual: la eliminación se ejecuta sin solicitar confirmación, y si falla, el sistema no lo informa al usuario.»

### RF-20: Búsqueda por similitud ⚠️ visto bueno del tutor

Estado: Parcial (sin cambio). Añadir al «Estado actual»:

> «Los resultados todavía pueden incluir documentos de los notebooks de otros usuarios (RF-17).»

### RF-22: Consulta y filtrado de la bitácora

Estado: **Implementado → Parcial**.

- **«Detalle y exportación»**, añadir al final:

  > «El detalle de los registros de carga muestra el nombre de su tipo y sus datos con etiqueta en español, en este orden y solo los que el registro guardó (ninguno vacío ni de relleno):
  > - Carga iniciada: Tema, Fecha y hora, Archivos aceptados y Archivos rechazados.
  > - Inicio del procesamiento y Procesamiento terminado: Tema, Fecha y hora y Archivo.
  > - Documento almacenado: además, Documento y Fragmentos.
  > - Error de procesamiento: además, Causa.
  > - Cancelación y Error de cancelación: los mismos datos.
  > - Carga rechazada: solo Fecha y hora y Motivo, sin el nombre del archivo ni el tema.
  >
  > La causa es siempre una de un conjunto cerrado («formato o tamaño no permitido», «no se pudo extraer el texto», «servicio de procesamiento no disponible», «no se pudo guardar para la búsqueda», «error interno»), nunca el texto técnico del error. No se muestran datos técnicos (identificador de tarea, colección, número de vectores). El encabezado del detalle dice «Tema» o «Sin tema asociado».»

- **«Manejo de errores»**, añadir al final:

  > «Si la consulta de la bitácora falla, el sistema responde con un error genérico, sin detalles técnicos.»

- **«Estado actual»** nuevo (después de «Manejo de errores»):

  > «Estado actual: el detalle de los registros de carga: implementado; pendiente la verificación de extremo a extremo (spec 005).»

- **Opcional (decisión de Andrés)**, añadir al «Estado actual»:

  > «La hora del listado se muestra con un desfase de 6 horas respecto de la hora de Costa Rica (corrección pendiente).»

### RNF-04: Diseño adaptable (responsive)

Estado: **Implementado → Parcial**. Párrafo nuevo:

> «Estado actual: el aviso de archivos rechazados (RF-05) y el detalle de los registros de carga de la bitácora (RF-22) en escritorio y en una pantalla de 616 px de ancho (con desplazamiento horizontal): implementado; pendiente la verificación de extremo a extremo (spec 005).»

### RNF-07: Autenticación y autorización basada en tokens

Estado: Parcial (sin cambio). Redacción sin rutas. Sustituir la frase «algunas funciones de la cuenta del propio usuario todavía no exigen token» por:

> «…algunas funciones de la cuenta del propio usuario y la documentación automática de la API todavía responden sin token. El servidor sigue aceptando un token después del cierre de sesión (RF-01). El chat de un notebook ajeno no se rechaza (RF-11). Ver o restaurar una conversación ajena se distingue de una inexistente (se rechaza con 403 en lugar de 404).»

El resto del párrafo (clave de firma, avatares) se mantiene.

Discrepancia: la frase existe tal cual, pero en el texto actual sigue sin punto: «…todavía no exigen token y el manejo de la clave de firma fuera de la recuperación todavía no se endurece (pendiente de la revisión del módulo de autenticación). Las fotografías de perfil…». Si se sustituye solo esa frase, «y el manejo de la clave de firma…» queda colgando tras «404).». Propuesta de ensamblaje, sin cambiar el contenido:

> «Estado actual: las funciones de gestión de usuarios, de bitácora y de correo exigen sesión y rol; algunas funciones de la cuenta del propio usuario y la documentación automática de la API todavía responden sin token, y el manejo de la clave de firma fuera de la recuperación todavía no se endurece (pendiente de la revisión del módulo de autenticación). El servidor sigue aceptando un token después del cierre de sesión (RF-01). El chat de un notebook ajeno no se rechaza (RF-11). Ver o restaurar una conversación ajena se distingue de una inexistente (se rechaza con 403 en lugar de 404). Las fotografías de perfil (avatares)… [sin cambios]»

---

## Casos de Uso

### CU-02: Cerrar Sesión

- **Paso 5**, sustituir por:

  > «El sistema elimina la sesión del navegador y el servidor deja de aceptar ese token en cualquier solicitud posterior, incluida la renovación.»

  Texto actual verificado (coincide): «5. El sistema elimina la sesión del navegador, de modo que el token deja de enviarse al servidor.»

- **Postcondición**:

  > «La sesión queda cerrada: el token ya no es válido aunque no haya vencido.»

  Discrepancia: la postcondición actual es «La sesión del usuario queda cerrada en el navegador, el cierre queda registrado en la bitácora y las páginas protegidas dejan de estar accesibles hasta un nuevo inicio de sesión.». Si se sustituye entera, se pierden el registro en la bitácora y las páginas protegidas. Propuesta: sustituir solo la primera cláusula («La sesión del usuario queda cerrada en el navegador») por la frase nueva y mantener el resto, o añadirla como frase final.

- Observación: el paso 5 y la postcondición describen el comportamiento meta; el ERS lo marca como pendiente en el «Estado actual» de RF-01.

### CU-07: Cargar Archivos (paso 7)

Sustituir «…y muestra "Subida iniciada: los archivos se están procesando en segundo plano"» por:

> «…almacena cada archivo aceptado y lo encola para su procesamiento. Tras la respuesta del servidor, muestra junto al tema la confirmación («1 archivo enviado a procesamiento» o «<n> archivos enviados a procesamiento») y el motivo de cada archivo rechazado. Los rechazados no pasan a procesamiento. Si no se aceptó ninguno, muestra «No se aceptó ningún archivo. Revise el motivo de cada uno.»»

Discrepancia: el texto actual es «7. El sistema asocia cada archivo al tema indicado, creándolo si todavía no existe (<<include>> Asociar archivo a un tema), almacena el archivo, lo encola para su procesamiento y muestra "Subida iniciada: los archivos se están procesando en segundo plano".». Como el texto nuevo empieza por «almacena cada archivo aceptado y lo encola…», el tramo que se sustituye debe empezar en «almacena el archivo, lo encola para su procesamiento y muestra…», no solo en «y muestra…». Si no, «almacena» y «encola» quedan duplicados.

### CU-07: FE-03 Error de procesamiento

Sustituir por:

> «En el paso 9, si el procesamiento de un archivo falla, el documento queda en estado Error. El progreso muestra "No se pudo procesar el archivo. Por favor, intente nuevamente." junto con su causa (formato o tamaño no permitido, no se pudo extraer el texto, servicio de procesamiento no disponible, no se pudo guardar para la búsqueda o error interno), sin detalles técnicos y sin detener el procesamiento de los demás archivos.»

Texto actual verificado (coincide): «FE-03 Error de procesamiento: en el paso 9, si el procesamiento de un archivo falla, el documento queda en estado Error con el mensaje "No se pudo procesar el archivo. Por favor, intente nuevamente.", sin detener el procesamiento de los demás archivos.». Conserva el rótulo «FE-03 Error de procesamiento:» al inicio.

### CU-15: FA-01 Ver detalle de un evento

Sustituir «para una carga, el identificador del documento y su número de fragmentos» por:

> «para una carga, el tipo de registro con sus datos (tema, fecha y hora, archivo, documento y fragmentos, archivos aceptados y rechazados o la causa del error); para un archivo rechazado, solo la fecha y hora y el motivo»

Texto actual verificado (coincide; en el PDF ocupa dos líneas).

---

## Pasos siguientes

1. Tutor: visto bueno a lo derivado de RF-17.3/RF-17.4 (RF-11, RF-12, RF-17 y RF-20).
2. Andrés: decide el párrafo opcional de RF-22 (desfase de 6 horas) y las observaciones de RF-05 y CU-02.
3. Andrés aplica los cambios en los `.docx` del ERS y de Casos de Uso (con el estado Parcial donde se indica) y exporta los PDF.
4. Andrés regenera el texto: `python3 -X utf8 graphify-out/generar_documentacion_texto.py`.
5. Comprobar en `graphify-out/documentacion_texto/` que cada párrafo aparece una sola vez y que los estados coinciden.
