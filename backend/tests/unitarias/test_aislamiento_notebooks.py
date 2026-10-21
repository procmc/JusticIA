"""Aislamiento de los notebooks entre usuarios, parte unitaria (spec 004b, T2; RF-17.3, RF-11.31, RF-17.32, RF-11.30; T4:
RF-11.32, RF-17.3 en la lectura de un tema).

SQL Server, Qdrant y Ollama simulados. Lo que se comprueba aquí es la regla y su cableado:
- RF-17.3: qué documentos puede ver cada usuario (`ids_documentos_visibles`, decidido con el tema de la base y no con el
  texto del fragmento), que la búsqueda excluye lo ajeno DENTRO de la consulta a Qdrant y que sin documentos visibles
  no devuelve nada (falla cerrado).
- RF-11.31 y RF-11.30: el chat por tema con forma de clave de notebook es el chat general; con un tema heredado no cambia.
- RF-17.32: la detección de un tema dentro de la pregunta no reconoce las claves de notebook.
Los datos son inventados.
"""
import asyncio
import logging
from types import SimpleNamespace

import pytest

USUARIO = "PRUEBA-U1"


def _notebook(id_notebook: int, usuario: str = USUARIO) -> SimpleNamespace:
    return SimpleNamespace(CN_Id_notebook=id_notebook, CN_Id_usuario=usuario, clave_interna=f"NB-{id_notebook}")


# --- RF-17.3: qué documentos puede ver cada usuario ---------------------------------------------------------------------------

# (id de documento, tema): un documento puede estar unido a más de un tema.
_DOCUMENTOS = [
    (1, "PRUEBA general"),
    (2, "NB-5"), (3, "nb-5"), (4, " Nb-5 "),            # el notebook 5 en cualquier grafía: del usuario
    (5, "NB-05"), (6, "NB- 5"), (7, "nb-5x"), (8, "NB-"),        # forma de clave que no es un notebook disponible
    (9, "NB-7"), (10, "nb-7"),                              # el notebook 7 no es del usuario (ajeno o inexistente)
    (11, "NB-٥"), (12, "NB-99999999999999999999999"),      # dígitos Unicode y un número fuera de rango
    (13, "99-000001-0001-PE"),                              # un tema heredado
    (14, "PRUEBA general"), (14, "NB-7"),                   # unido a un tema general Y a uno ajeno: fuera
    (15, "NB-5"), (15, "PRUEBA general"),                   # unido a un notebook propio y a un tema general: dentro
]


@pytest.fixture
def base_simulada(monkeypatch):
    """Una base inventada: los notebooks del usuario y los documentos Procesados con sus temas."""
    from app.repositories.documento_repository import DocumentoRepository
    from app.repositories.notebook_repository import NotebookRepository

    base = {"notebooks": {USUARIO: [_notebook(5)], "PRUEBA-U9": [_notebook(7, "PRUEBA-U9")]}, "documentos": list(_DOCUMENTOS), "consultas_de_notebook": []}

    monkeypatch.setattr(NotebookRepository, "listar_por_usuario", lambda self, db, usuario_id: base["notebooks"].get(usuario_id, []))
    monkeypatch.setattr(DocumentoRepository, "listar_procesados_con_temas", lambda self, db: list(base["documentos"]))

    def _obtener_por_id(self, db, notebook_id):
        base["consultas_de_notebook"].append(notebook_id)
        for notebooks in base["notebooks"].values():
            for notebook in notebooks:
                if notebook.CN_Id_notebook == notebook_id:
                    return notebook
        return None

    monkeypatch.setattr(NotebookRepository, "obtener_por_id", _obtener_por_id)
    return base


def _visibles(usuario_id) -> set:
    from app.services.notebook_service import NotebookService

    return asyncio.run(NotebookService().ids_documentos_visibles(None, usuario_id))


@pytest.mark.requisito("RF-17.3")
def test_ids_visibles_por_grafia(base_simulada):
    """RF-17.3: un documento es visible si ninguno de sus temas tiene forma de clave de notebook, salvo la de un notebook del
    propio usuario (en cualquier grafía de mayúsculas o con espacios alrededor). Una forma de clave que no es un notebook
    disponible (`NB-05`, `NB- 5`, dígitos Unicode, fuera de rango, de un notebook ajeno o sin notebook) esconde el documento,
    aunque además esté unido a un tema general."""
    assert _visibles(USUARIO) == {1, 2, 3, 4, 13, 15}


@pytest.mark.requisito("RF-17.3")
def test_otro_usuario_no_ve_el_notebook_del_primero(base_simulada):
    """RF-17.3: un usuario sin notebooks solo ve los documentos de los temas que no son de notebook; el dueño del notebook 7
    ve los suyos (también el unido a un tema general) y no los del notebook 5."""
    assert _visibles("PRUEBA-U2") == {1, 13}
    assert _visibles("PRUEBA-U9") == {1, 9, 10, 13, 14}


@pytest.mark.requisito("RF-17.3")
def test_sin_usuario_solo_ve_lo_que_no_es_de_notebook(base_simulada):
    """RF-17.3: sin usuario identificado no hay notebooks propios; solo se ven los documentos de temas que no son de notebook."""
    assert _visibles(None) == {1, 13}


@pytest.mark.requisito("RF-17.3")
def test_documentos_sin_tema_o_sin_registrar_no_son_visibles(base_simulada):
    """RF-17.3: la lista sale de los documentos Procesados con tema registrados en la base; lo que no está ahí (fragmentos de
    un documento que la base no conoce) nunca entra en ella."""
    base_simulada["documentos"] = []
    assert _visibles(USUARIO) == set()


# --- RF-17.3: la exclusión va dentro de la búsqueda; sin visibles no se consulta --------------------------------------------

class _AlmacenFalso:
    """Ocupa el lugar del almacén de LangChain: guarda los filtros con que se le consultó y no devuelve nada."""

    def __init__(self):
        self.filtros = []

    def similarity_search_with_score(self, query, k, filter=None):
        self.filtros.append(filter)
        return []


@pytest.fixture
def almacen(monkeypatch):
    from app.vectorstore import qdrant_backend

    falso = _AlmacenFalso()

    async def _entrega():
        return falso

    monkeypatch.setattr(qdrant_backend, "_get_langchain_vectorstore", _entrega)
    return falso


def _buscar(**parametros):
    from app.vectorstore.qdrant_backend import QdrantBackend

    return asyncio.run(QdrantBackend().search_by_text("PRUEBA consulta", top_k=5, score_threshold=0.0, **parametros))


@pytest.mark.requisito("RF-17.3")
def test_sin_visibles_falla_cerrado(almacen):
    """RF-17.3: con un conjunto vacío de documentos visibles la búsqueda devuelve una lista vacía SIN consultar el almacén
    (no hay nada que un usuario pueda ver; no se cae en «devolver todo»)."""
    assert _buscar(documentos_visibles=set()) == []
    assert almacen.filtros == []


@pytest.mark.requisito("RF-17.3")
def test_la_busqueda_filtra_por_documentos_visibles(almacen):
    """RF-17.3: los documentos visibles viajan en el filtro de la propia consulta a Qdrant (`metadata.id_documento`), junto
    con el tema exacto si se pidió; así los fragmentos ajenos no ocupan lugares de los `k` resultados."""
    _buscar(documentos_visibles={30, 10, 20})
    _buscar(documentos_visibles={4}, expediente_filter="PRUEBA tema")

    solo_visibles, con_tema = almacen.filtros
    assert [(c.key, sorted(c.match.any)) for c in solo_visibles.must] == [("metadata.id_documento", [10, 20, 30])]
    assert [c.key for c in con_tema.must] == ["metadata.numero_expediente", "metadata.id_documento"]
    assert con_tema.must[0].match.value == "PRUEBA tema"
    assert con_tema.must[1].match.any == [4]


