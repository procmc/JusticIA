# Plan — Spec 005a: Infraestructura de extremo a extremo, acceso y roles, pantallas de E2
Estado: aprobado (Andrés, 21/10/2026)

> Solo la 005a (secciones A, B y C de la spec). La 005b tendrá su propio plan cuando la 005a esté validada. Las decisiones 1-19 de la spec no se reabren; aquí se fijan los detalles técnicos. Archivos y líneas a 21/10/2026, rama `fase4` (grafo del 21/10, commit f5d5073; las pruebas, por `Grep`).

Historial:
- 21/10/2026 — creado (fase 3, planner).

## 1. Enfoque
- **Backend de pruebas**: un segundo proceso Python dentro del contenedor `backend` (`python -m tests.instancia_e2e`), puerto 8100, publicado como `127.0.0.1:8100:8100`. Importa la aplicación real (`backend/main.py`), le suma el router de control y la sirve con uvicorn **sin** `--reload`.
- **Entorno aislado**: base y colección `servia_pruebas_e2e`, carpeta temporal en `/tmp/servia_e2e/`, Redis simulado en el proceso, simulados de Ollama, HTR, audio y correo; reutiliza `tests/soporte/` de la 002 (sin `pytest` como ejecutor: `pytest.MonkeyPatch()` como objeto).
- **Frontend de pruebas**: `next build` con `distDir` propio (`.next-e2e`) y `next start -H 127.0.0.1 -p 3100`, con `NEXT_PUBLIC_API_URL=http://127.0.0.1:8100`, `NEXTAUTH_URL=http://127.0.0.1:3100` y un `NEXTAUTH_SECRET` aleatorio por corrida, todo por entorno del proceso (Next no pisa variables ya definidas con `.env.local`).
- **Orquestador** (`npm run e2e`, Windows): comprueba puertos, prepara (compila si cambió la huella, arranca la instancia, espera el estado), corre Playwright con el Chrome instalado, apaga siempre, busca contraseñas en los artefactos e imprime el resumen.
- **Un solo trabajador** (`workers: 1`): la instancia es compartida; tras cada prueba, una fixture automática limpia todo el entorno aislado y exige residuos en cero.

## 2. Archivos
Nuevos (⚠️ «Pregunta antes»; aprobados por la decisión 2, se marcan igual):

| Archivo | Responsabilidad | Requisitos |
|---|---|---|
| ⚠️ `backend/tests/instancia_e2e/__init__.py`, `__main__.py` | Arranque y `--apagar` (§3). | RA-02.40, RA-02.41 |
| ⚠️ `backend/tests/instancia_e2e/configuracion.py` | `construir_configuracion_e2e()` sobre `configuracion.construir_configuracion` (`tests/soporte/configuracion.py:73`): nombres `servia_pruebas_e2e`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `LANGSMITH_TRACING=false`, `PYTHONDONTWRITEBYTECODE=1`. | RA-02.41, RNF-09.40 |
| ⚠️ `backend/tests/instancia_e2e/control.py` | Router `/pruebas-e2e` (§4), con token. | RA-02.49 |
| ⚠️ `backend/tests/instancia_e2e/simulados_e2e.py` | Motor programable, ingesta en el proceso, retenciones de notebooks, vigilante de inactividad. | RA-02.49, RNF-09.40 |
| ⚠️ `backend/tests/unitarias/test_instancia_e2e.py` | Pruebas pytest de la lógica (§10). | RA-02.41, 02.42, 02.43, 02.49 |
| ⚠️ `frontend/playwright.config.js` | Proyectos, límites, artefactos (§6, §7). | RA-02.43, 02.46, 02.47 |
| ⚠️ `frontend/e2e/ejecutar.mjs` | Orquestador (§3). | RA-02.40, 02.41, 02.43, 02.47 |
| ⚠️ `frontend/e2e/soporte/` (`control.js`, `contrasenas.js`, `fixtures.js`, `consola_declarada.js`, `paginas.js`, `sesion.js`) | Cliente del control, contraseñas, fixtures transversales, lista de páginas. | RA-02.41-02.48 |
| ⚠️ `frontend/e2e/infraestructura/*.spec.js`, `frontend/e2e/flujos/*.spec.js` | Pruebas (§10). | todos |

