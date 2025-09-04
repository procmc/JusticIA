import uuid
import time
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.embeddings.embeddings import get_embeddings
from app.config.config import COLLECTION_NAME
from app.config.file_config import FILE_TYPE_CODES
from app.vectorstore.vectorstore import get_vectorstore
from pathlib import Path

async def store_in_vectorstore(texto: str, metadatos: dict, CT_Num_expediente: str):
    """
    Almacena el texto extraído en Milvus dividido en chunks para manejar documentos grandes.
    
    Args:
        texto: Texto completo del documento
        metadatos: Metadatos del documento  
        CT_Num_expediente: Número de expediente
        
    Returns:
        List: Resultados de inserción para cada chunk
    """
    # Obtener cliente Milvus
    client = await get_vectorstore()
    
    # Obtener modelo de embeddings
    embeddings_model = await get_embeddings()
    
    # Configurar el text splitter para chunks de máximo 7000 caracteres
    # (dejamos margen por si hay caracteres especiales que ocupen más espacio)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=7000,      # Tamaño máximo del chunk
        chunk_overlap=200,    # Overlap entre chunks para mantener contexto
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]  # Separadores en orden de preferencia
    )
    
    # Dividir el texto en chunks
    chunks = text_splitter.split_text(texto)
    
    print(f"Documento dividido en {len(chunks)} chunks")
    
    # Preparar datos comunes
    timestamp_ms = int(time.time() * 1000)
    extension = Path(metadatos["nombre_archivo"]).suffix.lower()
    tipo_archivo_codigo = FILE_TYPE_CODES.get(extension, 1)
    
    # Procesar cada chunk
    all_data = []
    results = []
    
    # Estimar páginas aproximadas (asumiendo ~500 palabras por página)
    caracteres_por_pagina = 2500  # Aproximadamente 500 palabras x 5 chars/palabra
    
    for i, chunk_text in enumerate(chunks):
        # Generar embedding para este chunk
        embedding = await embeddings_model.aembed_query(chunk_text)
        
        # Calcular páginas aproximadas para este chunk
        inicio_char = i * (7000 - 200)  # Tamaño chunk menos overlap
        fin_char = inicio_char + len(chunk_text)
        
        pagina_inicio = max(1, (inicio_char // caracteres_por_pagina) + 1)
        pagina_fin = max(pagina_inicio, (fin_char // caracteres_por_pagina) + 1)
        
        # Preparar datos según el schema de Milvus
        chunk_data = {
            "id_chunk": str(uuid.uuid4()),  # Primary key único para cada chunk
            "id_expediente": hash(CT_Num_expediente) % (2**31),
            "numero_expediente": CT_Num_expediente,
            "fecha_expediente_creacion": timestamp_ms,
            "id_documento": hash(metadatos["file_id"]) % (2**31),
            "nombre_archivo": metadatos["nombre_archivo"],
            "tipo_archivo": tipo_archivo_codigo,
            "fecha_carga": timestamp_ms,
            "texto": chunk_text,  # Texto del chunk (ya está dentro del límite)
            "embedding": embedding,
            "indice_chunk": i,  # Índice del chunk (0, 1, 2, ...)
            "pagina_inicio": pagina_inicio,  # Página aproximada de inicio
            "pagina_fin": pagina_fin,        # Página aproximada de fin
            "tipo_documento": "documento",
            "fecha_vectorizacion": timestamp_ms,
            "meta": {
                **metadatos,
                "total_chunks": len(chunks),
                "chunk_index": i,
                "chunk_length": len(chunk_text),
                "estimated_pages": f"{pagina_inicio}-{pagina_fin}"
            }
        }
        
        all_data.append(chunk_data)
    
    # Insertar todos los chunks en una sola operación
    if all_data:
        result = client.insert(
            collection_name=COLLECTION_NAME,
            data=all_data
        )
        results.append(result)
        
        print(f"{len(chunks)} chunks insertados en Milvus para: {metadatos['nombre_archivo']}")
    
    return results
