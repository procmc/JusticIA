# Tareas — Spec 008b: «Reintentar» en NotebookServIA
Estado: aprobado (04/11/2026), junto con `plan.md`. Decisiones P-1 a P-4 en el plan §12.

Orden: T0 → T1 → T2 ⚠️ → T3 (e2e en rojo) → T4 (frontend) → T5 (suites y verificación) → T6 (cierre). Total ~5,6 h.
Lectura del implementer: la sección de la spec y del plan que cita cada tarea; nada más salvo que la tarea lo pida.
Sin esquema, migraciones, dependencias, prompts, modelos ni `docker-compose.yml`. Los agentes no reinician servidores ni matan procesos por nombre.

**E (cierre estándar)**, con las reglas del plan §8:
- El rojo y su causa anotados; las pruebas existentes intactas salvo las que cita la tarea.
- Antes de cada suite: memoria libre (pytest ≥ 1,5 GB, e2e ≥ 2,3 GB), ninguna otra suite en marcha y `npm run dev` cerrado durante el e2e.
- `docker compose ps` sin reinicios; `curl http://localhost:8000/`; `docker compose logs --tail 100 backend` sin errores nuevos; servicios con `docker compose start`, nunca `up -d`.
- `npm run lint` sin advertencias nuevas en los archivos tocados.
- Una línea en `MEMORY.md` y parar.

- [x] **T0. Línea base (~0,3 h).** RNF-04.71 (presupuesto)
  - Pruebas: ninguna. `git diff --stat f0125e4 -- backend frontend` vacío (salvo `specs/`) → se reutilizan las cifras del cierre de la 008 (pytest 2231 + 47 xfail; e2e 165 = 152 + 6 + 7, suite 499,4 s) (plan D-4). Si hay cambios de código, se corren las dos suites.
  - Hecho cuando: anotados aquí el diff y la memoria libre de WSL.
  - Evidencia (04/11/2026): `git diff --stat f0125e4` vacío; `git status --short` solo `?? specs/008b-reintentar-notebookservia/`. Sin cambios de código: línea base = cierre de la 008 (pytest 2231 + 47 xfail; e2e 152 pasan, 6 xfail, 7 omitidas, 499,4 s, CORRECTO). Memoria WSL: 9,28 GB libres de 12,25 GB (MemAvailable). Entorno: 7 contenedores Up (backend, celery-worker, ollama, qdrant, redis, sqlserver, tika), sin reinicios; `servidor-htr` detenido; API `curl :8000` 200; frontend `:3000` sin respuesta (npm run dev no activo; no se tocó).

- [x] **T1. Desconexión del notebook (~0,4 h).** RF-16.62, RF-11.68, RF-21.60, RF-21.71
  - Leer: plan §2 (fila de `test_chat_contexto.py`) y §7.
  - Pruebas (primero): `test_desconexion_antes_y_despues_cancela` parametrizada con `TRES_CHATS`.
  - Se espera verde desde el inicio (cubre lo existente); si falla en el notebook, PARAR y avisar.
  - Hecho cuando: `docker compose exec backend pytest backend/tests/integracion/test_chat_contexto.py` verde (6 casos de desconexión) y E.
  - Evidencia (04/11/2026): verde desde el inicio, como se esperaba (cubre lo existente; no hubo rojo que anotar). Solo se tocó `backend/tests/integracion/test_chat_contexto.py`: `@pytest.mark.parametrize("chat", TRES_CHATS)` en la prueba, fixture `registro_de_datos` y alcance de `_alcance_vacio(chat, ...)` en el cuerpo. Antes: memoria 9,0 GB libres, ninguna otra suite. Corrida normal: 45 pasan, 0 fallan, 0 xfail, 0 XPASS, residuos ninguno, 200,5 s. `--orden-inverso`: 45 pasan, 0 fallan, 0 xfail, 0 XPASS, residuos ninguno, 189,0 s. Los 6 casos de desconexión (3 chats x antes/después) incluidos.

- [x] **T2. Contador `abandonados` en la instancia e2e (~0,5 h).** RF-15.72, RF-17.70, RA-02.49  ⚠️ cambio en el control de la instancia e2e (aprobado, P-2 = A)
  - Leer: plan §5.
  - Pruebas (primero, `test_instancia_e2e.py`): un turno cerrado antes de `done` sube `abandonados` a 1; uno terminado no lo cambia; restablecer lo deja en 0. Rojo: la clave no existe.
  - Hecho cuando: esas pruebas y `pytest backend/tests/unitarias/test_instancia_e2e.py` verdes; `control.js` lo expone si hace falta; E.
  - Evidencia (04/11/2026): memoria 9,7 GB libres, ninguna otra suite. Rojo: `test_chat_programable_cuenta_los_turnos_abandonados` y `..._valida_y_se_restablece` (estado exacto actualizado con `abandonados: 0`) fallan con `KeyError: 'abandonados'`. Verde: `test_instancia_e2e.py` 31 pasan, 0 fallan, 0 xfail, 0 XPASS, residuos ninguno; `--orden-inverso` igual (31). Cambio: `simulados_e2e.py` (`EstadoChat`: bandera `terminado` por `done`/`error` en `envolver_turno`, `abandonados` bajo candado, en `estado()`, a 0 en `configurar`/`restablecer`). `control.py` ya devolvía `estado()` y `control.js` `chatEstado` devuelve el JSON completo: sin cambios. No se corrió el e2e de Playwright (T5).

- [x] **T3. E2e única en rojo (~1 h).** RF-15.70 a RF-15.74, RF-17.70, RF-17.71, RF-21.71, RNF-04.71
  - Leer: spec A-C; plan §6 y §7a.
  - Pruebas (primero): «RF-15.70 · reintentar, cancelar, cambiar de notebook y Enter» en `notebooks.spec.js`, solo 1366 px, pasos 1-6 del plan §6. El paso 3 usa `modo: 'conexion'` (RF-15.73 solo tras un error); la mitad durante «Reintentando…» no se prueba (§7a).
  - Rojo esperado: una sola corrida con el código actual, que falla en el paso 1 (RF-15.70: «Reintentar» no hace nada).
  - Hecho cuando: ese rojo y su causa anotados (`npm run e2e -- --grep "RF-15.70"`); E.
  - Evidencia (04/11/2026): solo se tocó `frontend/e2e/flujos/notebooks.spec.js` (import de `escribir` y el `describe` «NotebookServIA: reintentar y cancelar» al final; `test.skip` en `pequena` con RNF-04.71). Antes de cada corrida: puerto 3000 = 000, memoria WSL 9,2 GB libres, ninguna otra suite.
    - Rojo (`--grep RF-15.70`): recolectadas 2, pasan 0, fallan 1 (escritorio), esperados 0, XPASS 0, omitidas 1 (`pequena`); preparación 17,7 s, suite 19,0 s, residuos 0, contraseñas 0, resultado FALLA. Error en el paso 1: «RF-15.70 · reintentar agrega la pregunta y la respuesta al final», `toHaveCount(4)` sobre `div.space-y-4 > div`, esperado 4 y recibido 2 (el clic en «Reintentar consulta» no hace nada; `onRetry={() => {}}`). El selector de burbujas resolvió bien las 2 previas.
    - `capacidades.spec.js` (en `e2e/infraestructura/`, no en `flujos/`): 15 recolectadas, 15 pasan, 0 fallan, 0 XPASS, preparación 15,4 s, suite 25,2 s, residuos 0, contraseñas 0, CORRECTO. El campo `abandonados` no la rompe; sin ajustes.
    - Desviaciones: (1) el paso 6 espera 6 consultas, no 7: la cuenta del plan (1: A y B = 2; 2: la final = 1; 3: error + reintento = 2; 4: ninguna; 5: el liberado = 1) suma 6; se confirma o corrige en T4 con la corrida en verde. (2) No se asevera el separador `---` de la burbuja cancelada (depende del render del markdown); se asevera texto parcial + «Consulta cancelada por el usuario». (3) Pasos 2 a 6 sin ejecutar aún (el rojo corta en el paso 1): selectores, el texto del error del paso 3, la restauración de A desde `sessionStorage` y el filtro de la bitácora (`tipoAccion` «Consulta RAG» + `informacionAdicional.tipo_consulta` = notebook) se validan en T4; puede aparecer una regla de consola a declarar con `consola.provocado` en el error del paso 3.

