"""
Generador de Resúmenes de Expedientes con LLM y Sistema Robusto de Reintentos.

Este módulo gestiona la generación de resúmenes automáticos de expedientes
judiciales utilizando modelos de lenguaje (LLM), implementando un sistema
avanzado de reintentos con validaciones progresivas y backoff exponencial.

Arquitectura de generación:

    Fase 1: Preparación de contexto
    └─> Formatear documentos del expediente
        └─> Limitar longitud (max_docs=20, max_chars=7000)
            └─> Validar contexto mínimo (>100 chars)

    Fase 2: Generación con LLM (hasta 3 intentos)
    └─> Intento 1: Prompt + LLM invocation
        └─> Validaciones:
            1. Respuesta no vacía
            2. Longitud mínima (200 chars)
            3. Contiene JSON básico {"resumen"...}
            4. Contiene campos requeridos
        └─> Si falla → Esperar 2s → Intento 2

    Intento 2: Backoff 4s
    └─> Mismas validaciones
        └─> Si falla → Esperar 4s → Intento 3

    Intento 3: Backoff 8s (último intento)
    └─> Validaciones relajadas (aceptar respuesta aunque no pase todas)
        └─> Retornar mejor respuesta disponible

Sistema de reintentos:
    - **Máximo intentos**: 3
    - **Backoff exponencial**: 2s, 4s, 8s
    - **Validaciones progresivas**: Estrictas → Relajadas
    - **Degradación elegante**: Aceptar respuesta parcial en último intento

Validaciones aplicadas (en orden):

    1. **Validación de vacío**:
       - Verificar que respuesta no sea None o ""
       - Crítica: Siempre falla si está vacía

    2. **Validación de longitud**:
       - Mínimo 200 caracteres
       - Relajada en último intento (acepta cualquier longitud)

    3. **Validación de estructura JSON**:
       - Debe contener '{', '}' y '"resumen"'
       - Relajada en último intento

    4. **Validación de campos requeridos**:
       - "resumen", "palabras_clave", "factores_similitud", "conclusion"
       - Relajada en último intento (puede faltar algunos campos)

Parámetros de configuración:
    - MAX_INTENTOS: 3
    - TIEMPO_ESPERA_BASE: 2 segundos
    - MIN_LONGITUD_RESPUESTA: 200 caracteres
    - max_docs: 20 chunks (balance contexto/tokens)
    - max_chars_per_doc: 7000 caracteres por chunk

Estrategia de backoff exponencial:
    - Intento 1 → Fallo → Esperar 2s (2^0 * 2)
    - Intento 2 → Fallo → Esperar 4s (2^1 * 2)
    - Intento 3 → Fallo → Esperar 8s (2^2 * 2)
    - Permite al LLM "recuperarse" de errores temporales

Escenarios manejados:

    1. **LLM devuelve respuesta vacía**:
       → Reintentar hasta 3 veces
       → Si persiste: ValueError

    2. **LLM corta la respuesta (JSON incompleto)**:
       → Validación detecta JSON incompleto
       → Reintentar
       → Último intento: Aceptar y dejar que ResponseParser repare

    3. **LLM responde en inglés o formato incorrecto**:
       → Validación de campos detecta problema
       → Reintentar
       → Último intento: Aceptar y dejar que ResponseParser maneje

    4. **Error de conexión o timeout del LLM**:
       → Capturar excepción
       → Reintentar con backoff
       → Último intento: Propagar error

    5. **Contexto demasiado corto**:
       → ValueError inmediato (no reintentar)
       → Problema con documentos, no con LLM

Integración con otros módulos:
    - similarity_prompt_builder: Construcción de prompts especializados
    - llm_service: Obtención de instancia LLM (Ollama)
    - ResponseParser: Parseo y reparación de respuestas (siguiente etapa)
    - SimilarityService: Orquestador principal

Example:
    >>> generator = SummaryGenerator()
    >>> 
    >>> # Crear contexto
    >>> contexto = await generator.crear_contexto_resumen(docs_expediente)
    >>> print(f"Contexto: {len(contexto)} chars")
    Contexto: 15847 chars
    >>> 
    >>> # Generar resumen con reintentos automáticos
    >>> respuesta = await generator.generar_respuesta_llm(
    ...     contexto, "24-000123-0001-PE"
    ... )
    >>> print(f"Respuesta: {len(respuesta)} chars")
    Intento 1/3 de generación
    Respuesta válida generada en intento 1
    Respuesta: 1245 chars

Logging y observabilidad:
    - Info: Inicio de generación, contexto creado, intento actual
    - Warning: Validaciones fallidas (respuesta corta, sin JSON, campos faltantes)
    - Error: Excepciones del LLM, contexto vacío

Performance:
    - Intento exitoso (1): ~2-5 segundos (depende del LLM)
    - Intento exitoso (2): ~8-12 segundos (incluye 2s espera)
    - Intento exitoso (3): ~20-30 segundos (incluye 6s espera acumulada)

Note:
    - El backoff exponencial evita saturar el LLM
    - Las validaciones relajadas en último intento maximizan disponibilidad
    - ResponseParser maneja reparación de JSON (siguiente etapa del pipeline)
    - La longitud de contexto afecta calidad y tiempo de respuesta

Ver también:
    - app.services.busqueda_similares.similarity_prompt_builder: Construcción de prompts
    - app.services.busqueda_similares.response_parser: Parseo de respuestas
    - app.llm.llm_service: Servicio LLM (Ollama)
    - app.services.busqueda_similares.similarity_service: Orquestador

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0
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
