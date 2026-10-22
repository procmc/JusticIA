# Tareas — Spec 005a: Infraestructura de extremo a extremo, acceso y roles, pantallas de E2
Estado: aprobadas (Andrés, 21/10/2026)

Historial: 21/10/2026 — creadas (fase 3, planner).

Orden: T1 → T2 → T3 → T4; T5 y T6 tras T3; T7-T9 tras T4 (T9 también tras T5); T10 al final. Detalle en `plan-005a.md` (§ entre paréntesis). Cada tarea empieza por sus pruebas y **las ve fallar, anotando la causa del rojo**; la que pasa desde el inicio se anota como protección.

⚠️ Archivos nuevos y dependencia aprobados por la decisión 2 (se marcan igual). Nada de código de producción del backend, esquema, migraciones, `requirements.txt`, prompts, modelos, `frontend/.env.local` ni datos reales.

**E (cierre estándar de cada tarea)**:
- Rojo y su causa anotados; pruebas existentes intactas.
- `docker compose exec backend pytest` y `--orden-inverso` pasan, sin residuos (la cifra no baja; base: la de 21/10, 1999 pasan y 45 `xfail`).
- Desde T2: `npm run e2e` (en `frontend/`) pasa; anotar preparación, duración de la suite (≤ 10 min, ninguna prueba > 60 s), residuos 0 y «contraseñas en artefactos: 0». Las pruebas nuevas, también solas (`npm run e2e -- --grep "<requisito>"`).
- `docker compose ps` sin reinicios; `curl http://localhost:8000/` responde; `docker compose logs --tail 100 backend` sin errores nuevos; `MSYS_NO_PATHCONV=1 docker compose exec backend cat /sys/fs/cgroup/memory.events` con `oom` y `oom_kill` en 0.
- `git diff` vacío en `frontend/.env.local`, `requirements.txt` y `backend/app/`; `.next` sin cambios de fecha; nada nuevo en `backend/uploads/`.
- Una línea en `MEMORY.md` y parar.

## Antes de empezar (Andrés)
- [x] Aprobar este plan y estas tareas (dudas al final del plan resueltas, 21/10/2026).
- [x] Antes de T2: ajustar el modo revisor de `.claude/hooks/validate-bash.sh` según el plan §15. (Comprobado en solo lectura el 22/10: líneas 104-111 permiten `npm run e2e`, `e2e:apagar`, sus formas `--prefix`, `cat /sys/fs/cgroup/memory.(current|peak|events|stat)` y `python -m tests.instancia_e2e` con y sin `-d`/`--apagar`; probado con el modo revisor: salida 0 en todos y salida 2 con `taskkill /IM node.exe`.)

## Tareas
- [x] **T1. Instancia de pruebas en el contenedor y medición.** RA-02.41, RA-02.49, RNF-09.40  ⚠️ archivos nuevos `backend/tests/instancia_e2e/`, `test_instancia_e2e.py`; `docker-compose.yml` (puerto `127.0.0.1:8100:8100`); cambios en `tests/soporte/` (§2-§4)
  - Pruebas: `test_configuracion_e2e_nombres_y_servicios_invalidos`, `test_proteccion_solo_los_dos_nombres`, `test_carpeta_temporal_fuera_de_app`, `test_control_ausente_en_main`, `test_vigilante_apaga_por_inactividad`.
  - Código: nombre activo y `NOMBRE_PRUEBAS_E2E`; configuración e2e; lanzador (`estado`, `apagar`, `--apagar`, vigilante). El implementer se detiene y avisa a Andrés, que recrea el `backend` (`docker compose up -d backend`); sigue cuando él lo confirma.
  - Manual: `curl http://127.0.0.1:8100/pruebas-e2e/estado` con los cuatro simulados activos y `servia_pruebas_e2e`; `curl http://localhost:8000/pruebas-e2e/estado` → 404; tras `--apagar`, la base y la colección no existen y el puerto rechaza.
  - Medición (§12): memoria con y sin la instancia y tiempo de arranque; si no alcanza, parar y preguntar.
  - Hecho cuando: pruebas rojas antes y verdes después; medición anotada; E (sin `npm run e2e`).

