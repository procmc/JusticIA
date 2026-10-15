# Tareas — Spec 004a: Correcciones urgentes de seguridad en los archivos de documentos
Estado: implementada (14/10/2026; T1 a T7 hechas; aprobadas el 12/10/2026)

> No se publica hasta cerrar T7 (tampoco `respaldo/`, que se borra en T7); evidencia y `MEMORY.md` en términos generales.
> T7 cerrada el 14/10/2026 y `respaldo/` borrada: publicable (commit con `@committer`).

Historial: 12/10/2026 — creadas · 12/10/2026 — condensadas; versión completa en `respaldo/` · 12/10/2026 — revisión del reviewer: T2 y T5 divididas (7 tareas), RNF-07.24, causa del rojo en plan §9.

Orden: T1 → T2 → T3; T4 tras T1; T5 independiente (tras T2); T6 y T7 al final. Prueba primero y **verla fallar, anotando la causa del rojo** (plan §9); la que pasa desde el inicio se anota como protección o caracterización. Detalle de pruebas, código y líneas: plan §2, §4, §9 (`fms` = `backend/app/services/documentos/file_management_service.py`).

⚠️ Solo los archivos nuevos aprobados con el plan. Nada de esquema, migraciones, `docker-compose.yml`, dependencias, prompts, modelos, `tests/soporte/`, frontend ni datos reales.

**E**: rojo y su causa anotados; pruebas existentes intactas (base: cifra al empezar T1; última 1029); suite y `--orden-inverso` pasan sin residuos, ninguna nueva > 5 s (`--durations=15`); restart, `ps`, `curl :8000/` y logs sin errores; `git diff` vacío en `requirements.txt`, `docker-compose.yml`, `frontend/`, `tests/soporte/` y sin migraciones nuevas; ninguna prueba apunta a rutas reales ni a `uploads/`; una línea en `MEMORY.md` y parar.

## Antes de empezar (Andrés)
- [x] Aprobar spec, plan y tareas (§14 ya resuelto). Aprobados el 12/10/2026.
- [x] Esta carpeta, incluida `respaldo/`, fuera de todo commit hasta T7 (vigente).
- [x] `backend` y `celery-worker` en marcha y la suite pasando (1230 pasan tras T1).

## Tareas
- [x] **T1. Confinamiento común.** RNF-07.21  ⚠️ nuevo `backend/tests/unitarias/test_confinamiento_rutas.py`
  - Pruebas: `test_obtener_ruta_archivo_confinada` (no seguros, `%00`, enlace dentro del tema que sale) y `test_es_nombre_seguro` (B1-B7, 255 bytes con tildes, `profiles` en varias grafías, A12).
  - Código: `es_nombre_seguro` (con `CARPETA_AVATARES` de `AVATAR_UPLOAD_DIR`), `_ubicacion_confinada`, `obtener_ruta_archivo` confinada (`fms:216-228`).
  - Hecho cuando: rojas antes y verdes después; previsualización y borrado de NotebookServIA siguen pasando; E.
  - Rojo (causa): 103 rojas y 13 que pasaban desde el inicio; 91 por `ImportError` de `es_nombre_seguro`, 1 por `AttributeError` de `CARPETA_AVATARES`, 11 por RNF-07.21 (`obtener_ruta_archivo` unía sin confinar); las 13 que pasaban son protección o caracterización. Corrección de la fase 6 (13/10/2026): +5 pruebas con archivo real en la ubicación no segura (A9-nombre-espacios, A9-control, B5-tema-reservado, B5-nombre-reservado, A8-mayusculas) y +5 que comprueban que sin `es_nombre_seguro` ese archivo se entrega; las 5 primeras, comprobadas rojas con la protección desactivada (no contra el código original), por RNF-07.21. NUL (A9-nul-*, A9-percent00-*) y `A9-tema-vacio` no pueden fallar sin la protección (`resolve()` lanza `ValueError` / la carpeta resuelta no cuelga de `uploads/`): defensa en profundidad, cubiertos por `es_nombre_seguro` directo (B1-B4). Con todo, 108 rojas y 18 que pasaban (las 5 de verificación, de protección).
  - Ajuste (13/10/2026, aprobado por Andrés): hueco cerrado en `_ubicacion_confinada`: un enlace de la carpeta de un tema hacia la de otro (`NB-5`, `profiles`) seguía siendo hijo de `uploads/` y saltaba la pertenencia; ahora la carpeta real debe llamarse igual que el tema. La prueba de caracterización se invirtió (`test_enlace_de_un_tema_a_la_carpeta_de_otro_tema_no_se_entrega`): roja (1 fallo, «DID NOT RAISE AccesoArchivoDenegado») porque la carpeta resuelta era hija directa de `uploads/` y su nombre difería del tema pedido; verde tras el cambio. Suite final: 1230 pasan, también con `--orden-inverso`; falta reiniciar `backend` y `celery-worker` (Andrés) para E.

- [x] **T2. Descarga confinada y pertenencia.** RNF-07.20, RF-18.20, RF-12.20  ⚠️ nuevo `backend/tests/integracion/test_descargas_confinadas.py`
  - Pruebas: `test_obtener_documento_por_ruta_rechaza` (en el archivo de T1; A1-A12, `NB-`/`nb-`), `test_ruta_fuera_de_la_carpeta_no_entrega_el_testigo`, `test_documento_de_notebook_ajeno_da_404` (con control del dueño), `test_descarga_legitima_como_la_cita_el_chat`.
  - Código: `obtener_documento_por_ruta`, `AccesoArchivoDenegado`; `archivos.py:248-321` (sin `266-272`) y `145-246` (no Procesado → 404); `descargar_archivo` (`fms:136-214`).
  - Hecho cuando: rojas antes con su causa anotada y verdes después; manual plan §11 pasos 1, 2 y la parte de descarga del 6; E.
  - Estado (13/10/2026): pruebas, suite (1219), `--orden-inverso` y E cumplidos.
  - Verificación manual (14/10/2026): chat del notebook `PRUEBA`, la fuente citada se descargó y abrió (Andrés); temas similares, descarga con 200 y `application/pdf`.
    - 8 rutas hostiles (`uploads/../x`, vacía, `/etc/hostname`, `uploads/NB-999999/x.pdf`, `uploads/nb-999999/x.pdf`, `../` entre temas, barra invertida, `../../etc/hostname`): todas 404 con `{"detail":"Archivo no encontrado"}`, sin 401, 403 ni 500.
    - Controles: 200. Logs sin trazas.
    - RF-18.20 con un notebook ajeno: cubierto solo por `test_documento_de_notebook_ajeno_da_404`, por decisión de Andrés («damos T2 por cerrada»).

