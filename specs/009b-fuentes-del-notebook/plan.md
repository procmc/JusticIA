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
  - `Dropdown` con disparador `aria-label="Opciones de <nombre>"` (`shrink-0`): «Cambiar el nombre» (entrega 2) y «Quitar fuente».
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
- Para el presupuesto (≤ 569 s): solo RNF-04.100 corre a 616 px; las demás, a 1366.
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
