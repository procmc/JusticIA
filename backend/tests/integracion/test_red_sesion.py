"""Red de seguridad del inicio de sesión (spec 004, T5; RF-01.1, RF-01.2, RF-21.7).

Inicia sesión por `POST /auth/login`, como lo haría el navegador, con usuarios `PRUEBA` de la base `servia_pruebas`:
- RF-01.1: por rol, con la vigencia fijada, el token trae identificador, rol y correo, vence a la vigencia indicada, la
  respuesta no trae contraseña ni hash y el último acceso se actualiza.
- RF-01.2: correo no registrado, contraseña incorrecta y cuenta Inactiva responden lo mismo (401 «Credenciales
  inválidas», sin token) y cada intento deja una fila; el motivo distinto de cada caso es una prueba aparte.
- RF-21.7: cada inicio deja su fila (exitoso o fallido) y ninguna fila lleva la contraseña ni el token.

Las contraseñas las genera la suite en cada corrida y nunca se escriben ni se muestran. «Sin exigir un número exacto»: se
busca la fila de cada caso y los secretos se buscan en todas las filas creadas durante la prueba.
"""
import calendar
import json
from datetime import datetime, timedelta

import jwt
import pytest
from sqlalchemy import text

from tests.soporte import rastros
from tests.soporte.datos import generar_contrasena
from tests.soporte.nombres import PREFIJO_DATOS

VIGENCIA_FIJADA = 37  # minutos; distinta de la de desarrollo para que la prueba no acierte por casualidad
MENSAJE_DE_RECHAZO = "Credenciales inválidas"
ROLES = ("administrador", "usuario_gubernamental")


def _consultar(consulta: str, parametros: dict = None) -> list:
    from app.db.database import engine

    with engine.connect() as conexion:
        return [tuple(fila) for fila in conexion.execute(text(consulta), parametros or {}).fetchall()]


def _ultimo_id_de_bitacora() -> int:
    return int(_consultar("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")[0][0])


def _filas_desde(ultimo_id: int) -> list:
    """Todas las filas de la bitácora creadas después de `ultimo_id`, como diccionarios."""
    filas = _consultar(
        "SELECT CN_Id_bitacora, CN_Id_usuario, CN_Id_tipo_accion, CT_Texto, CT_Informacion_adicional "
        "FROM T_Bitacora WHERE CN_Id_bitacora > :d ORDER BY CN_Id_bitacora", {"d": ultimo_id})
    return [{"id": f[0], "usuario": f[1], "tipo": f[2], "texto": f[3] or "", "adicional": f[4] or ""} for f in filas]


def _iniciar(cliente_api, correo: str, contrasena):
    return cliente_api.post("/auth/login", json={"email": correo, "password": contrasena})


# --- RF-01.1 y RF-21.7: inicio exitoso por rol ----------------------------------------------------------------------------

