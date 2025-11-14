"""
Retriever wrapper que formatea documentos con metadata visible.

Envuelve cualquier retriever de LangChain y añade formateo de metadata
directamente en el page_content de cada documento para que el LLM la vea.

Características:
    * Agrupa documentos por expediente
    * Añade headers de expediente (separadores visuales)
    * Formatea metadata en Markdown legible
    * Mantiene metadata original para referencias

Metadata formateada:
    * Expediente: Número completo
    * Archivo: Nombre del documento
    * Páginas: Rango de páginas del chunk
    * Tipo: Tipo de documento judicial
    * Ruta: Ruta de descarga

Agrupación:
    * Documentos se agrupan por expediente_numero
    * Cada grupo tiene un header visual
    * Orden alfabético de expedientes

Ejemplo de formateo:

    ================================================================================
    EXPEDIENTE: 24-000123-0001-PE (3 documentos)
    ================================================================================
    
    **Expediente:** 24-000123-0001-PE | **Archivo:** demanda.pdf | **Pág:** 1-3
    **Tipo:** Demanda
    **Ruta:** uploads/24-000123-0001-PE/demanda.pdf
    ---
    [Contenido del documento...]
    ---

Example:
    >>> from app.services.rag.formatted_retriever import FormattedRetriever
    >>> 
    >>> # Envolver retriever existente
    >>> formatted = FormattedRetriever(base_retriever=my_retriever)
    >>> 
    >>> # Usar como retriever normal
    >>> docs = await formatted.ainvoke("consulta")
    >>> # docs tienen metadata formateada en page_content

Note:
    * NO modifica la metadata original (solo page_content)
    * Headers de expediente son Documents separados (is_header=True)
    * Usado por general_chains y expediente_chains
    * El LLM ve la metadata formateada directamente

Ver también:
    * app.services.rag.document_formatter: Funciones de formateo
    * app.services.rag.general_chains: Usa FormattedRetriever
    * app.services.rag.expediente_chains: Usa FormattedRetriever

Authors:
    JusticIA Team

Version:
    1.0.0 - Wrapper para formateo de metadata
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
    Wrapper que formatea documentos con metadata visible.
    
    Toma documentos de cualquier retriever y añade metadata
    formateada en Markdown directamente en el page_content.
    
    Attributes:
        base_retriever: Retriever base a envolver.
    """
    base_retriever: Any = Field(description="The base retriever to wrap")
    
    def __init__(self, base_retriever, **kwargs):
        super().__init__(base_retriever=base_retriever, **kwargs)
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        # Obtener documentos del retriever base
        logger.info(f"Query enviada a Milvus: {query[:200]}")
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
        import asyncio
        return asyncio.run(self._aget_relevant_documents(query))
