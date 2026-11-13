"""Selección de fuentes del chat del notebook, parte unitaria (spec 009b, T1; RF-11.105, RF-11.106, RNF-07.100).

Sin base de datos: `seleccion_efectiva` usa repositorios simulados y el formato del campo se comprueba con el modelo de la
petición. Los datos son inventados.
"""
import asyncio
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

CLAVE = "NB-7"


def _documento(id_documento: int, estado: str = "Procesado"):
    return SimpleNamespace(CN_Id_documento=id_documento, estado=SimpleNamespace(CT_Nombre_estado=estado))


def _servicio(documentos, tema_existe=True):
    """Un `NotebookService` cuyo tema tiene `documentos`; `listar_por_expediente` respeta `solo_procesados` como el real."""
    from app.services.notebook_service import NotebookService

    servicio = NotebookService()
    servicio.expediente_repo = SimpleNamespace(obtener_por_numero=lambda db, numero: object() if tema_existe and numero == CLAVE else None)

    def listar(db, tema, solo_procesados=False):
        return [d for d in documentos if not solo_procesados or d.estado.CT_Nombre_estado == "Procesado"]

    servicio.documento_repo = SimpleNamespace(listar_por_expediente=listar)
    return servicio


def _seleccion(servicio, ids):
    return servicio.seleccion_efectiva(None, SimpleNamespace(clave_interna=CLAVE), ids)


@pytest.mark.requisito("RF-11.105")
def test_seleccion_efectiva_es_la_interseccion_con_los_procesados():
    """RF-11.105: la selección efectiva son los marcados que son del notebook y están Procesados."""
    servicio = _servicio([_documento(1), _documento(2), _documento(3)])
    assert _seleccion(servicio, [1, 3]) == {1, 3}
    assert _seleccion(servicio, [2, 2, 2]) == {2}


@pytest.mark.requisito("RF-11.106")
def test_seleccion_efectiva_solo_procesado():
    """RF-11.106: una fuente Pendiente o Error marcada no llega al chat."""
    servicio = _servicio([_documento(1), _documento(2, "Pendiente"), _documento(3, "Error")])
    assert _seleccion(servicio, [1, 2, 3]) == {1}
    assert _seleccion(servicio, [2, 3]) == set()


@pytest.mark.requisito("RNF-07.100")
def test_seleccion_efectiva_descarta_ajenos_inexistentes_y_enormes():
    """RNF-07.100: ids de otro notebook, inexistentes, negativos o más grandes que cualquier columna se descartan sin error."""
    servicio = _servicio([_documento(1)])
    assert _seleccion(servicio, [1, 99, 0, -4, 2 ** 70]) == {1}
    assert _seleccion(servicio, [99, 2 ** 70]) == set()


@pytest.mark.requisito("RF-11.105")
def test_seleccion_efectiva_vacia_y_sin_tema():
    """RF-11.105: una lista vacía, o un notebook sin tema, da una selección vacía."""
    assert _seleccion(_servicio([_documento(1)]), []) == set()
    assert _seleccion(_servicio([_documento(1)], tema_existe=False), [1]) == set()


@pytest.mark.requisito("RF-11.105")
def test_seleccion_vacia_es_una_excepcion_propia():
    """RF-11.105: `SeleccionVacia` existe para que el router la responda como 400."""
    from app.services.notebook_service import SeleccionVacia

    assert issubclass(SeleccionVacia, Exception)


@pytest.mark.requisito("RF-11.105")
@pytest.mark.parametrize("documentos", [["5"], [5.5], [True], [None], [[1]], ["5", 1], 5, "1"])
def test_seleccion_formato_422(documentos):
    """RF-11.105: `"5"`, `5.5`, `true`, `null` dentro de la lista (o un valor que no es lista) son un 422, no se convierten."""
    from app.routes.rag import ConsultaConHistorialRequest

    with pytest.raises(ValidationError):
        ConsultaConHistorialRequest(query="PRUEBA", session_id="s", documentos=documentos)


@pytest.mark.requisito("RF-11.105")
@pytest.mark.parametrize("documentos", [None, [], [1, 2, 3]])
def test_seleccion_formato_admitido(documentos):
    """RF-11.105: ausente (`None`), vacía o de enteros es válida."""
    from app.routes.rag import ConsultaConHistorialRequest

    assert ConsultaConHistorialRequest(query="PRUEBA", session_id="s", documentos=documentos).documentos == documentos
    assert ConsultaConHistorialRequest(query="PRUEBA", session_id="s").documentos is None


