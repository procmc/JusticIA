# Spec 011 — Vocabulario «tema» en toda la interfaz (empezando por la Bitácora)
Estado: aprobada por Andrés el 12/11/2026 («creo que sí lo apruebo»), salvo RT-06.133 (textos del modelo), pendiente de su aprobación explícita; sin implementar. Alcance y decisiones de las preguntas 1 a 6 en «Decisiones».

## Contexto y objetivo
- Petición de Andrés: en la Bitácora del Sistema del Administrador, lo que se llama «expediente» debe llamarse «tema», y ampliarlo a **toda la interfaz**.
- El ERS ya lo pide así: RF-22 dice que la tabla muestra «el tema asociado», que se filtra por «tema» y que el encabezado del detalle dice «Tema» o «Sin tema asociado»; RF-23 habla de «los 5 temas más consultados»; RT-06 y la convención del proyecto fijan el vocabulario «tema». Lo que cambia es la pantalla, que se quedó atrás: es un «Estado actual» por cerrar, no un requisito nuevo.
- Solo cambia lo que **lee una persona**. Los nombres técnicos (campos de la base de datos, claves de los datos, parámetros y rutas de la API, nombres del código) no cambian: renombrarlos exige la confirmación del tutor (RT-06).
- Los registros que la Bitácora ya guardó no se tocan (RN-01: son inmutables); los que se creen desde ahora se escriben con «tema».
- Función de varios módulos (Bitácora, Ingesta, chat, Temas Similares, notebooks): las pruebas siguen al ERS y los requisitos existentes de cada pantalla siguen pasando (testing.md, paso 3).

## Trazabilidad
- ERS V1.14: RF-21 (registro automático), RF-22 (consulta y filtrado de la bitácora; «Estado: Parcial»), RF-23 (dashboard de métricas), RT-06 (vocabulario), RT-07 (idioma), RN-01 y RNF-10 (conservación de la información), RNF-07.24 (la bitácora no guarda nombres de documentos ni de notebooks), RNF-04 (diseño adaptable).
- HU-22 · CU-15 (consultar y filtrar la bitácora). Para el resto de pantallas: HU y CU de Ingesta, chat y búsqueda de temas similares, que ya dicen «tema».
- «Estado actual» que cierra: el vocabulario «expediente» que todavía muestran la Bitácora y otras pantallas. No hay requisitos del ERS que cambiar de contenido (ya dicen «tema»).
- Bloque de numeración: **.130+**.

## Usuarios
- Administrador: consulta la Bitácora y sus estadísticas (RF-22, RF-23).
- Usuario Gubernamental: ve el resto de pantallas (Ingesta de Datos, chat, Temas Similares, NotebookServIA, inicio y menú).

## Historias de usuario
- HU-NUEVA-7. Como Administrador, quiero que la Bitácora hable de «temas» como el resto del sistema, para no confundirme con un término que el proyecto abandonó.
- HU-NUEVA-8. Como Usuario Gubernamental, quiero que todas las pantallas llamen «tema» a lo mismo, para entender el sistema sin traducir.

## Definiciones
- **Tema**: la unidad con la que ServIA agrupa documentos; en Ingesta es un nombre libre y en un notebook es su clave interna (`NB-<número>`).
- **Texto visible**: rótulos, títulos, columnas, ayudas dentro de los campos, avisos, mensajes de error, textos de confirmación y la exportación a PDF.
- **Registro nuevo / ya guardado**: el que se crea desde que esta spec se aplique / el que ya existe en la Bitácora.

## Requisitos funcionales

### A. Bitácora del Administrador (RF-22)
- **RF-22.130** `[NUEVO]` (RF-22, RT-06): EL SISTEMA muestra en el filtro de la Bitácora el rótulo «Tema» y la ayuda «Nombre del tema», en lugar de «Expediente» y «Número de expediente».
  - El filtro sigue combinándose con los demás y acepta lo mismo que hoy (incluida la clave de un notebook, `NB-12`).
- **RF-22.131** `[NUEVO]` (RF-22): EL SISTEMA llama «TEMA» a la columna de la tabla; muestra el tema asociado del registro y «-» cuando no tiene.
  - Las acciones hechas en un notebook siguen mostrando su clave interna (`NB-12`), sin nombres (RNF-07.24).
