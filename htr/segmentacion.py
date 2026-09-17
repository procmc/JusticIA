"""
Segmentación de líneas de texto manuscrito — módulo único.

POR QUÉ EXISTE ESTE ARCHIVO
---------------------------
La lógica de segmentación estaba duplicada: `recortar_lineas.py` tenía una
versión buena (detección de papel, remoción de encuadernado) y
`servidor_htr.py` una simplificada. Medido el 16/09/2026 sobre una foto de
22 líneas reales:

    recortar_lineas.py ... 17 bandas (77 %)
    servidor_htr.py ......  5 bandas, y eran basura

Es el clásico problema de tener dos implementaciones de lo mismo: se
arregla una y la otra queda atrás. Este módulo es la **única fuente de
verdad**; el servidor y los scripts lo importan.

LOS CUATRO ARREGLOS DEL CICLO 2
-------------------------------
1. **Umbral adaptativo (Otsu)** en vez de absoluto. La fórmula anterior
   `percentil_75 − max(28, std×0.9)` daba umbral 81 con `std=23`:
   demasiado oscuro, solo captaba la espiral negra y el escritorio, no la
   tinta azul del lápiz.

2. **Detección de la región de papel.** Sin esto, el fondo de la foto
   (madera, ropa, un teclado retroiluminado) entra en la proyección y
   distorsiona todas las estadísticas.

3. **Remoción del encuadernado.** La espiral aporta tinta en casi todas
   las filas: fusiona líneas reales y genera falsas en cada agujero.

4. **Proyección por franjas** para tolerar curvatura. Cuando la hoja no
   está plana, una línea de texto sube o baja a lo largo del ancho y la
   proyección sobre el ancho completo la difumina. Proyectar por franjas
   verticales estrechas y luego enlazarlas resuelve el caso, porque dentro
   de cada franja la línea sí es casi recta.

ORIENTACIÓN EXIF
----------------
No se maneja acá: es responsabilidad de quien abre la imagen, con
`ImageOps.exif_transpose()`. Se documenta porque fue un bug real — 19 de
27 fotos de prueba tenían EXIF "90 CW" sin aplicar, y sin corregirlo la
detección caía de 17 bandas a 4.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


# --------------------------------------------------------------------------
# 1. Umbral adaptativo
# --------------------------------------------------------------------------

def umbral_otsu(gris: np.ndarray) -> float:
    """
    Umbral que separa tinta de papel, por el método de Otsu.

    Otsu prueba todos los umbrales posibles y elige el que **maximiza la
    varianza entre las dos clases** resultantes (tinta y papel). No usa
    ningún valor fijo, así que funciona igual con tinta negra intensa o con
    lápiz azul claro — que es justo donde fallaba la fórmula anterior.
    """
    valores = gris.astype(np.uint8).ravel()
    hist = np.bincount(valores, minlength=256).astype(np.float64)
    total = hist.sum()
    if total == 0:
        return 128.0

    niveles = np.arange(256, dtype=np.float64)
    # Acumulados: peso y media de la clase "oscura" para cada corte.
    peso_bajo = np.cumsum(hist)
    suma_bajo = np.cumsum(hist * niveles)
    peso_alto = total - peso_bajo
    suma_total = suma_bajo[-1]

    # Se evitan los cortes donde una clase queda vacía.
    valido = (peso_bajo > 0) & (peso_alto > 0)
    media_bajo = np.zeros(256)
    media_alto = np.zeros(256)
    media_bajo[valido] = suma_bajo[valido] / peso_bajo[valido]
    media_alto[valido] = (suma_total - suma_bajo[valido]) / peso_alto[valido]

    varianza_entre = np.zeros(256)
    varianza_entre[valido] = (
        peso_bajo[valido] * peso_alto[valido]
        * (media_bajo[valido] - media_alto[valido]) ** 2
    )
    return float(np.argmax(varianza_entre))


def normalizar_iluminacion(imagen: Image.Image, radio_rel: float = 0.04
                           ) -> np.ndarray:
    """
    Quita el gradiente de iluminación de la foto y devuelve la escala de
    grises corregida.

    EL PROBLEMA QUE RESUELVE: Otsu calcula **un solo umbral global**. Con
    luz desigual —sombra de la mano en un lado, reflejo en el otro, o la
    curvatura del cuaderno oscureciendo el centro— ese umbral único queda
    demasiado oscuro en la zona sombreada (pierde trazo) y demasiado claro
    en la iluminada (capta textura del papel como tinta).

    MÉTODO: división por el fondo. Se estima la iluminación con un
    desenfoque fuerte —a ese radio el texto desaparece y solo queda el
    gradiente de luz— y se divide la imagen original por esa estimación.
    El resultado tiene el papel parejo en todo el ancho, y ahí sí un
    umbral global funciona.

    El radio se expresa como fracción del lado mayor para que funcione
    igual con una foto de 800 px o de 4000.

    ⚠️ RESULTADO NEGATIVO MEDIDO — NO se usa en el pipeline por defecto.
    Probada sobre tres fotos con conteo de líneas conocido (17/09/2026):

        sin normalizar ........ error total  8 líneas
        con normalización ..... error total 17  (más del doble)

    Una foto pasó de 16 bandas detectadas a 7. Causa probable: el radio de
    desenfoque (4 % del lado mayor = 160 px en una imagen de 4000) es lo
    bastante grande para incluir el texto, así que dividir por ese fondo le
    quita contraste al trazo. Y de paso realza las rayas impresas del
    cuaderno hasta volverlas comparables al texto real, lo que confunde al
    filtro por densidad.

    Se conserva porque la técnica es correcta para el problema que ataca
    (luz desigual) y podría servir con un radio mucho menor o aplicada solo
    a fotos donde se detecte gradiente fuerte. Pero tal como está, empeora.
    """
    gris = imagen.convert("L")
    radio = max(int(max(gris.size) * radio_rel), 3)
    fondo = gris.filter(ImageFilter.GaussianBlur(radius=radio))

    g = np.array(gris, dtype=np.float32)
    f = np.array(fondo, dtype=np.float32)
    f = np.maximum(f, 1.0)                     # evita dividir por cero

    # Se reescala a 0-255 tomando 255 como "papel limpio".
    corregida = np.clip(g / f * 255.0, 0, 255)
    return corregida


def limpiar_ruido(tinta: np.ndarray, vecinos_min: int = 2) -> np.ndarray:
    """
    Quita las manchas aisladas de la máscara de tinta.

    El grano del papel y el ruido del sensor producen píxeles oscuros
    sueltos que Otsu clasifica como tinta. No forman trazo, pero suman al
    perfil de proyección y pueden inventar bandas.

    Se cuenta cuántos vecinos de tinta tiene cada píxel en su entorno 3×3;
    los que tienen menos de `vecinos_min` se descartan. Es una apertura
    morfológica simple, implementada con desplazamientos de numpy para no
    depender de scipy.

    ⚠️ RESULTADO NEUTRO MEDIDO — no se usa por defecto. Sobre las tres
    fotos de prueba el error total quedó idéntico (8 líneas) con y sin
    limpieza: el grano del papel no era un problema real en este material.
    Se conserva para fotos de peor calidad, donde sí podría aportar.
    """
    t = tinta.astype(np.uint8)
    conteo = np.zeros_like(t, dtype=np.uint8)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            conteo += np.roll(np.roll(t, dy, axis=0), dx, axis=1)
    return tinta & (conteo >= vecinos_min)


def mascara_tinta(gris: np.ndarray, holgura: float = 0.0,
                  limpiar: bool = False) -> np.ndarray:
    """Máscara booleana de píxeles de tinta. `holgura` afloja el umbral."""
    m = gris < (umbral_otsu(gris) + holgura)
    return limpiar_ruido(m) if limpiar else m


# --------------------------------------------------------------------------
# 1b. Corrección de inclinación (deskew)
# --------------------------------------------------------------------------

def _nitidez_perfil(tinta: np.ndarray) -> float:
    """
    Mide qué tan "picudo" es el perfil horizontal de tinta.

    Es el criterio de calidad del deskew: cuando las líneas están
    horizontales, cada una concentra su tinta en pocas filas y el perfil
    tiene picos altos con valles profundos. Al inclinarse, la tinta de una
    línea se reparte en muchas filas y el perfil se aplana.

    Se usa la suma de las diferencias al cuadrado entre filas consecutivas,
    que premia los cambios bruscos — o sea, los bordes nítidos de cada
    banda. Es más sensible que la varianza simple.
    """
    perfil = tinta.sum(axis=1).astype(np.float64)
    if perfil.size < 2:
        return 0.0
    return float(np.sum(np.diff(perfil) ** 2))


def detectar_inclinacion(imagen: Image.Image, rango: float = 8.0,
                         paso: float = 0.5, ancho_analisis: int = 800
                         ) -> float:
    """
    Devuelve el ángulo de inclinación del texto, en grados.

    MÉTODO: perfil de proyección. Se rota la imagen por cada ángulo
    candidato y se mide la nitidez del perfil horizontal; gana el ángulo
    que la maximiza. Es el enfoque clásico y acá tiene una ventaja
    particular: **optimiza exactamente la métrica que usa el segmentador**,
    que también trabaja por proyección horizontal.

    POR QUÉ HACE FALTA: una línea de texto inclinada reparte su tinta en
    muchas filas, y la proyección la difumina hasta fusionarla con las
    vecinas. Es una de las causas por las que la segmentación automática
    quedaba por debajo del recorte manual.

    El análisis se hace sobre una versión reducida (`ancho_analisis`),
    porque el ángulo no necesita resolución completa y rotar una imagen de
    12 megapíxeles decenas de veces sería lentísimo. Luego se rota el
    original una sola vez.
    """
    chico = imagen.convert("L")
    if chico.width > ancho_analisis:
        escala = ancho_analisis / chico.width
        chico = chico.resize((ancho_analisis, max(int(chico.height * escala), 1)),
                             Image.Resampling.BILINEAR)

    base = np.array(chico, dtype=np.float32)
    umbral = umbral_otsu(base)

    mejor_angulo, mejor_valor = 0.0, -1.0
    angulo = -rango
    while angulo <= rango + 1e-9:
        if abs(angulo) < 1e-9:
            girada = base
        else:
            # fillcolor claro: el relleno no debe contar como tinta.
            g = chico.rotate(angulo, resample=Image.Resampling.BILINEAR,
                             expand=False, fillcolor=255)
            girada = np.array(g, dtype=np.float32)
        valor = _nitidez_perfil(girada < umbral)
        if valor > mejor_valor:
            mejor_valor, mejor_angulo = valor, angulo
        angulo += paso

    return mejor_angulo


def corregir_inclinacion(imagen: Image.Image, angulo: float | None = None,
                         minimo: float = 1.0) -> tuple[Image.Image, float]:
    """
    Rota la imagen para dejar el texto horizontal.

    Devuelve (imagen, ángulo aplicado).

    EL UMBRAL MÍNIMO NO ES UN DETALLE. Corregir inclinaciones diminutas
    hace daño, y se midió: con `minimo=0.4` una foto con solo 0.5° de
    inclinación pasó de 16 bandas detectadas a **30**. Dos causas:

      * `expand=True` cambia las dimensiones y agrega bordes blancos, que
        descolocan la detección de la región de papel.
      * La interpolación de la rotación difumina el trazo, y un trazo
        difuso altera el umbral de Otsu.

    Medición sobre tres fotos con conteo de líneas conocido:

        sin girar ....... error total 10 líneas
        minimo = 0.4 .... error total 10  (arregla una foto, rompe otra)
        minimo >= 0.8 ... error total  8  <- se elige 1.0

    Es decir: el deskew ayuda cuando la inclinación es real (una foto con
    −2.0° pasó de 20 bandas a 16, con 17 reales), y estorba cuando es
    ruido de medición.
    """
    if angulo is None:
        angulo = detectar_inclinacion(imagen)
    if abs(angulo) < minimo:
        return imagen, 0.0
    # expand=True para no recortar esquinas; el relleno claro se descarta
    # después al detectar la región de papel.
    girada = imagen.rotate(angulo, resample=Image.Resampling.BICUBIC,
                           expand=True, fillcolor=(255, 255, 255))
    return girada, angulo


# --------------------------------------------------------------------------
# 2. Región de papel
# --------------------------------------------------------------------------

def detectar_papel(gris: np.ndarray, margen: float = 0.02
                   ) -> tuple[int, int, int, int]:
    """
    Devuelve (x0, y0, x1, y1) de la zona de papel dentro de la foto.

    El papel es la región clara y grande. Se detecta por el porcentaje de
    píxeles claros en cada fila y columna, y se recorta un margen hacia
    adentro para dejar afuera el borde y su sombra.
    """
    alto, ancho = gris.shape
    # Umbral a medio camino entre lo oscuro del fondo y lo claro del papel.
    umbral = (np.percentile(gris, 10) + np.percentile(gris, 90)) / 2
    claro = gris > umbral

    filas = claro.mean(axis=1)
    cols = claro.mean(axis=0)
    ys = np.flatnonzero(filas > 0.5)
    xs = np.flatnonzero(cols > 0.5)
    if len(ys) < 2 or len(xs) < 2:
        return 0, 0, ancho, alto

    y0, y1 = int(ys[0]), int(ys[-1])
    x0, x1 = int(xs[0]), int(xs[-1])
    dx, dy = int((x1 - x0) * margen), int((y1 - y0) * margen)
    x0, y0 = x0 + dx, y0 + dy
    x1, y1 = x1 - dx, y1 - dy

    # Si el recorte deja menos de un tercio de la imagen, algo salió mal.
    if (x1 - x0) < ancho * 0.30 or (y1 - y0) < alto * 0.30:
        return 0, 0, ancho, alto
    return x0, y0, x1, y1


# --------------------------------------------------------------------------
# 3. Encuadernado (espiral, agujeros)
# --------------------------------------------------------------------------

def quitar_encuadernado(gris: np.ndarray) -> tuple[int, int]:
    """
    Devuelve (x0, x1) sin la espiral ni los agujeros del margen.

    La espiral se distingue del texto por la forma de su distribución: su
    tinta se reparte a lo largo de TODA la altura de la página, mientras el
    texto se concentra en bandas. Solo se inspecciona el 20 % de cada borde,
    porque el encuadernado nunca está en el medio.
    """
    alto, ancho = gris.shape
    tinta = mascara_tinta(gris)
    por_columna = tinta.sum(axis=0)
    estructural = por_columna > alto * 0.16

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

    if (x1 - x0) < ancho * 0.30:
        return 0, ancho
    return max(x0, 0), min(x1, ancho)


# --------------------------------------------------------------------------
# 4. Bandas de texto, con tolerancia a curvatura
# --------------------------------------------------------------------------

def _bandas_de_perfil(perfil: np.ndarray, minimo: float, hueco_max: int,
                      alto_min: int) -> list[tuple[int, int]]:
    """Agrupa filas activas en bandas, tolerando huecos pequeños."""
    activa = perfil > minimo
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
    return [(a, b) for a, b in bandas if (b - a) >= alto_min]


def estimar_espaciado(perfil: np.ndarray) -> int:
    """
    Estima el espaciado entre renglones (en píxeles) por autocorrelación.

    Hace falta porque el hueco que separa dos líneas NO se puede derivar
    del tamaño de la imagen. La versión anterior usaba `alto / 70`, que en
    una foto de 4000 px daba 57 px — del mismo orden que el espaciado real
    entre renglones de un párrafo, así que los fusionaba. Medido sobre la
    foto de referencia: con 57 detectaba 12 bandas de 22 reales; con 12,
    detecta 21.

    El texto manuscrito en renglones es **periódico**: la autocorrelación
    del perfil de tinta tiene un máximo en el período de esa repetición.
    """
    p = perfil - perfil.mean()
    n = len(p)
    if n < 40 or not np.any(p):
        return 12

    # Autocorrelación por FFT (mucho más rápida que la directa).
    espectro = np.fft.rfft(p, n * 2)
    auto = np.fft.irfft(espectro * np.conj(espectro))[:n]

    # Se busca el primer máximo claro después del origen. El rango acota
    # el espaciado plausible de un renglón manuscrito.
    lo = max(int(n * 0.01), 8)
    hi = max(min(int(n * 0.20), n - 1), lo + 1)
    if hi <= lo:
        return 12
    periodo = lo + int(np.argmax(auto[lo:hi]))

    # El hueco tolerable es una fracción del período: dentro de un renglón
    # hay filas sin tinta (entre palabras y bajo las mayúsculas), pero el
    # corte real es bastante menor que el período completo.
    return max(int(periodo * 0.18), 6)


def detectar_bandas(gris: np.ndarray, franjas: int = 1) -> list[tuple[int, int]]:
    """
    Detecta las bandas (y_inicio, y_fin) que contienen texto.

    Con `franjas > 1` la proyección se hace por franjas verticales y los
    resultados se combinan. Eso tolera **curvatura**: si la hoja no está
    plana, una línea sube o baja a lo largo del ancho y la proyección
    global la difumina, pero dentro de una franja estrecha sigue siendo
    casi recta.

    La combinación usa el criterio de mayoría: una fila cuenta como texto
    si aparece activa en al menos un tercio de las franjas. Así una sombra
    local no inventa líneas, y una línea curva no se pierde.
    """
    alto, ancho = gris.shape
    if alto == 0 or ancho == 0:
        return []

    tinta = mascara_tinta(gris)
    perfil_global = tinta.sum(axis=1).astype(float)
    if perfil_global.max() == 0:
        return []

    # El hueco se estima de los datos, no del tamaño de la imagen.
    hueco_max = estimar_espaciado(perfil_global)
    alto_min = max(int(hueco_max * 0.8), 6)

    if franjas <= 1:
        return _bandas_de_perfil(perfil_global, max(perfil_global.max() * 0.06, 3.0),
                                 hueco_max, alto_min)

    # Proyección por franjas: se marca cada fila como activa o no en cada
    # franja, y se suma el voto.
    votos = np.zeros(alto, dtype=float)
    paso = max(ancho // franjas, 1)
    usadas = 0
    for i in range(franjas):
        x0 = i * paso
        x1 = ancho if i == franjas - 1 else min((i + 1) * paso, ancho)
        if x1 - x0 < 8:
            continue
        perfil = tinta[:, x0:x1].sum(axis=1).astype(float)
        if perfil.max() == 0:
            continue
        votos += (perfil > max(perfil.max() * 0.06, 2.0)).astype(float)
        usadas += 1

    if usadas == 0:
        return []
    return _bandas_de_perfil(votos, usadas / 3.0, hueco_max, alto_min)


# --------------------------------------------------------------------------
# Función de alto nivel
# --------------------------------------------------------------------------

def filtrar_bandas_sin_texto(tinta: np.ndarray, bandas: list[tuple[int, int]],
                             factor: float = 0.6
                             ) -> tuple[list[tuple[int, int]], int]:
    """
    Descarta las bandas que no contienen texto real.

    EL PROBLEMA: en un cuaderno de renglones, una fila en blanco **no está
    vacía** — contiene la raya azul preimpresa. Otsu la clasifica como
    tinta, se crea una banda, y TrOCR —que siempre devuelve algo— alucina
    sobre papel vacío. Medido el 17/09/2026: producía líneas `0 0` en las
    posiciones de los renglones en blanco entre párrafos.

    LA SEÑAL: la **densidad** de tinta separa los dos casos con holgura.
    Sobre la foto de referencia:

        bandas de texto real ... 0.119 – 0.152  (mediana 0.134)
        bandas de solo raya .... 0.051 – 0.067

    Hay un hueco limpio entre 0.067 y 0.119, así que un umbral relativo a
    la mediana funciona sin calibrar nada por foto. Se usa la mediana y no
    el promedio porque una banda mal cortada (muy alta, con varias líneas
    fusionadas) arrastraría el promedio.

    La densidad es mejor discriminante que la altura: hay líneas de texto
    cortas y legítimas (una banda de 58 px con densidad 0.140 era la línea
    "el momento") que un filtro por altura descartaría.
    """
    if not bandas:
        return [], 0

    densidades = []
    for a, b in bandas:
        sub = tinta[a:b + 1]
        densidades.append(float(sub.sum()) / sub.size if sub.size else 0.0)

    mediana = float(np.median(densidades))
    if mediana <= 0:
        return bandas, 0

    minimo = mediana * factor
    conservadas = [bd for bd, d in zip(bandas, densidades) if d >= minimo]
    return conservadas, len(bandas) - len(conservadas)


def partir_bandas_altas(perfil: np.ndarray, bandas: list[tuple[int, int]],
                        factor: float = 1.6
                        ) -> tuple[list[tuple[int, int]], int]:
    """
    Parte las bandas que contienen varias líneas fusionadas.

    EL PROBLEMA, inverso al de las bandas sin texto: cuando los rasgos
    descendentes de una línea (la `j` de "juez", la `g` de "diligencia")
    invaden la zona de la siguiente, no queda ninguna fila sin tinta entre
    ambas y la proyección las detecta como una sola banda. Medido el
    17/09/2026 sobre la foto de referencia: bandas de 203, 341 y 559 px
    contra una mediana de 80. El modelo recibía tres líneas superpuestas en
    una imagen y devolvía basura (`1934`, `1930 1959`).

    LA SOLUCIÓN: cortar por el **valle de tinta** — la fila con menos tinta
    dentro de la banda. Aunque no llegue a cero, ahí es donde se separan las
    dos líneas. Se busca el valle en una ventana alrededor del corte
    proporcional, para no cortar al ras de una letra.

    Cuántas partes: se estima por la altura de la banda contra la **mediana**
    de todas, que representa la altura de una línea normal.

    ⚠️ RESULTADO NEGATIVO MEDIDO — por eso está DESACTIVADA por defecto.
    Probada sobre tres fotos con conteo de líneas conocido, ningún valor
    del factor mejoró el resultado:

        sin partir ...... error total 10 líneas
        factor 3.0 ...... error total 20
        factor 2.0 ...... error total 24
        factor 1.6 ...... error total 27

    La causa: sobre-parte. `partir_bandas.py` aplica esta misma técnica con
    éxito, pero ahí se le pasa `--renglones N` con el total **conocido** de
    renglones escritos. Sin ese dato hay que estimar cuántas líneas trae
    cada banda por su altura, y esa estimación es demasiado imprecisa.

    Se conserva porque sirve cuando el conteo se conoce: se activa pasando
    `partir=True` a `segmentar()`, o desde `partir_bandas.py`.
    """
    if len(bandas) < 3:
        return bandas, 0

    alturas = [b - a for a, b in bandas]
    mediana = float(np.median(alturas))
    if mediana <= 0:
        return bandas, 0

    resultado: list[tuple[int, int]] = []
    partidas = 0
    for a, b in bandas:
        alto = b - a
        if alto < mediana * factor:
            resultado.append((a, b))
            continue

        partes = max(int(round(alto / mediana)), 2)
        cortes = [a]
        for k in range(1, partes):
            centro = a + alto * k // partes
            margen = max(int(alto / partes * 0.30), 4)
            ini = max(centro - margen, a + 3)
            fin = min(centro + margen, b - 3)
            if fin <= ini:
                cortes.append(centro)
                continue
            cortes.append(ini + int(np.argmin(perfil[ini:fin])))
        cortes.append(b)
        resultado.extend((cortes[i], cortes[i + 1]) for i in range(partes))
        partidas += 1

    return resultado, partidas


def segmentar(imagen: Image.Image, franjas: int = 4, relleno: int = 10,
              max_lineas: int = 60, min_ancho_rel: float = 0.06,
              partir: bool = False, deskew: bool = True,
              detalle: dict | None = None) -> list[Image.Image]:
    """
    Parte una foto de página en imágenes de una línea cada una.

    TrOCR reconoce UNA línea por vez: pasarle la página completa devuelve
    basura por bueno que sea el modelo.

    Si no logra separar más de una banda, devuelve la imagen tal cual —
    el caso de una línea ya recortada.

    `detalle` recibe, si se pasa, las cifras intermedias del proceso, para
    diagnóstico y medición.
    """
    if np.asarray(imagen.convert("L")).size == 0:
        return [imagen]

    # (1b) Inclinación: se corrige ANTES de todo lo demás, porque tanto la
    # detección de papel como la proyección por filas asumen que el texto
    # es horizontal.
    angulo = 0.0
    if deskew:
        imagen, angulo = corregir_inclinacion(imagen)

    gris_total = np.array(imagen.convert("L"), dtype=np.float32)

    # (2) Papel
    px0, py0, px1, py1 = detectar_papel(gris_total)
    papel = imagen.crop((px0, py0, px1, py1))

    # (3) Encuadernado
    gris_papel = np.array(papel.convert("L"), dtype=np.float32)
    bx0, bx1 = quitar_encuadernado(gris_papel)
    if (bx0, bx1) != (0, papel.width):
        papel = papel.crop((bx0, 0, bx1, papel.height))

    # (1) + (4) Bandas con umbral Otsu y proyección por franjas
    gris = np.array(papel.convert("L"), dtype=np.float32)
    bandas = detectar_bandas(gris, franjas=franjas)

    tinta = mascara_tinta(gris)

    # Partición de bandas fusionadas: DESACTIVADA por defecto, porque
    # medida sobre fotos con conteo conocido empeoró el resultado (ver el
    # docstring de partir_bandas_altas). Se deja accesible con partir=True.
    partidas = 0
    if partir:
        perfil = tinta.sum(axis=1).astype(float)
        bandas, partidas = partir_bandas_altas(perfil, bandas)

    # Descartar las bandas que solo contienen la raya impresa del cuaderno.
    bandas, descartadas = filtrar_bandas_sin_texto(tinta, bandas)

    if detalle is not None:
        detalle.update({
            "imagen": imagen.size,
            "angulo_corregido": round(angulo, 2),
            "papel": (px0, py0, px1, py1),
            "encuadernado_x": (bx0, bx1),
            "umbral_otsu": round(umbral_otsu(gris), 1),
            "bandas": len(bandas),
            "bandas_sin_texto_descartadas": descartadas,
            "bandas_altas_partidas": partidas,
        })

    if len(bandas) <= 1:
        return [imagen]

    recortes: list[Image.Image] = []
    for ya, yb in bandas[:max_lineas]:
        arriba = max(ya - relleno, 0)
        abajo = min(yb + relleno, papel.height)

        # Recorte horizontal ajustado a la tinta de esta banda.
        cols = np.flatnonzero(tinta[ya:yb + 1].any(axis=0))
        if len(cols) == 0:
            continue
        izq = max(int(cols[0]) - relleno, 0)
        der = min(int(cols[-1]) + relleno, papel.width)

        # Una línea de texto ocupa un ancho razonable; lo muy angosto es
        # ruido (una marca, un resto de encuadernado, una mancha).
        if (der - izq) < papel.width * min_ancho_rel:
            continue
        recortes.append(papel.crop((izq, arriba, der, abajo)))

    return recortes if recortes else [imagen]
