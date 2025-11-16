"""
Arquitectura de Despliegue - JusticIA
Vista de infraestructura, contenedores Docker y servicios cloud.

Ejecutar: python arquitectura_despliegue.py
Output: output/arquitectura_despliegue.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Client
from diagrams.onprem.container import Docker
from diagrams.programming.framework import React, Fastapi
from diagrams.programming.language import Python
from diagrams.onprem.database import Mssql
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.compute import Server
from diagrams.custom import Custom

print("Generando diagrama: Arquitectura de Despliegue...")

with Diagram(
    "JusticIA - Arquitectura de Despliegue\nInfraestructura Docker y Servicios Cloud",
    show=False,
    direction="LR",
    filename="output/arquitectura_despliegue",
    outformat="png",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "ranksep": "3.0",
        "nodesep": "2.0",
        "pad": "2.0",
        "splines": "polyline"
    }
):
    usuarios = Client("Usuarios\nBrowser")
    
    # ========== CAPA 1: FRONTEND (FUERA DE DOCKER) ==========
    with Cluster("Frontend (Servidor Web / Vercel)", graph_attr={"bgcolor": "#BBDEFB", "penwidth": "3", "style": "rounded", "margin": "40", "pad": "0.8"}):
        frontend = Custom("next-frontend\n\nNext.js 15\nReact 18\nTailwindCSS\nFetch API\nNode.js 20", "/diagrams/icons/nextjs.png")
    
    # ========== CAPA 2: DOCKER HOST LOCAL ==========
    with Cluster("Docker Host Local (VM/Server)", graph_attr={"bgcolor": "#E3F2FD", "penwidth": "3", "style": "rounded", "margin": "40", "pad": "0.8"}):
        
        # Backend API
        with Cluster("API Layer", graph_attr={"bgcolor": "#CE93D8", "style": "rounded", "margin": "30", "pad": "0.8"}):
            backend = Fastapi("fastapi-backend\n\nPython 3.11\nFastAPI + Uvicorn\nLangChain\nSQLAlchemy\nBGE-M3 (embeddings)")
        
        # Workers
        with Cluster("Processing Layer", graph_attr={"bgcolor": "#F8BBD0", "style": "rounded", "margin": "30", "pad": "0.8"}):
            celery = Python("celery-worker\n\nPython 3.11\nCelery 5.3\nFaster-Whisper\nSentence-Transformers")
        
        # Cache
        with Cluster("Cache Layer", graph_attr={"bgcolor": "#FFCCBC", "style": "rounded", "margin": "30", "pad": "0.8"}):
            redis = Redis("redis\n\nRedis 7 Alpine")
        
        # Document Processing
        with Cluster("Document Processing", graph_attr={"bgcolor": "#C5E1A5", "style": "rounded", "margin": "30", "pad": "0.8"}):
            tika = Custom("apache-tika\n\nJava 17\nTika 2.8.0\nTesseract OCR", "/diagrams/icons/tika.svg.png")
    
    # ========== CAPA 3: SERVICIOS CLOUD ==========
    with Cluster("Azure Cloud", graph_attr={"bgcolor": "#BBDEFB", "penwidth": "3", "style": "rounded", "margin": "40", "pad": "0.8"}):
        azure_sql = Custom("Azure SQL Server", "/diagrams/icons/azure.png")
    
    with Cluster("Milvus (Local/Docker)", graph_attr={"bgcolor": "#B2DFDB", "penwidth": "3", "style": "rounded", "margin": "50", "pad": "1.0"}):
        milvus = Custom("Milvus\n\nVector Database", "/diagrams/icons/milvus.png")
    
    with Cluster("Ollama Cloud", graph_attr={"bgcolor": "#E1BEE7", "penwidth": "3", "style": "rounded", "margin": "40", "pad": "0.8"}):
        ollama = Custom("Ollama API\n\nLLM: gpt-oss-120B", "/diagrams/icons/ollama.png")
    
    # ===== FLUJO DE CONEXIONES =====
    
    # Usuario → Frontend
    usuarios >> Edge(label="HTTPS :3000", color="#1976D2", style="bold") >> frontend
    
    # Frontend → Backend
    frontend >> Edge(label="HTTP :8000\nREST API", color="#1976D2", style="bold") >> backend
    
    # Backend → Redis (cache/session)
    backend >> Edge(label="Redis :6379\nCache + Sessions", color="#F57C00", style="dashed") >> redis
    
    # Backend → Azure SQL
    backend >> Edge(label="TDS :1433\nMetadata", color="#0078D4") >> azure_sql
    
    # Backend → Milvus
    backend >> Edge(label="gRPC :19530\nVector Search", color="#00C7B7") >> milvus
    
    # Backend → Ollama
    backend >> Edge(label="HTTPS\nLLM Inference", color="#7C3AED") >> ollama
    
    # Backend → Celery (via Redis)
    backend >> Edge(label="Celery Tasks", color="#E91E63", style="bold") >> celery
    
    # Celery → Redis (queue)
    celery >> Edge(label="Redis :6379\nTask Queue", color="#F57C00", style="dashed") >> redis
    
    # Celery → Tika
    celery >> Edge(label="HTTP :9998\nDocument OCR", color="#388E3C") >> tika
    
    # Celery → Azure SQL (store metadata)
    celery >> Edge(label="TDS :1433\nStore Metadata", color="#0078D4") >> azure_sql
    
    # Celery → Milvus (store vectors)
    celery >> Edge(label="gRPC :19530\nStore Embeddings", color="#00C7B7") >> milvus

print("Diagrama generado: output/arquitectura_despliegue.png")