@pytest.mark.requisito("RF-11.30")
def test_sin_visibles_indicados_la_busqueda_no_cambia(almacen):
    """RF-11.30: quien no pide documentos visibles (otras vías, hasta que se les aplique) conserva el filtro de antes: ninguno,
    o solo el del tema."""
    _buscar()
    _buscar(expediente_filter="PRUEBA tema")

    sin_filtro, con_tema = almacen.filtros
    assert sin_filtro is None
    assert [c.key for c in con_tema.must] == ["metadata.numero_expediente"]


@pytest.mark.requisito("RF-17.3")
def test_los_tres_niveles_del_fallback_reciben_los_visibles(monkeypatch):
    """RF-17.3: la estrategia con fallback pasa el mismo conjunto en la búsqueda normal, con el umbral relajado y con el
    umbral mínimo; ninguno de los tres niveles puede buscar sin la exclusión."""
    from app.services.RAG import search_strategies

    recibidos = []

    class _Respaldo:
        async def search_by_text(self, query_text, top_k, threshold, expediente_filter=None, db=None, documentos_visibles=None):
            recibidos.append(documentos_visibles)
            return []

    monkeypatch.setattr(search_strategies, "get_vectorstore_backend", lambda: _Respaldo())
    asyncio.run(search_strategies.SearchStrategyManager().search_with_fallback(
        "PRUEBA consulta", top_k=5, threshold=0.3, documentos_visibles={1, 2}))

    assert recibidos == [{1, 2}] * 3


@pytest.mark.requisito("RF-17.3")
def test_el_retriever_pasa_los_visibles_a_la_busqueda_general(monkeypatch):
    """RF-17.3: el buscador del chat entrega a la búsqueda los documentos visibles con que se creó."""
    from app.services.RAG import retriever as modulo

    recibidos = []

    async def _busqueda(self, **parametros):
        recibidos.append(parametros.get("documentos_visibles", "no se pasó"))
        return []

    monkeypatch.setattr(modulo.search_manager.__class__, "search_with_fallback", _busqueda)
    buscador = modulo.DynamicServIARetriever(documentos_visibles={7, 8})
    asyncio.run(buscador._get_general_documents("PRUEBA consulta"))

    assert recibidos == [{7, 8}]


# --- RF-11.31, RF-11.30: el chat por tema -----------------------------------------------------------------------------------

@pytest.fixture
def servicio_de_chat(monkeypatch):
    """El servicio del chat con sus tres flujos reemplazados por registros: se comprueba solo a cuál se despacha."""
    from app.services.RAG import rag_chain_service
    from app.services.RAG.rag_chain_service import RAGChainService

    servicio = RAGChainService()
    llamadas = []

    async def _flujo(nombre, **parametros):
        llamadas.append((nombre, parametros))
        return "respuesta"

    monkeypatch.setattr(servicio, "_consulta_general_con_historial", lambda **p: _flujo("general", **p))
    monkeypatch.setattr(servicio, "_consulta_expediente_con_historial", lambda **p: _flujo("expediente", **p))
    monkeypatch.setattr(servicio, "_consulta_notebook_con_historial", lambda **p: _flujo("notebook", **p))
    monkeypatch.setattr(rag_chain_service.conversation_store, "update_metadata", lambda *a, **k: None)
    servicio.llamadas = llamadas
    return servicio


def _preguntar(servicio, **alcance):
    return asyncio.run(servicio.consulta_con_historial_streaming(
        pregunta="PRUEBA pregunta", session_id="session_PRUEBA_1", usuario_id=USUARIO, **alcance))


@pytest.mark.requisito("RF-11.31")
@pytest.mark.parametrize("tema", ["NB-5", "nb-5", " Nb-5 ", "NB-7", "NB-05", "NB-", "nb-999999999999999999999"])
def test_tema_con_forma_de_clave_es_el_chat_general(servicio_de_chat, tema):
    """RF-11.31: en el chat por tema, un tema con forma de clave de notebook (propia, ajena o inexistente, en cualquier
    grafía) se atiende como chat general del usuario: nunca como un chat acotado a ese tema."""
    _preguntar(servicio_de_chat, expediente_filter=tema)

    assert [nombre for nombre, _ in servicio_de_chat.llamadas] == ["general"]
    assert servicio_de_chat.llamadas[0][1]["usuario_id"] == USUARIO


@pytest.mark.requisito("RF-11.30")
@pytest.mark.parametrize("tema", ["99-000123-0001-PE", "PRUEBA tema libre", "Nota-5", "enb-5"])
def test_tema_heredado_o_libre_sigue_el_flujo_de_antes(servicio_de_chat, tema):
    """RF-11.30: un tema heredado o de nombre libre (que no empieza por `nb-`) conserva su flujo de siempre: el del tema."""
    _preguntar(servicio_de_chat, expediente_filter=tema)

    assert [nombre for nombre, _ in servicio_de_chat.llamadas] == ["expediente"]


@pytest.mark.requisito("RF-17.3")
def test_el_chat_general_recibe_al_usuario(servicio_de_chat):
    """RF-17.3: el chat general sabe de qué usuario es la consulta, para excluir lo ajeno."""
    _preguntar(servicio_de_chat)

    assert [nombre for nombre, _ in servicio_de_chat.llamadas] == ["general"]
    assert servicio_de_chat.llamadas[0][1]["usuario_id"] == USUARIO


# --- RF-17.32: la clave de notebook en la pregunta no es un tema -------------------------------------------------------------

@pytest.mark.requisito("RF-17.32")
@pytest.mark.parametrize("pregunta", [
    "¿Qué dice el notebook NB-5?", "nb-12 y NB-7 hablan de lo mismo", "mira NB-05, NB-٥ y  Nb-3 por favor", "NB-99-000123-0001-PE",
])
def test_la_clave_en_la_pregunta_no_se_detecta_como_tema(pregunta):
    """RF-17.32: la detección de un tema dentro de la pregunta solo reconoce el formato heredado; una clave de notebook
    mencionada no se toma como tema (no se filtra por ella), ni siquiera pegada a uno heredado."""
    from app.utils.expediente_validator import extraer_expediente_de_texto

    detectado = extraer_expediente_de_texto(pregunta)

    assert detectado is None or not detectado.casefold().startswith("nb-"), detectado
    if pregunta != "NB-99-000123-0001-PE":
        assert detectado is None


# --- La regla de la forma de clave -------------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-11.31")
@pytest.mark.parametrize("tema, esperado", [
    ("NB-5", True), ("nb-5", True), (" Nb-5 ", True), ("NB-", True), ("NB-05", True), ("nb-abc", True),
    ("PRUEBA", False), ("", False), ("N", False), ("NB5", False), ("xNB-5", False), ("99-000123-0001-PE", False), (None, False),
])
def test_forma_de_clave(tema, esperado):
    """Definiciones: forma de clave de notebook es el tema que, sin espacios al inicio y al final y sin distinguir
    mayúsculas, empieza por `NB-`."""
    from app.services.notebook_service import forma_de_clave

    assert forma_de_clave(tema) is esperado


