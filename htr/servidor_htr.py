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

import torch
from fastapi import FastAPI, HTTPException, Request
from PIL import Image, ImageOps
from starlette.concurrency import run_in_threadpool
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

from segmentacion import segmentar
from unir_lineas import unir

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("htr")

# El modelo es configurable a propósito: la elección se cerró con las
# métricas del Ciclo 1 (ver doc 22) y cambiarla no debe requerir tocar
# código.
MODELO = os.getenv("HTR_MODELO", "microsoft/trocr-large-handwritten")
MAX_TOKENS = int(os.getenv("HTR_MAX_TOKENS", "96"))
MAX_LINEAS = int(os.getenv("HTR_MAX_LINEAS", "60"))
# Franjas verticales para la proyeccion. 4 fue el valor con menor error
# sobre las fotos con conteo conocido (ver doc 25).
FRANJAS = int(os.getenv("HTR_FRANJAS", "4"))

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
    Parte la imagen en líneas, delegando al módulo `segmentacion`.

    Antes había acá una versión simplificada y propia de la segmentación,
    mientras `recortar_lineas.py` tenía otra mejor. Resultado medido el
    16/09/2026 sobre una foto de 22 líneas reales: la de este servidor
    detectaba 5 bandas (y eran basura), la otra 17.

    Tener dos implementaciones de lo mismo garantiza que una quede atrás.
    Ahora las dos importan `segmentacion.py`, que es la única fuente de
    verdad y trae los cuatro arreglos del Ciclo 2: umbral Otsu, detección
    de papel, remoción del encuadernado y proyección por franjas.
    """
    detalle: dict = {}
    lineas = segmentar(imagen, franjas=FRANJAS, max_lineas=MAX_LINEAS,
                       detalle=detalle)
    if detalle:
        logger.info(
            "segmentacion: papel=%s encuadernado=%s otsu=%s -> %d banda(s)",
            detalle.get("papel"), detalle.get("encuadernado_x"),
            detalle.get("umbral_otsu"), detalle.get("bandas", 0),
        )
    return lineas


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

    # Unir los renglones en párrafos. Sin esto el texto sale fragmentado, y
    # un chunk que empieza en "el próximo martes." pierde el sujeto y
    # recupera mal en el RAG. La unión además normaliza los artefactos de
    # espaciado del dataset IAM (el ` .` y las comillas sueltas del final).
    #
    # Medido el 17/09/2026 sobre las 16 líneas de la hoja de prueba:
    #   solo líneas ............ CER 0.2742
    #   + normalización ........ CER 0.2557  (-6.8 %)
    #   + unión en párrafos .... CER 0.2480  (-9.6 %)
    parrafos = unir([t for t in textos if t])

    return {
        "texto": "\n".join(parrafos),
        "lineas": len(lineas),
        "parrafos": len(parrafos),
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
        # exif_transpose es obligatorio: las camaras de celular no rotan
        # los pixeles, guardan la orientacion en EXIF y esperan que el
        # visor la aplique. Pillow NO lo hace solo. Sin esto, una foto
        # tomada en vertical llega de costado y la deteccion de lineas
        # por proyeccion horizontal se derrumba.
        #
        # Medido el 16/09/2026 sobre una foto real con EXIF "90 CW":
        # sin corregir, 4 bandas detectadas de 22 reales (18%);
        # con la correccion, 17 de 22 (77%).
        imagen = ImageOps.exif_transpose(
            Image.open(io.BytesIO(crudo))
        ).convert("RGB")
    except Exception as e:
        raise HTTPException(400, f"No se pudo abrir la imagen: {e}")

    logger.info("Imagen %dx%d recibida", imagen.width, imagen.height)
    # En un hilo aparte: la inferencia es bloqueante y no debe frenar el
    # bucle de eventos de FastAPI.
    resultado = await run_in_threadpool(_reconocer_sincrono, imagen)
    logger.info("HTR: %d línea(s) en %.2fs (%s)",
                resultado["lineas"], resultado["segundos"], resultado["dispositivo"])
    return resultado
