# Plan 011 — Vocabulario «tema» en toda la interfaz
Spec aprobada por Andrés el 12/11/2026, **salvo RT-06.133** (textos que se le dan al modelo), que necesita su aprobación explícita antes de tocarse. Cambio solo de **palabras**: sin migración, sin esquema, sin dependencias, sin páginas nuevas y sin cambio de roles. Grafo atrasado: los símbolos se confirmaron con `Grep` y un barrido de textos literales (ver «Cómo se encuentran»).

## 0. Cómo se encuentran los textos (y por qué una sola búsqueda no basta)
Un barrido de cadenas literales y texto JSX dio el inventario de las secciones 1 y 2. Aun así se le pueden escapar textos partidos en varias líneas o construidos con variables, por eso la **red de seguridad** son las pruebas de la sección 7: un e2e que recorre las pantallas y falla si el texto visible dice «expediente», más una prueba del servidor sobre las descripciones de los registros nuevos. Lo que el barrido omite lo atrapan ellas.
Se conservan sin cambio, por ser técnicos (RT-06): los parámetros y rutas de la API (`/expediente/{…}`, `expediente_numero`), los parámetros de la URL de la interfaz (`?mode=expediente`, `scroll=expedientes`), las claves de los datos (`consultasExpediente`, `expedientesMasConsultados`, `CT_Num_expediente`…), los nombres de funciones y archivos, los textos de `logger` y de registro técnico, y los textos de ayuda de la documentación de la API (`Field(description=…)`, docstrings).

## 1. Archivos de la interfaz que cambian (`frontend/`)
| Archivo (`archivo:línea`) | Texto → texto nuevo | Requisitos |
|---|---|---|
| `components/administracion/bitacora/FiltrosBitacora.jsx:157,159` | «Expediente» → «Tema»; «Número de expediente» → «Nombre del tema» | RF-22.130 |
| `components/administracion/bitacora/TablaBitacora.jsx:69` (y el caso `:132`) | «EXPEDIENTE» → «TEMA» | RF-22.131 |
| `components/administracion/bitacora/InformacionAdicionalRenderer.jsx:206,212,230,378,396,414,431,432` | «Número de Expediente»/«Expediente» → «Tema»; «Expedientes» → «Temas»; «Cantidad de Expedientes» → «Cantidad de temas»; «Top Expedientes Encontrados» → «Temas encontrados (los más relevantes)» | RF-22.132 |
| `components/administracion/bitacora/DetalleEvento.jsx` | Comprobar el encabezado: «Tema» o «Sin tema asociado» (ya lo pide RF-22) | RF-22.132 |
| `components/administracion/bitacora/DashboardEstadisticas.jsx:262,364,552,554,577` | «Consultas por Expediente» → «Consultas por Tema»; tarjeta «Expedientes» → «Temas»; «Expedientes más Consultados» → «Temas más Consultados»; «Top 5 de expedientes…» → «Top 5 de temas con más actividad»; «No hay datos de expedientes disponibles» → «No hay datos de temas disponibles» | RF-23.130 |
| `services/exportService.js:126,158,240,352,400` | El PDF: «Expedientes» y «Expediente» → «Tema(s)»; «- Expedientes involucrados» → «- Temas involucrados» | RF-22.133 |
| `services/bitacoraService.js:203,215`; `services/ingestaService.js:101`; `services/similarityService.js:168,173,362` | Mensajes que pueden llegar a pantalla: «número de expediente» → «tema» | RT-06.130, RT-06.131 |
| `utils/validation/expedienteValidator.js:226,232,236,240` | «El tema es requerido», «El tema debe tener al menos <N> caracteres», «El tema no debe exceder <M> caracteres», **sin** el formato `YY-NNNNNN-NNNN-XX` | RT-06.131 |
| `components/consulta-datos/busqueda-similares/results-grid/details-drawer/ResumenTab.jsx:28` | «No se encontró el número de expediente» → «No se encontró el tema» | RT-06.130 |
| `common/roles.js:37` | La descripción del rol: «base de datos de expedientes» → «base de datos de temas» | RT-06.130 |
| `pages/index.js:125,126` | «Reportes de Expedientes» → «Reportes de Temas»; «Top expedientes consultados…» → «Top temas consultados y métricas documentales» (las URL `?mode=expediente` y `scroll=expedientes` no cambian) | RT-06.130 |
| `data/mockBitacora.js` | Datos de ejemplo: si ningún archivo los importa, quedan como están (no se ven); si alguno los muestra, se cambian | RT-06.130 |
| Resto de pantallas (chat, Temas Similares, Ingesta, notebooks, menú) | Los textos que el barrido no vea y la prueba de la sección 7 detecte | RT-06.130 |

