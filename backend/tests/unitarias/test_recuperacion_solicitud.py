"""Pruebas de T5 (spec 003b): el paso 1 de la recuperación de contraseña, la solicitud del código, en el servicio.

Cubren RF-03.1 (el código solo viaja por correo), RF-03.2 (los cinco casos responden igual), RF-03.4 (se genera y se
envía un código solo a una cuenta Activa y queda un solo código vigente), RF-03.5 (una cuenta Inactiva no recibe
correo), RF-03.10 a RF-03.12 (una solicitud por minuto y cinco por hora, por correo normalizado, con o sin cuenta) y
RF-03.21 (el token tiene siempre la misma forma y no identifica la cuenta). El servicio es
`app/services/recuperacion_service.py`.

El servicio corre con un repositorio de usuarios simulado (sin base de datos), el Redis controlable de la suite
(`redis_controlable`) y el correo simulado (`correo_simulado`): nada sale de la prueba. Los correos y las cédulas son
inventados (prefijo `prueba`/`PRUEBA`, dominio `.invalid`); el código real se lee del correo simulado y nunca se imprime.
La clave de firma es la que fija la suite. Los plazos de Redis son tiempo VIRTUAL (`avanzar`).

Los casos de servicio no disponible (Redis sin respuesta y clave de firma inválida) se prueban aquí en lo mínimo; su
cobertura completa por la API llega en T8.
"""
import asyncio
import re
import sys
import types

import pytest

from tests.soporte import rastros

CORREO = "prueba.ana@prueba.invalid"
CEDULA = "PRUEBA700001"
MENSAJE_DEL_ERS = "Si el correo existe en nuestro sistema, recibirás un email con las instrucciones"
MENSAJE_CORREO_INVALIDO = "Ingresa un correo electrónico válido"
MENSAJE_SERVICIO_NO_DISPONIBLE = (
    "El servicio de recuperación de contraseña no está disponible por el momento. Inténtalo de nuevo más tarde."
)
PATRON_DEL_TOKEN = re.compile(r"[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{22}")
CLAVES_DE_REDIS = "recuperacion:*"


def _cuenta(correo=CORREO, estado="Activo", cedula=CEDULA):
    """Una cuenta inventada con la forma que el servicio lee del repositorio de usuarios."""
    return types.SimpleNamespace(
        CN_Id_usuario=cedula, CT_Nombre="PRUEBA", CT_Apellido_uno="Peña", CT_Apellido_dos="Núñez", CT_Correo=correo,
        CT_Contrasenna="PRUEBA-resumen-que-no-es-real", estado=types.SimpleNamespace(CT_Nombre_estado=estado),
    )


class RepositorioDeUsuariosSimulado:
    """Hace de `UsuarioRepository.obtener_usuario_por_correo` sin base de datos y anota qué correos se consultaron."""

    def __init__(self, *cuentas):
        self.cuentas = {cuenta.CT_Correo.strip().lower(): cuenta for cuenta in cuentas}
        self.consultas = []

    def obtener_usuario_por_correo(self, db, correo_normalizado):
        self.consultas.append(correo_normalizado)
        return self.cuentas.get(correo_normalizado)


@pytest.fixture
def armar(correo_simulado, redis_controlable):
    """Una función que arma el servicio con las cuentas dadas; devuelve `(servicio, repositorio_de_usuarios)`."""

    def _armar(*cuentas):
        from app.services.recuperacion_service import RecuperacionService
        from app.services.usuario_service import UsuarioService

        repositorio = RepositorioDeUsuariosSimulado(*cuentas)
        return RecuperacionService(usuarios=repositorio, servicio_de_usuarios=UsuarioService()), repositorio

    return _armar