Modificados:

| Archivo | Cambio | Requisitos |
|---|---|---|
| ⚠️ `docker-compose.yml` (servicio `backend`, `ports`, línea 9-10) | Agregar `"127.0.0.1:8100:8100"`. Única modificación autorizada (decisión 2). | RA-02.40 |
| ⚠️ `frontend/package.json` | devDependency `@playwright/test` en versión exacta (sin `^`); scripts `e2e` (`node e2e/ejecutar.mjs`) y `e2e:apagar`. Principio 1. | RA-02.40 |
| `frontend/next.config.mjs` | `distDir: process.env.NEXT_DIST_DIR \|\| '.next'`. Sin la variable, todo igual (ajuste de configuración permitido por «Fuera de alcance»). | RA-02.41 |
| `frontend/.gitignore` (o el de la raíz) | `.next-e2e/`, `test-results/`, `playwright-report/`. | RA-02.43 |
| `backend/tests/soporte/nombres.py` | `NOMBRE_PRUEBAS_E2E = "servia_pruebas_e2e"`. | RA-02.41 |
| `backend/tests/soporte/proteccion.py:24-35` | `exigir_nombre_pruebas` compara con el **nombre activo**; `fijar_nombre_activo(nombre)` solo acepta los dos nombres fijos (sin variable de entorno). Por omisión, `servia_pruebas`: pytest no cambia. | RA-02.41 |
| `backend/tests/soporte/entorno.py:294` | `cerrar_coleccion` usa el nombre activo, no `NOMBRE_PRUEBAS`. | RA-02.41 |

Sin cambios: código de producción del backend, `main.py`, esquema, Alembic, `requirements.txt`, prompts, modelos, `ROUTE_PERMISSIONS`, `frontend/.env.local`, `.next`.

## 3. Arranque y apagado
```
npm run e2e [-- <args de Playwright>]           # frontend/e2e/ejecutar.mjs
  t0; GET http://localhost:8000/ -> anotar (desarrollo responde, RA-02.41)
  si 127.0.0.1:3100 ocupado o GET :8100/pruebas-e2e/estado responde -> error «puerto ocupado ... (npm run e2e:apagar)»
  semilla = random(32 B), solo en memoria; secreto_nextauth = random
  huella = hash(fuentes del frontend + next.config + package-lock + NEXT_PUBLIC_API_URL)
  si huella != .next-e2e/huella-servia: next build (NEXT_DIST_DIR=.next-e2e, NEXT_TELEMETRY_DISABLED=1, URLs de la instancia)
  docker compose exec -d backend python -m tests.instancia_e2e
  esperar estado listo (sondeo con plazo, sin pausas fijas); token = docker compose exec -T backend cat /tmp/servia_e2e/control.token (no se imprime)
  next start (mismo entorno + secreto) ; esperar 200 en :3100/auth/login
  si pasó el límite de preparación (5 min) o el estado no confirma simulados y nombres -> abortar ANTES de abrir el navegador
  t1; playwright test --reporter=list,json (env: SEMILLA, TOKEN, URLs) ; t2
  finally: POST apagar -> {coincidencias_en_registro}; matar next start; comprobar que :8100 ya no responde
  buscar contraseñas (§5) en salida capturada, test-results/ y el informe JSON
  GET :8000/ otra vez; imprimir resumen: pasan, fallan, fallos esperados, XPASS (nombrados), preparación t1-t0, suite t2-t1, residuos, contraseñas encontradas
  código 0 solo si: >0 recolectadas, 0 fallan, 0 XPASS, residuos 0, contraseñas 0, desarrollo responde antes y después
```
- **Instancia** (`python -m tests.instancia_e2e`): `exigir_sin_modulos_importados` → `fijar_nombre_activo(E2E)` → configuración e2e → borrar y crear base y colección (`entorno.preparar`, `preparar_coleccion`; una base que dejó una corrida cortada se reemplaza) → simulados → `import main` → `app.include_router(control)` → `uvicorn.run(app, host="0.0.0.0", port=8100)`. El arranque real de `main.py` (`startup_event`, `main.py:128-166`) precalienta los embeddings y comprueba Qdrant.
- **Apagado**: `POST /pruebas-e2e/apagar` o `python -m tests.instancia_e2e --apagar` (SIGTERM al PID de `/tmp/servia_e2e/pid`). El cierre elimina base, colección y carpeta temporal (`entorno.cerrar`). **Vigilante**: sin peticiones al control durante 15 min, el proceso se apaga solo.
- `npm run e2e:apagar`: apaga una instancia y un `next start` que quedaron vivos.

