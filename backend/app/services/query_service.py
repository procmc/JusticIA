from typing import List, Dict, Any
from app.embeddings.embeddings import get_embedding
from app.llm.llm_service import consulta_simple, consulta_general_streaming
from app.vectorstore.vectorstore import search_by_vector, search_by_text
import os
import re

def is_greeting_or_simple_conversation(query: str) -> bool:
    """
    Detecta si la consulta es un saludo o conversación simple que no requiere búsqueda en expedientes.
    
    Args:
        query: Consulta del usuario
        
    Returns:
        True si es un saludo/conversación simple, False si es una consulta legal
    """
    query_lower = query.lower().strip()
    
    # Patrones de saludos y conversación simple
    greeting_patterns = [
        r'^(hola|hello|hi|buenos días|buenas tardes|buenas noches|saludos)\.?$',
        r'^(¿?cómo estás\??|¿?qué tal\??|¿?cómo están\??)\.?$',
        r'^(gracias|thank you|thanks)\.?$',
        r'^(adiós|bye|hasta luego|nos vemos)\.?$',
        r'^(¿?quién eres\??|¿?qué eres\??|¿?cuál es tu nombre\??)\.?$',
        r'^(ayuda|help|¿?en qué puedes ayudarme\??)\.?$',
        r'^(test|prueba|testing)\.?$'
    ]
    
    # Si la consulta tiene menos de 10 caracteres y coincide con patrones de saludo
    if len(query_lower) <= 15:
        for pattern in greeting_patterns:
            if re.match(pattern, query_lower):
                return True
    
    return False

async def handle_greeting_response(query: str) -> Dict[str, Any]:
    """
    Maneja respuestas para saludos y conversación simple.
    
    Args:
        query: Consulta del usuario
        
    Returns:
        Respuesta formateada para saludos
    """
    query_lower = query.lower().strip()
    
    if re.match(r'^(hola|hello|hi|buenos días|buenas tardes|buenas noches)', query_lower):
        respuesta = "¡Hola! Soy JusticIA, tu asistente virtual especializado en documentos legales del Poder Judicial de Costa Rica. Estoy aquí para ayudarte con consultas sobre expedientes, casos y información jurídica. ¿En qué puedo asistirte hoy?"
    elif re.match(r'^(¿?cómo estás\??|¿?qué tal\??)', query_lower):
        respuesta = "¡Muy bien, gracias por preguntar! Estoy aquí y listo para ayudarte con cualquier consulta sobre expedientes legales o información jurídica. ¿Hay algo específico en lo que pueda asistirte?"
    elif re.match(r'^(¿?quién eres\??|¿?qué eres\??)', query_lower):
        respuesta = "Soy JusticIA, un asistente virtual inteligente especializado en documentos legales y jurídicos del Poder Judicial de Costa Rica. Puedo ayudarte a buscar información en expedientes, analizar casos similares y responder consultas jurídicas. ¿En qué puedo ayudarte?"
    elif re.match(r'^(ayuda|help)', query_lower):
        respuesta = "¡Por supuesto! Puedo ayudarte con:\n\n• Búsqueda de expedientes específicos\n• Análisis de casos similares\n• Consultas sobre materias legales (civil, penal, laboral, etc.)\n• Información sobre procesos judiciales\n• Revisión de documentos legales\n\n¿Sobre qué tema específico te gustaría consultar?"
    else:
        respuesta = "¡Hola! Soy JusticIA, tu asistente legal virtual. Estoy aquí para ayudarte con consultas sobre expedientes y documentos jurídicos. ¿En qué puedo asistirte?"
    
    return {
        "respuesta": respuesta,
        "expedientes_consultados": 0,
        "documentos_similares": [],
        "es_saludo": True
    }

