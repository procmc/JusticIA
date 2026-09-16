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

Arranque:
    docker compose -f docker-compose.htr.yml up servidor-htr

Endpoints:
    GET  /salud   -> estado y modelo cargado
    POST /htr     -> imagen (bytes) -> texto reconocido
"""

from __future__ import annotations

import io
import logging
import os
import time

import numpy as np
import torch
from fastapi import FastAPI, HTTPException, Request
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("htr")

# El modelo es configurable a propósito: la elección definitiva se cierra
# con las métricas del Ciclo 1 y no debe requerir tocar el código.
MODELO = os.getenv("HTR_MODELO", "qantev/trocr-large-spanish")
MAX_TOKENS = int(os.getenv("HTR_MAX_TOKENS", "96"))
MAX_LINEAS = int(os.getenv("HTR_MAX_LINEAS", "60"))

app = FastAPI(title="JusticIA · Servidor HTR", version="0.1.0")

_estado: dict = {"procesador": None, "modelo": None, "dispositivo": None}


@app.on_event("startup")
def cargar_modelo() -> None:
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Cargando %s en %s ...", MODELO, dispositivo)
    t0 = time.perf_counter()

    procesador = TrOCRProcessor.from_pretrained(MODELO)
    modelo = VisionEncoderDecoderModel.from_pretrained(MODELO).to(dispositivo).eval()

    # Calentamiento: la primera inferencia paga la inicialización de
    # CUDA/cuDNN. Se hace acá para que la primera petición real no la pague.
    dummy = Image.new("RGB", (384, 96), (250, 250, 248))
    pix = procesador(images=dummy, return_tensors="pt").pixel_values.to(dispositivo)
    with torch.no_grad():
        modelo.generate(pix, max_new_tokens=4)
    if dispositivo == "cuda":
        torch.cuda.synchronize()

    _estado.update(procesador=procesador, modelo=modelo, dispositivo=dispositivo)
    logger.info("Modelo listo en %.1fs (dispositivo=%s)",
                time.perf_counter() - t0, dispositivo)


@app.get("/salud")
def salud() -> dict:
    listo = _estado["modelo"] is not None
    info = {
        "listo": listo,
        "modelo": MODELO,
        "dispositivo": _estado["dispositivo"],
    }
    if listo and _estado["dispositivo"] == "cuda":
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


@app.post("/htr")
async def reconocer(peticion: Request) -> dict:
    if _estado["modelo"] is None:
        raise HTTPException(503, "El modelo todavía no terminó de cargar")

    crudo = await peticion.body()
    if not crudo:
        raise HTTPException(400, "Cuerpo vacío: se espera una imagen en bytes")

    try:
        imagen = Image.open(io.BytesIO(crudo)).convert("RGB")
    except Exception as e:
        raise HTTPException(400, f"No se pudo abrir la imagen: {e}")

    procesador = _estado["procesador"]
    modelo = _estado["modelo"]
    dispositivo = _estado["dispositivo"]

    lineas = separar_lineas(imagen)
    logger.info("Imagen %dx%d -> %d línea(s)", imagen.width, imagen.height, len(lineas))

    t0 = time.perf_counter()
    textos: list[str] = []
    for linea in lineas:
        pix = procesador(images=linea, return_tensors="pt").pixel_values.to(dispositivo)
        with torch.no_grad():
            ids = modelo.generate(pix, max_new_tokens=MAX_TOKENS)
        textos.append(procesador.batch_decode(ids, skip_special_tokens=True)[0].strip())

    return {
        "texto": "\n".join(t for t in textos if t),
        "lineas": len(lineas),
        "modelo": MODELO,
        "segundos": round(time.perf_counter() - t0, 3),
    }
