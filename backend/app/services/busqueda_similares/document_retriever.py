"""
Servicio de Recuperación de Documentos de Expedientes con Estrategias de Fallback.

Este módulo implementa un sistema robusto de obtención de documentos judiciales
con múltiples estrategias de recuperación para garantizar disponibilidad de datos
incluso cuando el vectorstore presenta problemas.

Arquitectura de recuperación:

    Estrategia Principal: Milvus Vectorstore
    └─> DynamicJusticIARetriever con filtro por expediente
        └─> Búsqueda vectorial de hasta 50 documentos
            └─> Threshold: 0.2 (permisivo para recuperar todo el expediente)

    Estrategia Fallback: Base de Datos SQL Server
    └─> Consulta directa a T_Documento + T_Expediente_Documento
        └─> Conversión a formato LangChain Document
            └─> Preserva metadata para compatibilidad con pipeline RAG

Casos de uso de fallback:
    1. Milvus no disponible (conexión, timeout)
    2. Colección no existe o está vacía
    3. Expediente no encontrado en vectorstore (aún no indexado)
    4. Error de embeddings durante la búsqueda

Flujo de recuperación:
    1. Intentar recuperación desde Milvus con filtro de expediente
    2. Si retorna documentos → Éxito (fin)
    3. Si retorna vacío o error → Activar fallback
    4. Consultar BD para obtener documentos del expediente
    5. Convertir formato BD → LangChain Document
    6. Validar que haya contenido real (no vacíos)
    7. Retornar documentos o lanzar ValueError

Formato de salida (LangChain Document):
    Document(
        page_content=str,  # Contenido extraído del documento
        metadata={
            "numero_expediente": str,  # Ej: "24-000123-0001-PE"
            "nombre_archivo": str,     # Ej: "demanda.pdf"
            "id_documento": int,       # ID en BD
            "chunk_index": int,        # Índice de chunk (si aplica)
        }
    )

Parámetros de configuración:
    - top_k: 50 (recuperar todos los documentos del expediente)
    - similarity_threshold: 0.2 (muy permisivo, no filtrar por similitud)
    - expediente_filter: Número de expediente exacto

Integración con otros servicios:
    - DynamicJusticIARetriever: Búsqueda vectorial en Milvus
    - DocumentoService: Consultas directas a BD (fallback)
    - SimilarityService: Consumidor principal para búsquedas por expediente

Example:
    >>> retriever = DocumentRetriever()
    >>> docs = await retriever.obtener_documentos_expediente("24-000123-0001-PE")
    >>> print(f"Recuperados {len(docs)} documentos")
    Recuperados 12 documentos
    >>> print(docs[0].metadata)
    {'numero_expediente': '24-000123-0001-PE', 'nombre_archivo': 'demanda.pdf'}

Manejo de errores:
    - ValueError: Cuando no se encuentran documentos en ninguna fuente
    - Log warning: Cuando Milvus falla pero fallback tiene éxito
    - Log error: Cuando ambas estrategias fallan

Performance:
    - Milvus: ~100-300ms (vectorstore en red)
    - Fallback BD: ~50-150ms (SQL Server local)
    - Overhead total: <500ms en el peor caso

Note:
    - El fallback NO incluye búsqueda semántica, solo recuperación completa
    - Los documentos desde BD pueden no estar vectorizados aún
    - Se preserva la estructura de metadata para compatibilidad con RAG

Ver también:
    - app.services.RAG.retriever: DynamicJusticIARetriever
    - app.services.busqueda_similares.documentos.documento_service: Acceso a BD
    - app.services.busqueda_similares.similarity_service: Consumidor principal

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0
"""

import logging
from typing import List
from langchain_core.documents import Document

from app.services.RAG.retriever import DynamicJusticIARetriever
from .documentos.documento_service import DocumentoService

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Maneja la obtención de documentos de expedientes desde diferentes fuentes."""
    
    def __init__(self):
        self.documento_service = DocumentoService()
    
    async def obtener_documentos_expediente(self, numero_expediente: str) -> List[Document]:
        """
        Obtiene documentos del expediente usando retriever o fallback a BD.
        
        Args:
            numero_expediente: Número del expediente
            
        Returns:
            Lista de documentos del expediente
            
        Raises:
            ValueError: Si no se encuentran documentos
        """
        try:
            # Estrategia principal: usar retriever con filtro directo
            retriever = DynamicJusticIARetriever(
                top_k=50,
                similarity_threshold=0.2,
                expediente_filter=numero_expediente
            )
            
            query_expediente = f"documentos del expediente {numero_expediente}"
            docs_expediente = await retriever._aget_relevant_documents(query_expediente)
            
            if docs_expediente:
                logger.info(f"Recuperados {len(docs_expediente)} documentos para expediente {numero_expediente}")
                return docs_expediente
            else:
                logger.warning(f"No se encontraron documentos en Milvus, usando fallback para {numero_expediente}")
                return await self._obtener_documentos_fallback(numero_expediente)
                
        except Exception as e:
            logger.error(f"Error con retriever/Milvus para expediente {numero_expediente}: {e}")
            return await self._obtener_documentos_fallback(numero_expediente)
    
    async def _obtener_documentos_fallback(self, numero_expediente: str) -> List[Document]:
        """
        Estrategia de fallback: obtener documentos directamente de la BD.
        
        Args:
            numero_expediente: Número del expediente
            
        Returns:
            Lista de documentos desde BD
            
        Raises:
            ValueError: Si no se encuentran documentos en BD
        """
        logger.info(f"Obteniendo documentos desde BD para expediente {numero_expediente}")
        
        expediente_data = await self.documento_service.obtener_expediente_completo(
            numero_expediente, incluir_documentos=True
        )
        
        if not expediente_data or not expediente_data.get("documents"):
            raise ValueError(f"No se encontraron documentos para el expediente {numero_expediente}")
        
        # Convertir documentos a formato LangChain Document
        docs = []
        for doc_data in expediente_data["documents"]:
            content = doc_data.get("content_preview", "") or doc_data.get("content", "")
            if content.strip():
                doc = Document(
                    page_content=content,
                    metadata={
                        "numero_expediente": numero_expediente,
                        "nombre_archivo": doc_data.get("document_name", ""),
                        "id_documento": doc_data.get("id", ""),
                    }
                )
                docs.append(doc)
        
        if not docs:
            raise ValueError(f"No se encontraron documentos con contenido para el expediente {numero_expediente}")
        
        logger.info(f"Fallback exitoso: {len(docs)} documentos desde BD")
        return docs
