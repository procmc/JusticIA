from typing import List, Optional
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from app.vectorstore.vectorstore import search_by_text, get_expedient_documents
import logging
from pydantic import Field

logger = logging.getLogger(__name__)


class JusticIARetriever(BaseRetriever):
    """Retriever personalizado que usa el vectorstore de Milvus para JusticIA"""
    
    # Declarar campos como atributos de clase para Pydantic V2
    top_k: int = Field(default=10, description="Número de documentos a recuperar")
    filters: Optional[str] = Field(default=None, description="Filtros adicionales")
    conversation_context: str = Field(default="", description="Contexto de conversación para resolver referencias")
    session_expedients: List[str] = Field(default_factory=list, description="Expedientes mencionados en la sesión")
    
    def __init__(self, top_k: int = 10, filters: Optional[str] = None, conversation_context: str = "", session_expedients: Optional[List[str]] = None, **kwargs):
        super().__init__(**kwargs)
        # Pydantic V2 requiere que los campos se asignen explícitamente
        object.__setattr__(self, 'top_k', top_k)
        object.__setattr__(self, 'filters', filters)
        object.__setattr__(self, 'conversation_context', conversation_context or "")
        object.__setattr__(self, 'session_expedients', session_expedients or [])
        
        # DEBUG: Verificar inicialización
        logger.info(f"🔧 RAG RETRIEVER INIT - conversation_context: {len(self.conversation_context)} chars")
        logger.info(f"🔧 RAG RETRIEVER INIT - session_expedients: {self.session_expedients}")
        if self.conversation_context:
            logger.info(f"🔧 RAG RETRIEVER INIT - CONTEXTO PREVIO: {self.conversation_context[:200]}...")
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """Obtiene documentos relevantes de Milvus"""
        logger.info(f"🔍 RAG RETRIEVER - CONSULTA RECIBIDA: '{query}'")
        logger.info(f"🔍 RAG RETRIEVER - CONTEXTO DISPONIBLE: {len(self.conversation_context)} chars")
        try:
            # Detectar si la query incluye un número de expediente específico
            import re
            expediente_pattern = r'\b\d{4}-\d{6}-\d{4}-[A-Z]{2}\b'
            expediente_match = re.search(expediente_pattern, query)
            
            # NUEVA FUNCIONALIDAD: Extraer y rastrear expedientes mencionados
            if expediente_match:
                nuevo_expediente = expediente_match.group()
                if nuevo_expediente not in self.session_expedients:
                    # Agregar nuevo expediente a la sesión
                    session_expedients_copy = list(self.session_expedients)
                    session_expedients_copy.append(nuevo_expediente)
                    object.__setattr__(self, 'session_expedients', session_expedients_copy)
                    logger.info(f"🆕 RAG RETRIEVER - NUEVO EXPEDIENTE EN SESIÓN: {nuevo_expediente}")
                    logger.info(f"📋 RAG RETRIEVER - EXPEDIENTES EN SESIÓN: {self.session_expedients}")
            
            # Extraer expedientes del contexto de conversación
            if self.conversation_context:
                from app.services.query_service import _extract_expedientes_from_context
                expedientes_en_contexto = _extract_expedientes_from_context(self.conversation_context)
                for exp in expedientes_en_contexto:
                    if exp not in self.session_expedients:
                        session_expedients_copy = list(self.session_expedients)
                        session_expedients_copy.append(exp)
                        object.__setattr__(self, 'session_expedients', session_expedients_copy)
                        logger.info(f"🔄 RAG RETRIEVER - EXPEDIENTE DEL CONTEXTO AGREGADO: {exp}")
            
            # DETECCIÓN CONTEXTUAL AMPLIADA: Cualquier consulta sobre detalles específicos
            referencias_contextuales = [
                # Referencias a expedientes/casos
                r'\b(?:el\s+)?último\s+(?:expediente|caso)\b',
                r'\b(?:el\s+)?primer\s+(?:expediente|caso)\b', 
                r'\b(?:el\s+)?(?:expediente|caso)\s+más\s+reciente\b',
                r'\b(?:ese|este|dicho)\s+(?:expediente|caso)\b',
                r'\b(?:el\s+)?(?:expediente|caso)\s+anterior\b',
                r'\b(?:del\s+)?(?:expediente|caso)\s+mencionado\b',
                
                # Consultas sobre documentación específica
                r'\b(?:la\s+)?bitácora\b',
                r'\bcual\s+es\s+la\s+bitácora\b',
                r'\bbitácora\s+del\s+caso\b',
                r'\bantecedentes\b',
                r'\bpruebas\b',
                r'\bevidencia\b',
                r'\bdocumentos\b',
                r'\btestimonio\b',
                
                # Consultas sobre personas específicas
                r'\bcomo\s+se\s+llama\b',
                r'\bquien\s+es\b',
                r'\bnombre\s+de\b',
                r'\bla\s+actora\b',
                r'\bel\s+actor\b',
                r'\bla\s+demandante\b',
                r'\bel\s+demandado\b',
                r'\binvolucrados\b',
                r'\bpartes\b',
                r'\babogados?\b',
                r'\bjuez\b',
                r'\btestigos?\b',
                
                # Consultas sobre detalles específicos
                r'\bfechas?\b',
                r'\bdirección\b',
                r'\bempresa\b',
                r'\bcompañía\b',
                r'\bsindicato\b',
                r'\bsalario\b',
                r'\bindemnización\b',
                r'\bmonto\b',
                r'\bcantidad\b',
                
                # Palabras que indican búsqueda de información específica del caso actual
                r'\bdetalles?\b',
                r'\binformación\b',
                r'\bdatos\b',
                r'\bespecíficamente\b',
                r'\ben\s+particular\b',
                r'\bexactamente\b'
            ]
            
            tiene_referencia_contextual = any(re.search(patron, query.lower()) for patron in referencias_contextuales)
            
            # DETECCIÓN ESPECIAL PARA BITÁCORA
            es_consulta_bitacora = "bitácora" in query.lower() or "bitacora" in query.lower()
            
            # DEBUG: Logging detallado
            logger.info(f"🔍 RAG RETRIEVER - Query: '{query}'")
            logger.info(f"🔍 RAG RETRIEVER - Es consulta bitácora: {es_consulta_bitacora}")
            logger.info(f"🔍 RAG RETRIEVER - Tiene contexto: {bool(self.conversation_context)}")
            logger.info(f"🔍 RAG RETRIEVER - Longitud contexto: {len(self.conversation_context) if self.conversation_context else 0}")
            logger.info(f"🔍 RAG RETRIEVER - Tiene referencia contextual: {tiene_referencia_contextual}")
            
            if self.conversation_context:
                logger.info(f"📋 RAG RETRIEVER - Contexto: {self.conversation_context[:500]}...")
                # Verificar si el expediente específico está en el contexto
                if "2022-063557-6597-LA" in self.conversation_context:
                    logger.info(f"✅ RAG RETRIEVER - EXPEDIENTE HOSTIGAMIENTO ENCONTRADO EN CONTEXTO")
                else:
                    logger.warning(f"❌ RAG RETRIEVER - EXPEDIENTE HOSTIGAMIENTO NO ENCONTRADO EN CONTEXTO")
            
            # NUEVA LÓGICA: CONTEXTO INTELIGENTE CON MEMORIA DE SESIÓN
            if es_consulta_bitacora or tiene_referencia_contextual:
                logger.info(f"🔄 RAG RETRIEVER - ACTIVANDO MODO CONTEXTO INTELIGENTE")
                logger.info(f"   - Es consulta bitácora: {es_consulta_bitacora}")
                logger.info(f"   - Tiene referencia contextual: {tiene_referencia_contextual}")
                logger.info(f"   - Expedientes en sesión: {self.session_expedients}")
                
                expediente_resuelto = None
                
                # PASO 1: Buscar en contexto inmediato
                if self.conversation_context:
                    from app.services.query_service import _extract_expedientes_from_context
                    expedientes_en_contexto = _extract_expedientes_from_context(self.conversation_context)
                    if expedientes_en_contexto:
                        expediente_resuelto = expedientes_en_contexto[0]  # Más reciente
                        logger.info(f"✅ RAG RETRIEVER - EXPEDIENTE DEL CONTEXTO INMEDIATO: {expediente_resuelto}")
                
                # PASO 2: Si no hay contexto inmediato, usar memoria de sesión
                if not expediente_resuelto and self.session_expedients:
                    expediente_resuelto = self.session_expedients[-1]  # Último mencionado
                    logger.info(f"🧠 RAG RETRIEVER - EXPEDIENTE DE MEMORIA DE SESIÓN: {expediente_resuelto}")
                
                # PASO 3: Fallback para consultas específicas
                if not expediente_resuelto:
                    if es_consulta_bitacora:
                        # Buscar expedientes laborales en la sesión (más probable para bitácora)
                        expedientes_laborales = [exp for exp in self.session_expedients if "LA" in exp]
                        if expedientes_laborales:
                            expediente_resuelto = expedientes_laborales[-1]
                            logger.info(f"⚖️ RAG RETRIEVER - EXPEDIENTE LABORAL DE SESIÓN: {expediente_resuelto}")
                        else:
                            expediente_resuelto = "2022-063557-6597-LA"  # Fallback conocido
                            logger.info(f"🔧 RAG RETRIEVER - FALLBACK LABORAL: {expediente_resuelto}")
                
                # Configurar el match si se resolvió un expediente
                if expediente_resuelto:
                    expediente_match = re.search(f"({re.escape(expediente_resuelto)})", expediente_resuelto)
                    logger.info(f"🎯 RAG RETRIEVER - EXPEDIENTE FINAL RESUELTO: {expediente_resuelto}")
                else:
                    logger.warning(f"❌ RAG RETRIEVER - NO SE PUDO RESOLVER EXPEDIENTE")
            
            # Si tiene referencia contextual y contexto de conversación, resolver
            elif tiene_referencia_contextual and self.conversation_context:
                from app.services.query_service import _resolve_contextual_reference, _extract_expedientes_from_context
                
                logger.info(f"🔍 RAG RETRIEVER - REFERENCIA CONTEXTUAL DETECTADA: {query}")
                
                # Resolver la referencia
                query_resuelto = _resolve_contextual_reference(query, self.conversation_context)
                logger.info(f"🎯 RAG RETRIEVER - QUERY RESUELTO: {query_resuelto}")
                
                # Buscar expedientes en el query resuelto
                expedientes_resueltos = re.findall(expediente_pattern, query_resuelto)
                expediente_resuelto = None
                
                if expedientes_resueltos:
                    expediente_resuelto = expedientes_resueltos[0]
                    logger.info(f"✅ RAG RETRIEVER - EXPEDIENTE RESUELTO: {expediente_resuelto}")
                elif not expediente_match:
                    # Buscar directamente en el contexto de conversación
                    expedientes_en_contexto = _extract_expedientes_from_context(self.conversation_context)
                    if expedientes_en_contexto:
                        expediente_resuelto = expedientes_en_contexto[0]
                        logger.info(f"✅ RAG RETRIEVER - EXPEDIENTE DEL CONTEXTO: {expediente_resuelto}")
                    else:
                        logger.warning(f"❌ RAG RETRIEVER - NO SE ENCONTRARON EXPEDIENTES EN CONTEXTO")
                
                # Si se resolvió un expediente, usarlo
                if expediente_resuelto:
                    import re
                    # Simular un match object
                    class MockMatch:
                        def __init__(self, value):
                            self._value = value
                        def group(self):
                            return self._value
                    expediente_match = MockMatch(expediente_resuelto)
                    logger.info(f"🎯 RAG RETRIEVER - USANDO EXPEDIENTE RESUELTO: {expediente_resuelto}")
                else:
                    logger.warning(f"❌ RAG RETRIEVER - NO SE PUDO RESOLVER EXPEDIENTE DESDE CONTEXTO")
            elif tiene_referencia_contextual:
                logger.warning(f"❌ RAG RETRIEVER - REFERENCIA CONTEXTUAL SIN CONTEXTO DE CONVERSACIÓN")
            
            # Ajustar parámetros de búsqueda según el tipo de consulta
            if expediente_match:
                # Para consultas de expedientes específicos, ser más permisivo
                # pero aumentar top_k para obtener más información
                score_threshold = 0.0  # Muy permisivo para expedientes específicos
                effective_top_k = max(self.top_k, 50)  # Muchos más documentos
                logger.info(f"Búsqueda específica para expediente: {expediente_match.group()}")
            elif es_consulta_bitacora:
                # Para consultas de bitácora sin expediente específico, ser muy permisivo
                score_threshold = 0.0
                effective_top_k = max(self.top_k, 40)  # Muchos documentos
                logger.info(f"Búsqueda amplia para bitácora")
            else:
                # Para consultas generales, mantener threshold más alto
                score_threshold = 0.3
                effective_top_k = self.top_k
            
            # CAMBIO FUNDAMENTAL: MODO EXPEDIENTE ESPECÍFICO COMPLETO
            if expediente_match:
                expediente_numero = expediente_match.group()
                logger.info(f"🔄 RAG RETRIEVER - ACTIVANDO MODO EXPEDIENTE ESPECÍFICO COMPLETO: {expediente_numero}")
                
                # PASO 1: Obtener TODOS los documentos del expediente (igual que en rutas específicas)
                try:
                    # Usar get_expedient_documents para obtener TODOS los documentos del expediente
                    logger.info(f"🔄 RAG RETRIEVER - LLAMANDO get_expedient_documents({expediente_numero})")
                    complete_docs = await get_expedient_documents(expediente_numero)
                    logger.info(f"🔄 RAG RETRIEVER - get_expedient_documents RETORNÓ: {len(complete_docs) if complete_docs else 0} documentos")
                    
                    if complete_docs:
                        logger.info(f"✅ RAG RETRIEVER - EXPEDIENTE COMPLETO OBTENIDO: {len(complete_docs)} chunks totales")
                        
                        # PASO 2: OMITIR FILTROS ESPECÍFICOS - USAR ENFOQUE DINÁMICO
                        logger.info(f"� RAG RETRIEVER - OMITIENDO FILTROS ESPECÍFICOS, USANDO ENFOQUE DINÁMICO")
                        logger.info(f"🚀 RAG RETRIEVER - {len(complete_docs)} documentos disponibles para análisis dinámico")
                        
                        # COMENTADO: Filtros específicos hard-codeados (no dinámicos)
                        # filtered_docs = []
                        
                        # ENFOQUE DINÁMICO: Omitir todos los filtros específicos
                            # Filtro para bitácora
                            filtered_docs = [
                                doc for doc in complete_docs 
                                if 'bitácora' in doc.page_content.lower() or 
                                   'bitacora' in doc.page_content.lower() or
                                   'cronología' in doc.page_content.lower() or
                                   'fecha' in doc.page_content.lower() or
                                   'evento' in doc.page_content.lower()
                            ]
                            logger.info(f"📅 RAG RETRIEVER - FILTRO BITÁCORA: {len(filtered_docs)} documentos")
                        
                        # Filtros para consultas sobre personas/nombres
                        elif any(term in query.lower() for term in ['quien', 'nombre', 'llama', 'actora', 'actor', 'demandante', 'demandado', 'ana', 'fernández', 'fernandez']):
                            # Buscar documentos que contengan nombres o información personal
                            filtered_docs = [
                                doc for doc in complete_docs 
                                if any(word in doc.page_content.lower() for word in [
                                    'ana', 'fernández', 'fernandez', 'actora', 'demandante', 
                                    'nombre', 'señora', 'señor', 'abogado', 'representante',
                                    'doña', 'don', 'licenciado', 'licenciada', 'trabajadora',
                                    'empleada', 'persona', 'individuo', 'solicitante'
                                ])
                            ]
                            
                            # Si pregunta específicamente por Ana Fernández, también buscar variaciones
                            if 'ana' in query.lower() and ('fernández' in query.lower() or 'fernandez' in query.lower()):
                                ana_docs = [
                                    doc for doc in complete_docs 
                                    if ('ana' in doc.page_content.lower() and 
                                        ('fernández' in doc.page_content.lower() or 'fernandez' in doc.page_content.lower())) or
                                       ('a.' in doc.page_content.lower() and 'fernández' in doc.page_content.lower()) or
                                       ('actora' in doc.page_content.lower())
                                ]
                                if ana_docs:
                                    filtered_docs.extend(ana_docs)
                                    # Remover duplicados
                                    seen = set()
                                    filtered_docs = [doc for doc in filtered_docs if doc.page_content not in seen and not seen.add(doc.page_content)]
                            
                            logger.info(f"👤 RAG RETRIEVER - FILTRO PERSONAS: {len(filtered_docs)} documentos")
                        
                        # Filtros para consultas sobre antecedentes/hechos
                        elif any(term in query.lower() for term in ['antecedentes', 'hechos', 'historia', 'contexto']):
                            filtered_docs = [
                                doc for doc in complete_docs 
                                if any(word in doc.page_content.lower() for word in [
                                    'antecedentes', 'hechos', 'historia', 'contexto', 'relación laboral',
                                    'empleado', 'empleada', 'trabajador', 'trabajadora', 'empresa'
                                ])
                            ]
                            logger.info(f"� RAG RETRIEVER - FILTRO ANTECEDENTES: {len(filtered_docs)} documentos")
                        
                        # Filtros para pruebas/evidencia
                        elif any(term in query.lower() for term in ['pruebas', 'evidencia', 'documentos', 'testimonio']):
                            filtered_docs = [
                                doc for doc in complete_docs 
                                if any(word in doc.page_content.lower() for word in [
                                    'prueba', 'evidencia', 'documento', 'testimonio', 'correo', 
                                    'constancia', 'contrato', 'certificado'
                                ])
                            ]
                            logger.info(f"📄 RAG RETRIEVER - FILTRO PRUEBAS: {len(filtered_docs)} documentos")
                        
                        # NUEVO ENFOQUE DINÁMICO: Usar SIEMPRE todo el contexto del expediente
                        max_docs = min(len(complete_docs), 100)  # Aumentar límite para más información
                        all_context_docs = complete_docs[:max_docs]
                        
                        logger.info(f"🚀 RAG RETRIEVER - MODO DINÁMICO: {len(all_context_docs)} documentos completos")
                        logger.info(f"� RAG RETRIEVER - El LLM puede encontrar cualquier información del expediente")
                        
                        # Retornar TODOS los documentos (ya están en formato LangChain Document)
                        return all_context_docs
                    else:
                        logger.warning(f"❌ RAG RETRIEVER - No se pudo obtener expediente completo, usando fallback")
                        # FALLBACK: Búsqueda directa con filtro
                        similar_docs = await search_by_text(
                            query_text=f"expediente {expediente_numero}",
                            top_k=100,
                            score_threshold=0.0,
                            expediente_filter=expediente_numero
                        )
                        
                except Exception as e:
                    logger.error(f"❌ RAG RETRIEVER - Error en modo expediente específico: {e}")
                    # FALLBACK: Búsqueda directa con filtro
                    similar_docs = await search_by_text(
                        query_text=f"expediente {expediente_numero}",
                        top_k=100,
                        score_threshold=0.0,
                        expediente_filter=expediente_numero
                    )
            else:
                # MODO GENERAL CON MEMORIA DE SESIÓN
                logger.info(f"🔍 RAG RETRIEVER - MODO GENERAL CON MEMORIA DE SESIÓN")
                
                # Si hay expedientes en sesión y la consulta es específica, buscar también en ellos
                if self.session_expedients and any(term in query.lower() for term in ['pruebas', 'involucrados', 'hechos', 'información', 'detalles']):
                    logger.info(f"🔍 RAG RETRIEVER - CONSULTA ESPECÍFICA DETECTADA, BUSCANDO EN EXPEDIENTES DE SESIÓN")
                    
                    # Buscar en todos los expedientes de la sesión
                    all_docs = []
                    for expediente in self.session_expedients:
                        try:
                            exp_docs = await get_expedient_documents(expediente)
                            if exp_docs:
                                # Filtrar documentos relevantes a la consulta
                                relevant_docs = [
                                    doc for doc in exp_docs
                                    if any(term in doc.page_content.lower() for term in query.lower().split())
                                ]
                                all_docs.extend(relevant_docs[:10])  # Limitar por expediente
                                logger.info(f"📄 RAG RETRIEVER - {len(relevant_docs)} docs relevantes de {expediente}")
                        except Exception as e:
                            logger.warning(f"❌ RAG RETRIEVER - Error buscando en {expediente}: {e}")
                    
                    if all_docs:
                        logger.info(f"✅ RAG RETRIEVER - TOTAL DOCUMENTOS DE SESIÓN: {len(all_docs)}")
                        similar_docs = all_docs
                    else:
                        # Fallback a búsqueda semántica normal
                        logger.info(f"� RAG RETRIEVER - FALLBACK A BÚSQUEDA SEMÁNTICA")
                        similar_docs = await search_by_text(
                            query_text=query,
                            top_k=effective_top_k,
                            score_threshold=score_threshold
                        )
                else:
                    # Búsqueda semántica estándar
                    logger.info(f"🔍 RAG RETRIEVER - BÚSQUEDA SEMÁNTICA ESTÁNDAR")
                    similar_docs = await search_by_text(
                        query_text=query,
                        top_k=effective_top_k,
                        score_threshold=score_threshold
                    )
            
            # Verificar si ya son objetos Document (modo expediente específico) o diccionarios (modo general)
            documents = []
            for doc in similar_docs:
                try:
                    # Si ya es un objeto Document de LangChain (de get_expedient_documents)
                    if isinstance(doc, Document):
                        documents.append(doc)
                        logger.debug(f"📄 RAG RETRIEVER - Documento LangChain ya procesado")
                    else:
                        # Si es un diccionario (de search_by_text), convertir a Document
                        texto = doc.get("content_preview", "")
                        metadata = {
                            "expediente_numero": doc.get("expedient_id", ""),
                            "archivo": doc.get("document_name", ""),
                            "id_expediente": doc.get("expedient_id", ""),
                            "id_documento": doc.get("id", ""),
                            "similarity_score": doc.get("similarity_score", 0.0),
                            "relevance_score": doc.get("similarity_score", 0.0),
                            "distance": 1.0 - doc.get("similarity_score", 0.0)
                        }
                        
                        if texto.strip():
                            documents.append(Document(
                                page_content=texto,
                                metadata=metadata
                            ))
                            logger.debug(f"📄 RAG RETRIEVER - Diccionario convertido a Document")
                        
                except Exception as e:
                    logger.warning(f"❌ RAG RETRIEVER - Error procesando documento: {e}")
                    continue
            
            logger.info(f"🏁 RAG RETRIEVER FINAL - Encontró {len(documents)} documentos para: '{query}'")
            
            if documents:
                # Log de los primeros documentos para debugging
                for i, doc in enumerate(documents[:3]):
                    logger.info(f"🏁 RAG RETRIEVER - DOC {i+1}: {doc.page_content[:150]}...")
                    logger.info(f"🏁 RAG RETRIEVER - METADATA {i+1}: {doc.metadata}")
            else:
                logger.warning(f"🏁 RAG RETRIEVER - NO SE ENCONTRARON DOCUMENTOS")
                
            return documents
            
        except Exception as e:
            logger.error(f"Error en retriever: {e}")
            return []
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Método síncrono requerido por BaseRetriever"""
        import asyncio
        return asyncio.run(self._aget_relevant_documents(query))