- [x] **T3. Descarga: pertenencia por tema y nombre, bitácora del rechazo, datos personales y 500 genérico.** RF-18.20, RNF-07.20, RNF-07.21, RF-21.20, RNF-07.24, RNF-07.23
  - Ampliación (14/10/2026, aprobada por Andrés: «1, incluir (a), (b) y (c) en T3»), hallazgos del reviewer en T2:
    - (a) Ruta por tema y nombre (`archivos.py:145-241`): arma `uploads/{tema}/{nombre}` y llama a `obtener_documento_por_ruta` (plan §4); sin lógica duplicada. Notebook ajeno → 404 uniforme con motivo «documento ajeno».
    - (b) Pruebas de esa ruta en `test_descargas_confinadas.py` (sin archivo nuevo): `test_por_tema_y_nombre_de_notebook_ajeno_da_404` (`NB-`/`nb-`, control del dueño 200) y `test_por_tema_y_nombre_hostil_da_404` (`..`, `%2F`, `%5C`, absoluta, `%00`, vacío o solo espacios, enlace que sale).
    - (c) Claves `NB-` según plan §8 decisión 13, en `test_confinamiento_rutas.py`: `test_clave_nb_no_canonica_se_rechaza` (`NB-0005`, `NB-٥`, `NB-5x`, `NB-`, `NB-0`, 2^63 → «ruta no permitida» sin consultar la base) y `test_clave_nb_limite_y_minusculas` (2^63-1 → «documento ajeno»; `nb-5` = `NB-5`).
    - Rojo esperado: (a) ajeno → 200 por RF-18.20; (c) motivo distinto (hoy «documento no disponible») y 2^63 → desbordamiento en la base. Los hostiles de (b) pueden pasar ya por T2: protección, anotada.
  - Pruebas (en el archivo de T2): `test_rechazo_queda_en_bitacora_con_motivo` (+ bitácora que falla), `test_rechazo_no_repite_datos_personales` (A13, `%00`; respuesta, bitácora, `caplog`), `test_error_inesperado_es_generico`.
  - Código: `registrar_descarga_rechazada` y clasificación `tipo_error` (`archivos_audit_service.py:277-278`); `_sin_control`; traducción de errores en `archivos.py`; quitar `str(e)` y `logger.error` con la ruta (`archivos.py:166-241` y `302-306`, `fms:270`).
  - Hecho cuando: rojas antes (o caracterización anotada) y verdes después; manual §11 pasos 6 y 7 (descarga, también por tema y nombre con un notebook ajeno); E.
  - Estado (14/10/2026): pruebas, suite (1267), `--orden-inverso` (1267) y sin residuos cumplidos; falta reiniciar `backend` y `celery-worker` (Andrés) y la verificación manual.
  - Decisión 13 aplicada: `NB-0005`, `NB-٥`, `NB-５`, `NB-5x`, `NB-`, `NB-0`, `NB--5` y 2^63 → «ruta no permitida» sin consultar la base; 2^63-1 y `nb-5` → «documento ajeno». Se actualizó el esperado de una prueba de T2 (`A10-notebook-con-id-fuera-de-rango`: de «documento ajeno» a «ruta no permitida»), porque lo manda la decisión 13.
  - Rojo (causa): 17 rojas y 20 que pasaban (37 nuevas). Unitarias, 10 rojas: 9 de `test_clave_nb_no_canonica_se_rechaza` (motivo distinto: «documento no disponible» o «documento ajeno» en vez de «ruta no permitida») y 1 de `_sin_control` (`ImportError`). Integración, 7 rojas: `test_por_tema_y_nombre_de_notebook_ajeno_da_404` (RF-18.20: el ajeno recibía el documento, 200), `test_rechazo_queda_en_bitacora_con_motivo` (no registraba el rechazo), `test_rechazo_con_bitacora_que_falla_responde_igual` (mismo 200 con el notebook ajeno), `test_rechazo_no_repite_datos_personales` (RNF-07.24: la bitácora de la ruta por tema y nombre traía el nombre pedido y lo clasificaba «interno»), `test_error_inesperado_es_generico` (RNF-07.23: `detail` con `str(e)`) y 2 de `test_por_tema_y_nombre_hostil_da_404` (`barra-codificada-dos-veces`, `absoluta-codificada-dos-veces`) que eran un error mío de la prueba (el enrutador las frena con «Not Found»); corregidas antes del verde, así que el rojo real fue 17 - 2 = 15 de código más esos 2 del esperado de la prueba.
  - Pasaban desde el inicio (protección o caracterización): 11 nombres hostiles por tema y nombre (ya frenados por T2), `test_por_tema_y_nombre_con_tema_hostil...`, `test_clave_corta_de_notebook...` (400 «Formato de expediente inválido» para dueño y ajeno), `test_clave_nb_limite_y_minusculas` (5), `test_clave_nb_propia...` y `NB-5 ` con espacio final.
  - Verde: 238 en los dos archivos (189 unitarias + 49 integración).
  - Corrección 1 (14/10/2026, observación 1 del reviewer; Andrés: «1. Corregirlo ya»): el registro de acceso de uvicorn imprimía la URL completa (`GET /archivos/download?ruta_archivo=...`), contra RNF-07.24 y plan §11 paso 6. Filtro `OcultarDatosDeDescarga` en `backend/main.py` (solo la API, no el worker) sobre `uvicorn.access`: enmascara el valor de `ruta_archivo` (`?ruta_archivo=***`) y el tema y el nombre de `/archivos/expediente/{tema}/archivo/{nombre}` (`/archivos/expediente/***/archivo/***`); método, endpoint y estado se conservan y las demás rutas no se tocan. Pruebas en `test_descargas_confinadas.py`: `test_registro_de_acceso_no_repite_la_ruta_ni_el_nombre_pedidos` y `test_registro_de_acceso_conserva_el_resto_de_las_rutas`.
    - Rojo (causa): 2 rojas de 2; no existía ningún filtro, así que la línea salía con la ruta y el nombre completos, codificados o no, y el valor de `ruta_archivo` sin ocultar.
    - Verde: 2 de 2 (un primer intento dejaba pasar una ruta con espacios sin codificar; el patrón se corrigió a `[^&#]*`). Suite: 1269 pasan; `--orden-inverso`: 1269; sin residuos. Falta reiniciar `backend` (Andrés) y comprobar con `docker compose logs backend` en la verificación manual.
  - Hallazgo: la ruta por tema y nombre exige primero formato de expediente (17-20 caracteres): un `NB-<id>` real (corto) da 400 a todos y no llega a la pertenencia; las pruebas la ejercitan con `monkeypatch` de `validar_expediente`. Queda fuera de T3 el `str(e)` del listado de archivos (`archivos.py`, `listar_archivos_expediente`) y de `guardar_archivo` (T4).
  - Verificación manual (14/10/2026), OK, tras la corrección 1 y el reinicio:
    - Usuario Gubernamental, 9 rutas hostiles (`../`, `/etc/hostname`, byte nulo, nombre de persona inventado, `NB-0005`, dígito árabe, 2^63, `NB-999999`, `nb-999999`): 9 × 404 «Archivo no encontrado». La legítima: 200 (309631 B).
    - Administrador: 403 «Acceso denegado» en todo (el rol se comprueba antes).
    - Log de acceso: `ruta_archivo=***`, sin perder líneas.
    - Bitácora (vista del Administrador): 9/9 «Descarga rechazada: <motivo>» (6 ruta no permitida, 2 documento ajeno, 1 no disponible), sin rutas ni datos personales; las 2 legítimas presentes; ninguna fila por los 403 de rol.
    - Suite: 1269/1269, también `--orden-inverso`.
    - Limitación: el detalle de la bitácora en la interfaz no muestra `motivo`, `tipo_error` ni `ruta_archivo`; lo cubren el código y las pruebas.

