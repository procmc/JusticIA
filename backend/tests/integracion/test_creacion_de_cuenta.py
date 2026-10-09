"""Pruebas de T7 (spec 003a): la creación de una cuenta por el Administrador (RF-02.1, RF-21.4, RF-21.6, RNF-08.1, RNF-08.2).

`POST /usuarios/` crea la cuenta con una contraseña temporal (guardada con hash, último acceso vacío) y la envía por correo.
Si el correo no sale, la cuenta existe igual: la respuesta (200) dice que la notificación NO se entregó y lleva la advertencia
de la spec con el correo de la cuenta; si sale, dice que sí y lleva «Usuario creado exitosamente». La respuesta nunca trae la
temporal. El resultado queda en la bitácora (`notificacion_correo`) sin la temporal, y si la bitácora falla la cuenta se crea igual.

Usan la base `servia_pruebas` y el correo simulado: ningún correo sale de la prueba. Las cuentas son `PRUEBA9xxxxx`
(la limpieza por prefijo de la suite las borra); la temporal la genera el sistema y la prueba la lee del contenido real del
correo simulado o de un espía sobre el repositorio (nunca se imprime).
"""
import asyncio
import email
import email.policy
import itertools
import json
import logging

import aiosmtplib
import pytest
from sqlalchemy import text

from tests.soporte import rastros
from tests.soporte.datos import Contrasena
from tests.soporte.nombres import PREFIJO_DATOS

MENSAJE_EXITOSO = "Usuario creado exitosamente"
TEXTO_DEL_SERVIDOR = f"{PREFIJO_DATOS}-535 detalle-del-servidor-inventado clave=PRUEBA-clave-4417"
TEXTO_DE_LA_EXCEPCION = f"{PREFIJO_DATOS} detalle-interno-inventado prueba.error@prueba.invalid"
ID_CREAR_USUARIO = 7  # TiposAccion.CREAR_USUARIO
CAMPOS_NUEVOS = {"notificacion_entregada", "mensaje"}
ESCENARIOS_DE_FALLO = ["servidor_en_fallo", "cuenta_sin_configurar", "sin_servicio_de_correo"]

_consecutivo = itertools.count(1)


def _advertencia(correo):
    return (
        f"Usuario creado, pero no se pudo enviar el correo con la contraseña temporal a {correo}. "
        'Use "Resetear Contraseña" cuando el servicio de correo esté disponible.'
    )


def _consultar(consulta, parametros=None):
    from app.db.database import engine

    with engine.connect() as conexion:
        return conexion.execute(text(consulta), parametros or {}).fetchall()


def _id_del_rol(nombre="Usuario Judicial"):
    return _consultar("SELECT CN_Id_rol FROM T_Rol WHERE CT_Nombre_rol = :n", {"n": nombre})[0][0]


def _datos_de_cuenta(**cambios):
    """El cuerpo de la solicitud de una cuenta nueva e inventada, con tilde y «ñ» en el nombre de usuario (RF-03.18)."""
    numero = next(_consecutivo)
    datos = {
        "cedula": f"{PREFIJO_DATOS}9{numero:05d}",
        "nombre_usuario": f"{PREFIJO_DATOS} Peña Núñez {numero}",
        "nombre": PREFIJO_DATOS,
        "apellido_uno": "Peña",
        "apellido_dos": "Núñez",
        "correo": f"prueba9{numero}.nueva@prueba.invalid",
        "id_rol": _id_del_rol(),
    }
    datos.update(cambios)
    return datos


def _fila(cedula):
    """Lo que la base tiene de la cuenta (hash, último acceso, estado), o `None` si no existe."""
    filas = _consultar(
        "SELECT u.CT_Contrasenna, u.CF_Ultimo_acceso, e.CT_Nombre_estado FROM T_Usuario u "
        "JOIN T_Estado e ON e.CN_Id_estado = u.CN_Id_estado WHERE u.CN_Id_usuario = :c",
        {"c": cedula},
    )
    return filas[0] if filas else None


def _cuentas_de_la_prueba():
    """Cuántas cuentas de este archivo hay en la base (cédulas `PRUEBA9...`)."""
    return _consultar("SELECT COUNT(*) FROM T_Usuario WHERE CN_Id_usuario LIKE :p", {"p": f"{PREFIJO_DATOS}9%"})[0][0]


def _crear(cliente_api, cabeceras, datos):
    return cliente_api.post("/usuarios/", headers=cabeceras, json=datos)


