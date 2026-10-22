# MEMORY.md — ServIA

Historial y detalle de specs cerradas: `docs/memoria_historial.md` (no se lee por defecto; consultarlo solo si la tarea lo necesita). Máx. 100 líneas; sin datos sensibles (repo público). Actualizado: 22/10/2026 (cierre 005a).

## Estado actual

- Sistema funcionando (8 servicios + frontend npm, GPU 8 GB); rama de trabajo `fase4`. Fases 1-3 de la práctica cerradas; Fase 4 en curso (HTR integrado; manuscrito = limitación aceptada, RF-10).
- Suite vigente: pytest 2021 pasan, 45 `xfail`, 0 XPASS, sin residuos (~9 min, aceptado); `npm run e2e` 98 pasan + 6 esperados (~4,5 min). `-m infraestructura` aparte: sale con código 1 a propósito.
- Documentos vigentes (`Documentacion/Documentacion_ServIA_2026/`): ERS V1.7, CU V1.4, HU y Procesos V1.2, C4 1.1; resto sin versión. Enviados al tutor el 30/09, revisión pendiente.
- PDF: `Nombre_V#.#.pdf`, vigente = versión más alta; el Word conserva el mismo nombre y su portada debe coincidir. Los agentes no leen `.docx` (el coordinador pasa la ruta). `Documentacion_Lista/` no se toca.

## En curso

- **Spec 005a (extremo a extremo)**: aprobada y cerrada (22/10): @reviewer APROBADO en la vuelta 1 y Andrés (opción A). `npm run e2e` 104 = 98 pasan + 6 esperados, residuos 0, contraseñas 0; E2 retirada en 003/003a/003b; entorno aislado doble en la 002. Spec 005: «005a implementada; 005b pendiente». Detalle y hallazgos (a-j): `tasks-005a.md` y `docs/memoria_historial.md`.
  - Pendientes aparte: `contar_residuos_e2e` (`backend/tests/instancia_e2e/control.py:163-171`) sin reintento (excepción = 500 sin `detail`); causa real del 500 de `/limpiar` sin confirmar (si reaparece, `/tmp/servia_e2e/instancia.log`).
  - Propuesta de texto para `CLAUDE.md` y la regla 5b: `specs/005-red-de-seguridad-extremo-a-extremo/propuesta_claude_005a.md` (la aplica Andrés).
- **Spec 004b**: T10 pendiente: Andrés pega `documentacion_t10.md` en Word y exporta ERS V1.8 y CU V1.5; falta el visto bueno del tutor.
- **Spec 004**: pendiente el visto bueno del tutor para RF-11, RF-12, RF-17, RF-20 y una frase de RNF-07 (irá en ERS V1.8).
- Hallazgos sin `xfail` seguro (004/004b): chat de notebook registrado como «general», `str(e)` en 400/500, 500 en `mi-historial` y `expediente/{n}`, bitácora desfasada 6 h, logout toma el usuario del cuerpo; lista completa en el historial.
- Notebooks `PRUEBA 004b A/B` y B `PRUEBA` se conservan para la 005.

## Decisiones vigentes

- La documentación define el producto; la spec es referencia viva y todo cambio pasa primero por ella. `CLAUDE.md` no lleva estado; el planner no edita el ERS ni `CLAUDE.md`.
- «Expediente» → «tema» en código/BD solo con confirmación del tutor.
- Pruebas automatizadas obligatorias; meta: una por requisito, no 100 % de cobertura.
- Correo de desarrollo: Mailtrap (solo datos inventados); credenciales en `backend/.env`; necesita `EMAIL_PROVIDER=custom` y `EMAIL_USE_TLS=true`.
- Correos enmascarados en registros de cuentas; los `send_*` devuelven `bool` sin lanzar; los errores de recuperación de contraseña nunca son 401/403/404 (cerrarían la sesión).
- Agentes con lista cerrada de herramientas: implementer sin `Skill` ni Context7 (si falta una API, pide la consulta al coordinador); reviewer e implementer llevan `Monitor` junto a `mcp__chrome-devtools`.
- Aislamiento de notebooks: lo ajeno da 404 uniforme; los 500 registran tipo y traza, no el texto de la excepción.

## Errores a evitar

