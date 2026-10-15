"""Pruebas de T2 (spec 004a): la descarga solo entrega documentos registrados, Procesados, confinados y propios.

Cubren RNF-07.20 (la descarga por ruta y por tema y nombre responde el mismo 404 «Archivo no encontrado» a todo lo que no
sea un documento descargable: rutas absolutas, con `..`, codificadas, con `\\`, carpetas, archivos sin registrar, avatares,
registrados pero no Procesados, enlaces que salen), RF-18.20 (el documento de un notebook ajeno o inexistente, con la clave
en cualquier grafía, da 404 sin distinguirse; el dueño sí lo descarga) y RF-12.20 (la fuente citada en el chat llega íntegra,
con tildes, ñ, espacios, paréntesis y el sufijo `_1`).

Usan la base `servia_pruebas` y una carpeta temporal desviada (`carpeta_archivos`): el archivo testigo `PRUEBA_testigo.txt`
está FUERA de la carpeta de documentos pero dentro de la temporal, y nunca debe salir. Nunca se lee un archivo del
servidor ni se toca el `uploads/` real. Los documentos y temas llevan el prefijo `PRUEBA`; la clave `NB-<id>` de un
notebook de prueba no lo lleva, así que la fixture `notebook_con_documento` borra lo suyo.

T3 añade la misma pertenencia por la ruta de tema y nombre (RF-18.20), el rechazo en la bitácora solo con su motivo
(RF-21.20), sin nombres ni rutas pedidos en la respuesta, la bitácora ni el registro del servidor (RNF-07.24), y el 500
genérico (RNF-07.23). La ruta por tema y nombre exige primero un tema con formato de expediente (17 a 20 caracteres): una
clave `NB-<id>` corta nunca llega a la pertenencia (400), y por eso estas pruebas, para ejercitar la pertenencia, hacen
pasar esa validación de formato con `monkeypatch`; la prueba del 400 documenta el caso real.
"""
import json
import logging
from urllib.parse import quote

import pytest
from sqlalchemy import text

from tests.soporte import datos
from tests.soporte.nombres import PREFIJO_DATOS

TESTIGO = "PRUEBA_testigo.txt"
CONTENIDO_DEL_TESTIGO = b"PRUEBA contenido del testigo, fuera de la carpeta de documentos"
CONTENIDO_DEL_DOCUMENTO = b"PRUEBA contenido integro del documento registrado"
TEMA = "PRUEBA tema de descargas"
DOCUMENTO = "PRUEBA_registrado.txt"
# Tema con el formato que acepta la ruta por tema y nombre (17 a 20 caracteres alfanuméricos y guiones).
TEMA_CON_FORMATO = "PRUEBA-TEMA-T2-0001"


# --- Datos de prueba (base, disco y sesión) ---------------------------------------------------------------------

def _registrar_documento(tema: str, nombre: str, procesado: bool = True) -> None:
    """Da de alta tema (si falta), documento y su unión en la base de pruebas, con el estado indicado."""
    from app.db.database import SessionLocal
    from app.db.models import T_Documento, T_Estado_procesamiento, T_Expediente, T_Expediente_Documento

    with SessionLocal() as db:
        if procesado:
            filtro = T_Estado_procesamiento.CT_Nombre_estado == "Procesado"
        else:
            filtro = T_Estado_procesamiento.CT_Nombre_estado != "Procesado"
        id_estado = db.query(T_Estado_procesamiento.CN_Id_estado).filter(filtro).limit(1).scalar()
        assert id_estado is not None, "La base de pruebas no tiene los estados de procesamiento."
        expediente = db.query(T_Expediente).filter(T_Expediente.CT_Num_expediente == tema).first()
        if expediente is None:
            expediente = T_Expediente(CT_Num_expediente=tema)
            db.add(expediente)
            db.flush()
        documento = T_Documento(
            CT_Nombre_archivo=nombre, CT_Tipo_archivo="text/plain", CT_Ruta_archivo=f"uploads/{tema}/{nombre}",
            CN_Id_estado=id_estado,
        )
        db.add(documento)
        db.flush()
        db.execute(T_Expediente_Documento.insert().values(
            CN_Id_expediente=expediente.CN_Id_expediente, CN_Id_documento=documento.CN_Id_documento
        ))
        db.commit()


def _crear_en_disco(carpeta_archivos, tema: str, nombre: str, contenido: bytes = CONTENIDO_DEL_DOCUMENTO):
    carpeta = carpeta_archivos / "uploads" / tema
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre
    ruta.write_bytes(contenido)
    return ruta


def _descargar(cliente_api, cabeceras, ruta: str):
    """Pide la descarga como la interfaz: `GET /archivos/download?ruta_archivo=<ruta>` (el cliente la codifica una vez)."""
    return cliente_api.get("/archivos/download", params={"ruta_archivo": ruta}, headers=cabeceras)


