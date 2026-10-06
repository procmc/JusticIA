# HTR — Reconocimiento de escritura a mano alzada (Fase 4)

Herramientas de investigación y medición para el **Ciclo 1 de la Fase 4**:
llevar lectura de manuscrito en español al sistema.

Esto **no es código del backend**. Vive aparte a propósito: son
herramientas que se corren a mano más un servicio de inferencia. Lo único
que entra al backend es el cliente `htr_service.py` (ver
`integracion_backend/`).

---

## 1. Resultado del Ciclo 1 — modelo elegido

Medición sobre **18 líneas de letra humana real** (imprenta a mano, foto
de celular), con Ollama detenido para liberar la GPU:

| # | Modelo | Param | **CER** | WER | s/línea | VRAM |
|:-:|---|---:|---:|---:|---:|---:|
| 🥇 | **`microsoft/trocr-large-handwritten`** | 558M | **0.2771** | 0.8333 | 0.271 | 2.12 GB |
| 🥈 | `microsoft/trocr-base-handwritten` | 334M | 0.3934 | 0.9405 | 0.199 | 1.29 GB |
| 🥉 | `qantev/trocr-large-spanish` | 609M | 0.4031 | 0.8214 | 0.324 | 2.32 GB |
| 4 | `qantev/trocr-base-spanish` | 385M | 0.6260 | 0.9286 | 0.298 | 1.49 GB |
| 5 | `ifesther/trocr-spanish-handwritten` | 334M | 0.6570 | 0.9286 | 0.365 | 1.29 GB |

Los cinco tienen **licencia MIT**. El resultado se repitió en dos
escrituras independientes del mismo texto.

### Por qué gana el de manuscrito y no el de español

Las tres fallas de `trocr-large-handwritten` son **todas del decoder**:

1. **Traduce al inglés:** `certificación` → `Certification`,
   `octubre` → `October`, `el` → `of`.
2. **Borra todas las tildes:** nunca produce `á é í ó ú ñ`.
3. **Agrega ` .` al final**, sesgo del dataset IAM.

Pero el **encoder ya funciona**: salen exactos `Registro Nacional`,
`4872`, `315`, `mediante`, `inscrito`, `consta`, `vence`.

Leer trazos es lo difícil y no se improvisa; el idioma es lo fácil y se
arregla con fine-tuning. Por eso la ruta del **Ciclo 4** es
**LoRA sobre el decoder**, dejando el encoder intacto.

> ⚠️ Con una primera prueba de **2 líneas**, `qantev/trocr-large-spanish`
> ganaba (0.2258 vs 0.3226). Era **ruido de muestra pequeña**: con 18
> líneas el orden se invirtió. Ver doc 22, sección de metodología.

### Decisiones y descartes

| Qué | Decisión |
|---|---|
| Método de fine-tuning | **LoRA (PEFT)**. Un fine-tune completo pide ~8.8 GB de VRAM contra los 8 GB de la GPU. Además el adaptador pesa decenas de MB en vez de 1.4 GB, y es reversible |
| **Surya** (Datalab) | **Descartado por licencia:** sus pesos son "AI Pubs Open Rail-M" modificada — libre solo para investigación, uso personal y *startups* bajo $5M. Mismo criterio que descartó Transkribus |
| **Donut** (Naver) | Descartado: es comprensión de documentos, no transcripción. Sin checkpoint de manuscrito en español daría CER ≈ 1.0 |
| **Rodrigo Corpus** (CC-BY 4.0) | Descartado: 1545, un solo escribano, ortografía que ya no existe (`ç`, `Nauios`). Afinar con eso enseñaría a escribir mal. Ver `ver_rodrigo.py` |
| **SPA-Sentences / SPARTACUS** | Son el **mismo corpus**. Licencia de investigación con tarifa y restricción comercial. Plan B; solicitud redactada en el doc 23 |
| **Corrección con LLM** | Probada y **descartada**: empeoró el CER 10–14% y **destruye nombres propios** (`JusticIA` → `Justicia`) |
| Imágenes de internet | No sirven: un dataset supervisado necesita la **transcripción exacta** de cada imagen |

