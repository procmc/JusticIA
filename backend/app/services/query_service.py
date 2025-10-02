from typing import List, Dict, Any
from app.embeddings.embeddings import get_embedding
from app.llm.llm_service import consulta_general_streaming
from app.vectorstore.vectorstore import search_by_vector, search_by_text, get_complete_document_by_chunks
import os
import re
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

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

async def general_search(query: str, top_k: int = 30, conversation_context: str = "") -> Dict[str, Any]:
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
        
        # DETECCIÓN DE EXPEDIENTE ESPECÍFICO EN CONSULTA GENERAL
        import re
        expediente_pattern = r'\b\d{4}-\d{6}-\d{4}-[A-Z]{2}\b'
        expedientes_detectados = re.findall(expediente_pattern, query)
        
        # DETECCIÓN DE REFERENCIAS CONTEXTUALES
        referencias_contextuales = [
            r'\b(?:el\s+)?último\s+(?:expediente|caso)\b',
            r'\b(?:el\s+)?primer\s+(?:expediente|caso)\b', 
            r'\b(?:el\s+)?(?:expediente|caso)\s+más\s+reciente\b',
            r'\b(?:ese|este|dicho)\s+(?:expediente|caso)\b',
            r'\b(?:el\s+)?(?:expediente|caso)\s+anterior\b',
            r'\b(?:del\s+)?(?:expediente|caso)\s+mencionado\b'
        ]
        
        tiene_referencia_contextual = any(re.search(patron, query.lower()) for patron in referencias_contextuales)
        
        # Si hay referencias contextuales pero no expedientes explícitos, intentar resolver desde contexto
        if tiene_referencia_contextual and not expedientes_detectados and conversation_context:
            logger.info(f"🔍 REFERENCIA CONTEXTUAL DETECTADA: {query}")
            
            # Resolver la referencia usando el contexto de conversación  
            query_resuelto = _resolve_contextual_reference(query, conversation_context)
            logger.info(f"📝 QUERY ORIGINAL: {query}")
            logger.info(f"🎯 QUERY RESUELTO: {query_resuelto}")
            
            # Buscar expedientes en el query resuelto
            expedientes_resueltos = re.findall(expediente_pattern, query_resuelto)
            
            if expedientes_resueltos:
                # Usar búsqueda por expediente específico
                similar_docs = []
                for expediente in expedientes_resueltos:
                    docs_expediente = await search_by_text(
                        query_text=query,  # Usar query original para contexto
                        top_k=100,
                        expediente_filter=expediente
                    )
                    similar_docs.extend(docs_expediente)
                    logger.info(f"✅ CONTEXTO RESUELTO - Encontrados {len(docs_expediente)} documentos para expediente {expediente}")
            else:
                # Fallback a búsqueda semántica amplia
                similar_docs = await search_by_text(
                    query_text=query_resuelto,
                    top_k=60,
                    score_threshold=0.0
                )
        elif tiene_referencia_contextual and not expedientes_detectados:
            # Sin contexto de conversación disponible, hacer búsqueda amplia
            logger.warning(f"🔍 REFERENCIA CONTEXTUAL SIN CONTEXTO DISPONIBLE: {query}")
            similar_docs = await search_by_text(
                query_text=query,
                top_k=60,  # Buscar más documentos
                score_threshold=0.0
            )
        elif expedientes_detectados:
            # Si detectamos números de expediente, hacer búsqueda híbrida
            logger.info(f"🎯 EXPEDIENTES DETECTADOS EN CONSULTA GENERAL: {expedientes_detectados}")
            similar_docs = []
            
            for expediente in expedientes_detectados:
                # Búsqueda directa por expediente (como en consulta específica)
                docs_expediente = await search_by_text(
                    query_text=query,
                    top_k=100,  # Buscar muchos documentos del expediente
                    expediente_filter=expediente  # Usar el filtro específico
                )
                similar_docs.extend(docs_expediente)
                logger.info(f"✅ Encontrados {len(docs_expediente)} documentos para expediente {expediente}")
            
            # Si no encontramos nada con filtro, hacer búsqueda semántica normal
            if not similar_docs:
                logger.warning("❌ Búsqueda por expediente específico no encontró resultados, fallback a semántica")
                similar_docs = await search_by_text(
                    query_text=query,
                    top_k=top_k,
                    score_threshold=0.0
                )
        else:
            # BÚSQUEDA SEMÁNTICA NORMAL
            # Para casos específicos como hostigamiento laboral, aumentar significativamente top_k
            if "hostigamiento" in query.lower() or "bitácora" in query.lower():
                top_k_ajustado = max(top_k, 50)  # Buscar más documentos para casos complejos
                logger.info(f"🔍 Caso específico detectado, aumentando top_k a {top_k_ajustado}")
            else:
                top_k_ajustado = top_k
                
            # LangChain maneja automáticamente: texto → embedding → búsqueda
            similar_docs = await search_by_text(
                query_text=query,
                top_k=top_k_ajustado,
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
        
        # 3. Preparar contexto para el LLM con información enriquecida
        # Adaptar formato nuevo al formato legacy esperado por _prepare_context
        adapted_docs = []
        for doc in similar_docs:
            adapted_docs.append({
                "entity": {
                    "texto": doc.get("content_preview", ""),
                    "numero_expediente": doc.get("expedient_id", ""),
                    "nombre_archivo": doc.get("document_name", ""),
                    "id_documento": doc.get("metadata", {}).get("id_documento") if doc.get("metadata") else None
                },
                "distance": 1.0 - doc.get("similarity_score", 0.0)
            })
        
        # Usar el contexto mejorado con más información
        try:
            context = await _prepare_context_with_complete_documents(adapted_docs)
            logger.info(f"✅ Contexto completo generado exitosamente: {len(context)} caracteres")
            
            # DEBUG ESPECÍFICO para el caso de hostigamiento laboral
            if "2022-063557-6597-LA" in context or "hostigamiento" in query.lower():
                logger.info("🔍 CASO HOSTIGAMIENTO LABORAL - ANÁLISIS DE CONTEXTO:")
                logger.info(f"   - ¿Contiene 'Ana Fernández'? {'Ana Fernández' in context}")
                logger.info(f"   - ¿Contiene 'Bitácora'? {'Bitácora' in context or 'bitácora' in context}")
                logger.info(f"   - ¿Contiene '17/01/2025'? {'17/01/2025' in context}")
                logger.info(f"   - ¿Contiene '₡12.500.000'? {'₡12.500.000' in context}")
                if 'bitácora' in query.lower() or 'Bitácora' in query.lower():
                    logger.info("   - PREGUNTA ESPECÍFICA SOBRE BITÁCORA DETECTADA")
                    if 'Bitácora' not in context and 'bitácora' not in context:
                        logger.error("   - ❌ BITÁCORA NO ENCONTRADA EN CONTEXTO!")
                    else:
                        logger.info("   - ✅ BITÁCORA ENCONTRADA EN CONTEXTO")
        except Exception as e:
            logger.error(f"❌ Error usando contexto completo, fallback a método anterior: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
        logger.info(f"CONTEXT DEBUG - Tamaño del contexto: {len(context)} caracteres")
        logger.info(f"CONTEXT DEBUG - Número de documentos: {len(similar_docs)}")
        logger.info(f"CONTEXT DEBUG - Query original: {query}")
        if context:
            logger.info(f"CONTEXT DEBUG - Inicio del contexto: {context[:800]}...")
            # Para el caso específico de hostigamiento laboral, ver si está la información completa
            if "hostigamiento" in query.lower() or "2022-063557-6597-LA" in context:
                logger.info(f"CONTEXT DEBUG - CASO HOSTIGAMIENTO LABORAL DETECTADO")
                logger.info(f"CONTEXT DEBUG - ¿Contiene 'Ana Fernández'? {'Ana Fernández' in context}")
                logger.info(f"CONTEXT DEBUG - ¿Contiene 'Bitácora'? {'Bitácora' in context or 'bitácora' in context}")
                logger.info(f"CONTEXT DEBUG - ¿Contiene fechas específicas? {'17/01/2025' in context}")
        else:
            logger.warning("CONTEXT DEBUG - CONTEXTO VACÍO!")
        
        # 6. Generar respuesta usando el LLM disponible
        try:
            from app.llm.llm_service import get_llm
            llm = await get_llm()
            
            # Generar respuesta directa (sin streaming)
            response = await llm.ainvoke(full_prompt)
            respuesta = response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            logger.error(f"Error consultando LLM: {e}")
            respuesta = f"Se encontraron {len(similar_docs)} documentos relevantes. Consulte los detalles en las fuentes proporcionadas."
        
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

def _extract_expedientes_from_context(context: str) -> List[str]:
    """
    Extrae números de expediente del contexto de conversación.
    Retorna una lista ordenada por aparición (más reciente primero).
    """
    import re
    expediente_pattern = r'\b\d{4}-\d{6}-\d{4}-[A-Z]{2}\b'
    expedientes = re.findall(expediente_pattern, context)
    
    # Eliminar duplicados manteniendo el orden (más reciente primero)
    expedientes_unicos = []
    for exp in reversed(expedientes):  # Invertir para que el más reciente esté primero
        if exp not in expedientes_unicos:
            expedientes_unicos.append(exp)
    
    return expedientes_unicos

def _resolve_contextual_reference(query: str, context: str) -> str:
    """
    Resuelve referencias contextuales como 'el último expediente' 
    basándose en el contexto de conversación.
    """
    expedientes_en_contexto = _extract_expedientes_from_context(context)
    
    if not expedientes_en_contexto:
        return query  # No hay expedientes en el contexto
    
    query_lower = query.lower()
    
    # Resolver diferentes tipos de referencias
    if re.search(r'\b(?:el\s+)?último\s+(?:expediente|caso)\b', query_lower):
        # "el último expediente" = el más reciente mencionado
        expediente_resuelto = expedientes_en_contexto[0]
        return f"{query} [{expediente_resuelto}]"
    
    elif re.search(r'\b(?:el\s+)?primer\s+(?:expediente|caso)\b', query_lower):
        # "el primer expediente" = el más antiguo mencionado
        expediente_resuelto = expedientes_en_contexto[-1]
        return f"{query} [{expediente_resuelto}]"
    
    elif re.search(r'\b(?:ese|este|dicho)\s+(?:expediente|caso)\b', query_lower):
        # "ese expediente" = el más reciente mencionado
        expediente_resuelto = expedientes_en_contexto[0]
        return f"{query} [{expediente_resuelto}]"
    
    elif re.search(r'\b(?:el\s+)?(?:expediente|caso)\s+más\s+reciente\b', query_lower):
        # "el caso más reciente" = el más nuevo mencionado
        expediente_resuelto = expedientes_en_contexto[0]
        return f"{query} [{expediente_resuelto}]"
    
    return query

async def _prepare_context_with_complete_documents(documents: List[Dict[str, Any]]) -> str:
    """
    Prepara el contexto para el LLM recuperando documentos completos cuando sea posible.
    Agrupa chunks por documento y presenta información más coherente y completa.
    """
    # Agrupar documentos por id_documento para recuperar contexto completo
    documents_by_id = defaultdict(list)
    
    for doc in documents:
        entity = doc.get("entity", {})
        doc_id = entity.get("id_documento")
        if doc_id:
            documents_by_id[doc_id].append(doc)
    
    context_parts = []
    processed_docs = set()
    
    # Procesar documentos agrupados para obtener contexto completo
    for i, doc in enumerate(documents, 1):
        entity = doc.get("entity", {})
        doc_id = entity.get("id_documento")
        numero_expediente = entity.get("numero_expediente", "")
        nombre_archivo = entity.get("nombre_archivo", "")
        
        # Si ya procesamos este documento completo, saltar
        if doc_id in processed_docs:
            continue
            
        try:
            # Intentar recuperar el documento completo
            if doc_id:
                complete_chunks = await get_complete_document_by_chunks(int(doc_id))
                
                if complete_chunks:
                    # Combinar todos los chunks del documento en orden
                    texto_completo = ""
                    for chunk in complete_chunks:
                        chunk_text = chunk.get("texto", "")
                        if chunk_text.strip():
                            texto_completo += chunk_text + " "
                    
                    # Permitir documentos mucho más largos para casos complejos como el de hostigamiento laboral
                    if len(texto_completo) > 15000:
                        texto_para_contexto = texto_completo[:15000] + "... [documento continúa - información adicional disponible]"
                    else:
                        texto_para_contexto = texto_completo.strip()
                    
                    # Obtener metadatos adicionales del primer chunk
                    primer_chunk = complete_chunks[0]
                    tipo_documento = primer_chunk.get("tipo_documento", "documento")
                    pagina_inicio = primer_chunk.get("pagina_inicio")
                    pagina_fin = complete_chunks[-1].get("pagina_fin") if len(complete_chunks) > 1 else primer_chunk.get("pagina_fin")
                    
                    # Formato enriquecido con metadatos útiles
                    context_part = f"""
=== DOCUMENTO {i}: {tipo_documento.upper()} ===
Expediente: {numero_expediente}
Archivo: {nombre_archivo}"""
                    
                    if pagina_inicio and pagina_fin:
                        context_part += f"\nPáginas: {pagina_inicio}-{pagina_fin}"
                    
                    context_part += f"\n\nCONTENIDO COMPLETO:\n{texto_para_contexto}\n"
                    
                    context_parts.append(context_part)
                    processed_docs.add(doc_id)
                    
                else:
                    # Fallback al método anterior si no se puede recuperar completo
                    texto = entity.get("texto", "")
                    if texto.strip():
                        texto_para_contexto = texto[:3000] + "..." if len(texto) > 3000 else texto
                        context_part = f"""
=== FRAGMENTO {i} ===
Expediente: {numero_expediente}
Archivo: {nombre_archivo}

CONTENIDO:\n{texto_para_contexto}\n"""
                        context_parts.append(context_part)
            else:
                # Sin id_documento, usar método anterior mejorado
                texto = entity.get("texto", "")
                if texto.strip():
                    texto_para_contexto = texto[:3000] + "..." if len(texto) > 3000 else texto
                    context_part = f"""
=== FRAGMENTO {i} ===
Expediente: {numero_expediente}

CONTENIDO:\n{texto_para_contexto}\n"""
                    context_parts.append(context_part)
                    
        except Exception as e:
            # En caso de error, usar el método anterior como fallback
            logger.warning(f"Error recuperando documento completo {doc_id}: {e}")
            texto = entity.get("texto", "")
            if texto.strip():
                texto_para_contexto = texto[:3000] + "..." if len(texto) > 3000 else texto
                context_part = f"""
=== FRAGMENTO {i} ===
Expediente: {numero_expediente}\n
CONTENIDO:\n{texto_para_contexto}\n"""
                context_parts.append(context_part)
    
    return "\n".join(context_parts)

def _prepare_context(documents: List[Dict[str, Any]]) -> str:
    """
    Versión síncrona mejorada para compatibilidad con código existente.
    Aumenta los límites de texto y mejora el formato.
    """
    context_parts = []
    
    for i, doc in enumerate(documents, 1):
        # Obtener información del documento
        entity = doc.get("entity", {})
        texto = entity.get("texto", "")
        numero_expediente = entity.get("numero_expediente", "")
        nombre_archivo = entity.get("nombre_archivo", "")
        
        # Solo incluir texto si existe
        if texto.strip():
            # Aumentar límite significativamente para casos complejos como hostigamiento laboral
            texto_para_contexto = texto[:10000] + "... [continúa]" if len(texto) > 10000 else texto
            
            # Formato mejorado con más información
            context_part = f"""
=== DOCUMENTO {i} ===
Expediente: {numero_expediente}"""
            
            if nombre_archivo:
                context_part += f"\nArchivo: {nombre_archivo}"
            
            context_part += f"\n\nCONTENIDO:\n{texto_para_contexto}\n"
            
            context_parts.append(context_part)
    
    return "\n".join(context_parts)

def _extract_sources(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extrae información enriquecida de fuentes para mostrar al usuario.
    Incluye metadatos útiles manteniendo la privacidad apropiada.
    """
    sources = []
    documentos_vistos = set()
    
    for doc in documents:
        entity = doc.get("entity", {})
        numero_expediente = entity.get("numero_expediente")
        nombre_archivo = entity.get("nombre_archivo", "")
        doc_id = entity.get("id_documento")
        
        # Crear clave única por documento para evitar duplicados
        doc_key = f"{numero_expediente}_{doc_id}" if doc_id else numero_expediente
        
        if numero_expediente and doc_key not in documentos_vistos:
            # Determinar tipo de documento basado en el nombre del archivo
            tipo_documento = "Documento legal"
            if nombre_archivo:
                nombre_lower = nombre_archivo.lower()
                if "sentencia" in nombre_lower:
                    tipo_documento = "Sentencia"
                elif "resolucion" in nombre_lower or "resolución" in nombre_lower:
                    tipo_documento = "Resolución"
                elif "auto" in nombre_lower:
                    tipo_documento = "Auto judicial"
                elif "acta" in nombre_lower:
                    tipo_documento = "Acta"
                elif "demanda" in nombre_lower:
                    tipo_documento = "Demanda"
                elif "denuncia" in nombre_lower:
                    tipo_documento = "Denuncia"
                elif "dictamen" in nombre_lower:
                    tipo_documento = "Dictamen"
            
            source_info = {
                "numero_expediente": numero_expediente,
                "tipo_documento": tipo_documento,
                "fuente_sistema": "Sistema del Poder Judicial",
                "tiene_documento_completo": bool(doc_id),
                "nombre_archivo": nombre_archivo if nombre_archivo else "Documento sin nombre específico"
            }
            
            sources.append(source_info)
            documentos_vistos.add(doc_key)
    
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


async def general_search_streaming(query: str, top_k: int = 30, conversation_context: str = ""):
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
        
        # 1. DETECCIÓN DE EXPEDIENTE ESPECÍFICO EN CONSULTA GENERAL (STREAMING)
        import re
        expediente_pattern = r'\b\d{4}-\d{6}-\d{4}-[A-Z]{2}\b'
        expedientes_detectados = re.findall(expediente_pattern, query)
        
        # DETECCIÓN DE REFERENCIAS CONTEXTUALES (STREAMING)
        referencias_contextuales = [
            r'\b(?:el\s+)?último\s+(?:expediente|caso)\b',
            r'\b(?:el\s+)?primer\s+(?:expediente|caso)\b', 
            r'\b(?:el\s+)?(?:expediente|caso)\s+más\s+reciente\b',
            r'\b(?:ese|este|dicho)\s+(?:expediente|caso)\b',
            r'\b(?:el\s+)?(?:expediente|caso)\s+anterior\b',
            r'\b(?:del\s+)?(?:expediente|caso)\s+mencionado\b'
        ]
        
        tiene_referencia_contextual = any(re.search(patron, query.lower()) for patron in referencias_contextuales)
        
        # Resolver referencias contextuales primero
        if tiene_referencia_contextual and not expedientes_detectados and conversation_context:
            logger.info(f"🔍 STREAMING - REFERENCIA CONTEXTUAL DETECTADA: {query}")
            
            query_resuelto = _resolve_contextual_reference(query, conversation_context)
            logger.info(f"🎯 STREAMING - QUERY RESUELTO: {query_resuelto}")
            
            expedientes_resueltos = re.findall(expediente_pattern, query_resuelto)
            if expedientes_resueltos:
                expedientes_detectados = expedientes_resueltos
        
        if expedientes_detectados:
            # Si detectamos números de expediente, hacer búsqueda híbrida
            logger.info(f"🎯 STREAMING - EXPEDIENTES DETECTADOS: {expedientes_detectados}")
            similar_docs = []
            
            for expediente in expedientes_detectados:
                # Búsqueda directa por expediente (como en consulta específica)
                docs_expediente = await search_by_text(
                    query_text=query,
                    top_k=100,  # Buscar muchos documentos del expediente
                    expediente_filter=expediente  # Usar el filtro específico
                )
                similar_docs.extend(docs_expediente)
                logger.info(f"✅ STREAMING - Encontrados {len(docs_expediente)} documentos para expediente {expediente}")
            
            # Si no encontramos nada con filtro, hacer búsqueda semántica normal
            if not similar_docs:
                logger.warning("❌ STREAMING - Búsqueda por expediente específico no encontró resultados, fallback a semántica")
                similar_docs = await search_by_text(
                    query_text=query,
                    top_k=top_k,
                    score_threshold=0.0
                )
        else:
            # BÚSQUEDA SEMÁNTICA NORMAL
            # Para casos específicos como hostigamiento laboral, aumentar significativamente top_k
            if "hostigamiento" in query.lower() or "bitácora" in query.lower():
                top_k_ajustado = max(top_k, 50)  # Buscar más documentos para casos complejos
                logger.info(f"🔍 STREAMING - Caso específico detectado, aumentando top_k a {top_k_ajustado}")
            else:
                top_k_ajustado = top_k
                
            similar_docs = await search_by_text(
                query_text=query,
                top_k=top_k_ajustado,
                score_threshold=0.0
            )
        
        # 3. Preparar contexto para el LLM con información enriquecida
        if similar_docs:
            # Adaptar formato nuevo al formato legacy esperado por _prepare_context
            adapted_docs = []
            for doc in similar_docs:
                adapted_docs.append({
                    "entity": {
                        "texto": doc.get("content_preview", ""),
                        "numero_expediente": doc.get("expedient_id", ""),
                        "nombre_archivo": doc.get("document_name", ""),
                        "id_documento": doc.get("metadata", {}).get("id_documento") if doc.get("metadata") else None
                    },
                    "distance": 1.0 - doc.get("similarity_score", 0.0)
                })
            
            # Usar el contexto mejorado con más información
            try:
                context = await _prepare_context_with_complete_documents(adapted_docs)
            except Exception as e:
                logger.warning(f"Error usando contexto completo en streaming, fallback a método anterior: {e}")
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
