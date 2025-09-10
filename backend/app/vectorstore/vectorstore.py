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
        
        # Verificar que la colección existe y tiene datos
        try:
            stats = client.get_collection_stats(collection_name=COLLECTION_NAME)
            print(f"Estadísticas de la colección: {stats}")
            
            # Verificar si hay documentos
            row_count = stats.get('row_count', 0) if isinstance(stats, dict) else 0
            if row_count == 0:
                print("⚠️ La colección no tiene documentos")
                return []
                
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
        
        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 100}
        }
        
        # Preparar parámetros de búsqueda base
        search_kwargs = {
            "collection_name": COLLECTION_NAME,
            "data": [query_embedding],
            "anns_field": "embedding",
            "search_params": search_params,
            "limit": limit,
            "output_fields": ["id_chunk", "id_expediente", "id_documento", "texto", "nombre_archivo", "numero_expediente"]
        }
        
        # Solo agregar expr si filters no es None
        if filters is not None:
            search_kwargs["expr"] = filters
        
        print(f"Buscando con parámetros: {search_kwargs}")
        results = client.search(**search_kwargs)
        print(f"Resultados obtenidos: {len(results) if results else 0}")
        
        if not results or len(results) == 0:
            print("No se obtuvieron resultados de la búsqueda")
            return []
            
        hits = results[0]
        if not hits or len(hits) == 0:
            print("No hay hits en los resultados")
            return []
        
        print(f"Procesando {len(hits)} hits")
        processed = []
        for hit in hits:
            try:
                # Formato estándar PyMilvus - acceso seguro a atributos
                if hasattr(hit, 'entity') and hasattr(hit, 'distance'):
                    entity_data = getattr(hit, 'entity', {})
                    distance_value = getattr(hit, 'distance', 1.0)
                    processed.append({
                        "entity": entity_data,
                        "distance": distance_value
                    })
                # Formato dict directo
                elif isinstance(hit, dict):
                    if 'distance' not in hit:
                        hit['distance'] = 1.0
                    processed.append(hit)
                else:
                    continue
                    
            except Exception as e:
                print(f"Error procesando hit: {e}")
                continue
        
        print(f"Documentos procesados exitosamente: {len(processed)}")
        return processed
        
    except Exception as e:
        print(f"Error en búsqueda vectorial: {e}")
        return []
