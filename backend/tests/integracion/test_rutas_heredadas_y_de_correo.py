"""Pruebas de T3 (spec 003a): la ruta heredada ya no existe y las rutas de correo exigen Administrador.

Cubren RNF-07.1 (el restablecimiento heredado `POST /auth/restablecer-contrasenna` responde 404 con cualquier credencial
o sin ella, sin cambiar ninguna contraseña) y RNF-07.2 (`POST /email/test-email` y `GET /email/email-config`: 401 sin token,
403 con Usuario Gubernamental y funcionan con Administrador; la configuración no devuelve la contraseña de la cuenta de
correo y ninguna ruta de correo devuelve al navegador el texto de una excepción). RF-03.13 («una sola lógica» de
restablecimiento) queda comprobado en lo que toca a esta ruta: ya no hay un segundo camino.

Usan la base `servia_pruebas` y el correo simulado (`correo_simulado`): ningún envío sale de la prueba. Los usuarios son
`PRUEBA` y sus contraseñas las genera la suite; el texto de «servidor» y de «excepción» que se busca en las respuestas es
inventado.
"""
import logging

import aiosmtplib
import pytest
from sqlalchemy import text

from tests.soporte import datos
from tests.soporte.nombres import PREFIJO_DATOS

RUTA_HEREDADA = "/auth/restablecer-contrasenna"
DESTINO_DE_PRUEBA = "prueba.destino@prueba.invalid"
# Texto inventado que haría de «respuesta del servidor de correo» o de «mensaje de una excepción interna».
TEXTO_DEL_SERVIDOR = f"{PREFIJO_DATOS}-535 texto-del-servidor-de-correo-inventado.invalid"
TEXTO_DE_LA_EXCEPCION = f"{PREFIJO_DATOS} detalle-interno-inventado-de-la-excepcion"
CLAVES_DE_LA_CONFIGURACION = {"provider", "username", "host", "port", "configured"}


def _cuerpo_de_prueba_de_correo(contrasena):
    return {"email": DESTINO_DE_PRUEBA, "password": str(contrasena), "nombre_usuario": f"{PREFIJO_DATOS} Peña Núñez"}


def _hash_guardado(cedula):
    from app.db.database import engine

    with engine.connect() as conexion:
        return conexion.execute(
            text("SELECT CT_Contrasenna FROM T_Usuario WHERE CN_Id_usuario = :c"), {"c": cedula}
        ).scalar()


def _llamar(cliente_api, metodo, ruta, cabeceras, cuerpo=None):
    argumentos = {"json": cuerpo} if cuerpo is not None else {}
    return cliente_api.request(metodo, ruta, headers=cabeceras, **argumentos)


# --- RNF-07.1: la ruta heredada ya no existe ------------------------------------------------------------------------------

@pytest.mark.parametrize("quien", [
    pytest.param("sin_token", id="sin-token"),
    pytest.param("usuario_gubernamental", id="usuario-gubernamental"),
    pytest.param("administrador", id="administrador"),
])
def test_el_restablecimiento_heredado_responde_404_con_cualquier_credencial_y_no_cambia_ninguna_contrasena(
    cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, quien
):
    """RNF-07.1, RF-03.13: `POST /auth/restablecer-contrasenna` responde 404 igual que una ruta inexistente, sin token, con
    token de Usuario Gubernamental y con token de Administrador; ninguna contraseña guardada cambia y no sale ningún correo."""
    cabeceras = {} if quien == "sin_token" else iniciar_sesion(
        {"usuario_gubernamental": usuario_gubernamental, "administrador": administrador}[quien]
    )
    antes = {u.cedula: _hash_guardado(u.cedula) for u in (administrador, usuario_gubernamental)}

    respuesta = _llamar(cliente_api, "POST", RUTA_HEREDADA, cabeceras, {"cedula": usuario_gubernamental.cedula})
    inexistente = _llamar(cliente_api, "POST", "/auth/ruta-que-no-existe-prueba", cabeceras, {"cedula": usuario_gubernamental.cedula})

    assert respuesta.status_code == 404
    assert respuesta.json() == inexistente.json()  # no se distingue de una ruta que nunca existió
    assert {u.cedula: _hash_guardado(u.cedula) for u in (administrador, usuario_gubernamental)} == antes
    assert correo_simulado.intentos == []


