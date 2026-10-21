# Plan — Spec 004b: Aislamiento de los notebooks entre usuarios
Estado: aprobado (19/10/2026); cambio del 19/10/2026 aprobado por Andrés

> Publicable en términos generales: cita archivos y líneas (19/10/2026, rama `fase4`; revisarlas al empezar cada tarea) sin describir cómo aprovechar los fallos. Grafo consultado por el mapa y `Grep`; líneas confirmadas con `Read`.

Historial:
- 19/10/2026 — creado junto con las tareas, a partir de la spec aprobada.
- 19/10/2026 — cambio tras la T5 (§14.6-9): RNF-07.34 y RF-17.34 en la T6, `get_db` en la T6, ajuste aprobado de la T5, duración de la suite.
- 19/10/2026 — respuestas de Andrés (§14.10-12): D9 A, NFKC confirmado y el 500 de asociar el tema (`rag.py:273`) en la T6. Pendiente de la aprobación final.
- 20/10/2026 — cambio tras la T7 (§14.13, Andrés A): previsualizar fallido en la bitácora (§7) y `test_previsualizar_fallido_se_registra` (§9), en la corrección de la T8.
- 21/10/2026 — T10 (sin cambio de comportamiento): §9 corrige el mecanismo de RF-17.34 (INSERT, con el `CAST` como segunda lectura) y suma la fila de la vuelta 2; la decisión 11 cita la 17; §14.14-16 desglosados. Borrador de documentación en `documentacion_t10.md`.

## 1. Diagnóstico (rutas en `backend/app/`)
- **Búsqueda sin dueño**: `vectorstore/qdrant_backend.py:208-244` (`search_by_text`) filtra solo por tema exacto (`:222`, `MatchValue`) y después por «Procesado» (`_filter_by_processed_status`, `:88-113`, que devuelve todo si no obtiene ids). `search_similar_expedients` (`:281-328`) consulta sin filtro. Por eso el chat general, el por tema y temas similares traen notebooks ajenos.
- **Chat por tema con `NB-`**: `services/RAG/rag_chain_service.py:232-241` no pasa la regex heredada y cae al general (`:148`), que no sabe del usuario.
- **Chat del notebook**: `rag_chain_service.py:115` actualiza la conversación **antes** de comprobar nada; `:326-344` cae al general si el notebook no es del usuario o el id no es entero (`int()` acepta `+5`, ` 5 `, `05` y dígitos Unicode).
- **Conversaciones**: `routes/rag.py:302-315` y `:399-417` dan 403 a la ajena (restaurar la carga antes de mirar el dueño); `services/RAG/session_store.py:340-343` deduce el dueño del identificador (`split('_')[1]`: falla con `_` en el correo y deja `notebook` como dueño de los chats de notebook). Un identificador ajeno en el chat carga su historial (`:330-335`).
- **Asociar el tema** (`POST /rag/update-expediente-context`): `routes/rag.py:209-274` y `rag_chain_service.py:473-524` (`update_expediente_context`) añaden dos mensajes y tocan los metadatos de cualquier `session_id`, sin mirar el dueño; registran sesión y tema (`rag.py:243-244`, `rag_chain_service.py:480-481,519`). La interfaz lo llama con la conversación nueva al elegir el primer tema (`Chat.jsx:155`).
  - Con una inexistente, hoy: `update_metadata` (`session_store.py:384-406`) no hace nada (sin metadatos); `get_session_history` (`:322-359`) la crea e indexa; se guardan los dos mensajes; 200 con `success`, `message`, `session_id`, `expediente_number` y `action`, todo tomado de la petición (`rag.py:253-260`).
  - El 500 inesperado devuelve `str(e)` (`rag.py:269-274`).
- **Carga**: `routes/ingesta.py:188-209` valida el tema (004a) pero no la pertenencia de un `NB-`.
- **Grafía equivalente** (hipótesis del reviewer, sin verificar): `forma_de_clave` (`notebook_service.py:54-57`) y `_CLAVE_DE_NOTEBOOK` (`:43`) solo reconocen `nb-` ASCII. Si la intercalación de SQL Server no distingue ancho, `ＮＢ-<id>` pasa como tema libre y `obtener_por_numero` (`expediente_repository.py:82`) lo resolvería a la fila del notebook.
- **NotebookServIA** (`routes/notebooks.py`): usa repositorios, Qdrant y archivos directo (`:35-43`, `:106`, `:121-125`, `:150-184`); crear da 400 con `str(e)` (`:78-79`); quitar ignora el fallo del archivo (`:178-181`) y nada se registra en la bitácora.
- **Bitácora**: catálogo de 15 tipos (`constants/tipos_accion.py:64-99`; migración `alembic/versions/NUEVA_CONSOLIDADA_base_datos_completa.py:178-197`); filtros `le=15` en `routes/bitacora.py:97` y `:223`; interfaz `frontend/common/tiposAccion.js:21` y `frontend/services/bitacoraService.js:296-299` («Acción N»). `rag_audit_service.registrar_consulta_rag` (`:100-173`) solo distingue general/expediente.
- **Registro del servidor**: `rag.py:112-116` y `rag_chain_service.py:120,129,324,337` escriben sesión, tema y notebook pedidos; `db/database.py:68-73` registra como `ERROR Error en sesión de base de datos: 404: ...` el texto de toda `HTTPException` (el 404 de conversación repite el identificador).
- **Interfaz**: `frontend/services/httpService.js:284` solo cierra la sesión con 401 (RNF-07.30 se cumple); `pages/notebooks/index.js:141-149` no avisa si quitar falla y `services/notebookService.js:78` hace `console.error` (abre el aviso rojo de Next).

