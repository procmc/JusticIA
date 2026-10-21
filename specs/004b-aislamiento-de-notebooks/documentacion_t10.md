# Spec 004b, T10: borrador de cambios a la documentación de planificación
Fecha: 21/10/2026 · Origen: plan §13 · Estado: **BORRADOR**, pendiente de la aprobación de Andrés; después, el visto bueno del tutor (V1.8).

## Nota inicial
- Destinos con `archivo:línea` de `graphify-out/documentacion_texto/` (exportación de los PDF vigentes: ERS V1.7, Casos de Uso V1.4). Si el `.docx` va por delante, no dupliques.
- Los números RF-xx.y son de las specs 004 y 004b; en el ERS cada texto va en el requisito padre, sin sufijo.
- Este borrador **sustituye** lo que `specs/004-red-de-seguridad-backend/documentacion_t14.md` dejaba como «Estado actual» de aislamiento en RF-11, RF-12, RF-17 y RF-20 (nunca se pegó: esperaba al tutor). En V1.8 eso entra como regla cumplida.
- Redacción general, sin rutas ni nombres de código (decisión de la 004). El detalle técnico va en el Anexo A, que **no** se pega en el ERS (duda 2).

---

## ERS V1.8

### Portada (`ERS.txt:6`)
> «Versión: 1.8»

### 2.1 Perspectiva del producto (`ERS.txt:138`, párrafo nuevo después) — RF-17.33
> «Cada módulo separa sus capas: la API recibe la petición y la delega en la capa de servicio de su módulo, la única que accede a la base de datos, a la base vectorial y a los archivos.»

### RA-02 (`ERS.txt:392-409`) — RA-02.15, decisión 18
Añadir al final de su «Estado actual»:
> «La suite completa dura 9 min 22 s, por encima del límite fijado de 8 min 12 s; se acepta, porque el exceso es el arranque de la primera prueba de la corrida y repartirlo entre las pruebas no lo reduce.»

### RF-11 (`ERS.txt:900-904` y `:917`) — RF-11.3, 11.30-11.32, RF-17.3
Añadir a «Reglas y validaciones»:
> «El chat general y el acotado a un tema nunca recuperan documentos de los notebooks de otros usuarios; los notebooks propios sí entran en el chat general. Un tema con forma de clave de notebook en el chat por tema se trata como un tema inexistente. En NotebookServIA, si el notebook no pertenece al usuario, no existe o su identificador no es válido, el sistema rechaza la consulta con la misma respuesta en todos los casos y no consulta al modelo.»

Estado: ver duda 1. Si se elige A (Implementado → Parcial), párrafo nuevo, copiado del borrador T14 de la 004 sin su tercer punto:
> «Estado actual:
> - si no es posible conectar con el motor de lenguaje, el mensaje de error incluye el texto técnico del fallo;
> - si el modelo no devuelve texto, el servidor entrega una respuesta de relleno en lugar de cerrarla vacía, y la interfaz no puede distinguirla para reintentar;
> - el chat acotado a un tema de nombre libre consulta todos los documentos (RF-06).»

El tercer punto del T14 («en NotebookServIA, si el notebook consultado no pertenece al usuario o no existe, el chat no se rechaza: consulta todos los documentos del sistema») ya no se pega: queda como regla cumplida en la última frase de «Reglas y validaciones» de arriba.

### RF-12 (`ERS.txt:928-932`) — RF-17.3
Añadir a «Reglas y validaciones»:
> «Las fuentes citadas nunca incluyen documentos de los notebooks de otros usuarios.»

Estado: Implementado (sin cambio).

### RF-13 (`ERS.txt:951-954`) — RF-17.32 (su «Estado actual» **no** se cierra)
Añadir a «Reglas y validaciones», antes del «Estado actual»:
> «La mención de una clave de notebook en la pregunta no se detecta como tema.»

