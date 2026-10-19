# Spec 004 — Red de seguridad del backend (flujos críticos con pytest)
Estado: implementada (validada por el reviewer el 19/10/2026); RF-05.23, RF-22.1 y RNF-04.1 implementados, pendientes de la verificación de extremo a extremo (spec 005)

> Retroactiva (skill `sdd`, «Specs retroactivas»): solo pruebas del backend, sin código de producción, **salvo el bloque F** (correcciones de la interfaz de archivos rechazados, decisión de Andrés del 14/10). La 004a está cerrada y publicada (14/10); la 004 se commitea entera al terminar (Andrés, 14/10). Las debilidades se describen en términos generales y los `xfail` no nombran rutas (D-4).

Historial:
- 12/10/2026 — creada; el paso 2 de `.claude/rules/testing.md` se parte en 004 (backend, pytest) y 005 (extremo a extremo, Playwright) (Andrés, 07/10).
- 12/10/2026 — corregida tras el reviewer; decisiones D-1 a D-4 (abajo).
- 12/10/2026 — condensada para ahorrar tokens; versión completa en `respaldo/`.
- 12/10/2026 — aplicadas las 12 decisiones de Andrés: RF-02.3 solo en los flujos críticos (7-B), sin RF-21.8 (8-D), avatares públicos por ruta propia como en la 004a (1-A); sin dudas abiertas.
- 14/10/2026 — `/sdd-change` tras cerrar la 004a (aviso de su `tasks.md`): RF-05.1 sin «Estado actual» del guardado; avatares como ruta pública deliberada (RF-04.20, RNF-07.22); línea base y versiones del ERS al día; interfaz de los archivos rechazados como duda abierta.
- 14/10/2026 — Andrés elige «A» para esa duda: entra el bloque F «Correcciones» (RF-05.22, RF-05.23, RF-22.1, RNF-04.1), única excepción a «sin código de producción». La spec pasa de 14 a 17 tareas, por encima de D-3 y del máximo de 10 de la skill: decisión consciente de Andrés, sin dividir la spec.
- 14/10/2026 — duda 1 resuelta con C: el backend entrega armados los textos de las pantallas del bloque F; integración del contenido, presentación manual y extremo a extremo en la 005; cambia lo que la API entrega del detalle de la bitácora. Sigue en 17 tareas; sin dudas abiertas.
- 14-15/10/2026 — QA del reviewer (cambios necesarios, 15 hallazgos) y decisiones «A» de Andrés en sus 6 preguntas; la constitución no cambia («1»). RF-05.22 solo con los rechazos que el backend ya produce y contrato aditivo; carga iniciada solo con aceptados; todos rechazados = éxito con 0 aceptados; exención temporal hasta la 005; RF-22.1 `[NUEVO]`. Sigue en 17 tareas.
- 15/10/2026 — segunda QA del reviewer (6 medias, 7 bajas) y decisiones «A»/«B» de Andrés: cierre en la tarea 14 con el ERS editado; `message` y `total_files` cambian de valor; la lista de RF-22.1 sustituye a la actual y el encabezado dice «Tema»; todo rechazo deja fila; conjunto cerrado de causas; desplazamiento horizontal a 616 px. 17 tareas (previsiblemente 18, ver 9c).
- 15/10/2026 — tercera QA del reviewer (3 medias, 4 bajas) y decisiones P1-B, P2-A, P3-B de Andrés: causa «formato o tamaño no permitido», sin «tiempo agotado»; regla de clasificación con precedencia; tabla de RF-22.1 con la fila de almacenamiento y nombre visible de cada tipo; valores de relleno omitidos; RF-07.2 con `xfail` del estado Error; RF-05.23 también en el notebook. Sigue en 17 tareas (previsiblemente 18).
- 15/10/2026 — Andrés aprueba la spec tras las tres QA; pasa a plan y tareas.
- 19/10/2026 — T14, corrección editorial: «Tareas estimadas» pasa de 17 a 18 (la 9c se partió en 9c y 9d en tasks.md); el QUÉ no cambia.
- 19/10/2026 — implementada: validación final APROBADA por el reviewer y cierre aprobado por Andrés; RF-05.23, RF-22.1 y RNF-04.1 implementados, pendientes de la verificación de extremo a extremo (spec 005).

## Decisiones tomadas (Andrés)
- **D-1 = A**: las cuatro debilidades de archivos y descargas (lectura y escritura fuera de la carpeta de documentos, estáticos sin sesión, guardado que falla fuera de la carpeta del backend) se corrigieron en la 004a (cerrada el 14/10); aquí sus pruebas **pasan** (no `xfail`) y no se repiten sus regresiones.
- **D-2 = A**: cierre de sesión según HU-24 (el servidor deja de aceptar el token); RF-01.4 queda `xfail` estricto y el ERS pasa RF-01 a Parcial al cierre.
- **D-3 = B**: una sola spec 004 de 12 a 14 tareas. Ampliada el 14/10 a 17 por el bloque F: Andrés lo decidió sabiendo que supera este rango y el máximo de 10 de la skill `sdd`; no se divide.
- **D-4 = A**: ver aviso de arriba (la 004 se commitea entera al terminar; Andrés, 14/10).

## Objetivo
Pruebas de integración escritas **contra el ERS, no contra el código**, que protegen los tres flujos críticos por la API (hoy solo con pruebas humo): (1) inicio de sesión y acceso por rol (CU-01..03); (2) subir → Procesado → el chat lo cita (CU-07, CU-09); (3) NotebookServIA (CU-11..13); más un **inventario de todas las rutas** con su clase de acceso. Lo incumplido queda `xfail` estricto con su requisito; se corrige en otra spec. Es una red, no una corrección, salvo el bloque F (corrige la interfaz de los archivos rechazados que dejó pendiente la 004a). Servicios reales: SQL Server, Qdrant, Tika, embeddings; simulados: Ollama, Redis, HTR, audio, correo. Línea base: la suite tras la 004a (1326 pruebas a 14/10; su duración se mide al empezar la primera tarea), 0 `xfail` activos, `xfail_strict` activo.

## Trazabilidad
- ERS V1.6: RF-01, FS-01, RF-02, RF-04 (RF-04.20 de la 004a), RNF-07 (RNF-07.22 de la 004a) · RF-05..08, RNF-02 · RF-11, RF-12, RF-14 · RF-17..19, RN-01, RNF-10 · RF-21 · RN-03, RNF-09, RT-02, RT-07, RA-02 · bloque F: RF-05 («Manejo de errores» y «Salida»), RF-22 («Detalle»), RNF-03, RNF-04.
- HU (V1.2): HU-01, 02, 24, 05..08, 11, 12, 14, 17..19, 21, 22. CU (V1.3): CU-01 (FA-02, FE-01), CU-02, CU-03, CU-07 (p. 7, FA-01, FE-03, FE-05; FE-01 solo como contexto: formato y tamaño, fuera de alcance), CU-09 (FE-01, FE-03), CU-11..13, CU-15 (FA-01).
- El texto de confirmación de carga que fija el plan (RF-05.22) prevalece sobre el de CU-07 paso 7, que se actualiza al cierre.
- `.claude/rules/api-conventions.md`: 404 para recurso ajeno; nunca el texto de una excepción.
- «Estado actual» que cierra: ninguno por completo. Aporta evidencia a RNF-07 y RF-19; abre **RF-01 Parcial** (D-2) y el de **RF-05** (el servidor no valida formato, tipo ni tamaño); avanza RA-02.
- Numeración: ya existen RF-02.1-2, RNF-07.1-4, RF-21.1-6, RA-02.1-11 (specs 002, 003a, 003b) y RF-04.20, RF-05.20-21, RF-06.20, RF-21.20, RNF-07.22-24 (004a).

## Usuarios
Usuario Gubernamental (sesión, carga, chat, notebooks); Administrador (sesión y, en el bloque F, detalle de la bitácora; no entra a lo del Usuario Gubernamental, RN-03); sin sesión (solo rutas públicas). Usuarios `PRUEBA` de la spec 002 (RA-02.7). HU-NUEVA solo de desarrollo (no va al documento): avisar con pytest si un cambio rompe sesión, roles, ingesta, chat o notebooks.