@pytest.mark.requisito("RF-01.1")
@pytest.mark.requisito("RF-21.7")
@pytest.mark.parametrize("rol", ROLES)
def test_inicio_exitoso_por_rol(cliente_api, request, monkeypatch, rol):
    """RF-01.1, RF-21.7: un usuario Activo de cada rol inicia sesión; el token trae id, rol y correo y vence a la vigencia
    fijada; la respuesta no trae contraseña ni hash; el último acceso se actualiza y la bitácora registra el inicio sin
    contraseña ni token."""
    from app.auth import jwt_auth

    usuario = request.getfixturevalue(rol)
    monkeypatch.setattr(jwt_auth, "JWT_EXPIRE_MINUTES", VIGENCIA_FIJADA)
    inicio = datetime.utcnow()
    _ejecutar(
        "UPDATE T_Usuario SET CF_Ultimo_acceso = :v WHERE CN_Id_usuario = :c",
        {"v": inicio - timedelta(days=1), "c": usuario.cedula})
    hash_guardado = _consultar("SELECT CT_Contrasenna FROM T_Usuario WHERE CN_Id_usuario = :c", {"c": usuario.cedula})[0][0]
    ultimo_id = _ultimo_id_de_bitacora()

    respuesta = _iniciar(cliente_api, usuario.correo, usuario.contrasena)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["success"] is True
    token = cuerpo["access_token"]
    carga = jwt.decode(token, options={"verify_signature": False})
    assert str(carga["user_id"]) == usuario.cedula
    assert carga["role"] == usuario.rol
    assert carga["username"] == usuario.correo
    assert abs((carga["exp"] - carga["iat"]) - VIGENCIA_FIJADA * 60) <= 1
    assert cuerpo["user"]["email"] == usuario.correo
    assert cuerpo["user"]["role"] == usuario.rol
    assert not {"password", "contrasena", "contrasenna", "hash"} & {clave.lower() for clave in cuerpo["user"]}
    rastros.buscar_en_rastros(usuario.contrasena, respuesta=respuesta.text)
    rastros.buscar_en_rastros(hash_guardado, respuesta=respuesta.text)
    ultimo_acceso = _consultar("SELECT CF_Ultimo_acceso FROM T_Usuario WHERE CN_Id_usuario = :c", {"c": usuario.cedula})[0][0]
    assert ultimo_acceso >= inicio - timedelta(seconds=1), "el último acceso no se actualizó con el inicio de sesión"

    filas = _filas_desde(ultimo_id)
    propias = [f for f in filas if f["usuario"] == usuario.cedula and usuario.correo in f["texto"]]
    assert propias, "el inicio exitoso no dejó fila a nombre del usuario"
    assert all(f["tipo"] == 3 for f in propias)  # TiposAccion.LOGIN
    for secreto in (usuario.contrasena, token, hash_guardado):
        rastros.buscar_en_rastros(secreto, bitacora=[f["texto"] + f["adicional"] for f in filas])


def _ejecutar(consulta: str, parametros: dict) -> None:
    from app.db.database import engine

    with engine.begin() as conexion:
        conexion.execute(text(consulta), parametros)


# --- RF-01.2 y RF-21.7: tres fallos idénticos -----------------------------------------------------------------------------

def _provocar_los_tres_fallos(cliente_api, usuario_gubernamental, administrador):
    """Provoca los tres casos y devuelve, por caso, (respuesta, correo, contraseña enviada, filas nuevas)."""
    inactivo = administrador  # una cuenta propia de la prueba, desactivada solo para este caso
    _ejecutar(
        "UPDATE T_Usuario SET CN_Id_estado = (SELECT CN_Id_estado FROM T_Estado WHERE CT_Nombre_estado = 'Inactivo') "
        "WHERE CN_Id_usuario = :c", {"c": inactivo.cedula})
    casos = {
        "correo no registrado": (f"{PREFIJO_DATOS}.no.registrado@prueba.invalid", generar_contrasena()),
        "contraseña incorrecta": (usuario_gubernamental.correo, generar_contrasena()),
        "cuenta inactiva": (inactivo.correo, inactivo.contrasena),
    }
    resultados = {}
    for caso, (correo, contrasena) in casos.items():
        ultimo_id = _ultimo_id_de_bitacora()
        respuesta = _iniciar(cliente_api, correo, contrasena)
        resultados[caso] = (respuesta, correo, contrasena, _filas_desde(ultimo_id))
    return resultados


@pytest.mark.requisito("RF-01.2")
@pytest.mark.requisito("RF-21.7")
def test_tres_fallos_identicos_con_motivo(cliente_api, usuario_gubernamental, administrador):
    """RF-01.2, RF-21.7: correo no registrado, contraseña incorrecta y cuenta Inactiva dan el mismo 401 «Credenciales
    inválidas», sin token; cada intento deja su fila y ninguna lleva la contraseña enviada."""
    resultados = _provocar_los_tres_fallos(cliente_api, usuario_gubernamental, administrador)

    respuestas = [datos[0] for datos in resultados.values()]
    assert {r.status_code for r in respuestas} == {401}
    assert {json.dumps(r.json(), sort_keys=True) for r in respuestas} == {json.dumps({"detail": MENSAJE_DE_RECHAZO})}
    assert len({(r.headers.get("content-type"), r.headers.get("content-length"), r.headers.get("www-authenticate"))
                for r in respuestas}) == 1
    for caso, (respuesta, correo, contrasena, filas) in resultados.items():
        assert "access_token" not in respuesta.text, caso
        propias = [f for f in filas if correo in f["texto"]]
        assert len(propias) >= 1, f"el intento fallido «{caso}» no dejó fila en la bitácora"
        assert all(f["tipo"] == 3 for f in propias), caso  # TiposAccion.LOGIN
        rastros.buscar_en_rastros(contrasena, bitacora=[f["texto"] + f["adicional"] for f in filas])


