"""
Procesamiento de Documentos Legales - ServIA
Vista detallada del módulo de ingesta y procesamiento.

Ejecutar: python procesamiento_documentos.py
Output: output/procesamiento_documentos.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.programming.framework import Fastapi, React
from diagrams.programming.language import Python, Javascript
from diagrams.onprem.database import Mssql
from diagrams.generic.database import SQL
from diagrams.onprem.compute import Server
from diagrams.onprem.queue import Celery
from diagrams.custom import Custom


print("Generando diagrama: Procesamiento de Documentos Legales...")

with Diagram(
    "ServIA - Procesamiento de Documentos Legales\nMódulo de Ingesta y Embeddings",
    show=False,
    direction="LR",
    filename="output/procesamiento_documentos",
    outformat="png",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "pad": "2.0",
        "splines": "polyline",
        "nodesep": "1.8",
        "ranksep": "2.5"
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
    
    with Cluster("API Backend", graph_attr={
        "bgcolor": "#f3e5f5",
        "penwidth": "2",
        "style": "rounded",
        "margin": "25",
        "pad": "0.8"
    }):
        router = Fastapi("Router Ingesta\n\nPOST /ingesta/upload\nAutenticacion")
    
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

            # Imagenes -> Servidor HTR (Ciclo 1, GPU aparte)
            htr_srv = Server("Servidor HTR\n\ntrocr-large-handwritten\n+ docTR (GPU)")

        with Cluster("Limpieza", graph_attr={"bgcolor": "#e1f5fe", "margin": "20", "pad": "0.4", "style": "rounded"}):
            cleaner = Python("Limpieza Texto\n\nNormaliza espacios\nDetecta encoding")

        with Cluster("Generacion de Embeddings", graph_attr={"bgcolor": "#e8f5e9", "penwidth": "2", "style": "rounded", "margin": "30", "pad": "0.8"}):
            chunker = Python("Chunking\n\n512 tokens\n50 overlap")

        with Cluster("Vectorizacion", graph_attr={"bgcolor": "#ede7f6", "margin": "20", "pad": "0.4", "style": "rounded"}):
            embedder = Python("Embeddings\n\nmultilingual-e5-large\n1024D")

    with Cluster("Vector Database", graph_attr={
        "bgcolor": "#e0f2f1",
        "penwidth": "2",
        "style": "rounded",
        "margin": "20",
        "pad": "0.6"
    }):
        qdrant = SQL("Qdrant\n\nVectores chunks")

    with Cluster("Relational Database", graph_attr={
        "bgcolor": "#fce4ec",
        "penwidth": "2",
        "style": "rounded",
        "margin": "20",
        "pad": "0.6"
    }):
        sql = Mssql("SQL Server\n\n(local)\nMetadata documentos")
    
    # Flujo principal de ingesta
    usuario >> Edge(label=" 1. Carga archivo ", color="#2563eb", fontsize="10") >> upload
    upload >> Edge(label=" 2. Envia API ", color="#2563eb", fontsize="10") >> router
    
    router >> Edge(label=" 3. Orquesta ", color="#7c3aed", fontsize="10") >> orchestrator
    
    orchestrator >> Edge(label=" 4. Verifica duplicados ", color="#0891b2", fontsize="10") >> db_check
    db_check >> Edge(label=" Consulta ", color="#0891b2", fontsize="10") >> sql
    
    orchestrator >> Edge(label=" 5. Crea tarea ", color="#8b5cf6", fontsize="10") >> celery_task
    
    # Flujo dentro del worker - Rutas de extracción por tipo
    celery_task >> Edge(label=" 6a. Documentos:\nPDF, Word (DOC/DOCX)\nRTF, HTML, TXT ", color="#f59e0b", fontsize="9") >> tika_srv
    celery_task >> Edge(label=" 6b1. Audio pequeño\n(< 50MB) ", color="#10b981", fontsize="9") >> whisper_direct
    celery_task >> Edge(label=" 6b2. Audio grande\n(>= 50MB) ", color="#059669", fontsize="9") >> whisper_chunks
    celery_task >> Edge(label=" 6c. Imagenes:\nJPG, PNG, TIF, BMP ", color="#a21caf", fontsize="9") >> htr_srv

    tika_srv >> Edge(label=" 7a. Limpia texto ", color="#0891b2", fontsize="10") >> cleaner
    whisper_direct >> Edge(label=" 7b. Limpia transcripción ", color="#0891b2", fontsize="10") >> cleaner
    whisper_chunks >> Edge(label=" 7c. Une y limpia chunks ", color="#0891b2", fontsize="10") >> cleaner
    htr_srv >> Edge(label=" 7d. Limpia texto reconocido ", color="#0891b2", fontsize="10") >> cleaner
    
    cleaner >> Edge(label=" 8. Fragmenta ", color="#9333ea", fontsize="10") >> chunker
    chunker >> Edge(label=" 9. Vectoriza ", color="#9333ea", fontsize="10") >> embedder
    
    # Almacenamiento final
    embedder >> Edge(label=" 10. Guarda vectores ", color="#10b981", fontsize="10") >> qdrant
    embedder >> Edge(label=" 11. Guarda metadata ", color="#0891b2", fontsize="10") >> sql

print("Diagrama generado: output/procesamiento_documentos.png")
