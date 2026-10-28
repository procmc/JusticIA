"""Pruebas de T4 (spec 004a): la carga guarda confinada, sin archivos a medias y sin repetir lo pedido.

Cubren RF-06.20 (un tema que no sirve como nombre de carpeta rechaza la carga completa, 400 «El tema indicado no es
válido», sin escribir ni encolar nada), RF-05.20 (un archivo con nombre no válido se rechaza solo, con el aviso genérico
y sin su nombre, y los demás siguen), RF-05.21 (la carga funciona sea cual sea la ubicación de la carpeta de documentos
y devuelve `uploads/<tema>/<nombre>`; si la escritura falla, ese archivo figura rechazado sin rutas), RF-21.20 (cada
rechazo deja una fila solo con su motivo; si la bitácora falla, la respuesta es la misma), RNF-07.23 (un error inesperado
da un mensaje genérico, también en el listado de archivos de un tema) y RNF-07.24 (ni la respuesta, ni la bitácora, ni el
registro del servidor repiten el tema ni el nombre rechazados).

Todo ocurre en la carpeta temporal desviada (`carpeta_archivos`) y con Celery sustituido por un registro de lo que se
habría encolado: ninguna tarea corre ni se toca el `uploads/` real. Los nombres y temas llevan el prefijo `PRUEBA`.
"""
import json
import logging
import re

import pytest
from sqlalchemy import text

PERSONA = "PRUEBA Juana Inventada Solís"
_PARTES_DE_LA_PERSONA = ("Juana", "Inventada", "Solís")
TEMA = "PRUEBA tema de carga"
CONTENIDO = b"PRUEBA contenido inventado de la carga"
TEMA_CON_FORMATO = "PRUEBA-TEMA-T4-0001"


# --- Apoyo -------------------------------------------------------------------------------------------------------

@pytest.fixture
def sesion(cliente_api, iniciar_sesion, usuario_gubernamental):
    return iniciar_sesion(usuario_gubernamental)


@pytest.fixture
def encoladas(monkeypatch):
    """Sustituye el `.delay()` de la tarea de ingesta por un registro de lo que se habría encolado."""
    from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery

    lista = []

    class _Tarea:
        def __init__(self, numero):
            self.id = f"PRUEBA-tarea-{numero}"

    def _delay(tema, archivo_info, usuario_id):
        lista.append((tema, archivo_info, usuario_id))
        return _Tarea(len(lista))

    monkeypatch.setattr(procesar_archivo_celery, "delay", _delay)
    return lista


def _cargar(cliente_api, cabeceras, tema: str, archivos):
    """Carga como la interfaz: `POST /ingesta/archivos` con el tema y los archivos (nombre, contenido)."""
    partes = [("files", (nombre, contenido, "text/plain")) for nombre, contenido in archivos]
    return cliente_api.post("/ingesta/archivos", data={"CT_Num_expediente": tema}, files=partes, headers=cabeceras)


def _instantanea(raiz) -> list[str]:
    """Todo lo que hay bajo `raiz` (sin seguir enlaces): comprueba que no se creó ni se borró nada."""
    return sorted(str(p.relative_to(raiz)) for p in raiz.rglob("*"))


def _filas(usuario, tipo_accion: int) -> list:
    """Las filas de la bitácora del usuario para ese tipo de acción, en orden: [{texto, info, datos}]."""
    from app.db.database import engine

    with engine.connect() as conexion:
        filas = conexion.execute(
            text("SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_usuario = :u "
                 "AND CN_Id_tipo_accion = :t ORDER BY CN_Id_bitacora"),
            {"u": usuario.cedula, "t": tipo_accion},
        ).fetchall()
    return [{"texto": f[0], "info": f[1] or "", "datos": json.loads(f[1]) if f[1] else {}} for f in filas]


# --- RF-06.20: el tema se valida antes de escribir nada -----------------------------------------------------------

