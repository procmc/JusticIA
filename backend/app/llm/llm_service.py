from langchain_ollama import ChatOllama
from app.config.config import OLLAMA_MODEL, OLLAMA_BASE_URL
from fastapi.responses import StreamingResponse

_llm = None


async def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.1,
            streaming=True,
            keep_alive="5m",
            model_kwargs={
                "num_ctx": 4096,      # Aumentado para más contexto
                "num_predict": 512,   # Aumentado para respuestas más largas
                "top_k": 10,
                "top_p": 0.9
            },
        )
    return _llm


async def consulta_simple(pregunta: str):
    """Consulta simple a Ollama sin RAG"""
    print(f"Consulta recibida: {pregunta}")
    llm = await get_llm()
    print("LLM:", llm)
    try:
        response = await llm.ainvoke(pregunta)
        print("Respuesta:", response)
        # Si la respuesta tiene el atributo 'content'
        return {"respuesta": getattr(response, "content", str(response))}
    except Exception as e:
        print("Error:", e)
        return {"error": str(e)}


async def consulta_streaming(pregunta: str):
    """Consulta a Ollama con streaming de respuesta"""
    llm = await get_llm()
    print(f"Consulta recibida (streaming): {pregunta}")

    async def event_generator():
        async for chunk in llm.astream(pregunta):
            yield str(chunk.content)

    return StreamingResponse(event_generator(), media_type="text/plain")


async def consulta_general_streaming(prompt_completo: str):
    """Consulta general con RAG y streaming de respuesta"""
    print(f"Consulta general streaming iniciada")
    
    async def event_generator():
        try:
            # Obtener LLM con manejo de errores
            llm = await get_llm()
            print(f"LLM obtenido: {llm}")
            
            # Verificar conexión antes de hacer streaming
            print(f"Iniciando streaming para prompt de {len(prompt_completo)} caracteres")
            
            async for chunk in llm.astream(prompt_completo):
                # Enviar cada chunk como Server-Sent Event
                content = getattr(chunk, 'content', str(chunk))
                if content and content.strip():
                    print(f"Chunk recibido: {content[:50]}...")
                    yield f"data: {content}\n\n"
            
            # Señal de finalización
            print("Streaming completado exitosamente")
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            print(f"Error en streaming: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )