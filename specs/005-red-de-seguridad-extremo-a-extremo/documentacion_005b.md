# Documentación de cierre de la spec 005b

Texto para que Andrés actualice los documentos. Los agentes no editan el ERS, `CLAUDE.md`, `.claude/` ni la sección «Próximos pasos» de `MEMORY.md` (decisiones 23, 24 y 27). Fecha: 26/10/2026.

## 1. Qué se cubrió y las cifras finales

- T1: el control de la instancia e2e tiene la etapa `vectorizacion` y reintenta los residuos.
- T2: soporte del frontend (`soporte/datos.js`, `soporte/pantallas.js`, fixtures `otraPestana` y `otroUsuario`) y medición base.
- T3: `flujos/carga.spec.js`. Carga mixta, todos rechazados, ningún aviso antes de la respuesta, aviso accesible a 616 px (RF-05.40, RNF-04.40) y la cita en el chat general (RF-11.40, solo la cita).
- T3b: corrección de RF-07. Si falla la vectorización, el documento queda en Error (`document_processor.py`), con su prueba de regresión.
- T4: `flujos/notebooks.spec.js`. Crear y cargar en un notebook (RF-17.40, RF-05.40 en notebook).
- T5: previsualizar y quitar un documento (RF-18.40, RF-19.40, RF-19.41, RF-19.42, RNF-07.40).
- T6: corrida completa y verificación manual.

Cifras finales:
- `npm run e2e`: 141 recolectadas, 133 pasan, 8 fallos esperados, 0 XPASS, residuos 0, contraseñas 0. Suite 520 s (límite 600 s) y preparación 18,7 s.
- Los 8 fallos esperados son RF-01.40, RF-02.40, RF-01.43 y RF-19.40, cada uno en escritorio y en 616 px.
- pytest: 2028 pasan y 45 xfail.
- Verificación manual con Ollama real: el chat general y el del notebook citan `PRUEBA_contrato_servicios.txt`; fragmento en Qdrant con su clave; la bitácora registró las acciones; consola limpia; el Administrador no ve Ingesta ni NotebookServIA (redirección a `/?error=unauthorized` y 403 en la API).

## 2. Historia de usuario de la cita (decisión 26)

La cita del archivo en la respuesta (RF-11.40, solo la cita) corresponde a **HU-12** («Confiar en que las respuestas citen su fuente real»; trazabilidad RF-12, CU-09), no a HU-11 (que trata del alcance de la consulta y del streaming). La spec 005, que hoy dice «HU-11, HU-12» en la sección de lo que sale con E y G, ya los incluye a ambos; en la prueba y en `tasks-005b.md` la cita se refiere a HU-12. Nota para el ERS: la tabla de trazabilidad de V1.7 se extrae desalineada (RF-11 sin historia y RF-12 con HU-11); conviene revisarla al exportar V1.8: debería ser RF-11 → HU-11 y RF-12 → HU-12.

## 3. Pendientes para la spec de la ingesta y los ajustes gráficos

Hallazgos de la verificación manual (opción A de Andrés: se anotan, no se corrigen ahora):
- (a) Con dos temas en un mismo Guardar, todos los pendientes quedan en el último tema (ya figuraba como «cambiar el tema reescribe el de todos los pendientes»).
- (b) Un PDF dañado (falla en la extracción) no deja fila ni «Error» visible y deja un archivo huérfano en `uploads/`. La T3b solo cubrió el fallo en la vectorización. Coincide con el «Estado actual» de RF-07 sobre la extracción.
- (c) El aviso de rechazo con un nombre largo se desborda: `scrollWidth` 1216 contra `clientWidth` 451 a 616 px (RNF-04). Ajuste gráfico.
- (d) La suite e2e tarda 520 s con un límite de 600 s (RA-02.47): vigilarla. La prueba de RNF-07.40 en 616 px llegó a 33,6 s en una corrida suelta.

