# Tareas — Spec 007: Contexto y señales del chat
Estado: aprobado (29/10/2026), junto con `plan.md` (textos de §6; P-1 a P-5 resueltas).

Orden: T0 → bloque A (T1-T7 con T5b, backend) → bloque B (T8-T9, instancia e2e e interfaz) → bloque C (T10-T12, datos y motor real) → T13 (cierre). Cada tarea empieza por sus pruebas y **las ve fallar, anotando la causa del rojo**; la que pasa desde el inicio se anota como protección.

Lectura del implementer (sesión nueva, por secciones): siempre la spec «Definiciones» y la sección del plan que indica cada tarea; nada más salvo que la tarea lo pida.

⚠️ Sin esquema, migraciones, dependencias, modelos, `docker-compose.yml` ni renombrar «expediente». Los agentes no reinician servidores: **Andrés reinicia `backend` y `celery-worker`** donde la tarea lo dice, nunca durante un `npm run e2e`.

**E (cierre estándar de cada tarea)**:
- Rojo y su causa anotados; pruebas existentes intactas, salvo las que fijaban el defecto (plan §13), anotadas.
- `docker compose exec backend pytest` y `--orden-inverso`: 0 fallos, 0 XPASS, sin `xfail` nuevos, sin residuos; anotar pasan y `xfail`.
- Si toca la API o el frontend: `npm run e2e` (en `frontend/`): recolectadas, pasan, esperados, omitidas, 0 XPASS, suite, residuos 0, contraseñas 0; las nuevas también solas (`--grep`).
- **Control de tiempo** (tareas con e2e nuevo): suite ≤ M + 40 s (M de T0); si no, repetir una vez y, si sigue, PARAR y preguntar.
- `docker compose ps` sin reinicios; `curl http://localhost:8000/`; `docker compose logs --tail 100 backend celery-worker` sin errores nuevos; `curl http://localhost:3000/` vivo (nada se mata por nombre).
- Una línea en `MEMORY.md` y parar.

## Antes de empezar (Andrés)
- [x] Aprobar `plan.md` (con los textos de §6) y estas tareas; confirmar el diff de la spec y P-5 (plan §21). Aprobado el 29/10/2026.
- [ ] ⚠️ `.env` de desarrollo: ya tiene `LLM_NUM_CTX=8192` y `LLM_NUM_PREDICT=1024` (plan §4). Andrés lo confirma y lo aplica con el reinicio de T0.

## Bloque 0
- [ ] **T0. Línea base y ventana real del motor (~1,5 h).** RA-02.47, RF-11.63
  - Leer: plan §16 y §18 (R-1).
  - Pruebas: ninguna nueva. Dos corridas de `npm run e2e` y una de `pytest` sin cambios; media **M** de la suite y conteos (base: e2e 145 = 135 + 8 + 2 omitidas; pytest 2055 + 47 `xfail`).
  - Contexto: el implementer recuerda a Andrés confirmar en su `.env` `LLM_NUM_CTX=8192` y `LLM_NUM_PREDICT=1024` (sin leerlo ni mostrarlo). Andrés reinicia `backend` y `celery-worker` y después hace una consulta cualquiera en desarrollo, en el navegador (el agente no recibe contraseñas).
  - Luego el implementer lee `docker compose exec ollama ollama ps` (columna de contexto) y `docker compose logs --tail 200 ollama | grep -i truncating`. Anotar ambos.
  - Hecho cuando: M, conteos y contexto anotados aquí. Si M > 520 s, o si el contexto no es 8192 tras el ajuste del `.env`, PARAR y preguntar.

