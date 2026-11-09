# Tareas 009b — Fuentes del notebook
Plan: `plan.md` (§n). Empieza cuando la 009 cierre T7. Entrega 1 ~2 h (T1-T3); entrega 2 ~2 h 45 min (T4-T7); documentación 30 min. Una tarea por llamada del implementer.

## Cierre estándar (se cita como «Cierre»)
1. Pruebas nuevas en rojo antes del código; reportar el fallo.
2. `docker compose exec backend pytest` y `... pytest --orden-inverso`: 0 fallos, 0 XPASS, ningún `xfail` nuevo; reportar pasan / fallan / esperados.
3. e2e (desde `frontend/`) SOLO lo que diga la tarea, con `npm run dev` cerrado y ≥ 2,3 GB libres.
   - Subconjunto: `npm run e2e -- <archivo>` (~1-2 min). Completa: `npm run e2e` (~9-10 min; suite ≤ 720 s).
   - Reportar recolectadas, pasan, fallan, esperados, XPASS, suite, residuos y contraseñas.
4. `docker compose ps` sin reinicios; `docker compose logs --tail 100 backend` sin errores nuevos.
5. Marcar la tarea, anotar la evidencia aquí y una línea en `MEMORY.md`. Sin `chrome-devtools` ni reinicios: la verificación visual es de Andrés.

## Entrega 1 — casilla y menú ⋮ con «Quitar fuente» (sin migración)

- [x] **T1. Selección en el chat del notebook (servidor) (35 min).** RF-11.101, RF-11.102, RF-11.105, RF-11.106, RF-11.107, RNF-07.100, RF-21.102  ⚠️ archivos nuevos `test_fuentes_notebook.py` (unitarias e integración)
  - Pruebas: unitarias `test_seleccion_efectiva_*`, `test_seleccion_formato_422`; integración `test_chat_notebook_respeta_la_seleccion`, `test_seleccion_vacia_o_inefectiva_400`, `test_seleccion_ausente_como_hoy`, `test_seleccion_ignorada_en_general_y_tema`, `test_seleccion_ajena_descartada` (§9).
  - Pasos: `documentos` con `StrictInt`, `seleccion_efectiva`, `SeleccionVacia` y su 400, retriever con `documentos_visibles` (§2).
  - e2e: exento (campo opcional; ausente = hoy; la completa va en T3).
  - Hecho cuando: las pruebas y el Cierre pasan.
  - Evidencia (06/11): pruebas nuevas 27 (16 fallos + 11 errores en rojo antes del código); pytest completo 2325 pasan, 0 fallan, 47 xfail, 0 XPASS, residuos ninguno (822 s); orden inverso: ver MEMORY. e2e exento (campo opcional; ausente = como hoy). Corrección incluida: `DocumentoRepository.listar_por_expediente(solo_procesados=True)` usaba `doc.estado` (inexistente) y daba 500; ahora `estado_procesamiento`.

- [x] **T2. Fila de fuente con menú ⋮ y «Quitar fuente» (35 min).** RF-19.100, RF-19.101, RF-21.103  ⚠️ archivos nuevos `FuenteNotebook.jsx` y `notebooks-fuentes.spec.js`
  - Pruebas: e2e `RF-19.100 · el menú no abre la vista previa ni cambia la casilla` (sin la casilla aún: solo la vista previa).
  - Cambian su expectativa (§8): `pantallas.js:70` y `:84`, `notebooks.spec.js:295`; RF-19.40-42 deben seguir pasando sin tocar sus aserciones.
  - Pasos: `FuenteNotebook.jsx` (nombre, ⋮, `aria-disabled` al quitar), lista en `index.js` (:517-537), quitar el guardia `close chip` (:192) (§5).
  - e2e: subconjuntos `npm run e2e -- e2e/flujos/notebooks.spec.js` y `... notebooks-fuentes.spec.js`.
  - Además: `npm run lint`.
  - Hecho cuando: los subconjuntos, lint y el Cierre pasan.
  - Evidencia (06/11): `notebooks-fuentes.spec.js` en rojo antes del código (2 fallos); luego CORRECTO 2/2; `notebooks.spec.js` CORRECTO 24 recolectadas, 20 pasan, 0 fallan, 0 esperados, 0 XPASS, 4 omitidas, residuos 0, contraseñas 0 (RF-19.40-42 sin tocar aserciones); `chat.spec.js` (usa `fichaDeDocumento`) CORRECTO 14/12 pasan/2 omitidas; lint sin avisos nuevos. Backend no tocado: pytest de T1 vale.