- **RF-22.132** `[NUEVO]` (RF-22): EL SISTEMA etiqueta con «tema» todos los datos del detalle de un registro que hoy dicen «expediente»:
  - «Número de Expediente» → «Tema»; «Expediente» → «Tema»; «Expedientes» → «Temas»;
  - «Cantidad de Expedientes» → «Cantidad de temas»;
  - «Top Expedientes Encontrados» → «Temas encontrados (los más relevantes)».
  - El encabezado del detalle dice «Tema» o «Sin tema asociado» (ya lo pide RF-22).
- **RF-22.133** `[NUEVO]` (RF-22): CUANDO el Administrador exporta a PDF, EL SISTEMA usa «Tema» en las columnas, encabezados y filtros aplicados del documento, y ningún texto del PDF dice «expediente» salvo lo que contenga un registro ya guardado.
- **RF-22.134** `[NUEVO]` (RF-22): los avisos de la Bitácora (sin resultados, nada que exportar, error al consultar) no mencionan «expediente».

### B. Estadísticas (RF-23)
- **RF-23.130** `[NUEVO]` (RF-23): EL SISTEMA muestra en «Estadísticas»:
  - la tarjeta «Temas» (antes «Expedientes»);
  - el gráfico «Temas más Consultados» con la descripción «Top 5 de temas con más actividad» y, sin datos, «No hay datos de temas disponibles»;
  - la distribución del chat entre «Consultas Generales» y «Consultas por Tema» (antes «por Expediente»).

### C. Textos de los registros nuevos (RF-21)
- **RF-21.130** `[NUEVO]` (RF-21, RN-01): EL SISTEMA escribe con «tema» la descripción de todo registro nuevo que antes decía «expediente» (por ejemplo «Listado de archivos del tema: X», «Descarga de archivo: … (tema: X)», «Error listando archivos del tema: X»).
  - Los registros ya guardados no se modifican y la Bitácora los muestra tal como se guardaron.
  - Los datos que se guardan (el tema, sus valores y las claves internas) no cambian: filtros, estadísticas y exportación siguen funcionando igual con registros viejos y nuevos.

### D. El resto de la interfaz y los mensajes del servidor (RT-06, RT-07)
- **RT-06.130** `[NUEVO]` (RT-06, RT-07): EL SISTEMA no muestra al usuario las palabras «expediente» ni «Expediente» (ni «número de expediente») en ninguna pantalla: Ingesta de Datos (campo, lista de archivos y confirmación de la carga), chat (alcance, mensajes e historial), Temas Similares, NotebookServIA, inicio, menú y avisos. Se dice «tema», con género y número correctos (el tema, los temas).
- **RT-06.131** `[NUEVO]` (RT-06, RF-06): los mensajes de validación del tema dicen «tema» y no mencionan el formato heredado de número de expediente (`YY-NNNNNN-NNNN-XX`), que ya no aplica: «El tema es requerido», «El tema debe tener al menos <N> caracteres» y «El tema no debe exceder <M> caracteres», con el mínimo y el máximo vigentes.
- **RT-06.132** `[NUEVO]` (RT-06): los mensajes en español que el servidor devuelve y el usuario puede ver (por ejemplo «Formato de expediente inválido» o «Error actualizando el contexto del expediente») dicen «tema».
- **RT-06.133** `[NUEVO]` ⚠️ (RT-06; **cambia textos que se le dan al modelo: requiere la aprobación explícita de Andrés**): EL SISTEMA dice «tema» en lo que le entrega al modelo y que este puede repetir al usuario: el encabezado de cada documento en el contexto del chat («Expediente: …» y «Sin expediente») y las instrucciones y el formato del resumen de Temas Similares («el expediente», «Materia Jurídica del Expediente» en el resumen de respaldo).
  - Las instrucciones del chat de un tema y de un notebook ya dicen «tema» y no cambian.
  - Se prueba la estructura (el contexto trae «Tema: …»; el resumen conserva sus campos), no el texto exacto de las respuestas del modelo.

### Lo que no cambia
- Los nombres técnicos: tablas y columnas de la base de datos, claves de los datos guardados (por ejemplo, el campo que guarda el número de tema en cada registro), parámetros y rutas de la API, y nombres de archivos, funciones y variables del código (RT-06).
- Los registros ya guardados en la Bitácora y lo que digan los documentos cargados por los usuarios (su texto es de ellos).
- La documentación de planificación: ya dice «tema».

## Requisitos no funcionales
- **RT-07.130** `[NUEVO]` (RT-07): todo texto nuevo está en español, sin voseo, con la concordancia correcta.
- **RNF-04.130** `[NUEVO]` (RNF-04): los textos cambiados caben a 1366 px y a 616 px de ancho, sin desbordar ni quedar cortados, con la consola sin errores.
- **RNF-03.130** `[NUEVO]` (RNF-03): ningún mensaje deja de mostrarse o cambia de significado al cambiar la palabra.

