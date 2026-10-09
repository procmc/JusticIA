"""Pruebas de T6 (spec 003a): el restablecimiento de la contraseña por el Administrador (RF-03.13, RF-03.14, RF-21.4, RF-21.6, RNF-08.1).

`POST /usuarios/{id}/resetear-contrasenna` guarda una contraseña temporal sin confirmar, la envía por correo y solo si el
servidor de correo la aceptó confirma el cambio; si el envío falla, la contraseña y el último acceso del usuario NO cambian y
la respuesta es un 502 con el texto de la spec (nunca 401 ni 403: la interfaz cerraría la sesión del Administrador).
El intento queda en la bitácora con el resultado de la notificación (también el fallido, antes del 502), sin la temporal.

Usan la base `servia_pruebas` y el correo simulado: ningún correo sale de la prueba. Los usuarios son `PRUEBA`; la contraseña
temporal la genera el sistema y la prueba la lee del contenido real del correo simulado (nunca se imprime).
"""
import asyncio
import json
import logging

import aiosmtplib
import pytest
from sqlalchemy import text

from tests.soporte import rastros
from tests.soporte.nombres import PREFIJO_DATOS

MENSAJE_EXITOSO = "Contraseña reseteada exitosamente"
TEXTO_DEL_SERVIDOR = f"{PREFIJO_DATOS}-535 detalle-del-servidor-inventado clave=PRUEBA-clave-4417"
TEXTO_DE_LA_EXCEPCION = f"{PREFIJO_DATOS} detalle-interno-inventado prueba.error@prueba.invalid"
ID_EDITAR_USUARIO = 8  # TiposAccion.EDITAR_USUARIO


def _mensaje_fallido(correo):
    return (
        f"No se pudo enviar el correo a {correo}. La contraseña no fue modificada. "
        "Verifique el servicio de correo e inténtelo de nuevo."
    )


def _consultar(consulta, parametros):
    from app.db.database import engine

    with engine.connect() as conexion:
        return conexion.execute(text(consulta), parametros).fetchall()


def _fila(cedula):
    """Lo que la base tiene del usuario: hash, último acceso y estado."""
    return _consultar(
        "SELECT CT_Contrasenna, CF_Ultimo_acceso, CN_Id_estado FROM T_Usuario WHERE CN_Id_usuario = :c", {"c": cedula}
    )[0]


def _resetear(cliente_api, cabeceras, cedula):
    return cliente_api.post(f"/usuarios/{cedula}/resetear-contrasenna", headers=cabeceras)


def _iniciar_sesion(cliente_api, correo, contrasena):
    return cliente_api.post("/auth/login", json={"email": correo, "password": str(contrasena)})


def _temporal_enviada(correo_simulado):
    """La contraseña temporal que llevó el último correo (envuelta en `Contrasena`: su `repr` no la muestra)."""
    return rastros.valor_tras(correo_simulado.contenido_real().texto, "Tu nueva contraseña temporal es:")


def _registros_del_reseteo(cedula_administrador, cedula_reseteada):
    """Las filas de la bitácora del reseteo de esa cuenta: (tipo de acción, texto, información adicional ya leída)."""
    filas = _consultar(
        "SELECT CN_Id_tipo_accion, CT_Texto, CT_Informacion_adicional FROM T_Bitacora "
        "WHERE CN_Id_usuario = :c AND CT_Informacion_adicional LIKE :marca ORDER BY CN_Id_bitacora",
        {"c": cedula_administrador, "marca": '%"reseteo_contrasena"%'},
    )
    registros = [(tipo, texto, json.loads(adicional)) for tipo, texto, adicional in filas]
    return [r for r in registros if r[2].get("usuario_reseteado_id") == cedula_reseteada]


def _todas_las_filas_de_bitacora(*cedulas):
    """Texto e información adicional de toda la bitácora de esas cuentas (para buscar un secreto)."""
    filas = []
    for cedula in cedulas:
        filas += _consultar(
            "SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_usuario = :c", {"c": cedula}
        )
    return [list(fila) for fila in filas]


# --- RF-03.13: el reseteo con el correo funcionando -------------------------------------------------------------------------------

