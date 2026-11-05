# Spec 009 — Gestión de notebooks: renombrar y eliminar
Estado: implementada (T1-T7 hechas el 05/11/2026; falta la validación). Aprobada por Andrés el 05/11/2026 y corregida con la revisión de QA y sus decisiones. Plan y tareas en `plan.md` y `tasks.md`.

## Contexto y objetivo
- En NotebookServIA, el panel «Tus colecciones de documentos» solo permite crear notebooks (RF-17).
- Petición de Andrés: completar la gestión con **renombrar** y **eliminar**, y registrar cada acción en la bitácora para saber qué hizo cada persona en cada notebook.
- La eliminación es **lógica** y solo del notebook (RN-01, RNF-10): deja de existir para su dueño, pero sus datos se conservan. «Quitar documento» sigue siendo borrado físico (RF-19, sin cambios).
- Se agregan reglas al nombre, también al crear: largo máximo de 150 caracteres, caracteres admitidos y sin duplicados entre los notebooks activos del mismo usuario.
- Es una función nueva del módulo NotebookServIA (testing.md, paso 3): primero las pruebas de lo que cambia; los requisitos existentes del módulo siguen pasando.
- Tiempo disponible: menos de 5 h (spec y plan ~0,5 h, backend ~1,5 h, interfaz ~1 h, e2e ~1 h, cierre ~0,5 h). Orden y diferibles en «Prioridad».

## Trazabilidad
- ERS V1.11: RF-11.32, RF-17, RF-19, RF-21, RF-22, RF-23, RNF-04, RNF-07 (RNF-07.6, RNF-07.24), RNF-10, RN-01, RN-03, RT-07.
- HU-17 · CU-11 (FA-01, FA-02). Renombrar, eliminar y las reglas del nombre no existen en el ERS: son `[NUEVO]`.
- «Estado actual» que cierra: ninguno (hallazgo de `MEMORY.md`: «no hay borrado ni archivado de notebooks»).
- Bloque de numeración: **.80+**, tras el .70+ de la 008/008b.

## Usuarios
- Usuario Gubernamental: dueño del notebook; lo crea, lo renombra o lo elimina.
- Administrador: no entra a NotebookServIA (RN-03); consulta las acciones en el Historial (RF-22).

## Historias de usuario
- HU-17 (base).
- HU-NUEVA-1. Como Usuario Gubernamental, quiero cambiar el nombre de mi notebook para que describa mejor su contenido.
- HU-NUEVA-2. Como Usuario Gubernamental, quiero eliminar un notebook que ya no uso para mantener ordenada mi lista, sin que se pierda el registro institucional.

## Definiciones
- **Notebook eliminado**: notebook marcado como eliminado por su dueño, con la fecha. Su registro, documentos, archivos, fragmentos y filas de bitácora se conservan sin cambios; eliminarlo no borra su conversación (RF-17.87).
- **Notebook activo**: notebook no eliminado.
- **Notebook no disponible** (004b): se amplía con el notebook eliminado, con el mismo trato que uno ajeno o inexistente.
- **Identificador no canónico** (RF-11.32): el que la regla vigente de identificadores de notebook rechaza: `05`, `+5`, ` 5 `, `abc`, dígitos Unicode no ASCII o un número mayor que el rango de la columna.
- **Nombre normalizado**: el nombre en forma Unicode NFC y sin espacios al inicio ni al final; es el que se valida, se compara y se guarda.
- **Nombre vacío**: el normalizado no tiene ningún carácter visible: está vacío o solo tiene espacios o caracteres invisibles de formato (categoría Unicode Cf, como U+200B).
- **Nombre duplicado**: un nombre normalizado igual, sin distinguir mayúsculas de minúsculas, al de otro notebook activo del mismo usuario.
  - Las tildes y la «ñ» sí distinguen («Café» ≠ «Cafe»), y los espacios internos no se colapsan (D1).
  - «Cafe» + U+0301 (tilde combinada) se normaliza a «Café» y choca con «Café».
  - Los notebooks eliminados y los de otros usuarios no cuentan.

## Requisitos funcionales

### A. Nombre del notebook (RF-17)
Toda validación del nombre la hace el servidor y responde **400** con el `detail` exacto indicado, como la creación con nombre vacío. Orden: vacío → largo → caracteres → idéntico al actual (solo al renombrar) → duplicado.

