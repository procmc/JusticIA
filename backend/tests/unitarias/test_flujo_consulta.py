"""Flujo del turno del chat (spec 007, T6: RF-11.62, RF-11.64, RF-11.68, RF-16.60, RF-16.62, RF-21.60).

`stream_chain_response` es el orquestador del turno: emite las etapas, la señal de vida y el tope, detecta la desconexión, y
guarda el historial y registra la bitácora solo cuando corresponde. Aquí se prueba con el motor simulado y el reloj
controlable (tiempo virtual: 180 s no cuestan nada), sin base de datos ni Qdrant. Los textos esperados están escritos
literalmente, tal como los define la spec, para que un cambio del código no mueva también la prueba.
"""
import asyncio
import dataclasses
import json

import pytest

from app.config.contexto_config import CONFIGURACION
from app.services.RAG import general_chains

ETAPAS = ["Procesando consulta", "Analizando documentos", "Generando respuesta"]
TEXTO_LARGA = "La pregunta es demasiado larga. Acórtela e intente de nuevo."
TEXTO_TOPE = "La consulta tardó demasiado. Intente de nuevo."


class Registro:
    """El registrador de la bitácora que arma el router: anota el motivo con el que se le llama (`None`: turno terminado)."""

    def __init__(self):
        self.motivos = []

    async def __call__(self, motivo):
        self.motivos.append(motivo)


class CadenaFalsa:
    """Una cadena con el contrato que usa el orquestador: `cabe_la_pregunta`, `astream` y `guardar_turno`."""

    def __init__(self, guion=None, cabe=True):
        self.guion = guion  # corrutina `guion(cadena)` que produce los eventos; sin ella, no hace nada
        self.cabe = cabe
        self.puerta = asyncio.Event()
        self.empezo = False
        self.cancelada = False
        self.guardados = []

    def cabe_la_pregunta(self, pregunta):
        return self.cabe

    async def astream(self, input_dict, config=None):
        self.empezo = True
        try:
            if self.guion is not None:
                async for evento in self.guion(self):
                    yield evento
        except asyncio.CancelledError:
            self.cancelada = True
            raise

    def guardar_turno(self, pregunta, texto, config=None):
        self.guardados.append((pregunta, texto))


async def _esperar_siempre(cadena):
    await cadena.puerta.wait()
    yield {"answer": "nunca llega"}


class Conectado:
    """`Request` falso: la conexión sigue abierta hasta que `cerrar()` la corta."""

    def __init__(self):
        self.cortada = False

    def cerrar(self):
        self.cortada = True

    async def is_disconnected(self):
        return self.cortada


@pytest.fixture(autouse=True)
def configuracion_del_flujo(monkeypatch):
    """Señal de vida cada 10 s y tope de 180 s, aunque el servidor tenga otros valores."""
    monkeypatch.setattr(
        general_chains, "CONFIGURACION",
        dataclasses.replace(CONFIGURACION, senal_de_vida_segundos=10, tiempo_maximo_segundos=180), raising=False,
    )


def _evento(trozo: str) -> dict:
    assert trozo.startswith("data: ") and trozo.endswith("\n\n"), f"no es un evento del stream: {trozo!r}"
    return json.loads(trozo.removeprefix("data: "))


async def _recolectar(generador, eventos: list) -> None:
    async for trozo in generador:
        eventos.append(_evento(trozo))


def _correr(cadena, registro, http_request=None, pregunta="¿Qué dice el documento de PRUEBA?"):
    """Corre el turno completo con tiempo real (sin esperas largas) y devuelve los eventos."""
    eventos = []
    generador = general_chains.stream_chain_response(
        cadena, {"input": pregunta}, {"configurable": {"session_id": "PRUEBA"}}, http_request, registrar=registro
    )
    asyncio.run(_recolectar(generador, eventos))
    return eventos


class RecuperadorFalso:
    def __init__(self, error=None):
        self.error = error

    async def ainvoke(self, consulta):
        if self.error is not None:
            raise self.error
        return []


def _cadena_real(recuperador):
    from app.services.RAG.prompts import INSTRUCCIONES_GENERAL

    return general_chains.CadenaArmada("general", INSTRUCCIONES_GENERAL, recuperador, historial_de=None)


@pytest.mark.requisito("RF-11.64")
def test_etapas_en_orden(ollama_simulado):
    """RF-11.64 (regresión) · las tres etapas llegan en orden y antes del primer texto; después, el texto y el fin."""
    ollama_simulado.responder("Respuesta de PRUEBA con varias palabras.")
    registro = Registro()

    eventos = _correr(_cadena_real(RecuperadorFalso()), registro)

    tipos = [e["type"] for e in eventos]
    assert [e["content"] for e in eventos if e["type"] == "etapa"] == ETAPAS
    assert tipos[:3] == ["etapa"] * 3, f"las etapas deben ir antes del primer texto: {tipos}"
    assert tipos[-1] == "done" and "chunk" in tipos
    assert registro.motivos == [None]


