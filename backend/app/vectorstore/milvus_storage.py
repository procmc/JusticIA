"""
Almacenamiento vectorial usando LangChain como orquestador.

MIGRADO A LANGCHAIN: Este módulo ahora usa add_documents() para aprovechar
la automación completa de embeddings e inserción de LangChain.
"""

import uuid
import time
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.config.file_config import FILE_TYPE_CODES
from app.vectorstore.vectorstore import add_documents
from pathlib import Path

async def store_in_vectorstore(
    texto: str, 
    metadatos: dict, 
    CT_Num_expediente: str,
    id_expediente: int,  # ID real de la BD
    id_documento: int    # ID real de la BD
):
    """
    Almacena el texto en Milvus usando LangChain para automación completa.
    
    BENEFICIOS LANGCHAIN:
    - Embeddings automáticos (sin código manual)
    - Inserción optimizada
    - Gestión de errores integrada
    
    Args:
        texto: Texto completo del documento
        metadatos: Metadatos del documento  
        CT_Num_expediente: Número de expediente
        id_expediente: ID real del expediente en la BD transaccional
        id_documento: ID real del documento en la BD transaccional
        
    Returns:
        List: IDs de los documentos almacenados
    """
    # Configurar text splitter con chunks que respeten el límite de Milvus (8192 chars)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=7000,      # Seguro bajo límite de 8192 con margen para metadata
        chunk_overlap=500,    # Mayor overlap para mantener continuidad
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]  # Separadores en orden de preferencia
    )
    
    # Dividir el texto en chunks
    chunks = text_splitter.split_text(texto)
    print(f"Documento dividido en {len(chunks)} chunks para LangChain")
    
    # Preparar metadatos comunes
    timestamp_ms = int(time.time() * 1000)
    extension = Path(metadatos["nombre_archivo"]).suffix.lower()
    tipo_archivo_codigo = FILE_TYPE_CODES.get(extension, 1)
    
    # Estimar páginas aproximadas
    caracteres_por_pagina = 2500  # Aproximadamente 500 palabras x 5 chars/palabra
    
    # Crear documentos LangChain para cada chunk
    langchain_documents = []
    
    for i, chunk_text in enumerate(chunks):
        # Calcular páginas aproximadas para este chunk
        inicio_char = i * (7000 - 500)  # chunk_size menos overlap
        fin_char = inicio_char + len(chunk_text)
        
        pagina_inicio = max(1, (inicio_char // caracteres_por_pagina) + 1)
        pagina_fin = max(pagina_inicio, (fin_char // caracteres_por_pagina) + 1)
        
        # Metadatos específicos del chunk para LangChain
        chunk_metadata = {
            # IDs únicos
            "id_chunk": str(uuid.uuid4()),
            
            # Referencias a BD transaccional
            "id_expediente": id_expediente,
            "numero_expediente": CT_Num_expediente,
            "fecha_expediente_creacion": timestamp_ms,
            "id_documento": id_documento,
            "nombre_archivo": metadatos["nombre_archivo"],
            "tipo_archivo": tipo_archivo_codigo,
            "fecha_carga": timestamp_ms,
            
            # Info del chunk
            "indice_chunk": i,
            "pagina_inicio": pagina_inicio,
            "pagina_fin": pagina_fin,
            "tipo_documento": "documento",
            "fecha_vectorizacion": timestamp_ms,
            
            # Metadatos flexibles
            "meta": {
                **metadatos,
                "total_chunks": len(chunks),
                "chunk_index": i,
                "chunk_length": len(chunk_text),
                "estimated_pages": f"{pagina_inicio}-{pagina_fin}"
            }
        }
        
        # Crear documento LangChain
        document = Document(
            page_content=chunk_text,
            metadata=chunk_metadata
        )
        langchain_documents.append(document)
    
    # USAR LANGCHAIN: add_documents maneja embeddings automáticamente
    if langchain_documents:
        doc_ids = await add_documents(langchain_documents)
        print(f"LangChain: {len(doc_ids)} chunks almacenados para {metadatos['nombre_archivo']}")
        return doc_ids
    
    return []
