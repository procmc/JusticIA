"""Red de seguridad del detalle de carga en la bitácora completa (spec 004, tarea 9c, bloque F; RF-22.1).

`GET /bitacora/registros` (Administrador) añade a cada registro de carga su `detalle_carga`: el nombre visible del tipo
y los datos con su etiqueta en español, en el orden de la tabla de RF-22.1. Las filas se escriben con los mismos
servicios de auditoría que usa el sistema (una por tipo) y se leen por la API, como lo haría la interfaz.
- RF-22.1: el detalle de cada tipo; la causa clasificada sin el texto de la excepción; nada de lo prohibido (tareas,
  colección, rutas, error crudo, nombre de un archivo rechazado); el resto de la API sin cambios; un fallo de la
  consulta da 500 genérico; el Usuario Gubernamental no entra.

Son regresiones: se escribieron contra la spec y se vieron fallar antes del cambio. Los datos son inventados (usuarios y
temas `PRUEBA`, que la limpieza alcanza) y la hora del detalle es la de Costa Rica (UTC-6).
"""
import asyncio
import json
import logging
from datetime import timedelta

import pytest
from sqlalchemy import text

from tests.soporte.flujos import cargar, documento_de_prueba, tema_heredado

ETIQUETAS_PERMITIDAS = {"Tema", "Fecha y hora", "Archivos aceptados", "Archivos rechazados", "Archivo", "Documento",
                        "Fragmentos", "Causa", "Motivo"}
ERROR_CRUDO = r"Error extrayendo texto: fallo en C:\srv\PRUEBA_secreto\lector.py (connection refused)"


@pytest.fixture
def sesion_admin(iniciar_sesion, administrador):
    return iniciar_sesion(administrador)


@pytest.fixture
def sesion_usuario(iniciar_sesion, usuario_gubernamental):
    return iniciar_sesion(usuario_gubernamental)


# --- Escritura y lectura ---------------------------------------------------------------------------------------------------

def _escribir(escribir) -> int:
    """Ejecuta `escribir(db)` (una corrutina de un servicio de auditoría) y devuelve el identificador de la fila creada."""
    from app.db.database import SessionLocal

    async def _correr():
        with SessionLocal() as db:
            fila = await escribir(db)
            assert fila is not None, "el servicio de auditoría no pudo registrar la fila de prueba"
            return fila.CN_Id_bitacora

    return asyncio.run(_correr())


def _hora_guardada(id_bitacora: int):
    from app.db.database import engine

    with engine.connect() as conexion:
        return conexion.execute(text("SELECT CF_Fecha_hora FROM T_Bitacora WHERE CN_Id_bitacora = :i"),
                                {"i": id_bitacora}).scalar()


def _hora_de_costa_rica(id_bitacora: int) -> str:
    """La hora guardada (UTC) menos seis horas, con el formato del detalle; se calcula aquí a mano y no con el código."""
    return (_hora_guardada(id_bitacora) - timedelta(hours=6)).strftime("%d/%m/%Y %H:%M:%S")


def _listar(cliente_api, cabeceras: dict, cedula: str) -> dict:
    """Los registros del usuario por la bitácora completa, por identificador."""
    respuesta = cliente_api.get("/bitacora/registros", params={"usuario": cedula, "limite": 100}, headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return {item["id"]: item for item in respuesta.json()["items"]}


def _datos(item: dict) -> list:
    return [(d["etiqueta"], d["valor"]) for d in item["detalle_carga"]["datos"]]


def _escribir_una_por_tipo(cedula: str, tema: str, nombre: str) -> dict:
    """Una fila de cada tipo de la tabla de RF-22.1. Devuelve `{tipo visible: id}`."""
    from app.services.bitacora.ingesta_audit_service import ingesta_audit_service as audit

    tarea = "PRUEBA-tarea-1"
    return {
        "Carga iniciada": _escribir(lambda db: audit.registrar_ingesta(
            db, cedula, tema, "2 archivo(s)", f"{tarea},PRUEBA-tarea-2", "iniciado",
            archivos_aceptados=2, archivos_rechazados=1)),
        "Inicio del procesamiento": _escribir(lambda db: audit.registrar_ingesta(db, cedula, tema, nombre, tarea, "inicio")),
        "Documento almacenado": _escribir(lambda db: audit.registrar_almacenamiento_vectorial(
            db, cedula, tema, nombre, 41, 5)),
        "Procesamiento terminado": _escribir(lambda db: audit.registrar_ingesta(
            db, cedula, tema, nombre, tarea, "completado", documento_id=tarea)),
        "Error de procesamiento": _escribir(lambda db: audit.registrar_ingesta(
            db, cedula, tema, nombre, tarea, "error", error_details=ERROR_CRUDO)),
        "Carga rechazada": _escribir(lambda db: audit.registrar_carga_rechazada(db, cedula, "archivo vacío")),
        "Cancelación": _escribir(lambda db: audit.registrar_ingesta(
            db, cedula, "N/A", f"Task {tarea}", tarea, "cancelado")),
        "Error de cancelación": _escribir(lambda db: audit.registrar_ingesta(
            db, cedula, "N/A", f"Task {tarea}", tarea, "error_cancelacion")),
        "Error general de la carga": _escribir(lambda db: audit.registrar_ingesta(
            db, cedula, tema, "Error general", "N/A", "error")),
    }


# --- RF-22.1: el detalle de cada tipo ---------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-22.1")
def test_detalle_de_cada_tipo(cliente_api, sesion_admin, usuario_gubernamental, registro_de_datos):
    """RF-22.1: cada registro de carga trae su `detalle_carga` con el nombre visible del tipo y sus datos en el orden de
    la tabla, con la hora de Costa Rica (UTC-6), sin los valores de relleno y sin datos técnicos."""
    cedula, tema, nombre = usuario_gubernamental.cedula, tema_heredado(registro_de_datos), documento_de_prueba().nombre
    ids = _escribir_una_por_tipo(cedula, tema, nombre)

    items = _listar(cliente_api, sesion_admin, cedula)

    esperado = {
        "Carga iniciada": [("Tema", tema), ("Fecha y hora", _hora_de_costa_rica(ids["Carga iniciada"])),
                           ("Archivos aceptados", "2"), ("Archivos rechazados", "1")],
        "Inicio del procesamiento": [("Tema", tema), ("Fecha y hora", _hora_de_costa_rica(ids["Inicio del procesamiento"])),
                                     ("Archivo", nombre)],
        "Documento almacenado": [("Tema", tema), ("Fecha y hora", _hora_de_costa_rica(ids["Documento almacenado"])),
                                 ("Archivo", nombre), ("Documento", "41"), ("Fragmentos", "5")],
        "Procesamiento terminado": [("Tema", tema), ("Fecha y hora", _hora_de_costa_rica(ids["Procesamiento terminado"])),
                                    ("Archivo", nombre)],
        "Error de procesamiento": [("Tema", tema), ("Fecha y hora", _hora_de_costa_rica(ids["Error de procesamiento"])),
                                   ("Archivo", nombre), ("Causa", "servicio de procesamiento no disponible")],
        "Carga rechazada": [("Fecha y hora", _hora_de_costa_rica(ids["Carga rechazada"])), ("Motivo", "archivo vacío")],
        "Cancelación": [("Fecha y hora", _hora_de_costa_rica(ids["Cancelación"]))],
        "Error de cancelación": [("Fecha y hora", _hora_de_costa_rica(ids["Error de cancelación"]))],
        "Error general de la carga": [("Tema", tema),
                                      ("Fecha y hora", _hora_de_costa_rica(ids["Error general de la carga"])),
                                      ("Causa", "error interno")],
    }
    nombre_visible = {"Error general de la carga": "Error de procesamiento"}
    for clave, datos in esperado.items():
        item = items[ids[clave]]
        assert item["detalle_carga"]["tipo"] == nombre_visible.get(clave, clave), clave
        assert _datos(item) == datos, clave
        assert set(item["detalle_carga"]) == {"tipo", "datos"}, clave


# --- RF-22.1: la causa clasificada y lo prohibido ---------------------------------------------------------------------------

@pytest.mark.requisito("RF-22.1")
def test_causa_sin_texto_de_excepcion(cliente_api, sesion_admin, usuario_gubernamental, registro_de_datos):
    """RF-22.1: la causa del error es siempre una de la lista cerrada y el texto de la excepción guardado (con su ruta)
    no aparece en el detalle, aunque la fila lo conserve en `informacionAdicional` (lo que ya se entregaba)."""
    from app.services.bitacora.ingesta_audit_service import ingesta_audit_service as audit

    cedula, tema = usuario_gubernamental.cedula, tema_heredado(registro_de_datos)
    nombre = documento_de_prueba().nombre
    crudos = {
        "formato o tamaño no permitido": "Formato no permitido: .exe en /srv/PRUEBA_ruta",
        "no se pudo extraer el texto": ERROR_CRUDO.replace("(connection refused)", "(archivo dañado)"),
        "servicio de procesamiento no disponible": ERROR_CRUDO,
        "no se pudo guardar para la búsqueda": r"Fallo de Qdrant en C:\srv\PRUEBA_secreto",
        "error interno": r"KeyError: 'x' en /srv/PRUEBA_secreto/otro.py",
    }
    ids = {causa: _escribir(lambda db, c=crudo: audit.registrar_ingesta(
        db, cedula, tema, nombre, "PRUEBA-tarea-1", "error", error_details=c)) for causa, crudo in crudos.items()}

    items = _listar(cliente_api, sesion_admin, cedula)

    for causa, id_bitacora in ids.items():
        detalle = json.dumps(items[id_bitacora]["detalle_carga"], ensure_ascii=False)
        assert ("Causa", causa) in _datos(items[id_bitacora])
        for rastro in ("PRUEBA_secreto", "PRUEBA_ruta", "/srv", "C:\\\\", "lector.py", "connection", "KeyError"):
            assert rastro not in detalle, (causa, rastro)


@pytest.mark.requisito("RF-22.1")
@pytest.mark.requisito("RNF-07.24")
def test_sin_datos_prohibidos(cliente_api, sesion_admin, sesion_usuario, usuario_gubernamental, registro_de_datos,
                              carpeta_archivos, encolado_interceptado):
    """RF-22.1: tras una carga mixta real (un válido, uno vacío y uno de nombre no válido) más las filas de cada tipo, el
    detalle solo usa las etiquetas permitidas y no contiene tareas, colección, número de vectores, fase, rutas, el error
    crudo, contraseñas ni el nombre del archivo rechazado; el rechazo no lleva tema ni archivo."""
    cedula, tema = usuario_gubernamental.cedula, tema_heredado(registro_de_datos)
    valido, vacio, no_valido = documento_de_prueba(), "PRUEBA_vacio.txt", "../PRUEBA_nombre_secreto.txt"
    respuesta = cargar(cliente_api, sesion_usuario, tema,
                       [(valido.nombre, valido.contenido), (vacio, b""), (no_valido, b"PRUEBA contenido")])
    assert respuesta.status_code == 200
    _escribir_una_por_tipo(cedula, tema, valido.nombre)

    items = _listar(cliente_api, sesion_admin, cedula)

    con_detalle = [i for i in items.values() if "detalle_carga" in i]
    assert len(con_detalle) == 1 + 2 + 9  # la carga iniciada y los 2 rechazos reales, más las 9 escritas
    for item in con_detalle:
        detalle = json.dumps(item["detalle_carga"], ensure_ascii=False)
        assert {etiqueta for etiqueta, _ in _datos(item)} <= ETIQUETAS_PERMITIDAS
        for prohibido in ("PRUEBA-tarea", "collection", "colección", "documentos", "num_vectores", "fase", "PRUEBA_nombre_secreto",
                          "PRUEBA_secreto", "PRUEBA_vacio", "/srv", "C:\\\\", "password", "token", "contraseña", "Expediente"):
            assert prohibido not in detalle, (item["id"], prohibido)
    rechazos_reales = [i for i in con_detalle if i["detalle_carga"]["tipo"] == "Carga rechazada"
                       and i["texto"] in ("Carga rechazada: archivo vacío", "Carga rechazada: nombre de archivo no válido")]
    assert len(rechazos_reales) == 3  # los 2 reales y el escrito con «archivo vacío»
    for rechazo in rechazos_reales:
        assert [e for e, _ in _datos(rechazo)] == ["Fecha y hora", "Motivo"]
    iniciada_real = next(i for i in con_detalle if i["detalle_carga"]["tipo"] == "Carga iniciada"
                         and ("Archivos aceptados", "1") in _datos(i))
    assert ("Archivos rechazados", "2") in _datos(iniciada_real) and ("Tema", tema) in _datos(iniciada_real)


# --- RF-22.1: el resto de la API no cambia ---------------------------------------------------------------------------------

@pytest.mark.requisito("RF-22.1")
def test_otros_consumidores_sin_cambios(cliente_api, sesion_admin, sesion_usuario, usuario_gubernamental, registro_de_datos):
    """RF-22.1 (contrato aditivo): sin su `detalle_carga`, cada registro de la bitácora completa es igual al que arma
    `_expandir_registro` (de ahí sale la exportación); un registro que no es de carga no trae el detalle; y el historial
    propio, la bitácora de un tema y el servicio compartido no lo traen."""
    from app.db.database import SessionLocal
    from app.constants.tipos_accion import TiposAccion
    from app.services.bitacora.bitacora_service import bitacora_service
    from app.services.bitacora.bitacora_stats_service import bitacora_stats_service

    cedula, tema = usuario_gubernamental.cedula, tema_heredado(registro_de_datos)
    ids = _escribir_una_por_tipo(cedula, tema, documento_de_prueba().nombre)
    id_descarga = _escribir(lambda db: bitacora_service.registrar(
        db, cedula, TiposAccion.DESCARGAR_ARCHIVO, "PRUEBA descarga rechazada", info_adicional={"motivo": "sin permiso"}))

    items = _listar(cliente_api, sesion_admin, cedula)

    assert "detalle_carga" not in items[id_descarga]
    with SessionLocal() as db:
        previos = {i["id"]: i for i in bitacora_stats_service.obtener_con_filtros(db, usuario_id=cedula, limite=100)["items"]}
    assert not any("detalle_carga" in i for i in previos.values())
    assert set(previos) == set(items) >= set(ids.values()) | {id_descarga}  # y el inicio de sesión de la prueba
    for id_bitacora, item in items.items():
        sin_detalle = {k: v for k, v in item.items() if k != "detalle_carga"}
        assert sin_detalle == previos[id_bitacora], id_bitacora
    # Control positivo: sí lo traen los registros de carga de la bitácora completa.
    assert all("detalle_carga" in items[i] for i in ids.values())
    # Historial propio y bitácora de un tema: lo que respondan, no lleva el detalle (su forma actual no se toca; hoy ambas
    # rutas declaran una lista y devuelven un diccionario, y el cliente que no relanza errores recibe el 500).
    from fastapi.testclient import TestClient

    cliente_sin_relanzar = TestClient(cliente_api.app, raise_server_exceptions=False)
    for ruta in ("/bitacora/mi-historial", f"/bitacora/expediente/{tema}"):
        respuesta = cliente_sin_relanzar.get(ruta, headers=sesion_usuario)
        assert "detalle_carga" not in respuesta.text, ruta


# --- RF-22.1: fallo de la consulta y roles ----------------------------------------------------------------------------------

@pytest.mark.requisito("RF-22.1")
def test_consulta_que_falla_da_500_generico(cliente_api, sesion_admin, monkeypatch, caplog):
    """RF-22.1: si la consulta de la bitácora completa falla, responde 500 con «Error interno del servidor», sin el texto
    de la excepción ni su ruta (que va al registro del servidor)."""
    from app.repositories.bitacora_repository import BitacoraRepository

    secreto = "/srv/PRUEBA_secreto/consulta.py"

    def _falla(self, *args, **kwargs):
        raise RuntimeError(f"no se pudo consultar en {secreto}")

    monkeypatch.setattr(BitacoraRepository, "obtener_con_filtros", _falla)
    with caplog.at_level(logging.ERROR):
        respuesta = cliente_api.get("/bitacora/registros", params={"limite": 5}, headers=sesion_admin)

    assert (respuesta.status_code, respuesta.json()) == (500, {"detail": "Error interno del servidor"})
    assert secreto not in respuesta.text and "RuntimeError" not in respuesta.text
    assert any(r.name.startswith("app.") and r.levelno >= logging.ERROR and r.exc_info for r in caplog.records)


@pytest.mark.requisito("RF-22.1")
@pytest.mark.requisito("RF-02.3")
def test_usuario_gubernamental_da_403(cliente_api, sesion_usuario, usuario_gubernamental, registro_de_datos):
    """RF-22.1 y RF-02.3: la bitácora completa y su detalle son solo del Administrador; el Usuario Gubernamental recibe 403
    y nada de lo registrado."""
    _escribir_una_por_tipo(usuario_gubernamental.cedula, tema_heredado(registro_de_datos), documento_de_prueba().nombre)

    respuesta = cliente_api.get("/bitacora/registros", params={"usuario": usuario_gubernamental.cedula},
                                headers=sesion_usuario)

    assert respuesta.status_code == 403
    assert "detalle_carga" not in respuesta.text and "items" not in respuesta.json()
