# Plan — Spec 005b: Carga y NotebookServIA en el navegador
Estado: aprobada por Andrés (22/10/2026)

> Solo la 005b reducida (secciones D, con la cita en el chat general, y F de la spec; decisiones 20 y 21). Reutiliza la instancia, el control, los simulados y las fixtures de la 005a (`plan-005a.md` §1-§8); aquí solo lo nuevo. Las decisiones 1-20 de la spec no se reabren. Archivos y líneas a 22/10/2026, rama `fase4`; las pruebas, por `Grep` (el grafo no las incluye).

Historial:
- 22/10/2026 — creado (fase 3, planner).
- 22/10/2026 — reducido a D y F (decisión 20): fuera chat, bitácora e imagen sobre el chat; 6 tareas, ~28 h; propuesta de regla en §13.
- 22/10/2026 — dudas de §12 resueltas por Andrés (decisiones 21-24 de la spec): la cita entra en T3, limpieza manual por terminal, ERS V1.8 en un lote, regla de §13 aprobada; ~28,5 h.
- 22/10/2026 — aprobado por Andrés (opción A), con las resoluciones 25-28 de la spec: RF-11.40 partido con el mismo número (sin RF-11.44); la HU de la cita (HU-11 o HU-12) se ajusta en T6; en `MEMORY.md` Andrés cambia solo «Próximos pasos» 3 y 4 y los agentes siguen escribiendo el cierre de cada tarea; V1.8 ya exportada al cerrar → parar y preguntar (§11, confirmado).
- 26/10/2026 — cambio (decisiones 29 y 30 de la spec): RF-05.40 aclarado; nueva T3b corrige el hallazgo de RF-07 (§3); ~29,5 h.

## 1. Enfoque
- **Solo pruebas** (spec, «Partición»): ningún cambio de producción. Lo que el sistema no cumple queda con `fallaEsperada` tras verlo en rojo.
- **Datos de base por la API, el flujo bajo prueba por la interfaz**: el notebook con un documento Procesado de RF-18.40, por ejemplo, se crea por la API; la acción del requisito se hace en pantalla.
- **Archivos de prueba generados en memoria** (texto, PDF mínimo, PNG mínimo), con nombre `PRUEBA_<aleatorio>`; ningún archivo de datos en el repositorio.
- **Motores**: los de la 005a. Modelo de lenguaje, HTR, audio y correo simulados; embeddings y Tika reales y locales (sin GPU).
- Todo va a `servia_pruebas_e2e` y a `/tmp/servia_e2e` (plan-005a §6); la limpieza total cubre temas heredados, `NB-<id>`, archivos y puntos.

## 2. Archivos
Nuevos (⚠️ «Pregunta antes», crear archivos):

| Archivo | Responsabilidad | Requisitos |
|---|---|---|
| ⚠️ `frontend/e2e/soporte/datos.js` | Ayudas de Node movidas desde `capacidades.spec.js:169-247` (documento, tema, `cargar`, `esperarTarea`, `preguntar`, `PNG_MINIMO`), más `pdfMinimo()` y `notebookConDocumento()`. | D, F |
| ⚠️ `frontend/e2e/soporte/pantallas.js` | Acciones de pantalla: abrir Ingesta y cargar, abrir o crear un notebook, preguntar en el chat del notebook. Usa `pulsar`/`escribir` (616 px). | D, F |
| ⚠️ `frontend/e2e/flujos/carga.spec.js` | RF-05.40, RNF-04.40, RF-11.40 (solo la cita). | D |
| ⚠️ `frontend/e2e/flujos/notebooks.spec.js` | RF-05.40 (notebook), RF-17.40, RF-18.40, RF-19.40 a RF-19.42, RNF-07.40. | F |
| ⚠️ `specs/005-…/documentacion_005b.md` | Texto para el ERS; lo aplica Andrés (T6). | cierre |

Modificados:

| Archivo | Cambio | Requisitos |
|---|---|---|
| `backend/tests/instancia_e2e/simulados_e2e.py` (`EstadoIngesta`, :757; `instalar_controles`, :954) | Etapa `vectorizacion` para retener o fallar tras registrar el documento: envuelve `document_processor.store_in_vectorstore` (`document_processor.py:96`, llamada en :466). Por omisión, `extraccion` (la 005a no cambia). | RA-02.49 (RF-18.40) |
| `backend/tests/instancia_e2e/control.py` (`CuerpoIngesta`, :293; `residuos`, :157-160) | Campo `etapa`. `/residuos` con el mismo reintento de 5 s que `limpiar_todo` y `detail` en el 500 (pendiente de la 005a). | RA-02.49, RA-02.42 |
| `backend/tests/unitarias/test_instancia_e2e.py` | Pruebas de T1 (§6). | RA-02.42, RA-02.49 |
| `frontend/e2e/soporte/fixtures.js` (:110-156) | Fixtures `otraPestana` (mismo contexto, RNF-07.40) y `otroUsuario` (contexto nuevo, RF-17.40), con red, consola y `reescribirRedirecciones` (:60). | RA-02.41, RA-02.45 |
| `frontend/e2e/soporte/control.js` | `ingesta({ etapa })`. | RA-02.49 |
| `frontend/e2e/infraestructura/capacidades.spec.js` | Importa de `datos.js`; nueva prueba de la etapa. Ninguna prueba se borra. | RA-02.49 |
| `frontend/e2e/flujos/red.spec.js` | Prueba de las fixtures nuevas. | RA-02.41 |
| `frontend/e2e/soporte/consola_declarada.js` | Si aparece un error heredado (motivo y spec del módulo que lo corrija); en T6, el texto de la regla de §13. | RA-02.45 |

Sin cambios: código de producción, esquema, migraciones, `requirements.txt`, `package.json`, `docker-compose.yml`, prompts, modelos, `ROUTE_PERMISSIONS`, `.env.local`, el hook, `historial.spec.js`.

## 3. Control: etapa de vectorización (T1)
Hoy `retener`/`fallar` actúan en la extracción (`envolver_extraccion`, `simulados_e2e.py:852`), antes de que exista el documento (ERS RF-07, «Estado actual»): un documento Pendiente o con Error nunca aparece en la lista del notebook (CU-12 FA-01).
```
CuerpoIngesta.etapa ∈ {"extraccion" (omisión), "vectorizacion"}  # otro valor -> 400
envolver_vectorizacion(original):
  async almacenar(texto, metadatos, ...):
    nombre = metadatos["nombre_archivo"]
    si etapa == vectorizacion y nombre en retener: await compuerta.esperar_async()   # documento ya en BD como Pendiente
    si etapa == vectorizacion y nombre en fallar: raise ValueError("… (PRUEBA)")       # el sistema lo deja en Error (document_processor.py:540)
    return await original(...)
instalar_controles: parches.setattr(document_processor, "store_in_vectorstore", envolver_vectorizacion(...))
```
- La limpieza total ya suelta la compuerta y espera la ingesta (`restablecer`, :803); `etapa` vuelve a `extraccion`.
- Si el sistema no deja el documento en Error, hallazgo de RF-07 y la parte «con Error» de RF-18.40 queda con `fallaEsperada` (tras verla en rojo).
- Hallazgo confirmado en la T2 (`update_progress(..., status="error")` sin ese parámetro → TypeError, el documento queda Pendiente). Se corrige en la **T3b** (decisión 30): regresión en pytest primero y corrección mínima; la T5 prueba «Error» sin `fallaEsperada`.

## 4. Flujos por requisito (lo no obvio)
**D. Carga (RF-05.40, RNF-04.40).**
- Carga mixta: válido `.txt`, vacío (0 bytes) y nombre de más de 255 bytes (el único no válido que el navegador envía sin alterar).
- Ingesta: tema heredado nuevo (`nuevoTema`), `setInputFiles` con buffers, «Guardar», confirmar en el cuadro.
- Comprobar: motivo de cada rechazado igual al de la API; confirmación solo con aceptados; ningún texto con el nombre largo; ningún «procesando» en los rechazados; el aceptado llega a Procesado.
- «Ningún aviso antes de la respuesta»: `page.route` retiene `POST /ingesta/archivos` hasta comprobar que no hay aviso ni toast. Todos rechazados: ningún aviso de éxito.
- Notebook: la misma carga con «Confirmar y subir».
- RNF-04.40 (616 px): `exigirAccesible` sobre el aviso y cada motivo; texto completo visible al desplazarse (`scrollWidth` dentro del contenedor).
- RF-11.40, solo la cita (decisión 21): tras Procesado, en el Asistente (general) la pregunta por la frase del archivo muestra su nombre (motor simulado que cita lo recibido; `MarkdownRenderer.jsx:98`). Sin etapas, descarga ni acotado.

