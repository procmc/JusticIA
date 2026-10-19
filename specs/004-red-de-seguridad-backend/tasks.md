# Tareas — Spec 004: Red de seguridad del backend (flujos críticos con pytest)
Estado: completado (19/10/2026)

> La 004a está cerrada (14/10). La 004 se commitea entera al terminar (@committer, con aprobación de Andrés; nunca push). Evidencia y `MEMORY.md` en términos generales, sin nombrar rutas. Detalle: plan §3-§5, §9 y §10. Decisiones del plan §16 resueltas el 15/10 (1 B, 2 A, 4 B, 5 A, 6 A): archivos de prueba por bloque; ⚠️ «crea archivos» solo en la primera tarea de cada bloque, las siguientes añaden al suyo.

Historial:
- 12/10/2026 — creadas desde la spec aprobada (14 tareas, olas).
- 15/10/2026 — al día con la spec aprobada el 15/10: bloque F en 9a-9d (18 tareas; la 9c se partió en 9c y 9d), notebook propio en T1, ⚠️ revisadas.
- 15/10/2026 — §16 resuelto: archivo de cada tarea explícito, `--orden-inverso` por tarea, 9a (§16.5), 9b (lint), 9d (hora), T14 (corrección editorial de la spec).
- 15/10/2026: aprobado por Andrés con las tareas ⚠️ (T1, T2, T3, T5, T8, 9a, 9c, T10, T11, T14). Implementación desde T1 en una sesión nueva.
- 19/10/2026 — T14: la 9b quedó con aviso fijo cerrable (decisión de Andrés, 15/10 = B); el `npm run build` de 9b y 9d se verifica al cierre con `npm run dev` detenido.
- 19/10/2026 — T14 hecha: validación final APROBADA por el reviewer y cierre aprobado por Andrés; hallazgo de RF-01.2 a la retroactiva de autenticación (19/10 = A).

## Orden (plan §13)
- **Ola 1**: T1 · T2 · T5 → T6 → T7.
- **Ola 2**: T3 (tras T2) → T4 (y T1) · T8 → T9 → 9a → 9b; 9a → 9c → 9d · T10 · T11 → T12 → T13 (tras T1).
- **Ola 3**: T14.
- Las corridas de pytest van de una en una, en el turno que asigna el coordinador (comparten `servia_pruebas`; plan §16.2 = A).

**C — cierre estándar de cada tarea** (cada una lo cita):
1. Pruebas escritas primero y vistas en rojo con su causa; las que pasan desde el inicio, anotadas como caracterización; lo incumplido, `xfail` estricto «<requisito> · <módulo>» sin rutas, solo tras ver el rojo. En el bloque F, la regresión se ve en rojo y luego en verde.
2. `docker compose exec backend pytest` pasa: 0 fallos, 0 XPASS, «Residuos…: ninguno»; pruebas existentes intactas. `--orden-inverso` solo en las tareas marcadas «+ orden inverso» (plan §16.4 = B): T1, la última tarea de cada ola según el turno del coordinador, y T14.
3. Duración ≤ línea base + 3 min (1326 pruebas; D medida en T1) y ninguna prueba de flujo > 30 s (`--durations=25`).
4. `docker compose ps` sin reinicios, `curl http://localhost:8000/` responde, `docker compose logs --tail 100 backend celery-worker` sin errores nuevos.
5. `git diff` solo en los archivos de la tarea; `uploads/` y claves del Redis de desarrollo iguales antes y después.
6. Si tocó el frontend: `npm run build` y `npm run lint` sin errores (plan §16.6).
7. Reporte: cuántas pasan, fallan y son `xfail`.

## Antes de empezar (Andrés)
- [x] Elegir en el plan §16 (15/10/2026).
- [x] Aprobar plan y tareas (15/10/2026).
- [x] `backend` y `celery-worker` en marcha y la suite pasando; anotar la línea base (pruebas y duración D). Medida el 15/10: 1326 pasan, D = 5 min 12 s (300 s de pytest); tras T1: 1340 pasan, 4 min 55 s, e inversa 4 min 38 s.

