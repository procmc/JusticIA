"""
Nivel 2B - Componentes del Módulo RAG (Chat)
Vista detallada del sistema de conversación inteligente.

Ejecutar: python nivel_2b_rag.py
Output: output/nivel_2b_rag.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.programming.framework import React, Fastapi
from diagrams.programming.language import Python
from diagrams.onprem.database import Mssql
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.compute import Server

print("Generando Nivel 2B - Componentes del Modulo RAG...")

with Diagram(
    "Nivel 2B - Módulo RAG (Chat Inteligente)",
    show=False,
    direction="TB",
    filename="output/nivel_2b_rag",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "ranksep": "0.8"
    }
):
    usuario = User("Usuario")
    
    with Cluster("Frontend - Chat UI", graph_attr={"bgcolor": "#fff3e0"}):
        chat_ui = React("Chat.jsx\n\nInput conversacional\nSSE streaming\nTyping indicators")
        msg_utils = Server("messageUtils.js\n\nFormat messages\nManage history\nParse citations")
    
    with Cluster("Backend API - RAG Router", graph_attr={"bgcolor": "#f3e5f5"}):
        rag_router = Fastapi("routes/rag.py\n\nPOST /rag/query\nGET /rag/stream\nSession management")
    
    with Cluster("Servicio RAG Chain", graph_attr={"bgcolor": "#e1f5fe"}):
        rag_service = Python("RAGChainService\n\nOrquestación pipeline\nManejo contexto\nError handling")
        
        with Cluster("LangChain Pipeline"):
            history_aware = Server("History-Aware\nRetriever\n\nReformula query\ncon historial")
            retriever = Server("Retriever\n\nVector search\ntop_k=10-15\nReranking")
            rag_chain = Server("RAG Chain\n\nPrompt template\nContext injection\nCitations")
    
    with Cluster("Servicios de Búsqueda", graph_attr={"bgcolor": "#f3e5f5"}):
        vector_search = Server("VectorStoreService\n\nMilvus client\nSimilarity search\nMetadata filter")
        embedder = Server("EmbeddingService\n\nQuery embedding\nBGE-M3 1024D")
    
    with Cluster("Servicio LLM", graph_attr={"bgcolor": "#fce4ec"}):
        llm_service = Server("LLMService\n\nOllama client\nStreaming chunks\nTemperature: 0.3")
    
    with Cluster("Persistencia", graph_attr={"bgcolor": "#e8f5e9"}):
        redis_conv = Redis("Redis\n\nConversation\nhistory\nTTL: 24h")
        sql_audit = Mssql("SQL Server\n\nQuery audit\nUsage analytics\nFeedback")
        milvus = Server("Milvus\n\nChunk vectors\nDocument metadata")
    
    # Flujo principal RAG
    usuario >> Edge(label="1. Send message", color="blue") >> chat_ui
    chat_ui >> Edge(label="2. Format", color="blue") >> msg_utils
    msg_utils >> Edge(label="3. POST /rag/query", color="blue") >> rag_router
    
    rag_router >> Edge(label="4. Load session", color="red") >> redis_conv
    rag_router >> Edge(label="5. Orchestrate", color="green") >> rag_service
    
    # Pipeline interno
    rag_service >> Edge(label="6. Embed query", color="purple") >> embedder
    embedder >> Edge(label="7. Vector search", color="purple") >> vector_search
    vector_search >> Edge(label="Query vectors", color="gray") >> milvus
    
    vector_search >> Edge(label="8. Top chunks", color="orange") >> retriever
    retriever >> Edge(label="9. History context", color="orange") >> history_aware
    history_aware >> Edge(label="Fetch history", color="gray") >> redis_conv
    
    history_aware >> Edge(label="10. Build prompt", color="darkgreen") >> rag_chain
    rag_chain >> Edge(label="11. Stream generate", color="darkgreen") >> llm_service
    
    # Respuesta y persistencia
    llm_service >> Edge(label="12. SSE chunks", color="blue") >> rag_router
    rag_router >> Edge(label="13. Stream to client", color="blue") >> chat_ui
    
    rag_router >> Edge(label="14. Save conv", color="red") >> redis_conv
    rag_router >> Edge(label="15. Audit log", color="orange") >> sql_audit

print("Diagrama generado: output/nivel_2b_rag.png")
