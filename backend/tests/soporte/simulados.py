"""Piezas simuladas de la suite (spec 002, RA-02.5; T7 suma Ollama, HTR, audio y correo).

- Redis: `fakeredis` reemplaza a `redis.Redis` ANTES de importar nada de `app`, porque
  `session_store.py` crea `ConversationStore()` al importarse y éste hace `ping()`, y
  `progress_tracker.py` crea su cliente al importarse. Lo instala `pytest_configure`.
- Celery: las tareas se ejecutan dentro del proceso, sin publicarse en ninguna cola. Además,
  `REDIS_URL` apunta a un host `.invalid`, de modo que ni siquiera una tarea que escapara del
  modo inmediato podría llegar al Redis real ni ser consumida por el worker real.
- Archivos: `uploads/` se calcula con `Path(__file__)` en el sistema, así que no se desvía
  cambiando de directorio; se reemplazan `BASE_UPLOAD_DIR` y `upload_dir` por subcarpetas de una
  carpeta temporal en `/tmp` (fuera de `/app`, para no disparar el `--reload` del servidor). La sesión la
  elimina al cerrar, después de contar los residuos (T8).
- Ollama, HTR, audio y correo (T7, RA-02.6): cada uno tiene su fixture, responde lo que la prueba
  define y registra lo recibido. Se parchea en el punto más bajo que comparten todos los módulos
  del sistema (el singleton `_llm`, la instancia `htr_service`, el cargador de faster-whisper y
  `aiosmtplib.send`), así no importa cómo los haya importado cada módulo. `comprobar_simulados`
  aborta nombrando el servicio si el código todavía usaría el real.
- Guardianes de las unitarias: `instalar_guardianes` bloquea SQL Server, Qdrant y Tika reales y
  deja el modelo de embeddings en un falso de tamaño `DIM` (lo instala `tests/unitarias/conftest.py`).
  También oculta los singletons de Qdrant del sistema (`qdrant_backend._qdrant_client` y
  `_langchain_vectorstore`), que la integración deja creados con un cliente real.

Este módulo es también un plugin de pytest (lo declara el `conftest.py` raíz) y nunca importa
`app` ni `celery_app` al cargarse: lo hace dentro de las funciones y las fixtures.
"""
import contextlib
import email.message
import importlib.abc
import os
import re
import shutil
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Mapping, Optional

import pytest

from tests.soporte.proteccion import AbortoPruebas

# Estado de la sesión: el servidor de Redis simulado y la carpeta temporal.
_estado: Dict[str, object] = {"servidor_redis": None, "carpeta": None}

# Valores de Celery que fija el modo inmediato.
_CLAVES_CELERY = ("task_always_eager", "task_eager_propagates", "broker_url", "result_backend")


# --- Redis -----------------------------------------------------------------------------------

def instalar_redis_simulado():
    """Reemplaza `redis.Redis` y `redis.Redis.from_url` por un cliente de `fakeredis`.

    Todos los clientes comparten un único servidor en memoria (como en un Redis real: las
    conversaciones y el progreso de ingesta usan clientes distintos del mismo servidor). Es
    idempotente: una segunda llamada devuelve el mismo servidor sin envolver la clase otra vez.
    """
    if _estado["servidor_redis"] is not None:
        return _estado["servidor_redis"]

    import fakeredis
    import redis

    servidor = fakeredis.FakeServer()

    class RedisSimulado(fakeredis.FakeRedis):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("server", servidor)
            super().__init__(*args, **kwargs)

        @classmethod
        def from_url(cls, url, **kwargs):
            kwargs.setdefault("server", servidor)
            return super().from_url(url, **kwargs)

        def info(self, section=None, *args, **kwargs):
            # fakeredis no implementa INFO; el sistema solo lo usa para estadísticas de memoria.
            return {"used_memory": 0}

    redis.Redis = RedisSimulado
    _estado["servidor_redis"] = servidor
    return servidor


# --- Celery ----------------------------------------------------------------------------------

