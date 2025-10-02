from typing import List, Optional
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from app.vectorstore.vectorstore import search_by_text, get_expedient_documents
import logging
from pydantic import Field
import re

logger = logging.getLogger(__name__)


class DynamicJusticIARetriever(BaseRetriever):
    """Retriever completamente dinámico que usa el vectorstore de Milvus para JusticIA"""
    
    # Declarar campos como atributos de clase para Pydantic V2
    top_k: int = Field(default=10, description="Número de documentos a recuperar")
    filters: Optional[str] = Field(default=None, description="Filtros adicionales")
    conversation_context: str = Field(default="", description="Contexto de conversación para resolver referencias")
    session_expedients: Optional[List[str]] = Field(default=None, description="Expedientes de la sesión")
    
    def __init__(self, top_k: int = 10, filters: Optional[str] = None, conversation_context: str = "", session_expedients: Optional[List[str]] = None, **kwargs):
        super().__init__(**kwargs)
        # Pydantic V2 requiere que los campos se asignen explícitamente
        object.__setattr__(self, 'top_k', top_k)
        object.__setattr__(self, 'filters', filters)
        object.__setattr__(self, 'conversation_context', conversation_context or "")
        object.__setattr__(self, 'session_expedients', session_expedients or [])
        
        # DEBUG: Verificar inicialización
        logger.info(f"🔧 DYNAMIC RETRIEVER INIT - conversation_context: {len(self.conversation_context)} chars")
        logger.info(f"🔧 DYNAMIC RETRIEVER INIT - session_expedients: {self.session_expedients}")
        if self.conversation_context:
            logger.info(f"🔧 DYNAMIC RETRIEVER INIT - CONTEXTO PREVIO: {self.conversation_context[:200]}...")
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """Obtiene documentos relevantes de Milvus de forma completamente dinámica"""
        logger.info(f"🔍 DYNAMIC RETRIEVER - CONSULTA RECIBIDA: '{query}'")
        logger.info(f"🔍 DYNAMIC RETRIEVER - CONTEXTO DISPONIBLE: {len(self.conversation_context)} chars")
        
        try:
            # PASO 1: Detectar expedientes en la consulta directa
            expediente_pattern = r'\b\d{4}-\d{6}-\d{4}-[A-Z]{2}\b'
            expediente_match = re.search(expediente_pattern, query)
            
            # PASO 2: Detectar consultas contextuales (cualquier tipo)
            referencias_contextuales = [
                r'\b(?:el\s+)?último\s+(?:expediente|caso)\b',
                r'\b(?:el\s+)?primer\s+(?:expediente|caso)\b', 
                r'\b(?:el\s+)?(?:expediente|caso)\s+más\s+reciente\b',
                r'\b(?:ese|este|dicho)\s+(?:expediente|caso)\b',
                r'\b(?:el\s+)?(?:expediente|caso)\s+anterior\b',
                r'\b(?:del\s+)?(?:expediente|caso)\s+mencionado\b',
                
                # Consultas sobre contenido específico
                r'\b(?:la\s+)?bitácora\b',
                r'\bcual\s+es\s+la\s+bitácora\b',
                r'\bbitácora\s+del\s+caso\b',
                r'\bantecedentes\b',
                r'\bpruebas?\b',
                r'\bevidencia\b',
                r'\binforme\s+pericial\b',
                r'\bdeclaraciones?\b',
                r'\bquien\s+es\b',
                r'\bnombre\b',
                r'\bactora?\b',
                r'\bdemandad[ao]\b',
                r'\brepresentante\b',
                r'\bmonto\b',
                r'\bfecha\b',
                r'\bresoluci[oó]n\b'
            ]
            
            tiene_referencia_contextual = any(re.search(patron, query.lower()) for patron in referencias_contextuales)
            
            logger.info(f"🔍 DYNAMIC RETRIEVER - Expediente directo: {bool(expediente_match)}")
            logger.info(f"🔍 DYNAMIC RETRIEVER - Referencia contextual: {tiene_referencia_contextual}")
            logger.info(f"🔍 DYNAMIC RETRIEVER - Contexto disponible: {bool(self.conversation_context)}")
            
            # PASO 3: Si hay referencia contextual, resolver expediente del contexto
            expediente_resuelto = None
            if expediente_match:
                expediente_resuelto = expediente_match.group()
                logger.info(f"✅ DYNAMIC RETRIEVER - EXPEDIENTE DIRECTO: {expediente_resuelto}")
            elif tiene_referencia_contextual and self.conversation_context:
                # Extraer expedientes del contexto
                expedientes_en_contexto = re.findall(expediente_pattern, self.conversation_context)
                if expedientes_en_contexto:
                    expediente_resuelto = expedientes_en_contexto[-1]  # Usar el más reciente
                    logger.info(f"✅ DYNAMIC RETRIEVER - EXPEDIENTE DEL CONTEXTO: {expediente_resuelto}")
                else:
                    logger.warning(f"❌ DYNAMIC RETRIEVER - REFERENCIA CONTEXTUAL SIN EXPEDIENTE IDENTIFICABLE")
            
            # PASO 4: Si se resolvió un expediente, usar modo EXPEDIENTE COMPLETO
            if expediente_resuelto:
                logger.info(f"🚀 DYNAMIC RETRIEVER - ACTIVANDO MODO EXPEDIENTE COMPLETO: {expediente_resuelto}")
                
                try:
                    # Obtener TODOS los documentos del expediente
                    complete_docs = await get_expedient_documents(expediente_resuelto)
                    
                    if complete_docs:
                        logger.info(f"✅ DYNAMIC RETRIEVER - EXPEDIENTE COMPLETO: {len(complete_docs)} documentos")
                        logger.info(f"🚀 DYNAMIC RETRIEVER - MODO DINÁMICO: El LLM puede encontrar cualquier información")
                        
                        # ENFOQUE DINÁMICO: Devolver TODOS los documentos sin filtros
                        max_docs = min(len(complete_docs), 100)  # Límite para performance
                        return complete_docs[:max_docs]
                    else:
                        logger.warning(f"❌ DYNAMIC RETRIEVER - No se encontraron documentos del expediente")
                        
                except Exception as e:
                    logger.error(f"❌ DYNAMIC RETRIEVER - Error obteniendo expediente completo: {e}")
            
            # PASO 5: FALLBACK - Búsqueda semántica general
            logger.info(f"🔍 DYNAMIC RETRIEVER - MODO GENERAL: Búsqueda semántica")
            similar_docs = await search_by_text(
                query_text=query,
                top_k=self.top_k,
                score_threshold=0.3
            )
            
            # Convertir a formato LangChain Document si es necesario
            documents = []
            for doc in similar_docs:
                try:
                    # Si ya es un objeto Document de LangChain
                    if isinstance(doc, Document):
                        documents.append(doc)
                    else:
                        # Si es un diccionario, convertir a Document
                        texto = doc.get("content_preview", "")
                        metadata = {
                            "expediente_numero": doc.get("expedient_id", ""),
                            "archivo": doc.get("document_name", ""),
                            "id_expediente": doc.get("expedient_id", ""),
                            "id_documento": doc.get("id", ""),
                            "similarity_score": doc.get("similarity_score", 0.0)
                        }
                        
                        if texto.strip():
                            documents.append(Document(
                                page_content=texto,
                                metadata=metadata
                            ))
                            
                except Exception as e:
                    logger.warning(f"❌ DYNAMIC RETRIEVER - Error procesando documento: {e}")
                    continue
            
            logger.info(f"🏁 DYNAMIC RETRIEVER - RESULTADO FINAL: {len(documents)} documentos")
            return documents
            
        except Exception as e:
            logger.error(f"❌ DYNAMIC RETRIEVER - Error general: {e}")
            return []
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Método síncrono requerido por BaseRetriever"""
        import asyncio
        return asyncio.run(self._aget_relevant_documents(query))