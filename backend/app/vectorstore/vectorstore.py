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

# ================================
# HELPERS DE FILTRADO CENTRALIZADO
# ================================

def _get_processed_document_ids(db=None) -> set:
    """
    Obtiene IDs de documentos procesados usando repository centralizado.
    Crea sesión temporal si no se proporciona db.
    
    Args:
        db: Sesión de BD (opcional)
        
    Returns:
        Set de IDs de documentos procesados
    """
    from app.repositories.documento_repository import DocumentoRepository
    
    db_creada = False
    if db is None:
        try:
            from app.db.database import get_db
            db = next(get_db())
            db_creada = True
        except Exception as e:
            logger.error(f"No se pudo crear sesión de BD para filtrar: {e}")
            return set()
    
    try:
        repo = DocumentoRepository()
        return repo.obtener_ids_procesados(db)
    except Exception as e:
        logger.error(f"Error obteniendo IDs procesados: {e}")
        return set()
    finally:
        if db_creada and db:
            db.close()


def _filter_by_processed_status(results: List[Dict[str, Any]], db=None) -> List[Dict[str, Any]]:
    """
    Filtra resultados para incluir solo documentos procesados.
    Usa repository centralizado.
    
    Args:
        results: Lista de resultados de búsqueda
        db: Sesión de BD (opcional)
        
    Returns:
        Lista filtrada de resultados
    """
    if not results:
        return results
    
    processed_ids = _get_processed_document_ids(db)
    
    if not processed_ids:
        logger.warning("No se pudieron obtener IDs procesados, devolviendo todos los resultados")
        return results
    
    filtered_results = []
    for doc in results:
        # Buscar ID del documento en metadata
        doc_id = None
        if isinstance(doc, dict):
            doc_id = doc.get("metadata", {}).get("id_documento") or doc.get("documento_id")
        elif isinstance(doc, Document):
            doc_id = doc.metadata.get("id_documento") if hasattr(doc, "metadata") else None
        
        # Incluir solo si está procesado
        if doc_id and doc_id in processed_ids:
            filtered_results.append(doc)
        elif doc_id:
            logger.debug(f"Documento {doc_id} excluido (estado != Procesado)")
    
    logger.info(f"Filtrado: {len(results)} → {len(filtered_results)} (solo procesados)")
    return filtered_results


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
    query_text: str, top_k: int = 20, score_threshold: float = 0.0, expediente_filter: Optional[str] = None, db=None
) -> List[Dict[str, Any]]:
    """
    Búsqueda semántica directa con texto.
    LangChain maneja automáticamente: texto → embedding → búsqueda
    Filtra automáticamente solo documentos procesados.

    Args:
        query_text: Texto de consulta
        top_k: Máximo de resultados
        score_threshold: Umbral de similitud mínimo
        expediente_filter: Si se proporciona, filtra solo documentos de este expediente
        db: Sesión de BD (opcional) - para filtrar solo documentos procesados

    Returns:
        Lista de documentos similares (solo procesados)
    """
    try:
        vectorstore = await get_langchain_vectorstore()

        # Si hay filtro de expediente, usar búsqueda híbrida
        if expediente_filter:
            logger.info(f"Búsqueda específica en expediente: {expediente_filter}")
            # Buscar todos los documentos del expediente específico
            client = await get_client()
            
            # Primero obtener todos los documentos del expediente
            logger.info(f"Buscando documentos para expediente: {expediente_filter}")
            expediente_docs = client.query(
                collection_name=COLLECTION_NAME,
                filter=f'numero_expediente == "{expediente_filter}"',
                output_fields=["id_chunk", "numero_expediente", "nombre_archivo", "texto", "id_documento"],
                limit=100  # Límite alto para obtener todos los documentos del expediente
            )
            logger.info(f"Documentos encontrados para expediente {expediente_filter}: {len(expediente_docs) if expediente_docs else 0}")
            
            if not expediente_docs:
                logger.warning(f"No se encontraron documentos para expediente: {expediente_filter}")
                return []
            
            # Crear resultados con alta relevancia para documentos del expediente específico
            formatted_results = []
            for i, doc in enumerate(expediente_docs):
                similarity_score = 0.9 - (i * 0.01)  # Score alto decreciente
                formatted_result = {
                    "id": doc.get("id_chunk", ""),
                    "expedient_id": doc.get("numero_expediente", ""),
                    "document_name": doc.get("nombre_archivo", ""),
                    "content_preview": doc.get("texto", ""),
                    "similarity_score": similarity_score,
                    "documento_id": doc.get("id_documento"),  # Para filtrado
                }
                if similarity_score >= score_threshold:
                    formatted_results.append(formatted_result)
            
            # Filtrar por estado "Procesado"
            formatted_results = _filter_by_processed_status(formatted_results, db)
            
            logger.info(f"Búsqueda por expediente específico: {len(formatted_results)} resultados")
            return formatted_results
        
        else:
            # Búsqueda semántica normal
            results = vectorstore.similarity_search(query=query_text, k=top_k)

            # Formatear resultados
            formatted_results = []
            for i, doc in enumerate(results):
                similarity_score = _calculate_similarity_score(doc, i, len(results))

                if similarity_score >= score_threshold:
                    formatted_results.append(_format_document_result(doc, similarity_score))

            # Filtrar por estado "Procesado"
            formatted_results = _filter_by_processed_status(formatted_results, db)

            logger.info(f"Búsqueda semántica: {len(formatted_results)} resultados")
            return formatted_results

    except Exception as e:
        logger.error(f"Error en búsqueda semántica: {e}")
        raise


