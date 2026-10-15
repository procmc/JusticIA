# Plan — Spec 004a: Correcciones urgentes de seguridad en los archivos de documentos
Estado: implementada (14/10/2026; aprobado el 12/10/2026)

> No se publica hasta que las correcciones estén hechas y validadas; cita archivos y líneas (12/10/2026, rama `fase4`; revisarlas al empezar cada tarea) sin describir cómo aprovechar los fallos. `respaldo/` no se publica y se borra en T7.
> Cumplido el 14/10/2026 (validación APROBADO, `respaldo/` borrada): publicable.

Historial:
- 12/10/2026 — creado junto con la spec y las tareas.
- 12/10/2026 — condensado para ahorrar tokens; versión completa en `respaldo/`.
- 12/10/2026 — revisión del reviewer y decisiones de Andrés (§14): D7-B y RNF-07.24 (sin eco de nombres), no Procesado → 404, notebook contra la base sin distinguir mayúsculas, 255 bytes, reserva `profiles`, causa real del rojo (§9), interfaz de rechazados documentada (§6), T2 y T5 divididas (7 tareas).

## 1. Diagnóstico (`fms` = `backend/app/services/documentos/file_management_service.py`; rutas en `backend/app/`)
- **1. Descarga por ruta** (`routes/archivos.py:248-321`, `fms:136-214`): decodifica otra vez (`263-264`), completa `uploads/…` con la raíz del backend (`266-272`, es decir `/app`) o el directorio de trabajo (`fms:157-160`) y entrega si existe; sin confinar, sin base ni pertenencia. El servicio entregaría una ruta absoluta tal cual, pero por la API toda ruta que no empieza por `uploads/` (p. ej. absoluta) daba 500 por `UnboundLocalError` (un `import os` dentro de un `if` en `archivos.py`).
- **1b. Por tema y nombre** (`archivos.py:145-246`, `fms:216-228` `obtener_ruta_archivo`): decodifica otra vez (`156-157`) y une sin confinar; hoy lo frena `verificar_esta_procesado` (`171`, 400), pero la misma función usan previsualización (`routes/notebooks.py:153`) y borrado (`176-181`).
- **2. Guardado** (`fms:68-134`, `routes/ingesta.py:162-237`): tema (`ingesta.py:164`) y `file.filename` se unen (`fms:87`, `95-96`) y se escribe con `"wb"` (`106-107`).
- **2b. Ruta relativa** (`fms:114-115`): `relative_to(<raíz del backend>)` falla fuera de `/app` (la suite desvía la carpeta: `tests/soporte/simulados.py:390-419`) tras escribir. No afecta a producción.
- **3. Carpeta pública** (`backend/main.py:185-188`): `StaticFiles("uploads")` en `/uploads` sin token; avatares en `/uploads/profiles/<id>.<ext>` (`AVATAR_UPLOAD_DIR`, `constants/avatar_constants.py:26`), pedidos primero con **HEAD** (`frontend/contexts/AvatarContext.jsx:151`). En la suite, la carpeta de avatares es `<temporal>/avatares`, hermana de `uploads` (`simulados.py:401`).
- **Mensajes** con `str(e)`: `archivos.py:243-246`, `318-321`; `fms:130-134`; `ingesta.py:198-205` (devuelve además `filename`), `234-237`. Previsualización: sin `str(e)` (`notebooks.py:155` ya da 404).
- **Bitácora**: `archivos.py:303-305` relanza sin registrar; `archivos_audit_service.py:277-278` clasifica todo lo que no diga «no encontrado» como `interno` y pone el nombre en el texto; `ingesta_audit_service.registrar_ingesta` (`85-145`) pone el nombre en el texto y en `info`.
- **Frontend** (no cambia): cita del chat y temas similares usan `GET /archivos/download?ruta_archivo=…` con token (404 → «El archivo no existe o fue eliminado»); NotebookServIA exige token y pertenencia; nadie pide `/uploads/<tema>/…`. La ruta guardada la arma `services/ingesta/file_management/document_processor.py:209`.