# --- T5: reglas del nombre de una fuente (RF-19.102, RF-19.106, RF-19.107, RNF-07.101) -----------------------------------------

@pytest.mark.requisito("RF-19.102")
@pytest.mark.parametrize("interno, esperada", [
    ("informe.v2.pdf", ".pdf"), (".notas", ""), ("sin_punto", ""), ("a.b", ".b"), ("termina.", "."), ("", ""),
])
def test_extension_de(interno, esperada):
    """RF-19.102: la extensión es desde el ÚLTIMO punto, pero un punto inicial (`.notas`) no la inicia; sin punto, ninguna."""
    from app.services.notebook_service import extension_de

    assert extension_de(interno) == esperada


@pytest.mark.requisito("RF-19.103")
def test_nombre_mostrado_usa_el_visible_o_el_interno():
    """RF-19.103: se muestra el nombre visible; sin él (NULL, vacío o un objeto que ni tiene el atributo) el interno."""
    from app.services.notebook_service import nombre_mostrado

    assert nombre_mostrado(SimpleNamespace(CT_Nombre_visible="Nuevo.pdf", CT_Nombre_archivo="a.pdf")) == "Nuevo.pdf"
    assert nombre_mostrado(SimpleNamespace(CT_Nombre_visible=None, CT_Nombre_archivo="a.pdf")) == "a.pdf"
    assert nombre_mostrado(SimpleNamespace(CT_Nombre_visible="", CT_Nombre_archivo="a.pdf")) == "a.pdf"
    assert nombre_mostrado(SimpleNamespace(CT_Nombre_archivo="a.pdf")) == "a.pdf"


@pytest.mark.requisito("RF-19.106")
def test_validar_nombre_con_mensaje_de_vacio_propio():
    """RF-19.106: la regla de la 009 se reutiliza con el mensaje de vacío de la fuente (sin punto final); el de largo no cambia."""
    from app.services.notebook_service import NombreNoValido, validar_nombre

    for vacio in ("", "   ", None, "​"):
        with pytest.raises(NombreNoValido) as error:
            validar_nombre(vacio, mensaje_vacio="El nombre de la fuente no puede estar vacío")
        assert error.value.mensaje == "El nombre de la fuente no puede estar vacío"
        assert error.value.motivo == "nombre vacío"
    with pytest.raises(NombreNoValido) as error:
        validar_nombre("a" * 151, mensaje_vacio="otro")
    assert error.value.mensaje == "El nombre no puede superar 150 caracteres."
    assert validar_nombre("  café  ", mensaje_vacio="otro") == "café"


def _fuente(id_documento, interno="informe.pdf", visible=None, estado="Procesado", notebook="NB-7"):
    return SimpleNamespace(
        CN_Id_documento=id_documento, CT_Nombre_archivo=interno, CT_Nombre_visible=visible, esta_quitado=False,
        estado_procesamiento=SimpleNamespace(CT_Nombre_estado=estado), expedientes=[SimpleNamespace(CT_Num_expediente=notebook)])


class _Fuentes:
    """Un servicio con el notebook `NB-7` (id 7, de `U1`) y las fuentes dadas; anota qué se guardó."""

    def __init__(self, documentos, guarda_igual=True):
        from app.services.notebook_service import NotebookService

        self.documentos, self.guardados = documentos, []
        self.servicio = NotebookService()
        notebook = SimpleNamespace(clave_interna="NB-7", CN_Id_usuario="U1")
        self.servicio.notebook_repo = SimpleNamespace(obtener_por_id=lambda db, i: notebook if i == 7 else None)
        self.servicio.expediente_repo = SimpleNamespace(obtener_por_numero=lambda db, numero: object())

        def renombrar(db, documento, nombre):
            documento.CT_Nombre_visible = nombre
            self.guardados.append((documento.CN_Id_documento, nombre))
            return documento

        def listar(db, tema, solo_procesados=False):
            return [d for d in documentos if d.expedientes[0].CT_Num_expediente == "NB-7"]

        self.servicio.documento_repo = SimpleNamespace(
            obtener_por_id=lambda db, i: next((d for d in documentos if d.CN_Id_documento == i), None),
            listar_por_expediente=listar,
            como_lo_guarda_la_base=(lambda db, n: n) if guarda_igual else (lambda db, n: n.replace("\U0001f600", "?")),
            renombrar=renombrar)

    def renombrar(self, texto_nb, texto_doc, base, usuario="U1"):
        return asyncio.run(self.servicio.renombrar_documento(None, texto_nb, texto_doc, base, usuario))


