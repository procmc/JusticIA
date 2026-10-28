# Plan — Spec 006: Ingesta de los documentos de Nexus
Estado: implementada (28/10/2026); aprobado (27/10/2026)

> Parte de la spec aprobada el 27/10/2026 (D1-D5, R1-R5, S1-S4, T1-T2; no se reabren). No repite la spec: remite a sus requisitos. Archivos y líneas verificados el 27/10/2026 en la rama `fase4` (grafo del 26/10; pruebas por `Grep`).

Historial:
- 27/10/2026 — creado (fase 3, planner).
- 27/10/2026 — aprobado por Andrés, con sus respuestas a las dos dudas del plan:
  - U1 = A: la clave del notebook **propio** (`NB-<id>`) escrita como tema en Ingesta carga en ese notebook, como hoy (RF-17.4 sin cambios). «El tema indicado no es válido» solo para notebooks ajenos o inexistentes (y > 60 caracteres). Regresión en T4 (§9).
  - U2 = B: el desborde del nombre largo se corrige y prueba solo en Ingesta (RNF-04.50). El mismo desborde en el aviso del notebook se anota en `MEMORY.md` en T9, para la spec de mejoras del notebook.
- 28/10/2026 — corrección T10 (CC1 = A, Andrés): falla de RF-06.53 hallada en la verificación manual de T9 (tema nuevo en dos grafías en un mismo Guardar). §4.6, §8.9 y §9.
- 28/10/2026 — cierre: la spec recoge CC1, CC2 y DD1 en RF-06.53 (sin cambiar este diseño) y las decisiones W1, X1, Y1 y Z1; §10 suma `PRUEBA 3` y el notebook `PRUEBA 006`.

## 1. Enfoque
- Orden por valor (spec, «Orden de trabajo»): **bloque 1** (T1-T5) antes que **bloque 2** (T6-T8); cierre en T9.
- Corte: si tras T5 no caben T6-T8, la spec se cierra con el bloque 1 (§11).
- Pruebas primero, vistas en rojo con su causa anotada; luego el código.
- Archivos de prueba generados en memoria (PDF dañado, PDF sin texto, PNG), con prefijo `PRUEBA_`; ninguno en el repositorio.
- Motores: los simulados de la suite y de la instancia e2e (HTR, LLM); Tika real del entorno aislado.
- **Sin** esquema, migración, dependencia, prompt, modelo, `docker-compose.yml`, `ROUTE_PERMISSIONS` ni renombrar «expediente» en código o base (spec, «Pregunta antes»).

## 2. Archivos
Nuevos (⚠️ crear archivos):

| Archivo | Responsabilidad | Requisitos |
|---|---|---|
| ⚠️ `backend/tests/unitarias/test_ingesta_tema_y_fallo.py` | Unitarias: normalizar tema, mensaje de fallo, apagar rastreo. | RF-06.52, RF-06.53, RF-07.52, RNF-09.50 |
| ⚠️ `frontend/test-results/manual/PRUEBA_*` (temporales, T9) | Archivos inventados de la verificación manual; se borran al terminar. | verificación |

Modificados (backend):

