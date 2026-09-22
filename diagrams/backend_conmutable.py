"""
Backend Conmutable (Fase 2) — patrón Strategy para el motor vectorial.

Muestra la interfaz VectorStoreBackend y sus implementaciones. Milvus se
retiró del proyecto el 10/09/2026 — se muestra atenuado/discontinuo a
propósito, como nota histórica de la Fase 2 (cuando sí convivían dos
motores), no como parte del sistema activo hoy.

Ejecutar: python backend_conmutable.py
Output: output/backend_conmutable.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python
from diagrams.onprem.client import Client

print("Generando diagrama: Backend Conmutable...")

with Diagram(
    "ServIA - Backend Conmutable (Fase 2)\nPatron Strategy para el motor vectorial",
    show=False,
    direction="TB",
    filename="output/backend_conmutable",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "1.0",
        "splines": "spline",
        "nodesep": "1.2",
        "ranksep": "1.4"
    }
):
    resto_sistema = Client("Resto del sistema\n(RAG, ingesta,\nbusqueda similares)")

    selector = Python("get_vectorstore_backend()\n\nFase 2 (hasta 09/09): leia\nVECTORSTORE_BACKEND\n\nHOY (desde 10/09): hardcodeado,\nsiempre devuelve QdrantBackend")

    interfaz = Python("VectorStoreBackend\n(interfaz abstracta)\n\n9 metodos hoy\n(7 originales de Fase 2 +\n2 agregados despues)")

    with Cluster("Implementaciones", graph_attr={
        "bgcolor": "#eef2ff",
        "penwidth": "2",
        "style": "rounded",
        "margin": "25",
        "pad": "0.5"
    }):
        qdrant_backend = Python("QdrantBackend\n\nACTIVA HOY\n(unico motor)")
        milvus_backend = Python("MilvusBackend\n\nRETIRADA 10/09/2026\n(archivo ya no existe)")

    resto_sistema >> Edge(label="  usa  ", color="#2563eb", fontsize="11") >> selector
    selector >> Edge(label="  devuelve  ", color="#7c3aed", fontsize="11") >> interfaz
    interfaz >> Edge(label="  implementa  ", color="#059669", fontsize="11") >> qdrant_backend
    interfaz >> Edge(label="  implementaba\n  (Fase 2)  ", color="#9ca3af", fontsize="11", style="dashed") >> milvus_backend

print("Diagrama generado: output/backend_conmutable.png")
