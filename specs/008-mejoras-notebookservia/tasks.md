# Tareas — Spec 008: Mejoras de NotebookServIA
Estado: aprobado (04/11/2026), junto con `plan.md`. Decisiones: P-1 = A (evidencia por `Grep`), P-2 = A (`Registro_Indicaciones_2026/temporal_008/`), P-3 = A (pytest solo en T0 y T3); detalle en el plan §13.

Orden: T0 → T1 (A) → T2 (C) → T3 (suite y verificación conjuntas) → T4 (CF-1) → T5 (cierre). Total ~4,25 h.
Lectura del implementer: la sección de la spec y del plan que cita cada tarea; nada más salvo que la tarea lo pida.
Sin esquema, migraciones, dependencias, prompts, modelos ni `docker-compose.yml`. Los agentes no reinician servidores ni matan procesos por nombre.

**E (cierre estándar)**, con las reglas del plan §6:
- Rojo y su causa anotados; pruebas existentes intactas salvo las que cita la tarea.
- Antes de cada suite: memoria libre (pytest ≥ 1,5 GB, e2e ≥ 2,3 GB), ninguna otra suite en marcha, `npm run dev` cerrado durante el e2e.
- `docker compose ps` sin reinicios; `curl http://localhost:8000/`; `docker compose logs --tail 100 backend` sin errores nuevos; servicios con `docker compose start`, nunca `up -d`.
- `npm run lint` sin advertencias nuevas en los archivos tocados.
- Una línea en `MEMORY.md` y parar.

- [x] **T0. Línea base (~0,4 h).** RNF-04.70 (presupuesto)
  - Pruebas: ninguna nueva. `docker compose exec backend pytest` (una vez) y `npm run e2e` (una vez), sin cambios.
  - Hecho cuando: anotados aquí pytest (pasan, `xfail`, 0 XPASS) y e2e (recolectadas, pasan, esperados, omitidas, XPASS, residuos, contraseñas, suite). Si la suite ≥ 560 s o hay fallos, PARAR y preguntar.
  - **Hecho (04/11/2026).** Memoria WSL libre: 7,2 GB antes de pytest; 6,9 GB antes del e2e. pytest: 2231 pasan, 0 fallan, 47 xfail, 0 XPASS, 0 omitidas, 34 deseleccionadas, 798 s, «corrida correcta», sin residuos. e2e: 165 recolectadas, 153 pasan, 0 fallan, 8 fallos esperados, 0 XPASS, 4 omitidas; preparación 24,8 s; suite 541,9 s; residuos 0; contraseñas en artefactos 0; CORRECTO.

- [x] **T1. Confirmación al quitar (~1 h).** RF-19.40, RF-19.70, RF-21.70, RNF-04.70 (hecha 04/11/2026: rojo, XPASS y verde en `notebooks.spec.js`, 22/22; lint sin errores nuevos)
  - Leer: spec A; plan §3 y §5 (filas RF-19 y RF-21).
  - Pruebas (primero, en «RF-19.40 · confirmación…», `notebooks.spec.js:254`): título, cuerpo exacto y botones; cancelar sin DELETE ni registro; sin desborde a 616 px; doble clic = 1 DELETE, ficha fuera, sin cita; segundo documento con `retener_quitar` (ambos deshabilitados); 1 registro «Quitar Documento de Notebook».
  - Rojo: `npm run e2e -- --grep "RF-19.40"` sigue como fallo esperado. Código (`index.js`, plan §3) → XPASS → quitar `fallaEsperada`.
  - Hecho cuando: `npm run e2e -- e2e/flujos/notebooks.spec.js` verde (RF-19.41, RF-19.42, RNF-07.40 incluidas) y E.

