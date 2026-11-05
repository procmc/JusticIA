# Tareas 009 — Gestión de notebooks: renombrar y eliminar
Plan: `plan.md` (secciones citadas como §n). Presupuesto total ~4 h 10 min. Una tarea por llamada del implementer.

## Cierre estándar de cada tarea (se cita como «Cierre»)
1. Prueba en rojo primero: reportar el fallo de las pruebas nuevas antes del código.
2. Backend: `docker compose exec backend pytest` y `docker compose exec backend pytest --orden-inverso`, con 0 fallos, 0 XPASS y ningún `xfail` nuevo. Reportar pasan / fallan / esperados.
3. e2e, desde `frontend/`, SOLO lo que diga la tarea. Antes, `npm run dev` cerrado y ≥ 2,3 GB libres. Reportar recolectadas, pasan, fallan, esperados, XPASS, suite, residuos y contraseñas.
   - Subconjunto: `npm run e2e -- <archivo>`.
   - Completa: `npm run e2e` (~9 min; presupuesto de la suite ≤ 720 s; antes 569 s sobre el límite de 600 s, que Andrés subió a 720 s el 05/11).
4. `docker compose ps` sin reinicios y `docker compose logs --tail 100 backend` sin errores nuevos.
5. Marcar la tarea, anotar la evidencia aquí y actualizar `MEMORY.md` (una línea).
- No se usa el MCP `chrome-devtools`: la verificación visual la hace Andrés en persona.
- No se reinicia el servidor: uvicorn recarga solo; si muere, avisar a Andrés.
- Evidencia T2 (05/11): pytest 2257 pasan, 0 fallan, 47 xfail, 0 XPASS, residuos 0 (no se corrió `--orden-inverso`); e2e notebooks.spec.js 20 pasan, 4 omitidas (ya existentes), 0 fallan, 0 XPASS, residuos 0, contraseñas 0. Test extra actualizado por RF-21.81: `test_red_notebooks.py::test_nombre_vacio_o_espacios` (ahora espera 1 fila de bitácora).
- Evidencia T1 (05/11): pytest 2237 pasan, 0 fallan, 47 xfail, 0 XPASS, residuos 0; e2e historial 10/10, 0 residuos, 0 contraseñas; `alembic current` = d94c2a6e33a5.

## Tareas

- [x] **T1. Migración y catálogo (25 min).** RN-01.80, RF-21.80  ⚠️ archivo nuevo de migración y cambio de esquema; archivo nuevo `test_gestion_notebooks.py`
  - Pruebas: `test_migracion_tipos_y_columna`; cambios de expectativa del catálogo (§8: `test_aislamiento_notebooks.py:689-693` y `:729-730`, `test_usuarios_de_prueba.py:216`).
  - Pasos:
    - columna en `T_Notebook`, autogenerar y revisar la migración según §4, y `alembic upgrade head` en desarrollo;
    - `TiposAccion` 19 y 20, `le=20` en `routes/bitacora.py`;
    - `tiposAccion.js` y `bitacoraService.js`.
  - e2e: subconjunto `npm run e2e -- e2e/flujos/historial.spec.js`.
  - Hecho cuando: `alembic current` en la cabeza nueva, las pruebas y el Cierre pasan.

- [x] **T2. Reglas del nombre al crear y su bitácora (35 min).** RF-17.81, RF-17.82, RF-17.93, RF-17.84, RF-17.85, RNF-07.82, RF-21.81, RF-21.83, RF-17.91  ⚠️ archivo nuevo `test_nombre_notebook.py`
  - Pruebas:
    - unitarias `test_validar_nombre_*` y `test_admitido_*` (sin los casos de «propio»);
    - integración `test_crear_y_renombrar_rechazados` (parte de crear) y `test_nombre_no_latino_y_latino_con_tildes`;
    - nueva expectativa de `test_crear_con_error_inesperado_es_generico` (§8).
  - Pasos:
    - `validar_nombre`, `NombreNoValido` y `como_lo_guarda_la_base` (§2);
    - `registrar_creacion_fallida`;
    - ramas 400 y 500 de `POST /notebooks`;
    - revisión de nombres fijos en fixtures y en `inventario_rutas.py` (§8).
  - e2e: subconjunto `npm run e2e -- e2e/flujos/notebooks.spec.js`.
  - Hecho cuando: las pruebas y el Cierre pasan y ninguna prueba existente de notebooks falla por duplicado.

- [x] **T3. Renombrar y eliminar en la API (40 min).** RF-17.80, RF-17.83, RF-17.84, RF-17.87, RF-17.90, RNF-07.80, RNF-07.81, RF-21.81, RF-21.82, RF-21.83
  - Pruebas:
    - unitarias `test_renombrar_y_eliminar_no_disponible_antes_de_validar`, casos «propio» de `test_admitido_*` y `test_registro_sin_nombres_y_motivos_fijos`;
    - integración `test_renombrar_propio`, `test_eliminar_propio_conserva_todo`, `test_crear_y_renombrar_rechazados` (parte de renombrar), `test_no_disponible_404_uniforme`, `test_error_inesperado_renombrar_y_eliminar` y `test_bitacora_por_accion`.
  - Pasos: `renombrar`/`marcar_eliminado`, servicio, `PUT` y `DELETE /notebooks/{notebook_id}` con `id_de_notebook` (§2), auditoría (§6) e `inventario_rutas.py`.
  - e2e: exento (solo rutas nuevas que ninguna pantalla usa aún; las cubre T5).
  - Hecho cuando: las pruebas y el Cierre pasan.