## Tareas
- [x] **T1. Soporte de los flujos, notebook propio y limpieza ampliada** (30 min). RA-02.13, RA-02.14, RNF-09.1  ⚠️ crea `backend/tests/soporte/flujos.py` y `backend/tests/integracion/test_soporte_flujos.py`; modifica `backend/conftest.py`, `backend/tests/soporte/datos.py`, `backend/tests/unitarias/test_datos.py`.
  - Pruebas: `test_subir_con_encolado_interceptado`, `test_subir_y_procesar_sin_pausas`, `test_notebook_de_prueba_propio`, `test_residuos_con_tema_heredado_nb_y_conversacion`; casos nuevos de `test_datos` con destino falso.
  - Hecho cuando: rojas antes y verdes después; C + orden inverso.

- [x] **T2. Inventario y tabla de clasificación** (25 min). RA-02.12  ⚠️ crea `backend/tests/soporte/inventario_rutas.py` y `backend/tests/unitarias/test_inventario_rutas.py`.
  - Pruebas: `test_tabla_igual_a_rutas_registradas`, `test_ruta_sin_clasificar_se_nombra`; avatares `GET`/`HEAD` como pública deliberada.
  - Hecho cuando: roja antes y verde después (si importar `main` choca con los guardianes, va a integración y se anota); C.
  - Corrección 15/10 (aprobada por Andrés, entre T3 y T4): la renovación de sesión llevaba `estado_actual` pero ya exige sesión (RNF-07.5, RF-01.5); la tabla pasa a `None` y T3 deja de excluirla. Roja (5 XPASS estrictos al quitar solo la exclusión) y verde después.

- [x] **T3. 401 en todo el inventario** (30 min). RNF-07.5  ⚠️ crea `backend/tests/integracion/test_red_acceso.py`. Tras T2.
  - Pruebas: `test_ruta_protegida_sin_token_o_invalido_da_401` (inventario × 4 tokens, sin públicas ni avatares), `test_casos_del_recorrido` (a)-(e).
  - Hecho cuando: verdes o `xfail` «RNF-07.5 · autenticación»; ninguna 5xx; C.

- [x] **T4. Matriz de roles en los flujos críticos** (20 min). RF-02.3. Tras T1 y T3.
  - Pruebas: `test_flujo_critico_con_el_otro_rol_da_403_sin_efectos`, añadida a `test_red_acceso.py` (de T3).
  - Hecho cuando: verdes o `xfail` «RF-02.3 · <módulo>»; C.
  - Resultado 15/10: 15 casos (los 15 flujos críticos exclusivos de un rol), todos dan 403 sin efectos (caracterización; ningún `xfail`). Rojo visto con el token del mismo rol (200/404). Suite: 1660 pasan, 34 `xfail`, 0 XPASS, sin residuos, 5 min 49 s; la más lenta, 8,9 s.

- [x] **T5. Inicio de sesión** (30 min). RF-01.1, RF-01.2, RF-21.7  ⚠️ crea `backend/tests/integracion/test_red_sesion.py` y `backend/tests/unitarias/test_red_sesion.py`.
  - Pruebas: `test_inicio_exitoso_por_rol`, `test_vigencia_por_omision_60_min` (unitaria), `test_tres_fallos_identicos_con_motivo`, `test_una_sola_comparacion_de_hash` (unitaria).
  - Hecho cuando: verdes o `xfail` «RF-01.2 · autenticación» (motivo y tiempo por separado); C.
  - Resultado 15/10: 9 pruebas, 6 pasan (caracterización: token con id, rol y correo, vigencia fijada, último acceso, sin contraseña ni hash, 401 idéntico en los tres casos, una fila por intento, sin secretos en la bitácora) y 3 `xfail` estrictos con rojo visto: vigencia por omisión (hoy 480 min y no 60; «RF-01.1 · autenticación»), motivo distinto por caso (los tres quedan con el motivo genérico) y una sola comparación de hash (el correo no registrado no compara ninguna; ambos «RF-01.2 · autenticación»). El motivo se separó en `test_tres_fallos_registran_motivos_distintos`. Suite: 1666 pasan, 37 `xfail`, 0 XPASS, sin residuos, 5 min 56 s; la más lenta, 8,6 s.