## Definiciones
- **Ruta pública**: inicio de sesión (RF-01), los tres pasos de recuperación (RF-03 vía b) y la salud de la raíz. La documentación automática es **protegida** (decisión 5). Todo lo demás es **protegida**.
- **Ruta pública deliberada**: la lectura y la consulta de cabeceras (`GET` y `HEAD`) de un avatar por su dirección propia (RF-04.20, RNF-07.22; 004a, decisión 1-A). Es una excepción documentada a «toda función sensible exige token y rol»: no se prueba como protegida; exigirle sesión es de la retroactiva de autenticación.
- **Inventario de rutas**: todas las rutas registradas por la aplicación (incluidas estáticas y las del framework), obtenidas de ella, más una tabla de clasificación escrita a mano desde el ERS.
- **Flujos críticos** (alcance de RF-02.3): sesión (renovar, cerrar, cambio obligatorio), ingesta (carga y progreso), chat general y por tema, descarga del citado y NotebookServIA; y, del lado del Administrador, la gestión de usuarios (CU-03).
- **Documento de prueba**: texto generado por la suite, prefijo `PRUEBA`, con una frase distintiva única en la corrida.
- **Contexto enviado al modelo**: pregunta + fragmentos con su nombre de archivo, registrados por el simulado de la 002; así se comprueba «lo cita» de forma estructural.
- **Recurso ajeno**: notebook, documento de notebook o conversación de otro usuario.
- **Etiqueta de `xfail`**: «<requisito> · <módulo>», módulo ∈ autenticación, ingesta, RAG, notebooks, bitácora. Sin rutas (D-4).
- **Causa clasificada** (conjunto cerrado, común a RF-05.22, RF-07.2 y RF-22.1; literales exactos):
  - Rechazo en la carga: «tema no válido» (toda la carga, solo en la bitácora), «nombre de archivo no válido», «archivo vacío», «no se pudo guardar el archivo», «error interno».
  - Fallo del procesamiento: «formato o tamaño no permitido», «no se pudo extraer el texto», «servicio de procesamiento no disponible», «no se pudo guardar para la búsqueda», «error interno».
  - Lo que no encaje en otra causa es «error interno». El error crudo guardado (texto de la excepción) nunca se muestra. La cancelación no es una causa de error (fuera de alcance).
- **Regla de clasificación del fallo del procesamiento**: se aplica al error crudo guardado, sin distinguir mayúsculas; gana la primera que se cumple.
  1. «formato o tamaño no permitido»: empieza por «Formato no permitido», «Tipo MIME no permitido», «Archivo demasiado grande», «Extensión '» o «Tipo MIME '», o contiene «excede el límite» (rechazos que hoy hace el procesamiento; solo se etiquetan).
  2. Fallo de extracción: empieza por «Error extrayendo texto», «No se pudo extraer texto», «Error transcribiendo audio», «No se pudo transcribir» o «No se pudo reconocer el manuscrito». Entonces:
     - si además contiene «no disponible», «timeout», «timed out», «connection», «conexión» o «falló después de» → «servicio de procesamiento no disponible»;
     - si no → «no se pudo extraer el texto».
  3. «no se pudo guardar para la búsqueda»: contiene «qdrant», «vector», «embedding», «collection» o «colección» (la vectorización se agrupa con el guardado, como en RF-08).
  4. Sin error guardado, o cualquier otro texto → «error interno».
  - Por qué con texto: hoy la extracción envuelve todos sus fallos en un mismo tipo de excepción, así que el texto es la única señal; la 004 no cambia la extracción. Un nombre de archivo que contenga un patrón puede desviar la clasificación (aceptado).
  - Rechazos de la carga: su motivo ya se guarda como literal; si no es uno de la lista, «error interno».
- **Registro de carga**: fila de la bitácora del tipo carga de documentos; sus tipos y datos visibles, en RF-22.1.

## Clasificación de las rutas (base de RNF-07.5, RF-02.3, RA-02.12)
| Grupo | Clase | Base |
|---|---|---|
| Inicio de sesión; tres pasos de recuperación | Pública | RF-01, RF-03 |
| Salud de la raíz | Pública (decisión 5) | — |
| Avatares (`GET` y `HEAD` de su dirección propia) | Pública deliberada (004a, decisión 1-A) | RF-04.20, RNF-07.22 |
| Documentación automática | Protegida (decisión 5; `xfail` si hoy responde sin sesión) | RNF-07 |
| Renovar y cerrar sesión, cambiar la propia contraseña (incl. obligatorio), cambiar el avatar propio | Cualquier usuario con sesión, solo su cuenta | RF-01, RF-04, HU-24, CU-01 FA-02 |
| Usuarios, restablecer contraseñas, correo, bitácora completa, estadísticas y exportación, dashboard | Solo Administrador | RF-02, RF-22, RF-23 |
| Ingesta (carga, progreso, cancelación), chat y conversaciones, temas similares, NotebookServIA | Solo Usuario Gubernamental | RF-02, RN-03, RF-05..20 |
| Archivos de la carpeta de documentos | Protegida (004a) | RNF-07 |

No clasificadas por el ERS — tabla aprobada (decisión 3; donde el código difiera, `xfail` RNF-07.5 o RF-02.3):
| Función | Clase |
|---|---|
| Estadísticas de tareas de ingesta en curso | Solo Usuario Gubernamental |
| Estadísticas de conversaciones propias | Solo Usuario Gubernamental, sus conversaciones (RF-14) |
| Salud del almacén de conversaciones | Solo Usuario Gubernamental, sin detalle interno |
| Fijar el tema de una conversación | Solo Usuario Gubernamental (RF-11) |
| Bitácora de un tema; registrar exportación de bitácora | Solo Administrador (RF-22) |
| Historial propio en la bitácora | Solo Usuario Gubernamental, sus filas |
| Actualizar el último acceso de una cuenta | Solo Administrador (lo actualiza el sistema, RF-01) |
| Resumen con IA de tema similar | Solo Usuario Gubernamental (RF-20) |
| Listar y descargar archivos de un tema | Solo Usuario Gubernamental (RF-12, RF-20); sin notebooks ajenos (RF-17.3) |

## Requisitos funcionales
Todas las pruebas son de integración salvo que se diga otra cosa.

### A. Sesión y acceso por rol
- **RF-01.1** (RF-01, FS-01; HU-01; CU-01 p. 6-8): CUANDO un usuario Activo de cualquier rol, sin cambio pendiente, inicia sesión con credenciales correctas, EL SISTEMA responde con éxito, entrega un token firmado con **identificador, rol y correo** y vigencia **igual a la configurada** (por omisión **60 min**), los datos del usuario sin contraseña ni hash, y **actualiza el último acceso**.
  - *Comprobación*: por rol, con vigencia fijada: token decodificado (sin clave) con id, rol y correo; vencimiento − emisión = vigencia (±1 s); sin contraseña ni hash; último acceso posterior al inicio de la prueba. Unitaria: sin configuración, 60 min; si no, `xfail` «RF-01.1 · autenticación».
- **RF-01.2** (RF-01; CU-01 FE-01): SI el correo no existe, la contraseña no coincide o la cuenta está Inactiva, ENTONCES responde **401 «Credenciales inválidas»** idéntico en los tres casos, sin token, **sin diferencia de tiempo** que revele el caso, y registra el intento fallido **con su motivo** (correo no registrado, contraseña incorrecta, cuenta inactiva), visible solo para el Administrador.
  - *Comprobación*: tres casos con código, cuerpo y mensaje idénticos; sin token; una fila por caso con motivo distinto y sin la contraseña. Tiempo: unitaria estructural (la comparación contra un hash corre exactamente una vez en los tres casos, con hash de relleno si el correo no existe). `xfail` «RF-01.2 · autenticación» por separado (motivo y tiempo). Tiempos reales: verificación manual (como 003b).
- **RF-01.3** (CU-01 FA-02): CUANDO inicia sesión una cuenta con contraseña temporal (último acceso vacío), EL SISTEMA responde con éxito indicando el cambio obligatorio y **no** actualiza el último acceso.
  - *Comprobación*: usuario `PRUEBA` sin último acceso: indica el cambio y la fecha sigue vacía. La interfaz es de la 005.
