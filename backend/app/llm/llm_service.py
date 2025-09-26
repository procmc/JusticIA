import asyncio
from langchain_ollama import ChatOllama
from app.config.config import (
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_API_KEY,
    LLM_TEMPERATURE,
    LLM_KEEP_ALIVE,
    LLM_REQUEST_TIMEOUT,
    LLM_NUM_CTX,
    LLM_NUM_PREDICT,
    LLM_TOP_K,
    LLM_TOP_P,
    LLM_REPEAT_PENALTY,
)
from fastapi.responses import StreamingResponse

# Singleton LLM
_llm = None
_llm_lock = asyncio.Lock()

async def get_llm():
    """Obtiene la instancia compartida del LLM.

    Versión minimalista: sin logs ni lógica adicional. Si `OLLAMA_API_KEY` está
    definida, se pasa en los headers.
    """
    global _llm
    async with _llm_lock:
        if _llm is None:
            client_kwargs = {}
            if OLLAMA_API_KEY:
                client_kwargs = {"headers": {"Authorization": f"Bearer {OLLAMA_API_KEY}"}}

            _llm = ChatOllama(
                model=OLLAMA_MODEL,
                base_url=OLLAMA_BASE_URL,
                temperature=LLM_TEMPERATURE,
                streaming=True,
                keep_alive=LLM_KEEP_ALIVE,
                request_timeout=LLM_REQUEST_TIMEOUT,
                reasoning=False,
                client_kwargs=client_kwargs,
                model_kwargs={
                    "num_ctx": LLM_NUM_CTX,
                    "num_predict": LLM_NUM_PREDICT,
                    "top_k": LLM_TOP_K,
                    "top_p": LLM_TOP_P,
                    "repeat_penalty": LLM_REPEAT_PENALTY,
                },
            )
        return _llm

async def consulta_general_streaming(prompt_completo: str):
    """Streaming simplificado: obtiene el singleton LLM y re-emite los chunks.
    No logging, no filtrado.
    """
    import json
    async def event_generator():
        try:
            llm = await get_llm()
            buffer = ""
            min_size = 200
            async for chunk in llm.astream(prompt_completo):
                content = getattr(chunk, "content", str(chunk))
                if not content:
                    continue
                buffer += str(content)
                while True:
                    split_idx = buffer.find("\n\n")
                    if split_idx != -1:
                        to_send = buffer[:split_idx+2]
                        buffer = buffer[split_idx+2:]
                    elif len(buffer) >= min_size:
                        to_send = buffer
                        buffer = ""
                    else:
                        break
                    chunk_data = {"type": "chunk", "content": to_send}
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            if buffer:
                chunk_data = {"type": "chunk", "content": buffer}
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            done_data = {"type": "done", "content": "", "done": True}
            yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            done_data = {"type": "done", "content": "", "done": True}
            yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_data = {"type": "error", "content": f"Error: {str(e)}", "done": True}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            done_data = {"type": "done", "content": "", "done": True}
            yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )