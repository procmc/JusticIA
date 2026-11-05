# Tareas 009b — Fuentes del notebook
Plan: `plan.md` (§n). Empieza cuando la 009 cierre T7. Entrega 1 ~2 h (T1-T3); entrega 2 ~2 h 45 min (T4-T7); documentación 30 min. Una tarea por llamada del implementer.

## Cierre estándar (se cita como «Cierre»)
1. Pruebas nuevas en rojo antes del código; reportar el fallo.
2. `docker compose exec backend pytest` y `... pytest --orden-inverso`: 0 fallos, 0 XPASS, ningún `xfail` nuevo; reportar pasan / fallan / esperados.
3. e2e (desde `frontend/`) SOLO lo que diga la tarea, con `npm run dev` cerrado y ≥ 2,3 GB libres.
   - Subconjunto: `npm run e2e -- <archivo>` (~1-2 min). Completa: `npm run e2e` (~9-10 min; suite ≤ 569 s).
   - Reportar recolectadas, pasan, fallan, esperados, XPASS, suite, residuos y contraseñas.
4. `docker compose ps` sin reinicios; `docker compose logs --tail 100 backend` sin errores nuevos.
5. Marcar la tarea, anotar la evidencia aquí y una línea en `MEMORY.md`. Sin `chrome-devtools` ni reinicios: la verificación visual es de Andrés.

## Entrega 1 — casilla y menú ⋮ con «Quitar fuente» (sin migración)

- [ ] **T1. Selección en el chat del notebook (servidor) (35 min).** RF-11.101, RF-11.102, RF-11.105, RF-11.106, RF-11.107, RNF-07.100, RF-21.102  ⚠️ archivos nuevos `test_fuentes_notebook.py` (unitarias e integración)
  - Pruebas: unitarias `test_seleccion_efectiva_*`, `test_seleccion_formato_422`; integración `test_chat_notebook_respeta_la_seleccion`, `test_seleccion_vacia_o_inefectiva_400`, `test_seleccion_ausente_como_hoy`, `test_seleccion_ignorada_en_general_y_tema`, `test_seleccion_ajena_descartada` (§9).
  - Pasos: `documentos` con `StrictInt`, `seleccion_efectiva`, `SeleccionVacia` y su 400, retriever con `documentos_visibles` (§2).
  - e2e: exento (campo opcional; ausente = hoy; la completa va en T3).
  - Hecho cuando: las pruebas y el Cierre pasan.

- [ ] **T2. Fila de fuente con menú ⋮ y «Quitar fuente» (35 min).** RF-19.100, RF-19.101, RF-21.103  ⚠️ archivos nuevos `FuenteNotebook.jsx` y `notebooks-fuentes.spec.js`
  - Pruebas: e2e `RF-19.100 · el menú no abre la vista previa ni cambia la casilla` (sin la casilla aún: solo la vista previa).
  - Cambian su expectativa (§8): `pantallas.js:70` y `:84`, `notebooks.spec.js:295`; RF-19.40-42 deben seguir pasando sin tocar sus aserciones.
  - Pasos: `FuenteNotebook.jsx` (nombre, ⋮, `aria-disabled` al quitar), lista en `index.js` (:517-537), quitar el guardia `close chip` (:192) (§5).
  - e2e: subconjuntos `npm run e2e -- e2e/flujos/notebooks.spec.js` y `... notebooks-fuentes.spec.js`.
  - Además: `npm run lint`.
  - Hecho cuando: los subconjuntos, lint y el Cierre pasan.

- [ ] **T3. Casilla y envío de la selección (40 min + 10 de e2e completo).** RF-11.100, RF-11.102, RF-11.103, RF-11.104, RF-11.106, RNF-04.100, RT-07.100
  - Pruebas: e2e `RF-11.100 · RF-11.102 …`, `RF-11.104 · RF-11.106 …`, `RF-11.103 …`, `RNF-04.100 …` (616 px); completar RF-19.100 con la casilla.
  - Pasos: `Checkbox`, `desmarcadas`, `consultaService.js` (`documentos`), envío desactivado y aviso, `datos.js:99` (§5).
  - e2e: subconjunto mientras se desarrolla; al final UNA corrida completa `npm run e2e` (cierre de la entrega 1).
  - Además: `npm run lint`; `npm run build` con `NEXT_DIST_DIR` distinto o `npm run dev` cerrado.
  - Hecho cuando: e2e «CORRECTO» dentro del presupuesto, lint y build limpios, y Andrés hizo la verificación manual de la entrega 1 (§10).

