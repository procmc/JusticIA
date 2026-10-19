# Plan — Spec 004: Red de seguridad del backend (flujos críticos con pytest)
Estado: aprobado (15/10/2026)

> Retroactiva: solo pruebas, **salvo el bloque F** (tareas 9a-9d, código de producción del backend y del frontend). La 004a está cerrada (14/10). La 004 se commitea entera al terminar (lo hace @committer con aprobación de Andrés, nunca push). Los `xfail` llevan «<requisito> · <módulo>» y nunca una ruta. Líneas verificadas en `fase4` el 15/10/2026 (MCP de graphify sin conexión: ubicadas con `Grep`); revisarlas al empezar cada tarea.

Historial:
- 12/10/2026 — creado desde la spec aprobada (12/10): 14 tareas, dependencias y olas.
- 15/10/2026 — al día con la spec aprobada el 15/10: bloque F (9a-9d, 18 tareas), notebook propio en T1, inventario con avatares, línea base de 1326 pruebas, exención temporal hasta la 005, §16 revisado.
- 15/10/2026 — §16 resuelto por Andrés (1 B, 2 A, 4 B, 5 A, 6 A).
- 15/10/2026: aprobado por Andrés con las tareas ⚠️ (T1, T2, T3, T5, T8, 9a, 9c, T10, T11, T14). Implementación desde T1 en una sesión nueva.

## 1. Punto de partida (lo que las pruebas van a encontrar)
- **Sesión** (`backend/app/routes/auth.py`): `login` (93), `logout` (146; toma el usuario del cuerpo), `refresh-token` (175; solo valida la firma), `cambiar-contrasenna` (261; sin token). Token: `create_token` con `JWT_EXPIRE_MINUTES` (`app/auth/jwt_auth.py`). La contraseña se compara solo si el correo existe (`services/auth_service.py`).
- **Ingesta** (`routes/ingesta.py:164-254`): por archivo, `guardar_archivo` y `procesar_archivo_celery.delay(tema, archivo_info, usuario)`; un rechazo entra en `task_ids` como `{"error": True, "message": <aviso>}` en su posición.
  - Solo el nombre no válido deja fila de rechazo (214-217). La carga iniciada se registra siempre y cuenta `len(files)` (224-231). `message` y `total_files` cuentan todos (233-238).
  - La tarea (`celery_tasks.py:100-310`) usa `asyncio.run`: no puede correr dentro del bucle de la petición. El progreso vive en `task_progress:<id>` del Redis simulado; `schedule_task_cleanup` lanza hilos que duermen minutos.
- **Avisos del guardado** (`services/documentos/file_management_service.py`): `MENSAJE_NOMBRE_NO_VALIDO` (57), `MENSAJE_NO_SE_PUDO_GUARDAR` (58), «El archivo está vacío» como literal (184, 278).
- **Bitácora de ingesta** (`services/bitacora/ingesta_audit_service.py`): `registrar_ingesta` (86; guarda `task_id`, `expediente`, `archivo`, `fase`, `documento_id`, `error_details`), `registrar_carga_rechazada` (149; solo `motivo`), `registrar_almacenamiento_vectorial` (186; `documento_id`, `num_chunks`, `fase="vectorstore_exitoso"`).
  - Fases que existen: `iniciado` (ruta), `inicio`, `completado`, `error` (`celery_tasks.py:201, 228, 298`; `document_processor.py:195`), `cancelado`, `error_cancelacion` (`ingesta.py:315, 344`), «Error general» con `task_id="N/A"` (247).
- **Bitácora completa**: `GET /bitacora/registros` (`routes/bitacora.py:94-151`) → `bitacora_stats_service.obtener_con_filtros` (`bitacora_stats_service.py:98-163`), que **traga** las excepciones y devuelve una lista vacía; si algo falla fuera, el 500 lleva `str(e)` (150). `_expandir_registro` (686) arma cada fila; lo comparten `mi-historial` (231) y `expediente/{n}` (261). Fechas guardadas en UTC sin zona (`bitacora_repository.py:243`).
- **Chat** (`routes/rag.py`): `POST /rag/consulta-con-historial-stream` con `expediente_number` o `notebook_id`; 500 con `str(e)`. Conversaciones en `ConversationStore` + Redis simulado.
- **Notebooks** (`routes/notebooks.py`): crear (66), listar (82), documentos (112), previsualizar (136; 400 si no está Procesado), quitar (161; traga el `OSError` del archivo). `NotebookRepository.crear` (`repositories/notebook_repository.py:27`).
- **Frontend**: Ingesta (`hooks/ingesta-datos/useFileUploadProcess.js:363-425`) muestra «Subida iniciada» antes de la respuesta, marca todo «procesando» y consulta el progreso de cada posición, también de los rechazados. El notebook (`pages/notebooks/index.js:201-217`) hace lo mismo. El detalle de la bitácora (`components/administracion/bitacora/DetalleEvento.jsx:98-112, 186-212`) dice «Expediente» y pinta `InformacionAdicionalRenderer`.
- **Soporte de la 002/004a**: limpieza y residuos por el prefijo `PRUEBA` (`tests/soporte/datos.py:53-67, 289-380`): no alcanzan un tema heredado, `NB-<id>`, sus puntos ni las conversaciones. `celery_inmediato` (`simulados.py:350`), `carpeta_archivos` (416), `ollama_simulado` (856; registra cada contexto), `htr_simulado` (867). Modelos: `encoladas` y `_cargar` en `tests/integracion/test_carga_confinada.py:35-57`; JWT inventados en `test_humo.py`.

## 2. Archivos (⚠️ = nuevo)
Pruebas, en `backend/tests/` (agrupadas por bloque, §16.1 = B):
| Archivo | Tareas | Requisitos |
|---|---|---|
| `soporte/datos.py`, `../conftest.py`, `unitarias/test_datos.py` (casos nuevos) | T1 | RA-02.14 |
| ⚠️ `soporte/flujos.py`, ⚠️ `integracion/test_soporte_flujos.py` | T1 | RA-02.13, RA-02.14, RNF-09.1 |
| ⚠️ `soporte/inventario_rutas.py`, ⚠️ `unitarias/test_inventario_rutas.py` | T2 | RA-02.12 |
| ⚠️ `integracion/test_red_acceso.py` | T3, T4 | RNF-07.5, RF-02.3 |
| ⚠️ `integracion/test_red_sesion.py`, ⚠️ `unitarias/test_red_sesion.py` | T5, T6, T7 | RF-01.1-01.6, RF-21.7 |
| ⚠️ `integracion/test_red_ingesta.py` | T8, T9 | RF-05.1, RF-06.1, RF-06.2, RF-07.1, RF-07.2, RF-08.1, RF-21.7 |
| ⚠️ `integracion/test_red_cargas_rechazadas.py`; `integracion/test_carga_confinada.py` (ajuste, §16.5) | 9a, 9b | RF-05.22, RF-05.23 |
| ⚠️ `unitarias/test_detalle_carga.py`, ⚠️ `integracion/test_red_detalle_bitacora.py` | 9c | RF-22.1 |
| ⚠️ `integracion/test_red_chat.py` | T10 | RF-11.1, RF-11.2, RF-12.1, RF-21.7, RNF-09.1 |
| ⚠️ `integracion/test_red_notebooks.py` | T11, T12, T13 | RF-17.1-17.4, RF-18.1, RF-11.3, RNF-07.6, RF-19.1, RF-19.2 |

Producción (solo bloque F):
| Archivo | Tarea | Cambio |
|---|---|---|
| `backend/app/routes/ingesta.py` | 9a | aceptados, rechazados, confirmación; carga iniciada solo con aceptados; fila por rechazo |
| `backend/app/services/bitacora/ingesta_audit_service.py` | 9a | `MOTIVOS_DE_RECHAZO`; `registrar_ingesta` con `archivos_aceptados`/`archivos_rechazados`; `registrar_carga_rechazada(tipo_error=…)` |
| `backend/app/services/documentos/file_management_service.py` | 9a | constante `MENSAJE_ARCHIVO_VACIO` (mismo texto) |
| `frontend/hooks/ingesta-datos/useFileUploadProcess.js`, `components/ingesta-datos/FilesList.jsx`, `utils/ingesta-datos/iconos.js`, `pages/notebooks/index.js` | 9b | aviso por respuesta, estado «Rechazado», sin aviso previo |
| ⚠️ `backend/app/services/bitacora/detalle_carga.py` | 9c | `clasificar_causa`, `armar_detalle_carga` (funciones puras) |
| `backend/app/services/bitacora/bitacora_stats_service.py`, `backend/app/routes/bitacora.py` | 9c | `obtener_bitacora_completa`; 500 genérico |
| `frontend/services/bitacoraService.js`, `components/administracion/bitacora/DetalleEvento.jsx` | 9d | `detalleCarga`; sustitución; encabezado «Tema» |

