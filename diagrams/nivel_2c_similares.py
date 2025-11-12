"""
Nivel 2C - Componentes de Búsqueda de Casos Similares
Vista detallada del sistema de búsqueda semántica.

Ejecutar: python nivel_2c_similares.py
Output: output/nivel_2c_similares.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.programming.framework import React, Fastapi
from diagrams.programming.language import Python
from diagrams.onprem.database import Mssql
from diagrams.onprem.compute import Server

print("Generando Nivel 2C - Componentes de Busqueda de Casos Similares...")

with Diagram(
    "Nivel 2C - Búsqueda de Casos Similares",
    show=False,
    direction="LR",
    filename="output/nivel_2c_similares",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "ranksep": "1.0"
    }
):
    usuario = User("Usuario")
    
    with Cluster("Frontend - Búsqueda UI", graph_attr={"bgcolor": "#fff3e0"}):
        search_header = React("SearchHeader.jsx\n\nInput búsqueda\nFiltros expediente\nResults display")
        validator = Server("expedienteValidator.js\n\nNormaliza input\nValida formato")
    
    with Cluster("Backend API - Router", graph_attr={"bgcolor": "#f3e5f5"}):
        search_router = Fastapi("routes/search.py\n\nGET /search/similar\nQuery params\nPagination")
        schema = Server("search_schemas.py\n\nPydantic validation\nExpediente optional\nLimit/offset")
    
    with Cluster("Servicio de Similitud", graph_attr={"bgcolor": "#e1f5fe"}):
        similarity_service = Python("SimilarityService\n\nOrquestación búsqueda\nAlgoritmo ranking\nDe-duplication")
        
        with Cluster("Sub-componentes"):
            query_processor = Server("QueryProcessor\n\nExpand query\nExtract keywords\nSemantics")
            ranker = Server("RankingAlgorithm\n\nCOSINE score\nMetadata boost\nRelevance cutoff")
            aggregator = Server("ResultAggregator\n\nGroup by doc\nMerge chunks\nScore weighted")
    
    with Cluster("Búsqueda Vectorial", graph_attr={"bgcolor": "#f3e5f5"}):
        embedder = Server("EmbeddingService\n\nQuery embedding\nBGE-M3 1024D")
        vector_store = Server("VectorStoreService\n\nMulti-vector search\nMetadata filter\ntop_k configurable")
    
    with Cluster("Enriquecimiento Metadata", graph_attr={"bgcolor": "#fff9c4"}):
        doc_repo = Server("DocumentRepository\n\nFetch full metadata\nExpediente info\nDate/type/status")
        chunk_repo = Server("ChunkRepository\n\nContext expansion\nNeighbor chunks\nFull text")
    
    with Cluster("Almacenamiento", graph_attr={"bgcolor": "#e8f5e9"}):
        milvus = Server("Milvus\n\nVector similarity\nHNSW index\nCOSINE metric")
        sql = Mssql("SQL Server\n\nDocument details\nChunk context\nMetadata rich")
    
    # Flujo principal de búsqueda
    usuario >> Edge(label="1. Enter query", color="blue") >> search_header
    search_header >> Edge(label="2. Validate", color="blue") >> validator
    validator >> Edge(label="3. GET /search/similar", color="blue") >> search_router
    
    search_router >> Edge(label="4. Schema check", color="orange") >> schema
    search_router >> Edge(label="5. Orchestrate", color="green") >> similarity_service
    
    # Procesamiento interno
    similarity_service >> Edge(label="6. Process query", color="purple") >> query_processor
    query_processor >> Edge(label="7. Embed", color="purple") >> embedder
    embedder >> Edge(label="8. Vector search", color="purple") >> vector_store
    
    vector_store >> Edge(label="Search vectors", color="gray") >> milvus
    
    vector_store >> Edge(label="9. Top matches", color="darkgreen") >> ranker
    ranker >> Edge(label="10. Rank & score", color="darkgreen") >> aggregator
    
    # Enriquecimiento
    aggregator >> Edge(label="11. Fetch doc info", color="orange") >> doc_repo
    aggregator >> Edge(label="12. Fetch chunks", color="orange") >> chunk_repo
    
    doc_repo >> Edge(label="Query metadata", color="gray") >> sql
    chunk_repo >> Edge(label="Query chunks", color="gray") >> sql
    
    # Respuesta
    chunk_repo >> Edge(label="13. Enriched results", color="blue") >> search_router
    search_router >> Edge(label="14. JSON response", color="blue") >> search_header

print("Diagrama generado: output/nivel_2c_similares.png")
