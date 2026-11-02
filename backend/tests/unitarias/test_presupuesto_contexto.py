"""Pruebas de T3 (spec 007: RF-11.61, RF-11.62, RF-11.65, RF-11.66 en el cálculo, RF-12.60, RF-12.62).

El módulo `app.services.RAG.presupuesto_contexto` es puro: calcula cuántos tokens caben en una llamada al
motor y arma la entrada (historial y fragmentos) dentro del presupuesto de `CONFIGURACION`. Los textos son
inventados (letras repetidas); el conteo es el mismo estimador que usa el código.
"""
import math

import pytest

from app.config.contexto_config import CONFIGURACION as CFG
from app.services.RAG import presupuesto_contexto as pc

CHATS = ["general", "tema", "notebook"]
P = CFG.presupuesto


def _t(n: int) -> int:
    return math.ceil(n / CFG.caracteres_por_token)


def _frag(i: int, largo: int, archivo: str = None, tema: str = "PRUEBA tema") -> pc.Fragmento:
    return pc.Fragmento(
        texto="x" * largo,
        archivo=archivo or f"PRUEBA_archivo_{i}.pdf",
        tema=tema,
        ruta=f"/api/descargar/PRUEBA_ruta_{i}",
        pagina_inicio=1,
        pagina_fin=2,
    )


INSTR = "i" * 3000
PREG = "p" * 200


def _armar(chat="general", historial=(), fragmentos=(), pregunta=PREG, solicitud=None):
    return pc.armar_respuesta(chat, INSTR, pregunta, list(historial), list(fragmentos), solicitud)


def _max_pregunta(chat: str) -> int:
    """Largo máximo de pregunta que RF-11.62 acepta (el menor n tal que n + 1 ya no cabe)."""
    lo, hi = 0, 6 * P
    while lo < hi:
        medio = (lo + hi + 1) // 2
        if pc.cabe_la_pregunta(chat, INSTR, "p" * medio):
            lo = medio
        else:
            hi = medio - 1
    return lo


def test_historial_largo():
    """RF-11.61 · el historial usa como máximo el 20 % del presupuesto, con los mensajes más recientes."""
    historial = [f"{i}" + "h" * 2000 for i in range(20)]
    r = _armar(historial=historial, fragmentos=[_frag(1, 500)])
    assert r.historial == historial[-2:]
    assert sum(_t(len(m)) for m in r.historial) <= 0.2 * P


def test_fragmentos_de_sobra():
    """RF-11.61 · con fragmentos de sobra se envían 8, en orden de relevancia y enteros."""
    frs = [_frag(i, 1000) for i in range(15)]
    r = _armar(fragmentos=frs)
    assert [f.archivo for f in r.fragmentos] == [f.archivo for f in frs[:8]]
    assert all(("x" * 1000) in r.sistema for _ in r.fragmentos)


def test_ambos():
    """RF-11.61 · historial largo y muchos fragmentos: la entrada total cabe y el historial respeta el 20 %."""
    historial = ["h" * 2000 for _ in range(20)]
    frs = [_frag(i, 2800) for i in range(15)]
    r = _armar(historial=historial, fragmentos=frs)
    assert r.tokens_total <= P
    assert sum(_t(len(m)) for m in r.historial) <= 0.2 * P
    assert 0 < len(r.fragmentos) <= 8


def test_historial_corto_cede():
    """RF-11.61 · un historial corto cede su espacio a los fragmentos."""
    frs = [_frag(i, 2400) for i in range(8)]
    largo = _armar(historial=["h" * 2000 for _ in range(20)], fragmentos=frs)
    corto = _armar(historial=["hola"], fragmentos=frs)
    assert len(corto.fragmentos) == 8
    assert len(largo.fragmentos) < 8


def test_mensaje_mayor_que_20():
    """RF-11.61 · un mensaje que no cabe entero se omite junto con los anteriores."""
    historial = ["corto", "otro corto", "m" * 6000]
    r = _armar(historial=historial)
    assert r.historial == []
    historial2 = ["m" * 6000, "corto"]
    assert _armar(historial=historial2).historial == ["corto"]


def test_fragmento_grande_saltado():
    """RF-11.61 · el fragmento que no cabe se omite completo y se prueba el siguiente."""
    frs = [_frag(1, 500), _frag(2, 6 * P), _frag(3, 500)]
    r = _armar(fragmentos=frs)
    assert [f.archivo for f in r.fragmentos] == [frs[0].archivo, frs[2].archivo]