def test_el_reseteo_exitoso_cambia_la_contrasena_y_envia_la_temporal_al_correo_del_usuario(
    cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental
):
    """RF-03.13: 200 con el texto exacto; la contraseña guardada es un hash bcrypt de la temporal (no la temporal); el último
    acceso queda vacío; el correo va al correo del usuario y lleva la temporal."""
    from app.repositories.usuario_repository import UsuarioRepository

    hash_anterior = _fila(usuario_gubernamental.cedula).CT_Contrasenna

    respuesta = _resetear(cliente_api, iniciar_sesion(administrador), usuario_gubernamental.cedula)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"mensaje": MENSAJE_EXITOSO}
    assert [intento["a"] for intento in correo_simulado.intentos] == [usuario_gubernamental.correo]
    temporal = _temporal_enviada(correo_simulado)
    fila = _fila(usuario_gubernamental.cedula)
    assert len(temporal) == 8 and temporal.isalnum()
    assert fila.CT_Contrasenna != hash_anterior
    assert fila.CT_Contrasenna != temporal and temporal not in fila.CT_Contrasenna
    assert UsuarioRepository().pwd_context.verify(str(temporal), fila.CT_Contrasenna)
    assert fila.CF_Ultimo_acceso is None


def test_con_la_temporal_se_inicia_sesion_y_obliga_a_cambiar_la_contrasena_y_la_anterior_ya_no_sirve(
    cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental
):
    """RF-03.13: un inicio de sesión con la temporal funciona y pide cambiar la contraseña; la anterior queda inválida."""
    _resetear(cliente_api, iniciar_sesion(administrador), usuario_gubernamental.cedula)
    temporal = _temporal_enviada(correo_simulado)

    con_la_temporal = _iniciar_sesion(cliente_api, usuario_gubernamental.correo, temporal)
    con_la_anterior = _iniciar_sesion(cliente_api, usuario_gubernamental.correo, usuario_gubernamental.contrasena)

    assert con_la_temporal.status_code == 200
    assert con_la_temporal.json()["user"]["requiere_cambio_password"] is True
    assert con_la_anterior.status_code == 401


def test_un_usuario_inexistente_responde_404_sin_enviar_nada(cliente_api, iniciar_sesion, correo_simulado, administrador):
    """RF-03.13: una cédula que no existe responde 404 «Usuario no encontrado» y no sale ningún correo."""
    respuesta = _resetear(cliente_api, iniciar_sesion(administrador), f"{PREFIJO_DATOS}999999")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Usuario no encontrado"}
    assert correo_simulado.intentos == []


def test_sin_token_responde_401_y_no_cambia_nada(cliente_api, correo_simulado, usuario_gubernamental):
    """RF-03.13, RNF-07: sin token, 401; ni el correo sale ni la contraseña cambia."""
    antes = _fila(usuario_gubernamental.cedula)

    respuesta = _resetear(cliente_api, {}, usuario_gubernamental.cedula)

    assert respuesta.status_code == 401
    assert correo_simulado.intentos == []
    assert _fila(usuario_gubernamental.cedula) == antes


def test_el_usuario_gubernamental_recibe_403_y_no_cambia_nada(cliente_api, iniciar_sesion, correo_simulado, usuario_gubernamental):
    """RF-03.13, RNF-07: un Usuario Gubernamental no puede restablecer ni su propia contraseña por esta ruta: 403."""
    cabeceras = iniciar_sesion(usuario_gubernamental)  # iniciar sesión actualiza el último acceso: la foto se toma después
    antes = _fila(usuario_gubernamental.cedula)

    respuesta = _resetear(cliente_api, cabeceras, usuario_gubernamental.cedula)

    assert respuesta.status_code == 403
    assert correo_simulado.intentos == []
    assert _fila(usuario_gubernamental.cedula) == antes


def test_una_cuenta_inactiva_se_restablece_y_conserva_su_estado(
    cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental
):
    """RF-03.13 (caso límite): restablecer la contraseña de una cuenta Inactiva se permite; el estado no cambia y la cuenta
    sigue sin poder iniciar sesión."""
    from app.db.database import engine

    with engine.begin() as conexion:
        conexion.execute(
            text("UPDATE T_Usuario SET CN_Id_estado = (SELECT CN_Id_estado FROM T_Estado WHERE CT_Nombre_estado = 'Inactivo') "
                 "WHERE CN_Id_usuario = :c"),
            {"c": usuario_gubernamental.cedula},
        )
    antes = _fila(usuario_gubernamental.cedula)

    respuesta = _resetear(cliente_api, iniciar_sesion(administrador), usuario_gubernamental.cedula)

    despues = _fila(usuario_gubernamental.cedula)
    assert respuesta.status_code == 200 and respuesta.json() == {"mensaje": MENSAJE_EXITOSO}
    assert despues.CN_Id_estado == antes.CN_Id_estado
    assert despues.CT_Contrasenna != antes.CT_Contrasenna and despues.CF_Ultimo_acceso is None
    assert _iniciar_sesion(cliente_api, usuario_gubernamental.correo, _temporal_enviada(correo_simulado)).status_code == 401


