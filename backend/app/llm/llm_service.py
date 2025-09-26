import asyncio
import re
import logging
from langchain_ollama import ChatOllama
from app.config.config import (
    OLLAMA_MODEL, OLLAMA_BASE_URL,
    LLM_TEMPERATURE, LLM_KEEP_ALIVE, LLM_REQUEST_TIMEOUT,
    LLM_NUM_CTX, LLM_NUM_PREDICT, LLM_TOP_K, LLM_TOP_P, LLM_REPEAT_PENALTY
)
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

_llm = None
_llm_lock = asyncio.Lock()


def filter_thinking_chunk(chunk: str) -> str:
    """Filtra cualquier texto de pensamiento que aparezca en el chunk"""
    if not chunk:
        return chunk
    
    # Patrones más amplios para capturar todo tipo de texto de pensamiento
    patterns = [
        r'<think>.*?</think>',  # <think>...</think>
        r'<\|thinking\|>.*?</\|thinking\|>',  # <|thinking|>...</|thinking|>
        r'<think>.*',  # <think> hasta el final
        r'.*</think>',  # desde el inicio hasta </think>
        r'<\|thinking\|>.*',  # <|thinking|> hasta el final
        r'.*</\|thinking\|>',  # desde el inicio hasta </|thinking|>
        r'^.*?<think>',  # todo antes de <think>
        r'</think>.*?$',  # todo después de </think>
    ]
    
    filtered = chunk
    for pattern in patterns:
        filtered = re.sub(pattern, '', filtered, flags=re.DOTALL | re.IGNORECASE)
    
    # Limpiar espacios extra pero preservar la estructura del texto
    if filtered != chunk:  # Solo si se hizo algún cambio
        filtered = re.sub(r'\n\s*\n\s*\n', '\n\n', filtered)  # Máximo 2 saltos de línea
        filtered = filtered.strip()
    
    return filtered


class StreamBuffer:
    """Buffer para acumular chunks y filtrar pensamiento de manera más efectiva"""
    def __init__(self):
        self.buffer = ""
        self.in_thinking = False
    
    def add_chunk(self, chunk: str) -> str:
        """Agrega un chunk al buffer y retorna contenido filtrado listo para enviar"""
        self.buffer += chunk
        
        # Verificar si estamos en modo pensamiento
        if '<think>' in self.buffer.lower() or '<|thinking|>' in self.buffer.lower():
            self.in_thinking = True
        
        # Si estamos en modo pensamiento, buscar el cierre
        if self.in_thinking:
            if '</think>' in self.buffer.lower() or '</|thinking|>' in self.buffer.lower():
                # Filtrar todo el pensamiento acumulado
                filtered_buffer = filter_thinking_chunk(self.buffer)
                self.buffer = ""
                self.in_thinking = False
                return filtered_buffer
            else:
                # Seguimos acumulando hasta encontrar el cierre
                return ""
        else:
            # No estamos en pensamiento, devolver el chunk filtrado
            result = filter_thinking_chunk(chunk)
            return result


async def get_llm():
    """
    Obtiene una instancia del LLM principal.
    """
    # LLM principal (singleton con caché)
    global _llm
    async with _llm_lock:
        if _llm is None:
            _llm = ChatOllama(
                model=OLLAMA_MODEL,  # Usar el modelo principal de configuración
                base_url=OLLAMA_BASE_URL,
                temperature=LLM_TEMPERATURE,
                streaming=True,
                keep_alive=LLM_KEEP_ALIVE,
                request_timeout=LLM_REQUEST_TIMEOUT,
                reasoning=False,
                
                model_kwargs={
                    "num_ctx": LLM_NUM_CTX,
                    "num_predict": LLM_NUM_PREDICT,
                    "top_k": LLM_TOP_K,
                    "top_p": LLM_TOP_P,
                    "repeat_penalty": LLM_REPEAT_PENALTY,
                },

            )
        return _llm