- **RF-01.6** (CU-01 FA-02): CUANDO un usuario con cambio pendiente lo completa con **su** sesión (temporal, nueva y confirmación), EL SISTEMA guarda la nueva con hash, actualiza el último acceso, lo registra (RF-21) y el siguiente inicio ya no pide el cambio. SI la temporal es incorrecta o la nueva es igual a la actual, ENTONCES no cambia nada y responde error de datos en español.
  - *Comprobación*: la temporal deja de servir y la nueva sirve; último acceso con fecha; fila sin contraseña; en los dos errores el hash no cambia. La exigencia de sesión propia la cubre RNF-07.5; el mínimo de 8 caracteres (RNF-08) queda fuera.
- **RF-01.4** (RF-01, HU-24, CU-02; D-2): CUANDO un usuario cierra sesión, EL SISTEMA registra el cierre a nombre de **ese** usuario (RF-21) y desde entonces **rechaza con 401** ese token en toda ruta protegida, incluida la renovación. SI el registro falla, ENTONCES la sesión se cierra igual.
  - *Comprobación*: tras cerrar, ruta protegida y renovación con el mismo token dan 401; fila a nombre del usuario del token; con la bitácora forzada a fallar, el cierre responde éxito y el token deja de servir. *Estado actual*: el servidor aún acepta el token → `xfail` estricto «RF-01.4 · autenticación». Al cierre: RF-01 a Parcial y CU-02 (paso 5 y postcondición) dice que el servidor deja de aceptar el token.
- **RF-01.5** (CU-01 p. 9): CUANDO un usuario con token vigente pide renovar, EL SISTEMA entrega un token nuevo con mismo id, rol y correo y vigencia configurada contada desde la renovación. SI el token falta, es inválido, vencido o firmado con otra clave, ENTONCES 401 sin token.
  - *Comprobación*: por rol (emisión nueva > anterior; vigencia configurada) y los cuatro inválidos (modelo: JWT inventados de las pruebas humo).
- **RF-02.3** (RF-02, RN-03; HU-02; CU-03 FE-02): EL SISTEMA verifica el rol en las rutas de los **flujos críticos**; con el rol equivocado responde **403** (no 5xx ni 404) sin ejecutar la acción. El Administrador no entra a ingesta, chat, descarga del citado ni NotebookServIA; el Usuario Gubernamental no entra a la gestión de usuarios.
  - *Comprobación*: cada ruta de los flujos críticos (Definiciones) con el token del otro rol → 403; sin filas, puntos en Qdrant, archivos ni correos nuevos. El resto del inventario no entra en la matriz (decisión 7-B; ver Fuera de alcance); donde el código difiera, `xfail` «RF-02.3 · <módulo>».
- **RNF-07.5** (RNF-07): SI una petición a una ruta **protegida** no trae token o trae uno inválido, vencido o de otra clave, ENTONCES **401**, sin ejecutar, sin contenido y sin 5xx. Solo las públicas y la pública deliberada (avatares) se exceptúan; el comportamiento de los avatares ya lo cubren las pruebas de la 004a y no se repite.
  - *Comprobación*: recorre **todo** el inventario sin token y con token inválido, con el método registrado y datos válidos. *Estado actual*: funciones de la propia cuenta sin token → cada caso `xfail` estricto «RNF-07.5 · autenticación», sin nombrar la ruta; la lista la produce la prueba y no se copia en documentos. Los estáticos corregidos por la 004a **pasan**.
  - *Casos del recorrido*: (a) OPTIONS (CORS) no es acceso: solo se exige que no devuelva contenido ni ejecute; (b) 307 por barra final: se sigue y se exige 401 en el destino; (c) 405 no cuenta: solo métodos registrados; (d) 422 sin token solo con datos inválidos y sin efecto ni contenido; con datos válidos, 401; (e) `/docs`, `/redoc`, `/openapi.json` y su auxiliar son protegidas: si hoy responden sin sesión, `xfail` «RNF-07.5 · autenticación».
- **RNF-07.6** (RNF-07, RF-14, RF-18, RF-19; `api-conventions.md`): SI un Usuario Gubernamental pide un **recurso ajeno** (listar, previsualizar o quitar documentos de un notebook ajeno, consultar su chat; ver, eliminar o restaurar una conversación ajena), ENTONCES **404** con el mismo código y cuerpo que un recurso inexistente, sin leer, modificar ni entregar nada.
  - *Comprobación*: dos usuarios `PRUEBA`; cada operación con el token del otro → 404 idéntico al de un id inexistente; base, Qdrant, archivos y almacén de conversaciones sin cambios. *Estado actual*: las conversaciones distinguen «existe»/«no existe» → `xfail` «RNF-07.6 · RAG» o «RNF-07.6 · notebooks».

### B. Subir → Procesado → el chat lo cita
- **RF-05.1** (RF-05, RNF-02; HU-05; CU-07 p. 7): CUANDO el Usuario Gubernamental sube uno o varios documentos indicando un tema, EL SISTEMA guarda cada archivo, encola su procesamiento, responde **un identificador de tarea por archivo sin esperar** al procesamiento y registra la carga iniciada con usuario y tema (RF-21; con rechazados, ver RF-05.22).
  - *Comprobación*: API real **con encolado interceptado**: un id por archivo; cada archivo guardado en la carpeta de su tema dentro de la carpeta temporal (RA-02.5), sin sobrescribir otro; una tarea encolada por archivo; fila de carga iniciada; aún **no** existen documento ni fragmentos. Sin «Estado actual»: la 004a ya valida tema y nombre antes de escribir (RF-06.20, RF-05.20), escribe sin sobrescribir y borra solo lo que creó (RF-05.21); la prueba espera ese comportamiento y pasa (no `xfail`). Sus regresiones (nombres no válidos, 255 bytes, fallo de escritura) no se repiten.
- **RF-06.1** (RF-06; HU-06; CU-07 p. 7): CUANDO termina el procesamiento de un archivo en un tema inexistente, EL SISTEMA ha creado el tema y asociado el documento; si existía, lo agrega. El tema va en los metadatos de cada fragmento (clave anidada).
  - *Comprobación*: con procesamiento ejecutado y tema en **formato heredado** (decisión 2): un tema y una relación; segunda carga al mismo tema → sin duplicar y con dos documentos; fragmentos con filtro `metadata.numero_expediente` = tema.
- **RF-06.2** (RF-06 y su «Estado actual»): CUANDO sube a un tema de **nombre libre**, EL SISTEMA lo acepta, crea o reutiliza el tema y el chat acotado a ese tema recupera el documento.
  - *Comprobación*: aparte del flujo principal, tema libre con prefijo `PRUEBA`. Lo incumplido, `xfail` «RF-06.2 · ingesta» **solo tras verla en rojo**.
- **RF-07.1** (RF-07; HU-07; CU-07 p. 8-9): CUANDO termina el procesamiento de un texto válido, EL SISTEMA deja el documento **Procesado** y el progreso de su tarea informa completado y 100 %.
  - *Comprobación*: Tika real, procesamiento dentro de la prueba: estado «Procesado» en la base y progreso terminado.
- **RF-07.2** (RF-07; CU-07 FE-03): SI el procesamiento de un archivo falla, ENTONCES **ese** documento queda en **Error** y los demás de la carga en Procesado. (a) El **progreso** de esa tarea informa fallo con «No se pudo procesar el archivo. Por favor, intente nuevamente.» + la **causa clasificada** (Definiciones), sin texto de excepción ni rutas; (b) la **fila de error de la bitácora** conserva la causa (su presentación clasificada es RF-22.1).
  - *Comprobación*: carga de dos documentos con fallo provocado en la **extracción** de uno (mecanismo en el plan, sin detener servicios): el otro queda Procesado con fragmentos; progreso con texto fijo y causa; fila con la causa. (a) y (b) con `xfail` «RF-07.2 · ingesta» por separado si no se cumplen. Al cierre se propone alinear CU-07 FE-03.
  - «El documento queda en Error» es una aserción aparte con `xfail` estricto «RF-07.2 · ingesta»: hoy el documento se registra después de extraer, así que un fallo de extracción no deja documento.
  - El bloque F **no** clasifica el progreso: es código de producción del bloque B y la 004 no lo corrige. Si (a) falla (hoy entrega el nombre y el texto de la excepción), queda `xfail` para la retroactiva de ingesta, que puede reutilizar la clasificación que el bloque F crea para RF-22.1.