async def get_complete_document_by_chunks(document_id: int) -> List[Dict[str, Any]]:
    """
    Recupera todos los chunks de un documento específico, ordenados por índice.
    
    Args:
        document_id: ID del documento en la base de datos
        
    Returns:
        Lista de chunks ordenados del documento completo
    """
    try:
        client = await get_client()
        
        # Buscar todos los chunks del documento específico
        query_results = client.query(
            collection_name=COLLECTION_NAME,
            filter=f'id_documento == {document_id}',
            output_fields=[
                "id_chunk",
                "texto", 
                "indice_chunk",
                "nombre_archivo",
                "numero_expediente",
                "tipo_archivo",
                "pagina_inicio",
                "pagina_fin",
                "tipo_documento",
                "fecha_carga",
                "meta"
            ],
            limit=1000  # Máximo chunks por documento
        )
        
        if not query_results:
            logger.info(f"No se encontraron chunks para el documento {document_id}")
            return []
        
        # Ordenar por índice de chunk para mantener el orden correcto
        sorted_chunks = sorted(query_results, key=lambda x: x.get("indice_chunk", 0))
        
        logger.info(f"Recuperados {len(sorted_chunks)} chunks para documento {document_id}")
        return sorted_chunks
        
    except Exception as e:
        logger.error(f"Error recuperando documento completo {document_id}: {e}")
        return []

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
    expedient_id: str, top_k: int = 20, score_threshold: float = 0.3, db=None
) -> List[Dict[str, Any]]:
    """
    Busca expedientes similares usando todos los vectores del expediente de referencia.
    Combina múltiples búsquedas y rankea los resultados.
    Filtra automáticamente solo documentos procesados.

    Args:
        expedient_id: ID del expediente de referencia
        top_k: Máximo de resultados finales
        score_threshold: Umbral mínimo de similitud
        db: Sesión de BD (opcional) - para filtrar solo documentos procesados

    Returns:
        Lista de documentos similares de otros expedientes, rankeados por similitud (solo procesados)
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
                            "documento_id": metadata.get("id_documento"),  # Para filtrado
                        }
                    )

        # 3. Rankear expedientes por score máximo y convertir a formato final
        final_results = []
        for exp_id, data in all_results.items():
            for doc in data["docs"]:
                final_results.append(doc)

        # Ordenar por similarity_score descendente
        final_results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

        # Filtrar por estado "Procesado"
        final_results = _filter_by_processed_status(final_results, db)

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
    Obtiene todos los documentos de un expediente específico usando query directa a Milvus.
    
    Args:
        expedient_id: ID del expediente a buscar
        
    Returns:
        Lista de objetos Document del expediente ordenados por indice_chunk
    """
    try:
        logger.info(f"Buscando expediente: {expedient_id}")
        
        client = await get_client()
        
        # Query directa a Milvus con filtro (más eficiente que búsqueda vectorial)
        query_results = client.query(
            collection_name=COLLECTION_NAME,
            filter=f'numero_expediente == "{expedient_id}"',
            output_fields=["id_chunk", "numero_expediente", "nombre_archivo", "texto", "indice_chunk", "tipo_documento", "meta"],
            limit=1000  # Límite alto para expedientes grandes
        )
        
        if not query_results:
            logger.warning(f"Expediente {expedient_id}: sin documentos")
            return []
        
        # Ordenar por indice_chunk para mantener secuencia
        sorted_results = sorted(query_results, key=lambda x: x.get("indice_chunk", 0))
        
        # Convertir a LangChain Documents
        langchain_docs = []
        for doc in sorted_results:
            try:
                content = doc.get("texto", "")
                if content.strip():
                    # Extraer ruta del campo meta
                    meta_data = doc.get("meta", {})
                    ruta_archivo = meta_data.get("ruta_archivo", "") if isinstance(meta_data, dict) else ""
                    
                    metadata = {
                        "numero_expediente": doc.get("numero_expediente", expedient_id),
                        "id_expediente": doc.get("numero_expediente", expedient_id),
                        "archivo": doc.get("nombre_archivo", ""),
                        "chunk_id": doc.get("id_chunk", ""),
                        "indice_chunk": doc.get("indice_chunk", 0),
                        "tipo_documento": doc.get("tipo_documento", ""),
                        "ruta_archivo": ruta_archivo
                    }
                    
                    langchain_docs.append(Document(
                        page_content=content,
                        metadata=metadata
                    ))
            except Exception as e:
                logger.warning(f"Error procesando chunk: {e}")
                continue
        
        logger.info(f"Expediente {expedient_id}: {len(langchain_docs)} documentos recuperados")
        return langchain_docs
        
    except Exception as e:
        logger.error(f"Error obteniendo expediente {expedient_id}: {e}")
        return []


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
            doc.page_content if hasattr(doc, "page_content") else ""
        ),
        "similarity_score": similarity_score,
        "metadata": metadata,
        "documento_id": metadata.get("id_documento"),  # Para filtrado por estado
    }