**F. NotebookServIA.**
- RF-17.40: crear con botón y con Enter; primero en la lista, abierto con «Subir documentos», lista y chat. Nombre vacío: la lista no cambia. `otroUsuario` no lo ve.
- RF-18.40: imagen (PNG + HTR simulado) y PDF mínimo (Tika). `notebooks({ retener_vista_previa: true })` → «Abriendo…» (`index.js:462`); liberar → ventana con el nombre e `img` o `iframe` (`index.js:528-540`). Sin evento `download` ni página nueva.
- RF-18.40 FA-01 y FE-01: Pendiente por `etapa: vectorizacion` + `retener`; Error por `fallar`; al pulsarlos no aparece «Abriendo…» ni ventana. Un `.txt` Procesado muestra «Vista previa no disponible…».
- RF-19.40: la «x» espera un cuadro con el nombre y la advertencia; hoy no lo hay → `fallaEsperada(test, 'RF-19.40 · notebooks')` tras verla en rojo.
- RF-19.41: `retener_quitar` → documento deshabilitado (`index.js:457`); liberar → deja de listarse; la pregunta por su frase en el chat del notebook ya no lo cita.
- RF-19.42: `fallar_quitar` → «No se pudo quitar el documento. Intente de nuevo.» y sigue listado; sin el fallo, un nuevo intento lo quita.
- Si aparece una confirmación al pulsar la «x», la ayuda la acepta (spec).
- RNF-07.40: `otraPestana` quita el documento; en la primera, previsualizar y quitar reciben el 404 uniforme (`consola.provocado(/404/)`); la sesión sigue y la pantalla es operable (crear notebook). El aviso al previsualizar no se evalúa (decisión 12).

## 5. Decisiones
1. Datos de base por la API; la acción del requisito, en pantalla. Descartado: todo por la interfaz (duplica pasos y arriesga los 10 min).
2. Retención y fallo en la vectorización por parche de instancia. Descartado: insertar filas Pendiente o Error con el control (no las produce el sistema).
3. Nombre no válido por longitud. Descartado: separadores o caracteres de control (el navegador los altera).
4. Ayudas compartidas en `soporte/datos.js` y `soporte/pantallas.js`. Descartado: copiarlas en cada archivo.
5. Reintento en `/residuos` (pendiente de la 005a), en T1. La causa del 500 de `/limpiar` queda fuera: si reaparece, `/tmp/servia_e2e/instancia.log` y una corrección con prueba de regresión.
6. Tipo sin vista previa con `.txt`. Descartado: audio o Word (más preparación, mismo camino).
7. Carga en notebook dentro de `notebooks.spec.js`. Descartado: en `carga.spec.js` (comparte la preparación del notebook con RF-17.40).
- Retiradas con el cambio: eventos sintéticos de pegar y soltar, reloj del navegador, `chat.spec.js` y los cambios de `historial.spec.js`.

## 6. Pruebas por requisito
Títulos que empiezan por su requisito; corren en `escritorio` y `pequena`, salvo indicación.

| Requisito | Pruebas |
|---|---|
| RA-02.49 (etapa) | pytest `test_ingesta_retiene_tras_registrar_el_documento`, `test_ingesta_falla_tras_registrar_queda_en_error`, `test_etapa_invalida_400`; `capacidades.spec.js`: `ingesta retiene y falla en la vectorización` |
| RA-02.42 | pytest `test_residuos_reintenta_un_error_transitorio`, `test_residuos_500_con_detail` |
| RA-02.41, RA-02.45 | `red.spec.js`: `otra pestaña y otro usuario también quedan vigilados` |
| RF-05.40 | `carga.spec.js`: `Ingesta: carga mixta`, `Ingesta: todos rechazados sin aviso de éxito`, `Ingesta: ningún aviso antes de la respuesta`; `notebooks.spec.js`: `notebook: carga mixta` |
| RF-11.40 (solo la cita) | `carga.spec.js`: `Ingesta: Procesado y el chat general lo cita` |
| RNF-04.40 | `carga.spec.js`: `aviso accesible y completo` (en `pequena`) |
| RF-17.40 | `notebooks.spec.js`: `crear con botón y con Enter`, `nombre vacío`, `otro usuario no lo ve` |
| RF-18.40 | `notebooks.spec.js`: `vista previa de imagen y PDF`, `Pendiente y Error no se abren`, `tipo sin vista previa` |
| RF-19.40 | `notebooks.spec.js`: `confirmación con nombre y advertencia; cancelar no cambia nada` (`fallaEsperada`) |
| RF-19.41 | `notebooks.spec.js`: `deshabilitado, luego fuera de la lista y del chat` |
| RF-19.42 | `notebooks.spec.js`: `fallo con aviso y reintento` |
| RNF-07.40 | `notebooks.spec.js`: `documento quitado en otra pestaña: sesión y pantalla siguen` |