## 4. Control de pruebas (RA-02.49)
Prefijo `/pruebas-e2e`, token en la cabecera `X-Control-Pruebas` (salvo `estado`, de solo lectura). Existe solo en este proceso: `main.py` no lo incluye, así que el backend de desarrollo responde 404.

| Capacidad | Rutas (POST salvo indicación) | Tarea |
|---|---|---|
| Estado: simulados activos (`comprobar_simulados`, `simulados.py:827`), base, colección, Redis simulado | `GET /estado` | T1 |
| Apagar | `/apagar` | T1 |
| Usuarios `PRUEBA` (rol, temporal → `CF_Ultimo_acceso=NULL`, Inactivo) con la contraseña recibida | `/usuarios` | T3 |
| Residuos y limpieza total del entorno (filas fuera de los catálogos y del administrador sembrado, puntos, archivos, Redis simulado, buzón, programaciones, reloj) | `GET /residuos`, `/limpiar` | T3 |
| Correo: leer el código de un correo; programar fallo | `GET /correo/codigo`, `/correo` | T5 |
| Almacén temporal no disponible (`RedisControlable.no_responde`); avanzar el reloj (`avanzar`, `vincular_reloj`) | `/almacen`, `/reloj` | T5 |
| Filas de bitácora de cada tipo (incluidas carga cancelada, con error, «Gestionar Conversación», 16-18) | `/bitacora` | T5 |
| Motor: citar archivo, retener/liberar, secuencia, fallo de conexión, sin datos | `/motor`, `/motor/liberar` | T6 |
| Ingesta: procesar en el proceso (un hilo, fuera del bucle de la petición) con HTR y audio simulados; fallar o retener por nombre | `/ingesta`, `/ingesta/liberar` | T6 |
| Notebooks: retener la entrega de la vista previa; retener y hacer fallar la eliminación | `/notebooks`, `/notebooks/liberar` | T6 |

- La ingesta en el proceso reemplaza `procesar_archivo_celery.delay` como `Encolado` (`tests/soporte/flujos.py:122-136`), pero envía `apply(...)` a un `ThreadPoolExecutor(1)` en lugar de guardarla.
- La limpieza total vale porque la base nace vacía y es solo de la suite (como la 004, `contar_residuos`, `datos.py:408`); cubre los temas heredados y las claves `NB-<id>` sin registrarlos uno a uno.

## 5. Contraseñas (RA-02.43)
- La semilla vive solo en la memoria del orquestador y llega a Playwright por variable de entorno del proceso hijo; nunca a un archivo ni a la salida.
- Contraseña = `base64url(HMAC-SHA256(semilla, "<índice del trabajador>:<n>"))[:24]` más un sufijo fijo que cumple la política (≥ 8). La genera `contrasenas.js` en el trabajador; las nuevas (RF-01.43, RF-03.41) también.
- Viaja al control en el cuerpo de un `fetch` de Node (no la API `request` de Playwright, que entra en las trazas) y al navegador solo por el campo de contraseña.
- Artefactos: `trace: 'off'` y `video: 'off'` (la traza guarda los valores de `fill` y los cuerpos de las peticiones); `screenshot: 'only-on-failure'` (el campo muestra puntos); informe `list` + `json` en `test-results/`, sin HTML.
- Ocultar y buscar al final (decisión de Andrés, 22/10): primero `ocultarContrasenas` reemplaza cada contraseña de los artefactos de texto por `[CONTRASEÑA OCULTA]`; después la búsqueda recalcula las contraseñas posibles (trabajadores 0-199 × n 0-199) en un conjunto y recorre cada artefacto con una ventana de 24 caracteres (texto y binario como latin-1). La instancia guarda en memoria las que recibió y, al apagarse, cuenta coincidencias en su propio registro (`/tmp/servia_e2e/instancia.log`); solo devuelve el número.
- Comprobación (T10): `E2E_FALLO_PROVOCADO=1` activa una prueba de infraestructura que inicia sesión y falla a propósito; resultado esperado: «contraseñas en artefactos: 0».

