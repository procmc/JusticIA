"""
Nivel 1 - Arquitectura de Contenedores
Vista de alto nivel mostrando todos los servicios y sus tecnologías.

Ejecutar: python nivel_1_contenedores.py
Output: output/nivel_1_contenedores.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Users
from diagrams.programming.framework import React, Fastapi
from diagrams.programming.language import Python
from diagrams.onprem.database import Mssql
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.compute import Server

print("Generando Nivel 1 - Arquitectura de Contenedores...")

with Diagram(
    "Nivel 1 - Arquitectura de Contenedores",
    show=False,
    direction="TB",
    filename="output/nivel_1_contenedores",
    outformat="png",
    graph_attr={
        "fontsize": "14",
        "bgcolor": "white",
        "pad": "0.5"
    }
):
    usuarios = Users("Usuarios\nJudiciales")
    
    with Cluster("Capa de Presentación", graph_attr={"bgcolor": "#fff3e0"}):
        frontend = React("Frontend Web\n\nNext.js 15\nReact 18 + HeroUI\nTailwind CSS\nPuerto: 3000")
    
    with Cluster("Capa de Aplicación", graph_attr={"bgcolor": "#f3e5f5"}):
        api = Fastapi("API Gateway\n\nFastAPI 0.116\nUvicorn ASGI\nAsync/Await nativo\nPuerto: 8000")
        celery = Python("Workers Asíncronos\n\nCelery 5.3\n4 workers paralelos\nProcesamiento background")
    
    with Cluster("Capa de IA/ML", graph_attr={"bgcolor": "#fce4ec"}):
        embeddings = Server("Servicio Embeddings\n\nBGE-M3-ES-Legal\n1024 dimensiones\nsentence-transformers")
        llm = Server("Servicio LLM\n\nOllama GPT-OSS:20b\nContexto: 32K tokens\nStreaming")
    
    with Cluster("Capa de Datos", graph_attr={"bgcolor": "#e3f2fd"}):
        sql = Mssql("Base Transaccional\n\nSQL Server (Azure)\nMetadata documentos\nUsuarios y auditoría\nPool: 60 conexiones")
        milvus = Server("Base Vectorial\n\nMilvus (Zilliz Cloud)\nÍndice HNSW\nSimilitud COSINE")
        redis = Redis("Cache y Cola\n\nRedis 7\nConversaciones RAG\nTareas Celery\nProgress tracking")
    
    with Cluster("Capa de Procesamiento", graph_attr={"bgcolor": "#fff9c4"}):
        tika = Server("Extractor Documentos\n\nApache Tika 2.8\nTesseract OCR\nESP + ENG")
        whisper = Server("Transcriptor Audio\n\nFaster-Whisper\nModelo: base\nDevice: CPU int8")
    
    # Conexiones principales (con colores semánticos)
    usuarios >> Edge(label="HTTPS/JWT\nAuth", color="blue", style="bold") >> frontend
    
    frontend >> Edge(label="REST API\nSSE Streaming", color="blue") >> api
    
    api >> Edge(label="Async Tasks", color="green") >> celery
    api >> Edge(label="CRUD\nTransacciones", color="orange") >> sql
    api >> Edge(label="Vector Search\ntop_k=10-15", color="purple") >> milvus
    api >> Edge(label="Cache/Sessions\nQueue", color="red") >> redis
    api >> Edge(label="Generate Text\nStreaming", color="darkgreen") >> llm
    
    celery >> Edge(label="Extract Text\nOCR", color="brown") >> tika
    celery >> Edge(label="Transcribe\nAudio", color="brown") >> whisper
    celery >> Edge(label="Embed Chunks\n1024D", color="purple") >> embeddings
    celery >> Edge(label="Store Vectors\n+ metadata", color="purple") >> milvus
    celery >> Edge(label="Store Docs\nMetadata", color="orange") >> sql
    celery >> Edge(label="Progress\nTracking", color="red") >> redis

print("Diagrama generado: output/nivel_1_contenedores.png")
