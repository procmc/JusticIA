"""
Contexto del Sistema ServIA
Vista de alto nivel mostrando actores y sistemas externos.

Ejecutar: python contexto_sistema.py
Output: output/contexto_sistema.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.onprem.database import Mssql
from diagrams.generic.database import SQL
from diagrams.onprem.compute import Server
from diagrams.custom import Custom
from diagrams.programming.language import Python


print("Generando diagrama: Contexto del Sistema...")

with Diagram(
    "ServIA - Asistente de IA Gubernamental\nContexto del Sistema",
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
    sistema = Python("ServIA\n\nAsistente de IA\nGubernamental")

    # Sistemas externos - Paleta morado claro
    with Cluster("Servicios de Infraestructura (locales, Docker)", graph_attr={
        "bgcolor": "#f3e5f5",
        "penwidth": "2",
        "style": "rounded",
        "margin": "30",
        "pad": "0.6"
    }):
        sql_server = Mssql("SQL Server\n(Local)\n\nDatos transaccionales")
        # Sin ícono propio de Qdrant disponible: se usa un ícono generico
        # de base de datos en vez del logo de un motor distinto (antes
        # mostraba por error el logo de Milvus, retirado del proyecto).
        qdrant = SQL("Qdrant\n(Local)\n\nBusqueda vectorial")
        ollama = Custom("Ollama\nllama3.1:8b\n\nGeneracion IA (RAG)", "/diagrams/icons/ollama.png")
        htr = Server("Servidor HTR\ntrocr-large-handwritten\n\nReconocimiento de\nmanuscrito")

    # Relaciones - Usuarios (azul sistema)
    usuario_judicial >> Edge(label="  Consulta documentos  \n  Busca casos similares  \n  Genera resumenes  ", color="#2563eb", fontsize="11") >> sistema
    admin >> Edge(label="  Administra sistema  ", color="#7c3aed", fontsize="11") >> sistema

    # Relaciones - Servicios externos (paleta sistema)
    sistema >> Edge(label="  Almacena documentos  \n  y metadatos  ", color="#0891b2", fontsize="11") >> sql_server
    sistema >> Edge(label="  Busqueda semantica  \n  de documentos  ", color="#9333ea", fontsize="11") >> qdrant
    sistema >> Edge(label="  Generacion de  \n  respuestas  ", color="#8b5cf6", fontsize="11") >> ollama
    sistema >> Edge(label="  Texto desde\n  manuscrito  ", color="#059669", fontsize="11") >> htr

print("Diagrama generado: output/contexto_sistema.png")