- [x] **T4. Guardado confinado, sin archivos a medias ni eco de nombres.** RF-06.20, RF-05.20, RF-05.21, RF-21.20, RNF-07.23, RNF-07.24  ⚠️ nuevo `backend/tests/integracion/test_carga_confinada.py`
  - Pruebas: las de T4 en plan §9 (tema no válido B1-B7, nombre no válido con B6 en bytes y sufijo, carga válida fuera de `/app`, rechazo sin datos personales B11 + bitácora que falla, 500 genérico) y `test_escritura_fallida_no_deja_archivo` en el archivo de T1.
  - Código: `guardar_archivo` (`fms:68-134`, D5, `"xb"`, 255 bytes), `validar_tema`, `ingesta.py:162-237` (sin `filename` en el rechazo), `registrar_carga_rechazada`.
  - Además (decisión de Andrés, 14/10/2026): quitar el `str(e)` de `listar_archivos_expediente` (`archivos.py` ~152-157, en el `detail` y en `error=str(e)` de la bitácora), con su prueba de 500 genérico sin datos personales. RNF-07.23, RNF-07.24.
  - Hecho cuando: rojas antes y verdes después; caracterizaciones anotadas; manual §11 pasos 1 y la parte de carga del 6 (anotar qué ve el usuario con el rechazado); E.
  - Estado (14/10/2026): pruebas, suite (1310), `--orden-inverso` (1310) y sin residuos cumplidos; reinicio y verificación manual hechos (abajo).
  - Rojo (causa): 41 rojas de 41 nuevas (33 de integración en `test_carga_confinada.py` y 8 unitarias en `test_confinamiento_rutas.py`). Temas no válidos (19): 200 en vez de 400 (no se validaba el tema) y los archivos se intentaban guardar. Nombres no válidos (7 + el del sufijo): `relative_to` fuera de `/app` (RF-05.21) o el nombre no se rechazaba. `test_carga_valida_fuera_de_app`: 500 por `relative_to`. Escritura fallida: mensaje con `str(e)` y rutas. Rechazo sin datos personales y bitácora que falla: no había `registrar_carga_rechazada`. Error inesperado y listado: `detail=str(e)` y `error=str(e)` en la bitácora. Unitarias: `guardar_archivo` sin validación, `relative_to` y modo `wb` (el archivo ajeno se sobrescribía).
  - Verde: 41 de 41. Un primer verde falló en el caso del sufijo (254 bytes + `_1` = 256): `Path.exists()` lanza `ENAMETOOLONG` en vez de dar `False`, así que el límite se comprueba en `_get_unique_filename` antes de consultar el disco (400 «Nombre de archivo no válido», sin crear nada).
  - Código: `validar_tema`, `MENSAJE_*` y `guardar_archivo` (`fms`); `registrar_carga_rechazada` (`ingesta_audit_service.py`); `ingesta.py` (tema antes del bucle, rechazo por archivo sin `filename`, 500 genérico); `archivos.py` (listado sin `str(e)`; la bitácora guarda «error interno»).
  - Decisiones: (1) en `guardar_archivo` el registro del servidor solo lleva el tipo de error y el `errno` (no `logger.exception`): su traza y su texto traen la ruta con el tema y el nombre. (2) Los demás 500 de carga y listado sí usan `logger.exception` (no son rechazos). (3) El elemento rechazado es `{"error": true, "message": ...}`, sin `filename` y con su posición en `task_ids`. (4) Tema `""` (vacío): FastAPI lo da por ausente (422) antes de llegar; queda fuera de la prueba de temas; `es_nombre_seguro` ya lo rechaza (B1, T1).
  - Hallazgo: el registro de acceso de uvicorn de la carga no expone nombres: el tema y los archivos van en el cuerpo (`multipart`) y la URL es `POST /ingesta/archivos`, así que no se amplía `OcultarDatosDeDescarga`.
  - Verificación manual (14/10/2026): OK.
    - Reviewer: código APROBADO CON OBSERVACIONES; suite 1310/1310 (y en orden inverso, implementer).
    - Interfaz (Usuario Gubernamental): carga a Completado con su fragmento en Qdrant.
    - El mismo archivo otra vez se guarda como `_1` sin alterar el original.
    - Descarga 200 desde Temas similares; ventana de ~555 px sin desborde.
    - El formulario bloquea los temas no válidos antes de enviarlos.
    - API con token: `profiles` y `../PRUEBA` → 400 «El tema indicado no es válido».
    - Carga mixta: el no válido da `{"error":true,"message":"Nombre de archivo no válido"}` sin el nombre; el válido se encola.
    - Bitácora (Administrador): 2 «Carga rechazada: tema no válido» y 1 «…nombre de archivo no válido», sin tema, nombre ni ruta.
    - Las cargas correctas quedan registradas; logs sin nombres hostiles ni rutas.