## 7. Exenciones
- Calidad real de la respuesta y la cita: motor simulado; manual con Ollama.
- Aspecto visual: manual a 1366 y 616 px (principio 4).
- «Dos temas en un mismo Guardar» (decisión 13): solo manual.
- El worker de Celery real: solo manual (decisión 10).

## 8. Bitácora, datos e interfaz
- Bitácora (RF-21): ninguna acción nueva; la verificación manual confirma la fila de cada acción en SQL Server (sin prueba de la pantalla: RF-21.42 salió).
- Datos: sin migraciones; todo en el entorno aislado, borrado por la limpieza total.
- Interfaz: sin páginas ni cambios de `ROUTE_PERMISSIONS`.

## 9. Riesgos
- **Límite de 10 min (RA-02.47)**: hoy ~4,5 min con 104 pruebas; se suman ~15 pruebas × 2 pantallas con ingesta real (embeddings en CPU). Medir en T2 y T5; si la proyección pasa de 9 min, parar y preguntar (opciones de la antigua duda 1: medir con más datos por la API y, si aún pasa, `/sdd-change` de RA-02.47).
- **Memoria**: más ingesta en la instancia; vigilar `memory.events` en cada cierre E.
- **PDF en Chrome sin interfaz**: el visor puede tratar un `blob:` PDF como descarga. Si ocurre, es un hallazgo del entorno: parar y preguntar antes de marcar nada.
- **Carreras de animación**: avisos de HeroUI y el cajón; nada de `scroll` sobre listas abiertas (lección de la 005a); esperar estados, no tiempos.
- **Textos del ERS V1.8 sin exportar** (RF-19.42): si cambian, cambia la prueba.
- **Consola**: los errores provocados (404 de RNF-07.40, fallo de RF-19.42) se declaran por prueba (`consola.provocado`); los heredados, en `CONSOLA_DECLARADA` con la spec del módulo que los corregirá.

## 10. Verificación manual (T6)
Entorno de desarrollo con Ollama y el worker reales. Un agente con el MCP `chrome-devtools` (perfil propio, zoom 0,9: `emulate` 1229 = 1365 px CSS y 554 = 615). Andrés inicia sesión y escribe las contraseñas; los agentes no las reciben.
- Usuario Gubernamental, a 1365 y 615 px, consola limpia:
  - carga mixta en Ingesta y en un notebook `PRUEBA`; dos temas en un mismo «Guardar» (decisión 13);
  - el chat general cita el archivo cargado en Ingesta (Ollama real; RF-11.40, decisión 21);
  - notebook: crear, vista previa de imagen y PDF, quitar.
- Administrador: no ve Ingesta ni NotebookServIA; el Usuario Gubernamental no ve el Historial.
- Datos: fila en SQL Server, fragmentos en Qdrant con su clave y la fila de bitácora de cada acción. Conteos de desarrollo antes y después de `npm run e2e` (RA-02.41).
- Archivos `PRUEBA_*` inventados, temporales en `frontend/test-results/manual/` (ignorada por git), borrados al terminar.
- Limpieza de desarrollo (decisión 22): al terminar, por terminal (⚠️ confirmación del hook), los documentos, fragmentos, archivos y temas `PRUEBA` de la verificación; conteos de SQL Server, Qdrant y `uploads/` antes de cargar y después de borrar, iguales.

## 11. Documentación al cierre (T6; la aplica Andrés)
- `documentacion_005b.md` con el texto para el ERS:
  - RF-05: quitar «pendiente la verificación de extremo a extremo (spec 005)»;
  - RNF-04: dejar ese «Estado actual» solo para el detalle de la bitácora; RF-22: remitirlo a la spec de la bitácora;
  - RA-02: reemplazar «El extremo a extremo llega con la spec 005»;
  - cada `fallaEsperada` nueva, a su «Estado actual» (RF-19 ya lo tiene).
  - Versión (decisión 23): la misma V1.8, en un solo lote con la 004b, si sigue sin exportar; si ya se exportó, parar y preguntar a Andrés.
- Spec 004: retirar la exención temporal de RF-05.23 y del aviso de RNF-04.1 (spec.md:171, 199, 234, 237, 282), y remitir RF-22.1 a la spec de la bitácora.
- Regla de §13 (aprobada, decisión 24): el texto «Después» y el ajuste del paso 2 para `.claude/rules/testing.md`, y la lista de §13 de los demás documentos que nombran las retroactivas; los actualiza Andrés (los agentes no editan `CLAUDE.md`, `.claude/` ni `MEMORY.md` por esta regla).
- `frontend/e2e/soporte/consola_declarada.js`: «spec retroactiva que lo corregirá» → «spec del módulo que lo corrija» (lo hace el implementer; la spec 005 ya está ajustada).
- Spec 005: «implementada» (005b reducida); `generar_mapa_pruebas.py` y `graphify update .`; `MEMORY.md`.

## 12. Dudas (resueltas por Andrés, 22/10/2026)
1. **La cita en el chat: A** (decisión 21). Una prueba en `carga.spec.js`, «Ingesta: Procesado y el chat general lo cita», con el motor simulado y su paso manual con Ollama en T6; ~1 h más en T3. RF-11.40 (solo la cita) pasa al alcance; el paso 2 de `testing.md` conserva «→ el chat lo cita».
2. **Limpieza de la verificación manual: A** (decisión 22). Por terminal, ⚠️ con confirmación del hook y conteos antes y después en SQL Server, Qdrant y `uploads/` (§10).
3. **Versión del ERS: A** (decisión 23). La misma V1.8, en un solo lote, si al cerrar la 005b sigue sin exportar (§11).
4. **La regla de §13: A** (decisión 24). Aprobada tal cual.

## 13. Cambio de `.claude/rules/testing.md` (aprobado por Andrés tal cual, 22/10/2026)
Lo aplica Andrés en T6 (el planner y los agentes no editan `.claude/`). «Orden de trabajo», pasos 3 y 4.

**Antes:**
> 3. **Specs retroactivas por módulo**, por riesgo: autenticación y usuarios, ingesta, RAG y chat, notebooks, temas similares y bitácora.
> 4. Después, los «Estado actual» del ERS y las funciones nuevas, con sus pruebas desde el inicio.

**Después:**
> 3. **Cada spec prueba el módulo que toca** (sustituye a las specs retroactivas por módulo; decisión de Andrés, 22/10/2026): toda spec nueva o corrección escribe primero las pruebas de lo que cambia y de los requisitos existentes del módulo que modifica, contra el ERS; lo que el código no cumple, como fallo esperado con su referencia. Lo que ninguna spec toque queda como trabajo futuro documentado (su «Estado actual» en el ERS y una línea en `MEMORY.md`).
> 4. Con el paso 2 cerrado (spec 005b), empiezan las funciones nuevas y los «Estado actual» del ERS, cada una con sus pruebas desde el inicio según el paso 3.

Ajuste asociado del paso 2 (al cerrar la 005b; conserva «→ el chat lo cita», decisión 21): «Hechos (specs 005a y 005b): la infraestructura de extremo a extremo, el acceso, la carga con la cita en el chat general y NotebookServIA; el resto del chat y la bitácora en el navegador, a la spec de su módulo».

Otros textos que citan las retroactivas (no los editan los agentes; los actualiza Andrés en T6):
- `CLAUDE.md`, «Verificación»: «se cubre con specs retroactivas, en el orden de `.claude/rules/testing.md`».
- `.claude/skills/sdd/SKILL.md` («Specs retroactivas»), `.claude/agents/planner.md`, `implementer.md`, `coordinator.md`, `.claude/commands/sdd-implement.md` y `sdd-validate.md`: el mecanismo sigue sirviendo para los requisitos existentes que una spec toca; cambiar solo «el código heredado se cubre con specs retroactivas».
- `MEMORY.md`, «Próximos pasos» 3 y 4.
- `frontend/e2e/soporte/consola_declarada.js`: «la spec retroactiva que lo corregirá» pasa a «la spec del módulo que lo corrija» (implementer, T6). La spec 005 (RA-02.45, «Fuera de alcance») ya está ajustada.
- La constitución no las nombra: no cambia.