## Bloque A — backend
- [ ] **T1. Configuración única y coherente (~3 h).** RF-08.62, RF-11.63, RF-11.65 (valores)  ⚠️ archivos nuevos `app/config/contexto_config.py`, `tests/unitarias/test_contexto_config.py`
  - Leer: spec RF-08.62, RF-11.63, RF-11.65; plan §3 (tabla backend), §4, §12 D-3 y D-9.
  - Pruebas: `test_incoherente[tamaño ≤ 0, solapamiento < 0, solapamiento ≥ tamaño, cantidad ≤ 0, caracteres ≤ 0, ventana ≤ 0, reserva ≤ 0, reserva ≥ ventana, presupuesto bajo el mínimo, intervalo ≤ 0, tope ≤ 0, intervalo ≥ tope, no numérico]`, `test_coherente_sin_aviso`, `test_valores_por_omision`, `test_llamada_y_presupuesto_misma_configuracion`.
  - Código: `contexto_config.py`; `config.py:74-75`; `.env.example:50-51` y variables nuevas; `rag_config.py` sin 32.768 ni `TOP_K_*` fijos; `get_llm` lee de `contexto_config`.
  - Hecho cuando: rojo y verde; E con e2e (cambia la cantidad recuperada). Andrés reinicia `backend` y `celery-worker`.

- [ ] **T2. Fragmentación configurable y páginas reales (~2,5 h).** RF-08.60, RF-08.61
  - Leer: spec RF-08.60-61, «Página»; plan §3 (`storage.py`), §12 D-4.
  - Pruebas: ⚠️ `tests/unitarias/test_fragmentacion.py`: `test_tamano_y_solapamiento_configurados` (regresión), `test_paginas_por_posicion_real`; en ⚠️ `tests/integracion/test_refragmentado.py`, `test_documento_prueba_fragmentos_de_1500`.
  - Código: `storage.py:144-218` (configuración, `add_start_index`, ids propios, fechas originales opcionales).
  - Hecho cuando: rojo y verde; E (sin e2e: el Worker no cambia la API; justificarlo). Andrés reinicia `celery-worker`.

- [ ] **T3. Presupuesto y armado de la entrada (~4 h).** RF-11.61, RF-11.62 (cálculo), RF-11.65 (selección), RF-12.60, RF-12.62  ⚠️ archivos nuevos `services/RAG/presupuesto_contexto.py`, `tests/unitarias/test_presupuesto_contexto.py`
  - Leer: spec «Definiciones», RF-11.61-62, RF-11.65, RF-12.60, RF-12.62, «Casos límite»; plan §5.
  - Pruebas: `test_historial_largo`, `test_fragmentos_de_sobra`, `test_ambos`, `test_historial_corto_cede`, `test_mensaje_mayor_que_20`, `test_fragmento_grande_saltado`, `test_justo_bajo_el_limite_llama`, `test_justo_sobre_el_limite`, `test_encabezado_y_sin_rastros_de_omitidos`, `test_lista_solo_enviados`, `test_lista_dentro_del_presupuesto`, `test_notebook_bajo_el_limite_cabe_uno`, `test_cantidad_recuperada[>8, 3, 0, -1]`, `test_reformula_con_dos_mensajes[3 chats]`, `test_mensajes_enormes_1_o_0`, `test_sin_historial_no_reformula[3 chats]`.
  - Código: solo el módulo puro (nadie lo usa todavía).
  - Hecho cuando: rojo (`ImportError`) y verde; E (sin e2e: módulo sin uso en la API).

- [ ] **T4. Textos de instrucciones nuevos (~2 h).** RF-12.61, RF-11.66 (texto)  ⚠️ prompts; ⚠️ archivo nuevo `tests/unitarias/test_instrucciones_chat.py`
  - Leer: spec RF-12.61, RF-11.66; plan §6 (textos literales aprobados).
  - Pruebas: `test_instrucciones_estructura[general, tema, notebook, reformulación]`: tamaño ≤ 20 % (tema de 60 y notebook de 255 caracteres), cada regla de RF-12.61 presente, sin formas de voseo (plan §13), reformulación ≤ respuesta de su chat.
  - Código: sustituir los textos en `answer_prompt.py`, `expediente_prompt.py`, `notebook_prompt.py`, `contextualize_prompt.py` por los de §6, como texto con reemplazo (sin `ChatPromptTemplate`); conservar `reformular_referencia_imagen`. Si un texto no cabe, PARAR: no se edita sin aprobación.
  - Hecho cuando: rojo y verde; E (sin e2e: los chats aún no usan los textos nuevos si T5 no está; anotar).