@pytest.mark.requisito("RF-01.2")
@pytest.mark.xfail(strict=True, raises=AssertionError, reason="RF-01.2 · autenticación")
def test_tres_fallos_registran_motivos_distintos(cliente_api, usuario_gubernamental, administrador):
    """RF-01.2: el motivo registrado de cada intento es distinto (correo no registrado, contraseña incorrecta, cuenta
    inactiva); hoy los tres quedan con el mismo motivo genérico."""
    resultados = _provocar_los_tres_fallos(cliente_api, usuario_gubernamental, administrador)

    motivos = {}
    for caso, (_respuesta, correo, _contrasena, filas) in resultados.items():
        propias = [f for f in filas if correo in f["texto"]]
        assert propias, f"el intento fallido «{caso}» no dejó fila en la bitácora"
        motivos[caso] = json.loads(propias[0]["adicional"] or "{}").get("motivo")
    assert all(motivos.values()), "algún intento fallido no registró su motivo"
    assert len(set(motivos.values())) == 3, "los tres intentos fallidos no registran tres motivos distintos"


# --- RF-01.3, RF-01.6 y RF-21.7: contraseña temporal y cambio obligatorio -------------------------------------------------

def _hacer_temporal(usuario) -> None:
    """Deja la cuenta como la deja un alta o un reseteo: contraseña temporal, con el último acceso vacío."""
    _ejecutar("UPDATE T_Usuario SET CF_Ultimo_acceso = NULL WHERE CN_Id_usuario = :c", {"c": usuario.cedula})


def _fila_de_usuario(usuario) -> tuple:
    """(hash guardado, último acceso) de la cuenta."""
    return _consultar(
        "SELECT CT_Contrasenna, CF_Ultimo_acceso FROM T_Usuario WHERE CN_Id_usuario = :c", {"c": usuario.cedula})[0]


def _cambiar(cliente_api, usuario, token, actual, nueva):
    return cliente_api.put(
        "/auth/cambiar-contrasenna", headers={"Authorization": f"Bearer {token}"},
        json={"cedula_usuario": usuario.cedula, "contrasenna_actual": actual, "nueva_contrasenna": nueva})


@pytest.mark.requisito("RF-01.3")
@pytest.mark.requisito("RF-21.7")
def test_temporal_pide_cambio_sin_ultimo_acceso(cliente_api, usuario_gubernamental):
    """RF-01.3, RF-21.7: la cuenta con contraseña temporal (último acceso vacío) inicia sesión con éxito, la respuesta
    indica el cambio obligatorio y el último acceso sigue vacío; el inicio queda en la bitácora sin secretos."""
    usuario = usuario_gubernamental
    _hacer_temporal(usuario)
    hash_antes, _ = _fila_de_usuario(usuario)
    ultimo_id = _ultimo_id_de_bitacora()

    respuesta = _iniciar(cliente_api, usuario.correo, usuario.contrasena)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["success"] is True
    assert cuerpo["user"]["requiere_cambio_password"] is True
    assert cuerpo["access_token"]
    hash_despues, ultimo_acceso = _fila_de_usuario(usuario)
    assert ultimo_acceso is None, "el inicio con contraseña temporal no debe actualizar el último acceso"
    assert hash_despues == hash_antes
    filas = _filas_desde(ultimo_id)
    assert [f for f in filas if f["usuario"] == usuario.cedula and usuario.correo in f["texto"]], \
        "el inicio con contraseña temporal no dejó fila en la bitácora"
    for secreto in (usuario.contrasena, cuerpo["access_token"], hash_antes):
        rastros.buscar_en_rastros(secreto, bitacora=[f["texto"] + f["adicional"] for f in filas])


