# Spec 005 — Red de seguridad de extremo a extremo (flujos en el navegador)
Estado: 005a implementada (aprobada por Andrés, 22/10/2026); 005b pendiente

> Retroactiva (skill `sdd`, «Specs retroactivas»): pruebas en el navegador escritas contra el ERS, sin cambiar el comportamiento de producción; el control y los simulados del backend viven en una carpeta de apoyo de pruebas, inactiva fuera de la instancia de pruebas (decisión 17). Lo que el sistema no cumple queda como **fallo esperado estricto** con su requisito y se corrige en otra spec.

Historial:
- 21/10/2026 — creada (fase 1, planner). Segunda mitad del paso 2 de `.claude/rules/testing.md` (la 004 cubrió la API con pytest).
- 21/10/2026 — Andrés responde las dudas 1-10 (decisiones 1-10).
- 21/10/2026 — QA del reviewer (cambios necesarios) y decisiones 11-16 de Andrés: control de pruebas enumerado (RA-02.49), RF-19 partido en tres, RT-07.40 retirado, el caso «servidor no responde» de RF-01.42 sale, nombres propios del entorno.
- 21/10/2026 — segunda QA (cambios leves) y decisiones 17-19 de Andrés: control en carpeta de apoyo de pruebas del backend, solo en 127.0.0.1; puertos de RF-11.42 sin fallo esperado; preparación con límite de 5 min. Resultado por clase en RF-02.41.
- 21/10/2026 — Andrés (opción B): el plan puede ajustar el límite de 5 min de la preparación con justificación y su aprobación (RA-02.47, decisión 19).
- 21/10/2026 — aprobada por Andrés (fase 2 cerrada). Fase 3: `plan-005a.md` y `tasks-005a.md`; la 005b, después de validar la 005a.
- 22/10/2026 — 005a implementada: @reviewer APROBADO (vuelta 1) y aprobación de Andrés (opción A); la 005b sigue pendiente.

## Contexto y objetivo
La 004 protege los flujos críticos hasta la API; lo que se ve en el navegador no tiene ninguna prueba automatizada. Esta spec:
- prueba en el navegador, con los dos roles, en escritorio y en pantalla pequeña, los flujos críticos: acceso y roles; carga → Procesado → el chat lo cita; NotebookServIA;
- cierra las exenciones que esperaban a la 005: **E2** de la 003 (cuatro pantallas) y la **presentación del bloque F** de la 004 (RF-05.23, RF-22.1, RNF-04.1);
- crea la infraestructura de extremo a extremo, aislada del entorno de desarrollo y del de pytest.

Al cerrar la 005b queda cerrado el paso 2 y pueden empezar las funciones nuevas y las specs retroactivas por módulo.

## Trazabilidad
- ERS V1.7: RF-01, RF-02, RF-03, RF-05, RF-11, RF-12, RF-16, RF-17, RF-18, RF-19, RF-21, RF-22, RNF-04, RNF-07, RNF-09, RA-02. Del ERS V1.8 (borrador de la 004b, sin exportar) sale solo el texto de RF-19.42.
- CU: CU-01 (p. 1, 4, 8; FA-02, FE-01, FE-02), CU-02, CU-03 (FE-02), CU-04, CU-05, CU-07 (FA-01, FE-05), CU-09 (p. 5-6; FA-05, FE-01, FE-02, FE-03), CU-11, CU-12 (p. 2; FA-01, FE-01), CU-13 (p. 2-4; FA-01, FE-01), CU-15 (FA-01).
- Pendientes que recoge (el origen va en cada requisito): E2 de la 003; bloque F y «fuera de alcance» de la 004 (permisos por página, menú, panel obligatorio, streaming, RF-16, consola); extremo a extremo de la 004a y la 004b.
- «Estado actual» que cierra (005b): los tres «pendiente la verificación de extremo a extremo (spec 005)» de RF-05, RF-22 y RNF-04; en RA-02, «El extremo a extremo llega con la spec 005».

Numeración: bloque `.40`-`.49` (no usado por ninguna spec anterior).

## Partición: 005a y 005b
Un solo documento del QUÉ; dos planes y dos listas de tareas, en orden (decisión 1).

