# Plan — Spec 001: Reconocimiento de texto impreso (elección del modelo)

Parte de la spec 001 aprobada. Todo vive en `htr/`, que contiene herramientas de investigación y no es código del backend. Este plan no toca `backend/`, `frontend/` ni `docker-compose.yml`. Las pruebas corren con `docker compose exec servidor-htr pytest` (excepción aprobada en `.claude/rules/testing.md`).

## 1. Archivos y responsabilidades

| Archivo | Nuevo o modificado | Responsabilidad | Cubre |
|---|---|---|---|
| `htr/metricas_impreso.py` | Nuevo | Lógica pura, sin GPU ni red: normalización (NFC y espacios), CER de página, CER promedio, acierto en á é í ó ú ñ ü ¿ ¡, y elección del ganador con sus marcas | N-5, N-6, N-7, N-8 |
| `htr/evaluar_impreso.py` | Nuevo | Herramienta de evaluación. Contiene: la carga del set y sus mínimos, la preparación de cada imagen (EXIF, transparencia, escala de grises), las guardias de GPU y de red, los 5 candidatos, la corrida (calentamiento, tiempo y VRAM), el JSON en `htr/resultados/` y la tabla Markdown | N-1 a N-6, N-9, RNF-09.1, RT-03.1 |
| `htr/evaluar_modelos.py` | Modificado | Se agrega `"large_printed": "microsoft/trocr-large-printed"` a `MODELOS`. Así el nombre de cada repositorio vive en un solo lugar y se puede repetir la medición por línea si hace falta | N-3 |
| `htr/corpus/impreso/capturas/*.txt` | Nuevos, versionados | Textos de referencia propios del proyecto que se versionan (captura del ERS `1`) | N-1, N-10 |
| `htr/dataset/impreso/capturas/*` | Nuevos, no versionados (`dataset/` ya está en `.gitignore`) | Las 10 imágenes del set, y junto a ellas los `.txt` de referencia de terceros (capturas web, `12–16`) | N-1, N-10 |
| `htr/tests/conftest.py`, `htr/tests/test_metricas_impreso.py`, `htr/tests/test_evaluar_impreso.py`, `htr/pytest.ini` | Nuevos | Suite propia. Las imágenes de las pruebas las genera la propia suite con Pillow, en `tmp_path`. El marcador `integracion` señala las pruebas que necesitan GPU, pesos o Tika | Todos; N-11 |
| `htr/Dockerfile` | Modificado | Agrega `pytest` y fija `python-doctr` a la versión que ya está instalada, sin actualizarla | N-4; principio 1 |
| `specs/001-…/resultados.md`, `htr/README.md` | Nuevo y modificado | Documentación de resultados | N-9 |

Los resultados crudos van en `htr/resultados/`, que ya está en `.gitignore` (N-10).

## 2. Lógica por capa y dependencias externas

No hay router, servicio ni repositorio: la herramienta se ejecuta a mano dentro del contenedor `servidor-htr`, con `docker compose exec servidor-htr python evaluar_impreso.py`. Su estructura interna:

- **Lógica pura** (`metricas_impreso.py`): sin dependencias externas. Usa `rapidfuzz` para la distancia de edición y su alineación; ya está instalado porque docTR depende de él, así que no es una dependencia nueva.
- **Candidatos** (`evaluar_impreso.py`): todos cumplen la misma interfaz `leer_pagina(imagen) -> (texto, lineas_detectadas)`.

| # | Candidato | Cómo lee una página |
|---|---|---|
| 1 | `microsoft/trocr-large-handwritten` | `deteccion_aprendida.segmentar(...)` con los mismos parámetros que usa `servidor_htr.py` (`max_lineas=60`), y después TrOCR por renglón y `unir_lineas.unir(textos, cortes=…)`. Reproduce el flujo de producción |
| 2 | `qantev/trocr-large-spanish` | Igual que el 1 |
| 3 | `microsoft/trocr-large-printed` | Igual que el 1 |
| 4 | docTR completo | `doctr.models.ocr_predictor(pretrained=True)`, con detector y reconocedor predeterminados. El texto se arma con `resultado.render()` |
| 5 | Tesseract | `PUT http://tika:9998/tika` con la imagen ya preparada (PNG), `Accept: text/plain`, sin cabeceras de idioma: rige la configuración desplegada (`spa+eng`). Corre en CPU, así que su VRAM es 0 |