- **RF-08.1** (RF-08; HU-08; CU-07 p. 10): CUANDO un documento pasa a Procesado, EL SISTEMA ya tiene en Qdrant **todos** sus fragmentos (tantos como informó el procesamiento, ≥ 1), con vector de 1024 y metadatos de tema, nombre de archivo e id de documento.
  - *Comprobación*: nº de fragmentos en Qdrant = nº en la fila «Documento almacenado» (RF-22.1) (> 0); dimensión; `metadata.nombre_archivo` = nombre subido; `metadata.id_documento` = id de la base. Si la bitácora no guarda el número, se compara con el resultado de la tarea y esa parte es `xfail` «RF-21.7 · bitácora».
- **RF-11.1** (RF-11, RF-12; HU-11, HU-12; CU-09 p. 5-7): CUANDO pregunta en el chat acotado a un tema por un documento recién Procesado, EL SISTEMA (a) envía al modelo el fragmento con la frase distintiva **y el nombre de su archivo**; (b) **no** incluye fragmentos de otro tema aunque sean los más parecidos; (c) responde en streaming con fragmentos y evento final; (d) registra la consulta con el tema (RF-21).
  - *Comprobación*: Ollama simulado. (b): dos documentos en temas A y B; acotado a A se pregunta **por la frase de B** → el contexto no la contiene; control: en consulta general sí recupera B. (c): formato de eventos que **hoy define el código**; se decodifican y terminan con el evento final. Calidad real de la cita: exenta, verificación manual con Ollama real (decisión 10).
- **RF-11.2** (RF-11; CU-09 FE-03; `api-conventions.md`): SI no se puede conectar con el motor de lenguaje o falla, ENTONCES informa el error **dentro de la conversación** en español con posibles causas, **sin** texto de excepción, cierra con el evento final y sin 5xx.
  - *Comprobación*: simulado en fallo de conexión: evento de error en español, sin la cadena inventada de la excepción, evento final. Si no, `xfail` «RF-11.2 · RAG». El reintento automático (RF-11, CU-09 FE-01) vive en la interfaz → spec 005; aquí solo: si el modelo no devuelve texto, el backend cierra con evento final, sin fragmentos ni error.
- **RF-12.1** (RF-12; CU-09 p. 6): CUANDO pide descargar el original de un documento citado de un tema, EL SISTEMA entrega el archivo tal cual. SI no existe en ese tema, ENTONCES 404 con mensaje en español y sin contenido.
  - *Comprobación*: contenido idéntico byte a byte; nombre inexistente → 404. Protecciones de ruta: 004a. Notebook ajeno: RF-17.3.

### C. NotebookServIA
- **RF-17.1** (RF-17; HU-17; CU-11): CUANDO crea un notebook con nombre no vacío, EL SISTEMA lo crea a su nombre, con clave interna propia, primero en **su** lista. SI el nombre está vacío o solo espacios, ENTONCES no lo crea y responde 4xx (no 5xx) en español.
  - *Comprobación*: dos notebooks: orden (más reciente primero) y no aparecen en la lista de otro usuario; vacío y solo espacios → 4xx, sin fila.
- **RF-17.2** (RF-17, RF-05, RF-06; CU-07 FA-01): CUANDO sube un documento a **su** notebook, EL SISTEMA lo procesa como cualquier carga (RF-05.1 a RF-08.1) con el notebook como tema, y aparece en la lista del notebook con estado Procesado.
  - *Comprobación*: API real con la clave interna como tema: lista con nombre y Procesado; fragmentos con la clave en los metadatos.
- **RF-17.4** `[NUEVO]` (RF-17; se propone aclararlo en el ERS): SI sube archivos con la clave de un notebook **ajeno** o inexistente, ENTONCES **404** (igual que inexistente), sin guardar, encolar ni crear el tema.
  - *Comprobación*: dos usuarios `PRUEBA`: 404 y ni archivo, tarea, documento ni fragmentos. Si no, `xfail` «RF-17.4 · notebooks».
- **RF-11.3** (RF-11, FN-03; CU-09 FA-05): CUANDO pregunta en el chat de **su** notebook, EL SISTEMA envía al modelo solo fragmentos de ese notebook, con su nombre de archivo, nunca de otro notebook ni tema. SI el notebook no existe o es ajeno, ENTONCES no responde con contenido de ninguna parte (RNF-07.6).
  - *Comprobación*: dos notebooks del mismo usuario y un tema general, cada uno con su frase; se pregunta por la de **otro**: el contexto solo trae fragmentos del notebook consultado. Ajeno o inexistente: el modelo no recibe ninguna frase. Si no, `xfail` «RF-11.3 · notebooks».
- **RF-17.3** `[NUEVO]` (RF-17 frente a RF-11; decisión 1): EL SISTEMA nunca entrega a un usuario documentos del notebook de **otro**: ni en el chat general o por tema, ni en temas similares, ni en descargas. Al cierre hay que editar RF-11, RF-12, RF-17 y RF-20 del ERS con el visto bueno del tutor.
  - *Comprobación*: A sube a su notebook; B consulta su frase en los cuatro alcances; contexto, resultados y descargas sin el documento de A. Si no, `xfail` «RF-17.3 · notebooks».
- **RF-18.1** (RF-18; HU-18; CU-12): CUANDO pide ver el original de un documento **Procesado** de su notebook, EL SISTEMA lo entrega tal cual, en línea (sin forzar descarga) y con tipo de contenido acorde. SI no está Procesado, ENTONCES error de datos en español sin archivo. Ajeno: RNF-07.6.
  - *Comprobación*: byte a byte; sin pedir descarga; documento Pendiente creado por la prueba → 4xx con mensaje y sin cuerpo de archivo.
- **RF-19.1** (RF-19, RN-01, RNF-10; HU-19; CU-13): CUANDO quita un documento de su notebook, EL SISTEMA elimina sus **tres** representaciones (fragmentos, archivo, registro con su relación al tema); deja de listarse y el chat del notebook no recibe su contenido. No elimina el notebook, el tema, otros documentos ni filas de bitácora.
  - *Comprobación*: con dos documentos, al quitar uno sus tres capas quedan en cero y el otro intacto; lista y contexto sin él; notebook, tema y bitácora conservan sus filas.
- **RF-19.2** (RF-19, «sin información huérfana»; decisión 4): SI falla alguna de las tres eliminaciones, ENTONCES informa el error en español (sin texto de excepción), el documento **sigue listado** hasta que se borren las tres capas, y un nuevo intento completa lo que faltó y termina con éxito.
  - *Comprobación*: fallo provocado en la eliminación de fragmentos y en la del archivo (mecanismo en el plan): error con mensaje y documento listado; un segundo intento deja las tres capas en cero y el documento deja de listarse. *Estado actual* (ERS): no se informa → `xfail` «RF-19.2 · notebooks». La confirmación en la interfaz es de la 005.

### D. Bitácora de los flujos críticos
- **RF-21.7** (RF-21): EL SISTEMA deja fila con usuario, fecha, tipo y, si aplica, tema de: inicio de sesión exitoso y fallido (con motivo), cierre, cambio obligatorio de contraseña, consulta al asistente y **carga** (una fila de carga iniciada con el tema y, por archivo, su resultado: «Documento almacenado» con id de documento y nº de fragmentos (más la de «Procesamiento terminado», sin esos datos), o error con causa). Ninguna fila con contraseñas ni token.
  - *Comprobación*: dentro de las pruebas de RF-01.1, 01.2, 01.4, 01.6, 05.1, 07.2, 08.1 y 11.1: cada fila por usuario y tipo, **sin exigir un número exacto** por carga; se busca la contraseña y el token en todas las filas creadas.

### E. Soporte de pruebas (no es producto; solo se menciona en RA-02)
- **RA-02.12** `[NUEVO]` (antes RF-02.4): EL inventario clasifica **todas** las rutas registradas. SI aparece una sin clasificar o la tabla clasifica una que ya no existe, ENTONCES la prueba falla y nombra la ruta.
  - *Comprobación*: unitaria que compara rutas registradas con la tabla (ninguna sobra ni falta); su rojo con una ruta de ejemplo agregada dentro de la prueba.