def _iniciar_sesion(cliente_api, correo, contrasena):
    return cliente_api.post("/auth/login", json={"email": correo, "password": str(contrasena)})


def _temporal_enviada(correo_simulado):
    """La contraseña temporal que llevó el último correo de creación (envuelta en `Contrasena`: su `repr` no la muestra)."""
    return rastros.valor_tras(correo_simulado.contenido_real().texto, "Tu contraseña de acceso es:")


def _registros_de_la_creacion(cedula_administrador, cedula_creada):
    """Las filas de la bitácora de la creación de esa cuenta: (tipo de acción, texto, información adicional ya leída)."""
    filas = _consultar(
        "SELECT CN_Id_tipo_accion, CT_Texto, CT_Informacion_adicional FROM T_Bitacora "
        "WHERE CN_Id_usuario = :c AND CN_Id_tipo_accion = :t ORDER BY CN_Id_bitacora",
        {"c": cedula_administrador, "t": ID_CREAR_USUARIO},
    )
    registros = [(tipo, texto, json.loads(adicional)) for tipo, texto, adicional in filas]
    return [r for r in registros if r[2].get("usuario_creado_cedula") == cedula_creada]


def _todas_las_filas_de_bitacora(*cedulas):
    """Texto e información adicional de toda la bitácora de esas cuentas (para buscar un secreto)."""
    filas = []
    for cedula in cedulas:
        filas += _consultar(
            "SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_usuario = :c", {"c": cedula}
        )
    return [list(fila) for fila in filas]


@pytest.fixture
def temporales_generadas(monkeypatch):
    """Espía sobre el repositorio real: anota (en `Contrasena`) cada temporal que el sistema guarda al crear una cuenta.

    Sirve para buscar la temporal en los rastros también cuando el correo no sale (no hay mensaje del que leerla).
    """
    from app.routes.usuarios import usuario_service

    original = usuario_service.repository.crear_usuario
    generadas = []

    def _espiar(db, cedula, nombre_usuario, nombre, apellido_uno, apellido_dos, correo, contrasenna, id_rol):
        generadas.append(Contrasena(contrasenna))
        return original(db, cedula, nombre_usuario, nombre, apellido_uno, apellido_dos, correo, contrasenna, id_rol)

    monkeypatch.setattr(usuario_service.repository, "crear_usuario", _espiar)
    return generadas


@pytest.fixture
def fallo_del_correo(correo_simulado, monkeypatch):
    """Devuelve `_preparar(escenario)` -> `(provocar, restaurar)`: `provocar()` rompe el envío y `restaurar()` lo deja funcionando."""
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


# --- RF-02.1: la creación con el correo funcionando ---------------------------------------------------------------------------

def test_la_creacion_exitosa_responde_entregada_con_el_texto_de_exito_y_envia_la_temporal_al_correo_de_la_cuenta(
    cliente_api, iniciar_sesion, correo_simulado, administrador, temporales_generadas
):
    """RF-02.1: 200 con `notificacion_entregada` verdadero y «Usuario creado exitosamente»; la cuenta existe y está Activa, con
    un hash bcrypt de la temporal (no la temporal) y el último acceso vacío; el correo va a la dirección de la cuenta con la temporal."""
    from app.repositories.usuario_repository import UsuarioRepository

    datos = _datos_de_cuenta()

    respuesta = _crear(cliente_api, iniciar_sesion(administrador), datos)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["notificacion_entregada"] is True
    assert cuerpo["mensaje"] == MENSAJE_EXITOSO
    assert cuerpo["CN_Id_usuario"] == datos["cedula"] and cuerpo["CT_Correo"] == datos["correo"]
    assert cuerpo["CT_Nombre_usuario"] == datos["nombre_usuario"]
    assert cuerpo["estado"]["nombre"] == "Activo"
    assert [intento["a"] for intento in correo_simulado.intentos] == [datos["correo"]]
    temporal = _temporal_enviada(correo_simulado)
    fila = _fila(datos["cedula"])
    assert len(temporal) == 8 and temporal.isalnum()
    assert temporales_generadas == [temporal]
    assert fila.CT_Contrasenna != temporal and temporal not in fila.CT_Contrasenna
    assert UsuarioRepository().pwd_context.verify(str(temporal), fila.CT_Contrasenna)
    assert fila.CF_Ultimo_acceso is None and fila.CT_Nombre_estado == "Activo"
    assert str(temporal) not in respuesta.text