- [x] **T6. Contraseña temporal y cambio obligatorio** (25 min). RF-01.3, RF-01.6, RF-21.7. Tras T5.
  - Pruebas: `test_temporal_pide_cambio_sin_ultimo_acceso`, `test_cambio_obligatorio_con_su_sesion`, `test_temporal_incorrecta_o_igual_no_cambia`, añadidas a `integracion/test_red_sesion.py` (de T5).
  - Hecho cuando: verdes o `xfail` etiquetados; C.
  - Resultado 15/10: 4 pruebas nuevas (la tercera con 2 casos), todas verdes como caracterización, ningún `xfail`. Rojo visto con mutaciones temporales del servicio de autenticación, restauradas y comprobadas con `cmp`: último acceso actualizado con temporal, cambio sin actualizar el último acceso, temporal incorrecta aceptada y nueva igual aceptada. Suite: 1670 pasan, 37 `xfail`, 0 XPASS, sin residuos, 5 min 46 s; la más lenta, 8,9 s (preparación de una prueba existente).

- [x] **T7. Renovación y cierre de sesión** (25 min). RF-01.5, RF-01.4, RF-21.7. Tras T6.
  - Pruebas: `test_renovacion_por_rol`, `test_renovacion_con_token_invalido_da_401`, `test_token_cerrado_da_401`, `test_cierre_con_bitacora_que_falla`, añadidas a `integracion/test_red_sesion.py` (de T5).
  - Hecho cuando: RF-01.5 verde; RF-01.4 `xfail` estricto «RF-01.4 · autenticación»; C + orden inverso si cierra la ola 1 (prevista).
  - Resultado 15/10 (cierra la ola 1): 9 pruebas nuevas (con parámetros: renovación por rol, 4 tokens inválidos, cierre por rol, bitácora que falla, token cerrado en 3 casos). Verdes como caracterización (RF-01.5 y lo que el cierre ya cumple: fila a nombre del usuario sin secretos, éxito con la bitácora fallando). `xfail` estrictos «RF-01.4 · autenticación» (3): tras cerrar, el servidor sigue aceptando el token en una ruta protegida, en la renovación y con la bitácora fallando. Rojo visto con cada mutación sola (rol fijo, mismo token, sin correo, vigencia contada desde el token anterior, renovación sin verificar firma ni vigencia, cierre a nombre de otro usuario); la del registro que falla exige anular las dos capas que tragan el error. Defecto hallado al cerrar: el parche de la bitácora sobre la instancia dejaba el método original tapando el parche de clase de otra prueba (rompía una existente en orden inverso); se parcha la clase. Suite: 1679 pasan, 40 `xfail`, 0 XPASS, sin residuos, 6 min 29 s; inversa igual, 6 min 12 s; la más lenta, 8,8 s (preparación de una prueba existente).