def _sin_contenido_filtrado(respuesta) -> bool:
    return CONTENIDO_DEL_TESTIGO not in respuesta.content and CONTENIDO_DEL_DOCUMENTO not in respuesta.content


@pytest.fixture
def testigo(carpeta_archivos):
    """El archivo que nunca debe salir: fuera de la carpeta de documentos, dentro de la temporal."""
    ruta = carpeta_archivos / TESTIGO
    ruta.write_bytes(CONTENIDO_DEL_TESTIGO)
    return ruta


@pytest.fixture
def sesion(cliente_api, iniciar_sesion, usuario_gubernamental):
    """Las cabeceras de un Usuario Gubernamental de prueba."""
    return iniciar_sesion(usuario_gubernamental)


@pytest.fixture
def notebook_con_documento(carpeta_archivos, usuario_gubernamental):
    """Un notebook de `usuario_gubernamental` con un documento Procesado (tema `NB-<id>`) y su archivo en la temporal.

    Devuelve el id del notebook. Borra al terminar lo que la limpieza general no alcanza (el tema `NB-<id>` no lleva el
    prefijo `PRUEBA`): bitácora del tema, unión, documento y tema.
    """
    from app.db.database import SessionLocal
    from app.db.models import T_Notebook

    with SessionLocal() as db:
        notebook = T_Notebook(CT_Nombre=f"{PREFIJO_DATOS} notebook de descargas", CN_Id_usuario=usuario_gubernamental.cedula)
        db.add(notebook)
        db.commit()
        notebook_id = notebook.CN_Id_notebook
    tema = f"NB-{notebook_id}"
    _registrar_documento(tema, "PRUEBA_imagen.png")
    _crear_en_disco(carpeta_archivos, tema, "PRUEBA_imagen.png")
    try:
        yield notebook_id
    finally:
        with SessionLocal() as db:
            id_tema = f"(SELECT CN_Id_expediente FROM T_Expediente WHERE CT_Num_expediente = '{tema}')"
            db.execute(text(f"DELETE FROM T_Bitacora WHERE CN_Id_expediente = {id_tema}"))
            db.execute(text(f"DELETE FROM T_Expediente_Documento WHERE CN_Id_expediente = {id_tema}"))
            db.execute(text("DELETE FROM T_Documento WHERE CT_Nombre_archivo = 'PRUEBA_imagen.png' "
                            "AND CT_Ruta_archivo = :ruta"), {"ruta": f"uploads/{tema}/PRUEBA_imagen.png"})
            db.execute(text("DELETE FROM T_Expediente WHERE CT_Num_expediente = :tema"), {"tema": tema})
            db.commit()


# --- RNF-07.20: nada fuera de los documentos registrados sale ---------------------------------------------------

def _rutas_rechazadas():
    """Las rutas de los casos A1-A9 y A11 (la ruta se envía codificada una vez; el sistema la decodifica otra vez, D9)."""
    return [
        pytest.param(f"uploads/../{TESTIGO}", id="A1-padre-tras-el-prefijo"),
        pytest.param(f"uploads/{TEMA}/../../{TESTIGO}", id="A1-padre-en-medio"),
        pytest.param(f"../{TESTIGO}", id="A1-padre-al-inicio"),
        pytest.param("uploads/%2e%2e/" + TESTIGO, id="A3-codificada-una-vez"),
        pytest.param("uploads/%252e%252e/" + TESTIGO, id="A3-codificada-dos-veces"),
        pytest.param(f"uploads/{TEMA}/%2E%2E/%2E%2E/{TESTIGO}", id="A3-mayusculas-y-codificada"),
        pytest.param(f"uploads\\..\\{TESTIGO}", id="A4-contrabarras"),
        pytest.param(f"uploads/{TEMA}\\..\\..\\{TESTIGO}", id="A4-mezcladas"),
        pytest.param("uploads", id="A6-carpeta-de-documentos"),
        pytest.param(f"uploads/{TEMA}", id="A6-carpeta-de-un-tema"),
        pytest.param(f"uploads/{TEMA}/subcarpeta", id="A6-subcarpeta"),
        pytest.param(f"uploads/{TEMA}/PRUEBA_sin_registro.txt", id="A7-archivo-no-registrado"),
        pytest.param(f"uploads/PRUEBA tema ajeno/{DOCUMENTO}", id="A7-registrado-en-otro-tema"),
        pytest.param("uploads/profiles/PRUEBA_avatar.png", id="A8-avatar"),
        pytest.param("uploads/PROFILES/PRUEBA_avatar.png", id="A8-avatar-mayusculas"),
        pytest.param("", id="A9-vacia"),
        pytest.param("   ", id="A9-espacios"),
        pytest.param(f"uploads/{TEMA}/PRUEBA_registrado%00.txt", id="A9-percent00"),
        pytest.param(f"uploads/{TEMA}/PRUEBA_registrado\x00.txt", id="A9-nul"),
        pytest.param(f"uploads/{TEMA}/PRUEBA\n_registrado.txt", id="A9-control"),
        pytest.param(f"uploads/{TEMA}/PRUEBA_pendiente.txt", id="A11-registrado-no-procesado"),
    ]