@pytest.fixture
def bitacora_falsa(monkeypatch):
    """Sustituye la sesión propia de `completar_solicitud` y el registro de la solicitud en la bitácora; anota lo que recibieron."""
    from app.services.bitacora.auth_audit_service import auth_audit_service

    class Sesion:
        def __init__(self):
            self.cerrada = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.cerrada = True
            return False

    anotado = types.SimpleNamespace(sesiones=[], registros=[], error_al_abrir=None, error_al_registrar=None)

    def abrir_sesion():
        if anotado.error_al_abrir is not None:
            raise anotado.error_al_abrir
        anotado.sesiones.append(Sesion())
        return anotado.sesiones[-1]

    async def registrar(db, email, resultado, usuario_id=None, referencia=None):
        if anotado.error_al_registrar is not None:
            raise anotado.error_al_registrar
        anotado.registros.append(
            {"db": db, "email": email, "resultado": resultado, "usuario_id": usuario_id, "referencia": referencia}
        )

    modulo = types.ModuleType("app.db.database")
    modulo.SessionLocal = abrir_sesion
    monkeypatch.setitem(sys.modules, "app.db.database", modulo)
    monkeypatch.setattr(auth_audit_service, "registrar_recuperacion_solicitud", registrar)
    return anotado


# --- Auxiliares ----------------------------------------------------------------------------------------------------

def _solicitar(servicio, correo):
    return asyncio.run(servicio.solicitar(None, correo))


def _pedir_y_completar(servicio, correo):
    """Hace el paso 1 completo (la respuesta y lo que ocurre después de responder). Devuelve el resultado de la solicitud."""
    resultado = _solicitar(servicio, correo)
    asyncio.run(servicio.completar_solicitud(resultado.pendiente))
    return resultado


def _codigo_del_correo(correo_simulado, indice=-1):
    return rastros.valor_tras(correo_simulado.contenido_real(indice).texto, "Tu código de verificación es:", patron=r"[0-9]{6}")


def _huella(correo):
    from app.utils import clave_firma
    from app.utils import recuperacion_codigos as rc

    return rc.huella_de_correo(rc.derivar_claves_de_recuperacion(clave_firma.leer_clave_firma()).huella, correo)


def _forma(respuesta):
    """Lo que se puede comparar de una respuesta sin mostrar su token: campos, mensaje, éxito y forma del token."""
    return {
        "campos": list(respuesta.model_dump().keys()),
        "exito": respuesta.success,
        "mensaje": respuesta.message,
        "largo": len(respuesta.token),
        "segmentos": [len(segmento) for segmento in respuesta.token.split(".")],
        "formato": PATRON_DEL_TOKEN.fullmatch(respuesta.token) is not None,
    }


def _resumen_de_redis(redis):
    """El juego de claves de Redis sin la huella ni los valores: el tipo de cada clave y si caduca como debe."""
    tipos = {}
    for clave in redis.claves(CLAVES_DE_REDIS):
        tipo = clave.split(":")[1]
        tipos[tipo] = redis.cliente.ttl(clave) > 0
    return tipos


# --- RF-03.4 y RF-03.5: quién recibe un código ----------------------------------------------------------------------

def test_una_cuenta_activa_recibe_un_solo_correo_con_un_codigo_de_6_digitos(armar, correo_simulado, bitacora_falsa):
    """RF-03.4: la cuenta Activa recibe exactamente un correo, a su dirección, con un código de 6 dígitos."""
    from app.utils import recuperacion_codigos as rc

    servicio, _ = armar(_cuenta())

    _pedir_y_completar(servicio, CORREO)

    assert [intento["a"] for intento in correo_simulado.intentos] == [CORREO]
    assert rc.es_codigo_valido(str(_codigo_del_correo(correo_simulado)))


@pytest.mark.parametrize("correo, cuentas", [
    pytest.param("prueba.sin.cuenta@prueba.invalid", (), id="correo sin cuenta"),
    pytest.param(CORREO, (_cuenta(estado="Inactivo"),), id="cuenta Inactiva"),
])
def test_un_correo_sin_cuenta_y_una_cuenta_inactiva_no_reciben_ningun_correo(armar, correo_simulado, bitacora_falsa, correo, cuentas):
    """RF-03.4 y RF-03.5: sin cuenta o con la cuenta Inactiva no se genera ni se envía ningún código. Control positivo
    en la prueba de la cuenta Activa: el correo simulado sí registra el envío cuando corresponde."""
    servicio, _ = armar(*cuentas)

    resultado = _pedir_y_completar(servicio, correo)

    assert correo_simulado.intentos == []
    assert resultado.pendiente.envio is None