def test_con_la_temporal_se_inicia_sesion_y_obliga_a_cambiar_la_contrasena(
    cliente_api, iniciar_sesion, correo_simulado, administrador
):
    """RF-02.1: un inicio de sesión con la temporal del correo funciona y la respuesta pide cambiar la contraseña."""
    datos = _datos_de_cuenta()
    _crear(cliente_api, iniciar_sesion(administrador), datos)

    respuesta = _iniciar_sesion(cliente_api, datos["correo"], _temporal_enviada(correo_simulado))

    assert respuesta.status_code == 200
    assert respuesta.json()["user"]["requiere_cambio_password"] is True


def test_el_correo_de_la_cuenta_sale_en_utf_8_con_el_nombre_de_usuario_con_tilde_y_enie(
    cliente_api, iniciar_sesion, correo_simulado, administrador
):
    """RF-03.18, RF-02.1: el mensaje serializado se decodifica con un lector independiente y trae «PRUEBA Peña Núñez» en el cuerpo y
    «contraseña» en el asunto; el nombre de usuario con tilde y «ñ» se guarda sin errores."""
    datos = _datos_de_cuenta()

    respuesta = _crear(cliente_api, iniciar_sesion(administrador), datos)

    assert respuesta.status_code == 200
    mensaje = email.message_from_bytes(correo_simulado.intentos[-1].bytes_serializados, policy=email.policy.default)
    cuerpo = mensaje.get_body(preferencelist=("plain",)).get_content()
    assert f"{PREFIJO_DATOS} Peña Núñez" in cuerpo
    assert "contraseña" in str(mensaje["Subject"]).lower()
    assert _fila(datos["cedula"]) is not None
    assert respuesta.json()["CT_Nombre_usuario"] == datos["nombre_usuario"]


# --- RF-02.1: el envío falla -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("escenario", ESCENARIOS_DE_FALLO)
def test_si_el_envio_falla_la_cuenta_se_crea_y_la_respuesta_lleva_la_advertencia_de_la_spec(
    escenario, cliente_api, iniciar_sesion, correo_simulado, administrador, fallo_del_correo, temporales_generadas
):
    """RF-02.1 (regresión): con el servidor de correo en fallo, la cuenta de correo sin configurar o sin servicio de correo, la
    cuenta existe y está Activa, su contraseña es un hash de la temporal, el último acceso está vacío, `notificacion_entregada` es
    falso y `mensaje` es la advertencia completa con el correo; ni la temporal ni el texto del error del servidor están en la respuesta."""
    from app.repositories.usuario_repository import UsuarioRepository

    provocar, _ = fallo_del_correo(escenario)
    provocar()
    cabeceras = iniciar_sesion(administrador)
    datos = _datos_de_cuenta()

    respuesta = _crear(cliente_api, cabeceras, datos)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["notificacion_entregada"] is False
    assert cuerpo["mensaje"] == _advertencia(datos["correo"])
    assert cuerpo["CN_Id_usuario"] == datos["cedula"] and cuerpo["estado"]["nombre"] == "Activo"
    fila = _fila(datos["cedula"])
    assert fila is not None and fila.CF_Ultimo_acceso is None and fila.CT_Nombre_estado == "Activo"
    assert len(temporales_generadas) == 1
    temporal = temporales_generadas[0]
    assert fila.CT_Contrasenna != temporal and UsuarioRepository().pwd_context.verify(str(temporal), fila.CT_Contrasenna)
    rastros.buscar_en_rastros(temporal, respuesta=respuesta.text)
    assert TEXTO_DEL_SERVIDOR not in respuesta.text
    assert len(correo_simulado.intentos) == (1 if escenario == "servidor_en_fallo" else 0)


def test_tras_la_advertencia_el_reseteo_con_el_correo_funcionando_entrega_la_temporal(
    cliente_api, iniciar_sesion, correo_simulado, administrador, fallo_del_correo
):
    """RF-02.1: el texto manda usar «Resetear Contraseña» cuando el correo esté disponible, y funciona: tras la advertencia, el
    reseteo con el correo ya funcionando responde 200 y la temporal nueva inicia sesión."""
    provocar, restaurar = fallo_del_correo("servidor_en_fallo")
    provocar()
    cabeceras = iniciar_sesion(administrador)
    datos = _datos_de_cuenta()
    assert _crear(cliente_api, cabeceras, datos).json()["notificacion_entregada"] is False

    restaurar()
    reseteo = cliente_api.post(f"/usuarios/{datos['cedula']}/resetear-contrasenna", headers=cabeceras)

    assert reseteo.status_code == 200
    temporal_del_reseteo = rastros.valor_tras(correo_simulado.contenido_real().texto, "Tu nueva contraseña temporal es:")
    sesion = _iniciar_sesion(cliente_api, datos["correo"], temporal_del_reseteo)
    assert sesion.status_code == 200 and sesion.json()["user"]["requiere_cambio_password"] is True