def _preparar_escenario_de_rechazos(carpeta_archivos, testigo):
    """Un documento Procesado, uno sin registrar, uno no Procesado, una subcarpeta y un avatar, todo en la temporal."""
    _registrar_documento(TEMA, DOCUMENTO)
    _crear_en_disco(carpeta_archivos, TEMA, DOCUMENTO)
    _crear_en_disco(carpeta_archivos, TEMA, "PRUEBA_sin_registro.txt")
    _registrar_documento(TEMA, "PRUEBA_pendiente.txt", procesado=False)
    _crear_en_disco(carpeta_archivos, TEMA, "PRUEBA_pendiente.txt")
    (carpeta_archivos / "uploads" / TEMA / "subcarpeta").mkdir()
    _crear_en_disco(carpeta_archivos, "PRUEBA tema ajeno", DOCUMENTO)
    _crear_en_disco(carpeta_archivos, "profiles", "PRUEBA_avatar.png")


@pytest.mark.parametrize("ruta", _rutas_rechazadas())
def test_ruta_fuera_de_la_carpeta_no_entrega_el_testigo(cliente_api, sesion, carpeta_archivos, testigo, ruta):
    """RNF-07.20 (A1-A9, A11): lo que no es un documento registrado y Procesado da 404 «Archivo no encontrado», sin el
    contenido del testigo ni de ningún archivo y sin tocar el disco."""
    _preparar_escenario_de_rechazos(carpeta_archivos, testigo)
    antes = sorted(str(p.relative_to(carpeta_archivos)) for p in carpeta_archivos.rglob("*"))

    respuesta = _descargar(cliente_api, sesion, ruta)

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Archivo no encontrado"}
    assert _sin_contenido_filtrado(respuesta)
    assert sorted(str(p.relative_to(carpeta_archivos)) for p in carpeta_archivos.rglob("*")) == antes
    assert testigo.read_bytes() == CONTENIDO_DEL_TESTIGO


def test_ruta_absoluta_al_testigo_no_lo_entrega(cliente_api, sesion, carpeta_archivos, testigo):
    """RNF-07.20, A2: la ruta absoluta del archivo testigo (Linux, Windows, recurso de red y empezando por separador)
    da 404 y nunca su contenido."""
    _preparar_escenario_de_rechazos(carpeta_archivos, testigo)
    rutas = [str(testigo), "/etc/hostname", "C:\\Windows\\win.ini", "\\\\servidor\\recurso\\" + TESTIGO,
             f"/uploads/{TEMA}/{DOCUMENTO}"]

    for ruta in rutas:
        respuesta = _descargar(cliente_api, sesion, ruta)
        assert (respuesta.status_code, respuesta.json()) == (404, {"detail": "Archivo no encontrado"}), ruta
        assert _sin_contenido_filtrado(respuesta), ruta


def test_enlace_que_sale_de_la_carpeta_no_entrega_el_testigo(cliente_api, sesion, carpeta_archivos, testigo):
    """RNF-07.20, A5: un documento registrado y Procesado cuyo archivo es un enlace hacia fuera no se entrega."""
    _registrar_documento(TEMA, "PRUEBA_enlace.txt")
    carpeta = carpeta_archivos / "uploads" / TEMA
    carpeta.mkdir(parents=True)
    try:
        (carpeta / "PRUEBA_enlace.txt").symlink_to(testigo)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"No se pueden crear enlaces simbólicos aquí: {type(error).__name__}")

    respuesta = _descargar(cliente_api, sesion, f"uploads/{TEMA}/PRUEBA_enlace.txt")

    assert (respuesta.status_code, respuesta.json()) == (404, {"detail": "Archivo no encontrado"})
    assert _sin_contenido_filtrado(respuesta)