- [x] **T8. Subir → Procesado → fragmentos y tema; tema libre** (30 min). RF-05.1, RF-06.1, RF-06.2, RF-07.1, RF-08.1, RF-21.7  ⚠️ crea `backend/tests/integracion/test_red_ingesta.py`. Tras T1.
  - Pruebas: `test_carga_encolada_un_id_por_archivo`, `test_procesado_con_fragmentos_y_tema_heredado`, `test_segunda_carga_al_mismo_tema_sin_duplicar`, `test_tema_libre_y_chat_acotado`.
  - Hecho cuando: verdes o `xfail` (RF-06.2 solo tras el rojo); C.
  - Resultado 15/10: 5 pruebas (se añadió `test_tema_libre_se_acepta_y_crea_el_tema`; el chat acotado quedó aparte): 4 verdes como caracterización y 1 `xfail` estricto «RF-06.2 · ingesta» (el chat acotado exige el formato heredado y con un tema libre cae al chat general, que trae el documento de otro tema; el control con tema heredado pasa). Rojo visto con mutaciones sueltas, restauradas y comprobadas: un solo archivo encolado, sin fila de carga iniciada, documento que no queda Procesado, número de fragmentos distinto en la bitácora, id de documento equivocado en los metadatos, tema duplicado en la segunda carga, tema con espacios rechazado y filtro del chat por otra clave. La bitácora sí guarda el número de fragmentos (sin `xfail` de RF-21.7). Suite: 1683 pasan, 41 `xfail`, 0 XPASS, sin residuos, 6 min 28 s; la más lenta, 9,2 s (preparación de una prueba existente); la más lenta de T8, 1,4 s.

- [x] **T9. Error de procesamiento sin afectar a otros** (25 min). RF-07.2, RF-21.7. Tras T8.
  - Pruebas: `test_extraccion_que_falla_no_afecta_al_otro` (Procesado con puntos), `test_progreso_con_texto_fijo_y_causa`, `test_fila_de_error_con_la_causa`, `test_documento_queda_en_error`, añadidas a `test_red_ingesta.py` (de T8).
  - Hecho cuando: el otro Procesado verde; progreso y estado Error con `xfail` «RF-07.2 · ingesta» por separado; C.
  - Resultado 15/10: 4 pruebas. Verdes como caracterización: el otro documento queda Procesado (progreso al 100 %, fragmentos solo suyos, relación con el tema; la tarea del que falló termina en fallo y su progreso en «fallido») y la fila de error de la bitácora (a nombre del usuario, con el tema y la causa cruda de la extracción; el otro archivo sin fila de error; ninguna fila con contraseña ni token). `xfail` estrictos «RF-07.2 · ingesta» (2, por separado): (a) el progreso dice «Error crítico procesando …» con el texto de la excepción y no el texto fijo ni la causa clasificada (a), y el estado Error: un fallo de extracción no deja documento. Fallo provocado con un simulado de la extracción solo para el archivo marcado. Rojo visto con mutaciones sueltas, restauradas y comprobadas (ambos fallan, el otro en Error, causa no conservada, sin fila de error) y cada `xfail` pasa con un arreglo temporal. Suite: 1685 pasan, 43 `xfail`, 0 XPASS, sin residuos, 6 min 18 s; la más lenta, 8,4 s (preparación de una prueba existente); las de T9, 1 s (12,7 s la primera por preparación de los embeddings).

- [x] **T9a. Bloque F: carga con aceptados y rechazados** (30 min). RF-05.22, RF-05.23 (contenido), RF-21  ⚠️ crea `backend/tests/integracion/test_red_cargas_rechazadas.py`; modifica `backend/app/routes/ingesta.py`, `backend/app/services/bitacora/ingesta_audit_service.py`, `backend/app/services/documentos/file_management_service.py` y ajusta `test_carga_confinada.py` (plan §16.5). Tras T1 y T8.
  - Pruebas: `test_carga_mixta_a_un_tema`, `test_carga_mixta_al_notebook_propio`, `test_lista_de_identificadores_sin_cambios`, `test_guardado_fallido_y_error_interno_con_motivo_y_fila`, `test_todos_rechazados_exito_sin_confirmacion`, `test_tema_no_valido_sin_conteos`, `test_contenido_para_la_pantalla`.
  - Ajuste §16.5 = A: en `test_error_inesperado_es_generico` (004a), restablecer el encolado interceptado antes de la segunda parte, para que haya un aceptado y se registre la carga iniciada; comprueba lo mismo.
  - Hecho cuando: regresiones en rojo y luego en verde; las de la 004a siguen pasando; C.