## 2. Archivos
| Archivo | Cambio | Requisitos |
|---|---|---|
| `services/notebook_service.py` | `clasificar_clave(db, tema, usuario_id)` → `no_es_notebook` · `propio(notebook)` · `no_disponible`; `ids_documentos_visibles(db, usuario_id)`; `RecursoNoDisponible(Exception)` con `motivo`; listar, obtener documento, previsualizar, quitar (tres capas) y crear con 500 genérico; id > 2^63-1 → `None`. T6: `forma_de_clave` en NFKC; `clasificar_clave` reclasifica un tema libre con el tema guardado que le da la base (RF-17.34). | RF-17.3, 17.4, 17.30, 17.33, 17.34, 11.32, 19.2, RNF-07.32 |
| `repositories/documento_repository.py` | `listar_procesados_con_temas(db) -> list[(id, tema)]` (unión por `T_Expediente_Documento`). | RF-17.3 |
| `vectorstore/base.py` (`:55`, `:74`), `qdrant_backend.py` | Parámetro `documentos_visibles: Optional[set[int]]` en `search_by_text` y `search_similar_expedients`: `must` con `MatchAny` sobre `metadata.id_documento`; conjunto vacío → `[]` sin consultar. | RF-17.3 |
| `services/RAG/search_strategies.py:83-135`, `retriever.py:113-230` | Pasan `documentos_visibles`; el retriever lo recibe en su constructor. | RF-17.3 |
| `services/RAG/rag_chain_service.py` | Despacho del §4: comprobaciones antes de `update_metadata`; `NB-` en el chat por tema → general con visibles; notebook no válido → `RecursoNoDisponible`; conversación ajena → efímera; `update_expediente_context` comprueba el dueño primero (§4). Logs sin identificadores pedidos. | RF-11.3, 11.30-11.32, 17.31, 17.32, RNF-07.31, 07.33, 07.34 |
| `services/RAG/session_store.py`, `conversation_history_redis.py` | `dueno` en los metadatos al crear (usuario autenticado); `es_propia(id, usuario) -> True/False/None` leyendo solo los metadatos; compatibilidad de lectura; sesión efímera sin guardar ni indexar; chats de notebook sin índice de lista. | RNF-07.31, 07.33, 07.6 |
| `routes/rag.py` | Dueño antes de ver/restaurar/eliminar (404 uniforme, el de hoy para inexistente); traduce `RecursoNoDisponible` a 404 «Notebook no encontrado»; `update-expediente-context` con usuario: ajena → el mismo 200 y cuerpo de `:254-260` (D9 A), sin sesión ni tema en el registro; su 500 inesperado (`:269-274`) → «Error interno del servidor» + `logger.exception`; bitácora (§7). | RNF-07.6, 07.31, 07.34, RF-21.31-21.33 |
| `routes/similarity.py`, `services/busqueda_similares/similarity_service.py:243-371` | Usuario a la búsqueda (visibles); `NB-` como referencia o en el resumen → mismo camino que un tema inexistente; bitácora sin la clave. | RF-17.3, 17.31, RF-21.33 |
| `routes/ingesta.py:188-209` | Antes de `validar_tema`: `clasificar_clave`; `no_disponible` → 404 «Notebook no encontrado» + intento fallido; `propio` → clave canónica. T6: el mismo trato para un tema equivalente (RF-17.34). | RF-17.4, 17.34, RF-21.32 |
| `routes/notebooks.py` | Solo llama a `NotebookService`; traduce errores; bitácora (§7). | RF-17.33, 17.30, 19.2, RF-21.30, 21.32 |
| ⚠️ `services/bitacora/notebooks_audit_service.py` (nuevo) | `registrar_creacion`, `registrar_previsualizacion`, `registrar_quitar(exito, tipo_error)`, `registrar_intento_fallido(db, usuario_id, tipo_accion_id, motivo)`; textos con `_sin_control` (004a). | RF-21.30, 21.32 |
| `services/bitacora/rag_audit_service.py:100-173` | `tipo_consulta="notebook"` con la clave como tema; general sin clave. | RF-21.31, 21.33 |
| ⚠️ `alembic/versions/<rev>_tipos_accion_notebooks.py` (nuevo) | Inserta 16 «Crear Notebook», 17 «Quitar Documento de Notebook», 18 «Gestionar Conversación»; nada más. | RF-21.34 |
| `constants/tipos_accion.py`, `routes/bitacora.py:97,223` | Constantes 16-18 y descripciones; `le=18`. T7: los comentarios «1-15» de `bitacora.py:25` y `:113` y el JSDoc de `frontend/services/bitacoraService.js:24` pasan a 1-18. | RF-21.34 |
| `db/database.py:68-73` (T6) | No registra las `HTTPException` 4xx (respuestas previstas); 5xx y el resto siguen enmascarados, como hoy. | RF-21.32 |
| `frontend/common/tiposAccion.js`, `services/bitacoraService.js:296` | Los 3 nombres y su opción en el filtro. | RF-21.34 |
| `frontend/pages/notebooks/index.js:141-149`, `services/notebookService.js:73-80` | Aviso (`addToast`, peligro) con `result.message`; sin `console.error`. | RF-19.30 |