---

## 2. Contenido

```text
htr/
├── descargar_fuentes.py      21 tipografías de Google Fonts, verificando
│                             en el cmap que cubran ñ, tildes y ¿ ¡
├── ampliar_corpus.py         Genera oraciones por combinación de
│                             plantillas y vocabulario del dominio
├── generar_sintetico.py      Imágenes de línea + etiquetas, reproducible
│                             por semilla y ponderado por estilo de letra
├── ujipenchars.py            Lee UJIpenchars2 (11,640 caracteres de 60
│                             personas reales) y compone líneas con los
│                             trazos de UN escritor por línea
├── generar_uji.py            Corpus de líneas manuscritas reales, con
│                             partición por escritor reservado
├── evaluar_uji.py            Mide el modelo sobre ese corpus: CER y
│                             recuperación por carácter del español
├── hoja_contacto.py          Mosaico del sintético, inspección visual
├── recortar_lineas.py        Recorta líneas de una foto: detecta papel,
│                             quita espiral. Con --manual para forzar
│                             coordenadas cuando la automática falla
├── partir_bandas.py          Para cuadernos donde cada oración ocupa DOS
│                             renglones: parte cada banda por su valle de
│                             tinta (la proyección sola no las separa)
├── preparar_muestras.py      Procesa un lote de fotos y genera las
│                             plantillas .txt de transcripción
├── ver_rodrigo.py            Inspección del corpus Rodrigo (evidencia
│                             del descarte)
├── evaluar_modelos.py        CER / WER / tiempo / VRAM -> tabla + JSON
├── segmentacion.py           Ubicación de renglones por UMBRAL (Otsu):
│                             papel, encuadernado, deskew, franjas
├── deteccion_aprendida.py    Ubicación de renglones con un detector
│                             ENTRENADO (docTR). Reemplaza el umbral; ver §8
├── evaluar_hoja.py           Mide el pipeline COMPLETO sobre una foto de
│                             página, no el modelo sobre líneas recortadas
├── unir_lineas.py            Une los renglones reconocidos en párrafos
│                             con 8 reglas de puntuación española, más los
│                             cortes que vienen de la disposición de página
├── servidor_htr.py           Servicio HTTP de inferencia con GPU
├── Dockerfile                PyTorch + CUDA en contenedor
├── docker-compose.htr.yml    Servicios `htr` (one-shot) y `servidor-htr`
├── requirements.txt          Dependencias del entorno NATIVO (sin torch)
├── corpus/
│   ├── oraciones_es.txt              153 oraciones escritas a mano
│   ├── oraciones_es_generadas.txt    2,500 generadas por combinación
│   └── set_prueba_manuscrito.txt     16 líneas del SET DE PRUEBA
├── fuentes/                  21 .ttf + licencias/ + ATRIBUCION.md
├── integracion_backend/      Cliente y pasos para integrar al backend
└── dataset/                  NO se versiona (ver §6)
```

### Los dos scripts de recorte, y cuándo usar cada uno

| Script | Cuándo |
|---|---|
| `recortar_lineas.py` | Foto donde **cada línea de texto está separada**. Detecta el papel y quita el encuadernado. `--manual "322-400,392-478"` fuerza coordenadas |
| `partir_bandas.py` | Foto de cuaderno donde **una oración ocupa dos renglones**. La proyección horizontal no los separa porque los rasgos descendentes (la `j` de *juez*) invaden el renglón siguiente. Se le pasa `--renglones N` con el total escrito |

---

## 3. ⚠️ Dónde corre cada cosa

| Entorno | Qué corre ahí |
|---|---|
| `.venv` nativo (Windows) | Preparación de datos: fuentes, corpus, generador, recortes, hoja de contacto. Solo Pillow + numpy |
| **Contenedor Docker** | Todo lo que use **PyTorch**: evaluación, servidor, fine-tuning |

### Por qué PyTorch va en Docker