@pytest.mark.requisito("RF-19.102")
@pytest.mark.requisito("RF-19.103")
def test_renombrar_documento_guarda_base_normalizada_mas_extension():
    """RF-19.102, RF-19.103, RF-19.107: la base se normaliza (NFC, sin espacios) y se le pega la extensión del nombre interno;
    en Error se permite. El nombre interno no cambia."""
    f = _Fuentes([_fuente(1, "informe.v2.pdf", estado="Error")])
    documento, cambiado = f.renombrar("7", "1", "  Resumen café  ")
    assert cambiado is True and f.guardados == [(1, "Resumen café.pdf")]
    assert documento.CT_Nombre_visible == "Resumen café.pdf" and documento.CT_Nombre_archivo == "informe.v2.pdf"


@pytest.mark.requisito("RF-19.106")
def test_renombrar_documento_rechazos_de_la_base():
    """RF-19.106: vacío (sin punto final), de más de 150 y con caracteres que la base no guarda: `NombreNoValido` y no guarda."""
    from app.services.notebook_service import NombreNoValido

    f = _Fuentes([_fuente(1, estado="Error")], guarda_igual=False)
    casos = [("   ", "El nombre de la fuente no puede estar vacío"),
             ("a" * 151, "El nombre no puede superar 150 caracteres."),
             ("hola \U0001f600", "El nombre contiene caracteres no admitidos.")]
    for base, mensaje in casos:
        with pytest.raises(NombreNoValido) as error:
            f.renombrar("7", "1", base)
        assert error.value.mensaje == mensaje
    assert f.guardados == []
    # 150 exactos sin contar la extensión: se acepta
    f = _Fuentes([_fuente(1, estado="Error")])
    assert f.renombrar("7", "1", "a" * 150)[1] is True


@pytest.mark.requisito("RF-19.106")
def test_renombrar_documento_identico_no_cambia_nada():
    """RF-19.106: la misma base (mismo nombre mostrado, mayúsculas incluidas) no guarda nada; cambiar solo mayúsculas sí."""
    f = _Fuentes([_fuente(1, "informe.pdf", visible="Resumen.pdf", estado="Error"), _fuente(2, "otro.pdf")])
    _, cambiado = f.renombrar("7", "1", "Resumen")
    assert cambiado is False and f.guardados == []
    f2 = _Fuentes([_fuente(1, "informe.pdf", estado="Error")])
    assert f2.renombrar("7", "1", "informe")[1] is False  # el interno cuenta como nombre mostrado
    assert f.renombrar("7", "1", "RESUMEN")[1] is True and f.guardados == [(1, "RESUMEN.pdf")]


@pytest.mark.requisito("RF-19.106")
def test_renombrar_documento_duplicado_sin_distinguir_mayusculas():
    """RF-19.106: el nombre completo igual (sin mayúsculas) al MOSTRADO de otra fuente del notebook es «nombre duplicado»; la
    fuente de otro notebook no cuenta."""
    from app.services.notebook_service import NombreNoValido

    f = _Fuentes([_fuente(1, "informe.pdf", estado="Error"), _fuente(2, "otro.pdf", visible="Cartas.PDF"),
                  _fuente(3, "libre.pdf", notebook="NB-8")])
    with pytest.raises(NombreNoValido) as error:
        f.renombrar("7", "1", "cartas")
    assert error.value.motivo == "nombre duplicado"
    assert error.value.mensaje == "Ya hay una fuente con ese nombre en este notebook."
    assert f.renombrar("7", "1", "libre")[1] is True  # el nombre de la fuente de otro notebook está libre