@pytest.mark.requisito("RF-11.64")
def test_error_del_motor_tras_dos_etapas():
    """RF-11.64 · si algo falla tras «Analizando documentos», llegan las dos etapas ya emitidas y el error, sin la que falta;
    el turno se registra como «error del motor» y no queda en el historial (RF-11.68, RF-21.60)."""
    registro = Registro()
    cadena = _cadena_real(RecuperadorFalso(error=RuntimeError("fallo de PRUEBA")))
    cadena.guardar_turno = lambda *a, **k: pytest.fail("un turno con error no se guarda en el historial")

    eventos = _correr(cadena, registro)

    tipos = [e["type"] for e in eventos]
    assert tipos[:3] == ["etapa", "etapa", "error"], tipos
    assert [e["content"] for e in eventos if e["type"] == "etapa"] == ETAPAS[:2]
    assert "chunk" not in tipos
    assert registro.motivos == ["error del motor"]


@pytest.mark.requisito("RF-11.64")
def test_error_del_motor_al_generar_tras_tres_etapas(ollama_simulado):
    """RF-11.64 · si el motor cae al empezar a generar, las tres etapas ya se habían emitido y luego llega el error."""
    ollama_simulado.fallar(ConnectionError("motor caído de PRUEBA"))
    registro = Registro()

    eventos = _correr(_cadena_real(RecuperadorFalso()), registro)

    tipos = [e["type"] for e in eventos]
    assert tipos[:4] == ["etapa", "etapa", "etapa", "error"], tipos
    assert registro.motivos == ["error del motor"]


@pytest.mark.requisito("RF-11.62")
def test_pregunta_larga_sin_etapas():
    """RF-11.62 · una pregunta que no cabe se rechaza antes de cualquier etapa o llamada: solo el error, y queda registrada."""
    registro = Registro()
    cadena = CadenaFalsa(cabe=False)

    eventos = _correr(cadena, registro)

    assert [(e["type"], e["content"]) for e in eventos] == [("error", TEXTO_LARGA)]
    assert cadena.empezo is False, "la cadena no debió arrancar"
    assert registro.motivos == ["pregunta demasiado larga"] and cadena.guardados == []


@pytest.mark.requisito("RF-11.68")
@pytest.mark.requisito("RF-21.60")
def test_turno_terminado_guarda_registra_y_avisa():
    """RF-11.68, RF-21.60 · al terminar, el turno se guarda una vez con la pregunta y el texto completo, se registra sin motivo
    y se avisa a quien genera el título; todo ocurre antes de enviar el evento final."""
    async def guion(cadena):
        yield {"etapa": "Generando respuesta"}
        yield {"answer": "Hola "}
        yield {"answer": "mundo"}

    registro, avisos = Registro(), []
    cadena = CadenaFalsa(guion)
    eventos = []
    generador = general_chains.stream_chain_response(
        cadena, {"input": "¿Hola?"}, {}, None, registrar=registro, al_terminar=lambda: avisos.append(list(registro.motivos))
    )
    asyncio.run(_recolectar(generador, eventos))

    assert [e["type"] for e in eventos] == ["etapa", "chunk", "chunk", "done"]
    assert cadena.guardados == [("¿Hola?", "Hola mundo")]
    assert registro.motivos == [None]
    assert avisos == [[None]], "el título se genera una vez, con el turno ya registrado"


@pytest.mark.requisito("RF-16.60")
def test_senal_de_vida_cada_intervalo(reloj_controlable):
    """RF-16.60 · mientras la cadena no entrega nada, llega una señal de vida cada 10 s (ni antes ni después); la señal no es
    texto ni cambia la etapa, y al llegar el texto la respuesta termina bien."""
    async def escenario():
        cadena = CadenaFalsa(_esperar_siempre)
        eventos = []
        turno = asyncio.ensure_future(_recolectar(general_chains.stream_chain_response(
            cadena, {"input": "¿Hola?"}, {}, None, registrar=Registro()), eventos))
        await reloj_controlable.avanzar(9)
        assert [e["type"] for e in eventos] == [], "antes de 10 s no debe haber señal"
        await reloj_controlable.avanzar(1)
        assert [e["type"] for e in eventos] == ["vida"]
        await reloj_controlable.avanzar(10)
        await reloj_controlable.avanzar(10)
        assert [e["type"] for e in eventos] == ["vida"] * 3
        assert all(e["content"] == "" and e["done"] is False for e in eventos)
        cadena.puerta.set()
        await asyncio.wait_for(turno, 5)
        return eventos

    eventos = asyncio.run(escenario())
    assert [e["type"] for e in eventos][-2:] == ["chunk", "done"]


