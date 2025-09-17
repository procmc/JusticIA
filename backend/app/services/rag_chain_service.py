from typing import List, Dict, Any, Optional, Union
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_ollama import ChatOllama
from app.embeddings.embeddings import get_embedding
from app.vectorstore.vectorstore import search_by_text, search_by_vector
from app.llm.llm_service import get_llm
from app.config.config import COLLECTION_NAME
import logging

logger = logging.getLogger(__name__)

class JusticIARetriever(BaseRetriever):
    """Retriever personalizado que usa tu vectorstore de Milvus"""
    
    def __init__(self, top_k: int = 10, filters: Optional[str] = None):
        super().__init__()
        self.top_k = top_k
        self.filters = filters
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """Obtiene documentos relevantes de Milvus"""
        try:
            # Usar la nueva función de búsqueda del vectorstore central
            similar_docs = await search_by_text(
                query_text=query,
                top_k=self.top_k,
                score_threshold=0.0
            )
            
            # Convertir a formato LangChain Document
            documents = []
            for doc in similar_docs:
                try:
                    # Usar el nuevo formato del vectorstore central
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
                        
                except Exception as e:
                    logger.warning(f"Error procesando documento: {e}")
                    continue
            
            logger.info(f"Retriever encontró {len(documents)} documentos para: {query}")
            return documents
            
        except Exception as e:
            logger.error(f"Error en retriever: {e}")
            return []
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Método síncrono requerido por BaseRetriever"""
        import asyncio
        return asyncio.run(self._aget_relevant_documents(query))


class RAGChainService:
    """Servicio principal de RAG Chain para JusticIA"""
    
    def __init__(self):
        self.retriever = None
        self.llm: Optional[ChatOllama] = None
        self.qa_chain = None
        self._setup_prompts()
    
    def _setup_prompts(self):
        """Configura los prompts especializados para consultas legales"""
        
        # Prompt para consultas generales
        self.general_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un asistente legal interno especializado en analizar ÚNICAMENTE los expedientes de este despacho jurídico.

RESTRICCIONES ESTRICTAS:
- SOLO puedes usar información que aparezca en los expedientes proporcionados
- NUNCA hagas referencia a leyes, jurisprudencia o fuentes externas
- NUNCA recomiendes consultar fuentes externas o bases de datos públicas
- NO menciones legislación general ni códigos legales
- Si no tienes información suficiente en los expedientes, indica claramente que la consulta requiere revisar más documentos del despacho

FORMATO DE RESPUESTA REQUERIDO:
- Usa **texto en negrita** para números de expediente, materias importantes, fechas y nombres de juzgados
- Agrega líneas de separación (---) entre diferentes expedientes
- Estructura la información claramente con espacios y saltos de línea
- Usa bullet points (- ) para enumerar detalles importantes
- Mantén párrafos separados con doble salto de línea

Tu trabajo es:
1. Analizar ÚNICAMENTE la información de los expedientes internos proporcionados
2. Responder basándote EXCLUSIVAMENTE en los documentos de este despacho
3. Citar SOLAMENTE expedientes y documentos internos específicos
4. Estructurar la respuesta de forma clara y legible
5. Si falta información, sugerir revisar otros expedientes internos relacionados

IMPORTANTE - SISTEMA PRIVADO:
- Este es un sistema interno y confidencial
- Toda la información debe provenir de los expedientes del despacho
- Mantén la confidencialidad y privacidad de la información
- No hagas referencias a fuentes externas o públicas"""),
            
            ("human", """Expedientes internos del despacho:
{context}

Pregunta: {question}

IMPORTANTE: Responde ÚNICAMENTE basándote en los expedientes internos mostrados arriba. Si no hay información suficiente en estos expedientes específicos, indica que se necesita revisar más documentos internos del despacho. NO menciones fuentes externas.""")
        ])
        
        # Prompt para análisis de expedientes específicos
        self.expediente_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un asistente legal interno especializado en análisis de expedientes del despacho.

SISTEMA PRIVADO - RESTRICCIONES:
- SOLO analiza información de los expedientes internos proporcionados
- NUNCA menciones leyes, códigos o jurisprudencia externa
- NO recomiendes consultar fuentes externas
- Mantén toda la información confidencial dentro del despacho

FORMATO DE RESPUESTA REQUERIDO:
- Usa **texto en negrita** para números de expediente, materias importantes, fechas y nombres de juzgados
- Estructura la información claramente con espacios y saltos de línea
- Usa bullet points (- ) para enumerar detalles importantes
- Mantén párrafos separados con doble salto de línea

