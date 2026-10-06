# Resultados — Spec 001: Reconocimiento de texto impreso

Medición del 05/10/2026 (resultado crudo: `htr/resultados/eval_impreso_2026-10-06_010858.json`, no versionado). Este documento solo contiene cifras agregadas y fragmentos breves: ni imágenes ni textos completos del set (N-10).

## Límite principal

**RF-09 quedó medido solo en su caso «captura de pantalla».** No hay evidencia sobre fotos con celular ni escaneos, y la marca «listo para integrar» vale solo para capturas de pantalla (N-9).

## Conjunto medido

10 capturas y 155 líneas de referencia, sin imágenes excluidas: 2 capturas de un documento propio del proyecto y 8 de terceros (páginas web, artículos y un libro). Para la herramienta, 1 texto de referencia es «propio» (versionado) y 9 son «de terceros» (junto a la imagen, sin versionar); una de las capturas propias se guarda así por contener un nombre de persona. Los 5 candidatos se midieron con el mismo set, con calentamiento previo, la orientación EXIF aplicada, sin red y con Ollama detenido y el servidor HTR sin su modelo en la GPU (RT-03.1, RNF-09.1).

## Tabla comparativa

| # | Candidato | CER promedio | Tiempo (s/página) | VRAM pico (GB) | Acierto en español | Elegible |
|---|---|---|---|---|---|---|
| 1 | `microsoft/trocr-large-handwritten` (línea base) | 0,1208 | 8,52 | 2,15 | 0,0 % (0/169) | sí |
| 2 | `qantev/trocr-large-spanish` | 0,0642 | 10,25 | 2,35 | 88,8 % (150/169) | no: 10,25 s > 10 s |
| 3 | `microsoft/trocr-large-printed` | 0,8401 | 11,72 | 2,35 | 0,6 % (1/169) | no: 11,72 s > 10 s |
| 4 | docTR completo 1.1.0 | **0,0484** | 0,31 | 0,71 | 14,2 % (24/169) | sí |
| 5 | Tesseract (servicio de extracción) | 1,0000 | 0,03 | 0,00 | 0,0 % (0/169) | sí |

## Elección según N-6

- **Ganador: docTR completo (candidato 4), CER promedio 0,0484: «listo para integrar para capturas de pantalla»** (CER ≤ 0,10).
- **N-7:** la línea base no cumple el criterio (CER 0,1208 > 0,10; brecha de +0,021). Se propone pasar RF-09 a «Parcial» en el ERS, con su «Estado actual» (se hace en T10).
- **N-8:** gana docTR, así que la elección es un **cambio de requisito**: la planificación dice «docTR + TrOCR» (RF-09, HU-09, CU-08, FH-01). Se aprueba con `/sdd-change`.
- Brechas: candidato 2, +0,25 s sobre el límite de tiempo; candidato 3, +0,74 de CER y +1,72 s; candidato 5, +0,90 de CER.

## Advertencias

1. **El vocabulario de docTR no incluye á í ó ú ñ ¿ ¡.** Su acierto en esos caracteres es 14,2 %, frente a 88,8 % de qantev: sustituye las vocales con tilde y la ñ por la letra sin marca (todos sus aciertos, 24 de 24, son «é», que sí está en su vocabulario). Con el CER no se nota casi nada, porque cada tilde perdida es un solo carácter.
2. **qantev (CER 0,0642) quedó fuera por solo 0,25 s** sobre el límite de 10 s. Subir ese límite **no cambia el ganador**: qantev pasaría a ser elegible, pero docTR sigue teniendo el menor CER.
3. **El límite de 10 s lo propuso el planificador sin medirlo.** Andrés considera aceptable hasta 1 minuto por página en la ingesta, que es asíncrona.
4. **Prioridad de Andrés:** acertar las letras, respetando tildes y ñ cuando se pueda; su ausencia se toma como un detalle menor.
5. **La decisión final de qué reconocedor integrar queda para la spec de integración**, midiendo también la **recuperación en el chat** con docTR y con qantev: el CER no es lo único que importa para el RAG (`MEMORY.md`).
6. **Tesseract (CER 1,0) refleja un hallazgo, no su calidad.** El servicio de extracción desplegado procesa las imágenes PNG con `EmptyParser` y no hace OCR, aunque Tesseract ejecutado directamente sí las lee. Se corrige en una corrección de error aparte (`tika-config.xml`), que también debe comprobar si los PDF escaneados pierden su OCR.
7. **La captura 12 tiene CER 0,30 con docTR**, porque lee la ruta de navegación, la firma y el anuncio, que el texto de referencia excluye a propósito (en producción también aparecerían). Las otras 9 capturas van de 0,009 a 0,030.

## CER según dónde se guarda el texto de referencia (dato complementario)

| # | Versionado (1 captura) | Junto a la imagen (9 capturas) |
|---|---|---|
| 1 | 0,0464 | 0,1290 |
| 2 | 0,0055 | 0,0707 |
| 3 | 0,7917 | 0,8454 |
| 4 | 0,0165 | 0,0519 |
| 5 | 1,0000 | 1,0000 |

Con una sola captura en el primer grupo, este desglose no es concluyente.

## Versión y vocabulario de docTR

- Versión fijada: `python-doctr==1.1.0` (la que ya estaba instalada). Detector `fast_base`, reconocedor `crnn_vgg16_bn`.
- Caracteres del español que su vocabulario no incluye: á, í, ó, ú, ñ, ¿, ¡. Sí incluye é y ü.

## Otros límites

- **Set pequeño**: 10 capturas y 155 líneas, con solo 2 capturas de un documento propio. Los resultados orientan, no son definitivos.
- **No cubre fotos con celular ni escaneos.**
- **Textos de terceros**: este documento no los reproduce más allá de fragmentos breves.
- **Manuscrito**: sigue como limitación aceptada (RF-10); esta spec no lo midió.

## Hallazgos para la integración

- **Límite de 60 renglones**: ninguna captura se acercó (máximo 22 renglones de referencia), así que no se pudo comprobar el efecto de `max_lineas=60`.
- **Localizador de producción**: en 3 capturas detectó una «columna de numeración» y limpió entre 5 y 6 renglones; no se revisó a mano si eran falsos positivos. En la captura 12 detectó 18 renglones frente a 11 de referencia (el anuncio y la ruta de navegación).
- **Recorte de papel**: no se observó ningún caso, pero tampoco se verificó captura por captura.
- **VRAM**: docTR necesita 0,71 GB y los TrOCR de 2,15 a 2,35 GB, así que docTR convive mejor con Ollama en la GPU de 8 GB.
- **Tiempo**: docTR lee una página en 0,31 s; los TrOCR tardan de 8,5 a 11,7 s por el reconocimiento renglón por renglón.
- **Guardia de GPU**: en WSL2, `torch.cuda.mem_get_info` solo ve la memoria del propio proceso; se mide con `nvidia-smi` (plan, decisión 5).

## Exenciones verificadas a mano

- Tomar las capturas y redactar los textos de referencia (N-1) fue trabajo humano: Andrés revisó los 10 textos contra sus imágenes. El texto que nombra a una persona se dejó fuera del repositorio por su decisión.
- Revisión a ojo del texto de docTR en 4 capturas (2 del documento propio y 2 web): coherente con las referencias en renglones y contenido, con las tildes y la ñ sustituidas por la letra sin marca.
- La comparación de la tabla de este documento con la que generó la herramienta se hizo a mano contra el JSON.
