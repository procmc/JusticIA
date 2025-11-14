"""
Definición del schema de colección Milvus.

Define la estructura completa de campos de la colección vectorial incluyendo
identificadores, referencias, embeddings y metadata flexible.

Estructura de campos:
    * Identidad: id_chunk (PK, VARCHAR UUID)
    * Referencias expedientes: id_expediente, numero_expediente, fecha_expediente_creacion
    * Referencias documentos: id_documento, nombre_archivo, tipo_archivo, fecha_carga
    * Datos RAG: texto, embedding, indice_chunk, paginas, tipo_documento
    * Timestamps: fecha_vectorizacion
    * Metadata flexible: meta (JSON)

Campos clave:
    * id_chunk: UUID único del chunk (PRIMARY KEY)
    * id_expediente/id_documento: FKs a BD transaccional
    * numero_expediente: Formato YY-NNNNNN-NNNN-XX para filtros
    * texto: Contenido del chunk (máx 8192 chars)
    * embedding: Vector BGE-M3 (DIM dimensiones)
    * meta: JSON flexible para extensiones

DataTypes:
    * VARCHAR: Strings con max_length definido
    * INT64/INT32: Enteros de diferentes tamaños
    * FLOAT_VECTOR: Vector de embeddings con dimensión DIM
    * JSON: Metadata flexible (schema-less)

Índices (creados en vectorstore.py):
    * embedding: HNSW para búsqueda vectorial (COSINE)
    * Campos escalares: STL_SORT para filtros rápidos

Configuraci��n:
    * DIM: Dimensión de embeddings (default 768, BGE-M3 usa 1024)
    * Load desde .env para flexibilidad

Limites:
    * texto: 8192 caracteres (límite Milvus)
    * nombre_archivo: 512 caracteres
    * id_chunk: 128 caracteres (UUIDs)
    * numero_expediente: 64 caracteres

Example:
    >>> from app.vectorstore.schema import COLLECTION_SCHEMA, COLLECTION_FIELDS
    >>> 
    >>> # Ver campos del schema
    >>> for field in COLLECTION_FIELDS:
    ...     print(f"{field.name}: {field.dtype}")
    >>> 
    >>> # Crear colección con schema
    >>> client.create_collection(
    ...     collection_name="mi_coleccion",
    ...     schema=COLLECTION_SCHEMA
    ... )

Note:
    * Schema es inmutable después de crear la colección
    * Cambios de schema requieren recrear colección (migration)
    * DIM debe coincidir con dimensión del modelo de embeddings
    * Campo meta permite extensibilidad sin cambiar schema
    * Todos los campos tienen tipos explícitos para performance

Ver también:
    * app.vectorstore.vectorstore: Usa COLLECTION_SCHEMA
    * app.embeddings: Genera vectores con dimensión DIM
    * app.config.config: Configuración de Milvus

Authors:
    JusticIA Team

Version:
    1.0.0 - Schema completo con metadata JSON
"""

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
