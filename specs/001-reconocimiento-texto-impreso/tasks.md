# Tareas — Spec 001: Reconocimiento de texto impreso

Orden de dependencia. Cada tarea empieza por sus pruebas y comprueba que fallan antes de escribir el código. Las pruebas corren con `docker compose exec servidor-htr pytest`.

La T7 depende en parte de Andrés (revisar los textos de referencia y los datos personales) y puede hacerse en paralelo a la T4 y la T5. Plazo: del 05 al 08/10. Ajustada al cambio 1 de la spec (05/10): el set tiene solo capturas.

- [x] **T1. Preparar la suite de pruebas y fijar docTR.** N-4, N-11 ⚠️ archivos nuevos (`htr/pytest.ini`, `htr/tests/`), dependencia nueva en la imagen de `htr/` (`pytest`), cambio en el `Dockerfile` y reconstrucción del servicio `servidor-htr`
  - Consultar la versión instalada (`docker compose exec servidor-htr pip show python-doctr`) y fijarla con `==` en `htr/Dockerfile`. Agregar `pytest`.
  - Reconstruir: `docker compose build servidor-htr` y `docker compose up -d servidor-htr`.
  - Pruebas: la versión de docTR instalada es igual a la fijada (N-4); ninguna prueba usa la ruta `htr/dataset/` (N-11).
  - Hecho cuando: `docker compose exec servidor-htr pytest` corre y las 2 pruebas pasan, y `/salud` responde como antes.

- [x] **T2. Métricas puras.** N-5 ⚠️ archivo nuevo (`htr/metricas_impreso.py`)
  - Pruebas:
    - normalización NFC (vocal con tilde descompuesta igual a la compuesta);
    - espacios y saltos seguidos reducidos a uno;
    - CER de página y CER promedio (media por página) contra valores calculados a mano;
    - página vacía con CER 1;
    - acierto en á é í ó ú ñ ü ¿ ¡, con un caso de tildes borradas y uno de caracteres sustituidos.
  - Hecho cuando: esas pruebas y la suite completa pasan.

- [x] **T3. Elección del ganador y marcas.** N-6, N-7, N-8
  - Pruebas:
    - gana el de menor CER entre los elegibles;
    - se excluyen los que superan 2,5 GB de VRAM o 10 s por página;
    - una diferencia ≤ 0,005 se desempata por VRAM y luego por tiempo;
    - sin elegibles, no hay ganador y queda la brecha;
    - un ganador con CER > 0,10 no queda «listo para integrar»;
    - la marca N-7 aparece solo si la línea base no queda lista;
    - la marca N-8 aparece solo si gana docTR o Tesseract.
  - Hecho cuando: esas pruebas y la suite completa pasan.

- [x] **T4. Carga y preparación del set.** N-1, N-2, N-3, N-10 ⚠️ archivo nuevo (`htr/evaluar_impreso.py`)
  - Pruebas, con imágenes generadas en `tmp_path`:
    - un set de 10 capturas con ≥ 100 líneas se acepta, y con 9 capturas o 99 líneas aborta con un mensaje en español;
    - el texto de referencia se encuentra tanto en `corpus/impreso/capturas/` (propio) como junto a la imagen (terceros);
    - una imagen sin `.txt` en ninguna de las dos ubicaciones se excluye, se informa y la corrida sigue;
    - `preparar()` aplica la orientación EXIF;
    - RGBA y LA quedan sobre blanco, y L pasa a RGB;
    - `htr/dataset/impreso` (imágenes y textos de terceros) y `htr/resultados` quedan fuera de Git, y `htr/corpus/impreso` no.
  - Hecho cuando: esas pruebas y la suite completa pasan.

- [x] **T5. Guardias de GPU y de red.** RT-03.1, RNF-09.1
  - Pruebas, con `/salud` y la salida de `nvidia-smi` simulados:
    - con el servidor en `cuda`, con más de 1,0 GB de VRAM ocupada según `nvidia-smi` o si `nvidia-smi` no responde, no se mide y se informa el motivo;
    - en modo sin red, una conexión a un host externo falla con un mensaje claro, mientras `tika` y `localhost` siguen permitidos;
    - `--descargar` es el único modo que permite la red.
  - Hecho cuando: esas pruebas y la suite completa pasan.
  - Corregida en T8 (05/10): la guardia medía con `torch.cuda.mem_get_info`, que en WSL2 no ve la VRAM de otros procesos, y dejaba medir con Ollama cargado. Ahora mide con `nvidia-smi`, con un umbral de 1,0 GB (decisión 5 del plan).

- [x] **T6. Candidatos y corrida.** N-3, N-4, N-5, N-9
  - Agregar `large_printed` a `MODELOS` en `htr/evaluar_modelos.py`.
  - Implementar los adaptadores:
    - candidatos 1 a 3: TrOCR con el localizador docTR y los parámetros de producción, más `unir`;
    - candidato 4: docTR completo, con su versión y su vocabulario registrados;
    - candidato 5: Tika por HTTP.
  - Implementar la corrida: calentamiento, tiempo por página con sincronización de CUDA, VRAM por `max_memory_reserved` (0 para Tesseract), «sin medir» ante un fallo, y el JSON y la tabla Markdown.
  - Pruebas:
    - unitarias, con candidatos simulados: un fallo deja ese candidato «sin medir» y los demás se miden; 0 renglones dan texto vacío; el vocabulario faltante se informa; el JSON y la tabla traen todas las columnas;
    - de integración (`integracion`), sobre una página generada con texto conocido: cada candidato devuelve texto no vacío; con Tika inaccesible, Tesseract queda «sin medir».
  - Hecho cuando: las unitarias y la suite completa pasan. Las de integración pasan con Ollama detenido; si no se pueden correr todavía, quedan pendientes para la T8.

