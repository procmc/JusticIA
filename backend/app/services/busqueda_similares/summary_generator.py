"""
Módulo para generación de resúmenes con LLM.
Maneja la invocación del modelo, reintentos y validación de respuestas.
"""

import logging
import asyncio
from typing import List
from langchain_core.documents import Document

from app.llm.llm_service import get_llm
from .similarity_prompt_builder import (
    create_similarity_summary_prompt,
    create_similarity_search_context
)

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """Genera resúmenes de expedientes usando LLM con sistema de reintentos."""
    
    # Configuración de reintentos
    MAX_INTENTOS = 3
    TIEMPO_ESPERA_BASE = 2  # segundos
    MIN_LONGITUD_RESPUESTA = 200
    
    async def crear_contexto_resumen(self, docs_expediente: List[Document]) -> str:
        """
        Crea el contexto optimizado para documentos legales.
        
        Args:
            docs_expediente: Lista de documentos del expediente
            
        Returns:
            Contexto formateado como string
            
        Raises:
            ValueError: Si no hay documentos o el contexto es muy corto
        """
        if not docs_expediente:
            raise ValueError("No se encontraron documentos para el expediente")
        
        try:
            contexto_completo = create_similarity_search_context(
                docs_expediente, 
                max_docs=20,
                max_chars_per_doc=7000
            )
            
            if len(contexto_completo) < 100:
                raise ValueError(f"Contexto demasiado corto: {len(contexto_completo)} caracteres")
            
            logger.info(f"Contexto creado: {len(contexto_completo)} caracteres")
            return contexto_completo
            
        except Exception as e:
            logger.error(f"Error creando contexto: {e}", exc_info=True)
            raise ValueError(f"Error procesando documentos: {e}")
    
    async def generar_respuesta_llm(self, contexto_completo: str, numero_expediente: str) -> str:
        """
        Genera respuesta usando el LLM con sistema de reintentos.
        
        Args:
            contexto_completo: Contexto formateado de los documentos
            numero_expediente: Número del expediente
            
        Returns:
            Respuesta del LLM como string
            
        Raises:
            ValueError: Si todos los intentos fallan
        """
        for intento in range(1, self.MAX_INTENTOS + 1):
            try:
                logger.info(f"Intento {intento}/{self.MAX_INTENTOS} de generación")
                
                # Crear prompt y obtener LLM
                prompt = create_similarity_summary_prompt(contexto_completo, numero_expediente)
                llm = await get_llm()
                
                # Invocar LLM
                respuesta_llm = await llm.ainvoke(prompt)
                respuesta_content = getattr(respuesta_llm, "content", str(respuesta_llm))
                
                # Validar respuesta
                if not respuesta_content:
                    logger.error(f"Respuesta vacía del LLM en intento {intento}")
                    if intento < self.MAX_INTENTOS:
                        await self._esperar_antes_reintentar(intento)
                        continue
                    raise ValueError("LLM devolvió respuesta vacía después de todos los intentos")
                
                # Validar longitud mínima
                if not self._validar_longitud(respuesta_content, intento):
                    if intento < self.MAX_INTENTOS:
                        await self._esperar_antes_reintentar(intento)
                        continue
                
                # Validar estructura JSON
                if not self._validar_json_basico(respuesta_content, intento):
                    if intento < self.MAX_INTENTOS:
                        await self._esperar_antes_reintentar(intento)
                        continue
                
                # Validar campos requeridos
                if not self._validar_campos_requeridos(respuesta_content, intento):
                    if intento < self.MAX_INTENTOS:
                        await self._esperar_antes_reintentar(intento)
                        continue
                
                # Todas las validaciones pasaron
                logger.info(f"Respuesta válida generada en intento {intento}")
                return respuesta_content
                
            except Exception as e:
                logger.error(f"Error en intento {intento}/{self.MAX_INTENTOS}: {e}")
                if intento < self.MAX_INTENTOS:
                    await self._esperar_antes_reintentar(intento)
                else:
                    raise ValueError(f"Error del LLM después de {self.MAX_INTENTOS} intentos: {e}")
        
        raise ValueError(f"No se pudo generar un resumen válido después de {self.MAX_INTENTOS} intentos")
    
    def _validar_longitud(self, respuesta: str, intento: int) -> bool:
        """Valida que la respuesta tenga longitud mínima."""
        if len(respuesta) < self.MIN_LONGITUD_RESPUESTA:
            logger.warning(f"Respuesta muy corta ({len(respuesta)} chars) en intento {intento}")
            return intento >= self.MAX_INTENTOS  # Aceptar en último intento
        return True
    
    def _validar_json_basico(self, respuesta: str, intento: int) -> bool:
        """Valida que la respuesta contenga estructura JSON básica."""
        tiene_json = '{' in respuesta and '}' in respuesta and '"resumen"' in respuesta
        if not tiene_json:
            logger.warning(f"Respuesta sin JSON válido en intento {intento}")
            return intento >= self.MAX_INTENTOS  # Aceptar en último intento
        return True
    
    def _validar_campos_requeridos(self, respuesta: str, intento: int) -> bool:
        """Valida que la respuesta contenga todos los campos requeridos."""
        campos_requeridos = ['"resumen"', '"palabras_clave"', '"factores_similitud"', '"conclusion"']
        campos_faltantes = [campo for campo in campos_requeridos if campo not in respuesta]
        
        if campos_faltantes:
            logger.warning(f"Faltan campos {campos_faltantes} en intento {intento}")
            return intento >= self.MAX_INTENTOS  # Aceptar en último intento
        return True
    
    async def _esperar_antes_reintentar(self, intento: int):
        """Espera progresivamente antes de reintentar (backoff exponencial)."""
        tiempo_espera = self.TIEMPO_ESPERA_BASE * (2 ** (intento - 1))
        logger.info(f"Esperando {tiempo_espera}s antes del siguiente intento")
        await asyncio.sleep(tiempo_espera)
