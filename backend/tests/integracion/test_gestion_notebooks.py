"""Spec 009 — Gestión de notebooks (renombrar y eliminar). T1: migración y catálogo. T2: reglas del nombre al crear y su bitácora.

Ver también: specs/009-gestion-de-notebooks/spec.md (RN-01.80, RF-21.80, RF-17.81-17.85, RF-17.93, RF-21.81, RF-21.83).
"""
import json

import pytest
from sqlalchemy import text

from tests.integracion.conftest import _consultar
from tests.integracion.conftest import RESPUESTA_SIMULADA, _consultar_chat, _pregunta_sobre, _todo_lo_que_recibio_el_modelo
from tests.soporte.flujos import cargar, crear_notebook, documento_de_prueba
from tests.soporte.nombres import PREFIJO_DATOS

CREAR_NOTEBOOK = 16


@pytest.mark.requisito("RN-01.80")
@pytest.mark.requisito("RF-21.80")
def test_migracion_tipos_y_columna():
    """RN-01.80, RF-21.80: T_Notebook tiene CF_Fecha_eliminacion (admite vacío) y el catálogo suma 19 y 20 sin tocar el resto."""
    from app.constants.tipos_accion import DESCRIPCIONES_TIPOS_ACCION, TiposAccion

    columna = _consultar(
        "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = 'T_Notebook' AND COLUMN_NAME = 'CF_Fecha_eliminacion'")
    assert [fila[0] for fila in columna] == ["YES"]

    filas = dict(_consultar("SELECT CN_Id_tipo_accion, CT_Nombre_tipo_accion FROM T_Tipo_accion"))
    assert filas[19] == "Renombrar Notebook" and filas[20] == "Eliminar Notebook"
    assert (TiposAccion.RENOMBRAR_NOTEBOOK, TiposAccion.ELIMINAR_NOTEBOOK) == (19, 20)
    assert DESCRIPCIONES_TIPOS_ACCION[19] == "Renombrar Notebook" and DESCRIPCIONES_TIPOS_ACCION[20] == "Eliminar Notebook"
    assert {i: filas[i] for i in range(1, 19)} == {i: DESCRIPCIONES_TIPOS_ACCION[i] for i in range(1, 19)}


# --- T2: reglas del nombre al crear (RF-17.81, 17.82, 17.84, 17.85, 17.93) y su bitácora (RF-21.81, RF-21.83) ------------------

def _marca() -> int:
    return int(_consultar("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")[0][0])


def _filas(usuario, desde: int) -> list:
    """TODAS las filas del usuario posteriores a la marca: `{tipo, texto, expediente, info}` con `info` decodificado."""
    filas = _consultar(
        "SELECT CN_Id_tipo_accion, CT_Texto, CN_Id_expediente, CT_Informacion_adicional FROM T_Bitacora "
        "WHERE CN_Id_usuario = :u AND CN_Id_bitacora > :m ORDER BY CN_Id_bitacora", {"u": usuario.cedula, "m": desde})
    return [{"tipo": t, "texto": x, "expediente": e, "info": json.loads(i) if i else {}} for t, x, e, i in filas]


def _notebooks_de(usuario) -> int:
    return int(_consultar("SELECT COUNT(*) FROM T_Notebook WHERE CN_Id_usuario = :u", {"u": usuario.cedula})[0][0])


@pytest.mark.requisito("RF-17.81")
@pytest.mark.requisito("RF-17.82")
@pytest.mark.requisito("RF-17.84")
@pytest.mark.requisito("RF-17.85")
@pytest.mark.requisito("RF-21.81")
def test_crear_y_renombrar_rechazados(cliente_api, sesion, usuario_gubernamental, iniciar_sesion, registro_de_datos):
    """RF-17.81, 17.82, 17.84, 17.85, 21.81 (parte de crear): cada rechazo responde 400 con su detalle exacto, no crea nada y
    deja UNA fila «Crear Notebook» sin tema, con el resultado de error, su motivo fijo y tipo «validacion», sin el nombre
    pedido (aquí, un nombre de persona inventado). El nombre de un notebook de otro usuario sí se permite."""
    from tests.soporte.datos import ROL_USUARIO_GUBERNAMENTAL, crear_usuario

    persona = "Maria Fernanda Rojas Quesada"
    existente = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} {persona}", registro_de_datos)
    otro = crear_usuario(ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)
    crear_notebook(cliente_api, iniciar_sesion(otro), f"{PREFIJO_DATOS} nombre de otro", registro_de_datos)
    casos = [
        ("   ", "El nombre del notebook no puede estar vacío", "nombre vacío"),
        ("\u200b", "El nombre del notebook no puede estar vacío", "nombre vacío"),
        ("a" * 151, "El nombre no puede superar 150 caracteres.", "nombre demasiado largo"),
        (f"  {PREFIJO_DATOS} {persona.upper()}  ", "Ya tiene un notebook con ese nombre.", "nombre duplicado"),
        (f"{PREFIJO_DATOS} {persona} \U0001f600", "El nombre contiene caracteres no admitidos.",
         "nombre con caracteres no admitidos"),
    ]
    for nombre, detalle, motivo in casos:
        antes_notebooks, marca = _notebooks_de(usuario_gubernamental), _marca()
        respuesta = cliente_api.post("/notebooks", json={"nombre": nombre}, headers=sesion)
        assert respuesta.status_code == 400 and respuesta.json() == {"detail": detalle}, (motivo, respuesta.text)
        assert _notebooks_de(usuario_gubernamental) == antes_notebooks, f"{motivo}: se creó un notebook"
        filas = _filas(usuario_gubernamental, marca)
        assert len(filas) == 1, (motivo, filas)
        fila = filas[0]
        assert fila["tipo"] == CREAR_NOTEBOOK and fila["expediente"] is None
        assert fila["info"]["resultado"] == "error" and fila["info"]["motivo"] == motivo
        assert fila["info"]["tipo_error"] == "validacion"
        assert "Rojas" not in json.dumps(fila, ensure_ascii=False), "el nombre llegó a la bitácora"

    marca = _marca()
    permitido = cliente_api.post("/notebooks", json={"nombre": f"{PREFIJO_DATOS} nombre de otro"}, headers=sesion)
    assert permitido.status_code == 200, permitido.text
    registro_de_datos.registrar_tema(permitido.json()["clave_interna"])
    filas = _filas(usuario_gubernamental, marca)
    assert [f["tipo"] for f in filas] == [CREAR_NOTEBOOK] and filas[0]["info"]["resultado"] == "exitoso"
    assert existente["id"] != permitido.json()["id"]


@pytest.mark.requisito("RF-17.93")
def test_nombre_no_latino_y_latino_con_tildes(cliente_api, sesion, registro_de_datos):
    """RF-17.93: 150 caracteres fuera del juego latino dan 400 (nunca 500) y no crean nada; 150 latinos con tildes se aceptan y
    se guardan idénticos."""
    no_latino = "\u6f22\u5b57" * 75
    respuesta = cliente_api.post("/notebooks", json={"nombre": no_latino}, headers=sesion)
    assert respuesta.status_code == 400 and respuesta.json() == {"detail": "El nombre contiene caracteres no admitidos."}

    latino = ("\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1" * 25)[:150]
    creado = cliente_api.post("/notebooks", json={"nombre": latino}, headers=sesion)
    assert creado.status_code == 200, creado.text
    registro_de_datos.registrar_tema(creado.json()["clave_interna"])
    assert creado.json()["nombre"] == latino
    guardado = _consultar("SELECT CT_Nombre FROM T_Notebook WHERE CN_Id_notebook = :i", {"i": creado.json()["id"]})
    assert guardado[0][0] == latino


@pytest.mark.requisito("RF-21.81")
@pytest.mark.requisito("RF-21.83")
def test_crear_rechazado_con_bitacora_que_falla(cliente_api, sesion, monkeypatch):
    """RF-21.83: si la bitácora falla al registrar el rechazo, la respuesta sigue siendo el mismo 400."""
    from app.services.bitacora.notebooks_audit_service import notebooks_audit_service

    async def _falla(*args, **kwargs):
        raise Exception("falla simulada de la bitácora")

    monkeypatch.setattr(notebooks_audit_service.bitacora_service, "registrar", _falla)
    respuesta = cliente_api.post("/notebooks", json={"nombre": "  "}, headers=sesion)
    assert respuesta.status_code == 400 and respuesta.json() == {"detail": "El nombre del notebook no puede estar vacío"}


# --- T3: renombrar y eliminar (RF-17.80, 17.83, 17.84, 17.87, 17.90, RNF-07.80, RNF-07.81, RF-21.81-21.83) ------------------------

RENOMBRAR_NOTEBOOK, ELIMINAR_NOTEBOOK = 19, 20
IDS_NO_CANONICOS = ["abc", "05", "+5", "9" * 30, "0", "-1", "5.0"]


def _fila_de_notebook(id_notebook: int) -> tuple:
    return _consultar("SELECT CT_Nombre, CF_Fecha_eliminacion FROM T_Notebook WHERE CN_Id_notebook = :i", {"i": id_notebook})[0]


