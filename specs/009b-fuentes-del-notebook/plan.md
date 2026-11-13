# Plan 009b — Fuentes del notebook: usar o no usar, renombrar y quitar
Spec aprobada el 05/11/2026. Va DESPUÉS de la 009 (T1-T7). Grafo atrasado: los símbolos se confirmaron con `Grep` y `Read`.

## 1. Archivos y responsabilidades

Existentes (entrega 1):
- `backend/app/routes/rag.py:89` `ConsultaConHistorialRequest`: campo `documentos: Optional[List[StrictInt]] = None`; `except SeleccionVacia` → 400 antes del `except Exception` (:227). RF-11.105.
- `backend/app/services/RAG/rag_chain_service.py`:
  - `consulta_con_historial_streaming` (:198): recibe `documentos`; tras `_notebook_del_chat` (:218) calcula la selección efectiva, antes de tocar la conversación;
  - `_consulta_notebook_con_historial` (:411): pasa `documentos_visibles=selección` al `DynamicServIARetriever` (:431). RF-11.101.
- `backend/app/services/notebook_service.py`: nuevos `SeleccionVacia` y `seleccion_efectiva`; usa `documento_repo.listar_por_expediente(..., solo_procesados=True)` (`documento_repository.py:239`). RF-11.105, 11.106, RNF-07.100.
- `frontend/services/consultaService.js:126` `consultaGeneralStreaming`: parámetro final `documentos = null` → `payload.documentos` si es un arreglo.
- `frontend/pages/notebooks/index.js`: chips (:517-537) → lista de fuentes; `enviarPregunta` (:335, :353, :365) envía la selección; envío (:580, :587) desactivado; `handleVerArchivo` (:189) pierde el guardia de `close chip` (:192).
- `frontend/e2e/soporte/pantallas.js:70` `fichaDeDocumento` y `:81` `quitarDocumentoEnPantalla`; `frontend/e2e/soporte/datos.js:99` (`preguntar` acepta `documentos`).
- `frontend/e2e/flujos/notebooks.spec.js:295` `equis` → abrir ⋮ y «Quitar fuente» (cambio de expectativa, §8).

Existentes (entrega 2):
- `backend/app/db/models/documento.py:84`: columna `CT_Nombre_visible` (§4).
- `backend/app/repositories/documento_repository.py:86`: nuevos `renombrar` y `como_lo_guarda_la_base`.
- `backend/app/vectorstore/base.py` y `qdrant_backend.py:201`: nuevo `actualizar_nombre_de_documento(document_id, nombre)`.
- `backend/app/services/notebook_service.py`: `renombrar_documento`, `nombre_mostrado`, `extension_de`; `validar_nombre` de la 009 gana `mensaje_vacio` (por omisión, el del notebook).
- `backend/app/routes/notebooks.py`: `DocumentoNotebookResponse` (:112) suma `extension`; `nombre_archivo` pasa a llevar el nombre mostrado (:144); `FileResponse` (:183) con `filename`; ruta nueva `PUT /notebooks/{notebook_id}/documentos/{documento_id}`.
- `backend/app/services/bitacora/notebooks_audit_service.py:148`: nuevo `registrar_renombrado_documento`; reutiliza `registrar_intento_fallido` (:181).
- `backend/app/constants/tipos_accion.py` (21), `routes/bitacora.py:97,:223` (`le=21`), `frontend/common/tiposAccion.js`, `frontend/services/bitacoraService.js:298`.
- `backend/tests/soporte/inventario_rutas.py`: clasificar la ruta `PUT` nueva.
- `frontend/services/notebookService.js:73`: nuevo `renombrarDocumento` (`httpService.put`), con `status` en el error.

Nuevos ⚠️ (crear archivos):
- `frontend/components/notebooks/FuenteNotebook.jsx` (fila: casilla, nombre, ⋮, edición en línea).
- `backend/tests/unitarias/test_fuentes_notebook.py`, `backend/tests/integracion/test_fuentes_notebook.py`.
- `frontend/e2e/flujos/notebooks-fuentes.spec.js`.
- Entrega 2: `backend/alembic/versions/<rev>_nombre_visible_de_documento.py`.

## 2. Lógica — entrega 1 (selección)

```
notebook_service.seleccion_efectiva(db, notebook, ids) -> set[int]
  tema = expediente_repo.obtener_por_numero(db, notebook.clave_interna); sin tema → set()
  procesados = {d.CN_Id_documento for d in documento_repo.listar_por_expediente(db, tema, solo_procesados=True)}
  return procesados ∩ set(ids)             # ajenos, de otro notebook, inexistentes o enormes se descartan en Python (RNF-07.100)

consulta_con_historial_streaming(..., documentos=None)
  notebook = _notebook_del_chat(...)       # 404 uniforme primero (RF-11.32)
  seleccion = None
  si notebook y documentos is not None:     # campo ausente → como hoy (RF-11.105)
     seleccion = seleccion_efectiva(...)   # sesión propia, como _notebook_del_chat
     si vacía → raise SeleccionVacia        # antes de la conversación: no llama al modelo ni guarda la pregunta
  ... _consulta_notebook_con_historial(..., seleccion) → DynamicServIARetriever(documentos_visibles=seleccion)
```
- Chat general y por tema: `documentos` no se pasa (RF-11.107).
- `documentos_visibles` ya filtra dentro de la consulta de Qdrant (`qdrant_backend.py:251`): las marcadas no pierden resultados. La lista «ARCHIVOS DE ESTA CONSULTA» sale de los fragmentos recuperados (`presupuesto_contexto.py:148`).
- Router: `SeleccionVacia` → 400 «Marque al menos una fuente para consultar.»; `StrictInt` da el 422 de Pydantic para `"5"`, `5.5`, `true`.

## 3. Lógica — entrega 2 (renombrar)

```
extension_de(interno): i = interno.rfind("."); return interno[i:] si i > 0 si no ""
nombre_mostrado(doc): getattr(doc, "CT_Nombre_visible", None) or doc.CT_Nombre_archivo   # getattr: simulaciones unitarias

renombrar_documento(db, texto_nb, texto_doc, base, usuario) -> (doc, cambiado)
  nb  = id_de_notebook(texto_nb) → _notebook_o_no_disponible     # 404 + «notebook no disponible»
  doc = id_de_notebook(texto_doc) → _documento_del_notebook      # 404 + «documento no disponible» (RNF-07.101, antes de validar)
  si estado ∉ {Procesado, Error} → NombreNoValido(«fuente en proceso», «Espere a que termine de procesarse.»)
  b = validar_nombre(base, mensaje_vacio="El nombre de la fuente no puede estar vacío")   # vacío, >150
  nuevo = b + extension_de(doc.CT_Nombre_archivo)
  documento_repo.como_lo_guarda_la_base(db, nuevo) != nuevo → «nombre con caracteres no admitidos»
  nuevo == nombre_mostrado(doc) → (doc, False)                                     # sin fila
  nuevo.casefold() ∈ {nombre_mostrado(x).casefold() de las otras fuentes del notebook} → «nombre duplicado»
  anterior = nombre_mostrado(doc)
  si Procesado:
     try vector.actualizar_nombre_de_documento(id, nuevo)
     except: _devolver(id, anterior); raise ErrorAlRenombrar               # RF-19.105.2
  try documento_repo.renombrar(db, doc, nuevo)       # commit; rollback y relanza
  except: si Procesado: _devolver(id, anterior); raise ErrorAlRenombrar     # RF-19.105.3
  return (doc, True)
_devolver: try actualizar_nombre_de_documento(id, anterior) except: logger.exception (riesgo residual aceptado)
```
- Qdrant: `client.set_payload(collection, payload={"nombre_archivo": nombre}, key="metadata", points=FilterSelector(filter=metadata.id_documento == id), wait=True)`.
- Router `PUT`: `notebook_id: str`, `documento_id: str`, cuerpo `FuenteRenombrarRequest{nombre: str}` sin `max_length`; respuesta `DocumentoNotebookResponse`.
  - `RecursoNoDisponible` → `_no_encontrado(..., RENOMBRAR_DOCUMENTO_NOTEBOOK)` (:118);
  - `NombreNoValido` → fila de validación + 400 `detail=mensaje`;
  - `ErrorAlRenombrar` u otra → fila «error inesperado»/«interno» + 500 «Error interno del servidor» (traza sin texto).
- Listado (:141): `nombre_archivo=nombre_mostrado(d)`, `extension=extension_de(d.CT_Nombre_archivo)`.
- Vista previa (:183): `FileResponse(..., filename=nombre_mostrado, content_disposition_type="inline")`; el tipo sigue saliendo del nombre interno.
- Vista previa, `verificar_esta_procesado` (:242), descarga y quitar siguen con `CT_Nombre_archivo` (RF-19.103).

## 4. Datos — migración ⚠️ (entrega 2; RN-01.100, RF-21.100)
- `down_revision` = la cabeza que deje la 009 (hoy `d94c2a6e33a5`; confirmar con `alembic heads`).
- Autogenerada con el modelo ya cambiado y revisada: deja solo `add_column('T_Documento', CT_Nombre_visible String(500), nullable=True)`, más el `op.execute` del tipo 21 «Renombrar Documento de Notebook» con el patrón de `b7c4d2e9f013`.
- `downgrade`: `THROW` si hay nombres visibles o filas de bitácora con 21; si no, quita el tipo y la columna.
- Existentes: la columna queda NULL y se muestra el nombre interno. Qdrant: solo se tocan los puntos del documento renombrado. Redis: nada.

## 5. Interfaz (Usuario Gubernamental; `/notebooks` ya en `ROUTE_PERMISSIONS`)
- Lista `ul` con `aria-label="Fuentes del notebook"`, una `li` por fuente (`FuenteNotebook.jsx`):
  - `Checkbox` HeroUI con `aria-label="Usar <nombre> en el chat"`;
  - botón del nombre (`truncate`, `min-w-0`, `title` completo, color por estado como hoy): abre la vista previa si está Procesado;
  - `Dropdown` con disparador `aria-label="Opciones de <nombre>"` (`shrink-0`): «Cambiar el nombre de la fuente» (entrega 2) y «Quitar fuente».
  - Mientras se quita: la `li` con `aria-disabled="true"` y `data-disabled` (lo lee `notebooks.spec.js:320` y `:369`).
- Estado en `index.js`: `desmarcadas` (`Set` de ids). Así lo nuevo entra marcado; se vacía en `seleccionarNotebook` (:116). RF-11.103.
- Selección enviada = ids de `documentosNotebook` fuera de `desmarcadas`, en cualquier estado (RF-11.106).
- Sin fuentes Procesado marcadas: «Enviar» y Enter desactivados, y bajo el campo «Marque al menos una fuente para consultar.» (RF-11.104).
- Renombrar (entrega 2): `Input` con la base y la extensión fija como `endContent`; «Guardar» y «Cancelar»; Enter guarda, Escape cancela sin llamar.
  - Sin `maxLength`; el vacío también se envía. 400 → `detail` bajo el campo; 200 → `cargarDocumentos`.
  - 404 → se quita de la lista y aviso «La fuente ya no está disponible.»; 500 → `Toast.error` «No se pudo cambiar el nombre de la fuente. Intente de nuevo.».
  - En proceso: opción desactivada con «Espere a que termine de procesarse.» como descripción.
- Coordinación con la 009: no se toca `ItemNotebook.jsx` ni `pantallas.js:39`.

## 6. Bitácora (RF-21)
| Acción | Tipo | Tema | `info_adicional` |
|---|---|---|---|
| Renombrar fuente | 21 | `NB-<id>` | `resultado`, número de documento; `motivo` y `tipo_error` si falla |
| No disponible | 21 | ninguno | `registrar_intento_fallido`: «notebook no disponible» / «documento no disponible», `acceso` |
| Quitar fuente | 17 | sin cambios | sin cambios (RF-21.103) |
- Nunca nombres anterior ni nuevo (persona inventada en la prueba). Idéntico: sin fila. Marcar/desmarcar: sin fila (RF-21.102).
- El 400 de selección vacía no deja fila, como «La consulta no puede estar vacía» (rag.py:117).

## 7. Decisiones
1. Selección como `documentos_visibles` del retriever; descartado: filtrar tras recuperar (reduce los resultados de las marcadas).
2. `StrictInt` para el 422; descartado: `int` (aceptaría `"5"` sin error).
3. Intersección en Python con los Procesado del notebook; descartado: mandar los ids crudos a Qdrant.
4. `desmarcadas` en vez de `marcadas`; descartado: lista de marcadas (lo nuevo entraría desmarcado).
5. `nombre_archivo` del listado = nombre mostrado + campo `extension`; descartado: campo `nombre_mostrado` (cambia frontend y e2e sin necesidad).
6. «En proceso» = todo estado que no sea Procesado ni Error, y se comprueba antes del nombre; descartado: comparar solo «Pendiente».
7. `CT_Nombre_visible` `String(500)`; descartado: 255 (150 + una extensión larga no cabría).
8. `set_payload` con `key="metadata"` y filtro; descartado: reescribir cada punto (toca el texto y el vector). Si la versión no lo admitiera, se usa `listar_puntos_de_documento` + `set_payload` por ids.
9. `validar_nombre` de la 009 con `mensaje_vacio`; descartado: copiarla.
10. `FuenteNotebook.jsx` aparte; descartado: más código en `index.js` (~630 líneas).

## 8. Pruebas existentes que cambian (actualizar, nunca borrar)
- `pantallas.js:70` `fichaDeDocumento` → `li` de la lista «Fuentes del notebook»; `:84` → ⋮ y menú «Quitar fuente». Lo usan RF-19.40-42 y `chat.spec.js:41`.
- `notebooks.spec.js:295` `equis` → función que abre ⋮ y elige «Quitar fuente»; las aserciones de RF-19.40 no cambian.
- Entrega 2: `test_aislamiento_notebooks.py:689` (`range(1, 22)`), `:729-730` (el rechazado pasa de 21 a 22), `test_usuarios_de_prueba.py` (20 → 21).

## 9. Pruebas por requisito
**Unitarias** (`test_fuentes_notebook.py`):
- `test_seleccion_efectiva_*` (RF-11.105, 11.106, RNF-07.100): intersección, solo Procesado, ajenos y enormes descartados.
- `test_seleccion_formato_422` (RF-11.105): `"5"`, `5.5`, `true`, `null` en la lista.
- `test_extension_de` (Definiciones): `informe.v2.pdf`, `.notas`, `sin_punto`.
- `test_renombrar_documento_*` (RF-19.102, 19.106, 19.107, RNF-07.101): orden de validaciones, idéntico, duplicado sin mayúsculas, en proceso, 404 antes de validar.
- `test_renombrar_compensacion` (RF-19.105): fallo de Qdrant y fallo de la base, simulados.
**Integración** (`test_fuentes_notebook.py`, entorno aislado):
- `test_chat_notebook_respeta_la_seleccion` (RF-11.101, 11.102): fragmentos y lista que recibe el modelo simulado sin la desmarcada (`_todo_lo_que_recibio_el_modelo`).
- `test_seleccion_vacia_o_inefectiva_400` (RF-11.105): vacía, solo Pendiente/Error, solo ajenas → 400, modelo no llamado, sin historial.
- `test_seleccion_ausente_como_hoy` y `test_seleccion_ignorada_en_general_y_tema` (RF-11.105, 11.107).
- `test_seleccion_ajena_descartada` (RNF-07.100) y notebook ajeno → 404 uniforme.
- Entrega 2:
  - `test_migracion_tipo_21_y_columna` (RF-21.100);
  - `test_renombrar_fuente_procesada` (RF-19.103, 19.104): fila, puntos en Qdrant, archivo en disco igual, listado, cabecera de la vista previa;
  - `test_renombrar_rechazos_400` (RF-19.106, 19.107), `test_renombrar_no_disponible_404` (RNF-07.101, RF-21.104), `test_renombrar_compensa_si_falla_qdrant` (RF-19.105, 19.108);
  - `test_bitacora_renombrar` (RF-21.101, 21.103), `test_carga_tras_renombrar` (casos límite de carga).
**Extremo a extremo** (`notebooks-fuentes.spec.js`):
- Entrega 1:
  - `RF-11.100 · RF-11.102 · casilla marcada y selección enviada`;
  - `RF-11.104 · RF-11.106 · sin fuentes Procesado marcadas no se envía`;
  - `RF-11.103 · al volver al notebook todas marcadas`;
  - `RF-19.100 · el menú no abre la vista previa ni cambia la casilla`;
  - `RNF-04.100 · nombre de 150 sin desborde` (solo 616 px).
- Entrega 2: `RF-19.102 · RF-19.103 · renombrar, cancelar y Escape`, `RF-19.106 · rechazos`, `RF-19.107 · en proceso desactivado`.
- Diferibles (con exención y verificación manual): `RF-19.109 · otra pestaña`, `RF-19.110 · dos pestañas`, `RF-19.105 · aviso de fallo`.
- Para el presupuesto (≤ 720 s): solo RNF-04.100 corre a 616 px; las demás, a 1366.
**Exención de las e2e diferibles (decisión de Andrés, 09/11/2026)**: sin e2e quedan RF-19.109 en la interfaz (aviso «La fuente ya no está disponible.» y la fila desaparece), RF-19.110 (dos pestañas), RF-19.105 en la interfaz (aviso «No se pudo cambiar el nombre de la fuente. Intente de nuevo.», `frontend/pages/notebooks/index.js` ~244) y RNF-04.100 para el renombrado a 616 px. Justificación: la suite e2e ya dura 651–664 s de un límite de 720 s. Evidencia manual (entrega 2, MCP `chrome-devtools`, 09/11/2026): el 404 desde otra pestaña PASA (paso 8: aviso y fila retirada) y el renombrado a 616 px PASA (paso 11: sin desborde, `scrollWidth` = `clientWidth`); el aviso de fallo inesperado de RF-19.105 en la interfaz NO se verificó a mano (el servidor sí: `test_renombrar_compensacion`, `test_renombrar_compensa_si_falla_qdrant`).
**Exentos**: el aspecto visual y el nombre de descarga del visor de PDF del navegador (el servidor se prueba por la cabecera); los revisa Andrés.

## 10. Verificación manual (Andrés, en persona)
- Implementer: `alembic current` (entrega 2), `docker compose ps`, `docker compose logs --tail 100 backend` sin errores.
- Andrés, 1366 y 616 px, consola limpia: criterios de finalización de la spec (entrega 1 y 2); Administrador rechazado en `/notebooks`.
- Entrega 2: `curl` a Qdrant con `metadata.id_documento` muestra el nombre nuevo; el archivo en `uploads/NB-<id>/` conserva su nombre.
- Limpieza: fuentes `PRUEBA` quitadas desde la interfaz.

## 11. Documentación (última tarea) ⚠️
- ERS: RF-11 (casilla), RF-19 (menú y renombrado), RF-21 (tipo 21). CU-13 paso 1 (⋮ en vez de «x») y CU nuevo «Renombrar una fuente».
- HU-NUEVA-3 y HU-NUEVA-4; Modelo Relacional (`CT_Nombre_visible`, tipo 21).
- Sobre copias de los `.docx`, solo `word/document.xml`; los PDF los exporta Andrés. Además: `MEMORY.md` y `graphify-out/`.

---

## 12. Cambio GG1 — baja lógica de la fuente (11/11/2026)
Cubre la sección E de la spec: RF-19.111 a RF-19.115, RF-21.105, RN-01.101 (y los cambios a RF-19.101, RF-21.103 y RN-01.100). Spec aprobada por Andrés el 11/11/2026; falta el visto bueno del tutor para RN-01, RNF-10 y la constitución (no bloquea el código, sí el cierre documental). Grafo atrasado: los símbolos se confirmaron con `Grep` y `Read`.

**Idea en una frase**: «Quitar fuente» sigue borrando el archivo y los fragmentos, pero en vez de borrar la fila del documento la marca con la fecha y hora y quién la quitó; todo lo que lee documentos pasa a ignorar las filas marcadas.

