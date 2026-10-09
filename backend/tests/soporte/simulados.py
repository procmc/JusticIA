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
import asyncio
import contextlib
import copy
import email.generator
import email.message
import email.policy
import importlib.abc
import io
import os
import re
import shutil
import sys
import tempfile
import threading
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


# --- Redis controlable (spec 003b, RA-02.11) -------------------------------------------------

# Cuánto espera, como máximo, una llamada retenida por `colgar()` antes de rendirse con un error de tiempo.
# Es solo una red de seguridad: una prueba que olvide `liberar()` no deja un hilo colgado para siempre.
TOPE_DE_RETENCION = 10.0

_clases_de_cliente: Dict[object, type] = {}


def _clase_de_cliente_controlable():
    """La clase del cliente que obedece al controlador; se crea al primer uso sobre el `redis.Redis` simulado.

    Se crea aquí dentro (y no al cargar el módulo) porque necesita `redis` y `fakeredis`, y este módulo
    se carga como plugin antes de que `pytest_configure` los instale. Guarda en un `dict` la clase creada
    para cada `redis.Redis` (la suite instala uno solo, pero así no se crean clases de más).
    """
    instalar_redis_simulado()
    import fakeredis
    import redis

    base = redis.Redis
    if not issubclass(base, fakeredis.FakeRedis):
        raise AbortoPruebas("RedisControlable solo funciona sobre el Redis simulado, y `redis.Redis` no lo es.")
    if base not in _clases_de_cliente:

        class ClienteControlable(base):
            """Un cliente del servidor simulado que antes de cada orden (o transacción) consulta al controlador."""

            def __init__(self, controlador, *args, **kwargs):
                self._controlador = controlador
                super().__init__(*args, **kwargs)

            def execute_command(self, *args, **opciones):
                self._controlador._pasar()
                return super().execute_command(*args, **opciones)

            def pipeline(self, *args, **kwargs):
                tuberia = super().pipeline(*args, **kwargs)
                original = tuberia.execute
                controlador = self._controlador

                def execute(*argumentos, **opciones):
                    # Las órdenes de una transacción se encolan sin hablar con el servidor: el momento en que
                    # puede fallar es `execute()` (MULTI/EXEC), también si se armó antes de `no_responde()`.
                    controlador._pasar()
                    return original(*argumentos, **opciones)

                tuberia.execute = execute
                return tuberia

        _clases_de_cliente[base] = ClienteControlable
    return _clases_de_cliente[base]


class RedisControlable:
    """El Redis simulado de la suite, con tres poderes para la prueba (RA-02.11).

    - No responder: `no_responde("conexion")` / `no_responde("tiempo")` hacen que toda orden (y toda
      transacción) lance el error de `redis` correspondiente hasta `responder_bien()`; `colgar()` retiene
      la llamada hasta `liberar()`, con un tope de seguridad (`TOPE_DE_RETENCION`).
    - Perder claves: `perder(clave)` y `perder_todas()` imitan el desalojo por memoria. Son un efecto del
      servidor, así que funcionan aunque el cliente no pueda hablarle.
    - Caducar por tiempo virtual: `avanzar(segundos)` recorta la caducidad de las claves con la API pública
      (`pttl`, `pexpire`, `delete`), sin esperar tiempo real; `vincular_reloj(reloj)` hace que
      `await reloj.avanzar(s)` también la aplique.

    Envuelve un cliente del MISMO servidor en memoria que usa toda la suite: lo que escribe lo ven los demás
    clientes de su base y la limpieza de cada prueba (`flushall`) lo vacía. Cualquier otro atributo se
    delega al cliente, así que se usa como un `redis.Redis` (`set`, `hset`, `pipeline`, `ttl`...), con
    respuestas en texto. Redis real no se usa en ninguna prueba.
    """

    def __init__(self, db: int = 3):
        self.db = db
        self._fallo: Optional[str] = None
        self._colgado = False
        self._liberada = threading.Event()
        self._hay_retenida = threading.Event()
        self._cerrojo = threading.Lock()
        self._vinculo = None
        self.cliente = _clase_de_cliente_controlable()(self, db=db, decode_responses=True)

    def __getattr__(self, nombre: str):
        # Solo se llama cuando el atributo no existe aquí: lo demás es del cliente. Los nombres propios
        # todavía sin asignar (durante `__init__`) no se delegan, para no entrar en un ciclo.
        if nombre.startswith("_") or nombre in ("cliente", "db"):
            raise AttributeError(nombre)
        return getattr(self.cliente, nombre)

    # --- Que no responda ---

    def no_responde(self, tipo: str = "conexion") -> None:
        """Desde ahora toda orden lanza el error de `redis` de ese tipo: «conexion» o «tiempo»."""
        if tipo not in ("conexion", "tiempo"):
            raise ValueError("`no_responde` admite «conexion» o «tiempo».")
        self._fallo = tipo

    def responder_bien(self) -> None:
        """Restablece el servicio: se acaban los errores y se libera lo que estuviera retenido."""
        self._fallo = None
        self.liberar()

    def colgar(self) -> None:
        """Desde ahora cada llamada queda retenida (un Redis colgado) hasta `liberar()` o el tope de seguridad."""
        self._liberada.clear()
        self._hay_retenida.clear()
        self._colgado = True

    def liberar(self) -> None:
        """Suelta las llamadas retenidas por `colgar()`: terminan normalmente."""
        self._colgado = False
        self._liberada.set()

    def esperar_retenida(self, tiempo: float = 2.0) -> bool:
        """Espera (tiempo real, como máximo `tiempo`) a que alguna llamada quede retenida; dice si ya hay una."""
        return self._hay_retenida.wait(tiempo)

    def _pasar(self) -> None:
        """Lo llama el cliente antes de cada orden: lanza el fallo, retiene la llamada o la deja pasar."""
        from redis.exceptions import ConnectionError as ErrorDeConexion
        from redis.exceptions import TimeoutError as ErrorDeTiempo

        if self._fallo == "conexion":
            raise ErrorDeConexion("Redis simulado: sin conexión")
        if self._fallo == "tiempo":
            raise ErrorDeTiempo("Redis simulado: tiempo agotado")
        if self._colgado:
            self._hay_retenida.set()
            if not self._liberada.wait(TOPE_DE_RETENCION):
                raise ErrorDeTiempo("Redis simulado: la llamada retenida agotó el tope de seguridad")

    # --- Perder claves ---

    def _interno(self, db: Optional[int] = None):
        """Un cliente del mismo servidor que NO obedece al controlador: lo que hace el servidor por su cuenta."""
        import redis

        return redis.Redis(db=self.db if db is None else db, decode_responses=True)

    def perder(self, clave: str) -> None:
        """El servidor pierde esa clave (desalojo por memoria). Perder una que no existe no es un error."""
        self._interno().delete(clave)

    def perder_todas(self) -> None:
        """El servidor pierde todas sus claves, de todas las bases."""
        self._interno().flushall()

    def claves(self, patron: str = "*") -> List[str]:
        """Las claves de la base del cliente que coinciden con el patrón, como texto y ordenadas."""
        return sorted(self._interno().scan_iter(match=patron))

    # --- Caducidad por tiempo virtual ---

    def avanzar(self, segundos: float) -> None:
        """Pasan `segundos` de tiempo virtual: se recorta la caducidad de las claves y caducan las que se cumplen.

        Usa solo órdenes públicas (`pttl`, `pexpire`, `delete`) y recorre todas las bases, porque el tiempo
        es del servidor. Las claves sin caducidad no se tocan.
        """
        if segundos < 0:
            raise ValueError("El Redis controlable solo avanza (segundos >= 0).")
        milisegundos = int(round(segundos * 1000))
        for numero in list(_estado["servidor_redis"].dbs):
            cliente = self._interno(numero)
            for clave in list(cliente.scan_iter()):
                restante = cliente.pttl(clave)
                if restante < 0:  # -1 sin caducidad, -2 ya no existe
                    continue
                if restante - milisegundos <= 0:
                    cliente.delete(clave)
                else:
                    cliente.pexpire(clave, restante - milisegundos)

    def vincular_reloj(self, reloj) -> None:
        """Hace que `await reloj.avanzar(s)` también avance este Redis (el reloj sigue siendo el de la prueba)."""
        self.desvincular_reloj()
        original = reloj.avanzar

        async def avanzar(segundos: float) -> None:
            # Primero el servidor: así, cuando el reloj libera una espera, el Redis ya está en su nuevo momento.
            self.avanzar(segundos)
            await original(segundos)

        self._vinculo = (reloj, reloj.__dict__.get("avanzar"))
        reloj.avanzar = avanzar

    def desvincular_reloj(self) -> None:
        """Devuelve al reloj vinculado su `avanzar` original (no hace nada si no hay ninguno)."""
        if self._vinculo is None:
            return
        reloj, previo = self._vinculo
        self._vinculo = None
        if previo is None:
            reloj.__dict__.pop("avanzar", None)
        else:
            reloj.avanzar = previo

    def cerrar(self) -> None:
        """Lo que hace la fixture al terminar la prueba: libera lo retenido y desvincula el reloj."""
        self.liberar()
        self.desvincular_reloj()


