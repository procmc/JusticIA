"""
Como ServIA obtiene el texto de una imagen (vista general)
El Worker detecta que el archivo es una imagen y la envia al servidor de
reconocimiento (GPU). El texto vuelve al Worker, se limpia y se indexa en
Qdrant. Todo corre en local.

Ejecutar: python htr_proceso_imagen.py
Output: output/htr_proceso_imagen.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.queue import Celery
from diagrams.programming.language import Python
from diagrams.custom import Custom

print("Generando diagrama: Proceso de imagen a texto (general)...")

ICONOS = "/diagrams/icons/"


def cluster(color, margen="30"):
    return {"bgcolor": color, "penwidth": "2", "style": "rounded", "margin": margen, "pad": "0.6"}


with Diagram(
    "ServIA - Del archivo de imagen al texto\nVista general · 100 % local",
    show=False,
    direction="LR",
    filename="output/htr_proceso_imagen",
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
    imagen = Custom("Imagen subida\n\nJPG, PNG,\nTIF o BMP", ICONOS + "Archivos_originales.png")
    procesador = Celery("Worker\n\nElige la ruta\nsegún el tipo")

    with Cluster("servidor-htr · GPU · puerto 9100", graph_attr=cluster("#f3e5f5", "35")):
        servidor = Custom("Reconocimiento\nde texto\n\ndocTR + TrOCR", ICONOS + "docTR.png")

    limpieza = Python("Worker\n\nLimpia\nel texto")
    qdrant = Custom("Fragmenta e\nindexa\n\nQdrant", ICONOS + "Qdrant.png")

    imagen >> Edge(label="  Sube  ", color="#2563eb", fontsize="11") >> procesador
    procesador >> Edge(label="  HTTP  \n  bytes  ", color="#9333ea", fontsize="11") >> servidor
    servidor >> Edge(label="  Texto  \n  reconocido  ", color="#9333ea", fontsize="11") >> limpieza
    limpieza >> Edge(label="  Texto  \n  limpio  ", color="#ea580c", fontsize="11") >> qdrant

print("Diagrama generado: output/htr_proceso_imagen.png")
