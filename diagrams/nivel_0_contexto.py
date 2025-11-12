"""
Nivel 0 - Contexto del Sistema JusticIA
Vista de más alto nivel mostrando usuarios y sistemas externos.

Ejecutar: python nivel_0_contexto.py
Output: output/nivel_0_contexto.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.onprem.database import Mssql
from diagrams.onprem.compute import Server

print("Generando Nivel 0 - Contexto del Sistema...")

with Diagram(
    "Nivel 0 - Contexto del Sistema JusticIA",
    show=False,
    direction="LR",
    filename="output/nivel_0_contexto",
    outformat="png",
    graph_attr={
        "fontsize": "14",
        "bgcolor": "white"
    }
):
    # Actores externos
    juez = User("Juez")
    abogado = User("Abogado")
    admin = User("Administrador\nIT")
    
    # Sistema principal (representado como cluster)
    with Cluster("Sistema JusticIA", graph_attr={"bgcolor": "#e3f2fd"}):
        sistema = Server("Plataforma JusticIA\n\nAsistente Judicial con IA\n- Consulta expedientes\n- Chat inteligente RAG\n- Búsqueda casos similares\n- Generación resúmenes")
    
    # Sistemas externos - Cloud Services
    with Cluster("Servicios Cloud Externos", graph_attr={"bgcolor": "#fff3e0"}):
        azure_sql = Mssql("Azure SQL Server\n\nBase de Datos\nTransaccional")
        zilliz = Server("Zilliz Cloud\n\nMilvus Vector DB\nBúsqueda semántica")
        ollama = Server("Ollama Cloud\n\nGPT-OSS 20B\nGeneración IA")
    
    # Sistema legacy (opcional - futuro)
    pj_legacy = Mssql("Sistema Poder Judicial\n(Existente)\n\nIntegración futura")
    
    # Relaciones principales
    juez >> Edge(label="Consulta expedientes\nGenera resúmenes", color="blue") >> sistema
    abogado >> Edge(label="Busca casos similares\nAnálisis legal", color="blue") >> sistema
    admin >> Edge(label="Gestiona usuarios\nMonitorea sistema", color="red") >> sistema
    
    sistema >> Edge(label="Almacena metadata\nusuarios, documentos", color="orange") >> azure_sql
    sistema >> Edge(label="Búsqueda vectorial\nsemántica", color="purple") >> zilliz
    sistema >> Edge(label="Generación texto\nStreaming", color="green") >> ollama
    
    sistema >> Edge(label="Puede integrar datos\n(futuro)", color="gray", style="dashed") >> pj_legacy

print("Diagrama generado: output/nivel_0_contexto.png")