def test_documento_no_procesado_por_tema_y_nombre_da_404(cliente_api, sesion, carpeta_archivos):
    """RNF-07.20, A11 (ruta por tema y nombre): registrado pero no Procesado da el mismo 404 que lo que no existe, no un
    400 distinto que confirme que el documento está. El documento Procesado de control sí se descarga."""
    _registrar_documento(TEMA_CON_FORMATO, DOCUMENTO)
    _crear_en_disco(carpeta_archivos, TEMA_CON_FORMATO, DOCUMENTO)
    _registrar_documento(TEMA_CON_FORMATO, "PRUEBA_pendiente.txt", procesado=False)
    _crear_en_disco(carpeta_archivos, TEMA_CON_FORMATO, "PRUEBA_pendiente.txt")

    control = cliente_api.get(f"/archivos/expediente/{TEMA_CON_FORMATO}/archivo/{DOCUMENTO}", headers=sesion)
    pendiente = cliente_api.get(f"/archivos/expediente/{TEMA_CON_FORMATO}/archivo/PRUEBA_pendiente.txt", headers=sesion)
    inexistente = cliente_api.get(f"/archivos/expediente/{TEMA_CON_FORMATO}/archivo/PRUEBA_inexistente.txt", headers=sesion)

    assert (control.status_code, control.content) == (200, CONTENIDO_DEL_DOCUMENTO)
    assert (pendiente.status_code, pendiente.json()) == (404, {"detail": "Archivo no encontrado"})
    assert (inexistente.status_code, inexistente.json()) == (pendiente.status_code, pendiente.json())
    assert CONTENIDO_DEL_DOCUMENTO not in pendiente.content


# --- RF-18.20: el documento de un notebook ajeno no sale por ninguna grafía de la clave --------------------------

def test_documento_de_notebook_ajeno_da_404(cliente_api, iniciar_sesion, registro_de_datos, usuario_gubernamental,
                                            notebook_con_documento, carpeta_archivos):
    """RF-18.20 (A10): el dueño descarga su documento (control); otro Usuario Gubernamental recibe el mismo 404, sin el
    contenido, con la clave del notebook en cualquier grafía (`NB-`, `nb-`, `Nb-`) y también si el notebook no existe."""
    ajeno = iniciar_sesion(datos.crear_usuario(datos.ROL_USUARIO_GUBERNAMENTAL, registro_de_datos))
    dueno = iniciar_sesion(usuario_gubernamental)
    nombre = "PRUEBA_imagen.png"

    control = _descargar(cliente_api, dueno, f"uploads/NB-{notebook_con_documento}/{nombre}")
    assert (control.status_code, control.content) == (200, CONTENIDO_DEL_DOCUMENTO)

    inexistente = notebook_con_documento + 100000
    for tema in (f"NB-{notebook_con_documento}", f"nb-{notebook_con_documento}", f"Nb-{notebook_con_documento}",
                 f"nB-{notebook_con_documento}", f"NB-{inexistente}", f"nb-{inexistente}"):
        respuesta = _descargar(cliente_api, ajeno, f"uploads/{tema}/{nombre}")
        assert (respuesta.status_code, respuesta.json()) == (404, {"detail": "Archivo no encontrado"}), tema
        assert CONTENIDO_DEL_DOCUMENTO not in respuesta.content, tema
        # También con la ruta codificada: el sistema decodifica una vez más (D9) y comprueba la ruta final.
        codificada = _descargar(cliente_api, ajeno, f"uploads/%6eb-{notebook_con_documento}/{nombre}")
        assert codificada.status_code == 404 and CONTENIDO_DEL_DOCUMENTO not in codificada.content, tema


# --- RF-12.20: la fuente citada llega íntegra ------------------------------------------------------------------

@pytest.mark.parametrize("tema, nombre", [
    pytest.param("PRUEBA tema simple", "PRUEBA_contrato.pdf", id="simple"),
    pytest.param("PRUEBA Resolución Nº 5 (año 2026)", "PRUEBA informe final (copia) año 2026.pdf", id="tildes-espacios-y-parentesis"),
    pytest.param("PRUEBA tema ñandú", "PRUEBA Resolución ñandú.docx", id="ñ"),
    pytest.param("PRUEBA tema repetido", "PRUEBA_contrato_1.pdf", id="sufijo-de-nombre-repetido"),
])
def test_descarga_legitima_como_la_cita_el_chat(cliente_api, sesion, carpeta_archivos, tema, nombre):
    """RF-12.20: el documento registrado y Procesado se entrega íntegro, con su nombre, pidiéndolo con la ruta guardada
    (`uploads/<tema>/<nombre>`) como lo hacen la cita del chat y los temas similares."""
    contenido = CONTENIDO_DEL_DOCUMENTO + nombre.encode("utf-8")
    _registrar_documento(tema, nombre)
    _crear_en_disco(carpeta_archivos, tema, nombre, contenido)

    respuesta = _descargar(cliente_api, sesion, f"uploads/{tema}/{nombre}")

    assert respuesta.status_code == 200
    assert respuesta.content == contenido
    disposicion = respuesta.headers["content-disposition"]
    assert (f'filename="{nombre}"' in disposicion) if nombre.isascii() else (quote(nombre) in disposicion)


# --- T3, RF-18.20 y RNF-07.20: la ruta por tema y nombre comprueba lo mismo que la ruta completa ------------------

