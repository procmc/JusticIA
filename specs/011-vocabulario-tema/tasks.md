# Tareas 011 — Vocabulario «tema» en toda la interfaz
Plan: `plan.md`. Seis tareas (~3 h 15 min). Sin migración, esquema, dependencias ni cambios de rol. Una tarea por llamada del implementer. Aprobado por Andrés el 12/11/2026, incluido RT-06.133 (textos que se le dan al modelo), que va en la T5.

## Cierre (se cita como «Cierre»)
1. Pruebas nuevas en rojo antes del código; reportar el fallo.
2. Cada tarea corre sus pruebas y las relacionadas; la suite completa de pytest (normal e inverso) y `npm run e2e` van **una sola vez en la T6**, para no gastar ~1 hora tras cada tarea. El e2e completo no cabe en `globalTimeout` de 720 s: se corre en dos mitades (ver 009b T19) hasta que Andrés decida el límite.
3. `docker compose ps` sin reinicios y sin errores nuevos en el log del backend.
4. Marcar la tarea, anotar la evidencia y una línea en `MEMORY.md` (máximo 100 líneas).
5. Las pruebas existentes que comparan un texto con «expediente» se **actualizan**, no se borran ni se desactivan.

- [ ] **T1. Bitácora del Administrador y Estadísticas (30 min + e2e de subconjunto).** RF-22.130, RF-22.131, RF-22.132, RF-22.134, RF-23.130, RNF-04.130
  - Pruebas (e2e, en rojo primero; Administrador; escritorio y 616 px): el filtro dice «Tema» con la ayuda «Nombre del tema»; la columna dice «TEMA»; el detalle de un registro de carga, de una consulta de un tema y de una acción de notebook (clave `NB-<id>`) usa «Tema»/«Temas»/«Cantidad de temas»/«Temas encontrados (los más relevantes)»; filtrar por `NB-<id>` sigue funcionando; la pestaña Estadísticas dice «Temas», «Temas más Consultados», «Top 5 de temas con más actividad» y «Consultas por Tema»; el texto visible de la página no contiene «expediente» salvo dentro de un registro ya guardado (se siembra uno con esa palabra); sin errores en la consola ni desplazamiento horizontal.
  - Pasos: `FiltrosBitacora.jsx`, `TablaBitacora.jsx`, `InformacionAdicionalRenderer.jsx`, `DetalleEvento.jsx` (comprobar «Tema» / «Sin tema asociado») y `DashboardEstadisticas.jsx`, según el plan §1.
  - Hecho cuando: las pruebas pasan en ambos anchos, lint sin errores nuevos y las pruebas existentes de la bitácora siguen pasando (ajustadas a «tema»).

- [ ] **T2. PDF, validaciones, servicios, rol e inicio (25 min + e2e de subconjunto).** RF-22.133, RT-06.130, RT-06.131
  - Pruebas (en rojo primero): e2e de Ingesta de Datos con un tema vacío o muy corto: el aviso dice «El tema es requerido» o «El tema debe tener al menos <N> caracteres» y no menciona `YY-NNNNNN-NNNN-XX`, y uno de más de 60 caracteres «El tema no debe exceder 60 caracteres»; e2e del inicio (tarjeta «Reportes de Temas» y su descripción) y de la descripción del rol del Usuario Gubernamental; el panel de detalle de Temas Similares sin tema dice «No se encontró el tema»; la exportación a PDF no falla (el contenido se lee a mano, ver plan §6).
  - Pasos: `exportService.js`, `expedienteValidator.js`, `bitacoraService.js`, `ingestaService.js`, `similarityService.js`, `ResumenTab.jsx`, `roles.js` y `pages/index.js` (las URL `?mode=expediente` y `scroll=expedientes` no cambian).
  - Hecho cuando: las pruebas pasan en ambos anchos, lint sin errores nuevos y las pruebas existentes de Ingesta y de la bitácora siguen pasando.

