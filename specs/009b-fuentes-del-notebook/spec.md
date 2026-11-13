# Spec 009b — Fuentes del notebook: usar o no usar, renombrar y quitar
Estado: implementada (09/11/2026; aprobada el 05/11/2026 por Andrés, con P1-P8 y correcciones QA 1-12 incorporadas; falta la validación del @reviewer); cambio «baja lógica de la fuente» (GG1, Andrés, 11/11/2026): aprobado por Andrés el 11/11/2026 (necesario para la trazabilidad y la prevención de fraude); falta el visto bueno del tutor para RN-01, RNF-10 y la constitución; implementado (T9-T13; T14 abierta); cambio «nombre completo de la fuente» (HH1, Andrés, 12/11/2026): aprobado por Andrés el 12/11/2026, sin implementar; cambio «vista previa de todos los formatos permitidos» (II1, Andrés, 12/11/2026): aprobado por Andrés el 12/11/2026 (incluye TIFF y la dependencia Pillow), sin implementar

## Contexto y objetivo
- Petición de Andrés: un notebook puede tener varias fuentes; si una pierde valor para una consulta, se desmarca y el chat no la usa «en ese momento».
- Cada fuente lleva una casilla «usar en el chat» y, a su lado, un menú ⋮ con «Quitar fuente» y «Cambiar el nombre de la fuente».
- «Quitar fuente» es el «Quitar documento» de RF-19 y CU-13, con su borrado físico (excepción aprobada); solo cambia de lugar en la interfaz.
  - Cambio posterior (GG1, 11/11/2026): para que una auditoría sepa **qué** fuente se quitó, **quién** la quitó y **cuándo**, la fila del documento ya no se borra: pasa a baja lógica (sección E). El archivo y los fragmentos se siguen eliminando.
- Va después de la 009, con su mismo estilo de nombre, bitácora y aislamiento.
- Función nueva del módulo NotebookServIA (testing.md, paso 3): las pruebas existentes de quitar documento, vista previa y chat del notebook siguen pasando.

## Trazabilidad
- ERS V1.11: RF-11, RF-12, RF-18, RF-19, RF-21, RNF-04, RNF-07 (RNF-07.6, RNF-07.24), RN-01, RN-03, RA-02, RT-07.
- HU-17, HU-19 · CU-10, CU-13. La casilla y el renombrado de la fuente no existen en el ERS: son `[NUEVO]`.
- «Estado actual» que cierra: ninguno. Bloque de numeración: **.100+**, tras el .80+ de la 009.

## Prioridades y entregas (P8)
1. **Entrega 1**: casilla (A), menú ⋮ con «Quitar fuente» (B) y sus no funcionales. Sin migración.
2. **Entrega 2**: «Cambiar el nombre de la fuente» (C) y su bitácora (D), con una única migración ⚠️ posterior a la de la 009: la columna de nombre visible (QA-1) y el tipo de acción nuevo.
- Hasta la entrega 2, el menú muestra solo «Quitar fuente».

## Usuarios
- Usuario Gubernamental: dueño del notebook y de sus fuentes.
- Administrador: no entra a NotebookServIA (RN-03).

## Historias de usuario
- HU-NUEVA-3. Como Usuario Gubernamental, quiero desmarcar una fuente de mi notebook para que el chat no la use en mis próximas preguntas, sin quitarla.
- HU-NUEVA-4. Como Usuario Gubernamental, quiero cambiar el nombre de una fuente para reconocerla mejor en la lista y en las citas.
- HU-NUEVA-5 (HH1). Como Usuario Gubernamental, quiero ver el nombre completo de una fuente al pasar el mouse sobre él, para reconocerla aunque su nombre sea largo y la lista lo corte, sin una barra de desplazamiento incómoda.
- HU-NUEVA-6 (II1). Como Usuario Gubernamental, quiero abrir desde la lista cualquier fuente que pueda agregar a un notebook (PDF, Word, texto, HTML, imagen o audio) para verificar su contenido original, y en un audio poder reproducirlo, adelantarlo y atrasarlo viendo en qué segundo voy y cuánto dura.
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
- **RF-19.100** `[NUEVO]` (RF-19, CU-13 paso 1): EL SISTEMA muestra junto a cada fuente un botón de opciones (⋮, texto accesible «Opciones de <nombre mostrado>») con «Cambiar el nombre de la fuente» (entrega 2) y «Quitar fuente».
  - Reemplaza la «x» actual de la fuente; abrir el menú no abre la vista previa (RF-18) ni cambia la casilla.