# --- RF-03.14: el envío falla --------------------------------------------------------------------------------------------------------

ESCENARIOS_DE_FALLO = ["servidor_en_fallo", "cuenta_sin_configurar", "sin_servicio_de_correo"]


@pytest.fixture
def fallo_del_correo(correo_simulado, monkeypatch):
    """Devuelve `(provocar, restaurar)` para un escenario: `provocar()` rompe el envío y `restaurar()` lo deja funcionando."""
    from app.routes.usuarios import usuario_service

    def _preparar(escenario):
        servicio, configuracion = usuario_service.email_service, usuario_service.email_service.config
        contrasena_de_la_cuenta = configuracion.password
        if escenario == "servidor_en_fallo":
            return (lambda: correo_simulado.fallar(aiosmtplib.SMTPResponseException(535, TEXTO_DEL_SERVIDOR)),
                    correo_simulado.responder_bien)
        if escenario == "cuenta_sin_configurar":
            return (lambda: monkeypatch.setattr(configuracion, "password", ""),
                    lambda: monkeypatch.setattr(configuracion, "password", contrasena_de_la_cuenta))
        return (lambda: monkeypatch.setattr(usuario_service, "email_service", None),
                lambda: monkeypatch.setattr(usuario_service, "email_service", servicio))

    return _preparar


@pytest.mark.parametrize("escenario", ESCENARIOS_DE_FALLO)
def test_si_el_envio_falla_responde_502_con_el_texto_de_la_spec_y_no_cambia_la_contrasena(
    escenario, cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, fallo_del_correo
):
    """RF-03.14 (regresión): con el servidor de correo en fallo, la cuenta de correo sin configurar o sin servicio de correo,
    502 con el texto exacto y el correo del usuario; el hash y el último acceso son los de antes y la contraseña anterior
    sigue iniciando sesión. Nunca 401 ni 403 (cerraría la sesión del Administrador)."""
    provocar, _ = fallo_del_correo(escenario)
    provocar()
    cabeceras = iniciar_sesion(administrador)
    antes = _fila(usuario_gubernamental.cedula)

    respuesta = _resetear(cliente_api, cabeceras, usuario_gubernamental.cedula)

    assert respuesta.status_code == 502
    assert respuesta.json() == {"detail": _mensaje_fallido(usuario_gubernamental.correo)}
    assert TEXTO_DEL_SERVIDOR not in respuesta.text
    assert _fila(usuario_gubernamental.cedula) == antes
    assert _iniciar_sesion(cliente_api, usuario_gubernamental.correo, usuario_gubernamental.contrasena).status_code == 200
    assert len(correo_simulado.intentos) == (1 if escenario == "servidor_en_fallo" else 0)


@pytest.mark.parametrize("escenario", ESCENARIOS_DE_FALLO)
def test_tras_un_fallo_el_reintento_con_el_correo_funcionando_cambia_la_contrasena(
    escenario, cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, fallo_del_correo
):
    """RF-03.14: el Administrador puede reintentar: con el correo ya funcionando, el segundo intento responde 200 y cambia la contraseña."""
    provocar, restaurar = fallo_del_correo(escenario)
    provocar()
    cabeceras = iniciar_sesion(administrador)
    antes = _fila(usuario_gubernamental.cedula)
    assert _resetear(cliente_api, cabeceras, usuario_gubernamental.cedula).status_code == 502

    restaurar()
    respuesta = _resetear(cliente_api, cabeceras, usuario_gubernamental.cedula)

    despues = _fila(usuario_gubernamental.cedula)
    assert respuesta.status_code == 200 and respuesta.json() == {"mensaje": MENSAJE_EXITOSO}
    assert despues.CT_Contrasenna != antes.CT_Contrasenna and despues.CF_Ultimo_acceso is None
    assert _iniciar_sesion(cliente_api, usuario_gubernamental.correo, _temporal_enviada(correo_simulado)).status_code == 200


