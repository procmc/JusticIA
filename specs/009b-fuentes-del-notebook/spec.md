# Spec 009b — Fuentes del notebook: usar o no usar, renombrar y quitar
Estado: aprobada (05/11/2026, Andrés; P1-P8 y correcciones QA 1-12 incorporadas)

## Contexto y objetivo
- Petición de Andrés: un notebook puede tener varias fuentes; si una pierde valor para una consulta, se desmarca y el chat no la usa «en ese momento».
- Cada fuente lleva una casilla «usar en el chat» y, a su lado, un menú ⋮ con «Quitar fuente» y «Cambiar el nombre».
- «Quitar fuente» es el «Quitar documento» de RF-19 y CU-13, con su borrado físico (excepción aprobada); solo cambia de lugar en la interfaz.
- Va después de la 009, con su mismo estilo de nombre, bitácora y aislamiento.
- Función nueva del módulo NotebookServIA (testing.md, paso 3): las pruebas existentes de quitar documento, vista previa y chat del notebook siguen pasando.

## Trazabilidad
- ERS V1.11: RF-11, RF-12, RF-18, RF-19, RF-21, RNF-04, RNF-07 (RNF-07.6, RNF-07.24), RN-01, RN-03, RA-02, RT-07.
- HU-17, HU-19 · CU-10, CU-13. La casilla y el renombrado de la fuente no existen en el ERS: son `[NUEVO]`.
- «Estado actual» que cierra: ninguno. Bloque de numeración: **.100+**, tras el .80+ de la 009.

## Prioridades y entregas (P8)
1. **Entrega 1**: casilla (A), menú ⋮ con «Quitar fuente» (B) y sus no funcionales. Sin migración.
2. **Entrega 2**: «Cambiar el nombre» (C) y su bitácora (D), con una única migración ⚠️ posterior a la de la 009: la columna de nombre visible (QA-1) y el tipo de acción nuevo.
- Hasta la entrega 2, el menú muestra solo «Quitar fuente».

## Usuarios
- Usuario Gubernamental: dueño del notebook y de sus fuentes.
- Administrador: no entra a NotebookServIA (RN-03).

## Historias de usuario
- HU-NUEVA-3. Como Usuario Gubernamental, quiero desmarcar una fuente de mi notebook para que el chat no la use en mis próximas preguntas, sin quitarla.
- HU-NUEVA-4. Como Usuario Gubernamental, quiero cambiar el nombre de una fuente para reconocerla mejor en la lista y en las citas.
- HU-19 (base de «Quitar fuente»).

## Definiciones
- **Fuente**: un documento de un notebook. **Marcada / desmarcada**: con la casilla activa (el chat la usa) o inactiva.
- **Selección**: los identificadores de las fuentes marcadas (en cualquier estado) que la interfaz envía con cada pregunta.
- **Selección efectiva**: la selección ∩ las fuentes Procesado del propio notebook, calculada por el servidor en cada pregunta.
- **Nombre interno**: el nombre con que se guardó el archivo; ubica el archivo en disco y **nunca cambia**.
- **Nombre visible**: el que el usuario dio al renombrar; mientras no exista, se muestra el nombre interno.
- **Nombre mostrado**: el visible si existe, si no el interno. Lo muestran la lista, la vista previa, la confirmación de quitar, el nombre de descarga y las citas del chat.
- **Extensión**: la del nombre interno, desde su último punto (`informe.v2.pdf` → `.pdf`).
  - Si el nombre interno no tiene punto, o su único punto es el inicial (`.notas`), la extensión es vacía y todo el nombre es la base.
  - Se toma del nombre interno (no del mostrado) para que no pueda cambiar al renombrar; rechazar esos nombres impediría renombrar fuentes ya cargadas.
- **Base**: el nombre mostrado sin la extensión. Lo único editable.
- Nombre normalizado y no admitido: como en la spec 009 (NFC, sin espacios alrededor, categoría Cf).

## Requisitos funcionales

### A. Casilla «usar en el chat» (RF-11) — entrega 1
- **RF-11.100** `[NUEVO]`: EL SISTEMA muestra junto a cada fuente del notebook abierto una casilla, marcada al cargarla, con el texto accesible «Usar <nombre mostrado> en el chat».
- **RF-11.101** `[NUEVO]` (RF-11, RF-12): MIENTRAS una fuente está desmarcada, EL SISTEMA no recupera sus fragmentos para el chat de ese notebook, ni la cita, ni la lista entre los archivos de la consulta.
  - El servidor busca solo en la selección efectiva, dentro de la propia búsqueda por relevancia (RF-11), sin reducir los resultados de las marcadas.
  - Se verifica sobre los fragmentos recuperados y las fuentes listadas, no sobre el texto del modelo.
  - El historial de la conversación no se reescribe: el modelo puede recordar respuestas previas que usaron la fuente (riesgo aceptado).