def fijar_celery_inmediato(aplicacion) -> Dict[str, object]:
    """Pone la aplicación Celery en modo inmediato y devuelve sus valores anteriores.

    `task_always_eager`: `.delay()` ejecuta la tarea en el mismo proceso, sin cola;
    `task_eager_propagates`: una excepción de la tarea llega a la prueba;
    broker y resultados en memoria, para que ninguna consulta de estado toque un Redis.
    """
    anteriores = {clave: aplicacion.conf.get(clave) for clave in _CLAVES_CELERY}
    aplicacion.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        broker_url="memory://",
        result_backend="cache+memory://",
    )
    return anteriores


def restaurar_celery(aplicacion, anteriores: Dict[str, object]) -> None:
    """Devuelve a la aplicación Celery los valores que tenía antes de `fijar_celery_inmediato`."""
    aplicacion.conf.update(**anteriores)


@pytest.fixture
def aplicacion_celery():
    """La aplicación Celery del sistema. Se importa aquí porque `celery_app` importa `database.py`.

    Solo la piden las pruebas de integración (ya con la base de pruebas creada).
    """
    from celery_app import celery_app

    return celery_app


@pytest.fixture
def celery_inmediato(aplicacion_celery):
    """Las tareas se ejecutan dentro del proceso de pruebas y la configuración se restaura al terminar.

    Es opt-in (no se aplica sola a cada prueba): solo la piden las pruebas que llaman a `.delay()`, para
    que corran la tarea dentro del proceso. La garantía de que ninguna prueba publica en el Redis real no
    depende de pedirla: `REDIS_URL` y el broker apuntan a un host `.invalid`, así que una prueba que llame
    a `.delay()` sin esta fixture falla por red en lugar de encolar la tarea en el Redis de desarrollo.
    Se pide solo en integración porque `celery_app` importa `database.py` y la base de pruebas ya debe existir.
    """
    anteriores = fijar_celery_inmediato(aplicacion_celery)
    yield aplicacion_celery
    restaurar_celery(aplicacion_celery, anteriores)


# --- Carpeta temporal de archivos ------------------------------------------------------------

def carpeta_temporal_de_la_sesion() -> Path:
    """Crea (una sola vez) la carpeta temporal de la sesión en `/tmp` y la devuelve."""
    if _estado["carpeta"] is None:
        _estado["carpeta"] = Path(tempfile.mkdtemp(prefix="servia_pruebas_"))
    return _estado["carpeta"]


def carpeta_temporal_actual() -> Optional[Path]:
    """La carpeta temporal de la sesión si ya se creó (no la crea): el conteo de residuos la mira sin provocarla."""
    return _estado["carpeta"]


def eliminar_carpeta_temporal() -> None:
    """Elimina la carpeta temporal de la sesión; si hace falta, otra llamada crea una nueva.

    La elimina `pytest_sessionfinish` (`conftest.py` raíz) DESPUÉS de contar los residuos: si la eliminara una fixture
    de sesión, el conteo del cierre ya no vería los archivos que una prueba hubiera dejado.
    """
    carpeta: Optional[Path] = _estado["carpeta"]
    _estado["carpeta"] = None
    if carpeta is not None:
        shutil.rmtree(carpeta, ignore_errors=True)


@contextlib.contextmanager
def desviar_carpetas() -> Iterator[Path]:
    """Desvía `BASE_UPLOAD_DIR` (archivos) y `upload_dir` (avatares) a una subcarpeta temporal.

    Entrega la subcarpeta (con `uploads/` y `avatares/` dentro), restaura las dos rutas y elimina
    la subcarpeta al terminar. Nunca se escribe en el `uploads/` real.
    """
    from app.services.avatar_service import avatar_service
    from app.services.documentos.file_management_service import file_management_service

    carpeta = Path(tempfile.mkdtemp(dir=carpeta_temporal_de_la_sesion()))
    archivos, avatares = carpeta / "uploads", carpeta / "avatares"
    archivos.mkdir()
    avatares.mkdir()
    base_anterior, avatares_anterior = file_management_service.BASE_UPLOAD_DIR, avatar_service.upload_dir
    file_management_service.BASE_UPLOAD_DIR = archivos
    avatar_service.upload_dir = avatares
    try:
        yield carpeta
    finally:
        file_management_service.BASE_UPLOAD_DIR = base_anterior
        avatar_service.upload_dir = avatares_anterior
        shutil.rmtree(carpeta, ignore_errors=True)


@pytest.fixture
def carpeta_archivos() -> Iterator[Path]:
    """Carpeta temporal para los archivos de la prueba; desvía y restaura las rutas de `uploads/`."""
    with desviar_carpetas() as carpeta:
        yield carpeta


# --- Ollama, HTR, audio y correo simulados (T7, RA-02.6) -------------------------------------------

class _Simulado:
    """Marca de los simulados: `comprobar_simulados` la busca para confirmar que el código usa un falso."""

    es_simulado = True


def _es_simulado(objeto) -> bool:
    """¿Es `objeto` un simulado, o un método ligado a uno?"""
    return isinstance(getattr(objeto, "__self__", objeto), _Simulado)


def _trozos(texto: str) -> List[str]:
    """Parte una respuesta en palabras (con su espacio), como llegaría de un LLM en streaming."""
    return re.findall(r"\S+\s*", texto) or [texto]


def _clase_llm_simulado():
    """Crea (una sola vez) la clase del LLM simulado; LangChain solo se importa si una prueba la pide.

    Es un `BaseChatModel` de verdad, no un objeto suelto: así funciona dentro de las cadenas
    (`prompt | llm | parser`) con `invoke`, `ainvoke` y `astream`, igual que `ChatOllama`.
    """
    if "clase_llm" in _estado:
        return _estado["clase_llm"]

    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage, AIMessageChunk
    from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
    from pydantic import ConfigDict, Field

    class LLMSimulado(_Simulado, BaseChatModel):
        """LLM que transmite la respuesta que define la prueba y registra cada pregunta recibida."""

        model_config = ConfigDict(arbitrary_types_allowed=True)

        respuesta: str = "Respuesta simulada del modelo."
        preguntas: list = Field(default_factory=list)
        error: Optional[BaseException] = None

        @property
        def _llm_type(self) -> str:
            return "ollama-simulado"

        def responder(self, texto: str) -> None:
            """Define la respuesta (y quita un fallo definido antes)."""
            self.respuesta = texto
            self.error = None

        def fallar(self, excepcion: Optional[BaseException] = None) -> None:
            """Hace que la próxima consulta lance `excepcion`, como un Ollama caído."""
            self.error = excepcion or RuntimeError("Ollama no responde (simulado)")

        def _registrar(self, mensajes) -> None:
            self.preguntas.append("\n".join(str(m.content) for m in mensajes))
            if self.error is not None:
                raise self.error

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            self._registrar(messages)
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.respuesta))])

        def _stream(self, messages, stop=None, run_manager=None, **kwargs):
            self._registrar(messages)
            for trozo in _trozos(self.respuesta):
                yield ChatGenerationChunk(message=AIMessageChunk(content=trozo))

    _estado["clase_llm"] = LLMSimulado
    return LLMSimulado


class HTRSimulado(_Simulado):
    """Reemplaza a `htr_service`: devuelve el texto definido y registra nombre y tamaño (no el contenido)."""

    def __init__(self):
        self.texto = "Texto manuscrito simulado."
        self.error: Optional[BaseException] = None
        self.llamadas: List[dict] = []

    def responder(self, texto: str) -> None:
        self.texto = texto
        self.error = None

    def fallar(self, excepcion: Optional[BaseException] = None) -> None:
        self.error = excepcion or RuntimeError("El servidor HTR no responde (simulado)")

    def extract_text(self, content: bytes, filename: str = "") -> str:
        self.llamadas.append({"nombre": filename, "bytes": len(content)})
        if self.error is not None:
            raise self.error
        return self.texto

    def is_available(self) -> bool:
        return self.error is None


class ModeloWhisperSimulado(_Simulado):
    """Ocupa el lugar del `WhisperModel` de faster-whisper, que nunca se carga."""


class EstrategiaSimulada(_Simulado):
    """Ocupa el lugar de las estrategias directa y por trozos; el orquestador real sigue ejecutándose."""

    def __init__(self, audio: "AudioSimulado", nombre: str, atiende: bool):
        self._audio, self._nombre, self._atiende = audio, nombre, atiende

    def can_handle(self, file_size_mb: float, error_context: Optional[str] = None) -> bool:
        return self._atiende

    def get_strategy_name(self) -> str:
        return self._nombre

    async def transcribe(self, temp_file_path, filename, file_size_mb, progress_tracker=None) -> str:
        return self._audio.transcribir(temp_file_path, filename)


