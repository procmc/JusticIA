"""
Arquitectura de Despliegue - ServIA
Como se ejecuta el sistema: la aplicacion web (Node.js) y los ocho servicios de
Docker Compose del equipo local. Ollama y el servidor de reconocimiento de
imagen comparten la GPU. Nada sale a servicios en la nube.

Ejecutar: python arquitectura_despliegue.py
Output: output/arquitectura_despliegue.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Client
from diagrams.onprem.queue import Celery
from diagrams.onprem.inmemory import Redis
from diagrams.programming.framework import Fastapi
from diagrams.custom import Custom

print("Generando diagrama: Arquitectura de Despliegue...")

ICONOS = "/diagrams/icons/"


def cluster(color, margen="30"):
    return {"bgcolor": color, "penwidth": "2", "style": "rounded", "margin": margen, "pad": "0.6"}


with Diagram(
    "ServIA - Arquitectura de Despliegue\nEquipo local con Docker Compose",
    show=False,
    direction="TB",
    filename="output/arquitectura_despliegue",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "0.4",
        "splines": "spline",
        "nodesep": "0.6",
        "ranksep": "1.1"
    }
):
    usuarios = Client("Usuarios\nNavegador web")

    with Cluster("Aplicación Web (Node.js)", graph_attr=cluster("#e3f2fd")):
        web = Custom("next-frontend\n\nNext.js 15\nPuerto 3000", ICONOS + "nextjs.png")

    with Cluster("Docker Compose (equipo local)", graph_attr=cluster("#f5f5f5", "40")):
        with Cluster("Aplicación", graph_attr=cluster("#e8f5e9")):
            backend = Fastapi("backend\n\nFastAPI\nPuerto 8000")
            worker = Celery("celery-worker\n\nProcesa archivos")

        with Cluster("Procesamiento de Documentos", graph_attr=cluster("#f3e5f5")):
            tika = Custom("tika\n\nApache Tika\nPuerto 9998", ICONOS + "tika.svg.png")
            htr = Custom("servidor-htr (GPU)\n\ndocTR + TrOCR\nPuerto 9100", ICONOS + "docTR.png")

        with Cluster("IA Local", graph_attr=cluster("#fff3e0")):
            ollama = Custom("ollama (GPU)\n\nllama3.1:8b\nPuerto 11434", ICONOS + "ollama.png")

        with Cluster("Datos", graph_attr=cluster("#eceff1")):
            sql = Custom("sqlserver\n\nSQL Server 2022\nPuerto 1433", ICONOS + "SQL Server.png")
            qdrant = Custom("qdrant\n\nBúsqueda vectorial\nPuertos 6333 y 6334", ICONOS + "Qdrant.png")
            redis = Redis("redis\n\nRedis 7\nPuerto 6379")
            uploads = Custom("uploads\n\nArchivos originales", ICONOS + "Archivos_originales.png")

    usuarios >> Edge(label="  HTTPS  ", color="#2563eb", fontsize="11") >> web
    web >> Edge(label="  API REST  ", color="#2563eb", fontsize="11") >> backend
    backend >> Edge(label="  Cola de tareas  ", color="#dc2626", fontsize="11") >> redis
    redis >> Edge(label="  Entrega tareas  ", color="#dc2626", fontsize="11") >> worker

    worker >> Edge(label="  HTTP  ", color="#9333ea", fontsize="11") >> tika
    worker >> Edge(label="  HTTP  ", color="#9333ea", fontsize="11") >> htr
    backend >> Edge(label="  Genera respuestas  ", color="#8b5cf6", fontsize="11") >> ollama

    backend >> Edge(label="  ODBC  ", color="#0891b2", fontsize="11") >> sql
    worker >> Edge(label="  HTTP  ", color="#ea580c", fontsize="11") >> qdrant
    backend >> Edge(label="  Archivos  ", color="#ea580c", fontsize="11") >> uploads

print("Diagrama generado: output/arquitectura_despliegue.png")
