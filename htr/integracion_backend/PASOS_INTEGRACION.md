# Integración del HTR al backend — **APLICADA** el 16/09/2026

> Segunda mitad del **Ciclo 1** de la Fase 4 (cronograma: 28/09–01/10),
> completada el 16/09 — doce días antes de su fecha de inicio.
>
> Este documento era la lista de pasos a aplicar; ahora es el **registro de
> lo aplicado**, para poder auditarlo o revertirlo.

---

## Arquitectura: el HTR es infraestructura, no un microservicio

El servicio sigue **el mismo patrón que Apache Tika** en este proyecto:
contenedor propio que el backend consume por HTTP. No contradice la
decisión de mantener el monolito modular ([doc 21](../../Registro_Indicaciones_2026/21_Aclaracion_Arquitectura_Monolito_vs_Microservicios.md)):
igual que Tika, Qdrant, Redis u Ollama, es infraestructura que la
aplicación consume, no una pieza del dominio propio.

Tres razones concretas para que sea servicio aparte:

1. **GPU:** es el único contenedor, junto con Ollama, que la necesita. El
   backend y el celery-worker siguen sin GPU.
2. **Costo de carga:** el modelo tarda 60–150 s en cargar. Acá se paga una
   vez al arrancar, no en cada proceso ni en cada worker de Celery.
3. **Dependencias:** `torch` + `transformers` pesan ~3 GB. Mantenerlos
   fuera deja liviana la imagen del backend.

---

## Los seis cambios aplicados

### 1 · `backend/app/services/ingesta/htr_service.py` — **nuevo**

Cliente HTTP calcado de `tika_service.py`: misma forma, mismo estilo,
configuración por variable de entorno, `is_available()`, reintentos y
logging.

Detalle propio del HTR: `is_available()` no se conforma con que el
servidor responda — consulta `/salud` y verifica el campo `listo`, porque
el servicio acepta conexiones **antes** de terminar de cargar el modelo.

### 2 · `backend/app/config/config.py`

Agregado junto a `TIKA_SERVER_URL`:

```python
HTR_SERVER_URL = os.getenv("HTR_SERVER_URL", "http://localhost:9100")
HTR_TIMEOUT = int(os.getenv("HTR_TIMEOUT", "300"))
```

### 3 · `backend/app/config/file_config.py`

`ALLOWED_EXTENSIONS` ahora acepta imágenes:

```python
..., '.m4a', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']
```

Y `FILE_TYPE_CODES` recibió sus códigos para Qdrant — **esto es fácil de
olvidar** y sin ello la metadata del vector queda sin tipo de archivo:

```python
'.jpg': 20, '.jpeg': 20, '.png': 21,
'.tif': 22, '.tiff': 22, '.bmp': 23
```

### 4 · `backend/app/services/ingesta/file_management/document_processor.py`

Se agregó `import asyncio` al bloque de imports (no estaba), y la rama de
HTR en `extract_text_from_file()`:

```python
    # Imágenes: reconocimiento de escritura a mano (HTR) en su propio servicio.
    #
    # IMPORTANTE: esta rama va ANTES de la de Tika. Tika también acepta
    # imágenes y las procesaría con Tesseract, que lee texto impreso pero
    # NO manuscrito. Si esta rama quedara después, nunca se ejecutaría.
    if file_extension in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']:
        from app.services.ingesta.htr_service import htr_service
        return await asyncio.to_thread(htr_service.extract_text, content, filename)
```

Dos decisiones ahí:

* **El orden importa.** Va después de la rama de audio y antes de la de
  Tika, por el motivo del comentario.
* **`asyncio.to_thread`** porque `htr_service.extract_text` usa `requests`,
  que es bloqueante. Llamarlo directo dentro de una función `async`
  frenaría el bucle de eventos durante toda la inferencia.

### 5 · `docker-compose.yml` (el principal)

Se agregó el servicio `servidor-htr` con reserva de GPU y volumen
`htr_hf_cache` para los pesos descargados. Además:

* `backend` y `celery-worker` recibieron `HTR_SERVER_URL=http://servidor-htr:9100`
  y `servidor-htr` en su `depends_on`.
* **`ollama` recibió `OLLAMA_KEEP_ALIVE=2m`** — ver la sección de VRAM.

### 6 · `backend/.env`

```
HTR_SERVER_URL=http://servidor-htr:9100
HTR_TIMEOUT=300
```

---

## ⚡ La VRAM: intercambio por inactividad