- [x] **T9b. Bloque F: Ingesta y NotebookServIA presentan la respuesta** (30 min). RF-05.23, RNF-04.1. Modifica `frontend/hooks/ingesta-datos/useFileUploadProcess.js`, `frontend/components/ingesta-datos/FilesList.jsx`, `frontend/utils/ingesta-datos/iconos.js`, `frontend/pages/notebooks/index.js`. Tras 9a.
  - Pruebas: `test_imagen_pegada_en_el_notebook_llega_a_procesado`, añadida a `test_red_cargas_rechazadas.py` (de 9a; HTR simulado); las de 9a siguen verdes.
  - Lint (§16.6 = A): corregir los 4 errores heredados de `pages/notebooks/index.js` sin cambiar comportamiento.
  - Manual (E3): plan §12.6, parte de Ingesta y notebook, escritorio y 616 px; regresión manual vista antes del cambio.
  - Hecho cuando: C; **implementado, pendiente de la 005** (RF-05.23, RNF-04.1).
  - Hecha (15/10): build pendiente al cierre (se corre al final, con `npm run dev` detenido por Andrés; `npm run lint` ya sin errores).

- [x] **T9c. Bloque F: detalle de carga en la bitácora completa (backend)** (30 min). RF-22.1  ⚠️ crea `backend/app/services/bitacora/detalle_carga.py`, `backend/tests/unitarias/test_detalle_carga.py` y `backend/tests/integracion/test_red_detalle_bitacora.py`; modifica `bitacora_stats_service.py` y `routes/bitacora.py`. Tras 9a.
  - Pruebas: unitarias `test_clasifica_cada_regla`, `test_precedencia_extraccion_con_conexion`, `test_nombre_con_vector_dentro_de_extraccion`, `test_no_reconocido_y_vacio_son_error_interno`, `test_detalle_por_tipo_en_orden`, `test_relleno_omitido`, `test_hora_de_costa_rica`; integración `test_detalle_de_cada_tipo`, `test_causa_sin_texto_de_excepcion`, `test_sin_datos_prohibidos`, `test_otros_consumidores_sin_cambios`, `test_consulta_que_falla_da_500_generico`, `test_usuario_gubernamental_da_403`.
  - Hecho cuando: regresiones en rojo y luego en verde; las pruebas existentes de `/bitacora/registros` siguen pasando; C.

- [x] **T9d. Bloque F: pantalla del detalle de la bitácora** (20 min). RF-22.1, RNF-04.1. Modifica `frontend/services/bitacoraService.js` y `frontend/components/administracion/bitacora/DetalleEvento.jsx`. Tras 9c.
  - Pruebas: las integraciones de 9c siguen verdes (contenido); sin pruebas de JavaScript (E3).
  - Manual (E3): plan §12.6, parte del detalle, con el Administrador, escritorio y 616 px.
  - Hora (Andrés, 15/10 = B): la del detalle es la de Costa Rica, UTC−6 aplicado a la hora UTC guardada. No se compara con el listado (desfase de 6 h, `utcnow()`: hallazgo fuera de alcance, ver T14).
  - Hecho cuando: C; **implementado, pendiente de la 005** (RF-22.1, RNF-04.1).

- [x] **T10. Chat acotado, motor caído y descarga del citado** (30 min). RF-11.1, RF-11.2, RF-12.1, RF-21.7, RNF-09.1  ⚠️ crea `backend/tests/integracion/test_red_chat.py`. Tras T1.
  - Pruebas: `test_contexto_con_frase_y_nombre`, `test_no_mezcla_otro_tema`, `test_eventos_hasta_el_final`, `test_motor_sin_conexion`, `test_respuesta_vacia_cierra`, `test_descarga_del_citado`.
  - Hecho cuando: verdes o `xfail` «RF-11.2 · RAG»; C.

