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
        "fontsize": "11",
        "bgcolor": "white",
        "ranksep": "2.0",
        "nodesep": "1.5",
        "pad": "1.5",
        "splines": "ortho"
    }
):
    usuario = User("Usuario")
    
    # Capa 1: Frontend
    with Cluster("Frontend", graph_attr={"bgcolor": "#e3f2fd", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        search_ui = React("Search Interface\n\nModos: descripción\no expediente")
    
    # Capa 2: API Gateway
    with Cluster("API Gateway", graph_attr={"bgcolor": "#f3e5f5", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        similarity_router = Fastapi("Similarity Router\n\nroutes/similarity.py\nPOST /search")
    
    # Capa 3: Almacenamiento (arriba)
    with Cluster("Persistencia", graph_attr={"bgcolor": "#e8f5e9", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        sql_audit = Mssql("Azure SQL Server\n\nAuditoría búsquedas\nExpedientes")
    
    # Capa 4: Orquestador
    with Cluster("Orquestador Similitud", graph_attr={"bgcolor": "#ede7f6", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        similarity_service = Python("SimilarityService\n\nDos modos búsqueda\nAgregación resultados")
        
        with Cluster("Estrategias Búsqueda", graph_attr={"bgcolor": "#f3e5f5", "style": "rounded", "margin": "20", "pad": "0.4"}):
            busqueda_desc = Python("Búsqueda Descripción\n\nDynamicJusticIARetriever\ntop_k=30")
            busqueda_exp = Python("Búsqueda Expediente\n\nsearch_similar_expedients\nComparación vectorial")
    
    # Capa 5: Servicios de Procesamiento
    with Cluster("Procesamiento Documentos", graph_attr={"bgcolor": "#fff3e0", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        doc_retrieval = Python("DocumentoRetrievalService\n\nAgrupa por expediente\nCalcula scores")
        doc_service = Python("DocumentoService\n\nObtiene metadata BD\nEnriquece resultados")
    
    # Capa 6: Retrieval
    with Cluster("Retrieval", graph_attr={"bgcolor": "#e1f5fe", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        retriever = Python("DynamicJusticIARetriever\n\ntop_k configurable\nthreshold 0.3")
        embedder = Custom("Embedding Service\n\nBGE-M3-ES-Legal\n1024 dimensiones", "/diagrams/icons/bge.jpeg")
        vector_store = Custom("VectorStore Service\n\nCliente Milvus\nBúsqueda similitud", "/diagrams/icons/milvus.png")
    
    # Capa 7: Bases de datos (abajo)
    with Cluster("Base de Datos", graph_attr={"bgcolor": "#fce4ec", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        milvus_db = Custom("Milvus\n\nVector Database\njusticia_docs\n", "/diagrams/icons/milvus.png")
        sql_db = Custom("Azure SQL Server\n\nExpedientes\nDocumentos", "/diagrams/icons/azure.png")
    
    # ===== FLUJO PRINCIPAL =====
    # 1. Usuario → Frontend
    usuario >> Edge(label="1. Búsqueda", color="#1976d2", style="bold") >> search_ui
    
    # 2. Frontend → API
    search_ui >> Edge(label="2. POST /search", color="#1976d2", style="bold") >> similarity_router
    
    # 3. API → Orquestador
    similarity_router >> Edge(label="3. Invocar búsqueda", color="#7b1fa2", style="bold") >> similarity_service
    
    # 4. Orquestador → Estrategia (decidir cuál)
    similarity_service >> Edge(label="4a. Modo descripción", color="#f57c00") >> busqueda_desc
    similarity_service >> Edge(label="4b. Modo expediente", color="#0288d1") >> busqueda_exp
    
    # 5. Descripción → Retriever
    busqueda_desc >> Edge(label="5. Query texto", color="#f57c00") >> retriever
    
    # 6. Retriever → Embeddings
    retriever >> Edge(label="6. Vectorizar", color="#f57c00") >> embedder
    
    # 7. Embeddings → VectorStore
    embedder >> Edge(label="7. Buscar similares", color="#f57c00") >> vector_store
    
    # 8. VectorStore → Milvus (búsqueda)
    vector_store >> Edge(label="8. Query vectorial", color="#c2185b", style="dashed") >> milvus_db
    
    # 9. Milvus → VectorStore → Retriever (resultados)
    milvus_db >> Edge(label="9. Top K chunks", color="#c2185b", style="dashed") >> vector_store
    vector_store >> Edge(label="Documentos", color="#f57c00") >> retriever
    
    # 10. Expediente también usa VectorStore
    busqueda_exp >> Edge(label="10. Búsqueda expediente", color="#0288d1") >> vector_store
    
    # 11. Ambas estrategias → DocumentoRetrievalService
    retriever >> Edge(label="11a. Docs recuperados", color="#388e3c") >> doc_retrieval
    busqueda_exp >> Edge(label="11b. Expedientes similares", color="#388e3c") >> doc_retrieval
    
    # 12. DocumentoRetrieval → DocumentoService (enriquecer)
    doc_retrieval >> Edge(label="12. Agrupar casos", color="#388e3c") >> doc_service
    
    # 13. DocumentoService → SQL (obtener metadata)
    doc_service >> Edge(label="13. Obtener expedientes", color="#5e35b1", style="dashed") >> sql_db
    
    # 14. SQL → DocumentoService (datos)
    sql_db >> Edge(label="14. Metadata", color="#5e35b1", style="dashed") >> doc_service
    
    # 15. DocumentoService → Orquestador (resultados finales)
    doc_service >> Edge(label="15. Casos similares", color="#388e3c") >> similarity_service
    
    # 16. Orquestador → API
    similarity_service >> Edge(label="16. Respuesta procesada", color="#7b1fa2", style="bold") >> similarity_router
    
    # 17. API → SQL (auditoría)
    similarity_router >> Edge(label="17. Log auditoría", color="#5e35b1", style="dashed") >> sql_audit
    
    # 18. API → Frontend (respuesta)
    similarity_router >> Edge(label="18. JSON response", color="#1976d2", style="bold") >> search_ui
    
    # 19. Frontend → Usuario
    search_ui >> Edge(label="19. Mostrar resultados", color="#1976d2", style="bold") >> usuario

print("Diagrama generado: output/busqueda_similitud.png")