def test_con_un_servidor_que_no_responde_el_reseteo_termina_no_entregado_a_los_15_s_y_no_cambia_nada(
    correo_simulado, reloj_controlable, usuario_gubernamental, monkeypatch
):
    """RF-03.14, RF-03.16: con `no_responde()` y el reloj controlable, el servicio real y la base real: sigue pendiente a los
    14,9 s, termina «no entregada» a los 15 s y la base queda igual. Se llama al servicio dentro de `asyncio.run` porque
    `TestClient` corre la aplicación en otro hilo y bucle y la prueba no podría adelantar el reloj mientras la petición está en curso."""
    from app.db.database import SessionLocal
    from app.routes.usuarios import usuario_service

    monkeypatch.setattr(usuario_service.email_service.config, "timeout", 15.0)
    correo_simulado.no_responde()
    antes = _fila(usuario_gubernamental.cedula)

    async def _escenario():
        with SessionLocal() as db:
            tarea = asyncio.ensure_future(usuario_service.resetear_contrasenna_usuario(db, usuario_gubernamental.cedula))
            await reloj_controlable.avanzar(14.9)
            seguia_pendiente = not tarea.done()
            await reloj_controlable.avanzar(0.1)
            assert tarea.done(), "el envío debía darse por fallido a los 15 s"
            return seguia_pendiente, tarea.result()

    seguia_pendiente, resultado = asyncio.run(_escenario())

    assert seguia_pendiente is True
    assert resultado.entregada is False
    assert resultado.mensaje == _mensaje_fallido(usuario_gubernamental.correo)
    assert correo_simulado.tiempos_maximos == [15.0]
    assert _fila(usuario_gubernamental.cedula) == antes


def test_si_falla_la_confirmacion_responde_500_y_queda_la_contrasena_anterior(
    cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, monkeypatch
):
    """RF-03.14: el correo salió pero el commit falló: 500 genérico (no un éxito) y la base conserva la contraseña anterior."""
    from app.routes.usuarios import usuario_service

    def _commit_que_falla(db):
        db.rollback()
        raise RuntimeError(TEXTO_DE_LA_EXCEPCION)

    monkeypatch.setattr(usuario_service.repository, "confirmar_cambios", _commit_que_falla)
    cabeceras = iniciar_sesion(administrador)
    antes = _fila(usuario_gubernamental.cedula)

    respuesta = _resetear(cliente_api, cabeceras, usuario_gubernamental.cedula)

    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "Error interno del servidor"}
    assert TEXTO_DE_LA_EXCEPCION not in respuesta.text
    assert _fila(usuario_gubernamental.cedula) == antes


# --- Corrección del 08/10: el correo salió pero el guardado falló (caso límite de la spec) -----------------------------------------

def _hacer_que_falle_la_confirmacion(monkeypatch):
    """El `commit` del reseteo falla (después de que el correo salió): se revierte y se relanza, como el repositorio real."""
    from app.routes.usuarios import usuario_service

    def _commit_que_falla(db):
        db.rollback()
        raise RuntimeError(TEXTO_DE_LA_EXCEPCION)

    monkeypatch.setattr(usuario_service.repository, "confirmar_cambios", _commit_que_falla)