## 6. Aislamiento del entorno de desarrollo (RA-02.41)
- Base y colección: solo `servia_pruebas_e2e`, validadas por `exigir_nombre_pruebas` antes de cada DDL y sobre lo que ya tomó el sistema (`validar_valores_efectivos`, `configuracion.py:172`).
- Redis y broker: `redis://redis-simulado.invalid:6379` + Redis simulado en el proceso; sin worker.
- `uploads/` y avatares: desviados a `/tmp/servia_e2e/` (`desviar_carpetas`, `simulados.py:391`). Fuera de `/app`: una escritura ahí reiniciaría el `--reload` de desarrollo.
- Frontend: `.env.local` no se toca (el entorno del proceso manda) y `.next` tampoco (`distDir` propio); `npm run build` con `npm run dev` activo solo rompe si comparten carpeta.
- Navegador: perfil temporal de Playwright (sin cookies del Chrome de Andrés); host `127.0.0.1` en la instancia frente a `localhost` en desarrollo.
- Comprobación automática: fixture de red (§7) y `GET :8000/` antes y después. Manual (exenta): conteos de desarrollo, fechas de `.env.local` y `.next`, `docker compose ps`.

## 7. Fixtures transversales (`e2e/soporte/fixtures.js`)
- **Proyectos**: `infraestructura` (sin navegador, una vez), `escritorio` (1366 × 768) y `pequena` (616 × 768, `grepInvert: /@solo-escritorio/`); `channel: 'chrome'`; `timeout: 60_000`, `globalTimeout: 600_000`, `expect.timeout: 10_000`; `workers: 1`, `retries: 0`.
- **Red** (RA-02.41, RNF-09.40): `context.on('request')` registra todo origen distinto de `http://127.0.0.1:3100`, `http://127.0.0.1:8100`, `data:` y `blob:`; al final la prueba falla y los nombra.
- **Consola** (RA-02.45): `console` de tipo `error` y `pageerror`; se descartan los provocados que la prueba declara (`consola.provocado(/401/)`) y los de `consola_declarada.js` (patrón, motivo, spec que lo corregirá). Advertencias, no.
- **Limpieza** (RA-02.42): automática tras cada prueba: `/limpiar` y luego `GET /residuos` igual a cero; si no, falla nombrando la tabla.
- **Accesible a 616 px** (RA-02.46): `exigirAccesible(locator)`: desplaza, comprueba la caja dentro de la ventana y que `elementFromPoint(centro)` sea el elemento o un descendiente. Las acciones de los flujos pasan por `pulsar()` y `escribir()`, que lo aplican en `pequena`.
- **Fallo esperado** (RA-02.44): `fallaEsperada(test, 'RF-19.40 · notebooks')` valida el formato y llama `test.fail(true, anotación)`; Playwright ya es estricto (si pasa, la corrida falla). Solo tras verla en rojo.
- **Sin pausas fijas** (RA-02.47): una prueba de infraestructura busca `waitForTimeout` y `setTimeout(` en `e2e/flujos/`.

## 8. Lista de páginas (RA-02.48), `e2e/soporte/paginas.js`
| Clase | Direcciones |
|---|---|
| pública | `/auth/login`, `/auth/recuperar-contrasenna` |
| por rol | Administrador: `/`, `/administracion/gestion-usuarios`, `/administracion/bitacora`; Usuario Gubernamental: `/`, `/ingesta-datos`, `/consulta-datos/chat`, `/consulta-datos/busqueda-similares`, `/notebooks` |
| grupo sin página | `/administracion`, `/consulta-datos` |
| inexistente | `/PRUEBA-no-existe` |