- [ ] **T5. Los tres chats usan el armado (~6 h).** RF-11.60, RF-11.65, RF-11.66 (general), RF-12.60, RF-12.62  ⚠️ aplica los prompts de T4
  - Leer: spec RF-11.60, RF-11.65-66, RF-12.60, RF-12.62; plan §2, §5, §7 (solo «Historial»), §12 D-1.
  - Pruebas (primero): `test_entrada_dentro_del_presupuesto[general, tema, notebook]` y `test_fragmento_una_sola_vez` (regresión: hoy 5 y 7 copias); por chat, `test_cantidad_recuperada` y `test_respaldo_no_supera`. `LLMSimulado` (`tests/soporte/simulados.py:454`) captura cada llamada.
  - Código: `rag_chain_service.py:275-551`, `general_chains.py`, `expediente_chains.py`, `notebook_chains.py`, `formatted_retriever.py`, `document_formatter.py`, `retriever.py`, `search_strategies.py:128`, `rag.py:89-95, :154`. Quitar la búsqueda aparte del notebook. Tema y notebook conservan por ahora su lectura por número (la cambia T5b).
  - Regresión de la 004/005: `test_red_chat.py`, `test_aislamiento_notebooks.py`, `test_red_notebooks.py` y `RF-11.40` siguen pasando.
  - Hecho cuando: rojo y verde; E con e2e. Andrés reinicia `backend` y `celery-worker`.

- [ ] **T5b. Relevancia y reformulación en el chat por tema y el notebook (~2,5 h).** RF-11.69, RF-11.66 (tema y notebook)
  - Leer: spec RF-11.66, RF-11.69; plan §5.1, §12 D-11 y D-13.
  - Pruebas (primero): en `test_chat_contexto.py`, `test_recupera_por_relevancia[tema, notebook]` (regresión: hoy el fragmento de número alto no llega), `test_no_mezcla_otro_tema`, `test_pregunta_sin_relacion_trae_8`; en `test_presupuesto_contexto.py`, `test_tema_y_notebook_sin_umbral`, `test_reformula_con_dos_mensajes[tema, notebook]`, `test_notebook_reformula_la_adaptada`.
  - Código: `retriever.py:142-198` (búsqueda filtrada sin umbral en el chat; `_get_expediente_documents` solo para el resumen); los flujos de tema y notebook en `rag_chain_service.py` llaman a la reformulación de §5.1.
  - Hecho cuando: rojo y verde; las pruebas del resumen (004b) y `test_aislamiento_notebooks.py` siguen pasando; E con e2e. Andrés reinicia `backend`.

- [ ] **T6. Flujo del turno: etapas, señal de vida, tope, desconexión, historial y bitácora (~7 h).** RF-11.62, RF-11.64, RF-11.68, RF-16.60, RF-16.62, RF-21.60
  - Leer: spec RF-11.62, RF-11.64, RF-11.68, RF-16.60, RF-16.62, RF-21.60; plan §7, §12 D-6, D-7 y D-12, §18 R-3.
  - Pruebas: ⚠️ `tests/unitarias/test_flujo_consulta.py`: `test_etapas_en_orden` (regresión), `test_error_del_motor_tras_dos_etapas`, `test_senal_de_vida_cada_intervalo`, `test_tope_cancela` (reloj controlable). ⚠️ `tests/integracion/test_chat_contexto.py`: `test_pregunta_larga_solo_error`, etapas por chat, `test_senal_de_vida_con_motor_retenido`, `test_tope_libera_el_motor`, `test_desconexion_antes_y_despues_cancela`, `test_historial_solo_turnos_terminados[...]`, `test_bitacora_por_turno[3 chats × terminado, rechazo, tope, error; desconexión]`.
  - Apoyo: `LLMSimulado` con `_astream`, retención y registro de la cancelación.
  - Código: orquestador en `general_chains.py`; `rag.py:163-202` (registrador al final); `rag_audit_service.py:100` (`motivo`); `session_store.py` (guardar en FIN). Si la desconexión no se puede provocar en la integración (R-3), PARAR y preguntar.
  - Hecho cuando: rojo y verde; E con e2e (ajustar solo las pruebas que fijaban `chunk` como primer evento). Andrés reinicia `backend`.