@pytest.mark.requisito("RF-01.6")
@pytest.mark.requisito("RF-21.7")
def test_cambio_obligatorio_con_su_sesion(cliente_api, usuario_gubernamental):
    """RF-01.6, RF-21.7: con su sesión, el usuario con cambio pendiente cambia la temporal por una nueva; se guarda la
    nueva con hash, se actualiza el último acceso, queda registrado sin secretos y el siguiente inicio ya no pide el
    cambio (y la temporal deja de servir)."""
    from app.constants.tipos_accion import TiposAccion

    usuario = usuario_gubernamental
    _hacer_temporal(usuario)
    nueva = generar_contrasena()
    token = _iniciar(cliente_api, usuario.correo, usuario.contrasena).json()["access_token"]
    hash_antes, _ = _fila_de_usuario(usuario)
    inicio = datetime.utcnow()
    ultimo_id = _ultimo_id_de_bitacora()

    respuesta = _cambiar(cliente_api, usuario, token, usuario.contrasena, nueva)

    assert respuesta.status_code == 200
    assert respuesta.json()["success"] is True
    hash_despues, ultimo_acceso = _fila_de_usuario(usuario)
    assert hash_despues != hash_antes
    assert hash_despues not in (str(nueva), str(usuario.contrasena)), "la contraseña debe guardarse con hash"
    assert ultimo_acceso is not None and ultimo_acceso >= inicio - timedelta(seconds=1)

    filas = _filas_desde(ultimo_id)
    cambios = [f for f in filas if f["usuario"] == usuario.cedula and f["tipo"] == TiposAccion.CAMBIO_CONTRASENA]
    assert cambios, "el cambio obligatorio no quedó registrado en la bitácora"
    for secreto in (usuario.contrasena, nueva, token, hash_antes, hash_despues):
        rastros.buscar_en_rastros(secreto, respuesta=respuesta.text, bitacora=[f["texto"] + f["adicional"] for f in filas])

    siguiente = _iniciar(cliente_api, usuario.correo, nueva)
    assert siguiente.status_code == 200
    assert siguiente.json()["user"]["requiere_cambio_password"] is False
    assert _iniciar(cliente_api, usuario.correo, usuario.contrasena).status_code == 401


@pytest.mark.requisito("RF-01.6")
@pytest.mark.parametrize("caso", ("temporal incorrecta", "nueva igual a la actual"))
def test_temporal_incorrecta_o_igual_no_cambia(cliente_api, usuario_gubernamental, caso):
    """RF-01.6: con la temporal incorrecta, o con una nueva igual a la actual, no cambia nada (ni el hash ni el último
    acceso), no queda fila de cambio y responde 400 con un mensaje en español."""
    from app.constants.tipos_accion import TiposAccion

    usuario = usuario_gubernamental
    _hacer_temporal(usuario)
    token = _iniciar(cliente_api, usuario.correo, usuario.contrasena).json()["access_token"]
    antes = _fila_de_usuario(usuario)
    ultimo_id = _ultimo_id_de_bitacora()
    if caso == "temporal incorrecta":
        actual, nueva = generar_contrasena(), generar_contrasena()
    else:
        actual, nueva = usuario.contrasena, usuario.contrasena

    respuesta = _cambiar(cliente_api, usuario, token, actual, nueva)

    assert respuesta.status_code == 400
    detalle = respuesta.json()["detail"]
    assert isinstance(detalle, str) and detalle.strip()
    assert "contraseña" in detalle.lower(), "el mensaje de error debe estar en español y hablar de la contraseña"
    assert _fila_de_usuario(usuario) == antes
    assert not [f for f in _filas_desde(ultimo_id) if f["tipo"] == TiposAccion.CAMBIO_CONTRASENA]
    assert _iniciar(cliente_api, usuario.correo, usuario.contrasena).status_code == 200


# --- RF-01.5 y RF-21.7: renovación del token ------------------------------------------------------------------------------

