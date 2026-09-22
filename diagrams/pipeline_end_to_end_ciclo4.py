"""
Pipeline de punta a punta (doc 29, Fase 4 - Ciclo 4, primera mitad).

Une en un solo diagrama lo que los Ciclos 1, 2 y 3 construyeron por
separado: ingesta de manuscrito (HTR + localizador entrenado),
vectorizacion, y recuperacion hibrida en el chat. Es la vista que
verifico el Ciclo 4 con datos reales el 21/09/2026 (login, subida real,
Celery async, Qdrant, recuperacion semantica e hibrida) y que ningun
diagrama anterior mostraba junta.

Ejecutar: python pipeline_end_to_end_ciclo4.py
Output: output/pipeline_end_to_end_ciclo4.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python
from diagrams.generic.database import SQL
from diagrams.onprem.compute import Server
from diagrams.custom import Custom

print("Generando diagrama: Pipeline de punta a punta (Ciclo 4)...")

with Diagram(
    "ServIA - Pipeline de Punta a Punta (doc 29, Ciclo 4 - primera mitad)\nVerificado con datos reales el 21/09/2026: manuscrito -> texto -> vectores -> recuperacion hibrida -> respuesta",
    show=False,
    direction="LR",
    filename="output/pipeline_end_to_end_ciclo4",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "1.0",
        "splines": "spline",
        "nodesep": "0.85",
        "ranksep": "1.15"
    }
):
    with Cluster("1. Ingesta (Ciclo 1 + Ciclo 2)", graph_attr={
        "bgcolor": "#eff6ff", "penwidth": "2", "style": "rounded",
        "margin": "22", "pad": "0.5"
    }):
        subida = Python("POST /ingesta/archivos\n(Celery async)")
        htr = Server("servidor-htr\ndocTR (localizador) +\ntrocr-large-handwritten")
        subida >> Edge(color="#2563eb") >> htr

    with Cluster("2. Vectorizacion", graph_attr={
        "bgcolor": "#f0fdf4", "penwidth": "2", "style": "rounded",
        "margin": "22", "pad": "0.5"
    }):
        embed = Python("multilingual-e5-large\n+ chunking")
        qdrant = SQL("Qdrant\nmetadata.numero_expediente")
        embed >> Edge(color="#16a34a") >> qdrant

    with Cluster("3. Recuperacion hibrida (Ciclo 3)", graph_attr={
        "bgcolor": "#fdf4ff", "penwidth": "2", "style": "rounded",
        "margin": "22", "pad": "0.5"
    }):
        chat = Python("Chat general\nextraer_expediente_de_texto()")
        retriever = Python("DynamicServIARetriever\nsemantica + filtro exacto")
        chat >> Edge(color="#a855f7") >> retriever

    llm = Custom("Ollama (local)\nllama3.1:8b", "/diagrams/icons/ollama.png")

    htr >> Edge(color="#2563eb", label="  texto reconocido  ") >> embed
    qdrant >> Edge(color="#a855f7", style="dashed", label="  9. Query vectorial  ") >> retriever
    retriever >> Edge(color="#16a34a", label="  contexto  ") >> llm

print("Diagrama generado: output/pipeline_end_to_end_ciclo4.png")
