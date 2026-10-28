# Tareas — Spec 006: Ingesta de los documentos de Nexus
Estado: implementada (28/10/2026); aprobado (27/10/2026). Dudas resueltas por Andrés: U1 = A (clave del notebook propio en Ingesta carga en él; rechazo solo ajeno o inexistente), U2 = B (desborde solo en Ingesta; el del notebook, a `MEMORY.md` en T9). Ver historial de `plan.md`.

Orden: T0 → T1-T5 (bloque 1) → T6-T8 (bloque 2) → T10 (corrección, 28/10) → resto de T9. Detalle en `plan.md` (§ entre paréntesis). Cada tarea empieza por sus pruebas y **las ve fallar, anotando la causa del rojo**; la que pasa desde el inicio se anota como protección.

⚠️ Sin esquema, migraciones, dependencias, prompts, modelos, `docker-compose.yml` ni renombrar «expediente» en código o base. Los agentes no reinician servidores: **Andrés reinicia `backend` y `celery-worker`** tras T1, T2 y T3 (y antes de T9), nunca durante un `npm run e2e`.

**E (cierre estándar de cada tarea)**:
- Rojo y su causa anotados; pruebas existentes intactas (salvo las que fijaban el defecto, plan §9).
- `docker compose exec backend pytest` y `--orden-inverso`: 0 fallos, 0 XPASS, sin residuos; anotar pasan y `xfail`.
- Si toca frontend o API: `npm run e2e` (en `frontend/`): recolectadas, pasan, esperados, omitidas, 0 XPASS, suite, residuos 0, contraseñas 0; las nuevas también solas (`--grep`).
- **Control de tiempo** (tareas con e2e nuevo o ampliado): suite ≤ M + 30 s y ≤ 560 s (M de T0); si no, PARAR y preguntar.
- `docker compose ps` sin reinicios; `curl http://localhost:8000/`; `docker compose logs --tail 100 backend celery-worker` sin errores nuevos; `curl http://localhost:3000/` sigue vivo (nada se mata por nombre).
- Una línea en `MEMORY.md` y parar.

## Antes de empezar (Andrés)
- [x] Aprobar este plan y estas tareas (27/10/2026).

## Bloque 1
- [x] **T0. Línea base (~1,5 h).** RA-02.47
  - Pruebas: ninguna nueva. Dos corridas de `npm run e2e` y una de `pytest` sin cambios; anotar la media M de la suite y los conteos (base esperada: e2e 141 = 133 + 8; pytest 2028 + 45 `xfail`).
  - Hecho cuando: M y conteos anotados aquí; si M > 530 s, PARAR y preguntar (§10).
  - **Resultado (27/10):** e2e 141 recolectadas = 133 pasan + 8 esperados, 0 XPASS, residuos 0, contraseñas 0. Corrida 1: suite 491,2 s (1 fallo transitorio `browserType.launch` en RF-01.40; no es de código); corrida 2: 513,2 s, CORRECTO. **M = 513,2 s** (Andrés, 27/10: solo la corrida limpia; la corrida 1 abortó una prueba por un fallo transitorio de lanzamiento de Chrome en `acceso.spec.js:84`, a vigilar). pytest: 2028 pasan, 45 `xfail`, 0 XPASS, 558 s. Tope para lo nuevo: ≤ 543 s (M + 30); tope absoluto 560 s; límite 600 s sin subir.

- [x] **T1. Tema normalizado en el servidor y rastreo apagado (~3 h).** RF-06.52, RF-06.53, RNF-09.50  ⚠️ archivo nuevo `backend/tests/unitarias/test_ingesta_tema_y_fallo.py`
  - Primero, solo lectura en la base de desarrollo (sin modificarla): intercalación de `T_Expediente.CT_Num_expediente` y `SELECT` con «Políticas»/«Politicas». Si **no** distingue tildes, PARAR y preguntar (R5). Repetir en `servia_pruebas`.
  - Pruebas: `test_tema_de_61_caracteres_400`, `test_tema_se_recorta`, `test_rastreo_activo_se_apaga_con_aviso`, `test_rastreo_ausente_se_apaga_sin_aviso` (unitarias); `test_tema_normalizado_una_carpeta_y_un_valor` (integración).
  - Hecho cuando: rojo y verde (§4.1); E (con e2e: cambia la API). Reinicio de Andrés.
  - **Resultado (27/10):** tildes: la base de desarrollo y el servidor son `SQL_Latin1_General_CP1_CI_AS` (columna del tema igual) y «Políticas» ≠ «Politicas» (R5 = A se cumple; `servia_pruebas` se crea sin `COLLATE`, mismo valor del servidor). Rojo: `test_tema_se_recorta` (3, el tema con espacio se rechazaba con 400), `test_tema_usa_el_nombre_registrado` (AttributeError), 3 de rastreo (ImportError de `apagar_rastreo_externo`) e integración (400 por el espacio; sin el nombre registrado, tema `PRUEBA TEMA LIBRE…` en vez del registrado); `test_tema_de_61_caracteres_400` pasó desde el inicio (protección). Verde tras el código. `test_carga_confinada.py` `B5-espacio-final` fijaba el defecto (RF-06.53) y se sustituyó por `B5-punto-final-tras-recorte`. pytest `--orden-inverso`: 2037 pasan, 45 `xfail`, 0 XPASS, residuos 0 (541 s). e2e: 141 = 133 + 8 esperados, 0 XPASS, preparación 19,3 s, suite 512,7 s (≤ 543), residuos 0, contraseñas 0. La clave de notebook ajeno/inexistente sigue en 404 en el servidor; su mensaje «tema no válido» lo muestra T4 (frontend). Pendiente de Andrés: reiniciar `backend` y `celery-worker` (el worker aún no carga `apagar_rastreo_externo`).

