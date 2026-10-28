# MEMORY.md — ServIA

Historial y detalle de specs cerradas: `docs/memoria_historial.md` (no se lee por defecto; consultarlo solo si la tarea lo necesita). Máx. 100 líneas; sin datos sensibles (repo público). Actualizado: 28/10/2026 (cierre de la 006).

## Estado actual

- Sistema funcionando (8 servicios + frontend npm, GPU 8 GB); rama de trabajo `fase4`. Fases 1-3 de la práctica cerradas; Fase 4 en curso (HTR integrado; manuscrito = limitación aceptada, RF-10).
- Suite vigente (cierre de la 006): pytest 2055 pasan + 47 `xfail`, 0 XPASS (normal e inverso); `npm run e2e` 145 = 135 + 8 esperados + 2 omitidas, ~475-501 s de 600 s, residuos 0, contraseñas 0. `-m infraestructura` aparte: sale con código 1 a propósito.
- Documentos vigentes (`Documentacion/Documentacion_ServIA_2026/`): ERS V1.8, CU V1.5 y Modelo Relacional V1.1 (los Word originales ya están en esas versiones, iguales a sus PDF en PDF/; ERS 34 y CU 37 págs.), HU y Procesos V1.2, C4 1.1; resto sin versión. Documentación aprobada por el tutor; se entrega completa al final del proyecto con la versión final de cada documento (carpeta "Documentación", semana 4), no versión a versión.
- PDF: `Nombre_V#.#.pdf`, vigente = versión más alta; el Word conserva el mismo nombre y su portada debe coincidir. Los agentes no leen `.docx` (el coordinador pasa la ruta). `Documentacion_Lista/` no se toca.

## En curso

- **Spec 006 (ingesta del piloto de Nexus): implementada y validada (@reviewer APROBADO, 28/10/2026)**; pendientes: commits con @committer y el piloto de Nexus (paso operativo de Andrés: cargar 10-30 PDF de Nexus como temas; cada PDF Procesado o en Error; el chat general cita al menos uno). Riesgo RF-06.2: elegir un tema en el chat consulta todos los documentos. Observación: en la verificación, la respuesta del chat no mostró el nombre del archivo como fuente. Detalle de decisiones (D1-D5 … DD1) en `specs/006-ingesta-nexus/`.
  - Resumen: tema recortado y normalizado en el servidor (60 caracteres; `ExpedienteService.resolver_o_crear_tema` lo crea al cargar, `uq_expediente_num` CI_AS rechaza la carrera); el documento se registra Pendiente antes de extraer y todo fallo lo deja en Error con «Causa: …» (RN-01); reintento de Celery reconocido por `ingesta:documento_de_tarea:<id>` (T3); frontend: un tema por archivo, confirmación agrupada, imágenes JPG/JPEG/PNG/TIF/TIFF/BMP, advertencia de manuscrito; rastreo de LangChain apagado en `config.py` (RNF-09.50). 4 xfail nuevos (RF-05.51 ×3, RF-07.53).
  - Texto propuesto para el ERS/CU acumulado en `spec.md` para la versión final: RF-05, RF-06 (60 caracteres y creación al cargar), RF-07 «Parcial» por la cancelación, RF-10, RNF-04, RNF-09; CU-07.
  - Limpieza de desarrollo hecha (28/10, EE1 = A): quedan vacíos como residuo (la bitácora los referencia) los temas 70004 `PRUEBA`, 70005 `PRUEBA 2`, 70007 `PRUEBA 3` y el notebook `PRUEBA 006` (80003, tema interno 70006). Tiempos e2e: M = 513,2 s (topes 543/560 s, límite 600): ante tiempos altos, repetir antes de recortar pruebas.
- **Spec 005a (extremo a extremo)**: aprobada y cerrada (22/10): @reviewer APROBADO en la vuelta 1 y Andrés (opción A). `npm run e2e` 104 = 98 pasan + 6 esperados, residuos 0, contraseñas 0; E2 retirada en 003/003a/003b; entorno aislado doble en la 002. Spec 005: «005a implementada; 005b pendiente». Detalle y hallazgos (a-j): `tasks-005a.md` y `docs/memoria_historial.md`.
  - **005b T1-T6 implementada y validada por @reviewer (APROBADO, 26/10); commits hechos y publicados (`918964d`..`c143300`, más `d8ec8da` y `d0727ed`)** (pasada final hecha: `consola_declarada.js`, `red.spec.js:105`, `carga.spec.js:5`; suites: pytest 2028 + 45 xfail, e2e 141 = 133 + 8 esperados; `graphify-out/` actualizado el 26/10 y mapas regenerados): control con etapa `vectorizacion`; soporte (`datos.js`, `pantallas.js`, fixtures `otraPestana`/`otroUsuario`); `carga.spec.js` (carga mixta, rechazados, cita en el chat general) y `notebooks.spec.js` (crear, cargar, vista previa, quitar); T3b: la vectorización fallida deja el documento en «Error» (`document_processor.py`, Andrés reinicia `backend` y `celery-worker`). Solo RF-19.40 nuevo con `fallaEsperada`; `fixtures.js` deja pasar el visor de PDF de Chrome. Texto para ERS V1.8 y la regla «cada spec prueba el módulo que toca»: `specs/005-.../documentacion_005b.md` (la aplica Andrés). La cita del chat es HU-12. Verificación manual hecha (Ollama real, ambos roles); limpieza de desarrollo hecha (opción A): se borraron Qdrant, notebook 70003, documentos, relaciones y archivos; los temas 60004 y 60005 quedan vacíos a propósito, porque `T_Bitacora.CN_Id_expediente` los referencia (11 filas, clave foránea y RN-01).
  - Hallazgos de la 005b: los de ingesta (dos temas en un Guardar, PDF dañado, desborde del aviso de rechazo) los corrigió la 006; queda «expediente» en el panel del Administrador y «Poder Judicial» en el pie.
