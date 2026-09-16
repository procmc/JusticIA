"""
Servidor HTTP de reconocimiento de manuscrito (HTR).

Sigue el MISMO patrón que Apache Tika en este proyecto: un contenedor
aparte con su propio servicio, que el backend consume por HTTP. No es un
microservicio de dominio — es infraestructura, igual que Tika, Qdrant,
Redis u Ollama (ver doc 21 sobre la distinción).

Motivos para que sea un servicio aparte y no código dentro del backend:

  1. **GPU.** Solo este contenedor necesita la reserva de GPU. El backend
     y el celery-worker siguen sin GPU, como hoy.
  2. **Costo de carga.** Cargar el modelo toma entre 60 y 150 segundos.
     Acá se paga UNA vez al arrancar; si viviera dentro del backend se
     pagaría en cada arranque del proceso y en cada worker.
  3. **Aislamiento de dependencias.** torch + transformers pesan ~3 GB.
     Mantenerlos fuera del backend deja esa imagen liviana.
  4. **Smart App Control.** PyTorch nativo en Windows está bloqueado en la
     PC de trabajo; acá corre en Linux.

INTERCAMBIO DE GPU POR INACTIVIDAD
----------------------------------
La GPU tiene 8 GB y no alcanza para el modelo de HTR (~2.1 GB) más Ollama
con llama3.1:8b (~5.5 GB) con holgura. En vez de repartir un modelo entre
GPU y CPU —que obligaría a mover pesos en medio de cada inferencia y sería
lentísimo— se reparte **en el tiempo**:

  * El modelo sube a GPU en la primera petición.
  * Tras `HTR_IDLE_TIMEOUT` segundos sin peticiones, baja a CPU y se
    libera la VRAM.
  * La siguiente petición lo vuelve a subir.

Del otro lado, Ollama hace lo propio con `OLLAMA_KEEP_ALIVE`. Así ninguno
de los dos expulsa al otro, y el chat nunca cae a CPU (el problema que se
corrigió el 10/09, cuando una respuesta tardaba ~5 minutos).

Costo: la primera petición después de un período inactivo paga el
traslado (unos segundos). Con `HTR_IDLE_TIMEOUT=0` el modelo se queda
siempre en GPU y no hay intercambio.

Arranque:
    docker compose -f docker-compose.htr.yml up servidor-htr

Endpoints:
    GET  /salud   -> estado, dispositivo actual y VRAM
    POST /htr     -> imagen (bytes) -> texto reconocido
"""

from __future__ import annotations

import io
import logging
import os
import threading
import time

import numpy as np
import torch
from fastapi import FastAPI, HTTPException, Request
from PIL import Image
from starlette.concurrency import run_in_threadpool
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("htr")

# El modelo es configurable a propósito: la elección se cerró con las
# métricas del Ciclo 1 (ver doc 22) y cambiarla no debe requerir tocar
# código.
MODELO = os.getenv("HTR_MODELO", "microsoft/trocr-large-handwritten")
MAX_TOKENS = int(os.getenv("HTR_MAX_TOKENS", "96"))
MAX_LINEAS = int(os.getenv("HTR_MAX_LINEAS", "60"))

# Segundos sin peticiones antes de devolver la GPU. 0 = no devolverla.
IDLE_TIMEOUT = int(os.getenv("HTR_IDLE_TIMEOUT", "120"))

app = FastAPI(title="JusticIA · Servidor HTR", version="0.2.0")

_procesador: TrOCRProcessor | None = None
_modelo: VisionEncoderDecoderModel | None = None
_dispositivo = "cpu"
_hay_gpu = False
_ultimo_uso = 0.0

# Un solo candado protege tanto el traslado de dispositivo como la
# inferencia: dos peticiones simultáneas en GPU podrían agotar la VRAM, y
# mover el modelo mientras se infiere lo rompería.
_candado = threading.Lock()


def _mover(destino: str) -> None:
    """Mueve el modelo a 'cuda' o 'cpu' y libera la VRAM si corresponde."""
    global _dispositivo
    if _modelo is None or _dispositivo == destino:
        return
    t0 = time.perf_counter()
    _modelo.to(destino)
    if destino == "cpu":
        torch.cuda.empty_cache()      # sin esto la VRAM no se devuelve
    else:
        torch.cuda.synchronize()
    _dispositivo = destino
    logger.info("Modelo movido a %s en %.1fs", destino, time.perf_counter() - t0)


def _vigilante_inactividad() -> None:
    """Devuelve la GPU cuando el servicio queda sin uso."""
    while True:
        time.sleep(5)
        if IDLE_TIMEOUT <= 0 or not _hay_gpu:
            continue
        if _dispositivo != "cuda":
            continue
        if (time.time() - _ultimo_uso) < IDLE_TIMEOUT:
            continue
        # No se fuerza: si hay una inferencia en curso se espera al próximo ciclo.
        if _candado.acquire(blocking=False):
            try:
                if _dispositivo == "cuda" and (time.time() - _ultimo_uso) >= IDLE_TIMEOUT:
                    logger.info("Sin uso por %ds: devolviendo la GPU", IDLE_TIMEOUT)
                    _mover("cpu")
            finally:
                _candado.release()