@pytest.mark.requisito("RF-11.31")
@pytest.mark.parametrize("tema, esperado", [
    ("NB-5", "propio"), ("nb-5", "propio"), (" Nb-5 ", "propio"),       # el notebook 5 es del usuario
    ("NB-7", "no_disponible"), ("NB-99", "no_disponible"),              # ajeno o inexistente: no se distinguen
    ("NB-05", "no_disponible"), ("NB- 5", "no_disponible"), ("NB-٥", "no_disponible"), ("NB-", "no_disponible"),
    ("NB-99999999999999999999999", "no_disponible"),
    ("PRUEBA tema", "no_es_notebook"), ("99-000123-0001-PE", "no_es_notebook"), ("", "no_es_notebook"),
])
def test_clasificar_clave(base_simulada, tema, esperado):
    """Definiciones: notebook disponible es una forma de clave con número ASCII sin ceros a la izquierda de un notebook del
    propio usuario; cualquier otra es no disponible, con el mismo trato. Lo que no es forma de clave no es de notebook."""
    from app.services.notebook_service import NotebookService

    clasificacion = asyncio.run(NotebookService().clasificar_clave(None, tema, USUARIO))

    assert clasificacion.tipo == esperado
    assert (clasificacion.notebook.clave_interna if clasificacion.notebook else None) == ("NB-5" if esperado == "propio" else None)


@pytest.mark.requisito("RF-11.31")
@pytest.mark.parametrize("tema", ["NB-05", "NB- 5", "NB-٥", "NB-", "NB-99999999999999999999999", "NB-abc", "NB-+5"])
def test_clave_mal_formada_no_consulta_la_base(base_simulada, tema):
    """Definiciones: una forma de clave que no es canónica es no disponible sin consultar la base (nada de normalizar con
    `int()`, que aceptaría `+5`, ` 5 ` o dígitos Unicode, y un número enorme desbordaría la columna)."""
    from app.services.notebook_service import NotebookService

    clasificacion = asyncio.run(NotebookService().clasificar_clave(None, tema, USUARIO))

    assert clasificacion.tipo == "no_disponible"
    assert base_simulada["consultas_de_notebook"] == []


# --- RF-17.3, RF-17.31 (spec 004b, T3): temas similares y resumen IA -------------------------------------------------------------

class _PuntoFalso:
    def __init__(self, id_punto, expediente, id_documento, vector=None, puntuacion=0.9):
        self.id, self.vector, self.score = id_punto, vector, puntuacion
        self.payload = {"metadata": {"numero_expediente": expediente, "id_documento": id_documento, "nombre_archivo": f"PRUEBA_{id_punto}.txt"},
                        "page_content": "PRUEBA texto"}


class _ClienteFalso:
    """Ocupa el lugar del cliente de Qdrant: guarda los filtros con que se le consultó y devuelve puntos inventados."""

    def __init__(self, referencia, aciertos):
        self.referencia, self.aciertos, self.filtros_scroll, self.filtros_consulta = referencia, aciertos, [], []

    def scroll(self, collection_name, scroll_filter, limit, with_payload, with_vectors=False):
        self.filtros_scroll.append(scroll_filter)
        return self.referencia, None

    def query_points(self, collection_name, query, limit, with_payload, query_filter=None):
        self.filtros_consulta.append(query_filter)
        return SimpleNamespace(points=self.aciertos)


@pytest.fixture
def cliente_qdrant(monkeypatch):
    from app.vectorstore import qdrant_backend

    cliente = _ClienteFalso([_PuntoFalso(1, "PRUEBA ref", 1, vector=[0.1])], [_PuntoFalso(2, "PRUEBA otro", 2)])
    monkeypatch.setattr(qdrant_backend, "_get_client", lambda: cliente)
    monkeypatch.setattr(qdrant_backend, "_filter_by_processed_status", lambda resultados, db=None: resultados)
    return cliente


def _similares(**parametros):
    from app.vectorstore.qdrant_backend import QdrantBackend

    return asyncio.run(QdrantBackend().search_similar_expedients("PRUEBA ref", top_k=5, score_threshold=0.0, **parametros))


@pytest.mark.requisito("RF-17.3")
def test_similares_sin_visibles_falla_cerrado(cliente_qdrant):
    """RF-17.3: con un conjunto vacío de documentos visibles, la búsqueda de temas similares devuelve una lista vacía SIN
    consultar Qdrant (ni siquiera el tema de referencia)."""
    assert _similares(documentos_visibles=set()) == []
    assert cliente_qdrant.filtros_scroll == [] and cliente_qdrant.filtros_consulta == []


@pytest.mark.requisito("RF-17.3")
def test_similares_filtra_por_documentos_visibles_dentro_de_la_consulta(cliente_qdrant):
    """RF-17.3: los documentos visibles viajan en el filtro de la consulta de vecinos (y en la lectura del tema de
    referencia), de modo que los fragmentos ajenos no ocupan lugares de los `k` resultados."""
    _similares(documentos_visibles={9, 3})

    assert cliente_qdrant.filtros_consulta
    for filtro in cliente_qdrant.filtros_consulta:
        assert [(c.key, sorted(c.match.any)) for c in filtro.must] == [("metadata.id_documento", [3, 9])]
    assert [c.key for c in cliente_qdrant.filtros_scroll[0].must] == ["metadata.numero_expediente", "metadata.id_documento"]


@pytest.mark.requisito("RF-11.30")
def test_similares_sin_visibles_indicados_no_cambia(cliente_qdrant):
    """RF-11.30: quien no pide documentos visibles conserva la consulta de antes, sin filtro."""
    _similares()

    assert cliente_qdrant.filtros_consulta == [None]
    assert [c.key for c in cliente_qdrant.filtros_scroll[0].must] == ["metadata.numero_expediente"]


@pytest.fixture
def servicio_similares(monkeypatch):
    """`SimilarityService` con sus dependencias externas reemplazadas por registros y los documentos visibles fijos."""
    from app.services.busqueda_similares import document_retriever as modulo_documentos
    from app.services.busqueda_similares import similarity_service as modulo
    from app.vectorstore import qdrant_backend

    registro = {"retrievers": [], "busquedas": [], "visibles": [], "llm": 0}

    class _Retriever:
        def __init__(self, **parametros):
            registro["retrievers"].append(parametros)

        async def _aget_relevant_documents(self, consulta):
            return []

    async def _vecinos(self, **parametros):
        registro["busquedas"].append(parametros)
        return []

    async def _visibles(self, db, usuario_id):
        registro["visibles"].append(usuario_id)
        return {1, 2}

    monkeypatch.setattr(modulo, "DynamicServIARetriever", _Retriever)
    monkeypatch.setattr(modulo_documentos, "DynamicServIARetriever", _Retriever)
    monkeypatch.setattr(qdrant_backend.QdrantBackend, "search_similar_expedients", _vecinos)
    monkeypatch.setattr(modulo.SimilarityService, "_documentos_visibles", _visibles)
    servicio = modulo.SimilarityService()

    async def _contexto(docs):
        registro["llm"] += 1
        return ""

    monkeypatch.setattr(servicio.summary_generator, "crear_contexto_resumen", _contexto)
    servicio.registro = registro
    return servicio


def _pedido(modo, **campos):
    from app.schemas.similarity_schemas import SimilaritySearchRequest

    return SimilaritySearchRequest(modo_busqueda=modo, limite=5, umbral_similitud=0.1, **campos)