- **RF-11.102** `[NUEVO]`: CUANDO el Usuario Gubernamental marca o desmarca una fuente, EL SISTEMA aplica el cambio a la siguiente pregunta, sin afectar una respuesta en curso ni los mensajes ya guardados.
- **RF-11.103** `[NUEVO]` (P1): la selección vive solo en la página abierta; no se guarda en el servidor.
  - Al recargar la página, abrir otro notebook o volver al mismo, todas las fuentes vuelven a estar marcadas.
- **RF-11.104** `[NUEVO]` (P4): MIENTRAS ninguna fuente Procesado está marcada, EL SISTEMA desactiva el envío y muestra «Marque al menos una fuente para consultar.».
- **RF-11.105** `[NUEVO]` (P4, defensa): reglas del servidor para la selección en el chat del notebook:
  - campo ausente (cliente anterior): usa todas las fuentes Procesado, como hoy;
  - lista vacía, o selección efectiva vacía (solo Pendiente o Error, solo ajenas o inexistentes): 400 «Marque al menos una fuente para consultar.», sin llamar al modelo ni guardar la pregunta;
  - identificadores mal formados (no enteros): 422 de validación del formato, sin llamar al modelo. Se elige 422 y no descartarlos porque es un error del cliente, no del usuario, y descartarlos ocultaría fallos de la interfaz.
- **RF-11.106** `[NUEVO]`: una fuente en Pendiente o Error muestra la casilla igual; marcarla no la lleva al chat (RF-11: solo Procesado).
  - Una fuente Pendiente marcada que pasa a Procesado entra en la siguiente pregunta: la interfaz la envía en la selección y el servidor decide por su estado en ese momento.
- **RF-11.107** `[NUEVO]`: el campo de selección se ignora en el chat general y en el chat por tema.
- **RNF-07.100** (RNF-07.6): SI la selección incluye un documento ajeno, inexistente o de otro notebook, ENTONCES EL SISTEMA lo descarta y nunca lo recupera.
  - El notebook ajeno sigue respondiendo el 404 uniforme (RF-11.32). Descartar no deja fila propia en la bitácora; la consulta conserva su registro actual.

### B. Menú ⋮ de la fuente (RF-19) — entrega 1
- **RF-19.100** `[NUEVO]` (RF-19, CU-13 paso 1): EL SISTEMA muestra junto a cada fuente un botón de opciones (⋮, texto accesible «Opciones de <nombre mostrado>») con «Cambiar el nombre» (entrega 2) y «Quitar fuente».
  - Reemplaza la «x» actual de la fuente; abrir el menú no abre la vista previa (RF-18) ni cambia la casilla.
- **RF-19.101** (RF-19, P6): CUANDO el Usuario Gubernamental elige «Quitar fuente», EL SISTEMA sigue RF-19 y CU-13 sin cambios de texto.
  - Confirmación «Quitar documento» con «Quitar» y «Cancelar», doble clic con una sola solicitud, borrado de las tres capas y sus mensajes.

### C. Cambiar el nombre de la fuente (RF-19, `[NUEVO]`) — entrega 2
Toda validación la hace el servidor: **400** con el `detail` exacto, en el orden vacío → largo → caracteres → idéntico → duplicado (como la 009).
- **RF-19.102** `[NUEVO]` (P5): EL SISTEMA solo deja editar la base; la extensión se muestra fija y se conserva tal cual.
- **RF-19.103** `[NUEVO]` (QA-1, QA-2): CUANDO el Usuario Gubernamental confirma una base nueva para una de sus fuentes, EL SISTEMA guarda base normalizada + extensión como nombre visible.
  - Lo muestra en la lista, la vista previa, la confirmación de quitar y como nombre de descarga.
  - El nombre interno, el archivo en disco, su tipo (por la extensión), el estado, la casilla y el notebook no cambian; por eso vista previa, descarga y quitar siguen ubicando el archivo igual.
  - Cancelar (botón o Escape) no llama al servidor. Al terminar, la interfaz refresca la lista.
- **RF-19.104** `[NUEVO]` (P2): CUANDO se renombra una fuente Procesado, EL SISTEMA actualiza el nombre de archivo de todos sus fragmentos (los del documento) al nombre visible.
  - Las respuestas nuevas citan y listan el nombre nuevo; los mensajes ya guardados conservan su texto.