| | 005a (~10 tareas) | 005b (~9 tareas) |
|---|---|---|
| Secciones | A (infraestructura), B (acceso y roles), C (pantallas de E2) | D (carga), E (chat), F (notebooks), G (bitácora) |
| Entrega | la instancia de pruebas, todos los simulados y el control de RA-02.49 con todas sus capacidades, la lista de páginas (RA-02.48) y el comando con sus límites | solo pruebas; si necesita una capacidad nueva, su plan la agrega sin romper la 005a |
| Cierra | E2 de la 003 | bloque F de la 004, los tres «Estado actual» y el paso 2 |

RA-02.45 y RA-02.46 rigen en las dos. La 005b empieza cuando la 005a está validada.

## Usuarios
Usuario Gubernamental, Administrador y visitante sin sesión. Las pruebas usan solo usuarios `PRUEBA` que la suite crea. El usuario B `PRUEBA` y los notebooks `PRUEBA 004b A/B` de desarrollo son solo para la verificación manual.

## Historias de usuario
- HU-01 (RF-01.43), HU-02 (RF-02.40), HU-03 (RF-03.41), HU-26 (RF-03.41, RF-21.40), HU-05 (RF-05.40), HU-11 (RF-11.40), HU-12 (RF-11.40, cita real), HU-16 (RF-16.40), HU-17 (RF-17.40), HU-18 (RF-18.40), HU-19 (RF-19.40 a RF-19.42), HU-22 (RF-21.40 a RF-21.42, RF-22.40), HU-24 (RF-01.44), HU-25 (RF-02.42, RF-03.40).
- HU-NUEVA (solo de desarrollo, no va al documento): como desarrollador, quiero que una prueba en el navegador me avise si un cambio rompe el acceso, la carga, el chat o los notebooks tal como los ve el usuario.

## Definiciones
- **Instancia de pruebas**: un backend y un frontend que la suite levanta en puertos propios sobre un entorno aislado con nombres propios (base y colección `servia_pruebas_e2e`, almacén de archivos temporal, simulados), distinto del de desarrollo y del de pytest (`servia_pruebas`).
- **Escritorio**: ventana de 1366 × 768. **Pantalla pequeña**: 616 px CSS de ancho (medida de la 004a y la 004).
- **Accesible a 616 px**: al desplazarse hasta el elemento (también en horizontal), queda dentro de la ventana y es él quien recibe un clic en su centro.
- **Sin diferencia de diseño**: la prueba solo navega por dirección y comprueba a qué página llega, sin pulsar ni leer controles que otra prueba no cubra ya a 616 px. Corre solo en escritorio (RF-02.41 y RA-02.48).
- **Fallo esperado estricto**: prueba marcada con la anotación «<requisito> · <módulo>» (como la 004, sin rutas); si pasa, la corrida falla. Se marca solo tras verla en rojo.
- **Carga mixta**: un archivo válido, uno vacío y uno de nombre no válido (la de la 004, RF-05.22).

## Requisitos funcionales
Todas son pruebas de extremo a extremo salvo que se diga otra cosa. Cada flujo corre en escritorio y a 616 px, salvo los sin diferencia de diseño (RA-02.46), y exige consola limpia (RA-02.45).

### A. Infraestructura (RA-02, RNF-09) — 005a
- **RA-02.40** `[NUEVO]`: CUANDO se ejecuta el comando de extremo a extremo, EL SISTEMA prepara y levanta la instancia de pruebas, corre las pruebas, la apaga e informa cuántas pasan, fallan y son fallos esperados.
  - SI no se recolecta ninguna prueba, falla la preparación o un puerto de la instancia ya está ocupado, ENTONCES termina con error y dice el motivo.
- **RA-02.41** `[NUEVO]`: MIENTRAS corre la suite, EL SISTEMA no lee ni modifica la base, la colección, `uploads/` ni el Redis de desarrollo, ni la base y la colección de pytest; el backend y el frontend de desarrollo siguen respondiendo. SI el entorno aislado no está disponible, ENTONCES aborta antes de abrir el navegador.
  - El frontend de pruebas usa su propia dirección de la API, su propia dirección de sesión y su propio secreto de sesión, sin modificar la configuración local del frontend ni la compilación de desarrollo.
  - *Comprobación (suite)*: el backend de desarrollo responde antes y después de la corrida; todas las peticiones del navegador van a los puertos de la instancia (si alguna sale, la prueba falla y la nombra); con el entorno aislado no disponible, la suite aborta antes de abrir el navegador.
  - *Comprobación (manual, exenta de automatizar porque la suite no debe leer desarrollo)*: conteos de usuarios, temas, documentos, notebooks y bitácora, y puntos de Qdrant de desarrollo, iguales antes y después; la configuración local y la compilación de desarrollo del frontend, sin cambios de fecha ni contenido; el servidor de desarrollo del frontend responde; `docker compose ps` sin reinicios.