@pytest.mark.requisito("RF-17.80")
@pytest.mark.requisito("RF-17.83")
def test_renombrar_propio(cliente_api, sesion, usuario_gubernamental, registro_de_datos):
    """RF-17.80, 17.83: PUT cambia el nombre (normalizado), responde el notebook y deja una fila «Renombrar Notebook» con su
    clave; el mismo nombre responde 200 sin fila; solo cambiar las mayúsculas sí cambia."""
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} nombre original", registro_de_datos)
    marca = _marca()
    nuevo = f"{PREFIJO_DATOS} nombre nuevo"
    respuesta = cliente_api.put(f"/notebooks/{notebook['id']}", json={"nombre": f"  {nuevo}  "}, headers=sesion)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == nuevo and cuerpo["id"] == notebook["id"] and cuerpo["clave_interna"] == notebook["clave_interna"]
    assert _fila_de_notebook(notebook["id"]) == (nuevo, None)
    filas = _filas(usuario_gubernamental, marca)
    assert [f["tipo"] for f in filas] == [RENOMBRAR_NOTEBOOK]
    assert filas[0]["info"]["resultado"] == "exitoso" and filas[0]["info"]["tema"] == notebook["clave_interna"]

    marca = _marca()
    igual = cliente_api.put(f"/notebooks/{notebook['id']}", json={"nombre": nuevo}, headers=sesion)
    assert igual.status_code == 200 and igual.json()["nombre"] == nuevo
    assert _filas(usuario_gubernamental, marca) == []

    mayusculas = cliente_api.put(f"/notebooks/{notebook['id']}", json={"nombre": nuevo.upper()}, headers=sesion)
    assert mayusculas.status_code == 200 and _fila_de_notebook(notebook["id"])[0] == nuevo.upper()


@pytest.mark.requisito("RF-17.81")
@pytest.mark.requisito("RF-17.82")
@pytest.mark.requisito("RF-17.84")
@pytest.mark.requisito("RF-17.93")
@pytest.mark.requisito("RF-21.81")
def test_renombrar_rechazado(cliente_api, sesion, usuario_gubernamental, iniciar_sesion, registro_de_datos):
    """RF-17.81, 17.82, 17.84, 17.93, 21.81 (parte de renombrar): cada rechazo es 400 con su detalle exacto, no cambia el nombre y
    deja UNA fila «Renombrar Notebook» con su clave, el motivo fijo y «validacion», sin nombres (persona inventada). El nombre de
    un notebook eliminado propio y el de uno de otro usuario sí se permiten."""
    from tests.soporte.datos import ROL_USUARIO_GUBERNAMENTAL, crear_usuario

    persona = "Maria Fernanda Rojas Quesada"
    crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} {persona}", registro_de_datos)
    objetivo = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} segundo", registro_de_datos)
    eliminado = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} del pasado", registro_de_datos)
    assert cliente_api.delete(f"/notebooks/{eliminado['id']}", headers=sesion).status_code == 200
    ajeno = crear_usuario(ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)
    crear_notebook(cliente_api, iniciar_sesion(ajeno), f"{PREFIJO_DATOS} nombre de otro", registro_de_datos)
    casos = [
        ("   ", "El nombre del notebook no puede estar vacío", "nombre vacío"),
        ("a" * 151, "El nombre no puede superar 150 caracteres.", "nombre demasiado largo"),
        (f" {PREFIJO_DATOS} {persona.upper()} ", "Ya tiene un notebook con ese nombre.", "nombre duplicado"),
        (f"{PREFIJO_DATOS} {persona} \U0001f600", "El nombre contiene caracteres no admitidos.", "nombre con caracteres no admitidos"),
    ]
    for nombre, detalle, motivo in casos:
        marca = _marca()
        respuesta = cliente_api.put(f"/notebooks/{objetivo['id']}", json={"nombre": nombre}, headers=sesion)
        assert respuesta.status_code == 400 and respuesta.json() == {"detail": detalle}, (motivo, respuesta.text)
        assert _fila_de_notebook(objetivo["id"])[0] == f"{PREFIJO_DATOS} segundo", f"{motivo}: cambió el nombre"
        filas = _filas(usuario_gubernamental, marca)
        assert len(filas) == 1, (motivo, filas)
        assert filas[0]["tipo"] == RENOMBRAR_NOTEBOOK and filas[0]["info"]["tema"] == objetivo["clave_interna"]
        assert filas[0]["info"]["resultado"] == "error" and filas[0]["info"]["motivo"] == motivo
        assert filas[0]["info"]["tipo_error"] == "validacion"
        assert "Rojas" not in json.dumps(filas[0], ensure_ascii=False)
    for permitido in (f"{PREFIJO_DATOS} del pasado", f"{PREFIJO_DATOS} nombre de otro"):
        assert cliente_api.put(f"/notebooks/{objetivo['id']}", json={"nombre": permitido}, headers=sesion).status_code == 200


