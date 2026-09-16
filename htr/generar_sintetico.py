"""
Generador de manuscrito sintético en español para fine-tuning de TrOCR.

Produce imágenes de UNA LÍNEA de texto (el formato que TrOCR espera) a
partir del corpus de `corpus/oraciones_es.txt`, renderizadas con las
tipografías manuscritas de `fuentes/` (licencia SIL OFL).

Para que no parezcan texto tipografiado se aplica, en cadena:
  1. temblor de línea base (por carácter en imprenta, por palabra en cursiva)
  2. inclinación variable del trazo (cada persona escribe con otra pendiente)
  3. ondulación de la línea base (la mano no sigue una recta)
  4. papel con ruido, tono cálido y renglón tenue ocasional
  5. tinta de color variable (negro, azul, azul oscuro)
  6. desenfoque y variación de brillo/contraste (foto de celular)
  7. rotación leve de toda la línea (hoja no alineada)

IMPORTANTE — metodología: esto genera SOLO las particiones de
entrenamiento y validación. El set de PRUEBA debe ser letra humana real
y moderna; medir el CER contra sintético daría un número engañoso.

Uso:
    .venv/Scripts/python.exe generar_sintetico.py --cantidad 500
    .venv/Scripts/python.exe generar_sintetico.py --cantidad 20 --semilla 7
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

RAIZ = Path(__file__).parent
CORPUS = RAIZ / "corpus" / "oraciones_es.txt"
FUENTES = RAIZ / "fuentes"
SALIDA = RAIZ / "dataset" / "sintetico"

# Las cursivas ligan las letras: si se dibujan carácter por carácter se
# rompe el enlace. Se renderizan por palabra para conservarlo.
CURSIVAS = {
    "Caveat[wght].ttf", "DancingScript[wght].ttf", "BadScript-Regular.ttf",
    "MarckScript-Regular.ttf", "PetitFormalScript-Regular.ttf",
    "Allura-Regular.ttf", "Cedarville-Cursive.ttf",
    "HomemadeApple-Regular.ttf",
}

TRAZO_GRUESO = {
    "CaveatBrush-Regular.ttf", "Sriracha-Regular.ttf",
    "RockSalt-Regular.ttf", "PermanentMarker-Regular.ttf",
}

# DATO DE DOMINIO (encargado, 15/09/2026): en Costa Rica la cursiva ligada
# ya no se enseña en las escuelas ni se usa a nivel general. El caso real
# del proyecto es LETRA DE IMPRENTA A MANO.
#
# Por eso el muestreo de tipografías está ponderado: entrenar con 8 de 21
# fuentes cursivas gastaría capacidad del modelo en una distribución que
# no va a encontrar. Se les deja peso bajo (no cero) por si aparecen
# documentos de archivo escritos por generaciones anteriores.
PESO_ESTILO = {"imprenta": 10, "trazo grueso": 4, "cursiva": 1}

TINTAS = [
    (18, 18, 22),     # negro de bolígrafo
    (24, 34, 92),     # azul clásico
    (12, 28, 64),     # azul oscuro
    (40, 40, 48),     # grafito
]


def cargar_corpus() -> list[str]:
    """Lee todos los .txt de corpus/ (el manual y los generados)."""
    lineas: list[str] = []
    # El set de prueba NO entra al entrenamiento: si se entrena con las
    # mismas oraciones que se usan para medir, el CER sale falsamente bajo
    # (contaminacion del set de prueba). Ademas ese archivo tiene formato
    # "estilo|numero|texto", que se renderizaria literal.
    EXCLUIR = {"set_prueba_manuscrito.txt"}
    archivos = sorted(a for a in (RAIZ / "corpus").glob("*.txt")
                      if a.name not in EXCLUIR)
    for archivo in archivos:
        for cruda in archivo.read_text(encoding="utf-8").splitlines():
            texto = cruda.strip()
            if texto and not texto.startswith("#"):
                lineas.append(texto)
    if not lineas:
        raise SystemExit(f"Sin oraciones en {RAIZ / 'corpus'}")
    print(f"Corpus : {len(lineas)} oraciones de "
          f"{len(archivos)} archivo(s): {', '.join(a.name for a in archivos)}")
    return lineas


def estilo_de(nombre: str) -> str:
    if nombre in CURSIVAS:
        return "cursiva"
    if nombre in TRAZO_GRUESO:
        return "trazo grueso"
    return "imprenta"


def cargar_fuentes() -> tuple[list[Path], list[int]]:
    """Devuelve las fuentes y su peso de muestreo según el estilo."""
    rutas = sorted(FUENTES.glob("*.ttf"))
    if not rutas:
        raise SystemExit(
            f"No hay fuentes en {FUENTES}. Corré primero descargar_fuentes.py"
        )
    pesos = [PESO_ESTILO[estilo_de(r.name)] for r in rutas]

    resumen: dict[str, int] = {}
    for r in rutas:
        resumen[estilo_de(r.name)] = resumen.get(estilo_de(r.name), 0) + 1
    total = sum(pesos)
    detalle = ", ".join(
        f"{e}: {n} fuentes ({PESO_ESTILO[e] * n * 100 // total}%)"
        for e, n in sorted(resumen.items())
    )
    print(f"Fuentes: {len(rutas)} tipografías OFL/Apache — {detalle}")
    return rutas, pesos


def _fuente(ruta: Path, tamano: int, rng: random.Random) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(ruta), tamano)
    # Las fuentes variables permiten variar el grosor del trazo.
    if "[wght]" in ruta.name:
        try:
            f.set_variation_by_axes([rng.uniform(400, 700)])
        except Exception:
            pass
    return f


def dibujar_trazo(texto: str, ruta_fuente: Path, rng: random.Random) -> Image.Image:
    """Dibuja el texto en tinta sobre fondo transparente, con temblor."""
    tamano = rng.randint(38, 58)
    fuente = _fuente(ruta_fuente, tamano, rng)
    tinta = rng.choice(TINTAS)

    # Lienzo holgado: después se recorta al contenido real.
    ancho = int(len(texto) * tamano * 0.85) + 300
    alto = tamano * 5
    lienzo = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    lapiz = ImageDraw.Draw(lienzo)

    x = 100.0
    y_base = alto // 2
    temblor = rng.uniform(1.2, 3.8)          # cuánto "baila" la línea base

    if ruta_fuente.name in CURSIVAS:
        # Por palabra: conserva el ligado interno de la cursiva.
        for palabra in texto.split(" "):
            dy = rng.uniform(-temblor, temblor)
            lapiz.text((x, y_base + dy), palabra, font=fuente, fill=tinta + (255,))
            x += lapiz.textlength(palabra, font=fuente)
            x += lapiz.textlength(" ", font=fuente) * rng.uniform(0.8, 1.5)
    else:
        # Por carácter: máximo temblor, propio de la letra de imprenta a mano.
        for caracter in texto:
            dy = rng.uniform(-temblor, temblor)
            lapiz.text((x, y_base + dy), caracter, font=fuente, fill=tinta + (255,))
            avance = lapiz.textlength(caracter, font=fuente)
            x += avance * rng.uniform(0.94, 1.06)   # espaciado irregular

    caja = lienzo.getbbox()
    if caja is None:
        raise ValueError(f"No se dibujó nada para: {texto[:40]!r}")
    return lienzo.crop(caja)


def inclinar(img: Image.Image, rng: random.Random) -> Image.Image:
    """Inclina el trazo: la pendiente de la escritura varía por persona."""
    pendiente = rng.uniform(-0.28, 0.16)
    extra = int(abs(pendiente) * img.height) + 2
    ancho = img.width + extra
    desplace = extra if pendiente < 0 else 0
    return img.transform(
        (ancho, img.height),
        Image.Transform.AFFINE,
        (1, pendiente, -desplace - pendiente * img.height, 0, 1, 0),
        resample=Image.Resampling.BICUBIC,
    )


def ondular(img: Image.Image, rng: random.Random) -> Image.Image:
    """Ondula la línea base: la mano no sigue una recta perfecta."""
    arr = np.array(img)
    alto, ancho = arr.shape[:2]
    amplitud = rng.uniform(0.8, 3.0)
    frecuencia = rng.uniform(0.6, 2.0) * 2 * np.pi / max(ancho, 1)
    fase = rng.uniform(0, 2 * np.pi)
    corrimientos = (amplitud * np.sin(np.arange(ancho) * frecuencia + fase)).astype(int)

    salida = np.zeros_like(arr)
    for x in range(ancho):
        salida[:, x] = np.roll(arr[:, x], int(corrimientos[x]), axis=0)
    return Image.fromarray(salida)


def papel(tamano: tuple[int, int], rng: random.Random) -> Image.Image:
    """Fondo de papel: tono cálido, ruido de grano y renglón tenue a veces."""
    ancho, alto = tamano
    base = rng.randint(238, 252)
    fondo = np.full((alto, ancho, 3), base, dtype=np.int16)
    fondo[:, :, 2] -= rng.randint(0, 8)            # papel ligeramente cálido
    grano = np.random.normal(0, rng.uniform(1.5, 5.0), fondo.shape)
    fondo += grano.astype(np.int16)
    img = Image.fromarray(np.clip(fondo, 0, 255).astype(np.uint8), "RGB")

    if rng.random() < 0.35:                         # renglón de cuaderno
        lapiz = ImageDraw.Draw(img)
        y = int(alto * rng.uniform(0.72, 0.86))
        gris = rng.randint(186, 214)
        lapiz.line([(0, y), (ancho, y)], fill=(gris, gris, gris + 6), width=1)
    return img


def componer(trazo: Image.Image, rng: random.Random) -> Image.Image:
    """Pega el trazo sobre el papel y aplica efectos de captura."""
    margen_x = rng.randint(14, 44)
    margen_y = rng.randint(12, 30)
    lienzo = papel(
        (trazo.width + margen_x * 2, trazo.height + margen_y * 2), rng
    )
    lienzo.paste(trazo, (margen_x, margen_y), trazo)

    # Hoja no perfectamente alineada con la cámara.
    if rng.random() < 0.7:
        lienzo = lienzo.rotate(
            rng.uniform(-1.6, 1.6), resample=Image.Resampling.BICUBIC,
            expand=True, fillcolor=(246, 244, 238),
        )

    # Foco y iluminación del celular.
    lienzo = lienzo.filter(ImageFilter.GaussianBlur(rng.uniform(0.2, 0.9)))
    lienzo = ImageEnhance.Brightness(lienzo).enhance(rng.uniform(0.88, 1.10))
    lienzo = ImageEnhance.Contrast(lienzo).enhance(rng.uniform(0.85, 1.25))

    # Normalización de altura: TrOCR trabaja con líneas, no con páginas.
    alto_final = rng.randint(72, 108)
    escala = alto_final / lienzo.height
    return lienzo.resize(
        (max(int(lienzo.width * escala), 8), alto_final),
        Image.Resampling.LANCZOS,
    )


def generar(cantidad: int, semilla: int) -> None:
    rng = random.Random(semilla)
    np.random.seed(semilla)

    oraciones = cargar_corpus()
    fuentes, pesos = cargar_fuentes()
    destino_img = SALIDA / "imagenes"
    destino_img.mkdir(parents=True, exist_ok=True)

    print(f"Salida : {destino_img}")
    print(f"Semilla: {semilla}  (reproducible)\n")

    filas = []
    fallos = 0
    for i in range(cantidad):
        texto = rng.choice(oraciones)
        ruta_fuente = rng.choices(fuentes, weights=pesos, k=1)[0]
        try:
            img = componer(ondular(inclinar(dibujar_trazo(texto, ruta_fuente, rng), rng), rng), rng)
        except Exception as e:
            fallos += 1
            print(f"  [!] fallo en {ruta_fuente.name}: {type(e).__name__}: {e}")
            continue

        # JPEG a propósito: es el formato de una foto de celular, y sus
        # artefactos de compresión son aumentación realista sin costo.
        nombre = f"sint_{i:06d}.jpg"
        img.save(destino_img / nombre, quality=rng.randint(72, 94),
                 subsampling=rng.choice([0, 2]))

        # 90/10: el set de prueba NO es sintético (ver nota de metodología).
        filas.append({
            "archivo": nombre,
            "texto": texto,
            "fuente": ruta_fuente.name,
            "particion": "val" if rng.random() < 0.10 else "train",
        })

        if (i + 1) % 100 == 0 or i + 1 == cantidad:
            print(f"  {i + 1}/{cantidad} imágenes")

    csv_salida = SALIDA / "etiquetas.csv"
    with csv_salida.open("w", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(
            fh, fieldnames=["archivo", "texto", "fuente", "particion"]
        )
        escritor.writeheader()
        escritor.writerows(filas)

    n_train = sum(1 for f in filas if f["particion"] == "train")
    n_val = len(filas) - n_train
    print(f"\nListo: {len(filas)} imágenes  ({n_train} train / {n_val} val)")
    if fallos:
        print(f"Fallos: {fallos}")
    print(f"Etiquetas: {csv_salida}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cantidad", type=int, default=200,
                    help="cuántas imágenes generar (default 200)")
    ap.add_argument("--semilla", type=int, default=42,
                    help="semilla para reproducibilidad (default 42)")
    args = ap.parse_args()
    generar(args.cantidad, args.semilla)


if __name__ == "__main__":
    main()