def test_con_un_servidor_que_no_responde_la_cuenta_se_crea_y_la_notificacion_no_se_entrega_a_los_15_s(
    correo_simulado, reloj_controlable, temporales_generadas, monkeypatch
):
    """RF-02.1, RF-03.16: con `no_responde()` y el reloj controlable, el servicio real y la base real: el envío sigue pendiente a
    los 14,9 s, termina «no entregada» a los 15 s y la cuenta existe con su hash. Se llama al servicio dentro de `asyncio.run`
    porque `TestClient` corre la aplicación en otro hilo y bucle y la prueba no podría adelantar el reloj durante la petición."""
    from app.db.database import SessionLocal
    from app.routes.usuarios import usuario_service

    monkeypatch.setattr(usuario_service.email_service.config, "timeout", 15.0)
    correo_simulado.no_responde()
    datos = _datos_de_cuenta()

    async def _escenario():
        with SessionLocal() as db:
            tarea = asyncio.ensure_future(usuario_service.crear_usuario(
                db, datos["cedula"], datos["nombre_usuario"], datos["nombre"], datos["apellido_uno"],
                datos["apellido_dos"], datos["correo"], datos["id_rol"],
            ))
            await reloj_controlable.avanzar(14.9)
            seguia_pendiente = not tarea.done()
            await reloj_controlable.avanzar(0.1)
            assert tarea.done(), "el envío debía darse por fallido a los 15 s"
            return seguia_pendiente, tarea.result()

    seguia_pendiente, resultado = asyncio.run(_escenario())

    assert seguia_pendiente is True
    assert resultado.notificacion_entregada is False
    assert resultado.mensaje == _advertencia(datos["correo"])
    assert correo_simulado.tiempos_maximos == [15.0]
    fila = _fila(datos["cedula"])
    assert fila is not None and fila.CF_Ultimo_acceso is None and fila.CT_Nombre_estado == "Activo"
    assert len(temporales_generadas) == 1
    rastros.buscar_en_rastros(temporales_generadas[0], respuesta=resultado.model_dump_json())


# --- Datos inválidos y repetidos -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("defecto", ["sin_correo", "rol_en_texto", "cuerpo_vacio"])
def test_con_datos_invalidos_no_se_crea_la_cuenta_ni_se_intenta_enviar_el_correo(
    defecto, cliente_api, iniciar_sesion, correo_simulado, administrador
):
    """RF-02.1: una solicitud inválida responde 422, no crea ninguna cuenta y no sale ni se intenta ningún correo."""
    cabeceras = iniciar_sesion(administrador)
    datos = _datos_de_cuenta()
    if defecto == "sin_correo":
        del datos["correo"]
    elif defecto == "rol_en_texto":
        datos["id_rol"] = "no-es-un-numero"
    else:
        datos = {}
    antes = _cuentas_de_la_prueba()

    respuesta = _crear(cliente_api, cabeceras, datos)

    assert respuesta.status_code == 422
    assert _cuentas_de_la_prueba() == antes
    assert correo_simulado.intentos == []


def test_con_un_rol_inexistente_responde_500_sin_crear_la_cuenta_ni_enviar_el_correo(
    cliente_api, iniciar_sesion, correo_simulado, administrador
):
    """RF-02.1: si la base rechaza la cuenta (rol que no existe), el error es el 500 genérico, no hay cuenta, no hay correo y la
    bitácora no registra una creación."""
    cabeceras = iniciar_sesion(administrador)
    datos = _datos_de_cuenta(id_rol=987654)

    respuesta = _crear(cliente_api, cabeceras, datos)

    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "Error interno del servidor"}
    assert _fila(datos["cedula"]) is None
    assert correo_simulado.intentos == []
    assert _registros_de_la_creacion(administrador.cedula, datos["cedula"]) == []


