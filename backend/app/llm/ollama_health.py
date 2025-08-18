import httpx
from app.config.config import OLLAMA_BASE_URL

async def verificar_ollama():
    """Verifica si Ollama está corriendo y qué modelos tiene"""
    try:
        async with httpx.AsyncClient() as client:
            # Verificar que Ollama esté corriendo
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            
            if response.status_code == 200:
                modelos = response.json()
                return {
                    "status": "conectado",
                    "url": OLLAMA_BASE_URL,
                    "modelos_disponibles": [model["name"] for model in modelos.get("models", [])],
                    "total_modelos": len(modelos.get("models", []))
                }
            else:
                return {
                    "status": "error",
                    "url": OLLAMA_BASE_URL,
                    "mensaje": f"HTTP {response.status_code}"
                }
                
    except Exception as e:
        return {
            "status": "desconectado",
            "url": OLLAMA_BASE_URL,
            "error": str(e),
            "solucion": "¿Está Ollama corriendo? Ejecuta: ollama serve"
        }