- [x] **T2. El fallo deja el documento en Error con mensaje fijo y causa (~4,5 h).** RF-07.2, RF-07.52, RF-07.54, RF-21.50, RN-01.50
  - Pruebas: quitar `xfail` de `test_documento_queda_en_error` (parametrizada ×4) y de `test_progreso_con_texto_fijo_y_causa` (pasa a RF-07.52); `test_marcar_fallo_texto_fijo_y_causa` y la rama `FAILURE` (unitarias); `test_bitacora_caida_documento_igual_en_error`; `test_fallo_en_notebook_queda_en_error_y_se_quita`.
  - Actualizar `capacidades.spec.js:428-433` y la docstring de `simulados_e2e.py:764` (fijaban el defecto, §9).
  - Hecho cuando: rojo y verde (§4.2); E (con e2e). Reinicio de Andrés.
  - **Resultado (27/10):** rojo: 11 fallos + 1 `xfail`. pytest 2048 pasan + 43 `xfail`, 0 XPASS. e2e 141 = 133 pasan + 8 esperados, suite 475,4 s, CORRECTO. Se alinearon `test_celery_inmediato.py` y dos `RA-02.49` de `capacidades.spec.js` (fijaban el defecto, §9).

- [x] **T3. Reintento interno sin filas ni fragmentos duplicados (~3 h).** RF-07.51
  - Pruebas: `test_reintento_de_la_misma_tarea_una_fila`, `test_recarga_tras_error_fila_nueva` (integración).
  - Hecho cuando: rojo y verde (§4.3; sustituye la comprobación muerta de `celery_tasks.py:133-162`); E (con e2e: ruta de ingesta). Reinicio de Andrés.
  - **Resultado (27/10):** rojo: 3 de 4 (la de recarga tras Error ya pasaba: protección). pytest 2052 pasan + 43 `xfail`. e2e 141 = 133 pasan + 8 esperados, suite 486,1 s, CORRECTO. Ninguna prueba ajustada. Riesgo aceptado W1 (spec, «Decisiones de implementación»).

- [x] **T4. Ingesta: un tema por archivo, confirmación agrupada y sin formato heredado (~6 h).** RF-06.50, RF-06.51, RF-06.52, RF-06.54
  - Pruebas: e2e nueva `RF-06.50 · Ingesta: un tema por archivo y confirmación agrupada` (escritorio); aserción de RF-06.54 en `RF-05.40 · Ingesta: carga mixta` (ambos anchos); `campoDelTema` por rótulo «Tema» (`pantallas.js:93`).
  - Regresión U1 (RF-17.4), dentro de la e2e de RF-06.50: `NB-<id>` del notebook propio → aceptado y listado en ese notebook; `NB-<id inexistente>` → rechazado con «El tema indicado no es válido». Las integraciones de RF-17.4 siguen pasando.
  - Hecho cuando: rojo y verde (§4.4); `npm run lint` y `npm run build` (con `NEXT_DIST_DIR` propio) sin errores; E con control de tiempo.
  - **Resultado (27/10):** rojo: las 3 pruebas fallaban (no existía el rótulo «Tema»). Verde tras el código. e2e 143 recolectadas = 134 pasan + 8 esperados + 1 omitida (la nueva, en 616 px), 0 XPASS, preparación 15,5 s, suite 503,1 s (≤ 543), residuos 0, contraseñas 0. La e2e de RF-06.50 comprueba lo que la pantalla envía por tema (el listado `/archivos/expediente/{tema}/archivos` responde 500 en la instancia aislada: usa `os.getcwd()` y `uploads/` está desviado; hallazgo heredado sin corregir). Sin archivos nuevos.