**Dependencias externas**: GPU (candidatos 1 a 4), Tika (candidato 5) y el `/salud` del servidor HTR de producción, que corre en el mismo contenedor (`http://localhost:9100/salud`). No intervienen SQL Server, Qdrant, Ollama ni Redis.

## 3. Flujo (pseudocódigo)

```
main(--set htr/dataset/impreso, --refs htr/corpus/impreso, [--descargar] [--candidatos 1,2,3,4,5])
  si --descargar:                      # paso previo explícito, el único con red
      descargar pesos de 1–4 a las caches; salir
  activar_modo_sin_red()               # RNF-09.1: HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1
                                       # y guardia de socket: solo localhost, 127.0.0.1 y tika
  set = cargar_set()                   # N-1, N-2: por cada imagen de dataset/impreso/capturas/ busca
                                       # su .txt primero en corpus/impreso/capturas/ (propio) y si no,
                                       # junto a la imagen (terceros); excluye e informa las que no
                                       # tienen; si hay <10 imágenes o <100 líneas → aborta con mensaje
  comprobar_gpu_libre()                # RT-03.1: /salud dice dispositivo == "cpu" y la VRAM en uso
                                       # (nvidia-smi --query-gpu=memory.used, que ve todos los procesos) ≤ 1,0 GB;
                                       # si nvidia-smi no responde, no se mide. mem_get_info queda solo como dato;
                                       # si no → aborta indicando qué falló
  por cada candidato, en orden 1,2,3 → 4 → 5:
      intentar:
          liberar la GPU (del + empty_cache; anular el detector en caché de deteccion_aprendida antes del 4)
          torch.cuda.reset_peak_memory_stats()
          cargar candidato; si es el 4: registrar versión de docTR y vocabulario faltante (N-4)
          calentar con la primera imagen
          por página: imagen = preparar(ruta)          # EXIF, RGBA/LA/L → RGB sobre blanco
                      t0; texto, n = leer_pagina(imagen); sincronizar CUDA; t1
                      si n == 0: texto = ""            # caso límite: CER = 1
                      guardar CER de página, tiempo y acierto
          vram = torch.cuda.max_memory_reserved()  (0 para Tesseract)
      si falla: marcar "sin medir" con el motivo y continuar           # N-5
  resultado = elegir(métricas)         # N-6 (lógica pura)
  marcas    = N-7 (¿la línea base quedó lista?) y N-8 (¿el ganador es docTR o Tesseract?)
  escribir htr/resultados/eval_impreso_<fecha>.json e imprimir la tabla Markdown   # N-9
```

**Elección** (`elegir`, N-6):

1. Elegibles: candidatos medidos con VRAM pico ≤ 2,5 GB y tiempo promedio ≤ 10 s por página.
2. Si no hay ninguno: no hay ganador, y se reporta la brecha de cada candidato.
3. Se ordenan los elegibles por CER promedio. Si el primero y el segundo difieren en ≤ 0,005, se desempata por menor VRAM y luego por menor tiempo.
4. `listo_para_integrar = (CER del ganador ≤ 0,10)`, y vale solo para capturas de pantalla. Si no lo está, se reporta la brecha: cuánto supera el candidato cada límite.
5. N-7: aplica si la línea base falla cualquiera de los tres criterios (CER, VRAM o tiempo).

**Acierto en caracteres del español**: se obtienen los `opcodes` de Levenshtein entre la referencia normalizada y el texto reconocido normalizado. Para cada posición i de la referencia con un carácter del conjunto, cuenta como acierto si cae en un bloque `equal`, o en un `replace` cuyo carácter alineado es el mismo. Se reporta por carácter y en total.

## 4. Datos