- **RF-19.101** (RF-19, P6): CUANDO el Usuario Gubernamental elige «Quitar fuente», EL SISTEMA sigue RF-19 y CU-13 sin cambios de texto.
  - Confirmación «Quitar documento» con «Quitar» y «Cancelar», doble clic con una sola solicitud, borrado de las tres capas y sus mensajes.
  - Cambio (GG1): «las tres capas» pasan a ser fragmentos y archivo eliminados, más la baja lógica de la fila (RF-19.111); los textos de los errores no cambian. El cuerpo de la confirmación sí cambia (11/11/2026, Andrés): «¿Desea eliminar "<nombre>" de este notebook de forma definitiva?» (RF-19.70 de la 008); el título «Quitar documento» y los botones «Quitar» y «Cancelar» se conservan.

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
- **RF-19.107** `[NUEVO]` (P7): MIENTRAS la fuente está en Pendiente, EL SISTEMA muestra «Cambiar el nombre de la fuente» desactivado con el aviso «Espere a que termine de procesarse.».
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
  - Con GG1 el número de documento que lleva esa fila sigue apuntando a una fila existente (con su nombre, tipo y baja), no a una borrada (RF-19.111).

### E. Baja lógica de la fuente (RF-19, RN-01, RNF-10, RF-21) — cambio GG1 (11/11/2026)
Motivo (Andrés): en una auditoría de un caso específico hay que poder reconstruir la trazabilidad del uso del sistema; hoy, al quitar una fuente, se borra su fila y de ella solo queda en la bitácora un número que ya no apunta a nada. **Quién** y **cuándo** ya constan en la bitácora; falta **qué** era.
- **RF-19.111** `[NUEVO]` (RF-19, RN-01, RNF-10): CUANDO el Usuario Gubernamental confirma «Quitar fuente», EL SISTEMA elimina los fragmentos y el archivo de la fuente y marca su fila como quitada, sin borrarla.
  - La fila conserva el nombre interno, el nombre visible (si lo había), el tipo, la fecha de carga, el estado de procesamiento, su relación con el notebook, la **fecha y hora de la baja** y **quién la quitó**.
  - Ya no queda ningún fragmento en la base vectorial ni el archivo en disco; el contenido no se puede recuperar.
- **RF-19.112** `[NUEVO]` (RF-19, RF-19.2 de la 004): orden y fallos de la baja:
  1. primero se eliminan los fragmentos, después el archivo y, por último, se marca la fila como quitada;
  2. SI falla alguno de los dos borrados, ENTONCES EL SISTEMA responde 500 «No se pudo quitar el documento. Intente de nuevo.» (sin texto de excepción), la fila no se marca y el documento sigue en la lista; un nuevo intento completa lo que faltó (lo que ya no existe cuenta como eliminado);
  3. SI falla solo marcar la fila, ENTONCES el mismo 500 y mensaje: el documento sigue en la lista y el reintento termina la baja.
  - *Verificable*: con Qdrant, el disco o la base simulados para fallar en cada paso, la fila no queda marcada y el documento sigue listado.
- **RF-19.113** `[NUEVO]` (RF-11, RF-12, RF-18, RNF-07.6): MIENTRAS una fuente está quitada, EL SISTEMA la trata como inexistente para el usuario: no la lista, no entra en la selección efectiva del chat ni del Estudio, no se puede abrir ni descargar, y pedirla por su número responde el 404 uniforme (como RF-19.109).
  - Tampoco se cuenta como documento del notebook ni del tema `NB-<id>` en listados, contadores ni búsquedas.