@pytest.mark.requisito("RF-16.62")
@pytest.mark.requisito("RF-11.68")
@pytest.mark.requisito("RF-21.60")
def test_tope_cancela(reloj_controlable):
    """RF-16.62 · al cumplirse los 180 s la cadena se cancela (el motor deja de generar), llega el error del tope sin señal de
    vida de más, el turno se registra como «tiempo máximo agotado» y no se guarda en el historial."""
    async def escenario():
        cadena, registro, eventos = CadenaFalsa(_esperar_siempre), Registro(), []
        turno = asyncio.ensure_future(_recolectar(general_chains.stream_chain_response(
            cadena, {"input": "¿Hola?"}, {}, None, registrar=registro), eventos))
        await reloj_controlable.avanzar(179)
        assert not turno.done(), "a los 179 s todavía no vence el tope"
        await reloj_controlable.avanzar(1)
        await asyncio.wait_for(turno, 5)
        return cadena, registro, eventos

    cadena, registro, eventos = asyncio.run(escenario())
    assert (eventos[-1]["type"], eventos[-1]["content"]) == ("error", TEXTO_TOPE)
    assert [e["type"] for e in eventos].count("vida") == 17 and all(e["type"] == "vida" for e in eventos[:-1])
    assert cadena.cancelada is True
    assert registro.motivos == ["tiempo máximo agotado"] and cadena.guardados == []


@pytest.mark.requisito("RF-16.62")
@pytest.mark.requisito("RF-11.68")
@pytest.mark.requisito("RF-21.60")
def test_desconexion_cancela_sin_historial_ni_bitacora(reloj_controlable):
    """RF-16.62 · si el usuario cierra la conexión, se detecta a lo sumo en un intervalo: la cadena se cancela y no se guarda
    ni se registra nada."""
    async def escenario():
        cadena, registro, eventos, conexion = CadenaFalsa(_esperar_siempre), Registro(), [], Conectado()
        turno = asyncio.ensure_future(_recolectar(general_chains.stream_chain_response(
            cadena, {"input": "¿Hola?"}, {}, conexion, registrar=registro), eventos))
        await reloj_controlable.avanzar(10)
        conexion.cerrar()
        await reloj_controlable.avanzar(10)
        await asyncio.wait_for(turno, 5)
        return cadena, registro, eventos

    cadena, registro, eventos = asyncio.run(escenario())
    assert [e["type"] for e in eventos] == ["vida"], "tras cerrar la conexión no se envía nada más"
    assert cadena.cancelada is True
    assert registro.motivos == [] and cadena.guardados == []


class _BitacoraFalsa:
    """Sustituye a `bitacora_service`: anota con qué se le llama en vez de escribir en la base."""

    def __init__(self):
        self.llamadas = []

    async def registrar(self, **kwargs):
        self.llamadas.append(kwargs)


class _ExpedienteRepoFalso:
    def obtener_por_numero(self, db, numero):
        return None


def _registrar_consulta(monkeypatch, pregunta, motivo=None, tipo="general"):
    """Corre `registrar_consulta_rag` con la bitácora y el repositorio simulados; devuelve lo que se habría guardado."""
    from app.services.bitacora.rag_audit_service import rag_audit_service
    falsa = _BitacoraFalsa()
    monkeypatch.setattr(rag_audit_service, "bitacora_service", falsa)
    monkeypatch.setattr(rag_audit_service, "expediente_repo", _ExpedienteRepoFalso())
    asyncio.run(rag_audit_service.registrar_consulta_rag(
        db=None, usuario_id="PRUEBA", pregunta=pregunta, session_id="s", tipo_consulta=tipo, motivo=motivo))
    return falsa.llamadas[0]


@pytest.mark.requisito("RF-21.61")
def test_RF_21_61_rechazada_larga_recortada_en_texto_e_info(monkeypatch):
    """RF-21.61 · una pregunta rechazada por larga guarda 200 caracteres y «…», en la descripción y en `pregunta_completa`."""
    pregunta = "p" * 30000
    llamada = _registrar_consulta(monkeypatch, pregunta, motivo="pregunta demasiado larga")
    assert llamada["texto"] == "Consulta RAG general: " + "p" * 200 + "…"
    assert llamada["info_adicional"]["pregunta_completa"] == "p" * 200 + "…"


@pytest.mark.requisito("RF-21.61")
def test_RF_21_61_aceptada_larga_texto_recortado_info_entera(monkeypatch):
    """RF-21.61 · una pregunta larga que sí se atendió recorta la descripción, pero conserva `pregunta_completa` entera."""
    pregunta = "p" * 1000
    llamada = _registrar_consulta(monkeypatch, pregunta)
    assert llamada["texto"] == "Consulta RAG general: " + "p" * 200 + "…"
    assert llamada["info_adicional"]["pregunta_completa"] == pregunta


@pytest.mark.requisito("RF-21.61")
def test_RF_21_61_pregunta_de_200_sin_marca(monkeypatch):
    """RF-21.61 · una pregunta de exactamente 200 caracteres no se recorta ni lleva marca."""
    pregunta = "p" * 200
    llamada = _registrar_consulta(monkeypatch, pregunta, motivo="pregunta demasiado larga")
    assert llamada["texto"] == "Consulta RAG general: " + pregunta
    assert llamada["info_adicional"]["pregunta_completa"] == pregunta


@pytest.mark.requisito("RF-21.61")
def test_RF_21_61_pregunta_de_201_con_marca(monkeypatch):
    """RF-21.61 · con 201 caracteres ya se recorta a 200 y se marca con «…»."""
    llamada = _registrar_consulta(monkeypatch, "p" * 201)
    assert llamada["texto"] == "Consulta RAG general: " + "p" * 200 + "…"