def test_las_mayusculas_y_los_espacios_encuentran_la_cuenta(armar, correo_simulado, bitacora_falsa):
    """RF-03.4 y RF-03.12: «  PRUEBA.Ana@Prueba.INVALID » es el mismo correo que el de la cuenta; el servicio consulta el
    repositorio con el correo ya normalizado y el correo sale a la dirección de la cuenta."""
    servicio, repositorio = armar(_cuenta())

    _pedir_y_completar(servicio, "  PRUEBA.Ana@Prueba.INVALID ")

    assert repositorio.consultas == [CORREO]
    assert [intento["a"] for intento in correo_simulado.intentos] == [CORREO]


# --- RF-03.12: los mismos conteos con y sin cuenta -----------------------------------------------------------------------

def test_los_mismos_conteos_de_claves_con_y_sin_cuenta_y_con_cuenta_inactiva(armar, redis_controlable, bitacora_falsa):
    """RF-03.12: las claves de Redis (estado, bloqueo de 60 s y contador de la hora), su caducidad y los campos del estado son
    iguales para una cuenta Activa, un correo sin cuenta y una cuenta Inactiva: el límite no delata qué cuentas existen."""
    resumenes, campos = {}, {}
    for caso, correo, cuentas in (
        ("activa", CORREO, (_cuenta(),)),
        ("sin_cuenta", "prueba.nadie@prueba.invalid", ()),
        ("inactiva", "prueba.inactiva@prueba.invalid", (_cuenta("prueba.inactiva@prueba.invalid", "Inactivo", "PRUEBA700002"),)),
    ):
        redis_controlable.perder_todas()
        servicio, _ = armar(*cuentas)
        _pedir_y_completar(servicio, correo)
        resumenes[caso] = _resumen_de_redis(redis_controlable)
        campos[caso] = sorted(redis_controlable.cliente.hgetall(f"recuperacion:estado:{_huella(correo)}").keys())
        assert redis_controlable.cliente.get(f"recuperacion:hora:{_huella(correo)}") == "1"

    assert resumenes["activa"] == {"estado": True, "bloqueo": True, "hora": True}
    assert resumenes["sin_cuenta"] == resumenes["activa"]
    assert resumenes["inactiva"] == resumenes["activa"]
    assert campos["activa"] == ["cedula", "codigo", "emision", "intentos", "vinculo"]
    assert campos["sin_cuenta"] == campos["activa"] and campos["inactiva"] == campos["activa"]


def test_el_estado_guardado_coincide_con_la_cuenta(armar, correo_simulado, redis_controlable, bitacora_falsa):
    """RF-03.1 y RF-03.4: el estado de una cuenta Activa lleva el HMAC del código que salió por correo (no el código), su
    cédula, el vínculo con la cuenta, la emisión del token y cero intentos; caduca en 15 minutos."""
    from app.utils import clave_firma
    from app.utils import recuperacion_codigos as rc

    cuenta = _cuenta()
    servicio, _ = armar(cuenta)

    resultado = _pedir_y_completar(servicio, CORREO)

    claves = rc.derivar_claves_de_recuperacion(clave_firma.leer_clave_firma())
    huella = _huella(CORREO)
    codigo = str(_codigo_del_correo(correo_simulado))
    estado = redis_controlable.cliente.hgetall(f"recuperacion:estado:{huella}")
    assert estado["codigo"] == rc.hash_de_codigo(claves.codigo, huella, codigo)
    assert estado["cedula"] == CEDULA
    assert estado["vinculo"] == rc.vinculo_de_cuenta(claves.vinculo, CEDULA, CORREO, "Activo", cuenta.CT_Contrasenna)
    assert estado["intentos"] == "0"
    assert resultado.respuesta.token == f"{huella}.{estado['emision']}"
    assert 890 < redis_controlable.cliente.ttl(f"recuperacion:estado:{huella}") <= 900
    assert rastros.encontrar_en_rastros(codigo, estado=estado) == []


