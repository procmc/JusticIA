# Plan — Spec 008: Mejoras de NotebookServIA
Estado: aprobado (04/11/2026). Decisiones P-1 a P-3 en §13.

> Parte de la spec aprobada el 04/11/2026; no la repite, remite a sus requisitos. Código ubicado con `Grep` y `Read` por rangos en `fase4` (04/11/2026); no se consultó el grafo: los símbolos están en un solo archivo de página.

## 1. Enfoque
- Solo frontend y pruebas e2e: sin backend, esquema, migración, dependencia, prompt, modelo ni `docker-compose.yml` (RN-01.70).
- Corrección del módulo (testing.md, paso 3): primero la aserción que falla, después el código.
- Sin archivos de prueba nuevos (C3): las aserciones se funden en `notebooks.spec.js` y `chat.spec.js`; un ayudante nuevo en `pantallas.js`.
- Único archivo nuevo: el PNG temporal de CF-1 (⚠️), fuera de git y borrado al terminar.

## 2. Archivos

| Archivo | Cambio | Requisitos |
|---|---|---|
| `frontend/pages/notebooks/index.js` | Confirmación al quitar (`:57`, `:143-154`, chip `:455-468`) y los seis textos (`:225`, `:345`, `:368`, `:401`, `:500`, `:511`). | RF-19.40, RF-19.70, RF-21.70, RT-07.70 |
| `frontend/components/ui/ConfirmModal.jsx` | **No se toca** (componente común; ver D-1). | — |
| `frontend/e2e/flujos/notebooks.spec.js` | RF-19.40 ampliada, sin `fallaEsperada` (`:254-277`); textos nuevos (`:32`, `:68`, `:79`); voseo en tres estados; arrastre. | RF-19.40, RF-19.70, RF-21.70, RT-07.70, RNF-04.70 |
| `frontend/e2e/flujos/chat.spec.js` | Placeholder nuevo (`:42`). | RT-07.70 |
| `frontend/e2e/soporte/pantallas.js` | Ayudante `exigirSinVoseo(page)`. `quitarDocumentoEnPantalla` (`:81-91`) no cambia: ya acepta el cuadro. | RT-07.70 |
| ⚠️ PNG temporal (CF-1) | Archivo nuevo en carpeta ignorada (§7); se borra al terminar. | CF-1 |

Backend verificado, sin cambios: `DELETE /notebooks/{id}/documentos/{id}` (`routes/notebooks.py:186-215`) llama a `notebook_service.quitar_documento` (`notebook_service.py:249`), que borra Qdrant, archivo y fila dentro de la petición, y registra `QUITAR_DOCUMENTO_NOTEBOOK` (17) solo si tiene éxito o falla, nunca al mostrar o cancelar.

## 3. Confirmación al quitar (RF-19.40, RF-19.70, RF-21.70)

Estado en la página (sustituye `eliminandoId` único, `:57`):
- `documentoPorQuitar` (estado: `{id, nombre}` o `null`) abre la confirmación.
- `confirmacionRef` (ref) guarda el mismo documento; se vacía en el primer «Quitar».
- `eliminandoIds` (estado, `Set`) y `quitandoRef` (ref, `Set`): cada documento con su propio deshabilitado.

```
chip.onClose(doc)        → documentoPorQuitar = confirmacionRef = {doc.id, doc.nombre_archivo}
modal.onConfirm()        → doc = confirmacionRef.current; confirmacionRef.current = null
                           si doc es null → nada            (2.º clic del doble clic)
                           handleEliminarDocumento(doc.id)
modal.onClose()          → documentoPorQuitar = null        (ConfirmModal lo llama tras onConfirm y al cancelar)
handleEliminarDocumento(id):
  si quitandoRef tiene id → nada                            (defensa: nunca dos DELETE del mismo)
  agregar id a quitandoRef y a eliminandoIds
  resultado = eliminarDocumento(...)                        (sin cambios: lista o Toast de RF-19.42)
  quitar id de quitandoRef y de eliminandoIds               (permite el reintento de RF-19.42)
chip.isDisabled          → eliminandoIds.has(doc.id)
```

- `<ConfirmModal isOpen={!!documentoPorQuitar} title="Quitar documento" description={`¿Quitar "${nombre}" del notebook? Esta acción no se puede deshacer.`} confirmText="Quitar" cancelText="Cancelar" confirmColor="danger" …/>`.
- Por qué el doble clic llega dos veces: `ConfirmModal.handleConfirm` llama a `onConfirm` y `onClose`; el botón sigue en pantalla durante la animación de salida (0,2 s). El ref lo absorbe sin tocar el componente.
- Documento quitado en otra pestaña con el cuadro abierto: el DELETE da 404 y aplica el flujo vigente de RNF-07.40 (sin cambio).
- Pendiente y Error: la «x» abre el mismo cuadro (sin distinción por estado).
- Vista previa (RF-18): `handleVerArchivo` (`:164`) ya ignora el clic de la «x»; sin cambio.
- Bitácora (RF-21.70): cancelar no hace petición, así que no registra; el doble clic produce un solo DELETE y un solo registro.