- [ ] **T3. Servidor: mensajes de la API y descripción de los registros nuevos (35 min).** RF-21.130, RT-06.132, RNF-03.130
  - Pruebas (en rojo primero): **unitarias**: cada constructor de la descripción de un registro de los servicios de auditoría (archivos, consulta del chat, resumen de Temas Similares y los demás que el barrido encuentre) con datos inventados no contiene «expediente» y sí «tema»; **integración** (API real, SQL Server, Qdrant y Tika del entorno aislado): los mensajes de error de `archivos`, `rag` e ingesta dicen «tema»; un listado y una descarga de archivos dejan registros nuevos con «tema»; **un registro viejo insertado por la prueba con «expediente» se devuelve sin cambios** por la consulta de la Bitácora y entra en la exportación y los filtros junto a los nuevos; las estadísticas siguen contando igual.
  - Pasos: `routes/archivos.py`, `routes/rag.py`, `schemas/ingesta_schemas.py`, `rag_chain_service.py` (los avisos de cambio de tema, si siguen en uso), `bitacora_stats_service.py`, `archivos_audit_service.py`, `rag_audit_service.py`, `similarity_audit_service.py` y los demás servicios de auditoría; `docker compose restart backend celery-worker`.
  - Hecho cuando: las pruebas pasan, las claves técnicas, rutas y parámetros de la API están intactos (se comprueba con las pruebas de rutas e inventario que ya existen) y no hay errores nuevos en el log.

- [ ] **T4. Recorrido del resto de pantallas del Usuario Gubernamental (30 min + e2e de subconjunto).** RT-06.130, RT-07.130, RNF-04.130
  - Pruebas (e2e, en rojo primero; ambos anchos): un recorrido que abre Ingesta de Datos (campo, lista de archivos, confirmación), el chat general y de un tema, Temas Similares (modo descripción y por tema, y el panel de detalle), NotebookServIA, el inicio y el menú, y comprueba que el **texto visible** no contiene «expediente» (excluye el contenido de documentos y los nombres que el usuario escribió, que se siembran con esa palabra para probar que se respetan).
  - Pasos: corregir lo que el recorrido encuentre en la interfaz (textos partidos o construidos que el barrido no vio) y repetirlo hasta que pase.
  - Hecho cuando: el recorrido pasa en ambos anchos, lint sin errores nuevos y las pruebas de las pantallas tocadas siguen pasando.

- [ ] **T5. ⚠️ Textos que se le dan al modelo (25 min).** RT-06.133  ⚠️ toca prompts: aprobado por Andrés el 12/11/2026 («si correcto»)
  - Pruebas (modelo simulado; en rojo primero): el contexto del chat que recibe el modelo trae «Tema: X» y «Sin tema» y ya no «Expediente: X» ni «Sin expediente»; el resumen de Temas Similares se genera con las instrucciones nuevas y conserva sus campos (resumen, palabras clave, factores de similitud y conclusión); el resumen de respaldo dice «del tema» y «Materia Jurídica del Tema»; no se prueba el texto de las respuestas del modelo.
  - Pasos: `chunk_context_builder.py`, `similarity_prompt_builder.py` y `response_parser.py` (solo la palabra; ninguna otra instrucción cambia); `docker compose restart backend celery-worker`.
  - Hecho cuando: las pruebas del chat y de Temas Similares siguen pasando, la prueba de `chunk_context_builder` y las del chat de un tema y de un notebook (aislamiento) no se rompen y el log queda sin errores nuevos.

- [ ] **T6. Verificación completa y revisión manual (40 min + suites).** Todos los requisitos de la spec
  - Pruebas: sin código nuevo. `docker compose exec backend pytest` normal e inverso; `npm run e2e` completo (en dos mitades si sigue sin caber en 720 s); lint.
  - Verificación manual (Andrés, plan §7): Bitácora (filtros, tabla, detalle de carga y de consulta, Estadísticas, exportar y abrir el PDF), Ingesta (tema vacío o corto), chat con y sin tema, Temas Similares, notebooks, inicio y menú, a 1366 y 616 px, con ambos roles; ningún texto dice «expediente» (los registros viejos sí); consola limpia.
  - Hecho cuando: el Cierre pasa con pytest y e2e sin fallos nuevos (residuos 0, contraseñas 0) y Andrés confirma la verificación manual.

- **Documentación, memoria y grafo (al final de T6, no cuenta como tarea aparte)**
  - ERS, historias de usuario y casos de uso: sin cambios de contenido (ya dicen «tema»); se cierra el «Estado actual» de RF-22 en lo del vocabulario y se anota en RF-21 que los registros anteriores conservan «expediente» en su descripción.
  - `graphify update .`, nombres de comunidades, `graphify-out/generar_mapa.py` y `graphify-out/generar_mapa_pruebas.py`; una línea en `MEMORY.md`.
  - Si falta tiempo: T1 a T4 se cierran con el código; T5 puede dejarse para otra sesión (RT-06.133 es lo único que cambia lo que ve el modelo).