def test_si_el_correo_sale_pero_falla_el_guardado_el_intento_queda_en_la_bitacora_sin_secretos(
    cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, monkeypatch, caplog, capfd
):
    """RF-21.4, RF-03.14 (regresión): con el correo entregado y el `commit` fallando, además del 500 y de la contraseña
    anterior queda UNA fila en la bitácora (tipo y usuario como los demás registros del reseteo) que dice que el correo se
    entregó y que la contraseña NO se guardó, con `notificacion_correo` «entregada» y el indicador `contrasenna_guardada`
    en falso. Ni la temporal ni el correo completo del usuario quedan en la salida ni en los registros del servidor, y el
    texto de la excepción tampoco (solo su tipo). Control positivo: la temporal y el correo sí estaban en el mensaje armado."""
    _hacer_que_falle_la_confirmacion(monkeypatch)
    cabeceras = iniciar_sesion(administrador)
    caplog.set_level(logging.DEBUG, logger="app")
    capfd.readouterr()
    antes = _fila(usuario_gubernamental.cedula)

    respuesta = _resetear(cliente_api, cabeceras, usuario_gubernamental.cedula)

    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "Error interno del servidor"}
    assert _fila(usuario_gubernamental.cedula) == antes
    registros = _registros_del_reseteo(administrador.cedula, usuario_gubernamental.cedula)
    assert len(registros) == 1
    tipo, texto_registrado, adicional = registros[0]
    assert tipo == ID_EDITAR_USUARIO
    assert texto_registrado == (
        f"Intento de reseteo de contraseña de usuario: {usuario_gubernamental.cedula} - "
        "notificación por correo: entregada; la contraseña no se guardó"
    )
    assert adicional["usuario_reseteado_id"] == usuario_gubernamental.cedula
    assert adicional["notificacion_correo"] == "entregada"
    assert adicional["contrasenna_guardada"] is False
    # Rastros: control positivo y búsqueda
    contenido = correo_simulado.contenido_real()
    temporal = _temporal_enviada(correo_simulado)
    assert rastros.encontrar_en_rastros(temporal, correo=[contenido.texto, contenido.html]) == ["correo"]
    assert rastros.encontrar_en_rastros(usuario_gubernamental.correo, correo=[contenido.a]) == ["correo"]
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(
        temporal,
        salida=salida.out + salida.err,
        registros=caplog.text,
        bitacora=_todas_las_filas_de_bitacora(administrador.cedula, usuario_gubernamental.cedula),
        respuestas=respuesta.text,
    )
    rastros.buscar_en_rastros(usuario_gubernamental.correo, salida=salida.out + salida.err, registros=caplog.text)
    rastros.buscar_en_rastros(
        TEXTO_DE_LA_EXCEPCION, salida=salida.out + salida.err, registros=caplog.text, respuestas=respuesta.text
    )
    assert "RuntimeError" in caplog.text  # solo el tipo de la excepción queda en el registro del servidor


def test_si_el_correo_sale_pero_falla_el_guardado_y_tambien_la_bitacora_la_respuesta_sigue_siendo_500(
    cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, monkeypatch
):
    """RF-21.4 (RF-21: si falla el registro, la acción continúa): con el guardado fallando y la bitácora sin responder, la
    respuesta es el mismo 500 genérico, la contraseña anterior se conserva y no queda ninguna fila del intento."""
    from app.services.bitacora.usuarios_audit_service import usuarios_audit_service

    async def _falla(**argumentos):
        raise Exception("PRUEBA la bitácora no responde")

    _hacer_que_falle_la_confirmacion(monkeypatch)
    monkeypatch.setattr(usuarios_audit_service.bitacora_service, "registrar", _falla)
    cabeceras = iniciar_sesion(administrador)
    antes = _fila(usuario_gubernamental.cedula)

    respuesta = _resetear(cliente_api, cabeceras, usuario_gubernamental.cedula)

    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "Error interno del servidor"}
    assert _fila(usuario_gubernamental.cedula) == antes
    assert _registros_del_reseteo(administrador.cedula, usuario_gubernamental.cedula) == []


@pytest.mark.parametrize("entregado", [True, False], ids=["entregada", "no-entregada"])
def test_los_demas_casos_del_reseteo_no_ganan_el_indicador_de_contrasena_no_guardada(
    entregado, cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental
):
    """RF-21.4 (caracterización): el éxito y el fallo del envío siguen registrándose como antes, sin el indicador nuevo
    (solo lo lleva el intento cuyo correo salió y cuya contraseña no se guardó)."""
    if not entregado:
        correo_simulado.fallar(aiosmtplib.SMTPConnectError(TEXTO_DEL_SERVIDOR))

    _resetear(cliente_api, iniciar_sesion(administrador), usuario_gubernamental.cedula)

    registros = _registros_del_reseteo(administrador.cedula, usuario_gubernamental.cedula)
    assert len(registros) == 1
    assert "contrasenna_guardada" not in registros[0][2]
    assert "no se guardó" not in registros[0][1]


# --- RNF-08.2: un error inesperado no escribe su texto ni su traza ---------------------------------------------------------------