- [x] **T3. Casilla y envío de la selección (40 min + 10 de e2e completo).** RF-11.100, RF-11.102, RF-11.103, RF-11.104, RF-11.106, RNF-04.100, RT-07.100
  - Pruebas: e2e `RF-11.100 · RF-11.102 …`, `RF-11.104 · RF-11.106 …`, `RF-11.103 …`, `RNF-04.100 …` (616 px); completar RF-19.100 con la casilla.
  - Pasos: `Checkbox`, `desmarcadas`, `consultaService.js` (`documentos`), envío desactivado y aviso, `datos.js:99` (§5).
  - e2e: subconjunto mientras se desarrolla; al final UNA corrida completa `npm run e2e` (cierre de la entrega 1).
  - Además: `npm run lint`; `npm run build` con `NEXT_DIST_DIR` distinto o `npm run dev` cerrado.
  - Hecho cuando: e2e «CORRECTO» dentro del límite vigente de 720 s (decisión del 05/11 en la spec 009, ratificada por Andrés el 09/11 para la 009b; la suite dura 651–664 s), lint y build limpios, y Andrés hizo la verificación manual de la entrega 1 (§10).
  - Evidencia (06/11): `notebooks-fuentes.spec.js` en rojo antes del código (9 fallos); luego CORRECTO 9 pasan + 1 omitida. Completa `npm run e2e`: 201 recolectadas, 186 pasan, 0 fallan, 6 esperados, 0 XPASS, 9 omitidas, residuos 0, contraseñas 0, preparación 15,8 s, suite 651,7 s (límite 720 s; la primera corrida dio 664,9 s con 1 fallo: `notebooks.spec.js` RF-15.70 abría un notebook B vacío y B=1 desactiva el envío; ahora B lleva una fuente Procesado). Lint sin avisos nuevos (los de `index.js` :687 y `consultaService.js` :384 ya existían); `npm run build` con `NEXT_DIST_DIR=.next-t3` exit 0 (carpeta borrada). Backend no tocado: pytest de T1 vale. A 616 px la prueba RF-11.103 no cambia de notebook (la lista lateral no se alcanza, RNF-04.60): solo recarga. Verificación manual de la entrega 1 (§10) hecha con el MCP `chrome-devtools` por decisión de Andrés, el 06/11/2026, con su sesión de Usuario Gubernamental: PASA en escritorio (1365 px) y a 616 px, consola sin errores. Casilla marcada por defecto y ⋮ «Quitar fuente» (sin vista previa ni cambio de casilla); con `PRUEBA_b` desmarcada la petición lleva `documentos` [a, c] y la respuesta no la cita; marcada, lleva [a, b, c] y cita `PRUEBA_b.txt`; todas desmarcadas: aviso, botón y Enter no envían (0 peticiones nuevas) y el texto se conserva; cambiar de notebook y recargar vuelven todas a marcadas; nombre de 150 caracteres sin desbordar a 616 px; notebook vacío con el envío desactivado y el aviso; quitar fuentes y eliminar notebooks por la interfaz. Omitido: fuente en Pendiente/Error (no se logra sin trucos).

## Entrega 2 — cambiar el nombre

