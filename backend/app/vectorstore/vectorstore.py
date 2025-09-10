from pymilvus import MilvusClient
from app.config.config import MILVUS_URI, MILVUS_TOKEN, MILVUS_DB_NAME, COLLECTION_NAME
from app.vectorstore.schema import COLLECTION_SCHEMA
from typing import List, Dict, Any, Optional

_milvus_client = None

async def get_vectorstore():
    global _milvus_client
    if _milvus_client is None:
        _milvus_client = MilvusClient(
            uri=MILVUS_URI,
            token=MILVUS_TOKEN,
            db_name=MILVUS_DB_NAME,
        )
        # Verificar y crear colección si no existe
        existing = set(_milvus_client.list_collections())
        if COLLECTION_NAME not in existing:
            _milvus_client.create_collection(
                collection_name=COLLECTION_NAME,
                schema=COLLECTION_SCHEMA
            )
        # Crear índices (vector HNSW + escalares + JSON)
        index_params = _milvus_client.prepare_index_params()

        # Vector: HNSW (COSINE)
        index_params.add_index(
            field_name="embedding",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 200},
        )

        # Escalares que se filtran a menudo
        for f in [
            "id_expediente",
            "id_documento",
            "tipo_archivo",
            "fecha_carga",
        ]:
            index_params.add_index(field_name=f, index_type="STL_SORT")

        _milvus_client.create_index(collection_name=COLLECTION_NAME, index_params=index_params)
    return _milvus_client


async def search_similar_documents(
    query_embedding: List[float],
    limit: int = 30,
    filters: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Busca documentos similares basándose en el embedding de consulta.
    
    Args:
        query_embedding: Vector de la consulta
        limit: Número de documentos más relevantes a devolver
        filters: Filtros opcionales (ej: "id_expediente == 123")
    """
    try:
        client = await get_vectorstore()
        
        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 100}
        }
        
        results = client.search(
            collection_name=COLLECTION_NAME,
            data=[query_embedding],
            anns_field="embedding",
            search_params=search_params,
            limit=limit,
            expr=filters,
            output_fields=["id_chunk", "id_expediente", "id_documento", "texto", "nombre_archivo", "numero_expediente"]
        )
        
        if not results or len(results) == 0:
            return []
            
        hits = results[0]
        if not hits or len(hits) == 0:
            return []
        
        processed = []
        for hit in hits:
            try:
                # Formato estándar PyMilvus
                if hasattr(hit, 'entity') and hasattr(hit, 'distance'):
                    processed.append({
                        "entity": hit.entity,
                        "distance": hit.distance
                    })
                # Formato dict directo
                elif isinstance(hit, dict):
                    if 'distance' not in hit:
                        hit['distance'] = 1.0
                    processed.append(hit)
                else:
                    continue
                    
            except Exception:
                continue
        
        return processed
        
    except Exception as e:
        return []
