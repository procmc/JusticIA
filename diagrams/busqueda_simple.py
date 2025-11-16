"""
Búsqueda de Similitud - Flujo General
Flujo básico del módulo de búsqueda semántica de casos.

Ejecutar: python busqueda_simple.py
Output: output/busqueda_simple.png
"""

from diagrams import Diagram, Edge
from diagrams.onprem.client import User
from diagrams.programming.framework import React, Fastapi
from diagrams.programming.language import Python
from diagrams.custom import Custom


print("Generando diagrama: Búsqueda de Similitud (Simple)...")

with Diagram(
    "JusticIA - Búsqueda de Similitud\nFlujo General",
    show=False,
    direction="LR",
    filename="output/busqueda_simple",
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
    search_ui = React("Frontend\n\nBúsqueda Interface")
    api = Fastapi("API\n\nSimilarity Router")
    service = Python("Service\n\n2 modos")
    embedder = Custom("Embeddings\n\nBGE-M3\n(solo descripción)", "/diagrams/icons/bge.jpeg")
    milvus = Custom("Milvus\n\nVector Search", "/diagrams/icons/milvus.png")
    sql = Custom("Azure SQL\n\nMetadata", "/diagrams/icons/azure.png")
    
    # Flujo simplificado
    usuario >> Edge(label=" 1. Query ", color="#2563eb", style="bold", fontsize="10") >> search_ui
    search_ui >> Edge(label=" 2. POST /search ", color="#2563eb", style="bold", fontsize="10") >> api
    api >> Edge(label=" 3. Procesa ", color="#7b1fa2", style="bold", fontsize="10") >> service
    service >> Edge(label=" 4a. Por descripción\nvectoriza ", color="#f57c00", fontsize="10") >> embedder
    service >> Edge(label=" 4b. Por expediente\ncompara directo ", color="#0288d1", fontsize="10") >> milvus
    embedder >> Edge(label=" 5. Búsqueda vectorial ", color="#c2185b", fontsize="10") >> milvus
    milvus >> Edge(label=" 6. Top K docs ", color="#c2185b", style="dashed", fontsize="9") >> service
    service >> Edge(label=" 7. Enriquece ", color="#5e35b1", fontsize="10") >> sql
    sql >> Edge(label=" 8. Metadata ", color="#5e35b1", style="dashed", fontsize="9") >> service
    service >> Edge(label=" 9. Resultados ", color="#388e3c", style="bold", fontsize="10") >> search_ui
    search_ui >> Edge(label=" 10. Muestra casos ", color="#2563eb", style="bold", fontsize="10") >> usuario

print("Diagrama generado: output/busqueda_simple.png")
