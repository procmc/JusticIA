"""
Recorta líneas de una foto de cuaderno donde cada oración ocupa DOS
renglones.

Por qué hace falta además de recortar_lineas.py: la proyección horizontal
detecta la oración completa como una sola banda, porque los rasgos
descendentes de la primera línea (la `j` de "juez", la `g` de "diligencia")
invaden la zona de la segunda y no queda ninguna fila sin tinta entre
ambas.

La solución es partir cada banda por su **valle de tinta**: la fila con
menos tinta dentro de la banda, que es donde se separan las dos líneas
aunque no llegue a cero.

Uso:
    .venv/Scripts/python.exe partir_bandas.py foto.jpg --por-banda 2 \
        --y0 650 --y1 2500 --x0 250 --x1 1850 --saltar 1
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

RAIZ = Path(__file__).parent


def bandas_de_tinta(perfil: np.ndarray, minimo: int, hueco_max: int,
                    alto_min: int) -> list[tuple[int, int]]:
    activa = perfil > minimo
    bandas: list[tuple[int, int]] = []
    ini, hueco = None, 0
    for y, hay in enumerate(activa):
        if hay:
            if ini is None:
                ini = y
            hueco = 0
        elif ini is not None:
            hueco += 1
            if hueco > hueco_max:
                bandas.append((ini, y - hueco))
                ini, hueco = None, 0
    if ini is not None:
        bandas.append((ini, len(activa) - 1))
    return [(a, b) for a, b in bandas if (b - a) >= alto_min]


def partir_por_valle(perfil: np.ndarray, a: int, b: int, partes: int
                     ) -> list[tuple[int, int]]:
    """Parte la banda [a,b] en `partes` cortando por los valles de tinta."""
    if partes <= 1:
        return [(a, b)]

    cortes = [a]
    for k in range(1, partes):
        # Se busca el valle cerca de donde tocaría el corte proporcional,
        # con una ventana del 30% del tramo para no irse a los extremos.
        centro = a + (b - a) * k // partes
        margen = max(int((b - a) / partes * 0.30), 4)
        ini, fin = max(centro - margen, a + 3), min(centro + margen, b - 3)
        if fin <= ini:
            cortes.append(centro)
            continue
        valle = ini + int(np.argmin(perfil[ini:fin]))
        cortes.append(valle)
    cortes.append(b)
    return [(cortes[i], cortes[i + 1]) for i in range(partes)]


def recorte_horizontal(tinta_linea: np.ndarray, ancho: int,
                       zona_margen: int = 0, hueco_numero: int = 28
                       ) -> tuple[int, int]:
    """
    Devuelve (izq, der) de la línea, descartando el número de renglón.

    Los números al margen ("01", "02") son un bloque angosto seguido de un
    hueco ancho antes del texto. No hay un borde izquierdo único que sirva
    para toda la hoja: las líneas de continuación arrancan más a la
    izquierda que los propios números. Así que se detecta por forma.
    """
    cols = tinta_linea.sum(axis=0)
    activas = np.flatnonzero(cols > 0)
    if len(activas) == 0:
        return 0, ancho

    # Bloques de tinta separados por huecos de al menos 25 px.
    bloques, ini, prev = [], activas[0], activas[0]
    for x in activas[1:]:
        if x - prev > 25:
            bloques.append((ini, prev))
            ini = x
        prev = x
    bloques.append((ini, prev))

    # Si el primer bloque es angosto (un número de dos dígitos) y el hueco
    # que sigue es grande, se descarta.
    if len(bloques) > 1:
        (a0, b0), (a1, _) = bloques[0], bloques[1]
        if (b0 - a0) < 90 and (a1 - b0) > 30:
            return int(a1) - 10, int(activas[-1]) + 10

    # Regla de respaldo: el número puede quedar pegado al texto (hueco de
    # ~30 px) y entonces la detección por bloques lo mete en el primer
    # bloque. Se busca el HUECO MÁS ANCHO dentro de la zona del margen: si
    # supera el umbral, es la separación entre el número y el texto.
    if zona_margen > 0:
        limite = min(int(activas[0]) + zona_margen, len(cols))
        vacias = cols[:limite] == 0
        mejor_ancho, mejor_fin = 0, None
        x = int(activas[0])
        while x < limite:
            if vacias[x]:
                ini = x
                while x < limite and vacias[x]:
                    x += 1
                if (x - ini) > mejor_ancho:
                    mejor_ancho, mejor_fin = x - ini, x
            else:
                x += 1
        if mejor_fin is not None and mejor_ancho >= hueco_numero:
            return int(mejor_fin) - 8, int(activas[-1]) + 10

    return int(activas[0]) - 10, int(activas[-1]) + 10


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("foto")
    ap.add_argument("--renglones", type=int, default=0,
                    help="TOTAL de renglones escritos en la zona analizada. "
                         "Es el dato más confiable: uno sabe cuántas líneas "
                         "escribió. Con 0 se estima por altura mediana.")
    ap.add_argument("--y0", type=int, default=0)
    ap.add_argument("--y1", type=int, default=0, help="0 = alto de la imagen")
    ap.add_argument("--x0", type=int, default=0)
    ap.add_argument("--x1", type=int, default=0, help="0 = ancho de la imagen")
    ap.add_argument("--saltar", type=int, default=0,
                    help="bandas iniciales a descartar (p. ej. el encabezado)")
    ap.add_argument("--umbral", type=int, default=75,
                    help="cuánto más oscura que el papel debe ser la tinta")
    ap.add_argument("--salida", default="dataset/muestras_propias")
    ap.add_argument("--prefijo", default="hoja")
    ap.add_argument("--zona-numero", type=int, default=0,
                    help="px desde el inicio de la tinta donde buscar el "
                         "número de renglón para descartarlo (0 = no buscar)")
    ap.add_argument("--hueco-numero", type=int, default=28,
                    help="hueco mínimo que separa el número del texto")
    args = ap.parse_args()

    ruta = Path(args.foto)
    if not ruta.is_absolute():
        ruta = RAIZ / ruta
    original = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")

    y1 = args.y1 or original.height
    x1 = args.x1 or original.width
    recorte = original.crop((args.x0, args.y0, x1, y1))
    gris = np.array(recorte.convert("L"), dtype=np.float32)

    tinta = gris < (np.percentile(gris, 85) - args.umbral)
    perfil = tinta.sum(axis=1).astype(float)

    bandas = bandas_de_tinta(perfil, minimo=8, hueco_max=9, alto_min=15)
    print(f"Zona analizada: x={args.x0}..{x1}  y={args.y0}..{y1}")
    print(f"Bandas de oración detectadas: {len(bandas)}")
    if args.saltar:
        print(f"  se descartan las primeras {args.saltar} (encabezado)")
        bandas = bandas[args.saltar:]

    destino = Path(args.salida)
    if not destino.is_absolute():
        destino = RAIZ / destino
    destino.mkdir(parents=True, exist_ok=True)

    # Reparto ADAPTATIVO. No todas las bandas traen la misma cantidad de
    # renglones: en esta hoja la oración 01 quedó separada en dos bandas
    # (había hueco entre sus renglones) mientras las otras se fusionaron.
    # Un número fijo de partes rompe las que ya estaban bien, así que se
    # estima cuántos renglones trae cada banda por su altura contra la
    # mediana.
    # La mediana no sirve como "altura de un renglón" cuando la mayoría de
    # las bandas ya traen dos: la mediana misma es una banda doble. El dato
    # confiable es cuántos renglones se escribieron, así que se reparte el
    # total en proporción a la altura de cada banda.
    total_alto = sum(b - a for a, b in bandas)
    if args.renglones:
        unidad = total_alto / args.renglones
        print(f"Renglones esperados: {args.renglones} -> "
              f"altura de un renglón ~= {unidad:.0f} px")
    else:
        alturas = sorted(b - a for a, b in bandas)
        unidad = alturas[len(alturas) // 2]
        print(f"Sin --renglones: se usa la mediana ({unidad} px)")

    renglones = []
    for a, b in bandas:
        partes = max(round((b - a) / unidad), 1) if unidad else 1
        renglones.extend(partir_por_valle(perfil, a, b, partes))
    print(f"Renglones obtenidos: {len(renglones)}")
    if args.renglones and len(renglones) != args.renglones:
        print(f"  [!] no coincide con los {args.renglones} esperados: "
              f"revisá el control visual antes de seguir")

    n = 0
    for idx, (ya, yb) in enumerate(renglones, start=1):
        if True:
            relleno = 6
            arriba = max(ya - relleno, 0)
            abajo = min(yb + relleno, recorte.height)
            izq, der = recorte_horizontal(
                tinta[arriba:abajo], recorte.width,
                zona_margen=args.zona_numero, hueco_numero=args.hueco_numero)
            izq = max(izq, 0)
            der = min(der, recorte.width)
            linea = recorte.crop((izq, arriba, der, abajo))
            n += 1
            nombre = f"{args.prefijo}_r{idx:02d}.jpg"
            linea.save(destino / nombre, quality=95)
            print(f"  renglón {idx:02d}: "
                  f"{linea.width}x{linea.height} -> {nombre}")

    # Vista de control: qué se cortó y dónde.
    vista = recorte.copy()
    lapiz = ImageDraw.Draw(vista)
    for idx, (ya, yb) in enumerate(renglones, start=1):
        lapiz.rectangle([(0, ya), (vista.width - 1, yb)],
                        outline=(220, 30, 30), width=4)
        lapiz.text((6, ya + 2), f"r{idx}", fill=(220, 30, 30))
    vista.save(destino / f"{args.prefijo}_corte.jpg", quality=85)
    print(f"\n{n} renglones recortados. Control visual: "
          f"{args.prefijo}_corte.jpg")


if __name__ == "__main__":
    main()
