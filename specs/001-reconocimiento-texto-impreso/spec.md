# Spec 001 — Reconocimiento de texto impreso (elección del modelo)
Estado: implementada

Historial: 05/10 — cambio 1 (aprobado): el set de prueba queda solo con capturas de pantalla (10 imágenes, ≥ 100 líneas), se acepta texto propio del proyecto y de terceros (este último sin versionar), y las fotos con celular quedan como límite documentado.

## Contexto y objetivo

RF-09 orienta el reconocimiento en imagen exclusivamente a texto impreso o tipeado en español. Sin embargo, en producción sigue el modelo elegido para **manuscrito** (`microsoft/trocr-large-handwritten`), entrenado en inglés: traduce palabras, borra las tildes y nunca se midió sobre texto impreso.

Para manuscrito en español no existía un modelo ya entrenado que sirviera; por eso quedó como limitación aceptada (RT-05, RF-10). Para texto impreso en español sí existen. El objetivo de esta spec es **encontrar, entre modelos ya entrenados, el que mejor lea páginas impresas en español**, medido con evidencia sobre capturas de pantalla reales, y dejarlo listo para integrar en ese caso.

Esta spec es solo la elección y su documentación. La integración al pipeline de ingesta (incluida la vectorización) es otra spec, que espera a la red de seguridad de pruebas (`.claude/rules/testing.md`, paso 2).

**Límites documentados**:
- **Escaneos**: esta medición no cubre documentos escaneados ni formularios tipeados escaneados, porque no hay escáner disponible.
- **Fotos con celular**: tampoco cubre fotos con celular, ni de páginas impresas ni de una pantalla. Andrés descartó las fotos tomadas a pulso.

RF-09 no cambia. Esta spec lo mide **solo en su caso «captura de pantalla»**; el documento impreso fotografiado y el formulario escaneado siguen dentro de su alcance, pero sin evidencia aquí.

## Trazabilidad
- ERS: RF-09 (solo el reconocimiento), RNF-09 · Restricciones: RT-01, RT-02, RT-03, RT-04, RT-05, RT-07 · Historias de usuario: HU-09 (solo el reconocimiento; la vectorización corresponde a la spec de integración) · Casos de uso: CU-08
- «Estado actual» del ERS que cierra: ninguno. Puede abrir uno en RF-09 al cerrar la spec (requisito N-7).
- Los requisitos de la herramienta de evaluación no existen en el ERS: van marcados `[NUEVO]`, sirven para verificar RF-09 y no se proponen como requisitos del producto.

## Usuarios
Ninguno de forma directa: la evaluación la ejecuta el desarrollador. La beneficiaria es la persona Usuario Gubernamental que carga imágenes de documentos impresos (HU-09).

## Historias de usuario
- HU-09 (solo la parte de reconocimiento): «Como Usuario Gubernamental, necesita que el sistema reconozca el texto de una imagen de un documento impreso o tipeado, para poder consultar documentos que solo tiene como foto o escaneo.» Esta spec aporta evidencia solo sobre capturas de pantalla, no sobre fotos ni escaneos (ver «Límites documentados»).

## Definiciones
- **Herramienta de evaluación**: las herramientas de investigación que miden a los candidatos. En los requisitos se nombra «LA HERRAMIENTA».
- **Texto de referencia**: el texto exacto que aparece en la imagen, sin menús, barras ni otros elementos de la interfaz. Se escribe desde el texto fuente, nunca corrigiendo la salida de un modelo. Su origen puede ser:
  - inventado;
  - **propio del proyecto**, como el ERS;
  - **de terceros**, como páginas web públicas.

  En ningún caso contiene datos personales.
- **CER de página**: distancia de edición por carácter entre el texto reconocido de una página completa (los renglones unidos) y su texto de referencia, dividida entre la longitud de la referencia.
  - Antes de comparar, ambos textos se normalizan a Unicode NFC, y los espacios y saltos de línea seguidos se reducen a un solo espacio.
  - No se normalizan mayúsculas, tildes ni puntuación.
- **CER promedio**: la media de los CER de página de todas las capturas del set. Es la única métrica que decide.
- **Acierto en caracteres del español**: para cada carácter á, é, í, ó, ú, ñ, ü, ¿ y ¡ del texto de referencia, se alinea la referencia con el texto reconocido por distancia de edición. El acierto es la proporción de esas apariciones en las que el texto reconocido tiene el mismo carácter en la posición alineada. Se reporta por carácter y en total.
- **VRAM pico**: la memoria máxima de GPU reservada por PyTorch en el proceso que mide al candidato, incluido el localizador cuando lo usa. Para Tesseract es 0, porque corre en CPU.
- **Tiempo por página**: desde que se entrega la imagen hasta que se obtiene el texto de la página. Para Tesseract incluye la llamada al servicio de extracción.
- **Candidatos**: cada configuración completa es un candidato.

  | # | Candidato | Ubicación de renglones |
  |---|---|---|
  | 1 | Línea base: `microsoft/trocr-large-handwritten` | Localizador docTR de producción |
  | 2 | `qantev/trocr-large-spanish` | Localizador docTR de producción |
  | 3 | `microsoft/trocr-large-printed` | Localizador docTR de producción |
  | 4 | docTR completo, con su reconocedor predeterminado, en una versión fijada | Su propio análisis de página |
  | 5 | Tesseract tal como está desplegado en el servicio de extracción (idioma `spa+eng`, en CPU, consultado por HTTP y sin cambiar su configuración) | Su propio análisis de página |

