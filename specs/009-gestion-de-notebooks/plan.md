# Plan 009 — Gestión de notebooks: renombrar y eliminar
Spec aprobada el 05/11/2026 (incluida D4, RF-17.93 opción a). Grafo del 04/11 (commit f0125e4): lo posterior se confirmó con `Grep`.

## 1. Archivos y responsabilidades

Existentes (símbolo y `archivo:línea` confirmados):
- `backend/app/db/models/notebook.py:48` `T_Notebook`: columna nueva `CF_Fecha_eliminacion` (DateTime, admite NULL). RN-01.80.
- `backend/app/repositories/notebook_repository.py`: `listar_por_usuario` (:49) y `obtener_por_id` (:59) filtran activos; nuevos `renombrar`, `marcar_eliminado`, `como_lo_guarda_la_base`. RF-17.80, 17.87, 17.88, 17.93.
- `backend/app/services/notebook_service.py:170` `NotebookService`: `crear_notebook` (:178) aplica las reglas; nuevos `validar_nombre` (función de módulo), `renombrar_notebook`, `eliminar_notebook`, `conversacion_disponible`. RF-17.80-17.93.
- `backend/app/routes/notebooks.py`: `crear_notebook` (:76) registra el rechazo; rutas nuevas `PUT /notebooks/{notebook_id}` y `DELETE /notebooks/{notebook_id}`. RF-17, RNF-07.80, RF-21.81-83.
- `backend/app/services/bitacora/notebooks_audit_service.py:42`: nuevos `registrar_creacion_fallida`, `registrar_renombrado`, `registrar_eliminacion`; reutiliza `registrar_intento_fallido` (:181). RF-21.81-83.
- `backend/app/constants/tipos_accion.py:64`: `RENOMBRAR_NOTEBOOK = 19`, `ELIMINAR_NOTEBOOK = 20` y sus descripciones (:108). RF-21.80.
- `backend/app/routes/bitacora.py:97` y `:223`: `tipoAccion` pasa de `le=18` a `le=20`. RF-21.80.
- `backend/app/routes/rag.py:380`, `:435`, `:485` (detalle, borrar, restaurar conversación): añaden `conversacion_disponible`. RF-17.88.
- `backend/tests/soporte/inventario_rutas.py:204-208`: clasificar las dos rutas nuevas (si no, falla `test_inventario_rutas.py`).
- `frontend/services/notebookService.js`: `renombrarNotebook` (`httpService.put`) y `eliminarNotebook`; devuelven `status` en el error.
- `frontend/pages/notebooks/index.js`: lista (:407-425), creación (:97) con mensaje de rechazo, `ConfirmModal` de eliminar (patrón de :172-182 y :616).
- `frontend/common/tiposAccion.js:23-24` y `frontend/services/bitacoraService.js:298-299`: tipos 19 y 20.
- `frontend/e2e/soporte/pantallas.js:39` `listaDeNotebooks`: el selector `div.overflow-y-auto.space-y-1 > button` cambia porque cada fila deja de ser un botón suelto (ver §5).

Nuevos ⚠️ (crear archivos, «Pregunta antes»):
- `backend/alembic/versions/<rev>_eliminacion_logica_notebooks.py` (migración).
- `backend/tests/unitarias/test_nombre_notebook.py` y `backend/tests/integracion/test_gestion_notebooks.py`.
- `frontend/components/notebooks/ItemNotebook.jsx` (fila con nombre, renombrar en línea y eliminar).
- `frontend/e2e/flujos/notebooks-gestion.spec.js`.

## 2. Lógica por capa

**Repositorio** (solo SQL Server):
- `listar_por_usuario` y `obtener_por_id` añaden `CF_Fecha_eliminacion IS NULL`. Así el eliminado deja de existir para todo lo que ya los usa (§3).
- `renombrar(db, notebook, nombre)`: asigna y `commit`; `rollback` y relanza si falla.
- `marcar_eliminado(db, notebook)`: `CF_Fecha_eliminacion = datetime.utcnow()` (misma convención que `crear`, :33) y `commit`; `rollback` si falla. No toca nada más.
- `como_lo_guarda_la_base(db, nombre)`: `select(literal(nombre, T_Notebook.CT_Nombre.type))`, igual que `ExpedienteRepository.como_lo_guarda_la_base` (`expediente_repository.py:71`). Solo lectura.

