"""
Consultas con IA (RAG) - Flujo General
Flujo básico del sistema de consultas con inteligencia artificial.

Ejecutar: python rag_simple.py
Output: output/rag_simple.png
"""

from diagrams import Diagram, Edge
from diagrams.onprem.client import User
from diagrams.programming.framework import React, Fastapi
from diagrams.programming.language import Python
from diagrams.custom import Custom


print("Generando diagrama: Consultas con IA RAG (Simple)...")

with Diagram(
    "JusticIA - Consultas con IA (RAG)\nFlujo General",
    show=False,
    direction="LR",
    filename="output/rag_simple",
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
    chat_ui = React("Frontend\n\nChat Interface")
    api = Fastapi("API\n\nRAG Router")
    rag_service = Python("RAG Service\n\nLangChain")
    retriever = Python("Retriever\n\nVector Search")
    milvus = Custom("Milvus\n\nDocumentos", "/diagrams/icons/milvus.png")
    llm = Custom("LLM\n\ngpt-oss-120B", "/diagrams/icons/ollama.png")
    
    # Flujo simplificado
    usuario >> Edge(label=" 1. Pregunta ", color="#1976d2", style="bold", fontsize="10") >> chat_ui
    chat_ui >> Edge(label=" 2. POST /consulta ", color="#1976d2", style="bold", fontsize="10") >> api
    api >> Edge(label=" 3. Invoca RAG ", color="#7b1fa2", style="bold", fontsize="10") >> rag_service
    rag_service >> Edge(label=" 4. Busca contexto ", color="#0288d1", fontsize="10") >> retriever
    retriever >> Edge(label=" 5. Query vectorial ", color="#c2185b", fontsize="10") >> milvus
    milvus >> Edge(label=" 6. Documentos relevantes ", color="#c2185b", style="dashed", fontsize="9") >> retriever
    retriever >> Edge(label=" 7. Contexto ", color="#388e3c", fontsize="10") >> rag_service
    rag_service >> Edge(label=" 8. Prompt + Contexto ", color="#388e3c", style="bold", fontsize="10") >> llm
    llm >> Edge(label=" 9. Respuesta generada ", color="#f57f17", style="bold", fontsize="10") >> rag_service
    rag_service >> Edge(label=" 10. Stream ", color="#f57f17", style="bold", fontsize="10") >> api
    api >> Edge(label=" 11. SSE ", color="#1976d2", style="bold", fontsize="10") >> chat_ui
    chat_ui >> Edge(label=" 12. Muestra respuesta ", color="#1976d2", style="bold", fontsize="10") >> usuario

print("Diagrama generado: output/rag_simple.png")