### RF-17 (`ERS.txt:1044-1050`) — RF-17.3, 17.4, 17.30, 17.31, 17.34
Añadir a «Reglas y validaciones»:
> «Un notebook y sus documentos solo son visibles para su dueño: no aparecen a otros usuarios en el chat, en temas similares, en el resumen, en el listado ni en la descarga o la previsualización, y la exclusión se aplica en la propia búsqueda, sin reducir los resultados propios. La carga de archivos a un notebook ajeno o inexistente, o con su clave en una forma no válida, se rechaza con la misma respuesta que un notebook inexistente, sin guardar nada. Un tema que el sistema iguala con la clave de un notebook al buscarlo o al guardarlo se trata como esa clave, aunque se escriba con otros caracteres (letras de ancho completo, guiones tipográficos o caracteres invisibles); si su número lleva dígitos que no son ASCII, no está disponible para nadie, tampoco para su dueño. La clave propia escrita en otra forma se guarda en su forma canónica.»

Añadir a «Manejo de errores»:
> «Si la creación falla por un error inesperado, el sistema muestra un error genérico, sin detalles técnicos.»

Estado: Implementado (sin cambio).

### RF-19 (`ERS.txt:1093-1103`) — RF-19.2, 19.30
Añadir a «Reglas y validaciones»:
> «Un archivo o unos fragmentos que ya no existen cuentan como eliminados.»

Sustituir «Manejo de errores» (`:1097-1099`) por:
> «Si el usuario cancela la confirmación, el documento se mantiene sin cambios. Si alguna de las eliminaciones falla, el documento permanece en la lista del notebook, el sistema muestra "No se pudo quitar el documento. Intente de nuevo." y un nuevo intento completa lo que faltó.»

Sustituir el «Estado actual» (`:1101-1103`) por:
> «Estado actual: la eliminación se ejecuta sin solicitar confirmación.»

Estado: Parcial (sin cambio).

### RF-20 (`ERS.txt:1123-1130`) — RF-17.3, 17.31
Añadir a «Reglas y validaciones»:
> «Los resultados y el resumen nunca incluyen documentos de los notebooks de otros usuarios; una clave de notebook como tema de referencia se trata como un tema inexistente.»

Su «Estado actual» (`:1136-1137`) no cambia. Estado: Parcial (sin cambio).

### RF-21 (`ERS.txt:1153-1156`, `:1158-1167`, `:1169-1174`) — RF-21.30-21.34
`:1156`, en la lista de operaciones, antes de «y las exportaciones»:
> «…las búsquedas de temas similares, la creación de notebooks, la previsualización y el quitar documentos de un notebook (con éxito o con fallo) y las exportaciones de la bitácora.»

`:1167`, al final de «Contenido del registro»:
> «Las acciones de un notebook se registran con su clave y el número del documento, sin el nombre del notebook ni del documento; la consulta en un notebook propio, con alcance de notebook y su clave; la previsualización fallida, con un motivo fijo ("documento sin procesar" o "archivo no encontrado"). El catálogo incluye los tipos "Crear Notebook", "Quitar Documento de Notebook" y "Gestionar Conversación", que se consultan y filtran como los demás, también en el historial propio.»

`:1174`, al final de «Reglas y validaciones» — RF-21.32, RF-21.33:
> «Lo mismo vale para los intentos de usar un notebook, un documento o una conversación ajenos o inexistentes: se registran como error de acceso solo con su motivo, sin la clave, el identificador ni la pregunta.»

Estado: Implementado (sin cambio).

### RNF-07 (`ERS.txt:1335-1347`) — RNF-07.6, 07.30-07.34
Añadir a la «Descripción», después de `:1336`:
> «Un notebook, un documento de notebook o una conversación de otro usuario reciben la misma respuesta que uno inexistente, sin leer, cargar ni modificar nada, y esa respuesta no cierra la sesión. Cada conversación pertenece al usuario que la creó, aunque su identificador contenga a otro; usar en el chat una conversación ajena equivale a empezar una nueva, y asociarle un tema responde como con una inexistente, sin tocarla.»