class AudioSimulado(_Simulado):
    """Reemplaza la carga de faster-whisper: devuelve la transcripción definida y registra nombre y tamaño."""

    def __init__(self, orquestador):
        self._orquestador = orquestador
        self.texto = "Transcripción simulada."
        self.error: Optional[BaseException] = None
        self.llamadas: List[dict] = []
        self.modelo = ModeloWhisperSimulado()
        # Solo la estrategia directa atiende: si falla, no hay otra a la que recurrir.
        self.estrategia_directa = EstrategiaSimulada(self, "direct_transcription", True)
        self.estrategia_por_trozos = EstrategiaSimulada(self, "chunking_transcription", False)

    def responder(self, texto: str) -> None:
        self.texto = texto
        self.error = None

    def fallar(self, excepcion: Optional[BaseException] = None) -> None:
        self.error = excepcion or RuntimeError("faster-whisper falló (simulado)")

    def transcribir(self, ruta_temporal, nombre: str) -> str:
        self.llamadas.append({"nombre": nombre, "bytes": os.path.getsize(ruta_temporal)})
        if self.error is not None:
            raise self.error
        return self.texto

    def cargar_modelo(self):
        """Sustituye a `_load_faster_whisper_model`: instala las estrategias simuladas y no carga nada."""
        self._orquestador.direct_strategy = self.estrategia_directa
        self._orquestador.chunking_strategy = self.estrategia_por_trozos
        return self.modelo


class Intento(dict):
    """Un correo que se intentó enviar. Su `repr` omite el contenido para no mostrarlo en los informes."""

    def __repr__(self) -> str:
        return f"Intento(a={self['a']!r}, asunto={self['asunto']!r})"


class CorreoSimulado(_Simulado):
    """Reemplaza a `aiosmtplib.send`: falla a voluntad, registra los correos y hace observable el fallo.

    `EmailService.send_email` real sigue ejecutándose: si aquí se lanza una excepción, la atrapa y
    devuelve `False`, igual que en el sistema. Las credenciales que recibe `aiosmtplib.send`
    (`username`, `password`, `hostname`...) se descartan: nunca se leen ni se guardan.
    """

    def __init__(self):
        self.intentos: List[Intento] = []
        self._error: Optional[BaseException] = None
        self._secretos: List[str] = []

    def fallar(self, excepcion: Optional[BaseException] = None) -> None:
        import aiosmtplib

        self._error = excepcion or aiosmtplib.SMTPConnectError("El servidor de correo no responde (simulado)")

    def responder_bien(self) -> None:
        self._error = None

    def ocultar(self, *secretos: str) -> None:
        """Contraseñas o códigos que la prueba conoce: se reemplazan por `<oculto>` en lo que se registra."""
        self._secretos.extend(secreto for secreto in secretos if secreto)

    def _registrar(self, mensaje) -> Intento:
        campos = {"a": "", "asunto": "", "html": "", "texto": ""}
        if isinstance(mensaje, email.message.Message):
            campos["a"] = str(mensaje["To"] or "")
            campos["asunto"] = str(mensaje["Subject"] or "")
            for parte in mensaje.walk():
                carga = None if parte.is_multipart() else parte.get_payload(decode=True)
                if carga is None:
                    continue
                contenido = carga.decode(parte.get_content_charset() or "utf-8", errors="replace")
                if parte.get_content_type() == "text/html":
                    campos["html"] += contenido
                elif parte.get_content_type() == "text/plain":
                    campos["texto"] += contenido
        for secreto in self._secretos:
            campos = {nombre: valor.replace(secreto, "<oculto>") for nombre, valor in campos.items()}
        return Intento(campos)

    async def enviar(self, mensaje, /, *args, **kwargs):
        self.intentos.append(self._registrar(mensaje))
        if self._error is not None:
            raise self._error
        return {}, "OK (simulado)"

    def __repr__(self) -> str:
        return f"CorreoSimulado(intentos={len(self.intentos)}, falla={self._error is not None})"


def _ollama_es_simulado() -> bool:
    from app.llm import llm_service

    return isinstance(llm_service._llm, _Simulado)