- **RA-02.13** `[NUEVO]`: la suite permite (a) subir por la API real con **encolado interceptado**, (b) subir y **ejecutar el procesamiento dentro de la prueba** y (c) disponer de un **notebook propio de prueba** de un usuario `PRUEBA` sin depender de las pruebas de RF-17.1 (lo usa RF-05.22), en la carpeta temporal y sin tocar `uploads/` de desarrollo. Sin pausas fijas: si un estado no llega, falla diciendo qué esperaba.
  - *Comprobación*: prueba humo de cada modo; `uploads/` de desarrollo sin cambios (manual, como 002).
- **RA-02.14** `[NUEVO]`: los documentos de prueba los genera la suite (prefijo `PRUEBA`, frase distintiva). Todo lo creado (temas, documentos, relaciones, notebooks, fragmentos, archivos, filas de bitácora, conversaciones) se limpia al terminar, también con tema en formato heredado sin prefijo; residuos en cero, también con `--orden-inverso`.
  - *Comprobación*: conteo de residuos de la 002 ampliado a estos flujos, incluidas las conversaciones (Redis simulado o disco).
- **RA-02.15** `[NUEVO]` (RA-01, RA-02; decisión 12): sobre la línea base (Objetivo), esta spec aumenta la corrida como máximo **3 min** (mismo equipo) y ninguna prueba de flujo pasa de **30 s**.
  - *Comprobación*: duración antes y después en el plan, y `--durations`.

### F. Correcciones: archivos rechazados (decisión de Andrés, 14/10)
Única excepción a «sin código de producción»: errores que la 004a dejó pendientes (paso 6 de su plan). Son correcciones (permitidas en el paso 2 de `.claude/rules/testing.md`), no `xfail`. Cada una empieza por su prueba de regresión, vista en rojo con el error actual.
Decisión C (14/10): los textos que estas pantallas muestran los entrega el sistema ya redactados en español; la pantalla solo los presenta, sin armarlos ni cambiarlos (principio 3). Las integraciones cubren ese contenido.
**Exención temporal hasta la 005** (la repite el plan): que una pantalla presente tal cual lo que entrega el sistema se puede medir de extremo a extremo; no es solo aspecto visual, así que el principio 4 no la cubre.
- Se acepta solo porque el extremo a extremo llega con la 005 (paso 2 partido, Andrés 07/10) y la 004 no suma dependencias de JavaScript (principio 1).
- Condición de cierre: la 005 cubre de extremo a extremo RF-05.23, RF-22.1 y RNF-04.1; si no los cubre, no se cierran.
- Regla de estado (Andrés, 15/10, opción B): la 004 se cierra al terminar la tarea 14. Esos tres quedan «implementados, pendientes de la 005» en las tareas, y en el ERS con un «Estado actual»: «implementado; pendiente la verificación de extremo a extremo (spec 005)».
- Solo RNF-04.1 usa además la exención por aspecto visual del principio 4.
- **RF-05.22** (RF-05 «Manejo de errores» y «Salida»; HU-05; CU-07 p. 7, FA-01, FE-05): CUANDO una carga a un tema válido, desde Ingesta o desde un notebook propio, incluye archivos rechazados, EL SISTEMA responde con éxito y añade a lo que ya entrega:
  - los aceptados (cuántos y su identificador de tarea) y los rechazados (cuántos y, de cada uno, su posición en la carga y su motivo ya redactado en español);
  - la confirmación ya redactada en español, que cuenta solo los aceptados (texto exacto en el plan); si no hay aceptados, ningún texto dice que se enviaron archivos.
  - *Motivos* (solo los rechazos que el sistema ya produce; literales de «Causa clasificada»): «nombre de archivo no válido» (RF-05.20), «archivo vacío», «no se pudo guardar el archivo» (RF-05.21) y «error interno». Ninguno repite el nombre recibido, una ruta ni el texto de una excepción (RNF-07.23, RNF-07.24). Formato, tipo y tamaño: fuera de alcance.
  - *Contrato*: la lista de identificadores que hoy se entrega (uno por archivo, en el orden enviado, cada rechazado en su posición y con su forma actual) no cambia; lo nuevo se añade sin quitar ni renombrar nada. Así la interfaz actual sigue funcionando entre 9a y 9b. El plan inventaría los consumidores.
  - *Excepción explícita* (Andrés, 15/10, opción A): el mensaje y el total de archivos que hoy se entregan conservan nombre y tipo, pero cambia su valor: el mensaje pasa a ser la confirmación y el total cuenta solo los aceptados. Ningún consumidor de la interfaz los usa (verificado por el reviewer).
  - *Todos rechazados*: misma forma de respuesta, con éxito, 0 aceptados, cada rechazado con su motivo y un mensaje que no dice que se enviaron archivos. Excepción deliberada a la convención de 4xx: la petición es válida y se rechaza cada archivo; con un 4xx la interfaz no mostraría los motivos.
  - *Toda la carga rechazada*, sin conteos ni rechazados: tema no válido → 400 (RF-06.20). Notebook ajeno o inexistente: lo exige RF-17.4 (404), que puede quedar `xfail`; RF-05.22 no lo garantiza.
  - *Bitácora* (RF-21): la carga iniciada se registra solo con al menos un aceptado, con el número de aceptados y, si hubo, el de rechazados; el texto de esa fila cuenta solo los aceptados. Cada archivo rechazado deja **una** fila de rechazo con su motivo, sin el nombre ni el tema (como la 004a hace hoy con nombre y tema no válidos; Andrés, 15/10: también archivo vacío, guardado fallido y error interno).
  - *Comprobación*: encolado interceptado (RA-02.13); a un tema y al notebook propio de RA-02.13 (c), un válido, uno vacío y uno de nombre no válido:
    - aceptados 1 con su tarea; rechazados 2 con posición y motivo; total 1 y confirmación con 1;
    - filas nuevas exactamente: una de carga iniciada (1 aceptado, 2 rechazados), una de rechazo «archivo vacío» y una «nombre de archivo no válido»;
    - la lista de identificadores tiene el mismo largo, orden y forma que antes (detalle en el plan); ningún cuerpo ni fila contiene el nombre no válido.
    - Guardado fallido y error interno provocados: rechazados con su motivo y una fila de rechazo cada uno, sin texto de excepción.
    - Ese mecanismo (lo fija el plan) no deja archivos sin tarea, o la prueba los borra: residuos en cero (RA-02.14). Si se hace fallar el encolado, el archivo ya guardado queda (hallazgo excluido) y la prueba lo limpia.
    - Todos rechazados (vacío y nombre no válido): éxito, aceptados 0, sin tarea ni confirmación de envío; exactamente dos filas de rechazo y ninguna de carga iniciada. Tema no válido: 400 sin conteos.
    - Regresiones: hoy el total, el mensaje y el texto de la carga iniciada cuentan los rechazados, la carga iniciada se registra aunque no haya aceptados y el vacío, el guardado fallido y el error interno no dejan fila de rechazo.
- **RF-05.23** (RF-05 «En caso de error», RNF-03; HU-05; CU-07 FA-01, FE-05): CUANDO la respuesta de una carga trae rechazados, las pantallas de Ingesta y de NotebookServIA muestran al Usuario Gubernamental, tal como los entrega el sistema, un aviso con el motivo de cada rechazado y la confirmación de RF-05.22; los aceptados siguen su curso.
  - Un rechazado no pasa a «procesando» ni se consulta su progreso, ni en Ingesta (su fila queda rechazada con su motivo tal cual) ni en el notebook (carga desde la lista o pegando o arrastrando sobre el chat).
  - Ningún aviso de éxito ni de subida iniciada aparece antes de la respuesta; con 0 aceptados no aparece ninguno.
  - Ingesta envía una carga por tema: muestra un aviso por cada respuesta, tal cual, sin sumarlas (sumar obligaría a la pantalla a armar textos; principio 3); cada aviso va junto al tema que el usuario escribió, dato que la pantalla ya tiene.
  - Una imagen pegada o arrastrada sobre el chat del notebook (CU-07 FA-01) con nombre válido es aceptada, con la misma confirmación, y llega a Procesado.
  - *Comprobación automatizada*: integración del contenido que la pantalla presenta, desde Ingesta y desde un notebook: motivos sin el nombre, confirmación con solo los aceptados y, con todos rechazados, sin confirmación de envío. La regresión del conteo se ve en rojo aquí.
  - *Manual* (exención temporal hasta la 005): en las dos pantallas con la carga mixta de RF-05.22, y pegando o arrastrando una imagen sobre el chat del notebook (CU-07 FA-01), en escritorio y a 616 px de ancho:
    - aviso con los motivos tal cual, confirmación con los aceptados, rechazados sin «procesando» en las dos pantallas, el aceptado llega a Procesado, consola sin errores; dos temas a la vez en Ingesta → un aviso por tema; todos rechazados → sin aviso de éxito;
    - el Administrador no entra a esas pantallas. Regresión manual: hoy no hay aviso, «Subida iniciada» sale antes de la respuesta y los rechazados quedan «procesando».
