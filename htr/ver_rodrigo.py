"""
Muestra líneas reales del corpus Rodrigo junto a su transcripción, para
decidir con los ojos si la letra sirve para afinar el modelo.

Rodrigo es de 1545, un solo escribano, caligrafía antigua. El riesgo es
que afinar con esto especialice al modelo en letra del siglo XVI y lo
empeore en letra moderna. Esta herramienta existe para juzgar ese riesgo
antes de gastar una corrida de entrenamiento.

Uso:
    .venv/Scripts/python.exe ver_rodrigo.py --cantidad 8
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).parent
CORPUS = RAIZ / "dataset" / "rodrigo"
ANCHO = 1150


def cargar_transcripciones() -> dict[str, str]:
    texto = {}
    for linea in (CORPUS / "text" / "transcriptions.txt").read_text(
            encoding="utf-8", errors="replace").splitlines():
        if not linea.strip():
            continue
        clave, _, valor = linea.partition(" ")
        texto[clave] = valor
    return texto


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cantidad", type=int, default=8)
    ap.add_argument("--semilla", type=int, default=5)
    ap.add_argument("--particion", default="train",
                    choices=["train", "validation", "test"])
    ap.add_argument("--salida", default="muestra_rodrigo.jpg")
    args = ap.parse_args()

    transcripciones = cargar_transcripciones()
    claves = (CORPUS / "partitions" / f"{args.particion}.txt").read_text(
        encoding="utf-8").split()

    rng = random.Random(args.semilla)
    elegidas = rng.sample(claves, min(args.cantidad, len(claves)))

    bloques = []
    for clave in elegidas:
        ruta = CORPUS / "images" / f"{clave}.png"
        if not ruta.exists():
            continue
        img = Image.open(ruta).convert("RGB")
        escala = min(ANCHO / img.width, 1.0)
        if escala < 1.0:
            img = img.resize((int(img.width * escala), int(img.height * escala)),
                             Image.Resampling.LANCZOS)
        bloques.append((img, clave, transcripciones.get(clave, "(sin transcripción)")))

    etiqueta_h, margen = 34, 12
    alto = sum(i.height + etiqueta_h + margen for i, _, _ in bloques) + margen
    hoja = Image.new("RGB", (ANCHO, alto), (255, 255, 255))
    lapiz = ImageDraw.Draw(hoja)

    y = margen
    for img, clave, texto in bloques:
        hoja.paste(img, (0, y))
        y += img.height + 2
        lapiz.text((4, y), f"{clave}", fill=(150, 150, 160))
        lapiz.text((4, y + 14), f"-> {texto}", fill=(190, 40, 40))
        y += etiqueta_h + margen

    destino = RAIZ / args.salida
    hoja.save(destino, quality=92)
    print(f"{len(bloques)} líneas de '{args.particion}' -> {destino}")
    print(f"({hoja.width}x{hoja.height})")

    # Rasgos de la ortografía de 1545 que no existen en español moderno.
    muestra = " ".join(transcripciones.get(k, "") for k in claves[:4000])
    print("\nRasgos arcaicos en las primeras 4000 líneas:")
    for caracter, nota in [("ç", "cedilla"), ("_", "palabra cortada entre líneas"),
                           ("ſ", "s larga"), ("ũ", "u con virgulilla")]:
        print(f"  '{caracter}' ({nota}): {muestra.count(caracter)} apariciones")


if __name__ == "__main__":
    main()