@pytest.mark.requisito("RF-17.87")
@pytest.mark.requisito("RF-21.82")
def test_eliminar_propio_conserva_todo(cliente_api, sesion, usuario_gubernamental, registro_de_datos):
    """RF-17.87: DELETE marca la fecha de eliminación y conserva la fila (nombre, dueño); no se borra nada (RN-01); deja su fila
    «Eliminar Notebook»; el notebook sale de la lista y un segundo DELETE es el 404 uniforme."""
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} para eliminar", registro_de_datos)
    marca = _marca()
    respuesta = cliente_api.delete(f"/notebooks/{notebook['id']}", headers=sesion)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["id"] == notebook["id"] and respuesta.json()["mensaje"]
    nombre, fecha = _fila_de_notebook(notebook["id"])
    assert nombre == f"{PREFIJO_DATOS} para eliminar" and fecha is not None
    dueno = _consultar("SELECT CN_Id_usuario FROM T_Notebook WHERE CN_Id_notebook = :i", {"i": notebook["id"]})[0][0]
    assert dueno == usuario_gubernamental.cedula
    filas = _filas(usuario_gubernamental, marca)
    assert [f["tipo"] for f in filas] == [ELIMINAR_NOTEBOOK] and filas[0]["info"]["resultado"] == "exitoso"
    assert filas[0]["info"]["tema"] == notebook["clave_interna"]
    assert notebook["id"] not in [n["id"] for n in cliente_api.get("/notebooks", headers=sesion).json()]
    segundo = cliente_api.delete(f"/notebooks/{notebook['id']}", headers=sesion)
    assert segundo.status_code == 404 and segundo.json() == {"detail": "Notebook no encontrado"}


@pytest.mark.requisito("RNF-07.80")
@pytest.mark.requisito("RNF-07.81")
@pytest.mark.requisito("RF-21.82")
def test_no_disponible_404_uniforme(cliente_api, sesion, usuario_gubernamental, iniciar_sesion, administrador, registro_de_datos):
    """RNF-07.80, 07.81, RF-21.82: PUT y DELETE sobre un notebook ajeno, inexistente, eliminado o con un id no canónico dan el mismo
    404 (nunca 422), sin tocar nada y con UNA fila de intento «notebook no disponible» (solo el motivo; el nombre enviado, que
    además es inválido, no se valida antes). El Administrador recibe 403."""
    from tests.soporte.datos import ROL_USUARIO_GUBERNAMENTAL, crear_usuario

    ajeno_usuario = crear_usuario(ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)
    ajeno = crear_notebook(cliente_api, iniciar_sesion(ajeno_usuario), f"{PREFIJO_DATOS} de otro", registro_de_datos)
    eliminado = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} eliminado", registro_de_datos)
    assert cliente_api.delete(f"/notebooks/{eliminado['id']}", headers=sesion).status_code == 200
    inexistente = int(_consultar("SELECT COALESCE(MAX(CN_Id_notebook), 0) + 1000000 FROM T_Notebook")[0][0])
    ids = [str(ajeno["id"]), str(inexistente), str(eliminado["id"])] + IDS_NO_CANONICOS
    for texto_id in ids:
        for metodo, tipo in (("put", RENOMBRAR_NOTEBOOK), ("delete", ELIMINAR_NOTEBOOK)):
            marca = _marca()
            argumentos = {"json": {"nombre": "   "}} if metodo == "put" else {}
            respuesta = getattr(cliente_api, metodo)(f"/notebooks/{texto_id}", headers=sesion, **argumentos)
            assert respuesta.status_code == 404 and respuesta.json() == {"detail": "Notebook no encontrado"}, (metodo, texto_id, respuesta.text)
            filas = _filas(usuario_gubernamental, marca)
            assert len(filas) == 1 and filas[0]["tipo"] == tipo, (metodo, texto_id, filas)
            assert filas[0]["info"]["error"] == "intento fallido" and filas[0]["info"]["motivo"] == "notebook no disponible"
            assert filas[0]["info"]["tipo_error"] == "acceso" and filas[0]["expediente"] is None
            assert "tema" not in filas[0]["info"] and "de otro" not in json.dumps(filas[0], ensure_ascii=False)
    assert _fila_de_notebook(ajeno["id"]) == (f"{PREFIJO_DATOS} de otro", None)
    cabeceras_admin = iniciar_sesion(administrador)
    assert cliente_api.put(f"/notebooks/{ajeno['id']}", json={"nombre": "x"}, headers=cabeceras_admin).status_code == 403
    assert cliente_api.delete(f"/notebooks/{ajeno['id']}", headers=cabeceras_admin).status_code == 403


