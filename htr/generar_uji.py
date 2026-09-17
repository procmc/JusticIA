"""
Generador de líneas manuscritas a partir de UJIpenchars2.

QUÉ RESUELVE
------------
`generar_sintetico.py` dibuja las oraciones del corpus con 21 tipografías.
Eso da variedad de forma, pero una fuente escribe la `a` idéntica siempre.
Acá las letras son **trazos de puño y letra de 60 personas reales**, así
que la misma oración sale distinta en cada una — que es justo la variación
que el modelo tiene que aprender a tolerar.

Y cubre el hueco que el modelo base no tiene: `ñ Ñ`, las vocales
acentuadas, `ü Ü` y los signos `¿ ¡`. El dataset IAM con el que se entrenó
`trocr-large-handwritten` es inglés y nunca vio una tilde. Medido el
17/09/2026 sobre caracteres aislados, el modelo acertó 9 de 45 en ASCII y
**0 de 45 en los caracteres del español**; el patrón de fallo fue claro:
`ñ` -> `n.` y `é` -> `e '`. El codificador sí ve la tinta de la tilde, pero
el decodificador no sabe que la marca y la letra de abajo son un solo
carácter. Eso es exactamente lo que estas líneas van a enseñar.

LO QUE NO ES
------------
Letras aisladas puestas una al lado de la otra no igualan a escritura
corrida: una persona deforma cada letra según la que viene antes, y acá el
espaciado es regular y sin esa dependencia de contexto. Es **mejor que las
tipografías y peor que escribir de verdad**, y hay que decirlo cuando se
reporte el resultado.

PARTICIÓN POR ESCRITOR
----------------------
El set de validación se arma con escritores **reservados**, no con líneas
tomadas al azar. Si la misma mano estuviera en entrenamiento y en
validación, el CER de validación mediría qué tan bien el modelo memorizó
esa caligrafía, no qué tan bien generaliza a una mano nueva — que es el
caso real: cada expediente que llegue viene de alguien que el modelo nunca
vio.

Uso:
    python generar_uji.py --cantidad 3000
    python generar_uji.py --cantidad 20 --hoja        # hoja de revisión

Salida:
    dataset/uji_lineas/imagenes/*.jpg
    dataset/uji_lineas/etiquetas.csv   (archivo, texto, escritor, particion)

Atribución obligatoria por la licencia CC BY 4.0 del dataset: ver
`fuentes/ATRIBUCION.md`.
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import ujipenchars as uji
from generar_sintetico import TINTAS, cargar_corpus, componer, inclinar, ondular

RAIZ = Path(__file__).parent
SALIDA = RAIZ / "dataset" / "uji_lineas"

# Escritores reservados para validación (ver "PARTICIÓN POR ESCRITOR").
# 10 % de 60 es 6, tomados uno cada diez: W01, W11, W21, W31, W41, W51.
#
# Muestreo sistemático y no los últimos seis. Primero se tomaron los últimos
# por orden alfabético, y salió un set sesgado: esos seis escritores hacen
# las mayúsculas más chicas que el promedio (mediana 1.34 alturas x contra
# 1.51 del resto, y UPV_W57 dibuja la `E` igual de alta que la `e`). El
# modelo fallaba `Se` -> `se` en 59 de 234 líneas y buena parte de eso era
# el set, no el modelo. Uno cada diez reparte el sesgo a lo largo de la
# lista y sigue sin depender de la semilla.
PASO_VAL = 10


def preparar(datos: dict) -> tuple[list[str], dict[str, tuple]]:
    """Lista de escritores y sus métricas tipográficas, calculadas una vez."""
    escritores = sorted({w for wr in datos.values() for w in wr})
    metricas = {}
    for w in escritores:
        m = uji.metricas(datos, w)
        if m is not None:
            metricas[w] = m
    return [w for w in escritores if w in metricas], metricas


def generar(cantidad: int, semilla: int, alto_base: int = 96) -> list[dict]:
    rng = random.Random(semilla)
    np.random.seed(semilla)

    datos = uji.cargar()
    escritores, metricas = preparar(datos)
    oraciones = cargar_corpus()

    val = set(escritores[::PASO_VAL])
    print(f"Escritores : {len(escritores)}  "
          f"({len(escritores) - len(val)} train / {len(val)} val reservados)")
    print(f"Validación : {', '.join(sorted(val))}")

    destino = SALIDA / "imagenes"
    destino.mkdir(parents=True, exist_ok=True)
    print(f"Salida     : {destino}")
    print(f"Semilla    : {semilla}  (reproducible)\n")

    # Cache: la misma oración le sirve a los mismos escritores siempre.
    posibles: dict[str, list[str]] = {}
    filas: list[dict] = []
    sin_escritor = 0

    for i in range(cantidad):
        texto = rng.choice(oraciones)
        if texto not in posibles:
            posibles[texto] = [w for w in uji.escritores_completos(datos, texto)
                               if w in metricas]
        candidatos = posibles[texto]
        if not candidatos:
            sin_escritor += 1
            continue

        escritor = rng.choice(candidatos)
        trazo = uji.componer_linea(
            texto, datos, escritor, rng,
            alto=rng.randint(alto_base - 16, alto_base + 24),
            grosor=rng.randint(2, 4),
            tinta=rng.choice(TINTAS),
            fondo=None,                      # RGBA, para la cadena de efectos
            metrica=metricas[escritor],
        )
        if trazo is None:
            sin_escritor += 1
            continue

        # Misma cadena que el corpus con tipografías: inclinación del
        # renglón, ondulado de la línea base, papel con grano, foco y
        # iluminación de cámara. Está medida y validada, no hay razón para
        # tener una segunda versión.
        img = componer(ondular(inclinar(trazo, rng), rng), rng)

        nombre = f"uji_{i:06d}.jpg"
        img.save(destino / nombre, quality=rng.randint(72, 94),
                 subsampling=rng.choice([0, 2]))
        filas.append({
            "archivo": nombre,
            "texto": texto,
            "escritor": escritor,
            "particion": "val" if escritor in val else "train",
        })

        if (i + 1) % 250 == 0 or i + 1 == cantidad:
            print(f"  {i + 1}/{cantidad}")

    csv_salida = SALIDA / "etiquetas.csv"
    with csv_salida.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["archivo", "texto", "escritor",
                                           "particion"])
        w.writeheader()
        w.writerows(filas)

    n_val = sum(1 for f in filas if f["particion"] == "val")
    print(f"\nListo: {len(filas)} imágenes "
          f"({len(filas) - n_val} train / {n_val} val)")
    if sin_escritor:
        print(f"Descartadas: {sin_escritor} (ningún escritor tenía todos "
              f"los caracteres de la oración)")
    print(f"Etiquetas: {csv_salida}")
    return filas


def hoja_revision(filas: list[dict], destino: Path) -> None:
    """Pega las imágenes generadas en una sola hoja, para revisarlas a ojo."""
    imgs = [(f, Image.open(SALIDA / "imagenes" / f["archivo"])) for f in filas]
    ancho = max(i.width for _, i in imgs) + 8
    alto = sum(i.height + 20 for _, i in imgs) + 8
    hoja = Image.new("RGB", (ancho, alto), (255, 255, 255))
    lapiz = ImageDraw.Draw(hoja)
    y = 4
    for fila, img in imgs:
        lapiz.text((4, y), f"{fila['escritor']} · {fila['particion']} · "
                           f"{fila['texto'][:70]}", fill=(180, 30, 30))
        y += 18
        hoja.paste(img, (4, y))
        y += img.height + 2
    hoja.save(destino, quality=92)
    print(f"Hoja de revisión: {destino}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cantidad", type=int, default=2000,
                    help="cuántas líneas generar (por omisión 2000)")
    ap.add_argument("--semilla", type=int, default=42,
                    help="semilla, para que la corrida sea reproducible")
    ap.add_argument("--hoja", action="store_true",
                    help="además armar una hoja con todas para revisarlas")
    args = ap.parse_args()

    filas = generar(args.cantidad, args.semilla)
    if args.hoja and filas:
        hoja_revision(filas[:24], SALIDA / "revision.jpg")


if __name__ == "__main__":
    main()
