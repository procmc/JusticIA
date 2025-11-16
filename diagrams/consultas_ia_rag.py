"""
Consultas con IA (RAG) - JusticIA
Vista detallada del sistema de recuperación y generación aumentada.

Ejecutar: python consultas_ia_rag.py
Output: output/consultas_ia_rag.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.programming.framework import React, Fastapi
from diagrams.programming.language import Python
from diagrams.onprem.database import Mssql
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.compute import Server
from diagrams.custom import Custom


print("Generando diagrama: Consultas con IA (RAG)...")

with Diagram(
    "JusticIA - Consultas con IA\nRAG: Recuperación y Generación Aumentada",
    show=False,
    direction="LR",
    filename="output/consultas_ia_rag",
    outformat="png",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "ranksep": "2.0",
        "nodesep": "1.5",
        "pad": "1.5",
        "splines": "polyline"
    }
):
    usuario = User("Usuario")
    
    # Capa 1: Frontend
    with Cluster("Frontend", graph_attr={"bgcolor": "#e3f2fd", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        chat_ui = React("Chat Interface\n\nInput usuario\nStreaming SSE")
    
    # Capa 2: API Gateway
    with Cluster("API Gateway", graph_attr={"bgcolor": "#f3e5f5", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        rag_router = Fastapi("RAG Router\n\nroutes/rag.py\nPOST /consulta-con-historial")
    
    # Capa 3: Almacenamiento (arriba)
    with Cluster("Persistencia", graph_attr={"bgcolor": "#e8f5e9", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        redis_store = Redis("Redis\n\nSession Store\nConversaciones")
        sql_audit = Mssql("Azure SQL Server\n\nAuditoría RAG\nAnalítica")
    
    # Capa 4: Orquestador RAG
    with Cluster("Orquestador RAG", graph_attr={"bgcolor": "#ede7f6", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        rag_service = Python("RAGChainService\n\nConversational Chain\nGestión contexto")
        
        with Cluster("Pipeline LangChain", graph_attr={"bgcolor": "#f3e5f5", "style": "rounded", "margin": "20", "pad": "0.4"}):
            history_aware = Custom("History-Aware Retriever\n\nReformula query\ncon historial", "/diagrams/icons/langchain.png")
            stuff_chain = Custom("Stuff Documents Chain\n\nPrompt + Context\nGeneración respuesta", "/diagrams/icons/langchain.png")
    
    # Capa 5: Servicios
    with Cluster("Retrieval", graph_attr={"bgcolor": "#e1f5fe", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        retriever = Python("DynamicJusticIARetriever\n\ntop_k=15 general\ntop_k=30 expediente")
        embedder = Python("Embedding Service\n\nBGE-M3-ES-Legal\n1024 dimensiones")
        vector_store = Python("VectorStore Service\n\nCliente Milvus\nBúsqueda similitud")
    
    with Cluster("LLM", graph_attr={"bgcolor": "#fff3e0", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        llm = Custom("Ollama LLM\n\ngpt-oss:120b\nTemp: 0.3 | Stream", "/diagrams/icons/ollama.png")
    
    # Capa 6: Bases de datos (abajo)
    with Cluster("Base de Datos", graph_attr={"bgcolor": "#fce4ec", "penwidth": "2", "style": "rounded", "margin": "25", "pad": "0.8"}):
        milvus_db = Custom("Milvus\n\nVector Database\njusticia_docs\n", "/diagrams/icons/milvus.png")
    
    # ===== FLUJO PRINCIPAL =====
    # 1. Usuario → Frontend
    usuario >> Edge(label=" 1. Consulta ", color="#1976d2", style="bold", fontsize="10") >> chat_ui
    
    # 2. Frontend → API
    chat_ui >> Edge(label=" 2. POST /consulta ", color="#1976d2", style="bold", fontsize="10") >> rag_router
    
    # 3. API → Redis (cargar sesión)
    rag_router >> Edge(label=" 3. Cargar sesión ", color="#f57c00", style="dashed", fontsize="9") >> redis_store
    
    # 4. API → Orquestador
    rag_router >> Edge(label=" 4. Invocar RAG ", color="#7b1fa2", style="bold", fontsize="10") >> rag_service
    
    # 5. Orquestador → History-Aware (con historial de Redis)
    rag_service >> Edge(label=" 5. Reformular query ", color="#7b1fa2", fontsize="10") >> history_aware
    history_aware >> Edge(label=" Historial ", color="#f57c00", style="dashed", fontsize="9") >> redis_store
    
    # 6. History-Aware → Retriever
    history_aware >> Edge(label=" 6. Query reformulada ", color="#0288d1", fontsize="10") >> retriever
    
    # 7. Retriever → Embeddings
    retriever >> Edge(label=" 7. Vectorizar ", color="#0288d1", fontsize="10") >> embedder
    
    # 8. Embeddings → VectorStore
    embedder >> Edge(label=" 8. Buscar similares ", color="#0288d1", fontsize="10") >> vector_store
    
    # 9. VectorStore → Milvus
    vector_store >> Edge(label=" 9. Query vectorial ", color="#c2185b", style="dashed", fontsize="9") >> milvus_db
    
    # 10. Milvus → VectorStore → Retriever (resultados)
    milvus_db >> Edge(label=" 10. Top K chunks ", color="#c2185b", style="dashed", fontsize="9") >> vector_store
    vector_store >> Edge(label=" Documentos ", color="#0288d1", fontsize="9") >> retriever
    
    # 11. Retriever → Stuff Chain
    retriever >> Edge(label=" 11. Contexto ", color="#388e3c", fontsize="10") >> stuff_chain
    
    # 12. Stuff Chain → LLM
    stuff_chain >> Edge(label=" 12. Prompt completo ", color="#388e3c", style="bold", fontsize="10") >> llm
    
    # 13. LLM → Orquestador (streaming)
    llm >> Edge(label=" 13. Respuesta stream ", color="#f57f17", style="bold", fontsize="10") >> rag_service
    
    # 14. Orquestador → API
    rag_service >> Edge(label=" 14. Stream chunks ", color="#f57f17", style="bold", fontsize="10") >> rag_router
    
    # 15. API → Redis (guardar conversación)
    rag_router >> Edge(label=" 15. Guardar historial ", color="#f57c00", style="dashed", fontsize="9") >> redis_store
    
    # 16. API → SQL (auditoría)
    rag_router >> Edge(label=" 16. Log auditoría ", color="#5e35b1", style="dashed", fontsize="9") >> sql_audit
    
    # 17. API → Frontend (respuesta)
    rag_router >> Edge(label=" 17. SSE response ", color="#1976d2", style="bold", fontsize="10") >> chat_ui
    
    # 18. Frontend → Usuario
    chat_ui >> Edge(label=" 18. Mostrar respuesta ", color="#1976d2", style="bold", fontsize="10") >> usuario

print("Diagrama generado: output/consultas_ia_rag.png")