- [x] **T4. Migración y tipo 21 (25 min).** RN-01.100, RF-21.100  ⚠️ migración nueva y cambio de esquema
  - Pruebas: `test_migracion_tipo_21_y_columna`; cambios de expectativa del catálogo (§8).
  - Pasos: columna en `T_Documento`, migración tras la cabeza de la 009 (§4), `alembic upgrade head` en desarrollo; `TiposAccion` 21, `le=21`, `tiposAccion.js`, `bitacoraService.js`.
  - e2e: exento (solo catálogo; lo cubre la completa de T7).
  - Hecho cuando: `alembic current` en la cabeza nueva y el Cierre pasa.
  - Evidencia (06/11): rojo previo de las 4 pruebas (`test_migracion_tipo_21_y_columna` y 3 de catálogo); `alembic heads`/`current` = `e5a1f7c92b48 (head)` tras reiniciar; columna `CT_Nombre_visible` VARCHAR(500) NULL y tipo 21 en desarrollo; pytest completo 2326 pasan, 47 xfail, 0 XPASS en orden normal (819 s) e inverso (808 s); lint 0 errores.

- [x] **T5. Reglas del nombre y ruta `PUT` (40 min).** RF-19.102, RF-19.106, RF-19.107, RF-19.108, RF-19.109, RNF-07.101, RF-21.101, RF-21.104
  - Pruebas: unitarias `test_extension_de`, `test_renombrar_documento_*`; integración `test_renombrar_rechazos_400`, `test_renombrar_no_disponible_404`, `test_bitacora_renombrar`.
  - Pasos: `extension_de`, `nombre_mostrado`, `mensaje_vacio` en `validar_nombre`, `como_lo_guarda_la_base`, `renombrar` del repositorio, ruta, auditoría e `inventario_rutas.py` (§3, §6). Fuentes en Error primero (sin Qdrant).
  - e2e: exento (ruta nueva sin pantalla aún; la cubre T7).
  - Hecho cuando: las pruebas y el Cierre pasan.
  - Evidencia (06/11): pruebas nuevas 17 (16 en rojo antes del código: `extension_de`/`nombre_mostrado`/`renombrar_documento` no existían y la ruta daba 405; la 17.ª, `mensaje_vacio` de `validar_nombre`, ya pasaba porque la 009 lo dejó); luego 17 pasan. Pytest completo 2350 pasan, 0 fallan, 47 xfail (ninguno nuevo), 0 XPASS, residuos ninguno (816 s); orden inverso igual: 2350 pasan, 47 xfail, 0 XPASS (909 s). `docker compose ps` sin reinicios y registros sin errores. e2e exento. Decisión: una fuente Procesado válida (nombre distinto, sin duplicado) responde 500 `ErrorAlRenombrar` hasta T6 (Qdrant y compensación); los rechazos y «idéntico» sí rigen para Procesado. `PUT` devuelve `DocumentoNotebookResponse` con `nombre_archivo` = nombre mostrado (la `extension` en el listado y en la respuesta es de T6).

- [x] **T6. Fragmentos, compensación y nombre mostrado (35 min).** RF-19.103, RF-19.104, RF-19.105, RF-19.108, casos límite de carga
  - Pruebas: unitaria `test_renombrar_compensacion`; integración `test_renombrar_fuente_procesada`, `test_renombrar_compensa_si_falla_qdrant`, `test_carga_tras_renombrar`.
  - Pasos: `actualizar_nombre_de_documento` (§7.8) y sus simulados; orden y compensación (§3); listado con `extension`; `filename` en la vista previa.
  - e2e: subconjunto `npm run e2e -- e2e/flujos/notebooks.spec.js` (el listado cambia de forma).
  - Hecho cuando: las pruebas y el Cierre pasan.
  - Evidencia (06/11): pruebas nuevas 5 (2 unitarias `test_renombrar_procesado_actualiza_qdrant_antes_que_la_base` y `test_renombrar_compensacion`; 3 de integración) más `test_bitacora_renombrar` actualizada (la respuesta lleva `extension`); las 6 en rojo antes del código (sin `actualizar_nombre_de_documento` ni `extension`); luego pasan. Primera corrida completa: 13 fallos en `test_red_notebooks.py` por la forma exacta del listado (§8: se actualizaron 4 aserciones con `"extension"`, no se borró ninguna). Pytest completo: 2355 pasan, 0 fallan, 47 xfail (ninguno nuevo), 0 XPASS, residuos ninguno (828 s); orden inverso igual: 2355 pasan, 47 xfail, 0 XPASS (840 s). e2e `notebooks.spec.js`: 24 recolectadas, 20 pasan, 0 fallan, 0 esperados, 0 XPASS, 4 omitidas, residuos 0, contraseñas 0, suite 120 s, CORRECTO. Decisiones: el visible/interno anterior es lo que devuelve la compensación; `extension` es obligatorio en la respuesta de listado y de `PUT`; `Content-Disposition` sale codificado (`filename*=utf-8''…`). Sin tocar el frontend (lo hace T7).

