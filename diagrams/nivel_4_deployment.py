"""
Nivel 4 - Arquitectura de Deployment
Vista de infraestructura, contenedores Docker y recursos cloud.

Ejecutar: python nivel_4_deployment.py
Output: output/nivel_4_deployment.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Client
from diagrams.onprem.container import Docker
from diagrams.programming.framework import React, Fastapi
from diagrams.onprem.database import Mssql
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.compute import Server

print("Generando Nivel 4 - Arquitectura de Deployment...")

with Diagram(
    "Nivel 4 - Deployment & Infraestructura",
    show=False,
    direction="TB",
    filename="output/nivel_4_deployment",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "ranksep": "1.0"
    }
):
    usuarios = Client("Usuarios\nBrowser")
    
    with Cluster("Servidor de Aplicación (Docker Host)", graph_attr={"bgcolor": "#e3f2fd"}):
        docker_engine = Docker("Docker Engine\n\nCompose v2\nNetwork: justicia_net")
        
        with Cluster("Contenedor Frontend"):
            frontend_container = React("next-frontend\n\nNext.js 15\nNode 20 Alpine\nPort: 3000\nCPU: 1 core\nRAM: 512MB")
        
        with Cluster("Contenedor Backend"):
            backend_container = Fastapi("fastapi-backend\n\nPython 3.11 Slim\nUvicorn ASGI\nPort: 8000\nCPU: 2 cores\nRAM: 2GB")
        
        with Cluster("Contenedor Workers"):
            celery_container = Docker("celery-worker\n\nPython 3.11 Slim\nCelery 5.3\n4 workers\nCPU: 4 cores\nRAM: 4GB")
        
        with Cluster("Contenedor Redis"):
            redis_container = Redis("redis\n\nRedis 7 Alpine\nPort: 6379\nPersistence: AOF\nRAM: 512MB")
        
        with Cluster("Contenedor Tika"):
            tika_container = Server("apache-tika\n\nTika 2.8 + Tesseract\nPort: 9998\nCPU: 2 cores\nRAM: 2GB")
    
    with Cluster("Azure Cloud - Base de Datos", graph_attr={"bgcolor": "#0078d4"}):
        azure_sql = Mssql("Azure SQL Server\n\nPaas Managed\nTier: General Purpose\nvCores: 4\nStorage: 100GB\nBackup: 7 días\nGeo-redundancy")
    
    with Cluster("Zilliz Cloud - Vector Database", graph_attr={"bgcolor": "#00c7b7"}):
        zilliz_cluster = Server("Milvus Cluster\n\nManaged Service\nRegion: us-west-2\nCPU: 4 cores\nRAM: 8GB\nStorage: 50GB SSD\nReplicas: 2")
    
    with Cluster("Ollama Cloud - LLM Service", graph_attr={"bgcolor": "#7c3aed"}):
        ollama_api = Server("Ollama API\n\nGPT-OSS:20b-cloud\nGPU: 1x A100\nRAM: 40GB\nAPI Endpoint\nRate limit: 100 req/min")
    
    with Cluster("Servicios de IA Locales (Docker)", graph_attr={"bgcolor": "#fff9c4"}):
        embeddings_container = Docker("embeddings-service\n\nBGE-M3-ES-Legal\nPython 3.11\nCPU: 2 cores\nRAM: 4GB\nModelo: 2.3GB")
        
        whisper_container = Docker("whisper-service\n\nFaster-Whisper\nPython 3.11\nCPU inference\nRAM: 2GB\nModelo: base (142MB)")
    
    # Conexiones de red
    usuarios >> Edge(label="HTTPS\nPort 443", color="blue", style="bold") >> frontend_container
    
    frontend_container >> Edge(label="HTTP API\nPort 8000", color="blue") >> backend_container
    
    backend_container >> Edge(label="Queue\nPort 6379", color="red") >> redis_container
    backend_container >> Edge(label="TDS\nPort 1433", color="orange") >> azure_sql
    backend_container >> Edge(label="gRPC\nPort 19530", color="purple") >> zilliz_cluster
    backend_container >> Edge(label="HTTP API\nPort 11434", color="green") >> ollama_api
    
    celery_container >> Edge(label="Queue\nPort 6379", color="red") >> redis_container
    celery_container >> Edge(label="HTTP\nPort 9998", color="brown") >> tika_container
    celery_container >> Edge(label="Local\nInference", color="purple") >> embeddings_container
    celery_container >> Edge(label="Local\nInference", color="purple") >> whisper_container
    celery_container >> Edge(label="Store\nMetadata", color="orange") >> azure_sql
    celery_container >> Edge(label="Store\nVectors", color="purple") >> zilliz_cluster
    
    # Orquestación
    docker_engine >> Edge(label="Manage", color="gray", style="dashed") >> frontend_container
    docker_engine >> Edge(label="Manage", color="gray", style="dashed") >> backend_container
    docker_engine >> Edge(label="Manage", color="gray", style="dashed") >> celery_container
    docker_engine >> Edge(label="Manage", color="gray", style="dashed") >> redis_container
    docker_engine >> Edge(label="Manage", color="gray", style="dashed") >> tika_container
    docker_engine >> Edge(label="Manage", color="gray", style="dashed") >> embeddings_container
    docker_engine >> Edge(label="Manage", color="gray", style="dashed") >> whisper_container

print("Diagrama generado: output/nivel_4_deployment.png")