def _por_tema(cliente_api, cabeceras, tema: str, nombre_crudo: str):
    """Pide la descarga por tema y nombre; `nombre_crudo` va tal cual en la dirección (el cliente no lo codifica)."""
    return cliente_api.get(f"/archivos/expediente/{quote(tema)}/archivo/{nombre_crudo}", headers=cabeceras)


def _sin_formato(monkeypatch):
    """Hace pasar la validación de formato de expediente de la ruta, para llegar a la pertenencia con una clave `NB-<id>`."""
    monkeypatch.setattr("app.routes.archivos.validar_expediente", lambda numero: True)


@pytest.fixture
def ajeno_usuario(registro_de_datos):
    """Otro Usuario Gubernamental de prueba: no es dueño de ningún notebook."""
    return datos.crear_usuario(datos.ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)


def test_por_tema_y_nombre_de_notebook_ajeno_da_404(cliente_api, iniciar_sesion, ajeno_usuario, usuario_gubernamental,
                                                    notebook_con_documento, monkeypatch):
    """RF-18.20 (por tema y nombre): el dueño descarga su documento (control: el 404 no es por la ubicación); otro usuario
    recibe el mismo 404 sin el contenido, con la clave en cualquier grafía y también si el notebook no existe."""
    _sin_formato(monkeypatch)
    dueno = iniciar_sesion(usuario_gubernamental)
    ajeno = iniciar_sesion(ajeno_usuario)
    nombre = "PRUEBA_imagen.png"

    control = _por_tema(cliente_api, dueno, f"NB-{notebook_con_documento}", nombre)
    assert (control.status_code, control.content) == (200, CONTENIDO_DEL_DOCUMENTO)

    inexistente = notebook_con_documento + 100000
    for tema in (f"NB-{notebook_con_documento}", f"nb-{notebook_con_documento}", f"Nb-{notebook_con_documento}",
                 f"NB-{inexistente}", f"nb-{inexistente}"):
        respuesta = _por_tema(cliente_api, ajeno, tema, nombre)
        assert (respuesta.status_code, respuesta.json()) == (404, {"detail": "Archivo no encontrado"}), tema
        assert CONTENIDO_DEL_DOCUMENTO not in respuesta.content, tema


def test_clave_corta_de_notebook_por_tema_y_nombre_da_400_a_todos(cliente_api, iniciar_sesion, ajeno_usuario,
                                                                  usuario_gubernamental, notebook_con_documento):
    """Caracterización (RF-18.20): sin hacer pasar la validación de formato, una clave `NB-<id>` real (corta) da el mismo
    400 «Formato de expediente inválido» al dueño y al ajeno: esta ruta nunca llega a la pertenencia con ids pequeños."""
    for usuario in (usuario_gubernamental, ajeno_usuario):
        respuesta = _por_tema(cliente_api, iniciar_sesion(usuario), f"NB-{notebook_con_documento}", "PRUEBA_imagen.png")
        assert (respuesta.status_code, respuesta.json()) == (400, {"detail": "Formato de expediente inválido"})
        assert CONTENIDO_DEL_DOCUMENTO not in respuesta.content


# Nombre tal como va en la dirección, y si la petición llega al manejador (404 «Archivo no encontrado») o la frena antes
# el enrutador, porque un `/` decodificado ya no es un solo segmento (404 «Not Found»).
_NOMBRES_HOSTILES = [
    pytest.param("%2e%2e", True, id="padre-codificado"),
    pytest.param("%252e%252e", True, id="padre-codificado-dos-veces"),
    pytest.param("%2e", True, id="punto-solo"),
    pytest.param("..%5C" + TESTIGO, True, id="contrabarra-tras-padre"),
    pytest.param("%5C..%5C" + TESTIGO, True, id="contrabarras"),
    pytest.param("..%252F" + TESTIGO, False, id="barra-codificada-dos-veces"),
    pytest.param("..%2F..%2F" + TESTIGO, False, id="barras-codificadas"),
    pytest.param("%2Fetc%2Fhostname", False, id="absoluta-codificada"),
    pytest.param("%252Fetc%252Fhostname", False, id="absoluta-codificada-dos-veces"),
    pytest.param("PRUEBA_registrado%00.txt", True, id="nul"),
    pytest.param("%20", True, id="espacio"),
    pytest.param("%20%20", True, id="espacios"),
    pytest.param("PRUEBA_enlace.txt", True, id="enlace-que-sale"),
]