- [x] **T7. Interfaz de renombrar (45 min + 10 de e2e completo).** RF-19.102, RF-19.103, RF-19.105, RF-19.107, RF-19.109, RF-19.110, RNF-04.100
  - Pruebas: e2e de la entrega 2 (§9); diferibles solo si hay tiempo.
  - Pasos: `renombrarDocumento` en `notebookService.js`, edición en línea y opción desactivada en `FuenteNotebook.jsx` (§5).
  - e2e: subconjunto mientras se desarrolla; al final UNA corrida completa. Si pasa de 720 s, se repite una vez y decide Andrés.
  - Si se difieren las tres diferibles: exención en `plan.md` §9 con la verificación manual de Andrés y deuda en `MEMORY.md`.
  - Hecho cuando: e2e «CORRECTO», lint y build limpios, y verificación manual de la entrega 2 (§10).
  - Corrección de error RF-19.104 (09/11), hallado en el paso 9 de la verificación manual: tras renombrar `PRUEBA_a.txt`, FUENTES del chat del notebook seguía mostrando el nombre interno. Causa confirmada: `a_fragmento` (`document_formatter.py`) tomaba el nombre del encabezado («Archivo:») del nombre base de `ruta_archivo` (interno) y solo usaba `nombre_archivo` sin ruta; T6 actualiza `metadata.nombre_archivo`, que quedaba ignorado. Regresión escrita primero y vista en rojo: unitaria `test_a_fragmento_cita_el_nombre_visible_y_no_el_de_la_ruta` e integración `test_respuesta_nueva_cita_el_nombre_renombrado` (el modelo recibe `Archivo: <nuevo> |` y `- "<nuevo>"`, y la ruta conserva el interno); la unitaria de respaldos (`..._conserva_los_respaldos_...`) pasa antes y después. Corrección: `archivo = nombre_archivo or archivo or base de la ruta or "N/A"`; sin tocar prompts ni frontend (el listado FUENTES lo escribe el modelo copiando «Archivo:»). La copia anidada `metadata.meta.nombre_archivo` NO se actualiza: nadie la lee, y cambiarla alteraría lo que prueba T6 sin efecto. Sin cambios en citas existentes: en Qdrant de desarrollo, 14 414 fragmentos, 14 412 con `nombre_archivo` igual al nombre base de su ruta, 2 sin ruta (usan `nombre_archivo`), 0 distintos; los documentos antiguos sin `nombre_archivo` siguen con el respaldo de la ruta. Límite conocido: en los chats general y por tema el rótulo del enlace de descarga lo arma el frontend con el nombre base de la ruta (interno), que debe seguir siendo la del archivo en disco; el texto «<nombre>: (<ruta>)» del modelo sí lleva el nombre nuevo. Evidencia: pytest 2358 pasan, 0 fallan, 47 xfail, 0 XPASS, residuos ninguno (854 s) y `--orden-inverso` igual (847 s); e2e completo 207 recolectadas, 189 pasan, 0 fallan, 6 esperados, 0 XPASS, 12 omitidas, residuos 0, contraseñas 0, preparación 18,9 s, suite 664,0 s de 720 s, CORRECTO. Frontend no tocado (sin lint ni build). Verificación manual repetida con el MCP (09/11): notebook «PRUEBA cita renombrada», `PRUEBA_a.txt` renombrada a «PRUEBA renombrada», pregunta por el proyecto Alfa: FUENTES `Notebook "PRUEBA cita renombrada": (PRUEBA renombrada.txt)`; consola sin errores; captura `scratchpad/verif009b2/12_cita_corregida.png`; fuente quitada y notebook eliminado.
  - Verificación manual de la entrega 2 (§10, 09/11, con el MCP y la sesión de Andrés): paso 7 omitido; paso 9 corregido y repetido (PASA, ver arriba). Resto de pasos según el informe anterior.
  - Evidencia e2e completo (09/11): 1.ª corrida falló RF-19.102 (tarea de ingesta `PRUEBA-tarea-33` quedó `fallido` al preparar datos; 686 s); 2.ª falló `carga.spec.js` RNF-04.40 (`/pruebas-e2e/limpiar` 500 por `ResponseHandlingException` de Qdrant; 662 s); ambas ajenas al código de T7 (presión de memoria aparente, equipo de 16 GB). 3.ª corrida, con memoria liberada: 207 recolectadas, 189 pasan, 0 fallan, 6 esperados, 0 XPASS, 12 omitidas, residuos 0, contraseñas 0, preparación 19,3 s, suite 659,2 s, backend de desarrollo 200/200, CORRECTO. Las e2e de T7 se escribieron junto al código, sin rojo propio observado. Pendiente: verificación manual de la entrega 2 (§10) con Andrés.
  - Excepción aceptada por Andrés (09/11): las e2e de T7 se escribieron junto al código, sin rojo propio observado; el @reviewer las evaluó leyendo el código y sí pueden fallar (`toHaveValue(base)`, extensión fija, `aria-disabled`, `PUT` contados, mensajes del servidor).
  - Estado (09/11, previo a la marca): código y 3 e2e de la entrega 2 hechos por el implementer anterior (escritos junto al código: no se vio un rojo propio; se declaró `consola.provocado(/400/)`). Subconjunto `notebooks-fuentes.spec.js`: 16 recolectadas, 12 pasan, 0 fallan, 4 omitidas, residuos 0, contraseñas 0, suite 67,2 s, CORRECTO. Lint: 0 errores (solo avisos previos); build con `NEXT_DIST_DIR`: exit 0. Completa: 2 corridas FALLA, cada una con UNA prueba ajena y distinta (1.ª: tarea de ingesta `fallido` al preparar RF-19.102, suite 686,4 s; 2.ª: `/pruebas-e2e/limpiar` 500 por `ResponseHandlingException` de Qdrant en `carga.spec.js` RNF-04.40, suite 661,8 s); 188 pasan, 6 esperados, 0 XPASS, residuos 0, contraseñas 0. Pendiente: decisión de Andrés y verificación manual.

