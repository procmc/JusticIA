from typing import List, Optional
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from app.vectorstore.vectorstore import search_by_text
import logging
from pydantic import Field

logger = logging.getLogger(__name__)


class JusticIARetriever(BaseRetriever):
    """Retriever personalizado que usa el vectorstore de Milvus para JusticIA"""
    
    # Declarar campos como atributos de clase para Pydantic V2
    top_k: int = Field(default=10, description="Número de documentos a recuperar")
    filters: Optional[str] = Field(default=None, description="Filtros adicionales")
    
    def __init__(self, top_k: int = 10, filters: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.top_k = top_k
        self.filters = filters
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """Obtiene documentos relevantes de Milvus"""
        try:
            # Detectar si la query incluye un número de expediente específico
            import re
            expediente_pattern = r'\b\d{4}-\d{6}-\d{4}-[A-Z]{2}\b'
            expediente_match = re.search(expediente_pattern, query)
            
            # Ajustar parámetros de búsqueda según el tipo de consulta
            if expediente_match:
                # Para consultas de expedientes específicos, ser más permisivo
                # pero aumentar top_k para obtener más información
                score_threshold = 0.1
                effective_top_k = max(self.top_k, 20)  # Al menos 20 documentos
                logger.info(f"Búsqueda específica para expediente: {expediente_match.group()}")
            else:
                # Para consultas generales, mantener threshold más alto
                score_threshold = 0.3
                effective_top_k = self.top_k
            
            # Usar la función de búsqueda del vectorstore central
            if expediente_match:
                # Para expedientes específicos, usar filtro directo
                similar_docs = await search_by_text(
                    query_text=query,
                    top_k=effective_top_k,
                    score_threshold=score_threshold,
                    expediente_filter=expediente_match.group()
                )
            else:
                # Para consultas generales, búsqueda semántica normal
                similar_docs = await search_by_text(
                    query_text=query,
                    top_k=effective_top_k,
                    score_threshold=score_threshold
                )
            
            # Convertir a formato LangChain Document
            documents = []
            for doc in similar_docs:
                try:
                    # Usar el formato del vectorstore central
                    texto = doc.get("content_preview", "")
                    metadata = {
                        "expediente_numero": doc.get("expedient_id", ""),
                        "archivo": doc.get("document_name", ""),
                        "id_expediente": doc.get("expedient_id", ""),
                        "id_documento": doc.get("id", ""),
                        "similarity_score": doc.get("similarity_score", 0.0),
                        "relevance_score": doc.get("similarity_score", 0.0),
                        "distance": 1.0 - doc.get("similarity_score", 0.0)
                    }
                    
                    if texto.strip():
                        documents.append(Document(
                            page_content=texto,
                            metadata=metadata
                        ))
                        
                except Exception as e:
                    logger.warning(f"Error procesando documento: {e}")
                    continue
            
            logger.info(f"Retriever encontró {len(documents)} documentos para: {query}")
            return documents
            
        except Exception as e:
            logger.error(f"Error en retriever: {e}")
            return []
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Método síncrono requerido por BaseRetriever"""
        import asyncio
        return asyncio.run(self._aget_relevant_documents(query))