Sin cambios en `main.py`, `celery_app.py`, `requirements.txt`, `package.json`, `docker-compose.yml`, Alembic, prompts ni modelos. Solo T1 edita `tests/soporte/` y `conftest.py`; solo T2 el inventario.

## 3. Soporte de los flujos (T1; RA-02.13, RA-02.14)
- `encolado_interceptado`: reemplaza con `monkeypatch` el `.delay` (modelo: `encoladas` de la 004a); guarda `(tema, archivo_info, usuario)`, devuelve `id` `PRUEBA-tarea-<n>` y expone `pendientes`.
- `procesamiento_en_prueba` (usa el anterior, `celery_inmediato`, `carpeta_archivos`, `embeddings_reales`, `htr_simulado`, `audio_simulado`): `procesar()` ejecuta cada pendiente con `procesar_archivo_celery.apply(args, task_id=id, throw=False)` **desde el hilo de la prueba**. `schedule_task_cleanup` → función vacía.
- Sin pausas: `exigir_estado(id_documento, estado)` y `exigir_progreso(id_tarea, estado)` miran una vez y fallan con «se esperaba <estado> y se encontró <x>».
- `documento_de_prueba()`: `PRUEBA_<uuid8>.txt` con una frase distintiva única. `tema_heredado(registro)`: número en formato heredado, registrado.
- `notebook_de_prueba` (RA-02.13 c): crea con `NotebookRepository.crear` un notebook `PRUEBA` de un usuario `PRUEBA` y registra su `NB-<id>`. `crear_notebook(cliente, cabeceras, nombre, registro)`: por la API (lo usa T11).
- `cargar(cliente, cabeceras, tema, archivos)` (modelo `_cargar`), `leer_eventos(respuesta)`, `contexto_enviado(ollama_simulado)`.
- `foto_de_efectos()`: filas de T_Bitacora, T_Documento, T_Expediente, T_Notebook; puntos; archivos de la carpeta temporal; correos. Para «sin efectos».
- `datos.py`: `Registro.temas` + `registrar_tema`. La limpieza borra, en orden de claves foráneas, lo asociado a los temas registrados (bitácora, relaciones, documentos, temas) y sus puntos (`metadata.numero_expediente`); vacía del `ConversationStore` las sesiones de usuarios `PRUEBA`.
- Residuos: T_Expediente, T_Expediente_Documento, T_Documento y T_Notebook cuentan **todas** las filas (la base nace vacía); se suman las conversaciones en memoria.

## 4. Inventario de rutas (T2; RA-02.12, base de T3 y T4)
- `rutas_registradas(app)`: `(método, plantilla)` de cada `APIRoute`, `Mount` y ruta del framework (`/docs`, `/redoc`, `/openapi.json`, `/docs/oauth2-redirect`); sin `HEAD`/`OPTIONS` implícitos, salvo el `HEAD` explícito de avatares.
- `CLASIFICACION`: por `(método, plantilla)`: `clase` (pública · pública deliberada · cualquier sesión · Administrador · Usuario Gubernamental · protegida), `grupo`, `flujo_critico`, `ejemplo` (datos válidos `PRUEBA`) y `estado_actual` (etiqueta de `xfail`; nunca la ruta).
- `GET` y `HEAD /uploads/profiles/{nombre}`: **pública deliberada** (RF-04.20, RNF-07.22; excepción documentada a RNF-07.5). T3 no la recorre; su comportamiento lo cubren las pruebas de la 004a.
- RF-22.1 no añade rutas: su lista viaja en `GET /bitacora/registros`, ya clasificada (Administrador).
- Prueba: compara los dos conjuntos y nombra la ruta que sobra o falta; su rojo, con una ruta de ejemplo en una copia de la aplicación. Ids neutros (`<grupo>-<n>`).