En el «Estado actual», **quitar** (`:1342-1343`):
> «Ver o restaurar una conversación ajena se distingue de una inexistente (se rechaza con 403 en lugar de 404).»

Estado: Parcial (sin cambio: siguen los puntos de autenticación y avatares). «Único efecto visible» de RNF-07.33: ver duda 3.

---

## Casos de Uso V1.5

### CU-09 (`Casos_de_Uso.txt:708-711`, paso 5)
> «…recupera los fragmentos más relevantes de la base de datos vectorial dentro del alcance definido, sin documentos de los notebooks de otros usuarios (<<include>> Recuperar fragmentos relevantes).»

### CU-09 FA-01 (`:733-737`), añadir al final
> «Una conversación de otro usuario no puede abrirse, restaurarse ni eliminarse: el sistema responde como si no existiera.»

### CU-09 FA-05 (`:750-753`), añadir al final
> «Si el notebook no pertenece al usuario, no existe o su identificador no es válido, el sistema rechaza la consulta con la misma respuesta en todos los casos, sin consultar al motor de lenguaje ni guardar la conversación, y registra el intento en la bitácora.»

### CU-13 (`:902`, `:924-925`, `:932`, `:937-938`)
- `:902`: «Requerimientos funcionales cubiertos: RF-19, RF-21».
- Paso 5: «…pertenezca al notebook del usuario (<<include>> Verificar pertenencia del documento); si no, FE-02.»
- Paso 9: «El sistema quita el documento de la lista del notebook y registra la acción en la bitácora (<<include>> Registrar evento en bitácora).»
- FE-01: «Error al eliminar: si alguna de las eliminaciones falla, el documento permanece en la lista, el sistema muestra "No se pudo quitar el documento. Intente de nuevo." y registra el fallo; un nuevo intento completa lo que faltó. Un archivo o unos fragmentos que ya no existen cuentan como eliminados.»
- FE-02 (nuevo): «Documento o notebook no disponible: si el documento o el notebook son de otro usuario o no existen, el sistema responde como si no existieran, no elimina nada y registra el intento solo con su motivo.»

## Modelo Relacional
- `Modelo_Relacional.txt:103-104`: «Identificador fijo del tipo de acción (1 a 18).»
- Tabla de catálogos (`:395-424`), tras el 15: `T_Tipo_accion 16 Crear Notebook`, `17 Quitar Documento de Notebook`, `18 Gestionar Conversación` (nota «—»).

---

## Anexo A. Notas técnicas (quedan en la spec; no van al ERS salvo duda 2)

**A.1 RF-17.34, claves equivalentes.** La columna del tema es `VARCHAR(60)` con intercalación `SQL_Latin1_General_CP1_CI_AS` (página 1252, sin distinguir mayúsculas ni ancho).
- Dos conversiones a la columna, consultadas a la base (no imitadas): la del INSERT, que hace el controlador con el parámetro tipado (`como_lo_guarda_la_base`), y la del `CAST` del servidor (`como_lo_convierte_el_servidor`). Difieren: `NB−5` (U+2212) se guarda `NB–5` pero el `CAST` da `NB-5`.
- Además se prueba el texto escrito y ambas lecturas sin caracteres de formato (categoría Unicode Cf), porque algunos sobreviven a la conversión.
- El prefijo se lee en NFKC; el número, tal como se escribió.
- Confirmadas como `NB-<id>` (y tratadas como la clave): `ＮＢ-`, `ＮＢ－`, `NB-５`; `ŃB-`, `ŇB-`, guiones U+2010 y U+2011; `NB−` (por el `CAST`); U+200B, U+2060, U+FEFF, U+034F, U+2063, U+FE0F y U+0301 desaparecen en el INSERT (`NB-<U+200B>5` se guarda EXACTO `NB-5`); U+00AD sobrevive y se cubre por la lectura sin Cf.
- Descartadas (no igualan): `NB–` (U+2013), `ñb-`, `Ṅ` (queda `?`), espacio duro; U+200C, U+200D, U+200E, U+202A, U+180E, U+3164 y U+115F quedan `?`.
- **Decisión 17, sin excepciones**: si lo escrito lleva un dígito no ASCII (categoría Nd: `５`, `٥`), la clave es «no disponible» para todos, también para el dueño (`NB‐５`).
- **Caso `⑤`** (U+2464, categoría No, no Nd), según la revisión de la vuelta 2: la conversión lo vuelve dígito y no activa la decisión 17. B con `NB-⑤<id de A>` recibe el 404 de un ajeno; no hay fuga. El único efecto es que el dueño sí puede cargar a su notebook con esa grafía (se guarda canónica). No lo comprobé contra la base (duda 4).

