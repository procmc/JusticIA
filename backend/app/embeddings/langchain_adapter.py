"""
Adaptador LangChain para nuestro servicio de embeddings.

Este adaptador hace compatible nuestro EmbeddingsWrapper con 
la interfaz estándar de LangChain Embeddings.
"""

from typing import List
from langchain_core.embeddings import Embeddings
from app.embeddings.embeddings import get_embeddings


class LangChainEmbeddingsAdapter(Embeddings):
    """
    Adaptador que convierte nuestro EmbeddingsWrapper a la interfaz LangChain.
    
    BENEFICIOS:
    - Compatibilidad total con el ecosistema LangChain
    - Reutiliza nuestro modelo sentence-transformers existente
    - Mantiene la configuración centralizada
    - Permite usar LangChain VectorStore sin cambios en embeddings
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