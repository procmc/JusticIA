"""
Nivel 2A - Componentes del Módulo de Ingesta
Vista detallada del procesamiento de documentos.

Ejecutar: python nivel_2a_ingesta.py
Output: output/nivel_2a_ingesta.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.programming.framework import Fastapi
from diagrams.programming.language import Python
from diagrams.onprem.database import Mssql
from diagrams.onprem.compute import Server
from diagrams.onprem.queue import Celery

print("Generando Nivel 2A - Componentes del Modulo de Ingesta...")

with Diagram(
    "Nivel 2A - Módulo de Ingesta de Documentos",
    show=False,
    direction="LR",
    filename="output/nivel_2a_ingesta",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "ranksep": "1.0"
    }
):
    usuario = User("Usuario")
    
    with Cluster("Frontend - Ingesta UI", graph_attr={"bgcolor": "#fff3e0"}):
        upload = Server("IngestaForm.jsx\n\nValidación cliente\nDrag&Drop files\nProgress tracking")
        validator = Server("expedienteValidator.js\n\nNormaliza formato\nValida pattern\nErrores amigables")
    
    with Cluster("Backend API - Router", graph_attr={"bgcolor": "#f3e5f5"}):
        router = Fastapi("routes/ingesta.py\n\nPOST /ingesta/upload\nAuth middleware\nMultipart parsing")
        schema = Server("ingesta_schemas.py\n\nPydantic validation\nExpediente format\nFile constraints")
    
    with Cluster("Servicio Orquestador", graph_attr={"bgcolor": "#e1f5fe"}):
        orchestrator = Python("IngestionService\n\nCoordinación workflow\nValidación expediente\nDuplicates check")
        db_check = Server("ExpedienteRepo\n\nConsulta duplicados\nLock transaccional")
    
    with Cluster("Worker Celery - Procesamiento", graph_attr={"bgcolor": "#fff9c4"}):
        celery_task = Celery("tasks.process_file\n\n2h timeout\nRetry: 2x\nIdempotencia")
        
        with Cluster("Sub-proceso Extracción"):
            tika_srv = Server("ExtractionService\n\nTika client\n900s timeout\nOCR fallback")
            whisper_srv = Server("WhisperService\n\nFaster-Whisper\nChunking 30MB\nSpanish model")
        
        with Cluster("Sub-proceso Limpieza"):
            cleaner = Server("TextCleaningService\n\nRemove noise\nNormalize spaces\nLegal format")
        
        with Cluster("Sub-proceso Chunking"):
            chunker = Server("ChunkingService\n\nSize: 7000 chars\nOverlap: 700 chars\nMetadata inject")
        
        with Cluster("Sub-proceso Vectorización"):
            embedder = Server("EmbeddingService\n\nBGE-M3 Legal\nBatch: 32 chunks\n1024 dimensions")
    
    with Cluster("Almacenamiento", graph_attr={"bgcolor": "#e8f5e9"}):
        sql = Mssql("SQL Server\n\nDocumento metadata\nChunks metadata\nTransacción 2PC")
        milvus = Server("Milvus Cloud\n\nVector storage\nChunk embeddings\nHNSW index")
    
    # Flujo principal de ingesta
    usuario >> Edge(label="1. Upload file", color="blue") >> upload
    upload >> Edge(label="2. Validate", color="blue") >> validator
    validator >> Edge(label="3. POST /ingesta", color="blue") >> router
    
    router >> Edge(label="4. Schema check", color="orange") >> schema
    router >> Edge(label="5. Orchestrate", color="green") >> orchestrator
    
    orchestrator >> Edge(label="6. Check duplicates", color="red") >> db_check
    db_check >> Edge(label="Query", color="gray") >> sql
    
    orchestrator >> Edge(label="7. Async task", color="green") >> celery_task
    
    # Flujo dentro del worker
    celery_task >> Edge(label="8a. Extract\nPDF/DOCX", color="brown") >> tika_srv
    celery_task >> Edge(label="8b. Transcribe\nAudio", color="brown") >> whisper_srv
    
    tika_srv >> Edge(label="9. Clean text", color="purple") >> cleaner
    whisper_srv >> Edge(label="9. Clean text", color="purple") >> cleaner
    
    cleaner >> Edge(label="10. Split chunks", color="purple") >> chunker
    chunker >> Edge(label="11. Embed batches", color="purple") >> embedder
    
    # Almacenamiento final (transaccional)
    embedder >> Edge(label="12. Store vectors", color="darkgreen") >> milvus
    embedder >> Edge(label="13. Store metadata\n(2PC commit)", color="orange") >> sql

print("Diagrama generado: output/nivel_2a_ingesta.png")