Observaciones del Administrador (menores, ajustes gráficos):
- No hay aviso visible de la falta de permiso al redirigir a `/?error=unauthorized`.
- Quedan textos con «expediente» en el panel del Administrador.
- El pie de página dice «Poder Judicial».

Otros, ya conocidos: la «x» de un documento del notebook quita sin confirmar (RF-19.40); el error de watchfiles «Cannot allocate memory» durante el e2e (el backend siguió respondiendo).
- (e) Pegar o arrastrar una imagen sobre el chat del notebook (RF-05.23 de la 004, CU-07 FA-01) sigue sin prueba de extremo a extremo y el ERS V1.8 no la menciona: pendiente de la spec de las mejoras del notebook; se añadirá al «Estado actual» de RF-05 en la próxima versión del ERS.

## 4. Texto propuesto para el ERS V1.8 (decisión 23)

Estado: el ERS más alto exportado es V1.7 (`Documentacion/Documentacion_ServIA_2026/PDF/`). La V1.8 **no consta como exportada**, pero la 004b la tiene abierta con su lote (T10, pendiente). Andrés debe confirmar antes de aplicar que sigue sin exportar; si ya se exportó, se para y se decide (decisión 28). Los cambios van en un solo lote con los de la 004b.

- **RF-05** (Estado actual): quitar «pendiente la verificación de extremo a extremo (spec 005)». Queda: «El aviso con el motivo de cada archivo rechazado en Ingesta de Datos y en NotebookServIA: implementado y verificado de extremo a extremo (spec 005). El aviso con un nombre de archivo muy largo se desborda a 616 px (pendiente de los ajustes gráficos).»
- **RF-07** (Estado actual): el texto actual dice que si falla la extracción el documento no queda en Error. Mantenerlo (hallazgo b: además deja el archivo huérfano en `uploads/` y ninguna fila visible). Agregar: «Si falla la vectorización, el documento queda en estado Error (corregido y verificado, spec 005b).»
- **RF-11 / RF-12**: la cita del archivo en el chat general queda verificada de extremo a extremo (spec 005b). El resto de RF-11 y RF-12 sigue sin verificación de extremo a extremo y queda para la spec del módulo.
- **RF-19** (Estado actual, ya existe): sin cambio de fondo. Dejar explícito que «la eliminación se ejecuta sin solicitar confirmación» está verificado por una prueba que falla a propósito (`RF-19.40 · notebooks`).
- **RF-22** (Estado actual del detalle de los registros de carga): reemplazar «pendiente la verificación de extremo a extremo (spec 005)» por una remisión a la spec de la bitácora.
- **RNF-04** (Estado actual): dejar solo el detalle de la bitácora (remitido a la spec de la bitácora). El aviso de RF-05 queda verificado en escritorio y en 616 px, salvo el desborde por nombre largo.
- **RA-02**: reemplazar «El extremo a extremo llega con la spec 005» por «Existe un extremo a extremo (Playwright, `npm run e2e`) que cubre el acceso por rol, el menú, las cuentas, la recuperación de contraseña, el Historial, la carga en Ingesta, la cita en el chat general y NotebookServIA (crear, cargar, previsualizar y quitar); el resto del chat y la bitácora en el navegador llegan con la spec de su módulo.»
- Cada `fallaEsperada` nueva va a su «Estado actual»: la única nueva de la 005b es RF-19.40 (ya descrita en RF-19).
- Tabla de trazabilidad: revisar RF-11 → HU-11 y RF-12 → HU-12 (ver el punto 2).

## 5. Regla nueva «cada spec prueba el módulo que toca» (decisión 24; la aplica Andrés)

Para `.claude/rules/testing.md`, «Orden de trabajo», pasos 3 y 4:

> 3. **Cada spec prueba el módulo que toca** (sustituye a las specs retroactivas por módulo; decisión de Andrés, 22/10/2026): toda spec nueva o corrección escribe primero las pruebas de lo que cambia y de los requisitos existentes del módulo que modifica, contra el ERS; lo que el código no cumple, como fallo esperado con su referencia. Lo que ninguna spec toque queda como trabajo futuro documentado (su «Estado actual» en el ERS y una línea en `MEMORY.md`).
> 4. Con el paso 2 cerrado (spec 005b), empiezan las funciones nuevas y los «Estado actual» del ERS, cada una con sus pruebas desde el inicio según el paso 3.

Ajuste del paso 2: «Hechos (specs 005a y 005b): la infraestructura de extremo a extremo, el acceso, la carga con la cita en el chat general y NotebookServIA; el resto del chat y la bitácora en el navegador, a la spec de su módulo.»

Para la sección «Verificación» de `CLAUDE.md`, reemplazar «el código heredado todavía tiene poca cobertura (RA-02) y se cubre con specs retroactivas, en el orden de `.claude/rules/testing.md`» por: «el código heredado todavía tiene poca cobertura (RA-02): cada spec prueba el módulo que toca, según `.claude/rules/testing.md`».

## 6. Documentos que actualiza Andrés

- `.claude/rules/testing.md`: pasos 2, 3 y 4 (texto de la sección 5). HECHO (aplicada por Andrés).
- `CLAUDE.md`: «Verificación» (texto de la sección 5) y el estado de la 005b (el extremo a extremo cubre también ingesta, la cita en el chat general y NotebookServIA; las cifras de la suite). HECHO (aplicada por Andrés).
- `.claude/skills/sdd/SKILL.md` («Specs retroactivas»), `.claude/agents/planner.md`, `implementer.md`, `coordinator.md`, `.claude/commands/sdd-implement.md` y `sdd-validate.md`: cambiar solo «el código heredado se cubre con specs retroactivas». HECHO (aplicada por Andrés).
- `MEMORY.md`: «Próximos pasos» 3 y 4 (decisión 27); ya los dejó actualizados el implementer con el plan del mes, revisar el texto.
- ERS V1.8 (sección 4), junto con el lote de la 004b (T10: `documentacion_t10.md`). HECHO (26/10): exportado junto con CU V1.5 y Modelo Relacional V1.1, commit `d8ec8da`.
- Spec 004: retirar la exención temporal de RF-05.23 y del aviso de RNF-04.1 (spec.md:171, 199, 234, 237, 282) y remitir RF-22.1 a la spec de la bitácora. HECHO (26/10, planner): estado, historial, bloque F, RF-05.23, RF-22.1, RNF-04.1 y criterios de finalización.
- Spec 005: pasar a «implementada» (005b reducida) tras el veredicto del @reviewer. HECHO (26/10, planner): estado e historial con el veredicto APROBADO y las cifras finales.
- `frontend/e2e/soporte/consola_declarada.js` (líneas 2, 11 y 16): «spec retroactiva de autenticación y usuarios (paso 3…)» pasa a «spec del módulo que lo corrija». Es código de pruebas: lo hace el implementer en una pasada aparte, con las suites. HECHO (26/10; también `red.spec.js:105`).
- Grafo y mapas: `generar_mapa_pruebas.py` y `graphify update .` (la 005b cambió `document_processor.py`). HECHO (26/10): grafo y mapas actualizados con el `python.exe` del entorno de uv, porque Windows bloquea `graphify.exe`.
- Los datos de desarrollo de la verificación manual ya se limpiaron (opción A): quedan los temas 60004 y 60005 vacíos.

## 7. Hallazgo: no se puede borrar un tema con bitácora

Al limpiar los datos de la verificación manual se comprobó que `T_Bitacora.CN_Id_expediente` es una clave foránea hacia `T_Expediente`: un tema con acciones registradas no se puede borrar sin tocar la bitácora. Esto confirma RN-01 (ningún registro se elimina físicamente). Los temas 60004 y 60005 quedaron vacíos a propósito; las pruebas futuras que creen temas y los registren en la bitácora dejarán el mismo residuo.