@app.on_event("startup")
def cargar_modelo() -> None:
    global _procesador, _modelo, _hay_gpu, _ultimo_uso

    _hay_gpu = torch.cuda.is_available()
    logger.info("Cargando %s (GPU disponible: %s) ...", MODELO, _hay_gpu)
    t0 = time.perf_counter()

    _procesador = TrOCRProcessor.from_pretrained(MODELO)
    _modelo = VisionEncoderDecoderModel.from_pretrained(MODELO).eval()

    if _hay_gpu:
        _mover("cuda")
        # Calentamiento: la primera inferencia paga la inicialización de
        # CUDA/cuDNN. Se hace acá para que no la pague una petición real.
        dummy = Image.new("RGB", (384, 96), (250, 250, 248))
        pix = _procesador(images=dummy, return_tensors="pt").pixel_values.to("cuda")
        with torch.no_grad():
            _modelo.generate(pix, max_new_tokens=4)
        torch.cuda.synchronize()

    _ultimo_uso = time.time()
    logger.info("Modelo listo en %.1fs (dispositivo=%s, idle_timeout=%ds)",
                time.perf_counter() - t0, _dispositivo, IDLE_TIMEOUT)

    if _hay_gpu and IDLE_TIMEOUT > 0:
        threading.Thread(target=_vigilante_inactividad, daemon=True).start()


@app.get("/salud")
def salud() -> dict:
    listo = _modelo is not None
    info: dict = {
        "listo": listo,
        "modelo": MODELO,
        "dispositivo": _dispositivo,
        "gpu_disponible": _hay_gpu,
        "idle_timeout_s": IDLE_TIMEOUT,
        "segundos_sin_uso": round(time.time() - _ultimo_uso, 1) if listo else None,
    }
    if _hay_gpu:
        libre, total = torch.cuda.mem_get_info()
        info["vram_libre_GB"] = round(libre / 1024**3, 2)
        info["vram_total_GB"] = round(total / 1024**3, 2)
    return info


def separar_lineas(imagen: Image.Image) -> list[Image.Image]:
    """
    Separa una imagen en líneas de texto por proyección horizontal de tinta.

    TrOCR reconoce UNA línea por vez: pasarle una página completa devuelve
    basura por bueno que sea el modelo. Si no detecta más de una banda,
    devuelve la imagen tal cual (ya venía recortada).

    Nota: esta segmentación es deliberadamente simple. Los casos difíciles
    (espiral del cuaderno, fondo oscuro, rasgos que unen renglones) son
    alcance del Ciclo 2.
    """
    gris = np.array(imagen.convert("L"), dtype=np.float32)
    if gris.size == 0:
        return [imagen]

    nivel_papel = float(np.percentile(gris, 75))
    tinta = gris < (nivel_papel - max(28.0, float(gris.std()) * 0.9))
    por_fila = tinta.sum(axis=1)
    if por_fila.max() == 0:
        return [imagen]

    activa = por_fila > max(por_fila.max() * 0.06, 3)
    hueco_max = max(int(gris.shape[0] / 70), 6)

    bandas: list[tuple[int, int]] = []
    inicio, hueco = None, 0
    for y, hay in enumerate(activa):
        if hay:
            if inicio is None:
                inicio = y
            hueco = 0
        elif inicio is not None:
            hueco += 1
            if hueco > hueco_max:
                bandas.append((inicio, y - hueco))
                inicio, hueco = None, 0
    if inicio is not None:
        bandas.append((inicio, len(activa) - 1))

    bandas = [(a, b) for a, b in bandas if (b - a) >= 12][:MAX_LINEAS]
    if len(bandas) <= 1:
        return [imagen]

    relleno = 10
    return [
        imagen.crop((0, max(a - relleno, 0), imagen.width,
                     min(b + relleno, imagen.height)))
        for a, b in bandas
    ]


def _reconocer_sincrono(imagen: Image.Image) -> dict:
    """Trabajo bloqueante: se corre en un hilo aparte, con el candado tomado."""
    global _ultimo_uso

    with _candado:
        if _hay_gpu:
            _mover("cuda")          # puede haber estado en CPU por inactividad

        lineas = separar_lineas(imagen)
        t0 = time.perf_counter()
        textos: list[str] = []
        for linea in lineas:
            pix = _procesador(images=linea, return_tensors="pt").pixel_values.to(_dispositivo)
            with torch.no_grad():
                ids = _modelo.generate(pix, max_new_tokens=MAX_TOKENS)
            textos.append(_procesador.batch_decode(ids, skip_special_tokens=True)[0].strip())
        segundos = time.perf_counter() - t0
        _ultimo_uso = time.time()

    return {
        "texto": "\n".join(t for t in textos if t),
        "lineas": len(lineas),
        "modelo": MODELO,
        "dispositivo": _dispositivo,
        "segundos": round(segundos, 3),
    }


@app.post("/htr")
async def reconocer(peticion: Request) -> dict:
    if _modelo is None:
        raise HTTPException(503, "El modelo todavía no terminó de cargar")

    crudo = await peticion.body()
    if not crudo:
        raise HTTPException(400, "Cuerpo vacío: se espera una imagen en bytes")

    try:
        imagen = Image.open(io.BytesIO(crudo)).convert("RGB")
    except Exception as e:
        raise HTTPException(400, f"No se pudo abrir la imagen: {e}")

    logger.info("Imagen %dx%d recibida", imagen.width, imagen.height)
    # En un hilo aparte: la inferencia es bloqueante y no debe frenar el
    # bucle de eventos de FastAPI.
    resultado = await run_in_threadpool(_reconocer_sincrono, imagen)
    logger.info("HTR: %d línea(s) en %.2fs (%s)",
                resultado["lineas"], resultado["segundos"], resultado["dispositivo"])
    return resultado