### 12.1 Archivos y responsabilidades
| Archivo (símbolo, `archivo:línea`) | Cambio | Requisitos |
|---|---|---|
| **Nuevo** `backend/alembic/versions/<id>_baja_logica_de_documentos.py` (`down_revision = 'f2b8c4d1a937'`) ⚠️ | Agrega a `T_Documento` `CF_Fecha_baja` (fecha y hora, nula) y `CN_Id_usuario_baja` (clave foránea a `T_Usuario`, nula). Los existentes quedan activos (nulos). Se genera con `alembic revision --autogenerate` y se revisa antes de aplicar. | RF-19.111, RN-01.101 |
| `backend/app/db/models/documento.py:66` (`T_Documento`) | Las dos columnas nuevas (`Mapped[Optional[...]]`) y una propiedad `esta_quitado`. | RF-19.111 |
| `backend/app/repositories/documento_repository.py` | **Nuevo** `dar_de_baja(db, documento, usuario_id, auto_commit)` (marca fecha, UTC, y usuario; nunca borra). Todas las consultas excluyen quitados con una sola condición compartida (`CF_Fecha_baja IS NULL`): `obtener_por_id:96` (parámetro `incluir_quitados=False`), `listar_por_expediente:239`, `listar_rutas_de_carpeta:262`, `listar_procesados_con_temas:274`, `listar_procesados_de_temas:297`, `obtener_ids_procesados:321`, `listar_por_expediente_y_nombres:347`, `verificar_esta_procesado:438`. `eliminar:408` se **quita**: su único uso es `notebook_service.py:456` y dejarlo contradice RN-01.101. | RF-19.111, RF-19.113, RF-19.114 |
| `backend/app/services/notebook_service.py` | `quitar_documento:425`: orden fragmentos → archivo → `dar_de_baja` (en vez de `eliminar`), mismo `ErrorAlQuitar`. `_documento_del_notebook:328`: un quitado se trata como inexistente (404 uniforme). `listar_documentos_de_notebook:398`, `seleccion_efectiva:489` y el duplicado de `renombrar_documento:371` ya quedan filtrados por el repositorio. | RF-19.111 a RF-19.114 |
| `backend/app/services/ingesta/async_processing/celery_tasks.py:146,226` | Defensa: si el documento tiene baja cuando la tarea termina de procesarlo, no indexa y descarta lo ya indexado de ese documento; hoy, quitar un documento Pendiente borra su fila y la tarea falla, pero con la fila conservada la tarea podría terminar y dejar fragmentos de una fuente quitada. | RF-19.111, RF-19.113 |
| `backend/app/services/estudio_service.py:173,328` | Sin cambio de código: ambos leen por `listar_por_expediente`, que ya no devuelve quitados; el resultado guardado sigue mostrando el nombre y marca la fuente como faltante (`fuentes_faltantes`). Se comprueba con una prueba. | RF-19.115 |
| `backend/app/vectorstore/qdrant_backend.py:78` y `backend/app/services/documentos/file_management_service.py:253,370` | Sin cambio de código: usan `obtener_ids_procesados`, `verificar_esta_procesado` y `listar_por_expediente_y_nombres`. Con el filtro, ni la búsqueda vectorial ni la vista previa ni la descarga ven un quitado (defensa adicional: aunque quedara un fragmento, no se recupera). | RF-19.113 |
| `backend/app/services/expediente_service.py:322,347,367`, `backend/app/services/busqueda_similares/documentos/documento_service.py:130,239`, `backend/app/services/ingesta/refragmentado.py:68` | Sin cambio de código: consultan por el repositorio. Se cubren con la prueba de invariante (12.8). | RF-19.113 |
| `backend/app/repositories/bitacora_repository.py:973` (documentos por tipo en un rango) | Sin cambio (decisión D3 de 12.7). | RF-21.105 |
| `backend/app/routes/notebooks.py` (DELETE de un documento), esquemas | Sin cambio: misma ruta, mismos códigos (200/404/500) y mismos mensajes. Router delgado, sin repositorios (convención de la API). | RF-19.101, RF-19.112 |
| `backend/tests/soporte/datos.py:60-80`, `backend/tests/instancia_e2e/simulados_e2e.py:149` | Sin cambio: la limpieza borra `T_Documento` por prefijo del nombre (la fila quitada conserva su nombre) y `T_Usuario` va último, así que la clave foránea nueva no estorba. Se verifica con las pruebas de la instancia. | RA-02 |
| Frontend (`pages/notebooks/index.js`, `FuenteNotebook.jsx`, servicios) | **Sin cambio**: los textos de «Quitar documento» y de los errores no cambian (RF-19.101). | RF-19.101 |

### 12.2 Lógica por capa
- **Router** (sin cambio): recibe el DELETE, llama al servicio, registra en la bitácora y traduce errores (404 uniforme, 500 «No se pudo quitar el documento. Intente de nuevo.»).
- **Servicio** (`notebook_service`): valida que el notebook y el documento sean del usuario y que el documento no esté ya quitado; ejecuta los tres pasos en orden y levanta `ErrorAlQuitar` si falla alguno.
- **Repositorio** (`documento_repository`): único lugar que conoce la condición «activo»; `dar_de_baja` solo marca. Ninguna otra capa filtra por la columna.
- **Dependencias externas:** Qdrant (borrar fragmentos), disco (`unlink` del archivo), SQL Server (marcar la fila). No intervienen Ollama, Redis ni HTR.

### 12.3 Flujo
```
quitar_documento(notebook_id, documento_id, usuario):
    notebook  = notebook_propio(...)                      # 404 uniforme si ajeno o inexistente
    documento = documento_del_notebook(notebook, id)      # 404 uniforme si de otro notebook, inexistente o YA QUITADO
    try:
        1. vectorstore.delete_document_chunks(id)         # cero puntos = éxito (idempotente)
        2. archivo.unlink()  (FileNotFoundError = éxito)  # idempotente
        3. repo.dar_de_baja(documento, usuario)           # solo si 1 y 2 salieron bien
    except: raise ErrorAlQuitar(clave, id, causa)         # la fila NO se marca; sigue listada; reintentar completa
```
Un reintento tras un fallo en 3 repite 1 y 2 (ya cumplidos) y termina marcando la fila. La consulta de cada lectura: `WHERE ... AND CF_Fecha_baja IS NULL`.

### 12.4 Datos
- **Migración de Alembic ⚠️** (pide aprobación antes de crearla y de aplicarla): dos columnas nulas en `T_Documento`; `CN_Id_usuario_baja` con la misma forma y clave foránea que `T_Notebook.CN_Id_usuario`. Reversible (`downgrade` quita las columnas). El backend aplica `alembic upgrade head` al arrancar.
- **Datos existentes:** todos activos (nulos). Los documentos quitados antes del cambio no se pueden reconstruir y no se intenta.
- **La relación con el notebook** (`T_Expediente_Documento`) **se conserva** para el quitado: es lo que permite saber de qué notebook era sin otra columna (RF-19.111). Por eso el filtro vive en el repositorio y no en el ORM.
- **Qdrant:** sin cambio de metadatos; los fragmentos del quitado se eliminan. **Redis:** sin cambio.

### 12.5 Interfaz
Sin pantallas ni rutas nuevas (`ROUTE_PERMISSIONS` sin cambio). La interfaz es la misma: «Quitar fuente» → «Quitar documento» con «Quitar»/«Cancelar», aviso «No se pudo quitar el documento. Intente de nuevo.» y «La fuente ya no está disponible.» (RF-19.109). La advertencia «no se puede deshacer» sigue siendo cierta: el contenido se elimina y el usuario no puede restaurarlo.

### 12.6 Bitácora (RF-21)
Sin acción nueva: se conserva «Quitar Documento de Notebook» (`TiposAccion.QUITAR_DOCUMENTO_NOTEBOOK = 17`, `notebooks_audit_service.py` ~`:230-255`), con usuario, fecha y hora, clave `NB-<id>`, número de documento y resultado, **sin nombres** (RNF-07.24). La novedad es que ese número ahora llega a una fila existente con el nombre. Si el registro falla, la acción se completa igual (RF-21.83).