## 5. Flujo de las pruebas (pseudocódigo)
```
RNF-07.5 (T3): por cada entrada no pública ni pública deliberada × {sin token, inválido, vencido, otra clave}:
    r = pedir(método, ejemplo válido, siguiendo 307) → 401, sin contenido, foto igual; estado_actual → xfail
    OPTIONS: sin contenido ni efecto · 405 no cuenta · 422 solo con datos inválidos y sin efecto
RF-02.3 (T4): cada entrada con flujo_critico, token del otro rol → 403 y foto igual
Ingesta (T8): sube 1-2 documentos (tema heredado) → ids; encolado: sin documento ni puntos → procesar() →
    Procesado; progreso 100 %; nº puntos = nº de «Documento almacenado» (>0), dim 1024, metadatos; 2.ª carga sin duplicar
Chat (T10): temas A y B procesados → acotado a A con la frase de B → sin ella; general → con ella; eventos; fila
Notebook (T11-T13): crear → subir con NB-<id> → procesar → listar/previsualizar → chat → quitar
```
Carga con rechazos (9a, `routes/ingesta.py`):
```
por cada (posición p desde 1, archivo):
    intento: guardar; tarea = delay(...) → task_ids += tarea.id; aceptados += {posicion: p, id_tarea}
    HTTPException e → task_ids += {"error": True, "message": e.detail}  (igual que hoy)
        motivo = MOTIVOS_DE_RECHAZO.get(e.detail, "error interno"); rechazados += {posicion: p, motivo}; fila de rechazo
    otra excepción → logger.exception; task_ids += {... "Error interno del servidor"}; motivo «error interno»; fila
si aceptados: registrar_ingesta(fase="iniciado", filename=f"{n} archivo(s)", archivos_aceptados=n, archivos_rechazados=r)
devuelve {message: confirmación(n), task_ids, expediente, total_files: n,
          aceptados: {cantidad, tareas: [{posicion, id_tarea}]}, rechazados: {cantidad, archivos: [{posicion, motivo}]}}
```
- `confirmación(n)`: n = 1 → «1 archivo enviado a procesamiento»; n > 1 → «<n> archivos enviados a procesamiento»; n = 0 → «No se aceptó ningún archivo. Revise el motivo de cada uno.» (texto de CU-07 paso 7 al cierre).
- `MOTIVOS_DE_RECHAZO`: «Nombre de archivo no válido» → «nombre de archivo no válido»; «El archivo está vacío» → «archivo vacío»; «No se pudo guardar el archivo» → «no se pudo guardar el archivo».
- Tema no válido: sin cambios (400 y su fila «tema no válido»). El `except` general (500 y «Error general») no cambia.

Detalle de la bitácora (9c, `detalle_carga.py`):
```
tipo(info): fase iniciado→«Carga iniciada» · inicio→«Inicio del procesamiento» · vectorstore_exitoso→«Documento almacenado»
    · completado→«Procesamiento terminado» · error→«Error de procesamiento» · tiene motivo, sin fase→«Carga rechazada»
    · cancelado→«Cancelación» · error_cancelacion→«Error de cancelación» · otra→«Otra fase»
datos en el orden de la tabla de RF-22.1; se omite toda etiqueta sin valor o con relleno:
    Tema = info.expediente salvo «N/A»/vacío · Archivo = info.archivo salvo «Error general» o «Task …»
    Archivos aceptados / rechazados (este solo si > 0) · Documento = documento_id · Fragmentos = num_chunks
    Causa = clasificar_causa(error_details) · Motivo = motivo si ∈ lista cerrada, si no «error interno»
    Fecha y hora = CF_Fecha_hora (UTC) → hora de Costa Rica, «dd/mm/aaaa hh:mm:ss»
clasificar_causa(crudo): regla de la spec (Definiciones), en minúsculas, gana la primera; vacío → «error interno»
obtener_bitacora_completa(...): repo.obtener_con_filtros sin tragar excepciones; a cada fila de CARGA_DOCUMENTOS
    añade detalle_carga = {tipo, datos: [{etiqueta, valor}]}; las demás, igual que _expandir_registro
GET /bitacora/registros: usa obtener_bitacora_completa; except → logger.exception; 500 «Error interno del servidor»
```
Frontend (9b, 9d):
```
Ingesta, por tema: sin «Subida iniciada»; filas en «pendiente» con los controles deshabilitados mientras sube
    respuesta → task_ids[i] texto: «procesando» y progreso (como hoy) · objeto: estado «rechazado», mensaje = motivo de su posición
    un aviso por respuesta junto al tema: éxito si aceptados.cantidad > 0, si no advertencia; texto = message + «<nombre local>: <motivo>»
Notebook: igual; los rechazados no entran en archivosSubiendo ni se consultan
DetalleEvento: «Tema» / «Sin tema asociado»; valor = registro.expediente o el «Tema» de detalleCarga.datos;
    con detalleCarga: descripción = detalleCarga.tipo y lista etiqueta: valor en lugar de InformacionAdicionalRenderer
```