- [x] **T2. Textos sin voseo (~0,6 h).** RT-07.70, RNF-04.70 (hecha 04/11/2026: rojo 8 fallos, verde 34 pasan, 2 omitidas; lint sin errores nuevos)
  - Leer: spec C; plan §4 y §5 (fila RT-07.70).
  - Pruebas (primero): textos nuevos en `notebooks.spec.js:32,68,79` y `chat.spec.js:42`; «Elija o cree…» visible; `exigirSinVoseo` (nuevo en `pantallas.js`) en lista vacía, notebook abierto y revisión; arrastre con `dispatchEvent('dragover')`.
  - Rojo: esas pruebas fallan por el texto. Código: los seis textos de `index.js`.
  - Hecho cuando: `npm run e2e -- e2e/flujos/notebooks.spec.js e2e/flujos/chat.spec.js` verde; `Grep` de las formas buscadas en `index.js` = 0 (exención P-1); E.
  - Corrección fase 6 (04/11/2026): e2e del aviso de arrastre de RT-07.70 (`dragover`/`dragleave` sintéticos con `DataTransfer` en «RF-17.40 · crear con botón y con Enter», sin `drop`).
    - Rojo: con la cadena esperada alterada, 2 fallan (`toBeVisible`); restaurada, `notebooks.spec.js` verde: 22 pasan (suite 200,8 s).
    - Desviación, RF-01.43 «el siguiente inicio de sesión no muestra el panel»: prueba inestable previa. Fallaba solo en la suite completa (escritorio) por una carrera de navegación: el `goto` a `/auth/login` chocaba con la redirección del `signOut` («interrupted by another navigation»). Corrección solo en la prueba (`acceso.spec.js`: espera la redirección y el título de inicio de sesión antes de `clearCookies`). Aislada, 3 de 3 verdes (12 pasan, 2 fallos esperados).
    - Recorte de contingencia aplicado (dos corridas seguidas de 600,8 s y 598,7 s > 569 s): «RF-17.40 · otro usuario no lo ve», «RF-18.40 · Pendiente y Error no se abren» y «RNF-07.40 · documento quitado en otra pestaña» corren solo en escritorio (`test.skip` por proyecto `pequena`, como el chat del notebook).
    - Corrida final `npm run e2e`: CORRECTO; 165 recolectadas, 152 pasan, 0 fallan, 6 fallos esperados, 0 XPASS, 7 omitidas, preparación 15,0 s, suite 499,4 s (≤ 569 s), residuos 0, contraseñas 0. `npm run lint`: 0 errores, 1 aviso (`no-img-element` en `index.js:560`).

- [x] **T3. Suite completa y verificación manual de A y C (~0,9 h).** RF-19.40, RF-19.70, RF-21.70, RT-07.70, RNF-04.70, RN-01.70 (hecha 04/11/2026)
  - Pruebas: pytest normal y `--orden-inverso` (mismo conteo que T0); `npm run e2e` completo: «CORRECTO», un fallo esperado menos que T0, suite ≤ 569 s (si no, repetir una vez; contingencia solo si ambas pasan). `npm run build` con `NEXT_DIST_DIR` propio. `git diff --stat`: solo los archivos del plan §2.
  - Evidencia parte 1 (04/11/2026, dev cerrado, memoria WSL 7,2-7,5 GB antes de cada suite): pytest 2231 pasan / 0 fallan / 47 xfail / 0 XPASS / 0 omitidas, 809,9 s, residuos ninguno; `--orden-inverso` igual, 848 s. e2e corrida 1: 165 recolectadas, 155 pasan, 0 fallan, 6 fallos esperados (8 → 6: RF-19.40 en 2 proyectos), 0 XPASS, 4 omitidas, preparación 19,4 s, suite 573,9 s (> 569), residuos 0, contraseñas 0, CORRECTO; corrida 2: igual, suite 558,7 s (≤ 569), CORRECTO; sin recorte de contingencia. `npm run build` exit 0; `npm run lint` exit 0 (solo avisos heredados, incl. `<img>` en notebooks/index.js:560); backend 200, `docker compose ps` sin reinicios.
  - Evidencia parte 2 (rol Usuario Gubernamental, 04/11/2026, 1366 y 616 px): cuadro con título «Quitar documento», cuerpo exacto y botones sin desborde; «Cancelar» sin DELETE; «Quitar» un solo DELETE y el documento sale; bitácora: un registro «Quitar Documento de Notebook» por documento (2 de 2); textos «Elija o cree…», «revise antes de subir:» y placeholder nuevos; consola sin errores ni advertencias; Qdrant `NB-90004` = 0 fragmentos. Residuo: notebook `PRUEBA 008 manual` (id 90004). Pendiente: «Todavía no tiene notebooks» (e2e), arrastre y segundo rol.
  - Evidencia parte 2 (rol Administrador, 04/11/2026, 1366 y 616 px): `/notebooks` redirige a `/?error=unauthorized` con el aviso «Acceso Denegado» (RN-03) y NotebookServIA no aparece en su menú (solo Inicio y Administración); en la bitácora (`/administracion/bitacora`) hay exactamente dos filas «Quitar Documento de Notebook» de `NB-90004`, una por documento (150149 y 150150), legibles a ambos anchos (a 616 px la tabla se desplaza dentro de su contenedor, sin desborde de la página); consola sin errores (solo la advertencia heredada de proporción de imagen del pie).
  - Manual: plan §8 (Andrés inicia sesión; 1366 y 616 px; dos roles; consola).
  - Hecho cuando: evidencia de ambas suites y de la verificación manual anotada aquí, y E.

