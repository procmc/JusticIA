"""
Lector y renderizador del dataset UJIpenchars2.

QUÉ ES Y POR QUÉ IMPORTA
------------------------
UJIpenchars2 (UCI Machine Learning Repository, dataset 177) son **11,640
caracteres manuscritos de 60 escritores distintos**, capturados con lápiz
óptico: 60 escritores × 97 caracteres × 2 repeticiones.

Cubre los dos huecos que el generador con tipografías no puede llenar:

  1. **Variabilidad de trazo humano real.** Una fuente dibuja la `a`
     idéntica siempre; 60 personas la dibujan de 60 maneras.
  2. **Los 14 caracteres que el dataset IAM nunca tuvo:** `ñ Ñ`, las diez
     vocales acentuadas, `ü Ü`, más los signos de apertura `¿` `¡`. El
     modelo base nunca vio una tilde en su entrenamiento.

Y es letra de **imprenta suelta, no cursiva** — que coincide con el caso de
uso real del proyecto, porque en Costa Rica la cursiva ya no se usa.

LICENCIA
--------
**CC BY 4.0**: permite uso comercial y adaptación; solo exige atribución.
La cita requerida está en `fuentes/ATRIBUCION.md` y en el README.

    Prat, F., Castro, M., Llorens, D., Marzal, A., & Vilar, J. (2008).
    UJI Pen Characters (Version 2). UCI Machine Learning Repository.
    https://doi.org/10.24432/C5FG8S

FORMATO DE ORIGEN
-----------------
Es un dataset **online** (secuencias de coordenadas del lápiz), no
imágenes. TrOCR es **offline** (trabaja sobre píxeles), así que hay que
renderizar los trazos. Eso además da control sobre grosor de trazo, color
de tinta y fondo, igual que en `generar_sintetico.py`.

    // ASCII char: a
    WORD a trn_UJI_W01-01
      NUMSTROKES 1
      POINTS 44 # 557 844 550 803 ...

Las unidades son centésimas de milímetro (100 por mm).

LIMITACIÓN HONESTA
------------------
Son **caracteres aislados**, no palabras. Se pueden componer líneas
poniéndolos uno al lado del otro, pero eso no iguala a escritura real: una
persona varía la forma de cada letra según la que viene antes, y las
letras compuestas quedan con espaciado uniforme y sin esa dependencia de
contexto. Es **mejor que las tipografías, peor que escribir de verdad**.

Para que la línea sea creíble hay que tomar los caracteres del **mismo
escritor**: si cada letra viene de una persona distinta, la línea sale con
caligrafías mezcladas y el modelo aprende algo que no existe.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).parent
ARCHIVO = RAIZ / "dataset" / "ujipenchars" / "ujipenchars2.txt"

_RE_WORD = re.compile(r"^WORD\s+(\S+)\s+(\S+)\s*$")
_RE_NUM = re.compile(r"^\s*NUMSTROKES\s+(\d+)")
_RE_PTS = re.compile(r"^\s*POINTS\s+(\d+)\s*#\s*(.*)$")

# Un trazo es una lista de puntos (x, y); un carácter, una lista de trazos.
Trazo = list[tuple[int, int]]
Caracter = list[Trazo]


def cargar(archivo: Path | None = None) -> dict[str, dict[str, list[Caracter]]]:
    """
    Lee el dataset y devuelve {caracter: {escritor: [muestras]}}.

    Cada muestra es una lista de trazos, y cada trazo una lista de (x, y).
    """
    ruta = archivo or ARCHIVO
    if not ruta.exists():
        raise SystemExit(
            f"No existe {ruta}.\n"
            "Bajalo de https://archive.ics.uci.edu/dataset/177/"
            "uji+pen+characters+version+2 y descomprimilo ahí."
        )

    datos: dict[str, dict[str, list[Caracter]]] = defaultdict(lambda: defaultdict(list))
    caracter = escritor = None
    trazos: Caracter = []
    faltan = 0

    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _RE_WORD.match(linea)
        if m:
            # Se cierra la muestra anterior antes de empezar la nueva.
            if caracter is not None and trazos:
                datos[caracter][escritor].append(trazos)
            caracter, etiqueta = m.group(1), m.group(2)
            # "trn_UJI_W01-01" -> escritor "UJI_W01"
            escritor = etiqueta.split("_", 1)[-1].rsplit("-", 1)[0]
            trazos, faltan = [], 0
            continue

        m = _RE_NUM.match(linea)
        if m:
            faltan = int(m.group(1))
            continue

        m = _RE_PTS.match(linea)
        if m and faltan > 0:
            nums = [int(v) for v in m.group(2).split()]
            trazos.append(list(zip(nums[0::2], nums[1::2])))
            faltan -= 1

    if caracter is not None and trazos:
        datos[caracter][escritor].append(trazos)

    return {c: dict(w) for c, w in datos.items()}


def dibujar(muestra: Caracter, alto: int = 64, grosor: int = 3,
            margen: int = 4, tinta: tuple[int, int, int] = (20, 30, 90)
            ) -> Image.Image:
    """
    Renderiza un carácter a imagen, escalado a `alto` píxeles.

    Devuelve una imagen RGB con fondo blanco. El ancho sale de la
    proporción original del trazo, así que una `i` queda angosta y una `m`
    ancha — igual que en escritura real.
    """
    puntos = [p for trazo in muestra for p in trazo]
    if not puntos:
        return Image.new("RGB", (alto, alto), (255, 255, 255))

    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    ancho_u = max(x1 - x0, 1)
    alto_u = max(y1 - y0, 1)

    escala = (alto - 2 * margen) / alto_u
    ancho = max(int(ancho_u * escala) + 2 * margen, alto // 4)

    img = Image.new("RGB", (ancho, alto), (255, 255, 255))
    lapiz = ImageDraw.Draw(img)
    for trazo in muestra:
        pts = [(margen + (x - x0) * escala, margen + (y - y0) * escala)
               for x, y in trazo]
        if len(pts) == 1:
            r = grosor / 2
            lapiz.ellipse([pts[0][0] - r, pts[0][1] - r,
                           pts[0][0] + r, pts[0][1] + r], fill=tinta)
        else:
            lapiz.line(pts, fill=tinta, width=grosor, joint="curve")
    return img


def resumen(datos: dict[str, dict[str, list[Caracter]]]) -> None:
    """Imprime qué contiene el dataset cargado."""
    escritores = sorted({w for wr in datos.values() for w in wr})
    total = sum(len(m) for wr in datos.values() for m in wr.values())
    print(f"  caracteres distintos : {len(datos)}")
    print(f"  escritores           : {len(escritores)}")
    print(f"  muestras totales     : {total}")

    espanol = "ñÑáéíóúÁÉÍÓÚüÜ¿¡"
    print("\n  Caracteres del español presentes:")
    for c in espanol:
        if c in datos:
            n = sum(len(m) for m in datos[c].values())
            print(f"   '{c}'  {n:>4} muestras de {len(datos[c])} escritores")
        else:
            print(f"   '{c}'  AUSENTE")


# --------------------------------------------------------------------------
# Métricas tipográficas por escritor
# --------------------------------------------------------------------------
#
# Las coordenadas Y del dataset ya vienen alineadas: medido sobre el
# escritor UJI_W01, las letras de altura x (`e`, `o`, `n`) terminan en
# y≈1300, las ascendentes (`b`, `d`, `h`) comparten esa misma base y suben,
# y las descendentes (`p`, `g`, `y`, `j`) bajan hasta y≈1750. O sea que
# **el dataset ya trae la línea base codificada** y no hay que estimarla.
#
# Pero no es perfecto: medido sobre las 2,520 muestras no descendentes de
# los 60 escritores, el **5.6 %** se desvía de su propia línea base más de
# 0.4 alturas x. Eso se ve: una `c` minúscula dibujada a la altura de una
# `C`. Para datos de entrenamiento es tinta mal etiquetada — el modelo
# aprendería que esa forma se llama `c` cuando parece `C`. Así que cada
# muestra se ancla a la línea base del escritor antes de dibujarla.

# Letras sin ascendente ni descendente: su borde inferior ES la línea base y
# su altura ES la altura x. De acá salen las métricas del escritor.
_ALTURA_X = "aceimnorsuvwxz"

# Descendentes: su borde inferior queda por debajo de la línea base.
_DESCENDENTES = "gjpqy¿¡()$"

# Signos que cuelgan de arriba: anclarlos por abajo los tiraría al piso.
_VOLADOS = ('"', "'")

# Signos de media altura.
_MEDIOS = "-<>"


def _mediana(valores: list[float]) -> float | None:
    if not valores:
        return None
    ordenados = sorted(valores)
    return ordenados[len(ordenados) // 2]


def metricas(datos: dict, escritor: str) -> tuple[float, float, float] | None:
    """
    Devuelve `(linea_base, altura_x, profundidad_descendente)` del escritor,
    en unidades del dataset.

    Se usan medianas y no promedios: con el 5.6 % de muestras desviadas, un
    promedio se corre y la mediana no.
    """
    bases, alturas = [], []
    for c in _ALTURA_X:
        for m in datos.get(c, {}).get(escritor, []):
            ys = [p[1] for trazo in m for p in trazo]
            bases.append(max(ys))
            alturas.append(max(ys) - min(ys))

    base, altura_x = _mediana(bases), _mediana(alturas)
    if base is None or not altura_x:
        return None

    fondos = [max(p[1] for trazo in m for p in trazo)
              for c in "gpqy" for m in datos.get(c, {}).get(escritor, [])]
    profundidad = (_mediana(fondos) or base + altura_x * 0.8) - base

    return base, float(altura_x), max(profundidad, altura_x * 0.3)


def _anclaje(ch: str, muestra: Caracter, base: float, altura_x: float,
             profundidad: float) -> float:
    """
    Desplazamiento en Y que pone la muestra sobre la línea base del escritor.

    Cada grupo se ancla por el borde que le corresponde: una `o` por abajo,
    una `p` por la cola, una comilla por arriba, un guion por el medio.
    """
    ys = [p[1] for trazo in muestra for p in trazo]
    y_min, y_max = min(ys), max(ys)

    if ch in _VOLADOS:
        return (base - altura_x * 1.55) - y_min
    if ch in _MEDIOS:
        return (base - altura_x * 0.45) - (y_min + y_max) / 2
    if ch in _DESCENDENTES:
        return (base + profundidad) - y_max
    return base - y_max


def escritores_completos(datos: dict, texto: str) -> list[str]:
    """Escritores que tienen todos los caracteres que `texto` necesita."""
    necesarios = set(texto) - {" "}
    candidatos: set[str] | None = None
    for c in necesarios:
        con_c = set(datos.get(c, {}).keys())
        candidatos = con_c if candidatos is None else (candidatos & con_c)
        if not candidatos:
            return []
    return sorted(candidatos or [])


def componer_linea(texto: str, datos: dict, escritor: str, rng,
                   alto: int = 96, grosor: int = 3,
                   tinta: tuple[int, int, int] = (20, 30, 90),
                   fondo: tuple[int, int, int] | None = (255, 255, 255),
                   metrica: tuple[float, float, float] | None = None,
                   ) -> Image.Image | None:
    """
    Compone la imagen de una línea escribiendo `texto` con los trazos reales
    de un escritor. Devuelve `None` si al escritor le falta algún carácter.

    UN SOLO ESCRITOR POR LÍNEA: si cada letra viniera de una persona
    distinta, la línea saldría con caligrafías mezcladas y el modelo
    aprendería una escritura que no existe.

    Con `fondo=None` devuelve RGBA con el fondo transparente y recortado
    al trazo, que es lo que espera la cadena de efectos de
    `generar_sintetico.py` (inclinación, ondulado, papel, foco).

    ESCALA POR MÉTRICAS, NO POR EXTREMOS. La escala sale de la altura x del
    escritor, no del rango Y de esta línea en particular. Con los extremos,
    una línea que tenga una `j` (que abarca de la tilde a la cola) se
    dibujaría chica y la misma frase sin `j` grande: dos tamaños para la
    misma mano. Con las métricas, todas las líneas del escritor salen
    parejas y las de escritores distintos quedan comparables entre sí.
    """
    met = metrica or metricas(datos, escritor)
    if met is None:
        return None
    base, altura_x, profundidad = met

    # Se elige una muestra por carácter (hay 2 repeticiones por escritor).
    piezas: list[tuple[str, Caracter] | None] = []
    for ch in texto:
        if ch == " ":
            piezas.append(None)
            continue
        muestras = datos.get(ch, {}).get(escritor, [])
        if not muestras:
            return None
        piezas.append((ch, rng.choice(muestras)))

    # Reparto vertical en alturas x: ~2.3 arriba de la línea base (las
    # ascendentes llegan a 1.7, pero una mayúscula acentuada como `Á` sube
    # más) y ~1.1 abajo para las colas.
    escala = (alto * 0.28) / altura_x
    base_px = alto * 0.72
    margen = max(int(alto * 0.06), 3)

    # Red de seguridad. Si a un escritor la tinta no le cabe con la escala
    # de sus métricas, se encoge la línea entera hasta que entre. Recortar
    # el trazo contra el borde sería otra forma de tinta mal etiquetada: el
    # modelo vería una `á` sin tilde con la etiqueta `á`.
    anclados = [(y + _anclaje(ch, m, base, altura_x, profundidad) - base)
                for ch, m in (p for p in piezas if p)
                for trazo in m for _, y in trazo]
    arriba, abajo = min(anclados), max(anclados)
    if base_px + arriba * escala < margen:
        escala = min(escala, (base_px - margen) / -arriba)
    if base_px + abajo * escala > alto - margen:
        escala = min(escala, (alto - margen - base_px) / abajo)

    ref = datos.get("o", {}).get(escritor) or datos.get("a", {}).get(escritor)
    if ref:
        xs_ref = [p[0] for trazo in ref[0] for p in trazo]
        ancho_espacio = int((max(xs_ref) - min(xs_ref)) * escala * 0.9)
    else:
        ancho_espacio = int(altura_x * escala * 0.8)

    separacion = max(int(altura_x * escala * 0.14), 2)
    anchos: list[int] = []
    for pieza in piezas:
        if pieza is None:
            anchos.append(ancho_espacio)
            continue
        xs = [p[0] for trazo in pieza[1] for p in trazo]
        anchos.append(int((max(xs) - min(xs)) * escala) + separacion)

    ancho_img = max(sum(anchos) + 2 * margen, alto)
    if fondo is None:
        img = Image.new("RGBA", (ancho_img, alto), (0, 0, 0, 0))
        color = tinta + (255,)
    else:
        img = Image.new("RGB", (ancho_img, alto), fondo)
        color = tinta
    lapiz = ImageDraw.Draw(img)

    x_cursor = float(margen)
    for pieza, ancho_pieza in zip(piezas, anchos):
        if pieza is None:
            x_cursor += ancho_pieza
            continue
        ch, muestra = pieza
        x_min = min(p[0] for trazo in muestra for p in trazo)
        dy = _anclaje(ch, muestra, base, altura_x, profundidad)
        # Temblor: nadie escribe exactamente sobre la raya.
        tembleque = rng.uniform(-altura_x * 0.07, altura_x * 0.07)

        for trazo in muestra:
            pts = [(x_cursor + (x - x_min) * escala,
                    base_px + (y + dy + tembleque - base) * escala)
                   for x, y in trazo]
            if len(pts) == 1:
                r = grosor / 2
                lapiz.ellipse([pts[0][0] - r, pts[0][1] - r,
                               pts[0][0] + r, pts[0][1] + r], fill=color)
            else:
                lapiz.line(pts, fill=color, width=grosor, joint="curve")
        x_cursor += ancho_pieza

    if fondo is None:
        caja = img.getbbox()
        if caja is None:
            return None
        img = img.crop(caja)
    return img


if __name__ == "__main__":
    d = cargar()
    resumen(d)
