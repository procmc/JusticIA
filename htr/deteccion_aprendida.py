"""
Localización de renglones con un detector APRENDIDO, en vez de un umbral.

POR QUÉ EXISTE ESTE MÓDULO
--------------------------
`segmentacion.py` ubica los renglones con Otsu: calcula un umbral global de
gris y llama tinta a todo lo más oscuro. Medido el 17/09/2026 sobre la foto
de la hoja de imprenta, eso clasifica como tinta el **22 % de la página**
(el 35 % en la otra foto), contra 0.11 en los recortes hechos a mano. Las
rayas impresas del cuaderno entran como tinta, y de ahí en adelante todo lo
que se apoya en esa máscara queda contaminado: la detección de
encuadernado, el filtro de bandas vacías y los límites de cada banda.

Consecuencia medida de punta a punta sobre las 8 oraciones de la hoja:

    líneas ubicadas por una persona ..... CER 0.2480
    líneas ubicadas con Otsu ............ CER 0.5560

O sea que **el localizador aporta más error que el reconocedor**.

Aclarar la imagen no lo arregla (probado: el CER empeora a 0.6440), porque
Otsu escala junto con el histograma: multiplicar todos los píxeles por 1.4
mueve el umbral en la misma proporción.

QUÉ SE HACE EN SU LUGAR
-----------------------
Un detector de texto entrenado —DBNet con backbone ResNet-50, de docTR—
que **aprendió** qué trazo es escritura y qué no. No hay umbral que
calibrar: sobre la misma foto no pone ni una caja sobre las rayas del
cuaderno, y sí detecta `¡Atención!`, `vence` y `folio 315`, que eran
exactamente las palabras que el recorte por Otsu perdía.

Es la misma idea que usa un modelo de visión-lenguaje cuando lee una
página completa: distinguir tinta de fondo es parte de lo aprendido, no un
paso de preprocesamiento. La diferencia es que acá se aplica **solo a
ubicar los renglones**; el reconocimiento se queda en TrOCR, que es lo que
ya se midió y eligió en el Ciclo 1. El reconocedor de docTR es para texto
impreso y no sirve para manuscrito.

IMPORTANTE: NO SE BINARIZA LO QUE VE EL MODELO
----------------------------------------------
Igual que en `segmentacion.py`, la máscara y las cajas se usan **solo para
saber dónde cortar**. A TrOCR se le entregan los píxeles RGB originales.
Nunca hubo, ni acá ni antes, una "imagen limpia" intermedia.

LICENCIA
--------
docTR (Mindee) es **Apache 2.0**, con pesos preentrenados publicados por el
proyecto. Uso comercial e institucional permitido, sin pago ni permiso.
Corre local, así que ningún documento sale de la institución — que es
requisito por la Ley 8968.

    https://github.com/mindee/doctr
"""

from __future__ import annotations

import logging
import os
import threading

import numpy as np
from PIL import Image

from segmentacion import corregir_inclinacion, detectar_papel

logger = logging.getLogger("htr.deteccion")

# db_resnet50 es el de mejor calidad; db_mobilenet_v3_large pesa mucho menos
# si algún día hace falta bajar el consumo de VRAM.
ARQUITECTURA = os.getenv("HTR_DETECTOR", "db_resnet50")

_detector = None
_candado_carga = threading.Lock()


def _cargar():
    """Carga el detector una sola vez, la primera vez que se usa."""
    global _detector
    if _detector is not None:
        return _detector
    with _candado_carga:
        if _detector is None:
            from doctr.models import detection_predictor
            logger.info("Cargando detector %s ...", ARQUITECTURA)
            _detector = detection_predictor(ARQUITECTURA, pretrained=True,
                                            assume_straight_pages=True)
            logger.info("Detector listo")
    return _detector


def _cajas(imagen: Image.Image, umbral: float = 0.30) -> np.ndarray:
    """
    Cajas de palabra en píxeles absolutos: filas `(x0, y0, x1, y1)`.

    docTR devuelve coordenadas relativas y un puntaje por caja.
    """
    salida = _cargar()([np.asarray(imagen.convert("RGB"))])[0]
    crudas = np.asarray(salida["words"] if isinstance(salida, dict) else salida)
    if crudas.size == 0:
        return np.zeros((0, 4), dtype=np.int32)

    if crudas.shape[1] >= 5:
        crudas = crudas[crudas[:, 4] >= umbral]
    if crudas.size == 0:
        return np.zeros((0, 4), dtype=np.int32)

    W, H = imagen.size
    cajas = crudas[:, :4].copy()
    cajas[:, [0, 2]] *= W
    cajas[:, [1, 3]] *= H
    return cajas.astype(np.int32)