## 2. Archivos del servidor que cambian (`backend/app/`)
| Archivo (`archivo:línea`) | Texto | Requisitos |
|---|---|---|
| `routes/archivos.py:123,180`; `schemas/ingesta_schemas.py:14` | «Formato de expediente inválido» → «Formato de tema inválido» | RT-06.132 |
| `routes/rag.py:313,321` | «Contexto de expediente … actualizado correctamente» y «Error actualizando el contexto del expediente» → «tema» | RT-06.132 |
| `services/RAG/rag_chain_service.py:546,549,554,557` | Los avisos de cambio de tema del chat («**Expediente cambiado:**…») → «**Tema cambiado:**…» (la interfaz ya usa «Tema cambiado»; comprobar si todavía se usan) | RT-06.132 |
| `services/bitacora/bitacora_stats_service.py:697` | «No se encontraron registros para este expediente» → «…para este tema» | RT-06.132 |
| `services/bitacora/archivos_audit_service.py:271,376,381`; `services/bitacora/rag_audit_service.py:145`; `services/bitacora/similarity_audit_service.py:68,279,282` y los demás servicios de auditoría | La **descripción de los registros nuevos**: «Descarga de archivo: … (tema: X)», «Listado de archivos del tema: X (N archivos)», «Error listando archivos del tema: X…», «Resumen IA generado para tema: X», etc. Los registros ya guardados no cambian (RN-01). | RF-21.130 |
| `services/busqueda_similares/response_parser.py:373,379` | El resumen de respaldo que ve el usuario: «…del expediente judicial» → «…del tema»; «Materia Jurídica del Expediente» → «Materia Jurídica del Tema» | RT-06.133 ⚠️ |
| **⚠️ Aprobación de Andrés** `services/RAG/chunk_context_builder.py:228,276` | El encabezado del contexto del chat que ve el modelo: «Expediente: X» → «Tema: X» y «Sin expediente» → «Sin tema» | RT-06.133 |
| **⚠️ Aprobación de Andrés** `services/busqueda_similares/similarity_prompt_builder.py:36,131` | Las instrucciones y el formato del resumen de Temas Similares: «el expediente» → «el tema» | RT-06.133 |

## 3. Lógica y flujo
Sin capas nuevas: son cambios de literales. La Bitácora sigue guardando y leyendo los mismos datos; solo cambia la palabra con que la pantalla los nombra y la descripción de los registros que se creen.
```
mostrar un registro de la Bitácora → igual que hoy; solo cambian los rótulos y el título de la columna
crear un registro nuevo           → su descripción (CT_Texto) sale con «tema»; el dato guardado (tema, claves) no cambia
registros viejos                  → se muestran tal como se guardaron («expediente» dentro de su descripción)
```

## 4. Datos, interfaz y bitácora
- **Datos:** sin migración. Nada de lo guardado cambia; los registros viejos conviven con los nuevos (RN-01).
- **Interfaz y roles:** Administrador (Bitácora y Estadísticas) y Usuario Gubernamental (el resto). `ROUTE_PERMISSIONS` sin cambios. Los textos nuevos no desbordan a 1366 ni a 616 px (RNF-04.130).
- **Bitácora (RF-21):** no hay acciones nuevas ni tipo nuevo; solo cambia la descripción de los registros nuevos (RF-21.130).

