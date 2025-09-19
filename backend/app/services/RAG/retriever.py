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
            # Usar la función de búsqueda del vectorstore central
            similar_docs = await search_by_text(
                query_text=query,
                top_k=self.top_k,
                score_threshold=0.0
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