| Archivo (símbolo, línea) | Cambio | Requisitos |
|---|---|---|
| `app/config/config.py` (`load_dotenv`, :5) | `apagar_rastreo_externo()` llamada al importar; config la importan `main.py` (vía `app.*`) y `celery_app.py:86`. | RNF-09.50 |
| `app/routes/ingesta.py` (`ingestar_archivos`, :191-231) | Recorte del tema antes de `clasificar_clave` (:211); tras `validar_tema` (:226), el nombre registrado vía servicio. | RF-06.53 |
| `app/routes/ingesta.py` (`consultar_progreso_tarea`, :139-147) | Rama `FAILURE`: texto fijo en vez de `str(result.info)`. | RF-07.52 |
| `app/services/expediente_service.py` (:90) | `nombre_de_tema_registrado(db, tema)`: el registrado si existe igual salvo mayúsculas; si no, el recibido. T10: pasa a resolver **o crear** el tema (§4.6). | RF-06.53 |
| `app/repositories/expediente_repository.py` (`obtener_por_numero`, :89) | `obtener_por_nombre_sin_mayusculas(db, nombre)`: `func.lower(col) == nombre.lower()`, el de menor id. T10: alta que deja pasar `IntegrityError` (§4.6; `crear`, :113, lo envuelve en `Exception`). | RF-06.53 |
| `app/services/ingesta/file_management/document_processor.py` (`process_single_file_with_content`, :345-561) | Registrar el documento (pasos 1-3, :429-453) **antes** de extraer (:395); validar texto vacío dentro del `try`. | RF-07.2, RF-07.54 |
| idem (:534, :241) y `celery_tasks.py` (:282, :289) | `mark_failed` con texto fijo + causa clasificada; el texto crudo solo a la bitácora y al log. | RF-07.52, RF-21.50 |
| `app/services/ingesta/async_processing/progress_tracker.py` (`ProgressTracker.mark_failed`, :199; `ProgressManager`, :254) | `marcar_fallo(crudo)`; `recordar_documento` / `documento_de_tarea` (clave Redis aparte, §5). | RF-07.52, RF-07.51 |
| `app/services/ingesta/async_processing/celery_tasks.py` (`procesar_archivo_celery`, :99-162, :200) | Sustituye la comprobación muerta de :133-162 por la de §4.3; `registrar_ingesta(... "inicio")` envuelto en `try`. | RF-07.51, RF-21.50 |

Modificados (frontend):

| Archivo (línea) | Cambio | Requisitos |
|---|---|---|
| `hooks/ingesta-datos/useFileUpload.js` (:30-40, :61, :124-146) | Quita el `useEffect` que reescribe los pendientes (hallazgo a); `confirmarTema()`; tipo por extensión. | RF-06.50, RF-05.50 |
| `components/ingesta-datos/ExpedienteInput.jsx` (:30-58, :92, :117-133) | Rótulo «Tema», sin placeholder ni tope (:34-39); Enter/blur → `confirmarTema`; texto de Guardar deshabilitado; quita «Formato requerido». | RF-06.50, RF-06.52, RF-06.54 |
| `components/ingesta-datos/IngestaDatos.jsx` (:3, :47-67, :89-92) | Sin `validarFormatoExpediente` ni `alert`; Guardar deshabilitado solo por `uploading`, sin pendientes o pendiente sin tema. | RF-06.50, RF-06.54 |
| `components/ingesta-datos/DropZone.jsx` (:27-51, :69-74, :94) | Siempre habilitada (sin «Área bloqueada»); formatos con las 6 imágenes; advertencia de manuscrito. | RF-06.50, RF-05.50, RF-10.50 |
| `components/ingesta-datos/FilesList.jsx` (:99-120, :51-54) | Sin campo por fila: solo el chip del tema del archivo; aviso de rechazo sin desborde. | RF-06.50, RNF-04.50 |
| `components/ingesta-datos/UploadConfirmModal.jsx` (:37, :42-53, :62-106) | Agrupado por tema, textos con «tema»; chip «IMAGEN». | RF-06.51, RF-06.54, RF-05.50 |
| `hooks/ingesta-datos/useFileUploadProcess.js` (:154-187, :315-323, :421-439) | Muestra el mensaje del servidor si empieza por el texto fijo; grupo con tema rechazado → `rechazado`; quita `console.error` técnico (:168, :428). | RF-07.50, RF-06.52 |
| `services/ingestaService.js` (`subirArchivos`, :98-136) | Error con `temaNoValido` si 404 o 400 con «El tema indicado no es válido». | RF-06.52 |
| `utils/ingesta-datos/ingestaUtils.js` (:8-33) y `iconos.js` (:10-12) | `imagenes` en `tiposArchivo`, `obtenerTipoArchivo` → `image`; ícono de imagen. | RF-05.50 |
| `pages/notebooks/index.js` (:372-390) | Advertencia de manuscrito junto a «Subir documentos». | RF-10.50 |

Pruebas modificadas: `tests/integracion/test_red_ingesta.py`, `test_red_cargas_rechazadas.py`, `test_red_notebooks.py`, `tests/unitarias/test_confinamiento_rutas.py` (si ahí está `validar_tema`); e2e `soporte/pantallas.js` (:93), `flujos/carga.spec.js`, `flujos/notebooks.spec.js`, `infraestructura/capacidades.spec.js` (:428-433); `tests/instancia_e2e/simulados_e2e.py` (docstring :764).

Sin cambios: `expedienteValidator.js` (lo sigue usando el chat, `messageUtils.js:6`), `file_management_service.py` (salvo que la prueba lo pida), esquema, `.env`.

## 3. Hallazgos del código que el plan corrige o aprovecha
- (a) `useFileUpload.js:30-40` reescribe el tema de todos los pendientes al cambiar el campo: causa del hallazgo a.
- (b) `document_processor.py:395-402` extrae **antes** de crear el documento (:431): un fallo de extracción no deja fila; el archivo ya guardado por la ruta (:245) queda huérfano.
- `celery_tasks.py:141` llama a `doc_repo.buscar_por_nombre_y_expediente`, que **no existe**: el `except` (:159) lo silencia. Esa deduplicación nunca funcionó; §4.3 la sustituye.
- `celery_app.py:105` (`task_acks_late=True`): una tarea puede volver a ejecutarse con el mismo id (motivo de RF-07.51).
- `progress_tracker.py:148/174`: el seguimiento caduca a 1 h; `visibility_timeout` es 7200 s (`celery_app.py:112`).
- La causa clasificada ya existe: `clasificar_causa` (`services/bitacora/detalle_carga.py:69`); se reutiliza.
- `notebook_service.quitar_documento` (:249) ya quita documentos en Error (sin fragmentos = éxito): RF-07.54 sale de RF-07.2.

## 4. Flujos (lo no obvio)
### 4.1 Tema (RF-06.52, RF-06.53)
```
ingestar_archivos(tema, files):
  tema = tema.strip()                                   # RF-06.53, antes de todo
  clasificacion = clasificar_clave(tema)                # RF-17.4 sin cambios (404 ajeno/inexistente; propio -> NB-<id>)
  validar_tema(tema)                                    # 400 «El tema indicado no es válido» (> 60, etc.)
  si no es notebook propio:
    tema = ExpedienteService.nombre_de_tema_registrado(db, tema)   # igual salvo mayúsculas -> el registrado
  guardar_archivo(file, tema); delay(tema, ...)         # carpeta, fila y metadatos con el mismo nombre
```
- Tildes: dependen de la intercalación de SQL Server (R5, comprobación de T1). `func.lower` iguala mayúsculas aunque la columna fuera sensible.
- Varios registrados que difieren solo en mayúsculas (heredados): gana el de menor id.

### 4.2 Fallo del procesamiento (RF-07.2, RF-07.52, RF-21.50)
```
process_single_file_with_content(...):
  si expediente y db:
    documento = documento_previo o crear_documento(Pendiente, ruta=filepath); commit   # antes de extraer
    progress_manager.recordar_documento(task_id, documento.id)
  try:
    texto = extract_text_from_file(...); si vacío -> ValueError("No se pudo extraer texto del archivo")
    store_in_vectorstore(...); estado Procesado; commit
  except e:
    estado Error (commit); tracker.marcar_fallo(str(e)); raise          # el archivo no se borra (RN-01)
marcar_fallo(crudo):
  causa = clasificar_causa(crudo)
  mark_failed("No se pudo procesar el archivo. Por favor, intente nuevamente. Causa: " + causa + ".", error_details=causa)
```
- `celery_tasks.py:286-302` usa también `marcar_fallo`; la fila de bitácora sigue con `error_details=str(e)` (prueba `test_fila_de_error_con_la_causa`).
- Rechazo por validación en segundo plano (`validate_file`, :184) sigue sin fila (R2).

### 4.3 Reintento interno (RF-07.51)
```
procesar_archivo_celery(task_id):
  si seguimiento completado -> devolver previo (:117, se conserva)
  id = progress_manager.documento_de_tarea(task_id)          # clave Redis, TTL 3 h > visibility_timeout
  si id: documento = repo.obtener(id)
    Procesado -> devolver completado, sin fila ni fragmentos
    Error     -> marcar_fallo y terminar sin re-lanzar (sin fila nueva)
    Pendiente -> procesar con documento_previo=documento;
                 si ya hay fragmentos de ese id (get_complete_document_by_chunks) -> no vectorizar, Procesado
```
- Recarga del usuario tras un Error: tarea nueva con id nuevo y nombre único (`_get_unique_filename`) → fila nueva; la anterior queda en Error.

### 4.4 Ingesta: tema por archivo (RF-06.50, RF-06.51)
- Al agregar: `expediente = campo.trim()` (S2, ya en :54). Enter o blur: `confirmarTema()` asigna el texto a los pendientes sin tema.
- Guardar deshabilitado si hay un pendiente sin tema, con «Indique el tema antes de guardar los archivos.» visible.
- Confirmación: grupos `{tema → archivos}`; advertencia «… a su tema permanentemente».
- Subida: ya agrupa por `file.expediente` (`useFileUploadProcess.js:347-366`); el `catch` (:421) con `temaNoValido` → grupo `rechazado`, «El tema indicado no es válido»; los demás grupos siguen.

### 4.5 Error en pantalla e imágenes (RF-07.50, RF-05.50, RF-10.50, RNF-04.50)
- Fila en Error: mensaje del servidor si empieza por el texto fijo; si no, solo el texto fijo. Los contadores ya cuentan `fallido` (`useFileUpload.js:141`).
- Imágenes: `.jpg .jpeg .png .tif .tiff .bmp`; el backend ya las acepta (`file_config.py:27`) y las lleva al HTR (`document_processor.py:619`).
- Advertencia (texto literal de RF-10.50) en la zona de carga de Ingesta y junto a «Subir documentos» del notebook.
- Aviso de rechazo: clases que permitan partir el nombre (`[overflow-wrap:anywhere]`, `min-w-0`) en `FilesList.jsx:51-54`.

### 4.6 Tema nuevo en dos grafías a la vez (RF-06.53; T10)
- Causa (verificada en el código, 28/10): la ruta (`ingesta.py:241-242`) solo **lee** el nombre registrado; el tema se crea en el Worker (`document_processor.py:163`). Una petición que resuelve antes de esa alta conserva su grafía en carpeta, metadatos y bitácora.
- La base ya impide dos filas: `uq_expediente_num` sobre `CT_Num_expediente` con intercalación `CI_AS` (T1) trata «PRUEBA» y «prueba» como iguales. No hace falta esquema ni migración.
```
ingestar_archivos (rama no notebook, en lugar de :241-242):
  tema = ExpedienteService.resolver_o_crear_tema(db, tema)     # antes de guardar archivos y encolar
resolver_o_crear_tema(db, tema):
  registrado = repo.obtener_por_nombre_sin_mayusculas(db, tema)
  si registrado: devolver registrado.CT_Num_expediente
  try: repo.crear_tema(db, tema); commit; devolver tema
  except IntegrityError: rollback; devolver repo.obtener_por_nombre_sin_mayusculas(db, tema).CT_Num_expediente   # ganó la otra petición
```
- El Worker no cambia: `buscar_o_crear_expediente` encuentra la fila y recibe ya el nombre registrado.
- Efecto aceptado (duda CC2): el tema existe desde la carga, antes del procesamiento.

## 5. Datos
- SQL Server: sin cambios de esquema. Nuevo comportamiento: la fila del documento existe desde antes de extraer.
- Redis: clave nueva `ingesta:documento_de_tarea:<task_id>` → id del documento, TTL 10 800 s; solo la usa RF-07.51.
- Qdrant: metadatos sin cambios; `numero_expediente` pasa a ser siempre el nombre registrado.
- Datos existentes: no se migran; temas heredados que difieran solo en mayúsculas se conservan (gana el de menor id).

## 6. Interfaz y roles
- Solo el Usuario Gubernamental usa Ingesta y notebooks (`require_usuario_judicial`, sin cambios); el Administrador no entra (se comprueba en la verificación manual).
- Textos nuevos: «Tema», «Limpiar lista de archivos y tema», «Indique el tema antes de guardar los archivos.», «El tema indicado no es válido», texto fijo de RF-07.52 y advertencia de RF-10.50.

## 7. Bitácora (RF-21)
- Sin tipos de acción nuevos. La fila «error» sigue con tema, usuario y causa cruda (RF-21.50).
- Registro de «inicio» envuelto en `try` (`celery_tasks.py:200`): si la bitácora falla, el procesamiento sigue.

## 8. Decisiones
1. Crear la fila antes de extraer — descartada: crear la fila solo en el `except` (dos caminos de alta y el archivo sin fila durante la extracción).
2. Mensaje = texto fijo + causa en `message` — descartada: causa solo en `error_details` (la ruta de progreso no lo devuelve, :117-124).
3. Deduplicar por clave Redis propia — descartada: columna con el id de tarea (cambio de esquema, fuera de alcance).
4. Pendiente reejecutado: reutilizar la fila y no revectorizar si ya hay fragmentos — descartada: marcarlo Error (perdería un reintento válido).
5. Nombre registrado con `func.lower` en el repositorio — descartada: depender solo de la intercalación (no cubre una columna sensible a mayúsculas).
6. Rastreo apagado en `config.py` al importar — descartada: en `main.py` y `celery_app.py` por separado (dos lugares que mantener).
7. Las 2 pruebas e2e nuevas solo en escritorio con `test.skip(esPantallaPequena(), …)` — descartada: proyecto aparte (más configuración); el orquestador admite omitidas (`ejecutar.mjs:66`).
8. Archivos de prueba en memoria — descartada: archivos en el repositorio.
9. (T10) Crear el tema en la ruta, vía servicio, apoyado en la restricción única existente — descartadas: corregir en el Worker usando el nombre de la fila (la carpeta y la respuesta ya llevan la otra grafía; habría que mover archivos) y un bloqueo en Redis o `sp_getapplock` (más piezas para lo que la restricción ya garantiza).

## 9. Pruebas por requisito

| Requisito | Prueba (tipo, ubicación) |
|---|---|
| RF-06.50, 06.51, 06.52 | e2e `RF-06.50 · Ingesta: un tema por archivo y confirmación agrupada` (escritorio, `carga.spec.js`): A sin tema → texto y Guardar deshabilitado; Enter → A toma el tema 1; B con tema 1; C con tema 2 escrito sin confirmar; D con 61 caracteres; confirmación con 3 grupos; D rechazado; la API lista A y B en tema 1, C en tema 2. `provocado(/400/)`. |
| RF-06.52 | unitaria `test_tema_de_61_caracteres_400`; integración existente `test_tema_libre_se_acepta_y_crea_el_tema` y las de RF-17.4 siguen pasando (`test_carga_propia_en_otra_grafia_usa_la_canonica`, `test_aislamiento_notebooks.py:600`; `test_carga_a_notebook_ajeno_da_404`, `test_red_notebooks.py:379`). |
| RF-17.4 (U1, regresión) | e2e, en la prueba de RF-06.50: un archivo con la clave `NB-<id>` del notebook propio → aceptado y listado en ese notebook; otro con `NB-<id inexistente>` → grupo rechazado con «El tema indicado no es válido». |
| RF-06.53 | integración `test_tema_normalizado_una_carpeta_y_un_valor` (test_red_ingesta.py): «PRUEBA Normativa X», «prueba normativa x», « PRUEBA Normativa X » → 1 tema, 1 carpeta, 1 valor; «PRUEBA Normatíva X» → otro; unitaria del recorte. |
| RF-06.53 (T10, regresión) | integración `test_tema_nuevo_en_dos_grafias_un_solo_nombre` (test_red_ingesta.py): tema nuevo «PRUEBA X…» y «prueba x…» cargados **sin procesar entre medio** (orden del Worker) → 1 fila, 1 carpeta, 1 valor de `metadata.numero_expediente`, `CT_Ruta_archivo` y bitácora con el registrado. Unitaria `test_tema_en_carrera_usa_el_registrado` (test_ingesta_tema_y_fallo.py): alta con `IntegrityError` simulado → rollback y nombre del ganador. `test_carga_encolada_un_id_por_archivo` (:148) fijaba el orden viejo («todavía no hay tema»): pasa a «tema creado, sin documentos». |
| RF-06.54 | e2e, aserción añadida a `RF-05.40 · Ingesta: carga mixta` (ambos anchos): rótulo «Tema», sin «expediente» en la pantalla ni en la confirmación, tema de 3 caracteres habilita Guardar. |
| RF-07.2 | integración `test_documento_queda_en_error` sin `xfail`, parametrizada: PDF dañado, PDF sin texto, imagen sin texto (`htr_simulado.responder("")`), fallo del HTR (`htr_simulado.fallar()`); fila en Error con ruta y archivo en disco, sin puntos. |
| RF-07.52 | integración `test_progreso_con_texto_fijo_y_causa` sin `xfail` (referencia a RF-07.52); unitaria `test_marcar_fallo_texto_fijo_y_causa`; unitaria de la rama `FAILURE` de la ruta. |
| RF-07.50 | e2e `RF-07.50 · Ingesta: fallo en Error con su causa e imagen Procesada` (escritorio): PDF dañado → Error con texto y causa, contador de errores; en el bloque 1 el acompañante es un `.txt`, en T7 pasa a ser la PNG. |
| RF-07.51 | integración `test_reintento_de_la_misma_tarea_una_fila` y `test_recarga_tras_error_fila_nueva`. |
| RF-07.53 | integración `test_cancelacion_queda_cancelada`, `xfail(strict, "RF-07.53 · ingesta")`. |
| RF-07.54 | integración `test_fallo_en_notebook_queda_en_error_y_se_quita` (test_red_notebooks.py); e2e de notebooks intactas. |
| RF-21.50 | integración existente `test_fila_de_error_con_la_causa`; nueva `test_bitacora_caida_documento_igual_en_error` (bitácora `registrar` simulada con fallo). |
| RNF-09.50 | unitarias `test_rastreo_activo_se_apaga_con_aviso`, `test_rastreo_ausente_se_apaga_sin_aviso` (sin valores de claves en el log). |
| RNF-04.50 | e2e, aserción en `RNF-04.40 · aviso accesible y completo` (ambos anchos): `scrollWidth <= clientWidth` en título y lista. Solo Ingesta (U2); el aviso del notebook queda anotado en `MEMORY.md` (T9). |
| RF-10.50 | e2e, aserción en `RF-11.40 · Ingesta: …` y en `RF-05.40 · notebook: carga mixta` (ambos anchos). |
| RF-05.50 | e2e en la prueba de RF-07.50 (PNG Procesada, identificada como imagen, 6 formatos en la lista). |
| RF-05.51 | integración ×3 `xfail(strict, "RF-05.51 · ingesta")` en `test_red_cargas_rechazadas.py`: extensión, MIME real, tamaño (con `file_config.MAX_FILE_SIZE` reducido por `monkeypatch`). |
| RN-01.50 | integración de RF-07.2: el archivo sigue en disco; ninguna prueba nueva borra fuera del entorno aislado. |