def test_un_error_inesperado_da_500_y_no_deja_su_texto_ni_la_traza_en_la_salida_ni_en_los_registros(
    cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, monkeypatch, caplog, capfd
):
    """RNF-08.2 (regresión): ante una excepción inesperada, la respuesta es el 500 genérico y la salida y los registros solo
    traen el tipo de la excepción: ni su texto (que puede traer el correo de la cuenta) ni la traza ni un `print`."""
    from app.routes.usuarios import usuario_service

    async def _lanza(db, usuario_id):
        raise RuntimeError(TEXTO_DE_LA_EXCEPCION)

    monkeypatch.setattr(usuario_service, "resetear_contrasenna_usuario", _lanza)
    cabeceras = iniciar_sesion(administrador)
    caplog.set_level(logging.DEBUG, logger="app")
    capfd.readouterr()

    respuesta = _resetear(cliente_api, cabeceras, usuario_gubernamental.cedula)

    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "Error interno del servidor"}
    salida = capfd.readouterr()
    assert "RuntimeError" in caplog.text  # control positivo: el error sí se registró, solo su tipo
    for secreto in (TEXTO_DE_LA_EXCEPCION, "prueba.error@prueba.invalid"):
        rastros.buscar_en_rastros(secreto, salida=salida.out + salida.err, registros=caplog.text, respuestas=respuesta.text)
    assert "Traceback" not in salida.out + salida.err + caplog.text


# --- RF-21.4 y RF-21.6: la bitácora ---------------------------------------------------------------------------------------------------

def test_el_reseteo_exitoso_queda_en_la_bitacora_con_el_resultado_de_la_notificacion(
    cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental
):
    """RF-21.4: un registro con el administrador, la cédula de la cuenta y `notificacion_correo` = «entregada»; sin la temporal."""
    _resetear(cliente_api, iniciar_sesion(administrador), usuario_gubernamental.cedula)

    registros = _registros_del_reseteo(administrador.cedula, usuario_gubernamental.cedula)

    assert len(registros) == 1
    tipo, texto_registrado, adicional = registros[0]
    assert tipo == ID_EDITAR_USUARIO
    assert usuario_gubernamental.cedula in texto_registrado and "Intento" not in texto_registrado
    assert adicional["notificacion_correo"] == "entregada"
    assert adicional["usuario_reseteado_id"] == usuario_gubernamental.cedula


@pytest.mark.parametrize("escenario", ESCENARIOS_DE_FALLO)
def test_el_intento_fallido_tambien_queda_en_la_bitacora_antes_del_502(
    escenario, cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, fallo_del_correo
):
    """RF-21.4, RF-03.14: el intento fallido queda registrado («no entregada»; el texto dice que la contraseña no se modificó)."""
    provocar, _ = fallo_del_correo(escenario)
    provocar()

    respuesta = _resetear(cliente_api, iniciar_sesion(administrador), usuario_gubernamental.cedula)

    assert respuesta.status_code == 502
    registros = _registros_del_reseteo(administrador.cedula, usuario_gubernamental.cedula)
    assert len(registros) == 1
    tipo, texto_registrado, adicional = registros[0]
    assert tipo == ID_EDITAR_USUARIO
    assert usuario_gubernamental.cedula in texto_registrado
    assert "Intento de reseteo" in texto_registrado and "la contraseña no se modificó" in texto_registrado
    assert adicional["notificacion_correo"] == "no entregada"
    assert TEXTO_DEL_SERVIDOR not in json.dumps(adicional) + texto_registrado


@pytest.mark.parametrize("entregado", [True, False], ids=["entregada", "no-entregada"])
def test_la_consulta_de_la_bitacora_devuelve_el_resultado_de_la_notificacion(
    entregado, cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental
):
    """RF-21.6: `GET /bitacora/registros` devuelve `notificacion_correo` en el registro del reseteo."""
    if not entregado:
        correo_simulado.fallar(aiosmtplib.SMTPConnectError(TEXTO_DEL_SERVIDOR))
    cabeceras = iniciar_sesion(administrador)
    _resetear(cliente_api, cabeceras, usuario_gubernamental.cedula)

    respuesta = cliente_api.get(
        "/bitacora/registros", headers=cabeceras, params={"tipoAccion": ID_EDITAR_USUARIO, "usuario": administrador.correo, "limite": 100}
    )

    assert respuesta.status_code == 200
    items = [i for i in respuesta.json()["items"] if usuario_gubernamental.cedula in (i["texto"] or "")]
    assert len(items) == 1
    assert json.loads(items[0]["informacionAdicional"])["notificacion_correo"] == ("entregada" if entregado else "no entregada")


