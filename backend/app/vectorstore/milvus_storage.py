import uuid
import time
from app.embeddings.embeddings import get_embeddings
from app.config.config import COLLECTION_NAME
from app.config.file_config import FILE_TYPE_CODES
from app.vectorstore.vectorstore import get_vectorstore
from pathlib import Path

async def store_in_vectorstore(texto: str, metadatos: dict,  CT_Num_expediente: str):
    """
    Almacena el texto extraído en Milvus.
    """
    # Obtener cliente Milvus
    client = await get_vectorstore()
    
    # Generar embedding del texto
    embeddings_model = await get_embeddings()
    embedding = await embeddings_model.aembed_query(texto)
    
    # Preparar datos según el schema de Milvus
    timestamp_ms = int(time.time() * 1000)  # timestamp en milisegundos
    
    # Obtener código de tipo de archivo
    extension = Path(metadatos["nombre_archivo"]).suffix.lower()
    tipo_archivo_codigo = FILE_TYPE_CODES.get(extension, 1)  # Default TXT
    
    data = [{
        "id_chunk": str(uuid.uuid4()),  # Primary key según schema
        "id_expediente": hash(CT_Num_expediente) % (2**31),  # Convertir expediente a INT64
        "numero_expediente": CT_Num_expediente,
        "fecha_expediente_creacion": timestamp_ms,
        "id_documento": hash(metadatos["file_id"]) % (2**31),  # Convertir a INT64
        "nombre_archivo": metadatos["nombre_archivo"],
        "tipo_archivo": tipo_archivo_codigo,  # Usar código numérico
        "fecha_carga": timestamp_ms,
        "texto": texto[:8192],  # Truncar si es muy largo
        "embedding": embedding,
        "indice_chunk": 0,  # Primer chunk
        "pagina_inicio": 1,
        "pagina_fin": 1,
        "tipo_documento": "documento",
        "fecha_vectorizacion": timestamp_ms,
        "meta": metadatos  # Metadatos adicionales como JSON
    }]
    
    # Insertar en Milvus
    result = client.insert(
        collection_name=COLLECTION_NAME,
        data=data
    )
    
    print(f"✔ Documento insertado en Milvus: {metadatos['nombre_archivo']}")
    return result
