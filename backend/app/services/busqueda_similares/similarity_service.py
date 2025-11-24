"""
Servicio Principal de Búsqueda de Casos Similares y Generación de Resúmenes con IA.

Este módulo implementa el servicio de alto nivel para el sistema de búsqueda de
expedientes judiciales similares y generación automática de resúmenes legales,
unificando búsqueda vectorial (Milvus), búsqueda por expediente, y generación
de resúmenes con LLM en una arquitectura RAG (Retrieval-Augmented Generation).

Arquitectura del servicio:

    SimilarityService (Orquestador)
    ├─> DocumentRetriever: Obtención de documentos (Milvus + Fallback BD)
    ├─> SummaryGenerator: Generación de resúmenes con LLM + Reintentos
    ├─> ResponseParser: Parseo y reparación de respuestas LLM
    ├─> DocumentoService: Acceso a metadatos en BD
    └─> DocumentoRetrievalService: Procesamiento de resultados

Modos de búsqueda soportados:

    1. **Búsqueda por descripción** (modo="descripcion"):
       └─> Usuario escribe consulta en lenguaje natural
           └─> Embedding de consulta → Búsqueda vectorial en Milvus
               └─> DynamicJusticIARetriever con top_k y threshold
                   └─> Retorna documentos más similares semánticamente

    2. **Búsqueda por expediente** (modo="expediente"):
       └─> Usuario proporciona número de expediente de referencia
           └─> Búsqueda híbrida: vectorstore + filtros de BD
               └─> search_similar_expedients() del vectorstore
                   └─> Retorna expedientes similares al de referencia

Flujos principales:

    A. Búsqueda de casos similares (search_similar_cases):
       1. Validar parámetros de búsqueda
       2. Seleccionar modo (descripción vs expediente)
       3. Ejecutar búsqueda vectorial con retriever
       4. Procesar resultados (metadata, scores, previews)
       5. Calcular métricas (precisión promedio, tiempo)
       6. Retornar RespuestaBusquedaSimilitud

    B. Generación de resumen (generate_case_summary):
       1. Obtener documentos del expediente (DocumentRetriever)
       2. Crear contexto optimizado (SummaryGenerator)
       3. Generar respuesta con LLM + reintentos (SummaryGenerator)
       4. Parsear y validar JSON (ResponseParser)
       5. Retornar RespuestaGenerarResumen con ResumenIA

Parámetros de búsqueda:

    Búsqueda por descripción:
    - top_k: 30 (default) documentos recuperados
    - similarity_threshold: 0.3 (default) umbral de similitud

    Búsqueda por expediente:
    - top_k: 30 (default) expedientes similares
    - score_threshold: configurable
    - Filtra por estado de procesamiento (solo "Procesado")

Estructura de respuesta (búsqueda):

    RespuestaBusquedaSimilitud {
        criterio_busqueda: str,           # Texto o número de expediente
        modo_busqueda: str,               # "descripcion" o "expediente"
        total_resultados: int,            # Cantidad de casos encontrados
        casos_similares: List[Dict],      # Resultados con metadata
        tiempo_busqueda_segundos: float,  # Performance metric
        precision_promedio: float         # Score promedio (0-100)
    }

Estructura de respuesta (resumen):

    RespuestaGenerarResumen {
        numero_expediente: str,                # Expediente resumido
        total_documentos_analizados: int,      # Documentos procesados
        resumen_ia: ResumenIA {                # Resumen generado
            resumen: str,                      # Texto descriptivo
            palabras_clave: List[str],         # 3-10 palabras
            factores_similitud: List[str],     # Factores legales
            conclusion: str                    # Análisis jurídico
        },
        tiempo_generacion_segundos: float      # Performance metric
    }

Metadata incluida en resultados:

    Cada caso similar incluye:
    - id: ID del documento en BD
    - expedient_id: Número de expediente (formato estándar)
    - document_name: Nombre del archivo original
    - content_preview: Primeros 500 caracteres del contenido
    - similarity_score: Score de similitud (0.0-1.0)
    - metadata: Metadata completa de Milvus (timestamps, chunks, etc.)

Separación de responsabilidades:

    **SimilarityService** (este módulo):
    - Orquestación de flujos completos
    - Selección de modo de búsqueda
    - Métricas y timing
    - Manejo de errores de alto nivel

    **DocumentRetriever**:
    - Obtención de documentos con fallback
    - Integración con Milvus/BD

    **SummaryGenerator**:
    - Generación de resúmenes con LLM
    - Sistema de reintentos
    - Validaciones de respuesta

    **ResponseParser**:
    - Parseo de JSON del LLM
    - Reparación automática
    - Creación de objetos ResumenIA

Integración con RAG:

    La búsqueda por descripción usa arquitectura RAG completa:
    1. Retrieval: DynamicJusticIARetriever obtiene contexto relevante
    2. Augmentation: Contexto se agrega al prompt del LLM
    3. Generation: LLM genera respuesta informada por contexto

    La generación de resumen también usa RAG:
    1. Retrieval: DocumentRetriever obtiene documentos del expediente
    2. Augmentation: Documentos se formatean como contexto estructurado
    3. Generation: LLM genera resumen basado en documentos reales

Performance esperada:

    Búsqueda por descripción:
    - ~200-500ms (búsqueda vectorial Milvus)

    Búsqueda por expediente:
    - ~300-700ms (búsqueda híbrida + filtros BD)

    Generación de resumen:
    - ~5-15s (intento exitoso)
    - ~20-30s (con reintentos)

Manejo de errores:

    - ValueError: Parámetros inválidos, documentos no encontrados
    - Exception genérica: Errores del LLM, Milvus, BD
    - Logging detallado para debugging

Example:
    >>> service = SimilarityService()
    >>> 
    >>> # Búsqueda por descripción
    >>> request = SimilaritySearchRequest(
    ...     modo_busqueda="descripcion",
    ...     texto_consulta="despido injustificado por embarazo",
    ...     limite=10,
    ...     umbral_similitud=0.4
    ... )
    >>> resultado = await service.search_similar_cases(request, db)
    >>> print(f"Encontrados {resultado.total_resultados} casos")
    >>> print(f"Precisión: {resultado.precision_promedio}%")
    >>> 
    >>> # Generación de resumen
    >>> resumen_response = await service.generate_case_summary(
    ...     "24-000123-0001-LA"
    ... )
    >>> print(resumen_response.resumen_ia.resumen)
    >>> print(resumen_response.resumen_ia.palabras_clave)

Note:
    - Las búsquedas requieren que los documentos estén vectorizados en Milvus
    - La generación de resumen requiere que el expediente tenga documentos procesados
    - Los scores de similitud son normalizados (0.0-1.0)
    - La precisión promedio se calcula como porcentaje (0-100)

Ver también:
    - app.services.busqueda_similares.document_retriever: Recuperación de documentos
    - app.services.busqueda_similares.summary_generator: Generación con LLM
    - app.services.busqueda_similares.response_parser: Parseo de respuestas
    - app.services.RAG.retriever: DynamicJusticIARetriever
    - app.vectorstore.vectorstore: search_similar_expedients

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0
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

        retriever = DynamicJusticIARetriever(
            top_k=request.limite or 30,
            similarity_threshold=request.umbral_similitud if request.umbral_similitud > 0 else 0.3
        )
        
        docs = await retriever._aget_relevant_documents(request.texto_consulta)
        logger.info(f"Búsqueda por descripción: {len(docs)} documentos recuperados")

        similar_docs = []
        for doc in docs:
            similarity_score_from_metadata = doc.metadata.get(MF.SIMILARITY_SCORE, 0.0)
            
            preview_chars = 500
            content_preview = doc.page_content[:preview_chars] + "..." if len(doc.page_content) > preview_chars else doc.page_content
            
            similar_docs.append({
                "id": doc.metadata.get(MF.DOCUMENTO_ID, ""),
                "expedient_id": doc.metadata.get(MF.EXPEDIENTE_NUMERO, ""),
                "document_name": doc.metadata.get(MF.DOCUMENTO_NOMBRE, ""),
                "content_preview": content_preview,
                "similarity_score": similarity_score_from_metadata,
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