## Entrega 2 — cambiar el nombre

- [ ] **T4. Migración y tipo 21 (25 min).** RN-01.100, RF-21.100  ⚠️ migración nueva y cambio de esquema
  - Pruebas: `test_migracion_tipo_21_y_columna`; cambios de expectativa del catálogo (§8).
  - Pasos: columna en `T_Documento`, migración tras la cabeza de la 009 (§4), `alembic upgrade head` en desarrollo; `TiposAccion` 21, `le=21`, `tiposAccion.js`, `bitacoraService.js`.
  - e2e: exento (solo catálogo; lo cubre la completa de T7).
  - Hecho cuando: `alembic current` en la cabeza nueva y el Cierre pasa.

- [ ] **T5. Reglas del nombre y ruta `PUT` (40 min).** RF-19.102, RF-19.106, RF-19.107, RF-19.108, RF-19.109, RNF-07.101, RF-21.101, RF-21.104
  - Pruebas: unitarias `test_extension_de`, `test_renombrar_documento_*`; integración `test_renombrar_rechazos_400`, `test_renombrar_no_disponible_404`, `test_bitacora_renombrar`.
  - Pasos: `extension_de`, `nombre_mostrado`, `mensaje_vacio` en `validar_nombre`, `como_lo_guarda_la_base`, `renombrar` del repositorio, ruta, auditoría e `inventario_rutas.py` (§3, §6). Fuentes en Error primero (sin Qdrant).
  - e2e: exento (ruta nueva sin pantalla aún; la cubre T7).
  - Hecho cuando: las pruebas y el Cierre pasan.

- [ ] **T6. Fragmentos, compensación y nombre mostrado (35 min).** RF-19.103, RF-19.104, RF-19.105, RF-19.108, casos límite de carga
  - Pruebas: unitaria `test_renombrar_compensacion`; integración `test_renombrar_fuente_procesada`, `test_renombrar_compensa_si_falla_qdrant`, `test_carga_tras_renombrar`.
  - Pasos: `actualizar_nombre_de_documento` (§7.8) y sus simulados; orden y compensación (§3); listado con `extension`; `filename` en la vista previa.
  - e2e: subconjunto `npm run e2e -- e2e/flujos/notebooks.spec.js` (el listado cambia de forma).
  - Hecho cuando: las pruebas y el Cierre pasan.

- [ ] **T7. Interfaz de renombrar (45 min + 10 de e2e completo).** RF-19.102, RF-19.103, RF-19.105, RF-19.107, RF-19.109, RF-19.110, RNF-04.100
  - Pruebas: e2e de la entrega 2 (§9); diferibles solo si hay tiempo.
  - Pasos: `renombrarDocumento` en `notebookService.js`, edición en línea y opción desactivada en `FuenteNotebook.jsx` (§5).
  - e2e: subconjunto mientras se desarrolla; al final UNA corrida completa. Si pasa de 569 s, se repite una vez y decide Andrés.
  - Si se difieren las tres diferibles: exención en `plan.md` §9 con la verificación manual de Andrés y deuda en `MEMORY.md`.
  - Hecho cuando: e2e «CORRECTO», lint y build limpios, y verificación manual de la entrega 2 (§10).

- [ ] **T8. Documentación, memoria y grafo (30 min).** Criterios de finalización  ⚠️ edición del ERS, CU, HU y Modelo Relacional
  - Pasos: §11 sobre copias de los `.docx`; spec en «implementada»; `MEMORY.md`; `graphify update .` y los dos mapas.
  - e2e: exento (solo documentación).
  - Hecho cuando: Andrés revisa los documentos y exporta los PDF.

## Si falta tiempo
- La entrega 1 (T1-T3) se cierra sola: T8 puede documentar solo RF-11, CU-13 y HU-NUEVA-3 y dejar la entrega 2 para otra sesión.
- Diferibles: las tres e2e de T7 y, dentro de T8, la edición de los `.docx` (el texto queda en la spec).