async def general_search(query: str, top_k: int = 30) -> Dict[str, Any]:
    """
    Realiza una búsqueda general en toda la base de datos.
    
    Args:
        query: Consulta del usuario
        top_k: Número de documentos más relevantes a recuperar
        
    Returns:
        Diccionario con la respuesta y metadatos
    """
    try:
        # Verificar si es un saludo o conversación simple
        if is_greeting_or_simple_conversation(query):
            return await handle_greeting_response(query)
        
        # OPCIÓN 1: Búsqueda semántica directa (recomendada)
        # LangChain maneja automáticamente: texto → embedding → búsqueda
        similar_docs = await search_by_text(
            query_text=query,
            top_k=top_k,
            score_threshold=0.0
        )
        
        # Si no encuentra documentos, intentar con búsqueda vectorial manual
        if not similar_docs:
            # OPCIÓN 2: Generar embedding manualmente y buscar
            query_embedding = await get_embedding(query)
            similar_docs = await search_by_vector(
                query_vector=query_embedding,
                top_k=top_k,
                score_threshold=0.0
            )
        
        if not similar_docs:
            return {
                "respuesta": "No se encontraron documentos relevantes para tu consulta.",
                "documentos_encontrados": 0,
                "sources": [],
                "query_original": query
            }
        
        # 3. Preparar contexto para el LLM
        # Adaptar formato nuevo al formato legacy esperado por _prepare_context
        adapted_docs = []
        for doc in similar_docs:
            adapted_docs.append({
                "entity": {
                    "texto": doc.get("content_preview", ""),
                    "numero_expediente": doc.get("expedient_id", ""),
                    "nombre_archivo": doc.get("document_name", "")
                },
                "distance": 1.0 - doc.get("similarity_score", 0.0)
            })
        context = _prepare_context(adapted_docs)
        
        # 4. Cargar system prompt
        system_prompt = _load_system_prompt()
        
        # 5. Preparar prompt completo
        full_prompt = f"""
{system_prompt}

CONTEXTO RELEVANTE:
{context}

CONSULTA DEL USUARIO:
{query}

RESPUESTA:
"""
        
        # Log para debugging - ver qué contexto se está enviando
        print(f"CONTEXT DEBUG - Tamaño del contexto: {len(context)} caracteres")
        print(f"CONTEXT DEBUG - Número de documentos: {len(similar_docs)}")
        if context:
            print(f"CONTEXT DEBUG - Inicio del contexto: {context[:500]}")
        else:
            print("CONTEXT DEBUG - CONTEXTO VACÍO!")
        
        # 6. Consultar al LLM usando tu función existente
        respuesta_llm = await consulta_simple(full_prompt)
        respuesta = respuesta_llm.get("respuesta", "Error al generar respuesta")
        
        # 7. Preparar respuesta final
        return {
            "respuesta": respuesta,
            "documentos_encontrados": len(similar_docs),
            "sources": _extract_sources(similar_docs),
            "query_original": query
        }
    
    except Exception as e:
        return {
            "respuesta": f"Error al procesar la consulta: {str(e)}",
            "documentos_encontrados": 0,
            "sources": [],
            "query_original": query,
            "error": str(e)
        }

def _prepare_context(documents: List[Dict[str, Any]]) -> str:
    """
    Prepara el contexto para el LLM a partir de los documentos encontrados.
    Solo incluye el contenido textual relevante, sin información técnica.
    NUNCA incluye nombres de archivos o metadatos sensibles.
    """
    context_parts = []
    
    for i, doc in enumerate(documents, 1):
        # Obtener información del documento
        entity = doc.get("entity", {})
        texto = entity.get("texto", "")
        numero_expediente = entity.get("numero_expediente", "")
        
        # Solo incluir texto si existe
        if texto.strip():
            # Limitar contenido si es muy largo para mantener eficiencia
            texto_para_contexto = texto[:1500] + "..." if len(texto) > 1500 else texto
            
            # Formato simple sin información técnica
            context_part = f"""
FRAGMENTO {i}:
{texto_para_contexto}
"""
            # Solo agregar referencia al expediente si existe (sin revelar archivos específicos)
            if numero_expediente and numero_expediente.strip():
                context_part += f"(Del expediente: {numero_expediente})\n"
            
            context_parts.append(context_part)
    
    return "\n".join(context_parts)