def _htr_es_simulado() -> bool:
    from app.services.ingesta.htr_service import htr_service

    return _es_simulado(htr_service.extract_text) and _es_simulado(htr_service.is_available)


def _audio_es_simulado() -> bool:
    from app.services.ingesta.audio_transcription.whisper_service import audio_processor

    return _es_simulado(audio_processor._load_faster_whisper_model)


def _correo_es_simulado() -> bool:
    import aiosmtplib

    return _es_simulado(aiosmtplib.send)


# Cómo se nombra cada servicio en el mensaje de aborto y cómo se comprueba.
_SERVICIOS_SIMULADOS: Dict[str, tuple] = {
    "ollama": ("Ollama (el LLM)", _ollama_es_simulado),
    "htr": ("el servidor de reconocimiento de escritura (HTR)", _htr_es_simulado),
    "audio": ("la transcripción de audio (faster-whisper)", _audio_es_simulado),
    "correo": ("el envío de correo", _correo_es_simulado),
}


def comprobar_simulados(nombres=None) -> None:
    """Aborta, nombrándolos, si el código del sistema todavía usaría el servicio real de alguno de `nombres`.

    `nombres` son claves de `_SERVICIOS_SIMULADOS` (por omisión, las cuatro); una clave desconocida es
    un error de la suite (`ValueError`). Cada fixture lo llama justo después de parchear, así que un
    parche que no alcanzó al código detiene la corrida en lugar de llegar a Ollama, HTR o el correo.
    """
    nombres = list(_SERVICIOS_SIMULADOS) if nombres is None else list(nombres)
    desconocidos = [nombre for nombre in nombres if nombre not in _SERVICIOS_SIMULADOS]
    if desconocidos:
        raise ValueError(f"Servicio simulado desconocido: {', '.join(desconocidos)}")

    reales = [_SERVICIOS_SIMULADOS[nombre][0] for nombre in nombres if not _SERVICIOS_SIMULADOS[nombre][1]()]
    if reales:
        raise AbortoPruebas(
            "Se aborta la suite de pruebas: el código del sistema usaría el servicio real de "
            f"{', '.join(reales)} en lugar del simulado."
        )


def _exigir_simulados(*nombres: str) -> None:
    """Como `comprobar_simulados`, pero desde una fixture: detiene toda la corrida con `pytest.exit`."""
    try:
        comprobar_simulados(nombres)
    except AbortoPruebas as aborto:
        pytest.exit(str(aborto), returncode=2)


@pytest.fixture
def ollama_simulado(monkeypatch):
    """LLM simulado: `get_llm()` devuelve este objeto para todo el sistema (se reemplaza el singleton)."""
    from app.llm import llm_service

    simulado = _clase_llm_simulado()()
    monkeypatch.setattr(llm_service, "_llm", simulado)
    _exigir_simulados("ollama")
    return simulado


@pytest.fixture
def htr_simulado(monkeypatch):
    """Servidor HTR simulado: `htr_service.extract_text` e `is_available` pasan a ser los del simulado."""
    from app.services.ingesta.htr_service import htr_service

    simulado = HTRSimulado()
    monkeypatch.setattr(htr_service, "extract_text", simulado.extract_text)
    monkeypatch.setattr(htr_service, "is_available", simulado.is_available)
    _exigir_simulados("htr")
    return simulado


@pytest.fixture
def audio_simulado(monkeypatch):
    """Transcripción simulada: el modelo de faster-whisper no se carga; el orquestador real sí se ejecuta."""
    from app.services.ingesta.audio_transcription.whisper_service import audio_processor

    simulado = AudioSimulado(audio_processor)
    monkeypatch.setattr(audio_processor, "_load_faster_whisper_model", simulado.cargar_modelo)
    monkeypatch.setattr(audio_processor, "direct_strategy", simulado.estrategia_directa)
    monkeypatch.setattr(audio_processor, "chunking_strategy", simulado.estrategia_por_trozos)
    _exigir_simulados("audio")
    return simulado


@pytest.fixture
def correo_simulado(monkeypatch):
    """Correo simulado: `aiosmtplib.send` pasa a ser el del simulado; por omisión responde bien."""
    import aiosmtplib

    simulado = CorreoSimulado()
    monkeypatch.setattr(aiosmtplib, "send", simulado.enviar)
    _exigir_simulados("correo")
    return simulado