@pytest.fixture
def redis_controlable(monkeypatch):
    """El Redis simulado con fallos, pérdida de claves y caducidad por tiempo virtual (RA-02.11).

    No hace falta pedirlo para que Redis esté simulado (lo está en toda la suite): solo lo piden las pruebas
    que necesitan controlarlo. Además (spec 003b, T4) hace que el repositorio de la recuperación hable con este
    cliente: se parcha `obtener_cliente` del repositorio, así la recuperación obedece a `no_responde`, `colgar`
    y `avanzar`. Al terminar libera las llamadas retenidas y desvincula el reloj; las claves las vacía la
    limpieza de cada prueba y `monkeypatch` restaura el repositorio.
    """
    from app.repositories import recuperacion_estado_repository

    controlable = RedisControlable()
    monkeypatch.setattr(recuperacion_estado_repository, "obtener_cliente", lambda: controlable.cliente)
    try:
        yield controlable
    finally:
        controlable.cerrar()


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
    """Un correo que se intentó enviar. Su `repr` omite el contenido para no mostrarlo en los informes.

    Sigue siendo un diccionario de cuatro claves (`a`, `asunto`, `html`, `texto`). Lo que suma RA-02.10 es un
    atributo, no una clave, para que un `json.dumps(intentos)` no lo arrastre: `bytes_serializados` es el
    mensaje tal como se enviaría por la red (ver `CorreoSimulado`).
    """

    bytes_serializados: bytes = b""

    def __repr__(self) -> str:
        return f"Intento(a={self['a']!r}, asunto={self['asunto']!r})"


class ContenidoReal:
    """El contenido de un correo SIN reemplazar lo que la prueba declaró con `ocultar()` (RA-02.10).

    Existe para que la prueba lea de ahí la contraseña temporal o el código que el sistema envió. Su
    `repr` no muestra nada del contenido, así que no aparece en un informe ni en un fallo de aserción.
    Quien extraiga un secreto debe envolverlo en `Contrasena` (`tests/soporte/datos.py`).
    """

    __slots__ = ("a", "asunto", "html", "texto")

    def __init__(self, a: str, asunto: str, html: str, texto: str):
        self.a, self.asunto, self.html, self.texto = a, asunto, html, texto

    def __repr__(self) -> str:
        return "ContenidoReal(<oculto>)"