- Pruebas que fijaban el defecto (se actualizan, con la referencia RF-07.2): `capacidades.spec.js:428-433` («el documento nunca llega a registrarse» → Error) y la docstring de `simulados_e2e.py:764`. Si aparece otra, se anota y se avisa a Andrés.
- `test_falla_la_vectorizacion_el_documento_queda_en_error[cancelacion]` (:436) no cambia (contradice RF-07.53 a propósito).
- Fallos esperados al cerrar (pytest): línea base de T0 − 2 + 3 + 1 (≈ 45 → 47). E2e: sin fallos esperados nuevos; 2 omitidas nuevas (pequeña).
- Exención: el aspecto visual del aviso y de la advertencia (constitución, principio 4); se mide `scrollWidth` y el texto, no el estilo.

## 10. Presupuesto e2e y verificación manual
- T0: media de dos corridas = **M**. Límite: suite ≤ M + 30 s y ≤ 560 s; 600 s no se sube. Si M > 530 s, PARAR antes de T1.
- Punto de control tras T4, T5, T6 y T7 (las que añaden e2e): si se supera, PARAR y preguntar.
- Manual (T9), en desarrollo, con `PRUEBA` y `PRUEBA 2` (T10: `PRUEBA 3` y `prueba 3`, DD1; notebook `PRUEBA 006`), ambos roles, 1366 y 616 px (`emulate` 1229/554), consola limpia:
  - dos temas en un Guardar; un PDF dañado en Error con su causa; una PNG Procesada; aviso largo sin desborde; advertencia en Ingesta y notebook.
  - SQL Server (fila en Error con ruta), Qdrant (`metadata.numero_expediente`) y bitácora; el Administrador no entra a Ingesta.
  - Andrés revisa el `.env` real del `backend` y del `celery-worker` (RNF-09.50) y reinicia ambos antes.
- Limpieza ⚠️ (solo con aprobación de Andrés en ese momento): documentos, fragmentos y archivos de `PRUEBA`, `PRUEBA 2`, `PRUEBA 3` y del notebook `PRUEBA 006`; los temas quedan vacíos (residuo aceptado, como en la 005b).

## 11. Corte (si el bloque 2 no cabe)
- Se hacen T0-T5 y T9 (≈ 27 h). RF-07.50 queda probado con `.txt` + PDF dañado.
- Quedan para otra spec, con su «Estado actual» en el texto propuesto del ERS: RNF-04.50 (desborde), RF-10.50 (advertencia), RF-05.50 (imágenes en Ingesta), y los `xfail` de RF-05.51 y RF-07.53.
- `DropZone.jsx` no muestra imágenes; el piloto (PDF) no lo necesita.

## 12. Documentación a actualizar (T9)
- Texto propuesto para ERS y CU: el de la spec (no se edita el ERS); con corte, se ajusta según §11.
- Spec 006 → «implementada»; `MEMORY.md` (incluida la línea del desborde en el aviso del notebook, U2); `graphify-out/` (`python.exe` de uv, `generar_mapa.py`, `generar_mapa_pruebas.py`).
- Paso operativo de Andrés tras la validación: piloto de Nexus (cada PDF Procesado o en Error con causa; el chat general cita al menos uno); riesgo RF-06.2 anotado.

## 13. Cobertura
Bloque 1: RF-06.50-54, RF-07.2, RF-07.50-52, RF-07.54, RF-21.50, RNF-09.50, RN-01.50. Bloque 2: RNF-04.50, RF-10.50, RF-05.50, RF-05.51 (xfail), RF-07.53 (xfail). Regresión: RF-06.2 (xfail), RF-08, RF-09, RF-17.4, RF-22. Corrección T10: RF-06.53 (y RF-06.52: regla en el servidor).
