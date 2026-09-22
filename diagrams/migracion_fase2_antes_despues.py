"""
Migracion Fase 2 - Arquitectura Antes / Despues.

Compara el estado del backend antes de la Fase 2 (bloqueado, dependia
de credenciales de nube que no existian en el entorno local) contra el
estado despues (100% local, arranca sin credenciales externas).

Ejecutar: python migracion_fase2_antes_despues.py
Output: output/migracion_fase2_antes_despues.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python
from diagrams.onprem.database import Mssql
from diagrams.generic.database import SQL
from diagrams.custom import Custom

print("Generando diagrama: Migracion Fase 2 Antes/Despues...")

with Diagram(
    "ServIA - Migracion Fase 2\nArquitectura Antes vs Despues",
    show=False,
    direction="TB",
    filename="output/migracion_fase2_antes_despues",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "1.0",
        "splines": "spline",
        "nodesep": "1.5",
        "ranksep": "1.2"
    }
):
    with Cluster("ANTES (hasta 18/08/2026) - Backend NO arrancaba", graph_attr={
        "bgcolor": "#fef2f2",
        "penwidth": "2",
        "style": "rounded",
        "margin": "30",
        "pad": "0.6",
        "fontsize": "14"
    }):
        backend_antes = Python("backend\n\nRuntimeError al importar:\nfaltan credenciales")
        azure_sql = Custom("Azure SQL Server\n\n(nube, credenciales\ninstitucionales)", "/diagrams/icons/azure.png")
        milvus_cloud = Custom("Milvus\n\n(nube, requeria\nMILVUS_URI/TOKEN)", "/diagrams/icons/milvus.png")
        bge = Custom("BGE-M3\n\n(BAAI - origen chino,\nviola politica del proyecto)", "/diagrams/icons/bge.jpeg")

        backend_antes >> Edge(color="#dc2626", style="dashed", label="  bloqueado  ") >> azure_sql
        backend_antes >> Edge(color="#dc2626", style="dashed", label="  bloqueado  ") >> milvus_cloud
        backend_antes >> Edge(color="#dc2626", style="dashed", label="  origen no\n  permitido  ") >> bge

    with Cluster("DESPUES (desde 02/09/2026) - 100% local", graph_attr={
        "bgcolor": "#f0fdf4",
        "penwidth": "2",
        "style": "rounded",
        "margin": "30",
        "pad": "0.6",
        "fontsize": "14"
    }):
        backend_despues = Python("backend\n\nArranca sin\ncredenciales externas")
        sql_local = Mssql("SQL Server\n(contenedor Docker\nlocal)")
        qdrant_local = SQL("Qdrant\n(contenedor Docker\nlocal)")
        e5 = Python("multilingual-e5-large\n\n(Microsoft/intfloat,\nMIT, origen no chino)")

        backend_despues >> Edge(color="#16a34a", label="  local  ") >> sql_local
        backend_despues >> Edge(color="#16a34a", label="  local  ") >> qdrant_local
        backend_despues >> Edge(color="#16a34a", label="  local  ") >> e5

print("Diagrama generado: output/migracion_fase2_antes_despues.png")