⚠️ Pruebas nuevas: `backend/tests/unitarias/test_aislamiento_notebooks.py`, `backend/tests/integracion/test_aislamiento_notebooks.py`, `backend/tests/integracion/test_conversaciones_propias.py`. `Ajeno`, `ajeno` y `_consultar_chat` pasan de `test_red_notebooks.py:202-308` a `tests/integracion/conftest.py` para compartirlos (sin cambiar su comportamiento). Sin cambios en `docker-compose.yml`, dependencias, prompts, modelos ni datos guardados.

## 3. Lógica por capa
- **Router**: recibe, llama al servicio, registra en la bitácora (§7) y traduce: `RecursoNoDisponible` → 404 uniforme; `ValueError` de nombre vacío → 400 con su mensaje; otro → 500 genérico + `logger.exception` sin datos pedidos.
- **Servicio**: toda regla de pertenencia (`clasificar_clave`, `ids_documentos_visibles`, `es_propia`) y el orden de las comprobaciones. Ninguna ruta toca repositorios, Qdrant ni archivos (RF-17.33).
- **Repositorio**: `NotebookRepository.obtener_por_id` (`:59`), `DocumentoRepository.obtener_por_id` (`:96`), `listar_por_expediente` (`:239`), `eliminar` (`:331`) y el método nuevo.
- **Externos**: SQL Server, Qdrant (filtro por ids), Redis (metadatos de conversación), Ollama (simulado en pruebas). Sin Worker ni HTR.

## 4. Flujo (pseudocódigo)
```
FORMA = normalize("NFKC", tema.strip()).casefold().startswith("nb-")    # T6: NFKC (antes, solo ASCII)
clasificar_clave(db, tema, usuario):
    si no FORMA:                                           # T6, RF-17.34: lo que la base iguale con una clave
        fila = obtener_por_numero(db, tema.strip()); si fila y FORMA(fila.numero): tema = fila.numero
        si no: no_es_notebook
    m = fullmatch(r"[1-9][0-9]*", resto tal como se escribió, ASCII); no m o int > 2**63-1 → no_disponible
    nb = obtener_notebook_de_usuario(db, int, usuario); nb → propio(nb); si no → no_disponible

actualizar_tema_de_conversacion(sesion, tema, accion, usuario):   # T6, RNF-07.34
    propia = es_propia(sesion, usuario)                    # antes de leer, tocar o escribir en el registro
    si False: intento «conversación no disponible» (tipo 18); devolver «hecho» sin crear, leer ni guardar nada (D9 A)
    si None: crear con dueno = usuario (RNF-07.33)
    como hoy: update_metadata y los dos mensajes del aviso
    ruta: el cuerpo 200 se arma solo con la petición en ambos casos → idéntico por construcción
    error inesperado → 500 «Error interno del servidor» + logger.exception sin sesión ni tema

ids_documentos_visibles(db, usuario):                      # regla en un solo lugar
    propios = {nb.clave_interna.casefold() de mis notebooks}
    por documento Procesado: visible si NINGUNO de sus temas tiene FORMA salvo los de forma canónica en propios
    (un documento unido a un tema ajeno o sin notebook queda fuera, en cualquier grafía)

search_by_text(..., documentos_visibles):                  # exclusión dentro de la búsqueda
    visibles vacío → []                                    # falla cerrado, sin el «devuelve todo» de :95
    filtro.must += FieldCondition("metadata.id_documento", MatchAny(any=visibles))
    + el filtro de tema exacto si aplica; mismo k → misma cantidad de resultados propios

consulta_con_historial_streaming(pregunta, sesion, tema, notebook_id, usuario):
    si notebook_id no None:                                # RF-11.32, antes de leer o tocar nada
        no fullmatch(r"[1-9][0-9]*", ASCII) o > 2**63-1 o no es del usuario → RecursoNoDisponible("notebook no disponible")
    propia = es_propia(sesion, usuario)                    # solo metadatos
    si propia es False: sesion = crear_efimera(); marcar intento «conversación no disponible»   # RNF-07.31
    si propia es None: crear con dueno = usuario (notebook: sin índice de lista)               # RNF-07.33
    update_metadata(sesion)                                # recién aquí
    notebook → retriever con la clave propia (RF-11.3)
    tema con FORMA → general(visibles); intento «notebook no disponible» si clasificar ≠ propio   # RF-11.31
    tema heredado/libre → como hoy (RF-11.30); general → visibles (RF-17.3); detección sin cambios (RF-17.32)

es_propia(id, usuario): meta = metadatos(id); None si no hay
    meta.dueno == usuario  o  meta.user_id == usuario  o  tramo(id) == usuario    # compatibilidad, sin reescribir
    tramo: general entre "session_" y el último "_"; notebook entre "session_notebook_<n>_" y el último "_"

quitar(db, notebook, documento):                           # RF-19.2, cada paso idempotente
    borrar fragmentos (cero puntos = éxito) → borrar archivo (FileNotFoundError = éxito) → borrar registro
    cualquier otro error → ErrorAlQuitar; el registro queda, el reintento completa
```
- Temas similares: por descripción usa el retriever con visibles; por tema, `clasificar_clave ≠ no_es_notebook` → resultado de tema inexistente (lo caracteriza la primera prueba); si no, `search_similar_expedients(..., documentos_visibles)`. Resumen IA con `FORMA` → misma respuesta que un tema inexistente.
- Sesión efímera: identificador nuevo aleatorio, historial en memoria sin `save_callback`, sin metadatos ni índice; se descarta al terminar el streaming.