- [x] **T2. Playwright y orquestador.** RA-02.40, RA-02.43, RA-02.47, RNF-09.40  ⚠️ dependencia `@playwright/test` (principio 1); `package.json`, `next.config.mjs`, `.gitignore`; nuevos `playwright.config.js`, `e2e/ejecutar.mjs`, `e2e/soporte/control.js`, `contrasenas.js`; requiere el hook ajustado
  - Pruebas: `orquestador.spec.js` (`puerto ocupado`, `sin pruebas recolectadas`, `resumen con XPASS nombrado`, `búsqueda de contraseñas`, `sin pausas fijas`); `instancia.spec.js` (`simulados activos`, `usa servia_pruebas_e2e`, `control ausente en desarrollo (404)`, `desarrollo responde`).
  - Manual: `npm run e2e -- --grep NINGUNA` → código ≠ 0 y «no se recolectó ninguna prueba»; con 3100 ocupado → error que nombra el puerto; tras la corrida, 8100 no responde; con `npm run dev` activo, `.next` intacto y `http://localhost:3000` responde.
  - Medición: compilación con y sin huella nueva; preparación total frente a 5 min.
  - Corrección posterior (21/10, reportada en la T6): el orquestador solo borraba `test-results` justo antes de Playwright; si la preparación abortaba, el resumen mostraba las cifras del `informe.json` anterior (verde falso). Ahora lo borra al empezar (`prepararResultados`) y el resumen distingue «Sin informe de esta corrida» de «0 pruebas» (`resumirInforme`, `sinInforme`; motivo «no hubo informe de esta corrida»). Regresión: `orquestador.spec.js`, «informe de una corrida anterior…» (roja: `prepararResultados is not a function`; en real, «Recolectadas: 8, Pasan: 8» sin correr nada). `npm run e2e` 33/33.
  - Corrección posterior (21/10, opción D de Andrés, antes de la T8): Next 15.2.4 normaliza el loopback a `localhost` (`NextURL`), por lo que el middleware redirige a `localhost:3100`. La reescritura de esas redirecciones pasó del `beforeEach` de `acceso.spec.js` a `fixtures.js` (`reescribirRedirecciones`, automática con `page`). Pruebas en `red.spec.js`: centinela, reescritura y red intacta. Roja: la reescritura falló con `page.url()` = `http://localhost:3100/auth/login?...` y 10 pedidos a `localhost:3100` nombrados por la red (sin la reescritura). `npm run e2e` 75 recolectadas, 69 pasan, 6 fallos esperados.
  - Hecho cuando: pruebas rojas antes y verdes después; E.

- [x] **T3. Control de datos y limpieza por prueba.** RA-02.42, RA-02.43, RA-02.49  ⚠️ archivos nuevos `e2e/soporte/fixtures.js`
  - Pruebas: `instancia.spec.js` (`crea usuarios PRUEBA de cada rol, temporal e Inactivo`, `limpiar deja residuos en cero`); pytest `test_limpieza_rechaza_otra_base`, `test_registro_cuenta_contrasenas_recibidas`.
  - Código: `/usuarios`, `GET /residuos`, `/limpiar` (§4); fixture automática de limpieza y residuos.
  - Manual: cortar una corrida a la mitad (Ctrl+C) y repetir: empieza con residuos en cero.
  - Hecho cuando: pruebas rojas antes y verdes después; E.

- [x] **T4. Fixtures transversales: red, consola, 616 px y fallo esperado.** RA-02.41, RA-02.44, RA-02.45, RA-02.46  ⚠️ archivos nuevos `consola_declarada.js`, `sesion.js`, `red.spec.js`
  - Pruebas: `red.spec.js` (`el navegador solo habla con la instancia`, `error de consola no declarado`, `error provocado y declarado`, `accesible detecta un control tapado`); `orquestador.spec.js` (`anotación de fallo esperado`).
  - Manual: una prueba temporal que pide una dirección externa falla nombrándola (se quita después).
  - Hecho cuando: pruebas rojas antes y verdes después, en `escritorio` y `pequena`; E.

- [x] **T5. Control: recuperación y bitácora.** RA-02.49 (RF-02.42, RF-03.40, RF-03.41, RF-21.40, RF-22.40, RF-21.41)  ⚠️ archivo nuevo `capacidades.spec.js`
  - Pruebas: `capacidades.spec.js` (`código del correo por el control`, `correo en fallo`, `almacén no disponible`, `reloj vence el código`, `filas de bitácora de cada tipo`).
  - Hecho cuando: pruebas rojas antes y verdes después; E.