La PC tiene **Smart App Control activado**
(`VerifiedAndReputablePolicyState = 1`,
`CodeIntegrityPolicyEnforcementStatus = 2`), que bloquea binarios sin
firma reconocida **en cualquier ubicación del disco**:

```
OSError: [WinError 4551] Una directiva de Control de aplicaciones
bloqueó este archivo. Error loading "...\torch\lib\c10.dll"
```

Mover el proyecto fuera de OneDrive **no lo arregla** — no es un problema
de ruta. Y Smart App Control **no se puede reactivar** una vez apagado
(requiere reinstalar Windows), así que apagarlo no es decisión del
pasante. Los contenedores Linux no pasan por esa política.

Notas del contenedor, ambas descubiertas a la fuerza:
* `pip` necesita `--break-system-packages` (PEP 668 en la imagen base). En
  un contenedor desechable es lo correcto: el contenedor *es* el entorno.
* `transformers` está fijado a **`>=4.44,<5`**. Con la rama 5.x la carga
  de los checkpoints de TrOCR falla con
  `Couldn't instantiate the backend tokenizer`, incluso con
  `sentencepiece` instalado.

---

## 4. Uso

### Nativo — preparación de datos (sin GPU)

```bash
# Entorno, una sola vez
python -m venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt

# Tipografías, una sola vez
.venv/Scripts/python.exe descargar_fuentes.py

# Corpus y dataset
.venv/Scripts/python.exe ampliar_corpus.py --cantidad 2500
.venv/Scripts/python.exe generar_sintetico.py --cantidad 500 --semilla 42
.venv/Scripts/python.exe hoja_contacto.py --filas 10

# Recortar líneas de una foto de cuaderno (16 renglones escritos)
.venv/Scripts/python.exe partir_bandas.py dataset/paginas/foto.jpg \
    --renglones 16 --y0 1700 --y1 3900 --x0 60 --saltar 1
```

Rendimiento medido: **~100 imágenes cada 6 segundos**, ~21 KB cada una.

### Docker — evaluación y servicio (con GPU)

```bash
# Liberar la GPU: Ollama retiene ~5.5 GB de los 8 GB
docker compose stop ollama

docker compose -f docker-compose.htr.yml build

# Evaluación
docker compose -f docker-compose.htr.yml run --rm htr \
    python evaluar_modelos.py --muestras dataset/muestras_propias \
    --modelos base_en,large_en,base_es,large_es,base_es_hw

# Servicio de inferencia
docker compose -f docker-compose.htr.yml up -d servidor-htr
curl http://localhost:9100/salud
curl -X POST --data-binary @foto.jpg http://localhost:9100/htr

# Devolver la GPU al chat
docker compose start ollama
```

---

## 5. Licencias — todo limpio, sin pagos ni permisos

| Recurso | Licencia | Implica |
|---|---|---|
| 17 tipografías | **SIL OFL 1.1** | Uso comercial permitido. Exige que el aviso y la licencia acompañen los archivos → están en `fuentes/licencias/` |
| 4 tipografías | **Apache 2.0** | Uso comercial permitido |
| Los 3 corpus | Propios | Contenido **inventado**, sin datos de ninguna persona |
| UJIpenchars2 | **CC BY 4.0** | Uso comercial y adaptación permitidos. Exige **atribución** → abajo |
| docTR (Mindee) y sus pesos | **Apache 2.0** | Uso comercial permitido, sin atribución obligatoria. Corre local: ningún documento sale de la institución |
| `microsoft/trocr-*` y los demás modelos | MIT | Sin restricciones |

Las imágenes generadas con tipografías **no heredan restricción**: OFL y
Apache restringen la redistribución de los *archivos de fuente*, no de lo
que se renderiza con ellos. Detalle en `fuentes/ATRIBUCION.md`.

### Atribución de UJIpenchars2 (obligatoria)

La CC BY 4.0 permite usar, modificar y redistribuir el dataset, incluso
comercialmente, a cambio de una sola condición: **dar crédito**. Es la
licencia más cómoda que se encontró para este caso, porque no exige que lo
derivado se publique con la misma licencia (eso lo pediría una
*share-alike*) ni prohíbe el uso institucional.