- **RF-17.80** `[NUEVO]`: CUANDO el Usuario Gubernamental confirma un nombre nuevo para uno de sus notebooks, EL SISTEMA guarda el nombre normalizado y lo muestra en la lista y, si está abierto, en su encabezado.
  - No cambian la clave `NB-<id>`, los documentos, la conversación, el orden de la lista ni el notebook abierto.
  - Cancelar (botón o Escape) deja el nombre como estaba, sin llamar al servidor.
- **RF-17.81** `[NUEVO]` (RF-17, CU-11 FE-01): SI el nombre nuevo es un nombre vacío, ENTONCES EL SISTEMA no lo cambia y responde 400 «El nombre del notebook no puede estar vacío», el mismo de la creación.
- **RF-17.82** `[NUEVO]`: SI el nombre nuevo normalizado supera 150 caracteres, ENTONCES EL SISTEMA no lo cambia y responde 400 «El nombre no puede superar 150 caracteres.».
  - El límite lo valida el servidor (no el formato de la petición, que daría otro código).
  - El campo de la interfaz **no** corta la escritura en 150, para que el mensaje de 151 sea alcanzable y se pruebe en e2e.
- **RF-17.93** `[NUEVO]` (D3): SI el nombre normalizado tiene caracteres que el sistema no puede guardar tal cual (p. ej., emojis o letras fuera del juego latino), ENTONCES EL SISTEMA no lo guarda y responde 400 «El nombre contiene caracteres no admitidos.»; nunca un 500 ni un nombre degradado.
- **RF-17.83** `[NUEVO]`: SI el nombre nuevo normalizado es idéntico al actual (mismas mayúsculas), ENTONCES EL SISTEMA no lo cambia ni lo registra en la bitácora (no es una acción), y la interfaz cierra la edición sin error.
  - Esta comprobación va antes de la de duplicados: el propio notebook nunca cuenta como duplicado de sí mismo.
  - Cambiar solo mayúsculas o minúsculas («informe» → «Informe») es un renombrado válido (RF-17.80).
- **RF-17.84** `[NUEVO]`: SI el nombre nuevo es un nombre duplicado, ENTONCES EL SISTEMA no lo cambia y responde 400 «Ya tiene un notebook con ese nombre.».
- **RF-17.85** `[NUEVO]` (RF-17, cambia la creación): CUANDO el Usuario Gubernamental crea un notebook, EL SISTEMA aplica las mismas reglas del nombre que al renombrar (RF-17.81, 17.82, 17.93 y 17.84, con su 400 y su mensaje).
  - El rechazo no crea el notebook, pero sí deja su fila de bitácora (RF-21.81).

### B. Eliminar (RF-17, RNF-10)
- **RF-17.86** `[NUEVO]`: CUANDO el Usuario Gubernamental elige eliminar uno de sus notebooks, EL SISTEMA pide confirmación antes de hacer nada.
  - Título «Eliminar notebook», el nombre del notebook y el aviso de que dejará de estar disponible con sus documentos y su conversación; botones «Eliminar» y «Cancelar».
  - Cancelar no cambia nada. Un doble clic en «Eliminar» envía una sola solicitud (como RF-19).
- **RF-17.87** `[NUEVO]` (RN-01, RNF-10): CUANDO el Usuario Gubernamental confirma la eliminación, EL SISTEMA marca el notebook como eliminado, con la fecha, sin borrar ni modificar nada más.
  - La fecha sigue la misma convención que la fecha de creación del notebook (hora UTC del servidor).
  - Se conservan: la fila del notebook, sus documentos y su relación, los archivos, los fragmentos en la base vectorial y la bitácora.
  - Eliminar no borra la conversación; esta conserva su vencimiento habitual, sin garantía de plazo.
- **RF-17.88** `[NUEVO]` (RNF-07.6, RF-17.3, RF-17.4, RF-17.31): MIENTRAS un notebook está eliminado, EL SISTEMA lo trata como notebook no disponible en toda vía:
  - no aparece en la lista de su dueño;
  - abrir, listar, previsualizar o quitar documentos, cargar archivos, conversar, renombrar o eliminar de nuevo responden el 404 uniforme de un notebook inexistente;
  - su conversación, pedida por su identificador desde las conversaciones (consultar, restaurar o borrar), responde el 404 de una conversación no disponible;
  - su clave `NB-<id>` en la carga, el chat por tema, temas similares o el resumen recibe el trato de una clave no disponible;
  - sus fragmentos se conservan en la base vectorial pero no llegan al modelo ni a los resultados por ninguna vía, tampoco al chat general ni a temas similares de su dueño.
  - «Toda vía» no incluye las estadísticas (RF-23 y las de ingesta): siguen contando los documentos de los notebooks eliminados, porque se conservan.