@pytest.mark.requisito("RF-19.107")
def test_renombrar_documento_en_proceso_no_se_permite():
    """RF-19.107: una fuente Pendiente responde «fuente en proceso» con el aviso, aunque el nombre sea inválido (se decide
    antes que las reglas del nombre) y sin guardar."""
    from app.services.notebook_service import NombreNoValido

    f = _Fuentes([_fuente(1, estado="Pendiente")])
    for base in ("Nuevo", "   "):
        with pytest.raises(NombreNoValido) as error:
            f.renombrar("7", "1", base)
        assert error.value.motivo == "fuente en proceso" and error.value.mensaje == "Espere a que termine de procesarse."
    assert f.guardados == []


@pytest.mark.requisito("RNF-07.101")
def test_renombrar_documento_no_disponible_antes_de_validar_el_nombre():
    """RNF-07.101: notebook ajeno o inexistente, id no canónico, fuente de otro notebook o inexistente: `RecursoNoDisponible`
    con su motivo, ANTES de validar el nombre (aquí vacío), sin guardar."""
    from app.services.bitacora.notebooks_audit_service import MOTIVO_DOCUMENTO_NO_DISPONIBLE, MOTIVO_NOTEBOOK_NO_DISPONIBLE
    from app.services.notebook_service import RecursoNoDisponible

    f = _Fuentes([_fuente(1, estado="Error"), _fuente(2, notebook="NB-8", estado="Error")])
    casos = [("8", "1", MOTIVO_NOTEBOOK_NO_DISPONIBLE), ("05", "1", MOTIVO_NOTEBOOK_NO_DISPONIBLE),
             ("abc", "1", MOTIVO_NOTEBOOK_NO_DISPONIBLE), ("7", "2", MOTIVO_DOCUMENTO_NO_DISPONIBLE),
             ("7", "99", MOTIVO_DOCUMENTO_NO_DISPONIBLE), ("7", "01", MOTIVO_DOCUMENTO_NO_DISPONIBLE),
             ("7", "+1", MOTIVO_DOCUMENTO_NO_DISPONIBLE), ("7", "9" * 30, MOTIVO_DOCUMENTO_NO_DISPONIBLE)]
    for texto_nb, texto_doc, motivo in casos:
        with pytest.raises(RecursoNoDisponible) as error:
            f.renombrar(texto_nb, texto_doc, "   ")
        assert error.value.motivo == motivo, (texto_nb, texto_doc)
    with pytest.raises(RecursoNoDisponible):
        f.renombrar("7", "1", "   ", usuario="OTRO")  # el notebook es de U1
    assert f.guardados == []


class _VectorSimulado:
    """El núcleo `vectorstore` simulado: anota cada `actualizar_nombre_de_documento` y falla en las llamadas indicadas (1, 2…)."""

    def __init__(self, fallan=()):
        self.llamadas, self.fallan = [], set(fallan)

    async def actualizar_nombre_de_documento(self, document_id, nombre):
        self.llamadas.append((document_id, nombre))
        if len(self.llamadas) in self.fallan:
            raise RuntimeError("falla simulada de Qdrant con C:/ruta")


def _renombrar_con_vector(monkeypatch, documentos, vector, falla_la_base=False):
    from app.services import notebook_service as modulo

    monkeypatch.setattr(modulo, "get_vectorstore_backend", lambda: vector)
    f = _Fuentes(documentos)
    if falla_la_base:
        def _falla(db, documento, nombre):
            raise RuntimeError("falla simulada de la base")

        f.servicio.documento_repo.renombrar = _falla
    return f


@pytest.mark.requisito("RF-19.104")
def test_renombrar_procesado_actualiza_qdrant_antes_que_la_base(monkeypatch):
    """RF-19.104: una fuente Procesado actualiza primero los fragmentos (con el nombre nuevo) y después guarda la fila; una en
    Error no llama a Qdrant (no tiene fragmentos)."""
    vector = _VectorSimulado()
    f = _renombrar_con_vector(monkeypatch, [_fuente(1), _fuente(2, estado="Error")], vector)
    assert f.renombrar("7", "1", "Nuevo")[1] is True
    assert vector.llamadas == [(1, "Nuevo.pdf")] and f.guardados == [(1, "Nuevo.pdf")]
    f.renombrar("7", "2", "Otro")
    assert vector.llamadas == [(1, "Nuevo.pdf")] and (2, "Otro.pdf") in f.guardados