@pytest.mark.parametrize("nombre_crudo, llega_al_manejador", _NOMBRES_HOSTILES)
def test_por_tema_y_nombre_hostil_da_404(cliente_api, sesion, carpeta_archivos, testigo, nombre_crudo, llega_al_manejador):
    """RNF-07.20, RNF-07.21 (por tema y nombre): un nombre con `..`, barras codificadas, ruta absoluta, NUL, solo espacios
    o un enlace que sale da 404, nunca el testigo ni el documento, y no toca el disco."""
    _registrar_documento(TEMA_CON_FORMATO, DOCUMENTO)
    _crear_en_disco(carpeta_archivos, TEMA_CON_FORMATO, DOCUMENTO)
    _registrar_documento(TEMA_CON_FORMATO, "PRUEBA_enlace.txt")
    try:
        (carpeta_archivos / "uploads" / TEMA_CON_FORMATO / "PRUEBA_enlace.txt").symlink_to(testigo)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"No se pueden crear enlaces simbólicos aquí: {type(error).__name__}")
    antes = sorted(str(p.relative_to(carpeta_archivos)) for p in carpeta_archivos.rglob("*"))

    respuesta = _por_tema(cliente_api, sesion, TEMA_CON_FORMATO, nombre_crudo)

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Archivo no encontrado" if llega_al_manejador else "Not Found"}
    assert _sin_contenido_filtrado(respuesta)
    assert sorted(str(p.relative_to(carpeta_archivos)) for p in carpeta_archivos.rglob("*")) == antes


def test_por_tema_y_nombre_con_tema_hostil_no_llega_a_ningun_documento(cliente_api, sesion, carpeta_archivos, testigo):
    """RNF-07.20 (por tema y nombre): un tema que no es un solo nombre (`..`, `profiles`) da 400 o 404, nunca contenido."""
    _crear_en_disco(carpeta_archivos, "profiles", "PRUEBA_avatar.png")
    for tema in ("..", "%2e%2e", "profiles", "PROFILES"):
        respuesta = cliente_api.get(f"/archivos/expediente/{tema}/archivo/PRUEBA_avatar.png", headers=sesion)
        assert respuesta.status_code in (400, 404), tema
        assert _sin_contenido_filtrado(respuesta), tema
        assert CONTENIDO_DEL_DOCUMENTO not in respuesta.content, tema


# --- T3, RF-21.20: el rechazo queda en la bitácora solo con su motivo -------------------------------------------

def _filas_de_descarga(usuario) -> list:
    """Las filas de descarga de la bitácora del usuario, en orden: [{texto, info (texto JSON), datos (dict)}]."""
    from app.constants.tipos_accion import TiposAccion
    from app.db.database import engine

    with engine.connect() as conexion:
        filas = conexion.execute(
            text("SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_usuario = :u "
                 "AND CN_Id_tipo_accion = :t ORDER BY CN_Id_bitacora"),
            {"u": usuario.cedula, "t": TiposAccion.DESCARGAR_ARCHIVO},
        ).fetchall()
    return [{"texto": f[0], "info": f[1] or "", "datos": json.loads(f[1]) if f[1] else {}} for f in filas]


def _casos_de_rechazo(notebook_id: int):
    """(descripción, función que pide, motivo esperado) de cada clase de rechazo, por las dos vías de descarga."""
    return [
        ("ruta-con-padre", lambda c, h: _descargar(c, h, f"uploads/../{TESTIGO}"), "ruta no permitida"),
        ("ruta-notebook-ajeno", lambda c, h: _descargar(c, h, f"uploads/NB-{notebook_id}/PRUEBA_imagen.png"),
         "documento ajeno"),
        ("ruta-no-procesado", lambda c, h: _descargar(c, h, f"uploads/{TEMA}/PRUEBA_pendiente.txt"),
         "documento no disponible"),
        ("tema-padre", lambda c, h: _por_tema(c, h, TEMA, "%2e%2e"), "ruta no permitida"),
        ("tema-notebook-ajeno", lambda c, h: _por_tema(c, h, f"NB-{notebook_id}", "PRUEBA_imagen.png"), "documento ajeno"),
        ("tema-no-procesado", lambda c, h: _por_tema(c, h, TEMA, "PRUEBA_pendiente.txt"), "documento no disponible"),
    ]


def test_rechazo_queda_en_bitacora_con_motivo(cliente_api, iniciar_sesion, ajeno_usuario, notebook_con_documento,
                                              carpeta_archivos, testigo, monkeypatch):
    """RF-21.20: cada clase de rechazo, por ruta y por tema y nombre, deja UNA fila del usuario con «Descarga rechazada:
    <motivo>» y clasificada como error de acceso (no interno)."""
    _preparar_escenario_de_rechazos(carpeta_archivos, testigo)
    _sin_formato(monkeypatch)
    ajeno = iniciar_sesion(ajeno_usuario)

    for descripcion, pedir, motivo in _casos_de_rechazo(notebook_con_documento):
        antes = len(_filas_de_descarga(ajeno_usuario))
        respuesta = pedir(cliente_api, ajeno)
        filas = _filas_de_descarga(ajeno_usuario)

        assert respuesta.status_code == 404, descripcion
        assert len(filas) == antes + 1, descripcion
        assert filas[-1]["texto"] == f"Descarga rechazada: {motivo}", descripcion
        assert filas[-1]["datos"].get("tipo_error") == "acceso", descripcion