- **RF-17.89** `[NUEVO]` (RF-17.70): CUANDO el Usuario Gubernamental elimina el notebook que tiene abierto, EL SISTEMA lo cierra, vuelve al panel sin notebook seleccionado y muestra «Notebook eliminado.».
  - Si había una respuesta en curso, se cancela como en RF-17.70 y no se guarda.
- **RF-17.90** `[NUEVO]` (RF-17.30): SI renombrar o eliminar falla por un error inesperado, ENTONCES EL SISTEMA responde 500 «Error interno del servidor» sin texto de excepción y no cambia nada.
  - La interfaz muestra «No se pudo renombrar el notebook. Intente de nuevo.» o «No se pudo eliminar el notebook. Intente de nuevo.»; el notebook sigue en la lista.
- **RF-17.92** `[NUEVO]` (otra pestaña): SI el Usuario Gubernamental renombra o elimina un notebook que ya se eliminó en otra pestaña, ENTONCES EL SISTEMA responde el 404 uniforme y la interfaz lo quita de la lista con «El notebook ya no está disponible.».

### C. Aislamiento (RNF-07)
- **RNF-07.80** (RNF-07.6, RF-11.32): SI se pide renombrar o eliminar un notebook ajeno, inexistente, eliminado o con identificador no canónico, ENTONCES EL SISTEMA responde el 404 uniforme (nunca un error de validación), sin modificar nada ni revelar su existencia, y deja la fila de intento de RF-21.82.
  - La comprobación va antes de cualquier cambio, también antes de la validación del nombre y la de duplicados. La respuesta no cierra la sesión (RNF-07.30).
- **RNF-07.81** (RN-03): SI el Administrador pide renombrar o eliminar un notebook, ENTONCES EL SISTEMA lo rechaza como el resto de funciones de NotebookServIA.
- **RNF-07.82**: el mensaje de nombre duplicado no revela nada de notebooks ajenos: solo compara con los notebooks activos del propio usuario.

### D. Bitácora (RF-21)
Regla única: **cada acción queda registrada**: crear, renombrar y eliminar, con éxito o con fallo. Lo único que no se registra es renombrar con el nombre idéntico al actual (RF-17.83). Nunca se guardan nombres (RNF-07.24).

- **RF-21.80** `[NUEVO]` (RF-21.34): EL SISTEMA agrega al catálogo los tipos de acción «Renombrar Notebook» y «Eliminar Notebook», sin tocar los existentes; se consultan y filtran como los demás, también en el historial propio.
- **RF-21.81** (RF-21, RF-21.30): CUANDO el Usuario Gubernamental crea, renombra o elimina un notebook (con éxito o con fallo), EL SISTEMA registra el usuario, el tipo, la clave `NB-<id>` como tema y el resultado.
  - Sin el nombre anterior ni el nuevo: el nombre es texto libre y puede contener datos personales (RNF-07.24).
  - La creación rechazada usa el tipo existente «Crear Notebook» con resultado fallido y sin clave, porque el notebook no llega a existir.
  - Un rechazo por validación lleva un motivo fijo, clasificado como validación: «nombre vacío», «nombre demasiado largo», «nombre con caracteres no admitidos» o «nombre duplicado».
  - Un error inesperado lleva el motivo fijo «error inesperado», clasificado como «interno» (como el fallo de quitar documento), sin el texto de la excepción.
  - Cambio de comportamiento: hoy la creación rechazada no deja fila; la prueba existente que lo comprueba (RF-17.30, creación con error inesperado) actualiza su expectativa en el plan, sin borrarse.
- **RF-21.82** (RF-21.32): CUANDO se intenta renombrar o eliminar un notebook no disponible (incluido el eliminado y el identificador no canónico), EL SISTEMA registra el intento fallido solo con el motivo «notebook no disponible», idéntico en todos los casos.
- **RF-21.83** (RF-21): SI el registro en la bitácora falla, ENTONCES crear, renombrar o eliminar se completa igual y la respuesta no cambia.

