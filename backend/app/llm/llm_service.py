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
            model_kwargs={"num_ctx": 512, "num_predict": 128},
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
            yield chunk.content

    return StreamingResponse(event_generator(), media_type="text/plain")