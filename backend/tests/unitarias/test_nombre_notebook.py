"""Reglas del nombre de un notebook, parte unitaria (spec 009, T2; RF-17.81, RF-17.82, RF-17.93, RF-17.84, RNF-07.82).

Sin base de datos: `validar_nombre` es una función pura y la comprobación de lo admitido y de los duplicados usa un repositorio
simulado. Los datos son inventados.
"""
import asyncio
from types import SimpleNamespace

import pytest

USUARIO = "PRUEBA-U1"


def _validar(nombre, **kwargs):
    from app.services.notebook_service import validar_nombre

    return validar_nombre(nombre, **kwargs)


@pytest.mark.requisito("RF-17.81")
@pytest.mark.parametrize("nombre", ["", " ", "   ", "\t \n", "​", " ​﻿ ", "­"])
def test_validar_nombre_vacio(nombre):
    """RF-17.81: un nombre vacío, de solo espacios o de solo caracteres de formato (U+200B…) es «nombre vacío»."""
    from app.services.notebook_service import NombreNoValido

    with pytest.raises(NombreNoValido) as error:
        _validar(nombre)
    assert error.value.motivo == "nombre vacío"
    assert error.value.mensaje == "El nombre del notebook no puede estar vacío"


@pytest.mark.requisito("RF-17.81")
def test_validar_nombre_vacio_con_su_mensaje():
    """RF-17.81: el mensaje del vacío es un parámetro, para que otro nombre (una fuente, spec 009b) lo reutilice."""
    from app.services.notebook_service import NombreNoValido

    with pytest.raises(NombreNoValido) as error:
        _validar("  ", mensaje_vacio="El nombre de la fuente no puede estar vacío")
    assert error.value.mensaje == "El nombre de la fuente no puede estar vacío" and error.value.motivo == "nombre vacío"


@pytest.mark.requisito("RF-17.82")
def test_validar_nombre_largo():
    """RF-17.82: 150 caracteres normalizados se aceptan; 151 es «nombre demasiado largo». Los espacios de los extremos no cuentan."""
    from app.services.notebook_service import NombreNoValido

    assert _validar("a" * 150) == "a" * 150
    assert _validar("  " + "a" * 150 + "  ") == "a" * 150
    with pytest.raises(NombreNoValido) as error:
        _validar("a" * 151)
    assert error.value.motivo == "nombre demasiado largo"
    assert error.value.mensaje == "El nombre no puede superar 150 caracteres."


@pytest.mark.requisito("RF-17.82")
def test_validar_nombre_normaliza_a_nfc_antes_de_contar():
    """RF-17.82, RF-17.84: «Cafe» + U+0301 es «Café» (NFC) y cuenta como un solo carácter; se recorta el exterior."""
    assert _validar("Cafe\u0301") == "Caf\u00e9"  # el combinante U+0301 se compone en la «é» precompuesta (NFC)
    assert _validar("  Informe  anual \n") == "Informe  anual"
    assert _validar("e\u0301" * 150) == "\u00e9" * 150  # 150 con combinante cuentan 150 tras componer

# --- RF-17.93, RF-17.84, RNF-07.82: lo admitido ---------------------------------------------------------------------------------

def _notebook(nombre: str) -> SimpleNamespace:
    return SimpleNamespace(CT_Nombre=nombre)


@pytest.fixture
def base_simulada(monkeypatch):
    """Un repositorio inventado: lo que la base guarda tal cual (todo salvo lo marcado) y los notebooks activos por usuario."""
    from app.repositories.notebook_repository import NotebookRepository

    base = {"no_guardable": set(), "activos": {USUARIO: []}, "consultas": []}

    def _como_lo_guarda(self, db, nombre):
        return "?" * len(nombre) if nombre in base["no_guardable"] else nombre

    def _listar(self, db, usuario_id):
        base["consultas"].append(usuario_id)
        return base["activos"].get(usuario_id, [])

    monkeypatch.setattr(NotebookRepository, "como_lo_guarda_la_base", _como_lo_guarda)
    monkeypatch.setattr(NotebookRepository, "listar_por_usuario", _listar)
    return base


def _admitido(nombre: str, usuario: str = USUARIO) -> str:
    from app.services.notebook_service import NotebookService

    return NotebookService().nombre_admitido(None, usuario, nombre)


@pytest.mark.requisito("RF-17.93")
def test_admitido_no_guardable(base_simulada):
    """RF-17.93: lo que la base no guarda tal cual (aquí, un emoji) es «nombre con caracteres no admitidos», nunca guardado
    degradado; y esa comprobación va antes que la de duplicados."""
    from app.services.notebook_service import NombreNoValido

    base_simulada["no_guardable"].add("Informe \U0001f600")
    base_simulada["activos"][USUARIO] = [_notebook("Informe \U0001f600")]
    with pytest.raises(NombreNoValido) as error:
        _admitido("Informe \U0001f600")
    assert error.value.motivo == "nombre con caracteres no admitidos"
    assert error.value.mensaje == "El nombre contiene caracteres no admitidos."


@pytest.mark.requisito("RF-17.84")
def test_admitido_distinto_y_con_tildes(base_simulada):
    """RF-17.84, D1: «Café» y «Cafe» son nombres distintos (las tildes distinguen)."""
    base_simulada["activos"][USUARIO] = [_notebook("Cafe")]
    assert _admitido("Café") == "Café"


@pytest.mark.requisito("RF-17.84")
@pytest.mark.parametrize("repetido", ["Informe anual", "informe ANUAL", "INFORME anual"])
def test_admitido_duplicado_sin_distinguir_mayusculas(base_simulada, repetido):
    """RF-17.84: otro notebook activo del usuario con el mismo nombre, con otra grafía de mayúsculas, es «nombre duplicado»."""
    from app.services.notebook_service import NombreNoValido

    base_simulada["activos"][USUARIO] = [_notebook("Informe anual")]
    with pytest.raises(NombreNoValido) as error:
        _admitido(repetido)
    assert error.value.motivo == "nombre duplicado"
    assert error.value.mensaje == "Ya tiene un notebook con ese nombre."


@pytest.mark.requisito("RNF-07.82")
def test_admitido_solo_compara_con_los_activos_propios(base_simulada):
    """RNF-07.82: solo se consultan los notebooks activos del propio usuario: el nombre de uno ajeno no cuenta ni se consulta."""
    base_simulada["activos"]["PRUEBA-U9"] = [_notebook("Informe de otro")]
    assert _admitido("Informe de otro") == "Informe de otro"
    assert base_simulada["consultas"] == [USUARIO]


@pytest.mark.requisito("RF-17.85")
def test_crear_aplica_las_mismas_reglas(base_simulada, monkeypatch):
    """RF-17.85: crear valida igual que renombrar: recorta, normaliza y guarda el nombre normalizado; si no es válido no crea."""
    from app.repositories.notebook_repository import NotebookRepository
    from app.services.notebook_service import NombreNoValido, NotebookService

    creados = []
    monkeypatch.setattr(NotebookRepository, "crear", lambda self, db, nombre, usuario: creados.append(nombre) or SimpleNamespace())
    base_simulada["activos"][USUARIO] = [_notebook("Informe")]

    asyncio.run(NotebookService().crear_notebook(None, "  Café  ", USUARIO))
    assert creados == ["Café"]
    for invalido in ("  ", "informe", "a" * 151):
        with pytest.raises(NombreNoValido):
            asyncio.run(NotebookService().crear_notebook(None, invalido, USUARIO))
    assert creados == ["Café"]


# --- T3: renombrar y eliminar (RF-17.80, 17.83, 17.84, 17.87, RNF-07.80, RF-21.81-21.83) -----------------------------------------

@pytest.mark.requisito("RF-17.83")
def test_admitido_propio_sin_cambios_y_solo_mayusculas(base_simulada):
    """RF-17.83, RF-17.84: al renombrar, el nombre idéntico al propio es «sin cambios» (antes del duplicado, aunque el propio esté
    entre los activos); solo cambiar las mayúsculas sí cambia; el de OTRO notebook activo sigue siendo duplicado; «Café» ≠ «Cafe»."""
    from app.services.notebook_service import NombreNoValido, NotebookService, SinCambios

    propio, otro = _notebook("Informe anual"), _notebook("Presupuesto")
    base_simulada["activos"][USUARIO] = [propio, otro]
    servicio = NotebookService()
    with pytest.raises(SinCambios):
        servicio.nombre_admitido(None, USUARIO, "Informe anual", propio=propio)
    assert servicio.nombre_admitido(None, USUARIO, "INFORME ANUAL", propio=propio) == "INFORME ANUAL"
    with pytest.raises(NombreNoValido) as error:
        servicio.nombre_admitido(None, USUARIO, "presupuesto", propio=propio)
    assert error.value.motivo == "nombre duplicado"