@pytest.mark.requisito("RF-17.3")
def test_similares_por_descripcion_pasa_los_visibles_del_usuario(servicio_similares):
    """RF-17.3: la búsqueda por descripción crea su buscador con los documentos visibles del usuario que pregunta."""
    asyncio.run(servicio_similares.search_similar_cases(_pedido("descripcion", texto_consulta="PRUEBA consulta"), None, USUARIO))

    assert servicio_similares.registro["visibles"] == [USUARIO]
    assert [r["documentos_visibles"] for r in servicio_similares.registro["retrievers"]] == [{1, 2}]


@pytest.mark.requisito("RF-17.3")
def test_similares_por_tema_pasa_los_visibles_del_usuario(servicio_similares):
    """RF-17.3: la búsqueda por tema de referencia entrega a Qdrant los documentos visibles del usuario."""
    asyncio.run(servicio_similares.search_similar_cases(_pedido("expediente", numero_expediente="99-000001-0001-PE"), None, USUARIO))

    assert [b["documentos_visibles"] for b in servicio_similares.registro["busquedas"]] == [{1, 2}]


@pytest.mark.requisito("RF-17.31")
@pytest.mark.parametrize("tema", ["NB-5", "nb-5", " Nb-5 ", "NB-7", "NB-05", "NB-", "NB-99999999999999999999999"])
def test_similares_con_clave_de_referencia_no_consulta_qdrant(servicio_similares, tema):
    """RF-17.31: un tema de referencia con forma de clave de notebook (propio, ajeno o inexistente) se trata como un tema
    inexistente: respuesta vacía y sin consultar Qdrant, ni siquiera con los fragmentos de la clave."""
    respuesta = asyncio.run(servicio_similares.search_similar_cases(_pedido("expediente", numero_expediente=tema), None, USUARIO))

    assert respuesta.total_resultados == 0 and respuesta.casos_similares == []
    assert servicio_similares.registro["busquedas"] == []


@pytest.mark.requisito("RF-17.31")
@pytest.mark.parametrize("tema", ["NB-5", "nb-7", " NB-5 ", "NB-05", "NB-99999999999999999999999"])
def test_resumen_con_clave_es_como_un_tema_inexistente(servicio_similares, tema):
    """RF-17.31: el resumen IA de un tema con forma de clave de notebook responde igual que el de un tema sin documentos
    (`ValueError`), sin buscar documentos ni llamar al modelo."""
    with pytest.raises(ValueError, match="No se encontraron documentos"):
        asyncio.run(servicio_similares.generate_case_summary(tema, None, USUARIO))

    assert servicio_similares.registro["retrievers"] == [] and servicio_similares.registro["llm"] == 0


@pytest.mark.requisito("RF-17.3")
def test_resumen_de_un_tema_pasa_los_visibles_al_buscador(servicio_similares, monkeypatch):
    """RF-17.3: el resumen de un tema normal busca sus documentos solo entre los visibles del usuario; y el respaldo desde la
    base descarta los documentos que el usuario no puede ver aunque estén unidos a ese tema."""
    async def _completo(numero, incluir_documentos=True):
        return {"documents": [{"id": 1, "document_name": "PRUEBA_visible.txt", "content_preview": "PRUEBA texto visible"},
                              {"id": 99, "document_name": "PRUEBA_ajeno.txt", "content_preview": "PRUEBA texto ajeno"}]}

    monkeypatch.setattr(servicio_similares.document_retriever.documento_service, "obtener_expediente_completo", _completo)

    docs = asyncio.run(servicio_similares.document_retriever.obtener_documentos_expediente("99-000001-0001-PE", {1, 2}))

    assert servicio_similares.registro["retrievers"][0]["documentos_visibles"] == {1, 2}
    assert [d.metadata["nombre_archivo"] for d in docs] == ["PRUEBA_visible.txt"]


# --- RF-11.32 (spec 004b, T4): el chat del notebook comprueba el notebook antes de leer o tocar nada ---------------------------------

@pytest.mark.requisito("RF-11.32")
@pytest.mark.parametrize("texto, esperado", [
    ("5", 5), ("123", 123), ("9223372036854775807", 2**63 - 1),
    ("+5", None), (" 5 ", None), ("5 ", None), ("05", None), ("0", None), ("", None), ("   ", None), ("٥", None), ("5\n", None),
    ("5a", None), ("NB-5", None), ("-5", None), ("5.0", None), ("9223372036854775808", None), ("9" * 30, None), (None, None),
])
def test_id_de_notebook_solo_acepta_digitos_ascii_canonicos(texto, esperado):
    """RF-11.32: solo dígitos ASCII, sin signo, espacios ni ceros a la izquierda y dentro del rango de la columna son un
    identificador de notebook; `int()` aceptaría `+5`, ` 5 ` y los dígitos Unicode, creando alias."""
    from app.services.notebook_service import id_de_notebook

    assert id_de_notebook(texto) == esperado


@pytest.mark.requisito("RF-11.32")
@pytest.mark.parametrize("texto, propio", [
    ("5", True), ("7", False), ("99", False), ("+5", False), (" 5 ", False), ("05", False), ("٥", False), ("", False),
    ("9" * 30, False),
])
def test_notebook_para_el_chat_es_solo_el_propio_en_su_forma_canonica(base_simulada, texto, propio):
    """RF-11.32: el notebook del chat es el de un notebook del usuario en su forma canónica; el ajeno, el inexistente y las
    formas no canónicas dan `None`, y estas últimas ni siquiera consultan la base."""
    from app.services.notebook_service import NotebookService

    notebook = asyncio.run(NotebookService().obtener_notebook_para_chat(None, texto, USUARIO))

    assert (notebook.CN_Id_notebook if notebook else None) == (5 if propio else None)
    if texto in ("+5", " 5 ", "05", "٥", "", "9" * 30):
        assert base_simulada["consultas_de_notebook"] == []


@pytest.fixture
def chat_de_notebooks(servicio_de_chat, base_simulada, monkeypatch):
    """El servicio del chat con la base de notebooks simulada y un registro de cuándo se actualiza la conversación."""
    from app.services.RAG import rag_chain_service

    servicio_de_chat.metadatos = []
    monkeypatch.setattr(rag_chain_service.conversation_store, "update_metadata", lambda *a, **k: servicio_de_chat.metadatos.append(a))
    monkeypatch.setattr(rag_chain_service, "get_db", lambda: iter([SimpleNamespace(close=lambda: None)]))
    return servicio_de_chat


@pytest.mark.requisito("RF-11.32")
@pytest.mark.parametrize("notebook_id", ["7", "99", "+5", " 5 ", "05", "٥", "", "   ", "0", "5a", "9" * 30])
def test_notebook_no_disponible_no_llama_a_ningun_flujo_ni_toca_la_conversacion(chat_de_notebooks, notebook_id):
    """RF-11.32: con un notebook ajeno, inexistente o no numérico el servicio lanza `RecursoNoDisponible` ANTES de actualizar la
    conversación y sin despachar a ningún flujo (el modelo no se llama)."""
    from app.services.notebook_service import RecursoNoDisponible

    with pytest.raises(RecursoNoDisponible):
        _preguntar(chat_de_notebooks, notebook_filter=notebook_id)

    assert chat_de_notebooks.llamadas == [] and chat_de_notebooks.metadatos == []


@pytest.mark.requisito("RF-11.32")
def test_notebook_no_disponible_gana_a_un_tema_en_la_misma_peticion(chat_de_notebooks):
    """RF-11.32: la comprobación del notebook va primero: un notebook no disponible junto a un tema válido tampoco sigue."""
    from app.services.notebook_service import RecursoNoDisponible

    with pytest.raises(RecursoNoDisponible):
        _preguntar(chat_de_notebooks, notebook_filter="7", expediente_filter="99-000123-0001-PE")

    assert chat_de_notebooks.llamadas == [] and chat_de_notebooks.metadatos == []