- [x] **T5. Carpeta de documentos no pública; avatares funcionando.** RNF-07.22, RF-04.20  ⚠️ nuevos `backend/tests/integracion/test_carpeta_publica.py` y `backend/app/routes/avatares.py`
  - Pruebas: las de T5 en plan §9 (tabla de rutas, documento por dirección pública, avatar con `GET`/`HEAD`/`?v=` desde la ubicación real configurada, nombre de avatar no válido C3).
  - Código: quitar `main.py:185-188`; `obtener_ubicacion_avatar_publico`; router de avatares con `prefix="/uploads/profiles"` y su docstring de excepción.
  - Hecho cuando: tabla de rutas y avatar rojas antes y verdes después; protecciones verdes siempre; manual §11 pasos 4, 5 y 8; E.
  - Estado (14/10/2026): pruebas, suite (1325), `--orden-inverso` (1325, reviewer) y sin residuos cumplidos; reinicio y verificación manual hechos (abajo). Cerrada por Andrés («1, Cerrar T5»).
  - Rojo (causa): 3 rojas de 15 (12 pasaban: 12 protecciones de nombre de avatar). `test_ningun_montaje_publica_la_carpeta_de_documentos`: `main.py` montaba `StaticFiles` en `/uploads`. `test_avatar_se_entrega_con_get_y_head`: 404 por ubicación (el montaje servía `/app/uploads`, no la carpeta de avatares configurada). `test_documento_no_se_obtiene_por_la_direccion_publica`: rojo incidental, `/uploads` daba 307 (redirección del montaje) en vez de 404; la ruta de un documento ya daba 404 por ubicación, como anotó el plan.
  - Verde: 15 de 15 (1 unitaria en `test_confinamiento_rutas.py`; 14 de integración en `test_carpeta_publica.py`, con 12 casos de nombre no válido). Suite: 1325/1325, también `--orden-inverso`.
  - Código: `main.py` (sin `StaticFiles`; `include_router(avatares.router, prefix="/uploads/profiles")`), `routes/avatares.py` (nuevo), `avatar_service.obtener_ubicacion_avatar_publico`. Frontend sin cambios: `buildAvatarUrl` arma `API_URL/uploads/profiles/<id>.<ext>`.
  - Reviewer: APROBADO. Sin sesión, `/uploads/<tema>/<nombre>`, `/uploads/` y `/uploads` → 404 sin contenido; en `/uploads/profiles/`, nombres hostiles (`..%2F`, `.txt`, > 40 caracteres, inexistente) → 404.
  - Verificación manual (14/10/2026): OK.
    - Andrés (Chrome normal): subió su foto de perfil y la vio en el menú y en el chat, también tras recargar.
    - Reviewer (Chrome del MCP): `GET`/`HEAD /uploads/profiles/<id>.jpg` → 200 `image/jpeg` (id de 9 dígitos que cumple la regex).
    - Foto visible en menú y chat, a escritorio y a 616 px (mínimo del MCP, ~555 px con zoom 0,9), sin desbordes; consola sin 404 ni 405 del avatar.
    - RNF-07.22(b) con token: la cubre la prueba de integración; Andrés no corrió el script manual.
  - Corrección 1 (14/10, H2 de T6; aprobada por Andrés, opción «A»): el `fetch(..., {method:'HEAD'})` de `AvatarContext.jsx` fallaba por CORS tras recargar con el avatar en la caché, porque Chrome reutilizaba la respuesta del `<img>` (sin `Origin`, sin `Access-Control-Allow-Origin`). Frontend, CORS global y `docker-compose.yml` sin tocar.
    - Rojo: `test_avatar_no_se_reutiliza_entre_peticiones_con_y_sin_origen` (en `test_carpeta_publica.py`, RF-04.20) fallaba porque la respuesta no llevaba `Vary` (`assert 'origin' in ''`); 14 pasaban, 1 fallaba.
    - Código: `routes/avatares.py`, `FileResponse(ubicacion, headers={"Vary": "Origin"})`. `CORSMiddleware` solo actúa con `Origin` y no pisa el `Vary` de la ruta; los 404 no llevan imagen que guardar.
    - Verde: 15 de 15 en el archivo; suite 1326/1326 y `--orden-inverso` 1326/1326, sin residuos (antes 1325).
    - Verificación manual (14/10), tras el reinicio (Andrés); reviewer: CUMPLE.
      - `curl`: `vary: Origin` en `GET` y `HEAD` del avatar; con `Origin: http://localhost:3000`, además `access-control-allow-origin`. El 404 no cambia.
      - Chrome del MCP: tras vaciar la caché una vez y recargar varias veces, avatar visible en `/consulta-datos/chat`, `/notebooks` y `/consulta-datos/busqueda-similares`, también a 616 px.
      - Consola sin «blocked by CORS policy» ni «Error verificando avatar»; el `HEAD` da 200.
      - Suite: 1326/1326 en ambos órdenes.