## Casos límite
- Registros viejos con «expediente» conviven con registros nuevos con «tema» en la misma tabla, en el mismo PDF y en las mismas estadísticas.
- El filtro por tema acepta lo mismo de antes, incluida la clave de un notebook (`NB-12`).
- Un documento cargado cuyo texto dice «expediente» (por ejemplo, una demanda): se cita tal cual; es contenido del usuario y no se cambia.
- Un tema nuevo con la palabra «expediente» en su nombre (nombre libre): se muestra tal cual lo escribió el usuario.
- Un registro sin tema: la columna muestra «-» y el detalle dice «Sin tema asociado».
- Mayúsculas: «EXPEDIENTE» en un encabezado de tabla pasa a «TEMA».
- Plural y género: «expedientes más consultados» pasa a «temas más consultados»; «el expediente» a «el tema»; «del expediente» a «del tema».
- «Número de expediente» pasa a «Nombre del tema» o «tema» (un tema es un nombre, no un número) y no a «Número de tema».

## Fuera de alcance
- Renombrar tablas, columnas, claves de datos, parámetros y rutas de la API o nombres del código: requiere la confirmación del tutor (RT-06).
- Reescribir, ocultar o traducir al mostrarlos los registros ya guardados en la Bitácora (inmutables, RN-01).
- Cambiar el estilo o el contenido de las respuestas del modelo: solo cambia la palabra en lo que se le entrega (RT-06.133, sujeto a la aprobación de Andrés).
- Cambiar el comportamiento del filtro por tema, de la exportación o de las estadísticas: solo cambian las palabras.
- Mostrar un aviso cuando Ingesta de Datos descarta un archivo de formato no permitido (otra spec) o cambiar nombres de notebooks o documentos en la Bitácora (RNF-07.24).
- La documentación de planificación (ya dice «tema») y los nombres de carpetas de los archivos cargados.

## Criterios de finalización
- Cada requisito tiene al menos una prueba automatizada vista en rojo y luego en verde:
  - la Bitácora y sus estadísticas, con el Administrador, a 1366 y 616 px, sin «expediente» en ningún texto visible (rótulos, columna, detalle, avisos) y con la consola limpia;
  - el recorrido de las demás pantallas con el Usuario Gubernamental (Ingesta de Datos, chat, Temas Similares, notebooks, inicio y menú) sin «expediente»;
  - del servidor: los registros nuevos dicen «tema» y los ya guardados no cambian; los mensajes de la API dicen «tema».
- `pytest` (normal e inverso) y `npm run e2e` sin fallos nuevos ni XPASS; residuos 0.
- Verificación manual de Andrés (1366 y 616 px): recorrer la Bitácora (filtros, tabla, detalle de un registro de carga y de una consulta, estadísticas, exportar PDF) y el resto de pantallas, con el Administrador y el Usuario Gubernamental.
- Documentación: sin cambios en el ERS, las historias y los casos de uso (ya dicen «tema»); se cierra el «Estado actual» de RF-22 en lo del vocabulario.

## Dudas abiertas
- Ninguna. Decisiones de Andrés del 12/11/2026 abajo.

## Decisiones (12/11/2026, Andrés: preguntas 1 a 6)
1. **Alcance de los textos guardados:** pantalla **y** registros nuevos; los ya guardados siguen diciendo «expediente» (inmutables, RN-01).
2. **Estadísticas:** seguir el ERS («Temas», «Temas más Consultados», «Consultas por Tema»).
3. **Otras pantallas:** **toda la interfaz**, no solo la Bitácora.
4. **Prompts y mensajes del servidor:** sí los mensajes en español del servidor que el usuario ve. Sobre los prompts, la primera revisión (12/11) vio que los del chat ya dicen «tema» y se pensó no cambiar ninguno; al hacer el plan se encontró que **sí hay «expediente» en lo que le llega al modelo** (encabezado del contexto del chat e instrucciones del resumen de Temas Similares). Por eso se agregó RT-06.133, **pendiente de aprobación de Andrés**.
5. **Validación del campo del tema:** decir «tema» y quitar el formato heredado `YY-NNNNNN-NNNN-XX`.
6. **Notebooks:** la columna y el filtro dicen «Tema» y siguen mostrando la clave `NB-12` tal cual, sin cambiar lo que se guarda ni se filtra; los registros ya guardados quedan como están.