- No hay migración de Alembic ni cambios en Qdrant o Redis.
- **Set**: hay un solo tipo, «captura». Cada imagen `htr/dataset/impreso/capturas/<nombre>.{png,jpg,jpeg}` se empareja con un `<nombre>.txt` en UTF-8, que se busca en dos lugares:
  - `htr/corpus/impreso/capturas/`, para los textos propios del proyecto, que se versionan;
  - la misma carpeta de la imagen, para los textos de terceros, que no se versionan (N-10).

  El conteo de líneas se hace sobre las líneas no vacías del texto de referencia.
- **Resultados crudos**: JSON en `htr/resultados/`, no versionado, con las métricas, la predicción por página, la fecha, la versión de docTR y la configuración.
- No se modifica ni se borra ningún dato existente.

### 4.1 Set de partida (`Documentacion/Pruebas/`)

Tras el cambio 1 de la spec (05/10), el set queda solo con capturas de pantalla.

| Imágenes | Qué son | Texto de referencia | Versionado del texto |
|---|---|---|---|
| `1.png` | Captura del ERS 1.3 | Se extrae del Word vigente del ERS (texto fuente, no salida de un modelo), recortado a lo que se ve en la captura. Andrés lo revisa contra la imagen | Sí: `htr/corpus/impreso/capturas/` |
| `5.png` | Captura del ERS 1.3 con el nombre del tutor (dato personal) | Igual que la `1`, desde el Word del ERS | No: va junto a la imagen, en `dataset/`, para que el nombre no llegue al repositorio (decisión de Andrés, 05/10) |
| `2–4.png` | Capturas de terceros (un artículo web sobre SDD y páginas de un libro sobre LLM), no del ERS | Transcripción exacta desde la imagen, no desde la salida de un modelo | No: va junto a la imagen, en `dataset/` |
| `12–16.png` | Capturas de páginas web de terceros | Transcripción exacta desde la página original, no desde la salida de un modelo | No: va junto a la imagen, en `dataset/` |
| `6–11.jpeg` | Fotos con celular de una pantalla | — | Fuera del set: las fotos con celular son un límite documentado |
| `1.pdf` | PDF armado con capturas | — | Fuera de alcance |

- Las 10 capturas cumplen el mínimo de imágenes de N-1. El mínimo de 100 líneas lo confirma la herramienta (T7).
- Las 10 capturas se **mueven** a `htr/dataset/impreso/capturas/`, que está ignorada por Git (T7). `6–11` y `1.pdf` se quedan donde están. `Documentacion/` todavía no está versionada: antes de versionarla hay que confirmar que esas imágenes no se suban.
- **Datos personales**: la portada del ERS nombra a personas y las páginas web pueden mostrar autores o comentarios. La T7 revisa a mano `1–5` y `12–16`; una captura con datos personales se descarta, y si eso deja el set por debajo del mínimo, se reemplaza por otra.

## 5. Interfaz y roles

No aplica: no hay pantallas, rutas ni `ROUTE_PERMISSIONS`. Los mensajes de la herramienta van en español (RT-07).

## 6. Bitácora (RF-21)

No aplica: no hay acciones de usuarios del sistema. La herramienta la ejecuta el desarrollador fuera de la aplicación.

## 7. Decisiones (con la alternativa descartada)

1. **Medir dentro del contenedor `servidor-htr` en marcha**, con `exec`. Ya tiene la GPU, las caches de pesos y la red de compose hacia `tika`.
   - *Descartado*: un contenedor aparte con `docker-compose.htr.yml`. No está en la red de `tika` y dejaría el servidor de producción compitiendo por la GPU sin control.
2. **Usar el localizador con los parámetros de producción** (`max_lineas=60`, enderezado, detección de papel y quitado de la numeración).
   - *Descartado*: ajustarlos para el texto impreso. Eso mediría una configuración que no existe en producción, y la spec deja el preprocesamiento fuera de alcance.
   - Si una página supera los 60 renglones o el recorte de papel corta una captura, se documenta como hallazgo para la spec de integración.
