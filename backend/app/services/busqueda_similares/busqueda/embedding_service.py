"""
Servicio de generación de embeddings.

Este módulo maneja la generación de vectores de embedding para textos
utilizando el servicio de embeddings configurado.
"""

import logging
from typing import List, Optional
from app.embeddings.embeddings import get_embeddings

logger = logging.getLogger(__name__)


class EmbeddingGeneratorService:
    """Servicio para generar embeddings de textos."""
    
    def __init__(self):
        self.embeddings_service = None
    
    async def _get_embeddings_service(self):
        """Obtiene el servicio de embeddings de forma lazy."""
        if self.embeddings_service is None:
            self.embeddings_service = await get_embeddings()
        return self.embeddings_service
    
    async def generate_text_embedding(self, text: str) -> List[float]:
        """
        Genera un embedding para un texto dado.
        
        Args:
            text: Texto para generar el embedding
            
        Returns:
            Vector de embedding como lista de floats
        """
        try:
            if not text or not text.strip():
                raise ValueError("El texto no puede estar vacío")
            
            embeddings_service = await self._get_embeddings_service()
            embedding = await embeddings_service.aembed_query(text.strip())
            
            if not embedding or len(embedding) == 0:
                raise ValueError("No se pudo generar el embedding")
            
            logger.debug(f"Embedding generado con dimensión: {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Error generando embedding: {e}")
            raise
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para múltiples textos.
        
        Args:
            texts: Lista de textos para generar embeddings
            
        Returns:
            Lista de vectores de embedding
        """
        try:
            if not texts:
                return []
            
            # Filtrar textos vacíos
            valid_texts = [text.strip() for text in texts if text and text.strip()]
            
            if not valid_texts:
                logger.warning("No hay textos válidos para procesar")
                return []
            
            embeddings_service = await self._get_embeddings_service()
            embeddings = await embeddings_service.aembed_documents(valid_texts)
            
            logger.info(f"Generados {len(embeddings)} embeddings en batch")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generando embeddings en batch: {e}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """
        Obtiene la dimensión de los embeddings generados.
        
        Returns:
            Dimensión del vector de embedding
        """
        # Para sentence-transformers, la dimensión típica es 384 o 768
        # Esto debería obtenerse del modelo real, pero por ahora usamos un valor típico
        return 384