def agrupar_en_renglones(cajas: np.ndarray, tolerancia_rel: float = 0.60
                         ) -> list[np.ndarray]:
    """
    Junta las cajas de palabra que pertenecen al mismo renglón.

    El detector devuelve una caja por palabra, sin decir cuáles van juntas.
    Se agrupan por la **altura del centro** de cada caja, con una
    tolerancia que sale de la altura mediana de las cajas de la propia
    foto. Así no hay ningún número en píxeles que calibrar: una foto de
    4160 px de alto y una línea ya recortada usan la misma regla.

    POR QUÉ NO POR SOLAPE VERTICAL
    ------------------------------
    El primer intento agrupaba por solape entre la caja y la franja del
    renglón, dejando que la franja creciera al incorporar cada palabra.
    Falla en cuanto una oración ocupa dos renglones: la cola de la `j` de
    `juez` se mete en la fila de abajo, la franja se estira, y desde ahí se
    traga todo lo que sigue. Medido sobre la hoja de 17 renglones: devolvía
    **9 bandas de 235 a 442 px**, o sea un ítem completo —dos filas
    apiladas— en cada banda. A TrOCR, que lee UNA línea, eso le llega como
    basura.

    Comparar contra el centro mediano del renglón no tiene ese problema,
    porque el punto de referencia no se corre al agregar palabras.
    """
    if len(cajas) == 0:
        return []

    centros = (cajas[:, 1] + cajas[:, 3]) / 2.0
    alturas = cajas[:, 3] - cajas[:, 1]
    tolerancia = max(float(np.median(alturas)) * tolerancia_rel, 1.0)

    orden = np.argsort(centros)
    renglones: list[list[int]] = [[int(orden[0])]]
    for i in orden[1:]:
        actual = renglones[-1]
        referencia = float(np.median(centros[actual]))
        if abs(float(centros[i]) - referencia) <= tolerancia:
            actual.append(int(i))
        else:
            renglones.append([int(i)])

    grupos = [cajas[np.array(idx)] for idx in renglones]
    return [g[np.argsort(g[:, 0])] for g in grupos]


def quitar_columna_numeracion(grupos: list[np.ndarray], ancho: int,
                              minimo_lineas: int = 3
                              ) -> tuple[list[np.ndarray], list[int]]:
    """
    Descarta la columna de numeración manual (`01`, `02`, ...) si la hay,
    y devuelve **en qué renglones estaba**.

    Los índices se devuelven porque la numeración es dos cosas a la vez:
    basura para el texto y una **pista de estructura** excelente. Un
    renglón numerado arranca un ítem nuevo, así que ahí va un corte de
    párrafo — sin depender de que el reconocedor haya acertado el punto
    final, que es en lo que se apoya `unir_lineas`.

    Se notó al medir: al quitar los números, las 8 oraciones de la hoja se
    fusionaron en **1 solo párrafo**, porque el reconocedor entrega los
    renglones tan dañados que casi ninguno termina en punto legible. La
    numeración recupera esa estructura de forma independiente del texto.

    EL PROBLEMA: los números que la persona escribió al margen son texto
    legítimo, así que el detector los encuentra —y bien—. Pero no son parte
    de la oración: entraban al texto reconocido como `OL ET senior` y
    `04 Searedito`, y ensucian el CER y después el RAG.

    LA SEÑAL, MEDIDA: hay **dos columnas**. En la hoja de referencia las
    primeras cajas de las filas numeradas están en x0 = 0, 1, 6, 18, 29 —el
    margen— y las de las filas de continuación en x0 = 145, 152, 163, 175.
    Un hueco limpio entre 29 y 145.

    No se filtra por "palabra corta" a secas, porque `El`, `Se` y `La`
    abren oración legítimamente y son igual de cortas. El primer intento
    pedía un hueco grande entre el número y la palabra siguiente, y falló:
    de 17 renglones solo detectó 2, porque la persona escribió el número
    pegado al texto (huecos medidos de 2 a 63 px).

    LA REGLA SE VALIDA A SÍ MISMA. No basta con que haya cajas angostas al
    margen: se exige que **al quitarlas, esas filas queden alineadas con la
    columna de texto** de las filas que no tenían número. Si la foto es un
    documento normal, donde el texto sí arranca en el margen, no existe esa
    segunda columna y no se borra nada. Sin esa verificación la función
    podría comerse la primera palabra de cada párrafo.
    """
    if len(grupos) < minimo_lineas:
        return grupos, []

    # Candidatas: primera caja angosta y pegada al margen izquierdo.
    candidatas, resto = [], []
    for k, g in enumerate(grupos):
        x0 = float(g[0, 0])
        ancho_caja = float(g[0, 2] - g[0, 0])
        if len(g) >= 2 and x0 < ancho * 0.05 and ancho_caja < ancho * 0.09:
            candidatas.append((k, float(g[1, 0])))   # x donde sigue el texto
        else:
            resto.append(x0)

    if len(candidatas) < minimo_lineas:
        return grupos, []

    siguiente = np.array([c[1] for c in candidatas])
    tolerancia = ancho * 0.04

    if resto:
        # Verificación fuerte: la columna de texto tiene que coincidir con
        # donde arrancan las filas sin número.
        columna = float(np.median(resto))
        if abs(float(np.median(siguiente)) - columna) > tolerancia:
            return grupos, []
    else:
        # Sin filas de referencia, al menos se exige que las candidatas
        # coincidan entre sí en dónde retoma el texto.
        if float(np.std(siguiente)) > tolerancia:
            return grupos, []
        columna = float(np.median(siguiente))

    resultado = list(grupos)
    numeradas: list[int] = []
    for k, x_sig in candidatas:
        if abs(x_sig - columna) <= tolerancia:
            resultado[k] = resultado[k][1:]
            numeradas.append(k)

    if len(numeradas) < minimo_lineas:
        return grupos, []

    logger.info("Columna de numeracion detectada (texto retoma en x~%d): "
                "%d renglones limpiados", int(columna), len(numeradas))

    # Los índices se recalculan sobre la lista final, porque un renglón que
    # se quede sin cajas desaparece y correría la numeración.
    finales, mapa = [], {}
    for k, g in enumerate(resultado):
        if len(g):
            mapa[k] = len(finales)
            finales.append(g)
    return finales, [mapa[k] for k in numeradas if k in mapa]


def segmentar(imagen: Image.Image, relleno_rel: float = 0.18,
              max_lineas: int = 60, min_ancho_rel: float = 0.06,
              deskew: bool = True, quitar_numeracion: bool = True,
              detalle: dict | None = None) -> list[Image.Image]:
    """
    Parte una foto de página en imágenes de un renglón cada una.

    Misma firma de uso que `segmentacion.segmentar`, para poder cambiar de
    localizador sin tocar el servidor.

    `relleno_rel` es el margen que se agrega alrededor del renglón, como
    fracción de su propia altura. Es **proporcional** a propósito: un
    relleno fijo en píxeles queda chico en una foto de 4160 px de alto y
    enorme en una línea ya recortada. Las cajas del detector vienen ceñidas
    al trazo, y TrOCR fue entrenado con recortes que traían aire alrededor.

    Además el relleno se **recorta a la mitad del espacio libre** hasta el
    renglón de arriba y el de abajo. Sin ese tope, un relleno del 35 % de
    la altura metía la fila vecina dentro del recorte —verificado a ojo en
    la hoja de contacto— y TrOCR recibía dos líneas apiladas otra vez,
    aunque las bandas estuvieran bien calculadas.
    """
    if np.asarray(imagen.convert("L")).size == 0:
        return [imagen]

    angulo = 0.0
    if deskew:
        imagen, angulo = corregir_inclinacion(imagen)

    # El papel se recorta con el método de brillo que ya estaba: es
    # confiable y saca de la foto lo que no es hoja (en la foto de
    # referencia, un teclado que ocupaba el 36 % superior). Sin esto el
    # detector encuentra el texto de las teclas, que es texto de verdad
    # pero no del documento.
    gris = np.asarray(imagen.convert("L"), dtype=np.float32)
    px0, py0, px1, py1 = detectar_papel(gris)
    papel = imagen.crop((px0, py0, px1, py1))

    cajas = _cajas(papel)
    grupos = agrupar_en_renglones(cajas)

    numeradas: list[int] = []
    if quitar_numeracion:
        grupos, numeradas = quitar_columna_numeracion(grupos, papel.width)

    if detalle is not None:
        detalle.update({
            "localizador": f"doctr:{ARQUITECTURA}",
            "imagen": imagen.size,
            "angulo_corregido": round(angulo, 2),
            "papel": (px0, py0, px1, py1),
            "cajas_palabra": int(len(cajas)),
            "bandas": len(grupos),
            "numeracion_limpiada": len(numeradas),
            # Renglones que abren ítem: cortes de párrafo seguros.
            "inicios_bloque": numeradas,
        })

    if not grupos:
        return [imagen]

    limites = [(int(g[:, 1].min()), int(g[:, 3].max())) for g in grupos]

    recortes: list[Image.Image] = []
    for k, g in enumerate(grupos[:max_lineas]):
        x0, y0 = int(g[:, 0].min()), int(g[:, 1].min())
        x1, y1 = int(g[:, 2].max()), int(g[:, 3].max())
        deseado = max(int((y1 - y0) * relleno_rel), 2)

        # Tope: la mitad del espacio libre hasta el renglón vecino.
        hueco_arriba = y0 - limites[k - 1][1] if k > 0 else y0
        hueco_abajo = (limites[k + 1][0] - y1 if k + 1 < len(limites)
                       else papel.height - y1)
        arriba = max(min(deseado, hueco_arriba // 2), 0)
        abajo = max(min(deseado, hueco_abajo // 2), 0)

        recorte = papel.crop((max(x0 - deseado, 0), max(y0 - arriba, 0),
                              min(x1 + deseado, papel.width),
                              min(y1 + abajo, papel.height)))
        if recorte.width < papel.width * min_ancho_rel:
            continue
        recortes.append(recorte)

    return recortes if recortes else [imagen]
