"""
Servicio principal de búsqueda de similares unificado con vectorstore.
"""

import logging
import time
from typing import List, Dict, Any
from app.schemas.similarity_schemas import (
    SimilaritySearchRequest,
    RespuestaBusquedaSimilitud,
    ResumenIA,
    RespuestaGenerarResumen,
)

from .documentos.documento_service import DocumentoService
from .documentos.documento_retrieval_service import DocumentoRetrievalService
from app.embeddings.embeddings import get_embeddings
from app.llm.llm_service import consulta_simple, get_llm

logger = logging.getLogger(__name__)


class SimilarityService:
    """Servicio principal para búsqueda de casos legales similares unificado."""

    def __init__(self):
        self.documento_service = DocumentoService()
        self.documento_retrieval_service = DocumentoRetrievalService()
        self.embeddings_service = None

    async def _get_embeddings_service(self):
        if self.embeddings_service is None:
            self.embeddings_service = await get_embeddings()
        return self.embeddings_service

    async def search_similar_cases(
        self, request: SimilaritySearchRequest
    ) -> RespuestaBusquedaSimilitud:
        """Busca casos legales similares según el modo especificado."""
        try:
            if request.modo_busqueda == "descripcion":
                casos_similares = await self._buscar_por_descripcion(request)
                criterio_busqueda = request.texto_consulta
            else:
                casos_similares = await self._buscar_por_expediente(request)
                criterio_busqueda = request.numero_expediente

            return RespuestaBusquedaSimilitud(
                criterio_busqueda=criterio_busqueda,
                modo_busqueda=request.modo_busqueda,
                total_resultados=len(casos_similares),
                casos_similares=casos_similares,
            )

        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            raise

    async def _buscar_por_descripcion(
        self, request: SimilaritySearchRequest
    ) -> List[Dict[str, Any]]:
        """Busca casos similares por descripción usando vectorstore unificado."""
        if not request.texto_consulta:
            raise ValueError("texto_consulta es requerido")

        embeddings_service = await self._get_embeddings_service()
        query_vector = await embeddings_service.aembed_query(request.texto_consulta)

        # Usar vectorstore unificado
        from app.vectorstore.vectorstore import search_by_vector

        similar_docs = await search_by_vector(
            query_vector=query_vector,
            top_k=request.limite or 30,
            score_threshold=request.umbral_similitud,
        )

        return await self.documento_retrieval_service.procesar_casos_similares(
            similar_docs
        )

    async def _buscar_por_expediente(
        self, request: SimilaritySearchRequest
    ) -> List[Dict[str, Any]]:
        """Busca casos similares por expediente específico usando búsqueda híbrida."""
        expedient_id = request.numero_expediente
        if not expedient_id:
            raise ValueError("numero_expediente es requerido")

        from app.vectorstore.vectorstore import search_similar_expedients

        similar_docs = await search_similar_expedients(
            expedient_id=expedient_id,
            top_k=request.limite or 30,
            score_threshold=request.umbral_similitud,
        )

        return await self.documento_retrieval_service.procesar_casos_similares(
            similar_docs
        )

    async def generate_case_summary(self, numero_expediente: str) -> RespuestaGenerarResumen:
        """Genera un resumen de IA para un expediente específico."""
        start_time = time.time()
        
        try:
            # 1. Buscar todos los documentos del expediente
            from app.vectorstore.vectorstore import get_expedient_documents
            
            documentos = await get_expedient_documents(numero_expediente)
            
            if not documentos:
                raise ValueError(f"No se encontraron documentos para el expediente {numero_expediente}")
            
            # 2. Construir contexto completo del expediente
            contexto_completo = self._construir_contexto_expediente(documentos, numero_expediente)
            
            # 3. Generar resumen con IA usando el modelo rápido
            prompt = self._construir_prompt_resumen(contexto_completo, numero_expediente)
            
            # Usar el LLM rápido específico para resúmenes
            fast_llm = await get_llm(fast=True)
            respuesta_llm = fast_llm.invoke(prompt)
            respuesta_content = getattr(respuesta_llm, "content", str(respuesta_llm))
            
            # 4. Parsear respuesta de IA
            resumen_ia = self._parsear_respuesta_ia(respuesta_content)
            
            end_time = time.time()
            
            return RespuestaGenerarResumen(
                numero_expediente=numero_expediente,
                total_documentos_analizados=len(documentos),
                resumen_ia=resumen_ia,
                tiempo_generacion_segundos=round(end_time - start_time, 2)
            )
            
        except Exception as e:
            logger.error(f"Error generando resumen para expediente {numero_expediente}: {e}")
            raise

    def _construir_contexto_expediente(self, documentos: List[Any], numero_expediente: str) -> str:
        """Construye el contexto completo del expediente a partir de los documentos."""
        contexto = f"EXPEDIENTE: {numero_expediente}\n\n"
        contexto += "DOCUMENTOS DEL EXPEDIENTE:\n"
        contexto += "=" * 50 + "\n\n"
        
        for i, doc in enumerate(documentos, 1):
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            contenido = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            
            nombre_archivo = metadata.get('CT_Nombre_archivo', f'Documento {i}')
            contexto += f"DOCUMENTO {i}: {nombre_archivo}\n"
            contexto += "-" * 40 + "\n"
            contexto += f"{contenido}\n\n"
        
        return contexto

    def _construir_prompt_resumen(self, contexto: str, numero_expediente: str) -> str:
        """Construye el prompt para el LLM que generará el resumen estructurado."""
        return f"""Eres un asistente legal especializado en análisis de expedientes judiciales. 

Analiza el siguiente expediente completo y genera un resumen estructurado en el formato JSON EXACTO que se muestra a continuación.

{contexto}

Debes responder ÚNICAMENTE con un JSON válido en el siguiente formato, sin texto adicional:

{{
    "resumen": "Descripción detallada del caso, incluyendo los hechos principales, las partes involucradas, y el tipo de procedimiento legal",
    "palabras_clave": ["palabra1", "palabra2", "palabra3", "palabra4", "palabra5"],
    "factores_similitud": ["Factor legal 1", "Factor legal 2", "Factor legal 3", "Factor legal 4"],
    "conclusion": "Análisis de las perspectivas del caso y conclusiones principales"
}}

IMPORTANTE:
- El resumen debe ser comprensivo pero conciso (máximo 300 palabras)
- Las palabras clave deben ser términos legales relevantes (5-8 palabras)
- Los factores de similitud deben ser aspectos legales específicos que caracterizan el caso
- La conclusión debe evaluar las fortalezas del caso y perspectivas legales
- Responde SOLO con el JSON, sin explicaciones adicionales"""

    def _parsear_respuesta_ia(self, respuesta_raw: str) -> ResumenIA:
        """Parsea la respuesta del LLM y la convierte en objeto ResumenIA."""
        import json
        import re
        
        # Log para debug
        logger.info(f"Respuesta cruda del LLM (primeros 200 chars): {respuesta_raw[:200]}")
        
        try:
            # Limpiar la respuesta básica
            respuesta_limpia = respuesta_raw.strip()
            
            # Buscar JSON simple - patrón más básico y robusto
            json_match = re.search(r'\{[^{}]*"resumen"[^{}]*"palabras_clave"[^{}]*"factores_similitud"[^{}]*"conclusion"[^{}]*\}', 
                                 respuesta_limpia, re.DOTALL)
            
            if not json_match:
                # Intentar patrón más amplio
                json_match = re.search(r'\{.*?"resumen".*?\}', respuesta_limpia, re.DOTALL)
            
            if json_match:
                json_str = json_match.group()
                logger.info(f"JSON extraído: {json_str}")
                
                # Intentar parsear el JSON
                datos = json.loads(json_str)
                
                return ResumenIA(
                    resumen=datos.get("resumen", "No se pudo generar resumen"),
                    palabras_clave=datos.get("palabras_clave", []),
                    factores_similitud=datos.get("factores_similitud", []),
                    conclusion=datos.get("conclusion", "No se pudo generar conclusión")
                )
            else:
                logger.warning("No se encontró patrón JSON válido en la respuesta")
                return self._crear_resumen_fallback(respuesta_raw)
                
        except json.JSONDecodeError as e:
            logger.error(f"Error JSON decode: {e}")
            return self._crear_resumen_fallback(respuesta_raw)
        except Exception as e:
            logger.error(f"Error general parseando respuesta IA: {e}")
            return self._crear_resumen_fallback(respuesta_raw)
    
    def _crear_resumen_fallback(self, respuesta_raw: str) -> ResumenIA:
        """Crea un resumen de fallback cuando no se puede parsear JSON."""
        return ResumenIA(
            resumen=respuesta_raw[:500] if respuesta_raw else "No se pudo generar resumen automático",
            palabras_clave=["Análisis Legal", "Expediente Judicial", "Procedimiento"],
            factores_similitud=["Contenido del expediente", "Documentación legal"],
            conclusion="Se requiere análisis manual adicional para conclusiones específicas"
        )
