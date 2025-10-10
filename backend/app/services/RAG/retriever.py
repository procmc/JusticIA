from typing import List, Optional
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from app.vectorstore.vectorstore import search_by_text, get_expedient_documents
import logging
from pydantic import Field

# IMPORTANTE: Usar constantes de metadata para evitar typos
from app.constants.metadata_fields import MetadataFields as MF

# Nuevas importaciones para mejoras RAG
from app.config.rag_config import rag_config
from app.services.RAG.search_strategies import search_manager

# Importar limpieza de encoding para post-procesamiento
from app.services.ingesta.file_management.text_cleaner import fix_encoding_issues

logger = logging.getLogger(__name__)


class DynamicJusticIARetriever(BaseRetriever):
    # Campos Pydantic V2
    top_k: int = Field(default=rag_config.TOP_K_GENERAL, description="Número de documentos a recuperar")
    similarity_threshold: float = Field(default=rag_config.SIMILARITY_THRESHOLD_GENERAL, description="Umbral de similitud mínimo")
    expediente_filter: Optional[str] = Field(default=None, description="Filtro por expediente específico")
    
    def __init__(
        self, 
        top_k: int = None,  # None = usar valor del config
        similarity_threshold: float = None,  # None = usar valor del config
        expediente_filter: Optional[str] = None,
        **kwargs
    ):
        # Usar valores del config si no se especifican
        if top_k is None:
            top_k = rag_config.TOP_K_GENERAL
        if similarity_threshold is None:
            similarity_threshold = rag_config.SIMILARITY_THRESHOLD_GENERAL
        
        super().__init__(**kwargs)
        object.__setattr__(self, 'top_k', top_k)
        object.__setattr__(self, 'similarity_threshold', similarity_threshold)
        object.__setattr__(self, 'expediente_filter', expediente_filter)
        
        logger.info(
            f"DynamicJusticIARetriever inicializado - "
            f"top_k={top_k}, threshold={similarity_threshold}, "
            f"expediente={expediente_filter or 'None'}"
        )
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        try:
            # FLUJO 1: Expediente específico (filtro explícito)
            if self.expediente_filter:
                logger.info(f"Búsqueda en expediente: {self.expediente_filter}")
                docs = await self._get_expediente_documents(self.expediente_filter)
                logger.debug(f"Expediente: {len(docs)} documentos recuperados")
                return docs
            
            # FLUJO 2: Búsqueda general semántica
            logger.info(f"Búsqueda general: query='{query[:100]}...', top_k={self.top_k}")
            docs = await self._get_general_documents(query)
            logger.debug(f"General: {len(docs)} documentos recuperados")
            
            if len(docs) == 0:
                logger.warning(f"No se encontraron documentos para: '{query[:100]}'")
            
            return docs
            
        except Exception as e:
            logger.error(f"Error en retriever: {e}", exc_info=True)
            return []
    
    async def _get_expediente_documents(self, expediente_numero: str) -> List[Document]:
        """Obtiene todos los documentos de un expediente específico con limpieza de encoding."""
        try:
            logger.info(f"Obteniendo documentos del expediente: {expediente_numero}")
            
            # Obtener documentos completos del expediente
            docs = await get_expedient_documents(expediente_numero)
            
            if not docs:
                logger.warning(f"Expediente {expediente_numero}: sin documentos")
                return []
            
            # Aplicar limpieza de encoding a todos los documentos
            for doc in docs:
                if hasattr(doc, 'page_content'):
                    doc.page_content = fix_encoding_issues(doc.page_content)
            
            # Limitar al top_k configurado
            result = docs[:self.top_k]
            logger.info(f"Expediente {expediente_numero}: {len(result)} documentos recuperados (con limpieza de encoding)")
            return result
            
        except Exception as e:
            logger.error(f"Error obteniendo expediente {expediente_numero}: {e}", exc_info=True)
            return []
    
    async def _get_general_documents(self, query: str) -> List[Document]:
        """Búsqueda semántica general con fallback automático."""
        try:
            # Búsqueda con fallback
            logger.info(f"Búsqueda general con fallback habilitado")
            results = await search_manager.search_with_fallback(
                query_text=query,
                top_k=self.top_k,
                threshold=self.similarity_threshold
            )
            
            if not results:
                logger.warning(f"No se encontraron resultados para: '{query[:100]}'")
                return []
            
            # Convertir a LangChain Documents con metadata enriquecida y limpieza de encoding
            documents = []
            for doc in results:
                if isinstance(doc, Document):
                    # Limpiar encoding del contenido existente
                    doc.page_content = fix_encoding_issues(doc.page_content)
                    documents.append(doc)
                else:
                    content = doc.get("content_preview", "")
                    if content.strip():
                        # Limpiar encoding antes de crear el documento
                        content_limpio = fix_encoding_issues(content)
                        
                        # Extraer metadata completa de Milvus
                        milvus_metadata = doc.get("metadata", {})
                        
                        # Construir metadata enriquecida para el LLM
                        enriched_metadata = {
                            # Identificación del expediente
                            MF.EXPEDIENTE_NUMERO: doc.get("expedient_id", ""),
                            MF.DOCUMENTO_NOMBRE: doc.get("document_name", ""),
                            MF.DOCUMENTO_ID: doc.get("id", ""),
                            
                            # Información del chunk
                            "indice_chunk": milvus_metadata.get("indice_chunk", 0),
                            "id_chunk": milvus_metadata.get("id_chunk", ""),
                            
                            # Información de páginas (si existe)
                            "pagina_inicio": milvus_metadata.get("pagina_inicio"),
                            "pagina_fin": milvus_metadata.get("pagina_fin"),
                            
                            # Tipo de documento (sentencia, resolución, etc.)
                            "tipo_documento": milvus_metadata.get("tipo_documento", ""),
                            
                            # Score de similitud
                            MF.SIMILARITY_SCORE: doc.get("similarity_score", 0.0)
                        }
                        
                        documents.append(Document(
                            page_content=content_limpio,
                            metadata=enriched_metadata
                        ))
            
            logger.info(f"Búsqueda completada: {len(documents)} documentos (con limpieza de encoding)")
            return documents
            
        except Exception as e:
            logger.error(f"Error en búsqueda general: {e}", exc_info=True)
            return []
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Método síncrono requerido por BaseRetriever."""
        import asyncio
        return asyncio.run(self._aget_relevant_documents(query))