def _extract_sources(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extrae información de fuentes para mostrar al usuario.
    NO incluye información técnica como similitud, nombres de archivos o IDs.
    """
    sources = []
    expedientes_vistos = set()
    
    for doc in documents:
        entity = doc.get("entity", {})
        numero_expediente = entity.get("numero_expediente")
        
        # Solo incluir información básica de la fuente sin duplicados
        if numero_expediente and numero_expediente not in expedientes_vistos:
            source_info = {
                "numero_expediente": numero_expediente,
                "tipo_documento": "Documento legal",  # Genérico, sin especificar archivo
                "fuente_sistema": "Sistema del Poder Judicial"
            }
            
            sources.append(source_info)
            expedientes_vistos.add(numero_expediente)
    
    return sources

def _load_system_prompt() -> str:
    """
    Carga el system prompt desde archivo.
    
    Returns:
        Contenido del system prompt
    """
    try:
        prompt_path = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "config", 
            "system_prompt.txt"
        )
        
        with open(prompt_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    
    except Exception as e:
        return """Eres JustiBot, un asistente virtual especializado en documentos legales. 
        Responde de forma clara, profesional y basándote únicamente en el contexto proporcionado.
        Si la información no está en el contexto, indica claramente que no tienes esa información."""


async def general_search_streaming(query: str, top_k: int = 30):
    """
    Realiza una búsqueda general con streaming de respuesta.
    
    Args:
        query: Consulta del usuario
        top_k: Número de documentos más relevantes a recuperar
        
    Returns:
        StreamingResponse con la respuesta en tiempo real
    """
    try:
        # Verificar si es un saludo o conversación simple
        if is_greeting_or_simple_conversation(query):
            # Para saludos, devolver respuesta directamente sin streaming complejo
            greeting_response = await handle_greeting_response(query)
            
            # Simular streaming suave para mantener consistencia con la interfaz
            async def greeting_stream():
                respuesta = greeting_response["respuesta"]
                
                # Enviar la respuesta en chunks más naturales (por oraciones)
                oraciones = respuesta.split('. ')
                for i, oracion in enumerate(oraciones):
                    if i > 0:
                        # Agregar el punto que se perdió al hacer split
                        chunk = '. ' + oracion
                    else:
                        chunk = oracion
                    
                    # Asegurar que no esté vacío
                    if chunk.strip():
                        yield f"data: {chunk}\n\n"
                        # Pequeña pausa entre oraciones para efecto natural
                        import asyncio
                        await asyncio.sleep(0.1)
                
                yield "data: [DONE]\n\n"
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                greeting_stream(), 
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )
        
        # 1. Búsqueda semántica directa con LangChain (solo para consultas legales)
        similar_docs = await search_by_text(
            query_text=query,
            top_k=top_k,
            score_threshold=0.0
        )
        
        # 3. Preparar contexto para el LLM
        if similar_docs:
            # Adaptar formato nuevo al formato legacy esperado por _prepare_context
            adapted_docs = []
            for doc in similar_docs:
                adapted_docs.append({
                    "entity": {
                        "texto": doc.get("content_preview", ""),
                        "numero_expediente": doc.get("expedient_id", ""),
                        "nombre_archivo": doc.get("document_name", "")
                    },
                    "distance": 1.0 - doc.get("similarity_score", 0.0)
                })
            context = _prepare_context(adapted_docs)
        else:
            context = "No se encontraron documentos relevantes en la base de datos."
        
        # 4. Cargar system prompt
        system_prompt = _load_system_prompt()
        
        # 5. Preparar prompt completo
        full_prompt = f"""
{system_prompt}

CONTEXTO RELEVANTE:
{context}

CONSULTA DEL USUARIO:
{query}

RESPUESTA:
"""
        
        # Log para debugging - ver qué contexto se está enviando
        print(f"CONTEXT DEBUG - Tamaño del contexto: {len(context)} caracteres")
        print(f"CONTEXT DEBUG - Número de documentos: {len(similar_docs) if similar_docs else 0}")
        if context:
            print(f"CONTEXT DEBUG - Inicio del contexto: {context[:500]}")
        else:
            print("CONTEXT DEBUG - CONTEXTO VACÍO!")
        
        # DEBUG: Imprimir el prompt completo que se envía al LLM
        print("=" * 80)
        print("PROMPT COMPLETO ENVIADO AL LLM:")
        print("=" * 80)
        print(full_prompt)
        print("=" * 80)
        print("FIN DEL PROMPT")
        print("=" * 80)
        
        # 6. Consultar al LLM con streaming
        return await consulta_general_streaming(full_prompt)
    
    except Exception as e:
        # En caso de error, devolver un streaming response con el error
        from fastapi.responses import StreamingResponse
        
        async def error_generator():
            yield f"data: Error al procesar la consulta: {str(e)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            error_generator(), 
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