- **RF-19.105** `[NUEVO]` (P2, QA-3): orden y compensación del renombrado de una fuente Procesado:
  1. primero se actualizan los fragmentos del documento; después se confirma el nombre visible en la base;
  2. SI la actualización de los fragmentos falla, ENTONCES EL SISTEMA intenta devolver al nombre anterior los que ya cambió y no modifica la base;
  3. SI falla la confirmación en la base, ENTONCES EL SISTEMA devuelve los fragmentos al nombre anterior;
  - en ambos fallos responde 500 «Error interno del servidor» sin texto de excepción; la interfaz muestra «No se pudo cambiar el nombre de la fuente. Intente de nuevo.».
  - *Verificable*: con la base vectorial simulada para fallar, el nombre en la base queda intacto y los fragmentos con el nombre anterior.
  - *Riesgo residual aceptado*: si falla también la compensación, o una búsqueda concurrente cae en la ventana, pueden verse dos nombres; el siguiente renombrado lo corrige.
- **RF-19.106** `[NUEVO]` (P5): reglas de la base normalizada, con su 400:
  - vacía: «El nombre de la fuente no puede estar vacío» (sin punto final, igual que el de vacío de la 009, RF-17.81);
  - más de 150 caracteres (sin contar la extensión): «El nombre no puede superar 150 caracteres.»; el campo no corta la escritura en 150;
  - caracteres no admitidos (los de la 009): «El nombre contiene caracteres no admitidos.»;
  - idéntica a la actual (mismas mayúsculas): no cambia nada, no deja fila y cierra la edición sin error;
  - nombre completo igual, sin distinguir mayúsculas, al nombre mostrado de otra fuente del mismo notebook: «Ya hay una fuente con ese nombre en este notebook.».
- **RF-19.107** `[NUEVO]` (P7): MIENTRAS la fuente está en Pendiente, EL SISTEMA muestra «Cambiar el nombre» desactivado con el aviso «Espere a que termine de procesarse.».
  - Defensa en el servidor: renombrar una fuente Pendiente (también una que volvió a Pendiente) responde 400 con ese mismo texto, sin cambiar nada.
  - En Error se permite y solo cambia el nombre visible (no tiene fragmentos).
- **RF-19.108** `[NUEVO]` (RF-17.90): SI renombrar falla por otro error inesperado, ENTONCES EL SISTEMA responde 500 como en RF-19.105, sin cambiar nada.
- **RF-19.109** `[NUEVO]`: SI la fuente ya no existe (quitada en otra pestaña), ENTONCES EL SISTEMA responde el 404 uniforme y la interfaz la quita de la lista con «La fuente ya no está disponible.».
- **RF-19.110** `[NUEVO]` (QA-10): renombrar en dos pestañas: gana el último renombrado confirmado; cada pestaña refresca la lista tras su cambio.
- **RNF-07.101** (RNF-07.6, CU-13 FE-02): SI se pide renombrar una fuente ajena, inexistente, de un notebook eliminado (009) o con identificador no canónico, ENTONCES EL SISTEMA responde el 404 uniforme antes de validar el nombre, sin cambiar nada.
  - El Administrador queda rechazado (RN-03). El duplicado solo compara con fuentes del propio notebook.

### D. Bitácora (RF-21)
Regla de la 009: cada acción queda registrada, con éxito o con fallo, con la clave `NB-<id>` y el número del documento, nunca con nombres (RNF-07.24).
- **RF-21.100** `[NUEVO]` (entrega 2): EL SISTEMA agrega al catálogo el tipo «Renombrar Documento de Notebook» (siguiente número libre tras los de la 009), consultable y filtrable como los demás, también en el historial propio.
- **RF-21.101** (RF-21, entrega 2): CUANDO se intenta renombrar una fuente disponible, EL SISTEMA registra usuario, tipo, clave, número de documento y resultado, sin el nombre anterior ni el nuevo.
  - Motivos de validación (clasificados como validación): «nombre vacío», «nombre demasiado largo», «nombre con caracteres no admitidos», «nombre duplicado», «fuente en proceso».
  - «error inesperado», clasificado como interno, sin el texto de la excepción (como la 009).
  - Renombrar con la base idéntica no deja fila.
- **RF-21.104** (RF-21.32, RF-21.82): CUANDO se intenta renombrar en un notebook no disponible (ajeno, inexistente, eliminado o no canónico), EL SISTEMA registra solo el motivo «notebook no disponible»; con el notebook propio y la fuente ajena o inexistente, solo «documento no disponible».
  - Ambos clasificados como error de acceso, sin clave, número, nombres ni identificadores pedidos; idénticos para ajeno e inexistente.