def test_el_estado_senuelo_de_un_correo_sin_cuenta_y_de_una_cuenta_inactiva_tiene_el_mismo_aspecto(armar, redis_controlable, bitacora_falsa):
    """RF-03.8: sin cuenta Activa se guarda un estado con la misma forma (HMAC y vínculo de 64 hexadecimales, cinco campos,
    cero intentos) que ningún código puede acertar; la cédula de una cuenta Inactiva se guarda solo para la bitácora."""
    inactiva = _cuenta("prueba.inactiva@prueba.invalid", "Inactivo", "PRUEBA700002")
    servicio, _ = armar(inactiva)

    _pedir_y_completar(servicio, "prueba.nadie@prueba.invalid")
    _pedir_y_completar(servicio, inactiva.CT_Correo)

    sin_cuenta = redis_controlable.cliente.hgetall(f"recuperacion:estado:{_huella('prueba.nadie@prueba.invalid')}")
    de_inactiva = redis_controlable.cliente.hgetall(f"recuperacion:estado:{_huella(inactiva.CT_Correo)}")
    for estado in (sin_cuenta, de_inactiva):
        assert re.fullmatch(r"[0-9a-f]{64}", estado["codigo"]) and re.fullmatch(r"[0-9a-f]{64}", estado["vinculo"])
        assert estado["intentos"] == "0"
    assert sin_cuenta["cedula"] == "" and de_inactiva["cedula"] == "PRUEBA700002"


# --- RF-03.2 y RF-03.21: la respuesta uniforme -------------------------------------------------------------------------------

def test_los_cinco_casos_responden_igual_con_un_token_de_la_misma_forma_que_no_identifica_la_cuenta(armar, correo_simulado, bitacora_falsa):
    """RF-03.2 y RF-03.21: cuenta Activa, correo no registrado, cuenta Inactiva, envío fallido y límite alcanzado dan los
    mismos campos en el mismo orden, el mismo mensaje del ERS y un token con la misma forma (22 + punto + 22 caracteres de
    URL); ni el cuerpo ni el token llevan la cédula ni el correo (ni su parte local)."""
    otra = _cuenta("prueba.otra@prueba.invalid", cedula="PRUEBA700003")
    inactiva = _cuenta("prueba.inactiva@prueba.invalid", "Inactivo", "PRUEBA700002")
    servicio, _ = armar(_cuenta(), inactiva, otra)

    casos = {
        "activa": (_pedir_y_completar(servicio, CORREO), _cuenta()),
        "limite": (_pedir_y_completar(servicio, CORREO), _cuenta()),
        "no_registrada": (_pedir_y_completar(servicio, "prueba.nadie@prueba.invalid"), None),
        "inactiva": (_pedir_y_completar(servicio, inactiva.CT_Correo), inactiva),
    }
    correo_simulado.fallar()
    casos["envio_fallido"] = (_pedir_y_completar(servicio, otra.CT_Correo), otra)

    formas = {nombre: _forma(resultado.respuesta) for nombre, (resultado, _) in casos.items()}
    assert formas["activa"]["mensaje"] == MENSAJE_DEL_ERS and formas["activa"]["exito"] is True
    assert formas["activa"]["formato"] is True
    assert formas["activa"]["campos"] == ["success", "message", "token"]
    assert [nombre for nombre, forma in formas.items() if forma != formas["activa"]] == []
    for nombre, (resultado, cuenta) in casos.items():
        correo = cuenta.CT_Correo if cuenta else "prueba.nadie@prueba.invalid"
        datos = [correo, correo.split("@")[0]] + ([cuenta.CN_Id_usuario] if cuenta else [])
        cuerpo = resultado.respuesta.model_dump_json()
        assert [dato for dato in datos if rastros.encontrar_en_rastros(dato, cuerpo=cuerpo)] == [], nombre


def test_cada_solicitud_aceptada_devuelve_un_token_distinto(armar, redis_controlable, bitacora_falsa):
    """RF-03.4: la emisión de cada solicitud aceptada es nueva, así el código anterior responde como vencido."""
    servicio, _ = armar(_cuenta())

    primera = _pedir_y_completar(servicio, CORREO).respuesta.token
    redis_controlable.avanzar(61)
    segunda = _pedir_y_completar(servicio, CORREO).respuesta.token

    emision_guardada = redis_controlable.cliente.hget(f"recuperacion:estado:{_huella(CORREO)}", "emision")
    assert primera != segunda
    assert segunda.split(".")[1] == emision_guardada and primera.split(".")[1] != emision_guardada


# --- RF-03.10 y RF-03.11: los límites ---------------------------------------------------------------------------------------