3. **Unir los renglones con `unir_lineas.unir`, como producción.**
   - *Descartado*: unirlos con un espacio. El CER normaliza los espacios de todos modos, pero `unir` también limpia los artefactos (` .`) que hoy recibe el usuario.
4. **Tesseract a través de Tika tal como está** (decisión de Andrés).
   - *Descartado*: instalar Tesseract en la imagen de `htr/`, que sería una dependencia nueva y otra configuración.
5. **Guardia de GPU con `nvidia-smi --query-gpu=memory.used` y `/salud`** (corregida en T8, 05/10, con la aprobación de Andrés).
   - La VRAM ocupada se lee con `nvidia-smi`, que está dentro de la imagen y ve la memoria de todos los procesos. Si `nvidia-smi` no responde, no se mide.
   - El umbral de 1,0 GB distingue la base sin ningún modelo cargado (493–522 MiB medidos) de un modelo cargado (≥ 2 GB del HTR y 5713 MiB con Ollama).
   - *Descartado*: `torch.cuda.mem_get_info`, que queda solo como dato. En WSL2 solo ve la memoria del propio proceso: con Ollama cargado informaba 1,05 GB en uso mientras `nvidia-smi` marcaba 5713 MiB, así que la guardia dejaba medir. El umbral de 1,5 GB de T5 se había fijado sobre esa misma lectura.
6. **Modo sin red con variables de entorno y una guardia de socket propia**, más un paso `--descargar` explícito y separado.
   - *Descartado*: cortar la red del contenedor, porque exige tocar `docker-compose.yml` y además corta el acceso a Tika.
7. **Fijar `python-doctr` a la versión que ya está instalada** (`pip show`).
   - *Descartado*: subir a la última versión, que cambiaría el localizador de producción como efecto secundario.
8. **VRAM pico con `torch.cuda.max_memory_reserved`** (lo pide la spec), medida por proceso. Así no le afecta el contexto residual del servidor.
9. **`metricas_impreso.py` separado de la herramienta**, para probar la lógica sin GPU.
   - *Descartado*: un solo archivo, cuya lógica pura no se podría importar en las pruebas sin traer también torch y docTR.

## 8. Pruebas por requisito

Pruebas **unitarias**: sin GPU ni red, con imágenes generadas con Pillow en `tmp_path` (N-11). Pruebas de **integración**: marcadas `@pytest.mark.integracion`, necesitan GPU, pesos en caché y Tika arriba.