@pytest.mark.parametrize("chat", CHATS)
def test_justo_bajo_el_limite_llama(chat):
    """RF-11.62 · pregunta justo en el límite: cabe, no se recorta y cabe un fragmento (RF-12.62 en el notebook)."""
    n = _max_pregunta(chat)
    pregunta = "p" * n
    assert pc.cabe_la_pregunta(chat, INSTR, pregunta)
    r = _armar(chat=chat, pregunta=pregunta, fragmentos=[_frag(1, CFG.fragmento_tamano_maximo)])
    assert r.pregunta == pregunta
    assert len(r.fragmentos) == 1
    assert r.tokens_total <= P


@pytest.mark.parametrize("chat", CHATS)
def test_justo_sobre_el_limite(chat):
    """RF-11.62 · un carácter más y no cabe: el motor no debe recibir llamadas."""
    n = _max_pregunta(chat)
    assert not pc.cabe_la_pregunta(chat, INSTR, "p" * (n + 1))
    assert not pc.cabe_la_pregunta(chat, INSTR, "p" * (n + 50))


def test_espacio_minimo_por_omision():
    """RF-11.62 · espacio mínimo: 572 tokens (1500 + 500 caracteres) y 658 en el notebook (+300)."""
    assert pc.espacio_minimo("general") == 572
    assert pc.espacio_minimo("tema") == 572
    assert pc.espacio_minimo("notebook") == 658


def test_encabezado_y_sin_rastros_de_omitidos():
    """RF-12.60 · cada fragmento enviado lleva archivo, tema y ruta; los omitidos no dejan rastro."""
    frs = [_frag(1, 500), _frag(2, 6 * P), _frag(3, 500)]
    r = _armar(fragmentos=frs, historial=["hola"])
    for f in (frs[0], frs[2]):
        assert f"Archivo: {f.archivo}" in r.sistema
        assert f"Tema: {f.tema}" in r.sistema
        assert f"Ruta: {f.ruta}" in r.sistema
    entrada = r.sistema + "".join(r.historial) + r.pregunta
    assert frs[1].archivo not in entrada
    assert frs[1].ruta not in entrada


def test_lista_solo_enviados():
    """RF-12.62 · la lista del notebook solo tiene archivos de fragmentos enviados, sin repetir."""
    frs = [_frag(1, 500, archivo="PRUEBA_a.pdf"), _frag(2, 6 * P, archivo="PRUEBA_omitido.pdf"),
           _frag(3, 500, archivo="PRUEBA_a.pdf"), _frag(4, 500, archivo="PRUEBA_b.pdf")]
    r = _armar(chat="notebook", fragmentos=frs)
    assert r.archivos == ["PRUEBA_a.pdf", "PRUEBA_b.pdf"]
    assert "PRUEBA_omitido.pdf" not in r.sistema


def test_lista_titulo_y_formato_del_plan():
    """RF-12.62 · título exacto «ARCHIVOS DE ESTA CONSULTA:» (el que cita la regla 3) y líneas `- "<nombre>"`."""
    frs = [_frag(1, 500, archivo="PRUEBA_a.pdf"), _frag(2, 500, archivo="PRUEBA_b.pdf")]
    r = _armar(chat="notebook", fragmentos=frs)
    esperado = f'{INSTR}\n\nARCHIVOS DE ESTA CONSULTA:\n- "PRUEBA_a.pdf"\n- "PRUEBA_b.pdf"\n\nFRAGMENTOS RECUPERADOS:\n'
    assert r.sistema.startswith(esperado)
    assert "ARCHIVOS DEL NOTEBOOK" not in r.sistema


def test_lista_dentro_del_presupuesto():
    """RF-12.62 · con 8 archivos distintos la entrada, con su lista, cabe en el presupuesto."""
    frs = [_frag(i, 1500, archivo="A" * 255 + f"{i}.pdf") for i in range(15)]
    r = _armar(chat="notebook", fragmentos=frs, historial=["h" * 2000 for _ in range(20)])
    assert len(r.archivos) <= 8
    assert r.tokens_total <= P


def test_lista_vacia_fuera_del_notebook():
    """RF-12.62 · solo el notebook lleva lista de archivos."""
    assert _armar(chat="tema", fragmentos=[_frag(1, 500)]).archivos == []


