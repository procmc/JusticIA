"""
Retriever wrapper que formatea documentos con metadata para el LLM.

Este retriever envuelve otro retriever base y formatea los documentos
recuperados agregando metadata visible (expediente, archivo, chunk, páginas)
y agrupándolos por expediente.
"""
from typing import List, Any
from collections import defaultdict
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from pydantic import Field
import logging

from .document_formatter import format_document_with_metadata, create_expediente_header

logger = logging.getLogger(__name__)


class FormattedRetriever(BaseRetriever):
    """
    Retriever que formatea documentos con metadata visible y los agrupa por expediente.
    
    Este retriever envuelve un retriever base y post-procesa los documentos recuperados
    para hacerlos más legibles para el LLM, agregando:
    - Headers de expediente para agrupar documentos
    - Metadata visible en cada documento (expediente, archivo, chunk, páginas)
    - Formato estructurado con separadores visuales
    
    Attributes:
        base_retriever: El retriever base que se envuelve
    """
    
    base_retriever: Any = Field(description="The base retriever to wrap")
    
    def __init__(self, base_retriever, **kwargs):
        """
        Inicializa el FormattedRetriever.
        
        Args:
            base_retriever: Retriever base a envolver (debe tener método ainvoke)
            **kwargs: Argumentos adicionales para BaseRetriever
        """
        super().__init__(base_retriever=base_retriever, **kwargs)
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """
        Recupera documentos relevantes y los formatea con metadata.
        
        Proceso:
        1. Invoca el retriever base para obtener documentos
        2. Agrupa documentos por expediente
        3. Para cada expediente:
           - Agrega un header de expediente
           - Formatea cada documento con su metadata
        4. Retorna lista ordenada de documentos formateados
        
        Args:
            query: Consulta de búsqueda
            
        Returns:
            List[Document]: Documentos formateados y agrupados por expediente
        """
        # Obtener documentos del retriever base
        docs = await self.base_retriever.ainvoke(query)
        
        if not docs:
            logger.warning(f"No se recuperaron documentos para query: '{query[:100]}'")
            return []
        
        logger.info(f"Formateando {len(docs)} documentos recuperados")
        
        # Agrupar por expediente
        docs_by_exp = defaultdict(list)
        for doc in docs:
            exp_num = doc.metadata.get('expediente_numero', 'N/A')
            docs_by_exp[exp_num].append(doc)
        
        # Formatear cada documento con metadata en su page_content
        formatted_docs = []
        for exp_num in sorted(docs_by_exp.keys()):
            exp_docs = docs_by_exp[exp_num]
            
            # Agregar header de expediente
            header_content = create_expediente_header(exp_num, len(exp_docs))
            header_doc = Document(
                page_content=header_content,
                metadata={"expediente_numero": exp_num, "is_header": True}
            )
            formatted_docs.append(header_doc)
            
            # Agregar documentos formateados
            for doc in exp_docs:
                formatted_doc = Document(
                    page_content=format_document_with_metadata(doc),
                    metadata=doc.metadata
                )
                formatted_docs.append(formatted_doc)
        
        logger.info(
            f"Documentos formateados: {len(formatted_docs)} total "
            f"({len(docs_by_exp)} expedientes)"
        )
        
        return formatted_docs
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """
        Versión síncrona de _aget_relevant_documents.
        
        Args:
            query: Consulta de búsqueda
            
        Returns:
            List[Document]: Documentos formateados
        """
        import asyncio
        return asyncio.run(self._aget_relevant_documents(query))