- [ ] **T7. Resumen dentro del presupuesto (~3 h).** RF-20.60, RF-20.61, RF-20.62
  - Leer: spec bloque E; plan §8.
  - Pruebas: `test_resumen_dentro_del_presupuesto` y `test_resumen_fragmentos_enteros_en_orden` (regresiones), `test_tema_corto_completo`, `test_instrucciones_solas_no_llama` (en `test_presupuesto_contexto.py`); `test_resumen_500_literal` (en `test_chat_contexto.py`).
  - Código: `summary_generator.py:169-265`, `similarity_prompt_builder.py:163-183`, `chunk_context_builder.py:83-109`. El texto del resumen no cambia; si parece que debe acortarse, PARAR.
  - Hecho cuando: rojo y verde; E con e2e. Andrés reinicia `backend`.

## Bloque B — instancia e2e e interfaz
- [ ] **T8. Capacidades de la instancia e2e (~3 h).** RA-02.49 (apoyo de RF-11.64, 67, RF-16.40, 60, 62)
  - Leer: plan §3 (tabla de pruebas y frontend), §16.
  - Pruebas: casos nuevos en `capacidades.spec.js` (`RA-02.49 · …`): programar señal de vida y tope, modo mudo, pausa entre etapas, evento desconocido; cada uno se restablece al limpiar.
  - Código: `tests/instancia_e2e/simulados_e2e.py`, `control.py`; `frontend/e2e/soporte/control.js`. Nada en `main`.
  - Hecho cuando: rojo y verde; E con e2e y control de tiempo.

- [ ] **T9. Interfaz: etapas, plazo con cualquier dato, errores y avisos (~6 h).** RF-11.64, RF-11.67, RF-16.40, RF-16.60, RF-16.61, RF-16.62, RF-11.62, RNF-04.60  ⚠️ archivo nuevo `frontend/e2e/flujos/chat.spec.js`
  - Leer: spec bloque C y RNF-04.60 (matriz); plan §10, §16.
  - Pruebas (primero, en rojo): las 12 ejecuciones de la matriz (plan §16).
  - Código: `consultaService.js:199-217`, `messageUtils.js:171-285`, `TypingIndicator.jsx`, `MessageBubble.jsx` (y `Chat.jsx`, `pages/notebooks/index.js:285-300` si hace falta pasar la etapa).
  - Hecho cuando: rojo y verde; `npm run lint` y `npm run build` (con `NEXT_DIST_DIR` propio) sin errores; E con control de tiempo (≤ M + 40 s).

## Bloque C — datos y motor real
- [ ] **T10. Procedimiento de re-fragmentado en el entorno aislado (~5 h).** RF-08.63, RN-01.60  ⚠️ archivo nuevo `app/services/ingesta/refragmentado.py`
  - Leer: spec RF-08.63, RN-01.60; plan §9, §12 D-8.
  - Pruebas: `test_cli_exige_temas` (unitaria); en `test_refragmentado.py`: tema indicado (≤ 1.500, mismas filas y metadatos), otro tema intacto, archivo faltante, inserción fallida (conservan los anteriores, sin restos), dos corridas iguales, simulación sin cambios, duplicados de una corrida fallida limpiados.
  - Código: el módulo y lo que necesite de `qdrant_backend.py` (leer puntos de un documento; borrar por ids). Solo se ejecuta en `servia_pruebas` y, en desarrollo, **solo** `--simular`.
  - Manual: simulación en desarrollo con los tres temas de Nexus = 27 documentos y 48 fragmentos.
  - Hecho cuando: rojo y verde; simulación anotada; E (sin e2e: sin efecto en la API; justificarlo).