- **RF-19.114** `[NUEVO]` (RF-19.106): los nombres de las fuentes quitadas no cuentan para el duplicado de nombre al renombrar, y un archivo nuevo puede cargarse con el nombre de una fuente quitada (su archivo ya no está en disco).
- **RF-19.115** `[NUEVO]` (RF-14.123): los resultados del Estudio generados con una fuente quitada siguen mostrando su nombre y el aviso de que la fuente ya no está disponible; nada cambia en ellos.
- **RF-21.105** `[NUEVO]` (RF-21): la fila de la bitácora de «Quitar fuente» no cambia (usuario, fecha y hora, tipo, clave `NB-<id>`, número de documento y resultado, sin nombres, RNF-07.24); con RF-19.111 ese número permite llegar al nombre y los datos de la fuente quitada.

### F. Nombre completo de la fuente (RF-19, RNF-04) — cambio HH1 (12/11/2026)
Motivo (Andrés): al agregar archivos al notebook, los nombres largos no se leen completos; en la lista se cortan con «…» (el aviso del navegador tarda y no sale con el teclado) y la etiqueta del archivo que se está agregando desborda y deja una barra de desplazamiento horizontal incómoda. Solo cambia cómo se muestra el nombre: no cambia el nombre guardado, el servidor ni la bitácora.
- **RF-19.116** `[NUEVO]` (RF-19, RNF-04): CUANDO el Usuario Gubernamental pasa el mouse sobre el nombre de una fuente de la lista, o lo enfoca con el teclado, EL SISTEMA muestra un aviso flotante con el nombre mostrado completo.
  - El aviso sale casi de inmediato, se cierra al quitar el mouse, perder el foco o pulsar Escape, y no tapa el menú ⋮ ni la casilla.
  - Una fuente Procesado conserva además la indicación actual «haga clic para ver el archivo original» en una segunda línea del mismo aviso; Pendiente y Error muestran solo el nombre.
  - Con un nombre largo o sin espacios, el aviso lo parte en varias líneas dentro de la pantalla (a 1366 px y a 616 px), sin barra de desplazamiento.
  - El aviso se muestra siempre, aunque el nombre quepa entero (no se mide el recorte).
- **RF-19.117** `[NUEVO]` (RF-19, RNF-04): MIENTRAS un archivo se está agregando al notebook (subida en curso), EL SISTEMA muestra su etiqueta en una sola línea, recorta el nombre con «…» y deja siempre visible el porcentaje de avance; al pasar el mouse o enfocar la etiqueta, muestra el nombre completo en el mismo aviso.
  - La etiqueta nunca es más ancha que el panel de Fuentes: no genera barra de desplazamiento horizontal.
- **RNF-04.101** `[NUEVO]` (RNF-04.100): a 1366 px y a 616 px, con un nombre de 150 caracteres más su extensión, ni la lista de fuentes ni las subidas en curso desbordan el panel: el ancho de desplazamiento del panel no supera su ancho visible, y el aviso queda dentro de la pantalla.
- **RF-19.118** `[NUEVO]` (RT-07): el aviso muestra el nombre sin modificarlo ni traducirlo, como texto (nunca como HTML) y sin agregar textos nuevos salvo la indicación ya existente (RF-19.116).

### G. Vista previa de todos los formatos permitidos (RF-18) — cambio II1 (12/11/2026)
Nota (FFF1, 12/11/2026): el RTF dejó de ser un formato permitido (spec 006, RF-05.52): su vista de texto se quita de esta sección.
Motivo (Andrés): al pulsar una fuente `.txt` o `.m4a` la ventana dice «Vista previa no disponible para este tipo de archivo.»; hoy solo se ven imágenes y PDF, y él quiere poder ver todas las fuentes que se pueden agregar (los formatos de RF-05: PDF, DOC, DOCX, TXT, HTML, HTM, XHTML, MP3, WAV, OGG, M4A, JPG, JPEG, PNG, TIF, TIFF y BMP). Cambia RF-18 del ERS, que excluye el audio y Word de la vista previa. Excel no es un formato permitido (RF-05), así que no tiene vista previa. El texto, el audio y las imágenes se muestran con lo que el servidor ya entrega (RF-18.1: `.m4a` → `audio/mp4`, `.wav` → `audio/x-wav`, `.txt` → `text/plain`); Word y HTML necesitan una vista de texto del servidor y TIFF una conversión a imagen.
- **RF-18.100** `[NUEVO]` (RF-18; CU-12; HU-NUEVA-6): CUANDO el Usuario Gubernamental pulsa una fuente Procesado de texto plano (`.txt`), EL SISTEMA abre la misma ventana de vista previa (título con el nombre mostrado) y muestra su contenido como texto, respetando los saltos de línea.
  - El texto se muestra como texto (nunca interpretado como HTML), con ajuste de línea y desplazamiento dentro de la ventana, sin desbordar a 1366 px ni a 616 px.
  - Si el archivo supera 200.000 caracteres, se muestran los primeros 200.000 y debajo el aviso «Se muestran los primeros 200.000 caracteres del archivo.».
  - Si el archivo está vacío, la ventana muestra «El archivo está vacío.».
- **RF-18.101** `[NUEVO]` (RF-18; CU-12; HU-NUEVA-6): CUANDO pulsa una fuente Procesado de audio (`.mp3`, `.wav`, `.ogg`, `.m4a`), EL SISTEMA abre la ventana de vista previa con un reproductor del audio original, con:
  - botones de reproducir y pausar;
  - una barra de progreso que muestra en qué parte va y que el usuario puede arrastrar o pulsar para adelantar o atrasar;
  - el tiempo transcurrido y la duración total, en minutos y segundos (`m:ss`) y, desde una hora, en horas, minutos y segundos (`h:mm:ss`);
  - control de volumen.
- **RF-18.102** `[NUEVO]` (RF-18.101): MIENTRAS el audio no ha empezado a reproducirse, EL SISTEMA no lo reproduce solo (sin reproducción automática); CUANDO el usuario cierra la ventana, EL SISTEMA detiene el audio y libera el archivo cargado.
- **RF-18.103** `[NUEVO]` (RF-18): SI el navegador no puede reproducir el audio (formato o códec no admitido), ENTONCES la ventana muestra «Su navegador no puede reproducir este audio.» en lugar del reproductor.
- **RF-18.104** `[NUEVO]` (RF-18): imagen (JPG, JPEG, PNG, BMP) y PDF se muestran como antes (RF-18.40); cualquier tipo que no tenga vista previa (hoy, ninguno de los permitidos por RF-05) muestra «Vista previa no disponible para este tipo de archivo.».
  - La interfaz decide por el tipo de contenido que entrega el servidor (`image/*`, `application/pdf`, `text/plain`, `audio/*`) y por la extensión para Word y HTML (RF-18.106).
- **RF-18.106** `[NUEVO]` (RF-18; RF-05; HU-NUEVA-6): CUANDO pulsa una fuente Procesado de Word (`.doc`, `.docx`) o HTML (`.html`, `.htm`, `.xhtml`), EL SISTEMA abre la ventana de vista previa con una **vista de texto** del documento: el texto que contiene, con sus párrafos y saltos de línea, obtenido del archivo original en ese momento.
  - Encima del texto, una línea fija: «Vista de texto: no conserva el formato ni las imágenes del original.».
  - Las tablas se muestran como texto, fila por fila. Un archivo HTML nunca se muestra como página ni se ejecuta: solo su texto, como texto (RF-18.100).
  - Mismos límites que `.txt`: más de 200.000 caracteres se cortan con su aviso (RF-18.100); sin texto, la ventana dice «El documento no tiene texto que mostrar.».
  - Es la misma extracción de texto que usa la ingesta (Apache Tika); no se agrega ningún servicio.