- [x] **T4. El eliminado no está disponible en ninguna vía (30 min).** RF-17.88, RF-17.89 (servidor), RN-01.80
  - Pruebas: unitaria `test_conversacion_disponible`; integración `test_eliminado_no_disponible_en_toda_via` y `test_eliminar_con_documento_pendiente`.
  - Pasos: filtro de activos en `listar_por_usuario` y `obtener_por_id` (§3); `conversacion_disponible` en `rag.py:380`, `:435` y `:485`.
  - e2e: subconjunto `npm run e2e -- e2e/flujos/notebooks.spec.js`.
  - Hecho cuando: las pruebas y el Cierre pasan, y `curl` a Qdrant muestra los puntos del eliminado de la prueba manual.

- [x] **T5. Interfaz y e2e básicos (65 min).** RF-17.80-17.90, RF-17.92 (interfaz), RT-07.80  ⚠️ archivos nuevos `ItemNotebook.jsx` y `notebooks-gestion.spec.js`
  - Pruebas: las e2e básicas de §9, escritas primero y vistas en rojo con el subconjunto.
  - Pasos: `notebookService.js` (renombrar y eliminar), `ItemNotebook.jsx`, cambios de `index.js` y `pantallas.js:39` (§5).
  - e2e:
    - subconjunto `npm run e2e -- e2e/flujos/notebooks-gestion.spec.js` mientras se desarrolla;
    - al final, UNA corrida completa `npm run e2e`.
  - Además: `npm run lint`, y `npm run build` con `NEXT_DIST_DIR` distinto o con `npm run dev` cerrado.
  - Hecho cuando: e2e «CORRECTO» dentro del presupuesto, lint y build sin errores, y Andrés hizo la verificación manual (§10).

- [x] **T6. e2e diferibles (40 min; se difiere si falta tiempo).** RF-17.86 (doble clic), RF-17.89 (respuesta retenida), RF-17.92 (otra pestaña), RNF-04.80 (616 px)
  - Pruebas: las cuatro diferibles de §9.
  - e2e: subconjunto del archivo y UNA corrida completa al final. Si la suite pasa de 720 s, se repite una vez y se informa a Andrés (el recorte lo decide él, RA-02.80).
  - Si se difiere: anotar en `plan.md` §9 la exención de cada una, con la verificación manual de Andrés como evidencia, y dejar la deuda en `MEMORY.md`. La corrida completa de T5 cuenta como la de cierre.
  - Hecho cuando: las cuatro pasan a 1366 y 616 px y el Cierre pasa, o quedan sus exenciones anotadas.

- [x] **T7. Documentación, memoria y grafo (30 min).** Criterios de finalización  ⚠️ edición del ERS, de los Casos de Uso, de las Historias de Usuario y del Modelo Relacional
  - Pasos:
    - aplicar §11 sobre copias de los `.docx`, solo en `word/document.xml`, comparando el resto byte a byte;
    - spec en «implementada»; `MEMORY.md` (estado, decisiones, hallazgo de las rutas `int` existentes, deudas);
    - `graphify update .` y los dos mapas.
  - e2e: exento (solo documentación).
  - Hecho cuando: Andrés revisa los documentos y exporta los PDF.
  - Evidencia T7 (05/11): `.docx` editados solo en `word/document.xml` (el resto del zip idéntico byte a byte; XML bien formado): ERS V1.12, CU V1.9, HU V1.3, MR V1.2; respaldo de las versiones anteriores fuera del proyecto; `graphify update .` (4052 nodos) y los dos mapas regenerados. Pendiente de Andrés: revisar los Word, exportar los PDF y los diagramas (CU-17, CU-11, relacional).

- Evidencia correcciones del @reviewer, vuelta 1 (05/11): pruebas nuevas `test_eliminado_no_disponible_en_las_demas_vias` (RF-17.88: quitar documento, carga, temas similares por tema y texto, resumen y chats frente a una clave/id inexistente; las 7 vías ya cumplían), `test_error_inesperado_no_registra_texto_libre_de_la_url` (falló en rojo antes del cambio) y `test_filtro_por_tipo_nuevo` ahora incluye los tipos 19 y 20 (RF-21.80); `routes/notebooks.py` usa `_clave_validada` (el texto libre de la URL ya no llega a la bitácora; sin tema si el id no es canónico); docstring de la migración y prueba unitaria del nombre corregidos; borrada `frontend/.next-revisor/`; textos de los cuatro Word extraídos al scratchpad. Suite: ver MEMORY.md.

## Si falta tiempo
- Se difiere T6 completa (con exención y verificación manual de Andrés) y, dentro de T7, la edición de los `.docx`: el texto de RF-17, RF-21, RNF-10, el CU nuevo y las dos HU queda en la spec para la entrega final.
- T1 a T5 no se difieren (prioridades 1 y 2 de la spec).