- [x] **T4. Frontend: A1 y el notebook (~1,25 h).** RF-15.70 a RF-15.74, RF-17.70, RF-17.71
  - Leer: plan §3 y §4.
  - Pruebas: la e2e de T3 (no se escriben nuevas).
  - Código, primero sin A1: `enviarPregunta`, `reintentar`, `cancelarEnCurso`, `seleccionarNotebook` y Enter en `index.js`.
  - Rojo de A1: correr la e2e; el paso 2 debe fallar con 1 conexión abortada en vez de 2. Se anota.
  - Después, A1: el `finally` de `consultaService.js` (plan §3), y la e2e en verde.
  - P-4 (anular el reintento automático pendiente y marcar su burbuja) se implementa igual, sin prueba: exención del plan §7a.
  - Medir el paso 3: si pasa de 5 s, se retira de la e2e; se anota la exención en el plan §7a y pasa a T5.
  - Hecho cuando: `npm run e2e -- e2e/flujos/notebooks.spec.js e2e/flujos/chat.spec.js` verde; el coste de la e2e nueva y del paso 3 anotado; E.
  - Evidencia (04/11/2026): antes de cada corrida, puerto 3000 = 000, memoria WSL 8,9 a 9,1 GB libres, ninguna otra suite. Código: `pages/notebooks/index.js` (`hayEnCurso`, `cancelarEnCurso` con marca inactiva `{active:false,id:'cancelada'}` y `markMessageAsCanceled`, `handleEnviarMensaje` que bloquea Enter, `reintentar`, `enviarPregunta(query)`, `seleccionarNotebook` guarda la conversación cancelada bajo el notebook anterior, `onRetry={reintentar}`; P-4: la burbuja «Reintentando…» se vacía y queda con solo el aviso) y `services/consultaService.js` (controlador propio y `finally` condicionado, A1). Diff: 2 archivos de la app, +57 -8.
    - Rojo de A1 (todo el código salvo el `finally`): `npm run e2e -- --grep RF-15.70`, 1 fallo en el paso 2: «RF-15.74 · dos cancelaciones seguidas cierran dos conexiones», `expect.poll(() => abortadas).toBe(2)`, recibido 1.
    - Desviación de la prueba: tras A1 el paso 2 falló en «RF-15.72 · el servidor registra dos consultas abandonadas» (esperado 2, recibido 0 en 10 s): con la señal de vida por omisión de 10 s el servidor no nota la desconexión de una respuesta retenida a tiempo. Corrección mínima: `control.chat({ senal_de_vida_segundos: 1 })` en lugar de `control.chat({})`.
    - Verde `--grep RF-15.70`: recolectadas 2, pasan 1, fallan 0, esperados 0, XPASS 0, omitidas 1; preparación 15,0 s, suite 12,8 s (la prueba, 10,0 s); residuos 0, contraseñas 0, CORRECTO. Pasó completa a la primera tras el ajuste, así que los selectores, el error del paso 3 sin regla de consola nueva, la restauración desde `sessionStorage` y el filtro de la bitácora quedaron validados; el paso 6 confirma 6 consultas (no 7; el plan sumaba mal), una con motivo. El paso 3, acotado por la propia aserción a ≤ 5 s, pasó: no hay exención de P2.
    - `notebooks.spec.js` + `chat.spec.js`: recolectadas 38, pasan 32, fallan 0, esperados 0, XPASS 0, omitidas 6 (`pequena`, incluida la nueva), preparación 14,5 s, suite 166,4 s, residuos 0, contraseñas 0, CORRECTO.
    - `npm run lint`: 0 errores, 1 aviso (`<img>` en `pages/notebooks/index.js:604`, ya existente, no de esta tarea).