**Servicio**:
```
validar_nombre(nombre) -> str normalizado | NombreNoValido(motivo, mensaje)   # pura, sin base
  n = NFC(nombre).strip()
  si todos los caracteres de n son espacio o categoría Cf → «nombre vacío», RF-17.81
  si len(n) > 150 → «nombre demasiado largo», RF-17.82
  devuelve n

_nombre_admitido(db, usuario, n, propio=None)
  si repo.como_lo_guarda_la_base(db, n) != n → «nombre con caracteres no admitidos», RF-17.93
  si propio y n == propio.CT_Nombre → SinCambios (RF-17.83, antes del duplicado)
  si n.casefold() in {x.CT_Nombre.casefold() for x in repo.listar_por_usuario(db, usuario) if x is not propio}
     → «nombre duplicado», RF-17.84 (solo activos propios, RNF-07.82)

crear_notebook: n = validar_nombre; _nombre_admitido; repo.crear(n)              # RF-17.85
renombrar_notebook(db, texto_id, nombre, usuario) -> (notebook, cambiado)
  nb = _notebook_de_texto(db, texto_id, usuario)   # RecursoNoDisponible ANTES de validar (RNF-07.80)
  n = validar_nombre; _nombre_admitido(propio=nb) → SinCambios ⇒ (nb, False)
  repo.renombrar(nb, n) ⇒ (nb, True)
eliminar_notebook(db, texto_id, usuario) -> nb: _notebook_de_texto; repo.marcar_eliminado
_notebook_de_texto: id = id_de_notebook(texto_id) (:99); None u obtener_notebook_de_usuario None → RecursoNoDisponible(MOTIVO_NOTEBOOK_NO_DISPONIBLE)
conversacion_disponible(db, session_id, usuario) -> bool
  m = re.match(r"session_notebook_([0-9]+)_", session_id); sin m → True
  return await obtener_notebook_para_chat(db, m.group(1), usuario) is not None
```
- `NombreNoValido(motivo, mensaje)` es una excepción nueva del servicio; su `mensaje` es el `detail` exacto de la spec y el `motivo`, el fijo de RF-21.81.
- Los mensajes: «El nombre del notebook no puede estar vacío» (sin punto, el de hoy), «El nombre no puede superar 150 caracteres.», «El nombre contiene caracteres no admitidos.», «Ya tiene un notebook con ese nombre.».

**Router** (`routes/notebooks.py`, delgado):
- `POST ""`: `NombreNoValido` → `registrar_creacion_fallida(motivo, "validacion")` + 400 `detail=mensaje`; otra excepción → `registrar_creacion_fallida("error inesperado", "interno")` + 500 «Error interno del servidor» (traza sin texto, como :93).
- `PUT /{notebook_id}` (`notebook_id: str`, cuerpo `NotebookRenombrarRequest{nombre: str}` sin `max_length`, RF-17.82) → `NotebookResponse`.
  - `RecursoNoDisponible` → `_no_encontrado(..., TiposAccion.RENOMBRAR_NOTEBOOK)` (:118): 404 «Notebook no encontrado» + intento.
  - `NombreNoValido` → `registrar_renombrado(clave, exito=False, motivo, "validacion")` + 400.
  - Sin cambios → 200 sin fila. Error inesperado → fila «error inesperado»/«interno» + 500 «Error interno del servidor».
- `DELETE /{notebook_id}` (`str`) → `NotebookEliminadoRespuesta{mensaje, id}`; mismas ramas de 404 y 500 con `ELIMINAR_NOTEBOOK`.
- Los esquemas nuevos van en el mismo archivo, junto a `NotebookCrearRequest` (:56).

