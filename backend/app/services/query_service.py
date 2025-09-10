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
                        if hasattr(hit, 'entity'):
                            similar_docs.append({
                                "entity": hit.entity,
                                "distance": hit.distance
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
    """
    context_parts = []
    
    for i, doc in enumerate(documents, 1):
        # Obtener información del documento
        entity = doc.get("entity", {})
        texto = entity.get("texto", "")  # ✅ Cambió de "contenido" a "texto"
        id_expediente = entity.get("id_expediente", "")
        id_documento = entity.get("id_documento", "")
        tipo_archivo = entity.get("tipo_archivo", "")
        fecha = entity.get("fecha_carga", "")
        nombre_archivo = entity.get("nombre_archivo", "")
        numero_expediente = entity.get("numero_expediente", "")
        similitud = round(1 - doc.get("distance", 1), 3)  # Convertir distancia a similitud
        
        # Limitar contenido si es muy largo
        texto_resumido = texto[:500] + "..." if len(texto) > 500 else texto
        
        context_part = f"""
Documento {i} (Similitud: {similitud}):
- Expediente: {numero_expediente} (ID: {id_expediente})
- Archivo: {nombre_archivo} (ID: {id_documento})
- Tipo: {tipo_archivo}
- Fecha: {fecha}
- Contenido: {texto_resumido}
"""
        context_parts.append(context_part)
    
    return "\n".join(context_parts)

def _extract_sources(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extrae información de fuentes para mostrar al usuario.
    """
    sources = []
    
    for doc in documents:
        entity = doc.get("entity", {})
        similitud = round(1 - doc.get("distance", 1), 3)
        
        sources.append({
            "id_expediente": entity.get("id_expediente"),
            "numero_expediente": entity.get("numero_expediente"),
            "id_documento": entity.get("id_documento"),
            "nombre_archivo": entity.get("nombre_archivo"),
            "tipo_archivo": entity.get("tipo_archivo"),
            "fecha_carga": entity.get("fecha_carga"),
            "similitud": similitud
        })
    
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
        return """Eres JusticIA, un asistente virtual especializado en documentos legales. 
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
