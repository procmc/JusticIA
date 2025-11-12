"""
Procesamiento de Documentos Legales - JusticIA
Vista detallada del módulo de ingesta y procesamiento.

Ejecutar: python procesamiento_documentos.py
Output: output/procesamiento_documentos.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.programming.framework import Fastapi, React
from diagrams.programming.language import Python, Javascript
from diagrams.onprem.database import Mssql
from diagrams.onprem.compute import Server
from diagrams.onprem.queue import Celery
from diagrams.custom import Custom


print("Generando diagrama: Procesamiento de Documentos Legales...")

with Diagram(
    "JusticIA - Procesamiento de Documentos Legales\nMódulo de Ingesta y Embeddings",
    show=False,
    direction="LR",
    filename="output/procesamiento_documentos",
    outformat="png",
    graph_attr={
        "fontsize": "12",
        "bgcolor": "white",
        "pad": "1.5",
        "splines": "spline",
        "nodesep": "1.2",
        "ranksep": "1.5"
    }
):
    usuario = User("Usuario")
    
    with Cluster("Frontend", graph_attr={
        "bgcolor": "#e3f2fd",
        "penwidth": "2",
        "style": "rounded",
        "margin": "25",
        "pad": "0.8"
    }):
        upload = React("Formulario Ingesta\n\nValidacion cliente\nArrastrar archivos")
        validator = Javascript("Validador Expediente\n\nNormaliza formato\nValidacion pattern")
    
    with Cluster("API Backend", graph_attr={
        "bgcolor": "#f3e5f5",
        "penwidth": "2",
        "style": "rounded",
        "margin": "25",
        "pad": "0.8"
    }):
        router = Fastapi("Router Ingesta\n\nPOST /ingesta/upload\nAutenticacion")
        schema = Python("Validacion Schema\n\nPydantic\nFormato expediente")
    
    with Cluster("Orquestador", graph_attr={
        "bgcolor": "#e1f5fe",
        "penwidth": "2",
        "style": "rounded",
        "margin": "25",
        "pad": "0.8"
    }):
        orchestrator = Python("Orquestador Ingesta\n\nCoordina workflow\nVerifica duplicados")
        db_check = Python("Repositorio\n\nConsulta BD\nLock transaccional")
    
    with Cluster("Worker Procesamiento", graph_attr={
        "bgcolor": "#ede7f6",
        "penwidth": "2",
        "style": "rounded",
        "margin": "25",
        "pad": "0.8"
    }):
        celery_task = Celery("Tarea Celery\n\nTimeout: 2h\nReintentos: 2x")
        
        with Cluster("Extraccion de Texto", graph_attr={"bgcolor": "#f3e5f5", "style": "rounded", "margin": "25", "pad": "0.4"}):
            # Documentos -> Tika
            tika_srv = Custom("Apache Tika + OCR\n\nPDF, Word, RTF\nHTML, TXT", "/diagrams/icons/tika.svg.png")
            
            # Audio -> Faster-Whisper (dos estrategias)
            whisper_direct = Custom("Faster-Whisper Directo\n\nArchivos < 50MB\nTranscripcion completa", "/diagrams/icons/openai.png")
            whisper_chunks = Custom("Faster-Whisper Chunks\n\nArchivos >= 50MB\nDivision en segmentos", "/diagrams/icons/openai.png")
        
        with Cluster("Limpieza", graph_attr={"bgcolor": "#e1f5fe", "margin": "20", "pad": "0.4", "style": "rounded"}):
            cleaner = Python("Limpieza Texto\n\nNormaliza espacios\nDetecta encoding")
        
        with Cluster("Generacion de Embeddings", graph_attr={"bgcolor": "#e8f5e9", "penwidth": "2", "style": "rounded", "margin": "30", "pad": "0.8"}):
            chunker = Python("Chunking\n\n512 tokens\n50 overlap")
        
        with Cluster("Vectorizacion", graph_attr={"bgcolor": "#ede7f6", "margin": "20", "pad": "0.4", "style": "rounded"}):
            embedder = Custom("Embeddings\n\nBGE-M3\n1024D", "/diagrams/icons/bge.jpeg")
    
    with Cluster("Almacenamiento", graph_attr={
        "bgcolor": "#e8f5e9",
        "penwidth": "2",
        "style": "rounded",
        "margin": "25",
        "pad": "0.8"
    }):
        sql = Custom("Azure SQL Server\n\nMetadata documentos", "/diagrams/icons/azure.png")
        milvus = Custom("Milvus\n\nVectores chunks", "/diagrams/icons/milvus.png")
    
    # Flujo principal de ingesta
    usuario >> Edge(label=" 1. Carga archivo ", color="#2563eb", fontsize="10") >> upload
    upload >> Edge(label=" 2. Valida ", color="#2563eb", fontsize="10") >> validator
    validator >> Edge(label=" 3. Envia API ", color="#2563eb", fontsize="10") >> router
    
    router >> Edge(label=" 4. Valida schema ", color="#7c3aed", fontsize="10") >> schema
    router >> Edge(label=" 5. Orquesta ", color="#7c3aed", fontsize="10") >> orchestrator
    
    orchestrator >> Edge(label=" 6. Verifica duplicados ", color="#0891b2", fontsize="10") >> db_check
    db_check >> Edge(label=" Consulta ", color="#0891b2", fontsize="10") >> sql
    
    orchestrator >> Edge(label=" 7. Crea tarea ", color="#8b5cf6", fontsize="10") >> celery_task
    
    # Flujo dentro del worker - Rutas de extracción por tipo
    celery_task >> Edge(label=" 8a. Documentos:\nPDF, Word (DOC/DOCX)\nRTF, HTML, TXT ", color="#f59e0b", fontsize="9") >> tika_srv
    celery_task >> Edge(label=" 8b1. Audio pequeño\n(< 50MB) ", color="#10b981", fontsize="9") >> whisper_direct
    celery_task >> Edge(label=" 8b2. Audio grande\n(>= 50MB) ", color="#059669", fontsize="9") >> whisper_chunks
    
    tika_srv >> Edge(label=" 9a. Limpia texto ", color="#0891b2", fontsize="10") >> cleaner
    whisper_direct >> Edge(label=" 9b. Limpia transcripción ", color="#0891b2", fontsize="10") >> cleaner
    whisper_chunks >> Edge(label=" 9c. Une y limpia chunks ", color="#0891b2", fontsize="10") >> cleaner
    
    cleaner >> Edge(label=" 10. Fragmenta ", color="#9333ea", fontsize="10") >> chunker
    chunker >> Edge(label=" 11. Vectoriza ", color="#9333ea", fontsize="10") >> embedder
    
    # Almacenamiento final
    embedder >> Edge(label=" 12. Guarda vectores ", color="#10b981", fontsize="10") >> milvus
    embedder >> Edge(label=" 13. Guarda metadata ", color="#0891b2", fontsize="10") >> sql

print("Diagrama generado: output/procesamiento_documentos.png")