- **RA-02.42** `[NUEVO]`: las pruebas usan solo datos que la suite genera, con prefijo `PRUEBA`; cada prueba limpia lo que crea (usuarios, temas, documentos, fragmentos, archivos, notebooks, conversaciones, filas de bitácora); residuos en cero al terminar, también corriendo una prueba sola o en otro orden.
  - Excepción: los temas escritos en Ingesta y en el chat acotado siguen el formato heredado que exige la interfaz (RF-06 «Estado actual»), sin prefijo; las claves `NB-<id>` tampoco lo llevan. La suite los registra al crearlos para que la limpieza los alcance (como la 004).
- **RA-02.43** `[NUEVO]`: las contraseñas de prueba se generan en cada corrida y solo viven en memoria. No aparecen en el código, la salida, los registros ni los artefactos (trazas, capturas, videos, informes). Ningún agente recibe contraseñas ni usa las de Andrés.
  - *Comprobación*: tras una corrida con un fallo provocado, se buscan las contraseñas generadas en todos los artefactos: cero coincidencias.
- **RA-02.44** `[NUEVO]`: lo que el sistema no cumple se marca como fallo esperado estricto. Si un fallo esperado pasa, la corrida falla y lo nombra.
- **RA-02.45** `[NUEVO]`: SI durante una prueba aparece en la consola un error o una excepción sin capturar no declarados, ENTONCES la prueba falla y muestra el mensaje. Se consideran declarados:
  - las respuestas 4xx/5xx que la propia prueba provoca (credenciales inválidas, recurso no disponible, fallo programado) y el aviso de carga de recurso que el navegador emite por ellas;
  - los errores de consola heredados que la interfaz emite en un flujo correcto o en un error provocado (p. ej., al fallar el inicio de sesión o al rechazar un archivo), en una única lista de la suite, cada uno con su motivo y la spec retroactiva que lo corregirá. No son fallos esperados; quitarlos de la lista es parte de esa corrección.
  - Las advertencias no cuentan.
- **RA-02.46** `[NUEVO]` (RNF-04): cada flujo se ejecuta en escritorio y a 616 px, solo en Chrome; a 616 px los controles que el flujo usa son accesibles. Los flujos sin diferencia de diseño corren solo en escritorio.
- **RA-02.47** `[NUEVO]` (RA-01, RA-02): las pruebas duran en total como máximo 10 min y ninguna pasa de 60 s; sin pausas fijas: si un estado no llega, la prueba falla diciendo qué esperaba. Tiene su propio comando; su límite no suma al de RA-02.15.
  - La preparación (compilar el frontend de pruebas, levantar la instancia, precalentar el modelo de embeddings) queda fuera de los 10 min, con su propio límite de 5 min (decisión 19), que el plan mide y puede ajustar con justificación, con la aprobación de Andrés del plan.
- **RA-02.48** `[NUEVO]` (como RA-02.12): la suite tiene la lista de las direcciones de la interfaz, escrita desde el ERS, cada una en una clase:
  - **pública**: «Inicio de sesión» y la recuperación de contraseña, abiertas sin sesión;
  - **por rol**: cada página con el rol que puede abrirla;
  - **grupo sin página**: los prefijos de grupo del control de acceso que no tienen página propia (Administración, Búsqueda y Consulta); con cualquier rol, no muestran contenido de otro rol;
  - **inexistente**: una dirección inventada; con sesión no muestra contenido protegido.
  - El resultado esperado de cada clase con sesión está en RF-02.41.
  - SI aparece una página sin clasificar o la lista nombra una que no existe, ENTONCES la prueba falla y la nombra.