- [x] **T6. Control: motor, ingesta y notebooks (para la 005b).** RA-02.49, RNF-09.40 (RF-11.40-43, RF-16.40, RF-18.40, RF-19.41, RF-19.42)
  - Pruebas: pytest `test_motor_programable`; `capacidades.spec.js` por API (`motor cita, retiene, secuencia, falla y no emite`, `ingesta procesa en el proceso, falla y retiene`, `imagen con HTR simulado`, `vista previa retenida`, `quitar retenido y fallido`).
  - Hecho cuando: pruebas rojas antes y verdes después; E.

- [x] **T7. Acceso y menú.** RF-01.40, RF-01.41, RF-01.42, RF-01.43, RF-01.44, RF-02.40  ⚠️ archivo nuevo `acceso.spec.js`
  - Pruebas: las de RF-01.40 a RF-01.44 y RF-02.40 del plan §10.
  - Manual: Andrés inicia sesión con los dos roles en desarrollo (1366 y 616 px): menú, panel obligatorio con una cuenta `PRUEBA` temporal, cerrar sesión y Atrás.
  - Hecho cuando: pasan o quedan con `fallaEsperada` tras verlas en rojo; E.

- [x] **T8. Páginas, roles y cuentas.** RA-02.48, RF-02.41, RF-02.42, RF-03.40  ⚠️ archivos nuevos `paginas.js`, `paginas-y-roles.spec.js`, `cuentas.spec.js`
  - Pruebas: `lista de páginas completa`, `@solo-escritorio cada rol contra cada clase`, `crear cuenta: éxito y correo en fallo`, `resetear: explicación, éxito y correo en fallo con sesión activa`.
  - Manual: una página nueva temporal sin clasificar hace fallar la lista (se quita después); Andrés crea y resetea una cuenta `PRUEBA` en desarrollo.
  - Hecho cuando: pasan o quedan con `fallaEsperada` tras verlas en rojo; E.
  - Corrección (21/10, decisión 5): la premisa «`/limpiar` borra por prefijo `PRUEBA`» era falsa. `limpiar_todo` y `contar_residuos_e2e` filtran `T_Usuario` solo con `NOT IN (sembrados)`, así que la cuenta de cédula numérica de `cuentas.spec.js` se cuenta y se borra; no hizo falta un rango reservado. Protección (verde desde el inicio, sin rojo posible): `test_limpieza_incluye_usuarios_sin_prefijo_prueba` y, al final de `RF-02.42 · crear cuenta`, `residuos.filas.T_Usuario == 3` durante la corrida y total 0 tras `/limpiar`. Cierre E: pytest 2020 + 45 xfail (directo e inverso); `npm run e2e` 83 = 77 + 6 esperados, residuos 0.

- [x] **T9. Recuperación e Historial.** RF-03.41, RF-21.40  ⚠️ archivos nuevos `recuperacion.spec.js`, `historial.spec.js`
  - Pruebas: las de RF-03.41 y RF-21.40 del plan §10 (cada flujo de recuperación con su propio usuario `PRUEBA`).
  - Manual: Andrés recorre la recuperación en desarrollo (correo de Mailtrap) y abre el detalle en Historial a 1366 y 616 px.
  - Hecho cuando: pasan o quedan con `fallaEsperada` tras verlas en rojo; E.
  - Resultado (21/10): `recuperacion.spec.js` (5 pruebas) y `historial.spec.js` (4 pruebas, una de hora), todas pasan en `escritorio` y `pequena` desde el inicio (ningún incumplimiento del ERS), así que son de protección: se comprobó con mutaciones temporales de las respuestas de la API (`page.route`), restauradas con `cmp`. `npm run e2e`: 101 = 95 pasan + 6 esperados.