@pytest.fixture
def base_de_notebooks(monkeypatch):
    """Notebooks inventados por id: «5» propio, «6» de otro usuario, «7» eliminado (el repositorio ya no lo devuelve) y un
    registro de lo renombrado o marcado como eliminado."""
    from app.repositories.notebook_repository import NotebookRepository

    notebooks = {5: SimpleNamespace(CN_Id_notebook=5, CN_Id_usuario=USUARIO, CT_Nombre="Informe", clave_interna="NB-5"),
                 6: SimpleNamespace(CN_Id_notebook=6, CN_Id_usuario="PRUEBA-U9", CT_Nombre="Ajeno", clave_interna="NB-6")}
    hechos = {"renombrados": [], "eliminados": []}
    monkeypatch.setattr(NotebookRepository, "obtener_por_id", lambda self, db, i: notebooks.get(i))
    monkeypatch.setattr(NotebookRepository, "listar_por_usuario",
                        lambda self, db, u: [n for n in notebooks.values() if n.CN_Id_usuario == u])
    monkeypatch.setattr(NotebookRepository, "como_lo_guarda_la_base", lambda self, db, nombre: nombre)
    monkeypatch.setattr(NotebookRepository, "renombrar", lambda self, db, nb, nombre: hechos["renombrados"].append(nombre) or nb)
    monkeypatch.setattr(NotebookRepository, "marcar_eliminado", lambda self, db, nb: hechos["eliminados"].append(nb) or nb)
    return hechos


@pytest.mark.requisito("RNF-07.80")
@pytest.mark.parametrize("texto_id", ["abc", "05", "+5", " 5 ", "５", "9" * 30, "0", "6", "7", "999", "", "5.0"])
def test_renombrar_y_eliminar_no_disponible_antes_de_validar(base_de_notebooks, texto_id):
    """RNF-07.80, RF-11.32: un id no canónico, ajeno, eliminado o inexistente es «notebook no disponible» ANTES de mirar el
    nombre (aunque este sea inválido) y no cambia nada. «5» sí es propio: ahí el nombre inválido da su propio error."""
    from app.services.notebook_service import NombreNoValido, NotebookService, RecursoNoDisponible

    servicio = NotebookService()
    with pytest.raises(RecursoNoDisponible) as error:
        asyncio.run(servicio.renombrar_notebook(None, texto_id, "   ", USUARIO))
    assert error.value.motivo == "notebook no disponible"
    with pytest.raises(RecursoNoDisponible):
        asyncio.run(servicio.eliminar_notebook(None, texto_id, USUARIO))
    assert base_de_notebooks == {"renombrados": [], "eliminados": []}
    with pytest.raises(NombreNoValido):
        asyncio.run(servicio.renombrar_notebook(None, "5", "   ", USUARIO))


@pytest.mark.requisito("RF-17.80")
@pytest.mark.requisito("RF-17.83")
@pytest.mark.requisito("RF-17.87")
def test_renombrar_y_eliminar_propio(base_de_notebooks):
    """RF-17.80, 17.83, 17.87: renombrar guarda el nombre normalizado y dice que cambió; el mismo nombre no escribe y dice que no;
    eliminar marca el notebook propio."""
    from app.services.notebook_service import NotebookService

    servicio = NotebookService()
    notebook, cambiado = asyncio.run(servicio.renombrar_notebook(None, "5", "  Nuevo  ", USUARIO))
    assert cambiado is True and base_de_notebooks["renombrados"] == ["Nuevo"]
    notebook, cambiado = asyncio.run(servicio.renombrar_notebook(None, "5", " Informe ", USUARIO))
    assert cambiado is False and base_de_notebooks["renombrados"] == ["Nuevo"]
    eliminado = asyncio.run(servicio.eliminar_notebook(None, "5", USUARIO))
    assert eliminado.CN_Id_notebook == 5 and base_de_notebooks["eliminados"] == [eliminado]