- [x] **T8. Documentación, memoria y grafo (30 min).** Criterios de finalización  ⚠️ edición del ERS, CU, HU y Modelo Relacional
  - Pasos: §11 sobre copias de los `.docx`; spec en «implementada»; `MEMORY.md`; `graphify update .` y los dos mapas.
  - e2e: exento (solo documentación).
  - Hecho cuando: Andrés revisa los documentos y exporta los PDF.
  - Evidencia (09/11): ERS V1.13 (RF-11, RF-12, RF-19, RF-21, FN-03/FN-04 y matriz; límite del rótulo de descarga en el «Estado actual» de RF-12), CU V1.10 (CU-18 nuevo, FA en CU-09/CU-11/CU-13, paso 1 de CU-13, índice, conteo de 18), HU V1.4 (HU-29, HU-30, criterio en HU-19), MR V1.3 (`CT_Nombre_visible`, tipo 21); diagramas `cu-18`, `cu-11` y el general. Ningún «Estado actual» cerrado. Solo `word/document.xml` (más relaciones y medios del diagrama nuevo); zip y XML verificados; respaldo en el scratchpad `orig009b`. PDF sin exportar (los exporta Andrés).

## Si falta tiempo
- La entrega 1 (T1-T3) se cierra sola: T8 puede documentar solo RF-11, CU-13 y HU-NUEVA-3 y dejar la entrega 2 para otra sesión.
- Diferibles: las tres e2e de T7 y, dentro de T8, la edición de los `.docx` (el texto queda en la spec).