@pytest.mark.requisito("RF-11.3")
def test_notebook_propio_va_al_flujo_del_notebook_y_actualiza_la_conversacion_despues(chat_de_notebooks):
    """RF-11.3: con un notebook propio el servicio despacha al flujo del notebook con el notebook ya comprobado, y solo
    entonces actualiza la conversación."""
    _preguntar(chat_de_notebooks, notebook_filter="5")

    assert [nombre for nombre, _ in chat_de_notebooks.llamadas] == ["notebook"]
    assert chat_de_notebooks.llamadas[0][1]["notebook"].clave_interna == "NB-5"
    assert chat_de_notebooks.metadatos == [("session_PRUEBA_1",)]


# --- RF-17.3 (T4): la lectura de un tema también se limita a los documentos visibles ------------------------------------------------

@pytest.mark.requisito("RF-17.3")
def test_leer_un_tema_filtra_por_documentos_visibles(cliente_qdrant):
    """RF-17.3: la lectura de todos los fragmentos de un tema (que usa el resumen IA) lleva los documentos visibles en el
    filtro, junto al tema; sin indicar visibles conserva la consulta de antes."""
    from app.vectorstore.qdrant_backend import QdrantBackend

    asyncio.run(QdrantBackend().get_expedient_documents("PRUEBA tema", documentos_visibles={9, 3}))
    asyncio.run(QdrantBackend().get_expedient_documents("PRUEBA tema"))

    con, sin = cliente_qdrant.filtros_scroll
    assert [(c.key, sorted(c.match.any) if hasattr(c.match, "any") else c.match.value) for c in con.must] == [
        ("metadata.numero_expediente", "PRUEBA tema"), ("metadata.id_documento", [3, 9])]
    assert [c.key for c in sin.must] == ["metadata.numero_expediente"]


@pytest.mark.requisito("RF-17.3")
def test_leer_un_tema_sin_visibles_falla_cerrado(cliente_qdrant):
    """RF-17.3: con un conjunto vacío de documentos visibles la lectura de un tema devuelve una lista vacía SIN consultar Qdrant."""
    from app.vectorstore.qdrant_backend import QdrantBackend

    assert asyncio.run(QdrantBackend().get_expedient_documents("PRUEBA tema", documentos_visibles=set())) == []
    assert cliente_qdrant.filtros_scroll == []


@pytest.mark.requisito("RF-17.3")
def test_el_retriever_de_un_tema_pasa_los_visibles_a_la_lectura(monkeypatch):
    """RF-17.3: el buscador de un tema entrega a la lectura los documentos visibles con que se creó (defensa en profundidad
    del resumen y de temas similares); sin ellos no restringe."""
    from app.services.RAG import retriever as modulo

    recibidos = []

    class _Respaldo:
        async def get_expedient_documents(self, expedient_id, documentos_visibles=None):
            recibidos.append(documentos_visibles)
            return []

    monkeypatch.setattr(modulo, "get_vectorstore_backend", lambda: _Respaldo())
    asyncio.run(modulo.DynamicServIARetriever(expediente_filter="PRUEBA tema", documentos_visibles={4})._get_expediente_documents("PRUEBA tema"))
    asyncio.run(modulo.DynamicServIARetriever(expediente_filter="PRUEBA tema")._get_expediente_documents("PRUEBA tema"))

    assert recibidos == [{4}, None]


# --- RF-17.34 (T6): la forma de clave se lee en NFKC y la base decide la equivalencia ------------------------------------------------

# Letras y guion de ancho completo; los dígitos se escriben aparte (`５` es un dígito Unicode, no ASCII).
ANCHO_NB = "ＮＢ"
ANCHO_GUION = "－"


@pytest.mark.requisito("RF-17.34")
@pytest.mark.parametrize("tema, esperado", [
    (f"{ANCHO_NB}-5", True), (f"{ANCHO_NB}{ANCHO_GUION}5", True), (f"ｎｂ{ANCHO_GUION}5", True), (f"  {ANCHO_NB}{ANCHO_GUION}5  ", True),
    (f"{ANCHO_NB}-５", True), (f"{ANCHO_NB}{ANCHO_GUION}", True),            # forma de clave aunque el resto no sirva
    (f"{ANCHO_NB}5", False), (f"Ｎ Ｂ{ANCHO_GUION}5", False), (f"Ｘ{ANCHO_GUION}5", False), ("NB‐5", False),
])
def test_forma_de_clave_en_nfkc(tema, esperado):
    """RF-17.34 y Definiciones: la forma de clave se lee en NFKC (`ＮＢ－5` se lee `NB-5`) sin distinguir mayúsculas; el guion
    de ancho completo y las letras de ancho completo valen, un espacio dentro o un guion distinto no."""
    from app.services.notebook_service import forma_de_clave

    assert forma_de_clave(tema) is esperado


@pytest.mark.requisito("RF-17.34")
@pytest.mark.parametrize("tema, esperado", [
    ("NB-5", "propio"), (f"{ANCHO_NB}-5", "propio"), (f"{ANCHO_NB}{ANCHO_GUION}5", "propio"), (f"ｎｂ{ANCHO_GUION}5", "propio"),
    (f" {ANCHO_NB}{ANCHO_GUION}5 ", "propio"),
    (f"{ANCHO_NB}-7", "no_disponible"), (f"{ANCHO_NB}{ANCHO_GUION}99", "no_disponible"),     # ajeno o inexistente
    ("NB-５", "no_disponible"), (f"{ANCHO_NB}{ANCHO_GUION}５", "no_disponible"),              # el dígito, tal como se escribió
    (f"{ANCHO_NB}-05", "no_disponible"), (f"{ANCHO_NB}{ANCHO_GUION}", "no_disponible"), (f"{ANCHO_NB}- 5", "no_disponible"),
    (f"{ANCHO_NB}{ANCHO_GUION}{'9' * 30}", "no_disponible"),
    (f"{ANCHO_NB}5", "no_es_notebook"),
])
def test_clasificar_clave_de_ancho_completo(base_simulada, tema, esperado):
    """RF-17.34: la clave de ancho completo se trata como la clave (`ＮＢ-5` es `NB-5`), pero el resto, tal como se escribió,
    sigue siendo solo dígitos ASCII: `NB-５` no está disponible (decisión 11). Sin número válido, no disponible sin consultar."""
    from app.services.notebook_service import NotebookService

    clasificacion = asyncio.run(NotebookService().clasificar_clave(None, tema, USUARIO))

    assert clasificacion.tipo == esperado
    assert (clasificacion.notebook.clave_interna if clasificacion.notebook else None) == ("NB-5" if esperado == "propio" else None)


@pytest.mark.requisito("RF-17.34")
@pytest.mark.parametrize("tema", ["NB-５", f"{ANCHO_NB}{ANCHO_GUION}５", f"{ANCHO_NB}-05", f"{ANCHO_NB}{ANCHO_GUION}", f"{ANCHO_NB}- 5"])
def test_clave_de_ancho_completo_mal_formada_no_consulta_la_base(base_simulada, tema):
    """RF-17.34: una forma de clave de ancho completo con un resto que no es un número ASCII canónico es no disponible sin
    consultar la base."""
    from app.services.notebook_service import NotebookService

    assert asyncio.run(NotebookService().clasificar_clave(None, tema, USUARIO)).tipo == "no_disponible"
    assert base_simulada["consultas_de_notebook"] == []