## 6. Datos
Sin migración ni esquema. Todo vive en `servia_pruebas` (base y colección), la carpeta temporal y el Redis simulado; `uploads/` y el Redis de desarrollo no se tocan (se cuentan antes y después). Claves: `metadata.numero_expediente`, `metadata.nombre_archivo`, `metadata.id_documento`.
- La bitácora gana dos claves opcionales en `CT_Informacion_adicional` de la carga iniciada (`archivos_aceptados`, `archivos_rechazados`) y `tipo_error` en los rechazos; las filas anteriores siguen válidas (sus etiquetas se omiten).
- Borrado físico solo de lo que crea la suite (excepción de RN-01).

## 7. Interfaz y roles
- Sin `ROUTE_PERMISSIONS` ni páginas nuevas. Ingesta y NotebookServIA: Usuario Gubernamental; detalle de la bitácora: Administrador (sin cambios de acceso).
- Mensajes nuevos en español: confirmación (§5), motivos de «Causa clasificada», estado «Rechazado», etiquetas de RF-22.1.
- **Consumidores de la carga** (RF-05.22): `ingestaService.subirArchivos` (`services/ingestaService.js:98-137`) → `useFileUploadProcess.js:379-404` y `pages/notebooks/index.js:204-212`; ambos usan `task_ids` por posición. Nadie lee `message` ni `total_files`.
- **Consumidores de `GET /bitacora/registros`** (RF-22.1): `bitacoraService.obtenerRegistros` → `_mapearRegistros` (225; arma el objeto campo a campo) → `Bitacora.jsx` (tabla, `DetalleEvento`, exportación a PDF con `exportService.js`). `mi-historial` y `expediente/{n}` siguen en `obtener_con_filtros`.

## 8. Bitácora (RF-21)
- RF-21.7 dentro de T5-T10: fila por usuario y tipo (con tema si aplica), sin exigir un número exacto por carga; ninguna fila con contraseña ni token. Lo que falte, `xfail` «RF-21.x · bitácora» por separado.
- Bloque F (9a): carga iniciada solo con ≥ 1 aceptado, contándolos; una fila de rechazo por archivo con su motivo, sin nombre ni tema. Sin constantes nuevas de `TiposAccion` (sigue `CARGA_DOCUMENTOS`). Si el registro falla, la carga continúa (como hoy).

## 9. Decisiones (con la alternativa descartada)
1. **Procesar fuera del bucle de la petición** (interceptar `.delay` y ejecutar desde la prueba). Descartado: Celery inmediato en la ruta (choca con `asyncio.run`) y worker real (rompe el aislamiento).
2. **Residuos por tabla completa** en temas, documentos y notebooks. Descartado: contar por prefijo (no alcanza el formato heredado ni `NB-<id>`).
3. **Clasificación con su `estado_actual` en la tabla**. Descartado: lista aparte de rutas que fallan (duplica la tabla y nombra rutas).
4. **Fallos provocados con `monkeypatch`**, sin detener servicios:
   - extracción (RF-07.2): `extract_text_from_file` lanza «Error extrayendo texto: …» solo para el archivo marcado;
   - fragmentos y archivo (RF-19.2); conexión del LLM (RF-11.2);
   - guardado fallido (9a): `_get_unique_filename` lanza `OSError` para el nombre marcado, antes de escribir (como la 004a);
   - error interno (9a): `guardar_archivo` lanza `RuntimeError` para el nombre marcado, antes de escribir;
   - consulta de la bitácora (9c): `BitacoraRepository.obtener_con_filtros` lanza un `RuntimeError` con una ruta inventada.
   - Ninguno deja archivo; aun así la prueba compara la carpeta antes y después y registra cualquier residuo para borrarlo. Descartado: hacer fallar el encolado (deja el archivo guardado, hallazgo excluido).
5. **Tiempo de RF-01.2 estructural** (contar comparaciones de hash). Descartado: medir tiempos en la suite (inestable).
6. **Notebook propio por repositorio** (T1). Descartado: por la API (un fallo de RF-17.1 rompería RF-05.22).
7. **La confirmación viaja en `message`** (excepción de la spec). Descartado: un campo `confirmacion` duplicado.
8. **`obtener_bitacora_completa` nueva** para la bitácora completa. Descartado: tocar `obtener_con_filtros` (cambiaría `mi-historial`, `expediente/{n}` y las estadísticas, que deben quedar igual).
9. **El repositorio que falla da 500** (hoy 200 con lista vacía). Descartado: probar solo el `except` de la ruta (un fallo real de la base seguiría sin verse).
10. **Hora de Costa Rica con desplazamiento fijo UTC−6** (sin horario de verano desde 1992). Descartado: `zoneinfo` (puede exigir `tzdata`, dependencia nueva).
11. **Estado «Rechazado» propio** en la lista de Ingesta (mismo ícono y color que «Error»). Descartado: reutilizar «Error» (la spec pide la fila «rechazada»).
12. **Filas en «pendiente» mientras sube**. Descartado: marcarlas «procesando» antes de la respuesta (un rechazado pasaría por «procesando»).
13. **Detalle en `DetalleEvento` sin componente nuevo**. Descartado: un componente aparte (archivo nuevo para una lista simple).

## 10. Trazabilidad requisito → tarea → prueba (se escriben primero)
| Requisito | Tarea | Pruebas | ¿Falla hoy? |
|---|---|---|---|
| RA-02.13, RA-02.14 | T1 | `test_soporte_flujos`: encolado, procesar, notebook propio, residuos (heredado, `NB-<id>`, conversación); `test_datos`: casos nuevos | Sí (no existen) |
| RA-02.12 | T2 | `test_inventario_rutas`: tabla = registradas; rojo con ruta de ejemplo | Sí |
| RNF-07.5 | T3 | `test_red_acceso`: inventario × 4 tokens; casos (a)-(e) | Parcial → `xfail` |
| RF-02.3 | T4 | `test_red_acceso`: flujos críticos con el otro rol | A confirmar |
| RF-01.1, RF-01.2 | T5 | `test_red_sesion` (integración y unitaria) | RF-01.2 sí (motivo, tiempo) |
| RF-01.3, RF-01.6 | T6 | temporal → cambio; cambio con su sesión; dos errores | A confirmar |
| RF-01.5, RF-01.4 | T7 | renovación por rol, 4 inválidos; token cerrado | RF-01.4 sí |
| RF-05.1, RF-06.1, RF-06.2, RF-07.1, RF-08.1 | T8 | `test_red_ingesta`: flujo con tema heredado; tema libre | A confirmar |
| RF-07.2 | T9 | dos documentos, extracción de uno forzada | Sí: progreso y estado Error → `xfail` |
| RF-05.22 | 9a | `test_carga_mixta_a_un_tema`, `…_al_notebook_propio`, `test_lista_de_identificadores_sin_cambios`, `test_guardado_fallido_y_error_interno_con_motivo_y_fila`, `test_todos_rechazados_exito_sin_confirmacion`, `test_tema_no_valido_sin_conteos` | Sí (regresiones de la spec) |
| RF-05.23 | 9a, 9b | `test_contenido_para_la_pantalla` (9a); `test_imagen_pegada_en_el_notebook_llega_a_procesado` (9b) | Sí / caracterización |
| RF-22.1 | 9c | `test_detalle_carga` (cada regla, precedencias, no reconocido, vacío, tabla por tipo, relleno, hora); `test_red_detalle_bitacora` (cada tipo, causa sin excepción, prohibidos, otros consumidores, 500, 403) | Sí |
| RNF-04.1 | 9b, 9d | manual (§11, §12) | — |
| RF-11.1, RF-11.2, RF-12.1 | T10 | `test_red_chat` | RF-11.2 sí |
| RF-17.1, RF-17.2, RF-18.1 | T11 | `test_red_notebooks` | Probable en vacío y «en línea» |
| RF-11.3, RF-17.3, RF-17.4, RNF-07.6 | T12 | `test_red_notebooks` | Sí en conversaciones y carga a ajeno |
| RF-19.1, RF-19.2 | T13 | `test_red_notebooks` | RF-19.2 sí |
| RF-21.7 | T5-T10 | dentro de cada flujo | Parcial |
| RNF-09.1 | T1, T10 | flujos con simulados; `comprobar_simulados` | No |
| RA-02.15 | T14 | duración frente a la línea base; `--durations=25` | — |

- **Otros consumidores sin cambios** (RF-22.1): cada fila de la bitácora completa, sin `detalle_carga`, es igual a `_expandir_registro` de esa fila (así la exportación, que se arma con esos campos, no cambia); `mi-historial`, `expediente/{n}` y una descarga rechazada no traen `detalle_carga`.
- Reglas: `@pytest.mark.requisito("<id>")` y docstring en español; datos `PRUEBA` o temas registrados; ningún `xfail` sin ver el rojo; estricto y con «<requisito> · <módulo>»; no se modifica ninguna prueba existente salvo el ajuste de §16.5.

## 11. Exenciones
- **E0**: lo del navegador (incluido el reintento automático del chat) → spec 005.
- **E1**: calidad real de la respuesta y la cita (RF-11.1) → manual con Ollama real.
- **E2**: tiempos reales de los tres inicios fallidos (RF-01.2) → manual; en la suite, estructural.
- **E3 — exención temporal hasta la 005** (la constitución no cambia): que Ingesta, NotebookServIA y el detalle de la bitácora presenten tal cual lo que entrega el sistema (RF-05.23, RF-22.1, RNF-04.1).
  - Se puede medir de extremo a extremo, así que no es aspecto visual (principio 4). Se acepta porque el extremo a extremo llega con la 005 y la 004 no suma dependencias de JavaScript (principio 1). Aquí: integraciones del contenido + manual.
  - Condición de cierre: la 005 los cubre de extremo a extremo; si no, no se cierran.
  - Regla de estado: la 004 se cierra en T14; los tres quedan «implementados, pendientes de la 005» en `tasks.md` y con «Estado actual» en el ERS.
- **E4**: aspecto visual de RNF-04.1 (principio 4).

## 12. Verificación manual (T14; por la API y, para el bloque F, en el navegador)
Tras `docker compose restart backend celery-worker`: `ps` sin reinicios, `curl :8000/`, logs limpios; `uploads/` y claves del Redis de desarrollo iguales antes y después. Datos inventados; credenciales de Andrés (no se escriben).
1. Subir un texto `PRUEBA` a un tema → Procesado y fragmentos con `metadata.numero_expediente`.
2. Chat con **Ollama real** acotado a ese tema: cita por nombre de archivo y en español; descargar el citado.
3. Notebook `PRUEBA`: crear, subir, chatear, previsualizar y quitar (sin fragmentos, archivo ni registro).
4. Tres inicios fallidos: mismo cuerpo; anotar los tiempos.
5. Bitácora (Administrador): cada paso con su usuario; sin contraseñas ni tokens.
6. Bloque F (navegador, escritorio y 616 px, consola sin errores), lo de RF-05.23, RF-22.1 y RNF-04.1 en la spec:
   - Ingesta y notebook con un válido, uno vacío y uno de nombre no válido; dos temas a la vez; todos rechazados; una imagen pegada y otra arrastrada sobre el chat del notebook.
   - Detalle de un registro de cada tipo, encabezado «Tema» y descripción con el nombre del tipo.
   - El Administrador no entra a Ingesta ni a NotebookServIA; el Usuario Gubernamental no ve la bitácora completa.
7. Limpiar lo creado.

## 13. Orden y paralelismo
- **Ola 1**: T1 · T2 · T5 → T6 → T7. **Ola 2**: T3 (tras T2) → T4 (y T1) · T8 → T9 → 9a → 9b; 9a → 9c → 9d · T10 · T11 → T12 → T13 (tras T1). **Ola 3**: T14.
- 9a necesita T1 (notebook propio, encolado) y T8 (spec: el bloque F va tras la carga); 9c necesita 9a (claves de la carga iniciada y filas de rechazo).
- Dos corridas de pytest a la vez se pisan (misma base `servia_pruebas`): van por turnos que asigna el coordinador (§16.2 = A).
- `MEMORY.md`: una línea al cerrar cada ola y el cierre en T14.

## 14. Riesgos
- Importar `main` en una unitaria (T2) puede chocar con los guardianes: si pasa, va a integración y se anota.
- Memoria y tiempo con embeddings reales y Tika: un solo modelo de sesión, documentos de pocas líneas; medir contra la línea base al cerrar cada ola.
- `search_by_text` cambia según haya documentos Procesados: cada prueba crea los suyos.
- 9a cambia la respuesta y la bitácora de la carga: las pruebas de la 004a deben seguir pasando (§16.5).
- `npm run build` hoy falla por 4 errores de lint heredados en `pages/notebooks/index.js` (MEMORY), que 9b toca (§16.6).
- 9c es la tarea más larga: si pasa de 30 min, se corta entre `detalle_carga.py` con su unitaria y el cableado con su integración.
- Debilidad grave no prevista: se detiene la tarea (decisión 6 de la spec).