### 12.7 Decisiones técnicas
- **D1. El filtro «activo» va en el repositorio, en cada consulta, y `eliminar` se quita.** Alternativa descartada: filtrar en el ORM con un `secondaryjoin` en `T_Expediente.documentos` (`expediente.py:81`): es una relación de escritura y las condiciones personalizadas en una relación así dan advertencias y casos raros, y no cubriría las consultas con `select`.
- **D2. Se conserva la fila de `T_Expediente_Documento`.** Alternativa descartada: borrarla al quitar y guardar el notebook en una columna: haría que todas las consultas por unión excluyeran solas al quitado (menos filtros), pero perdería la relación «de verdad» y es un borrado físico de otra fila, justo lo que GG1 quiere evitar.
- **D3. La estadística de la bitácora «documentos por tipo en un rango» (`bitacora_repository.py:973`) sigue contando todo lo cargado, también lo quitado.** Es un recuento de cargas y borrarlo falsearía el historial; si Andrés prefiere excluir los quitados, es un filtro más. Se anota en la spec como caso límite al aprobar.
- **D4. La baja se marca al final.** Alternativa descartada: marcar primero y borrar el contenido después: un fallo dejaría un documento «quitado» con fragmentos o archivo huérfanos, y el reintento ya no lo vería.
- **D5. Quitar un documento mientras se procesa:** la tarea descarta lo indexado si el documento tiene baja. Alternativa descartada: impedir quitar un Pendiente: cambiaría RF-19 («en cualquier momento»).
- **D6. Una sola condición reutilizable** (constante en el repositorio) y una prueba de invariante que recorre todas las consultas públicas. Alternativa descartada: confiar en revisar a mano cada llamada (se nos escaparía una).

### 12.8 Pruebas (primero en rojo; datos `PRUEBA` en el entorno aislado)
**Unitarias** (`backend/tests/unitarias/test_baja_logica_documentos.py`, **nuevo**; servicio con repositorio, Qdrant y disco simulados):
- Orden y marca: fragmentos → archivo → baja, con el usuario; no se llama a `eliminar` (RF-19.111).
- Falla en cada paso (fragmentos, archivo, marca): `ErrorAlQuitar`, la baja no se marca antes de tiempo y el reintento termina (RF-19.112).
- Un documento ya quitado es 404 uniforme en `_documento_del_notebook` (RF-19.113).

**Integración** (SQL Server, Qdrant y Tika reales del entorno aislado; Redis simulado), en `test_red_notebooks.py` (se actualizan) y `test_baja_logica_documentos.py` (nuevo):
- Tras quitar: la fila existe con `CF_Fecha_baja` reciente, `CN_Id_usuario_baja` del usuario, y su nombre, tipo, fecha de carga y relación con el notebook intactos; no hay archivo ni fragmentos (RF-19.111).
- Con la base, Qdrant o el disco simulados para fallar en cada paso: 500 con el mensaje exacto, fila sin marcar, documento listado; el reintento completa (RF-19.112).
- **Invariante** (parametrizada sobre todas las consultas públicas del repositorio y los servicios que leen documentos): el quitado no aparece en la lista, la selección efectiva del chat (si era la única marcada, 400), el Estudio (generar), la vista previa, la descarga, el renombrado ni Casos Similares (RF-19.113).
- Quitar dos veces o desde otra pestaña: 404 uniforme (RF-19.113, RF-19.109).
- Renombrar otra fuente con el nombre de la quitada: permitido; cargar un archivo con ese nombre: sin sufijo (RF-19.114).
- Resultado del Estudio previo: sigue abriéndose, con el nombre y `fuentes_faltantes` verdadero (RF-19.115).
- Bitácora: la fila de «Quitar Documento de Notebook» no trae nombres y su número resuelve a la fila quitada (RF-21.105, RF-21.103).
- Quitar un documento Pendiente mientras se procesa: no quedan fragmentos al terminar la tarea (RF-19.113, D5).
- La migración: columnas presentes y nulas en los existentes; `upgrade` y `downgrade` sin error.
- Se **actualizan** (no se borran ni se desactivan): `test_red_notebooks.py:443` (`test_quitar_uno_de_dos`), `:519`, `:559`, `:586` («tras quitarlo no queda fila…», pasa a «queda la fila quitada»), `test_aislamiento_notebooks.py:1194` y lo que mencione `eliminar`/tres representaciones; la prueba de `tests/instancia_e2e/` que cuente `T_Documento`.

**Extremo a extremo:** la interfaz no cambia, así que RF-19.40, RF-19.41, RF-19.42 y RNF-07.40 (`notebooks.spec.js:279-406`) deben seguir pasando tal cual (desaparece de la lista y del chat, fallo con reintento, otra pestaña). Se agrega a RF-19.41 la aserción de que, tras quitar, el chat no cita la fuente (si no está ya). Sin pruebas nuevas, para no pasar del presupuesto de ≤ 720 s.

**No automatizable:** la lectura por una persona de una auditoría real (la tabla de la fila quitada se revisa a mano en 12.9).

### 12.9 Verificación manual (Andrés)
1. Aplicar la migración y reiniciar: `docker compose restart backend celery-worker`; `docker compose exec backend alembic current` en el nuevo número; backend sano y sin errores en el log.
2. Con un usuario de prueba, un notebook `PRUEBA` con dos fuentes: quitar una por el menú ⋮ a 1366 y a 616 px. Debe salir de la lista y el chat no debe citarla.
3. En SQL Server: la fila del documento sigue, con `CF_Fecha_baja` y `CN_Id_usuario_baja` llenos; en Qdrant: cero puntos con su `id_documento`; en `uploads/NB-<id>/`: el archivo no está; en la bitácora: «Quitar Documento de Notebook» con el usuario, la hora, `NB-<id>` y el número que apunta a esa fila.
4. Generar un Resumen antes de quitar y abrirlo después: conserva el nombre de la fuente y el aviso de que ya no está.
5. Casos de error: Qdrant detenido al quitar (500 con mensaje en español, documento sigue); recurso de otro usuario (404).
6. Limpiar los datos de prueba (la fila quitada es residuo aceptado en desarrollo; la suite la borra en su entorno aislado).

### 12.10 Documentación (última tarea) ⚠️
- **ERS** (`Documentacion_ServIA_2026/`): RF-19 (la eliminación pasa a fragmentos y archivo más baja lógica de la fila; deja de ser la única eliminación definitiva de filas), RN-01 y RNF-10 (excepción limitada al contenido), RF-21 (nota de la fila de «Quitar fuente»); versión nueva del ERS.
- **HU-19** y **CU-13** (pasos y salida), con su diagrama si menciona el borrado de la fila.
- **Modelo Relacional** (`T_Documento`: dos columnas nuevas y la clave foránea) y su diagrama.
- **`docs/constitution.md` principio 5**, **`CLAUDE.md` («Datos»)** y **`.claude/rules/testing.md`** (menciona la excepción): requieren tu aprobación y conviene el visto bueno del tutor.
- Después, `graphify update .`, el mapa y `MEMORY.md`. Cualquier texto previo de las specs 004, 004b, 005 y 008 sobre «tres representaciones» se anota como superado por GG1 (no se reescriben).

### 12.11 Riesgos y orden sugerido
- **Riesgo principal:** una consulta que no excluya quitados mostraría o citaría una fuente quitada. Mitigación: condición única, prueba de invariante por consulta y la defensa de los ids procesados en la búsqueda vectorial.
- **Orden de dependencia** (lo detalla `tasks.md`): migración y modelo → repositorio (filtro, `dar_de_baja`, sin `eliminar`) → servicio de quitar → defensa del Worker → actualizar las pruebas existentes → verificación y documentación.