> Prat, F., Castro, M., Llorens, D., Marzal, A., & Vilar, J. (2008).
> *UJI Pen Characters* (Version 2). UCI Machine Learning Repository.
> https://doi.org/10.24432/C5FG8S

El crédito tiene que viajar con el material: si algún día se publica el
corpus de líneas generado por `generar_uji.py`, o un modelo afinado con
él, esta cita va incluida. Por eso está acá y en el encabezado de
`ujipenchars.py`, no en un documento aparte.

---

## 6. Qué se versiona y qué no

**No se versiona `dataset/`** — ni el sintético, ni Rodrigo (382 MB de
Zenodo), ni las muestras propias, ni `uji_lineas/` (53 MB) ni
`ujipenchars/` (9 MB). Dos razones distintas:

* Lo generado es **reproducible**: misma semilla, mismas imágenes. Y lo
  descargado se vuelve a bajar: UJIpenchars2 sale del UCI Machine Learning
  Repository y Rodrigo de Zenodo.
* **Ley 8968:** las fotos de manuscrito pueden contener nombres, cédulas o
  datos de terceros.

**Tampoco `resultados/`**: los JSON guardan la transcripción completa de
lo evaluado.

**Sí se versionan las 21 tipografías** (~3.5 MB), y es deliberado: son el
**único insumo no reproducible**. Google Fonts ya renombró y movió
archivos — 11 de 24 candidatos fallaron por eso en la primera corrida. Si
las fuentes no están fijas, el generador deja de ser determinista y la
decisión de no versionar el dataset se cae.

---

## 7. ⚠️ Limitaciones y trampas conocidas

**1. El set de prueba es de un solo escritor.** 18 líneas, letra propia.
Falta variabilidad entre personas — es lo único que ni el sintético ni las
muestras propias pueden dar. Pendiente: conseguir muestras de ~20
escritores.

**2. La cursiva no es el caso de uso.** Dato del encargado (15/09/2026):
en Costa Rica la cursiva ligada ya no se enseña ni se usa. El generador
está ponderado en consecuencia — **imprenta 78%, trazo grueso 15%,
cursiva 5%** (peso bajo, no cero, por documentos de archivo de
generaciones anteriores).

**3. El set de prueba debe ser letra humana moderna, siempre.** El
generador produce **solo** `train` y `val`. Medir el CER contra sintético
da un número engañoso: en sintético `large_es` sacaba CER 0.0213 y
`base_es` quedaba 2º, pero con letra real `base_es` cae al **último**
lugar. El sintético favorece estructuralmente a los modelos entrenados
con texto renderizado.

**4. El ground truth es lo que está en el papel**, no lo ortográficamente
correcto. Si se escribió `practica` sin tilde, el ground truth dice
`practica`. Y se transcribe **desde cero**, nunca corrigiendo la salida de
un modelo: eso volvería la medición circular. La pre-anotación solo vale
para el set de **entrenamiento**.

**5. La segmentación de líneas es un problema aparte.** Casos reales que la
rompen: espiral dentro del papel (aporta tinta en casi todas las filas),
fondo más oscuro que la tinta, rasgos descendentes que unen renglones
contiguos, y texto que toca el borde de la foto. Cae en el alcance del
**Ciclo 2** (preprocesamiento).

**6. ✅ RESUELTO — los números de renglón se filtraban.** En algunos
recortes el número del cuaderno queda pegado al texto (hueco de ~30 px) y
la detección por bloques no lo separa. El modelo lee `IL`, `13`, `15` y
cuenta como error. **Afecta a los 5 modelos por igual, así que el ranking
era válido**, pero los CER estaban inflados. Corregido con la regla del
hueco más ancho en el margen más recorte individual de las dos líneas
rebeldes: el CER de `large_en` pasó de 0.2868 a **0.2771**.