@pytest.mark.requisito("RF-19.105")
def test_renombrar_compensacion(monkeypatch):
    """RF-19.105, RF-19.108: si falla Qdrant se devuelve el nombre anterior a los fragmentos y no se guarda la fila; si falla la
    base se devuelve el anterior en Qdrant; si falla también la compensación, igual responde `ErrorAlRenombrar` (sin el texto
    de la excepción)."""
    from app.services.notebook_service import ErrorAlRenombrar

    # 1) Falla Qdrant (1.ª llamada): compensación con el anterior (el interno, porque no tenía nombre visible); la base intacta
    vector = _VectorSimulado(fallan={1})
    f = _renombrar_con_vector(monkeypatch, [_fuente(1)], vector)
    with pytest.raises(ErrorAlRenombrar) as error:
        f.renombrar("7", "1", "Nuevo")
    assert vector.llamadas == [(1, "Nuevo.pdf"), (1, "informe.pdf")] and f.guardados == []
    assert "C:/ruta" not in str(error.value) and isinstance(error.value.causa, RuntimeError)

    # 2) Falla la base: Qdrant ya tenía el nuevo y se devuelve el anterior (el visible)
    vector = _VectorSimulado()
    f = _renombrar_con_vector(monkeypatch, [_fuente(1, visible="Previo.pdf")], vector, falla_la_base=True)
    with pytest.raises(ErrorAlRenombrar):
        f.renombrar("7", "1", "Nuevo")
    assert vector.llamadas == [(1, "Nuevo.pdf"), (1, "Previo.pdf")] and f.guardados == []

    # 3) Falla la base y también la compensación: riesgo residual aceptado, pero la respuesta sigue siendo ErrorAlRenombrar
    vector = _VectorSimulado(fallan={2})
    f = _renombrar_con_vector(monkeypatch, [_fuente(1)], vector, falla_la_base=True)
    with pytest.raises(ErrorAlRenombrar):
        f.renombrar("7", "1", "Nuevo")
    assert len(vector.llamadas) == 2

    # 4) Falla la base en una fuente en Error: no hay fragmentos que devolver
    vector = _VectorSimulado()
    f = _renombrar_con_vector(monkeypatch, [_fuente(1, estado="Error")], vector, falla_la_base=True)
    with pytest.raises(ErrorAlRenombrar):
        f.renombrar("7", "1", "Nuevo")
    assert vector.llamadas == []


@pytest.mark.requisito("RF-19.104")
def test_a_fragmento_cita_el_nombre_visible_y_no_el_de_la_ruta():
    """RF-19.104 · una fuente renombrada: el fragmento nombra el `nombre_archivo` actual (el que renombra T6), mientras la
    ruta de descarga sigue siendo la del archivo en disco."""
    from langchain_core.documents import Document

    from app.services.RAG.document_formatter import a_fragmento

    ruta = "uploads/NB-7/PRUEBA_a.txt"
    f = a_fragmento(Document(page_content="x", metadata={"nombre_archivo": "PRUEBA renombrada.txt", "ruta_archivo": ruta}))
    assert f.archivo == "PRUEBA renombrada.txt" and f.ruta == ruta
    # el chat general trae el nombre en `archivo`
    assert a_fragmento(Document(page_content="x", metadata={"archivo": "PRUEBA renombrada.txt", "ruta_archivo": ruta})).archivo \
        == "PRUEBA renombrada.txt"


@pytest.mark.requisito("RF-19.104")
def test_a_fragmento_conserva_los_respaldos_para_documentos_antiguos():
    """RF-19.104 · sin `nombre_archivo` ni `archivo` el nombre sale de la ruta; sin nada, «N/A» (no empeora lo de antes)."""
    from langchain_core.documents import Document

    from app.services.RAG.document_formatter import a_fragmento

    assert a_fragmento(Document(page_content="x", metadata={"ruta_archivo": "uploads/NB-7/PRUEBA_a.txt"})).archivo == "PRUEBA_a.txt"
    assert a_fragmento(Document(page_content="x", metadata={"nombre_archivo": "", "ruta_archivo": "uploads/NB-7/b.pdf"})).archivo == "b.pdf"
    assert a_fragmento(Document(page_content="x", metadata={})).archivo == "N/A"
