"""
Contexto del Sistema JusticIA
Vista de alto nivel mostrando actores y sistemas externos.

Ejecutar: python contexto_sistema.py
Output: output/contexto_sistema.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.onprem.database import Mssql
from diagrams.onprem.compute import Server
from diagrams.custom import Custom
from diagrams.programming.language import Python


print("Generando diagrama: Contexto del Sistema...")

with Diagram(
    "JusticIA - Asistente Judicial con IA\nContexto del Sistema",
    show=False,
    direction="TB",
    filename="output/contexto_sistema",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "1.5",
        "splines": "spline",
        "nodesep": "2.0",
        "ranksep": "2.0"
    }
):
    # Actores - Paleta azul claro
    with Cluster("Usuarios", graph_attr={
        "bgcolor": "#e3f2fd",
        "penwidth": "2",
        "style": "rounded",
        "margin": "30",
        "pad": "0.6"
    }):
        usuario_judicial = User("Usuario Judicial")
        admin = User("Administrador")
    
    # Sistema principal
    sistema = Python("JusticIA\n\nAsistente Judicial\ncon IA")
    
    # Sistemas externos - Paleta morado claro
    with Cluster("Servicios Externos", graph_attr={
        "bgcolor": "#f3e5f5",
        "penwidth": "2",
        "style": "rounded",
        "margin": "30",
        "pad": "0.6"
    }):
        azure_sql = Custom("Azure SQL Server\n\nDatos transaccionales", "/diagrams/icons/azure.png")
        milvus = Custom("Milvus\n(Cloud o Local)\n\nBusqueda vectorial", "/diagrams/icons/milvus.png")
        ollama = Custom("Ollama\n(Cualquier LLM)\n\nGeneracion IA", "/diagrams/icons/ollama.png")
    
    # Relaciones - Usuarios (azul sistema)
    usuario_judicial >> Edge(label="  Consulta expedientes  \n  Busca casos similares  \n  Genera resumenes  ", color="#2563eb", fontsize="11") >> sistema
    admin >> Edge(label="  Administra sistema  ", color="#7c3aed", fontsize="11") >> sistema
    
    # Relaciones - Servicios externos (paleta sistema)
    sistema >> Edge(label="  Almacena documentos  \n  y metadatos  ", color="#0891b2", fontsize="11") >> azure_sql
    sistema >> Edge(label="  Busqueda semantica  \n  de casos  ", color="#9333ea", fontsize="11") >> milvus
    sistema >> Edge(label="  Generacion de  \n  respuestas  ", color="#8b5cf6", fontsize="11") >> ollama

print("Diagrama generado: output/contexto_sistema.png")