## 15. Documentación (T14; la edita otro, no el planner)
- ERS: RF-01 Parcial (RF-01.4); «Estado actual» de RNF-07 y RF-19 coherentes; RA-02 menciona la red; RF-11, RF-12, RF-17 y RF-20 por RF-17.3 y RF-17.4 (visto bueno del tutor).
- ERS RF-05: «Salida» (confirmación de §5, solo aceptados); «Manejo de errores» con «archivo vacío», «no se pudo guardar el archivo» y «error interno» y su fila de rechazo; «Estado actual» (el servidor no valida formato, tipo ni tamaño).
- ERS RF-22 «Detalle» (RF-22.1, encabezado «Tema»). «Estado actual» de RF-05.23, RF-22.1 y RNF-04.1: «implementado; pendiente la verificación de extremo a extremo (spec 005)».
- Casos de Uso: CU-02 (paso 5 y postcondición), CU-07 paso 7 (texto de §5) y FE-03, CU-15 FA-01.
- Grafo y mapas (`graphify update .`, comunidades, `generar_mapa.py`, `generar_mapa_pruebas.py`): el bloque F cambió código. `MEMORY.md`.

## 16. Decisiones de Andrés (resueltas el 15/10/2026)
Resultado: 1 = B · 2 = A · 3 sin objeto · 4 = B · 5 = A · 6 = A. Las opciones quedan abajo como registro.
- 4 = B, regla «por ola» (confirmada el 15/10): `--orden-inverso` en T1 (prueba su propia limpieza), al cerrar cada ola (T7 si cierra la ola 1, T13 si cierra la ola 2, o la última que asigne el coordinador) y en T14.
- Hora del detalle (15/10 = B): 9d solo verifica la hora de Costa Rica (UTC−6 sobre la UTC guardada), sin compararla con el listado. El desfase de 6 h del listado (`utcnow()`) queda fuera de alcance: corrección aparte con su prueba de regresión (pendiente en T14).
- Corrección editorial de «Tareas estimadas» de spec.md (15/10 = A): el planner, a pedido del coordinador, durante T14.
- 6 = A: 9b corrige los 4 errores sin cambiar comportamiento; `npm run build` y `npm run lint` sin errores.

1. **Archivos de prueba**: A) uno por tarea (más archivos nuevos, todas las tareas ⚠️) · B) agrupados por bloque, como en §2 (**recomendada**: las tareas del mismo bloque ya van en orden y las corridas van por turnos, así que A casi no gana paralelismo y suma archivos nuevos).
2. **Corridas en paralelo**: A) un turno a la vez, que asigna el coordinador (**recomendada**) · B) una base y colección por implementador (cambia el soporte de la 002) · C) una copia del entorno por implementador (no cabe en memoria ni GPU).
3. ~~T5-T7 antes de cerrar la 004a~~: sin objeto (la 004a cerró el 14/10).
4. **Evidencia por tarea** (línea base 1326 pruebas; la duración D se mide en T1): A) suite y `--orden-inverso` en cada tarea (≈ 2·D × 18) · B) suite en cada tarea y `--orden-inverso` al cerrar cada ola y en T14 (≈ D × 18 + 3·D; **recomendada**: con D ≈ 5 min, A suma unas 1 h 30 min más).
5. **Ajuste de `test_error_inesperado_es_generico` (004a)**: su segunda parte provoca el 500 haciendo fallar la carga iniciada mientras el encolado sigue fallando; con 9a ya no hay aceptados ni carga iniciada y responde 200. A) restablecer el encolado interceptado antes de esa parte, sin cambiar lo que comprueba (**recomendada**) · B) mantener la carga iniciada sin aceptados (contradice RF-05.22).
6. **Lint heredado de `pages/notebooks/index.js`**: A) corregir sus 4 errores en 9b, sin cambiar comportamiento (**recomendada**: la spec exige `npm run build` y `npm run lint` sin errores) · B) exigir solo «sin errores nuevos» (requiere `/sdd-change`).
