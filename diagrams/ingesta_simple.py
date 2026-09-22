"""
Ingesta de Documentos - Flujo General
Flujo básico del módulo de ingesta de documentos legales.

Ejecutar: python ingesta_simple.py
Output: output/ingesta_simple.png
"""

from diagrams import Diagram, Edge
from diagrams.onprem.client import User
from diagrams.programming.framework import React, Fastapi
from diagrams.programming.language import Python
from diagrams.generic.database import SQL
from diagrams.onprem.compute import Server
from diagrams.custom import Custom


print("Generando diagrama: Ingesta de Documentos (Simple)...")

with Diagram(
    "ServIA - Ingesta de Documentos\nFlujo General",
    show=False,
    direction="LR",
    filename="output/ingesta_simple",
    outformat="png",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "ranksep": "2.0",
        "nodesep": "1.5",
        "pad": "1.5",
        "splines": "polyline"
    }
):
    usuario = User("Usuario")
    upload = React("Frontend\n\nFormulario Upload")
    api = Fastapi("API\n\nRouter Ingesta")
    worker = Python("Worker\n\nCelery Task")
    tika = Custom("Tika\n\nPDF, Word, RTF", "/diagrams/icons/tika.svg.png")
    whisper = Custom("Whisper\n\nAudio MP3/WAV", "/diagrams/icons/openai.png")
    htr = Server("Servidor HTR\n\nManuscrito\n(JPG/PNG/TIF)")
    embedder = Python("Embeddings\n\nmultilingual-e5-large")
    storage = SQL("Storage\n\nQdrant + SQL Server\n(ambos locales)")

    # Flujo simplificado
    usuario >> Edge(label=" 1. Sube archivo ", color="#2563eb", style="bold", fontsize="10") >> upload
    upload >> Edge(label=" 2. POST /upload ", color="#2563eb", style="bold", fontsize="10") >> api
    api >> Edge(label=" 3. Crea tarea ", color="#8b5cf6", style="bold", fontsize="10") >> worker
    worker >> Edge(label=" 4a. Documentos ", color="#f59e0b", fontsize="10") >> tika
    worker >> Edge(label=" 4b. Audio ", color="#10b981", fontsize="10") >> whisper
    worker >> Edge(label=" 4c. Manuscrito ", color="#a21caf", fontsize="10") >> htr
    tika >> Edge(label=" 5. Vectoriza ", color="#9333ea", fontsize="10") >> embedder
    whisper >> Edge(label=" 5. Vectoriza ", color="#9333ea", fontsize="10") >> embedder
    htr >> Edge(label=" 5. Vectoriza ", color="#9333ea", fontsize="10") >> embedder
    embedder >> Edge(label=" 6. Almacena ", color="#10b981", style="bold", fontsize="10") >> storage

print("Diagrama generado: output/ingesta_simple.png")
