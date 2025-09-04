
import os
from dotenv import load_dotenv
from pymilvus import CollectionSchema, FieldSchema, DataType


load_dotenv()
DIM = int(os.getenv("DIM", "768"))

COLLECTION_FIELDS = [
    # --- Identidad del chunk (PK en la vectorial) ---
    FieldSchema(name="id_chunk", dtype=DataType.VARCHAR, is_primary=True, max_length=128),

    # --- Referencias a Expedientes (transaccional) ---
    FieldSchema(name="id_expediente", dtype=DataType.INT64, max_length=64),     # Expedientes.IdExpediente
    FieldSchema(name="numero_expediente", dtype=DataType.VARCHAR, max_length=64), # Expedientes.NumeroExpediente (único a nivel negocio)
    FieldSchema(name="fecha_expediente_creacion", dtype=DataType.INT64, nullable=True),  # Expedientes.FechaCreacion (epoch ms)

    # --- Referencias a Documentos (transaccional) ---
    FieldSchema(name="id_documento", dtype=DataType.INT64, max_length=64),      # Documentos.IdDocumento
    FieldSchema(name="nombre_archivo", dtype=DataType.VARCHAR, max_length=512),   # Documentos.NombreArchivo
    FieldSchema(name="tipo_archivo", dtype=DataType.INT32, max_length=16),      # Documentos.TipoArchivo (PDF, DOCX, MP3, ...)
    FieldSchema(name="fecha_carga", dtype=DataType.INT64),                        # Documentos.FechaCarga (epoch ms)

    # --- Datos del chunk (para RAG) ---
    FieldSchema(name="texto", dtype=DataType.VARCHAR, max_length=8192, nullable=True),  # Chunk de texto (máx 8K chars)
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIM),
    FieldSchema(name="indice_chunk", dtype=DataType.INT32, nullable=True),
    FieldSchema(name="pagina_inicio", dtype=DataType.INT32, nullable=True),
    FieldSchema(name="pagina_fin", dtype=DataType.INT32, nullable=True),
    FieldSchema(name="tipo_documento", dtype=DataType.VARCHAR, max_length=32, nullable=True),  # p.ej. sentencia, resolución

    # --- Tiempos del pipeline de IA ---
    FieldSchema(name="fecha_vectorizacion", dtype=DataType.INT64, nullable=True), # cuándo se generó el embedding (epoch ms)

    # --- Metadatos flexibles ---
    FieldSchema(name="meta", dtype=DataType.JSON, nullable=True),
]

COLLECTION_SCHEMA = CollectionSchema(fields=COLLECTION_FIELDS)