@pytest.mark.parametrize("repetido", ["cedula", "correo", "nombre_usuario"])
def test_una_cuenta_repetida_da_500_sin_cambiar_la_existente_ni_enviar_correo_ni_dejar_el_correo_en_los_registros(
    repetido, cliente_api, iniciar_sesion, correo_simulado, administrador, usuario_gubernamental, caplog, capfd
):
    """RF-02.1, RNF-08.2: repetir la cédula, el correo o el nombre de usuario de otra cuenta da el 500 genérico (el comportamiento
    de siempre); la cuenta existente no cambia, no sale ningún correo y el error de la base (que lista los parámetros de la
    consulta, entre ellos el correo) no llega a la salida, a los registros ni a la respuesta."""
    caplog.set_level(logging.DEBUG, logger="app")
    cabeceras = iniciar_sesion(administrador)
    existente = {"cedula": usuario_gubernamental.cedula, "correo": usuario_gubernamental.correo,
                 "nombre_usuario": usuario_gubernamental.nombre_usuario}
    datos = _datos_de_cuenta(**{repetido: existente[repetido]})
    antes = _fila(usuario_gubernamental.cedula)
    cuentas = _cuentas_de_la_prueba()
    capfd.readouterr()

    respuesta = _crear(cliente_api, cabeceras, datos)

    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "Error interno del servidor"}
    assert _fila(usuario_gubernamental.cedula) == antes
    assert _cuentas_de_la_prueba() == cuentas
    assert correo_simulado.intentos == []
    assert "IntegrityError" in caplog.text or "ProgrammingError" in caplog.text  # control: el fallo sí se registró, solo su tipo
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(
        datos["correo"], salida=salida.out + salida.err, registros=caplog.text, respuestas=respuesta.text
    )


# --- Roles ---------------------------------------------------------------------------------------------------------------------

def test_sin_token_responde_401_y_no_crea_nada(cliente_api, correo_simulado):
    """RF-02.1, RNF-07: sin token, 401; no hay cuenta ni correo."""
    datos = _datos_de_cuenta()

    respuesta = _crear(cliente_api, {}, datos)

    assert respuesta.status_code == 401
    assert _fila(datos["cedula"]) is None
    assert correo_simulado.intentos == []


def test_el_usuario_gubernamental_recibe_403_y_no_crea_nada(cliente_api, iniciar_sesion, correo_simulado, usuario_gubernamental):
    """RF-02.1, RNF-07: un Usuario Gubernamental no puede crear cuentas: 403; no hay cuenta ni correo."""
    cabeceras = iniciar_sesion(usuario_gubernamental)
    datos = _datos_de_cuenta()

    respuesta = _crear(cliente_api, cabeceras, datos)

    assert respuesta.status_code == 403
    assert _fila(datos["cedula"]) is None
    assert correo_simulado.intentos == []


# --- El listado y la edición no cambian ---------------------------------------------------------------------------------------

def test_el_listado_y_la_edicion_no_ganan_los_campos_nuevos(cliente_api, iniciar_sesion, correo_simulado, administrador):
    """RF-02.1 (riesgo del plan): `GET /usuarios/`, `GET /usuarios/{id}` y `PUT /usuarios/{id}` siguen usando `UsuarioRespuesta`: no
    traen `notificacion_entregada` ni `mensaje` (solo la creación); el esquema de OpenAPI lo confirma."""
    cabeceras = iniciar_sesion(administrador)
    datos = _datos_de_cuenta()
    assert _crear(cliente_api, cabeceras, datos).status_code == 200
    id_activo = _consultar("SELECT CN_Id_estado FROM T_Estado WHERE CT_Nombre_estado = 'Activo'")[0][0]

    listado = cliente_api.get("/usuarios/", headers=cabeceras)
    uno = cliente_api.get(f"/usuarios/{datos['cedula']}", headers=cabeceras)
    edicion = cliente_api.put(f"/usuarios/{datos['cedula']}", headers=cabeceras, json={
        "nombre_usuario": datos["nombre_usuario"], "nombre": datos["nombre"], "apellido_uno": datos["apellido_uno"],
        "apellido_dos": datos["apellido_dos"], "correo": datos["correo"], "id_rol": datos["id_rol"], "id_estado": id_activo,
    })

    assert listado.status_code == 200 and uno.status_code == 200 and edicion.status_code == 200
    de_la_cuenta = [u for u in listado.json() if u["CN_Id_usuario"] == datos["cedula"]]
    assert len(de_la_cuenta) == 1
    for objeto in (*listado.json(), uno.json(), edicion.json()):
        assert not CAMPOS_NUEVOS & set(objeto)
    esquemas = cliente_api.get("/openapi.json").json()["components"]["schemas"]
    assert not CAMPOS_NUEVOS & set(esquemas["UsuarioRespuesta"]["properties"])
    assert CAMPOS_NUEVOS <= set(esquemas["UsuarioCreadoRespuesta"]["properties"])