Escrita desde el ERS (RF-02, CU-03). La prueba compara con `frontend/pages/**` (sin `_app`, `_document`, `api/`) y falla nombrando la página sin clasificar o la que no existe.

## 9. Decisiones
1. Instancia con el código real más un router que solo monta el lanzador; descartado un indicador en `main.py` (tocaría producción, decisión 17).
2. Nombre activo elegido por código entre dos constantes; descartada una variable de entorno (la 002 prohíbe desactivar la protección por configuración).
3. uvicorn sin `--reload`; descartado el recargador (murió por memoria y vigilaría `/app`).
4. Limpieza total tras cada prueba; descartado el registro por prueba de la 004 (la interfaz crea datos que la prueba no ve, como los temas heredados).
5. `workers: 1`; descartado el paralelismo (instancia compartida y limpieza total).
6. Orquestador Node propio; descartado `webServer`/`globalSetup` de Playwright (no da el límite de preparación ni el «abortar antes del navegador» con motivo).
7. Compilar solo si cambia la huella; descartado compilar siempre (consume la preparación) y no compilar nunca (compilación vieja).
8. Token del control leído de un archivo `0600` de `/tmp` del contenedor; descartado pasarlo con `docker compose exec -e` (comportamiento sin verificar en Windows).
9. Trazas y video apagados; descartado `retain-on-failure` (guarda contraseñas y no hay forma fiable de enmascararlas).
10. Orden: sin opción nativa de orden inverso en Playwright; la independencia la garantizan la limpieza y los residuos por prueba, y se comprueba corriendo pruebas sueltas (`--grep`) y por archivo. Descartado un reordenamiento propio (complejidad sin ganancia).
11. Puertos 8100 y 3100 (libres en `docker-compose.yml`; HTR usa 9100).

## 10. Pruebas por requisito
Playwright (`<archivo>: <título>`; cada título empieza por su requisito). pytest: `test_instancia_e2e.py`.

| Requisito | Pruebas |
|---|---|
| RA-02.40 | `orquestador.spec.js`: `puerto ocupado`, `sin pruebas recolectadas`, `resumen con XPASS nombrado`; comandos de evidencia de T2 |
| RA-02.41 | `instancia.spec.js`: `usa servia_pruebas_e2e`, `desarrollo responde`; `red.spec.js`: `el navegador solo habla con la instancia`; pytest `test_configuracion_e2e_nombres_y_servicios_invalidos`, `test_proteccion_solo_los_dos_nombres`, `test_carpeta_temporal_fuera_de_app`; manual §12 |
| RA-02.42 | fixture de limpieza en todas; `instancia.spec.js`: `limpiar deja residuos en cero`; pytest `test_limpieza_rechaza_otra_base` |
| RA-02.43 | `orquestador.spec.js`: `búsqueda de contraseñas`; pytest `test_registro_cuenta_contrasenas_recibidas`; corrida con fallo provocado (T10) |
| RA-02.44 | `orquestador.spec.js`: `anotación de fallo esperado` |
| RA-02.45 | `red.spec.js`: `error de consola no declarado`, `error provocado y declarado` |
| RA-02.46 | proyectos `escritorio`/`pequena`; `red.spec.js`: `accesible detecta un control tapado` |
| RA-02.47 | límites de la configuración; `orquestador.spec.js`: `sin pausas fijas`; tiempos del resumen |
| RA-02.48 | `paginas-y-roles.spec.js`: `lista de páginas completa` |
| RA-02.49 | `instancia.spec.js`: `control ausente en desarrollo (404)`, `puerto cerrado tras apagar` (orquestador); `capacidades.spec.js` (T5, T6); pytest `test_control_ausente_en_main`, `test_vigilante_apaga_por_inactividad`, `test_motor_programable` |
| RNF-09.40 | `instancia.spec.js`: `simulados activos`; red; `NEXT_TELEMETRY_DISABLED` |
| RF-01.40 | `acceso.spec.js`: `sin sesión va a inicio de sesión y vuelve a la página pedida` |
| RF-01.41, RF-02.40 | `acceso.spec.js`: `cada rol entra a inicio con su menú y sus tarjetas` |
| RF-01.42 | `acceso.spec.js`: `credenciales inválidas idénticas en tres casos`, `campos obligatorios sin enviar`, `correo sin formato` |
| RF-01.43 | `acceso.spec.js`: `panel obligatorio no se cierra ni deja navegar`, `errores del panel`, `cambio y siguiente inicio sin panel` |
| RF-01.44 | `acceso.spec.js`: `cerrar sesión: ni Atrás ni la dirección vuelven` |
| RF-02.41 | `paginas-y-roles.spec.js`: `@solo-escritorio cada rol contra cada clase` |
| RF-02.42 | `cuentas.spec.js`: `crear cuenta: éxito y correo en fallo` |
| RF-03.40 | `cuentas.spec.js`: `resetear: explicación, éxito y correo en fallo con sesión activa` |
| RF-03.41 | `recuperacion.spec.js`: `mensaje uniforme en tres casos`, `sin afirmar ni negar la cuenta`, `código incorrecto, vencido y almacén no disponible`, `cinco intentos`, `código del correo simulado y nueva contraseña` |
| RF-21.40 | `historial.spec.js`: `detalle de creación y reseteo`, `detalle de recuperación`, `filtro trae recuperaciones sin usuario` |

