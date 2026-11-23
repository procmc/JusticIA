"""
Componentes de la API Backend de ServIA (C4 nivel 3)
Version resumida: los 19 componentes del diagrama de planificacion se agrupan
en modulos funcionales, servicios de apoyo e IA local. Los contenedores con los
que se comunica la API aparecen como logos en la caja de la derecha.

Ejecutar: python componentes_api.py
Output: output/componentes_api.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.programming.language import Python
from diagrams.programming.framework import Fastapi
from diagrams.onprem.inmemory import Redis


print("Generando diagrama: Componentes de la API Backend...")

ICONOS = "/diagrams/icons/"


def cluster(color):
    return {"bgcolor": color, "penwidth": "2", "style": "rounded", "margin": "30", "pad": "0.6"}


with Diagram(
    "ServIA - API Backend\nComponentes",
    show=False,
    direction="TB",
    filename="output/componentes_api",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "0.4",
        "splines": "spline",
        "compound": "true",
        "nodesep": "0.6",
        "ranksep": "1.1"
    }
):
    web = Custom("Aplicación Web\nNext.js 15", ICONOS + "nextjs.png")
    main = Fastapi("FastAPI\nmain.py\n\nMonta los routers")

    with Cluster("Módulos Funcionales", graph_attr=cluster("#e8f5e9")):
        auth = Python("Autenticación\ny Usuarios")
        ingesta = Python("Ingesta\ny Archivos")
        rag = Python("Consultas RAG\n\nOrquestador, recuperador\ne historial")
        notebooks = Python("NotebookServIA")
        similares = Python("Temas Similares")
        bitacora = Python("Bitácora\ny Métricas")

    with Cluster("Servicios de Apoyo", graph_attr=cluster("#f3e5f5")):
        seguridad = Custom("Seguridad\nJWT y roles", ICONOS + "JWT_t.png")
        auditoria = Python("Auditoría")
        correo_srv = Python("Envío de correo\naiosmtplib")
        archivos_srv = Python("Gestión de archivos")
        datos = Custom("Acceso a datos\nSQLAlchemy", ICONOS + "SQLAlchemy_t.png")

    with Cluster("IA Local", graph_attr=cluster("#fff3e0")):
        embeddings = Custom("Modelo de embeddings\nmultilingual-e5-large", ICONOS + "HuggingFace_t.png")
        vector = Python("Adaptador vectorial")
        llm = Custom("Cliente del modelo\nde lenguaje", ICONOS + "langchain.png")

    with Cluster("Contenedores de ServIA", graph_attr=cluster("#eceff1")):
        sql = Custom("SQL Server 2022", ICONOS + "SQL Server.png")
        qdrant = Custom("Qdrant", ICONOS + "Qdrant.png")
        ollama = Custom("Ollama\nllama3.1:8b", ICONOS + "ollama.png")
        redis = Redis("Redis 7")
        uploads = Custom("Carpeta uploads", ICONOS + "Archivos_originales.png")
        gmail = Custom("Servidor de correo\n(Gmail, SMTP)", ICONOS + "Gmail.png")

    web >> Edge(label="  API REST\n  (HTTPS, JWT)  ", color="#2563eb", fontsize="11", minlen="0") >> main
    main >> Edge(label="  Enruta las peticiones  ", color="#059669", fontsize="11", lhead="cluster_Módulos Funcionales") >> rag

    rag >> Edge(label="  Usan seguridad, auditoría,  \n  correo, archivos y datos  ", color="#9333ea", fontsize="11", ltail="cluster_Módulos Funcionales", lhead="cluster_Servicios de Apoyo") >> auditoria
    ingesta >> Edge(label="  Encola archivos  \n  y guarda conversaciones  ", color="#dc2626", fontsize="11") >> redis
    rag >> Edge(label="  Consultan con IA  ", color="#ea580c", fontsize="11", ltail="cluster_Módulos Funcionales", lhead="cluster_IA Local") >> vector

    datos >> Edge(label="  Lee y escribe  ", color="#0891b2", fontsize="11") >> sql
    vector >> Edge(label="  Busca y elimina  \n  fragmentos  ", color="#9333ea", fontsize="11") >> qdrant
    llm >> Edge(label="  Genera texto  \n  (streaming)  ", color="#8b5cf6", fontsize="11") >> ollama
    archivos_srv >> Edge(label="  Lee y escribe  ", color="#ea580c", fontsize="11") >> uploads
    correo_srv >> Edge(label="  SMTP  ", color="#546e7a", fontsize="11") >> gmail

print("Diagrama generado: output/componentes_api.png")