- **RF-18.107** `[NUEVO]` (RF-18.106): SI el servidor no puede obtener la vista de texto (Tika no responde o el archivo está dañado), ENTONCES la ventana muestra «No se pudo mostrar el documento. Intente de nuevo.» sin texto de excepción, y la fuente sigue como estaba; mientras tanto la fuente dice «Abriendo…».
- **RF-18.108** `[NUEVO]` (RF-18; RF-05) ⚠️ aprobado por Andrés el 12/11/2026 (dependencia nueva): CUANDO pulsa una fuente Procesado de imagen TIFF (`.tif`, `.tiff`), que el navegador no muestra, EL SISTEMA la muestra convertida a imagen (PNG); si el TIFF tiene varias páginas, se muestra la primera con el aviso «Se muestra la primera página.».
  - La conversión necesita una dependencia nueva en el backend (Pillow, que hoy no está instalada) y reconstruir la imagen de `backend` (`docker compose build backend`); aprobado por Andrés el 12/11/2026.
  - SI la conversión falla, ENTONCES aplica el aviso de RF-18.107.
- **RF-18.105** `[NUEVO]` (RF-18.40, RNF-04): la vista previa de todos los formatos mantiene el comportamiento de RF-18.40: «Abriendo…» sobre la fuente mientras se obtiene el archivo, solo fuentes Procesado, la fuente con el menú ⋮ abierto no se ve afectada y la ventana cabe en 1366 px y en 616 px.
- **RNF-07.102** `[NUEVO]` (RNF-07.6, RNF-07.21): texto, audio e imágenes se entregan por la ruta autenticada de RF-18.1; la vista de texto (RF-18.106) y la conversión de TIFF (RF-18.108) son funciones nuevas del servidor y cumplen lo mismo: token y rol Usuario Gubernamental, verificación de que el documento es de un notebook del usuario (404 uniforme para lo ajeno, inexistente, quitado o de un notebook eliminado), solo documentos Procesado, y el mismo registro de bitácora de la previsualización, con su fallo clasificado; sin nombres, rutas ni texto del archivo en la bitácora (RNF-07.24). Un `.html` no se interpreta ni se muestra como página.

## Requisitos no funcionales
- **RNF-04.100** (RNF-04): casilla, menú y renombrado se usan a 1366 px y a 616 px, sin que un nombre de 150 caracteres desborde la lista ni tape la casilla o el ⋮ (el ancho de desplazamiento de la lista no supera su ancho visible).
- **RN-01.100** (RN-01): renombrar y desmarcar no borran nada. «Quitar fuente» solo borra de forma definitiva el contenido (fragmentos y archivo); la fila del documento se conserva con baja lógica (RF-19.111, GG1). Antes de GG1 era el único borrado físico de filas de documentos.
  - Única migración ⚠️ (entrega 2): la columna de nombre visible del documento (opcional; vacía en los existentes, que siguen mostrando su nombre interno) y el tipo de RF-21.100. La casilla no necesita migración.
- **RN-01.101** `[NUEVO]` (GG1, RNF-10): con el cambio no queda ninguna eliminación física de **filas** de documentos en el sistema; las únicas eliminaciones definitivas son el archivo y los fragmentos de una fuente quitada y el reemplazo de fragmentos del re-fragmentado (spec 007).
  - Migración ⚠️ (GG1): columnas opcionales en el documento para la fecha y hora de la baja y quién la quitó (vacías en los existentes, que siguen activos). Todo consulta de documentos de notebooks debe excluir los quitados. Los documentos que se quitaron antes de este cambio no se pueden reconstruir.