## 2. Archivos
| Archivo | Cambio | Requisitos |
|---|---|---|
| `fms` | Nuevas `es_nombre_seguro`, `validar_tema`, `_ubicacion_confinada`, `obtener_documento_por_ruta`, `_sin_control(texto)`, `AccesoArchivoDenegado(HTTPException)` con `motivo`; `obtener_ruta_archivo`, `guardar_archivo`, `descargar_archivo` según §4. | RNF-07.20, 07.21, 07.23, 07.24, RF-18.20, RF-06.20, RF-05.20, RF-05.21 |
| `routes/archivos.py` | `/download` según §4 (sin `266-272`); por tema y nombre confinada y no Procesado → 404; 500 genérico; auditoría de rechazo solo con motivo. | RNF-07.20, 07.21, 07.23, 07.24, RF-18.20, RF-21.20 |
| `routes/ingesta.py` | `validar_tema` antes del bucle (`185`); rechazo por archivo sin `filename` (`198-205`); 500 genérico (`234-237`). | RF-06.20, RF-05.20, RF-05.21, RF-21.20, RNF-07.23, 07.24 |
| `services/bitacora/archivos_audit_service.py` | Nueva `registrar_descarga_rechazada(db, usuario_id, motivo)`: texto «Descarga rechazada: <motivo>», `tipo_error="acceso"`, sin nombre ni ruta; `_sin_control` en lo que registra. | RF-21.20, RNF-07.24 |
| `services/bitacora/ingesta_audit_service.py` | Nueva `registrar_carga_rechazada(db, usuario_id, motivo)`: texto «Carga rechazada: <motivo>», `tipo_error="validacion"`, sin tema ni nombre. | RF-21.20, RNF-07.24 |
| `routes/notebooks.py` | Sin cambios: hereda el confinamiento; si no es confinable, previsualizar da 404 y quitar borra fragmentos y registro sin tocar el disco. | RNF-07.21 |
| `backend/main.py` | Quita `185-188`; incluye avatares con `prefix="/uploads/profiles"` (D1). | RNF-07.22, RF-04.20 |
| ⚠️ `routes/avatares.py` (nuevo) | `api_route` `GET`/`HEAD` `/{nombre}`; docstring: excepción a «todo endpoint exige rol» y a `prefix="/<modulo>"` (conserva la dirección de hoy), con referencia a la spec de autenticación. | RF-04.20, RNF-07.22 |
| `services/avatar_service.py` | `obtener_ubicacion_avatar_publico(nombre) -> Optional[Path]`: `^[A-Za-z0-9_-]{1,40}` + extensión de `ALLOWED_IMAGE_EXTENSIONS` (`avatar_constants.py:23`), resuelta en `self.upload_dir` por petición, confinada. | RF-04.20 |

⚠️ Pruebas nuevas en `backend/tests/`: `unitarias/test_confinamiento_rutas.py`, `integracion/test_descargas_confinadas.py`, `integracion/test_carga_confinada.py`, `integracion/test_carpeta_publica.py` (§9). No cambian frontend, `docker-compose.yml`, dependencias, esquema, Alembic, Qdrant, Redis, prompts, modelos, `TiposAccion` ni `tests/soporte/` (se usan `carpeta_archivos`, `celery_inmediato` y los usuarios `PRUEBA`).

## 3. Lógica por capa
- **Router**: recibe, llama al servicio, audita con el servicio de su módulo y traduce errores (`AccesoArchivoDenegado` → 404 uniforme; `HTTPException` 400 → su `detail`; otro → 500 genérico + `logger.exception` sin el texto pedido). No toca disco ni repositorios.
- **Servicio**: toda la validación y el confinamiento. Pertenencia con `notebook_service.obtener_notebook_de_usuario(db, id, usuario_id)` (`notebook_service.py:65-72`), importado dentro de la función para evitar ciclos.
- **Repositorio**: sin cambios; `DocumentoRepository.verificar_esta_procesado(db, tema, nombre)` (`documento_repository.py:361`).
- **Externos**: SQL Server y disco. Sin Qdrant, Ollama, Redis ni HTR; el Worker recibe el mismo `archivo_info`.