def _firmar(carga: dict, clave: str = None) -> str:
    import jwt as _jwt

    from app.config.config import JWT_ALGORITHM, JWT_SECRET_KEY

    return _jwt.encode(carga, clave or JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _token_vigente_de(usuario, emitido_hace: timedelta, vence_en: timedelta) -> str:
    """Un token vigente del usuario, con otra emisión que la de la renovación para poder compararlas."""
    ahora = datetime.utcnow()
    return _firmar({"user_id": usuario.cedula, "role": usuario.rol, "username": usuario.correo,
                    "iat": ahora - emitido_hace, "exp": ahora + vence_en})


def _renovar(cliente_api, token=None):
    cabeceras = {} if token is None else {"Authorization": f"Bearer {token}"}
    return cliente_api.post("/auth/refresh-token", headers=cabeceras)


@pytest.mark.requisito("RF-01.5")
@pytest.mark.parametrize("rol", ROLES)
def test_renovacion_por_rol(cliente_api, request, monkeypatch, rol):
    """RF-01.5: con un token vigente, la renovación entrega uno nuevo (emisión posterior) con el mismo id, rol y correo y la
    vigencia configurada contada desde la renovación; la respuesta no trae contraseña ni hash."""
    from app.auth import jwt_auth

    usuario = request.getfixturevalue(rol)
    monkeypatch.setattr(jwt_auth, "JWT_EXPIRE_MINUTES", VIGENCIA_FIJADA)
    anterior = _token_vigente_de(usuario, emitido_hace=timedelta(minutes=10), vence_en=timedelta(minutes=5))
    antes = jwt.decode(anterior, options={"verify_signature": False})
    hash_guardado = _consultar("SELECT CT_Contrasenna FROM T_Usuario WHERE CN_Id_usuario = :c", {"c": usuario.cedula})[0][0]
    pedida = datetime.utcnow()

    respuesta = _renovar(cliente_api, anterior)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["success"] is True
    nuevo = cuerpo["access_token"]
    assert nuevo and nuevo != anterior
    carga = jwt.decode(nuevo, options={"verify_signature": False})
    assert carga["iat"] > antes["iat"], "el token nuevo debe tener una emisión posterior a la del anterior"
    assert str(carga["user_id"]) == usuario.cedula
    assert carga["role"] == usuario.rol
    assert carga["username"] == usuario.correo
    assert abs((carga["exp"] - carga["iat"]) - VIGENCIA_FIJADA * 60) <= 1, "la vigencia no es la configurada"
    vence_esperado = calendar.timegm(pedida.utctimetuple()) + VIGENCIA_FIJADA * 60
    assert 0 <= carga["exp"] - vence_esperado <= 10, "la vigencia no se cuenta desde la renovación"
    assert carga["exp"] > antes["exp"]
    assert cuerpo["user"]["email"] == usuario.correo
    assert cuerpo["user"]["role"] == usuario.rol
    assert not {"password", "contrasena", "contrasenna", "hash"} & {clave.lower() for clave in cuerpo["user"]}
    rastros.buscar_en_rastros(usuario.contrasena, respuesta=respuesta.text)
    rastros.buscar_en_rastros(hash_guardado, respuesta=respuesta.text)


@pytest.mark.requisito("RF-01.5")
@pytest.mark.parametrize("tipo", ("sin-token", "invalido", "vencido", "otra-clave"))
def test_renovacion_con_token_invalido_da_401(cliente_api, usuario_gubernamental, tipo):
    """RF-01.5: si el token falta, es inválido, está vencido o está firmado con otra clave, la renovación responde 401 y no
    entrega ningún token. Los tres con token llevan una carga que el sistema aceptaría si no fallara la firma o la vigencia."""
    usuario = usuario_gubernamental
    ahora = datetime.utcnow()
    carga = {"user_id": usuario.cedula, "role": usuario.rol, "username": usuario.correo, "iat": ahora}
    if tipo == "sin-token":
        token = None
    elif tipo == "invalido":
        token = "PRUEBA.token.invalido"
    elif tipo == "vencido":
        token = _firmar({**carga, "exp": ahora - timedelta(hours=1)})
    else:
        token = _firmar({**carga, "exp": ahora + timedelta(hours=1)},
                        clave="PRUEBA-otra-clave-de-firma-distinta-de-la-del-sistema-0123456789")

    respuesta = _renovar(cliente_api, token)

    assert respuesta.status_code == 401
    assert "access_token" not in respuesta.text


# --- RF-01.4 y RF-21.7: cierre de sesión ----------------------------------------------------------------------------------

def _cerrar(cliente_api, usuario, token):
    return cliente_api.post(
        "/auth/logout", headers={"Authorization": f"Bearer {token}"},
        json={"usuario_id": usuario.cedula, "email": usuario.correo})


def _forzar_fallo_de_la_bitacora(monkeypatch) -> None:
    """Parcha la clase, no la instancia: al deshacer, monkeypatch dejaría en la instancia el método original y taparía el
    parche de clase de otras pruebas (dependencia de orden)."""
    from app.services.bitacora.bitacora_service import BitacoraService

    async def _falla(self, *_args, **_kwargs):
        raise RuntimeError("PRUEBA: la bitácora no responde")

    monkeypatch.setattr(BitacoraService, "registrar", _falla)


@pytest.mark.requisito("RF-01.4")
@pytest.mark.requisito("RF-21.7")
@pytest.mark.parametrize("rol", ROLES)
def test_cierre_registra_a_nombre_del_usuario(cliente_api, request, rol):
    """RF-01.4, RF-21.7: el cierre de sesión deja una fila a nombre del usuario que cierra, sin contraseña ni token, y
    responde éxito."""
    from app.constants.tipos_accion import TiposAccion

    usuario = request.getfixturevalue(rol)
    token = _iniciar(cliente_api, usuario.correo, usuario.contrasena).json()["access_token"]
    ultimo_id = _ultimo_id_de_bitacora()

    respuesta = _cerrar(cliente_api, usuario, token)

    assert respuesta.status_code == 200
    assert respuesta.json()["success"] is True
    filas = _filas_desde(ultimo_id)
    cierres = [f for f in filas if f["tipo"] == TiposAccion.LOGOUT]
    assert [f for f in cierres if f["usuario"] == usuario.cedula and usuario.correo in f["texto"]], \
        "el cierre de sesión no dejó fila a nombre del usuario"
    for secreto in (usuario.contrasena, token):
        rastros.buscar_en_rastros(secreto, respuesta=respuesta.text, bitacora=[f["texto"] + f["adicional"] for f in filas])


@pytest.mark.requisito("RF-01.4")
def test_cierre_con_bitacora_que_falla(cliente_api, usuario_gubernamental, monkeypatch):
    """RF-01.4: si el registro del cierre falla, la sesión se cierra igual: el servidor responde éxito, sin error, y no queda
    fila (el efecto sobre el token se comprueba en `test_token_cerrado_da_401`)."""
    from app.constants.tipos_accion import TiposAccion

    usuario = usuario_gubernamental
    token = _iniciar(cliente_api, usuario.correo, usuario.contrasena).json()["access_token"]
    _forzar_fallo_de_la_bitacora(monkeypatch)
    ultimo_id = _ultimo_id_de_bitacora()

    respuesta = _cerrar(cliente_api, usuario, token)

    assert respuesta.status_code == 200
    assert respuesta.json()["success"] is True
    assert not [f for f in _filas_desde(ultimo_id) if f["tipo"] == TiposAccion.LOGOUT]


@pytest.mark.requisito("RF-01.4")
@pytest.mark.xfail(strict=True, raises=AssertionError, reason="RF-01.4 · autenticación")
@pytest.mark.parametrize("caso", ("ruta protegida", "renovación", "con la bitácora fallando"))
def test_token_cerrado_da_401(cliente_api, usuario_gubernamental, monkeypatch, caso):
    """RF-01.4: tras cerrar sesión, el servidor rechaza con 401 ese token en una ruta protegida y en la renovación, también
    cuando el registro del cierre falla. Hoy el servidor sigue aceptándolo."""
    usuario = usuario_gubernamental
    token = _iniciar(cliente_api, usuario.correo, usuario.contrasena).json()["access_token"]
    if caso == "con la bitácora fallando":
        _forzar_fallo_de_la_bitacora(monkeypatch)
    assert _cerrar(cliente_api, usuario, token).status_code == 200

    if caso == "renovación":
        respuesta = _renovar(cliente_api, token)
    else:
        respuesta = cliente_api.get(
            "/notebooks", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 401, "el servidor sigue aceptando un token de una sesión cerrada"
    assert "access_token" not in respuesta.text