- **RF-21.102** (P3): marcar o desmarcar una fuente no se registra en la bitácora.
- **RF-21.103**: «Quitar fuente» conserva su registro actual («Quitar Documento de Notebook»). Si el registro falla, toda acción se completa igual (RF-21.83).

## Requisitos no funcionales
- **RNF-04.100** (RNF-04): casilla, menú y renombrado se usan a 1366 px y a 616 px, sin que un nombre de 150 caracteres desborde la lista ni tape la casilla o el ⋮ (el ancho de desplazamiento de la lista no supera su ancho visible).
- **RN-01.100** (RN-01): renombrar y desmarcar no borran nada; el único borrado físico sigue siendo «Quitar fuente» (RF-19).
  - Única migración ⚠️ (entrega 2): la columna de nombre visible del documento (opcional; vacía en los existentes, que siguen mostrando su nombre interno) y el tipo de RF-21.100. La casilla no necesita migración.
- **RA-02.100**: sin dependencias, servicios, prompts ni modelos nuevos; el e2e queda dentro de su presupuesto (≤ 569 s).
- **RT-07.100** (RT-07): textos nuevos en español, sin voseo.

## Casos límite
- Desmarcar la única fuente Procesado con otras en Pendiente o Error: RF-11.104 (envío desactivado); si igual llega, RF-11.105 (400).
- Fuente nueva cargada, o imagen pegada o arrastrada al chat (008), con otras desmarcadas: entra marcada y las demás conservan su casilla.
- Quitar una fuente desmarcada: igual que una marcada; la selección deja de incluirla.
- Desmarcar durante una respuesta en curso: la respuesta no cambia (RF-11.102).
- Renombrar solo con cambio de mayúsculas: válido. Base con espacios alrededor: se guarda recortada.
- Nombres con varios puntos, sin extensión o que empiezan en punto: ver «Extensión» en Definiciones.
- Renombrar una fuente desmarcada: sigue desmarcada.
- Una fuente pasa de Pendiente a Procesado con el menú abierto: la opción se habilita al refrescar la lista; el servidor decide por el estado actual.
- Carga y renombrado (QA-1; comportamiento de hoy verificado en el código de la carga, fijado con una prueba de integración):
  - cargar un archivo con el **nombre interno** de una fuente renombrada choca en disco como dos archivos de igual nombre hoy: se guarda con sufijo (`informe_1.pdf`) y se muestra con ese nombre; la renombrada no cambia;
  - cargar uno con el **nombre visible** de otra fuente no choca en disco: ambas se muestran con el mismo nombre. La regla de duplicados (RF-19.106) solo aplica al renombrar.

## Fuera de alcance
- Guardar la selección en el servidor o entre sesiones (P1).
- Reescribir el historial de la conversación al desmarcar (RF-11.101).
- Cambiar «Quitar fuente» a eliminación lógica o cambiar sus textos (P6).
- Marcar o desmarcar fuentes en el chat general, el chat por tema, temas similares o el resumen.
- Renombrar documentos de la Ingesta de Datos (temas fuera de notebooks), el nombre interno, el archivo en disco o la extensión.
- Comprobar duplicados de nombre al cargar.
- Reordenar fuentes o marcar y desmarcar todas de una vez.

## Criterios de finalización
- Cada requisito tiene su prueba, vista en rojo y luego en verde, o su exención en el plan.
- `pytest` (normal e inverso) sin fallos ni XPASS nuevos; `npm run e2e` «CORRECTO», dentro del presupuesto. Cada entrega cierra con ambas suites.
- Verificación manual de Andrés (1366 y 616 px, consola limpia): desmarcar y comprobar que la respuesta no cita esa fuente; todas desmarcadas; quitar desde el menú; Administrador rechazado.
- Entrega 2, además: renombrar y ver el nombre en la lista, la vista previa, la descarga y la cita de una respuesta nueva; fragmentos en Qdrant con el nombre nuevo; archivo en disco sin cambios; acción en el Historial.
- Documentación, en la última tarea: RF-11 (casilla), RF-19 (menú y renombrado), RF-21 (tipo nuevo), CU-13 paso 1 (menú en vez de «x»), CU nuevo de renombrar fuente, HU-NUEVA-3 y 4, y el Modelo Relacional (columna de nombre visible y catálogo).

## Dudas abiertas
- Ninguna. Decisiones confirmadas por Andrés en la aprobación (05/11/2026):
  1. identificadores mal formados en la selección → 422 (RF-11.105);
  2. la extensión se toma del nombre interno (Definiciones);
  3. el mensaje de vacío va sin punto final, como RF-17.81 (RF-19.106);
  4. al cargar no se comprueban duplicados de nombre (Casos límite, Fuera de alcance).