async def get_fresh_llm():
    """
    Crear una nueva instancia de LLM sin contexto previo.
    Útil para consultas que NO deberían tener memoria de conversaciones anteriores.
    
    IMPORTANTE: Cada llamada crea una instancia completamente nueva,
    garantizando que no hay memoria de conversaciones previas.
    """
    fresh_llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=LLM_TEMPERATURE,
        streaming=True,
        keep_alive="0s",  # Inmediatamente liberar memoria después de usar
        request_timeout=LLM_REQUEST_TIMEOUT,
        reasoning=False,
        
        model_kwargs={
            "num_ctx": LLM_NUM_CTX,
            "num_predict": LLM_NUM_PREDICT,
            "top_k": LLM_TOP_K,
            "top_p": LLM_TOP_P,
            "repeat_penalty": LLM_REPEAT_PENALTY,
            "stop": ["<think>", "</think>", "<|thinking|>", "</|thinking|>"]
        }
    )
    
    return fresh_llm


async def clear_llm_context():
    """
    Limpiar el contexto de la instancia global del LLM.
    Esto fuerza al modelo a "olvidar" todas las conversaciones anteriores.
    """
    global _llm
    if _llm is not None:
        try:
            # Forzar que Ollama libere la memoria del modelo
            await _llm.ainvoke("") # Mensaje vacío para limpiar
            _llm = None  # Destruir la instancia actual
        except Exception as e:
            logger.warning(f"Error limpiando contexto LLM: {e}")
            _llm = None


async def consulta_simple(pregunta: str):
    """Consulta simple a Ollama sin RAG"""
    print(f"Consulta recibida: {pregunta}")
    llm = await get_llm()
    print("LLM:", llm)
    try:
        response = await llm.ainvoke(pregunta)
        raw_content = getattr(response, "content", str(response))
        
        # Aplicar filtrado de pensamiento
        filtered_content = filter_thinking_chunk(raw_content)
        
        print("Respuesta filtrada:", filtered_content)
        return {"respuesta": filtered_content}
    except Exception as e:
        print("Error:", e)
        return {"error": str(e)}


async def consulta_streaming(pregunta: str):
    """Consulta a Ollama con streaming de respuesta"""
    llm = await get_llm()
    print(f"Consulta recibida (streaming): {pregunta}")

    async def event_generator():
        async for chunk in llm.astream(pregunta):
            content = str(chunk.content)
            # Solo filtrar si realmente hay marcadores de pensamiento
            filtered_content = filter_thinking_chunk(content)
            if filtered_content.strip():  # Solo enviar si hay contenido después del filtrado
                yield filtered_content

    return StreamingResponse(event_generator(), media_type="text/plain")


async def consulta_general_streaming(prompt_completo: str):
    """Consulta general con RAG y streaming de respuesta"""
    print(f"Consulta general streaming iniciada")
    
    async def event_generator():
        llm = None
        try:
            # Obtener LLM con manejo de errores
            llm = await get_llm()
            print(f"LLM obtenido: {llm}")
            
            # Verificar conexión antes de hacer streaming
            print(f"Iniciando streaming para prompt de {len(prompt_completo)} caracteres")
            
            chunk_count = 0
            stream_buffer = StreamBuffer()
            
            async for chunk in llm.astream(prompt_completo):
                # Enviar cada chunk como Server-Sent Event
                content = getattr(chunk, 'content', str(chunk))
                if content and content.strip():
                    # Usar el buffer inteligente para filtrar pensamiento
                    filtered_content = stream_buffer.add_chunk(content)
                    if filtered_content and filtered_content.strip():  # Solo enviar si hay contenido válido
                        chunk_count += 1
                        print(f"Chunk {chunk_count} recibido: {content[:50]}...")
                        yield f"data: {filtered_content}\n\n"
            
            # Señal de finalización
            print(f"Streaming completado exitosamente. Total chunks: {chunk_count}")
            yield "data: [DONE]\n\n"
            
        except asyncio.CancelledError:
            print("Streaming cancelado por el cliente")
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"Error en streaming: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            # Cleanup si es necesario
            print("Limpieza del streaming completada")

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