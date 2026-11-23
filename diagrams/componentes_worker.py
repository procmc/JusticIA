"""
Componentes del Worker de procesamiento de ServIA (C4 nivel 3)
Version resumida: el recorrido de un archivo, desde que la API encola la tarea
hasta que sus fragmentos quedan indexados. Los contenedores con los que se
comunica el Worker aparecen como logos en la caja de la derecha.

Ejecutar: python componentes_worker.py
Output: output/componentes_worker.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.programming.language import Python
from diagrams.programming.framework import Fastapi
from diagrams.onprem.queue import Celery
from diagrams.onprem.inmemory import Redis


print("Generando diagrama: Componentes del Worker...")

ICONOS = "/diagrams/icons/"


def cluster(color):
    return {"bgcolor": color, "penwidth": "2", "style": "rounded", "margin": "30", "pad": "0.6"}


with Diagram(
    "ServIA - Worker de procesamiento\nComponentes",
    show=False,
    direction="TB",
    filename="output/componentes_worker",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "0.4",
        "splines": "spline",
        "compound": "true",
        "nodesep": "0.6",
        "ranksep": "1.0"
    }
):
    api = Fastapi("API Backend\nFastAPI")
    redis = Redis("Redis 7\n\nCola y progreso")

    with Cluster("Worker (Celery)", graph_attr=cluster("#e8f5e9")):
        tarea = Celery("Tarea de procesamiento\n\nUn archivo por tarea,\ncon su seguimiento")
        procesador = Python("Procesador\nde documentos")
        limpieza = Python("Limpieza de texto")
        auditoria = Python("Auditoría\nde ingesta")

    with Cluster("Extracción según el Tipo", graph_attr=cluster("#f3e5f5")):
        extractor = Python("Cliente de extracción\nDocumentos")
        transcriptor = Custom("faster-whisper\nAudio", ICONOS + "Whisper_t.png")
        cliente_htr = Python("Cliente de\nreconocimiento\nImágenes")

    with Cluster("Indexación", graph_attr=cluster("#fff3e0")):
        vectorizador = Custom("Fragmentación\ne indexación", ICONOS + "langchain.png")
        embeddings = Custom("Modelo de embeddings\nmultilingual-e5-large", ICONOS + "HuggingFace_t.png")
        vector = Python("Adaptador vectorial")
        datos = Custom("Acceso a datos\nSQLAlchemy", ICONOS + "SQLAlchemy_t.png")

    with Cluster("Contenedores de ServIA", graph_attr=cluster("#eceff1")):
        tika = Custom("Apache Tika\nTesseract OCR", ICONOS + "tika.svg.png")
        htr = Custom("docTR + TrOCR", ICONOS + "docTR.png")
        qdrant = Custom("Qdrant", ICONOS + "Qdrant.png")
        sql = Custom("SQL Server 2022", ICONOS + "SQL Server.png")

    api >> Edge(label="  Encola una tarea  \n  por archivo  ", color="#2563eb", fontsize="11", minlen="0") >> redis
    redis >> Edge(label="  Entrega la tarea  ", color="#2563eb", fontsize="11") >> tarea
    tarea >> Edge(label="  Procesa el archivo  ", color="#059669", fontsize="11") >> procesador
    tarea >> Edge(label="  Registra inicio,  \n  fin o error  ", color="#546e7a", fontsize="11", minlen="0") >> auditoria

    procesador >> Edge(label="  Documentos  ", color="#9333ea", fontsize="11") >> extractor
    procesador >> Edge(label="  Audio  ", color="#9333ea", fontsize="11") >> transcriptor
    procesador >> Edge(label="  Imágenes  ", color="#9333ea", fontsize="11") >> cliente_htr
    procesador >> Edge(label="  Limpia el texto  ", color="#059669", fontsize="11") >> limpieza
    limpieza >> Edge(label="  Fragmenta e indexa  ", color="#ea580c", fontsize="11") >> vectorizador

    vectorizador >> Edge(label="  Genera los vectores  ", color="#ea580c", fontsize="11", minlen="0") >> embeddings
    vectorizador >> Edge(label="  Inserta fragmentos  ", color="#ea580c", fontsize="11", minlen="0") >> vector
    procesador >> Edge(label="  Registra documento\n  y estado  ", color="#0891b2", fontsize="11") >> datos

    extractor >> Edge(label="  HTTP  ", color="#9333ea", fontsize="11") >> tika
    cliente_htr >> Edge(label="  HTTP · JSON  ", color="#9333ea", fontsize="11") >> htr
    vector >> Edge(label="  HTTP  ", color="#ea580c", fontsize="11") >> qdrant
    datos >> Edge(label="  Lee y escribe  ", color="#0891b2", fontsize="11") >> sql

print("Diagrama generado: output/componentes_worker.png")
