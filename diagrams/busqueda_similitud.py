"""
Búsqueda de Similitud de Casos - JusticIA
Vista detallada del sistema de búsqueda semántica de casos judiciales.

Ejecutar: python busqueda_similitud.py
Output: output/busqueda_similitud.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.programming.framework import React, Fastapi
from diagrams.programming.language import Python
from diagrams.onprem.database import Mssql
from diagrams.onprem.compute import Server
from diagrams.custom import Custom


print("Generando diagrama: Búsqueda de Similitud de Casos...")

with Diagram(
    "JusticIA - Búsqueda Semántica\nAnálisis de Similitud de Casos Judiciales",
    show=False,
    direction="LR",
    filename="output/busqueda_similitud",
    outformat="png",
    graph_attr={
        "fontsize": "10",
        "bgcolor": "white",
        "ranksep": "2.5",
        "nodesep": "1.8",
        "pad": "2.0",
        "splines": "polyline"
    }
):
    usuario = User("Usuario")
    
    # Capa 1: Frontend
    with Cluster("Frontend", graph_attr={"bgcolor": "#e3f2fd", "penwidth": "2", "style": "rounded", "margin": "20", "pad": "0.6"}):
        search_ui = React("Search Interface")
    
    # Capa 2: API Gateway
    with Cluster("API", graph_attr={"bgcolor": "#f3e5f5", "penwidth": "2", "style": "rounded", "margin": "20", "pad": "0.6"}):
        similarity_router = Fastapi("Similarity Router\n\nPOST /search")
    
    # Capa 3: Almacenamiento (arriba)
    with Cluster("Persistencia", graph_attr={"bgcolor": "#e8f5e9", "penwidth": "2", "style": "rounded", "margin": "20", "pad": "0.6"}):
        sql_audit = Mssql("Azure SQL\n\nAuditoría")
    
    # Capa 4: Orquestador
    with Cluster("Orquestador", graph_attr={"bgcolor": "#ede7f6", "penwidth": "2", "style": "rounded", "margin": "20", "pad": "0.6"}):
        similarity_service = Python("SimilarityService\n\nAgregación resultados")
        busqueda_desc = Python("Búsqueda Descripción\n\ntop_k=30")
        busqueda_exp = Python("Búsqueda Expediente\n\nComparación vectorial")
    
    # Capa 5: Servicios de Procesamiento
    with Cluster("Procesamiento", graph_attr={"bgcolor": "#fff3e0", "penwidth": "2", "style": "rounded", "margin": "20", "pad": "0.6"}):
        doc_retrieval = Python("DocumentoRetrievalService\n\nAgrupa expedientes")
        doc_service = Python("DocumentoService\n\nEnriquece metadata")
    
    # Capa 6: Retrieval
    with Cluster("Retrieval", graph_attr={"bgcolor": "#e1f5fe", "penwidth": "2", "style": "rounded", "margin": "20", "pad": "0.6"}):
        retriever = Python("Retriever\n\ntop_k configurable")
        embedder = Custom("Embeddings\n\nBGE-M3", "/diagrams/icons/bge.jpeg")
        vector_store = Custom("VectorStore\n\nMilvus Client", "/diagrams/icons/milvus.png")
    
    # Capa 7: Base de datos vectorial
    with Cluster("Vector Database", graph_attr={"bgcolor": "#e0f2f1", "penwidth": "2", "style": "rounded", "margin": "20", "pad": "0.6"}):
        milvus_db = Custom("Milvus\n\nVector DB", "/diagrams/icons/milvus.png")
    
    # Capa 8: Base de datos relacional
    with Cluster("Relational Database", graph_attr={"bgcolor": "#fce4ec", "penwidth": "2", "style": "rounded", "margin": "20", "pad": "0.6"}):
        sql_db = Custom("Azure SQL\n\nMetadata", "/diagrams/icons/azure.png")
    
    # ===== FLUJO PRINCIPAL =====
    # 1. Usuario → Frontend
    usuario >> Edge(label=" 1. Búsqueda ", color="#1976d2", style="bold", fontsize="10") >> search_ui
    
    # 2. Frontend → API
    search_ui >> Edge(label=" 2. POST /search ", color="#1976d2", style="bold", fontsize="10") >> similarity_router
    
    # 3. API → Orquestador
    similarity_router >> Edge(label=" 3. Invocar búsqueda ", color="#7b1fa2", style="bold", fontsize="10") >> similarity_service
    
    # 4. Orquestador → Estrategias
    similarity_service >> Edge(label=" 4a. Modo descripción ", color="#f57c00", fontsize="9") >> busqueda_desc
    similarity_service >> Edge(label=" 4b. Modo expediente ", color="#0288d1", fontsize="9") >> busqueda_exp
    
    # 5. Descripción → Retriever
    busqueda_desc >> Edge(label=" 5. Query texto ", color="#f57c00", fontsize="10") >> retriever
    
    # 6. Retriever → Embeddings
    retriever >> Edge(label=" 6. Vectorizar ", color="#f57c00", fontsize="10") >> embedder
    
    # 7. Embeddings → VectorStore
    embedder >> Edge(label=" 7. Buscar similares ", color="#f57c00", fontsize="10") >> vector_store
    
    # 8. Expediente → VectorStore (directo)
    busqueda_exp >> Edge(label=" 8. Comparar vectores ", color="#0288d1", fontsize="10") >> vector_store
    
    # 9. VectorStore → Milvus
    vector_store >> Edge(label=" 9. Query vectorial ", color="#c2185b", style="dashed", fontsize="9") >> milvus_db
    
    # 10. Milvus → VectorStore (resultados)
    milvus_db >> Edge(label=" 10. Top K chunks ", color="#c2185b", style="dashed", fontsize="9") >> vector_store
    
    # 11. VectorStore → DocumentoRetrievalService
    vector_store >> Edge(label=" 11. Docs recuperados ", color="#388e3c", fontsize="10") >> doc_retrieval
    
    # 12. DocumentoRetrieval → DocumentoService
    doc_retrieval >> Edge(label=" 12. Agrupar casos ", color="#388e3c", fontsize="10") >> doc_service
    
    # 13. DocumentoService → SQL
    doc_service >> Edge(label=" 13. Obtener metadata ", color="#5e35b1", style="dashed", fontsize="9") >> sql_db
    
    # 14. SQL → DocumentoService
    sql_db >> Edge(label=" 14. Enriquecer datos ", color="#5e35b1", style="dashed", fontsize="9") >> doc_service
    
    # 15. DocumentoService → Orquestador
    doc_service >> Edge(label=" 15. Casos similares ", color="#388e3c", style="bold", fontsize="10") >> similarity_service
    
    # 16. Orquestador → API
    similarity_service >> Edge(label=" 16. Respuesta ", color="#7b1fa2", style="bold", fontsize="10") >> similarity_router
    
    # 17. API → SQL (auditoría)
    similarity_router >> Edge(label=" 17. Auditoría ", color="#5e35b1", style="dashed", fontsize="9") >> sql_audit
    
    # 18. API → Frontend
    similarity_router >> Edge(label=" 18. JSON response ", color="#1976d2", style="bold", fontsize="10") >> search_ui
    
    # 19. Frontend → Usuario
    search_ui >> Edge(label=" 19. Mostrar resultados ", color="#1976d2", style="bold", fontsize="10") >> usuario

print("Diagrama generado: output/busqueda_similitud.png")