# --- RF-21.4 y RF-21.6: la bitácora ---------------------------------------------------------------------------------------------

def test_la_creacion_exitosa_queda_en_la_bitacora_con_el_resultado_de_la_notificacion(
    cliente_api, iniciar_sesion, correo_simulado, administrador, temporales_generadas
):
    """RF-21.4: un registro con el administrador, la cédula de la cuenta y `notificacion_correo` = «entregada»; sin la temporal."""
    datos = _datos_de_cuenta()
    _crear(cliente_api, iniciar_sesion(administrador), datos)

    registros = _registros_de_la_creacion(administrador.cedula, datos["cedula"])

    assert len(registros) == 1
    tipo, texto_registrado, adicional = registros[0]
    assert tipo == ID_CREAR_USUARIO
    assert datos["cedula"] in texto_registrado and "entregada" in texto_registrado and "no entregada" not in texto_registrado
    assert adicional["notificacion_correo"] == "entregada"
    assert adicional["usuario_creado_cedula"] == datos["cedula"] and adicional["email"] == datos["correo"]
    rastros.buscar_en_rastros(temporales_generadas[0], texto=texto_registrado, adicional=adicional)


@pytest.mark.parametrize("escenario", ESCENARIOS_DE_FALLO)
def test_la_creacion_con_el_envio_fallido_tambien_queda_en_la_bitacora_como_no_entregada(
    escenario, cliente_api, iniciar_sesion, correo_simulado, administrador, fallo_del_correo, temporales_generadas
):
    """RF-21.4: la cuenta creada con la notificación no entregada queda registrada («no entregada»), sin la temporal ni el texto del servidor."""
    provocar, _ = fallo_del_correo(escenario)
    provocar()
    datos = _datos_de_cuenta()

    respuesta = _crear(cliente_api, iniciar_sesion(administrador), datos)

    assert respuesta.status_code == 200
    registros = _registros_de_la_creacion(administrador.cedula, datos["cedula"])
    assert len(registros) == 1
    tipo, texto_registrado, adicional = registros[0]
    assert tipo == ID_CREAR_USUARIO
    assert datos["cedula"] in texto_registrado and "no entregada" in texto_registrado
    assert adicional["notificacion_correo"] == "no entregada"
    rastros.buscar_en_rastros(temporales_generadas[0], texto=texto_registrado, adicional=adicional)
    assert TEXTO_DEL_SERVIDOR not in json.dumps(adicional) + texto_registrado


@pytest.mark.parametrize("entregado", [True, False], ids=["entregada", "no-entregada"])
def test_la_consulta_de_la_bitacora_devuelve_el_resultado_de_la_notificacion(
    entregado, cliente_api, iniciar_sesion, correo_simulado, administrador
):
    """RF-21.6: `GET /bitacora/registros` devuelve `notificacion_correo` en el registro de la creación."""
    if not entregado:
        correo_simulado.fallar(aiosmtplib.SMTPConnectError(TEXTO_DEL_SERVIDOR))
    cabeceras = iniciar_sesion(administrador)
    datos = _datos_de_cuenta()
    _crear(cliente_api, cabeceras, datos)

    respuesta = cliente_api.get(
        "/bitacora/registros", headers=cabeceras, params={"tipoAccion": ID_CREAR_USUARIO, "usuario": administrador.correo, "limite": 100}
    )

    assert respuesta.status_code == 200
    items = [i for i in respuesta.json()["items"] if datos["cedula"] in (i["texto"] or "")]
    assert len(items) == 1
    assert json.loads(items[0]["informacionAdicional"])["notificacion_correo"] == ("entregada" if entregado else "no entregada")


