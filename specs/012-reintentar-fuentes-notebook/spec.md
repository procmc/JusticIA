# Spec 012 — Reintentar una fuente que falló en NotebookServIA (y corregir el segundo audio)
Estado: implementada el 20/11/2026 por pedido directo de Andrés («solamente impleméntela»); pruebas del reintento (7), del audio (2) y de extremo a extremo pasan; la suite completa del backend y la verificación manual del reintento con un audio quedan pendientes.

## Contexto y objetivo
- Hallazgo de Andrés (20/11/2026) al capturar el manual: una fuente de un notebook queda en rojo (Error) y no hay forma de reprocesarla; solo se puede quitar y volver a subir. Ingesta de Datos sí tiene «Reintentar» (spec 006, RF-06.50), pero solo mientras el archivo sigue en la memoria del navegador.
- Esta spec agrega «Reintentar» a las fuentes en Error de un notebook: el sistema vuelve a procesar el archivo original que ya tiene guardado, sin pedir subirlo otra vez.
- El caso que lo motivó es un audio (mp3) que falló sin que el archivo tuviera culpa: el servicio de transcripción borra su modelo de Whisper al terminar el primer audio y el siguiente audio del mismo servicio falla («'DirectTranscriptionStrategy' object has no attribute 'whisper_model'»). Sin corregirlo, reintentar ese audio volvería a fallar, así que la corrección va en esta misma spec.
- Función de varios módulos (procesamiento, notebooks, bitácora): las pruebas siguen al ERS y los requisitos existentes de cada módulo siguen pasando (testing.md, paso 3). La parte B es una corrección: primero la prueba que falla y después el código.
- Presupuesto estimado: **~6,5 h** (rango 5-8 h): spec, plan y tareas ~1 h; backend ~1,5 h; interfaz ~1 h; pruebas (unitarias, integración y e2e) ~2 h; verificación manual ~0,5 h; documentación, memoria y grafo ~0,5 h.

## Trazabilidad
- ERS: RF-07 (seguimiento y manejo de errores; «Estado: Parcial»), RF-17 (notebooks), RF-19 (documentos del notebook), RF-21 (bitácora), RN-01 y RNF-10 (conservación de datos), RNF-07.24 (la bitácora no guarda nombres de documentos ni de notebooks), RNF-04 (diseño adaptable).
- HU-07 y HU-19 · CU-07 y CU-13.
- «Estado actual» que cierra: ninguno por completo; agrega a RF-07 el reintento de una fuente de notebook y deja constancia de la corrección del audio.
- Bloque de numeración: **RF-07.60+**. `[NUEVO]` marca un requisito que pide texto nuevo en el ERS.

## Usuarios
- Usuario Gubernamental: dueño del notebook; reintenta sus fuentes.
- Administrador: no entra a NotebookServIA (RN-03); lo cubren las pruebas de acceso existentes.

## Historias de usuario
- HU-07 y HU-19 (existentes).
- HU-NUEVA-9. Como Usuario Gubernamental, quiero reintentar una fuente de mi notebook que falló al procesarse, para no tener que subirla de nuevo.

## Definiciones
- **Fuente en Error:** documento de un notebook cuyo procesamiento terminó mal (RF-07). La interfaz la muestra en rojo.
- **Archivo original:** el archivo que el usuario subió, que el sistema conserva en disco cuando el procesamiento falla.

## Requisitos funcionales

### A. Reintentar una fuente en Error (RF-07)
- **RF-07.60** `[NUEVO]` (D1 = solo en Error; RF-07 «Manejo de errores»): MIENTRAS una fuente de un notebook está en estado Error, EL SISTEMA ofrece en su menú de opciones «Reintentar». En cualquier otro estado (en proceso o Procesado) no se ofrece.
- **RF-07.61** `[NUEVO]` (RF-07): CUANDO el Usuario Gubernamental elige «Reintentar» en una fuente en Error de su notebook, EL SISTEMA vuelve a procesar el archivo original ya guardado, con el mismo notebook y el mismo nombre, sin pedir que lo suba de nuevo. La fuente vuelve a «en proceso» con su porcentaje de avance (RF-07 «Seguimiento») y no se duplica en la lista.
- **RF-07.62** (RF-07, RF-11.106): CUANDO el reintento termina bien, EL SISTEMA deja la fuente en Procesado y utilizable en el chat y en el Estudio del notebook. SI el reintento falla de nuevo, ENTONCES vuelve a Error con su mensaje descriptivo y «Reintentar» sigue disponible.
- **RF-07.63** `[NUEVO]` (D2 = sin límite): EL SISTEMA no limita las veces que una fuente en Error puede reintentarse.
- **RF-07.64** `[NUEVO]` (RF-07, RN-01): CUANDO se reintenta, EL SISTEMA reutiliza el mismo registro del documento (no crea otro) y no deja fragmentos duplicados ni sobrantes de intentos anteriores en la búsqueda semántica (RF-08).
- **RF-07.65** `[NUEVO]` (RF-07): SI el archivo original ya no está en el disco, ENTONCES EL SISTEMA muestra «No se encontró el archivo original. Quite la fuente y vuelva a subirla.», no inicia el procesamiento y la fuente sigue en Error.
- **RF-07.66** `[NUEVO]` (RF-17, spec 004b): SI el notebook no es del usuario, no existe, o la fuente no pertenece a él, ENTONCES EL SISTEMA responde igual que en las demás acciones sobre fuentes de un notebook ajeno (404 uniforme), sin reprocesar nada.
- **RF-07.67** `[NUEVO]` (RF-07): MIENTRAS la fuente se reintenta, EL SISTEMA no permite cambiarle el nombre ni volver a reintentarla (RF-19.107); quitarla sigue permitido (RF-19). Un doble clic en «Reintentar» envía una sola solicitud.
- **RF-07.68** `[NUEVO]` (RF-07): SI el servidor no puede encolar el procesamiento, ENTONCES EL SISTEMA lo informa con un mensaje en español sin datos internos, y la fuente conserva su estado Error.