- **RA-02.49** `[NUEVO]`: la instancia de pruebas ofrece a la prueba un control propio, activo solo cuando el backend arranca con la configuración de la instancia; el backend de desarrollo, aunque ejecuta el mismo código, no lo ofrece.
  - El control y los simulados viven en una carpeta de apoyo de pruebas del backend y no cambian el comportamiento de producción (decisión 17).
  - El control y el puerto de la instancia escuchan solo en el equipo local (127.0.0.1), porque el control crea usuarios y filas.
  - Capacidades y requisito que las usa:
  - motor: responder citando el archivo recibido (RF-11.40, RF-11.43); retener la respuesta para ver etapas y texto parcial (RF-11.40); programar una secuencia, p. ej. vacío y luego respuesta (RF-11.41); fallar por conexión (RF-11.42); no emitir ningún dato (RF-16.40);
  - ingesta: procesar con el HTR o el audio simulados; hacer fallar o retener el procesamiento de un documento (RF-18.40);
  - notebooks: retener la entrega del archivo para la vista previa (RF-18.40); retener la eliminación de un documento y hacerla fallar (RF-19.41, RF-19.42);
  - recuperación: leer el código del correo simulado y programar su fallo (RF-02.42, RF-03.40, RF-03.41); hacer no disponible el almacén temporal y avanzar el reloj del servidor (RF-03.41);
  - datos: crear usuarios `PRUEBA` con la contraseña que genera la suite, también temporal (RF-01.43 y todos); crear filas de bitácora de cada tipo, incluidas la carga cancelada, con error y «Gestionar Conversación» (RF-22.40, RF-21.41); contar y limpiar residuos (RA-02.42);
  - consultar si los simulados están activos (RNF-09.40).
  - *Comprobación (suite)*: el control pedido al backend de desarrollo responde 404; al apagar la instancia, su puerto rechaza la conexión. *Comprobación (manual)*: la configuración del backend de desarrollo no activa el control.
- **RNF-09.40** (RNF-09, RT-02): ninguna prueba llama al modelo de lenguaje, al HTR, al audio ni al correo reales; la suite comprueba por el control que los simulados están activos antes de empezar (como RA-02.6).
  - El navegador no hace ninguna petición fuera de los puertos de la instancia (comprobación de RA-02.41).
  - Se usa el Chrome instalado (no se descargan navegadores) y la compilación del frontend de pruebas no envía telemetría.

### B. Acceso y roles (RF-01, RF-02; CU-01..03) — 005a
- **RF-01.40** (RF-02 «Control en la interfaz»; CU-01 p. 1): SI un visitante sin sesión abre una página protegida, ENTONCES el sistema lo dirige a «Inicio de sesión» y, tras autenticarse, lo devuelve a la página pedida.
- **RF-01.41** (RF-01 «Salida»; CU-01 p. 8): CUANDO un usuario Activo de cada rol inicia sesión con credenciales correctas, el sistema lo dirige a la página de inicio con el menú de su rol.
- **RF-01.42** (RF-01; CU-01 p. 4, FE-01, FE-02):
  - SI el correo no existe, la contraseña no coincide o la cuenta está Inactiva, ENTONCES muestra «Credenciales inválidas», idéntico en los tres casos, sin sesión.
  - SI falta un dato, ENTONCES muestra «El correo electrónico es obligatorio» o «La contraseña es obligatoria» y no envía la solicitud.
  - SI el correo no tiene formato válido, ENTONCES muestra un mensaje en español y no envía la solicitud.
- **RF-01.43** (RF-01; CU-01 FA-02): CUANDO inicia sesión una cuenta con contraseña temporal, el sistema abre el panel «Cambio de Contraseña Obligatorio», que no se cierra (Escape, clic fuera) y no deja abrir ninguna otra página.
  - Tras cambiarla (temporal, nueva y confirmación), el usuario continúa en la página de inicio y el siguiente inicio de sesión no muestra el panel.
  - SI la temporal es incorrecta, la nueva tiene menos de 8 caracteres o es igual a la actual, o la confirmación no coincide, ENTONCES muestra un mensaje en español y el panel sigue abierto.
- **RF-01.44** (RF-01 «Al cerrar la sesión»; CU-02): CUANDO cierra sesión desde su menú de usuario, el sistema muestra «Inicio de sesión», y ni el botón Atrás ni la dirección directa vuelven a mostrar una página protegida.
  - *Comprobación*: tras Atrás o la dirección, la prueba espera «Inicio de sesión»; falla si no llega o si, ya en ella, se ve el menú del rol o contenido de la página protegida. Un destello previo de la página en caché no cuenta.