- [x] **T4. CF-1: imagen en el notebook (~0,75 h).** RF-05, RF-09, RF-21, RN-01.70  ⚠️ archivo nuevo (PNG temporal) y carpeta `Registro_Indicaciones_2026/temporal_008/` (P-2) (hecha 04/11/2026)
  - Leer: spec «Criterios de finalización», CF-1; plan §7.
  - Pruebas: ninguna automatizada (verificación manual de la spec). `git check-ignore -v` sobre la carpeta antes de crear el PNG.
  - Orden: memoria ≥ 1,5 GB, sin suites → `docker compose start tika celery-worker servidor-htr` → PNG → subir → Procesado → cadena en Qdrant → `docker compose stop servidor-htr celery-worker` → «¿Qué dice la imagen?» (1366 y 616 px) → bitácora (carga y consulta) → quitar desde la interfaz → `docker compose stop tika`.
  - Hecho cuando: respuesta con la cadena (o hallazgo anotado para Andrés), 0 fragmentos del notebook en Qdrant, PNG y carpeta borrados (`git status` limpio de ellos) y E.
  - Evidencia (04/11/2026, rol Usuario Gubernamental, notebook `PRUEBA 008 manual`, `NB-90004`): PNG tipeado (`.gitignore:20`) con la cadena `ZAFIRO-7342-QUETZAL`. Memoria WSL antes del HTR: 1,3-1,6 GB libres y 4,1 GB disponibles (HTR, worker y Tika ya estaban arriba, Ollama vacío, sin suites); tras detener el HTR: 5,3 GB libres. Subida: Procesado (HTR 4 líneas, 162 caracteres, 43 s en total); Qdrant `metadata.numero_expediente = NB-90004`: 1 fragmento con el texto exacto «PRUEBA 008 - Informe de inventario Codigo de control: ZAFIRO-7342-QUETZAL El almacen central tiene doce cajas de papel. La revision se realizo en la bodega norte.» (sin errores de reconocimiento). «¿Qué dice la imagen?»: a 1366 px (~30 s, modelo en frío) y a 616 px (~5 s) la respuesta transcribe el texto completo con la cadena y cita «Notebook "PRUEBA 008 manual": (prueba_008.png)»; consola sin errores ni advertencias; sin desborde a 616 px. Bitácora: 4 «Carga de Documentos» (2 por la subida y 2 del worker), 2 «Consulta RAG» y 1 «Quitar Documento de Notebook» (documento 150151). Limpieza: quitado desde la interfaz con confirmación; Qdrant `NB-90004` = 0; PNG y carpeta borrados (`git status` sin rastro); `servidor-htr` detenido (`celery-worker`, Tika y el resto sin cambios); backend 200 y `npm run dev` responde (307 a inicio de sesión).