### B. Bitácora (RF-21)
- **RF-21.110** `[NUEVO]` (RF-21, RNF-07.24): EL SISTEMA registra en la bitácora cada reintento (el pedido y su resultado: completado o con error), con el usuario, la fecha y hora, la clave `NB-<id>` y el número del documento, sin nombres de documentos ni de notebooks. Los registros existentes no cambian (RN-01).

### C. Audio: varios audios seguidos (RF-07, corrección)
- **RF-07.70** (RF-07; corrección): CUANDO el sistema transcribe varios audios uno tras otro, EL SISTEMA transcribe cada uno con éxito: un audio ya procesado no deja al siguiente sin modelo.
- **RF-07.71** (RF-07; corrección): CUANDO se reintenta un audio que falló por el defecto anterior, EL SISTEMA lo deja Procesado.

## Requisitos no funcionales
- **RNF-03.60** (RNF-03): EL SISTEMA muestra en la fuente que se reintenta el mismo seguimiento visible de cualquier procesamiento (porcentaje y color), sin recargar la página.
- **RNF-04.60** (RNF-04): «Reintentar» se puede usar en 1366 px y en 616 px de ancho.
- **RNF-09.60** (RNF-09, Constitución 6): el reintento y la corrección del audio no envían datos a servicios externos ni cargan más de un modelo de transcripción a la vez, para caber en la memoria disponible.

## Casos límite
- Fuente en Error con el archivo original borrado: RF-07.65.
- Reintentar una fuente que otra pestaña ya está reprocesando: la solicitud se rechaza con un mensaje en español y no se duplica el trabajo (RF-07.67).
- Fuente que falla de nuevo con la misma causa: vuelve a Error; el usuario puede reintentar o quitarla.
- Quitar una fuente mientras se reintenta: el flujo de RF-19 sigue igual; el procesamiento en curso no deja fragmentos huérfanos (queda como cualquier otra fuente quitada mientras se procesa).
- Audio tras otro audio en el mismo servicio: RF-07.70.
- Fuentes en Error de otros tipos (PDF, imagen, texto): el mismo reintento de RF-07.61 aplica a todas.

## Fuera de alcance
- «Reintentar» en Ingesta de Datos: ya existe (RF-06.50) y no cambia.
- Reintento automático sin que el usuario lo pida, «Reintentar todas» o reintentar varias fuentes a la vez.
- Límite de reintentos (decisión D2: sin límite).
- Mejorar el motivo del error mostrado ni arreglar otras causas de fallo (HTR, Tika, memoria).
- Un botón de reintento para fuentes «Pendiente» que llevan mucho tiempo sin avanzar (decisión D1).
- Cambiar el modelo de Whisper o el tamaño con el que se elige transcripción directa o por fragmentos.

## Decisiones (entrevista con Andrés, 20/11/2026)
- **D1:** «Reintentar» solo aparece con la fuente en Error.
- **D2:** sin límite de reintentos (Andrés corrigió su primera respuesta); por eso no hay contador ni dato nuevo.
- **D3:** alcance = reintento + corrección del audio.
- **D4 (propuesta, a confirmar):** el trabajo va en la rama `optimizacion`; `fase4` queda como respaldo intacto.

## Decisiones tomadas al implementar (20/11/2026)
- **Sin migración:** el reintento usa el tipo de acción existente «Carga de documentos» con `accion = reintentar_documento` (RF-21.110); el resultado lo registra la propia tarea (inicio, completado o error). Alternativa descartada: un tipo de acción nuevo, que exigía migración.
- **Memoria del audio:** se quitó el `del self.whisper_model` de las dos estrategias. Quitar esa referencia no liberaba memoria (el servicio conserva la suya) y dejaba sin modelo a la estrategia que el servicio reutiliza.
- **Cómo se reutiliza la fila:** el servidor agrega `documento_reintento_id` a los datos de la tarea, que reutiliza el documento como en RF-07.51; antes del encolado se borran los fragmentos y la fuente pasa a Pendiente, y si el encolado falla vuelve a Error.
- **Códigos:** 409 si la fuente no está en Error o falta su archivo original; 404 uniforme para lo ajeno; 500 con mensaje fijo si falla el encolado.
- **Cambio vecino (RF-05.23):** el aviso de la carga en NotebookServIA se estiraba hasta llenar la columna de Fuentes; ahora mide lo que ocupa su texto (sin icono y con menos relleno). Prueba de extremo a extremo propia.
- Los dos servidores en marcha (backend y worker) no recargan solos en esta máquina: tras el cambio hay que reiniciarlos (`docker compose restart backend celery-worker`).

## Criterios de finalización
- Cada requisito tiene al menos una prueba automatizada que pasa (o su exención justificada en el plan) y su verificación manual.
- La suite completa pasa y los requisitos existentes de procesamiento, notebooks y bitácora siguen pasando.
- Verificación manual: subir dos audios seguidos a un notebook (ambos Procesado); provocar un Error (archivo original borrado o servicio caído), reintentar y ver el cambio de color; comprobar el registro en la bitácora con el Administrador.

## Pendiente
- Correr la suite completa del backend y el extremo a extremo de notebooks en las dos pantallas.
- Verificación manual: reintentar un audio en Error, comprobar la fila en la bitácora con el Administrador y la ficha en 616 px.
- Actualizar el ERS (RF-07 «Seguimiento» y «Manejo de errores», RF-21), la historia HU-NUEVA-9 y el caso de uso CU-13, y cerrar la spec.