- [x] **T11. Notebook: crear, listar, subir, previsualizar** (30 min). RF-17.1, RF-17.2, RF-18.1  ⚠️ crea `backend/tests/integracion/test_red_notebooks.py`. Tras T1.
  - Pruebas: `test_crear_y_orden_propio`, `test_nombre_vacio_o_espacios`, `test_subir_al_notebook_procesado`, `test_previsualizar_en_linea`, `test_previsualizar_no_procesado`.
  - Hecho cuando: verdes o `xfail` etiquetados; C.

- [x] **T12. Notebook: chat acotado, ajenos y carga a ajeno** (30 min). RF-11.3, RF-17.3, RF-17.4, RNF-07.6. Tras T11.
  - Pruebas: `test_chat_solo_del_notebook`, `test_notebook_ajeno_o_inexistente_sin_contenido`, `test_documentos_de_notebook_ajeno_no_se_entregan`, `test_recurso_ajeno_da_404_identico`, `test_carga_a_notebook_ajeno_da_404`, añadidas a `test_red_notebooks.py` (de T11).
  - Hecho cuando: verdes o `xfail` «<requisito> · notebooks/RAG»; C.

- [x] **T13. Quitar documentos, su error y reintento** (25 min). RF-19.1, RF-19.2. Tras T12.
  - Pruebas: `test_quitar_uno_de_dos`, `test_fallo_al_quitar_y_reintento` (fragmentos y archivo), añadidas a `test_red_notebooks.py` (de T11).
  - Hecho cuando: RF-19.1 verde; RF-19.2 verde o `xfail` estricto; C + orden inverso si cierra la ola 2 (prevista).

- [x] **T14. Corrida completa, verificación manual, documentación y cierre** (30 min). Todos, RA-02.15  ⚠️ borra los datos de la verificación manual; tras ella, commit con @committer. Tras todas.
  - Pruebas: ninguna nueva; suite y `--orden-inverso` con conteo por requisito (al menos una que pasa, `xfail` etiquetado o exención E0-E4); duración frente a la línea base.
  - Trabajo: verificación manual del plan §12 con Ollama real y limpieza; documentación del plan §15 sobre copias (Andrés exporta los PDF); grafo y mapas; `MEMORY.md`; corrección editorial en spec.md («Tareas estimadas» dice 17, son 18): la hace el planner a pedido del coordinador durante T14.
  - Pendiente fuera de alcance: el listado de la bitácora sale 6 h desfasado (`utcnow()`); se corrige después, en una corrección aparte con su prueba de regresión. Se anota en `MEMORY.md`.
  - Hecho cuando: RA-02.15 cumplido; recorrido reportado; spec «implementada» con aprobación de Andrés; RF-05.23, RF-22.1 y RNF-04.1 **implementados, pendientes de la 005** (con su «Estado actual» en el ERS).
  - Resultado (19/10): suite 1764 pasan, 56 xfail, 0 XPASS, residuos ninguno, en ambos órdenes.
    - RA-02.15: 7 min 35 s (reviewer); 8 min 14 s (implementer), 2 s sobre el límite: no bloquea (reviewer y Andrés).
    - `npm run build` y `npm run lint` sin errores; manual del plan §12 con los dos roles y Ollama real.
    - Limpieza de los datos de prueba aprobada y hecha; borrador de documentación en `documentacion_t14.md` (los `.docx` los edita Andrés).
  - Hallazgo (Andrés, 19/10 = A): la medición de tiempos de RF-01.2 del plan §12.4 con contraseña incorrecta y cuenta inactiva no se hizo.
    - Solo 3 intentos con correo inexistente, registrados con el mismo motivo y sin contraseña.
    - Pasa a la retroactiva de autenticación, junto con que la bitácora guarda el correo completo del intento fallido (permitido por RNF-08; a valorar por la Ley 8968).
