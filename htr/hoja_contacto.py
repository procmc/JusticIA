"""
Arma una hoja de contacto con muestras del dataset sintético, para
inspección visual rápida de la calidad generada.

Uso:
    .venv/Scripts/python.exe hoja_contacto.py --filas 10
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).parent
DATASET = RAIZ / "dataset" / "sintetico"
ANCHO = 1100


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--filas", type=int, default=10)
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--salida", default="hoja_contacto.jpg")
    args = ap.parse_args()

    with (DATASET / "etiquetas.csv").open(encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))

    rng = random.Random(args.semilla)
    muestra = rng.sample(filas, min(args.filas, len(filas)))

    recortes = []
    for fila in muestra:
        img = Image.open(DATASET / "imagenes" / fila["archivo"]).convert("RGB")
        escala = min(ANCHO / img.width, 1.0)
        if escala < 1.0:
            img = img.resize((int(img.width * escala), int(img.height * escala)),
                             Image.Resampling.LANCZOS)
        recortes.append((img, fila["fuente"]))

    margen, etiqueta_h = 10, 16
    alto = sum(i.height + margen + etiqueta_h for i, _ in recortes) + margen
    hoja = Image.new("RGB", (ANCHO, alto), (255, 255, 255))
    lapiz = ImageDraw.Draw(hoja)

    y = margen
    for img, fuente in recortes:
        lapiz.text((4, y), fuente, fill=(150, 150, 160))
        y += etiqueta_h
        hoja.paste(img, (0, y))
        y += img.height + margen

    destino = RAIZ / args.salida
    hoja.save(destino, quality=92)
    print(f"{len(recortes)} muestras -> {destino}  ({hoja.width}x{hoja.height})")


if __name__ == "__main__":
    main()