**7. ✅ RESUELTO — HTR y Ollama compartiendo la GPU.** El HTR retiene
~2.1 GB y Ollama ~5.5 GB: 7.6 GB de 8, sin margen. Se resolvió con
**intercambio por inactividad**: cada servicio devuelve la VRAM cuando
queda sin uso (`HTR_IDLE_TIMEOUT=120` y `OLLAMA_KEEP_ALIVE=2m`). Medido:
la GPU baja de 2,602 a 440 MiB al quedar inactiva, y el traslado de vuelta
cuesta ~0.02 s. Detalle en `integracion_backend/PASOS_INTEGRACION.md`.

---

## 8. Los dos localizadores de renglones, y por qué se cambió

TrOCR reconoce **una línea por vez**. Todo el trabajo de partir la página
en renglones existe únicamente por eso. Y medido de punta a punta, ese
paso llegó a aportar más error que el propio reconocedor.

Importante para no confundirse: **nunca se binariza lo que ve el modelo.**
La máscara y las cajas sirven solo para saber dónde cortar; a TrOCR se le
entregan los píxeles RGB originales. No existe una "imagen limpia"
intermedia en ningún punto.

### El problema del umbral

`segmentacion.py` decide qué es tinta con un umbral global de Otsu. En una
foto de cuaderno **rayado**, de bajo contraste, eso se rompe:

| | Fracción de la imagen que Otsu llama tinta |
|---|---|
| Recortes hechos a mano (los del CER 0.2480) | 0.111 |
| Líneas compuestas de UJIpenchars2 | 0.062 |
| **Foto de página completa** | **0.217 y 0.350** |

Con una quinta parte de la página marcada como tinta, todo lo que se apoya
en esa máscara queda contaminado. Aclarar la foto **no** lo arregla: Otsu
escala junto con el histograma (probado, el CER empeora a 0.6440).

### La medición de punta a punta

Sobre la hoja de 8 oraciones en letra de imprenta, con `evaluar_hoja.py`:

| Localizador | CER | Párrafos armados (de 9) |
|---|---|---|
| Otsu, versión original | 0.5780 | 3 |
| Otsu, con `quitar_encuadernado` corregido | 0.5560 | 1 |
| **docTR + cortes por disposición** | **0.3248** | **9** ✓ |
| Recortes hechos por una persona (meta) | 0.2480 | — |

Las dos últimas filas del cuadro se miden distinto (la última no pasa por
ninguna ubicación automática), así que la comparación justa entre
localizadores es 0.4507 contra 0.3248: **−28 % relativo**.

### Las dos ideas que lo movieron

1. **Detector entrenado en vez de umbral.** docTR con DBNet aprendió qué
   trazo es escritura; sobre la misma foto no pone ni una caja sobre las
   rayas del cuaderno, y sí detecta `¡Atención!`, `vence` y `folio 315`,
   que eran justo las palabras que el recorte por umbral perdía.

2. **La numeración manual como estructura, no como basura.** Los `01`,
   `02`... que la persona escribió al margen se detectan como columna, se
   quitan del texto y se usan como **corte de párrafo**. Eso importa
   porque las 8 reglas de `unir_lineas` leen el texto, así que se caen
   cuando el CER es alto: sin esta señal las 8 oraciones se fusionaban en
   un solo párrafo. La geometría de la página no se degrada con el CER.

Se elige con `HTR_LOCALIZADOR=doctr|otsu`. Los dos se conservan: son
enfoques distintos para el mismo paso, y cuál gana se decide midiendo.

### Lo que queda

La brecha es ahora 0.3248 contra 0.2480. Lo que falta es de dos tipos:

- **Ubicación:** en 2 de los 8 ítems las dos filas del ítem se fusionan en
  una sola banda, y TrOCR recibe dos líneas apiladas.
- **Reconocimiento:** el resto ya no es ubicación. Es el decodificador
  inglés jalando el español (`juez` → `jazz`, `ordenó` → `orders`), que es
  lo que va al Ciclo 4 con LoRA.

---

## 9. Ciclo de texto impreso (spec 001)