@pytest.mark.requisito("RF-17.90")
@pytest.mark.requisito("RF-21.81")
@pytest.mark.requisito("RF-21.82")
def test_error_inesperado_renombrar_y_eliminar(cliente_api, sesion, usuario_gubernamental, registro_de_datos, monkeypatch):
    """RF-17.90: si el repositorio falla, PUT y DELETE dan 500 genérico (sin el texto del error), no cambian nada y dejan su fila
    «error inesperado» / «interno»."""
    from app.repositories.notebook_repository import NotebookRepository

    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} frágil", registro_de_datos)

    def _falla(*args, **kwargs):
        raise Exception("detalle interno secreto C:/ruta")

    monkeypatch.setattr(NotebookRepository, "renombrar", _falla)
    monkeypatch.setattr(NotebookRepository, "marcar_eliminado", _falla)
    for metodo, tipo in (("put", RENOMBRAR_NOTEBOOK), ("delete", ELIMINAR_NOTEBOOK)):
        marca = _marca()
        argumentos = {"json": {"nombre": f"{PREFIJO_DATOS} otro"}} if metodo == "put" else {}
        respuesta = getattr(cliente_api, metodo)(f"/notebooks/{notebook['id']}", headers=sesion, **argumentos)
        assert respuesta.status_code == 500 and respuesta.json() == {"detail": "Error interno del servidor"}, respuesta.text
        filas = _filas(usuario_gubernamental, marca)
        assert len(filas) == 1 and filas[0]["tipo"] == tipo and filas[0]["info"]["tema"] == notebook["clave_interna"]
        assert filas[0]["info"]["resultado"] == "error" and filas[0]["info"]["motivo"] == "error inesperado"
        assert filas[0]["info"]["tipo_error"] == "interno" and "secreto" not in json.dumps(filas[0])
    assert _fila_de_notebook(notebook["id"]) == (f"{PREFIJO_DATOS} frágil", None)


@pytest.mark.requisito("RF-17.90")
@pytest.mark.requisito("RNF-07.24")
def test_error_inesperado_no_registra_texto_libre_de_la_url(cliente_api, sesion, usuario_gubernamental, monkeypatch):
    """RF-17.90, RNF-07.24: si el servicio falla antes de validar el id, la fila «error inesperado» no lleva el texto crudo de la
    URL (ni como tema ni en el texto); con un id canónico sí lleva su clave `NB-<id>`."""
    from app.routes.notebooks import notebook_service

    def _falla(*args, **kwargs):
        raise Exception("falla simulada")

    async def _falla_async(*args, **kwargs):
        _falla()

    monkeypatch.setattr(notebook_service, "renombrar_notebook", _falla_async)
    monkeypatch.setattr(notebook_service, "eliminar_notebook", _falla_async)
    libre = "Maria-Rojas-Quesada"
    for metodo, tipo in (("put", RENOMBRAR_NOTEBOOK), ("delete", ELIMINAR_NOTEBOOK)):
        argumentos = {"json": {"nombre": f"{PREFIJO_DATOS} x"}} if metodo == "put" else {}
        for texto_id, clave in ((libre, None), ("7", "NB-7")):
            marca = _marca()
            respuesta = getattr(cliente_api, metodo)(f"/notebooks/{texto_id}", headers=sesion, **argumentos)
            assert respuesta.status_code == 500, respuesta.text
            filas = _filas(usuario_gubernamental, marca)
            assert len(filas) == 1 and filas[0]["tipo"] == tipo, (metodo, texto_id, filas)
            assert filas[0]["info"]["motivo"] == "error inesperado" and filas[0]["expediente"] is None
            assert filas[0]["info"].get("tema") == clave, (metodo, texto_id, filas[0])
            assert "Maria" not in json.dumps(filas[0], ensure_ascii=False), (metodo, "el texto de la URL llegó a la bitácora")