class CorreoSimulado(_Simulado):
    """Reemplaza a `aiosmtplib.send`: falla a voluntad, registra los correos y hace observable el fallo.

    `EmailService.send_email` real sigue ejecutándose: si aquí se lanza una excepción, la atrapa y
    devuelve `False`, igual que en el sistema. Las credenciales que recibe `aiosmtplib.send`
    (`username`, `password`, `hostname`...) se descartan: nunca se leen ni se guardan.

    Desde la spec 003a (RA-02.10) también:
    - `tiempos_maximos`: el `timeout` con que se llamó cada envío (`None` si no se pasó), en orden.
    - `Intento.bytes_serializados`: el mensaje aplanado con el mismo generador que usa `aiosmtplib`, para que
      la prueba lo lea con un lector independiente (`email.message_from_bytes`). Son los bytes REALES: no se
      les aplica `ocultar()` (un valor dentro de un cuerpo en base64 no se podría reemplazar) y no salen en ningún `repr`.
    - `contenido_real()`: el contenido sin ocultar de un intento.
    - `no_responde()` y `lento()`: un servidor que nunca contesta y otro que tarda, medido con el reloj
      controlable. NO reproducen el diálogo SMTP (EHLO, STARTTLS, AUTH...), los límites del servidor ni TLS.

    Desde la spec 003b (T7, RF-03.3) también `retener()` y `liberar()`: el envío queda registrado como intento y
    detenido hasta que la prueba lo libera, para observar qué hace la aplicación MIENTRAS el envío sigue pendiente.
    `esperar_retenido()` espera (tiempo real, con tope) a que llegue un envío retenido y `envios_retenidos` los cuenta.
    Los envíos retenidos viven en el bucle de eventos donde se invocaron: se retienen y se liberan en el mismo bucle.
    """

    def __init__(self):
        self.intentos: List[Intento] = []
        self.tiempos_maximos: List[Optional[float]] = []
        self._contenidos: List[ContenidoReal] = []
        self._error: Optional[BaseException] = None
        self._secretos: List[str] = []
        self._cuelga = False
        self._demora: Optional[tuple] = None  # (reloj, operaciones, segundos)
        self._retiene = False
        self._retenidos: List["asyncio.Future"] = []  # envíos detenidos; `liberar` los resuelve
        self._esperas_de_retenido: List["asyncio.Future"] = []  # quienes esperan a que llegue un envío retenido

    def fallar(self, excepcion: Optional[BaseException] = None) -> None:
        import aiosmtplib

        self._error = excepcion or aiosmtplib.SMTPConnectError("El servidor de correo no responde (simulado)")

    def responder_bien(self) -> None:
        """Vuelve a la normalidad: sin error, sin colgarse, sin demora y sin retener (lo retenido se libera)."""
        self._error = None
        self._cuelga = False
        self._demora = None
        self.liberar()

    def retener(self) -> None:
        """Desde ahora cada envío queda registrado como intento y detenido hasta `liberar()` (RF-03.3, spec 003b)."""
        self._retiene = True

    def liberar(self, error: Optional[BaseException] = None) -> None:
        """Deja de retener y suelta los envíos detenidos: terminan bien o, si se da `error`, lanzando ese error.

        Es lo que ve el sistema cuando el servidor de correo contesta (o cae) mientras el envío estaba en curso. No hace
        nada si no había nada retenido. Se llama desde el mismo bucle donde se retuvo, o desde otro hilo.
        """
        self._retiene = False
        pendientes, self._retenidos = self._retenidos, []
        for envio in pendientes:
            try:
                envio.get_loop().call_soon_threadsafe(self._soltar, envio, error)
            except RuntimeError:  # el bucle ya se cerró: nadie espera este envío
                pass

    @staticmethod
    def _soltar(envio: "asyncio.Future", error: Optional[BaseException]) -> None:
        if not envio.done():
            envio.set_result(error)

    @property
    def envios_retenidos(self) -> int:
        """Cuántos envíos siguen detenidos por `retener()`."""
        return len(self._retenidos)

    async def esperar_retenido(self, tiempo: float = 2.0) -> bool:
        """Espera (tiempo REAL, como máximo `tiempo`) a que haya un envío retenido; dice si lo hay.

        Sirve para saber, sin adivinar vueltas del bucle, que la aplicación ya invocó el envío y este sigue pendiente.
        """
        if self._retenidos:
            return True
        espera = asyncio.get_running_loop().create_future()
        self._esperas_de_retenido.append(espera)
        try:
            await asyncio.wait_for(espera, tiempo)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            if espera in self._esperas_de_retenido:
                self._esperas_de_retenido.remove(espera)

    def no_responde(self) -> None:
        """El envío registra el intento y se queda esperando para siempre: solo un límite de tiempo lo corta."""
        self._cuelga = True
        self._demora = None

    def lento(self, reloj, operaciones: int, segundos: float) -> None:
        """El servidor tarda `segundos` en cada una de `operaciones` (conexión, saludo, autenticación, envío...).

        Mide con `reloj` (el controlable): el envío termina cuando el reloj avanzó `operaciones * segundos`.
        Si además la prueba llamó a `fallar()`, el error llega después de esa espera.
        """
        self._demora = (reloj, operaciones, segundos)
        self._cuelga = False

    def ocultar(self, *secretos: str) -> None:
        """Contraseñas o códigos que la prueba conoce: se reemplazan por `<oculto>` en lo que se registra."""
        self._secretos.extend(secreto for secreto in secretos if secreto)

    def contenido_real(self, indice: int = -1) -> ContenidoReal:
        """El contenido sin ocultar del intento `indice` (por omisión, el último)."""
        try:
            return self._contenidos[indice]
        except IndexError:
            raise LookupError(f"No hay un intento de correo en la posición {indice} ({len(self._contenidos)} registrados).") from None

    @staticmethod
    def _campos(mensaje) -> Dict[str, str]:
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
        return campos

    @staticmethod
    def _aplanar(mensaje) -> bytes:
        """Los bytes del mensaje, como los aplana `aiosmtplib.send` (sin los encabezados `Bcc`)."""
        if isinstance(mensaje, bytes):
            return mensaje
        if isinstance(mensaje, str):
            return mensaje.encode("utf-8")
        if not isinstance(mensaje, email.message.Message):
            return b""
        copia = copy.copy(mensaje)
        del copia["Bcc"]
        del copia["Resent-Bcc"]
        politica = email.policy.SMTP if isinstance(copia, email.message.EmailMessage) else email.policy.compat32
        with io.BytesIO() as salida:
            email.generator.BytesGenerator(salida, policy=politica).flatten(copia)
            return salida.getvalue()

    def _registrar(self, mensaje) -> Intento:
        reales = self._campos(mensaje)
        self._contenidos.append(ContenidoReal(**reales))
        campos = dict(reales)
        for secreto in self._secretos:
            campos = {nombre: valor.replace(secreto, "<oculto>") for nombre, valor in campos.items()}
        intento = Intento(campos)
        intento.bytes_serializados = self._aplanar(mensaje)
        return intento

    async def enviar(self, mensaje, /, *args, **kwargs):
        self.intentos.append(self._registrar(mensaje))
        self.tiempos_maximos.append(kwargs.get("timeout"))
        if self._retiene:
            retenido = asyncio.get_running_loop().create_future()
            self._retenidos.append(retenido)
            for espera in self._esperas_de_retenido:
                if not espera.done():
                    espera.set_result(True)
            try:
                error_al_liberar = await retenido  # `liberar` lo resuelve con `None` o con el error que debe lanzar el envío
            finally:  # si el envío se cancela (por su plazo) mientras está retenido, deja de contar como retenido
                if retenido in self._retenidos:
                    self._retenidos.remove(retenido)
            if error_al_liberar is not None:
                raise error_al_liberar
        if self._cuelga:
            await asyncio.get_running_loop().create_future()  # nadie lo resuelve: solo una cancelación lo termina
        if self._demora is not None:
            reloj, operaciones, segundos = self._demora
            for _ in range(operaciones):
                await reloj.dormir(segundos)
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