Los ciclos anteriores midieron manuscrito. Este mide **texto impreso en
capturas de pantalla** (RF-09) con `evaluar_impreso.py`, y su detalle y sus
límites están en `specs/001-reconocimiento-texto-impreso/resultados.md`.

**Cómo correrlo** (desde la raíz del proyecto, con el set en
`htr/dataset/impreso/capturas/`, que no se versiona):

```bash
docker compose exec servidor-htr pytest                       # suite (sin la de integración)
docker compose exec servidor-htr python evaluar_impreso.py --solo-verificar-set
docker compose exec servidor-htr python evaluar_impreso.py --descargar   # único paso con red
docker compose stop ollama                                    # esperar a que /salud diga "cpu" (~120 s)
docker compose exec servidor-htr python evaluar_impreso.py    # mide sin red; deja el JSON en resultados/
docker compose exec servidor-htr pytest -m integracion        # GPU, pesos y Tika reales
docker compose start ollama
```

La herramienta se niega a medir si Ollama tiene un modelo cargado (lee la
VRAM con `nvidia-smi`: en WSL2 `torch.cuda.mem_get_info` solo ve el propio
proceso) o si el servidor HTR tiene el suyo en la GPU.

**Resultado** (10 capturas, 155 líneas, 05/10/2026):

| # | Candidato | CER | s/página | VRAM (GB) | Acierto en español |
|---|---|---|---|---|---|
| 1 | trocr-large-handwritten (producción) | 0,1208 | 8,52 | 2,15 | 0,0 % |
| 2 | qantev/trocr-large-spanish | 0,0642 | 10,25 | 2,35 | 88,8 % |
| 3 | trocr-large-printed | 0,8401 | 11,72 | 2,35 | 0,6 % |
| 4 | **docTR 1.1.0 completo** | **0,0484** | 0,31 | 0,71 | 14,2 % |
| 5 | Tesseract (vía Tika) | 1,0000 | 0,03 | 0,00 | 0,0 % |

Gana docTR, «listo para integrar para capturas de pantalla»; la línea base no
cumple el criterio (CER > 0,10) y gana un candidato distinto de TrOCR, así que
queda propuesto RF-09 «Parcial» y un cambio de requisito.

**Advertencias**:

* El vocabulario de docTR no incluye á í ó ú ñ ¿ ¡: pierde esas marcas siempre.
* qantev (mejor acierto en español) quedó fuera por 0,25 s sobre el límite de
  10 s; subir el límite no cambia el ganador. Cuál integrar se decide en la spec
  de integración, midiendo también la recuperación en el chat.
* Tesseract da CER 1 porque el Tika desplegado no hace OCR de imágenes
  (`EmptyParser`): es un error de configuración aparte, no la calidad de
  Tesseract.
* Solo capturas de pantalla: sin fotos con celular ni escaneos.

**Estado**: medición hecha y documentada; la integración al pipeline de
ingesta es otra spec y espera a la red de seguridad de pruebas.

---

## 10. Estado

- [x] Entorno aislado del backend, PyTorch en contenedor
- [x] 21 tipografías con cobertura del español verificada + licencias
- [x] Corpus de 2,653 oraciones, sin datos personales
- [x] Generador sintético reproducible y ponderado por estilo
- [x] Set de prueba propio (18 líneas) con ground truth
- [x] **5 modelos evaluados; modelo elegido y justificado**
- [x] Servidor HTTP con GPU, probado de punta a punta
- [x] Cliente y pasos de integración redactados
- [x] Bug de los números de renglón corregido; CER limpio **0.2771**
- [ ] Muestras de varios escritores
- [x] **Integración al backend aplicada y verificada** (16/09)
- [x] **Conflicto de VRAM resuelto** — intercambio por inactividad
      (`HTR_IDLE_TIMEOUT` + `OLLAMA_KEEP_ALIVE`)
- [ ] Fine-tuning con LoRA (Ciclo 4)

> Documentación: `Registro_Indicaciones_2026/` docs **20** (criterios y
> dataset), **22** (resultados del Ciclo 1), **23** (solicitud de
> SPA-Sentences), **17** (estado del arte), **14** (puntos de integración).