@pytest.mark.requisito("RF-17.34")
def test_documentos_visibles_con_la_clave_de_ancho_completo(base_simulada):
    """RF-17.34: un documento unido a un tema con la clave de ancho completo se decide como el de la clave: visible si el
    notebook es del usuario y oculto si es ajeno."""
    from app.services.notebook_service import NotebookService

    base_simulada["documentos"] = [(1, f"{ANCHO_NB}-5"), (2, f"{ANCHO_NB}{ANCHO_GUION}7"), (3, "PRUEBA general"), (4, f"{ANCHO_NB}-９")]

    assert asyncio.run(NotebookService().ids_documentos_visibles(None, USUARIO)) == {1, 3}


@pytest.mark.requisito("RF-17.34")
def test_clasificar_clave_reclasifica_lo_que_la_base_iguala(base_simulada, monkeypatch):
    """RF-17.34: un tema sin forma de clave que la base iguala con el tema guardado de un notebook se trata como esa clave:
    propia si es del usuario, no disponible si es ajena o inexistente; si la base lo iguala con un tema común, o con nada,
    no es de notebook. Sin sesión de base de datos no hay con qué comparar."""
    from app.repositories.expediente_repository import ExpedienteRepository
    from app.services.notebook_service import NotebookService

    guardados = {"PRUEBA igual a la propia": "NB-5", "PRUEBA igual a la ajena": "NB-7", "PRUEBA igual a un tema": "PRUEBA otro tema"}
    consultados = []

    def _por_numero(self, db, numero):
        consultados.append(numero)
        return SimpleNamespace(CT_Num_expediente=guardados[numero]) if numero in guardados else None

    monkeypatch.setattr(ExpedienteRepository, "obtener_por_numero", _por_numero)
    # Ajuste de la vuelta 1 (B1): ahora también se pregunta cómo guardaría la base el tema; aquí lo guarda tal cual.
    monkeypatch.setattr(ExpedienteRepository, "como_lo_guarda_la_base", lambda self, db, numero: numero)
    monkeypatch.setattr(ExpedienteRepository, "como_lo_convierte_el_servidor", lambda self, db, numero: numero)
    base_de_datos = object()

    clasificar = lambda tema, db=base_de_datos: asyncio.run(NotebookService().clasificar_clave(db, tema, USUARIO))

    propia = clasificar("PRUEBA igual a la propia")
    assert (propia.tipo, propia.notebook.clave_interna) == ("propio", "NB-5")
    assert clasificar("PRUEBA igual a la ajena").tipo == "no_disponible"
    assert clasificar("PRUEBA igual a un tema").tipo == "no_es_notebook"
    assert clasificar("PRUEBA sin tema guardado").tipo == "no_es_notebook"
    assert clasificar("  PRUEBA igual a la propia  ").tipo == "propio", "el tema se compara sin espacios alrededor"
    consultados.clear()
    assert clasificar("PRUEBA igual a la propia", db=None).tipo == "no_es_notebook" and consultados == []
    clasificar("NB-7"), clasificar(f"{ANCHO_NB}-5")
    assert consultados == [], "una forma de clave no consulta la base para reclasificarse"


@pytest.mark.requisito("RF-17.34")
def test_clasificar_clave_con_lo_que_la_base_guardaria_como_clave(base_simulada, monkeypatch):
    """RF-17.34 (B1 de la revisión T6-T8): un tema sin forma de clave que SQL Server guardaría en la columna VARCHAR como una
    clave `NB-<n>` (`ŃB-5`, guion U+2010, signo menos U+2212) recibe el trato de esa clave aunque NO exista fila de tema: propia
    si el notebook es del usuario, no disponible si es ajeno o inexistente. Lo que se guardaría distinto de una clave (un
    tema legítimo con caracteres no Latin-1) sigue siendo un tema común."""
    from app.repositories.expediente_repository import ExpedienteRepository
    from app.services.notebook_service import NotebookService

    convertidos = {"ŃB-5": "NB-5", "NB‐5": "NB-5", "NB−7": "NB-7", "NB−999": "NB-999", "ŃB-05": "NB-05",
                   "NB‐５": "NB-5", "ŃB-５": "NB-5", "PRUEBA tema ń": "PRUEBA tema ń", "PRUEBA Ń": "PRUEBA N"}
    consultados = []

    def _como_lo_guarda(self, db, numero):
        consultados.append(numero)
        return convertidos.get(numero, numero)

    monkeypatch.setattr(ExpedienteRepository, "como_lo_guarda_la_base", _como_lo_guarda)
    monkeypatch.setattr(ExpedienteRepository, "como_lo_convierte_el_servidor", lambda self, db, numero: convertidos.get(numero, numero))
    monkeypatch.setattr(ExpedienteRepository, "obtener_por_numero", lambda self, db, numero: None)    # sin fila de tema
    base_de_datos = object()
    clasificar = lambda tema, db=base_de_datos: asyncio.run(NotebookService().clasificar_clave(db, tema, USUARIO))

    propia = clasificar("ŃB-5")
    assert (propia.tipo, propia.notebook.clave_interna) == ("propio", "NB-5")
    assert clasificar("NB‐5").tipo == "propio" and clasificar("  NB‐5  ").tipo == "propio"
    assert clasificar("NB−7").tipo == "no_disponible"                       # ajeno
    assert clasificar("NB−999").tipo == "no_disponible"                     # inexistente
    assert clasificar("ŃB-05").tipo == "no_disponible", "una clave no canónica no es un tema"
    # Decisión 17 (Andrés, 20/10/2026, B): si el resto, tal como se escribió, no son dígitos ASCII, no está disponible para nadie,
    # aunque la base lo guarde como la clave propia (decisión 11 sin excepciones).
    assert clasificar("NB‐５").tipo == "no_disponible", "el dígito de ancho completo no vale aunque la base lo guarde como NB-5"
    assert clasificar("ŃB-５").tipo == "no_disponible"
    assert clasificar("PRUEBA tema ń").tipo == "no_es_notebook" and clasificar("PRUEBA Ń").tipo == "no_es_notebook"
    consultados.clear()
    assert clasificar("ŃB-5", db=None).tipo == "no_es_notebook" and consultados == []
    clasificar("NB-7"), clasificar(f"{ANCHO_NB}-5")
    assert consultados == [], "una forma de clave no consulta la base para reclasificarse"