def test_una_segunda_solicitud_antes_de_60_segundos_no_envia_ni_cambia_el_estado(armar, correo_simulado, redis_controlable, bitacora_falsa):
    """RF-03.10: la solicitud bloqueada responde igual, no envía un correo nuevo ni reemplaza el código vigente; después de
    61 s se acepta."""
    servicio, _ = armar(_cuenta())
    primera = _pedir_y_completar(servicio, CORREO)
    clave = f"recuperacion:estado:{_huella(CORREO)}"
    emision = redis_controlable.cliente.hget(clave, "emision")

    segunda = _pedir_y_completar(servicio, CORREO)

    assert len(correo_simulado.intentos) == 1
    assert redis_controlable.cliente.hget(clave, "emision") == emision == primera.respuesta.token.split(".")[1]
    assert segunda.respuesta.token.split(".")[1] != emision
    assert _forma(segunda.respuesta) == _forma(primera.respuesta)
    redis_controlable.avanzar(61)
    _pedir_y_completar(servicio, CORREO)
    assert len(correo_simulado.intentos) == 2


def test_la_sexta_solicitud_de_la_hora_no_envia_y_responde_igual(armar, correo_simulado, redis_controlable, bitacora_falsa):
    """RF-03.11: cinco solicitudes aceptadas por hora; la sexta responde igual y no envía."""
    servicio, _ = armar(_cuenta())
    for _ in range(5):
        _pedir_y_completar(servicio, CORREO)
        redis_controlable.avanzar(61)

    sexta = _pedir_y_completar(servicio, CORREO)

    assert len(correo_simulado.intentos) == 5
    assert sexta.pendiente.resultado == "límite alcanzado" and sexta.pendiente.envio is None


# --- RF-03.12: la entrada inválida ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("correo", [
    pytest.param("", id="vacío"),
    pytest.param("   ", id="solo espacios"),
    pytest.param(None, id="ausente"),
    pytest.param("x" * 91 + "@correo.cr", id="101 caracteres"),
    pytest.param("sin-arroba.correo.cr", id="sin arroba"),
    pytest.param("ana@@correo.cr", id="dos arrobas"),
    pytest.param("ana perez@correo.cr", id="espacio interno"),
    pytest.param("ana@correo", id="sin punto en el dominio"),
])
def test_un_correo_mal_formado_es_entrada_invalida_y_no_deja_ninguna_clave(armar, correo_simulado, redis_controlable, bitacora_falsa, correo):
    """RF-03.12 y RF-03.22: un correo vacío, de más de 100 caracteres o mal formado da 400 con su mensaje; no cuenta para
    los límites (no crea ninguna clave en Redis), no consulta la cuenta, no envía nada y no se registra en la bitácora."""
    from app.services.recuperacion_service import ErrorDeRecuperacion

    servicio, repositorio = armar(_cuenta())

    with pytest.raises(ErrorDeRecuperacion) as error:
        _pedir_y_completar(servicio, correo)

    assert (error.value.estado, error.value.mensaje) == (400, MENSAJE_CORREO_INVALIDO)
    assert error.value.registrar is False
    assert redis_controlable.claves() == []
    assert repositorio.consultas == [] and correo_simulado.intentos == [] and bitacora_falsa.registros == []


def test_un_correo_de_exactamente_100_caracteres_es_valido(armar, redis_controlable, bitacora_falsa):
    """RF-03.12: el límite es de 100 caracteres inclusive."""
    servicio, _ = armar()

    resultado = _pedir_y_completar(servicio, "x" * 90 + "@correo.cr")

    assert resultado.respuesta.success is True and len(redis_controlable.claves(CLAVES_DE_REDIS)) == 3


# --- RF-03.2 y RF-03.3: lo que ocurre después de responder ---------------------------------------------------------------------------

def test_el_envio_fallido_no_cambia_la_respuesta_y_no_lanza(armar, correo_simulado, bitacora_falsa):
    """RF-03.2: con el servidor de correo caído la respuesta es la misma, el intento queda registrado y completar no lanza."""
    sin_fallo, _ = armar(_cuenta())
    esperada = _forma(_pedir_y_completar(sin_fallo, CORREO).respuesta)
    correo_simulado.fallar()
    con_fallo, _ = armar(_cuenta("prueba.otra@prueba.invalid", cedula="PRUEBA700003"))

    resultado = _pedir_y_completar(con_fallo, "prueba.otra@prueba.invalid")

    assert _forma(resultado.respuesta) == esperada
    assert len(correo_simulado.intentos) == 2  # el segundo se intentó y falló