**Identificador canónico (RF-11.32)**:
- Rutas nuevas: `notebook_id: str` y `id_de_notebook` en el servicio, así `abc`, `05`, `+5`, ` 5 `, dígitos Unicode y el desborde dan el 404 uniforme con su intento, nunca 422.
- Rutas existentes (`/{notebook_id}/documentos…`, :129, :151, :186) siguen con `notebook_id: int` y el rango de `_notebook_o_no_disponible` (:199). Hoy `05` se lee como 5 y `abc` da 422: fuera de alcance, queda como hallazgo en `MEMORY.md` (cambiarlo alteraría pruebas de la 004b).

## 3. Dónde se filtran los activos (RF-17.88)
- `NotebookRepository.listar_por_usuario`: la lista (RF-17.88 a) y `ids_documentos_visibles` (`notebook_service.py:365`), que oculta los fragmentos del eliminado en el chat general y en temas similares del dueño.
- `NotebookRepository.obtener_por_id` → `obtener_notebook_de_usuario` (:285), del que dependen:
  - `_notebook_o_no_disponible` (:199): listar, previsualizar y quitar documentos;
  - `obtener_notebook_para_chat` (:294): chat del notebook;
  - `clasificar_clave` (:304): carga (`routes/ingesta.py:217`), chat por tema (`rag.py:146`) y resumen y similares (`similarity.py:88`);
  - `file_management_service.py:250`: descarga por ruta `uploads/NB-<id>/…`.
- Se filtra en el repositorio y no en el servicio: las unitarias simulan `obtener_por_id` y `listar_por_usuario` con `SimpleNamespace` sin la columna nueva (`tests/unitarias/test_aislamiento_notebooks.py:22,48,59`). Descartado: comprobar el atributo en el servicio.
- Conversación: el prefijo `session_notebook_<id>_` es el que ya reconoce `ConversationStore._tramo_de_usuario` (`session_store.py:397`). `conversacion_disponible` se suma a `es_propia` en `rag.py:380`, `:435` y `:485`: si es False, mismo intento (`_registrar_intento_de_conversacion`) y mismo 404. Las conversaciones de prueba existentes usan notebooks propios y activos (`test_conversaciones_propias.py:145,189,302`).
- Estadísticas (RF-23, ingesta): no usan estos métodos; siguen contando (fuera de alcance).
- Ingesta en curso: el Worker no consulta el notebook; un documento Pendiente termina igual y queda oculto por `ids_documentos_visibles`.

## 4. Datos — migración ⚠️ (RN-01.80, RF-21.80)
- Una migración, `down_revision = 'b7c4d2e9f013'` (cabeza actual).
- Se genera con el modelo ya cambiado: `docker compose exec backend alembic revision --autogenerate -m "eliminacion logica de notebooks"`.
- Revisión del archivo generado, antes de aplicarlo:
  1. deja solo `op.add_column('T_Notebook', sa.Column('CF_Fecha_eliminacion', sa.DateTime(), nullable=True))`;
  2. borra cualquier otra diferencia que detecte (índices, intercalaciones, tipos de otras tablas);
  3. añade el `op.execute` de los tipos 19 «Renombrar Notebook» y 20 «Eliminar Notebook», copiando el patrón de `b7c4d2e9f013` (`IDENTITY_INSERT` y `WHERE NOT EXISTS`).
- `downgrade`: `THROW` si hay notebooks con fecha de eliminación o filas de bitácora con 19 o 20 (RN-01); si no, borra los tipos y la columna.
- Se aplica a desarrollo con `docker compose exec backend alembic upgrade head` y se comprueba con `alembic current`. Las suites lo aplican solas (`tests/soporte/entorno.py:190`).
- Datos existentes: la columna queda NULL, todos los notebooks siguen activos, los nombres repetidos no se tocan.
- Sin cambios en Qdrant ni Redis.

## 5. Interfaz (Usuario Gubernamental; `/notebooks` ya está en `ROUTE_PERMISSIONS`)
- `ItemNotebook.jsx`: una fila `div` con el botón del nombre (`truncate`, `min-w-0`, `title` con el nombre completo) y, a la derecha (`shrink-0`), dos botones de ícono `aria-label` «Renombrar notebook» y «Eliminar notebook». RNF-04.80.
- Renombrar en línea: un `Input` con el nombre, «Guardar» y «Cancelar»; Enter guarda y Escape cancela sin llamar al servidor.
  - El campo no lleva `maxLength`, para que se vea el 400 de 151 (RF-17.82).
  - La validación es del servidor: el vacío también se envía, para mostrar su mensaje (RF-17.81).
  - 400: el `detail` bajo el campo (`errorMessage`). 200: nombre nuevo en la fila y en el encabezado si está abierto, mismo orden.