- **RF-02.40** (RF-02 «Control en la interfaz»): MIENTRAS hay sesión, el menú lateral y las tarjetas de inicio muestran solo las opciones del rol:
  - Administrador: «Inicio» y «Administración» («Usuarios del Sistema», «Historial de Actividades»);
  - Usuario Gubernamental: «Inicio», «Búsqueda y Consulta» («Asistente Virtual», «Temas Similares»), «Ingesta de Datos» y «NotebookServIA».
- **RF-02.41** (RF-02, RN-03; CU-03 FE-02): SI un usuario escribe la dirección de una página de otro rol, ENTONCES el sistema no la muestra y lo dirige a la página de inicio. Recorre toda la lista de RA-02.48 con cada rol (sin diferencia de diseño).
  - Resultado con sesión, por clase: página de otro rol → no la muestra y dirige a inicio; grupo sin página e inexistente → sin contenido protegido (no se exige redirección); pública → excluida, porque el ERS (RF-02, CU-03) no define su comportamiento con sesión.

### C. Pantallas de la exención E2 (003a, 003b) — 005a
Retira E2: el texto exacto ya lo cubren las integraciones de la 003; aquí se prueba que la pantalla lo presenta tal cual.
- **RF-02.42** (RF-02.2; CU-05): CUANDO el Administrador crea una cuenta, la pantalla muestra el texto de éxito de la API; con el correo simulado en fallo, muestra la advertencia de la API, distinta del aviso de éxito, y la cuenta aparece en la lista.
- **RF-03.40** (RF-03.15; CU-05): en «Resetear Contraseña», el cuadro explica que se enviará una contraseña temporal; en éxito muestra el texto de la API; con el correo en fallo, el cuadro sigue abierto con el texto de la API y la sesión sigue activa.
- **RF-03.41** (RF-03.23 a-g; CU-04): en las pantallas de la recuperación:
  - correo registrado, no registrado e Inactivo muestran la misma pantalla con el mensaje uniforme como aviso informativo (no de éxito), sin afirmar que el código se envió, y avanzan al paso de verificación;
  - ninguna pantalla afirma ni niega que la cuenta existe (ni «Email no registrado» ni «Demasiados intentos»);
  - código incorrecto, código vencido, almacén temporal no disponible: el mensaje de la API, opción de reintentar, sin «Sesión expirada» ni redirección; tras cinco intentos, el mensaje de RF-03.9;
  - con el código leído del correo simulado (nunca de lo que recibe el navegador) define la nueva contraseña, que sirve para iniciar sesión.
  - Por los límites de RF-03 (una solicitud por minuto y cinco por hora por correo), cada flujo usa su propio usuario `PRUEBA`.
- **RF-21.40** (RF-21.6, RF-21.3; RF-22; CU-15 FA-01): en «Historial de Actividades», el detalle de una creación de cuenta y de un reseteo muestra «Entregada» o «No entregada»; el de una recuperación, su paso y su resultado; filtrar por tipo trae también las recuperaciones sin usuario asociado.

### D. Carga y archivos rechazados (bloque F de la 004) — 005b
- **RF-05.40** (cierra RF-05.23; CU-07 FA-01, FE-05): con la carga mixta, en Ingesta y en un notebook propio:
  - aviso con el motivo de cada rechazado tal cual y la confirmación con solo los aceptados; ningún texto con el nombre no válido;
  - los rechazados nunca muestran «procesando»; el aceptado llega a Procesado;
  - ningún aviso de éxito ni de subida iniciada antes de la respuesta; con todos rechazados, ninguno;
  - una imagen pegada y otra arrastrada sobre el chat del notebook son aceptadas, con la misma confirmación, y llegan a Procesado (HTR simulado).
  - Dos temas en un mismo «Guardar»: solo verificación manual (decisión 13).
- **RF-22.40** (cierra RF-22.1; CU-15 FA-01): el Administrador abre el detalle de un registro de cada tipo de carga (tabla de RF-22.1 de la 004): nombre visible del tipo, etiquetas en su orden, sin etiquetas vacías, «Expediente», «N/A», «Task» ni datos técnicos; la carga rechazada sin nombre ni tema; encabezado «Tema» o «Sin tema asociado». Las filas las crea el control.
- **RNF-04.40** (cierra RNF-04.1): a 616 px, el aviso de RF-05.40 y el detalle de RF-22.40 son accesibles y su texto completo es visible al desplazarse. El aspecto visual sigue siendo manual (principio 4).