- [x] **T7. Set de prueba real, a partir de `Documentacion/Pruebas/`.** N-1, N-2, N-10 ⚠️ mover imágenes (de `Documentacion/Pruebas/` a `htr/dataset/impreso/capturas/`, que está ignorada por Git) y archivos nuevos (`htr/corpus/impreso/capturas/1.txt`, versionado). Incluye una revisión manual de Andrés (aprobada el 05/10).
  1. **Mover las 10 capturas** `1–5.png` y `12–16.png` a `htr/dataset/impreso/capturas/`. Las imágenes nunca van a `corpus/`, porque esa carpeta se versiona. `6–11.jpeg` (fotos con celular, límite documentado) y `1.pdf` (fuera de alcance) se quedan donde están.
  2. **Revisar a mano los datos personales.** Solo `1` y `5` son capturas del ERS; `2–4` y `12–16` son de terceros. `5` nombra al tutor: se usa igual, pero su texto no se versiona (decisión de Andrés). En `4` y `14` aparecen autores citados y un jurista histórico, que no se consideran datos personales.
  3. **Texto de referencia de `1`**: extraído del Word vigente del ERS (texto fuente), recortado a lo que se ve completo en la captura. Se guarda en `htr/corpus/impreso/capturas/1.txt` y se versiona.
  4. **Textos de referencia de `2–5` y `12–16`**: `5` desde el Word del ERS; los demás, transcritos exactos desde la imagen (nunca desde la salida de un modelo), sin menús, anuncios ni barras. Se guardan junto a la imagen, en `htr/dataset/impreso/capturas/<n>.txt`, y no se versionan: son de terceros o, en el caso de `5`, contienen un dato personal. Andrés revisó los 10 textos contra sus imágenes.
  - Pruebas: las 2 de `--solo-verificar-set`, que se agregó a la herramienta para esta tarea. El cargador de la T4 sobre el set real hace de comprobación automática.
  - Hecho cuando:
    - `python evaluar_impreso.py --solo-verificar-set` informa ≥ 10 capturas y ≥ 100 líneas, sin imágenes excluidas;
    - `git status` muestra solo `htr/corpus/impreso/capturas/1.txt`, sin imágenes ni los demás textos;
    - `Documentacion/Pruebas/` ya no contiene `1–5.png` ni `12–16.png`.

- [x] **T8. Medición real.** N-1 a N-9, RT-03.1, RNF-09.1 ⚠️ detener Ollama y esperar a que el servidor HTR libere la GPU
  1. `python evaluar_impreso.py --descargar`: único paso con red.
  2. `docker compose stop ollama` y esperar a que `/salud` diga `"dispositivo": "cpu"`. No cargar archivos en la ingesta mientras se mide.
  3. Correr las pruebas `integracion` pendientes y después la medición completa.
  4. `docker compose start ollama`.
  - Pruebas: la suite completa, incluida `integracion`.
  - Hecho cuando:
    - la suite pasa;
    - el JSON trae los 5 candidatos, medidos o «sin medir» con su motivo;
    - la revisión a ojo de 2 capturas del ERS y 2 capturas web es coherente;
    - con Ollama arriba y un modelo cargado, la guardia se niega a medir;
    - el chat y `/salud` funcionan igual que antes de medir.

- [x] **T9. Documentar los resultados.** N-9, N-7, N-8 ⚠️ archivo nuevo (`specs/001-…/resultados.md`)
  - `resultados.md`:
    - abre con el límite principal: RF-09 quedó medido solo en su caso «captura de pantalla», sin evidencia sobre fotos con celular ni escaneos, y la marca «listo para integrar» vale solo para capturas;
    - la tabla, el ganador y su marca, o la brecha (cuánto supera cada límite);
    - la versión y el vocabulario de docTR;
    - los demás límites: set pequeño, y del texto de terceros solo fragmentos breves (N-10);
    - los hallazgos para la integración (límite de 60 renglones, recorte de papel en las capturas);
    - las exenciones verificadas a mano.
  - `htr/README.md`: sección del ciclo de texto impreso, con cómo correr la herramienta, el resultado y el estado.
  - Pruebas: la tabla de `resultados.md` coincide con la tabla Markdown que generó la herramienta (comparación hecha a mano contra el JSON).
  - Hecho cuando: los dos documentos están actualizados y la suite completa sigue pasando.

- [x] **T10. Actualizar la documentación de planificación y cerrar.** N-7, N-8
  - Si aplica N-7: Andrés edita el Word vigente del ERS para dejar RF-09 como «Parcial», con su «Estado actual», que menciona también que las fotos y los escaneos no se midieron. Después se regenera el PDF.
  - Si aplica N-8: abrir `/sdd-change` para RF-09, HU-09, CU-08 y FH-01 (y la regla de `CLAUDE.md` si gana Tesseract) antes de la spec de integración.
  - Actualizar `MEMORY.md`, con el modelo elegido para RF-09 y si sigue vigente el Ciclo 4.
  - Pasar la spec a «implementada».
  - Pruebas: no lleva pruebas nuevas. La suite completa debe pasar.
  - Hecho cuando: el ERS y el PDF reflejan el estado de RF-09 (o se deja constancia de que no aplica), `/sdd-change` está abierto si corresponde, `MEMORY.md` está actualizado y la spec está en «implementada».