### E. Requisitos existentes del módulo (testing.md, paso 3)
- **RF-17.91**: siguen pasando las pruebas existentes de crear, abrir, cargar, previsualizar, quitar documento, chat del notebook y reintentar (004b, 005b, 007, 008, 008b), sin fallos esperados nuevos (salvo el cambio de expectativa de RF-21.81).
  - Revisado (05/11): la mayoría crean notebooks con nombres distintos dentro de cada prueba o con un sufijo aleatorio.
  - Riesgo a confirmar en el plan: nombres fijos con el mismo usuario de sesión, que chocarían con la regla de duplicados si la limpieza no fuera por prueba:
    - la fixture con `f"{PREFIJO_DATOS} notebook propio"` (conftest de integración);
    - «notebook del otro» (prueba de aislamiento de notebooks) y «notebook de B» (prueba de conversaciones propias).
  - El plan confirma el alcance de las fixtures de usuario (`usuario_gubernamental`): por prueba o compartido.

## Requisitos no funcionales
- **RNF-04.80** (RNF-04): renombrar y eliminar se pueden usar a 1366 px y a 616 px de ancho, sin que un nombre de 150 caracteres desborde la lista ni tape las opciones (medido: el ancho de desplazamiento de la lista no supera su ancho visible).
- **RN-01.80** (RN-01, RNF-10, principio 5): ningún borrado físico del notebook. Una única migración ⚠️ agrega la fecha de eliminación (admite vacío) al notebook y los dos tipos de RF-21.80.
  - No cambia datos existentes: los notebooks actuales quedan activos, aunque haya nombres repetidos entre ellos (la regla aplica solo a lo que se cree o renombre después).
- **RA-02.80** (RA-02.47): sin dependencias, servicios, prompts ni modelos nuevos. La «suite» de `npm run e2e` queda dentro de su presupuesto (≤ 720 s); el recorte solo lo decide Andrés tras dos corridas altas. Decisión de Andrés (05/11/2026, en la T6): el límite subió de 600 s a 720 s (`globalTimeout` de Playwright), y el presupuesto de 569 s —que se calculó sobre el límite de 600 s— pasó a 720 s; la suite mide ~614-622 s.
- **RT-07.80** (RT-07): todos los textos nuevos en español, sin voseo.

## Pruebas exigidas (principio 4)
- **Unitarias**: validación del nombre (vacío, espacios, solo U+200B, 150 y 151 caracteres, no codificable, igual al actual, solo cambio de mayúsculas, duplicado con otra grafía de mayúsculas o espacios, «Cafe» + U+0301 contra «Café», distinto solo por tilde); el eliminado se trata como no disponible; el registro sin nombres, con cada motivo fijo y con la bitácora que falla (RF-21.83).
- **Integración** (entorno aislado, usuarios `PRUEBA` A y B):
  - renombrar y eliminar propios: 200, fila conservada con la marca y la fecha; documentos, archivos y conteo de fragmentos sin cambios;
  - crear y renombrar con nombre vacío, de 151 caracteres o duplicado: 400 con el `detail` exacto, sin cambios en los notebooks y con su fila fallida; con el nombre de un eliminado de A o de un notebook de B: se permite;
  - crear con 150 caracteres que no son del juego latino: 400 de RF-17.93, nunca 500; con 150 caracteres latinos con tildes: se acepta y se guarda igual;
  - con el notebook de A desde B, uno inexistente, uno eliminado y los identificadores `abc`, `05`, `+5` y uno mayor que el rango: 404 idéntico y una fila de intento; Administrador rechazado;
  - el eliminado no sale en la lista; su chat, carga, listado, previsualización, quitar y su conversación por identificador dan 404; su clave en el chat por tema y en temas similares recibe el trato de no disponible; sus fragmentos siguen en la base vectorial y no llegan al chat general ni a temas similares del dueño;
  - error inesperado forzado al renombrar y al eliminar (RF-17.90): 500 genérico, sin cambios y con su fila «interno»;
  - eliminar con un documento en Pendiente (procesamiento simulado): al terminar la ingesta, sus fragmentos existen y no llegan a ninguna vía;
  - migración (RF-21.80, RN-01.80): los dos tipos están en el catálogo y filtran también el historial propio; un notebook sin fecha de eliminación es activo;
  - una fila en la bitácora por acción (tipo, `NB-<id>` o sin clave, resultado, motivo), sin los nombres inventados; renombrar con el nombre idéntico no deja fila.