Lo que no cumpla el ERS queda con `fallaEsperada` (p. ej., si «Inactiva» no da «Credenciales inválidas»), tras verlo en rojo.

## 11. Exenciones (spec, «Criterios de finalización»)
- Calidad de la respuesta del LLM y del modelo real: la suite usa el motor simulado (RNF-09.40); se verifica a mano con Ollama.
- Aspecto visual: no medible de forma fiable (principio 4); a mano a 1366 y 616 px.
- Entrega real del correo: no hay cuenta institucional; el correo simulado entrega el código.
- RA-02.41 (conteos, fechas, `ps`) y RA-02.49 (configuración de desarrollo): la suite no debe leer desarrollo.

## 12. Medición temprana (T1 y T2) y verificación manual
- **Memoria** (cgroup del contenedor, no solo `docker stats`): `memory.current`, `memory.peak` y `memory.events` (`oom`, `oom_kill`) con el backend de desarrollo solo, con la instancia en marcha y durante una corrida. Condición: sin reinicios ni eventos de falta de memoria. Si no alcanza: parar y preguntar.
- **Tiempos**: arranque de la instancia (base, migraciones, embeddings), compilación con y sin huella nueva, preparación total. Si pasa de 5 min: proponer el ajuste justificado a Andrés (decisión 19).
- **Manual de cierre (T10)**: Andrés inicia sesión (los agentes no reciben contraseñas) en el entorno de desarrollo con Ollama y el worker reales; acceso, roles, cuentas, reseteo, recuperación e Historial con los dos roles a 1366 y 616 px (Chrome normal; el del MCP no baja de ~555 px con zoom 0,9); consola limpia; conteos de desarrollo antes y después; limpieza de los datos `PRUEBA`.

## 13. Bitácora, datos e interfaz
- Bitácora (RF-21): ninguna acción nueva de usuario; el control crea filas solo en el entorno aislado, a pedido.
- Datos: sin migraciones; la base de pruebas se crea con las existentes.
- Interfaz: sin páginas nuevas ni cambios de `ROUTE_PERMISSIONS`.

