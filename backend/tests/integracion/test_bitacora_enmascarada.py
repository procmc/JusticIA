"""Pruebas de T5 (spec 003a): los correos no quedan en claro en los registros del servidor, pero sí en la bitácora (RNF-08.2).

Cubren el único punto de la bitácora (`BitacoraService.registrar`: la línea de INFO sale con el correo enmascarado
y la fila de la bitácora conserva el texto completo), el inicio de sesión de un usuario de prueba y el intento de
crear una cuenta con una cédula repetida (500: el mensaje de la base de datos lista los parámetros de la consulta,
entre ellos el correo, y no debe llegar a la salida ni a los registros).

Usan la base `servia_pruebas`; los usuarios son `PRUEBA` y el correo es siempre el simulado. Los registros se capturan
solo del paquete `app` (`caplog.set_level(..., logger="app")`): así no entra el registro de consultas de SQLAlchemy.
"""
import asyncio
import logging

import pytest
from sqlalchemy import text

from tests.soporte import rastros
from tests.soporte.nombres import PREFIJO_DATOS

CORREO_DE_LA_BITACORA = f"{PREFIJO_DATOS}.titular@prueba.invalid"
CORREO_ENMASCARADO = "P***@prueba.invalid"


def _consultar(consulta, parametros):
    from app.db.database import engine

    with engine.connect() as conexion:
        return [fila[0] for fila in conexion.execute(text(consulta), parametros).fetchall()]


# --- El punto único: BitacoraService.registrar ---------------------------------------------------------------------

def _registrar(administrador, texto, info_adicional=None):
    """Registra una acción de prueba con el servicio real y devuelve el identificador de la fila."""
    from app.constants.tipos_accion import TiposAccion
    from app.db.database import SessionLocal
    from app.services.bitacora.bitacora_service import bitacora_service

    with SessionLocal() as db:
        registro = asyncio.run(bitacora_service.registrar(
            db=db, usuario_id=administrador.cedula, tipo_accion_id=TiposAccion.LOGIN, texto=texto,
            info_adicional=info_adicional,
        ))
        return registro.CN_Id_bitacora


def test_registrar_enmascara_el_correo_en_el_registro_y_lo_conserva_completo_en_la_fila(administrador, caplog):
    """RNF-08.2: la línea de INFO trae `P***@prueba.invalid`; la fila de la bitácora conserva el texto y la información adicional completos."""
    caplog.set_level(logging.DEBUG, logger="app")
    texto = f"{PREFIJO_DATOS} Inicio de sesión exitoso: {CORREO_DE_LA_BITACORA}"

    identificador = _registrar(administrador, texto, {"email": CORREO_DE_LA_BITACORA})

    assert CORREO_ENMASCARADO in caplog.text
    rastros.buscar_en_rastros(CORREO_DE_LA_BITACORA, registros=caplog.text)
    fila = _consultar("SELECT CT_Texto FROM T_Bitacora WHERE CN_Id_bitacora = :i", {"i": identificador})
    adicional = _consultar("SELECT CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_bitacora = :i", {"i": identificador})
    assert fila == [texto]
    assert CORREO_DE_LA_BITACORA in adicional[0]


def test_registrar_no_altera_un_texto_sin_correo(administrador, caplog):
    """RNF-08.2: control; un texto sin correo se escribe tal cual en el registro y en la fila."""
    caplog.set_level(logging.DEBUG, logger="app")
    texto = f"{PREFIJO_DATOS} Consulta RAG: ¿Qué es la prescripción?"

    identificador = _registrar(administrador, texto)

    assert texto in caplog.text
    assert _consultar("SELECT CT_Texto FROM T_Bitacora WHERE CN_Id_bitacora = :i", {"i": identificador}) == [texto]


def test_registrar_enmascara_cada_correo_del_texto(administrador, caplog):
    """RNF-08.2: si el texto trae varios correos, todos salen enmascarados en el registro."""
    caplog.set_level(logging.DEBUG, logger="app")
    otro = f"{PREFIJO_DATOS}.otro@prueba.invalid"

    _registrar(administrador, f"{PREFIJO_DATOS} Reseteo de {CORREO_DE_LA_BITACORA} hecho por {otro}")

    rastros.buscar_en_rastros(CORREO_DE_LA_BITACORA, registros=caplog.text)
    rastros.buscar_en_rastros(otro, registros=caplog.text)
    assert caplog.text.count("***@prueba.invalid") == 2


# --- Inicio de sesión ------------------------------------------------------------------------------------------------------