def test_sin_servicio_de_correo_o_con_un_error_inesperado_completar_no_lanza(armar, correo_simulado, bitacora_falsa):
    """RF-03.2: sin servicio de correo configurado o con un error cualquiera al enviar, el envío cuenta como fallido y la
    tarea posterior termina sin lanzar (la respuesta ya se dio)."""
    servicio, _ = armar(_cuenta())
    servicio.servicio_de_usuarios.email_service = None

    _pedir_y_completar(servicio, CORREO)

    assert correo_simulado.intentos == []
    correo_simulado.fallar(RuntimeError("PRUEBA fallo inesperado del envío"))
    otro, _ = armar(_cuenta("prueba.otra@prueba.invalid", cedula="PRUEBA700003"))
    _pedir_y_completar(otro, "prueba.otra@prueba.invalid")
    assert len(correo_simulado.intentos) == 1


def test_el_codigo_y_el_correo_no_salen_en_el_repr_del_envio_pendiente(armar, correo_simulado, bitacora_falsa):
    """RF-03.1 y RNF-08: el `repr` del envío pendiente, de la solicitud pendiente y del resultado no muestra el código ni el
    correo ni el nombre. Control positivo: el envío pendiente SÍ guarda el código (es el del correo) y el correo."""
    servicio, _ = armar(_cuenta())

    resultado = _solicitar(servicio, CORREO)
    asyncio.run(servicio.completar_solicitud(resultado.pendiente))

    codigo = str(_codigo_del_correo(correo_simulado))
    envio = resultado.pendiente.envio
    assert str(envio.codigo) == codigo and envio.correo == CORREO
    representaciones = {"envio": repr(envio), "pendiente": repr(resultado.pendiente), "resultado": repr(resultado), "texto": str(envio)}
    for valor in (codigo, CORREO, CORREO.split("@")[0], "Peña"):
        assert rastros.encontrar_en_rastros(valor, **representaciones) == []


# --- RF-21.1 y RF-21.5: el registro de la solicitud en la bitácora (las filas reales: test_recuperacion_bitacora.py) -----

def test_completar_registra_la_solicitud_con_su_propia_sesion_despues_del_envio(armar, correo_simulado, bitacora_falsa):
    """RF-21.1: tras el envío, `completar_solicitud` registra la solicitud en la bitácora con una sesión propia que cierra
    al terminar (la sesión de la petición puede estar cerrada)."""
    servicio, _ = armar(_cuenta())
    resultado = _solicitar(servicio, " " + CORREO.upper())

    asyncio.run(servicio.completar_solicitud(resultado.pendiente))

    assert len(correo_simulado.intentos) == 1
    assert len(bitacora_falsa.sesiones) == 1 and bitacora_falsa.sesiones[0].cerrada is True
    assert [registro["email"] for registro in bitacora_falsa.registros] == [CORREO]
    assert bitacora_falsa.registros[0]["db"] is bitacora_falsa.sesiones[0]
    assert bitacora_falsa.registros[0]["resultado"] == "código enviado"
    assert bitacora_falsa.registros[0]["usuario_id"] == CEDULA
    assert bitacora_falsa.registros[0]["referencia"] == _huella(CORREO)[:8]


@pytest.mark.parametrize("fallo", ["al_abrir", "al_registrar"])
def test_si_la_bitacora_falla_completar_no_lanza_y_el_correo_ya_salio(armar, correo_simulado, bitacora_falsa, fallo, caplog):
    """RF-21.5: si abrir la sesión o registrar falla, la acción sigue: el correo salió, `completar_solicitud` no lanza y el
    registro del servidor trae solo el tipo de la excepción (nunca su texto)."""
    servicio, _ = armar(_cuenta())
    resultado = _solicitar(servicio, CORREO)
    setattr(bitacora_falsa, "error_" + fallo, RuntimeError(f"PRUEBA texto que no debe salir {CORREO}"))

    with caplog.at_level("DEBUG", logger="app"):
        asyncio.run(servicio.completar_solicitud(resultado.pendiente))

    assert len(correo_simulado.intentos) == 1
    assert rastros.encontrar_en_rastros("texto que no debe salir", registros=caplog.text) == []
    assert rastros.encontrar_en_rastros(CORREO, registros=caplog.text) == []