- **RA-02.100**: sin dependencias, servicios, prompts ni modelos nuevos; el e2e queda dentro de su presupuesto (≤ 720 s).
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
- Nombre sin espacios de 150 caracteres más extensión: la fila lo recorta con «…» y el aviso lo parte en líneas (RF-19.116, RNF-04.101).
- Fuente renombrada: el aviso muestra el nombre visible completo, no el interno (RF-19.103).
- Fuente con el menú ⋮ abierto o mientras dice «Abriendo…»: el aviso del nombre no tapa el menú; el texto «Abriendo…» no sustituye el nombre del aviso.
- Pantalla táctil sin mouse (616 px): el aviso sale al enfocar con el teclado; tocar el nombre sigue abriendo la vista previa y no se cambia (RF-18).
- Varias subidas a la vez con nombres largos: cada etiqueta se recorta por su cuenta y conserva su porcentaje (RF-19.117).
- Texto con codificación que no es UTF-8 (por ejemplo Latin-1): se muestra decodificado como UTF-8, con símbolos de reemplazo en las letras que no coincidan; el archivo no se modifica (RF-18.100).
- Texto de más de 200.000 caracteres: se corta en la vista previa, no el archivo ni su contenido indexado (RF-18.100).
- Audio muy largo (más de una hora): el tiempo se muestra como `h:mm:ss` (RF-18.101). El audio se carga completo antes de abrir la ventana, así que uno de cientos de megabytes tarda en abrir mientras la fuente dice «Abriendo…».
- Word protegido con contraseña, dañado o sin texto: aviso de RF-18.107 o «El documento no tiene texto que mostrar.» (RF-18.106).
- Un `.docx` con imágenes y tablas: se ve su texto, las tablas fila por fila y no las imágenes; para verlas el usuario no tiene vista fiel (límite aceptado, RF-18.106).
- Un `.html` con `<script>`: nunca se ejecuta; solo se muestra su texto (RF-18.106, RNF-07.102).
- Una fuente de Excel: no puede existir, porque RF-05 no permite subirla.
- Tika detenido al abrir un Word: aviso de RF-18.107; texto, audio, imagen y PDF no dependen de Tika y siguen funcionando.
- Audio `.m4a` en un navegador sin el códec: aviso de RF-18.103; el resto de la fuente (chat, Estudio) no se ve afectado.
- Cerrar la ventana con el audio sonando: se detiene al instante; abrir otra fuente no mezcla dos audios (RF-18.102).
- Una fuente de audio en estado Pendiente o Error: no se abre, como hoy (RF-18.105).
- Quitar la fuente que otra pestaña acaba de quitar: 404 uniforme y la interfaz la saca de la lista (RF-19.109, RF-19.113).
- Quitar con un fallo a mitad (fragmentos borrados y archivo no, o ambos y la fila no marcada): el documento sigue en la lista, sin fragmentos; reintentar completa la baja (RF-19.112).
- Cargar de nuevo un archivo con el nombre de una fuente quitada: se guarda sin sufijo y se muestra con su nombre; la quitada no cambia (RF-19.114).
- Un resultado del Estudio con una fuente quitada: conserva su nombre y el aviso (RF-19.115).
- Carga y renombrado (QA-1; comportamiento de hoy verificado en el código de la carga, fijado con una prueba de integración):
  - cargar un archivo con el **nombre interno** de una fuente renombrada choca en disco como dos archivos de igual nombre hoy: se guarda con sufijo (`informe_1.pdf`) y se muestra con ese nombre; la renombrada no cambia;
  - cargar uno con el **nombre visible** de otra fuente no choca en disco: ambas se muestran con el mismo nombre. La regla de duplicados (RF-19.106) solo aplica al renombrar.

## Fuera de alcance
- Guardar la selección en el servidor o entre sesiones (P1).
- Reescribir el historial de la conversación al desmarcar (RF-11.101).
- Cambiar los textos de «Quitar fuente» (P6). Su paso a baja lógica de la fila se hace en la sección E (GG1).
- Restaurar o «deshacer» una fuente quitada, conservar su archivo o su contenido, o mostrar las fuentes quitadas en la interfaz.
- Una pantalla de auditoría para el Administrador: la consulta sale de la bitácora y de la fila (RN-03).
- Quitar documentos de Ingesta de Datos (temas fuera de notebooks): no existe y no se agrega.
- El aviso del nombre completo en otras listas: los notebooks del panel izquierdo, la Ingesta de Datos, las fuentes del Estudio y las citas del chat (se pueden pedir aparte).
- Cambiar el ancho de los paneles, medir si el nombre está recortado, o mostrar el nombre completo en la lista (con varias líneas).
- Vista fiel al original de Word y HTML (con su diseño, imágenes y estilos): exigiría convertirlos con un servicio nuevo (por ejemplo LibreOffice) y no se hace; la vista es de texto (RF-18.106).
- Permitir subir otros formatos (Excel, PowerPoint, CSV…) o su vista previa: no son formatos permitidos (RF-05). Si se piden, es un cambio de RF-05 y de la ingesta, con su propia spec.
- Cambiar la ingesta o el procesamiento de los archivos.
- Reproducción de audio por tramos (streaming con `Range`): el audio se obtiene completo antes de mostrarse. Control de velocidad, subtítulos o transcripción en la ventana.
- Vista previa en el Estudio, el chat general o la Ingesta de Datos; descargar el archivo.
- Resaltar o buscar texto dentro del archivo, o mostrar `.txt` con otra codificación.
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
- HH1: verificación manual de Andrés (1366 y 616 px): pasar el mouse y usar el teclado sobre una fuente de nombre largo y sobre un archivo que se está agregando; sin barra horizontal; consola limpia.
- HH1, pruebas: e2e en `notebooks-fuentes.spec.js` (nombre de 150 caracteres: aviso con el nombre completo al pasar el mouse y al enfocar; sin desborde del panel a 1366 y 616 px; etiqueta de subida en curso recortada con el porcentaje visible, usando la retención de la ingesta del control de la instancia); sin pruebas de backend ni migración.
- HH1, documentación: RNF-04 del ERS (una frase) y HU-NUEVA-5; sin cambios en casos de uso, diagramas ni Modelo Relacional.
- II1: verificación manual de Andrés (1366 y 616 px, consola limpia): abrir un `.txt`, un `.docx` y ver su texto con la línea «Vista de texto…»; un `.html` y ver que solo muestra texto; abrir un `.m4a`/`.mp3`, reproducir, pausar, adelantar y atrasar con la barra, ver el tiempo y la duración; cerrar con el audio sonando; un `.tif` (si RF-18.108 se aprueba).
- II1, pruebas: e2e en `notebooks-fuentes.spec.js` (o el archivo de vista previa de `notebooks.spec.js`): `.txt` inventado con contenido y saltos de línea visibles, con `<script>` escrito como texto; texto largo cortado con su aviso; audio `.wav` inventado generado por la prueba (el navegador de Playwright decodifica WAV; `.m4a` no siempre): reproductor presente sin reproducción automática, barra que se mueve y se adelanta (`currentTime`), duración mostrada, y audio detenido al cerrar; un `.docx` y un `.html` con `<script>` muestran su texto sin ejecutar nada. Pruebas de integración del backend (SQL Server, Tika y archivos reales del entorno aislado): la vista de texto de un `.docx` y `.html` inventados devuelve su texto; ajeno, inexistente, quitado y Pendiente responden como RF-18.1; Tika caído da el error de RF-18.107 sin texto de excepción; el límite de 200.000 caracteres; la bitácora registra la previsualización sin nombres ni texto; y, si se aprueba RF-18.108, un TIFF de varias páginas. Sin migración.
- II1, documentación: RF-18 del ERS (hoy dice «imagen o PDF» y excluye el audio y Word), HU-18 (criterios), CU-12 (flujo y alternativas; Tika como actor secundario de la vista de texto) y su diagrama, y la arquitectura si se agrega Pillow; sin cambios en el Modelo Relacional.
- GG1, además: RF-19 del ERS (la eliminación pasa a fragmentos y archivo más baja lógica de la fila, y deja de ser «la única eliminación definitiva» de filas), RN-01 y RNF-10 (la excepción se limita al contenido), HU-19 y CU-13 (textos de eliminación y salida), el Modelo Relacional (columnas de baja), el principio 5 de la constitución y la sección «Datos» de `CLAUDE.md`.
- GG1, pruebas: integración de la baja (fila conservada con nombre, tipo, fecha y quién; archivo y fragmentos ausentes; no listada ni en el chat ni en el Estudio; 404 en vista previa y descarga; fallos simulados en cada paso); unitaria de los filtros; las pruebas existentes de RF-19.1 y RF-19.2 (004, 004b, 005, 008) se actualizan a este comportamiento, no se desactivan; e2e: tras quitar, el documento no aparece y el chat no lo cita.

## Dudas abiertas
- Ninguna sobre GG1 tras la respuesta de Andrés del 11/11/2026. Aprobado por Andrés el 11/11/2026. Falta el visto bueno del tutor para los cambios de RN-01, RNF-10 y la constitución.
- HH1 (aprobado por Andrés el 12/11/2026 con «sí a todo», tomando las propuestas): (a) el aviso se muestra siempre, no solo cuando el nombre está recortado; (b) en una fuente Procesado se conserva la segunda línea «haga clic para ver el archivo original»; (c) las otras listas quedan fuera de alcance.
- II1 (decidido por Andrés el 12/11/2026): Word y HTML con **vista de texto de Tika** (no fiel al original, sin servicio nuevo); Excel y otros formatos no permitidos quedan fuera.
- II1 (aprobado por Andrés el 12/11/2026 con «sí a todo», tomando las propuestas; incluye TIFF y la dependencia Pillow, RF-18.108): (a) límite de 200.000 caracteres para el texto; (b) el reproductor del navegador (barra, tiempo transcurrido y duración, `m:ss` y `h:mm:ss`) en vez de uno propio; (c) el audio se obtiene completo antes de abrir (sin streaming), con espera en audios muy grandes; (d) **TIFF**: lo incluí (RF-18.108) interpretando tu respuesta, pero exige agregar Pillow al backend (dependencia nueva y reconstruir la imagen): ¿lo apruebas o TIFF queda con «Vista previa no disponible»?; (e) cambia RF-18 del ERS, que hoy excluye el audio y Word.
- Decisiones confirmadas por Andrés en la aprobación (05/11/2026):
  1. identificadores mal formados en la selección → 422 (RF-11.105);
  2. la extensión se toma del nombre interno (Definiciones);
  3. el mensaje de vacío va sin punto final, como RF-17.81 (RF-19.106);
  4. al cargar no se comprueban duplicados de nombre (Casos límite, Fuera de alcance).

## Decisión del cambio «baja lógica de la fuente» (11/11/2026, Andrés: GG1)
- **GG1 = A** (opción intermedia): al quitar una fuente se conservan la fila con su nombre, tipo, fechas, quién y cuándo la quitó (baja lógica) y se eliminan el archivo y los fragmentos. Motivo: la auditoría necesita saber qué fuente fue, no solo que «algo» se quitó. Sustituye la parte de P6 que dejaba el borrado físico de la fila.

## Decisión del cambio «nombre completo de la fuente» (12/11/2026, Andrés: HH1)
- **HH1**: un aviso flotante con el nombre completo (en vez del atributo `title` del navegador, que tarda y no sale con teclado) en las fuentes de la lista y en las subidas en curso, y la etiqueta de subida recortada con «…» y el porcentaje siempre visible, para quitar la barra horizontal. Es solo de interfaz: sin servidor, bitácora, migración ni dependencias nuevas (el aviso es del propio HeroUI, RA-02.100).

## Decisión del cambio «vista previa de texto y audio» (12/11/2026, Andrés: II1)
- **II1**: todas las fuentes que se pueden agregar tienen vista previa: texto, audio (reproductor con barra de progreso, tiempo transcurrido y duración), Word y HTML (vista de texto de Tika) y TIFF (convertido, si se aprueba). Motivo: al abrir un `.txt` o un `.m4a` el usuario solo veía «Vista previa no disponible» y no podía verificar el original. Texto y audio son de interfaz; Word, HTML y TIFF necesitan una función nueva del servidor (la vista de texto reutiliza Tika, sin servicio nuevo). Sin migración; solo TIFF agrega una dependencia (Pillow) pendiente de aprobación. Excel no es un formato permitido y queda fuera.