- **Spec 004b**: T10 cerrada en la documentación (26/10): ERS V1.8 y CU V1.5, revisadas por Andrés (5 dudas opción A; RF-11 Parcial confirmado); PDF V1.8 / V1.5 exportados a `PDF/` (26/10) desde las copias de trabajo (`*_revision.docx`, ya borradas el 26/10 por ser idénticas a los originales). T10 aplicada del todo en la documentación (ERS, CU y Modelo Relacional V1.1, con los tipos de acción 16-18 verificados contra `TiposAccion` y la migración `b7c4d2e9f013`; PDF V1.1 exportado el 26/10). Los `.docx` originales se reemplazaron el 26/10 por las copias (respaldo de V1.7/V1.4/1.0 fuera del proyecto, sin commit aún); PDF V1.8 / V1.5 exportados el 26/10 desde las copias (Word por COM). Sin envío intermedio al tutor: se valida con la entrega final de la documentación.
- **Spec 004**: los cambios de RF-11, RF-12, RF-17, RF-20 y una frase de RNF-07 ya están en el ERS V1.8 y se validan con la entrega final; no hay envío intermedio pendiente.
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
- Graphify: el control de aplicaciones de Windows bloquea los lanzadores `.exe` (`graphify.exe`, `graphify-mcp.exe`), no el `python.exe` de uv. Se invoca así: en PowerShell `& "$(uv tool dir)\graphifyy\Scripts\python.exe" -m graphify update .`; en Git Bash `"$(uv tool dir)/graphifyy/Scripts/python.exe" -m graphify update .`. El MCP sigue pendiente de la decisión de Andrés sobre `.mcp.json`. Actualizado el 28/10 (cierre de la 006): 3700 nodos, 221 comunidades; se conservan los nombres existentes y los sin nombre son tarea aparte.
- Cada spec que cambie código: actualizar `graphify-out/` (`graphify update .` por esa vía, nombres de comunidades, `generar_mapa.py`, `generar_mapa_pruebas.py`; tras un PDF nuevo, `generar_documentacion_texto.py`).
- Interfaz: pantallas de acceso con tarjeta clara siempre (sin `dark:`); `ConfirmModal` llama a `onClose` tras `onConfirm`.

## Hallazgos sin corregir

- `metadata_fields.py` no coincide con las claves reales de Qdrant; Tika no hace OCR de imágenes.
- Bitácora de «Editar Usuario» lista todos los campos como modificados; hora del Historial en UTC vs. local.
- Ingesta: rechazados no cuentan en las estadísticas. `GET /archivos/expediente/{tema}/archivos` da 500 en la instancia e2e (`relative_to(os.getcwd())` con `uploads/` desviado).
- `console.error` heredado de `usuarioService.js`; sin botón para cambiar de tema.
- Ingesta (W1 = A, Andrés 27/10): si el worker muere a mitad de la vectorización y Celery reintenta la misma tarea, un documento Pendiente con fragmentos parciales se da por Procesado (T3); riesgo conocido y aceptado, para una spec posterior.
- Ingesta: `ingestaService.js` trata cualquier 404 como «tema no válido» (enmascara una ruta inexistente); `redis.setex` con DeprecationWarning en `progress_tracker.py:304`.
- Notebook: el aviso con nombre largo se desborda (U2, para la spec de mejoras del notebook); no hay borrado ni archivado de notebooks (residuo `PRUEBA 006`).
- Pruebas: `notebooks.spec.js:117` (RF-05.40) posiblemente inestable (falló 1 vez en T10, pasó al repetir) y fallo de lanzamiento de Chrome en T0; espacio perdido en `carga.spec.js:240` (estilo).- Más menores en el historial.


## Próximos pasos

1. Commits de la 006 con @committer (⚠️).
2. Piloto de Nexus (paso operativo de Andrés; ver «En curso»). La fuente: autorización por correo del 26/10 guardada por Andrés fuera del repositorio, autorizada por el tutor; ningún documento de Nexus va al repositorio. Pendiente aún de la 005b: Andrés aplica `documentacion_005b.md` (ERS V1.8, `testing.md`, `CLAUDE.md`) si no lo hizo.
3. Spec de mejoras del notebook (RF-19.40 confirmación, imagen pegada o arrastrada RF-05.23, desborde U2, borrado/archivado de notebook si Andrés lo quiere) y ajustes gráficos («expediente» en el panel del Administrador y tarjetas de inicio, «Poder Judicial» en el pie), con `/feature`.
4. Semana 4: documentación y cierre de la práctica. El tutor pide subir toda la documentación en una carpeta «Documentación»; hoy es `Documentacion/Documentacion_ServIA_2026/` (sin tilde): decidir al final, una sola vez, porque toca rutas de `CLAUDE.md`, los agentes y los scripts de graphify.
5. Después: spec de integración de imágenes (RF-09, `/sdd-change`); corregir el cambio obligatorio repetido tras la recuperación; nombres de comunidades del grafo. Con el tutor: «expediente» → «tema» y el correo institucional.