- Eliminar: `ConfirmModal` «Eliminar notebook», con el nombre y el aviso de que deja de estar disponible con sus documentos y su conversación; «Eliminar» y «Cancelar».
  - Envío único con una `ref`, como `confirmacionRef` (:172-182).
  - Al confirmar: se quita de la lista. Si estaba abierto: `cancelarEnCurso()` sin guardar en `sessionStorage`, se borra su entrada guardada, `notebookActivo = null` y aviso «Notebook eliminado.». RF-17.89.
- Errores: 500 → `Toast.error` «No se pudo renombrar el notebook. Intente de nuevo.» o «No se pudo eliminar el notebook. Intente de nuevo.» (RF-17.90). 404 → se quita de la lista y aviso «El notebook ya no está disponible.» (RF-17.92).
- Crear: hoy un rechazo no muestra nada (:102); ahora el `detail` del 400 queda bajo el campo de creación. El vacío se sigue bloqueando sin llamar (la prueba RF-17.40 «nombre vacío» lo exige, `notebooks.spec.js:82`).
- `pantallas.js:39`: `listaDeNotebooks` pasa a `div.overflow-y-auto.space-y-1 > div > button:first-child`, para que `toHaveText(nombre)` siga leyendo solo el nombre.
- Spec 009b (fuentes): este plan no toca los chips de documentos (:430-560), ni `listarDocumentos`, ni las rutas `/{id}/documentos…`. `validar_nombre` recibe el nombre ya leído y no depende del notebook, para que la 009b la reutilice al renombrar una fuente. Sus tipos de bitácora seguirán desde el 21, con su migración encadenada tras esta.
- Textos en español, sin voseo (RT-07.80).

## 6. Bitácora (RF-21)
| Acción | Tipo | Tema | `info_adicional` |
|---|---|---|---|
| Crear con éxito | 16 | `NB-<id>` | sin cambios (`registrar_creacion`, :74) |
| Crear rechazado | 16 | ninguno | `resultado: error`, `motivo`, `tipo_error: validacion/interno` |
| Renombrar | 19 | `NB-<id>` | `resultado: exitoso/error`, `motivo` y `tipo_error` si falla |
| Eliminar | 20 | `NB-<id>` | ídem |
| No disponible | 19/20 | ninguno | `registrar_intento_fallido`: «notebook no disponible», `acceso` |
- Nunca el nombre anterior ni el nuevo (RNF-07.24): se prueba con un nombre de persona inventado.
- Renombrar sin cambios no deja fila (RF-17.83). Si `BitacoraService.registrar` falla, cada método devuelve None y la acción sigue (RF-21.83; fixture `bitacora_que_falla`).

## 7. Decisiones
1. Filtrar activos en el repositorio (`obtener_por_id`, `listar_por_usuario`); descartado: en el servicio (rompe las simulaciones unitarias).
2. Lo no admitido se pregunta a la base (`literal` con el tipo de la columna); descartado: `encode("cp1252")` en Python (supone la intercalación).
3. Duplicados con `casefold()` en Python sobre los activos propios; descartado: comparar en SQL (la intercalación ignora espacios finales y depende de la base).
4. `PUT /notebooks/{id}` (ya existe `httpService.put`) y `DELETE /notebooks/{id}`; descartado: `PATCH` (no hay `httpService.patch`).
5. Rutas nuevas con `notebook_id: str` + `id_de_notebook`; descartado: cambiar las existentes en esta spec.
6. Conversación: no disponible si el notebook de su prefijo no es activo y propio; descartado: solo si está eliminado (necesitaría leer eliminados y otro método).
7. Esquemas en `routes/notebooks.py`, como los existentes; descartado: `schemas/notebook_schemas.py` (archivo nuevo sin necesidad).
8. `ItemNotebook.jsx` aparte; descartado: todo en `index.js` (~630 líneas).
9. Sin índice único (D2).