- [x] **T5. Propuesta de documentación y cierre (~0,6 h).** RF-19, RF-05, RT-07 (hecha 04/11/2026: aplicadas P1, P2, P3 y P6 con RF-19 = A y RT-07.70 = A, es decir, no se añade al ERS; ERS V1.10 y CU V1.7 con su PDF; spec en «implementada»; MEMORY y graphify-out actualizados)
  - Leer: plan §9.
  - Pruebas: ninguna.
  - Hecho cuando: propuesta de texto para ERS (RF-19, RF-05, y RF-19.70 y RT-07.70 si Andrés aprueba) y CU (CU-11 p. 2, CU-09 FA-05) entregada a Andrés; `graphify-out/` actualizado (grafo, `generar_mapa.py`, `generar_mapa_pruebas.py`); spec en «implementada»; `MEMORY.md` actualizado.

### Propuesta T5 (aprobada y aplicada por Andrés el 04/11/2026: RF-19 = A, RT-07.70 = A)
Fuente: textos de `graphify-out/documentacion_texto/` (ERS V1.9, CU V1.6, HU V1.2). Nada aplicado todavía.

**P1. ERS, RF-19 (Eliminación de documentos del notebook).**
- «Estado actual», antes: «Estado actual: la eliminación se ejecuta sin solicitar confirmación. Esta ausencia está verificada de extremo a extremo por una prueba que falla a propósito (RF-19.40, spec 005b).»
- Después (opción A, recomendada): el párrafo se elimina.
- Después (opción B): «Estado actual: la confirmación (título, nombre del documento, una sola solicitud ante un doble clic y documento deshabilitado mientras se quita) está implementada y verificada de extremo a extremo en escritorio y a 616 px (spec 008).»
- Línea de estado, antes: «Prioridad: Media Estado: Parcial» → después: «Prioridad: Media Estado: Implementado».
- RF-19.70 (solo si Andrés lo aprueba), al final de «Reglas y validaciones», texto nuevo: «La confirmación se titula "Quitar documento" y ofrece "Quitar" y "Cancelar"; un doble clic en "Quitar" envía una sola solicitud, y cada documento que se está quitando conserva su propio estado deshabilitado.»

**P2. ERS, RF-05 (Carga de archivos multiformato), «Estado actual».**
- Antes (última frase): «El aviso con un nombre de archivo muy largo se desborda a 616 px (pendiente de los ajustes gráficos).»
- Después: esa frase se conserva y se añade: «En NotebookServIA, una imagen con texto tipeado cargada con "Subir documentos" está verificada de punta a punta (spec 008): queda Procesado y la respuesta del chat del notebook recoge el texto reconocido y cita la imagen como fuente. Pegar (Ctrl+V) o arrastrar una imagen sobre el chat todavía no tiene prueba de extremo a extremo; solo la tiene el aviso que aparece al arrastrar.»
- RF-05 sigue «Parcial» (Ingesta sin imágenes; validación en el servidor).

**P3. Casos de Uso, citas con voseo.**
- CU-11, flujo principal, paso 2. Antes: «…si todavía no hay ninguno, muestra "Todavía no tenés notebooks. Creá uno arriba."» → después: «…muestra "Todavía no tiene notebooks. Cree uno arriba."»
- CU-09, FA-05. Antes: «el campo de texto indica "Preguntale algo a <nombre del notebook>"» → después: «el campo de texto indica "Pregúntele algo a <nombre del notebook>"».
- Búsqueda (`Grep` de tenés, creá, elegí, revisá, soltá, preguntale, podés, intentá y otras formas comunes del voseo) en `documentacion_texto/` (ERS, CU, HU, Procesos, modelos, Visión, StakeHolder) y en los archivos de texto de `Documentacion/Documentacion_ServIA_2026/`: solo esas dos citas. HU: ninguna. Los `.docx` no se buscan directamente (su texto es el de los PDF vigentes).
- Fuera de alcance (tuteo, coincide con la interfaz actual): «Tus colecciones de documentos» (CU-11 p. 2, ERS RF-17), «Selecciona tus archivos» (CU-07 p. 2), «¿Olvidaste tu contraseña?» (CU-01, CU-04, ERS RF-03).