- Fallas silenciadas (filtro de Qdrant, `num_ctx`, un join, la clave de metadatos): probar con datos reales de punta a punta.
- `npm run build` con `npm run dev` activo pisa `.next`: usar `NEXT_DIST_DIR` distinto o detener el servidor. `npm run lint` es seguro. Tocar `next.config.mjs` reinicia `npm run dev`.
- Chrome del MCP `chrome-devtools`: no abre el diálogo de archivos; `upload_file` solo acepta rutas dentro del proyecto. Zoom 0,9 (`emulate` 1229 = 1365 px CSS, 554 = 615); perfil propio: Andrés inicia sesión en esa ventana.
- Simulados: parchar la instancia, no la clase. Los agentes no reinician el servidor: reiniciar `backend` y `celery-worker` a mano (el recargador puede morir por memoria). El `.env` solo se lee al reiniciar.
- Agentes: no reciben contraseñas ni inician sesión. Revertir mutaciones de prueba con `cmp` contra respaldo y revisar el diff al retomar.
- `.docx`: no usar python-docx; editar solo `word/document.xml` dentro del zip, sobre copia fuera del proyecto, y comparar el resto byte a byte. Leer el archivo vigente antes de decir que se actualizó.
- Pruebas: `qdrant_backend._get_client()` CREA la colección si falta (usar la fixture); comparar ids de Qdrant como `uuid.UUID`; una prueba con `await` se cuelga si el código falla; medir memoria con el cgroup. Editar `backend/` recarga uvicorn.
- Agentes: nunca matar procesos por nombre (`taskkill /IM node.exe`): mata el `npm run dev` de Andrés; apagar solo por PID o con `npm run e2e:apagar`.
- e2e: Next 15.2.4 normaliza el loopback a `localhost` (`NextURL`), así que el middleware redirige a `localhost:3100`. Andrés eligió la opción D: la reescritura vive en `e2e/soporte/fixtures.js` (página automática); quitarla cuando el centinela de `red.spec.js` falle.
- Aserciones de e2e: no usar `JSON.stringify` de un usuario con contraseña; no probar un mensaje con una expresión que el propio localizador cumple (`/tapado/` con `#tapado`).
- Git Bash: heredoc con comillas invertidas falla; `docker compose exec -w` y `docker cp` necesitan `MSYS_NO_PATHCONV=1`; no editar con Python en heredoc si el texto lleva `\n` o `\b`.
- Cada spec que cambie código: actualizar `graphify-out/` (`graphify update .`, nombres de comunidades, `generar_mapa.py`, `generar_mapa_pruebas.py`; tras un PDF nuevo, `generar_documentacion_texto.py`).
- Interfaz: pantallas de acceso con tarjeta clara siempre (sin `dark:`); `ConfirmModal` llama a `onClose` tras `onConfirm`.

## Hallazgos sin corregir

- `metadata_fields.py` no coincide con las claves reales de Qdrant; Tika no hace OCR de imágenes.
- Bitácora de «Editar Usuario» lista todos los campos como modificados; hora del Historial en UTC vs. local.
- Ingesta: rechazados no cuentan en las estadísticas; cambiar el tema reescribe el de todos los pendientes.
- `console.error` heredado de `usuarioService.js`; sin botón para cambiar de tema.
- Sin `LANGSMITH_TRACING=false` fijado en la suite (RNF-09). Más menores en el historial.

## Próximos pasos

1. Andrés aplica `propuesta_claude_005a.md` en `CLAUDE.md` y `.claude/rules/testing.md`; commits con @committer (push de `fase4`, Andrés).
2. Plan de la 005b; nombres de las comunidades del grafo (116 de 225, tarea aparte).
3. Corregir el cambio obligatorio repetido tras la recuperación pública (aclarar antes el ERS); hallazgos (a), (d)-(j) de la 005a para las retroactivas (autenticación y usuarios, bitácora).
4. Cerrar la T10 de la 004b; luego specs retroactivas por módulo (ingesta, RAG, notebooks…).
5. Spec de integración de imágenes (RF-09, `/sdd-change`: docTR vs. qantev) tras la red de seguridad; valorar quitar el MCP de graphify con el ahorro medido (`rtk gain`).
6. Con el tutor: revisión de los 9 documentos, «expediente» → «tema», Nexus.PJ, correo institucional.