## 5. Datos
- ⚠️ **Migración** (Q1): solo `INSERT` de los ids 16-18 con `IDENTITY_INSERT`; `downgrade` borra esos 3 solo si ninguna fila de `T_Bitacora` los usa (si no, falla con un mensaje). Ninguna tabla cambia de esquema.
- **Redis**: las conversaciones nuevas guardan `dueno` en sus metadatos; las guardadas no se reescriben (compatibilidad del §4). Los chats de notebook nuevos no entran en `user_sessions:*` (hoy caen en `user_sessions:notebook`, compartido).
- **Qdrant**: sin cambios ni reindexado; la exclusión usa `metadata.id_documento` (ya presente en cada fragmento).
- **Inventario de solo lectura** (T1; solo cantidades, aprobadas por Andrés, nada al repositorio):
  1. Temas con FORMA: canónicos con notebook, canónicos sin notebook, no canónicos (`nb-5`, `NB-05`, espacios).
  2. Choques: dos temas que coinciden tras `strip().casefold()`.
  3. Qdrant (scroll solo de `metadata.numero_expediente` e `id_documento`): valores con FORMA por grafía; puntos cuyo `id_documento` no está en la base; puntos cuyo tema difiere del de su documento en la base.
  4. Conversaciones en Redis: total y cuántas son de chats de notebook (sin leer mensajes).
  - Si 3 da puntos con tema distinto del de su documento, Andrés decide antes de T2 (la regla usa el tema de la base).

## 6. Interfaz y roles
- Solo cambian el aviso de RF-19.30 y los 3 tipos de RF-21.34. Mensajes: «Notebook no encontrado» y «Documento no encontrado en este notebook» (los de hoy), «No se pudo quitar el documento. Intente de nuevo.», «Error interno del servidor».
- Todas las rutas siguen con `require_usuario_judicial`; el Administrador mantiene su 403 y ve la bitácora. Ningún rechazo es 401 ni 403 (RNF-07.30; `httpService.js:284`).
- Sin cambios en `ROUTE_PERMISSIONS` ni en la navegación.

## 7. Bitácora (RF-21)
| Hecho | Tipo | Contenido |
|---|---|---|
| Crear notebook | 16 | `NB-<id>` como tema, resultado |
| Previsualizar (éxito / fallo) | 10 | `NB-<id>`, número de documento, resultado; fallo con motivo «documento sin procesar» (`tipo_error="validacion"`) o «archivo no encontrado» (`"interno"`); sin nombre, ruta ni excepción (§14.13) |
| Quitar (éxito / fallo) | 17 | `NB-<id>`, número de documento, resultado; fallo con `tipo_error="interno"` |
| Chat de notebook propio | 12 | `tipo_consulta="notebook"`, `NB-<id>` como tema |
| Chat por tema con FORMA | 12 | consulta general **sin** la clave (+ intento si ≠ propio) |
| Intento fallido | el de la acción (12, 2, 11, 10, 17, 18, 1, 13) | «Intento fallido: notebook / documento / conversación no disponible», `tipo_error="acceso"`; sin clave, nombre, pregunta ni identificador |
- Tema: la relación con `T_Expediente` si la fila existe; siempre `info_adicional.tema`. Sin nombres de notebook ni de documento.
- Si el registro falla, la respuesta no cambia (cada servicio devuelve `None`, como en la 004a).