# --- RF-03.20 y RNF-07.3 en lo mínimo (la cobertura por la API llega en T8) ---------------------------------------------------------

@pytest.mark.parametrize("tipo", ["conexion", "tiempo"])
def test_con_redis_sin_respuesta_la_solicitud_es_servicio_no_disponible_sin_mirar_la_cuenta(armar, correo_simulado, redis_controlable, bitacora_falsa, tipo):
    """RF-03.20: si Redis no responde (error de conexión o de tiempo) la solicitud lanza el error de servicio uniforme (503)
    ANTES de consultar la cuenta, y no envía nada."""
    from app.services.recuperacion_service import ServicioNoDisponible

    servicio, repositorio = armar(_cuenta())
    redis_controlable.no_responde(tipo)

    with pytest.raises(ServicioNoDisponible) as error:
        _solicitar(servicio, CORREO)

    assert (error.value.estado, error.value.mensaje) == (503, MENSAJE_SERVICIO_NO_DISPONIBLE)
    assert repositorio.consultas == [] and correo_simulado.intentos == []


@pytest.mark.parametrize("valor", ["", "corta", "default-secret-key-change-in-production"], ids=["ausente", "débil", "de respaldo"])
def test_con_la_clave_de_firma_invalida_la_solicitud_es_servicio_no_disponible_y_no_toca_redis(armar, correo_simulado, redis_controlable, bitacora_falsa, monkeypatch, valor):
    """RNF-07.3: con la clave de firma ausente, débil o de respaldo, la solicitud lanza el mismo error de servicio uniforme,
    no consulta la cuenta, no usa Redis y no envía nada."""
    from app.services.recuperacion_service import ServicioNoDisponible

    servicio, repositorio = armar(_cuenta())
    monkeypatch.setenv("JWT_SECRET_KEY", valor)

    with pytest.raises(ServicioNoDisponible) as error:
        _solicitar(servicio, CORREO)

    assert (error.value.estado, error.value.mensaje) == (503, MENSAJE_SERVICIO_NO_DISPONIBLE)
    assert repositorio.consultas == [] and correo_simulado.intentos == [] and redis_controlable.claves() == []


# --- El repositorio de usuarios: guardar la contraseña de la recuperación (la usa el último paso, T6) ----------------------------------

class SesionDeBaseSimulada:
    """Una sesión que anota `commit` y `rollback`; con `error_al_confirmar` el `commit` lanza."""

    def __init__(self, error_al_confirmar=None):
        self.error_al_confirmar = error_al_confirmar
        self.llamadas = []

    def commit(self):
        self.llamadas.append("commit")
        if self.error_al_confirmar is not None:
            raise self.error_al_confirmar

    def rollback(self):
        self.llamadas.append("rollback")


def test_actualizar_contrasenna_recuperacion_guarda_solo_el_hash_y_confirma():
    """RF-03.4: el repositorio cambia el hash de la contraseña y confirma; no toca el último acceso ni el estado."""
    from app.repositories.usuario_repository import UsuarioRepository

    usuario = types.SimpleNamespace(CT_Contrasenna="PRUEBA-hash-anterior", CF_Ultimo_acceso="PRUEBA-fecha", CN_Id_estado=1)
    sesion = SesionDeBaseSimulada()

    UsuarioRepository().actualizar_contrasenna_recuperacion(sesion, usuario, "PRUEBA-hash-nuevo")

    assert (usuario.CT_Contrasenna, usuario.CF_Ultimo_acceso, usuario.CN_Id_estado) == ("PRUEBA-hash-nuevo", "PRUEBA-fecha", 1)
    assert sesion.llamadas == ["commit"]


def test_si_el_guardado_de_la_contrasenna_falla_se_deshace_y_el_error_sigue():
    """RF-03.4: si el `commit` falla, el repositorio hace `rollback` y relanza el error (la ruta responde el 500 genérico)."""
    from app.repositories.usuario_repository import UsuarioRepository

    sesion = SesionDeBaseSimulada(error_al_confirmar=RuntimeError("PRUEBA fallo de la base"))

    with pytest.raises(RuntimeError):
        UsuarioRepository().actualizar_contrasenna_recuperacion(sesion, types.SimpleNamespace(CT_Contrasenna="x"), "PRUEBA-hash-nuevo")

    assert sesion.llamadas == ["commit", "rollback"]