@pytest.mark.parametrize("entregado", [True, False], ids=["entregada", "no-entregada"])
def test_si_falla_el_registro_en_la_bitacora_la_cuenta_se_crea_igual_y_el_error_no_deja_el_correo_en_los_registros(
    entregado, cliente_api, iniciar_sesion, correo_simulado, administrador, monkeypatch, caplog, capfd
):
    """RF-21.4, RNF-08.2 (regresión del aviso de T6): con `bitacora_service.registrar` fallando, la creación responde 200 igual, la
    cuenta existe, y el texto del error del INSERT (que lleva el correo de la cuenta) no queda en claro en los registros."""
    from app.services.bitacora.usuarios_audit_service import usuarios_audit_service

    datos = _datos_de_cuenta()

    async def _falla(**argumentos):
        raise Exception(f"INSERT fallido, parámetros: ('{datos['correo']}', '{PREFIJO_DATOS}')")

    cabeceras = iniciar_sesion(administrador)
    if not entregado:
        correo_simulado.fallar(aiosmtplib.SMTPConnectError(TEXTO_DEL_SERVIDOR))
    monkeypatch.setattr(usuarios_audit_service.bitacora_service, "registrar", _falla)
    caplog.set_level(logging.DEBUG, logger="app")
    capfd.readouterr()

    respuesta = _crear(cliente_api, cabeceras, datos)

    assert respuesta.status_code == 200
    assert respuesta.json()["notificacion_entregada"] is entregado
    assert _fila(datos["cedula"]) is not None
    assert _registros_de_la_creacion(administrador.cedula, datos["cedula"]) == []
    assert "Error registrando creación de usuario" in caplog.text  # control: el fallo sí se registró
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(datos["correo"], salida=salida.out + salida.err, registros=caplog.text)


# --- RNF-08.1 y RNF-08.2: nada de la temporal ni del correo completo en los rastros -----------------------------------------------

@pytest.mark.parametrize("escenario", ["exito", "fallo"])
def test_la_contrasena_temporal_no_queda_en_la_salida_ni_en_los_registros_ni_en_la_bitacora_ni_en_las_respuestas(
    escenario, cliente_api, iniciar_sesion, correo_simulado, administrador, temporales_generadas, caplog, capfd
):
    """RNF-08.1: el flujo completo, con el correo funcionando y con el servidor en fallo, no deja la temporal en la salida, los
    registros (DEBUG), las filas de bitácora ni los cuerpos de las respuestas. El control positivo comprueba que la temporal sí
    estaba en el correo que el sistema armó (la búsqueda no es en vacío)."""
    if escenario == "fallo":
        correo_simulado.fallar(aiosmtplib.SMTPResponseException(535, TEXTO_DEL_SERVIDOR))
    cabeceras = iniciar_sesion(administrador)
    datos = _datos_de_cuenta()
    caplog.set_level(logging.DEBUG, logger="app")
    capfd.readouterr()

    respuesta = _crear(cliente_api, cabeceras, datos)

    contenido = correo_simulado.contenido_real()
    temporal = temporales_generadas[0]
    assert rastros.encontrar_en_rastros(temporal, correo=[contenido.texto, contenido.html]) == ["correo"]
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(
        temporal,
        salida=salida.out + salida.err,
        registros=caplog.text,
        bitacora=_todas_las_filas_de_bitacora(administrador.cedula, datos["cedula"]),
        respuestas=respuesta.text,
    )


@pytest.mark.parametrize("escenario", ["exito", "fallo"])
def test_el_correo_completo_de_la_cuenta_no_queda_en_los_registros_de_la_creacion(
    escenario, cliente_api, iniciar_sesion, correo_simulado, administrador, caplog, capfd
):
    """RNF-08.2: el correo de la cuenta sale enmascarado en los registros del servidor (salida y `logging`); la respuesta de la
    advertencia sí lo lleva (RF-02.1) y el control positivo comprueba que era el destinatario del mensaje armado."""
    if escenario == "fallo":
        correo_simulado.fallar(aiosmtplib.SMTPResponseException(535, TEXTO_DEL_SERVIDOR))
    cabeceras = iniciar_sesion(administrador)
    datos = _datos_de_cuenta()
    caplog.set_level(logging.DEBUG, logger="app")
    capfd.readouterr()

    respuesta = _crear(cliente_api, cabeceras, datos)

    assert rastros.encontrar_en_rastros(datos["correo"], correo=[correo_simulado.contenido_real().a]) == ["correo"]
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(datos["correo"], salida=salida.out + salida.err, registros=caplog.text)
    assert (datos["correo"] in respuesta.json()["mensaje"]) is (escenario == "fallo")