@pytest.mark.requisito("RF-17.34")
def test_clasificar_clave_con_caracteres_invisibles(base_simulada, monkeypatch, caplog):
    """RF-17.34 (B2 de la vuelta 2): un tema que sin sus caracteres de formato (categoría Cf: guion blando, ancho cero, BOM…)
    tiene forma de clave se trata como esa clave, aunque la conversión de la base los deje (el guion blando sobrevive a la
    página de códigos) o los cambie por `?`. Un tema legítimo con un carácter invisible, sin forma de clave, sigue siendo común.
    Si la base falla, `es_tema_de_clave` no lleva nada del contenido al registro."""
    from app.repositories.expediente_repository import ExpedienteRepository
    from app.services.notebook_service import NotebookService

    monkeypatch.setattr(ExpedienteRepository, "como_lo_guarda_la_base", lambda self, db, numero: numero.replace("​", "?"))
    monkeypatch.setattr(ExpedienteRepository, "como_lo_convierte_el_servidor", lambda self, db, numero: numero.replace("​", "?"))
    monkeypatch.setattr(ExpedienteRepository, "obtener_por_numero", lambda self, db, numero: None)
    base_de_datos = object()
    servicio = NotebookService()
    clasificar = lambda tema: asyncio.run(servicio.clasificar_clave(base_de_datos, tema, USUARIO))

    assert clasificar("N­B-5").tipo == "propio"
    assert clasificar("NB-​5").tipo == "no_disponible", "ya tiene forma de clave y el resto no es un número"
    assert clasificar("﻿NB-5").tipo == "propio"
    assert clasificar("N‍B-7").tipo == "no_disponible" and clasificar("⁠NB-999").tipo == "no_disponible"
    assert clasificar("N­B-05").tipo == "no_disponible"
    assert clasificar("N­B-５").tipo == "no_disponible", "dígito no ASCII: no disponible para todos (decisión 17)"
    assert clasificar("PRUEBA tema​").tipo == "no_es_notebook" and clasificar("PRUEBA­tema").tipo == "no_es_notebook"
    assert asyncio.run(servicio.es_tema_de_clave(base_de_datos, "NB-​7")) is True
    assert asyncio.run(servicio.es_tema_de_clave(base_de_datos, "PRUEBA tema​")) is False

    def _falla(self, db, numero):
        raise RuntimeError("PRUEBA contenido ajeno NB-7")

    monkeypatch.setattr(ExpedienteRepository, "como_lo_guarda_la_base", _falla)
    assert asyncio.run(servicio.es_tema_de_clave(base_de_datos, "PRUEBA otro tema")) is False
    assert "contenido ajeno" not in caplog.text and "NB-7" not in caplog.text, "el registro repite el texto de la excepción"


# --- RF-21.32 (T6): get_db no anota como error las respuestas 4xx previstas ----------------------------------------------------------

@pytest.mark.requisito("RF-21.32")
@pytest.mark.parametrize("estado", [400, 404, 422])
def test_get_db_no_anota_los_4xx(estado, caplog, monkeypatch):
    """RF-21.32: una `HTTPException` 4xx (respuesta prevista, como el 404 uniforme que repite un identificador) cruza la sesión
    de base de datos sin escribir `ERROR` en el registro del servidor, y se vuelve a lanzar igual con la sesión deshecha y cerrada."""
    from starlette.exceptions import HTTPException

    from app.db import database

    cerradas = []
    sesion_falsa = SimpleNamespace(rollback=lambda: cerradas.append("rollback"), close=lambda: cerradas.append("close"))
    monkeypatch.setattr(database, "SessionLocal", lambda: sesion_falsa)
    caplog.set_level(logging.DEBUG, logger="app")
    pedido = "session_PRUEBA_pedida_123"

    generador = database.get_db()
    next(generador)
    error = HTTPException(status_code=estado, detail=f"Conversación {pedido} no encontrada")
    with pytest.raises(HTTPException) as lanzada:
        generador.throw(error)

    assert lanzada.value is error
    assert pedido not in caplog.text and not [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert cerradas == ["rollback", "close"]


@pytest.mark.requisito("RF-21.32")
@pytest.mark.parametrize("error", [
    pytest.param(lambda: __import__("starlette.exceptions", fromlist=["HTTPException"]).HTTPException(502, "falla de PRUEBA@correo.invalid"), id="5xx"),
    pytest.param(lambda: RuntimeError("falla de PRUEBA@correo.invalid"), id="otro_error"),
])
def test_get_db_sigue_anotando_los_5xx_y_los_errores_enmascarados(error, caplog, monkeypatch):
    """RF-21.32 y RNF-08.2: los 5xx y cualquier otro error siguen anotándose como `ERROR`, con el correo enmascarado."""
    from app.db import database

    sesion_falsa = SimpleNamespace(rollback=lambda: None, close=lambda: None)
    monkeypatch.setattr(database, "SessionLocal", lambda: sesion_falsa)
    caplog.set_level(logging.DEBUG, logger="app")

    generador = database.get_db()
    next(generador)
    with pytest.raises(Exception):
        generador.throw(error())

    errores = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errores) == 1 and "Error en sesión de base de datos" in errores[0].getMessage()
    assert "PRUEBA@correo.invalid" not in caplog.text


# --- RNF-07.31, RNF-07.33 (T6): de quién es una conversación -----------------------------------------------------------------------

class _RedisDeConversaciones:
    """El historial en Redis, simulado a mano: solo guarda lo que se le da y anota cada lectura, para comprobar que decidir el
    dueño lee únicamente los metadatos y nunca los mensajes."""

    def __init__(self, metadatos=None):
        self.metadatos = dict(metadatos or {})
        self.lecturas_de_mensajes = []
        self.guardadas = []

    def load_metadata(self, session_id):
        return self.metadatos.get(session_id)

    def load_conversation(self, session_id):
        self.lecturas_de_mensajes.append(session_id)
        return None

    def save_conversation(self, session_id, user_id, messages, metadata, en_lista=True):
        self.guardadas.append((session_id, user_id, metadata.get("dueno"), en_lista))
        return True


@pytest.fixture
def almacen_de_conversaciones():
    """Un almacén de conversaciones nuevo, con un Redis simulado a mano."""
    from app.services.RAG.session_store import ConversationStore

    nuevo = ConversationStore()
    nuevo._redis_history = _RedisDeConversaciones()
    return nuevo


def _meta(user_id, dueno=None):
    datos = {"user_id": user_id}
    if dueno is not None:
        datos["dueno"] = dueno
    return datos


@pytest.mark.requisito("RNF-07.31")
@pytest.mark.parametrize("sesion, metadatos, usuario, esperado", [
    # Con dueño registrado decide solo el dueño, aunque el identificador diga otro usuario (escritura cruzada).
    ("session_a@x_1", _meta("a@x", "a@x"), "a@x", True),
    ("session_a@x_1", _meta("a@x", "b@x"), "a@x", False),
    ("session_a@x_1", _meta("a@x", "b@x"), "b@x", True),
    # Guardadas antes de esta spec, sin dueño: el usuario de sus metadatos o el tramo del identificador.
    ("session_a@x_1", _meta("a@x"), "a@x", True),
    ("session_a@x_1", _meta("a@x"), "b@x", False),
    ("session_a_b@x_17", _meta("a"), "a_b@x", True),                  # correo con `_`: los metadatos dicen otro, el tramo coincide
    ("session_a_b@x_17", _meta("a"), "a_b", False),                   # un prefijo del tramo no basta: coincide completo y exacto
    ("session_notebook_5_a@x_17", _meta("notebook"), "a@x", True),    # chat de notebook: tramo tras `session_notebook_<n>_`
    ("session_notebook_5_a@x_17", _meta("notebook"), "a@x_17", False),
    ("session_notebook_5_a@x_17", _meta("notebook"), "5_a@x", False),
    ("session_a@x_1", None, "a@x", None),                             # no guardada
])
def test_es_propia(almacen_de_conversaciones, sesion, metadatos, usuario, esperado):
    """RNF-07.31 y Definiciones: la conversación es propia si su dueño registrado es el usuario; sin dueño registrado (guardada
    antes), si el usuario de sus metadatos o el tramo del identificador coincide completo y exacto. Sin conversación, `None`.
    Solo se consultan los metadatos: los mensajes no se leen."""
    if metadatos is not None:
        almacen_de_conversaciones._redis_history.metadatos[sesion] = metadatos

    assert almacen_de_conversaciones.es_propia(sesion, usuario) is esperado
    assert almacen_de_conversaciones._redis_history.lecturas_de_mensajes == []
    assert sesion not in almacen_de_conversaciones._store and sesion not in almacen_de_conversaciones._metadata, "decidir el dueño cargó la conversación"