- **RF-22.1** `[NUEVO]` (detalla RF-22 «Detalle» y RF-21 «Contenido del registro»; HU-22; CU-15 FA-01): CUANDO el Administrador consulta la bitácora completa, EL SISTEMA entrega con cada registro de carga (los tipos de la tabla) su detalle listo para mostrar al abrirlo (CU-15 FA-01):
  - el nombre visible de su tipo (columna 1) y cada dato con su etiqueta en español y su valor, en el orden de la tabla; las etiquetas dicen «Tema», nunca «Expediente» (principio 7, RT-06);
  - solo los datos que la bitácora guardó: ninguna etiqueta con valor vacío.

  | Tipo (nombre visible) | Fila de la bitácora | Datos (etiqueta: valor) |
  |---|---|---|
  | Carga iniciada | carga iniciada | Tema; Fecha y hora; Archivos aceptados; Archivos rechazados (solo si > 0) |
  | Inicio del procesamiento | inicio, del procesamiento | Tema; Fecha y hora; Archivo |
  | Documento almacenado | almacenamiento (número real del documento y fragmentos) | Tema; Fecha y hora; Archivo; Documento (su número); Fragmentos |
  | Procesamiento terminado | completado, del procesamiento (su identificador no es el número del documento) | Tema; Fecha y hora; Archivo |
  | Error de procesamiento | error | Tema; Fecha y hora; Archivo; Causa (clasificada) |
  | Carga rechazada | rechazo (cualquier motivo) | Fecha y hora; Motivo — sin tema ni nombre (RNF-07.24) |
  | Cancelación · Error de cancelación · Otra fase | cancelado, error de cancelación u otra fase | Tema; Fecha y hora; Archivo |

  - No se muestran: identificador de tarea, colección, número de vectores, fase interna ni el error crudo (datos técnicos que no aportan al Administrador). No cambia lo que el procesamiento guarda (P2).
  - *Valores de relleno*: si el tema guardado es «N/A» o está vacío, o el archivo es «Error general» o «Task <identificador>», ese dato se omite. Resultado: la cancelación y su error muestran solo Fecha y hora; el error general de la carga, Tema; Fecha y hora; Causa «error interno» (no guardó error).
  - La pantalla de detalle presenta esa lista tal cual y, en los registros de carga, **sustituye** a los datos que hoy pinta («Expediente», «Task ID», «Número de Chunks», «Colección»; Andrés, 15/10).
  - En los registros de carga, la descripción del detalle muestra el nombre visible del tipo en lugar del texto guardado de la fila (que puede contar rechazados o decir «chunks»).
  - El encabezado fijo del detalle dice «Tema» y «Sin tema asociado» en lugar de «Expediente» y «Sin expediente asociado», en todos los registros: es texto visible, no un identificador de código ni de la base (RT-06 no lo impide; principio 7).
  - En un registro de carga sin tema asociado cuya lista trae «Tema» (p. ej. la carga iniciada de un tema nuevo), el encabezado muestra ese valor.
  - *Dónde viaja*: con cada registro del listado de la bitácora completa, desde el que hoy se abre el detalle; no hace falta otra consulta.
  - *Contrato de la API*: la lista se **añade** sin quitar ni renombrar datos. No cambian: la bitácora de un tema, el historial propio, el contenido de la exportación ni los registros que no son de carga (p. ej. una descarga rechazada). El plan inventaría los consumidores.
  - *Contenido prohibido*: contraseñas, token, rutas del servidor, texto de excepción y el nombre de un archivo rechazado. La causa es siempre una de «Causa clasificada», nunca el error crudo guardado (RNF-07.23, `api-conventions.md`).
  - SI la consulta de la bitácora completa falla, ENTONCES responde 500 con «Error interno del servidor», sin el texto de la excepción, que va al registro del servidor (`api-conventions.md`; hoy lo devuelve en la respuesta).
  - *Comprobación automatizada*: integración con filas de cada tipo de la tabla creadas por la suite, incluidas una cancelación y un error general con valores de relleno:
    - la bitácora del Administrador entrega el nombre visible y la lista de cada una con las etiquetas y el orden de la tabla; sin etiquetas vacías, «Expediente», «N/A» ni «Task»; sin los datos técnicos excluidos; la rechazada sin el nombre; los datos previos siguen presentes;
    - una fila de error con texto de excepción inventado muestra solo su causa clasificada; uno no reconocido, «error interno»;
    - en las listas no aparecen la contraseña, el token, una ruta del servidor ni el texto de una excepción provocada;
    - la bitácora de un tema, el historial propio y un registro de descarga rechazada quedan como antes, sin la lista; la exportación conserva su contenido (cómo se comprueba, en el plan);
    - consulta forzada a fallar → 500 genérico sin el texto inventado de la excepción;
    - el Usuario Gubernamental pide la bitácora completa → 403.
    - Unitaria del armado de la lista por tipo y de la clasificación, con textos inventados en las formas reales: cada regla, conflictos de precedencia (extracción con patrón de conexión; nombre que contiene «vector»), no reconocido y vacío. Regresión: hoy no hay lista; la pantalla muestra la fecha del registro, pero la información adicional de la carga no muestra la causa clasificada y sí datos técnicos; el 500 expone la excepción.
  - *Manual* (exención temporal hasta la 005): un registro de cada tipo con el Administrador, en escritorio y a 616 px, consola sin errores; encabezado «Tema» (con el tema en la carga iniciada de un tema nuevo); descripción con el nombre del tipo; el Usuario Gubernamental no ve la bitácora completa.
- **RNF-04.1** (RNF-04): el aviso de RF-05.23 y el detalle de RF-22.1 son legibles, sin elementos superpuestos ni inaccesibles, en escritorio y en una pantalla pequeña de 616 px de ancho (la medida de la 004a).
  - A 616 px cuenta como accesible llegar al aviso y al detalle con desplazamiento horizontal (mismo criterio que la 004a). Rediseñar la tabla queda fuera de alcance.
  - *Comprobación*: manual en los dos tamaños con los dos roles, consola sin errores. En la 004, exento por aspecto visual (principio 4) y por la exención temporal; su extremo a extremo es condición de cierre en la 005. El contenido lo cubren las integraciones de RF-05.23 y RF-22.1.

## Requisitos no funcionales
- **RNF-09.1** (RNF-09, RT-02): ninguna prueba llama a servicios reales de LLM, HTR, audio ni correo; se usan los simulados de la 002 y su comprobación (RA-02.6).
- RT-07: los mensajes de error comprobados están en español (dentro de cada requisito).