## Requisitos funcionales

- N-1 `[NUEVO]` (verifica RF-09 en su caso «captura de pantalla», RT-01): LA HERRAMIENTA usa un set de prueba real de **capturas de pantalla**, en formatos admitidos por RT-01, con al menos 10 imágenes y al menos 100 líneas. Cada imagen trae su texto de referencia, sin datos personales. SI el set no alcanza esos mínimos, ENTONCES LA HERRAMIENTA no mide y lo informa.
- N-2 `[NUEVO]` (verifica RF-09): SI una imagen no tiene texto de referencia, ENTONCES LA HERRAMIENTA la excluye de la medición y lo informa, sin detener la corrida.
- N-3 `[NUEVO]` (verifica RF-09, RT-02, RT-04):
  - LA HERRAMIENTA mide los 5 candidatos con el mismo set, en igualdad de condiciones, con calentamiento previo y aplicando la orientación EXIF a cada imagen antes de entregarla, también a Tesseract.
  - Todos los candidatos corren en la infraestructura local y son de origen permitido por RT-04, tal como lo aplica el ERS.
  - Quedan fuera Donut, porque no transcribe, y Surya, por la licencia de sus pesos; no por su origen.
- N-4 `[NUEVO]` (verifica RF-09): ANTES de medir docTR, LA HERRAMIENTA registra su versión fijada y comprueba si el vocabulario de su reconocedor incluye á, é, í, ó, ú, ñ, ü, ¿ y ¡. Si falta alguno, lo documenta como límite y docTR se mide igual.
- N-5 `[NUEVO]` (verifica RF-09, RT-07): CUANDO evalúa un candidato, LA HERRAMIENTA reporta el CER promedio, que es la métrica que decide. Como dato complementario reporta:
  - el CER de cada página;
  - el tiempo promedio por página;
  - la VRAM pico;
  - el acierto en los caracteres del español.
- N-6 `[NUEVO]` (verifica RF-09, RT-03): CUANDO terminan las mediciones, LA HERRAMIENTA elige así:
  1. Entran solo los candidatos con VRAM pico ≤ 2,5 GB y tiempo promedio ≤ 10 s por página. Gana el de menor CER promedio.
  2. Si dos candidatos difieren en 0,005 o menos de CER promedio, gana el de menor VRAM pico y, si siguen empatados, el de menor tiempo promedio.
  3. Si el ganador tiene CER promedio ≤ 0,10, se declara «listo para integrar para capturas de pantalla». La marca no se extiende a fotos ni a escaneos.
  4. SI el ganador tiene CER promedio > 0,10, ENTONCES se elige igual, pero sin la marca «listo para integrar» y con la brecha documentada.
  5. SI ningún candidato cumple los límites de VRAM y tiempo, ENTONCES no hay ganador, y se documenta la brecha de cada candidato.

  *Aclaraciones (confirmadas por Andrés el 05/10):*
  - **Brecha**: cuánto supera el candidato cada límite que no cumple (CER − 0,10, VRAM − 2,5 GB, tiempo − 10 s).
  - **Desempate**: solo entre el primero y el segundo por CER promedio.
- N-7 `[NUEVO]` (afecta a RF-09): SI la línea base no queda «lista para integrar», ENTONCES, al cerrar esta spec, RF-09 pasa a «Parcial» en el ERS, con un párrafo «Estado actual» que diga que el reconocedor en producción no cumple el criterio sobre capturas de pantalla, y que las fotos y los escaneos no se han medido. Ese estado se mantiene hasta cerrar la spec de integración (principio 2).

  *Aclaración (confirmada el 05/10):* la línea base queda «lista» solo si cumple el criterio completo: CER promedio ≤ 0,10, VRAM pico ≤ 2,5 GB y tiempo promedio ≤ 10 s por página. Si falla cualquiera de los tres, aplica N-7.
- N-8 `[NUEVO]` (afecta a RF-09, HU-09, CU-08 y FH-01): SI gana docTR o Tesseract, ENTONCES la elección se marca como **cambio de requisito**, porque la planificación dice «docTR + TrOCR».
  - El cambio se aprueba con `/sdd-change`.
  - Se actualizan RF-09, HU-09, CU-08 y FH-01 del ERS antes de empezar la spec de integración.
  - Si gana Tesseract, también la regla de `CLAUDE.md` que envía las imágenes al servidor HTR antes que al servicio de extracción.