- [x] **T5. Suites completas y verificación manual (~1,5 h).** todos, RN-01.71
  - Pruebas: pytest normal y `--orden-inverso` (T0 + los casos nuevos de T1 y T2; 0 XPASS). `npm run e2e` completo: CORRECTO, suite ≤ 569 s; si la pasa, repetir una vez, y el recorte solo con dos corridas seguidas por encima y con la decisión de Andrés. `npm run build` con `NEXT_DIST_DIR` propio. `git diff --stat` solo en los archivos del plan §2.
  - Manual: plan §9 (Andrés inicia sesión; 1366 y 616 px; dos roles; consola).
  - Hecho cuando: la evidencia de ambas suites y de la verificación manual anotada aquí, y E.
  - Evidencia parte 1 (04/11/2026): memoria libre 2,27 GB antes de pytest y 2,3 GB antes del e2e; puerto 3000 = 000; una suite a la vez. pytest normal: 2236 pasan, 0 fallan, 47 fallos esperados, 0 XPASS, 0 errores de preparación, 0 omitidas, residuos ninguno, 782,05 s. pytest `--orden-inverso`: igual (2236 / 0 / 47 / 0 XPASS, residuos ninguno, 793,32 s). e2e `npm run e2e`: CORRECTO; recolectadas 167, pasan 153, fallan 0, fallos esperados 6, XPASS 0, omitidas 8; preparación 16,1 s; suite 508,9 s (límite de la tarea 569 s: una sola corrida, no hizo falta repetir); residuos 0; contraseñas en artefactos 0; backend de desarrollo 200/200. `npm run build`: exit 0. `npm run lint`: exit 0, 0 errores y 1 aviso (`<img>` en `pages/notebooks/index.js:604`, ya existía en HEAD). Salud: `docker compose ps` sin reinicios, `curl localhost:8000/` responde. `git diff --stat`: 6 archivos (+276 -15): `simulados_e2e.py`, `test_chat_contexto.py`, `test_instancia_e2e.py`, `notebooks.spec.js`, `notebooks/index.js`, `consultaService.js`. Pendiente: verificación manual (parte 2).
  - Evidencia parte 2 (Usuario Gubernamental, 04/11/2026; motor real `llama3.1:8b`; memoria libre WSL 7,1 GB antes, Ollama sin modelo cargado; MCP a 1229 ≈ 1366 px y 554 ≈ 616 px; notebook `PRUEBA 008 manual` = 90004, vacío al inicio; un `.txt` `PRUEBA` inyectado como `File` en memoria, Procesado con 1 fragmento):
    - RF-15.70/15.71 (1366 y 616): pregunta y respuesta; con el borrador escrito, «Reintentar» agrega la misma pregunta y una respuesta nueva al final, la anterior queda intacta y el borrador se conserva. OK en ambos anchos.
    - RF-15.72 (1366 y 616): con respuesta en curso, «Reintentar» deja la burbuja con el texto parcial («El informe de inventario **») y «Consulta cancelada por el usuario», y llega una respuesta nueva al final. Doble pulsación (250 ms): 2 canceladas, 1 respuesta completa, envío libre. OK.
    - RF-17.70 (1366 y 616): con respuesta en curso, abrir `PRUEBA 007 verificacion` (90003): sin mensajes del otro notebook, sin aviso, envío libre (también 4 s después, sin respuesta tardía). Al volver, la burbuja cancelada con su aviso. OK.
    - RF-17.71 (1366 y 616): Enter en curso (evento `keydown` Enter, no el teclado físico): no envía, el texto queda en el campo y no aparece en el chat, y sigue así al terminar. OK.
    - RF-15.74 (1366 y 616, Asistente Virtual): detener y enviar dos veces seguidas: A y B canceladas, C completa, una sola burbuja por pregunta, sin duplicados ni bloqueo (envío libre). OK.
    - Consola: 0 errores y 0 avisos en cada paso; solo el aviso de Chrome «A form field element should have an id or name attribute» (tipo issue, no error; ya existía). Sin desbordamiento horizontal a 616 px (scrollWidth 615).
    - Bitácora (`T_Bitacora`, solo lectura; tipo de acción 12): a 1366, 6 consultas del notebook (= 6 turnos terminados: 1 + reintento, resumen, reintento de «segunda», «tercera» final, «quinta») y ninguna por las 4 canceladas (original de «segunda», 2 de «tercera», «cuarta» al cambiar de notebook); 2 consultas generales (la 1.ª y la C; A y B canceladas sin registro). A 616, 5 del notebook (= 5 terminados) y 1 general (C), ninguna por las canceladas. La vista en la interfaz queda para el Administrador.
    - Ollama: modelo cargado con expiración normal de 9 min tras las cancelaciones; sin generación colgada (el estado es `ollama ps`, no hay un contador de generaciones activas).
    - Limpieza: documento 150152 quitado desde la interfaz con la confirmación de la 008; Qdrant `metadata.numero_expediente = NB-90004` = 0 fragmentos, 0 filas en `T_Expediente_Documento`, sin archivo en `uploads`; sin archivos temporales en el repositorio. Residuos: notebooks 90004 (`PRUEBA 008 manual`, vacío; su historial de chat sigue solo en `sessionStorage` del navegador del MCP) y 90003 (`PRUEBA 007 verificacion`, solo abierto, sin cambios); filas de `T_Bitacora` 260653 a 260670 por RN-01.
  - Evidencia parte 2 (Administrador, 04/11/2026; 1229 ≈ 1366 px y 554 ≈ 616 px): RN-03: `/notebooks` redirige a `/?error=unauthorized` y el menú no muestra NotebookServIA (solo Inicio y Administración), en ambos anchos. Bitácora en la interfaz (`/administracion/bitacora`, filtro Expediente `NB-90004`, 4 páginas): hoy aparecen 11 «Consulta RAG» del notebook (6 de la pasada de 1366 + 5 de la de 616, sin filas de los cancelados), más «Quitar Documento de Notebook» y 4 de «Carga de Documentos»; con filtro por usuario, las 3 consultas generales (la 1.ª, la C de 1366 y la 616C; A, B, 616A y 616B canceladas sin fila). Las filas se leen bien a 1366 px; a 616 px la tabla desborda su caja pero está dentro de un contenedor con desplazamiento horizontal (`overflow-x: auto`) y la descripción se lee al desplazar (comportamiento ya existente del módulo, no tocado por la 008b). Consola: 0 errores; un aviso de `next/image` de `/InteligenciaInformacion.png` en la página de inicio (ya existente, ajeno). Viewport devuelto sin emulación.

- [x] **T6. Propuesta de documentación y cierre (~0,6 h).** RF-15, RF-17, CU-10, E1 (hecha 04/11/2026: aplicadas P1, P2, P3 con FE-01 = A en el «Estado actual» de RF-11, RF-17.71 = A solo en la spec, portada ERS 1.11 y CU 1.8 con «noviembre 2026»; PDF V1.11 y V1.8; spec en «validada»; MEMORY y graphify-out actualizados)
  - Leer: plan §10.
  - Pruebas: ninguna.
  - Hecho cuando: la propuesta para el ERS (RF-15 Implementado, RF-15.72, RF-17.70, «Estado actual» del hallazgo FE-01 como «camino inalcanzable hoy (el servidor sustituye la respuesta vacía desde la 007)») y para CU-10 FA-01 entregada a Andrés; hallazgo FE-01 en `MEMORY.md`, con la misma redacción; `graphify-out/` actualizado (grafo, `generar_mapa.py`, `generar_mapa_pruebas.py`); spec en «implementada».

### Propuesta T6 (aprobada y aplicada por Andrés el 04/11/2026: FE-01 = A, RF-17.71 = A, portada = A)
Fuente: `graphify-out/documentacion_texto/` (ERS V1.10, CU V1.7). Nada aplicado todavía, salvo la corrección del plan (P6).

**P1. ERS, RF-15 (Copiar y reintentar respuesta).**
- «Reglas y validaciones», al final, texto nuevo (RF-15.72): «Si se reintenta mientras una respuesta está en curso, esa consulta se cancela en el servidor, no se guarda ni se registra, y su respuesta conserva el texto recibido seguido de "Consulta cancelada por el usuario".»
- «Estado actual», antes: «Estado actual: en el chat de NotebookServIA la acción de reintentar todavía no tiene efecto.» → después: el párrafo se elimina.
- Línea de estado, antes: «Prioridad: Baja Estado: Parcial» → después: «Prioridad: Baja Estado: Implementado».

**P2. ERS, RF-17 (Creación de notebooks).**
- «Reglas y validaciones», al final, después de «…se guarda en su forma canónica.», texto nuevo (RF-17.70): «Abrir otro notebook mientras una respuesta está en curso la cancela de la misma forma que el reintento (RF-15); no se escribe nada en la conversación del notebook que se abre y, al volver, esa respuesta muestra el texto recibido y el aviso de cancelación.»
- RF-17.71 (Enter con una respuesta en curso), según D2:
  - Opción A, recomendada: no se añade; queda en la spec. El ERS no describe el bloqueo del envío durante la respuesta (tampoco el del botón), como el precedente RT-07.70.
  - Opción B: en CU-09 FA-05, al final: «Mientras una respuesta está en curso, el sistema no envía otra pregunta, ni con el botón ni con la tecla Enter, y conserva el texto escrito.»

**P3. Casos de Uso, CU-10 FA-01 (Reintentar).**
- Antes: «…genera una nueva respuesta con el mismo proceso de CU-09 (<<include>> Generar respuesta con cita de fuente), que se agrega al final de la conversación sin borrar la anterior.»
- Después: la misma frase y, a continuación: «Si al pulsarlo hay una respuesta en curso, el sistema primero la cancela: esa respuesta no se guarda ni se registra en la bitácora y conserva el texto recibido seguido de "Consulta cancelada por el usuario".»

**P4. Hallazgo FE-01 (reintento automático ante respuesta vacía), según D1.**
- Hecho: desde la 007 el servidor sustituye la respuesta vacía por su aviso de «sin respuesta», así que «Reintentando obtener respuesta...» y su reintento automático no se alcanzan. Si se alcanzaran, el reintento cambia el id a `requestId + 0.1` (`messageUtils.js:361-362`) y los callbacks comparan con `requestId`: no mostraría su respuesta y dejaría el envío bloqueado, en los tres chats.
- Opción A, recomendada: ampliar el «Estado actual» de RF-11, que ya describe la mitad. Antes: «…si el modelo no devuelve texto, el servidor entrega una respuesta de relleno en lugar de cerrarla vacía, y la interfaz no puede distinguirla para reintentar;» → después: «…y la interfaz no puede distinguirla para reintentar, de modo que el reintento automático es hoy un camino inalcanzable; además, si se alcanzara, no mostraría su respuesta y dejaría el envío bloqueado;». Es el requisito cuyo «Manejo de errores» define el reintento automático; RF-15 queda sin «Estado actual».
- Opción B: un «Estado actual» nuevo en RF-15. Mezcla el reintento manual (cerrado) con el automático y RF-15 no podría pasar limpio a Implementado.
- Opción C: solo en `MEMORY.md`. El ERS seguiría sin el defecto del id, que nadie vería al cerrar la práctica.
- RF-16 y CU-09 FE-01 (plan §10) se descartan: RF-16 es el corte de conexión y los CU no llevan «Estado actual». En `MEMORY.md` va igual (P6).