@pytest.mark.parametrize("entregado, codigo_esperado", [(True, 200), (False, 502)], ids=["entregada", "no-entregada"])
def test_si_falla_el_registro_en_la_bitacora_la_accion_termina_con_su_resultado_normal(
    entregado, codigo_esperado, cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, monkeypatch
):
    """RF-21.4 (caracterización): con `bitacora_service.registrar` fallando, el reseteo responde igual (200 o 502) y el cambio
    de contraseña se decide solo por el correo."""
    from app.services.bitacora.usuarios_audit_service import usuarios_audit_service

    async def _falla(**argumentos):
        raise Exception("PRUEBA la bitácora no responde")

    cabeceras = iniciar_sesion(administrador)
    antes = _fila(usuario_gubernamental.cedula)
    if not entregado:
        correo_simulado.fallar(aiosmtplib.SMTPConnectError(TEXTO_DEL_SERVIDOR))
    monkeypatch.setattr(usuarios_audit_service.bitacora_service, "registrar", _falla)

    respuesta = _resetear(cliente_api, cabeceras, usuario_gubernamental.cedula)

    assert respuesta.status_code == codigo_esperado
    assert (_fila(usuario_gubernamental.cedula).CT_Contrasenna != antes.CT_Contrasenna) is entregado
    assert _registros_del_reseteo(administrador.cedula, usuario_gubernamental.cedula) == []


# --- RNF-08.1: la temporal no queda en ningún rastro -----------------------------------------------------------------------------------

@pytest.mark.parametrize("escenario", ["exito", "fallo"])
def test_la_contrasena_temporal_no_queda_en_la_salida_ni_en_los_registros_ni_en_la_bitacora_ni_en_las_respuestas(
    escenario, cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, caplog, capfd
):
    """RNF-08.1: el flujo completo, con el correo funcionando y con el servidor en fallo, no deja la temporal en la salida, los
    registros (DEBUG), las filas de bitácora ni los cuerpos de las respuestas. El control positivo comprueba que la temporal sí
    estaba en el correo que el sistema armó (la búsqueda no es en vacío)."""
    if escenario == "fallo":
        correo_simulado.fallar(aiosmtplib.SMTPResponseException(535, TEXTO_DEL_SERVIDOR))
    cabeceras = iniciar_sesion(administrador)
    caplog.set_level(logging.DEBUG, logger="app")
    capfd.readouterr()

    respuesta = _resetear(cliente_api, cabeceras, usuario_gubernamental.cedula)

    contenido = correo_simulado.contenido_real()
    temporal = _temporal_enviada(correo_simulado)
    assert rastros.encontrar_en_rastros(temporal, correo=[contenido.texto, contenido.html]) == ["correo"]
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(
        temporal,
        salida=salida.out + salida.err,
        registros=caplog.text,
        bitacora=_todas_las_filas_de_bitacora(administrador.cedula, usuario_gubernamental.cedula),
        respuestas=respuesta.text,
    )


@pytest.mark.parametrize("escenario", ["exito", "fallo"])
def test_el_correo_completo_del_usuario_no_queda_en_los_registros_del_reseteo(
    escenario, cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, caplog, capfd
):
    """RNF-08.2: el correo del usuario sale enmascarado en los registros del servidor (salida y `logging`); la respuesta del
    fallo sí lo lleva (RF-03.14) y el control positivo comprueba que era el destinatario del mensaje armado."""
    if escenario == "fallo":
        correo_simulado.fallar(aiosmtplib.SMTPResponseException(535, TEXTO_DEL_SERVIDOR))
    cabeceras = iniciar_sesion(administrador)
    caplog.set_level(logging.DEBUG, logger="app")
    capfd.readouterr()

    respuesta = _resetear(cliente_api, cabeceras, usuario_gubernamental.cedula)

    assert rastros.encontrar_en_rastros(usuario_gubernamental.correo, correo=[correo_simulado.contenido_real().a]) == ["correo"]
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(usuario_gubernamental.correo, salida=salida.out + salida.err, registros=caplog.text)
    assert (usuario_gubernamental.correo in respuesta.text) is (escenario == "fallo")
