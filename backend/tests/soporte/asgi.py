"""Llamar a la aplicación por ASGI dentro del bucle de la prueba (spec 003b, T7; plan, decisión 11).

El `TestClient` de Starlette y el `ASGITransport` de `httpx` devuelven la respuesta cuando la aplicación terminó, y eso
incluye las tareas posteriores a la respuesta (`BackgroundTasks`). Con ellos una prueba no puede ver «la API ya respondió y el
envío del correo sigue pendiente», que es justo lo que exige RF-03.3. `llamar` invoca la aplicación directamente, como lo
haría un servidor ASGI, y separa los dos momentos:

- `respuesta`: un futuro que se resuelve cuando llega el cuerpo completo de la respuesta (aunque la aplicación siga
  trabajando).
- `tarea`: la aplicación completa, con sus tareas posteriores; termina cuando ellas terminan (o falla con su error).

Corre dentro del bucle de eventos de la prueba (por ejemplo, el de `asyncio.run`), así que la prueba puede controlar en ese
mismo bucle lo que la aplicación espera: el correo simulado retenido (`CorreoSimulado.retener`), el reloj controlable o un
Redis colgado. Como un servidor real, avisa de la desconexión (`http.disconnect`) cuando la respuesta ya se envió.

No agrega dependencias y no importa `app` al cargarse (regla de la suite). No ejecuta el arranque ni el cierre de la aplicación
(`lifespan`), igual que el `TestClient` de la suite, que no se usa con `with`: ese arranque cargaría los embeddings.
"""
import asyncio
import json as _json
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple


class RespuestaAsgi:
    """La respuesta HTTP completa de una llamada por ASGI. Su `repr` solo muestra el código: el cuerpo puede traer un token."""

    def __init__(self, status_code: int, headers: List[Tuple[str, str]], content: bytes):
        self.status_code = status_code
        self.headers: Dict[str, str] = {nombre.lower(): valor for nombre, valor in headers}
        self.content = content

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return _json.loads(self.content)

    def __repr__(self) -> str:
        return f"RespuestaAsgi(status_code={self.status_code})"


class Llamada:
    """Una llamada en curso: `respuesta` (futuro de `RespuestaAsgi`) y `tarea` (la aplicación entera, tareas posteriores incluidas)."""

    def __init__(self, respuesta: "asyncio.Future[RespuestaAsgi]", tarea: "asyncio.Task[None]"):
        self.respuesta = respuesta
        self.tarea = tarea

    def __repr__(self) -> str:
        return f"Llamada(respondida={self.respuesta.done()}, terminada={self.tarea.done()})"


def llamar(
    app: Callable,
    metodo: str,
    ruta: str,
    json: Any = None,
    cabeceras: Optional[Mapping[str, str]] = None,
) -> Llamada:
    """Invoca `app` por ASGI y devuelve enseguida la `Llamada`, sin esperar a que la aplicación responda.

    Debe llamarse dentro de un bucle de eventos en marcha (`RuntimeError` si no lo hay). `json` se envía como cuerpo con su
    tipo de contenido; `cabeceras` se suman a las que se arman solas. Si la aplicación falla antes de responder, `respuesta`
    y `tarea` fallan con ese error; si falla después (en una tarea posterior), solo `tarea` falla.
    """
    try:
        bucle = asyncio.get_running_loop()
    except RuntimeError:
        raise RuntimeError(
            "`asgi.llamar` solo funciona dentro del bucle de eventos de la prueba (por ejemplo, dentro de `asyncio.run`)."
        ) from None

    cuerpo = b"" if json is None else _json.dumps(json).encode("utf-8")
    encabezados = [(b"host", b"testserver"), (b"content-length", str(len(cuerpo)).encode("ascii"))]
    if json is not None:
        encabezados.append((b"content-type", b"application/json"))
    for nombre, valor in (cabeceras or {}).items():
        encabezados.append((nombre.lower().encode("latin-1"), str(valor).encode("latin-1")))
    ruta_sin_consulta, _, consulta = ruta.partition("?")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": metodo.upper(),
        "scheme": "http",
        "path": ruta_sin_consulta,
        "raw_path": ruta_sin_consulta.encode("utf-8"),
        "query_string": consulta.encode("utf-8"),
        "root_path": "",
        "headers": encabezados,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    respuesta: "asyncio.Future[RespuestaAsgi]" = bucle.create_future()
    respuesta_completa = asyncio.Event()
    estado: Dict[str, Any] = {"entregado": False, "codigo": None, "cabeceras": [], "trozos": []}

    async def recibir() -> dict:
        if not estado["entregado"]:
            estado["entregado"] = True
            return {"type": "http.request", "body": cuerpo, "more_body": False}
        await respuesta_completa.wait()  # como un servidor: la desconexión se avisa cuando la respuesta ya se envió
        return {"type": "http.disconnect"}

    async def enviar(mensaje: dict) -> None:
        if mensaje["type"] == "http.response.start":
            estado["codigo"] = mensaje["status"]
            estado["cabeceras"] = [
                (nombre.decode("latin-1"), valor.decode("latin-1")) for nombre, valor in mensaje.get("headers", [])
            ]
        elif mensaje["type"] == "http.response.body":
            estado["trozos"].append(mensaje.get("body", b""))
            if not mensaje.get("more_body", False):
                if not respuesta.done():
                    respuesta.set_result(RespuestaAsgi(estado["codigo"], estado["cabeceras"], b"".join(estado["trozos"])))
                respuesta_completa.set()

    async def ejecutar() -> None:
        try:
            await app(scope, recibir, enviar)
        except BaseException as error:
            if not respuesta.done():
                respuesta.set_exception(error)
                respuesta.exception()  # se marca como leída: si nadie la espera, no queda un aviso de «nunca recuperada»
            raise
        finally:
            respuesta_completa.set()
        if not respuesta.done():
            respuesta.set_exception(RuntimeError("La aplicación terminó sin enviar una respuesta completa."))
            respuesta.exception()

    return Llamada(respuesta, bucle.create_task(ejecutar()))