**P5. Versiones.**
- ERS: `ERS_Avances de desarrollo - ServIA.docx`, portada «Versión: 1.10» → «Versión: 1.11»; PDF nuevo `PDF/ERS_Avances de desarrollo - ServIA_V1.11.pdf`.
- CU: `Casos de Uso - ServIA.docx`, «Versión del documento: 1.7» → «1.8» (y P2 opción B si se elige); PDF nuevo `PDF/Casos de Uso - ServIA_V1.8.pdf`.
- Fecha de portada «octubre 2026» en ambos: la V1.10 y la V1.7 la conservaron; se propone «noviembre 2026» (D3).
- Después: `python3 -X utf8 graphify-out/generar_documentacion_texto.py`. HU, Procesos, modelos, C4 y diagramas: sin cambios.

**P6. Cierre.**
- `spec.md` línea 2: «Estado: aprobada (04/11/2026)» → «Estado: implementada (04/11/2026)».
- `plan.md` §6, paso 6: «= 7 turnos terminados» → «= 6 turnos terminados». Ya aplicado (está en `specs/`, es una corrección de hecho confirmada en T4 y T5, no un estado).
- `MEMORY.md` (hoy 88 líneas; queda ≤ 100):
  - Cabecera: «Actualizado: 04/11/2026 (spec 008b implementada; validación del reviewer pendiente)».
  - Línea 8 («Suite vigente»), antes «(cierre de la 008): pytest 2231 + 47 … suite 499,4 s …» → después: «Suite vigente (cierre de la 008b): pytest 2236 + 47 `xfail`, 0 XPASS (normal e inverso); `npm run e2e` 167 recolectadas = 153 pasan + 6 esperados + 8 omitidas, suite 508,9 s, CORRECTO, residuos 0, contraseñas 0.» (se conserva la frase del recorte de RNF-04.70 y la de `-m infraestructura`).
  - Línea 9: «ERS V1.10, CU V1.7» → «ERS V1.11, CU V1.8» si se aplican P1-P5.
  - Punto 3, la viñeta «Pendiente 008b (sin fecha)…» se reemplaza por: «**Spec 008b («Reintentar» en NotebookServIA): implementada (04/11/2026), validación pendiente.** RF-15.70-74, RF-17.70/71, RF-21.71; cancelación compartida con el Asistente Virtual (A1: `finally` por identidad del controlador); e2e única a 1366 px (616 en manual); contador `abandonados` en `/control/chat`. Las e2e de abandono necesitan `senal_de_vida_segundos: 1`: con los 10 s por omisión el servidor no nota a tiempo la desconexión. Detalle: `specs/008b-reintentar-notebookservia/tasks.md`.»
  - «Hallazgos sin corregir», línea nueva: «FE-01 (reintento automático ante respuesta vacía): camino inalcanzable hoy (el servidor sustituye la respuesta vacía desde la 007); si se alcanzara, `messageUtils.js:361-362` cambia el id a `requestId + 0.1` y los callbacks comparan con `requestId`: no mostraría la respuesta y bloquearía el envío (tres chats).»
  - Residuos: la viñeta existente se conserva tal cual (90003, 80003 y 90004); 90004 sigue vacío tras la 008b.
  - H6 del punto 1: «(pasa a la 008b)» → «(resuelto en la 008b)».
- `graphify-out/` (cambió `pages/notebooks/index.js`, `consultaService.js` y las pruebas): `graphify update .` por la vía de `python.exe` de uv, nombres de comunidades, `generar_mapa.py` y `generar_mapa_pruebas.py`; tras los PDF, `generar_documentacion_texto.py`. Lo corre quien tenga terminal (el planner no la tiene).

**Dudas para Andrés.**
- D1. Hallazgo FE-01: A (ampliar «Estado actual» de RF-11), B («Estado actual» de RF-15) o C (solo `MEMORY.md`). Recomendada: A.
- D2. RF-17.71 (Enter): A (solo en la spec) o B (frase en CU-09 FA-05). Recomendada: A.
- D3. Fecha de portada: A («noviembre 2026» en ERS V1.11 y CU V1.8) o B (conservar «octubre 2026», como la 008). Recomendada: A.

Fase 5: un implementer corre las suites para el reviewer, como en la 008 (plan §8).