## 8. Fixtures y pruebas existentes que cambian (RF-17.91)
- Alcance confirmado: `usuario_gubernamental` (`tests/soporte/datos.py:629`), `administrador` (:623), `sesion` (`tests/integracion/conftest.py:113`) y `ajeno_ligero` (:175) son de función. Cada prueba tiene su propio usuario y la limpieza es por prueba.
  - Los nombres fijos («PRUEBA notebook propio», «notebook del otro», «notebook de B») solo chocan si UNA prueba crea dos con el mismo usuario y el mismo nombre.
  - T2 lo comprueba con `Grep` (pruebas que usan `ajeno`/`ajeno_ligero` y además llaman a `crear_notebook` con «notebook propio» y la misma `sesion`). Si aparece, se agrega un sufijo `uuid` al nombre, sin cambiar lo que la prueba comprueba.
  - `crear_notebook_de_prueba` ya numera (`flujos.py:83`). En `inventario_rutas.py:204` («PRUEBA notebook»), revisar si un mismo usuario lo crea dos veces.
- Cambios de expectativa (no se borra ninguna):
  - `test_crear_con_error_inesperado_es_generico` (`integracion/test_aislamiento_notebooks.py:1112`): `foto_de_efectos` ya no queda igual: hay exactamente una fila nueva, tipo 16, sin tema, `resultado: error`, `motivo: error inesperado`, `tipo_error: interno`, sin la ruta. El 400 del vacío pasa a comparar el `detail` exacto y deja su fila. Docstring actualizado.
  - Catálogo: `test_aislamiento_notebooks.py:689-693` (rango 1-20, tipos 19 y 20), `:729-730` (el rechazado pasa de 19 a 21) y `test_usuarios_de_prueba.py:216` (18 → 20).

## 9. Pruebas por requisito
**Unitarias** (`test_nombre_notebook.py`, base y bitácora simuladas):
- `test_validar_nombre_*` (RF-17.81, 17.82): vacío, espacios, solo U+200B, 150/151, NFC «Cafe»+U+0301 = «Café», recorte.
- `test_admitido_*` (RF-17.93, 17.83, 17.84, RNF-07.82):
  - no admitido (con `como_lo_guarda_la_base` simulado);
  - idéntico → sin cambios; solo mayúsculas → cambia;
  - duplicado con otra grafía de mayúsculas o espacios; «Café» ≠ «Cafe»;
  - eliminado y ajeno no cuentan;
  - el orden de las validaciones.
- `test_renombrar_y_eliminar_no_disponible_antes_de_validar` (RNF-07.80): `abc`, `05`, `+5`, enorme, ajeno, eliminado; nombre inválido a la vez.
- `test_conversacion_disponible` (RF-17.88).
- `test_registro_sin_nombres_y_motivos_fijos`, `test_bitacora_que_falla_no_cambia_la_accion` (RF-21.81-83).

**Integración** (`test_gestion_notebooks.py`, usuarios `PRUEBA` A y B):
- `test_migracion_tipos_y_columna` (RF-21.80, RN-01.80): tipos 19 y 20; un notebook sin fecha es activo; filtro de 19 y 20 en `/bitacora/registros` y en el historial propio.
- `test_renombrar_propio` y `test_eliminar_propio_conserva_todo` (RF-17.80, 17.87): 200; fila con marca y fecha; documento, archivo y conteo de puntos en Qdrant iguales.
- `test_crear_y_renombrar_rechazados` (RF-17.81, 17.82, 17.84, 17.85, 21.81): `detail` exacto, sin cambios y con su fila. El nombre de un eliminado de A y el de un notebook de B se permiten.
- `test_nombre_no_latino_y_latino_con_tildes` (RF-17.93): 150 no latinos → 400, nunca 500; 150 con tildes → se guarda igual.
- `test_no_disponible_404_uniforme` (RNF-07.80, 21.82): de A desde B, inexistente, eliminado, `abc`, `05`, `+5`, enorme → mismo cuerpo, una fila de intento. Administrador → 403 (RNF-07.81).
- `test_eliminado_no_disponible_en_toda_via` (RF-17.88):
  - fuera de la lista; documentos, previsualizar, quitar, carga y chat → 404;
  - su conversación (detalle, restaurar, borrar) → 404;
  - `NB-<id>` en el chat por tema y en similares → trato de no disponible;
  - sus puntos siguen en Qdrant y no llegan al modelo simulado (chat general) ni a similares del dueño.