### E. Chat (RF-11, RF-12, RF-16; CU-09) — 005b
- **RF-11.40** (RF-11, RF-12; CU-09 p. 5-6): CUANDO el Usuario Gubernamental pregunta (general y acotado a un tema) por un documento Procesado:
  - con la respuesta retenida, la pantalla muestra las etapas («Procesando consulta», «Analizando documentos», «Generando respuesta») y texto parcial antes del final;
  - la respuesta muestra el nombre del archivo citado; al pulsarlo descarga el original, idéntico byte a byte;
  - acotado al tema A, una pregunta por la frase del tema B no cita el archivo de B.
- **RF-11.41** (RF-11 «Manejo de errores»; CU-09 FE-01): SI el motor no devuelve texto, ENTONCES el sistema reintenta una sola vez mostrando «Reintentando obtener respuesta...» y presenta la respuesta del segundo intento. SI el segundo también llega vacío, ENTONCES muestra un error en la conversación con el control de envío disponible.
- **RF-11.42** (RF-11; CU-09 FE-03; RF-11.2 de la 004): SI no se puede conectar con el motor, ENTONCES muestra en la conversación «Error de Conexión» con al menos una posible causa, en español y sin el texto de la excepción, y el control de envío queda disponible.
  - Hoy el mensaje nombra puertos del servidor: no lo prohíbe el ERS, así que no es fallo esperado aquí; queda como hallazgo para la retroactiva de chat (decisión 18).
- **RF-11.43** (RF-11; CU-09 FA-05): en el chat de un notebook, el campo empieza por «Preguntale algo a "<nombre del notebook>"» (comprobación por prefijo) y las respuestas citan solo documentos de ese notebook (pregunta por la frase de otro notebook del mismo usuario: no lo cita).
- **RF-16.40** (RF-16; CU-09 FE-02): SI pasan 30 s sin recibir datos (desde el inicio o tras el último fragmento), ENTONCES el control de envío se libera, el texto recibido se conserva y aparece «Se perdió la conexión con el servidor. Intentá de nuevo.». Antes de los 30 s el control sigue bloqueado.
  - La prueba controla el reloj del navegador solo en esa prueba (decisión 7): no espera 30 s reales.

### F. NotebookServIA (RF-17..19, RNF-07; CU-11..13) — 005b
- **RF-17.40** (RF-17; CU-11): CUANDO crea un notebook con nombre (botón o Enter), aparece primero en la lista y se abre con «Subir documentos», su lista y el chat. SI el nombre está vacío, ENTONCES no se crea y la lista no cambia. Otro usuario no lo ve en su lista.
- **RF-18.40** (RF-18; CU-12 p. 2, FA-01, FE-01): CUANDO pulsa un documento Procesado (imagen y PDF), aparece «Abriendo…» sobre el documento mientras se obtiene el archivo y luego una ventana con su nombre y el contenido en línea.
  - *Comprobación*: sin evento de descarga ni pestaña nueva, y la ventana contiene el visor (imagen o documento incrustado); no se inspecciona el contenido del PDF.
  - Un documento Pendiente o con Error no se abre (CU-12 FA-01); con un tipo sin vista previa, la misma ventana lo indica (FE-01).
- **RF-19.40** (RF-19; CU-13 p. 2-3, FA-01): CUANDO pulsa la «x» de un documento, el sistema pide confirmar con su nombre y la advertencia de que no puede deshacerse; si cancela, nada cambia.
  - *Estado actual* (ERS): se elimina sin confirmación → fallo esperado «RF-19.40 · notebooks».
- **RF-19.41** (RF-19; CU-13 p. 4): CUANDO quita un documento, este aparece deshabilitado mientras dura la operación, luego deja de listarse y el chat del notebook ya no lo cita. Debe pasar hoy.
- **RF-19.42** (RF-19.30 de la 004b; CU-13 FE-01): SI quitar falla, ENTONCES aparece «No se pudo quitar el documento. Intente de nuevo.» (ERS V1.8) y el documento sigue listado; un nuevo intento sin el fallo lo quita.
- En las pruebas que pulsan la «x» (RF-19.41, RF-19.42, RNF-07.40), si aparece la confirmación, la prueba la acepta.
- **RNF-07.40** (RNF-07.30 de la 004b): SI una acción del notebook recibe la respuesta uniforme de no disponible (previsualizar o quitar un documento ya quitado desde otra pestaña), ENTONCES la sesión sigue abierta y la pantalla sigue operable. El aviso al quitar es el de RF-19.42; el aviso al previsualizar queda para la retroactiva de notebooks (decisión 12).