## Casos límite
- Token ausente, inválido, vencido o de otra clave en cualquier ruta: RNF-07.5 (renovación: RF-01.5); OPTIONS, 307, 405, 422, documentación: RNF-07.5 (a)-(e).
- Ruta nueva sin clasificar o clasificada inexistente: RA-02.12.
- Rol equivocado en un flujo crítico: RF-02.3. Token de sesión cerrada (incl. renovación) y fallo del registro del cierre: RF-01.4.
- Cuenta Inactiva, correo inexistente, contraseña incorrecta: RF-01.2. Contraseña temporal: RF-01.3; su cambio y errores: RF-01.6.
- Varios archivos: un id por archivo (RF-05.1); uno falla y otro no (RF-07.2).
- Tema inexistente/existente: RF-06.1. Tema libre: RF-06.2.
- Pregunta por el documento de otro tema: RF-11.1. Dos notebooks del mismo usuario: RF-11.3. Notebook ajeno: RNF-07.6, RF-11.3, RF-17.3, RF-17.4. Conversación ajena: RNF-07.6.
- Motor sin conexión y respuesta vacía: RF-11.2. Archivo citado inexistente: RF-12.1. Documento no Procesado: RF-18.1.
- Fallo de una de las tres eliminaciones y reintento: RF-19.2; quitar uno de dos: RF-19.1. Nombre de notebook vacío o espacios: RF-17.1.
- Prueba cortada a la mitad: residuos y reemplazo de la base de la 002 (RA-02.4, RA-02.14).
- Carga con aceptados y rechazados, o solo rechazados (éxito con 0 aceptados), desde Ingesta, un notebook o pegando una imagen en su chat; archivo vacío, guardado fallido o error interno (cada uno con su fila de rechazo): RF-05.22, RF-05.23. Sin aceptados, sin fila de carga iniciada ni aviso de éxito: RF-05.22, RF-05.23. Varios temas a la vez en Ingesta: un aviso por tema (RF-05.23).
- Tema no válido: toda la carga rechazada, sin conteos (RF-06.20; RF-05.22). Notebook ajeno: RF-17.4.
- Detalle de un rechazo (sin el nombre ni el tema); error crudo no reconocido o ausente → «error interno»; valores de relleno omitidos; fallo de la consulta de la bitácora → 500 genérico; otros consumidores y tipos de registro sin cambios: RF-22.1.
- Rechazo de formato o tamaño en el procesamiento: hoy deja dos filas de error (una con el motivo detallado y otra con el resumen); ambas muestran «formato o tamaño no permitido» (RF-22.1).
- Fallo de extracción: no deja documento en Error (`xfail`, RF-07.2).
- Cuenta desactivada con token vigente: solo observación para la retroactiva de autenticación, sin prueba (decisión 11).

## Fuera de alcance
- **004a** (cerrada): lectura y escritura fuera de la carpeta de documentos, estáticos protegidos, comportamiento de la ruta pública de avatares, validación del tema y del nombre, guardado fuera de la carpeta del backend y sus regresiones.
- **005**: todo lo del navegador (middleware y `ROUTE_PERMISSIONS`, menú por rol, redirecciones, panel de cambio obligatorio, confirmación al quitar, streaming en pantalla, **reintento automático del chat**, RF-16, RNF-04 —salvo la verificación manual de RNF-04.1—, consola, y el extremo a extremo de las pantallas del bloque F), su instancia de pruebas, cómo recibe las contraseñas y el cierre de la exención E2 de la 003. En la 004, sin dependencias de pruebas de JavaScript.
- **Retroactiva de autenticación**: corregir rutas sin sesión, invalidación del token (RF-01.4), motivo y tiempo (RF-01.2), clave de firma, mínimo de 8 (RNF-08), cambio voluntario (RF-04), exigir sesión a los avatares, sus registros y los demás, la **matriz de roles en el resto del inventario** (decisión 7-B) y la cuenta desactivada con token vigente (decisión 11).
- **Retroactiva de notebooks**: la bitácora de crear un notebook y de quitar un documento (antes RF-21.8; decisión 8-D).
- **Infraestructura de Redis** (aquí simulado).
- **Retroactivas de ingesta, RAG y chat, notebooks, temas similares y bitácora**: formato, tipo y tamaño (RF-05; hoy el servidor no los valida, «Estado actual» al cierre), audio e imagen (RF-09, RF-10), cancelación y duplicados (RF-07), fragmentos no Procesados en el chat (RF-08), búsqueda híbrida (RF-13), historial (RF-14), copiar y reintentar (RF-15), temas similares más allá de RF-17.3 (RF-20), consulta y dashboard de bitácora (RF-22, RF-23), y corregir los `xfail` de la 004.
- Otra debilidad grave no prevista: va a la 004a o a una corrección urgente aparte antes de seguir (decisión 6).
- Calidad real de la respuesta y la cita (exención, manual); rendimiento y concurrencia (RNF-01).
- `docker-compose.yml`, migraciones, prompts, modelos, dependencias nuevas (incluidas herramientas de pruebas del frontend; decisión C); código de producción fuera del bloque F. En el bloque F: otros cambios de la bitácora en la interfaz (filtro y columna heredados, RT-06), filas sin tema en la carga y el archivo que queda sin tarea si falla el encolado (hallazgos de la 004a; la prueba limpia el suyo, RF-05.22), clasificar el progreso del procesamiento (RF-07.2 a) y rediseñar la tabla de la bitácora para pantallas pequeñas (RNF-04.1).
- Bloque F, además: validar formato y tamaño en la carga (la causa «formato o tamaño no permitido» solo etiqueta el rechazo que ya hace el procesamiento; P1); cambiar lo que el procesamiento guarda en la bitácora (P2); la columna de descripción del listado de la bitácora, que sigue mostrando el texto guardado de filas anteriores (p. ej. «chunks»; hallazgo).
- Hallazgos para la retroactiva de ingesta: el tiempo de procesamiento agotado no escribe fila de error en la bitácora (P3; si la escribiera, sería «error interno»); el documento no se registra antes de extraer (RF-07.2).

## Riesgos para el plan
- Tema en formato heredado no lleva prefijo `PRUEBA`: el plan lo registra para la limpieza (RA-02.14, decisión 2).
- Memoria y tiempo (embeddings + Tika; pico 3,77 GiB de 6 en la 002): reutilizar el modelo de la sesión y medir contra la línea base.
- Almacén de conversaciones en disco o Redis: no escribir fuera de la carpeta temporal y limpiar.
- El inventario incluye estáticos (avatares públicos y documentos protegidos, por separado) y rutas del framework; tabla a mano, sin datos sensibles.
- `xfail` estricto que pasa hace fallar la corrida: marcar solo tras ver el rojo, con requisito y etiqueta, sin rutas.

## Criterios de finalización
- Cada requisito con prueba que pasa o `xfail` estricto etiquetado. Únicas exenciones (justificadas en el plan): calidad real de la cita (RF-11.1, manual), reintento del chat (005) y, en el bloque F, la exención temporal hasta la 005 de la presentación (RF-05.23, RF-22.1, RNF-04.1; su condición de cierre, en el bloque F) más el aspecto visual de RNF-04.1 (principio 4).
- La 004 se cierra al terminar la tarea 14 (Andrés, 15/10, opción B): RF-05.23, RF-22.1 y RNF-04.1 quedan «implementados, pendientes de la 005», no cerrados.
- `docker compose exec backend pytest` pasa, también con `--orden-inverso`, con cero residuos y dentro de RA-02.15; se informa cuántos `xfail` quedan (en términos generales).
- Manual por la API (sin navegador), con datos inventados: subir → Procesado con fragmentos (`metadata.numero_expediente`) → chat con **Ollama real** que cita por nombre de archivo en español → descarga del citado; lo mismo en un notebook, incluido quitar; medir tiempo de los tres inicios fallidos; bitácora de cada paso; limpieza.
- `docker compose ps` sin reinicios; logs de `backend` y `celery-worker` sin errores nuevos; `uploads/` y nº de claves del Redis de desarrollo sin cambios.
- Bloque F: regresiones vistas en rojo y luego en verde; integraciones del contenido entregado por la API pasando (RF-05.22, RF-05.23, RF-22.1); `npm run build` y `npm run lint` sin errores; manual en el navegador con los dos roles (el Administrador no entra a Ingesta ni a NotebookServIA; el Usuario Gubernamental no ve la bitácora completa), en escritorio y a 616 px.
- Documentación al cierre, en la tarea 14 (la edita otro, no el planner):
  - ERS: RF-01 Parcial (D-2); «Estado actual» de RNF-07 y RF-19 coherentes; RA-02 menciona la red.
  - ERS RF-05: «Salida» (confirmación con solo los aceptados); «Manejo de errores» con los motivos «archivo vacío», «no se pudo guardar el archivo» y «error interno» `[NUEVO]` y su fila de rechazo; «Estado actual» (el servidor no valida formato, tipo ni tamaño; retroactiva de ingesta).
  - ERS RF-22 «Detalle» (RF-22.1 y el encabezado «Tema»).
  - ERS: párrafo «Estado actual» en RF-05.23, RF-22.1 y RNF-04.1: «implementado; pendiente la verificación de extremo a extremo (spec 005)».
  - CU-02 (paso 5 y postcondición), CU-07 paso 7 (texto del plan) y FE-03, CU-15 FA-01; RF-11, RF-12, RF-17 y RF-20 por RF-17.3 y RF-17.4 (visto bueno del tutor); `MEMORY.md`.