## 8. Decisiones (con la alternativa descartada)
1. **Lista de documentos visibles por id en el filtro de Qdrant**: cubre cualquier grafía porque decide con el tema de la base, no con el texto del fragmento. Descartadas: `must_not` con las grafías conocidas (no cubre las desconocidas), índice de texto (cambia la colección) y filtrar después (reduce resultados, contra RF-17.3).
2. **La regla en `NotebookService`** y el repositorio solo lista pares (id, tema): un `LIKE` en SQL dependería de la intercalación y duplicaría la regla.
3. **Falla cerrado** sin visibles o sin base: hoy `_filter_by_processed_status` devuelve todo si no obtiene ids.
4. **Clave propia en otra grafía se carga como canónica** (RF-17.4): guardarla tal cual crea grafías nuevas, el problema que esta spec contiene.
5. **Sesión efímera** para la conversación ajena (RNF-07.31): un id nuevo guardado aparecería en la lista de B.
6. **Chats de notebook fuera del índice de lista**: indexarlos bajo el usuario los mostraría en su lista (contra RNF-07.33).
7. **`get_db` sin registrar los 4xx**: abrir otra sesión para auditar duplicaría el manejo de sesión; los 4xx no son errores de sesión.
8. **Un servicio de auditoría de notebooks también para los intentos de chat, carga y similares**: uno por módulo repetiría la misma fila.
9. **`downgrade` solo sin referencias** (RN-01): un borrado incondicional dejaría filas de bitácora sin tipo.
10. **Equivalencia por la búsqueda de la base** (RF-17.34): cubre la intercalación real, sea cual sea. Descartada: imitar en Python la intercalación o una lista de caracteres equivalentes (no cubre los desconocidos).
11. **NFKC solo para la forma; los dígitos, tal como se escribieron**: `NB-５` sigue no disponible, como los demás dígitos Unicode (Definiciones). Descartado: NFKC también en los dígitos (abriría grafías nuevas de una clave propia). Con la decisión 17 (§14.17) no tiene excepciones: un dígito no ASCII en lo escrito (`NB‐５`) es no disponible aunque la base lo guarde como `NB-5`.
12. **Ajena = el 200 de una inexistente, armado con la petición** (RNF-07.34, D9 A): uniforme por construcción y no rompe el primer tema. Descartadas: 404 para ambas (cambia `Chat.jsx:155`) y 404 solo para la ajena (la distingue).
13. **El 500 de `:264` (`success` falso) se deja**: ya es un texto fijo sin detalles; solo `:273` expone `str(e)`. Descartado: unificarlo (cambio visible sin necesidad).

## 9. Trazabilidad requisito → tarea → prueba (se escriben primero)
`xfail` de `tests/integracion/test_red_notebooks.py` que cierra cada tarea; las demás pruebas, nuevas (u = unitaria, i = integración).

