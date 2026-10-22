# Propuesta de texto para `CLAUDE.md` y la regla 5b (cierre de la 005a)

Documento de propuesta (plan 005a §16): lo aplica Andrés; los agentes no editan `CLAUDE.md` ni `.claude/`. Cada bloque dice dónde va.
Se suma a la reescritura corta de `CLAUDE.md` que Andrés prepare: las líneas de «Convenciones» sobre `tests.instancia_e2e` quedan cubiertas por los bloques B y C de abajo.

## A. «Comandos» (después de la línea de «Pruebas del backend»)

- Pruebas de extremo a extremo (desde `frontend/`, con el servidor `backend` en marcha; el `npm run dev` de desarrollo puede seguir activo): `npm run e2e` levanta una instancia aislada (backend en `127.0.0.1:8100`, frontend de pruebas en `127.0.0.1:3100`, base y colección `servia_pruebas_e2e`), corre Playwright en escritorio (1366 px) y en pantalla pequeña (616 px), imprime el resumen (recolectadas, pasan, fallan, fallos esperados, XPASS, preparación, suite, residuos, contraseñas en artefactos) y la apaga. Con argumentos: `npm run e2e -- --grep RF-03.41` o `npm run e2e -- e2e/flujos/acceso.spec.js`. Si una corrida quedó a medias: `npm run e2e:apagar`. El resultado es «CORRECTO» solo con 0 fallos, 0 XPASS, residuos 0 y contraseñas 0.
- Una corrida completa tarda unos 6 minutos (preparación ~25 s, suite ~5 min; límites 300 s y 600 s). Cada corrida reemplaza la base `servia_pruebas_e2e`; `docker compose restart backend` mata la instancia.

## B. «Convenciones» o «Reglas de dominio» (pruebas de extremo a extremo)

- Hay dos entornos aislados: `servia_pruebas` (pytest) y `servia_pruebas_e2e` (extremo a extremo). La protección acepta solo esos nombres completos; el extremo a extremo nunca lee ni escribe los datos de desarrollo, y desvía `uploads/` y los avatares a `/tmp/servia_e2e`. Los motores (LLM, HTR, audio, correo, Redis) son simulados y se programan por el control de la instancia (`backend/tests/instancia_e2e/`); no existe en `main`.
- Las contraseñas de la suite las genera cada corrida y no se escriben ni se muestran. Antes de la búsqueda final, el orquestador (`ocultarContrasenas` en `e2e/ejecutar.mjs`) reemplaza cada contraseña por `[CONTRASEÑA OCULTA]` en los artefactos de texto de `test-results/` (`error-context.md`, json, md, log…) y cuenta las que queden como «contraseñas en artefactos»; no se abre ni se pega en una conversación el contenido de `test-results/`. Las capturas de pantalla en fallo (PNG, `only-on-failure`) no se ocultan ni se buscan: riesgo bajo aceptado (los campos de contraseña muestran puntos); trazas y vídeo están apagados.
- Cada prueba de Playwright empieza con su requisito (`RF-01.40 · …`) y un fallo del ERS se marca con `fallaEsperada(test, '<requisito> · <módulo>')` tras verlo en rojo.
- Una página nueva del frontend debe quedar clasificada también en `frontend/e2e/soporte/paginas.js` (la prueba `RA-02.48` falla si falta).

## C. «Infraestructura» / «Nunca» (procesos)

- **Nunca mates procesos por nombre de imagen** (`taskkill /IM node.exe`, `pkill node`): mata el `npm run dev` de desarrollo (puerto 3000). Detén lo tuyo por PID o con `npm run e2e:apagar`, y comprueba con `curl http://localhost:3000/` que desarrollo sigue vivo.
- En Git Bash, los comandos manuales con rutas del contenedor (`/sys/fs/cgroup/...`, `/tmp/...`) necesitan `MSYS_NO_PATHCONV=1`.
- `npm run build` con `npm run dev` activo pisa `.next`; el extremo a extremo usa su propia carpeta y no lo afecta.

## D. «Verificación» (sustituye la primera viñeta de pruebas)

- Pruebas: la suite completa es `docker compose exec backend pytest` y, si la tarea toca el frontend o la API, también `npm run e2e` (desde `frontend/`); ambas usan entornos aislados y datos inventados con el prefijo `PRUEBA`, y cada prueba limpia lo que crea. El extremo a extremo ya existe (spec 005a: acceso por rol, menú, cuentas, recuperación de contraseña e Historial; la 005b cubrirá ingesta, chat y notebooks).
- Interfaz: la verificación manual con el navegador (`chrome-devtools`) se hace sobre desarrollo y a 1366 px y 616 px; el agente nunca recibe contraseñas ni códigos: inicia sesión y los escribe Andrés en el navegador.
- El MCP `chrome-devtools` usa un perfil propio: Andrés inicia sesión en esa ventana. Con su zoom de 0,9, `emulate` 1229 equivale a 1365 px CSS y 554 a 615 px CSS.

## E. Regla 5b (`CLAUDE.md`, «Forma de trabajar» / «Siempre», y `.claude/rules/testing.md`, «Orden de trabajo» y «Evidencia»)

> **5b. Desde el cierre de la 005a, la «suite completa» de toda tarea que toque el frontend o la API incluye el extremo a extremo** (`npm run e2e`, desde `frontend/`), además de `docker compose exec backend pytest`. La evidencia reporta ambas salidas (pasan, fallan, fallos esperados, XPASS, residuos y contraseñas en artefactos). Una tarea que solo toca documentación o el backend sin efecto en la API puede omitir el extremo a extremo si lo justifica.

Cambios concretos en `.claude/rules/testing.md`:

- «Tipos de prueba → Extremo a extremo»: añadir «Existe desde la spec 005a: `npm run e2e` (Playwright, instancia aislada `servia_pruebas_e2e`)».
- «Orden de trabajo», punto 2: marcar la parte de infraestructura de extremo a extremo y los flujos de acceso como hechos; quedan ingesta, chat y notebooks (005b).
- «Evidencia»: añadir «y la del extremo a extremo cuando la tarea toca el frontend o la API».
- «Datos de prueba»: sin cambios (ya dicen que las contraseñas de la suite no se escriben ni se muestran).

## F. Hook de la terminal (`.claude/hooks/validate-bash.sh`, ya ajustado en parte)

Comprobar que en el modo revisor siguen permitidos `npm run e2e`, `npm run e2e -- <args>`, `npm run e2e:apagar` y `docker compose exec -T backend cat /sys/fs/cgroup/memory.(current|peak|events|stat)` (plan §15).