El problema medido: el HTR retiene **~2.1 GB** y Ollama con `llama3.1:8b`
**~5.5 GB**. Suma **7.6 GB de 8 GB** — entra, pero sin margen para picos.
Si uno expulsa al otro y le toca a Ollama, el chat vuelve a CPU: ~5
minutos por respuesta, el problema que se corrigió el 10/09.

**Solución adoptada: repartir la GPU en el tiempo, no en el espacio.**
Cada servicio la devuelve cuando queda inactivo.

| Servicio | Mecanismo | Valor |
|---|---|---|
| `servidor-htr` | `HTR_IDLE_TIMEOUT` — mueve el modelo a CPU y libera la VRAM | 120 s |
| `ollama` | `OLLAMA_KEEP_ALIVE` — descarga el modelo | 2 m |

Descartada la alternativa de repartir **un** modelo entre GPU y CPU
(*offloading* por capas): obligaría a mover pesos en medio de cada
inferencia y sería mucho más lento que el traslado completo.

### Medición del intercambio

| Momento | VRAM ocupada | Dispositivo |
|---|---:|---|
| Modelo cargado | 2,602 MiB | `cuda` |
| Tras el timeout de inactividad | **440 MiB** | `cpu` |
| Al llegar una petición | 2,634 MiB | `cuda` |

Costo del traslado: **~0.02 s**. La primera petición tras un período
inactivo tardó 0.15 s contra 0.133 s de la siguiente — es decir, el
intercambio es prácticamente gratis, porque mover 558M parámetros de RAM
a VRAM por PCIe es rápido.

El estado se puede consultar en vivo:

```bash
curl http://localhost:9100/salud
# {"listo":true,"dispositivo":"cuda","idle_timeout_s":120,
#  "segundos_sin_uso":2.4,"vram_libre_GB":4.79,...}
```

---

## Verificación realizada

```bash
# 1. Los 8 contenedores arriba
docker compose ps

# 2. El servidor cargó el modelo
curl http://localhost:9100/salud

# 3. El backend ve la configuración
docker compose exec backend python -c "
from app.config.config import HTR_SERVER_URL
from app.config.file_config import ALLOWED_EXTENSIONS, FILE_TYPE_CODES
print(HTR_SERVER_URL, '.jpg' in ALLOWED_EXTENSIONS, FILE_TYPE_CODES['.jpg'])"

# 4. El cliente alcanza el servidor por la red de Docker
docker compose exec backend python -c "
from app.services.ingesta.htr_service import htr_service
print(htr_service.is_available())"

# 5. El flujo real: extract_text_from_file() con una imagen
docker compose exec backend python -c "
import asyncio
from app.services.ingesta.file_management.document_processor import extract_text_from_file
async def m():
    with open('/app/uploads/foto.jpg','rb') as f: c=f.read()
    print(await extract_text_from_file(c, 'foto.jpg', 'image/jpeg'))
asyncio.run(m())"
```

**Resultado:** los cinco pasos pasaron. El paso 5 con una línea ya
recortada devolvió exactamente el mismo texto que la evaluación aislada
(`" American Eltering impiscurable vence` para
`¡Atención! El término improrrogable vence`), lo que confirma que la
cadena es **fiel**: mismo modelo, mismo resultado, ahora accesible desde
el backend.

---

## ⚠️ Limitación conocida: la segmentación

Con una **foto de página completa**, el servidor devolvió 11 líneas de las
cuales varias son basura (`1934`, `1961 62m.`). La segmentación integrada
en `servidor_htr.py` es deliberadamente simple y tropieza con:

* fondo brillante o cargado (en la prueba, un teclado retroiluminado),
* la espiral del cuaderno,
* los renglones impresos del papel,
* oraciones que ocupan dos renglones.

**Esto es alcance del Ciclo 2** ("Investigar preprocesamiento: deskew,
denoise, segmentación"). Con la línea ya recortada el resultado es
correcto, así que **el problema está en la segmentación, no en la
integración ni en el modelo**.

Mientras tanto, `htr/partir_bandas.py` y `htr/recortar_lineas.py` hacen un
trabajo mucho mejor que la versión embebida; consolidar esa lógica dentro
del servidor es la tarea natural del Ciclo 2.

---

## Cómo revertir

```bash
git diff HEAD~1 -- backend/ docker-compose.yml   # ver qué cambió
git checkout HEAD~1 -- backend/app/config/config.py \
    backend/app/config/file_config.py \
    backend/app/services/ingesta/file_management/document_processor.py \
    docker-compose.yml
rm backend/app/services/ingesta/htr_service.py
```

Y quitar las dos líneas de `HTR_*` de `backend/.env`.
