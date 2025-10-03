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
from app.services.RAG.retriever import JusticIARetriever

# Importar constructor de prompts específico para similarity
from .similarity_prompt_builder import (
    create_similarity_summary_prompt,
    create_similarity_search_context
)

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
        start_time = time.time()
        
        try:
            if request.modo_busqueda == "descripcion":
                casos_similares = await self._buscar_por_descripcion(request)
                criterio_busqueda = request.texto_consulta
            else:
                casos_similares = await self._buscar_por_expediente(request)
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
        retriever = JusticIARetriever(top_k=request.limite or 30)
        
        # Obtener documentos como LangChain Documents
        docs = await retriever._aget_relevant_documents(request.texto_consulta)
        
        # Filtrar por umbral de similitud si se especifica
        if request.umbral_similitud > 0:
            docs = [doc for doc in docs if doc.metadata.get("similarity_score", 0) >= request.umbral_similitud]

        # Convertir LangChain Documents al formato esperado por documento_retrieval_service
        similar_docs = []
        for doc in docs:
            # Usar más caracteres para documentos legales (500 en lugar de 200)
            preview_chars = 500
            content_preview = doc.page_content[:preview_chars] + "..." if len(doc.page_content) > preview_chars else doc.page_content
            
            similar_docs.append({
                "id": doc.metadata.get("id_documento", ""),
                "expedient_id": doc.metadata.get("expediente_numero", ""),
                "document_name": doc.metadata.get("archivo", ""),
                "content_preview": content_preview,
                "similarity_score": doc.metadata.get("similarity_score", 0.0),
                "metadata": doc.metadata
            })

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
        """Genera un resumen de IA para un expediente específico usando arquitectura RAG."""
        start_time = time.time()
        
        try:
            logger.info(f"Iniciando generación de resumen para expediente: {numero_expediente}")
            
            # 1. Obtener documentos del expediente
            docs_expediente = await self._obtener_documentos_expediente(numero_expediente)
            
            # 2. Crear contexto para el LLM
            contexto_completo = await self._crear_contexto_resumen(docs_expediente)
            
            # 3. Generar respuesta con LLM
            respuesta_content = await self._generar_respuesta_llm(contexto_completo, numero_expediente)
            
            # 4. Parsear respuesta de IA
            resumen_ia = self._parsear_respuesta_ia(respuesta_content)
            
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

    async def _obtener_documentos_expediente(self, numero_expediente: str) -> List[Document]:
        """Obtiene documentos del expediente usando retriever o fallback a BD."""
        try:
            # Estrategia principal: usar retriever
            retriever = JusticIARetriever(top_k=50)
            logger.info("Retriever inicializado correctamente")
            
            query_expediente = f"expediente {numero_expediente} documentos contenido"
            logger.info(f"Query para búsqueda: {query_expediente}")
            
            docs = await retriever._aget_relevant_documents(query_expediente)
            logger.info(f"Documentos obtenidos del retriever: {len(docs)}")
            
            # Filtrar solo documentos de este expediente específico
            # IMPORTANTE: el campo en Milvus es "numero_expediente", no "expediente_numero"
            docs_expediente = [
                doc for doc in docs 
                if doc.metadata.get("numero_expediente") == numero_expediente
            ]
            
            if docs_expediente:
                logger.info(f"Documentos filtrados para expediente {numero_expediente}: {len(docs_expediente)}")
                return docs_expediente
            else:
                logger.warning("No se encontraron documentos en retriever, usando fallback")
                return await self._obtener_documentos_fallback(numero_expediente)
                
        except Exception as e:
            logger.error(f"Error con retriever/Milvus: {e}")
            return await self._obtener_documentos_fallback(numero_expediente)

    async def _obtener_documentos_fallback(self, numero_expediente: str) -> List[Document]:
        """Estrategia de fallback: obtener documentos directamente de la BD."""
        logger.info("Intentando fallback con documento_service")
        
        expediente_data = await self.documento_service.obtener_expediente_completo(
            numero_expediente, incluir_documentos=True
        )
        
        if not expediente_data or not expediente_data.get("documents"):
            raise ValueError(f"No se encontraron documentos para el expediente {numero_expediente}")
        
        # Convertir documentos a formato LangChain Document
        docs = []
        for doc_data in expediente_data["documents"]:
            content = doc_data.get("content_preview", "") or doc_data.get("content", "")
            if content.strip():
                doc = Document(
                    page_content=content,
                    metadata={
                        "numero_expediente": numero_expediente,  # Consistente con Milvus
                        "nombre_archivo": doc_data.get("document_name", ""),
                        "id_documento": doc_data.get("id", ""),
                    }
                )
                docs.append(doc)
        
        logger.info(f"Fallback exitoso: {len(docs)} documentos desde BD")
        return docs

    async def _crear_contexto_resumen(self, docs_expediente: List[Document]) -> str:
        """Crea el contexto optimizado para documentos legales."""
        try:
            contexto_completo = create_similarity_search_context(
                docs_expediente, 
                max_docs=20,  # Más documentos para resumen completo
                max_chars_per_doc=7000  # Más caracteres para documentos legales
            )
            logger.info(f"Contexto creado con {len(contexto_completo)} caracteres")
            return contexto_completo
        except Exception as e:
            logger.error(f"Error creando contexto: {e}")
            raise ValueError(f"Error procesando documentos: {e}")

    async def _generar_respuesta_llm(self, contexto_completo: str, numero_expediente: str) -> str:
        """Genera respuesta usando el LLM."""
        try:
            # Crear prompt especializado
            prompt = create_similarity_summary_prompt(contexto_completo, numero_expediente)
            logger.info("Prompt creado correctamente")
        
            # Obtener LLM 
            llm = await get_llm()
            logger.info("LLM obtenido correctamente")
            
            respuesta_llm = await llm.ainvoke(prompt)
            respuesta_content = getattr(respuesta_llm, "content", str(respuesta_llm))
            logger.info(f"Respuesta del LLM obtenida: {len(respuesta_content)} caracteres")
            
            return respuesta_content
            
        except Exception as e:
            logger.error(f"Error con LLM: {e}")
            raise ValueError(f"Error de conexión con Ollama: {e}")

    def _parsear_respuesta_ia(self, respuesta_raw: str) -> ResumenIA:
        """Parsea la respuesta del LLM y la convierte en objeto ResumenIA."""
        import json
        import re
        
        # Log para debug
        logger.info(f"Respuesta cruda del LLM (primeros 200 chars): {respuesta_raw[:200]}")
        logger.info(f"Respuesta cruda del LLM (últimos 100 chars): {respuesta_raw[-100:]}")
        
        try:
            # Limpiar la respuesta básica
            respuesta_limpia = respuesta_raw.strip()
            
            # Intentar encontrar JSON completo primero
            json_match = re.search(r'\{[^{}]*"resumen"[^{}]*"palabras_clave"[^{}]*"factores_similitud"[^{}]*"conclusion"[^{}]*\}', 
                                 respuesta_limpia, re.DOTALL)
            
            if not json_match:
                # Intentar reparar JSON incompleto
                logger.warning("JSON completo no encontrado, intentando reparar...")
                json_reparado = self._intentar_reparar_json(respuesta_limpia)
                if json_reparado:
                    json_str = json_reparado
                    logger.info(f"JSON extraído/reparado: {json_str}")
                    
                    # Intentar parsear el JSON
                    datos = json.loads(json_str)
                    
                    return ResumenIA(
                        resumen=datos.get("resumen", "No se pudo generar resumen"),
                        palabras_clave=datos.get("palabras_clave", []),
                        factores_similitud=datos.get("factores_similitud", []),
                        conclusion=datos.get("conclusion", "No se pudo generar conclusión")
                    )
                else:
                    logger.warning("No se pudo reparar el JSON")
                    return self._crear_resumen_fallback(respuesta_raw)
            else:
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
                
        except json.JSONDecodeError as e:
            logger.error(f"Error JSON decode: {e}")
            return self._crear_resumen_fallback(respuesta_raw)
        except Exception as e:
            logger.error(f"Error general parseando respuesta IA: {e}")
            return self._crear_resumen_fallback(respuesta_raw)

    def _intentar_reparar_json(self, respuesta: str) -> str:
        """Intenta reparar JSON incompleto añadiendo campos faltantes."""
        import json
        try:
            # Buscar inicio del JSON
            inicio_json = respuesta.find('{')
            if inicio_json == -1:
                return ""
                
            json_parte = respuesta[inicio_json:]
            
            # Verificar si tiene al menos el resumen
            if '"resumen"' not in json_parte:
                return ""
            
            # Intentar cerrar JSON incompleto de forma inteligente
            json_reparado = json_parte
            
            # Si no termina con }, intentar cerrarlo
            if not json_reparado.rstrip().endswith('}'):
                # Contar llaves abiertas vs cerradas
                abiertas = json_reparado.count('{')
                cerradas = json_reparado.count('}')
                
                # Si falta cerrar, agregar campos por defecto y cerrar
                if abiertas > cerradas:
                    # Verificar qué campos faltan y agregarlos
                    if '"palabras_clave"' not in json_reparado:
                        json_reparado += ', "palabras_clave": ["Análisis Legal", "Expediente Judicial", "Procedimiento Legal", "Documentación Oficial", "Proceso Judicial", "Materia Jurídica"]'
                    
                    if '"factores_similitud"' not in json_reparado:
                        json_reparado += ', "factores_similitud": ["Contenido del expediente legal", "Documentación procesal oficial", "Tipo de procedimiento judicial", "Materias jurídicas involucradas", "Contexto procesal específico"]'
                    
                    if '"conclusion"' not in json_reparado:
                        json_reparado += ', "conclusion": "Se requiere análisis manual adicional para conclusiones jurídicas específicas"'
                    
                    # Cerrar JSON
                    json_reparado += '}'
            
            # Verificar que el JSON sea válido
            json.loads(json_reparado)
            logger.info("JSON reparado exitosamente")
            return json_reparado
            
        except Exception as e:
            logger.error(f"Error reparando JSON: {e}")
            return ""
    
    def _crear_resumen_fallback(self, respuesta_raw: str) -> ResumenIA:
        """Crea un resumen de fallback cuando no se puede parsear JSON - optimizado para español."""
        return ResumenIA(
            resumen=respuesta_raw[:600] if respuesta_raw else "No se pudo generar resumen automático del expediente",
            palabras_clave=[
                "Análisis Legal", "Expediente Judicial", "Procedimiento Legal", 
                "Documentación Oficial", "Proceso Judicial", "Materia Jurídica"
            ],
            factores_similitud=[
                "Contenido del expediente legal", 
                "Documentación procesal oficial",
                "Tipo de procedimiento judicial",
                "Materias jurídicas involucradas"
            ],
            conclusion="Se requiere análisis manual adicional para conclusiones jurídicas específicas y recomendaciones legales detalladas"
        )