| Requisito | Tarea | Prueba | Rojo esperado |
|---|---|---|---|
| RF-17.3 | T2 | `xfail` `test_documentos_de_notebook_ajeno_no_se_entregan[chat_general]`, `[chat_por_tema]`; i `test_ajenos_mejor_puntuados_no_reducen_resultados`, `test_grafia_distinta_y_sin_notebook_no_llegan` | contexto con lo ajeno |
| RF-17.3 | T2 | u `test_ids_visibles_por_grafia` (`NB-5`, `nb-5`, ` Nb-5 `, `NB-05`, sin notebook, propio), `test_sin_visibles_falla_cerrado` | `ImportError` |
| RF-11.31, 17.31, 21.33 (chat) | T2 | i `test_chat_por_tema_con_clave_es_general` (ajena, inexistente, propia; contexto igual al general; filas) | lo ajeno llega; fila con la clave |
| RF-17.32, RF-11.30 | T2 | i `test_clave_en_la_pregunta_no_se_detecta`; las del chat por tema existentes y RF-06.2 en `xfail` | probable protección (anotar) |
| RF-17.3, 17.31, 21.33 | T3 | `xfail` `[temas_similares]`; i `test_similares_y_resumen_con_clave_como_inexistente` (descripción, tema y resumen) | resultados con lo ajeno |
| RF-11.3 | T4 | `xfail` `test_notebook_ajeno_o_inexistente_sin_contenido[ajeno]`, `[inexistente]` | cae al general |
| RF-11.32, RNF-07.6 | T4 | `xfail` `test_recurso_ajeno_da_404_identico[chat]`; i `test_notebook_no_numerico_da_404` (`+5`, ` 5 `, `05`, `٥`, vacío; modelo sin llamar; fecha de la conversación igual) | 200 por el general |
| RF-21.31, 21.32 | T4 | i `test_chat_de_notebook_se_registra_con_su_clave`, `test_intento_fallido_solo_con_motivo` (+ `caplog` del paquete `app`, bitácora que falla) | fila «general»; logs con el id |
| RF-17.4 | T4 | `xfail` `test_carga_a_notebook_ajeno_da_404`; i `test_carga_con_clave_no_canonica_da_404` (`NB-0<id>`), `test_carga_propia_en_otra_grafia_usa_la_canonica` | 200, archivo guardado |
| RF-21.34 | T5 | i `test_catalogo_con_tres_tipos_nuevos` (15 intactos + 3), `test_filtro_por_tipo_nuevo` (bitácora y servicio del historial propio) | 15 filas; 422 por `le=15` |
| RNF-07.6 | T6 | `xfail` `[ver_conversacion]`, `[restaurar_conversacion]`; `[eliminar_conversacion]` con su fila | 403 |
| RNF-07.31, 07.33 | T6 | i `test_conversacion_ajena_como_nueva`, `test_escritura_cruzada`, `test_historial_igual_que_antes` (también correo con `_`), `test_restaurar_no_carga_la_ajena` | historial de A al modelo; aparece en la lista de A |
| RF-17.34 | T6 (primera) | i `test_carga_con_clave_de_ancho_completo` (`ＮＢ-<id A>`, `ＮＢ－<id A>` → 404 + intento tipo 2; la propia → `NB-<id B>`), `test_chat_por_tema_con_clave_de_ancho_completo`; u `test_forma_de_clave_en_nfkc` | confirma: documento en el notebook de A; descarta: protección (anotar) |
| RF-17.34 (grafías que la base guarda como clave; vuelta 1, B1) | T6 (corrección) | i `test_carga_con_grafia_que_la_base_guarda_como_clave[ajeno_ligero\|ajeno]` (`ŃB-`, guion U+2010, signo menos U+2212 → 404 uniforme + intento, sin documento ni tarea, con y sin fila de tema), `test_chat_por_tema_con_grafia_...`, `test_similares_y_resumen_con_grafia_...`; u `test_clasificar_clave_con_lo_que_la_base_guardaria_como_clave`. Mecanismo (desde la vuelta 2): lo que guarda el INSERT, con el parámetro tipado con la columna (`ExpedienteRepository.como_lo_guarda_la_base`); el `CAST` del servidor es la segunda lectura (`como_lo_convierte_el_servidor`) | carga de B aceptada y documento unido a `NB-<id>` de A |
| RF-17.34 (caracteres invisibles, Cf y decisión 17; vuelta 2, B2) | T6 (corrección) | i `test_carga_con_caracteres_invisibles_en_la_clave[ajeno_ligero\|ajeno]` (16 grafías invisibles más `NB‐５`, `ŃB-５` y `NB−５`, ajenas y propias → 404 uniforme + un intento; sin fila de tema, documento, tarea ni archivo; la primera carga de A queda bajo `NB-<id>`), `test_como_lo_guarda_la_base_coincide_con_el_insert_del_orm` (6 grafías); u `test_clasificar_clave_con_caracteres_invisibles`, `test_clasificar_clave_con_lo_que_la_base_guardaria_como_clave` (decisión 17) | `N­B-<id>` aceptada (200); el método daba el `CAST`; `NB‐５` propio |
| RNF-07.34, 07.33, RF-21.32 | T6 | i `test_tema_de_conversacion_ajena_no_la_toca` (general y de notebook, `set` y `change`; código y cuerpo iguales a los de una inexistente; listas de A y B sin cambios; fila tipo 18; `caplog`), `test_tema_de_conversacion_nueva_fija_el_dueno` | mensajes añadidos a la de A |
| RNF-07.34 (500) | T6 | i `test_tema_de_conversacion_500_sin_detalle` (servicio simulado que lanza con una ruta inventada → 500 «Error interno del servidor», sin la ruta en el cuerpo ni en `caplog`) | 500 con el texto de la excepción |
| RF-21.32 (`get_db`) | T6 | u `test_get_db_no_anota_los_4xx` (404 sin `ERROR` ni identificador; 5xx sigue, enmascarado) | `ERROR ... 404: <id>` |
| RF-17.33 | T7 | u `test_rutas_de_notebooks_solo_usan_el_servicio` (AST: sin `app.repositories`, `app.vectorstore` ni `file_management_service`) | importa repositorios |
| RF-17.30 | T7 | i `test_crear_con_error_inesperado_es_generico` | 400 con la ruta |
| RF-21.30, RNF-07.32, 07.6 | T7 | i `test_acciones_de_notebook_en_bitacora` (nombres inventados ausentes; bitácora que falla), `test_documento_ajeno_en_notebook_propio`; RNF-07.6 con una fila por petición en listar, previsualizar y quitar | sin filas |
| RF-21.30 (previsualizar fallido) | T8 (corrección, §14.13) | i `test_previsualizar_fallido_se_registra` (`[sin_procesar]` → 400, motivo «documento sin procesar», `validacion`; `[archivo_faltante]` → 404, «archivo no encontrado», `interno`; tipo 10, `NB-<id>`, número de documento; nombre y ruta inventados ausentes; respuesta igual con la bitácora que falla) | sin fila de fallo |
| RF-19.2 | T8 | `xfail` `test_fallo_al_quitar_y_reintento[fragmentos]`, `[archivo]`; i `test_archivo_ya_borrado_es_exito` | 200 y documento borrado |

- **Ajuste D1 en `test_recurso_ajeno_da_404_identico`**: compara la foto sin la bitácora y exige 2 filas de intento (una por petición) para las operaciones de un conjunto `_CON_INTENTO`, que crece en T4 (chat), T6 (conversaciones) y T7 (documentos); en T7 cubre todas y el conjunto se quita.
- **Ajuste aprobado en T5** (Andrés, 19/10): `tests/integracion/test_usuarios_de_prueba.py:216` espera 18 tipos de acción en vez de 15 (RF-21.34). Son los dos únicos ajustes a pruebas existentes.
- Simulados: parchar la instancia, no la clase (MEMORY). En integración, `caplog` limitado a `app`. Datos `PRUEBA`; cada prueba limpia; ninguna > 5 s.
- Conteo: 11 `xfail` cerrados → **45** al final, RF-06.2 entre ellos; 0 XPASS.