**A.2 Guarda de la descarga sin NFKC** (`file_management_service.py:246`): compara `tema[:3].casefold() == "nb-"` en ASCII. Por lectura del código, `uploads/ＮＢ-<id>/<nombre>` no pasa por la comprobación del dueño. La de «procesado» iguala por la intercalación, pero la carpeta `ＮＢ-<id>` no existe en disco, así que responde 404. La protección depende del sistema de archivos y no tiene prueba: pendiente B.6.

**A.3 Desviación de `logger.exception`.** El plan (§2-§4) y `.claude/rules/code-style.md` piden `logger.exception`. Los 500 de crear notebook, quitar y asociar el tema usan `logger.error` con el tipo y `traceback.format_tb`, porque `logger.exception` escribe el texto de la excepción, que puede llevar rutas o datos pedidos. Aceptada (plan §14.14-16). Propuesta: anotar la excepción en la regla de estilo.

**A.4 Decisión 11 + 17.** NFKC solo para leer el prefijo; los dígitos, tal como se escribieron. `ＮＢ-<id propio>` se carga como `NB-<id>`; `NB-５` y `NB‐５` son «no disponible» para todos (decisión 17).

**A.5 RNF-07.33, «Único efecto visible».** Las conversaciones guardadas antes de la 004b por un usuario con `_` en su correo pasan a ser suyas al verlas, restaurarlas o eliminarlas (antes se le rechazaban); su lista no cambia.

## B. Pendientes para una spec futura (no se arreglan en la 004b)
1. Previsualizar con 404: la interfaz no avisa al usuario; en desarrollo Next muestra «Unhandled Runtime Error» por un `console.error`.
2. Los 404 de conversaciones no son uniformes: repiten el identificador enviado y el texto cambia entre ver, restaurar y eliminar.
3. El recargador del backend (`--reload`) dio `WatchfilesRustInternalError: Cannot allocate memory` (entorno, sin efecto en la API).
4. Limpiar `NB-10003` y los archivos huérfanos de `uploads/NB-2` (⚠️ borrado de datos: con aprobación).
5. Visto bueno del tutor al ERS V1.8.
6. Guarda de la descarga sin NFKC (A.2) y, si se decide, el caso `⑤` (A.1).

## Dudas para Andrés
1. **RF-11**: el borrador T14 de la 004 tenía otros tres puntos para su «Estado actual» (texto técnico del error de conexión, respuesta de relleno, tema libre en el chat). A) Pegarlos ahora y pasar RF-11 a Parcial (recomendado: ya los aceptaste el 19/10). B) Dejar RF-11 en Implementado y llevarlos a la retroactiva de RAG.
2. **Anexo A en el ERS**: A) Solo la regla general en RF-17; el detalle queda en la spec (recomendado: el ERS no lleva nombres de código). B) Pegar A.1 como nota de RF-17.
3. **«Único efecto visible» (A.5)**: A) Solo en la spec, porque es compatibilidad transitoria (recomendado). B) Una frase en RNF-07.
4. **Caso `⑤`**: A) Aceptarlo como residuo documentado, sin fuga (recomendado). B) Ampliar la decisión 17 a todo carácter con valor numérico no ASCII, en una spec futura.
5. **Casos de Uso V1.5**: A) Aplicar CU-09 y CU-13 junto con el ERS V1.8 (recomendado). B) Esperar al tutor.