TEMAS_NO_VALIDOS = [
    pytest.param("   ", id="B1-espacios"),
    pytest.param(".", id="B1-punto"),
    pytest.param("..", id="B1-dos-puntos"),
    pytest.param("a/b", id="B2-separador"),
    pytest.param("a\\b", id="B2-contrabarra"),
    pytest.param("../PRUEBA", id="B2-padre-al-inicio"),
    pytest.param("PRUEBA/..", id="B2-padre-al-final"),
    pytest.param("/PRUEBA", id="B3-absoluto-linux"),
    pytest.param("C:\\PRUEBA", id="B3-absoluto-windows"),
    pytest.param("PRUEBA:flujo", id="B3-dos-puntos"),
    pytest.param("PRUEBA\x00x", id="B4-nul"),
    pytest.param("PRUEBA\nx", id="B4-salto-de-linea"),
    # RF-06.53 (spec 006): un espacio final ya no invalida el tema, porque se recorta antes de validar; lo que queda tras el
    # recorte (aquí, un punto final) sí se rechaza.
    pytest.param("PRUEBA . ", id="B5-punto-final-tras-recorte"),
    pytest.param("PRUEBA.", id="B5-punto-final"),
    pytest.param("CON", id="B5-reservado"),
    pytest.param("PRUEBA" + "x" * 55, id="B6-61-caracteres"),
    pytest.param("profiles", id="B7-profiles"),
    pytest.param("PROFILES", id="B7-profiles-mayusculas"),
    pytest.param("pRoFiLeS", id="B7-profiles-mezcla"),
]


@pytest.mark.parametrize("tema", TEMAS_NO_VALIDOS)
def test_tema_no_valido_no_escribe_nada(cliente_api, sesion, carpeta_archivos, encoladas, tema):
    """RF-06.20: 400 «El tema indicado no es válido», carpeta temporal exactamente igual y nada encolado."""
    antes = _instantanea(carpeta_archivos)

    respuesta = _cargar(cliente_api, sesion, tema, [("PRUEBA_a.txt", CONTENIDO), ("PRUEBA_b.txt", CONTENIDO)])

    assert (respuesta.status_code, respuesta.json()) == (400, {"detail": "El tema indicado no es válido"})
    assert _instantanea(carpeta_archivos) == antes
    assert encoladas == []


# --- RF-05.20: un nombre no válido se rechaza y el otro sigue ----------------------------------------------------

NOMBRES_NO_VALIDOS = [
    pytest.param("../PRUEBA_x.txt", id="B2-padre"),
    pytest.param("PRUEBA\\x.txt", id="B2-contrabarra"),
    pytest.param("PRUEBA:flujo.txt", id="B3-dos-puntos"),
    pytest.param("PRUEBA_x.txt.", id="B5-punto-final"),
    pytest.param("CON.txt", id="B5-reservado-con-extension"),
    pytest.param("PRUEBA_" + "a" * 250 + ".txt", id="B6-mas-de-255-bytes"),
    pytest.param("PRUEBA_" + "ñ" * 130 + ".txt", id="B6-tildes-mas-de-255-bytes"),
]


@pytest.mark.parametrize("nombre", NOMBRES_NO_VALIDOS)
def test_nombre_no_valido_se_rechaza_y_el_otro_sigue(cliente_api, sesion, carpeta_archivos, encoladas, nombre):
    """RF-05.20: el archivo inválido figura rechazado en su posición, con el aviso genérico y sin su nombre; el válido
    se guarda en su tema y se encola; no se escribe nada fuera de la carpeta del tema."""
    respuesta = _cargar(cliente_api, sesion, TEMA, [(nombre, CONTENIDO), ("PRUEBA_valido.txt", CONTENIDO)])

    assert respuesta.status_code == 200
    ids = respuesta.json()["task_ids"]
    assert ids[0] == {"error": True, "message": "Nombre de archivo no válido"}
    assert ids[1] == "PRUEBA-tarea-1"
    assert nombre not in respuesta.text and "filename" not in ids[0]
    assert _instantanea(carpeta_archivos / "uploads") == [TEMA, f"{TEMA}/PRUEBA_valido.txt"]
    assert [p.name for p in (carpeta_archivos / "uploads" / TEMA).iterdir()] == ["PRUEBA_valido.txt"]
    assert len(encoladas) == 1 and encoladas[0][1]["filename"] == "PRUEBA_valido.txt"