- [x] **T5. Ingesta: el archivo que falla se ve en Error con su causa (~3 h).** RF-07.50
  - Pruebas: e2e nueva `RF-07.50 · Ingesta: fallo en Error con su causa e imagen Procesada` (escritorio), con PDF dañado + `.txt` válido.
  - Hecho cuando: rojo y verde (§4.5); E con control de tiempo. **Punto de decisión**: horas usadas frente a lo previsto; si el bloque 2 no cabe, preguntar a Andrés y pasar a T9 con el corte (§11).
  - **Resultado (27/10):** rojo: la fila mostraba solo el texto fijo, sin «Causa: …», y el `console.error('[Error técnico …]')` del hook rompía la vigilancia de consola. Verde tras `useFileUploadProcess.js` (muestra el mensaje del servidor si empieza por el texto fijo; si no, el texto fijo; sin `console.error`). e2e 145 recolectadas = 135 pasan + 8 esperados + 2 omitidas, 0 XPASS, preparación 15,6 s, suite 508,5 s (≤ 543; quedan 34,5 s), residuos 0, contraseñas 0. Lint sin errores (1 advertencia heredada de `notebooks/index.js`) y build sin errores. El acompañante es el `.txt`; la PNG llega con T7.

## Bloque 2
- [x] **T6. Aviso largo sin desborde y advertencia de manuscrito (~3 h).** RNF-04.50, RF-10.50
  - Pruebas: aserciones en `RNF-04.40 · aviso accesible y completo`, `RF-11.40 · Ingesta: …` y `RF-05.40 · notebook: carga mixta` (ambos anchos). El desborde se corrige solo en Ingesta (U2); en el notebook solo se prueba la advertencia.
  - Hecho cuando: rojo y verde; E con control de tiempo.
  - **Resultado (27/10):** rojo y verde comprobados (aviso largo sin desborde en Ingesta con `min-w-0` y `[overflow-wrap:anywhere]` en `FilesList.jsx`; advertencia de manuscrito en `DropZone.jsx` y `notebooks/index.js`). e2e 145 recolectadas = 135 pasan + 8 esperados + 2 omitidas, 0 XPASS, preparación 31,0 s, suite 511,6 s (≤ 543; quedan 31,4 s), residuos 0, contraseñas 0, CORRECTO. La primera corrida (568,7 s) fue ruido de la máquina: repetida sin cambiar nada, bajó a 511,6 s.

- [x] **T7. Imágenes en Ingesta (~3 h).** RF-05.50
  - Pruebas: la e2e de RF-07.50 cambia el `.txt` por una PNG (HTR simulado) → Procesada, identificada como imagen; lista con las 6 extensiones.
  - Hecho cuando: rojo y verde; `npm run lint`; E con control de tiempo.
  - **Resultado (27/10):** rojo y verde comprobados en `RF-07.50` (PNG en memoria Procesada, chip «IMAGEN» en la confirmación, 6 extensiones en la lista y en `accept`). e2e 145 = 135 pasan + 8 esperados + 2 omitidas, 0 XPASS, preparación 15,7 s, suite 499,1 s (≤ 543; quedan 43,9 s), residuos 0, contraseñas 0, CORRECTO. lint y build sin errores.

- [x] **T8. Fallos esperados del módulo (~2 h).** RF-05.51, RF-07.53
  - Pruebas: 3 `xfail(strict)` «RF-05.51 · ingesta» en `test_red_cargas_rechazadas.py`; `test_cancelacion_queda_cancelada` `xfail(strict)` «RF-07.53 · ingesta».
  - Hecho cuando: cada una vista en rojo por el motivo correcto; pytest (sin e2e: solo pruebas del backend, sin efecto en la API).
  - **Resultado (27/10):** los 4 `xfail(strict)` vistos en rojo con `--runxfail`. pytest 2052 pasan + 47 `xfail`, 0 XPASS, orden normal e inverso. Sin e2e (justificado: solo pruebas del backend, sin código de producción).