@pytest.mark.parametrize("solicitud,esperado", [(None, 8), (20, 8), (3, 3), (0, 8), (-1, 8)])
def test_cantidad_recuperada(solicitud, esperado):
    """RF-11.65 · una solicitud pide menos, nunca más; 0 o negativa usa el valor del servidor."""
    assert pc.cantidad_a_recuperar(solicitud) == esperado


@pytest.mark.parametrize("chat", CHATS)
def test_cantidad_en_el_armado(chat):
    """RF-11.65 · el armado respeta la cantidad solicitada en cada chat."""
    r = _armar(chat=chat, fragmentos=[_frag(i, 300) for i in range(15)], solicitud=3)
    assert len(r.fragmentos) == 3


@pytest.mark.parametrize("chat", CHATS)
def test_reformula_con_dos_mensajes(chat):
    """RF-11.66 · se reformula con los 2 últimos mensajes y dentro del presupuesto."""
    historial = [f"m{i}" for i in range(6)]
    msgs = pc.mensajes_para_reformular("r" * 1000, PREG, historial)
    assert msgs == ["m4", "m5"]
    assert _t(1000) + _t(len(PREG)) + sum(_t(len(m)) for m in msgs) <= P
    assert _armar(chat=chat, historial=historial).tokens_total <= P


def test_mensajes_enormes_1_o_0():
    """RF-11.66 · si los 2 no caben queda 1; si ninguno cabe, 0 (sin llamada de reformulación)."""
    assert pc.mensajes_para_reformular("r" * 1000, PREG, ["a" * 20000, "b" * 20000]) == ["b" * 20000]
    assert pc.mensajes_para_reformular("r" * 1000, PREG, ["a" * 20000, "b" * 30000]) == []


@pytest.mark.parametrize("chat", CHATS)
def test_sin_historial_no_reformula(chat):
    """RF-11.66 · sin historial no hay mensajes y, por tanto, no hay llamada de reformulación."""
    assert pc.mensajes_para_reformular("r" * 1000, PREG, []) == []


# --- T5: los tres chats usan el armado (RF-11.60, RF-11.65, RF-12.60, RF-12.62) --------------------------------------------------
# Se recorre el flujo real del servicio (`_despachar_consulta`) con el motor simulado, que registra cada llamada, y un
# recuperador falso: lo que se mide es lo que RECIBE el motor. Los textos son inventados (`MARCAnn` identifica cada fragmento).

TEMA_FORMA_JUDICIAL = "24-000123-0001-PE"  # el chat por tema solo reconoce hoy números con esta forma
NOMBRE_NOTEBOOK = "PRUEBA cuaderno"


def _documentos(n: int, largo: int, tema: str):
    from langchain_core.documents import Document

    return [
        Document(
            page_content=f"MARCA{i:02d} " + "x" * largo,
            metadata={
                "expediente_numero": tema, "archivo": f"PRUEBA_{i}.pdf", "nombre_archivo": f"PRUEBA_{i}.pdf",
                "ruta_archivo": f"uploads/{tema}/PRUEBA_{i}.pdf", "pagina_inicio": 1, "pagina_fin": 2,
            },
        )
        for i in range(n)
    ]


def _recuperador_falso_cls():
    from typing import Any, Optional

    from langchain_core.retrievers import BaseRetriever

    class RecuperadorFalso(BaseRetriever):
        documentos: list
        top_k: Optional[int] = None
        recibidos: Any = None

        async def _aget_relevant_documents(self, query, **kwargs):
            return self.documentos if self.top_k is None else self.documentos[: max(self.top_k, 0)]

        def _get_relevant_documents(self, query, **kwargs):
            raise NotImplementedError

    return RecuperadorFalso


class _Turno:
    """Resultado de una consulta de prueba: llamadas al motor, eventos e historial."""

    def __init__(self, llamadas, eventos, sesion):
        self.llamadas, self.eventos, self.sesion = llamadas, eventos, sesion

    @property
    def respuesta(self) -> str:
        return "\n".join(self.llamadas[-1])

    def marcas(self) -> list:
        return [i for i in range(40) if f"MARCA{i:02d}" in self.respuesta]