def test_nombre_que_con_el_sufijo_supera_los_255_bytes_se_rechaza(cliente_api, sesion, carpeta_archivos, encoladas):
    """RF-05.20 (B6 con sufijo): el nombre cabe (254 bytes) pero ya existe y su copia `_1` llegaría a 256 bytes: se
    rechaza sin crear nada nuevo."""
    nombre = "a" * 250 + ".txt"
    carpeta = carpeta_archivos / "uploads" / TEMA
    carpeta.mkdir(parents=True)
    (carpeta / nombre).write_bytes(b"PRUEBA ya existia")
    antes = _instantanea(carpeta_archivos)

    respuesta = _cargar(cliente_api, sesion, TEMA, [(nombre, CONTENIDO)])

    assert respuesta.status_code == 200
    assert respuesta.json()["task_ids"] == [{"error": True, "message": "Nombre de archivo no válido"}]
    assert _instantanea(carpeta_archivos) == antes
    assert (carpeta / nombre).read_bytes() == b"PRUEBA ya existia"
    assert encoladas == []


# --- RF-05.21 (a): la carga funciona sea cual sea la ubicación de la carpeta de documentos -----------------------

def test_carga_valida_fuera_de_app(cliente_api, sesion, carpeta_archivos, encoladas):
    """RF-05.21: con la carpeta de documentos fuera de `/app` (la temporal), la carga devuelve un id de tarea, deja el
    archivo en `<temporal>/uploads/<tema>/` y entrega la ruta `uploads/<tema>/<nombre>`; un nombre repetido recibe el
    sufijo de siempre, confinado."""
    nombre = "PRUEBA contrato (1) año.txt"

    primera = _cargar(cliente_api, sesion, TEMA, [(nombre, CONTENIDO)])
    segunda = _cargar(cliente_api, sesion, TEMA, [(nombre, CONTENIDO + b" otra")])

    assert primera.status_code == 200 and segunda.status_code == 200
    assert primera.json()["task_ids"] == ["PRUEBA-tarea-1"] and segunda.json()["task_ids"] == ["PRUEBA-tarea-2"]
    carpeta = carpeta_archivos / "uploads" / TEMA
    assert (carpeta / nombre).read_bytes() == CONTENIDO
    assert (carpeta / "PRUEBA contrato (1) año_1.txt").read_bytes() == CONTENIDO + b" otra"
    assert [e[1]["relative_path"] for e in encoladas] == [
        f"uploads/{TEMA}/{nombre}", f"uploads/{TEMA}/PRUEBA contrato (1) año_1.txt"
    ]
    assert not encoladas[0][1]["relative_path"].startswith("/")


def test_escritura_que_falla_figura_rechazada_sin_rutas(cliente_api, sesion, carpeta_archivos, encoladas, monkeypatch):
    """RF-05.21 (b) y RNF-07.23: si la escritura falla, ese archivo figura rechazado con «No se pudo guardar el
    archivo», sin la ruta ni el texto de la excepción, sin tarea y sin archivo; el otro archivo sigue."""
    from app.services.documentos.file_management_service import file_management_service

    real = file_management_service._get_unique_filename
    secreto = "/srv/PRUEBA_interna/PRUEBA_secreto.txt"

    def _falla_con_el_primero(directorio, nombre):
        if nombre == "PRUEBA_falla.txt":
            raise OSError(f"disco lleno en {secreto}")
        return real(directorio, nombre)

    monkeypatch.setattr(file_management_service, "_get_unique_filename", _falla_con_el_primero)

    respuesta = _cargar(cliente_api, sesion, TEMA, [("PRUEBA_falla.txt", CONTENIDO), ("PRUEBA_sigue.txt", CONTENIDO)])

    assert respuesta.status_code == 200
    assert respuesta.json()["task_ids"] == [{"error": True, "message": "No se pudo guardar el archivo"}, "PRUEBA-tarea-1"]
    assert secreto not in respuesta.text and "PRUEBA_secreto" not in respuesta.text and "PRUEBA_falla" not in respuesta.text
    assert [p.name for p in (carpeta_archivos / "uploads" / TEMA).iterdir()] == ["PRUEBA_sigue.txt"]