- N-9 `[NUEVO]` (verifica RF-09): CUANDO se hace la elección, los resultados se documentan en `resultados.md` de esta spec y en la documentación de las herramientas de investigación. Incluyen:
  - la tabla comparativa;
  - el ganador y su marca, o la brecha;
  - la versión y el vocabulario de docTR;
  - los límites del set, empezando por este: **RF-09 quedó medido solo en su caso «captura de pantalla»**; no hay evidencia sobre fotos con celular ni escaneos.

## Requisitos no funcionales

- RNF-09.1: LA HERRAMIENTA mide con los pesos de los candidatos ya descargados y sin conexión de red hacia afuera; solo se comunica con los servicios locales. SI necesita salir a la red durante la medición, ENTONCES falla y lo informa, en vez de descargar o enviar datos.
- RT-03.1: MIENTRAS se mide:
  - Ollama está detenido;
  - el servidor HTR de producción sigue arriba, pero con su modelo fuera de la GPU.

  ANTES de cada corrida, LA HERRAMIENTA comprueba automáticamente que ningún otro proceso tenga un modelo cargado en la GPU. SI lo hay, ENTONCES no mide e informa qué proceso es.
- N-10 `[NUEVO]` (protege datos, RNF-09): el repositorio público recibe el código, las pruebas, los textos de referencia inventados o propios del proyecto y los resultados documentados (`resultados.md`). No recibe:
  - las imágenes del set;
  - los textos de referencia de fuentes de terceros (las capturas web), por posibles derechos de autor;
  - ningún dato personal: las capturas web se revisan a mano antes de usarlas.

  `resultados.md` no reproduce texto de terceros más allá de fragmentos breves de ejemplo.
- N-11 `[NUEVO]` (verifica RF-09): las pruebas automatizadas de la herramienta usan imágenes generadas por las propias pruebas, nunca el set real.

## Casos límite
- **Imagen con la orientación guardada en sus metadatos (EXIF):** se mide con la orientación ya aplicada (N-3).
- **Captura que incluye menús o barras de la interfaz:** lo que el candidato lea ahí cuenta como error, porque el texto de referencia no los incluye. Es intencional: es lo que pasa en producción.
- **Captura en modo oscuro (texto claro sobre fondo oscuro):** se mide tal cual, sin invertir los colores, y el resultado se reporta como dato.
- **Captura con texto cortado en el borde:** el texto de referencia incluye solo lo que se ve completo en la imagen.
- **PNG con transparencia o en escala de grises:** se convierte a color sobre fondo blanco antes de entregarlo a cualquier candidato, y la conversión es la misma para todos.
- **Página donde no se detecta ningún renglón:** el texto reconocido es vacío (CER = 1 para esa página) y se reporta.
- **Salida en otro idioma, sin tildes o con un punto agregado al final:** se mide como error, sin corregir la salida.
- **Un candidato falla al cargar o a mitad de la corrida, o el servicio de extracción no responde:** LA HERRAMIENTA registra el fallo, sigue con los demás y lo reporta como «sin medir».

## Fuera de alcance
- Integrar el ganador al pipeline de ingesta o cambiar el reconocedor en producción.
- La vectorización del texto reconocido.
- Los PDF escaneados y los documentos o formularios escaneados (límite documentado).
- Las fotos con celular, de páginas impresas o de pantallas (límite documentado).
- El manuscrito y el afinado (LoRA).
- El aviso de la pantalla de carga (RF-05, RF-10).
- Cualquier preprocesamiento distinto del localizador actual.
- Cambiar la configuración del servicio de extracción.
- Variantes base de TrOCR y otras variantes de docTR.
- Condiciones difíciles controladas.

## Criterios de finalización
- Cada requisito tiene al menos una prueba automatizada que pasa en la suite propia de las herramientas de investigación, ejecutada en su contenedor (excepción aprobada el 05/10), o una exención justificada.
- Las dependencias de prueba que haga falta agregar a la imagen de las herramientas de investigación (por ejemplo, pytest) están permitidas. El plan decide cuáles y las justifica (principio 1 de la constitución).
- **Exenciones justificadas** (no automatizables): tomar las capturas y redactar los textos de referencia (N-1), que incluye comprobar a mano que las capturas y sus textos no tengan datos personales. Se verifican a mano y se registran en `resultados.md`. El conteo de imágenes y líneas de N-1 sí se comprueba automáticamente.
- La tabla de los 5 candidatos y la elección (N-6) están en `resultados.md`, y la documentación de las herramientas de investigación está actualizada.
- Si aplica N-7, RF-09 queda como «Parcial», con su «Estado actual», en el ERS.
- Si aplica N-8, el cambio está aprobado con `/sdd-change` y el ERS actualizado antes de abrir la spec de integración.
- Plazo: del 05 al 08/10.
- `MEMORY.md` está actualizado.

## Dudas abiertas
- Ninguna.