---

## 13. Cambio HH1 — nombre completo de la fuente (12/11/2026)
Cubre la sección F de la spec: RF-19.116, RF-19.117, RF-19.118, RNF-04.101, HU-NUEVA-5. Aprobado por Andrés el 12/11/2026; sin dudas abiertas. Es solo de interfaz: sin backend, migración, bitácora ni dependencias (`Tooltip` es de HeroUI, que ya se usa en `ExpedienteInput.jsx` y `MessageBubble.jsx`). Grafo atrasado: los símbolos se confirmaron con `Grep` y `Read`.

### 13.1 Archivos y responsabilidades
| Archivo (símbolo, `archivo:línea`) | Cambio | Requisitos |
|---|---|---|
| `frontend/components/notebooks/FuenteNotebook.jsx:101-108` (el `<button>` del nombre) | Se envuelve en `Tooltip` de HeroUI (`delay=0`, `closeDelay=0`, `placement="top"`): contenido = nombre mostrado completo y, solo en Procesado, una segunda línea «Haga clic para ver el archivo original». Se quita el atributo `title` (evita el aviso nativo duplicado). El botón ya es enfocable: el aviso sale también con teclado. Clases del aviso: `max-w-xs break-all` (parte nombres sin espacios). | RF-19.116, RF-19.118, RNF-04.101 |
| `frontend/pages/notebooks/index.js:739-753` (subidas en curso, `archivosSubiendo`) | El `Chip` pasa a una sola línea: `base: max-w-full`, nombre en `<span class="truncate min-w-0">` y porcentaje en `<span class="shrink-0">`; todo envuelto en un `Tooltip` cuyo disparador es un `<span tabIndex={0}>` (la etiqueta no es enfocable por sí sola) con el nombre completo y el porcentaje. El contenedor `flex flex-wrap` suma `min-w-0` y `w-full`. | RF-19.117, RNF-04.101 |
| `frontend/e2e/flujos/notebooks-fuentes.spec.js` | Pruebas nuevas (ver 13.5). | RF-19.116 a 19.118, RNF-04.101 |

### 13.2 Lógica y flujo
- Sin capas de servidor. El nombre mostrado es `fuente.nombre_archivo` (ya viene como nombre mostrado, RF-19.103).
```
al pasar el mouse o enfocar el nombre → Tooltip(delay 0) muestra [nombre] (+ «Haga clic…» si Procesado)
al salir / perder foco / Escape → se cierra
etiqueta de subida: [icono][nombre truncado «…»][ — N%]  (el N% nunca se recorta)
```

### 13.3 Datos, bitácora y roles
Sin cambios. `ROUTE_PERMISSIONS` sin cambios (la página `/notebooks` ya existe). Textos nuevos: ninguno (la línea «haga clic para ver el archivo original» ya existía en el `title`).

### 13.4 Decisiones
- **D1. `Tooltip` de HeroUI en lugar del `title` del navegador.** Aparece sin retraso y con teclado y se estiliza. Alternativa descartada: dejar `title` (el problema original: tarda y no sale con teclado).
- **D2. El aviso se muestra siempre.** Alternativa descartada: medir `scrollWidth > clientWidth` para mostrarlo solo si hay recorte (más código, parpadeos al redimensionar; ya lo aprobó Andrés).
- **D3. Recortar el nombre de la etiqueta con `truncate` y dejar el porcentaje fuera del recorte.** Alternativa descartada: dejar `flex-wrap` del nombre en varias líneas (cambia la altura de la lista).

### 13.5 Pruebas (e2e, primero en rojo; datos `PRUEBA`)
En `notebooks-fuentes.spec.js`, escritorio y 616 px (usar `irAlPanel` en 616):
- **RF-19.116:** una fuente cuyo nombre interno tiene 150 caracteres + `.txt` (se sube con `subirYProcesar`): al pasar el mouse (`hover`) y al enfocar (`focus`) aparece un `role=tooltip` con el nombre completo; se cierra con Escape y al salir; una Procesado muestra además «Haga clic para ver el archivo original».
- **RNF-04.101:** `scrollWidth <= clientWidth` del panel de Fuentes con ese nombre, y la caja del aviso dentro de la ventana.
- **RF-19.117:** una subida en curso con nombre largo: se usa la retención de ingesta del control de la instancia (`control.ingesta({retener: …})`, la misma que usa `RA-02.49`) para mantener la etiqueta visible; comprueba que es una sola línea, que el porcentaje se ve, que no hay barra horizontal y que el aviso muestra el nombre completo.
- **RF-19.118:** nombre con `<b>x</b>` (permitido por la 009): el aviso lo muestra como texto, sin elementos `b`.
- **No automatizable:** la sensación de «sin retraso» (se verifica a mano) y la apariencia del aviso.

### 13.6 Verificación manual (Andrés)
A 1366 y 616 px: subir un archivo de nombre muy largo; ver que la etiqueta de subida no genera barra y que el aviso muestra el nombre completo al pasar el mouse; en la lista de fuentes, pasar el mouse y usar Tab sobre un nombre cortado; consola limpia.

### 13.7 Documentación
RNF-04 del ERS (una frase) y HU-NUEVA-5; sin cambios en casos de uso, diagramas ni Modelo Relacional.

---

## 14. Cambio II1 — vista previa de todos los formatos permitidos (12/11/2026)
Cubre la sección G de la spec: RF-18.100 a RF-18.108, RNF-07.102, HU-NUEVA-6. Aprobado por Andrés el 12/11/2026 (incluye TIFF y la dependencia Pillow). Cambia RF-18 del ERS. Sin migración. Grafo atrasado: los símbolos se confirmaron con `Grep` y `Read`.

**Idea en una frase**: la ruta actual de la vista previa (`/archivo`) no cambia (imagen, PDF y, ahora, audio). Dos funciones nuevas del servidor devuelven la **vista de texto** (TXT, Word, HTML; con Tika para los que no son texto plano) y la **vista de imagen** (TIFF convertido a PNG); la ventana de la interfaz decide qué pedir y cómo mostrarlo.

Nota (FFF1, 12/11/2026): el RTF dejó de ser un formato permitido (spec 006, RF-05.52): la vista de texto es de TXT, Word y HTML.