# --- RF-21.20 y RNF-07.24: el rechazo no repite lo pedido -------------------------------------------------------

def test_rechazo_de_carga_sin_datos_personales(cliente_api, sesion, usuario_gubernamental, carpeta_archivos, encoladas,
                                               caplog):
    """RNF-07.24 (B11) y RF-21.20: con un nombre de persona inventado y un carácter no válido en el tema o en el
    nombre del archivo, ni la respuesta, ni la bitácora, ni el registro del servidor lo contienen; la bitácora guarda
    solo el motivo («tema no válido» o «nombre de archivo no válido») como error de validación."""
    from app.constants.tipos_accion import TiposAccion

    caplog.set_level(logging.DEBUG, logger="app")
    tema_malo = f"{PERSONA}:"
    nombre_malo = f"{PERSONA}\\documento.txt"

    por_tema = _cargar(cliente_api, sesion, tema_malo, [(f"{PERSONA}.txt", CONTENIDO)])
    por_nombre = _cargar(cliente_api, sesion, TEMA, [(nombre_malo, CONTENIDO)])

    assert (por_tema.status_code, por_tema.json()) == (400, {"detail": "El tema indicado no es válido"})
    assert por_nombre.status_code == 200
    assert por_nombre.json()["task_ids"] == [{"error": True, "message": "Nombre de archivo no válido"}]
    for respuesta in (por_tema, por_nombre):
        assert not any(parte in respuesta.text for parte in _PARTES_DE_LA_PERSONA), respuesta.text

    rechazos = [f for f in _filas(usuario_gubernamental, TiposAccion.CARGA_DOCUMENTOS) if "rechazada" in f["texto"]]
    assert [f["texto"] for f in rechazos] == ["Carga rechazada: tema no válido", "Carga rechazada: nombre de archivo no válido"]
    assert all(f["datos"].get("tipo_error") == "validacion" for f in rechazos)
    for fila in _filas(usuario_gubernamental, TiposAccion.CARGA_DOCUMENTOS):
        registrado = fila["texto"] + fila["info"]
        assert not any(parte in registrado for parte in _PARTES_DE_LA_PERSONA), registrado
        assert not re.search(r"[\x00-\x1f\x7f-\x9f]", fila["texto"])
    assert not any(parte in caplog.text for parte in _PARTES_DE_LA_PERSONA), "El registro del servidor repite lo pedido."


def test_rechazo_de_carga_con_bitacora_que_falla_responde_igual(cliente_api, sesion, usuario_gubernamental,
                                                                carpeta_archivos, encoladas, monkeypatch):
    """RF-21.20: si el registro en la bitácora falla, las respuestas son las mismas y no queda ninguna fila de rechazo."""
    from app.constants.tipos_accion import TiposAccion
    from app.services.bitacora.bitacora_service import BitacoraService

    async def _falla(self, *args, **kwargs):
        raise Exception("falla simulada de la bitácora")

    monkeypatch.setattr(BitacoraService, "registrar", _falla)

    por_tema = _cargar(cliente_api, sesion, "a/b", [("PRUEBA_a.txt", CONTENIDO)])
    por_nombre = _cargar(cliente_api, sesion, TEMA, [("../PRUEBA_x.txt", CONTENIDO)])

    assert (por_tema.status_code, por_tema.json()) == (400, {"detail": "El tema indicado no es válido"})
    assert por_nombre.status_code == 200
    assert por_nombre.json()["task_ids"] == [{"error": True, "message": "Nombre de archivo no válido"}]
    assert _filas(usuario_gubernamental, TiposAccion.CARGA_DOCUMENTOS) == []


# --- RNF-07.23: un error inesperado da un mensaje genérico ------------------------------------------------------

def test_error_inesperado_es_generico(cliente_api, sesion, usuario_gubernamental, carpeta_archivos, encoladas, monkeypatch):
    """RNF-07.23: un error inesperado con una ruta del servidor inventada en su mensaje da, por archivo, «Error interno
    del servidor» y, en la carga completa, 500 con ese mismo texto; ninguna respuesta repite la ruta, ni el nombre del
    archivo, ni el texto de la excepción.

    Spec 004 (tarea 9a, plan §16.5): la carga iniciada se registra solo si hay al menos un archivo aceptado, así que
    antes de la segunda parte se restablece el encolado interceptado; lo que se comprueba es lo mismo."""
    from app.services.bitacora.ingesta_audit_service import ingesta_audit_service
    from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery

    secreto = "/srv/PRUEBA_interna/PRUEBA_secreto.txt"

    def _falla_al_encolar(*args, **kwargs):
        raise RuntimeError(f"fallo leyendo {secreto}")

    encolado_interceptado = procesar_archivo_celery.delay    # el de la fixture `encoladas`
    monkeypatch.setattr(procesar_archivo_celery, "delay", _falla_al_encolar)
    por_archivo = _cargar(cliente_api, sesion, TEMA, [(f"{PERSONA}.txt", CONTENIDO)])

    assert por_archivo.status_code == 200
    assert por_archivo.json()["task_ids"] == [{"error": True, "message": "Error interno del servidor"}]

    monkeypatch.setattr(procesar_archivo_celery, "delay", encolado_interceptado)
    original = ingesta_audit_service.registrar_ingesta

    async def _falla_en_la_primera(*args, **kwargs):
        if kwargs.get("fase") == "iniciado":
            raise RuntimeError(f"fallo grabando {secreto}")
        return await original(*args, **kwargs)

    monkeypatch.setattr(ingesta_audit_service, "registrar_ingesta", _falla_en_la_primera)
    general = _cargar(cliente_api, sesion, TEMA, [(f"{PERSONA}.txt", CONTENIDO)])

    assert (general.status_code, general.json()) == (500, {"detail": "Error interno del servidor"})
    for respuesta in (por_archivo, general):
        assert secreto not in respuesta.text and "PRUEBA_secreto" not in respuesta.text
        assert not any(parte in respuesta.text for parte in _PARTES_DE_LA_PERSONA)


def test_listado_con_error_es_generico(cliente_api, sesion, usuario_gubernamental, monkeypatch):
    """RNF-07.23 y RNF-07.24 (listado de archivos de un tema): un error inesperado con una ruta y un nombre de persona
    inventados da 500 «Error interno del servidor» sin ellos, y la bitácora lo guarda como error interno, también sin
    ellos."""
    from app.constants.tipos_accion import TiposAccion
    from app.services.documentos.file_management_service import file_management_service

    secreto = f"/srv/PRUEBA_interna/{PERSONA}.txt"

    def _falla(*args, **kwargs):
        raise RuntimeError(f"fallo leyendo {secreto}")

    monkeypatch.setattr(file_management_service, "listar_archivos_expediente", _falla)

    respuesta = cliente_api.get(f"/archivos/expediente/{TEMA_CON_FORMATO}/archivos", headers=sesion)

    assert (respuesta.status_code, respuesta.json()) == (500, {"detail": "Error interno del servidor"})
    assert "PRUEBA_interna" not in respuesta.text
    assert not any(parte in respuesta.text for parte in _PARTES_DE_LA_PERSONA)
    filas = _filas(usuario_gubernamental, TiposAccion.LISTAR_ARCHIVOS)
    assert len(filas) == 1
    registrado = filas[0]["texto"] + filas[0]["info"]
    assert "PRUEBA_interna" not in registrado and not any(parte in registrado for parte in _PARTES_DE_LA_PERSONA)
    assert filas[0]["datos"].get("tipo_error") == "interno"