Analiza el expediente interno proporcionado y responde de manera estructurada:
1. Resumen del caso basado en documentos internos
2. Partes involucradas según los documentos del expediente
3. Estado procesal actual según actuaciones registradas
4. Documentos principales disponibles en el expediente
5. Próximas actuaciones mencionadas en los documentos

Usa terminología jurídica precisa pero basa todo en los documentos internos del despacho."""),
            
            ("human", """Información del expediente interno {expediente_numero}:
{context}

Pregunta específica: {question}

RECORDATORIO: Responde basándote ÚNICAMENTE en los documentos internos del expediente mostrados arriba. No menciones leyes externas o fuentes públicas.""")
        ])
        
        # Prompt para búsqueda de similitudes
        self.similarity_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un asistente legal interno especializado en encontrar casos similares dentro del despacho.

SISTEMA PRIVADO - RESTRICCIONES ESTRICTAS:
- SOLO analiza expedientes internos del despacho proporcionados
- NUNCA menciones jurisprudencia externa o casos públicos
- NO recomiendes consultar bases de datos externas
- Mantén toda la información confidencial dentro del despacho

FORMATO DE RESPUESTA REQUERIDO:
- Usa **texto en negrita** para números de expediente, materias importantes, fechas y nombres de juzgados
- Agrega líneas de separación (---) entre diferentes expedientes
- Estructura la información claramente con espacios y saltos de línea
- Usa bullet points (- ) para enumerar detalles importantes
- Mantén párrafos separados con doble salto de línea

Analiza los expedientes internos proporcionados y:
1. Identifica similitudes en cuanto a materia y hechos según documentos internos
2. Destaca diferencias relevantes entre los casos del despacho
3. Sugiere expedientes del despacho que podrían servir como precedente interno
4. Proporciona un ranking de similitud basado en los documentos internos

Enfócate en aspectos jurídicos relevantes como tipo de proceso, materias involucradas, y procedimientos similares, todo basado en la experiencia interna del despacho."""),
            
            ("human", """Expedientes internos del despacho encontrados:
{context}

Caso de referencia: {question}

IMPORTANTE: Analiza ÚNICAMENTE las similitudes y diferencias entre los expedientes internos del despacho mostrados arriba. Proporciona recomendaciones basadas exclusivamente en la experiencia interna del despacho. No menciones casos externos o jurisprudencia pública.""")
        ])
    
    async def _initialize_components(self):
        """Inicializa los componentes necesarios"""
        if not self.llm:
            self.llm = await get_llm()
    
    async def consulta_general(self, pregunta: str, top_k: int = 15) -> Dict[str, Any]:
        """Consulta general en todos los expedientes usando RAG Chain"""
        try:
            await self._initialize_components()
            
            # Crear retriever para búsqueda general
            retriever = JusticIARetriever(top_k=top_k)
            
            # Obtener documentos relevantes
            docs = await retriever._aget_relevant_documents(pregunta)
            
            if not docs:
                return {
                    "respuesta": "No se encontró información relevante en la base de datos para responder tu consulta.",
                    "expedientes_consultados": 0,
                    "fuentes": []
                }
            
            # Preparar contexto para el LLM
            context = self._format_context(docs)
            
            # Asegurar que el LLM esté inicializado
            if not self.llm:
                await self._initialize_components()
            
            # Crear prompt manual para evitar problemas de tipos
            prompt_text = f"""Eres un asistente legal interno especializado en analizar ÚNICAMENTE los expedientes de este despacho jurídico.

RESTRICCIONES ESTRICTAS:
- SOLO puedes usar información que aparezca en los expedientes proporcionados
- NUNCA hagas referencia a leyes, jurisprudencia o fuentes externas
- NUNCA recomiendes consultar fuentes externas o bases de datos públicas
- NO menciones legislación general ni códigos legales
- Si no tienes información suficiente en los expedientes, indica claramente que la consulta requiere revisar más documentos del despacho

FORMATO DE RESPUESTA REQUERIDO:
- Usa **texto en negrita** para números de expediente, materias importantes, fechas y nombres de juzgados
- Agrega líneas de separación (---) entre diferentes expedientes cuando listés múltiples casos
- Estructura la información claramente con espacios y saltos de línea
- Usa bullet points (- ) para enumerar detalles importantes
- Mantén párrafos separados con doble salto de línea

IMPORTANTE - SISTEMA PRIVADO:
- Este es un sistema interno y confidencial
- Toda la información debe provenir de los expedientes del despacho
- Mantén la confidencialidad y privacidad de la información
- No hagas referencias a fuentes externas o públicas

Expedientes internos del despacho:
{context}

Pregunta: {pregunta}

IMPORTANTE: Responde ÚNICAMENTE basándote en los expedientes internos mostrados arriba. Si no hay información suficiente en estos expedientes específicos, indica que se necesita revisar más documentos internos del despacho. NO menciones fuentes externas."""
            
            # Ejecutar LLM directamente con verificación
            if self.llm is None:
                raise Exception("LLM no inicializado correctamente")
            
            respuesta_raw = await self.llm.ainvoke(prompt_text)
            respuesta = getattr(respuesta_raw, "content", str(respuesta_raw))
            
            # Preparar metadatos de respuesta
            expedientes_unicos = list(set([
                doc.metadata.get("expediente_numero", "")
                for doc in docs
                if doc.metadata.get("expediente_numero")
            ]))
            
            fuentes = self._extract_sources(docs)
            
            return {
                "respuesta": respuesta,
                "expedientes_consultados": len(expedientes_unicos),
                "expedientes": expedientes_unicos,
                "fuentes": fuentes,
                "total_documentos": len(docs)
            }
            
        except Exception as e:
            logger.error(f"Error en consulta general RAG: {e}")
            return {
                "error": f"Error procesando consulta: {str(e)}",
                "respuesta": "Hubo un error al procesar tu consulta. Por favor intenta nuevamente."
            }
    
    async def consulta_expediente(self, pregunta: str, expediente_numero: str, top_k: int = 10) -> Dict[str, Any]:
        """Consulta específica sobre un expediente usando RAG Chain"""
        try:
            await self._initialize_components()
            
            # Crear filtro para expediente específico
            filtro_expediente = f'numero_expediente == "{expediente_numero}"'
            retriever = JusticIARetriever(top_k=top_k, filters=filtro_expediente)
            
            # Obtener documentos del expediente
            docs = await retriever._aget_relevant_documents(pregunta)
            
            if not docs:
                return {
                    "respuesta": f"No se encontró información para el expediente {expediente_numero}.",
                    "expediente": expediente_numero,
                    "fuentes": []
                }
            
            # Preparar contexto
            context = self._format_context(docs)
            
            # Asegurar que el LLM esté inicializado
            if not self.llm:
                await self._initialize_components()
            
            # Crear prompt manual
            prompt_text = f"""Eres un asistente legal interno especializado en análisis de expedientes del despacho.

SISTEMA PRIVADO - RESTRICCIONES:
- SOLO analiza información de los expedientes internos proporcionados
- NUNCA menciones leyes, códigos o jurisprudencia externa
- NO recomiendes consultar fuentes externas
- Mantén toda la información confidencial dentro del despacho

FORMATO DE RESPUESTA REQUERIDO:
- Usa **texto en negrita** para números de expediente, materias importantes, fechas y nombres de juzgados
- Estructura la información claramente con espacios y saltos de línea
- Usa bullet points (- ) para enumerar detalles importantes
- Mantén párrafos separados con doble salto de línea

Analiza el expediente interno proporcionado y responde de manera estructurada:
1. Resumen del caso basado en documentos internos
2. Partes involucradas según los documentos del expediente
3. Estado procesal actual según actuaciones registradas
4. Documentos principales disponibles en el expediente
5. Próximas actuaciones mencionadas en los documentos

Información del expediente interno {expediente_numero}:
{context}

Pregunta específica: {pregunta}

RECORDATORIO: Responde basándote ÚNICAMENTE en los documentos internos del expediente mostrados arriba. No menciones leyes externas o fuentes públicas."""
            
            # Ejecutar LLM directamente
            if self.llm is None:
                raise Exception("LLM no inicializado correctamente")
                
            respuesta_raw = await self.llm.ainvoke(prompt_text)
            respuesta = getattr(respuesta_raw, "content", str(respuesta_raw))
            fuentes = self._extract_sources(docs)
            
            return {
                "respuesta": respuesta,
                "expediente": expediente_numero,
                "fuentes": fuentes,
                "documentos_analizados": len(docs)
            }
            
        except Exception as e:
            logger.error(f"Error en consulta expediente RAG: {e}")
            return {
                "error": f"Error consultando expediente: {str(e)}",
                "respuesta": "Hubo un error al consultar el expediente. Por favor intenta nuevamente."
            }
    
    async def buscar_casos_similares(self, descripcion_caso: str, expediente_excluir: Optional[str] = None, top_k: int = 20) -> Dict[str, Any]:
        """Busca casos similares usando RAG Chain"""
        try:
            await self._initialize_components()
            
            # Crear filtro para excluir expediente actual si se especifica
            filtros = None
            if expediente_excluir:
                filtros = f'numero_expediente != "{expediente_excluir}"'
            
            retriever = JusticIARetriever(top_k=top_k, filters=filtros)
            
            # Buscar documentos similares
            docs = await retriever._aget_relevant_documents(descripcion_caso)
            
            if not docs:
                return {
                    "respuesta": "No se encontraron casos similares.",
                    "casos_similares": [],
                    "total_casos": 0
                }
            
            # Agrupar por expediente y calcular relevancia
            casos_similares = self._group_by_expediente(docs)
            
            # Preparar contexto para análisis
            context = self._format_context(docs)
            
            # Asegurar que el LLM esté inicializado
            if not self.llm:
                await self._initialize_components()
            
            # Crear prompt manual
            prompt_text = f"""Eres un asistente legal interno especializado en encontrar casos similares dentro del despacho.

SISTEMA PRIVADO - RESTRICCIONES ESTRICTAS:
- SOLO analiza expedientes internos del despacho proporcionados
- NUNCA menciones jurisprudencia externa o casos públicos
- NO recomiendes consultar bases de datos externas
- Mantén toda la información confidencial dentro del despacho

Analiza los expedientes internos proporcionados y:
1. Identifica similitudes en cuanto a materia y hechos según documentos internos
2. Destaca diferencias relevantes entre los casos del despacho
3. Sugiere expedientes del despacho que podrían servir como precedente interno
4. Proporciona un ranking de similitud basado en los documentos internos

Expedientes internos del despacho encontrados:
{context}

Caso de referencia: {descripcion_caso}

IMPORTANTE: Analiza ÚNICAMENTE las similitudes y diferencias entre los expedientes internos del despacho mostrados arriba. Proporciona recomendaciones basadas exclusivamente en la experiencia interna del despacho. No menciones casos externos o jurisprudencia pública."""
            
            # Ejecutar LLM directamente
            if self.llm is None:
                raise Exception("LLM no inicializado correctamente")
                
            analisis_raw = await self.llm.ainvoke(prompt_text)
            analisis = getattr(analisis_raw, "content", str(analisis_raw))
            
            return {
                "respuesta": analisis,
                "casos_similares": casos_similares[:10],  # Top 10
                "total_casos": len(casos_similares),
                "descripcion_busqueda": descripcion_caso
            }
            
        except Exception as e:
            logger.error(f"Error en búsqueda de similares RAG: {e}")
            return {
                "error": f"Error buscando casos similares: {str(e)}",
                "respuesta": "Hubo un error al buscar casos similares."
            }
    
    def _format_context(self, docs: List[Document]) -> str:
        """Formatea documentos para el contexto del LLM"""
        if not docs:
            return "No hay información disponible."
        
        context_parts = []
        for i, doc in enumerate(docs, 1):
            expediente = doc.metadata.get("expediente_numero", "N/A")
            archivo = doc.metadata.get("archivo", "N/A")
            relevancia = doc.metadata.get("relevance_score", 0)
            
            context_parts.append(
                f"--- Documento {i} ---\n"
                f"Expediente: {expediente}\n"
                f"Archivo: {archivo}\n"
                f"Relevancia: {relevancia:.2f}\n"
                f"Contenido:\n{doc.page_content}\n"
            )
        
        return "\n\n".join(context_parts)
    
    def _extract_sources(self, docs: List[Document]) -> List[Dict[str, Any]]:
        """Extrae información de fuentes de los documentos"""
        fuentes = []
        for doc in docs:
            fuente = {
                "expediente": doc.metadata.get("expediente_numero", ""),
                "archivo": doc.metadata.get("archivo", ""),
                "relevancia": doc.metadata.get("relevance_score", 0),
                "fragmento": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            }
            fuentes.append(fuente)
        return fuentes
    
    def _group_by_expediente(self, docs: List[Document]) -> List[Dict[str, Any]]:
        """Agrupa documentos por expediente y calcula relevancia total"""
        expedientes = {}
        
        for doc in docs:
            exp_num = doc.metadata.get("expediente_numero", "")
            if not exp_num:
                continue
                
            if exp_num not in expedientes:
                expedientes[exp_num] = {
                    "expediente": exp_num,
                    "relevancia_total": 0,
                    "documentos": [],
                    "resumen_fragmentos": []
                }
            
            relevancia = doc.metadata.get("relevance_score", 0)
            expedientes[exp_num]["relevancia_total"] += relevancia
            expedientes[exp_num]["documentos"].append(doc.metadata.get("archivo", ""))
            
            # Agregar fragmento de texto si es relevante
            if len(doc.page_content) > 50:
                fragmento = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
                expedientes[exp_num]["resumen_fragmentos"].append(fragmento)
        
        # Ordenar por relevancia total
        casos_ordenados = sorted(
            expedientes.values(),
            key=lambda x: x["relevancia_total"],
            reverse=True
        )
        
        return casos_ordenados


# Instancia global del servicio
_rag_service = None

async def get_rag_service() -> RAGChainService:
    """Dependency para obtener el servicio RAG"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGChainService()
    return _rag_service