- **Extremo a extremo** (Playwright, 1366 y 616 px): renombrar (con éxito, vacío, 151 caracteres, duplicado, cancelar); crear con nombre duplicado; eliminar (cancelar, confirmar y desaparece de la lista; el abierto se cierra); doble clic en «Eliminar» envía una sola solicitud (RF-17.86); eliminar el abierto con una respuesta retenida no la guarda (RF-17.89); otra pestaña (RF-17.92); 150 caracteres sin desborde (RNF-04.80); el Administrador no entra.

## Prioridad (menos de 5 h)
1. Migración y backend, con sus unitarias e integración: no se difiere.
2. Interfaz (renombrar, eliminar, mensajes): no se difiere.
3. Extremo a extremo: primero los flujos básicos (renombrar, eliminar, duplicado, Administrador).
- Si falta tiempo, se difieren con exención anotada en el plan y verificación manual de Andrés: doble clic (RF-17.86), respuesta retenida (RF-17.89), otra pestaña (RF-17.92) y el desborde a 616 px (RNF-04.80). Quedan como deuda en `MEMORY.md`.

## Casos límite
- Nombre nuevo con espacios alrededor: se guarda recortado; solo espacios o solo invisibles (U+200B): RF-17.81.
- Exactamente 150 caracteres tras normalizar: se acepta; 151: RF-17.82.
- Emojis o letras no latinas: RF-17.93.
- Renombrar o eliminar desde otra pestaña con el notebook ya eliminado: RF-17.92.
- Eliminar un notebook con documentos aún en Pendiente: la ingesta termina igual y sus fragmentos quedan conservados, sin llegar a ninguna vía.
- Eliminar un notebook vacío: igual que uno con documentos.
- Crear o renombrar con el nombre de uno eliminado: se permite; el nuevo es otro notebook con otra clave.
- Dos usuarios con notebooks del mismo nombre: se permite.
- Nombre con un nombre de persona inventado: no llega a la bitácora.

## Fuera de alcance
- Ver o restaurar notebooks eliminados, para cualquier rol.
- Cambiar «quitar documento» a eliminación lógica.
- Borrar físicamente datos de un notebook eliminado o liberar su espacio; garantizar cuánto dura su conversación.
- Excluir los notebooks eliminados de las estadísticas (RF-23, ingesta).
- Corregir los nombres repetidos que ya existan en los datos.
- Garantizar la unicidad ante dos creaciones o renombrados simultáneos del mismo usuario (D2): no hay índice único; lo mitiga el envío único del doble clic.
- Archivar, duplicar, compartir u ordenar notebooks.
- Renombrar «expediente» y los residuos de notebooks (90003, 80003, 90004): se pueden eliminar con esta función tras el cierre, si Andrés lo decide.

## Criterios de finalización
- Cada requisito tiene su prueba, vista en rojo y luego en verde, o su exención en el plan.
- `pytest` (normal e inverso): 0 fallos, 0 XPASS, ningún fallo esperado nuevo. `npm run e2e`: «CORRECTO», dentro del presupuesto.
- La fila en la bitácora y la marca de eliminación se comprueban con las pruebas de integración; los fragmentos del eliminado, con `curl` a Qdrant.
- Verificación manual: **Andrés revisa la interfaz en persona** (1366 y 616 px, consola sin errores; en esta spec no se usa el MCP `chrome-devtools`):
  - el Usuario Gubernamental renombra, elimina y ve los rechazos;
  - el Administrador es rechazado en la interfaz, por el menú y escribiendo la ruta;
  - las acciones aparecen en el Historial.
- `npm run build` y `npm run lint` sin errores.
- Documentación, en la última tarea: RF-17 (renombrar, eliminar y reglas del nombre al crear), RF-21 (los dos tipos y el registro de la creación rechazada), RNF-10 (eliminación lógica del notebook), CU nuevo, HU-NUEVA-1 y HU-NUEVA-2, Modelo Relacional (fecha de eliminación y tipos).

## Decisiones tomadas (05/11, Andrés)
- D1. Las tildes distinguen. Se normaliza a NFC y se rechaza lo no codificable (RF-17.93), en vez de comparar contra lo que la base guarda degradado: así lo validado, lo comparado y lo guardado son el mismo texto, y dos nombres distintos no chocan por una sustitución silenciosa.
- D2. Las solicitudes simultáneas quedan fuera de alcance.
- D3. Lo no codificable se rechaza con 400 (RF-17.93), nunca 500 ni guardado degradado; prueba de integración con 150 caracteres no latinos.
- D4. Aprobada (05/11) la opción (a) de RF-17.93: el mensaje es «El nombre contiene caracteres no admitidos.».