- [x] **T6. Punta a punta e inventario.** Todos los requisitos
  - Pruebas: ninguna nueva; suite y `--orden-inverso`, con conteo por requisito (al menos una que pasa, o E0/E1).
  - Trabajo: plan §11 completo con los dos roles y pantalla pequeña; inventario §5 (solo cantidades, con aprobación de Andrés); limpieza de datos `PRUEBA`.
  - Limpiar datos de prueba de T4: temas `99-999904-0001-PR` y `99-999904-0002-PR` (4 documentos, sus archivos en `backend/uploads/`, 4 fragmentos en Qdrant y 1 conversación de chat).
  - Ubicación: en el anfitrión los documentos están en `backend/uploads/` (`/app/uploads` en el contenedor), no en `uploads/` de la raíz. El punto 5 del inventario §5 (archivos sueltos y enlaces) se revisa ahí; los puntos 1 y 4 comparan el texto guardado `uploads/…`, que no cambia.
  - Avance 14/10: puntos 1 y 2 hechos (autorizados por Andrés). Suite: 1325 pasan, 0 fallan, 0 fallos esperados, 0 XPASS, sin residuos; `--orden-inverso`: igual (1325/0/0, sin residuos). Conteo por requisito (pruebas con la referencia en nombre, docstring o cuerpo; una prueba puede citar varios): RF-04.20 13, RF-05.20 33, RF-05.21 7, RF-06.20 25, RF-12.20 8, RF-18.20 67, RF-21.20 6, RNF-07.20 86, RNF-07.21 134, RNF-07.22 3, RNF-07.23 6, RNF-07.24 8; ninguno sin prueba que pase y ninguna es fallo esperado. Inventario §5 (solo lectura, base con 9 documentos y 5 temas, 3 claves `NB-`): P1 0; P2 0; P3 0 (incluye `profiles`; las 3 `NB-` son válidas para `validar_tema`); P4 0 con ruta que no empieza por `uploads/`, pero 2217 de 2217 puntos de `justicia_docs` no traen `metadata.ruta_archivo` (la descarga usa la base); P5 0 sueltos en la raíz y 0 enlaces simbólicos, con 269 carpetas de tema más `profiles/` (frente a 5 temas en la base: carpetas sin tema registrado, a decidir). Faltan recorrido de punta a punta (plan §11) y limpieza de datos `PRUEBA`.
  - Recorrido (14/10), CUMPLE:
    - Notebook `PRUEBA_004a` (`NB-30003`): PDF con texto en imágenes; OCR de Tika bueno (dos defectos menores); Procesado en ~32 s, 1 fragmento.
    - El chat responde en español y lo cita; vista previa 200 con el tamaño de disco; logs sin rutas ni nombres en los errores.
    - Asistente con el tema `99-999904-0001-PR`: cita la fuente; descarga 200 con tamaño y ETag iguales al archivo.
    - Temas similares: descarga 200. Pantalla de 616 px sin desbordes.
  - Inventario, punto 4 corregido (H7): la ruta está en `metadata.meta.ruta_archivo` (anidada), no en `metadata.ruta_archivo`.
    - Con la clave correcta: 2218 puntos; 2216 empiezan por `uploads/`; 2 sin `metadata.meta`; 0 fuera de `uploads/`. P4 queda en 0.
  - Pasos 6 y 7: el 7 CUMPLE (Historial como Administrador, 14/10); el 6 (qué ve el usuario con un archivo rechazado) se deja para la spec 004, por decisión de Andrés. La limpieza quedó hecha (ver «Limpieza 14/10»).
    - `SELECT` de `CT_Ruta_archivo` del documento 70014: el hook bloquea al reviewer; se da por cubierto con la vista previa en 200.
    - Corrección 1 de T5 (CORS del avatar): verificada, CUMPLE (ver T5).
  - Datos de prueba que se suman a la limpieza:
    - notebook `PRUEBA_004a` (`NB-30003`, `T_Expediente` 20006), documento 70014 (`Legislación_Política.pdf`), 1 punto en Qdrant y `backend/uploads/NB-30003/`;
    - sus conversaciones de notebook y 1 conversación del Asistente con el tema `99-999904-0001-PR` (reviewer, 14/10).
    - El notebook `PRUEBA` (`NB-20003`) es de Andrés: no entra salvo que él lo decida.
  - Limpieza 14/10 (autorizada por Andrés; datos de prueba de T4):
    - A. Qdrant `justicia_docs`: total 2218 → 2214 (4 puntos borrados por id); `count` por tema `99-999904-0001-PR` 3 → 0 y `99-999904-0002-PR` 1 → 0.
    - B. SQL Server (script con transacción y asserts): `OK 4 4`; documentos y enlaces de los ids 70010-70013 4 → 0 y 4 → 0; temas que quedan 2.
    - C. `backend/uploads/`: 271 → 269 carpetas (`99-999904-0001-PR` y `99-999904-0002-PR` borradas); `99-999904-*` ya no existe.
    - Los temas 20004 y 20005 quedan vacíos (sin documentos), no se borran, porque `T_Bitacora` los referencia (RN-01).
    - Suite tras la limpieza: 1326 pasan, 0 fallan, 0 fallos esperados, sin residuos.
    - Pendientes de Andrés, desde la interfaz: borrar el notebook `PRUEBA_004a` (`NB-30003`) y las 2 conversaciones del 14/10; decidir sobre `NB-20003` (notebook `PRUEBA`, suyo). Resueltos más abajo.
    - D. PDF de `PRUEBA_004a`: lo quitó Andrés desde la interfaz y está comprobado: documento 70014 con 0 filas y `NB-30003` con 0 puntos en Qdrant (total 2213). El notebook 30003 (`T_Expediente` 20006) y su carpeta vacía `NB-30003/` se conservan, porque la interfaz no permite eliminar notebooks.
    - E. Redis (DB 2), 3 conversaciones borradas con `delete_session` (autorizado por Andrés, con comprobación previa de tema/prefijo y de mensajes): 2 del Asistente con el tema `99-999904-0001-PR` (4 y 8 mensajes) y 1 del notebook `NB-30003` (6 mensajes). `conversation:*` 58 → 55 y `conversation_meta:*` 58 → 55; las claves y sus entradas en `user_sessions:*` ya no existen. Verificado después: 0 sesiones del tema, 0 de `notebook_30003`, 2 de `notebook_20003` sin cambio. `T_Bitacora` sin tocar.
    - Decisión D1 de Andrés (14/10): el notebook `PRUEBA` (`NB-20003`), con los PDF de la UCR, se conserva.
    - Se conservan: temas 20004 y 20005 vacíos (RN-01), notebook `PRUEBA_004a` vacío (la interfaz no elimina notebooks), `NB-20003` (D1) y `T_Bitacora`.
  - Hecho cuando: suite sin residuos; recorrido reportado (incluido qué ve el usuario con un archivo rechazado); inventario en cero o decidido por Andrés sin tocar datos.
  - Estado (14/10/2026): suite 1326 en ambos órdenes, sin residuos; los 12 requisitos con al menos una prueba que pasa; inventario §5 en 0 (P4 con `metadata.meta.ruta_archivo`); recorrido CUMPLE salvo el paso 6, diferido a la spec 004 por Andrés. Cerrada por Andrés («1, cierra T6»), 14/10/2026.
  - Aplazamiento (Andrés, 14/10/2026): el paso 6 del §11 (qué ve el usuario con un archivo rechazado en la interfaz) queda aplazado a la spec 004; el «Hecho cuando» de T6 se cumple sin él.

