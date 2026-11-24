"""
Paso a paso con una captura real: de la imagen al texto.
Compone, con las imagenes que genera htr/ilustrar_pipeline.py, una lamina de
cuatro pasos con muy poco texto, pensada para explicarla de viva voz.

Uso (local):
    py htr_paso_a_paso.py [carpeta_con_la_salida_de_ilustrar_pipeline]
Output: output/htr_paso_a_paso.png
"""

import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ORIGEN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../htr/dataset/paginas/ilustracion_captura")
FUENTES = "C:/Windows/Fonts/"
TEXTO, GRIS, FONDO = "#1f2937", "#6b7280", "#ffffff"
AZUL, VERDE, MORADO, NARANJA = "#2563eb", "#16a34a", "#9333ea", "#ea580c"


def fuente(nombre, tam):
    return ImageFont.truetype(FUENTES + nombre, tam)


F_NUM, F_TIT, F_SUB = fuente("segoeuib.ttf", 40), fuente("segoeuib.ttf", 34), fuente("segoeui.ttf", 26)
F_LEC = fuente("consola.ttf", 24)

ANCHO_PANEL, ALTO_PANEL, SEP, MARGEN = 760, 740, 90, 50
ARRIBA = 170


def panel_base(lienzo, k, titulo, subtitulo, color):
    x = MARGEN + k * (ANCHO_PANEL + SEP)
    d = ImageDraw.Draw(lienzo)
    d.rounded_rectangle([x, ARRIBA, x + ANCHO_PANEL, ARRIBA + ALTO_PANEL], 24, fill="#f8fafc", outline="#e2e8f0", width=3)
    d.ellipse([x + 24, 30, x + 94, 100], fill=color)
    d.text((x + 59, 65), str(k + 1), font=F_NUM, fill="white", anchor="mm")
    d.text((x + 116, 52), titulo, font=F_TIT, fill=TEXTO, anchor="lm")
    d.text((x + 116, 100), subtitulo, font=F_SUB, fill=GRIS, anchor="lm")
    return x


def pegar(lienzo, ruta, x, y, ancho):
    img = Image.open(ruta).convert("RGB")
    img = img.resize((ancho, int(img.height * ancho / img.width)), Image.LANCZOS)
    lienzo.paste(img, (x, y))
    ImageDraw.Draw(lienzo).rectangle([x, y, x + img.width, y + img.height], outline="#cbd5e1", width=2)
    return img.height


def main():
    lecturas = json.loads((ORIGEN / "lecturas.json").read_text(encoding="utf-8"))
    final = (ORIGEN / "texto_final.txt").read_text(encoding="utf-8")
    n_panel = 4
    ancho = MARGEN * 2 + n_panel * ANCHO_PANEL + (n_panel - 1) * SEP
    lienzo = Image.new("RGB", (ancho, ARRIBA + ALTO_PANEL + 50), FONDO)
    d = ImageDraw.Draw(lienzo)
    interior = ANCHO_PANEL - 60

    # 1. La captura
    x = panel_base(lienzo, 0, "La captura", "Imagen subida por el usuario", AZUL)
    pegar(lienzo, ORIGEN / "p1_original.jpg", x + 30, ARRIBA + 40, interior)

    # 2. Renglones
    x = panel_base(lienzo, 1, "Localiza los renglones", "docTR · detector entrenado", MORADO)
    pegar(lienzo, ORIGEN / "p3_renglones.jpg", x + 30, ARRIBA + 40, interior)

    # 3. Lectura de cada renglon
    x = panel_base(lienzo, 2, "Lee cada renglón", "TrOCR · un renglón por vez", VERDE)
    y = ARRIBA + 40
    for k in range(1, 5):
        alto = pegar(lienzo, ORIGEN / "recortes" / f"{k + 1:02d}.png", x + 30, y, interior)
        y += alto + 6
        texto = lecturas[k].replace(" ,", ",").replace(" .", ".").replace(" ( ", " (").replace(" )", ")")
        for linea in textwrap.wrap(texto, 54)[:2]:
            d.text((x + 30, y), linea, font=F_LEC, fill=VERDE)
            y += 31
        y += 26
    d.text((x + ANCHO_PANEL // 2, ARRIBA + ALTO_PANEL - 34), "Repite lo mismo en cada renglón", font=F_SUB, fill=GRIS, anchor="mm")

    # 4. Texto final
    x = panel_base(lienzo, 3, "Une en párrafos", "Texto listo para indexar", NARANJA)
    y = ARRIBA + 44
    for parrafo in final.split("\n")[:2]:
        for linea in textwrap.wrap(parrafo, 52)[:8 if y < ARRIBA + 300 else 9]:
            d.text((x + 30, y), linea, font=F_LEC, fill=TEXTO)
            y += 32
        y += 22
    d.text((x + 30, y + 4), "…", font=F_LEC, fill=GRIS)

    # Flechas entre paneles
    for k in range(n_panel - 1):
        xa = MARGEN + (k + 1) * ANCHO_PANEL + k * SEP + 12
        ym = ARRIBA + ALTO_PANEL // 2
        d.line([xa, ym, xa + SEP - 24, ym], fill="#94a3b8", width=6)
        d.polygon([(xa + SEP - 24, ym - 18), (xa + SEP - 24, ym + 18), (xa + SEP - 2, ym)], fill="#94a3b8")

    lienzo.save("output/htr_paso_a_paso.png")
    print("Lamina generada: output/htr_paso_a_paso.png", lienzo.size)


main()
