from typing import List, Optional
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from app.vectorstore.vectorstore import search_by_text, get_expedient_documents
import logging
from pydantic import Field

logger = logging.getLogger(__name__)


class DynamicJusticIARetriever(BaseRetriever):
    """
    Retriever optimizado para JusticIA con LangChain.
    
    RESPONSABILIDADES:
    - Búsqueda vectorial en Milvus
    - Filtrado por expediente específico (si se proporciona)
    - Control de threshold y top-k
    
    NO maneja (lo hace LangChain):
    - Reformulación de queries (create_history_aware_retriever)
    - Contexto conversacional (RunnableWithMessageHistory)
    - Referencias contextuales ("último caso", etc.) - LangChain las reformula
    """
    
    # Campos Pydantic V2
    top_k: int = Field(default=10, description="Número de documentos a recuperar")
    similarity_threshold: float = Field(default=0.3, description="Umbral de similitud mínimo")
    expediente_filter: Optional[str] = Field(default=None, description="Filtro por expediente específico")
    
    def __init__(
        self, 
        top_k: int = 10,
        similarity_threshold: float = 0.3,
        expediente_filter: Optional[str] = None,
        **kwargs
    ):
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
        """
        Recupera documentos relevantes de Milvus.
        
        NOTA: La query ya viene reformulada por create_history_aware_retriever
        si se usa con gestión de historial. No necesitamos detectar referencias
        contextuales manualmente.
        """
        print(f"\n{'='*80}")
        print(f"🔍 RETRIEVER - Query recibida: '{query}'")
        print(f"   - Expediente filter: {self.expediente_filter or 'None'}")
        print(f"   - Top-K: {self.top_k}")
        print(f"   - Threshold: {self.similarity_threshold}")
        print(f"{'='*80}\n")
        
        try:
            # FLUJO 1: Expediente específico (filtro explícito)
            if self.expediente_filter:
                logger.info(f"Búsqueda en expediente: {self.expediente_filter}")
                docs = await self._get_expediente_documents(self.expediente_filter)
                print(f"✅ Retriever - Expediente: {len(docs)} documentos recuperados")
                return docs
            
            # FLUJO 2: Búsqueda general semántica
            logger.info(f"Búsqueda general: query='{query[:80]}...', top_k={self.top_k}")
            docs = await self._get_general_documents(query)
            print(f"✅ Retriever - General: {len(docs)} documentos recuperados")
            
            if len(docs) == 0:
                print(f"⚠️  ADVERTENCIA: Retriever no encontró documentos para: '{query}'")
            
            return docs
            
        except Exception as e:
            print(f"❌ ERROR en retriever: {e}")
            logger.error(f"Error en retriever: {e}", exc_info=True)
            return []
    
    async def _get_expediente_documents(self, expediente_numero: str) -> List[Document]:
        """Obtiene todos los documentos de un expediente específico."""
        try:
            # Obtener documentos completos del expediente
            docs = await get_expedient_documents(expediente_numero)
            
            if docs:
                # Limitar al top_k configurado
                result = docs[:self.top_k]
                logger.info(f"Expediente {expediente_numero}: {len(result)} documentos recuperados")
                return result
            
            logger.warning(f"Expediente {expediente_numero}: sin documentos")
            return []
            
        except Exception as e:
            logger.error(f"Error obteniendo expediente {expediente_numero}: {e}")
            return []
    
    async def _get_general_documents(self, query: str) -> List[Document]:
        """Búsqueda semántica general en toda la base de datos."""
        try:
            # Búsqueda vectorial
            results = await search_by_text(
                query_text=query,
                top_k=self.top_k,
                score_threshold=self.similarity_threshold
            )
            
            # Convertir a LangChain Documents
            documents = []
            for i, doc in enumerate(results):
                if isinstance(doc, Document):
                    documents.append(doc)
                else:
                    # Convertir dict a Document
                    # Nota: content_preview ahora contiene el contenido COMPLETO (sin truncar)
                    content = doc.get("content_preview", "")
                    if content.strip():
                        documents.append(Document(
                            page_content=content,
                            metadata={
                                "expediente_numero": doc.get("expedient_id", ""),
                                "archivo": doc.get("document_name", ""),
                                "id_documento": doc.get("id", ""),
                                "similarity_score": doc.get("similarity_score", 0.0)
                            }
                        ))
                        # Debug primeros documentos
                        if i < 2:
                            print(f"   📄 Doc {i+1}: {len(content)} chars, expediente: {doc.get('expedient_id', 'N/A')}, similarity: {doc.get('similarity_score', 0.0):.3f}")
            
            print(f"   ✅ {len(documents)} documentos convertidos a LangChain format")
            logger.info(f"Búsqueda general: {len(documents)} documentos recuperados")
            return documents
            
        except Exception as e:
            logger.error(f"Error en búsqueda general: {e}")
            return []
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Método síncrono requerido por BaseRetriever."""
        import asyncio
        return asyncio.run(self._aget_relevant_documents(query))



# Alias para compatibilidad
JusticIARetriever = DynamicJusticIARetriever