# --- Guardianes de las pruebas unitarias (T7, RA-02.6) ---------------------------------------------

class ServicioRealProhibido(Exception):
    """Una prueba unitaria intentó usar un servicio real (SQL Server, Qdrant, Tika o el modelo de embeddings)."""


class ModeloEmbeddingsFalso:
    """Ocupa el lugar de `SentenceTransformer`: vectores de `dim` dimensiones, deterministas por texto.

    Registra los textos que recibe (`textos`) para comprobar los prefijos `query: ` y `passage: `, que
    pone `EmbeddingsWrapper`, el código real del sistema.
    """

    def __init__(self, dim: int):
        self.dim = dim
        self.textos: List[str] = []

    def _vector(self, texto: str):
        import numpy

        vector = numpy.random.default_rng(zlib.crc32(texto.encode("utf-8"))).standard_normal(self.dim)
        return vector / numpy.linalg.norm(vector)

    def encode(self, textos):
        import numpy

        un_solo_texto = isinstance(textos, str)
        lista = [textos] if un_solo_texto else list(textos)
        self.textos.extend(lista)
        if not lista:
            return numpy.zeros((0, self.dim))
        vectores = numpy.stack([self._vector(texto) for texto in lista])
        return vectores[0] if un_solo_texto else vectores


class BuscadorGuardian(importlib.abc.MetaPathFinder):
    """Actúa en el momento de importar: bloquea módulos antes de ejecutarlos y parchea otros al importarlos.

    Los módulos pesados (Qdrant, embeddings) solo se cargan si una prueba los pide, y `database.py`
    (que se conecta a SQL Server al importarse) nunca llega a ejecutarse.
    """

    def __init__(self, parches: Mapping[str, Callable], bloqueados: Mapping[str, Callable]):
        self.parches = dict(parches)
        self.bloqueados = dict(bloqueados)

    def find_spec(self, nombre, ruta=None, destino=None):
        if nombre in self.bloqueados:
            self.bloqueados[nombre]()  # lanza ServicioRealProhibido
        parche = self.parches.get(nombre)
        if parche is None:
            return None

        especificacion = None
        for buscador in sys.meta_path:
            if buscador is self or not hasattr(buscador, "find_spec"):
                continue
            especificacion = buscador.find_spec(nombre, ruta, destino)
            if especificacion is not None:
                break
        if especificacion is None or not hasattr(especificacion.loader, "exec_module"):
            return especificacion

        ejecutar_original = especificacion.loader.exec_module

        def ejecutar_y_parchear(modulo):
            ejecutar_original(modulo)
            parche(modulo)

        especificacion.loader.exec_module = ejecutar_y_parchear
        return especificacion