## 14. Riesgos y trampas conocidas
- **Memoria**: dos procesos con el modelo de embeddings (~2,5 GB cada uno) en el mismo contenedor; WSL2 con 12 GB. Mitigación: medir en T1 antes de seguir.
- **0.0.0.0 dentro del contenedor**: Docker solo lo publica en 127.0.0.1, pero la red interna de Compose lo alcanza; por eso el token.
- `load_dotenv()` no pisa lo definido y `app.db.database` conecta al importarse: el lanzador fija el entorno antes de importar nada (`exigir_sin_modulos_importados`).
- `qdrant_backend._get_client()` crea la colección si falta: se crea antes con `DIM` y se valida el nombre.
- `npm run build` con `npm run dev` activo rompe `.next`: aquí no se comparte carpeta; T2 comprueba que `.next` no cambia y que `npm run dev` sigue respondiendo.
- Git Bash: `MSYS_NO_PATHCONV=1` en los comandos manuales con rutas del contenedor (`/sys/fs/cgroup/...`, `/tmp/...`). El orquestador usa `spawn` de Node: no le afecta.
- `docker compose restart backend` mata la instancia: la siguiente corrida reemplaza la base que quedó.
- El informe de errores de Playwright (`error-context`) puede incluir valores de campos: el orquestador oculta las contraseñas que encuentre en él antes de la búsqueda final de §5 (que debe dar 0).
- La suite de pytest ya está sobre su límite (9 min 22 s frente a 8 min 12 s): las pruebas pytest nuevas son unitarias y rápidas.
- RF-01.43 y RF-03.41 dependen de textos del ERS; si un texto cambia, cambia la prueba.
- **Riesgo aceptado (Andrés, 22/10/2026, opción A)**: las capturas de pantalla en fallo (`screenshot: 'only-on-failure'`; trazas y vídeo en `off`) son binarios PNG que el orquestador no oculta ni busca; el riesgo es bajo porque los campos de contraseña muestran puntos. Las contraseñas en los artefactos de texto sí se ocultan (`[CONTRASEÑA OCULTA]`, `ocultarContrasenas` en `e2e/ejecutar.mjs`).

## 15. Hook de la terminal (lo ajusta Andrés antes de T2)
Modo revisor de `.claude/hooks/validate-bash.sh` (lista `permitido`, líneas 100-108). Deben quedar permitidos, solos o encadenados con los ya permitidos:
- `npm run e2e`, `npm run e2e -- <args>`, `npm run e2e:apagar` y sus formas `npm --prefix frontend run e2e…`: cambiar `run (build|lint)` por `run (build|lint|e2e|e2e:apagar)` en las dos alternativas de `npm`.
- `docker compose exec( -T)? backend cat /sys/fs/cgroup/memory\.(current|peak|events|stat)` (medición, T1 y T10).
- `docker compose exec( -T)? backend python -m tests\.instancia_e2e( --apagar)?` y `docker compose exec -d backend python -m tests\.instancia_e2e` (T1, antes de que exista el orquestador).
El modo general no bloquea ninguno de estos. Los agentes no tocan `.claude/`.

## 16. Documentación al cierre de la 005a (T10)
- Specs 003, 003a y 003b: retirar la exención E2 (remitir a esta spec).
- Spec 002 (definición del entorno aislado) y `CLAUDE.md` («Comandos» y «Verificación»): dos entornos, `servia_pruebas` (pytest) y `servia_pruebas_e2e` (extremo a extremo); el comando `npm run e2e` (desde `frontend/`) y `npm run e2e:apagar`. `CLAUDE.md`: texto propuesto, lo aplica Andrés.
- Regla 5b, **solo propuesta** para `CLAUDE.md` y `.claude/rules/testing.md` (la edita Andrés): «Desde el cierre de la 005a, la "suite completa" de toda tarea que toque el frontend o la API incluye el extremo a extremo (`npm run e2e`)».
- `graphify-out/generar_mapa_pruebas.py` y `mapa_pruebas.md`: incluir `frontend/e2e/` (soporte y archivos de prueba con sus títulos) y `backend/tests/instancia_e2e/`; `frontend/e2e/` en `.graphifyignore`; `graphify update .` y `generar_mapa.py` (cambió `next.config.mjs`).
- `MEMORY.md`: estado, decisiones, medición de memoria y tiempos, y la medición de tokens prevista para la 005 (`rtk gain`; tamaño de spec, `plan-005a.md` y `tasks-005a.md` frente a la 004a: ~5k, ~8k y ~2k tokens).

## 17. Dudas resueltas (Andrés, 21/10/2026)
Sin dudas abiertas.
1. Puertos: A, 8100 (backend) y 3100 (frontend), solo en `127.0.0.1`.
2. Trazas y video de Playwright apagados; solo captura de pantalla al fallar (RA-02.43).
3. Recrear el `backend` en T1 para publicar el puerto lo hace Andrés: el implementer se detiene en ese punto y le avisa.