## 4. Textos sin voseo (RT-07.70)
- Los seis reemplazos de la tabla de la spec, literal, en las líneas de §2. Sin otros textos (el estado vacío del chat y el error de conexión quedan fuera).
- `exigirSinVoseo(page)`: `expect(page.locator('body')).not.toContainText(/tenés|creá|elegí|revisá|soltá|preguntale|podés|intentá/i)`. Sin `\b`: no funciona con vocales con tilde.
- Arrastre: React escucha `dragover` nativo en la raíz, así que `dispatchEvent('dragover', { dataTransfer })` sobre el contenedor del chat (con `new DataTransfer()` creado en la página) muestra el aviso. Se comprueba el texto y luego `dragleave` lo retira. **Se prueba en e2e; no hace falta exención.**
- Error al subir: **exención** (P-1). El texto es el respaldo de `error.message || '…'` (`:225`), y `ingestaService.subirArchivos` (`services/ingestaService.js:98-142`) siempre lanza con mensaje («Error al procesar la ingesta. Intente nuevamente más tarde.» o «El tema indicado no es válido»). Ni una e2e ni la verificación manual pueden mostrarlo; la evidencia es `Grep` de las formas buscadas en `index.js` = 0.

## 5. Pruebas por requisito

| Requisito | Prueba (e2e, 1366 y 616 px salvo indicación) | Rojo esperado |
|---|---|---|
| RF-19.40 | `notebooks.spec.js` «RF-19.40 · confirmación…» (`:254`): la existente, con las aserciones de abajo; se retira `fallaEsperada` tras verla en XPASS. | Fallo esperado: no aparece el cuadro. |
| RF-19.70 | Misma prueba: título «Quitar documento»; cuerpo exacto (`toHaveText` con comillas); botones «Quitar» y «Cancelar»; sin desborde a 616 px (`scrollWidth ≤ clientWidth`, como `historial.spec.js:258`). | Igual. |
| RF-19.70 doble clic | `dblclick` en «Quitar»: lista de DELETE con longitud 1; ficha fuera; `listarDocumentos` vacío; la pregunta por API ya no lo cita (`citaEnElChat`, como RF-19.41). | Igual. |
| RF-19.70 por documento | Segundo documento (`subirYProcesar` en el mismo notebook); `control.notebooks({ retener_quitar: true })`; confirmar ambos; `esperando_quitar` = 2 y los dos deshabilitados; `notebooksLiberar` y ambos fuera. | Igual (hoy `eliminandoId` único habilita el primero). |
| RF-21.70 | Administrador por API (`crearUsuario('administrador')`), `GET /bitacora/registros?usuario=<cédula>`: 0 «Quitar Documento de Notebook» tras cancelar; exactamente 1 por el documento del doble clic. | Igual. |
| RT-07.70 | `:68`, `:79` (lista vacía), `:32` y `chat.spec.js:42` (placeholder) con el texto nuevo; «Elija o cree…» visible en «RF-17.40 · nombre vacío»; `exigirSinVoseo` en lista vacía (`:65`), notebook abierto (`exigirNotebookAbierto`, `:29`) y revisión (RF-05.40 carga mixta, con «revise antes de subir»); arrastre en «RF-17.40 · crear con botón y con Enter». | Rojo: los textos nuevos no existen. |
| RNF-04.70 | Todas las anteriores corren en `escritorio` y `pequena` (el chat del notebook en `chat.spec.js` sigue solo escritorio, RNF-04.60). | — |
| D (existentes) | RF-19.41, RF-19.42, RNF-07.40, RF-18.x, RF-17.40, RF-05.40 y `chat.spec.js` sin cambios de lógica. | Deben seguir verdes. |
| RN-01.70 | Sin prueba nueva: `git diff --stat` solo en los 4 archivos de §2; ningún archivo de `backend/`. | — |

- pytest: ningún cambio en el backend. Se corre en T0 (base) y en el cierre conjunto (normal e inverso): mismo conteo que T0.
- Presupuesto e2e: base de T0 + ~5 s (dos anchos: doble clic, segundo documento y bitácora ~2 s; voseo y arrastre ~0,5 s). Si T0 da ≥ 560 s, avisar antes de T1.

## 6. Reglas operativas (cada corrida de suite)
- Memoria libre antes: pytest ≥ 1,5 GB, e2e ≥ 2,3 GB (cgroup de WSL). Nunca dos suites a la vez; `npm run dev` cerrado durante el e2e.
- Servicios con `docker compose start <servicio>`, nunca `up -d`. `tika`, `celery-worker` y `servidor-htr` detenidos salvo en CF-1.
- Evidencia: pytest (pasan, `xfail`, fallos, XPASS) y e2e (recolectadas, pasan, fallan, esperados, omitidas, XPASS, residuos, contraseñas, suite vs. 569 s).
- Durante el desarrollo de T1 y T2, solo `npm run e2e -- e2e/flujos/notebooks.spec.js` (y `chat.spec.js` en T2): ~1-2 min.
- Contingencia (RNF-04.70 de la spec): solo si dos corridas completas seguidas pasan de 569 s, y en su orden.