### G. Bitácora (RF-21, RF-22) — 005b
- **RF-21.41** (RF-21.34 de la 004b): «Historial de Actividades» muestra «Crear Notebook», «Quitar Documento de Notebook» y «Gestionar Conversación» con su nombre (no «Acción 16») y su filtro los ofrece y filtra. Las filas las crea el control.
- **RF-21.42** (RF-21; RF-22): cada prueba ejecuta con un Usuario Gubernamental `PRUEBA` su propio flujo (inicio de sesión, carga, consulta, crear notebook o quitar documento) y luego el Administrador encuentra esa acción en «Historial de Actividades» con su usuario y tipo, sin contraseñas. Ninguna depende de otra.

## Requisitos no funcionales
RNF-09.40, RNF-04.40, RNF-07.40 y los de la sección A. Los textos en español (RT-07) se comprueban con los textos exactos de cada requisito.

## Casos límite
- Prueba cortada a la mitad: la siguiente corrida empieza con residuos en cero (RA-02.42).
- Corrida anterior sin apagar o puerto ocupado: RA-02.40.
- Fallo con traza, captura o video guardados: RA-02.43.
- Error de consola heredado que se corrige: se quita de la lista declarada (RA-02.45).

## Fuera de alcance
- Corregir lo que falle (fallos esperados → specs retroactivas), salvo un ajuste de configuración que la instancia necesite sin cambiar comportamiento (lo justifica el plan).
- RF-01.42 con el servidor caído (hoy muestra «Credenciales inválidas»): retroactiva de autenticación (decisión 11). También la inactividad de una hora, la renovación automática y el token aceptado tras cerrar sesión.
- El aviso al previsualizar un documento no disponible: retroactiva de notebooks.
- RF-13, RF-14, RF-15, RF-20, RF-23, RF-04 y la exportación de la bitácora: specs retroactivas.
- RNF-05: Firefox y Edge quedan sin verificar; el ERS no cambia por esta spec.
- Calidad real de la respuesta y la cita y el modelo real (verificación manual con Ollama); aspecto visual (manual); entrega real al buzón; rendimiento (RNF-01); integración continua.

## Decisiones (Andrés, 21/10/2026)
Restricciones para los planes; los detalles técnicos los fija cada plan.
1. Partición en 005a y 005b (sección «Partición»).
2. Playwright en Windows, como dependencia de desarrollo del frontend, con el Chrome instalado. Backend de pruebas: un segundo proceso dentro del contenedor del backend.
   - `docker-compose.yml`: solo se autoriza publicar un puerto más en el servicio del backend, enlazado a 127.0.0.1.
   - La dependencia nueva (principio 1) y los archivos nuevos quedan aprobados; el plan los marca con ⚠️ igualmente.
3. Frontend de pruebas: compilación de producción en una carpeta de salida propia, servida en otro puerto; no pisa la compilación ni el servidor de desarrollo.
4. Motor de lenguaje simulado en toda la suite; el real, solo en la verificación manual. HTR, audio y correo simulados; el correo entrega el código a la prueba.
5. Límite propio: 10 min y 60 s por prueba, con comando aparte (RA-02.47).
   - **5b**: desde el cierre de la 005a, la «suite completa» de toda tarea que toque el frontend o la API incluye el extremo a extremo. Regla permanente: se propone para `CLAUDE.md` y `.claude/rules/testing.md`.
