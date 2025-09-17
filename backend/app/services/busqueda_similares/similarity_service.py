"""
Servicio principal de búsqueda de similares.

Este servicio orquesta todos los módulos especializados para proporcionar
la funcionalidad completa de búsqueda de casos legales similares.
"""

import logging
from typing import List, Dict, Any, Optional
from app.schemas.similarity_schemas import SimilaritySearchRequest

# Importar módulos especializados
from .busqueda.milvus_service import MilvusSearchService
from .resumen.resumen_service import ResumenSemanticoService
from .documentos.documento_service import DocumentoService
from .validacion.validacion_service import ValidacionService

# Importar servicio de embeddings centralizado
from app.embeddings.embeddings import get_embeddings

logger = logging.getLogger(__name__)


class SimilarityService:
    """
    Servicio principal para búsqueda de casos legales similares.
    
    Orquesta todos los componentes especializados para proporcionar una interfaz
    unificada para la búsqueda semántica de expedientes legales.
    """
    
    def __init__(self):
        """Inicializa todos los servicios especializados."""
        self.milvus_service = MilvusSearchService()
        self.resumen_service = ResumenSemanticoService()
        self.documento_service = DocumentoService()
        self.validacion_service = ValidacionService()
        self.embeddings_service = None  # Inicialización lazy
        
        logger.info("SimilarityService inicializado con todos los módulos")
    
    async def _get_embeddings_service(self):
        """Obtiene el servicio de embeddings de forma lazy."""
        if self.embeddings_service is None:
            self.embeddings_service = await get_embeddings()
        return self.embeddings_service
    
    async def search_similar_cases(
        self,
        request: SimilaritySearchRequest
    ) -> List[Dict[str, Any]]:
        """
        Busca casos legales similares a un expediente dado.
        
        Args:
            request: Solicitud de búsqueda con parámetros
            
        Returns:
            Lista de diccionarios con casos similares encontrados
        """
        try:
            # 1. Validar solicitud
            es_valido, error_msg = self.validacion_service.validar_solicitud_busqueda(request)
            if not es_valido:
                raise ValueError(f"Solicitud inválida: {error_msg}")
            
            # Determinar el ID del expediente según el modo de búsqueda
            if request.search_mode == "expedient":
                expedient_id = request.expedient_number
                if not expedient_id:
                    raise ValueError("expedient_number es requerido para búsqueda por expediente")
                    
                logger.info(f"Iniciando búsqueda de similares para expediente: {expedient_id}")
                
                # 2. Verificar existencia del expediente
                expediente_existe = await self.documento_service.verificar_existencia_expediente(
                    expedient_id
                )
                if not expediente_existe:
                    raise ValueError(f"Expediente {expedient_id} no encontrado")
                
                # 3. Obtener datos completos del expediente
                expedient_data = await self.documento_service.obtener_expediente_completo(
                    expedient_id, incluir_documentos=True
                )
                
                if not expedient_data:
                    raise ValueError(f"No se pudieron obtener datos del expediente {expedient_id}")
                
                # 4. Generar embedding del expediente
                expedient_text = self._preparar_texto_expediente(expedient_data)
                embeddings_service = await self._get_embeddings_service()
                query_vector = await embeddings_service.aembed_query(expedient_text)
                exclude_expedient_id = expedient_id
                
            else:  # search_mode == "description"
                if not request.query_text:
                    raise ValueError("query_text es requerido para búsqueda por descripción")
                    
                logger.info(f"Iniciando búsqueda de similares por descripción")
                
                # 4. Generar embedding del texto de consulta
                embeddings_service = await self._get_embeddings_service()
                query_vector = await embeddings_service.aembed_query(request.query_text)
                exclude_expedient_id = None
            
            # 5. Buscar documentos similares en Milvus
            if exclude_expedient_id:
                similar_docs = await self.milvus_service.search_by_expedient_vector(
                    expedient_vector=query_vector,
                    exclude_expedient_id=exclude_expedient_id,
                    top_k=request.limit or 30
                )
            else:
                similar_docs = await self.milvus_service.search_by_vector(
                    query_vector=query_vector,
                    top_k=request.limit or 30
                )
            
            # 6. Filtrar por threshold
            similar_docs = [
                doc for doc in similar_docs 
                if doc.get("similarity_score", 0) >= request.similarity_threshold
            ]
            
            # 7. Agrupar por expediente y obtener datos completos
            expedientes_similares = await self._procesar_documentos_similares(
                similar_docs, True  # Siempre incluir resumen por ahora
            )
            
            logger.info(f"Encontrados {len(expedientes_similares)} expedientes similares")
            return expedientes_similares
            
        except Exception as e:
            logger.error(f"Error en búsqueda de similares: {e}")
            raise
    
    async def _procesar_documentos_similares(
        self,
        similar_docs: List[Dict[str, Any]],
        incluir_resumen: bool
    ) -> List[Dict[str, Any]]:
        """
        Procesa los documentos similares para generar casos similares.
        
        Args:
            similar_docs: Lista de documentos similares de Milvus
            incluir_resumen: Si incluir resumen semántico
            
        Returns:
            Lista de diccionarios con casos similares procesados
        """
        try:
            # Agrupar documentos por expediente
            expedientes_map = {}
            for doc in similar_docs:
                expedient_id = doc.get("expedient_id")
                if expedient_id:
                    if expedient_id not in expedientes_map:
                        expedientes_map[expedient_id] = {
                            "expedient_id": expedient_id,
                            "documents": [],
                            "max_similarity": 0.0
                        }
                    
                    expedientes_map[expedient_id]["documents"].append(doc)
                    expedientes_map[expedient_id]["max_similarity"] = max(
                        expedientes_map[expedient_id]["max_similarity"],
                        doc.get("similarity_score", 0)
                    )
            
            # Obtener datos completos de expedientes
            expedient_ids = list(expedientes_map.keys())
            expedientes_completos = await self.documento_service.obtener_expedientes_batch(
                expedient_ids, incluir_documentos=True
            )
            
            # Construir casos similares
            casos_similares = []
            for expediente in expedientes_completos:
                expedient_id = expediente["expedient_id"]
                similar_info = expedientes_map.get(expedient_id, {})
                
                # Generar resumen si se solicita
                semantic_summary = None
                if incluir_resumen:
                    try:
                        semantic_summary = await self.resumen_service.generar_resumen_expediente(
                            expediente
                        )
                    except Exception as e:
                        logger.warning(f"No se pudo generar resumen para {expedient_id}: {e}")
                
                # Preparar documentos coincidentes
                matching_documents = []
                for doc in similar_info.get("documents", []):
                    matching_documents.append({
                        "document_name": doc.get("document_name"),
                        "content_preview": doc.get("content_preview"),
                        "similarity_score": doc.get("similarity_score")
                    })
                
                caso_similar = {
                    "expedient_id": expedient_id,
                    "expedient_name": expediente.get("expedient_name"),
                    "similarity_score": similar_info.get("max_similarity", 0),
                    "matching_documents": matching_documents,
                    "semantic_summary": semantic_summary
                }
                
                casos_similares.append(caso_similar)
            
            # Ordenar por similarity_score descendente
            casos_similares.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            
            return casos_similares
            
        except Exception as e:
            logger.error(f"Error procesando documentos similares: {e}")
            raise
    
    def _preparar_texto_expediente(self, expedient_data: Dict[str, Any]) -> str:
        """
        Prepara el texto del expediente para generar embedding.
        
        Args:
            expedient_data: Datos completos del expediente
            
        Returns:
            Texto unificado del expediente
        """
        try:
            texto_parts = []
            
            # Agregar metadatos básicos
            if expedient_data.get("expedient_name"):
                texto_parts.append(f"Expediente: {expedient_data['expedient_name']}")
            
            # Agregar contenido de documentos
            documents = expedient_data.get("documents", [])
            for doc in documents[:10]:  # Limitar a primeros 10 documentos
                if doc.get("content_preview"):
                    texto_parts.append(doc["content_preview"])
            
            texto_completo = " ".join(texto_parts)
            
            # Sanitizar y validar
            texto_limpio = self.validacion_service.sanitizar_texto(texto_completo)
            
            if not texto_limpio:
                raise ValueError("No se pudo generar texto válido del expediente")
            
            return texto_limpio
            
        except Exception as e:
            logger.error(f"Error preparando texto del expediente: {e}")
            raise

    def __del__(self):
        """Limpia recursos al destruir el servicio."""
        try:
            # El vectorstore centralizado maneja sus propias conexiones
            logger.info("SimilarityService destruido - recursos centralizados")
        except Exception as e:
            logger.error(f"Error limpiando recursos: {e}")