## 4. Flujo (pseudocódigo)
```
CARPETA_AVATARES = Path(AVATAR_UPLOAD_DIR).name                      # "profiles", constante de producción

es_nombre_seguro(texto, es_tema):
    falso si vacío o solo espacios/puntos; contiene "/", "\", ":", NUL o control; algún componente ".."
          termina en espacio o punto; parte antes del primer punto (mayúsculas) reservada de Windows
          es_tema y (len(texto) > 60 o texto.casefold() == CARPETA_AVATARES)
          no es_tema y len(texto.encode("utf-8")) > 255
    si no, verdadero

_ubicacion_confinada(tema, nombre) -> Path|None:
    None si no es_nombre_seguro(tema, True) o no es_nombre_seguro(nombre, False)
    base = BASE_UPLOAD_DIR.resolve(); carpeta_tema = (base / tema).resolve()     # sigue enlaces
    None si carpeta_tema.parent != base
    real = (carpeta_tema / nombre).resolve()
    None si real.parent != carpeta_tema o no real.is_file()
    devolver real

obtener_ruta_archivo(tema, nombre) = _ubicacion_confinada(tema, nombre)          # misma firma: descarga, previsualización, borrado

obtener_documento_por_ruta(db, ruta, usuario_id) -> Path:                       # ruta ya decodificada
    partes = ruta.split("/"); denegar("ruta no permitida") si len != 3 o partes[0] != "uploads" o algún nombre no seguro
    si tema.casefold().startswith("nb-"):                                         # decisión 13
        m = re.fullmatch(r"nb-([1-9][0-9]*)", tema, re.IGNORECASE | re.ASCII)
        denegar("ruta no permitida") si no m o int(m[1]) > 2**63 - 1            # antes de consultar la base
    si m y no obtener_notebook_de_usuario(db, int(m[1]), usuario_id): denegar("documento ajeno")   # ajeno o inexistente
    si no verificar_esta_procesado(db, tema, nombre): denegar("documento no disponible")          # 404, no 400
    devolver _ubicacion_confinada(tema, nombre) o denegar("ruta no permitida")

denegar(motivo): raise AccesoArchivoDenegado(404, "Archivo no encontrado", motivo)

GET /archivos/download(ruta_archivo, usuario):
    ruta = unquote(ruta_archivo)                                                # se conserva (D9)
    AccesoArchivoDenegado e → registrar_descarga_rechazada(motivo=e.motivo); relanzar   # sin ruta en bitácora ni log
    respuesta = descargar_archivo(ubicacion)    # ya confinada; MIME y nombre como hoy
    auditar éxito(_sin_control(ruta de documento), tamaño)
    otro error → logger.exception("Error inesperado en la descarga"); auditar motivo "error interno"; 500 genérico

GET /archivos/expediente/{tema}/archivo/{nombre}: igual, con obtener_documento_por_ruta(db, f"uploads/{tema}/{nombre}", usuario)   # misma pertenencia y 404 (T3)

guardar_archivo(file, tema):
    validar_tema(tema)                                   # 400 "El tema indicado no es válido"
    nombre no seguro → 400 "Nombre de archivo no válido"
    crear carpeta_tema y comprobar su confinamiento; nombre_unico = _get_unique_filename(...)
    nombre_unico > 255 bytes → 400 "Nombre de archivo no válido"
    ruta_documento = f"uploads/{tema}/{nombre_unico}"    # sin relative_to
    contenido vacío → 400 (como hoy); escribir en modo "xb"
    fallo de escritura → borrar solo el archivo creado por esta llamada (D5); 500 "No se pudo guardar el archivo"
    devolver las mismas claves (relative_path = ruta_documento)

POST /ingesta/archivos(tema, files):
    sin files → 400; validar_tema falla → registrar_carga_rechazada("tema no válido"); 400
    por archivo i: HTTPException 400 → {error, message: e.detail}  (sin filename; posición i) + registrar_carga_rechazada("nombre de archivo no válido")
                   500 de escritura → {error, message: "No se pudo guardar el archivo"}; logger.exception sin el nombre
                   otro → logger.exception; {error, message: "Error interno del servidor"}
    500 general: "Error interno del servidor"

GET|HEAD /uploads/profiles/{nombre}:  ubicacion = obtener_ubicacion_avatar_publico(nombre) o 404 "Archivo no encontrado"; ?v= se ignora
```
- `HEAD` es obligatorio: sin él, 405 y la interfaz cae a las iniciales.
- El modo `"xb"` evita sobrescribir un archivo aparecido entre el cálculo del nombre y la escritura; se trata como fallo y no se borra el archivo ajeno.
- `_sin_control` quita caracteres de control y NUL de todo texto que se registra (bitácora o registro del servidor) en descarga y carga exitosas.