- [x] **T10. Cierre de la 005a: corrida completa, verificación manual y documentación.** Todos
  - Pruebas: ninguna nueva. `npm run e2e` completa (conteo por requisito: al menos una que pasa o un fallo esperado estricto); `E2E_FALLO_PROVOCADO=1 npm run e2e -- --grep RA-02.43` → «contraseñas en artefactos: 0»; pruebas sueltas por archivo; memoria durante la corrida (§12).
  - Manual: plan §12 y las comprobaciones manuales de RA-02.41 y RA-02.49; limpieza de los datos `PRUEBA` de desarrollo.
  - Documentación (§16): E2 en 003, 003a y 003b; entorno aislado en la 002; texto para `CLAUDE.md` y la regla 5b (los aplica Andrés); mapa de pruebas, su generador, `.graphifyignore` y grafo; `MEMORY.md` con la medición de tokens (`rtk gain`; tamaños frente a la 004a).
  - Hecho cuando: suite dentro de RA-02.47, residuos 0, pytest pasando, sin tocar desarrollo; validación del reviewer; spec 005 «005a implementada» con la aprobación de Andrés.
  - Decisión de Andrés (21/10) sobre la verificación manual (T7-T9, §12, RA-02.41, RA-02.49): la hace un agente con el MCP `chrome-devtools` sobre desarrollo; Andrés inicia sesión y escribe él mismo en el navegador las contraseñas y los códigos de Mailtrap; los agentes nunca los reciben.
  - Hecho de la T10 (parte 1, 21/10, sin navegador): `npm run e2e` completo 101 = 95 pasan + 6 esperados, 0 XPASS, preparación 27,2 s, suite 314,4 s, residuos 0, contraseñas 0; cada archivo por separado (suma 101, todos CORRECTO); memoria del contenedor `backend` sin OOM (pico de la corrida 2,9 GB, `memory.peak` 4,08 GB); pytest 2020 + 45 xfail, normal e inverso; E2 retirada en 003, 003a y 003b y entorno doble en la 002; `propuesta_claude_005a.md` (texto para `CLAUDE.md` y regla 5b, lo aplica Andrés); `generar_mapa_pruebas.py` con `frontend/e2e/` y `instancia_e2e`, `.graphifyignore`, `graphify update .`, `generar_mapa.py`; `MEMORY.md` e historial.
  - Resuelto (22/10, opción A de Andrés): `ocultarContrasenas` en `e2e/ejecutar.mjs` reemplaza cada contraseña por `[CONTRASEÑA OCULTA]` en los artefactos de texto (prueba «RA-02.43 · ocultar contraseñas…» en `orquestador.spec.js`); con `E2E_FALLO_PROVOCADO=1` da contraseñas 0 y residuos 0. `flujos/provocado.spec.js` se conserva (solo corre con `E2E_FALLO_PROVOCADO=1`).
  - Riesgo aceptado (Andrés, 22/10, opción A): las capturas de pantalla en fallo (`screenshot: 'only-on-failure'`; trazas y vídeo en `off`) son binarios PNG que el orquestador no oculta ni busca; el riesgo es bajo porque los campos de contraseña muestran puntos.
  - Hecho de la T10 (parte final, 22/10): corrida normal 102 recolectadas = 96 pasan + 6 fallos esperados, 0 fallan, 0 XPASS, residuos 0, contraseñas 0, 247 s.
  - Verificación manual (22/10, MCP `chrome-devtools` sobre desarrollo, ambos roles a 1365 y 615 px CSS; zoom 0,9 del MCP): menú, tarjetas, páginas propias, bloqueos por rol, dirección inexistente y 404, consola sin errores propios. T7 (cerrar sesión + Atrás): Andrés, OK. T8: cuenta PRUEBA creada y reseteo (aviso «Contraseña reseteada exitosamente», último acceso «Nunca», bitácora con correo entregada). T9: recuperación completa (Andrés, OK), pantallas a 615 px y bitácora de la recuperación con 5 eventos sin código ni contraseñas. Las contraseñas y los códigos los escribió Andrés.
  - RA-02.41 / RA-02.49: conteos de desarrollo idénticos antes y después de `npm run e2e` (T_Usuario 8, T_Bitacora 883, T_Documento 5, T_Expediente 14, T_Expediente_Documento 5, T_Notebook 8; Qdrant `justicia_docs` 2213 puntos; `uploads/` 302 archivos, misma huella).
  - Limpieza: cuentas PRUEBA de desarrollo dadas de baja (Inactivo, sin borrar, RN-01): prueba.t10 y prueba.t9b (eventos #190188 y #190190); prueba.t8, t8b y t9a ya estaban inactivas.
  - Decisiones de Andrés (22/10): los nombres de las 116 comunidades del grafo (de 225) quedan para una tarea aparte, fuera de la 005a; `propuesta_claude_005a.md` se conserva y Andrés la aplica en `CLAUDE.md` y `.claude/rules/testing.md`; la línea E2 de 002, 003, 003a y 003b sigue «pendiente de su validación» hasta el veredicto del reviewer.
  - Hallazgos para el reviewer (no corregidos en la 005a): (a) «Información adicional → TIMESTAMP» del detalle de bitácora en UTC (+6 h) en todos los tipos de evento, aunque la tabla y «Fecha y hora» están bien (explica la decisión 5 de la T9); (b) cambio obligatorio repetido tras la recuperación pública: el ERS, la 003a y la 003b no definen que la vía b lo limpie; primero aclararlo en el ERS y corregir aparte con su prueba de regresión; (c) posible inestabilidad de `cuentas.spec.js › RF-02.42` en escritorio («element is not stable» en la opción «Usuario Judicial», vista una vez); (d) la baja de una cuenta registra todos los campos como modificados y «Id Estado: 2» en vez de «Inactivo»; (e) el panel de cambio obligatorio no tiene `autoComplete` (Chrome rellena «Contraseña actual»; `CambiarContraseña.jsx:190-198`); (f) tras resetear, la tabla de usuarios no se refresca sin recargar; (g) a 615 px el menú lateral aparece abierto tras la carga completa y deja una franja de ~25 px al cerrarlo; (h) el campo del código de recuperación no tiene id/name/etiqueta y el panel azul del paso del código sigue diciendo «Ingresa tu correo…»; (i) vocabulario heredado (Usuario Judicial, JusticBot, Poder Judicial, Expedientes), RT-06; (j) 4 de las 6 tarjetas del Administrador apuntan a la bitácora, más opciones de las 2 que define RF-02.40.
  - Correcciones de la vuelta 1 (22/10; reviewer: CAMBIOS NECESARIOS por inestabilidad): (1) `cuentas.spec.js › RF-02.42`: `elegirRol` reabre la lista del selector (react-aria la cierra si el cuerpo del cajón se desplaza) y entre las dos creaciones espera el cajón cerrado y la fila visible; antes 5 de 10 fallaban, después 10/10 en escritorio y 20/20 en ambas pantallas (`--repeat-each`). (2) `POST /pruebas-e2e/limpiar`: causa del 500 NO confirmada (no se reprodujo con 140 limpiezas bajo carga ni con 96 repeticiones de RF-21.40); `limpiar_todo` repite el borrado de tablas y carpetas dentro de 5 s (prueba `test_limpieza_reintenta_un_error_transitorio_de_la_base`) y `control.js` incluye el `detail` (prueba «RA-02.42 · el error del control incluye el detail…»). (3) RA-02.45: los dos `console.error` heredados están en `CONSOLA_DECLARADA` con su spec retroactiva (autenticación y usuarios); prueba ampliada en `red.spec.js` (rojo 2 fallan, verde 4 pasan). (4) RA-02.41: `validarEstado` exportada y probada con sus cuatro casos de aborto. (5) Textos: ver los cambios en esta tarea, el plan §5 y §14, `propuesta_claude_005a.md`, `MEMORY.md` y el título de la prueba de la hora (RF-22 del ERS).
  - Estabilidad tras las correcciones (22/10): 3 corridas completas seguidas de `npm run e2e`, todas CORRECTO: 104 recolectadas = 98 pasan + 6 esperados, 0 fallan, 0 XPASS, residuos 0, contraseñas 0; suite 265,0 s, 270,0 s y 265,6 s (preparación 15,4 s la primera). pytest completo 2021 pasan + 45 `xfail`; `-m unitaria` 1223 pasan + 2 `xfail`.
  - Cierre (22/10/2026): @reviewer dio el veredicto APROBADO en la vuelta 1 (`npm run e2e` 104 = 98 pasan + 6 esperados, 0 fallan, 0 XPASS, residuos 0, contraseñas 0; pytest 2021 pasan + 45 xfail; con las 3 corridas del implementer, 4 corridas completas en verde) y Andrés aprobó la 005a el 22/10/2026 (opción A): spec 005 «005a implementada; 005b pendiente»; la línea E2 de 003, 003a y 003b pasa a «retirada» (la 002 no la tiene).
  - Pendientes aparte: el recuento `contar_residuos_e2e` (`backend/tests/instancia_e2e/control.py:163-171`) no tiene reintento y una excepción ahí sale como 500 sin `detail`; la causa real del 500 de `/limpiar` sigue sin confirmarse (si reaparece, revisar `/tmp/servia_e2e/instancia.log`).