| Requisito | Unitarias | Integración |
|---|---|---|
| N-1 | Un set de 10 capturas con ≥ 100 líneas se acepta. Con 9 capturas o con 99 líneas, aborta con un mensaje en español. La referencia se encuentra tanto en `corpus/` (propia) como junto a la imagen (terceros) | — |
| N-2 | Una imagen sin `.txt` en ninguna de las dos ubicaciones se excluye, se informa y la corrida sigue | — |
| N-3 | `preparar()` aplica la orientación EXIF (una imagen generada con la etiqueta 6 sale girada). RGBA y LA quedan sobre blanco y L pasa a RGB. Los 5 candidatos reciben la misma imagen. `MODELOS` contiene los tres repositorios de TrOCR | Cada candidato lee una página generada con texto conocido y devuelve texto no vacío |
| N-4 | La comprobación del vocabulario informa los caracteres faltantes (con un vocabulario simulado). La versión instalada de docTR es igual a la fijada | El vocabulario real de docTR queda registrado en el JSON |
| N-5 | La normalización NFC: «á» descompuesta = «á» compuesta. Espacios y saltos seguidos se reducen a uno. CER de página y CER promedio (media por página) con valores calculados a mano. Acierto en caracteres del español con un caso de borrado de tildes. Una página con 0 renglones da CER 1 | La corrida reporta el CER de cada página, el tiempo, la VRAM y el acierto en el JSON |
| N-5 (fallos) | Un candidato que lanza una excepción queda «sin medir» y los demás se miden | Con Tika inaccesible, Tesseract queda «sin medir» |
| N-6 | Gana el de menor CER entre los elegibles. Se excluyen los que superan 2,5 GB o 10 s. Una diferencia ≤ 0,005 entre el primero y el segundo se desempata por VRAM y luego por tiempo. Sin elegibles, no hay ganador. Un ganador con CER > 0,10 no queda «listo para integrar para capturas de pantalla». La brecha es cuánto supera cada límite | — |
| N-7 | La marca «RF-09 a Parcial» aparece si la línea base falla cualquiera de los tres criterios (CER, VRAM o tiempo) | — |
| N-8 | La marca «cambio de requisito» aparece solo si gana docTR o Tesseract | — |
| N-9 | El JSON y la tabla Markdown traen todas las columnas, el ganador o la brecha, y la versión de docTR | — |
| RNF-09.1 | Con el modo sin red, una conexión a un host externo lanza un error claro, y `tika` y `localhost` siguen permitidos | — |
| RT-03.1 | Con `/salud` en `cuda`, o con la VRAM ocupada según `nvidia-smi` por encima de 1,0 GB (simulada), o si `nvidia-smi` no responde, no se mide y se informa el motivo | La guardia real se niega con Ollama cargado y pasa con Ollama detenido y el servidor sin el modelo en la GPU |
| N-10 | Ningún archivo de `dataset/impreso` (imágenes y textos de terceros) ni de `resultados/` queda versionado, y `corpus/impreso` sí se versiona: una prueba lee `git check-ignore`, o en su defecto el `.gitignore` | — |
| N-11 | Ninguna prueba lee `htr/dataset/`: una prueba revisa que la suite no use esa ruta | — |

**Exenciones justificadas**:

- Tomar las capturas, redactar los textos de referencia y revisar que no tengan datos personales (N-1) es trabajo humano. El conteo sí se automatiza.
- No hay pruebas de extremo a extremo en navegador, porque la spec no tiene interfaz.

## 9. Verificación manual de punta a punta

1. `docker compose exec servidor-htr pytest` con todas las pruebas pasando, incluidas las de integración.
2. `docker compose stop ollama`. Esperar a que `curl http://localhost:9100/salud` diga `"dispositivo": "cpu"` (unos 120 s sin uso) y no cargar archivos en la ingesta durante la medición.
3. `docker compose exec servidor-htr python evaluar_impreso.py`: la guardia pasa, los 5 candidatos se miden o se reportan «sin medir» con su motivo, y queda el JSON.
4. Revisar a ojo 2 capturas del ERS y 2 capturas web: que el texto reconocido corresponda a la imagen y que el CER sea coherente con lo que se ve.
5. Comprobar que la guardia funciona: con Ollama arriba y un modelo cargado, la herramienta se niega a medir.
6. `docker compose start ollama`, y comprobar que el chat y `/salud` responden igual que antes.
7. `git status`: no aparece ninguna imagen, ningún texto de terceros ni ningún JSON crudo.

## 10. Documentación a actualizar

- `specs/001-…/resultados.md`:
  - empieza con el límite principal: RF-09 quedó medido solo en su caso «captura de pantalla», sin evidencia sobre fotos ni escaneos, y la marca «listo para integrar» vale solo para capturas;
  - la tabla, el ganador o la brecha, y la versión y el vocabulario de docTR;
  - los demás límites (set pequeño);
  - los hallazgos para la integración (por ejemplo, el límite de 60 renglones y el recorte de papel);
  - las exenciones verificadas a mano.

  Del texto de terceros solo cita fragmentos breves (N-10).
- `htr/README.md`: nueva sección del ciclo de texto impreso, con cómo correr la herramienta, el resultado y el estado.
- **ERS**: si aplica N-7, el «Estado actual» de RF-09 pasa a «Parcial». Andrés lo edita en el Word vigente y se regenera el PDF.
- Si aplica N-8: abrir `/sdd-change` para RF-09, HU-09, CU-08, FH-01 (y la regla de `CLAUDE.md` si gana Tesseract) antes de la spec de integración.
- `MEMORY.md`.