def test_rechazo_con_bitacora_que_falla_responde_igual(cliente_api, iniciar_sesion, ajeno_usuario, notebook_con_documento,
                                                       carpeta_archivos, testigo, monkeypatch):
    """RF-21.20: si el registro en la bitácora falla, la respuesta es la misma 404 uniforme y no se rompe nada."""
    from app.services.bitacora.bitacora_service import BitacoraService

    _preparar_escenario_de_rechazos(carpeta_archivos, testigo)
    _sin_formato(monkeypatch)
    ajeno = iniciar_sesion(ajeno_usuario)

    async def _falla(self, *args, **kwargs):
        raise Exception("falla simulada de la bitácora")

    monkeypatch.setattr(BitacoraService, "registrar", _falla)
    for descripcion, pedir, motivo in _casos_de_rechazo(notebook_con_documento):
        respuesta = pedir(cliente_api, ajeno)
        assert (respuesta.status_code, respuesta.json()) == (404, {"detail": "Archivo no encontrado"}), descripcion
    assert _filas_de_descarga(ajeno_usuario) == []


# --- T3, RNF-07.24: ni el nombre ni la ruta pedidos se repiten ---------------------------------------------------

PERSONA = "PRUEBA Juana Inventada Solís"
_PARTES_DE_LA_PERSONA = ("Juana", "Inventada", "Solís")


def test_rechazo_no_repite_datos_personales(cliente_api, sesion, usuario_gubernamental, carpeta_archivos, caplog):
    """RNF-07.24 (A13 y `%00`): con un nombre de persona inventado en el tema, el nombre o la ruta pedidos, ni la
    respuesta, ni ninguna fila de la bitácora, ni el registro del servidor lo contienen; nada registrado lleva NUL ni
    caracteres de control, y la ruta con `%00` da 404 uniforme."""
    import re

    caplog.set_level(logging.DEBUG, logger="app")
    _registrar_documento(TEMA_CON_FORMATO, DOCUMENTO)
    _crear_en_disco(carpeta_archivos, TEMA_CON_FORMATO, DOCUMENTO)
    por_ruta = [
        f"uploads/{PERSONA}/{PERSONA}.pdf",
        f"uploads/{PERSONA}/../{PERSONA}.pdf",
        f"/home/{PERSONA}/{PERSONA}.pdf",
        f"uploads/{TEMA_CON_FORMATO}/{PERSONA}%00.pdf",
        f"uploads/{TEMA_CON_FORMATO}/{PERSONA}\x00.pdf",
        f"uploads/{TEMA_CON_FORMATO}/{PERSONA}\n.pdf",
    ]
    por_tema = [quote(f"{PERSONA}.pdf"), quote(PERSONA) + "%00.pdf", quote(PERSONA) + "%0A.pdf", quote(f"../{PERSONA}")]
    respuestas = [_descargar(cliente_api, sesion, ruta) for ruta in por_ruta]
    respuestas += [_por_tema(cliente_api, sesion, TEMA_CON_FORMATO, nombre) for nombre in por_tema]
    respuestas.append(_por_tema(cliente_api, sesion, PERSONA, "PRUEBA_x.pdf"))

    for respuesta in respuestas:
        assert respuesta.status_code in (400, 404)
        assert not any(parte in respuesta.text for parte in _PARTES_DE_LA_PERSONA), respuesta.text
        assert "\x00" not in respuesta.text and "%00" not in respuesta.text
    assert all(r.status_code == 404 and r.json() == {"detail": "Archivo no encontrado"} for r in respuestas[:len(por_ruta)])

    filas = _filas_de_descarga(usuario_gubernamental)
    assert filas, "Los rechazos de ruta deben quedar en la bitácora (con su motivo)."
    for fila in filas:
        registrado = fila["texto"] + fila["info"]
        assert not any(parte in registrado for parte in _PARTES_DE_LA_PERSONA), registrado
        assert not re.search(r"[\x00-\x1f\x7f-\x9f]", fila["texto"]) and "\\u00" not in fila["info"], registrado
        assert "%00" not in registrado
    assert not any(parte in caplog.text for parte in _PARTES_DE_LA_PERSONA), "El registro del servidor repite lo pedido."
    assert "\x00" not in caplog.text