## 5. Decisiones técnicas
- **D1. Cambiar los literales en su sitio.** Alternativa descartada: un catálogo central de textos (refactor grande y sin otra necesidad).
- **D2. No reemplazar la palabra al mostrar registros viejos.** Es lo que decidió Andrés y evita alterar un texto que no debía (por ejemplo, un nombre de tema que el usuario escribió con «expediente»). Alternativa descartada: reemplazo automático al mostrar.
- **D3. Conservar las claves técnicas.** Renombrarlas exige al tutor (RT-06). Alternativa descartada: renombrar claves de los datos y rutas.
- **D4. La red de seguridad es un recorrido e2e del texto visible**, no solo la búsqueda de cadenas. Alternativa descartada: confiar en el barrido (omite textos partidos o construidos).
- **D5. Las dos entradas ⚠️ de RT-06.133 van en una tarea aparte y solo con la aprobación de Andrés**, porque cambian lo que se le entrega al modelo. Alternativa descartada: hacerlo junto con lo demás sin avisar.
- **D6. Las pruebas existentes que comparan un texto viejo se actualizan, no se borran ni se desactivan** (testing.md).

## 6. Pruebas (primero en rojo; entornos aislados; datos `PRUEBA`)
- **e2e, Administrador** (`bitacora` nuevo o en el archivo de la bitácora, 1366 y 616 px): el filtro dice «Tema» y «Nombre del tema»; la columna dice «TEMA»; el detalle de un registro de carga, de una consulta de un tema y de una acción de notebook usa «Tema»; la pestaña Estadísticas dice «Temas», «Temas más Consultados» y «Consultas por Tema»; el filtro por `NB-12` sigue funcionando; la exportación a PDF no falla; **el texto visible de la página no contiene «expediente»** salvo dentro del contenido de un registro ya guardado.
- **e2e, Usuario Gubernamental** (ambos anchos): recorrido de Ingesta de Datos (campo, lista de archivos, confirmación, errores de validación del tema), chat general y de un tema, Temas Similares (ambos modos y el panel de detalle), notebooks, inicio y menú: ningún texto visible dice «expediente».
- **Integración** (API real, SQL Server, Tika, Qdrant): los mensajes de error que dicen «tema» (`archivos`, `rag`, ingesta); los registros nuevos de listado y descarga de archivos, de consulta y de resumen dicen «tema» y **un registro viejo insertado en la prueba con «expediente» se devuelve sin cambios**; la exportación y los filtros siguen funcionando con ambos.
- **Unitarias:** cada constructor de la descripción de un registro (servicios de auditoría) con datos inventados no contiene «expediente»; las funciones de validación del tema devuelven los mensajes nuevos; el resumen de respaldo.
- **RT-06.133 (solo con aprobación):** con el modelo simulado, el contexto del chat trae «Tema: X» y «Sin tema»; el resumen de Temas Similares conserva sus campos; no se prueba el texto de las respuestas del modelo.
- Se **actualizan** (no se borran): las pruebas existentes que comparan textos con «expediente» (se buscan con la misma búsqueda y se ajustan a «tema»).
- **No automatizable de forma fiable:** el contenido del PDF generado (se descarga y se lee a mano) y el texto exacto de lo que responde el modelo (no determinista, testing.md).

## 7. Verificación manual (Andrés)
A 1366 y 616 px, con el Administrador: la Bitácora (filtros, tabla, detalle de un registro de carga y de una consulta, Estadísticas, exportar PDF y abrirlo); con el Usuario Gubernamental: Ingesta (probar un tema vacío o muy corto), chat con y sin tema, Temas Similares, notebooks, inicio y menú. Ver que ningún texto diga «expediente»; los registros viejos sí. Consola limpia.

## 8. Documentación (última tarea)
Sin cambios en ERS, HU ni CU (ya dicen «tema»); se cierra el «Estado actual» de RF-22 en lo del vocabulario. Después `graphify update .` y `MEMORY.md`.

## 9. Riesgos y orden sugerido
- **Riesgo:** un texto que el barrido no ve (partido en líneas o armado con variables). Mitigación: el recorrido e2e que lee el texto visible y la prueba del servidor.
- **Otro:** que una prueba existente compare el texto viejo; se actualiza.
- **Orden** (lo detallará `tasks.md`): Bitácora y Estadísticas → PDF, validaciones y mensajes del servicio → textos de los registros nuevos y mensajes de la API → el recorrido de las demás pantallas y lo que encuentre → ⚠️ textos del modelo (solo con tu aprobación) → verificación y documentación.