def _preparar(monkeypatch, ollama_simulado, historial: int = 0):
    from unittest.mock import MagicMock

    from langchain_core.messages import AIMessage, HumanMessage

    from app.services.RAG import expediente_chains, general_chains, notebook_chains
    from app.services.RAG import rag_chain_service as servicio
    from app.services.RAG.session_store import InMemoryChatMessageHistory, LimitedChatMessageHistory

    sesion = InMemoryChatMessageHistory("PRUEBA-sesion")
    for i in range(historial):
        sesion.add_message((HumanMessage if i % 2 == 0 else AIMessage)(content=f"H{i:02d} " + "h" * 3000))
    for modulo in (general_chains, expediente_chains, notebook_chains):
        monkeypatch.setattr(modulo, "get_session_history_func", lambda: (lambda sid: LimitedChatMessageHistory(sesion)),
                            raising=False)
    monkeypatch.setattr(servicio, "conversation_store", MagicMock())
    ollama_simulado.responder("Respuesta de PRUEBA.")
    return servicio, sesion


def _consultar(chat: str, servicio, sesion, ollama_simulado, solicitud=None, pregunta="¿Qué dice el documento?") -> _Turno:
    import asyncio
    import json
    from types import SimpleNamespace

    svc = servicio.RAGChainService()

    async def visibles(usuario_id):
        return {1}

    svc._documentos_visibles = visibles
    notebook = SimpleNamespace(clave_interna="NB-7", CT_Nombre=NOMBRE_NOTEBOOK) if chat == "notebook" else None
    tema = TEMA_FORMA_JUDICIAL if chat == "tema" else None

    async def correr():
        respuesta = await svc._despachar_consulta(pregunta, "PRUEBA-sesion", solicitud, tema, notebook, "1", None)
        eventos = []
        async for trozo in respuesta.body_iterator:
            eventos.append(json.loads(trozo.removeprefix("data: ")))
        return eventos

    eventos = asyncio.run(correr())
    errores = [e for e in eventos if e.get("type") == "error"]
    assert not errores, f"el flujo respondió con error: {errores[0].get('content')}"
    return _Turno(ollama_simulado.llamadas, eventos, sesion)


def _con_recuperador_falso(monkeypatch, servicio, documentos: list) -> list:
    """Sustituye al recuperador del servicio y devuelve la lista donde queda lo que pidió el flujo."""
    clase = _recuperador_falso_cls()
    creados: list = []

    def fabrica(**kwargs):
        recuperador = clase(documentos=documentos, top_k=kwargs.get("top_k"), recibidos=kwargs)
        creados.append(recuperador)
        return recuperador

    monkeypatch.setattr(servicio, "DynamicServIARetriever", fabrica)
    return creados


def _tema_de(chat: str) -> str:
    return {"general": "PRUEBA tema general", "tema": TEMA_FORMA_JUDICIAL, "notebook": NOMBRE_NOTEBOOK}[chat]


@pytest.mark.parametrize("chat", CHATS)
def test_entrada_dentro_del_presupuesto(chat, monkeypatch, ollama_simulado):
    """RF-11.60 · con 15 fragmentos de 7.000 caracteres y 20 mensajes largos, NINGUNA llamada al motor supera el presupuesto."""
    servicio, sesion = _preparar(monkeypatch, ollama_simulado, historial=20)
    _con_recuperador_falso(monkeypatch, servicio, _documentos(15, 7000, _tema_de(chat)))
    turno = _consultar(chat, servicio, sesion, ollama_simulado)
    assert turno.llamadas, "el motor no recibió ninguna llamada"
    for llamada in turno.llamadas:
        assert sum(pc.tokens(m) for m in llamada) <= P, f"una llamada de {sum(pc.tokens(m) for m in llamada)} tokens"


@pytest.mark.parametrize("chat", CHATS)
def test_fragmento_una_sola_vez(chat, monkeypatch, ollama_simulado):
    """RF-11.60 (regresión) · cada fragmento aparece una sola vez en la entrada (antes: 5 copias en el general y 7 en el tema),
    con el encabezado de RF-12.60 y los títulos fijos una sola vez."""
    servicio, sesion = _preparar(monkeypatch, ollama_simulado, historial=4)
    _con_recuperador_falso(monkeypatch, servicio, _documentos(15, 700, _tema_de(chat)))
    turno = _consultar(chat, servicio, sesion, ollama_simulado)
    assert turno.marcas(), "ningún fragmento llegó al motor"
    for i in range(15):
        assert turno.respuesta.count(f"MARCA{i:02d}") <= 1, f"el fragmento {i} está repetido"
    assert turno.respuesta.count("FRAGMENTOS RECUPERADOS:") == 1
    primero = turno.marcas()[0]
    assert f"Archivo: PRUEBA_{primero}.pdf | Tema: {_tema_de(chat)}" in turno.respuesta  # RF-12.60
    assert f"uploads/{_tema_de(chat)}/PRUEBA_{primero}.pdf" in turno.respuesta
    assert "**Expediente:**" not in turno.respuesta  # sin el encabezado de formato anterior


