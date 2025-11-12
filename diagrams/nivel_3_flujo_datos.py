"""
Nivel 3 - Flujo de Datos Completo
Vista del ciclo de vida de un documento desde ingesta hasta consulta.

Ejecutar: python nivel_3_flujo_datos.py
Output: output/nivel_3_flujo_datos.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.onprem.compute import Server
from diagrams.onprem.database import Mssql
from diagrams.onprem.queue import Celery

print("Generando Nivel 3 - Flujo de Datos Completo...")

with Diagram(
    "Nivel 3 - Flujo de Datos del Documento",
    show=False,
    direction="TB",
    filename="output/nivel_3_flujo_datos",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "ranksep": "0.8"
    }
):
    with Cluster("Fase 1: INGESTA", graph_attr={"bgcolor": "#fff3e0"}):
        upload = User("Usuario\nsube archivo")
        file_raw = Server("📄 Archivo\nRAW\n\nPDF/DOCX/MP3\nSize: hasta 100MB")
    
    with Cluster("Fase 2: EXTRACCIÓN", graph_attr={"bgcolor": "#f3e5f5"}):
        extraction = Celery("Worker\nExtracción")
        file_text = Server("📝 Texto\nPlano\n\nUTF-8\nLimpiado")
    
    with Cluster("Fase 3: TRANSFORMACIÓN", graph_attr={"bgcolor": "#e1f5fe"}):
        chunking = Server("Chunking\nService")
        chunks = Server("🧩 Chunks\nTexto\n\n7000 chars\n700 overlap\nMetadata")
    
    with Cluster("Fase 4: VECTORIZACIÓN", graph_attr={"bgcolor": "#f3e5f5"}):
        embedding = Server("Embedding\nService")
        vectors = Server("🔢 Vectores\n1024D\n\nBGE-M3\nNormalizados")
    
    with Cluster("Fase 5: ALMACENAMIENTO", graph_attr={"bgcolor": "#e8f5e9"}):
        storage_dual = Server("Storage\nDual")
        
        with Cluster("Transaccional"):
            sql_data = Mssql("SQL Server\n\nDocumento:\n- ID\n- expediente\n- filename\n- status\n\nChunks:\n- chunk_id\n- text\n- position")
        
        with Cluster("Vectorial"):
            milvus_data = Server("Milvus\n\nVectores:\n- vector (1024D)\n- doc_id\n- chunk_id\n- metadata")
    
    with Cluster("Fase 6: CONSULTA", graph_attr={"bgcolor": "#fff9c4"}):
        query_user = User("Usuario\nconsulta")
        query_text = Server("❓ Pregunta\nNatural\n\n'Casos de...'")
        query_vector = Server("🔢 Vector\nQuery\n\n1024D")
        search = Server("Similarity\nSearch")
    
    with Cluster("Fase 7: RECUPERACIÓN", graph_attr={"bgcolor": "#fce4ec"}):
        results = Server("📊 Resultados\nRankeados\n\ntop_k chunks\nScore COSINE\nMetadata")
        context = Server("📖 Contexto\nEnriquecido\n\nText + metadata\nDoc info")
    
    with Cluster("Fase 8: GENERACIÓN", graph_attr={"bgcolor": "#f3e5f5"}):
        llm = Server("LLM\nService")
        response = Server("💬 Respuesta\nIA\n\nStreaming\nCitaciones")
    
    # Flujo de ingesta → almacenamiento
    upload >> Edge(label="Upload", color="blue") >> file_raw
    file_raw >> Edge(label="Procesa", color="brown") >> extraction
    extraction >> Edge(label="Extrae", color="brown") >> file_text
    
    file_text >> Edge(label="Split", color="purple") >> chunking
    chunking >> Edge(label="Produce", color="purple") >> chunks
    
    chunks >> Edge(label="Embed", color="purple") >> embedding
    embedding >> Edge(label="Genera", color="purple") >> vectors
    
    vectors >> Edge(label="Guarda", color="green") >> storage_dual
    storage_dual >> Edge(label="Metadata\n+ Text", color="orange") >> sql_data
    storage_dual >> Edge(label="Vectors\n1024D", color="purple") >> milvus_data
    
    # Flujo de consulta → respuesta
    query_user >> Edge(label="Pregunta", color="blue") >> query_text
    query_text >> Edge(label="Embed", color="purple") >> query_vector
    query_vector >> Edge(label="Busca", color="purple") >> search
    
    search >> Edge(label="Query\nvectors", color="gray") >> milvus_data
    milvus_data >> Edge(label="Top chunks", color="darkgreen") >> results
    
    results >> Edge(label="Enrich", color="orange") >> context
    context >> Edge(label="Fetch\nmetadata", color="gray") >> sql_data
    
    context >> Edge(label="Prompt +\nContext", color="darkgreen") >> llm
    llm >> Edge(label="Genera", color="darkgreen") >> response
    response >> Edge(label="Respuesta", color="blue") >> query_user

print("Diagrama generado: output/nivel_3_flujo_datos.png")
