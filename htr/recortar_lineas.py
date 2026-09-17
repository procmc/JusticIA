"""
Recorta las líneas de texto de una foto de página manuscrita.

Necesario porque TrOCR lee UNA LÍNEA recortada por vez: si se le pasa la
foto completa de una página devuelve basura, sin importar qué tan bueno
sea el modelo.

Hace dos cosas en orden:
  1. Detecta el papel dentro de la foto (descarta fondo, ropa, espiral)
     por perfil de brillo por fila y por columna.
  2. Detecta las bandas con tinta por proyección horizontal y recorta
     cada una como una imagen de línea independiente.

Uso:
    .venv/Scripts/python.exe recortar_lineas.py foto.jpg
    .venv/Scripts/python.exe recortar_lineas.py foto.jpg --debug
    .venv/Scripts/python.exe recortar_lineas.py foto.jpg --salida dataset/muestras_propias
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps


def detectar_papel(gris: np.ndarray, margen: float = 0.04) -> tuple[int, int, int, int]:
    """Devuelve (x0, y0, x1, y1) del papel: la zona clara de la foto."""
    # El papel es notablemente más claro que el fondo. Se usa un umbral a
    # medio camino entre el fondo oscuro y el papel.
    umbral = (np.percentile(gris, 10) + np.percentile(gris, 90)) / 2

    filas_claras = (gris > umbral).mean(axis=1)
    cols_claras = (gris > umbral).mean(axis=0)

    # Una fila/columna pertenece al papel si más de la mitad es clara.
    ys = np.flatnonzero(filas_claras > 0.5)
    xs = np.flatnonzero(cols_claras > 0.5)
    if len(ys) == 0 or len(xs) == 0:      # foto sin papel distinguible
        return 0, 0, gris.shape[1], gris.shape[0]

    y0, y1 = int(ys[0]), int(ys[-1])
    x0, x1 = int(xs[0]), int(xs[-1])

    # Se recorta un margen hacia adentro: bordes, sombra y espiral.
    dx = int((x1 - x0) * margen)
    dy = int((y1 - y0) * margen)
    return x0 + dx, y0 + dy, x1 - dx, y1 - dy


def quitar_encuadernado(gris: np.ndarray) -> tuple[int, int]:
    """
    Devuelve (x0, x1) sin la espiral o los agujeros de encuadernado.

    La espiral produce columnas con mucha tinta repartida a lo largo de
    TODA la altura de la página, a diferencia del texto, que se concentra
    en unas pocas bandas. Si no se quita, sus marcas aportan tinta en casi
    cada fila y la detección de líneas por proyección horizontal se rompe:
    fusiona líneas reales y genera líneas falsas en cada agujero.
    """
    alto, ancho = gris.shape
    tinta = gris < (np.percentile(gris, 75) - 28)
    por_columna = tinta.sum(axis=0)

    # Una columna es "estructura" si tiene tinta en buena parte de la altura.
    estructural = por_columna > alto * 0.16

    # Solo se inspecciona el 20% de cada borde: el encuadernado va al margen,
    # nunca en el medio del texto.
    borde = max(int(ancho * 0.20), 1)
    margen = max(int(ancho * 0.012), 4)

    x0 = 0
    for x in range(borde):
        if estructural[x]:
            x0 = x + 1 + margen

    x1 = ancho
    for x in range(ancho - 1, ancho - borde - 1, -1):
        if estructural[x]:
            x1 = x - margen

    if x1 - x0 < ancho * 0.3:          # recorte absurdo: mejor no tocar
        return 0, ancho
    return max(x0, 0), min(x1, ancho)


def detectar_lineas(
    gris: np.ndarray, min_alto: int = 12, hueco_max: int | None = None,
) -> list[tuple[int, int]]:
    """Devuelve las bandas (y_inicio, y_fin) que contienen tinta."""
    # El hueco que separa dos líneas escala con el tamaño de la imagen.
    if hueco_max is None:
        hueco_max = max(int(gris.shape[0] / 70), 6)

    # Tinta = píxeles claramente más oscuros que el papel.
    nivel_papel = np.percentile(gris, 75)
    umbral = nivel_papel - max(28.0, gris.std() * 0.9)
    tinta = gris < umbral

    por_fila = tinta.sum(axis=1)
    if por_fila.max() == 0:
        return []

    # Una fila "tiene texto" si su cantidad de tinta supera un mínimo
    # relativo al máximo de la página (robusto a ruido de fondo).
    activa = por_fila > max(por_fila.max() * 0.06, 3)

    bandas: list[tuple[int, int]] = []
    inicio = None
    hueco = 0
    for y, hay in enumerate(activa):
        if hay:
            if inicio is None:
                inicio = y
            hueco = 0
        elif inicio is not None:
            hueco += 1
            if hueco > hueco_max:                 # se cerró la línea
                bandas.append((inicio, y - hueco))
                inicio = None
                hueco = 0
    if inicio is not None:
        bandas.append((inicio, len(activa) - 1))

    return [(a, b) for a, b in bandas if (b - a) >= min_alto]


def recortar_manual(
    ruta: Path, destino: Path, rangos: list[tuple[int, int]],
    x0: int, x1: int | None,
) -> list[Path]:
    """
    Recorta líneas en coordenadas explícitas de la imagen ORIGINAL.

    Existe porque la detección automática no siempre acierta: fotos con
    fondo cargado, espiral, sombras en el borde del papel, o líneas cuyos
    rasgos descendentes y ascendentes se entrelazan (una "j" que baja hasta
    la línea siguiente). En esos casos el perfil de tinta se mide a mano y
    se pasan los rangos — queda reproducible y auditable.

    Las coordenadas se obtienen del perfil de tinta por fila; ver el bloque
    de diagnóstico del README.
    """
    original = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
    destino.mkdir(parents=True, exist_ok=True)
    der = x1 if x1 is not None else original.width
    base = ruta.stem
    generados: list[Path] = []

    print(f"Recorte manual sobre {original.width}x{original.height}, "
          f"x={x0}..{der}")
    for i, (ya, yb) in enumerate(rangos, start=1):
        linea = original.crop((x0, ya, der, yb))
        salida = destino / f"{base}_linea{i:02d}.jpg"
        linea.save(salida, quality=95)
        generados.append(salida)
        print(f"  línea {i}: y={ya}..{yb}  ->  {linea.width}x{linea.height}  "
              f"{salida.name}")
    return generados


def recortar(
    ruta: Path, destino: Path, debug: bool = False, relleno: int = 14,
) -> list[Path]:
    original = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
    gris_completo = np.array(original.convert("L"), dtype=np.float32)

    x0, y0, x1, y1 = detectar_papel(gris_completo)
    papel = original.crop((x0, y0, x1, y1))
    print(f"Papel detectado: ({x0},{y0})-({x1},{y1})  "
          f"[{x1-x0}x{y1-y0} de {original.width}x{original.height}]")

    # Quitar espiral/agujeros antes de proyectar: si no, arruinan la detección.
    gris_papel = np.array(papel.convert("L"), dtype=np.float32)
    bx0, bx1 = quitar_encuadernado(gris_papel)
    if (bx0, bx1) != (0, papel.width):
        print(f"Encuadernado recortado: x {bx0}..{bx1} "
              f"(se quitaron {papel.width - (bx1 - bx0)} px de margen)")
        papel = papel.crop((bx0, 0, bx1, papel.height))

    gris = np.array(papel.convert("L"), dtype=np.float32)
    bandas = detectar_lineas(gris)
    print(f"Líneas detectadas: {len(bandas)}")

    destino.mkdir(parents=True, exist_ok=True)
    base = ruta.stem
    generados: list[Path] = []

    aceptadas: list[tuple[int, int]] = []
    for ya, yb in bandas:
        arriba = max(ya - relleno, 0)
        abajo = min(yb + relleno, papel.height)

        # Recorte horizontal ajustado a la tinta de esta banda.
        tinta_banda = gris[ya:yb + 1] < (np.percentile(gris, 75) - 28)
        cols = np.flatnonzero(tinta_banda.any(axis=0))
        izq = max(int(cols[0]) - relleno, 0) if len(cols) else 0
        der = min(int(cols[-1]) + relleno, papel.width) if len(cols) else papel.width

        # Una línea de texto ocupa un ancho razonable. Lo muy angosto es
        # ruido (una marca, un resto de encuadernado, una mancha).
        if (der - izq) < papel.width * 0.08:
            print(f"  descartada banda angosta: {der - izq}x{abajo - arriba} px")
            continue

        linea = papel.crop((izq, arriba, der, abajo))
        i = len(aceptadas) + 1
        salida = destino / f"{base}_linea{i:02d}.jpg"
        linea.save(salida, quality=95)
        generados.append(salida)
        aceptadas.append((ya, yb))
        print(f"  línea {i}: {linea.width}x{linea.height} -> {salida.name}")

    bandas = aceptadas

    if debug:
        vista = papel.copy()
        lapiz = ImageDraw.Draw(vista)
        for i, (ya, yb) in enumerate(bandas, start=1):
            lapiz.rectangle([(0, ya), (vista.width - 1, yb)],
                            outline=(220, 30, 30), width=3)
            lapiz.text((6, max(ya - 16, 0)), f"L{i}", fill=(220, 30, 30))
        ruta_debug = destino / f"{base}_deteccion.jpg"
        vista.save(ruta_debug, quality=88)
        print(f"  [debug] {ruta_debug}")

    return generados


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("foto", help="ruta de la foto de la página")
    ap.add_argument("--salida", default="dataset/muestras_propias",
                    help="carpeta destino de las líneas recortadas")
    ap.add_argument("--debug", action="store_true",
                    help="guarda una imagen mostrando qué detectó")
    ap.add_argument("--manual", default=None,
                    help='rangos de fila explícitos, ej: "325-400,393-478"')
    ap.add_argument("--x0", type=int, default=0,
                    help="borde izquierdo del recorte manual")
    ap.add_argument("--x1", type=int, default=None,
                    help="borde derecho del recorte manual (default: ancho)")
    args = ap.parse_args()

    raiz = Path(__file__).parent
    foto = Path(args.foto)
    if not foto.is_absolute():
        foto = (raiz / foto).resolve() if not foto.exists() else foto
    if not foto.exists():
        raise SystemExit(f"No existe la foto: {foto}")

    destino = Path(args.salida)
    if not destino.is_absolute():
        destino = raiz / destino

    if args.manual:
        rangos = []
        for parte in args.manual.split(","):
            a, _, b = parte.strip().partition("-")
            rangos.append((int(a), int(b)))
        lineas = recortar_manual(foto, destino, rangos, args.x0, args.x1)
    else:
        lineas = recortar(foto, destino, debug=args.debug)

    print(f"\n{len(lineas)} línea(s) lista(s) para TrOCR.")
    print("Escribí la transcripción exacta de cada una en un .txt con el "
          "mismo nombre (ground truth).")


if __name__ == "__main__":
    main()