- [ ] **T11. CF-1: conteo contra el motor real (~3 h).** CF-1 (RF-11.60, RF-20.60)  ⚠️ archivos nuevos `tests/motor_real/conftest.py`, `tests/motor_real/test_conteo_motor_real.py`
  - Leer: spec «Criterios de finalización» (CF-1), «Conteo»; plan §15, §12 D-10.
  - Pruebas: `test_conteo_sin_cache_es_estable` (primero), `test_entrada_maxima[chat × reformulación/respuesta, resumen] × [narrativo, denso]`.
  - Código: marcador `motor_real` en `marcadores.py:11-15` y `pytest.ini:9`.
  - Hecho cuando: el comando por omisión no la recolecta; `pytest -m motor_real` pasa una vez con su salida (conteo real y estimado por llamada) anotada aquí. Si el real supera al estimado, PARAR y preguntar (Q-B). E (sin e2e).

- [ ] **Antes de T12 (Andrés):** aplicar la primera parte del Anexo (plan, Anexo C.1: principio 5, «Datos» de `CLAUDE.md`, RN-01 y RNF-10 del ERS) y aprobar la lista de temas: NEXUS-Avisos-Corte, NEXUS-Circulares-DE, NEXUS-Circulares-SC.

- [ ] **T12. Re-fragmentar Nexus y recargar las tres circulares (~2 h).** RF-08.63, RN-01.60, P7  ⚠️ borra fragmentos de Qdrant en desarrollo (solo esos tres temas, con la lista aprobada)
  - Leer: plan §9, §17 (pasos 3 y 10).
  - Pruebas: ninguna nueva.
  - Pasos: conteo de puntos de la colección y de cada tema; simulación (= 27); corrida real; repetir el conteo. Recarga de SC 182, 183 y 177 por Ingesta (agente con el MCP, sesión de Andrés, `/add-dir` de `~\Documents\ServIA-fuentes`).
  - Hecho cuando: mismas filas, fragmentos ≤ 1.500, puntos fuera de Nexus iguales, las tres circulares Procesado con fila nueva (las anteriores en Error).

## Cierre
- [ ] **T13. Verificación manual, carga de los 128 PDF, `.env.example`, documentación y commits (~7,5 h).** Todos, RNF-09.60  ⚠️ archivos temporales `PRUEBA_*` de la verificación; ⚠️ configuración: `backend/.env.example:38-44` al motor local (`http://ollama:11434`, `llama3.1:8b`, clave vacía; plan §3); ⚠️ borrar los datos `PRUEBA` de desarrollo (con aprobación de Andrés en ese momento); ⚠️ commit y push con @committer
  - Leer: plan §17, §19, Anexo C.2.
  - Pruebas: ninguna nueva. pytest, `--orden-inverso`, `npm run e2e` completos; conteo por requisito; CF-1 vigente.
  - Manual: plan §17 completo (ambos roles, 1366 y 616 px; datos en SQL Server, Qdrant y bitácora), incluida la carga de los 128 PDF en tandas de ≤ 10 (P-4 = A) y la revisión de `.env.example` (paso 12).
  - Documentación: entregar a Andrés el Anexo C.2 (con la viñeta de CF-1); spec 005 (RF-16.40), spec 006 (L231 «(salvo EEE1)» y resultados del piloto); spec 007 «implementada»; `graphify-out/` y mapas; `MEMORY.md` con los Error nuevos de la carga.
  - Hecho cuando: suites en verde dentro del presupuesto; limpieza hecha; veredicto del @reviewer y aprobación de Andrés.

Total: ~58 h (1,5 + 3 + 2,5 + 4 + 2 + 6 + 2,5 + 7 + 3 + 3 + 6 + 5 + 3 + 2 + 7,5). Plazo compartido con la spec del notebook: ~64 h (quedan ~6 h; plan §18 R-7).