@pytest.mark.requisito("RF-21.81")
@pytest.mark.requisito("RF-21.82")
@pytest.mark.requisito("RF-21.83")
def test_registro_sin_nombres_y_motivos_fijos(monkeypatch):
    """RF-21.81-21.83, RNF-07.24: renombrar y eliminar dejan su tipo (19 y 20), la clave `NB-<id>`, el resultado y, si fallan, un
    motivo fijo y su clasificación; ninguna fila lleva un nombre; y si la bitácora falla, devuelven None sin lanzar."""
    from app.services.bitacora.notebooks_audit_service import NotebooksAuditService

    servicio = NotebooksAuditService()
    filas = []

    async def _registrar(**kwargs):
        filas.append(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr(servicio.bitacora_service, "registrar", _registrar)
    monkeypatch.setattr(servicio, "_id_del_tema", lambda db, clave: None)
    asyncio.run(servicio.registrar_renombrado(None, USUARIO, "NB-5", exito=True))
    asyncio.run(servicio.registrar_renombrado(None, USUARIO, "NB-5", exito=False, motivo="nombre vacío", tipo_error="validacion"))
    asyncio.run(servicio.registrar_eliminacion(None, USUARIO, "NB-5", exito=True))
    asyncio.run(servicio.registrar_eliminacion(None, USUARIO, "NB-5", exito=False, motivo="error inesperado", tipo_error="interno"))
    assert [f["tipo_accion_id"] for f in filas] == [19, 19, 20, 20]
    assert [f["info_adicional"]["resultado"] for f in filas] == ["exitoso", "error", "exitoso", "error"]
    assert all(f["info_adicional"]["tema"] == "NB-5" for f in filas)
    assert filas[1]["info_adicional"]["motivo"] == "nombre vacío" and filas[1]["info_adicional"]["tipo_error"] == "validacion"
    assert filas[3]["info_adicional"]["motivo"] == "error inesperado" and filas[3]["info_adicional"]["tipo_error"] == "interno"

    async def _falla(**kwargs):
        raise Exception("falla simulada")

    monkeypatch.setattr(servicio.bitacora_service, "registrar", _falla)
    assert asyncio.run(servicio.registrar_renombrado(None, USUARIO, "NB-5", exito=True)) is None
    assert asyncio.run(servicio.registrar_eliminacion(None, USUARIO, "NB-5", exito=True)) is None


# --- T4: la conversación de un notebook eliminado no está disponible (RF-17.88, RF-17.89) -----------------------------------------

def _disponible(session_id, notebook, monkeypatch):
    """`conversacion_disponible` con un repositorio simulado que devuelve `notebook` (o nada) y cuenta las consultas."""
    from app.repositories.notebook_repository import NotebookRepository
    from app.services.notebook_service import NotebookService

    consultas = []
    monkeypatch.setattr(NotebookRepository, "obtener_por_id", lambda self, db, id_notebook: consultas.append(id_notebook) or notebook)
    return asyncio.run(NotebookService().conversacion_disponible(None, session_id, USUARIO)), consultas


@pytest.mark.requisito("RF-17.88")
def test_conversacion_disponible(monkeypatch):
    """RF-17.88: la conversación de un notebook (`session_notebook_<id>_…`) solo está disponible si el notebook existe, no está
    eliminado (el repositorio ya no lo devuelve) y es del usuario; un id no canónico no lo está y no consulta la base; la del
    chat general no depende de ningún notebook."""
    propio = SimpleNamespace(CN_Id_usuario=USUARIO)
    ajeno = SimpleNamespace(CN_Id_usuario="PRUEBA-U2")
    assert _disponible("session_notebook_7_a@b.cr_123", propio, monkeypatch) == (True, [7])
    assert _disponible("session_notebook_7_a@b.cr_123", None, monkeypatch) == (False, [7])
    assert _disponible("session_notebook_7_a@b.cr_123", ajeno, monkeypatch) == (False, [7])
    for no_canonico in ("session_notebook_07_a@b.cr_1", "session_notebook_0_a@b.cr_1", "session_notebook_" + "9" * 30 + "_a@b.cr_1"):
        assert _disponible(no_canonico, propio, monkeypatch) == (False, []), no_canonico
    for general in ("session_a@b.cr_123", "session_notebook_a@b.cr_123", ""):
        assert _disponible(general, None, monkeypatch) == (True, []), general