def _lineas_de_acceso(*rutas: str) -> list[str]:
    """Emite, por el registro de acceso de uvicorn, una línea por ruta con el mismo formato que usa el servidor real
    (`%s - "%s %s HTTP/%s" %d`) y devuelve lo que un manejador habría escrito."""

    class _Captura(logging.Handler):
        def __init__(self):
            super().__init__()
            self.lineas: list[str] = []

        def emit(self, record):
            self.lineas.append(record.getMessage())

    captura = _Captura()
    acceso = logging.getLogger("uvicorn.access")
    acceso.addHandler(captura)
    nivel = acceso.level
    acceso.setLevel(logging.INFO)
    try:
        for ruta in rutas:
            acceso.info('%s - "%s %s HTTP/%s" %d', "172.18.0.1:5000", "GET", ruta, "1.1", 404)
    finally:
        acceso.removeHandler(captura)
        acceso.setLevel(nivel)
    return captura.lineas


def test_registro_de_acceso_no_repite_la_ruta_ni_el_nombre_pedidos(cliente_api):
    """RNF-07.24: el registro de acceso de uvicorn (lo que muestra `docker compose logs backend`) trae la URL completa;
    el valor de `ruta_archivo` y, en la ruta por tema y nombre, el tema y el nombre se ocultan (`***`), codificados o
    no. El método, la ruta del endpoint y el estado siguen apareciendo."""
    ruta = f"uploads/{PERSONA}/{PERSONA}.pdf"
    por_ruta = f"/archivos/download?ruta_archivo={quote(ruta, safe='')}"
    por_ruta_sin_codificar = f"/archivos/download?ruta_archivo={ruta}"
    por_tema = f"/archivos/expediente/{quote(PERSONA, safe='')}/archivo/{quote(PERSONA + '.pdf', safe='')}"
    por_tema_sin_codificar = f"/archivos/expediente/{PERSONA}/archivo/{PERSONA}.pdf"
    lineas = _lineas_de_acceso(por_ruta, por_ruta_sin_codificar, por_tema, por_tema_sin_codificar)

    assert len(lineas) == 4
    prohibidas = (*_PARTES_DE_LA_PERSONA, quote(PERSONA, safe=""), quote(ruta, safe=""), "uploads/PRUEBA", "%2F")
    for linea in lineas:
        assert not any(parte in linea for parte in prohibidas), linea
    assert all(linea.endswith('"GET %s HTTP/1.1" 404' % esperada) for linea, esperada in zip(lineas, (
        "/archivos/download?ruta_archivo=***", "/archivos/download?ruta_archivo=***",
        "/archivos/expediente/***/archivo/***", "/archivos/expediente/***/archivo/***"))), lineas


def test_registro_de_acceso_conserva_el_resto_de_las_rutas(cliente_api):
    """RNF-07.24 (sin enmascarar de más): otras rutas y otros parámetros de la misma consulta no se tocan."""
    rutas = ["/archivos/download?otro=1&ruta_archivo=uploads%2Fx%2Fy.pdf&mas=2", "/archivos/expediente/NB-5",
             "/notebooks?pagina=2", "/"]
    lineas = _lineas_de_acceso(*rutas)
    assert lineas[0].endswith('"GET /archivos/download?otro=1&ruta_archivo=***&mas=2 HTTP/1.1" 404'), lineas[0]
    assert [linea.split('"GET ')[1] for linea in lineas[1:]] == [f"{r} HTTP/1.1\" 404" for r in rutas[1:]]


# --- T3, RNF-07.23: un error inesperado da 500 genérico -----------------------------------------------------------

def test_error_inesperado_es_generico(cliente_api, sesion, usuario_gubernamental, carpeta_archivos, monkeypatch):
    """RNF-07.23 (por ruta y por tema y nombre): un error inesperado con una ruta del servidor inventada en su mensaje
    da 500 «Error interno del servidor» sin esa ruta, y la bitácora lo guarda como error interno, también sin ella."""
    from app.repositories.documento_repository import DocumentoRepository

    ruta_inventada = "/srv/PRUEBA_interna/PRUEBA_secreto.txt"
    _registrar_documento(TEMA_CON_FORMATO, DOCUMENTO)
    _crear_en_disco(carpeta_archivos, TEMA_CON_FORMATO, DOCUMENTO)

    def _falla(self, db, tema, nombre):
        raise RuntimeError(f"fallo leyendo {ruta_inventada}")

    monkeypatch.setattr(DocumentoRepository, "verificar_esta_procesado", _falla)

    respuestas = [
        _descargar(cliente_api, sesion, f"uploads/{TEMA_CON_FORMATO}/{DOCUMENTO}"),
        _por_tema(cliente_api, sesion, TEMA_CON_FORMATO, DOCUMENTO),
    ]

    for respuesta in respuestas:
        assert (respuesta.status_code, respuesta.json()) == (500, {"detail": "Error interno del servidor"})
        assert ruta_inventada not in respuesta.text and "PRUEBA_secreto" not in respuesta.text
    filas = _filas_de_descarga(usuario_gubernamental)
    assert len(filas) == 2
    for fila in filas:
        assert "PRUEBA_secreto" not in fila["texto"] + fila["info"]
        assert fila["datos"].get("tipo_error") == "interno"