## 5. Datos (RN-01)
- Sin migración ni cambios en SQL Server, Qdrant, Redis o archivos; `CT_Ruta_archivo` y `metadata.ruta_archivo` siguen `uploads/<tema>/<nombre>`.
- La descarga no confía en la ruta guardada: toma tema y nombre, los busca en la base y calcula la ubicación.
- Podría dejar de descargarse (sin borrar nada) un documento con tema o nombre no seguro (incl. > 255 bytes), ruta mal formada o archivo fuera de su tema: 404 al descargar y previsualizar; quitarlo del notebook sigue quitando fragmentos y registro sin tocar el disco.
- **Inventario de solo lectura** (T6; Andrés o el implementador con su aprobación; solo **cantidades**, nada en el repositorio):
  1. `T_Documento.CT_Ruta_archivo` que no empieza por `uploads/`, vacío o con `..` o `\`.
  2. `T_Documento.CT_Nombre_archivo` con `/`, `\`, `:` o `..`, que termina en espacio o punto, o de más de 255 bytes.
  3. `T_Expediente.CT_Num_expediente` que no sería tema válido (incl. `profiles`).
  4. Puntos de Qdrant con `metadata.ruta_archivo` que no empieza por `uploads/`.
  5. Archivos sueltos en la raíz de `uploads/` o carpetas de tema que sean enlaces simbólicos.
  Si algo es > 0, se informa a Andrés y se decide aparte, sin borrar.

## 6. Interfaz y roles
- Sin cambios de frontend ni `ROUTE_PERMISSIONS`. Mensajes: «El archivo no existe o fue eliminado» (ya existe, ante el 404), «El tema indicado no es válido», «Nombre de archivo no válido», «No se pudo guardar el archivo».
- **Limitación conocida (se arregla en la 004)**: la interfaz de carga (`hooks/ingesta-datos/useFileUploadProcess.js`) y la de NotebookServIA (`pages/notebooks/index.js`) tratan cada elemento de la respuesta como un id de tarea y lo sondean; un archivo rechazado **no muestra** «Nombre de archivo no válido» (sale un fallo genérico o de sondeo). La API sí devuelve el aviso correcto (se prueba); qué ve el usuario se comprueba a mano (§11 paso 6) y se anota para la 004.
- Descarga, carga y previsualización siguen con `require_usuario_judicial`; el Administrador sigue con 403. Avatares públicos (D1-A) hasta la spec de autenticación.
- Ningún rechazo de ruta responde 401/403 (la interfaz cerraría la sesión): solo 404 o 400.

## 7. Bitácora (RF-21, RNF-07.24)
- Descarga rechazada: `registrar_descarga_rechazada`, `TiposAccion.DESCARGAR_ARCHIVO`, texto «Descarga rechazada: ruta no permitida | documento ajeno | documento no disponible», `tipo_error="acceso"`; sin nombre, tema, ruta ni texto pedido (D7-B).
- Carga rechazada: `registrar_carga_rechazada`, `TiposAccion.CARGA_DOCUMENTOS`, «Carga rechazada: tema no válido | nombre de archivo no válido», `tipo_error="validacion"`; sin tema ni nombre.
- Éxitos: como hoy, con la ruta de documento (no la del servidor) y sin caracteres de control.
- Sin constantes nuevas. Si el registro falla, el servicio devuelve `None` y la respuesta no cambia (se prueba).

## 8. Decisiones (con la alternativa descartada)
1. **Validar contra la base, no solo el disco** (D2-A): el confinamiento puro deja pasar no-documentos y no comprueba la pertenencia de RF-18.
2. **Una sola función de confinamiento por ubicaciones resueltas** para las tres vías: filtrar textos (`..`, `%2e`…) con listas siempre deja variantes.
3. **Rechazar el archivo con nombre no válido** (D3-A): sanear cambia en silencio el nombre citado y puede chocar.
4. **Tema: solo nombre seguro** (D4-A): exigir el formato heredado bloquea el tema libre de RF-06.
5. **Ruta propia para avatares en la misma dirección** (D1-A), con prefijo `/uploads/profiles` en vez de `/<modulo>`: conserva la dirección que usa la interfaz; un prefijo nuevo obligaría a cambiar el frontend y los datos guardados (`CT_Avatar_ruta`).
6. **Reserva por la constante de producción** (`profiles`): reservar el nombre de la carpeta de la suite (`avatares`) no protegería producción; se prueban ambos hechos: el tema `profiles` se rechaza y el avatar se sirve desde la ubicación real configurada.
7. **Notebook por la base y sin distinguir mayúsculas**: un patrón sensible a mayúsculas deja pasar `nb-5`, que el disco y SQL Server tratan como `NB-5`.
8. **No Procesado → 404** (no el 400 de hoy): RNF-07.20 exige no revelar existencia; un 400 distinto confirma que el documento existe. La interfaz muestra «El archivo no existe o fue eliminado».
9. **Ruta de documento respecto de la carpeta de documentos**: misma forma en producción y funciona en la suite; capturar el error de `relative_to` dejaría la ruta mal formada.
10. **Conservar la segunda decodificación** (D9): se comprueba la ruta final; quitarla podría romper nombres con `%`.
11. **Bitácora solo con el motivo** (D7-B, Ley 8968): el texto pedido puede contener nombres de personas; el motivo basta para auditar.
12. **Límite en bytes**: el sistema de archivos limita a 255 bytes; contar caracteres deja pasar nombres con tildes que fallan al escribir.
13. **Clave `NB-` solo canónica** (14/10/2026, T3): todo tema que empieza por `nb-` (sin distinguir mayúsculas) debe ser `NB-` + dígitos ASCII sin cero inicial y ≤ 2^63-1; si no, «ruta no permitida» sin consultar la base.
    - `nb-5` = `NB-5` (decisión 7). `NB-0005`, `NB-٥`, `NB-5x`, `NB-`, `NB-0` y 2^63 → 404; 2^63-1 → «documento ajeno».
    - Descartado: normalizar con `int()` (acepta dígitos Unicode y ceros, crea alias de `NB-5`) y dejar que la base desborde (500).

## 9. Trazabilidad requisito → tarea → prueba (se escriben primero)
Hoy la descarga resuelve `uploads/…` contra `/app`, no contra la carpeta temporal: una ruta relativa da 404 **por ubicación**, no por confinamiento. Por eso cada fila anota la causa real del rojo.

| Requisito | Tarea | Prueba | Tipo | ¿Falla hoy? (causa) |
|---|---|---|---|---|
| RNF-07.21, A5 | T1 | `test_confinamiento_rutas::test_obtener_ruta_archivo_confinada` (no seguros, `%00`, enlace que sale) | unit. | Sí, por la razón correcta: hoy une sin confinar |
| RNF-07.21 | T1 | `test_confinamiento_rutas::test_es_nombre_seguro` (B1-B7, 255 bytes con tildes, `profiles`, A12) | unit. | Sí, por importación (se anota) |
| RNF-07.20, RF-18.20 | T2 | `test_confinamiento_rutas::test_obtener_documento_por_ruta_rechaza` (A1-A12, `NB-`/`nb-` ajeno e inexistente con base simulada) | unit. | Sí, por importación; es el rojo real de RF-18.20 |
| RNF-07.20 | T2 | `test_descargas_confinadas::test_ruta_fuera_de_la_carpeta_no_entrega_el_testigo` (A1-A9, A11) | int. | Sí solo por A2: por la API la absoluta daba 500 (`UnboundLocalError`, §1), no el testigo; las relativas pasan hoy por ubicación (anotado) |
| RF-18.20 | T2 | `test_descargas_confinadas::test_documento_de_notebook_ajeno_da_404` (dos grafías; control del dueño; motivo en bitácora) | int. | Sí, por ubicación (el control del dueño falla) y por falta del motivo |
| RF-12.20 | T2 | `test_descargas_confinadas::test_descarga_legitima_como_la_cita_el_chat` (tildes, ñ, espacios, paréntesis, `_1`) | int. | Sí, por ubicación (no es protección pura); verde tras la corrección |
| RF-18.20 | T3 | `test_descargas_confinadas::test_por_tema_y_nombre_de_notebook_ajeno_da_404` (dos grafías; control del dueño) | int. | Sí: hoy entrega el documento ajeno Procesado |
| RNF-07.20, 07.21 | T3 | `test_descargas_confinadas::test_por_tema_y_nombre_hostil_da_404` (`..`, `%2F`, `%5C`, absoluta, `%00`, vacío, enlace) | int. | Probable protección tras T2 (anotada) |
| RF-18.20 (dec. 13) | T3 | `test_confinamiento_rutas::test_clave_nb_no_canonica_se_rechaza` · `::test_clave_nb_limite_y_minusculas` | unit. | Sí: motivo distinto y 2^63 desborda en la base |
| RF-21.20 | T3 | `test_descargas_confinadas::test_rechazo_queda_en_bitacora_con_motivo` + variante con bitácora que falla | int. | Sí: hoy no registra el rechazo ni lo clasifica |
| RNF-07.24 | T3 | `test_descargas_confinadas::test_rechazo_no_repite_datos_personales` (A13 y `%00`; respuesta, bitácora y `caplog`) | int. | A confirmar al verla fallar; si pasa, caracterización |
| RNF-07.23 | T3 | `test_descargas_confinadas::test_error_inesperado_es_generico` (error con ruta inventada) | int. | Sí: hoy `str(e)` |
| RF-06.20 | T4 | `test_carga_confinada::test_tema_no_valido_no_escribe_nada` (B1-B7; instantánea de la temporal) | int. | Sí (o caracterización) |
| RF-05.20 | T4 | `test_carga_confinada::test_nombre_no_valido_se_rechaza_y_el_otro_sigue` (incl. B6 en bytes y con sufijo) | int. | Sí |
| RF-05.21 (a) | T4 | `test_carga_confinada::test_carga_valida_fuera_de_app` (`carpeta_archivos`, `celery_inmediato`) | int. | Sí: 500 por `relative_to` |
| RF-05.21 (b) | T4 | `test_confinamiento_rutas::test_escritura_fallida_no_deja_archivo` | unit. | Sí: hoy queda el archivo |
| RF-21.20, RNF-07.24 | T4 | `test_carga_confinada::test_rechazo_de_carga_sin_datos_personales` (B11; respuesta, bitácora, `caplog`; bitácora que falla) | int. | Sí: hoy devuelve `filename` y no registra |
| RNF-07.23 | T4 | `test_carga_confinada::test_error_inesperado_es_generico` | int. | Sí: hoy `str(e)` |
| RNF-07.22 (a) | T5 | `test_confinamiento_rutas::test_ningun_montaje_publica_la_carpeta_de_documentos` (`app.routes`) | unit. | Sí, por la razón correcta |
| RNF-07.22 (b) | T5 | `test_carpeta_publica::test_documento_no_se_obtiene_por_la_direccion_publica` (sin y con token) | int. | No: el montaje sirve `/app/uploads`, no la temporal; el rojo lo da (a) |
| RF-04.20 | T5 | `test_carpeta_publica::test_avatar_se_entrega_con_get_y_head` (ubicación real configurada, `?v=`) · `::test_nombre_de_avatar_no_valido_da_404` | int. | 1.ª sí, por ubicación (404 en la suite); 2.ª protección |

Reglas: cada prueba nombra su requisito; datos `PRUEBA`; solo `carpeta_archivos`; nunca rutas reales ni `uploads/` de desarrollo; cada prueba limpia; ≤ 5 s; no se modifica ninguna prueba existente.

## 10. Exenciones
- **E0**: extremo a extremo en el navegador hasta la 005; los flujos de interfaz (incl. qué ve el usuario con un archivo rechazado) se comprueban a mano (§11) y se proponen como casos de la 005.
- **E1**: aspecto visual del avatar, solo manual (principio 4); su entrega sí está automatizada.

## 11. Verificación manual de punta a punta
Tras `docker compose restart backend celery-worker`, `ps` sin reinicios, `curl http://localhost:8000/` y logs limpios; datos `PRUEBA`, credenciales de Andrés (no se escriben):
1. Usuario Gubernamental: cargar `prueba_contrato.pdf` en un tema `PRUEBA` → Procesado; preguntar en el chat y descargar la fuente citada (íntegra).
2. Temas similares: abrir el detalle y descargar un documento.
3. NotebookServIA: crear «PRUEBA 004a», subir una imagen, previsualizarla y quitarla (fuera del disco, Qdrant y base).
4. Avatar inventado: se ve en menú y chat, también tras recargar.
5. Sin sesión (`curl`): documento por la dirección pública → 404 sin contenido; avatar responde a `GET` y `HEAD`.
6. Con token (`curl`): ruta no permitida y documento de otro notebook (`NB-` y `nb-`) → 404 «Archivo no encontrado»; carga con un nombre no válido inventado lo rechaza sin repetir el nombre y sigue con el otro. En la interfaz, anotar qué ve el usuario con el archivo rechazado (para la 004). Sin rutas del servidor ni nombres en `docker compose logs backend`.
7. Administrador: el Historial de Actividades muestra los rechazos con su motivo y sin nombres ni rutas; sigue con 403 en la descarga.
8. Pantalla pequeña: repetir 1 y 4; consola sin errores.
9. Limpiar los datos de prueba; `uploads/` de desarrollo solo cambió por lo hecho a mano.