@pytest.mark.requisito("RF-21.81")
@pytest.mark.requisito("RF-21.82")
@pytest.mark.requisito("RF-21.83")
def test_bitacora_por_accion(cliente_api, sesion, usuario_gubernamental, registro_de_datos, monkeypatch):
    """RF-21.81-21.83, RNF-07.24: una acción = una fila, con la clave y sin ningún nombre (persona inventada, antes y después);
    si la bitácora falla, las respuestas son las mismas y el cambio se hace igual."""
    from app.services.bitacora.notebooks_audit_service import notebooks_audit_service

    antes, despues = f"{PREFIJO_DATOS} Carlos Mora Vargas", f"{PREFIJO_DATOS} Ana Solis Rojas"
    notebook = crear_notebook(cliente_api, sesion, antes, registro_de_datos)
    marca = _marca()
    assert cliente_api.put(f"/notebooks/{notebook['id']}", json={"nombre": despues}, headers=sesion).status_code == 200
    assert cliente_api.delete(f"/notebooks/{notebook['id']}", headers=sesion).status_code == 200
    filas = _filas(usuario_gubernamental, marca)
    assert [f["tipo"] for f in filas] == [RENOMBRAR_NOTEBOOK, ELIMINAR_NOTEBOOK]
    volcado = json.dumps(filas, ensure_ascii=False)
    assert all(nombre not in volcado for nombre in ("Carlos", "Mora", "Ana", "Solis"))

    async def _falla(*args, **kwargs):
        raise Exception("falla simulada de la bitácora")

    monkeypatch.setattr(notebooks_audit_service.bitacora_service, "registrar", _falla)
    otro = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} con bitácora caída", registro_de_datos)
    assert cliente_api.put(f"/notebooks/{otro['id']}", json={"nombre": f"{PREFIJO_DATOS} renombrado"}, headers=sesion).status_code == 200
    assert _fila_de_notebook(otro["id"])[0] == f"{PREFIJO_DATOS} renombrado"
    assert cliente_api.put("/notebooks/abc", json={"nombre": "x"}, headers=sesion).status_code == 404
    assert cliente_api.delete(f"/notebooks/{otro['id']}", headers=sesion).status_code == 200
    assert _fila_de_notebook(otro["id"])[1] is not None


# --- T4: el eliminado no está disponible en ninguna vía y todo lo suyo se conserva (RF-17.88, RF-17.89, RN-01.80) ---------------

def _puntos_de(clave: str) -> int:
    from tests.soporte.flujos import contar_puntos

    return contar_puntos(clave)


@pytest.mark.requisito("RF-17.88")
@pytest.mark.requisito("RF-17.89")
@pytest.mark.requisito("RN-01.80")
def test_eliminado_no_disponible_en_toda_via(cliente_api, ajeno, ollama_simulado, usuario_gubernamental):
    """RF-17.88: tras eliminarlo, el notebook (con documento Procesado y conversación) no aparece en la lista y su lista de
    documentos, su original, la descarga por ruta, su chat (por `notebook_id` y por tema) y su conversación (ver, restaurar,
    eliminar) dan el mismo 404 que uno inexistente, sin entregar su contenido; los intentos dejan su fila. RN-01.80: la fila, el
    documento, el archivo y los puntos siguen."""
    from app.services.RAG.session_store import conversation_store
    from tests.integracion.conftest import RESPUESTA_SIMULADA, _consultar_chat, _pregunta_sobre, _todo_lo_que_recibio_el_modelo

    ollama_simulado.responder(RESPUESTA_SIMULADA)
    cabeceras, notebook = ajeno.cabeceras_dueno, ajeno.notebook
    id_nb, clave = notebook["id"], notebook["clave_interna"]
    sesion_nb = f"session_notebook_{id_nb}_{usuario_gubernamental.correo}_{PREFIJO_DATOS}hilo"
    conversation_store.get_session_history(sesion_nb).add_user_message(f"{PREFIJO_DATOS} pregunta en el notebook")
    try:
        ruta = f"uploads/{clave}/{ajeno.documento.nombre}"
        pregunta = _pregunta_sobre(ajeno.documento)
        assert cliente_api.get(f"/rag/conversations/{sesion_nb}", headers=cabeceras).status_code == 200, "control: conversación"
        assert cliente_api.get("/archivos/download", params={"ruta_archivo": ruta}, headers=cabeceras).status_code == 200
        puntos = _puntos_de(clave)
        assert puntos > 0

        assert cliente_api.delete(f"/notebooks/{id_nb}", headers=cabeceras).status_code == 200
        marca = _marca()
        ollama_simulado.preguntas.clear()
        id_inexistente = ajeno.id_inexistente
        sesion_inexistente = f"session_notebook_{id_inexistente}_{usuario_gubernamental.correo}_{PREFIJO_DATOS}hilo"

        def _vias(n, sesion):
            return {
                "documentos": cliente_api.get(f"/notebooks/{n}/documentos", headers=cabeceras),
                "original": cliente_api.get(f"/notebooks/{n}/documentos/{ajeno.id_documento}/archivo", headers=cabeceras),
                "chat": _consultar_chat(cliente_api, cabeceras, pregunta, notebook_id=str(n)),
                "ver": cliente_api.get(f"/rag/conversations/{sesion}", headers=cabeceras),
                "restaurar": cliente_api.post(f"/rag/conversations/{sesion}/restore", headers=cabeceras),
                "eliminar": cliente_api.delete(f"/rag/conversations/{sesion}", headers=cabeceras),
            }

        eliminado, inexistente = _vias(id_nb, sesion_nb), _vias(id_inexistente, sesion_inexistente)
        for via, respuesta in eliminado.items():
            assert respuesta.status_code == 404, (via, respuesta.status_code, respuesta.text)
            esperado = inexistente[via].text.replace(str(id_inexistente), "{n}").replace(sesion_inexistente, "{s}")
            assert respuesta.text.replace(str(id_nb), "{n}").replace(sesion_nb, "{s}") == esperado, via
            assert ajeno.documento.frase not in respuesta.text
        assert not ollama_simulado.preguntas, "el modelo recibió algo del chat del notebook eliminado"

        assert id_nb not in [n["id"] for n in cliente_api.get("/notebooks", headers=cabeceras).json()]
        assert cliente_api.get("/archivos/download", params={"ruta_archivo": ruta}, headers=cabeceras).status_code in (403, 404)
        # Por tema (clave): chat general sin el contenido del notebook eliminado.
        assert _consultar_chat(cliente_api, cabeceras, pregunta, expediente_number=clave).status_code == 200
        recibido = _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta)
        assert ajeno.documento.frase not in recibido and ajeno.documento.nombre not in recibido

        filas = [f for f in _filas(usuario_gubernamental, marca) if f["info"].get("error") == "intento fallido"]
        assert len(filas) >= 6 and {f["info"]["motivo"] for f in filas} <= {"notebook no disponible", "conversación no disponible"}

        # RN-01.80: todo se conserva.
        assert _fila_de_notebook(id_nb)[1] is not None
        assert _puntos_de(clave) == puntos
        assert _consultar("SELECT COUNT(*) FROM T_Documento WHERE CN_Id_documento = :d", {"d": ajeno.id_documento})[0][0] == 1
    finally:
        conversation_store._store.pop(sesion_nb, None)
        conversation_store._metadata.pop(sesion_nb, None)