## 10. Exenciones
- **E0**: extremo a extremo en el navegador hasta la 005; la interfaz (aviso de RF-19.30, tipos en la bitácora, sesión que no se cierra) se comprueba a mano (§11) y se propone como caso de la 005.
- **E1**: la calidad de la respuesta del LLM no se prueba; sí qué contexto recibe.

## 11. Verificación manual de punta a punta (T9)
Antes: `docker compose restart backend celery-worker` (Andrés), `ps`, `curl :8000/`, logs limpios. Andrés crea el Usuario Gubernamental B `PRUEBA` desde el Administrador e inicia las sesiones en el Chrome del MCP; los agentes no reciben contraseñas.
1. A crea «PRUEBA 004b A», sube un documento inventado y chatea: cita solo lo suyo.
2. B, con la frase de A: chat general, por tema (`NB-<id A>`, `nb-<id A>`), temas similares (descripción y tema), resumen y descarga: nada de A; la sesión no se cierra.
3. B por `curl` con su token: chat de notebook, listar, previsualizar, quitar y cargar con el notebook de A y uno inexistente; ver/restaurar/eliminar una conversación de A: 404 idénticos. Logs sin identificadores pedidos.
4. A quita un documento con éxito; con un fallo provocado (Andrés deja el archivo de solo lectura en el contenedor), aviso con el mensaje y documento listado; reintento correcto.
5. Administrador: filas de las acciones (clave y número) e intentos (solo motivo); los 3 tipos con su nombre y en el filtro; historial propio de A.
6. Escritorio y 616 px (`resize_page` 555): consola sin errores. `npm run lint`; `npm run build` con `npm run dev` detenido por Andrés.
7. Limpieza: documentos desde la interfaz; conversaciones de prueba en Redis (⚠️, con su aprobación); Andrés desactiva B (sin borrado físico); los notebooks vacíos se conservan.

## 12. Riesgos
- La suite ronda el límite de RA-02.15 (8 min 12 s): pruebas nuevas cortas, sin LLM real. Se mide en cada tarea; si se pasa, el coordinador avisa a Andrés antes de seguir (aprobado 19/10).
  - Tras la T5 se pasó: el reviewer midió 8 min 48 s en una corrida limpia (el implementer, 8 min 1 s). Andrés lo acepta por ahora (19/10) y se revisa en la T9 con la suite completa.
  - Opción para la T9: mover a una fixture compartida el `setup` de 14,7 s de `test_ajenos_mejor_puntuados_no_reducen_resultados`.
- El filtro `MatchAny` crece con los documentos visibles: aceptable con miles; anotarlo para la spec de RAG.
- `mi-historial` sigue dando 500 (`xfail` de la 004, fuera de alcance, aprobado 19/10): el filtro del historial propio se prueba en su servicio; quedan 45 `xfail`.
- El inventario puede revelar fragmentos con tema distinto del de su documento (§5).

## 13. Documentación (T10)
- Borrador del ERS V1.8 en `specs/004b-aislamiento-de-notebooks/documentacion_t10.md`: RF-11, RF-12, RF-17, RF-19, RF-20, RF-21 y RNF-07 como regla cumplida (sustituye los «Estado actual» de `specs/004-red-de-seguridad-backend/documentacion_t14.md`); RF-13 (RF-17.32); ERS 2.1 (RF-17.33); RF-19 conserva el «Estado actual» de la confirmación. Cambio del 19/10: RNF-07 recoge RNF-07.34 (asociar el tema de una conversación ajena) y RF-17 recoge RF-17.34 (tema equivalente a una clave).
- CU-09 (FA-05: 404 sin respuesta) y CU-13 si cambia; Modelo Relacional si lista el catálogo de tipos.
- El `.docx` y el PDF, solo tras la aprobación del borrador por Andrés (editar `word/document.xml` sobre una copia; MEMORY).
- `MEMORY.md`; grafo y mapas (`graphify update .`, comunidades, `generar_mapa.py`, `generar_mapa_pruebas.py`).

