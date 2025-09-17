from typing import List, Dict, Any, Optional
import logging

# LangChain imports para operaciones vectoriales
from langchain_milvus import Milvus
from langchain_core.documents import Document

# PyMilvus solo para configuración inicial
from pymilvus import MilvusClient

# Configuración local
from app.config.config import MILVUS_URI, MILVUS_TOKEN, MILVUS_DB_NAME, COLLECTION_NAME
from app.vectorstore.schema import COLLECTION_SCHEMA

logger = logging.getLogger(__name__)

# ================================
# CLIENTES GLOBALES
# ================================
_milvus_client = None
_langchain_vectorstore = None

# ================================
# FUNCIONES DE CONFIGURACIÓN
# ================================

async def get_client():
    """
    Cliente PyMilvus para configuración inicial y administración.
    """
    global _milvus_client
    
    if _milvus_client is None:
        _milvus_client = MilvusClient(
            uri=MILVUS_URI,
            token=MILVUS_TOKEN,
            db_name=MILVUS_DB_NAME,
        )
        
        # Crear colección si no existe
        if COLLECTION_NAME not in _milvus_client.list_collections():
            logger.info(f"Creando colección: {COLLECTION_NAME}")
            _milvus_client.create_collection(
                collection_name=COLLECTION_NAME,
                schema=COLLECTION_SCHEMA
            )
            
            # Crear índices optimizados
            index_params = _milvus_client.prepare_index_params()
            
            # Vector HNSW para similitud coseno
            index_params.add_index(
                field_name="embedding",
                index_type="HNSW",
                metric_type="COSINE",
                params={"M": 16, "efConstruction": 200},
            )
            
            # Índices escalares para filtros
            for field in ["id_expediente", "id_documento", "tipo_archivo", "fecha_carga"]:
                index_params.add_index(field_name=field, index_type="STL_SORT")
            
            _milvus_client.create_index(collection_name=COLLECTION_NAME, index_params=index_params)
            logger.info(f"Colección {COLLECTION_NAME} creada con índices optimizados")
    
    return _milvus_client

async def get_langchain_vectorstore():
    """
    VectorStore LangChain para todas las operaciones vectoriales.
    """
    global _langchain_vectorstore
    
    if _langchain_vectorstore is None:
        # Asegurar configuración inicial
        await get_client()
        
        # Crear adaptador de embeddings
        from app.embeddings.langchain_adapter import LangChainEmbeddingsAdapter
        embeddings_adapter = LangChainEmbeddingsAdapter()
        
        # Crear VectorStore LangChain
        _langchain_vectorstore = Milvus(
            embedding_function=embeddings_adapter,
            collection_name=COLLECTION_NAME,
            connection_args={
                "uri": MILVUS_URI,
                "token": MILVUS_TOKEN,
                "secure": True
            },
            primary_field="id_chunk",
            text_field="texto",
            vector_field="embedding"
        )
        
        logger.info("LangChain VectorStore configurado correctamente")
    
    return _langchain_vectorstore

# ================================
# INTERFAZ PRINCIPAL - BÚSQUEDAS
# ================================

async def search_by_vector(
    query_vector: List[float],
    top_k: int = 20,
    score_threshold: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Búsqueda vectorial usando LangChain.
    
    Args:
        query_vector: Vector de consulta
        top_k: Máximo de resultados
        score_threshold: Umbral de similitud mínimo
        
    Returns:
        Lista de documentos similares formateados
    """
    try:
        vectorstore = await get_langchain_vectorstore()
        
        # Búsqueda vectorial con LangChain
        results = vectorstore.similarity_search_by_vector(
            embedding=query_vector,
            k=top_k
        )
        
        # Formatear resultados
        formatted_results = []
        for i, doc in enumerate(results):
            similarity_score = _calculate_similarity_score(doc, i, len(results))
            
            if similarity_score >= score_threshold:
                formatted_results.append(_format_document_result(doc, similarity_score))
        
        logger.info(f"Búsqueda vectorial: {len(formatted_results)} resultados")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error en búsqueda vectorial: {e}")
        raise

async def search_by_text(
    query_text: str,
    top_k: int = 20,
    score_threshold: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Búsqueda semántica directa con texto.
    LangChain maneja automáticamente: texto → embedding → búsqueda
    
    Args:
        query_text: Texto de consulta
        top_k: Máximo de resultados
        score_threshold: Umbral de similitud mínimo
        
    Returns:
        Lista de documentos similares
    """
    try:
        vectorstore = await get_langchain_vectorstore()
        
        # Búsqueda semántica automática
        results = vectorstore.similarity_search(
            query=query_text,
            k=top_k
        )
        
        # Formatear resultados
        formatted_results = []
        for i, doc in enumerate(results):
            similarity_score = _calculate_similarity_score(doc, i, len(results))
            
            if similarity_score >= score_threshold:
                formatted_results.append(_format_document_result(doc, similarity_score))
        
        logger.info(f"Búsqueda semántica: {len(formatted_results)} resultados")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error en búsqueda semántica: {e}")
        raise

# ================================
# INTERFAZ PRINCIPAL - ALMACENAMIENTO
# ================================

async def add_documents(documents: List[Document]) -> List[str]:
    """
    Almacena documentos con embeddings automáticos.
    
    Args:
        documents: Lista de documentos LangChain
        
    Returns:
        Lista de IDs asignados
    """
    try:
        vectorstore = await get_langchain_vectorstore()
        
        # LangChain maneja automáticamente embeddings + inserción
        doc_ids = vectorstore.add_documents(documents)
        
        logger.info(f"Almacenados {len(doc_ids)} documentos")
        return doc_ids
        
    except Exception as e:
        logger.error(f"Error almacenando documentos: {e}")
        raise


async def get_stats() -> Dict[str, Any]:
    """
    Estadísticas de la colección.
    """
    try:
        client = await get_client()
        stats = client.get_collection_stats(collection_name=COLLECTION_NAME)
        
        return {
            "collection_name": COLLECTION_NAME,
            "stats": stats if isinstance(stats, dict) else {},
            "langchain_enabled": True
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return {"error": str(e)}

# ================================
# FUNCIONES AUXILIARES
# ================================

def _calculate_similarity_score(doc: Document, index: int, total: int) -> float:
    """Calcula score de similitud desde metadatos o estima por posición."""
    if hasattr(doc, 'metadata') and 'score' in doc.metadata:
        return doc.metadata['score']
    
    # Estimación por posición (más arriba = más similar)
    return max(0.0, 1.0 - (index * 0.05))

def _format_document_result(doc: Document, similarity_score: float) -> Dict[str, Any]:
    """Formatea documento LangChain al formato esperado por el sistema."""
    metadata = doc.metadata if hasattr(doc, 'metadata') else {}
    
    return {
        "id": metadata.get("id_chunk"),
        "expedient_id": metadata.get("numero_expediente") or metadata.get("id_expediente"),
        "document_name": metadata.get("nombre_archivo"),
        "content_preview": doc.page_content[:500] if hasattr(doc, 'page_content') else "",
        "similarity_score": similarity_score,
        "metadata": metadata
    }