class GuardianServicios:
    """Hace fallar a la prueba unitaria que use un servicio real y deja los embeddings en un falso.

    Cada intento se registra en `intentos`: aunque el código del sistema atrape la excepción, la
    prueba falla al cerrarse (`exigir_sin_intentos`) salvo que la haya esperado (`reconocer`).
    """

    def __init__(self):
        self.intentos: List[str] = []
        self._parches: Optional[pytest.MonkeyPatch] = None
        self._buscador: Optional[BuscadorGuardian] = None

    # Registro de intentos.

    def registrar(self, servicio: str) -> None:
        self.intentos.append(servicio)

    def reconocer(self, *servicios: str) -> None:
        """La prueba esperaba el intento: se quita del registro (todos, si no se indican servicios)."""
        if servicios:
            self.intentos[:] = [intento for intento in self.intentos if intento not in servicios]
        else:
            self.intentos.clear()

    def exigir_sin_intentos(self) -> None:
        if self.intentos:
            nombres = ", ".join(sorted(set(self.intentos)))
            pytest.fail(
                f"La prueba unitaria intentó usar servicios reales ({nombres}). Las unitarias usan "
                "simulados; lo que necesita el servicio real va en una prueba de integración.",
                pytrace=False,
            )

    def prohibido(self, servicio: str) -> Callable:
        """Función que registra el intento y lanza `ServicioRealProhibido` (acepta cualquier argumento)."""
        def _prohibido(*args, **kwargs):
            self.registrar(servicio)
            raise ServicioRealProhibido(
                f"Una prueba unitaria intentó usar {servicio} real. Las unitarias usan simulados; "
                "lo que necesita el servicio real va en una prueba de integración."
            )

        return _prohibido

    # Instalación.

    def instalar(self) -> None:
        self._vaciar_pool_del_motor()
        self._parches = pytest.MonkeyPatch()
        parches = {
            "qdrant_client": self._parchar_qdrant,
            "app.services.ingesta.tika_service": self._parchar_tika,
            "app.embeddings.embeddings": self._parchar_embeddings,
            "app.vectorstore.qdrant_backend": self._parchar_vectorstore,
        }
        self._buscador = BuscadorGuardian(parches, {"app.db.database": self.prohibido("SQL Server")})
        sys.meta_path.insert(0, self._buscador)
        for nombre, parche in parches.items():
            if nombre in sys.modules:  # ya importado por una prueba anterior: se parchea ahora
                parche(sys.modules[nombre])
        try:
            import pyodbc
        except ImportError:  # sin conector no hay forma de llegar a SQL Server
            return
        self._parches.setattr(pyodbc, "connect", self.prohibido("SQL Server"))

    @staticmethod
    def _vaciar_pool_del_motor() -> None:
        """Cierra las conexiones que haya en el pool del motor de SQLAlchemy (plan, §12, O1).

        Desde T4 toda corrida importa `app.db.database`, así que ya no hay importación que bloquear.
        Las pruebas de integración corren antes y dejan conexiones reales en el pool; sin vaciarlo,
        `engine.connect()` las reutilizaría y una unitaria usaría SQL Server sin que el guardián se
        entere. Vacío, el motor tiene que abrir una conexión nueva y la frena el bloqueo de `pyodbc`.
        """
        motor = getattr(sys.modules.get("app.db.database"), "engine", None)
        if motor is not None:
            motor.dispose()

    def desinstalar(self) -> None:
        """Quita los guardianes y restaura lo parchado. Se puede llamar más de una vez."""
        if self._buscador is not None and self._buscador in sys.meta_path:
            sys.meta_path.remove(self._buscador)
        self._buscador = None
        if self._parches is not None:
            self._parches.undo()
            self._parches = None

    def _parchar_qdrant(self, modulo) -> None:
        for nombre in ("QdrantClient", "AsyncQdrantClient"):
            clase = getattr(modulo, nombre, None)
            if clase is not None and self._parches is not None:
                self._parches.setattr(clase, "__init__", self.prohibido("Qdrant"))

    def _parchar_vectorstore(self, modulo) -> None:
        """Oculta a la unitaria el cliente y el vectorstore de Qdrant que el sistema guarda como singletons (M1).

        Las pruebas de integración usan `get_vectorstore_backend()` y dejan esos dos singletons creados con un
        cliente real. El parche de `QdrantClient.__init__` solo frena clientes NUEVOS, así que sin esto una
        unitaria reutilizaría el real sin que el guardián se entere. En `None`, el sistema tiene que crear uno
        y lo frena el guardián; al desinstalar vuelve lo que había (la integración sigue usando su cliente).
        """
        if self._parches is None:
            return
        for singleton in ("_qdrant_client", "_langchain_vectorstore"):
            self._parches.setattr(modulo, singleton, None)

    def _parchar_tika(self, modulo) -> None:
        if self._parches is None:
            return
        for metodo in ("extract_text", "is_available"):
            self._parches.setattr(modulo.TikaService, metodo, self.prohibido("Tika"))

    def _parchar_embeddings(self, modulo) -> None:
        if self._parches is None:
            return
        from app.config.config import DIM

        self._parches.setattr(modulo, "SentenceTransformer", self.prohibido("el modelo de embeddings"))
        falso = modulo.EmbeddingsWrapper(ModeloEmbeddingsFalso(int(DIM)), modulo.EMBEDDING_MODEL)
        self._parches.setattr(modulo, "_embeddings", falso)


def instalar_guardianes() -> GuardianServicios:
    """Crea e instala los guardianes de una prueba unitaria. Quien la llama debe llamar a `desinstalar()`."""
    guardian = GuardianServicios()
    guardian.instalar()
    return guardian