def test_el_inicio_de_sesion_no_deja_el_correo_completo_en_el_registro(cliente_api, usuario_gubernamental, caplog, capfd):
    """RNF-08.2: iniciar sesión deja el registro en la bitácora con el correo completo, pero no en la salida ni en los registros del servidor."""
    caplog.set_level(logging.DEBUG, logger="app")

    respuesta = cliente_api.post(
        "/auth/login", json={"email": usuario_gubernamental.correo, "password": usuario_gubernamental.contrasena}
    )

    assert respuesta.status_code == 200
    filas = _consultar(
        "SELECT CT_Texto FROM T_Bitacora WHERE CN_Id_usuario = :c", {"c": usuario_gubernamental.cedula}
    )
    # Control positivo: la bitácora sí consigna el correo (la búsqueda no es vacía) y el flujo sí escribió en el registro.
    assert rastros.encontrar_en_rastros(usuario_gubernamental.correo, bitacora=filas) == ["bitacora"]
    assert "Bitácora registrada" in caplog.text
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(usuario_gubernamental.correo, salida=salida.out + salida.err, registros=caplog.text)


def test_un_inicio_de_sesion_fallido_tampoco_deja_el_correo_completo_en_el_registro(
        cliente_api, usuario_gubernamental, caplog, capfd):
    """RNF-08.2: el intento fallido (contraseña equivocada) también va a la bitácora con el correo y no al registro del servidor."""
    caplog.set_level(logging.DEBUG, logger="app")

    respuesta = cliente_api.post(
        "/auth/login", json={"email": usuario_gubernamental.correo, "password": f"{PREFIJO_DATOS}-contrasena-equivocada"}
    )

    assert respuesta.status_code == 401
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(usuario_gubernamental.correo, salida=salida.out + salida.err, registros=caplog.text)


# --- Crear una cuenta con una cédula repetida ---------------------------------------------------------------------------------

def test_crear_una_cedula_repetida_da_500_y_el_registro_no_contiene_el_correo_de_la_cuenta(
        cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, caplog, capfd):
    """RNF-08.2, RNF-08.1: la cédula repetida da 500 genérico; el error de la base de datos (que lista el correo y la clave de la
    consulta) no llega a la salida, a los registros ni a la respuesta, y no sale ningún correo."""
    caplog.set_level(logging.DEBUG, logger="app")
    cabeceras = iniciar_sesion(administrador)
    id_rol = _consultar("SELECT CN_Id_rol FROM T_Rol WHERE CT_Nombre_rol = :n", {"n": "Usuario Judicial"})[0]
    correo_de_la_cuenta = f"{PREFIJO_DATOS}.cuenta.repetida@prueba.invalid"

    respuesta = cliente_api.post("/usuarios/", headers=cabeceras, json={
        "cedula": usuario_gubernamental.cedula,  # ya existe: la base rechaza la inserción
        "nombre_usuario": f"{PREFIJO_DATOS}_cuenta_repetida", "nombre": PREFIJO_DATOS, "apellido_uno": "Peña",
        "apellido_dos": "Núñez", "correo": correo_de_la_cuenta, "id_rol": id_rol,
    })

    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "Error interno del servidor"}
    assert correo_simulado.intentos == []
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(
        correo_de_la_cuenta, salida=salida.out + salida.err, registros=caplog.text, respuestas=respuesta.text
    )


# --- El error de la bitácora (T6, decisión de Andrés del 07/10/2026) -----------------------------------------------------------------------

def test_si_falla_el_registro_el_error_del_servidor_sale_con_el_correo_enmascarado(monkeypatch, caplog, capfd):
    """RNF-08.2 (regresión): si el INSERT falla, el texto del error puede traer los parámetros de la consulta (entre ellos un
    correo). La línea de ERROR de `BitacoraService.registrar` lo escribe enmascarado, y el fallo sigue llegando al llamador."""
    from app.constants.tipos_accion import TiposAccion
    from app.services.bitacora.bitacora_service import bitacora_service

    def _insert_que_falla(**argumentos):
        raise RuntimeError(f"INSERT fallido, parámetros: ('{CORREO_DE_LA_BITACORA}', 'PRUEBA')")

    monkeypatch.setattr(bitacora_service.repo, "crear", _insert_que_falla)
    caplog.set_level(logging.DEBUG, logger="app")
    capfd.readouterr()

    with pytest.raises(Exception, match="Error al registrar en bitácora"):
        asyncio.run(bitacora_service.registrar(
            db=None, usuario_id=None, tipo_accion_id=TiposAccion.LOGIN, texto=f"{PREFIJO_DATOS} acción de prueba",
        ))

    assert "Error registrando en bitácora" in caplog.text and CORREO_ENMASCARADO in caplog.text
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(CORREO_DE_LA_BITACORA, salida=salida.out + salida.err, registros=caplog.text)