## Corrección (CC1 = A, Andrés, 28/10/2026)
- [x] **T10. Tema nuevo en dos grafías en un mismo Guardar: un solo nombre (~3 h).** RF-06.53, RF-06.52
  - Falla (verificación manual de T9, 27/10): «PRUEBA» y «prueba» nuevos en peticiones simultáneas → fila `PRUEBA` bien, pero Qdrant, `CT_Ruta_archivo` y bitácora del otro documento con «prueba». Causa en plan §4.6.
  - Pruebas (primero, en rojo): integración `test_tema_nuevo_en_dos_grafias_un_solo_nombre` en `test_red_ingesta.py`: dos cargas sin procesar entre medio (orden del Worker), luego procesar → 1 fila, 1 carpeta, 1 valor de `metadata.numero_expediente`, rutas y bitácora con el registrado.
  - Unitaria `test_tema_en_carrera_usa_el_registrado` en `test_ingesta_tema_y_fallo.py` (`IntegrityError` simulado → rollback y nombre del ganador).
  - Actualizar `test_carga_encolada_un_id_por_archivo` (:148), que fijaba el orden viejo (plan §9).
  - Código: servicio `resolver_o_crear_tema` y alta del repositorio que deja pasar `IntegrityError`; la ruta lo llama antes de guardar y encolar (router → servicio → repositorio; nada en el frontend, principio 3). Sin esquema ni migración (basta `uq_expediente_num` con `CI_AS`); sin archivos nuevos. Si resultara imprescindible tocar el esquema, ⚠️ PARAR y preguntar.
  - Hecho cuando: rojo con su causa y verde; E (con e2e: cambia la API; suite ≤ 543 s y ≤ 560 s). Andrés reinicia `backend` y `celery-worker` y repite el caso manual con un tema nuevo.
  - **Resultado (28/10):** rojo: 8. pytest 2055 pasan + 47 `xfail`, normal e inverso. e2e 145 = 135 pasan + 8 esperados + 2 omitidas, suite 475,2 s (la 1.ª corrida tuvo 1 fallo inestable en `notebooks.spec.js:117`; repetida sin cambios). Alineadas `test_carga_encolada_un_id_por_archivo` y `test_subir_con_encolado_interceptado`. Manual con `PRUEBA 3`/`prueba 3` (DD1): OK, tema 70007.

## Cierre
- [x] **T9. Validación, verificación manual, documentación y commits (~6 h).** Todos  ⚠️ archivos temporales `frontend/test-results/manual/PRUEBA_*`; ⚠️ borrar datos de desarrollo de `PRUEBA`, `PRUEBA 2`, `PRUEBA 3` y del notebook `PRUEBA 006` (solo con aprobación de Andrés en ese momento); ⚠️ commit y push con @committer
  - Pruebas: ninguna nueva. pytest, `--orden-inverso` y `npm run e2e` completos; fallos esperados recalculados (≈ 47); conteo por requisito.
  - Manual (§10): ambos roles a 1366 y 616 px; datos en SQL Server, Qdrant y bitácora; Andrés revisa el `.env` real (RNF-09.50).
  - Documentación (§12): spec «implementada»; texto propuesto del ERS/CU entregado (ajustado si hubo corte); `graphify-out/` vía `python.exe` de uv y mapas; `MEMORY.md`, con una línea en «Hallazgos sin corregir» o «Próximos pasos»: el desborde del nombre largo en el aviso del notebook, para la spec de mejoras del notebook (U2); paso operativo del piloto de Nexus para Andrés, con el riesgo RF-06.2.
  - Hecho cuando: suites en verde dentro del presupuesto; limpieza hecha y temas vacíos anotados; veredicto del @reviewer y aprobación de Andrés.
  - **Avance (28/10):** verificación manual hecha: Usuario Gubernamental (27/10, y T10 el 28/10); Administrador (28/10) OK, aviso «Acceso Denegado» visible; `.env` limpio (RNF-09.50).
  - Validación de @reviewer: APROBADO (28/10) con suites propias: pytest 2055 + 47 `xfail`, normal e inverso; e2e 145 = 135 + 8 + 2 omitidas, suite 501,4 s, residuos 0, contraseñas 0; lint y build OK.
  - **Cierre (28/10):** limpieza hecha (EE1 = A): 17 documentos, 14 fragmentos y 4 carpetas borrados; quedan como residuo vacío los temas 70004 `PRUEBA`, 70005 `PRUEBA 2`, 70007 `PRUEBA 3` y el notebook `PRUEBA 006` (80003, tema interno 70006), porque el sistema no tiene borrado ni archivado de notebooks. `graphify-out/` (`python.exe` de uv) y mapas regenerados; `MEMORY.md` y spec marcados «implementada».
  - Pendientes fuera de T9: commits (⚠️, los hace @committer) y el paso operativo del piloto de Nexus (de Andrés).

Total: ~38 h (1,5 + 3 + 4,5 + 3 + 6 + 3 + 3 + 3 + 2 + 6 + 3 de T10). Con corte (T0-T5 + T9 + T10): ~30 h. Plazo compartido con la spec del notebook: ~64 h.
