"""
Dentro del servidor de reconocimiento (servidor-htr)
Los cuatro pasos que convierten la foto de una pagina en parrafos de texto.
TrOCR lee una sola linea por vez, por eso primero hay que partir la pagina
en renglones.

Ejecutar: python htr_servidor_detalle.py
Output: output/htr_servidor_detalle.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python
from diagrams.custom import Custom

print("Generando diagrama: Detalle del servidor de reconocimiento...")

ICONOS = "/diagrams/icons/"


def cluster(color, margen="30"):
    return {"bgcolor": color, "penwidth": "2", "style": "rounded", "margin": margen, "pad": "0.6"}


with Diagram(
    "ServIA - Dentro del servidor de reconocimiento\nCuatro pasos de la página al texto",
    show=False,
    direction="LR",
    filename="output/htr_servidor_detalle",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "0.4",
        "splines": "spline",
        "nodesep": "0.7",
        "ranksep": "0.8"
    }
):
    entrada = Custom("Foto o captura\nde la página", ICONOS + "Archivos_originales.png")

    with Cluster("servidor-htr (GPU)", graph_attr=cluster("#f3e5f5", "35")):
        localizador = Custom("1. Localiza\nlos renglones\n\ndocTR (DBNet)\nDetector entrenado", ICONOS + "docTR.png")
        recorte = Python("2. Recorta\ncada renglón\n\nUsa los píxeles\noriginales")
        lector = Custom("3. Lee cada\nrenglón\n\nTrOCR\nlarge-handwritten", ICONOS + "HuggingFace_t.png")
        union = Python("4. Une los\nrenglones en\npárrafos\n\n8 reglas de\npuntuación")

    salida = Python("Texto\nen párrafos")

    entrada >> Edge(label="  Imagen  ", color="#2563eb", fontsize="11") >> localizador
    localizador >> Edge(label="  Cajas  ", color="#9333ea", fontsize="11") >> recorte
    recorte >> Edge(label="  Un renglón  \n  por vez  ", color="#9333ea", fontsize="11") >> lector
    lector >> Edge(label="  Texto por  \n  renglón  ", color="#9333ea", fontsize="11") >> union
    union >> Edge(label="  JSON  ", color="#ea580c", fontsize="11") >> salida

print("Diagrama generado: output/htr_servidor_detalle.png")
