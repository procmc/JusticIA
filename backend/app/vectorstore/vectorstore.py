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
                collection_name=COLLECTION_NAME, schema=COLLECTION_SCHEMA
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
            for field in [
                "id_expediente",
                "id_documento",
                "tipo_archivo",
                "fecha_carga",
            ]:
                index_params.add_index(field_name=field, index_type="STL_SORT")

            _milvus_client.create_index(
                collection_name=COLLECTION_NAME, index_params=index_params
            )
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
            connection_args={"uri": MILVUS_URI, "token": MILVUS_TOKEN, "secure": True},
            primary_field="id_chunk",
            text_field="texto",
            vector_field="embedding",
        )

        logger.info("LangChain VectorStore configurado correctamente")

    return _langchain_vectorstore


# ================================
# INTERFAZ PRINCIPAL - BÚSQUEDAS
# ================================


async def search_by_vector(
    query_vector: List[float], top_k: int = 20, score_threshold: float = 0.0
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
            embedding=query_vector, k=top_k
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
    query_text: str, top_k: int = 20, score_threshold: float = 0.0
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
        results = vectorstore.similarity_search(query=query_text, k=top_k)

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


async def get_expedient_summary(expedient_id: str) -> str:
    """
    Busca todos los documentos de un expediente en Milvus y genera un resumen.

    Args:
        expedient_id: ID del expediente a buscar

    Returns:
        Resumen combinado del contenido de todos los documentos del expediente
    """
    try:
        client = await get_client()

        # Buscar todos los documentos del expediente usando filtro
        query_results = client.query(
            collection_name=COLLECTION_NAME,
            filter=f'numero_expediente == "{expedient_id}"',
            output_fields=[
                "texto",
                "nombre_archivo",
                "numero_expediente",
                "tipo_archivo",
            ],
            limit=1000,  # Máximo documentos por expediente
        )

        if not query_results:
            logger.info(
                f"No se encontraron documentos para el expediente {expedient_id}"
            )
            return f"Expediente {expedient_id} sin contenido"

        # Combinar contenido de todos los documentos
        texto_parts = [expedient_id]  # Incluir ID del expediente

        for doc in query_results:
            texto_content = doc.get("texto", "")
            if texto_content and texto_content.strip():
                # Tomar primeros 300 caracteres de cada chunk
                preview = texto_content.strip()[:300]
                texto_parts.append(preview)

        resumen_final = " ".join(texto_parts)
        return resumen_final if resumen_final else f"Expediente {expedient_id}"

    except Exception as e:
        logger.error(f"Error obteniendo resumen del expediente {expedient_id}: {e}")
        return f"Expediente {expedient_id}"


async def search_similar_expedients(
    expedient_id: str, top_k: int = 20, score_threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Busca expedientes similares usando todos los vectores del expediente de referencia.
    Combina múltiples búsquedas y rankea los resultados.

    Args:
        expedient_id: ID del expediente de referencia
        top_k: Máximo de resultados finales
        score_threshold: Umbral mínimo de similitud

    Returns:
        Lista de documentos similares de otros expedientes, rankeados por similitud
    """
    try:
        client = await get_client()
        vectorstore = await get_langchain_vectorstore()

        # 1. Obtener todos los vectores del expediente de referencia
        query_results = client.query(
            collection_name=COLLECTION_NAME,
            filter=f'numero_expediente == "{expedient_id}"',
            output_fields=["embedding", "texto", "nombre_archivo"],
            limit=100,  # Máximo chunks por expediente
        )

        if not query_results:
            logger.info(f"No se encontraron vectores para el expediente {expedient_id}")
            return []

        # 2. Buscar similares para cada vector del expediente
        all_results = {}  # {expedient_id: {score: max_score, docs: [docs]}}

        for i, doc in enumerate(query_results):
            embedding = doc.get("embedding", [])
            if not embedding:
                continue

            # Buscar similares usando este vector específico
            vector_results = vectorstore.similarity_search_by_vector(
                embedding=embedding, k=top_k * 2  # Buscar más para tener opciones
            )

            # Procesar resultados de esta búsqueda
            for j, result_doc in enumerate(vector_results):
                metadata = (
                    result_doc.metadata if hasattr(result_doc, "metadata") else {}
                )
                result_expedient_id = metadata.get("numero_expediente") or metadata.get(
                    "id_expediente"
                )

                # Excluir el expediente actual
                if result_expedient_id == expedient_id or not result_expedient_id:
                    continue

                # Calcular score para este resultado
                similarity_score = _calculate_similarity_score(
                    result_doc, j, len(vector_results)
                )

                if similarity_score < score_threshold:
                    continue

                # Combinar resultados por expediente
                if result_expedient_id not in all_results:
                    all_results[result_expedient_id] = {
                        "max_score": similarity_score,
                        "docs": [],
                    }
                else:
                    # Actualizar score máximo
                    all_results[result_expedient_id]["max_score"] = max(
                        all_results[result_expedient_id]["max_score"], similarity_score
                    )

                # Agregar documento si no existe
                doc_exists = any(
                    doc.get("document_name") == metadata.get("nombre_archivo")
                    for doc in all_results[result_expedient_id]["docs"]
                )

                if not doc_exists:
                    all_results[result_expedient_id]["docs"].append(
                        {
                            "id": metadata.get("id_chunk"),
                            "expedient_id": result_expedient_id,
                            "document_name": metadata.get("nombre_archivo"),
                            "content_preview": (
                                result_doc.page_content[:500]
                                if hasattr(result_doc, "page_content")
                                else ""
                            ),
                            "similarity_score": similarity_score,
                            "metadata": metadata,
                        }
                    )

        # 3. Rankear expedientes por score máximo y convertir a formato final
        final_results = []
        for exp_id, data in all_results.items():
            for doc in data["docs"]:
                final_results.append(doc)

        # Ordenar por similarity_score descendente
        final_results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

        # Limitar resultados finales
        final_results = final_results[:top_k]

        return final_results

    except Exception as e:
        logger.error(f"Error en búsqueda híbrida para expediente {expedient_id}: {e}")
        return []


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
            "langchain_enabled": True,
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return {"error": str(e)}


async def get_expedient_documents(expedient_id: str) -> List[Document]:
    """
    Obtiene todos los documentos de un expediente específico usando LangChain.
    
    Args:
        expedient_id: ID del expediente a buscar
        
    Returns:
        Lista de objetos Document del expediente
    """
    try:
        vectorstore = await get_langchain_vectorstore()
        
        # Buscar usando el número de expediente como query
        # Esto debería devolver documentos relacionados con el expediente
        all_docs = vectorstore.similarity_search(
            query=f"expediente {expedient_id}",
            k=500  # Buscar muchos documentos para asegurar obtener todos del expediente
        )
        
        if not all_docs:
            logger.info(f"No se encontraron documentos para el expediente {expedient_id}")
            return []
        
        # Filtrar documentos que realmente pertenecen al expediente
        expedient_docs = []
        for doc in all_docs:
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            doc_expedient = metadata.get('numero_expediente') or metadata.get('id_expediente')
            
            if doc_expedient == expedient_id:
                expedient_docs.append(doc)
        
        # Si no encontramos documentos con filtro, intentar búsqueda más amplia
        if not expedient_docs:
            logger.info(f"No se encontraron documentos con filtro, intentando búsqueda más amplia")
            
            # Hacer una búsqueda más general
            all_docs_broad = vectorstore.similarity_search(
                query=expedient_id,  # Buscar solo por el ID
                k=1000
            )
            
            for doc in all_docs_broad:
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
                doc_expedient = metadata.get('numero_expediente') or metadata.get('id_expediente')
                
                if doc_expedient == expedient_id:
                    expedient_docs.append(doc)
        
        logger.info(f"Encontrados {len(expedient_docs)} documentos para expediente {expedient_id}")
        return expedient_docs
        
    except Exception as e:
        logger.error(f"Error obteniendo documentos del expediente {expedient_id}: {e}")
        raise


# ================================
# FUNCIONES AUXILIARES
# ================================


def _calculate_similarity_score(doc: Document, index: int, total: int) -> float:
    """Calcula score de similitud desde metadatos o estima por posición."""
    if hasattr(doc, "metadata") and "score" in doc.metadata:
        return doc.metadata["score"]

    # Estimación por posición (más arriba = más similar)
    return max(0.0, 1.0 - (index * 0.05))


def _format_document_result(doc: Document, similarity_score: float) -> Dict[str, Any]:
    """Formatea documento LangChain al formato esperado por el sistema."""
    metadata = doc.metadata if hasattr(doc, "metadata") else {}

    return {
        "id": metadata.get("id_chunk"),
        "expedient_id": metadata.get("numero_expediente")
        or metadata.get("id_expediente"),
        "document_name": metadata.get("nombre_archivo"),
        "content_preview": (
            doc.page_content[:500] if hasattr(doc, "page_content") else ""
        ),
        "similarity_score": similarity_score,
        "metadata": metadata,
    }