**P4. RF-15.** Sin cambios. Su «Estado actual» («en el chat de NotebookServIA la acción de reintentar todavía no tiene efecto») sigue correcto: `onRetry={() => {}}` en `notebooks/index.js:529`. Pasa a la 008b.

**P5. RT-07.70.** Opción A (recomendada): no se añade al ERS; la regla vive en la spec, como el precedente RF-16.61 (el ERS no menciona voseo ni trato de usted). Opción B: añadir a RT-07 «, con trato de usted»; abriría un «Estado actual» por los textos con tuteo de P3.

**P6. Cierre.**
- `spec.md` línea 2: «Estado: aprobada (04/11/2026)» → «Estado: implementada (04/11/2026)».
- `MEMORY.md` (queda ≤ 100 líneas): cabecera «Actualizado: 04/11/2026 (spec 008 implementada; validación del reviewer pendiente)»; línea 9: «ERS V1.8, CU V1.5» → «ERS V1.9, CU V1.6» (o las versiones nuevas si se aplica P1-P3); el punto 3 de «Próximos pasos» se reemplaza por:
  - «3. **Spec 008 (mejoras de NotebookServIA): implementada (04/11/2026), validación pendiente.** Confirmación «Quitar documento» con doble clic absorbido y estado por documento (RF-19.70); seis textos sin voseo (RT-07.70); CF-1 aprobado (PNG tipeado reconocido sin errores, respuesta con el texto y la cita). Suites: pytest 2231 + 47 xfail (normal e inverso); e2e 165 = 155 + 6 esperados + 4 omitidas, suite 558,7 s (primera corrida 573,9 s: repetir antes de recortar). Detalle: `specs/008-mejoras-notebookservia/tasks.md`.»
  - «Pendiente 008b (sin fecha): «Reintentar» del notebook (RF-15) con lo heredado: RF-15.70 agrega al final, RF-15.72 cancela de verdad en el servidor con «Consulta cancelada por el usuario», RF-17.70/71, RF-21.71; e2e solo a 1366 px. Ver spec 008 «Fuera de alcance».»
  - «Residuos sin borrado (RN-01): notebooks vacíos 90003 `PRUEBA 007 verificacion`, 80003 `PRUEBA 006` y 90004 `PRUEBA 008 manual`.»
  - «Observación: a 616 px, al recargar NotebookServIA la barra lateral tapa la lista de notebooks (sin spec; junto con H4).»
  - En el punto 1, «paso 8 (imagen en el notebook…) para la spec del notebook» se quita (hecho en la 008) y H6 remite a la 008b; en «Hallazgos», la línea del notebook conserva U2 y remite a los residuos.
- `graphify-out/`: sí hace falta (cambió `frontend/pages/notebooks/index.js` y las e2e): `graphify update .` por la vía de `python.exe` de uv, nombres de comunidades, `generar_mapa.py` y `generar_mapa_pruebas.py`; si se exportan PDF nuevos, también `generar_documentacion_texto.py`.

**Archivos de documentación que cambian si se aprueba P1-P3:** `ERS_Avances de desarrollo - ServIA.docx` y su PDF nuevo en `PDF/`; `Casos de Uso - ServIA.docx` y su PDF nuevo en `PDF/`; después, `graphify-out/documentacion_texto/` regenerado. Historias de Usuario, Procesos, modelos, C4 y diagramas: sin cambios (HU-19 ya pide la confirmación; CU-13 ya describe confirmar y cancelar).

Fase 5: un implementer corre las suites para el reviewer (plan §11).