- [x] **T7. Documentación y cierre.** Todos los requisitos
  - Trabajo: documentación del plan §13 sobre copias (ERS, CU-07, C4 de componentes con la ruta de avatares y su PNG); Andrés exporta los PDF; `MEMORY.md`; avisar del `/sdd-change` sobre la 004 (RF-05.1, ruta de avatares, interfaz de rechazados); borrar `respaldo/`.
  - Hecho cuando: documentos exportados; C4 regenerado; `respaldo/` borrada; spec «implementada» con aprobación de Andrés y solo entonces publicable.
  - Corrección del método (14/10, Andrés, «B, con la copia previa y las comprobaciones»): la edición en el sitio con python-docx reescribió partes internas del ERS (`styles.xml`, `settings.xml`, `numbering.xml`, `[Content_Types].xml`); los dos `.docx` del proyecto se restauraron a `HEAD` (79321c1, 12/10/2026) y los mismos cambios se rehicieron sobre copias de trabajo en el scratchpad (`docx_trabajo_t7\`), tocando solo `word/document.xml`. **Los `.docx` están en copias de trabajo pendientes de la revisión de Andrés en Word; los del proyecto siguen como en `HEAD`.** Ya hechos: el C4 (`.puml` y PNG). T7 sigue sin marcar.
  - Avance 14/10 (puntos 1 a 5, sin marcar T7; el contenido de los `.docx` es el de las copias de trabajo, no el de los del proyecto): `ERS_Avances de desarrollo - ServIA.docx` (RF-05 «Manejo de errores», RF-06 «Reglas y validaciones», RF-21 «Reglas y validaciones», RNF-07 «Descripción» y «Estado actual»; RF-12 y RF-18 siguen siendo ciertos, sin cambio) y `Casos de Uso - ServIA.docx` (CU-07, flujo de excepción FE-05); C4: `Diagramas/Arquitectura_C4/c4_nivel3_componentes_api.puml` (componente «Avatares públicos») y su PNG regenerado; `MEMORY.md`. Texto del `/sdd-change` sobre la 004 entregado al coordinador. Falta: Andrés exporta los PDF del ERS y de Casos de Uso, `respaldo/` por borrar y la validación final.
  - Estado de los PDF y las copias (14/10/2026): los PDF `ERS_Avances de desarrollo - ServIA_V1.6.pdf` (portada «Versión: 1.5») y `Casos de Uso - ServIA_V1.3.pdf` (portada «Versión del documento: 1.2») que hay ahora en `PDF/` se exportaron desde los `.docx` originales, sin los cambios de la 004a: hay que volver a exportarlos. Las copias de trabajo (`docx_trabajo_t7\`) están verificadas (cambios de la 004a presentes; difieren de los `.docx` del proyecto solo en `word/document.xml`) y con la portada actualizada (ERS 1.5 → 1.6, Casos de Uso 1.2 → 1.3; ninguno tiene tabla de historial de versiones), pendientes del visto bueno de Andrés. Después: sustituir los `.docx` del proyecto y exportar los PDF.
  - Sustitución (14/10/2026, con el visto bueno de Andrés): los `.docx` del proyecto (`ERS_Avances de desarrollo - ServIA.docx` y `Casos de Uso - ServIA.docx`) ya son las copias de trabajo, idénticas byte a byte (SHA-256 verificado) y distintas de `HEAD` solo en `word/document.xml`. Falta que Andrés los revise y vuelva a exportar los PDF encima de `PDF/ERS_Avances de desarrollo - ServIA_V1.6.pdf` y `PDF/Casos de Uso - ServIA_V1.3.pdf`. T7 sigue sin marcar.
  - PDF exportados (14/10/2026, a pedido de Andrés): `PDF/ERS_Avances de desarrollo - ServIA_V1.6.pdf` (32 páginas) y `PDF/Casos de Uso - ServIA_V1.3.pdf` (36 páginas), con Microsoft Word por COM (`ExportAsFixedFormat`, PDF optimizado para impresión, con marcadores; lectura sola, sin actualizar campos). Los `.docx` conservan su SHA-256. Índice de texto (`graphify-out/documentacion_texto/`) regenerado. T7 sigue sin marcar.
  - Arquitectura C4 (14/10/2026, aprobado por Andrés: «1 sí»): `Arquitectura C4 - ServIA.docx` estaba limpio en git (último commit `9db1f24`). Cambios solo en `word/document.xml` y en la imagen `word/media/5d3ff0ca…png` (diagrama de componentes de la API, sustituido por el PNG regenerado; alto recalculado a 5087689 EMU manteniendo el ancho); `[Content_Types].xml` no cambió (ya declaraba `png`). Textos: «Aplicación FastAPI» ya no dice «archivos estáticos» (ahora «incluida la entrega pública de avatares»), fila nueva «Avatares públicos» en el §6.1 (`avatares.py`, `GET`/`HEAD /uploads/profiles/{nombre}`, sin sesión, excepción deliberada RF-04.20/RNF-07.22, `Vary: Origin`) y portada 1.0 → 1.1. `testzip` sin errores, XML bien formado, diff por párrafos: solo esos cambios. PDF `PDF/Arquitectura C4 - ServIA.pdf` (15 páginas, mismo nombre, sin versión) exportado con Word por COM; el `.docx` conservó su SHA-256 (`115890B2…5C20`); no quedó ningún `WINWORD`. Copias del original y del PDF previo en el scratchpad (`c4_t7\`). Índice de texto regenerado.
  - Borrado de `respaldo/` (14/10/2026, aprobado por Andrés: «3 sí»): `specs/004a-correcciones-urgentes-de-seguridad/respaldo/` eliminada con `rm -r` tras comprobar la ruta (no era enlace ni estaba en git); `spec.md`, `plan.md` y `tasks.md` siguen en su sitio.
  - Aviso `/sdd-change` sobre la 004 (aprobado por Andrés, 14/10). No ejecutado; no se toca `specs/004-*` hasta que se lance:
    1. RF-05.1: quitar el «Estado actual» del guardado. La 004a ya valida el tema y el nombre antes de escribir (400 genéricos, límite de 255 bytes, sin repetir el nombre), escribe sin sobrescribir y borra solo lo que creó.
    2. Clasificar `GET`/`HEAD /uploads/profiles/{nombre}` como ruta pública deliberada (RF-04.20, RNF-07.22): una excepción a «todo endpoint exige rol», que no se prueba como protegida. Exigir sesión queda para la spec de autenticación.
    3. Arreglar la interfaz de los archivos rechazados (paso 6 del plan §11 de la 004a, aplazado por Andrés el 14/10):
       - el aviso y el motivo, sin repetir el nombre, en Ingesta y NotebookServIA;
       - «N archivos enviados a procesamiento» y `total_files` deben separar aceptados de rechazados;
       - `InformacionAdicionalRenderer.jsx:374` lee campos que el backend no guarda y no muestra `tipo_error` ni la fecha de la carga;
       - pruebas de integración de `total_files` y verificación manual con los dos roles y pantalla pequeña.
  - Validación final (reviewer, 14/10/2026): APROBADO. Los 12 requisitos cumplen; suite de 1326, sin residuos.
  - Estado (14/10/2026): documentación hecha (ERS V1.6, Casos de Uso V1.3 y C4 1.1, PDF exportados con Word; `.puml` y PNG regenerados); índice de texto regenerado; `respaldo/` borrada; aviso del `/sdd-change` sobre la 004 anotado.
    - Portada del C4: la fecha se queda en «setiembre 2026», por decisión de Andrés.
    - «Hecho cuando» cumplido: documentos exportados, C4 regenerado, `respaldo/` borrada y spec «implementada» con la aprobación de Andrés: publicable.
    - Cerrada con la aprobación de Andrés, 14/10/2026. Siguiente: commit con `@committer`.

## Hallazgos para otras specs (no 004a)
- Chat/RAG: el prompt de notebook (~21840 tokens) se trunca a 4098 (`keep=4`); el chat no encuentra datos concretos que sí están en el documento.
- Streaming: no envía nada antes del primer token y el frontend corta a los 30 s (`frontend/utils/chat/messageUtils.js:219`): «Se perdió la conexión» con Ollama en frío (~70 s).
- `get_db` (`backend/app/db/database.py:71`) registra toda `HTTPException` como «Error en sesión de base de datos».
- Aviso `inert` de HeroUI Tabs en el drawer de temas similares: viene de `@heroui/tabs` 2.2.13 con React 18.3.1; se resolvería actualizando `@heroui/react` (decisión aparte).
- Descarga por tema y nombre: exige `validar_expediente` (17-20 caracteres), así que un `NB-<id>` real da 400 antes de comprobar la pertenencia (hallazgo 2 de T3).
- Docstring de `archivos.py:15` dice «usuarios judiciales y admins», pero `require_usuario_judicial` solo admite «Usuario Judicial»; falta decidir si el Administrador debe descargar.
- `InformacionAdicionalRenderer.jsx:374` lee `expediente`, `archivo`, `tamanio_bytes` y `tipo_mime`; el backend guarda `nombre_archivo`, `ruta_archivo`, `motivo`, `error` y `tipo_error`.
  - En la interfaz tampoco se muestra `tipo_error`; en el caso 2 (carga) no se muestra nada, ni siquiera la fecha.
- Bitácora en la interfaz: siguen el filtro y la columna «Expediente» (RT-06).
- En este entorno `docker compose logs --since` devuelve 0 líneas: usar `--tail`.
- Carga: la respuesta dice «N archivos enviados a procesamiento» y `total_files` cuenta los rechazados (spec 004, junto al aviso de rechazo en la interfaz).
- Bitácora de ingesta: algunas filas «Iniciado» e «Inicio» muestran «-» como tema (comportamiento previo).
- Observaciones opcionales del reviewer sobre T4:
  - `test_escritura_que_falla_figura_rechazada_sin_rutas` no comprueba `caplog`.
  - Si `procesar_archivo_celery.delay` falla tras guardar, el archivo queda sin tarea.
  - `ingesta.py` decide si audita comparando `e.detail == MENSAJE_NOMBRE_NO_VALIDO` (frágil).
  - `archivos.py` importa `_sin_control`, que es privada.
- El MCP de Chrome no baja de ~555 px de ancho: la prueba a 390 px (RNF-04) se hace a mano.
- Herramientas: el Chrome del MCP `chrome-devtools` no abre el diálogo nativo de archivos y `upload_file` solo acepta rutas del proyecto; las subidas de archivos personales se prueban en un Chrome normal.
- Avatar con GIF: `AvatarSelector.jsx:80,351,363` lo admite y anuncia, pero `frontend/constants/avatarConstants.js:28` y `backend/app/constants/avatar_constants.py` lo rechazan; el usuario solo ve «Error al guardar el avatar» (`UserButton.jsx:193`). Va a la spec retroactiva de usuarios y perfil, con prueba de backend de que la subida rechaza GIF.
- Teclado en la zona de carga: «Subir Foto» es un `div` sin `role="button"`, sin `tabIndex` ni manejo de teclado (`AvatarSelector.jsx:344-355`).
- Extensión de la ruta del avatar: `AvatarContext.jsx:212-213` la arma con la extensión del nombre original, que puede diferir de la que guarda el backend (`.JPG`, `.jpeg`).
- Notas de T5 para la 004:
  - Los 404 bajo `/uploads/<tema>/…` devuelven `{"detail":"Not Found"}` de FastAPI, no «Archivo no encontrado» (cumple RNF-07.22b).
  - El log de acceso de uvicorn muestra sin ocultar las direcciones `/uploads/<tema>/<nombre>` intentadas; `OcultarDatosDeDescarga` solo cubre `/archivos/...`.
  - El confinamiento de avatares va aparte del helper de T1; podría unificarse.
  - La URL del avatar contiene la cédula del usuario (como antes).
- Metadatos de los documentos (inventario de T6): para Andrés son clave en las búsquedas, los filtros y la escalabilidad.
  - Corrección (14/10, H7): cada fragmento de `justicia_docs` guarda `nombre_archivo`, `numero_expediente` (el tema) y también la ruta, anidada en `metadata.meta.ruta_archivo`.
  - Andrés considera suficientes `nombre_archivo` y `numero_expediente` (el tema); aún no ve la utilidad de `ruta_archivo`. A tener en cuenta en la spec futura: hoy se usa.
    - Recorrido: `qdrant_backend.py:170,360` → `retriever.py:267` → `document_formatter.py:89-97`.
    - Entra al contexto del LLM como «Ruta:» (`prompts/expediente_prompt.py:275` pide citarla) y de ella se saca el nombre real del archivo.
    - La interfaz arma con ella `/archivos/download?ruta_archivo=…`: quitarla rompería la cita con descarga.
    - `MetadataFields.DOCUMENTO_RUTA` usa la clave plana (trampa de `code-style.md`).
  - Andrés aclaró (14/10) que `numero_archivo` es el mismo `numero_expediente` (el tema); no es un campo nuevo.
  - Va a una spec propia, con su requisito en el ERS. Si cambian los metadatos, hay que volver a vectorizar.
- Expedientes heredados de JusticIA (inventario de T6): unas 264 carpetas en `backend/uploads/` sin tema registrado (la base tiene 5 temas).
  - Por decisión de Andrés (14/10) no se tocan hasta tener la documentación de interés público que los sustituirá; mientras tanto solo se conservan; no se usan en pruebas: las pruebas siguen con datos `PRUEBA` inventados (regla de `testing.md`, confirmada por Andrés el 14/10).
  - Están fuera del repositorio (`.gitignore`: `/backend/uploads/`). Su retiro es ⚠️ y se decide aparte.
- CORS (`main.py:195-200`): `allow_origins=["*"]` con `allow_credentials=True`, combinación insegura; a la spec de autenticación y seguridad (RNF-07).
- Rendimiento: los avatares (~1,6 MB) no se redimensionan al subirse.
- A 616 px, el menú lateral aparece abierto tras recargar y tapa el contenido (RNF-04; sin confirmar si es el comportamiento por omisión).
- Vocabulario heredado (RT-06, RT-07): «casos legales», «Expediente», «Casos Similares» y «Despido laboral» en busqueda-similares; voseo «Elegí o creá un notebook» en `/notebooks`.
- Temas similares lista claves de notebook (`NB-2`): revisar si la búsqueda global puede mezclar documentos de notebooks de otros usuarios (seguridad; spec 004 o de notebooks).
- Chat: el enlace de descarga depende de que el LLM escriba `uploads/…` (no determinista); en el chat de notebooks la fuente no es un enlace.
- Uvicorn `--reload`: `WatchfilesRustInternalError: Cannot allocate memory` al cargar el LLM (presión de memoria de WSL2; puede influir que vigile `backend/uploads/`).
- OCR (menor): el párrafo se duplica en el salto de página y aparece «Á través».
- Notebooks: la interfaz no permite eliminar un notebook (CRUD incompleto); por eso `PRUEBA_004a` quedó vacío. A la spec retroactiva de notebooks.
- Bitácora: la hora del detalle sale 6 h adelantada en toda la bitácora.
  - El backend guarda `datetime.utcnow().isoformat()` sin zona y el frontend la lee como hora local.
- Bitácora de desarrollo: las descargas exitosas muestran nombres de documentos reales (la spec lo permite en los éxitos); esa base no debe publicarse.
- Historial a 616 px: la tabla exige desplazamiento horizontal para ver «Descripción» y el detalle (cumple RNF-04; experiencia mejorable).
- Página de la bitácora: `console.log` de depuración «Estadísticas combinadas».
- Dato (T7): `PDF/Arquitectura C4 - ServIA.pdf` bajó de 1,90 MB a 1,56 MB por la exportación con Word; contenido verificado.