- `test_eliminar_con_documento_pendiente` (RF-17.88, caso límite): `encolado_interceptado` + `procesamiento_en_prueba`.
- `test_error_inesperado_renombrar_y_eliminar` (RF-17.90): repositorio que lanza → 500 genérico, sin cambios, fila «interno».
- `test_bitacora_por_accion` (RF-21.81-83): una fila por acción; sin nombres (persona inventada); idéntico sin fila; con `bitacora_que_falla` la respuesta no cambia.

**Extremo a extremo** (`notebooks-gestion.spec.js`, 1366 y 616 px):
- Básicas (T5):
  - `RF-17.80 · renombrar, cancelar y Escape`;
  - `RF-17.81 · RF-17.82 · RF-17.84 · rechazos al renombrar` (vacío, 151, duplicado);
  - `RF-17.85 · crear con nombre duplicado`;
  - `RF-17.86 · RF-17.87 · eliminar: cancelar y confirmar`;
  - `RF-17.89 · el abierto se cierra`.
  - El Administrador ya está cubierto por `acceso.spec.js:80` (no se duplica).
- Diferibles (T6; si no se hacen, exención y verificación manual de Andrés):
  - `RF-17.86 · doble clic envía una sola solicitud` (cuenta los `DELETE`);
  - `RF-17.89 · respuesta retenida no se guarda` (`control.motor({ retener_tras })`);
  - `RF-17.92 · otra pestaña` (fixture `otraPestana`);
  - `RNF-04.80 · 150 caracteres sin desborde` (`scrollWidth <= clientWidth` de la lista, a 616).

**Exentos de automatizar**: el aspecto visual (principio 4). Lo revisa Andrés en persona.

## 10. Verificación manual (Andrés, en persona; los implementers no usan `chrome-devtools`)
- Implementer:
  - `docker compose exec backend alembic current` en la nueva cabeza;
  - `docker compose ps` sin reinicios; `docker compose logs --tail 100 backend` sin errores;
  - `curl http://localhost:6333/collections` responde.
- Andrés, a 1366 y 616 px, con la consola sin errores:
  - como Usuario Gubernamental, renombra, ve los cuatro rechazos y elimina uno abierto y otro cerrado;
  - como Administrador, `/notebooks` está rechazado por el menú y escribiendo la ruta;
  - en el Historial ve «Renombrar Notebook» y «Eliminar Notebook».
- Fragmentos del eliminado: `curl` a Qdrant con el filtro `metadata.numero_expediente = NB-<id>` sigue devolviendo puntos.
- Limpieza: notebooks `PRUEBA 009 …` eliminados desde la interfaz (sin borrado físico, RN-01).

## 11. Documentación (T7) ⚠️
- ERS:
  - RF-17: renombrar, eliminar y reglas del nombre al crear;
  - RF-21: tipos 19 y 20 y creación rechazada registrada;
  - RNF-10: eliminación lógica del notebook.
- Casos de Uso: CU nuevo «Gestionar un notebook» (renombrar y eliminar) y CU-11 FE-01 con las reglas nuevas.
- Historias de Usuario: HU-NUEVA-1 y HU-NUEVA-2.
- Modelo Relacional: `T_Notebook.CF_Fecha_eliminacion` y tipos 19-20.
- Edición sobre una copia del `.docx` fuera del proyecto, solo `word/document.xml` (`MEMORY.md`). Los PDF los exporta Andrés.
- Además: `MEMORY.md` y `graphify-out/` (`graphify update .` por `python.exe` de uv, `generar_mapa.py`, `generar_mapa_pruebas.py`).
