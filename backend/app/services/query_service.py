from typing import List, Dict, Any
from app.embeddings.embeddings import get_embedding
from app.llm.llm_service import consulta_simple, consulta_general_streaming
from app.vectorstore.vectorstore import search_similar_documents
import os

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
        # 1. Generar embedding de la consulta
        query_embedding = await get_embedding(query)
        
        # 2. Buscar documentos similares en Milvus
        similar_docs = await search_similar_documents(
            query_embedding=query_embedding,
            limit=top_k,
            filters=None
        )
        
        # Si no encuentra documentos, intentar query directo como fallback
        if not similar_docs:
            from app.vectorstore.vectorstore import get_vectorstore
            from app.config.config import COLLECTION_NAME
            
            client = await get_vectorstore()
            
            try:
                # Fallback: búsqueda con vector dummy
                dummy_vector = [0.1] * 768
                search_results = client.search(
                    collection_name=COLLECTION_NAME,
                    data=[dummy_vector],
                    anns_field="embedding",
                    search_params={"metric_type": "COSINE", "params": {"ef": 64}},
                    limit=top_k,
                    output_fields=["id_chunk", "texto", "numero_expediente", "nombre_archivo"]
                )
                
                # Convertir search results a formato estándar
                if search_results and len(search_results) > 0:
                    for hit in search_results[0]:
                        if hasattr(hit, 'entity') and hasattr(hit, 'distance'):
                            # Acceso seguro a los datos de la entidad usando getattr
                            entity_obj = getattr(hit, 'entity', {})
                            entity_data = {}
                            
                            if hasattr(entity_obj, 'get'):
                                # Si entity es un diccionario
                                entity_data = dict(entity_obj)
                            else:
                                # Si entity es un objeto, extraer campos específicos
                                for field in ["id_chunk", "texto", "numero_expediente", "nombre_archivo"]:
                                    if hasattr(entity_obj, field):
                                        entity_data[field] = getattr(entity_obj, field)
                            
                            similar_docs.append({
                                "entity": entity_data,
                                "distance": getattr(hit, 'distance', 0.5)
                            })
                        elif isinstance(hit, dict):
                            similar_docs.append({
                                "entity": hit,
                                "distance": hit.get('distance', 0.5)
                            })
                            
            except Exception:
                pass
        
        if not similar_docs:
            return {
                "respuesta": "No se encontraron documentos relevantes para tu consulta.",
                "documentos_encontrados": 0,
                "sources": [],
                "query_original": query
            }
        
        # 3. Preparar contexto para el LLM
        context = _prepare_context(similar_docs)
        
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
        # 1. Generar embedding de la consulta
        query_embedding = await get_embedding(query)
        
        # 2. Buscar documentos similares en Milvus
        similar_docs = await search_similar_documents(
            query_embedding=query_embedding,
            limit=top_k,
            filters=None  # Sin filtros = búsqueda general
        )
        
        # 3. Preparar contexto para el LLM
        if similar_docs:
            context = _prepare_context(similar_docs)
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
