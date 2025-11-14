"""
Adaptador LangChain para embeddings de JusticIA.

Implementa interfaz Embeddings de LangChain sobre nuestro servicio
de embeddings basado en sentence-transformers.

Características:
    * Compatibilidad: LangChain Embeddings interface
    * Reutilización: Usa get_embeddings() existente
    * Configuración centralizada: EMBEDDING_MODEL
    * Métodos sync + async: embed_query, aembed_query
    * Thread-safe: Maneja event loops correctamente

Beneficios:
    * Integración con LangChain VectorStore
    * Uso en LangChain chains y retrievers
    * Sin duplicar modelo en memoria
    * Configuración única (EMBEDDING_MODEL)

Interface LangChain:
    Métodos síncronos (requeridos):
        * embed_query(text: str) -> List[float]
        * embed_documents(texts: List[str]) -> List[List[float]]
    
    Métodos async (opcionales):
        * aembed_query(text: str) -> List[float]
        * aembed_documents(texts: List[str]) -> List[List[float]]

Event loop handling:
    * Detecta si hay event loop activo
    * Crea nuevo loop en thread separado si necesario
    * Evita "RuntimeError: This event loop is already running"
    * Compatible con FastAPI async + LangChain sync

Example:
    >>> from app.embeddings.langchain_adapter import LangChainEmbeddingsAdapter
    >>> from langchain_milvus import Milvus
    >>> 
    >>> # Crear adaptador
    >>> embeddings = LangChainEmbeddingsAdapter()
    >>> 
    >>> # Usar con LangChain VectorStore
    >>> vectorstore = Milvus(
    ...     embedding_function=embeddings,
    ...     collection_name="expedientes",
    ...     connection_args={"host": "milvus", "port": "19530"}
    ... )
    >>> 
    >>> # Búsqueda por similitud
    >>> docs = vectorstore.similarity_search("consulta legal", k=5)
    >>> 
    >>> # Uso async directo
    >>> vector = await embeddings.aembed_query("¿Qué dice la ley?")

Note:
    * Métodos sync usan ThreadPoolExecutor para async
    * Lazy loading del servicio de embeddings
    * Primera llamada carga modelo (~5-10s)
    * Compartido con resto del sistema (misma instancia)
    * Compatible con LangChain 0.1.x y 0.2.x

Ver también:
    * app.embeddings.embeddings: Servicio base de embeddings
    * app.vectorstore.milvus_storage: Usa este adaptador
    * app.services.rag.retriever: Usa para retrieval

Authors:
    JusticIA Team

Version:
    1.0.0 - Adaptador con manejo robusto de event loops
"""

from typing import List
from langchain_core.embeddings import Embeddings
from app.embeddings.embeddings import get_embeddings


class LangChainEmbeddingsAdapter(Embeddings):
    """
    Adaptador que convierte nuestro EmbeddingsWrapper a la interfaz LangChain.
    
    Implementa interfaz Embeddings de LangChain reutilizando nuestro
    servicio de embeddings basado en sentence-transformers.
    
    Beneficios:
        * Compatibilidad total con el ecosistema LangChain
        * Reutiliza nuestro modelo sentence-transformers existente
        * Mantiene la configuración centralizada
        * Permite usar LangChain VectorStore sin cambios en embeddings
    
    Attributes:
        _embeddings_service: Servicio de embeddings (lazy loaded).
    """
    
    def __init__(self):
        self._embeddings_service = None
    
    async def _get_embeddings_service(self):
        """Obtiene el servicio de embeddings de forma lazy."""
        if self._embeddings_service is None:
            self._embeddings_service = await get_embeddings()
        return self._embeddings_service
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of documents.
        
        NOTA: LangChain requiere métodos síncronos para embed_documents
        """
        import asyncio
        try:
            # Intentar obtener el loop actual
            loop = asyncio.get_running_loop()
            # Usar asyncio.create_task() para ejecutar en el loop actual
            import concurrent.futures
            import threading
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(self.aembed_documents(texts))
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
                
        except RuntimeError:
            # No hay event loop, usar asyncio.run()
            return asyncio.run(self.aembed_documents(texts))

    def embed_query(self, text: str) -> List[float]:
        """
        Embeds a single query text.
        
        NOTA: LangChain requiere métodos síncronos para embed_query
        """
        import asyncio
        try:
            # Intentar obtener el loop actual
            loop = asyncio.get_running_loop()
            # Usar asyncio.create_task() para ejecutar en el loop actual
            import concurrent.futures
            import threading
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(self.aembed_query(text))
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
                
        except RuntimeError:
            # No hay event loop, usar asyncio.run()
            return asyncio.run(self.aembed_query(text))
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Versión async para embeds de documentos."""
        embeddings_service = await self._get_embeddings_service()
        return await embeddings_service.aembed_documents(texts)
    
    async def aembed_query(self, text: str) -> List[float]:
        """Versión async para embed de consulta."""
        embeddings_service = await self._get_embeddings_service()
        return await embeddings_service.aembed_query(text)