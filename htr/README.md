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
| 🥇 | **`microsoft/trocr-large-handwritten`** | 558M | **0.2868** | 0.8690 | 0.198 | 2.12 GB |
| 🥈 | `qantev/trocr-large-spanish` | 609M | 0.3857 | 0.7738 | 0.378 | 2.32 GB |
| 🥉 | `microsoft/trocr-base-handwritten` | 334M | 0.3953 | 0.9762 | 0.168 | 1.29 GB |
| 4 | `ifesther/trocr-spanish-handwritten` | 334M | 0.6453 | 0.9048 | 0.339 | 1.29 GB |
| 5 | `qantev/trocr-base-spanish` | 385M | 0.6647 | 0.9643 | 0.338 | 1.49 GB |

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
| `microsoft/trocr-*` y los demás modelos | MIT | Sin restricciones |

Las imágenes generadas **no heredan restricción**: ambas licencias
restringen la redistribución de los *archivos de fuente*, no de lo que se
renderiza con ellos. Detalle en `fuentes/ATRIBUCION.md`.

---

## 6. Qué se versiona y qué no

**No se versiona `dataset/`** — ni el sintético, ni Rodrigo (382 MB de
Zenodo), ni las muestras propias. Dos razones distintas:

* Lo generado es **reproducible**: misma semilla, mismas imágenes.
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

**6. 🔴 Bug abierto: los números de renglón se filtran.** En algunos
recortes el número del cuaderno queda pegado al texto (hueco de ~30 px) y
la detección por bloques no lo separa. El modelo lee `IL`, `13`, `15` y
cuenta como error. **Afecta a los 5 modelos por igual, así que el ranking
es válido**, pero los CER absolutos están inflados unos 5–7 puntos: el
valor real de `large_en` probablemente esté cerca de **0.24–0.25**.

**7. ⚠️ HTR y Ollama no caben juntos con holgura.** Medido con
`nvidia-smi`: el servidor HTR retiene **~2.45 GB netos**, Ollama con
`llama3.1:8b` ~5.5 GB. Suma **~7.95 GB de 8 GB**, sin margen para picos.
Si Ollama pierde, el chat vuelve a CPU (~5 min por respuesta). Hay que
resolverlo **antes** de dejar el HTR en el `docker-compose.yml` principal
con `restart: unless-stopped`. Opciones en
`integracion_backend/PASOS_INTEGRACION.md`.

---

## 8. Estado

- [x] Entorno aislado del backend, PyTorch en contenedor
- [x] 21 tipografías con cobertura del español verificada + licencias
- [x] Corpus de 2,653 oraciones, sin datos personales
- [x] Generador sintético reproducible y ponderado por estilo
- [x] Set de prueba propio (18 líneas) con ground truth
- [x] **5 modelos evaluados; modelo elegido y justificado**
- [x] Servidor HTTP con GPU, probado de punta a punta
- [x] Cliente y pasos de integración redactados
- [ ] Corregir el bug de los números de renglón y volver a medir
- [ ] Muestras de varios escritores
- [ ] Aplicar los 6 pasos de integración al backend
- [ ] Resolver el conflicto de VRAM
- [ ] Fine-tuning con LoRA (Ciclo 4)

> Documentación: `Registro_Indicaciones_2026/` docs **20** (criterios y
> dataset), **22** (resultados del Ciclo 1), **23** (solicitud de
> SPA-Sentences), **17** (estado del arte), **14** (puntos de integración).