@pytest.mark.parametrize("chat", CHATS)
@pytest.mark.parametrize("solicitud, esperado", [(20, 8), (3, 3), (0, 8), (-1, 8), (None, 8)])
def test_cantidad_recuperada_por_chat(chat, solicitud, esperado, monkeypatch, ollama_simulado):
    """RF-11.65 · el flujo pide al recuperador la cantidad configurada (8), o menos si la solicitud pide menos; nunca más."""
    servicio, sesion = _preparar(monkeypatch, ollama_simulado)
    creados = _con_recuperador_falso(monkeypatch, servicio, _documentos(15, 300, _tema_de(chat)))
    turno = _consultar(chat, servicio, sesion, ollama_simulado, solicitud=solicitud)
    assert [c.top_k for c in creados] == [esperado]
    assert len(turno.marcas()) == esperado


class _AlmacenFalso:
    """Qdrant simulado: la búsqueda solo devuelve resultados con el umbral de respaldo y no respeta el `k` pedido."""

    def __init__(self, tema: str):
        self.tema, self.pedidos = tema, []

    async def search_by_text(self, query_text, top_k, threshold, expediente_filter=None, db=None, documentos_visibles=None):
        from app.config.rag_config import rag_config

        self.pedidos.append(top_k)
        if threshold != rag_config.SIMILARITY_THRESHOLD_FALLBACK:
            return []
        return [
            {"id": str(i), "expedient_id": self.tema, "document_name": f"PRUEBA_{i}.pdf",
             "content_preview": f"MARCA{i:02d} texto", "similarity_score": 0.3,
             "metadata": {"meta": {"ruta_archivo": f"uploads/{self.tema}/PRUEBA_{i}.pdf"}}}
            for i in range(20)
        ]

    async def get_expedient_documents(self, expedient_id, documentos_visibles=None):
        return _documentos(20, 300, self.tema)


@pytest.mark.parametrize("chat", CHATS)
@pytest.mark.parametrize("solicitud, maximo", [(None, 8), (3, 3)])
def test_respaldo_no_supera(chat, solicitud, maximo, monkeypatch, ollama_simulado):
    """RF-11.65 · la búsqueda de respaldo (general) y la lectura del tema o notebook nunca devuelven ni piden más que la cantidad."""
    from app.services.RAG import retriever, search_strategies

    servicio, sesion = _preparar(monkeypatch, ollama_simulado)
    almacen = _AlmacenFalso(_tema_de(chat))
    monkeypatch.setattr(search_strategies, "get_vectorstore_backend", lambda: almacen)
    monkeypatch.setattr(retriever, "get_vectorstore_backend", lambda: almacen)
    turno = _consultar(chat, servicio, sesion, ollama_simulado, solicitud=solicitud)
    assert 1 <= len(turno.marcas()) <= maximo
    assert all(p <= maximo for p in almacen.pedidos), f"se pidió más de {maximo}: {almacen.pedidos}"


@pytest.mark.parametrize("chat", CHATS)
def test_guarda_pregunta_y_respuesta(chat, monkeypatch, ollama_simulado):
    """RF-11.60 (regresión) · el turno terminado deja en el historial la pregunta y la respuesta."""
    servicio, sesion = _preparar(monkeypatch, ollama_simulado, historial=2)
    _con_recuperador_falso(monkeypatch, servicio, _documentos(3, 100, _tema_de(chat)))
    _consultar(chat, servicio, sesion, ollama_simulado, pregunta="Pregunta de PRUEBA")
    assert [type(m).__name__ for m in sesion.messages[-2:]] == ["HumanMessage", "AIMessage"]
    assert sesion.messages[-2].content == "Pregunta de PRUEBA"
    assert sesion.messages[-1].content == "Respuesta de PRUEBA."