## 7. CF-1 — paso 8 de la 007 (manual)
- **Quitar no depende del worker** (§2): se quita con `celery-worker` ya detenido; el orden de la spec se mantiene.
- Carpeta del PNG: `Registro_Indicaciones_2026/temporal_008/` (ignorada por `.gitignore:20`; dentro del proyecto, como exige `upload_file`; ni la app ni el e2e la leen). Antes de crearla: `git check-ignore -v` sobre la ruta. Ver P-2.
- Generar el PNG en `servidor-htr` (ya arrancado en ese paso; docTR trae Pillow): texto tipeado negro sobre blanco, fuente ≥ 40 px, con «PRUEBA-R5-K7Q2», y `docker compose cp` a la carpeta (`MSYS_NO_PATHCONV=1`). Si no hay Pillow, Andrés lo crea con Paint.
- Comprobación en Qdrant: `scroll` con filtro `metadata.numero_expediente = NB-<id>` y buscar la cadena en `page_content`.
- La consulta usa Ollama real: comprobar la GPU libre (HTR detenido) antes de preguntar.

## 8. Verificación manual (Andrés inicia sesión en el MCP; 1229 ≈ 1366 px y 554 ≈ 616 px)
- Usuario Gubernamental, notebook `PRUEBA 008` con un `.txt` `PRUEBA`: «x» → cuadro con título, texto y botones; Cancelar no cambia nada; Quitar lo quita; una fila en la bitácora.
- Otra pestaña: abrir el cuadro, quitar en la otra, confirmar en la primera: aviso, sesión y pantalla siguen.
- Los textos: lista vacía (usuario sin notebooks o recuento visual), sin notebook abierto, revisión, placeholder, arrastre real de una imagen (sin soltar). Error al subir: exento (§4).
- Administrador: `/notebooks` lo redirige (RN-03). Consola sin errores.
- Limpieza: quitar el `.txt` desde la interfaz; el notebook `PRUEBA 008` queda vacío como residuo (sin borrado de notebooks, decisión 2).

## 9. Documentación (T5, propuesta a Andrés; el planner no la edita)
- ERS: RF-19 sin «Estado actual» (Implementado); RF-05 «Estado actual» completado (e2e de pegar o arrastrar pendiente; resultado de CF-1); RF-19.70 y RT-07.70 si Andrés lo aprueba; RF-15 sigue abierto (008b).
- CU-11 p. 2 y CU-09 FA-05: textos sin voseo.
- `graphify-out/` (actualizar grafo y mapas; cambió `notebooks/index.js`), `MEMORY.md` y el estado de la spec.

## 10. Decisiones
- D-1: confirmación en la página con `ConfirmModal` sin cambios. Descartada: añadir un candado a `ConfirmModal` (lo usan Ingesta y Gestión de usuarios; más pruebas afectadas).
- D-2: doble clic absorbido con un ref que se vacía al confirmar, más el candado por documento. Descartada: deshabilitar «Quitar» con `isLoading` (el cuadro se quedaría abierto durante el quitar, contra RF-19.70 «la confirmación ya está cerrada»).
- D-3: `Set` de documentos en curso. Descartada: conservar `eliminandoId` único (habilita el primero al quitar el segundo).
- D-4: arrastre probado con `dispatchEvent`. Descartada: exención (el evento sintético sí lo reproduce).
- D-5: pytest solo en T0 y en el cierre conjunto (T3), porque no cambia el backend. Descartada: pytest en cada tarea (~20 min más cada vez sin cubrir nada nuevo).
- D-6: una sola suite completa y una verificación manual para A y C (T3). Descartada: una por tarea (dos corridas e2e de ~10 min y dos inicios de sesión de Andrés).

## 11. Validación (fase 5)
- El reviewer no mide la memoria: un implementer corre pytest (normal e inverso) y `npm run e2e` con las reglas de §6 y le entrega la evidencia; el reviewer revisa el diff, la evidencia y la interfaz.

## 12. Fuera de tareas
- Recordatorio: un implementer completa con `Edit` la entrada del 04/11/2026 de `Registro_Indicaciones_2026/Bitacora/15_Bitacora_Practica.md` al terminar el día.

## 13. Decisiones de Andrés (04/11/2026)
- P-1 = A: el error al subir se evidencia con `Grep` de las formas con voseo en `index.js` = 0. Descartada: dejar el texto sin cambiar (contradice RT-07.70).
- P-2 = A: PNG en `Registro_Indicaciones_2026/temporal_008/`, ignorada por `.gitignore:20`; `git check-ignore -v` antes de crearla. Descartada: `frontend/out/` (carpeta de exportación de Next).
- P-3 = A: pytest solo en T0 y T3; en T1 y T2 solo los archivos e2e tocados; una suite completa y una verificación manual en T3 (D-5, D-6). Descartada: suite completa por tarea (+~40 min).