@pytest.mark.requisito("RNF-07.33")
def test_crear_una_conversacion_fija_al_usuario_autenticado_como_dueno(almacen_de_conversaciones):
    """RNF-07.33: la conversación nueva guarda como dueño al usuario autenticado, aunque su identificador contenga a otro, y es
    propia solo para él; el chat de un notebook no entra en la lista de conversaciones."""
    almacen_de_conversaciones.crear_conversacion("session_otro@x_1", dueno="yo@x")
    almacen_de_conversaciones.crear_conversacion("session_notebook_5_yo@x_2", dueno="yo@x", en_lista=False)
    almacen_de_conversaciones.get_session_history("session_otro@x_1").add_user_message("PRUEBA hola")
    almacen_de_conversaciones.get_session_history("session_notebook_5_yo@x_2").add_user_message("PRUEBA hola")

    assert almacen_de_conversaciones.es_propia("session_otro@x_1", "yo@x") is True
    assert almacen_de_conversaciones.es_propia("session_otro@x_1", "otro@x") is False
    assert almacen_de_conversaciones.es_propia("session_notebook_5_yo@x_2", "yo@x") is True
    guardadas = {s: (usuario, dueno, en_lista) for s, usuario, dueno, en_lista in almacen_de_conversaciones._redis_history.guardadas}
    assert guardadas["session_otro@x_1"] == ("yo@x", "yo@x", True), "se guardó y se indexó bajo otro usuario"
    assert guardadas["session_notebook_5_yo@x_2"][1:] == ("yo@x", False)


@pytest.mark.requisito("RNF-07.31")
def test_la_conversacion_efimera_no_se_guarda_ni_se_indexa(almacen_de_conversaciones):
    """RNF-07.31: la sesión efímera con que se atiende una conversación ajena vive en memoria solo mientras dura la respuesta:
    sin metadatos, sin índice y sin guardar en Redis; se descarta al terminar."""
    identificador = almacen_de_conversaciones.crear_efimera()
    historial = almacen_de_conversaciones.get_session_history(identificador)
    historial.add_user_message("PRUEBA hola")
    almacen_de_conversaciones.update_metadata(identificador)

    assert len(historial.messages) == 1
    assert almacen_de_conversaciones._redis_history.guardadas == [] and identificador not in almacen_de_conversaciones._metadata and identificador not in almacen_de_conversaciones._store
    almacen_de_conversaciones.descartar_efimera(identificador)
    assert identificador not in almacen_de_conversaciones._efimeras


# --- T7: NotebookServIA por su servicio y su auditoría (RF-17.33, RF-21.30) --------------------------------------------------

@pytest.mark.requisito("RF-17.33")
def test_rutas_de_notebooks_solo_usan_el_servicio():
    """RF-17.33: ninguna ruta de NotebookServIA usa directamente repositorios, Qdrant ni archivos: solo llama al servicio del
    módulo, a los servicios de auditoría y a la autenticación (se inspecciona el código fuente de las rutas)."""
    import ast
    import importlib.util
    from pathlib import Path

    origen = importlib.util.find_spec("app.routes.notebooks").origin
    arbol = ast.parse(Path(origen).read_text(encoding="utf-8"))
    importados, atributos = [], set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados += [a.name for a in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            importados += [nodo.module or ""] + [f"{nodo.module}.{a.name}" for a in nodo.names]
        elif isinstance(nodo, ast.Attribute):
            atributos.add(nodo.attr)

    prohibidos = ("app.repositories", "app.vectorstore", "app.services.documentos", "app.db.models")
    assert [m for m in importados if m.startswith(prohibidos)] == [], "la ruta importa acceso a datos"
    acceso_a_datos = {"obtener_por_id", "obtener_por_numero", "listar_por_expediente", "eliminar", "verificar_esta_procesado",
                      "delete_document_chunks", "obtener_ruta_archivo", "unlink"}
    assert atributos & acceso_a_datos == set(), "la ruta llama al acceso a datos"
    assert "app.services.notebook_service" in importados


class _BitacoraGrabadora:
    """Reemplaza al servicio base de la bitácora: guarda lo que se le pide registrar."""

    def __init__(self):
        self.registros = []

    async def registrar(self, **datos):
        self.registros.append(datos)
        return SimpleNamespace(CN_Id_bitacora=len(self.registros))


@pytest.mark.requisito("RF-21.30")
def test_auditoria_de_notebooks_sin_caracteres_de_control(monkeypatch):
    """RF-21.30: lo que la auditoría de notebooks escribe en la bitácora (texto e información adicional) no lleva NUL ni
    caracteres de control, aunque la clave que recibe los traiga; y lleva el tema, el número del documento y el resultado."""
    from app.repositories.expediente_repository import ExpedienteRepository
    from app.services.bitacora.notebooks_audit_service import NotebooksAuditService

    monkeypatch.setattr(ExpedienteRepository, "obtener_por_numero", lambda self, db, numero: None)
    servicio = NotebooksAuditService()
    servicio.bitacora_service = _BitacoraGrabadora()
    clave = "NB-5\x00\n\x1b[31m"

    asyncio.run(servicio.registrar_creacion(None, USUARIO, clave))
    asyncio.run(servicio.registrar_previsualizacion(None, USUARIO, clave, 9))
    asyncio.run(servicio.registrar_quitar(None, USUARIO, clave, 9, exito=True))
    asyncio.run(servicio.registrar_quitar(None, USUARIO, clave, 9, exito=False, tipo_error="interno"))

    registros = servicio.bitacora_service.registros
    assert [r["tipo_accion_id"] for r in registros] == [16, 10, 17, 17]
    for registro in registros:
        crudo = registro["texto"] + repr(registro["info_adicional"])
        assert "\x00" not in crudo and "\n" not in registro["texto"] and "\x1b" not in crudo
        assert registro["info_adicional"]["tema"] == "NB-5[31m" and registro["usuario_id"] == USUARIO
    assert [r["info_adicional"].get("documento_id") for r in registros] == [None, 9, 9, 9]
    assert [r["info_adicional"]["resultado"] for r in registros] == ["exitoso", "exitoso", "exitoso", "error"]
    assert registros[3]["info_adicional"]["tipo_error"] == "interno" and "tipo_error" not in registros[2]["info_adicional"]


@pytest.mark.requisito("RF-21.30")
def test_auditoria_de_notebooks_no_propaga_el_fallo_del_registro(monkeypatch):
    """RF-21.30: si el registro en la bitácora falla, cada método de la auditoría de notebooks devuelve None sin lanzar."""
    from app.repositories.expediente_repository import ExpedienteRepository
    from app.services.bitacora.notebooks_audit_service import NotebooksAuditService

    class _Rota:
        async def registrar(self, **datos):
            raise Exception("falla simulada de la bitácora")

    monkeypatch.setattr(ExpedienteRepository, "obtener_por_numero", lambda self, db, numero: None)
    servicio = NotebooksAuditService()
    servicio.bitacora_service = _Rota()

    assert asyncio.run(servicio.registrar_creacion(None, USUARIO, "NB-5")) is None
    assert asyncio.run(servicio.registrar_previsualizacion(None, USUARIO, "NB-5", 9)) is None
    assert asyncio.run(servicio.registrar_quitar(None, USUARIO, "NB-5", 9, exito=False, tipo_error="interno")) is None