def _forma(respuesta, *sustituciones) -> tuple:
    """Código y cuerpo de la respuesta, con los tiempos fuera y cada `(texto, marcador)` sustituido (clave o id pedidos)."""
    cuerpo = respuesta.text
    for texto, marcador in sustituciones:
        cuerpo = cuerpo.replace(texto, marcador)
    try:
        datos = json.loads(cuerpo)
    except ValueError:
        return respuesta.status_code, cuerpo
    if isinstance(datos, dict):
        datos = {k: v for k, v in datos.items() if not k.startswith("tiempo_")}
    return respuesta.status_code, datos


@pytest.mark.requisito("RF-17.88")
def test_eliminado_no_disponible_en_las_demas_vias(cliente_api, ajeno, ollama_simulado):
    """RF-17.88: con el notebook eliminado, quitar un documento, cargar a su clave, temas similares (por tema y por texto), el
    resumen y el chat (general y por su clave) lo tratan igual que a una clave o un id inexistente y no entregan nada suyo."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    cabeceras, notebook, documento = ajeno.cabeceras_dueno, ajeno.notebook, ajeno.documento
    id_nb, clave, inexistente = notebook["id"], notebook["clave_interna"], f"NB-{ajeno.id_inexistente}"
    pregunta = _pregunta_sobre(documento)

    def _buscar(**cuerpo):
        return cliente_api.post("/similarity/search", headers=cabeceras, json={"limite": 30, "umbral_similitud": 0.1, **cuerpo})

    def _por_texto():
        return _buscar(modo_busqueda="descripcion", texto_consulta=documento.frase)

    control = _por_texto()  # el dueño sí encuentra su documento mientras el notebook existe
    assert control.status_code == 200 and documento.nombre in str(control.json()["casos_similares"]), "control: búsqueda"

    assert cliente_api.delete(f"/notebooks/{id_nb}", headers=cabeceras).status_code == 200
    ollama_simulado.preguntas.clear()
    subsidiarios = [(clave, "<tema>"), (str(id_nb), "{n}")]
    inexistentes = [(inexistente, "<tema>"), (str(ajeno.id_inexistente), "{n}")]

    # Quitar un documento: el mismo 404 que un notebook inexistente, y el documento sigue.
    quitar = cliente_api.delete(f"/notebooks/{id_nb}/documentos/{ajeno.id_documento}", headers=cabeceras)
    quitar_inexistente = cliente_api.delete(f"/notebooks/{ajeno.id_inexistente}/documentos/{ajeno.id_documento}", headers=cabeceras)
    assert quitar.status_code == 404, quitar.text
    assert _forma(quitar, *subsidiarios) == _forma(quitar_inexistente, *inexistentes)
    assert _consultar("SELECT COUNT(*) FROM T_Documento WHERE CN_Id_documento = :d", {"d": ajeno.id_documento})[0][0] == 1

    # Carga a su clave: igual que a una clave inexistente, y no deja ningún documento nuevo.
    nuevo, otro_nuevo = documento_de_prueba(), documento_de_prueba()
    cargas_antes = _consultar("SELECT COUNT(*) FROM T_Documento")[0][0]
    carga = cargar(cliente_api, cabeceras, clave, [(nuevo.nombre, nuevo.contenido)])
    carga_inexistente = cargar(cliente_api, cabeceras, inexistente, [(otro_nuevo.nombre, otro_nuevo.contenido)])
    assert carga.status_code == 404, carga.text
    assert _forma(carga, *subsidiarios, (nuevo.nombre, "<a>")) == _forma(carga_inexistente, *inexistentes, (otro_nuevo.nombre, "<a>"))
    assert _consultar("SELECT COUNT(*) FROM T_Documento")[0][0] == cargas_antes

    # Temas similares por tema (su clave) y por texto.
    por_tema = _buscar(modo_busqueda="expediente", numero_expediente=clave)
    por_tema_inexistente = _buscar(modo_busqueda="expediente", numero_expediente=inexistente)
    assert _forma(por_tema, *subsidiarios) == _forma(por_tema_inexistente, *inexistentes)
    assert documento.nombre not in por_tema.text and documento.frase not in por_tema.text
    por_texto = _por_texto()
    assert por_texto.status_code == 200
    assert documento.nombre not in str(por_texto.json()["casos_similares"]), "la búsqueda por texto entregó el eliminado"

    # Resumen.
    resumen = cliente_api.post("/similarity/generate-summary", headers=cabeceras, json={"numero_expediente": clave})
    resumen_inexistente = cliente_api.post("/similarity/generate-summary", headers=cabeceras, json={"numero_expediente": inexistente})
    assert _forma(resumen, *subsidiarios) == _forma(resumen_inexistente, *inexistentes)
    assert documento.frase not in resumen.text and documento.nombre not in resumen.text

    # Chat general (sin tema) y por su clave, comparado con una clave inexistente.
    assert _consultar_chat(cliente_api, cabeceras, pregunta).status_code == 200
    por_clave = _consultar_chat(cliente_api, cabeceras, pregunta, expediente_number=clave)
    por_clave_inexistente = _consultar_chat(cliente_api, cabeceras, pregunta, expediente_number=inexistente)
    assert por_clave.status_code == por_clave_inexistente.status_code
    recibido = _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta)
    assert documento.frase not in recibido and documento.nombre not in recibido, "el modelo recibió algo del eliminado"
    assert documento.frase not in por_clave.text and documento.nombre not in por_clave.text


@pytest.mark.requisito("RN-01.80")
@pytest.mark.requisito("RF-17.87")
def test_eliminar_con_documento_pendiente(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    """RN-01.80, RF-17.87: eliminar un notebook con un documento Pendiente (aún sin terminar su procesamiento) conserva el
    documento, su archivo, sus fragmentos en Qdrant y su unión con el tema; no borra nada y el notebook deja de estar disponible."""
    from app.db.database import engine
    from app.services.documentos.file_management_service import file_management_service
    from tests.integracion.conftest import _documento_procesado_en_el_notebook
    from tests.soporte.flujos import exigir_estado

    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} con pendiente", registro_de_datos)
    clave = notebook["clave_interna"]
    documento, id_documento = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)
    with engine.begin() as conexion:
        conexion.execute(
            text("UPDATE T_Documento SET CN_Id_estado = (SELECT CN_Id_estado FROM T_Estado_procesamiento "
                 "WHERE CT_Nombre_estado = 'Pendiente') WHERE CN_Id_documento = :d"), {"d": id_documento})
    exigir_estado(id_documento, "Pendiente")
    puntos = _puntos_de(clave)
    assert puntos > 0 and file_management_service.obtener_ruta_archivo(clave, documento.nombre) is not None

    assert cliente_api.delete(f"/notebooks/{notebook['id']}", headers=sesion).status_code == 200

    exigir_estado(id_documento, "Pendiente")
    assert _puntos_de(clave) == puntos
    assert file_management_service.obtener_ruta_archivo(clave, documento.nombre) is not None
    uniones = _consultar("SELECT COUNT(*) FROM T_Expediente_Documento WHERE CN_Id_documento = :d", {"d": id_documento})
    assert uniones[0][0] == 1
    assert _fila_de_notebook(notebook["id"])[1] is not None
    assert cliente_api.get(f"/notebooks/{notebook['id']}/documentos", headers=sesion).status_code == 404