## 12. Riesgos
- Un documento existente con nombre no seguro o > 255 bytes deja de descargarse (inventario del §5).
- Avatares siguen públicos: se anota en el «Estado actual» de RNF-07 y pasa a la spec de autenticación.
- Hasta la 004, el usuario no ve el aviso de un archivo rechazado (§6).

## 13. Documentación (T7)
- **ERS** (copia que edita el implementador; Andrés exporta el PDF): RNF-07 «Estado actual» (avatares sin sesión) y regla de datos personales en rechazos (RNF-07.24, Ley 8968); RF-05 «Manejo de errores» (nombre no válido, límite de 255 bytes, sin repetir el nombre); RF-06 «Reglas y validaciones» (tema usable como carpeta, `profiles` reservado; «El tema indicado no es válido»); RF-21 (rechazos solo con motivo); comprobar que RF-12 y RF-18 siguen siendo ciertos.
- **Casos de Uso**: CU-07 (flujo alterno de nombre o tema no válido); CU-12 si Andrés lo pide.
- **C4** (`Diagramas/Arquitectura_C4/c4_nivel3_componentes_api.puml`): quitar la publicación estática de `uploads/` y agregar el componente de avatares públicos (`/uploads/profiles`, sin sesión, prefijo distinto de `/<modulo>` para conservar la dirección); regenerar el PNG.
- `MEMORY.md` en términos generales.
- `/sdd-change` sobre la 004: quitar el «Estado actual» del guardado en RF-05.1, clasificar la ruta de avatares como pública y agregar el arreglo de la interfaz de rechazados.
- Borrar `respaldo/` (no se publica).

## 14. Dudas para Andrés — resueltas 12/10/2026
1. Avatares sin sesión: **A** (ruta pública solo de avatares, misma dirección, `GET`/`HEAD`).
2. Qué entrega la descarga por ruta: **A** (documentos registrados, Procesados y con pertenencia); ajuste del reviewer: no Procesado → 404 uniforme (§8.8).
3. Nombre de archivo no válido: **A** (rechazar ese archivo y seguir).
4. Qué se exige al tema: **A** (solo nombre seguro).
5. Archivo a medias: **A** (borrar solo el creado por esa llamada).
6. Carga en notebook ajeno: **A** (fuera; la 004 la marca `xfail`).
7. Bitácora del rechazo: **B** (solo el motivo) + RNF-07.24 (Ley 8968).
8. Numeración: **A** (bloque `.20+`).
9. Segunda decodificación: **A** (conservarla).
- Pregunta bloqueante del reviewer (interfaz de rechazados): **A** (documentar y verificar a mano; arreglo en la 004).
