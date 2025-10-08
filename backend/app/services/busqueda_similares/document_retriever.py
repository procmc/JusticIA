"""
Módulo para obtención de documentos de expedientes.
Maneja la lógica de retrieval desde Milvus y fallback a BD.
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