### 14.1 Archivos y responsabilidades
| Archivo (símbolo, `archivo:línea`) | Cambio | Requisitos |
|---|---|---|
| **Nuevo** `backend/app/services/vista_previa_service.py` | `VistaPreviaService`: `vista_de_texto(ruta, extension) -> (texto, truncado)` y `vista_de_imagen(ruta) -> (png_base64, paginas)`. Texto plano: lee como máximo 1 MiB de bytes y decodifica en UTF-8 con reemplazo. Word/HTML: usa `TikaService.extract_text` (`ingesta/tika_service.py:111`) con `enable_ocr=False`, `timeout=60` y `max_retries=1` fijados en la instancia (sin tocar `tika_service.py`), dentro de `run_in_threadpool` (es síncrono). Corta a 200.000 caracteres. TIFF: Pillow abre, toma el primer cuadro, reduce a 4000 px por lado y guarda PNG. Errores propios: `VistaNoDisponible`. | RF-18.100, 18.106, 18.107, 18.108 |
| `backend/app/routes/notebooks.py:235` `ver_archivo_documento_notebook` | **Sin cambios** (RF-18.1 sigue byte a byte, audio incluido: `audio/mp4`, `audio/x-wav`, `audio/mpeg`, `audio/ogg`). | RF-18.101 |
| `backend/app/routes/notebooks.py` (junto a la anterior) | **Dos rutas nuevas** `GET /notebooks/{id}/documentos/{id}/vista-texto` y `.../vista-imagen`, con `require_usuario_judicial`, la misma verificación que la ruta actual (`notebook_service.obtener_archivo_de_documento:412`, que da el 404 uniforme, `DocumentoSinProcesar` y `ArchivoNoEncontrado`), y el servicio de vista previa. Responden JSON: `{"texto": str, "truncado": bool}` y `{"imagen": "<base64 PNG>", "paginas": int}`. Error de la vista: 500 con «No se pudo mostrar el documento. Intente de nuevo.» sin texto de excepción. Router delgado: sin repositorios. | RF-18.106, 18.107, 18.108, RNF-07.102 |
| `backend/app/services/bitacora/notebooks_audit_service.py:171,195` | Se reutilizan `registrar_previsualizacion` y `registrar_previsualizacion_fallida` (motivos nuevos fijos: «no se pudo extraer el texto», «no se pudo convertir la imagen»; clasificación «interno»). Sin tipo de acción nuevo. | RF-21, RNF-07.24 |
| `backend/requirements.txt` ⚠️ | Se agrega `Pillow` con versión fija. Reconstruir la imagen (`docker compose build backend`, luego `up -d backend celery-worker`). | RF-18.108 |
| `frontend/services/notebookService.js:83` `obtenerArchivoPreview` | Se mantiene; **nuevos** `obtenerVistaTexto(notebookId, documentoId)` y `obtenerVistaImagen(...)` (GET con `httpService`, JSON). | RF-18.106, 18.108 |
| `frontend/pages/notebooks/index.js:314` `handleVerArchivo` y `:833-846` (el `Modal` de la vista previa) | `handleVerArchivo` elige el modo por la extensión de la fuente (`doc.extension`): `.txt`, `.doc`, `.docx`, `.html`, `.htm`, `.xhtml` → vista de texto; `.tif`, `.tiff` → vista de imagen; el resto → `/archivo` como hoy. El `Modal` muestra: `audio/*` → `<audio controls preload="metadata" src=…>` (sin `autoPlay`; `onError` → «Su navegador no puede reproducir este audio.»); texto → `<pre class="whitespace-pre-wrap break-words max-h-[70vh] overflow-auto">` con el texto como hijo (nunca HTML), la línea «Vista de texto: no conserva el formato ni las imágenes del original.» (Word, HTML) y los avisos de corte, vacío y primera página; imagen → `<img>` del PNG. Al cerrar, el `<audio>` se desmonta (se detiene) y se libera la URL (`cerrarPreview`). Textos nuevos en 14.4. | RF-18.100 a 18.108 |
| `frontend/e2e/flujos/notebooks.spec.js:265` | La prueba `RF-18.40 · tipo sin vista previa` usaba un `.txt`, que ahora sí tiene vista previa: se actualiza (no se borra) a «`.txt` se muestra como texto» (RF-18.100). | RF-18.100 |
| **Nuevos** `backend/tests/integracion/test_vista_previa.py`, `backend/tests/unitarias/test_vista_previa_service.py`; en `frontend/e2e/flujos/notebooks-fuentes.spec.js` (o `notebooks.spec.js`) pruebas e2e | Ver 14.5. | todos |

### 14.2 Lógica por capa
- **Router** (`notebooks.py`): valida rol y pertenencia; llama al servicio; traduce errores; registra bitácora.
- **Servicio de notebooks** (`notebook_service`): sin cambio; entrega `(notebook, documento, ruta)` o el 404 uniforme / 400 sin procesar.
- **Servicio de vista previa** (nuevo): lee el archivo del disco y produce el texto o el PNG. **Externos:** disco (`uploads/`), Apache Tika (solo Word y HTML). No intervienen SQL Server (más allá de la verificación existente), Qdrant, Ollama, Redis ni HTR.

### 14.3 Flujo
```
pulsar fuente Procesado (doc.extension):
  .txt .doc .docx .html .htm .xhtml → GET .../vista-texto  → {texto, truncado}
  .tif .tiff                              → GET .../vista-imagen → {imagen, paginas}
  otro (pdf, jpg, png, bmp, audio)        → GET .../archivo       (como hoy) → blob.type

vista_de_texto(ruta, ext):
  si ext == .txt: bytes = leer(ruta, 1 MiB); texto = bytes.decode(utf-8, reemplazo)
  si no: texto = Tika.extract_text(archivo, ocr=False, timeout=60, reintentos=1)
  si texto.strip() == "": texto = ""  (la interfaz dice «no tiene texto que mostrar» / «archivo vacío»)
  truncado = len(texto) > 200000 ; texto = texto[:200000]

vista_de_imagen(ruta): Pillow abre; n = paginas; primer cuadro; reducir a ≤ 4000 px; PNG; base64
cualquier fallo → VistaNoDisponible → 500 + bitácora «fallida (interno)»
```
Modal: audio → reproductor del navegador; error del audio → aviso; cerrar → se desmonta.

### 14.4 Interfaz y mensajes (español, sin voseo; RT-07)
Roles: solo Usuario Gubernamental (como la ruta actual); el Administrador queda rechazado (RN-03). Textos nuevos: «Se muestran los primeros 200.000 caracteres del archivo.», «El archivo está vacío.», «El documento no tiene texto que mostrar.», «Vista de texto: no conserva el formato ni las imágenes del original.», «Su navegador no puede reproducir este audio.», «No se pudo mostrar el documento. Intente de nuevo.», «Se muestra la primera página.». La ventana cabe a 1366 y 616 px (`size="3xl"`, texto con desplazamiento interno). `ROUTE_PERMISSIONS`: sin cambios.

### 14.5 Pruebas (primero en rojo; entorno aislado, datos `PRUEBA`)
**Unitarias** (`test_vista_previa_service.py`; Tika simulado con un servidor falso y archivos en `tmp`): texto plano UTF-8 y Latin-1 (con reemplazo); corte a 200.000 y bandera `truncado`; vacío; el TIFF de 1 y de 3 páginas (se genera con Pillow en la prueba) devuelve PNG de la primera y `paginas`; TIFF dañado → `VistaNoDisponible`; un `.html` con `<script>` devuelve su texto, nunca el HTML (RF-18.106, RNF-07.102).

