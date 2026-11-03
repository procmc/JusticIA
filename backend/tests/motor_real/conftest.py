"""Fixtures de las pruebas del marcador `motor_real` (spec 007, CF-1; plan §15).

Estas pruebas hablan con el Ollama real: solo corren a mano con `pytest -m motor_real` y la variable
`SERVIA_MOTOR_REAL_URL`. No tocan SQL Server ni Qdrant (arman las entradas en memoria con textos `PRUEBA`).
Si falta la variable, o su host no es local (RNF-09), la corrida se detiene con un mensaje en español.
"""
import os
from urllib.parse import urlparse

import httpx
import pytest

HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1", "ollama", "host.docker.internal"}
MODELO_POR_OMISION = "llama3.1:8b"
TIEMPO_MAXIMO_LLAMADA = 900.0  # segundos: incluye cargar el modelo en frío


class MotorReal:
    """Cliente mínimo del `POST /api/chat` nativo de Ollama, sin caché de prefijos (`keep_alive: 0`)."""

    def __init__(self, url: str, modelo: str):
        self.url = url.rstrip("/")
        self.modelo = modelo
        self.version = ""

    def contar(self, mensajes: list) -> dict:
        """Una llamada con las mismas opciones que `get_llm` (ventana y reserva de `CONFIGURACION`).

        Devuelve `prompt_eval_count` (tokens de entrada que cuenta el motor, plantilla incluida) y `eval_count`.
        """
        from app.config.contexto_config import CONFIGURACION

        cuerpo = {
            "model": self.modelo,
            "messages": mensajes,
            "stream": False,
            "keep_alive": 0,
            "options": {"num_ctx": CONFIGURACION.ventana, "num_predict": CONFIGURACION.reserva, "temperature": 0},
        }
        respuesta = httpx.post(f"{self.url}/api/chat", json=cuerpo, timeout=TIEMPO_MAXIMO_LLAMADA)
        respuesta.raise_for_status()
        datos = respuesta.json()
        return {"real": datos.get("prompt_eval_count"), "salida": datos.get("eval_count")}


@pytest.fixture(scope="session")
def motor() -> MotorReal:
    """El motor real, verificado: variable presente, host local y modelo descargado."""
    url = os.environ.get("SERVIA_MOTOR_REAL_URL", "").strip()
    if not url:
        pytest.exit("Falta SERVIA_MOTOR_REAL_URL (por ejemplo http://ollama:11434): las pruebas motor_real usan el Ollama real.", returncode=2)
    host = (urlparse(url).hostname or "").lower()
    if host not in HOSTS_LOCALES:
        pytest.exit(f"El host «{host}» no es local: ServIA no usa servicios de IA en la nube (RNF-09).", returncode=2)
    cliente = MotorReal(url, os.environ.get("SERVIA_MOTOR_REAL_MODELO", MODELO_POR_OMISION))
    try:
        cliente.version = httpx.get(f"{cliente.url}/api/version", timeout=10).json().get("version", "?")
        modelos = [m.get("name") for m in httpx.get(f"{cliente.url}/api/tags", timeout=10).json().get("models", [])]
    except Exception as error:
        pytest.exit(f"No se pudo consultar el motor en {cliente.url} ({type(error).__name__}).", returncode=2)
    if cliente.modelo not in modelos:
        pytest.exit(f"El modelo {cliente.modelo} no está descargado en el motor.", returncode=2)
    print(f"\nMotor real: Ollama {cliente.version}, modelo {cliente.modelo}")
    return cliente