6. Fallo esperado estricto con la anotación «<requisito> · <módulo>» (RA-02.44).
7. RF-16 con el reloj del navegador controlado por la prueba (RF-16.40).
8. Escritorio 1366 × 768 y 616 px, solo Chrome (RNF-05 fuera).
9. RF-18.40 y RF-21.42 entran, en la 005b.
10. Almacén temporal (Redis) simulado dentro del proceso del backend de pruebas; la ingesta se procesa en ese proceso, fuera del bucle de la petición, sin worker de Celery ni servicios nuevos. El worker real se comprueba solo en la verificación manual.
11. (Q1 = C) RF-01.42 sin el caso «servidor no responde»: pasa a la retroactiva de autenticación.
12. (Q2 = A) Alcance de RNF-07.40 (ver el requisito).
13. (Q3 = B) «Dos temas en un mismo Guardar», solo manual (RF-05.40).
14. (Q4 = C con A) La preparación queda fuera de los 10 min, con su límite propio (RA-02.47); los flujos sin diferencia de diseño corren solo en escritorio.
15. (Q5 = A) Base y colección propias (`servia_pruebas_e2e`), distintas de las de pytest.
16. (Q6 = A) RF-19 en tres requisitos (RF-19.40 a RF-19.42).
17. (N3 = A) El control de pruebas y los simulados viven en una carpeta de apoyo de pruebas dentro del backend, inactiva salvo con la configuración de la instancia de pruebas; no cambian producción (RA-02.49).
18. Los puertos que nombra el mensaje de RF-11.42 no son fallo esperado en la 005: hallazgo para la retroactiva de chat.
19. La preparación tiene un límite de 5 min, que el plan puede ajustar con justificación y la aprobación de Andrés (RA-02.47).

### Riesgos para los planes
- **Memoria y CPU**: dos procesos del backend en un contenedor (el recargador de desarrollo ya murió por memoria). El plan mide la memoria del contenedor antes y durante la corrida; condición: sin reinicios ni eventos de falta de memoria.
- **Configuración del frontend de pruebas**: la dirección de la API se fija al compilar; si se toma la de desarrollo, las pruebas tocarían desarrollo (RA-02.41, RNF-09.40).
- **Reloj del navegador** (RF-16.40): puede adelantar la sesión de NextAuth, los avisos con tiempo y el sondeo de la ingesta. Se instala solo en esa prueba, tras iniciar sesión, y se avanza lo justo para cruzar el plazo de inactividad del streaming (constante `STREAM_INACTIVITY_TIMEOUT_MS`).
- **RF-19.42** depende del ERS V1.8, sin exportar ni visto bueno del tutor: si el texto cambia, cambia la prueba.
- **Hook de terminal**: `validate-bash.sh` no permite hoy el comando de Playwright ni arrancar el segundo proceso del backend. Lo ajusta Andrés antes de la tarea que lo necesite (los agentes no tocan `.claude/`); ⚠️ «Pregunta antes».

## Criterios de finalización
- Cada requisito con prueba de extremo a extremo que pasa o fallo esperado estricto etiquetado. Exenciones (en el plan): calidad del LLM, aspecto visual, entrega real del correo y las comprobaciones manuales de RA-02.41 y RA-02.49.
- La suite de extremo a extremo pasa dentro de RA-02.47, con residuos en cero, sin tocar desarrollo; `docker compose exec backend pytest` sigue pasando.
- Verificación manual de punta a punta con Ollama real y el worker real, los dos roles, escritorio y 616 px; Andrés inicia la sesión y no da contraseñas a los agentes.
- Documentación al cierre (la edita otro, no el planner):
  - 005a: retirar E2 en las specs 003, 003a y 003b; definición del entorno aislado de la 002 y su mención en `CLAUDE.md` (dos entornos: `servia_pruebas` y `servia_pruebas_e2e`); `CLAUDE.md` («Comandos»: el comando de extremo a extremo); la regla 5b en `CLAUDE.md` y `.claude/rules/testing.md`, si Andrés la aprueba; `graphify-out/mapa_pruebas.md` y su generador, para cubrir las pruebas de extremo a extremo; `MEMORY.md`.
  - 005b: ERS (quitar los tres «Estado actual» de la 005 en RF-05, RF-22 y RNF-04; RA-02; los requisitos con fallo esperado, a su «Estado actual»); retirar la exención temporal en la 004; `CLAUDE.md` («Verificación») y `.claude/rules/testing.md` (paso 2 cerrado); `MEMORY.md`.

## Dudas abiertas
Ninguna sobre los requisitos. Pendientes aparte de la 005a (22/10/2026):
- El recuento `contar_residuos_e2e` de `backend/tests/instancia_e2e/control.py:163-171` no tiene reintento: una excepción ahí sale como 500 sin `detail`.
- La causa real del 500 de `/limpiar` sigue sin confirmarse; si reaparece, revisar `/tmp/servia_e2e/instancia.log`.
