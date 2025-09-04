from pymilvus import MilvusClient
from app.config.config import MILVUS_URI, MILVUS_TOKEN, MILVUS_DB_NAME, COLLECTION_NAME
from app.vectorstore.schema import COLLECTION_SCHEMA

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
            print(f"Colección creada: {COLLECTION_NAME}")

        else:
            print(f"Colección ya existe: {COLLECTION_NAME}")

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
        print("Índices creados/actualizados")

        # (Opcional) mostrar resumen
        print("Colecciones:", _milvus_client.list_collections())
    return _milvus_client
