"""
Servicio principal de búsqueda de similares unificado con vectorstore.
"""

import logging
import time
from typing import List, Dict, Any
from langchain_core.documents import Document

from app.schemas.similarity_schemas import (
    SimilaritySearchRequest,
    RespuestaBusquedaSimilitud,
    ResumenIA,
    RespuestaGenerarResumen,
)

from .documentos.documento_service import DocumentoService
from .documentos.documento_retrieval_service import DocumentoRetrievalService
from app.embeddings.embeddings import get_embeddings
from app.llm.llm_service import get_llm

# Importar módulos RAG para consistencia
from app.services.RAG.retriever import DynamicJusticIARetriever

# Importar constructor de prompts específico para similarity
from .similarity_prompt_builder import (
    create_similarity_summary_prompt,
    create_similarity_search_context
)

# IMPORTANTE: Usar constantes de metadata para evitar typos
from app.constants.metadata_fields import MetadataFields as MF

# Módulos especializados para separación de responsabilidades
from .document_retriever import DocumentRetriever
from .summary_generator import SummaryGenerator
from .response_parser import ResponseParser

logger = logging.getLogger(__name__)

class SimilarityService:
    """Servicio principal para búsqueda de casos legales similares unificado."""

    def __init__(self):
        self.documento_service = DocumentoService()
        self.documento_retrieval_service = DocumentoRetrievalService()
        self.embeddings_service = None
        
        # Inicializar módulos especializados
        self.document_retriever = DocumentRetriever()
        self.summary_generator = SummaryGenerator()
        self.response_parser = ResponseParser()

    async def _get_embeddings_service(self):
        if self.embeddings_service is None:
            self.embeddings_service = await get_embeddings()
        return self.embeddings_service

    async def search_similar_cases(
        self, request: SimilaritySearchRequest, db=None
    ) -> RespuestaBusquedaSimilitud:
        """Busca casos legales similares según el modo especificado."""
        start_time = time.time()
        
        try:
            if request.modo_busqueda == "descripcion":
                casos_similares = await self._buscar_por_descripcion(request)
                criterio_busqueda = request.texto_consulta
            else:
                casos_similares = await self._buscar_por_expediente(request, db)
                criterio_busqueda = request.numero_expediente

            end_time = time.time()
            tiempo_busqueda = round(end_time - start_time, 2)
            
            # Calcular precisión promedio
            if casos_similares:
                precision_promedio = round(
                    sum(caso.get('puntuacion_similitud', 0) for caso in casos_similares) / len(casos_similares) * 100, 
                    1
                )
            else:
                precision_promedio = 0.0

            return RespuestaBusquedaSimilitud(
                criterio_busqueda=criterio_busqueda,
                modo_busqueda=request.modo_busqueda,
                total_resultados=len(casos_similares),
                casos_similares=casos_similares,
                tiempo_busqueda_segundos=tiempo_busqueda,
                precision_promedio=precision_promedio
            )

        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            raise

    async def _buscar_por_descripcion(
        self, request: SimilaritySearchRequest
    ) -> List[Dict[str, Any]]:
        """Busca casos similares por descripción usando LangChain Retriever como RAG."""
        if not request.texto_consulta:
            raise ValueError("texto_consulta es requerido")

        # Usar el mismo retriever que RAG para consistencia
        retriever = DynamicJusticIARetriever(
            top_k=request.limite or 30,
            similarity_threshold=request.umbral_similitud if request.umbral_similitud > 0 else 0.3
        )
        
        # Obtener documentos como LangChain Documents
        # El retriever ya aplica el similarity_threshold internamente
        docs = await retriever._aget_relevant_documents(request.texto_consulta)
        
        logger.info(f"Búsqueda por descripción: {len(docs)} documentos recuperados")

        # Convertir LangChain Documents al formato esperado por documento_retrieval_service
        similar_docs = []
        for doc in docs:
            # Usar más caracteres para documentos legales (500)
            preview_chars = 500
            content_preview = doc.page_content[:preview_chars] + "..." if len(doc.page_content) > preview_chars else doc.page_content
            
            # Usar constantes de metadata (MF) para evitar typos
            similar_docs.append({
                "id": doc.metadata.get(MF.DOCUMENTO_ID, ""),
                "expedient_id": doc.metadata.get(MF.EXPEDIENTE_NUMERO, ""),
                "document_name": doc.metadata.get(MF.DOCUMENTO_NOMBRE, ""),
                "content_preview": content_preview,
                "similarity_score": doc.metadata.get(MF.SIMILARITY_SCORE, 0.0),
                "metadata": doc.metadata
            })

        return await self.documento_retrieval_service.procesar_casos_similares(
            similar_docs
        )

    async def _buscar_por_expediente(
        self, request: SimilaritySearchRequest, db=None
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
            db=db  # Pasar db para filtrar por estado
        )

        return await self.documento_retrieval_service.procesar_casos_similares(
            similar_docs
        )

    async def generate_case_summary(self, numero_expediente: str) -> RespuestaGenerarResumen:
        """Genera un resumen de IA para un expediente específico usando arquitectura RAG."""
        start_time = time.time()
        
        try:
            logger.info(f"Iniciando generación de resumen para expediente: {numero_expediente}")
            
            # 1. Obtener documentos del expediente (usando DocumentRetriever)
            docs_expediente = await self.document_retriever.obtener_documentos_expediente(numero_expediente)
            
            # 2. Crear contexto para el LLM (usando SummaryGenerator)
            contexto_completo = await self.summary_generator.crear_contexto_resumen(docs_expediente)
            
            # 3. Generar respuesta con LLM con reintentos (usando SummaryGenerator)
            respuesta_content = await self.summary_generator.generar_respuesta_llm(
                contexto_completo, 
                numero_expediente
            )
            
            # 4. Parsear respuesta de IA (usando ResponseParser)
            resumen_ia = self.response_parser.parsear_respuesta_ia(respuesta_content)
            
            end_time = time.time()
            
            return RespuestaGenerarResumen(
                numero_expediente=numero_expediente,
                total_documentos_analizados=len(docs_expediente),
                resumen_ia=resumen_ia,
                tiempo_generacion_segundos=round(end_time - start_time, 2)
            )
            
        except Exception as e:
            logger.error(f"Error generando resumen para expediente {numero_expediente}: {e}")
            raise