def test_la_contrasena_del_usuario_sigue_sirviendo_tras_llamar_a_la_ruta_heredada(
    cliente_api, correo_simulado, usuario_gubernamental
):
    """RNF-07.1: control de la prueba anterior, a nivel de lo que ve el usuario: tras la llamada sin sesión, su contraseña
    sigue iniciando sesión y no se le obliga a cambiarla."""
    _llamar(cliente_api, "POST", RUTA_HEREDADA, {}, {"cedula": usuario_gubernamental.cedula})

    respuesta = cliente_api.post(
        "/auth/login", json={"email": usuario_gubernamental.correo, "password": usuario_gubernamental.contrasena}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["user"]["requiere_cambio_password"] is False


def test_openapi_no_lista_la_ruta_heredada(cliente_api):
    """RNF-07.1: la ruta tampoco aparece en la descripción pública de la API (con un control: las demás rutas de
    autenticación sí aparecen, así que la lista no está vacía)."""
    rutas = cliente_api.get("/openapi.json").json()["paths"]

    assert "/auth/login" in rutas
    assert RUTA_HEREDADA not in rutas


# --- RNF-07.2: las rutas de correo exigen Administrador --------------------------------------------------------------------

@pytest.mark.parametrize("metodo, ruta, con_cuerpo", [
    pytest.param("POST", "/email/test-email", True, id="test-email"),
    pytest.param("GET", "/email/email-config", False, id="email-config"),
])
class TestRutasDeCorreoExigenAdministrador:
    def _cuerpo(self, con_cuerpo):
        return _cuerpo_de_prueba_de_correo(datos.generar_contrasena()) if con_cuerpo else None

    def test_sin_token_responde_401_y_no_envia_nada(self, cliente_api, correo_simulado, metodo, ruta, con_cuerpo):
        """RNF-07.2: sin token, 401 «Token requerido»; el correo de prueba no sale."""
        respuesta = _llamar(cliente_api, metodo, ruta, {}, self._cuerpo(con_cuerpo))

        assert respuesta.status_code == 401
        assert respuesta.json()["detail"] == "Token requerido"
        assert correo_simulado.intentos == []

    def test_el_usuario_gubernamental_recibe_403_y_no_envia_nada(
        self, cliente_api, iniciar_sesion, correo_simulado, usuario_gubernamental, metodo, ruta, con_cuerpo
    ):
        """RNF-07.2: con token de Usuario Gubernamental, 403; el correo de prueba no sale."""
        respuesta = _llamar(
            cliente_api, metodo, ruta, iniciar_sesion(usuario_gubernamental), self._cuerpo(con_cuerpo)
        )

        assert respuesta.status_code == 403
        assert correo_simulado.intentos == []

    def test_el_administrador_si_puede(
        self, cliente_api, iniciar_sesion, correo_simulado, administrador, metodo, ruta, con_cuerpo
    ):
        """RNF-07.2: con token de Administrador la ruta funciona (200)."""
        respuesta = _llamar(cliente_api, metodo, ruta, iniciar_sesion(administrador), self._cuerpo(con_cuerpo))

        assert respuesta.status_code == 200


def test_el_envio_de_prueba_del_administrador_queda_en_el_correo_simulado(
    cliente_api, iniciar_sesion, correo_simulado, administrador
):
    """RNF-07.2: con Administrador, `POST /email/test-email` responde con el contrato de siempre (`success` y `message`),
    el envío llega al simulado con el destino pedido y la contraseña de la solicitud no vuelve en la respuesta."""
    contrasena = datos.generar_contrasena()

    respuesta = cliente_api.post(
        "/email/test-email", headers=iniciar_sesion(administrador), json=_cuerpo_de_prueba_de_correo(contrasena)
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"success", "message"}
    assert cuerpo["success"] is True
    assert DESTINO_DE_PRUEBA in cuerpo["message"]
    assert contrasena not in respuesta.text
    assert [intento["a"] for intento in correo_simulado.intentos] == [DESTINO_DE_PRUEBA]


def test_la_configuracion_trae_solo_los_cinco_datos_y_no_la_contrasena_del_correo(
    cliente_api, iniciar_sesion, correo_simulado, administrador
):
    """RNF-07.2: `GET /email/email-config` devuelve solo `provider`, `username`, `host`, `port` y `configured`; ni la
    contraseña de la cuenta de correo (la que fija la suite) aparece en la respuesta."""
    import os

    respuesta = cliente_api.get("/email/email-config", headers=iniciar_sesion(administrador))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == CLAVES_DE_LA_CONFIGURACION
    assert cuerpo["configured"] is True
    assert cuerpo["host"] == os.environ["EMAIL_HOST"]
    assert os.environ["EMAIL_PASSWORD"] not in respuesta.text


def test_si_el_envio_falla_la_respuesta_no_trae_el_texto_del_servidor(
    cliente_api, iniciar_sesion, correo_simulado, administrador
):
    """RNF-07.2, RF-03.17: con el simulado en fallo, cuya excepción lleva un texto de servidor, la respuesta informa el fallo
    con el contrato de siempre y no contiene ese texto."""
    correo_simulado.fallar(aiosmtplib.SMTPConnectError(TEXTO_DEL_SERVIDOR))

    respuesta = cliente_api.post(
        "/email/test-email", headers=iniciar_sesion(administrador), json=_cuerpo_de_prueba_de_correo(datos.generar_contrasena())
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"success": False, "message": "Error al enviar el correo"}
    assert TEXTO_DEL_SERVIDOR not in respuesta.text
    assert len(correo_simulado.intentos) == 1  # el intento sí se hizo: es el fallo lo que se oculta


def test_una_excepcion_inesperada_del_envio_da_500_generico_y_queda_en_el_registro(
    cliente_api, iniciar_sesion, correo_simulado, administrador, monkeypatch, caplog
):
    """RNF-07.2: si `EmailService.send_password_email` lanza una excepción inesperada, 500 con «Error interno del servidor»
    sin el texto de la excepción; el detalle va al registro del servidor con su traza (`logger.exception`)."""
    from app.email import EmailService

    async def _lanza(self, *args, **kwargs):
        raise RuntimeError(TEXTO_DE_LA_EXCEPCION)

    monkeypatch.setattr(EmailService, "send_password_email", _lanza)
    cabeceras = iniciar_sesion(administrador)
    caplog.set_level(logging.ERROR)

    respuesta = cliente_api.post(
        "/email/test-email", headers=cabeceras, json=_cuerpo_de_prueba_de_correo(datos.generar_contrasena())
    )

    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "Error interno del servidor"}
    assert TEXTO_DE_LA_EXCEPCION not in respuesta.text
    registros = [r for r in caplog.records if r.name == "app.routes.email" and r.exc_info]
    assert len(registros) == 1 and registros[0].exc_info[0] is RuntimeError


def test_una_excepcion_inesperada_al_leer_la_configuracion_da_500_generico(
    cliente_api, iniciar_sesion, correo_simulado, administrador, monkeypatch, caplog
):
    """RNF-07.2: lo mismo en `GET /email/email-config`: 500 genérico, sin el texto de la excepción, y la traza en el registro."""
    from app.routes import email as rutas_de_correo

    def _lanza(*args, **kwargs):
        raise RuntimeError(TEXTO_DE_LA_EXCEPCION)

    monkeypatch.setattr(rutas_de_correo, "ConfiguracionCorreoRespuesta", _lanza)
    cabeceras = iniciar_sesion(administrador)
    caplog.set_level(logging.ERROR)

    respuesta = cliente_api.get("/email/email-config", headers=cabeceras)

    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "Error interno del servidor"}
    assert TEXTO_DE_LA_EXCEPCION not in respuesta.text
    assert [r for r in caplog.records if r.name == "app.routes.email" and r.exc_info]