## 14. Decisiones aprobadas por Andrés (19/10/2026)
1. Carga con la clave propia en otra grafía (`nb-5`): se guarda canónica como `NB-5` (decisión 4).
2. `get_db` deja de registrar los errores 4xx, porque el 404 de conversación repetiría el identificador en el registro del servidor (decisión 7): cambio acotado en el núcleo, aprobado.
3. El `downgrade` de la migración solo borra los 3 tipos si ninguna fila de la bitácora los usa (decisión 9; RN-01, sin borrado físico de registros).
4. El 500 de `mi-historial` (`xfail` de la 004) queda fuera de alcance; el filtro del historial propio se prueba en su servicio; quedan 45 `xfail` (§12).
5. Riesgo RA-02.15 (8 min 12 s): se mide en cada tarea; si se pasa, el coordinador avisa a Andrés antes de seguir (§12).
6. Duración tras la T5 (8 min 48 s del reviewer): aceptada por ahora; se revisa en la T9 (§12).
7. Ajuste de `test_usuarios_de_prueba.py:216` (15 → 18 tipos), junto al D1 (§9).
8. Asociar el tema de una conversación ajena (RNF-07.34) y el tema equivalente a una clave (RF-17.34) entran en la spec y se implementan en la T6.
9. `get_db` (decisión 7, §14.2) se implementa en la T6, no en la T7.
10. D9 A: asociar el tema de una conversación ajena da el mismo 200 y cuerpo que una inexistente, sin crear ni tocar nada, con el intento tipo 18 (decisión 12).
11. Confirmado: `ＮＢ-<id propio>` se carga como `NB-<id>`; `NB-５` es no disponible (decisión 11).
12. El 500 inesperado de `rag.py:273` pasa a «Error interno del servidor» en la T6 (RNF-07.34; decisión 13).
13. Andrés, 20/10/2026: A. El previsualizar fallido de un documento propio se registra (tipo 10) con motivo fijo: «documento sin procesar» (`validacion`, como los rechazos corregibles de la ingesta) o «archivo no encontrado» (`interno`, fallo del servidor). Descartado `acceso` para el archivo faltante (lo mezclaría con los intentos de RF-21.32). Se implementa en la vuelta de correcciones de la revisión T6-T8 (§7, §9).
14. Andrés, 20/10/2026: A. Acepta las 6 decisiones que el implementer tomó en la T6, que el reviewer recomendó aceptar (desglose de la T10, tomado del «Resultado» y la «Corrección (vuelta 1)» de la T6 en `tasks.md`):
    1. Conversaciones: `dueno` y `en_lista` en los metadatos; `es_propia` solo los lee; la ajena en el chat es sesión efímera; el chat de notebook queda fuera del índice de la lista.
    2. El 500 de asociar el tema registra solo el tipo y la traza (`logger.error` + `traceback.format_tb`), no `logger.exception`, que escribe el texto de la excepción.
    3. Mecanismo de la vuelta 1: preguntar a la base cómo guardaría el tema. Descartadas: una lista de grafías, rechazar todo tema que la conversión cambie y comparar solo con la fila del tema.
    4. El mismo criterio en el chat por tema (`es_tema_de_clave`; la ruta pasa `tema_es_clave`, sin sesión nueva), en temas similares y en el resumen IA.
    5. `registrar_intento_fallido` anota solo `type(e).__name__`.
    6. `clasificar_clave` sigue aceptando `db=None` (sin sesión, «no es de notebook»); la prueba `test_clasificar_clave_reclasifica_lo_que_la_base_iguala` simula también `como_lo_guarda_la_base`.
15. Andrés, 20/10/2026: A. Acepta las 5 decisiones que el implementer tomó en la T7, que el reviewer recomendó aceptar (desglose del «Resultado» de la T7):
    1. Un id fuera del rango de la columna es no disponible, sin consultar la base.
    2. Crear: el `ValueError` del nombre vacío da 400 con su mensaje; el resto, 500 «Error interno del servidor», con solo el tipo y la traza en el registro.
    3. `RecursoNoDisponible` lleva el motivo; `DocumentoSinProcesar`, `ArchivoNoEncontrado` y `ErrorAlQuitar` llevan la clave, el número del documento y la causa.
    4. Quitar conserva el comportamiento heredado hasta la T8: registra el fallo y vuelve a lanzar la causa original, para que los 2 `xfail` de RF-19.2 no pasen a XPASS.
    5. La auditoría usa `_sin_control`, el tema asociado si su fila existe e `info_adicional.tema`; los intentos llevan el tipo de la acción (listar 11, previsualizar 10, quitar 17).
16. Andrés, 20/10/2026: A. Acepta las 3 decisiones que el implementer tomó en la T8, que el reviewer recomendó aceptar (desglose del «Resultado» y la «Corrección (vuelta 1)» de la T8):
    1. Al borrar el archivo solo `FileNotFoundError` cuenta como éxito; cualquier otro error (un permiso) es `ErrorAlQuitar` y para antes de la fila.
    2. El registro del servidor lleva solo el tipo y la traza del fallo al quitar, sin el texto de la excepción.
    3. Previsualizar fallido: las excepciones llevan la clave y el número del documento, nunca el nombre ni la ruta, y la prueba exige que no lleguen a la fila.
    - Nota de la T10: la lista exacta del reviewer no está en `tasks.md`; Andrés confirma que este desglose coincide.
18. Andrés, 20/10/2026: A. Se acepta la duración de la suite (9 min 22 s) frente al límite de RA-02.15 (8 min 12 s): el setup lento de la primera prueba es arranque de la sesión, y una fixture compartida no lo reduce.
17. Andrés, 20/10/2026: B. `NB‐５` y similares (resto con dígitos no ASCII) son no disponibles para todos; la decisión 11 queda sin excepciones.