## Tareas estimadas (D-3 = B ampliada: 18 de 20-30 min; T1-T14 con 9a-9d)
⚠️ = crea archivos nuevos. Las tres del bloque F (9a-9c) van tras la carga (decisión C: 17). 9a no depende de la 11: usa el notebook propio del soporte de la tarea 1 (RA-02.13 c).
1. ⚠️ Soporte: encolado interceptado, procesamiento en la prueba, notebook propio de prueba, documentos de prueba y limpieza ampliada (RA-02.13, RA-02.14); modifica `conftest`. La 004a ya está cerrada (14/10).
2. ⚠️ Inventario y tabla de clasificación (RA-02.12).
3. 401 en todo el inventario, casos límite y `xfail` (RNF-07.5).
4. Matriz de roles en los flujos críticos: 403 sin efectos (RF-02.3).
5. ⚠️ Inicio de sesión: éxito, token, vigencia, último acceso; inválidas con motivo y sin diferencia de tiempo (RF-01.1, RF-01.2, RF-21.7 sesión).
6. Contraseña temporal y cambio obligatorio (RF-01.3, RF-01.6).
7. Renovación y cierre (RF-01.5, RF-01.4).
8. ⚠️ Subir → Procesado → fragmentos y tema; tema libre (RF-05.1, RF-06.1, RF-06.2, RF-07.1, RF-08.1, RF-21.7 carga).
9. Error de procesamiento sin afectar a otros (RF-07.2).
9a. Bloque F, backend: aceptados y rechazados con motivo, confirmación y total ya redactados; fila de rechazo por cada motivo (RF-05.22).
9b. Bloque F, Ingesta y NotebookServIA presentan esos textos tal cual; filas rechazadas sin «procesando»; un aviso por tema (RF-05.23, RNF-04.1).
9c. Bloque F, lista etiquetada del detalle de carga con causa clasificada, 500 genérico de la bitácora, sustitución del detalle actual y encabezado «Tema» (RF-22.1, RNF-04.1). Junta backend y frontend: con lo añadido el 15/10 es previsible que el plan la parta (18 tareas).
10. ⚠️ Chat acotado que cita y no mezcla, motor sin conexión, descarga del citado (RF-11.1, RF-11.2, RF-12.1, RF-21.7 consulta).
11. ⚠️ Notebook: crear, listar, subir, listar documentos, previsualizar (RF-17.1, RF-17.2, RF-18.1).
12. Notebook: chat acotado, recursos ajenos (incl. conversaciones), aislamiento, carga a notebook ajeno (RF-11.3, RF-17.3, RF-17.4, RNF-07.6).
13. Quitar documentos, su error y reintento (RF-19.1, RF-19.2).
14. Corrida completa e inversa con duración (RA-02.15), verificación manual con Ollama real y documentación (Criterios de finalización); cierra la 004 con RF-05.23, RF-22.1 y RNF-04.1 «implementados, pendientes de la 005».

Para toda la spec: ⚠️ archivos nuevos y cambios al soporte de pruebas (`conftest`, datos); sin dependencias, migraciones, `docker-compose.yml`, prompts ni modelos; código de producción solo en el bloque F. Commit: la 004 se commitea entera al terminar (D-4; Andrés, 14/10).

## Decisiones de Andrés (12/10/2026)
1. A — notebooks privados en todo (chat general y por tema, temas similares, descargas): RF-17.3 `[NUEVO]`; al cierre, editar RF-11, RF-12, RF-17 y RF-20 con el tutor.
2. A — flujo principal con tema en formato heredado; nombre libre aparte (RF-06.2, `xfail` si falla).
3. A — tabla aprobada para las rutas que el ERS no clasifica; `xfail` donde el código difiera.
4. A — RF-19.2: un nuevo intento completa lo que faltó; el documento sigue listado hasta borrarlo todo.
5. A — raíz pública; `/docs`, `/redoc` y `/openapi.json` protegidas (`xfail` si hoy responden sin sesión).
6. A — otra debilidad grave no prevista va a la 004a o a una corrección urgente aparte antes de seguir.
7. B — RF-02.3 solo en las rutas de los flujos críticos; RNF-07.5 sigue sobre todo el inventario.
8. D — sin bitácora de crear notebook ni de quitar documento en la 004 (RF-21.8 retirado; pendiente de la retroactiva de notebooks).
9. A — entran RF-07.2, RF-11.2 y RF-19.2.
10. A — «el chat lo cita»: estructural con modelo simulado + manual con Ollama real.
11. A — cuenta desactivada con token vigente: observación para la retroactiva de autenticación.
12. A — tope: +3 min sobre la línea base y 30 s por prueba de flujo.

## Decisión de Andrés (14/10/2026)
- Interfaz de los archivos rechazados = A: entra como bloque F con su prueba de regresión; la exclusión de código de producción se levanta solo para ese bloque; 17 tareas (ver D-3).
- Prueba de la parte de interfaz de RF-05.23 y RF-22.1 = C: el backend entrega en español los textos de las pantallas (motivos sin el nombre, confirmación con solo los aceptados, detalle de la bitácora con sus etiquetas); integración del contenido; presentación y aspecto manuales (exención, principio 4) con extremo a extremo en la 005. Andrés acepta que cambie lo que la API entrega del detalle de la bitácora (se añade, no se quita). Descartadas: A (el error de pantalla no se detectaría), B (dependencias de JavaScript, principio 1) y D (contradice la decisión A). Sigue en 17 tareas.

## Decisiones de Andrés (14-15/10/2026, QA del reviewer)
- RF-05.22 = A: solo los rechazos que el backend ya produce; formato y tamaño, fuera de alcance y «Estado actual» de RF-05 al cierre.
- Contrato de la carga = A: la lista de identificadores no cambia; lo nuevo se añade.
- Exención de presentación = A: temporal hasta la 005, con condición de cierre; la constitución no cambia («1»).
- RF-22.1 = A: `[NUEVO]`, con los documentos a actualizar al cierre.
- Bitácora de carga iniciada = A: solo con aceptados y contándolos.
- Casos sin definir = A: todos rechazados = éxito con 0 aceptados (excepción a 4xx); tema no válido = 400 de toda la carga.

## Decisiones de Andrés (15/10/2026, segunda QA del reviewer)
1. Cierre = B: la 004 se cierra al terminar la tarea 14 con el ERS editado; RF-05.23, RF-22.1 y RNF-04.1 llevan «Estado actual» «implementado; pendiente la verificación de extremo a extremo (spec 005)».
2. Mensaje y total de la carga = A: conservan nombre y tipo, cambia su valor (confirmación; solo aceptados). Excepción explícita a «sin quitar ni renombrar»; la lista de identificadores no cambia.
3. Detalle de la bitácora = A: la lista de RF-22.1 sustituye al detalle actual de la carga; el encabezado visible dice «Tema».
4. Rechazos en la bitácora = A: archivo vacío, guardado fallido y error interno también dejan fila de rechazo, solo con su motivo.
5. Causas = A: conjunto cerrado común a RF-05.22, RF-07.2 y RF-22.1 (Definiciones); el error crudo nunca se muestra.
6. 616 px = A: el desplazamiento horizontal cuenta como accesible (criterio de la 004a); sin rediseñar la tabla.

## Decisiones de Andrés (15/10/2026, tercera QA del reviewer)
- P1 = B: se añade la causa «formato o tamaño no permitido» para los rechazos que hoy hace el procesamiento; solo etiquetado, sin validación nueva en la carga.
- P2 = A: «Documento almacenado» es la fila de almacenamiento (número real y fragmentos); la fila «completado» del procesamiento se muestra como «Procesamiento terminado», sin «Documento». No cambia lo que se guarda.
- P3 = B: sin «tiempo de procesamiento agotado»; si ocurre, «error interno». Que hoy no deje fila es hallazgo para la retroactiva de ingesta.
- Sin preguntar (planner): regla de clasificación con precedencia; `xfail` del estado Error en RF-07.2; valores de relleno omitidos; descripción del detalle = nombre del tipo y encabezado con el tema de la lista (N5); RF-05.23 en el notebook; RF-17.4 sin garantizarlo en RF-05.22.

## Dudas abiertas
Ninguna.