**Integración** (`test_vista_previa.py`: API real, SQL Server, Tika y archivos reales del entorno aislado; Ollama simulado):
- `.txt`, `.html` y un `.docx` (se arma en la prueba con `zipfile`, sin dependencias) inventados devuelven su texto por `vista-texto` (RF-18.100, 18.106).
- `.html` con `<script>alert(1)</script>`: la respuesta contiene el texto visible y nunca las etiquetas (RF-18.106).
- Texto de más de 200.000 caracteres → `truncado: true` y longitud 200.000 (RF-18.100).
- TIFF de 1 y 3 páginas → `imagen` PNG válido (cabecera `\x89PNG`) y `paginas` 1 y 3 (RF-18.108).
- Ajeno, inexistente, quitado, de un notebook eliminado, Administrador y sin token: igual que RF-18.1 (404 uniforme, 403, 401) en las dos rutas; Pendiente: 400 como la ruta actual (RNF-07.102).
- Tika detenido (se hace fallar el servicio) → 500 con el mensaje exacto y sin texto de excepción, y una fila de bitácora de previsualización fallida «interno» sin nombre ni ruta (RF-18.107, RF-21).
- La bitácora registra la previsualización exitosa de cada ruta sin texto del archivo (RNF-07.24).
- La ruta `/archivo` de un `.m4a`/`.wav` sigue entregando el archivo byte a byte con su tipo (RF-18.101, RF-18.1).
- Se actualizan (no se borran): las pruebas de RF-18.1 solo se revisan, no cambian.

**e2e** (`notebooks-fuentes.spec.js` u otro archivo de vista previa; escritorio y 616 px con `irAlPanel`): `.txt` con saltos de línea se ve como texto y con `<script>` escrito literal (RF-18.100); texto largo con su aviso; `.html` con la línea «Vista de texto…» y sin ejecutar nada (RF-18.106); audio `.wav` inventado (cabecera WAV con 2 s de silencio, generado por la prueba): ventana con `<audio controls>`, `paused` verdadero (sin reproducción automática), `duration` ≈ 2 s, `currentTime` se puede adelantar, y tras cerrar la ventana no queda ningún `<audio>` en la página (RF-18.101, 18.102); Tika caído no se prueba en e2e. Se actualiza `RF-18.40 · tipo sin vista previa`. Riesgo a verificar: que el audio simulado de la instancia deje el `.wav` en Procesado (RNF-09.40).
**No automatizable de forma fiable:** el formato `m:ss`/`h:mm:ss` y el aspecto del reproductor (son del navegador, dentro de su propio árbol); RF-18.103 (códec no admitido) y la reproducción real del `.m4a` (Chromium de Playwright no trae el códec AAC); RF-18.104 (el aviso de «tipo sin vista previa»: ningún formato permitido por RF-05 lo dispara). Se cubren con la verificación manual y con la revisión del código.

### 14.6 Decisiones técnicas
- **D1. `.txt` también por `vista-texto` (servidor) y no leyendo el blob en el navegador.** El servidor lee a lo sumo 1 MiB de un archivo que puede pesar 1 GB; el navegador tendría que descargarlo entero. Alternativa descartada: `blob.text()` en el cliente.
- **D2. Word/HTML con Tika en texto plano.** Reutiliza el extractor de la ingesta y no agrega servicios. Alternativas descartadas: LibreOffice a PDF (servicio nuevo, imagen pesada, no aprobado); renderizar el HTML de Tika (superficie de ataque: habría que sanear); `mammoth.js` en el navegador (solo `.docx`, dependencia nueva).
- **D3. Rutas nuevas en lugar de cambiar `/archivo`.** RF-18.1 exige el archivo «tal cual» y sus pruebas lo comprueban byte a byte. Alternativa descartada: un parámetro `?modo=` en la ruta actual (mezcla dos contratos).
- **D4. Las dos vistas responden JSON.** El PNG iría en base64 para llevar el número de páginas, porque CORS (`main.py:195`) no expone cabeceras personalizadas. Alternativa descartada: PNG con cabecera `X-Paginas` (haría falta `expose_headers`).
- **D5. TIFF reducido a 4000 px por lado.** Acota memoria y tamaño de la respuesta. Alternativa descartada: convertir sin límite (un escaneo grande puede agotar memoria; Pillow además corta las «bombas de descompresión» y eso se trata como fallo de RF-18.107).
- **D6. Tika con `timeout=30` y 2 intentos para la vista previa** (cambio del 12/11: antes 60 s y 1 intento; un solo intento fallaba si Tika estaba reiniciándose tras un archivo dañado). La ingesta usa 600 s y 3 reintentos con esperas (10 y 20 s), demasiado para una persona esperando. Se fijan en la instancia sin tocar `tika_service.py`. Alternativa descartada: agregar parámetros a `extract_text`.
- **D7. Reproductor nativo `<audio controls>`.** Da barra, tiempo transcurrido, duración (`m:ss`, y `h:mm:ss` desde una hora), volumen y teclado. Alternativa descartada: uno propio (más código, accesibilidad y pruebas, sin beneficio).
- **D8. Audio por blob completo (sin streaming).** Un `<audio src>` no puede enviar el `Authorization`. Alternativa descartada: URL firmada temporal con `Range` (superficie de seguridad nueva).
- **D9. Modo decidido por la extensión de la fuente.** `doc.extension` ya llega en la lista y evita una petición previa; el servidor vuelve a validar el tipo. Alternativa descartada: pedir `/archivo` primero y decidir por `blob.type` (descarga archivos grandes inútilmente).

### 14.7 Verificación manual (Andrés, en persona)
1. Reconstruir la imagen y reiniciar: `docker compose build backend`, `docker compose up -d backend celery-worker`; `docker compose exec backend python -c "import PIL"` sin error; backend sano.
2. En un notebook `PRUEBA`, subir y abrir: un `.txt`, un `.docx`, un `.html` (con un `<script>` escrito dentro), un `.tif` (idealmente de 2 páginas), un `.wav` o `.m4a`, un PDF y una imagen. Cada uno se ve como describe la spec; el `.html` muestra solo texto.
3. Audio: reproducir, pausar, arrastrar la barra adelante y atrás, ver el tiempo transcurrido y la duración; cerrar con el audio sonando (se detiene).
4. Casos de error: detener Tika (`docker compose stop tika`), abrir un Word (aviso de RF-18.107), volver a levantarlo; abrir un Word con contraseña o dañado.
5. 1366 y 616 px, consola limpia; la acción de previsualizar aparece en el Historial.
6. Limpiar los datos de prueba.

### 14.8 Documentación (última tarea) ⚠️
- **ERS:** RF-18 (hoy «imagen o PDF», con el audio y Word excluidos), con su «Estado actual»; RF-05 sin cambios; versión nueva.
- **HU-18** (criterios), **CU-12** (flujo y alternativas; Tika como actor secundario de la vista de texto) y su diagrama; **Arquitectura C4** si registra dependencias del backend (Pillow).
- **Modelo Relacional:** sin cambios. `CLAUDE.md`/constitución: sin cambios.
- Después, `graphify update .`, el mapa y `MEMORY.md`.

### 14.9 Riesgos y orden sugerido
- **Riesgo principal:** Tika con documentos grandes o con contraseña (tarda o falla): acotado por el plazo de 60 s y el aviso de RF-18.107. **Otro:** `.m4a` en navegadores sin AAC (aviso de RF-18.103).
- **Orden** (lo detallará `tasks.md`): HH1 en la interfaz → servicio de vista previa y rutas de texto → Pillow y vista de imagen → modal de la interfaz (texto, audio, imagen, avisos) → verificación completa y documentación.
