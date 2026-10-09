"""Pruebas de T9 (spec 003b): cada paso de la recuperación de contraseña queda en la bitácora con su resultado (RF-21.1, RF-21.2,
RF-21.3, RF-21.5) y ni el código, ni la contraseña nueva, ni el correo completo quedan a la vista en lo que escribe el código de la
recuperación (RNF-08.1 y RNF-08.2, acotados a la recuperación).

Qué comprueban, siempre por la API como lo haría el navegador y mirando por dentro solo la bitácora y el Redis simulado:

- RF-21.1: cada uno de los seis resultados de la solicitud (`código enviado`, `envío fallido`, `correo no registrado`,
  `cuenta inactiva`, `límite alcanzado` y `servicio no disponible`) deja una fila de tipo «Recuperación de Contraseña» con su
  resultado, el correo normalizado y la `referencia`; la fila lleva el usuario cuando existe la cuenta (Activa o Inactiva) y no
  lo lleva cuando no existe ni cuando el servicio no está disponible. Una entrada inválida no deja fila.
- RF-21.2: un caso por cada resultado de la verificación y del cambio (también `servicio no disponible`) y el flujo completo
  deja una fila por paso, en orden, con la misma `referencia` y sin el correo en los pasos 2 y 3.
- RF-21.3: `GET /bitacora/registros?tipoAccion=6` como Administrador devuelve esas filas, incluidas las sin usuario, con su
  resultado en `informacionAdicional`; el Usuario Gubernamental no entra.
- RF-21.5: con el registro de la bitácora fallando, cada paso responde su resultado normal.
- RNF-08.1 y RNF-08.2: el flujo completo (entrada inválida, éxito, cada resultado, servicio no disponible y bitácora que falla)
  recorre SOLO las tres rutas de la recuperación y, en la salida capturada, los registros del servidor (`caplog` limitado al
  paquete `app`), las filas de bitácora, las respuestas y TODO el contenido del Redis simulado, no aparece ningún código ni
  ninguna contraseña nueva, y ninguna línea de registro lleva el correo completo. Control positivo: el código sí está en el
  correo, así que la búsqueda no es en vacío.

Usan la base `servia_pruebas`, el correo y el Redis simulados: nada sale de la prueba. Las cuentas son `PRUEBA`; las contraseñas
y los códigos inventados los genera la suite en cada corrida y el código real se lee del correo simulado y nunca se imprime.
Todo correo sin cuenta lleva «prueba» para que la limpieza por texto borre sus filas. Las filas de bitácora SIN usuario de los
pasos 2 y 3 no las alcanza esa limpieza: las borra la fixture `bitacora` de este archivo, por su `referencia`.
"""
import json
import logging
import secrets
from dataclasses import dataclass, field
from typing import List, Optional

import pytest
from sqlalchemy import text

from tests.soporte import datos, rastros
from tests.soporte import flujo_recuperacion as flujo
from tests.soporte.proteccion import exigir_nombre_pruebas

TIPO_RECUPERACION = 6  # TiposAccion.RECUPERACION_CONTRASENA
MENSAJE_DEL_ERS = "Si el correo existe en nuestro sistema, recibirás un email con las instrucciones"
MENSAJE_CORREO_INVALIDO = "Ingresa un correo electrónico válido"
MENSAJE_CODIGO_INCORRECTO = "Código de verificación incorrecto"
MENSAJE_CODIGO_VENCIDO = "El código ha expirado. Por favor, solicita un nuevo código de recuperación"
MENSAJE_PROCESO_VENCIDO = "El token de verificación ha expirado. Por favor, inicia el proceso de recuperación nuevamente"
MENSAJE_IGUAL_A_LA_ACTUAL = "La nueva contraseña debe ser diferente a la actual"
MENSAJE_CAMBIADO = "Contraseña recuperada exitosamente"
MENSAJE_VERIFICADO = "Código verificado correctamente"
MENSAJE_SERVICIO_NO_DISPONIBLE = (
    "El servicio de recuperación de contraseña no está disponible por el momento. Inténtalo de nuevo más tarde."
)

# Los resultados que fija la spec (RF-21.1 y RF-21.2).
ENVIADO, ENVIO_FALLIDO = "código enviado", "envío fallido"
NO_REGISTRADO, INACTIVA, LIMITE = "correo no registrado", "cuenta inactiva", "límite alcanzado"
SERVICIO_NO_DISPONIBLE = "servicio no disponible"
VERIFICADO, INCORRECTO, VENCIDO = "código verificado", "código incorrecto", "código vencido"
INVALIDADO = "código invalidado por intentos"
CAMBIADA, RECHAZADO = "contraseña cambiada", "cambio rechazado"


# --- Apoyo: las filas de bitácora y su limpieza -------------------------------------------------------------------------

@dataclass
class Fila:
    """Una fila de bitácora de recuperación: su identificador, su usuario, su texto y su información adicional."""

    id: int
    usuario: Optional[str]
    texto: str = field(repr=False)
    info_json: str = field(repr=False)

    @property
    def info(self) -> dict:
        return json.loads(self.info_json) if self.info_json else {}

    @property
    def resultado(self) -> Optional[str]:
        return self.info.get("resultado")

    @property
    def cruda(self):
        """Lo que se busca con `rastros`: el texto y la información adicional SIN su marca de tiempo.

        La marca trae microsegundos de seis dígitos y un código de seis dígitos podría coincidir con ellos por azar; el resto
        de la información (resultado, correo, referencia) es lo que podría llevar un dato que no debe estar."""
        sin_marca = {clave: valor for clave, valor in self.info.items() if clave != "timestamp"}
        return (self.texto, json.dumps(sin_marca, ensure_ascii=False))


class Bitacora:
    """Las filas de recuperación que deja UNA prueba: las posteriores a la marca que se tomó al empezar.

    `filas()` las lee de la base de pruebas (en orden) y anota sus `referencia`. Al terminar, `limpiar()` borra las que NO llevan
    usuario y cuya `referencia` anotó (o que no traen ninguna, como un token no reconocido): la limpieza por texto de la suite
    no las alcanza porque su texto no nombra el correo. Las que llevan usuario las borra la suite al borrar a ese usuario.
    """

    def __init__(self):
        self.marca = self._consultar("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora", {})[0][0]
        self.referencias = set()

    @staticmethod
    def _consultar(consulta, parametros):
        from app.db.database import engine

        with engine.connect() as conexion:
            return conexion.execute(text(consulta), parametros).fetchall()

    def filas(self) -> List[Fila]:
        registros = self._consultar(
            "SELECT CN_Id_bitacora, CN_Id_usuario, CT_Texto, CT_Informacion_adicional FROM T_Bitacora "
            "WHERE CN_Id_tipo_accion = :t AND CN_Id_bitacora > :m ORDER BY CN_Id_bitacora",
            {"t": TIPO_RECUPERACION, "m": self.marca},
        )
        filas = [Fila(r[0], r[1], r[2], r[3] or "") for r in registros]
        self.referencias.update(f.info["referencia"] for f in filas if f.info.get("referencia"))
        return filas

    def resultados(self) -> List[str]:
        return [fila.resultado for fila in self.filas()]

    def limpiar(self) -> None:
        from app.db.database import engine

        exigir_nombre_pruebas(engine.url.database, "la base de datos donde se borran las filas de bitácora de la prueba")
        propias = [
            f.id for f in self.filas()
            if f.usuario is None and (not f.info.get("referencia") or f.info["referencia"] in self.referencias)
        ]
        with engine.begin() as conexion:
            for identificador in propias:
                conexion.execute(text("DELETE FROM T_Bitacora WHERE CN_Id_bitacora = :i AND CN_Id_usuario IS NULL"), {"i": identificador})


@pytest.fixture
def bitacora(registro_de_datos):
    """Marca el último identificador de bitácora al empezar y entrega `Bitacora`; al terminar borra las filas sin usuario."""
    seguimiento = Bitacora()
    yield seguimiento
    seguimiento.limpiar()


@pytest.fixture
def nueva_cuenta(registro_de_datos):
    """Una función que crea una cuenta `PRUEBA` más (Usuario Gubernamental, Activa) y la deja registrada para su limpieza."""

    def _crear():
        return datos.crear_usuario(datos.ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)

    return _crear


@pytest.fixture
def cuenta_inactiva(cliente_api, iniciar_sesion, administrador, nueva_cuenta):
    """Una cuenta `PRUEBA` ya desactivada por el Administrador con `PUT /usuarios/{id}`, como lo hace la interfaz."""
    cuenta = nueva_cuenta()
    flujo.desactivar_cuenta(cliente_api, iniciar_sesion(administrador), cuenta)
    return cuenta


# --- Apoyo: el flujo --------------------------------------------------------------------------------------------------------

def _pedir(cliente_api, correo_simulado, cuenta):
    """Paso 1 con una cuenta Activa: devuelve el token de la solicitud y el código que llegó al correo simulado."""
    respuesta = flujo.solicitar(cliente_api, cuenta.correo)
    assert respuesta.status_code == 200
    return respuesta.json()["token"], flujo.codigo_enviado(correo_simulado)


def _verificar(cliente_api, correo_simulado, cuenta):
    """Pasos 1 y 2 con una cuenta Activa: devuelve `(token, token de verificación)`."""
    token, codigo = _pedir(cliente_api, correo_simulado, cuenta)
    verificada = flujo.verificar(cliente_api, token, codigo)
    assert verificada.status_code == 200
    return token, verificada.json()["verificationToken"]


def _ultima(bitacora) -> Fila:
    return bitacora.filas()[-1]


def _comprobar_fila(fila, *, resultado, usuario, referencia, paso=None, correo=None):
    """Una fila de recuperación: su resultado, su usuario (o ninguno), su referencia y, solo en la solicitud, el correo."""
    assert fila.resultado == resultado
    assert fila.usuario == usuario
    assert fila.info.get("referencia") == referencia
    assert "timestamp" in fila.info
    if paso is not None:
        assert fila.info.get("paso") == paso
    if correo is None:
        assert "email" not in fila.info, "solo la solicitud lleva el correo"
    else:
        assert fila.info.get("email") == correo


# --- RF-21.1: los seis resultados de la solicitud --------------------------------------------------------------------------------

def test_una_cuenta_activa_deja_la_fila_codigo_enviado_con_su_usuario_el_correo_normalizado_y_sin_el_codigo(
    cliente_api, correo_simulado, nueva_cuenta, bitacora
):
    """RF-21.1: la solicitud de una cuenta Activa registra `código enviado` con el usuario, el correo normalizado (aunque haya
    llegado con mayúsculas y espacios), la referencia del token y ningún código."""
    cuenta = nueva_cuenta()

    respuesta = flujo.solicitar(cliente_api, f"  {cuenta.correo.upper()} ")

    assert respuesta.status_code == 200
    filas = bitacora.filas()
    assert len(filas) == 1
    _comprobar_fila(
        filas[0], resultado=ENVIADO, usuario=cuenta.cedula, referencia=respuesta.json()["token"][:8], paso="solicitud",
        correo=cuenta.correo,
    )
    codigo = flujo.codigo_enviado(correo_simulado)
    assert rastros.encontrar_en_rastros(codigo, correo=correo_simulado.contenido_real().texto) == ["correo"]  # control positivo
    rastros.buscar_en_rastros(codigo, bitacora=filas[0].cruda)


def test_un_envio_fallido_deja_la_fila_envio_fallido_con_su_usuario(cliente_api, correo_simulado, nueva_cuenta, bitacora):
    """RF-21.1: si el servidor de correo falla, la persona recibe la respuesta de siempre y la fila dice `envío fallido`
    (el fallo del envío se informa solo en la bitácora), con el usuario de la cuenta Activa."""
    cuenta = nueva_cuenta()
    correo_simulado.fallar()

    respuesta = flujo.solicitar(cliente_api, cuenta.correo)

    assert (respuesta.status_code, respuesta.json()["message"]) == (200, MENSAJE_DEL_ERS)
    filas = bitacora.filas()
    assert len(filas) == 1
    _comprobar_fila(
        filas[0], resultado=ENVIO_FALLIDO, usuario=cuenta.cedula, referencia=respuesta.json()["token"][:8], paso="solicitud",
        correo=cuenta.correo,
    )


def test_un_correo_sin_cuenta_deja_la_fila_correo_no_registrado_sin_usuario(cliente_api, correo_simulado, bitacora):
    """RF-21.1: un correo sin cuenta registra `correo no registrado`, sin usuario, con el correo normalizado."""
    sin_cuenta = flujo.correo_sin_cuenta()

    respuesta = flujo.solicitar(cliente_api, f" {sin_cuenta.upper()}")

    assert respuesta.status_code == 200 and correo_simulado.intentos == []
    filas = bitacora.filas()
    assert len(filas) == 1
    _comprobar_fila(
        filas[0], resultado=NO_REGISTRADO, usuario=None, referencia=respuesta.json()["token"][:8], paso="solicitud",
        correo=sin_cuenta,
    )


def test_una_cuenta_inactiva_deja_la_fila_cuenta_inactiva_con_su_usuario_y_no_recibe_correo(
    cliente_api, correo_simulado, cuenta_inactiva, bitacora
):
    """RF-21.1: la cuenta Inactiva no recibe correo y la fila dice `cuenta inactiva` con su usuario."""
    respuesta = flujo.solicitar(cliente_api, cuenta_inactiva.correo)

    assert respuesta.status_code == 200 and correo_simulado.intentos == []
    filas = bitacora.filas()
    assert len(filas) == 1
    _comprobar_fila(
        filas[0], resultado=INACTIVA, usuario=cuenta_inactiva.cedula, referencia=respuesta.json()["token"][:8],
        paso="solicitud", correo=cuenta_inactiva.correo,
    )


def test_la_segunda_solicitud_antes_de_un_minuto_deja_la_fila_limite_alcanzado_con_su_usuario(
    cliente_api, correo_simulado, nueva_cuenta, bitacora
):
    """RF-21.1: la segunda solicitud del mismo correo antes de 60 s no envía nada y registra `límite alcanzado` con el
    usuario de la cuenta; las dos filas comparten la referencia (es el mismo correo)."""
    cuenta = nueva_cuenta()

    primera = flujo.solicitar(cliente_api, cuenta.correo)
    segunda = flujo.solicitar(cliente_api, cuenta.correo)

    assert len(correo_simulado.intentos) == 1
    filas = bitacora.filas()
    assert [f.resultado for f in filas] == [ENVIADO, LIMITE]
    _comprobar_fila(
        filas[1], resultado=LIMITE, usuario=cuenta.cedula, referencia=segunda.json()["token"][:8], paso="solicitud",
        correo=cuenta.correo,
    )
    assert primera.json()["token"][:8] == segunda.json()["token"][:8]


def test_con_redis_sin_respuesta_la_solicitud_deja_la_fila_servicio_no_disponible_sin_usuario_aunque_la_cuenta_exista(
    cliente_api, correo_simulado, redis_controlable, nueva_cuenta, bitacora
):
    """RF-21.1 y RF-03.20: con Redis caído la solicitud responde 503 y registra `servicio no disponible` SIN usuario (no se
    mira la cuenta), con el correo normalizado y la referencia del correo."""
    cuenta = nueva_cuenta()
    primera = flujo.solicitar(cliente_api, cuenta.correo)
    redis_controlable.no_responde("conexion")

    caida = flujo.solicitar(cliente_api, f" {cuenta.correo.upper()} ")

    assert (caida.status_code, caida.json()) == (503, {"detail": MENSAJE_SERVICIO_NO_DISPONIBLE})
    filas = bitacora.filas()
    assert [f.resultado for f in filas] == [ENVIADO, SERVICIO_NO_DISPONIBLE]
    _comprobar_fila(
        filas[1], resultado=SERVICIO_NO_DISPONIBLE, usuario=None, referencia=primera.json()["token"][:8], paso="solicitud",
        correo=cuenta.correo,
    )


def test_con_la_clave_de_firma_invalida_la_solicitud_deja_la_fila_servicio_no_disponible_sin_usuario_ni_referencia(
    cliente_api, correo_simulado, monkeypatch, nueva_cuenta, bitacora
):
    """RF-21.1 y RNF-07.3: con una clave de firma débil la solicitud responde 503 y registra `servicio no disponible` sin
    usuario y sin referencia (sin clave válida no hay huella), con el correo normalizado."""
    cuenta = nueva_cuenta()
    monkeypatch.setenv("JWT_SECRET_KEY", secrets.token_hex(15))  # 30 caracteres: débil

    caida = flujo.solicitar(cliente_api, cuenta.correo)

    assert caida.status_code == 503 and correo_simulado.intentos == []
    filas = bitacora.filas()
    assert len(filas) == 1
    _comprobar_fila(filas[0], resultado=SERVICIO_NO_DISPONIBLE, usuario=None, referencia=None, paso="solicitud", correo=cuenta.correo)


@pytest.mark.parametrize("cuerpo", [{"email": ""}, {"email": "sin-arroba"}, {"email": "a" * 101 + "@prueba.invalid"}, {}])
def test_una_entrada_invalida_en_la_solicitud_no_deja_ninguna_fila(cuerpo, cliente_api, correo_simulado, bitacora):
    """RF-21.1: un correo vacío, ausente o mal formado es entrada inválida (400) y no se registra (no es una solicitud)."""
    respuesta = cliente_api.post(flujo.RUTA_SOLICITAR, json=cuerpo)

    assert (respuesta.status_code, respuesta.json()) == (400, {"detail": MENSAJE_CORREO_INVALIDO})
    assert bitacora.filas() == []


# --- RF-21.2: los resultados de la verificación ------------------------------------------------------------------------------

def test_un_codigo_correcto_deja_la_fila_codigo_verificado_con_su_usuario_y_sin_el_correo(
    cliente_api, correo_simulado, nueva_cuenta, bitacora
):
    """RF-21.2: la verificación correcta registra `código verificado` con el usuario y la referencia del token, sin el correo
    y sin el código."""
    cuenta = nueva_cuenta()
    token, codigo = _pedir(cliente_api, correo_simulado, cuenta)

    verificada = flujo.verificar(cliente_api, token, codigo)

    assert (verificada.status_code, verificada.json()["message"]) == (200, MENSAJE_VERIFICADO)
    fila = _ultima(bitacora)
    _comprobar_fila(fila, resultado=VERIFICADO, usuario=cuenta.cedula, referencia=token[:8], paso="verificación del código")
    rastros.buscar_en_rastros(codigo, bitacora=fila.cruda)


def test_un_codigo_incorrecto_deja_la_fila_codigo_incorrecto_con_su_usuario(cliente_api, correo_simulado, nueva_cuenta, bitacora):
    """RF-21.2: un código incorrecto registra `código incorrecto` con el usuario de la cuenta Activa. El código inventado que se
    intentó tampoco queda en la fila."""
    cuenta = nueva_cuenta()
    token, codigo = _pedir(cliente_api, correo_simulado, cuenta)
    equivocado = flujo.codigo_inventado(distinto_de=codigo)

    respuesta = flujo.verificar(cliente_api, token, equivocado)

    assert (respuesta.status_code, respuesta.json()["detail"]) == (400, MENSAJE_CODIGO_INCORRECTO)
    fila = _ultima(bitacora)
    _comprobar_fila(fila, resultado=INCORRECTO, usuario=cuenta.cedula, referencia=token[:8], paso="verificación del código")
    rastros.buscar_en_rastros(equivocado, bitacora=fila.cruda)


def test_un_codigo_reemplazado_deja_la_fila_codigo_vencido_con_su_usuario(
    cliente_api, correo_simulado, redis_controlable, nueva_cuenta, bitacora
):
    """RF-21.2 y RF-03.4: un código que otra solicitud reemplazó responde vencido y registra `código vencido` con el usuario."""
    cuenta = nueva_cuenta()
    primero, codigo_primero = _pedir(cliente_api, correo_simulado, cuenta)
    redis_controlable.avanzar(61)
    flujo.solicitar(cliente_api, cuenta.correo)

    respuesta = flujo.verificar(cliente_api, primero, codigo_primero)

    assert (respuesta.status_code, respuesta.json()["detail"]) == (400, MENSAJE_CODIGO_VENCIDO)
    _comprobar_fila(
        _ultima(bitacora), resultado=VENCIDO, usuario=cuenta.cedula, referencia=primero[:8], paso="verificación del código"
    )


def test_un_estado_perdido_deja_la_fila_codigo_vencido_sin_usuario(
    cliente_api, correo_simulado, redis_controlable, nueva_cuenta, bitacora
):
    """RF-21.2 y RF-03.25: si Redis perdió el estado, el código correcto responde vencido y la fila no lleva usuario (ya no
    se sabe de quién era), pero sí la referencia."""
    cuenta = nueva_cuenta()
    token, codigo = _pedir(cliente_api, correo_simulado, cuenta)
    redis_controlable.perder_todas()

    respuesta = flujo.verificar(cliente_api, token, codigo)

    assert (respuesta.status_code, respuesta.json()["detail"]) == (400, MENSAJE_CODIGO_VENCIDO)
    _comprobar_fila(_ultima(bitacora), resultado=VENCIDO, usuario=None, referencia=token[:8], paso="verificación del código")


def test_un_token_no_reconocido_deja_la_fila_codigo_vencido_sin_usuario_ni_referencia(cliente_api, correo_simulado, bitacora):
    """RF-21.2: un token con otro formato responde «no reconocido» y registra `código vencido` (el conjunto de resultados es
    fijo), sin usuario y sin referencia."""
    respuesta = flujo.verificar(cliente_api, "esto-no-es-un-token", flujo.codigo_inventado())

    assert respuesta.status_code == 400
    _comprobar_fila(_ultima(bitacora), resultado=VENCIDO, usuario=None, referencia=None, paso="verificación del código")


def test_el_quinto_fallo_deja_la_fila_codigo_invalidado_por_intentos_y_el_codigo_correcto_despues_tambien(
    cliente_api, correo_simulado, nueva_cuenta, bitacora
):
    """RF-21.2 y RF-03.9: cuatro códigos incorrectos y luego el quinto fallo, que invalida el código (429); el código correcto
    que llega después también se rechaza por intentos y se registra igual."""
    cuenta = nueva_cuenta()
    token, codigo = _pedir(cliente_api, correo_simulado, cuenta)

    respuestas = [flujo.verificar(cliente_api, token, flujo.codigo_inventado(distinto_de=codigo)) for _ in range(5)]
    despues = flujo.verificar(cliente_api, token, codigo)

    assert [r.status_code for r in respuestas] == [400, 400, 400, 400, 429] and despues.status_code == 429
    assert bitacora.resultados() == [ENVIADO] + [INCORRECTO] * 4 + [INVALIDADO, INVALIDADO]
    for fila in bitacora.filas()[1:]:
        assert fila.usuario == cuenta.cedula and fila.info["referencia"] == token[:8]


def test_con_redis_sin_respuesta_la_verificacion_deja_la_fila_servicio_no_disponible_sin_usuario(
    cliente_api, correo_simulado, redis_controlable, nueva_cuenta, bitacora
):
    """RF-21.2 y RF-03.20: con Redis caído la verificación responde 503 y registra `servicio no disponible` sin usuario (no se
    sabe de qué cuenta es), con la referencia del token."""
    cuenta = nueva_cuenta()
    token, codigo = _pedir(cliente_api, correo_simulado, cuenta)
    redis_controlable.no_responde("tiempo")

    caida = flujo.verificar(cliente_api, token, codigo)

    assert (caida.status_code, caida.json()) == (503, {"detail": MENSAJE_SERVICIO_NO_DISPONIBLE})
    _comprobar_fila(
        _ultima(bitacora), resultado=SERVICIO_NO_DISPONIBLE, usuario=None, referencia=token[:8], paso="verificación del código"
    )


def test_con_la_clave_de_firma_invalida_la_verificacion_deja_la_fila_servicio_no_disponible(
    cliente_api, correo_simulado, monkeypatch, nueva_cuenta, bitacora
):
    """RF-21.2 y RNF-07.3: con una clave débil la verificación responde 503 y registra `servicio no disponible` (sin usuario;
    la referencia sale del token, que el navegador ya tenía)."""
    cuenta = nueva_cuenta()
    token, codigo = _pedir(cliente_api, correo_simulado, cuenta)
    monkeypatch.setenv("JWT_SECRET_KEY", secrets.token_hex(15))

    caida = flujo.verificar(cliente_api, token, codigo)

    assert caida.status_code == 503
    _comprobar_fila(
        _ultima(bitacora), resultado=SERVICIO_NO_DISPONIBLE, usuario=None, referencia=token[:8], paso="verificación del código"
    )


def test_el_codigo_incorrecto_de_un_correo_sin_cuenta_y_de_una_cuenta_inactiva_se_registran_como_los_de_una_cuenta_activa(
    cliente_api, correo_simulado, cuenta_inactiva, bitacora
):
    """RF-21.2 y RF-03.8: los pasos siguientes de un correo sin cuenta y de una cuenta Inactiva responden y se registran como
    `código incorrecto`; la fila lleva el usuario de la cuenta Inactiva y ninguno para el correo sin cuenta."""
    sin_cuenta = flujo.correo_sin_cuenta()
    token_sin_cuenta = flujo.solicitar(cliente_api, sin_cuenta).json()["token"]
    token_inactiva = flujo.solicitar(cliente_api, cuenta_inactiva.correo).json()["token"]

    r_sin_cuenta = flujo.verificar(cliente_api, token_sin_cuenta, flujo.codigo_inventado())
    r_inactiva = flujo.verificar(cliente_api, token_inactiva, flujo.codigo_inventado())

    assert (r_sin_cuenta.status_code, r_sin_cuenta.json()) == (r_inactiva.status_code, r_inactiva.json())
    filas = bitacora.filas()
    assert [f.resultado for f in filas] == [NO_REGISTRADO, INACTIVA, INCORRECTO, INCORRECTO]
    _comprobar_fila(filas[2], resultado=INCORRECTO, usuario=None, referencia=token_sin_cuenta[:8], paso="verificación del código")
    _comprobar_fila(
        filas[3], resultado=INCORRECTO, usuario=cuenta_inactiva.cedula, referencia=token_inactiva[:8], paso="verificación del código"
    )


def test_una_entrada_invalida_en_la_verificacion_y_en_el_cambio_no_deja_fila(cliente_api, correo_simulado, nueva_cuenta, bitacora):
    """RF-21.2: un código que no son 6 dígitos, un token vacío, una contraseña corta o sin datos son entrada inválida (400) y no
    se registran. Solo queda la fila de la solicitud."""
    cuenta = nueva_cuenta()
    token, verificacion = _verificar(cliente_api, correo_simulado, cuenta)

    assert flujo.verificar(cliente_api, token, "123").status_code == 400
    assert flujo.verificar(cliente_api, "", flujo.codigo_inventado()).status_code == 400
    assert flujo.cambiar(cliente_api, verificacion, "corta").status_code == 400
    assert flujo.cambiar(cliente_api, "", datos.generar_contrasena()).status_code == 400

    assert bitacora.resultados() == [ENVIADO, VERIFICADO]


# --- RF-21.2: los resultados del cambio ---------------------------------------------------------------------------------------------

def test_el_flujo_completo_deja_una_fila_por_paso_en_orden_con_la_misma_referencia_y_sin_el_correo_en_los_pasos_2_y_3(
    cliente_api, correo_simulado, nueva_cuenta, bitacora
):
    """RF-21.2: solicitar, verificar y cambiar dejan tres filas, en ese orden, cada una con su resultado, el usuario y la misma
    referencia; el correo solo está en la de la solicitud; ni el código ni la contraseña nueva quedan en ellas."""
    cuenta = nueva_cuenta()
    nueva = datos.generar_contrasena()
    token, codigo = _pedir(cliente_api, correo_simulado, cuenta)
    verificada = flujo.verificar(cliente_api, token, codigo)
    cambio = flujo.cambiar(cliente_api, verificada.json()["verificationToken"], nueva)

    assert (cambio.status_code, cambio.json()["message"]) == (200, MENSAJE_CAMBIADO)
    filas = bitacora.filas()
    assert [f.resultado for f in filas] == [ENVIADO, VERIFICADO, CAMBIADA]
    assert [f.info["paso"] for f in filas] == ["solicitud", "verificación del código", "cambio de contraseña"]
    assert [f.id for f in filas] == sorted(f.id for f in filas)
    assert {f.usuario for f in filas} == {cuenta.cedula}
    assert {f.info["referencia"] for f in filas} == {token[:8]}
    assert [("email" in f.info) for f in filas] == [True, False, False]
    for fila in filas:
        rastros.buscar_en_rastros(codigo, bitacora=fila.cruda)
        rastros.buscar_en_rastros(nueva, bitacora=fila.cruda)


def test_un_cambio_con_una_verificacion_vencida_deja_la_fila_cambio_rechazado_sin_usuario(
    cliente_api, correo_simulado, redis_controlable, nueva_cuenta, bitacora
):
    """RF-21.2 y RF-03.7: pasados los 10 minutos de la verificación el cambio responde proceso vencido y registra `cambio
    rechazado` sin usuario (la verificación ya no existe), con la referencia del token."""
    cuenta = nueva_cuenta()
    _, verificacion = _verificar(cliente_api, correo_simulado, cuenta)
    redis_controlable.avanzar(601)

    respuesta = flujo.cambiar(cliente_api, verificacion, datos.generar_contrasena())

    assert (respuesta.status_code, respuesta.json()["detail"]) == (400, MENSAJE_PROCESO_VENCIDO)
    _comprobar_fila(
        _ultima(bitacora), resultado=RECHAZADO, usuario=None, referencia=verificacion[:8], paso="cambio de contraseña"
    )


def test_un_cambio_de_una_cuenta_desactivada_despues_de_verificar_deja_la_fila_cambio_rechazado_con_su_usuario(
    cliente_api, iniciar_sesion, administrador, correo_simulado, nueva_cuenta, bitacora
):
    """RF-21.2 y RF-03.6: si el Administrador desactiva la cuenta después de verificar, el cambio se rechaza como proceso
    vencido y la fila `cambio rechazado` lleva el usuario de la cuenta (la verificación vigente lo conserva)."""
    cuenta = nueva_cuenta()
    _, verificacion = _verificar(cliente_api, correo_simulado, cuenta)
    flujo.desactivar_cuenta(cliente_api, iniciar_sesion(administrador), cuenta)

    respuesta = flujo.cambiar(cliente_api, verificacion, datos.generar_contrasena())

    assert (respuesta.status_code, respuesta.json()["detail"]) == (400, MENSAJE_PROCESO_VENCIDO)
    _comprobar_fila(
        _ultima(bitacora), resultado=RECHAZADO, usuario=cuenta.cedula, referencia=verificacion[:8], paso="cambio de contraseña"
    )


def test_una_contrasena_igual_a_la_actual_deja_cambio_rechazado_y_el_reintento_deja_contrasena_cambiada(
    cliente_api, correo_simulado, nueva_cuenta, bitacora
):
    """RF-21.2 y RF-03.7: «igual a la actual» se rechaza (la verificación sigue vigente) y se registra `cambio rechazado` con el
    usuario; el reintento con otra contraseña registra `contraseña cambiada`."""
    cuenta = nueva_cuenta()
    _, verificacion = _verificar(cliente_api, correo_simulado, cuenta)

    igual = flujo.cambiar(cliente_api, verificacion, cuenta.contrasena)
    reintento = flujo.cambiar(cliente_api, verificacion, datos.generar_contrasena())

    assert (igual.status_code, igual.json()["detail"]) == (400, MENSAJE_IGUAL_A_LA_ACTUAL) and reintento.status_code == 200
    filas = bitacora.filas()
    assert [f.resultado for f in filas] == [ENVIADO, VERIFICADO, RECHAZADO, CAMBIADA]
    assert {f.usuario for f in filas} == {cuenta.cedula}


def test_un_token_de_verificacion_no_reconocido_deja_la_fila_cambio_rechazado_sin_usuario_ni_referencia(
    cliente_api, correo_simulado, bitacora
):
    """RF-21.2: un token de verificación con otro formato responde proceso vencido y registra `cambio rechazado` sin usuario y
    sin referencia."""
    respuesta = flujo.cambiar(cliente_api, "esto-no-es-un-token", datos.generar_contrasena())

    assert (respuesta.status_code, respuesta.json()["detail"]) == (400, MENSAJE_PROCESO_VENCIDO)
    _comprobar_fila(_ultima(bitacora), resultado=RECHAZADO, usuario=None, referencia=None, paso="cambio de contraseña")


def test_con_redis_sin_respuesta_el_cambio_deja_la_fila_servicio_no_disponible_sin_usuario(
    cliente_api, correo_simulado, redis_controlable, nueva_cuenta, bitacora
):
    """RF-21.2 y RF-03.20: con Redis caído el cambio responde 503 y registra `servicio no disponible` sin usuario, con la
    referencia del token de verificación; la contraseña no cambia."""
    cuenta = nueva_cuenta()
    _, verificacion = _verificar(cliente_api, correo_simulado, cuenta)
    redis_controlable.no_responde("conexion")

    caida = flujo.cambiar(cliente_api, verificacion, datos.generar_contrasena())

    assert (caida.status_code, caida.json()) == (503, {"detail": MENSAJE_SERVICIO_NO_DISPONIBLE})
    _comprobar_fila(
        _ultima(bitacora), resultado=SERVICIO_NO_DISPONIBLE, usuario=None, referencia=verificacion[:8], paso="cambio de contraseña"
    )
    redis_controlable.responder_bien()
    assert cliente_api.post("/auth/login", json={"email": cuenta.correo, "password": cuenta.contrasena}).status_code == 200


# --- RF-21.3: la consulta del Historial --------------------------------------------------------------------------------------------

def test_la_consulta_por_tipo_devuelve_las_filas_de_recuperacion_tambien_las_sin_usuario_con_su_resultado(
    cliente_api, iniciar_sesion, administrador, correo_simulado, redis_controlable, nueva_cuenta, bitacora
):
    """RF-21.3: `GET /bitacora/registros?tipoAccion=6` como Administrador devuelve las filas de recuperación, también las sin
    usuario (correo sin cuenta, servicio no disponible, verificación sin estado), y cada una trae su resultado en
    `informacionAdicional`."""
    cuenta, sin_cuenta = nueva_cuenta(), flujo.correo_sin_cuenta()
    _, verificacion = _verificar(cliente_api, correo_simulado, cuenta)
    flujo.solicitar(cliente_api, sin_cuenta)
    redis_controlable.no_responde("conexion")
    flujo.cambiar(cliente_api, verificacion, datos.generar_contrasena())
    redis_controlable.responder_bien()
    propias = bitacora.filas()
    assert len(propias) == 4

    respuesta = cliente_api.get(
        "/bitacora/registros", params={"tipoAccion": TIPO_RECUPERACION, "limite": 100}, headers=iniciar_sesion(administrador)
    )

    assert respuesta.status_code == 200
    items = respuesta.json()["items"]
    assert items and all(item["idTipoAccion"] == TIPO_RECUPERACION for item in items)
    referencias = {fila.info.get("referencia") for fila in propias}
    devueltas = [i for i in items if json.loads(i["informacionAdicional"] or "{}").get("referencia") in referencias]
    assert sorted(json.loads(i["informacionAdicional"])["resultado"] for i in devueltas) == sorted(
        [ENVIADO, VERIFICADO, NO_REGISTRADO, SERVICIO_NO_DISPONIBLE]
    )
    sin_usuario = [i for i in devueltas if i["idUsuario"] is None]
    assert sorted(json.loads(i["informacionAdicional"])["resultado"] for i in sin_usuario) == sorted(
        [NO_REGISTRADO, SERVICIO_NO_DISPONIBLE]
    )


def test_el_usuario_gubernamental_no_puede_consultar_la_bitacora(cliente_api, iniciar_sesion, usuario_gubernamental):
    """RF-21.3: el Historial de Actividades es del Administrador; el Usuario Gubernamental recibe 403."""
    respuesta = cliente_api.get(
        "/bitacora/registros", params={"tipoAccion": TIPO_RECUPERACION}, headers=iniciar_sesion(usuario_gubernamental)
    )

    assert respuesta.status_code == 403


# --- RF-21.5: si la bitácora falla, la acción sigue ---------------------------------------------------------------------------------

def test_con_la_bitacora_fallando_cada_paso_responde_su_resultado_normal(
    cliente_api, correo_simulado, redis_controlable, monkeypatch, nueva_cuenta, bitacora
):
    """RF-21.5: con `BitacoraService.registrar` fallando, la solicitud responde la respuesta uniforme (y el correo sale), la
    verificación y el cambio responden su resultado, y los errores (código incorrecto, 503) siguen siendo los de siempre. No
    queda ninguna fila ni el texto de la excepción en los registros del servidor."""
    from app.services.bitacora.bitacora_service import BitacoraService

    cuenta = nueva_cuenta()
    nueva = datos.generar_contrasena()

    async def falla(self, *args, **kwargs):
        raise RuntimeError(f"PRUEBA la bitácora no responde ({cuenta.correo})")

    monkeypatch.setattr(BitacoraService, "registrar", falla)

    solicitud = flujo.solicitar(cliente_api, cuenta.correo)
    codigo = flujo.codigo_enviado(correo_simulado)
    incorrecto = flujo.verificar(cliente_api, solicitud.json()["token"], flujo.codigo_inventado(distinto_de=codigo))
    verificada = flujo.verificar(cliente_api, solicitud.json()["token"], codigo)
    cambio = flujo.cambiar(cliente_api, verificada.json()["verificationToken"], nueva)
    redis_controlable.no_responde("conexion")
    caida = flujo.solicitar(cliente_api, cuenta.correo)
    redis_controlable.responder_bien()

    assert (solicitud.status_code, solicitud.json()["message"]) == (200, MENSAJE_DEL_ERS) and len(correo_simulado.intentos) == 1
    assert (incorrecto.status_code, incorrecto.json()["detail"]) == (400, MENSAJE_CODIGO_INCORRECTO)
    assert (verificada.status_code, verificada.json()["message"]) == (200, MENSAJE_VERIFICADO)
    assert (cambio.status_code, cambio.json()["message"]) == (200, MENSAJE_CAMBIADO)
    assert (caida.status_code, caida.json()) == (503, {"detail": MENSAJE_SERVICIO_NO_DISPONIBLE})
    assert bitacora.filas() == []
    assert cliente_api.post("/auth/login", json={"email": cuenta.correo, "password": str(nueva)}).status_code == 200


# --- RNF-08.1 y RNF-08.2: nada que no deba verse, en todo el flujo ------------------------------------------------------------------

def _contenido_de_redis(redis_controlable) -> List[str]:
    """TODO lo que hay en el Redis simulado de la recuperación: cada clave y cada valor (campos y valores de los hashes)."""
    textos = []
    for clave in redis_controlable.claves("*"):
        tipo = redis_controlable.type(clave)
        valor = redis_controlable.hgetall(clave) if tipo == "hash" else redis_controlable.get(clave)
        textos.extend([clave, json.dumps(valor, ensure_ascii=False)])
    return textos


def _cuerpo_sin_tokens(respuesta) -> str:
    """El cuerpo de una respuesta sin el valor de sus tokens: que ningún token se derive del código ya lo prueba, para los 10^6
    códigos, `test_recuperacion_codigo_no_deducible.py`; aquí un token es un texto largo y, sin quitarlo, un código de seis
    dígitos podría coincidir con él por azar."""
    try:
        cuerpo = respuesta.json()
    except ValueError:
        return respuesta.text
    if isinstance(cuerpo, dict):
        cuerpo = {k: ("[token]" if k in ("token", "verificationToken") else v) for k, v in cuerpo.items()}
    return json.dumps(cuerpo, ensure_ascii=False)


def test_el_flujo_completo_no_deja_el_codigo_ni_la_contrasena_ni_el_correo_completo_en_ningun_rastro(
    cliente_api, correo_simulado, redis_controlable, monkeypatch, caplog, capsys, nueva_cuenta, cuenta_inactiva, bitacora,
):
    """RNF-08.1 y RNF-08.2 (acotados a la recuperación): el flujo completo recorre SOLO las tres rutas de la recuperación
    (entrada inválida, éxito, cada resultado de la solicitud, la verificación y el cambio, el servicio no disponible y la
    bitácora que falla) y, en la salida capturada, los registros del servidor, las filas de bitácora, las respuestas y todo el
    Redis simulado, no aparece ningún código ni ninguna contraseña nueva; y ninguna línea de registro lleva un correo completo.
    Control positivo: cada código sí está en su correo, y los correos enmascarados sí están en los registros."""
    from app.services.bitacora.bitacora_service import BitacoraService
    from app.repositories.bitacora_repository import BitacoraRepository
    from app.utils.enmascarar import enmascarar_correo

    # Las cuentas y el administrador se preparan ANTES de capturar: esas rutas (usuarios, inicio de sesión) no son de esta spec.
    exitosa, bloqueada, cuenta_c, envio_fallido, con_bitacora_rota = (nueva_cuenta() for _ in range(5))
    sin_cuenta = flujo.correo_sin_cuenta()
    inactiva = cuenta_inactiva
    correos = [c.correo for c in (exitosa, bloqueada, cuenta_c, envio_fallido, con_bitacora_rota, inactiva)] + [sin_cuenta]
    caplog.set_level(logging.DEBUG, logger="app")
    caplog.clear()
    capsys.readouterr()

    respuestas, codigos, contrasenas = [], [], []

    def anotar(respuesta):
        respuestas.append(respuesta)
        return respuesta

    # 1. Entrada inválida en los tres pasos.
    anotar(cliente_api.post(flujo.RUTA_SOLICITAR, json={"email": "sin-arroba"}))
    anotar(flujo.verificar(cliente_api, "esto-no-es-un-token", "123"))
    anotar(flujo.cambiar(cliente_api, "esto-no-es-un-token", "corta"))

    # 2. Éxito, con una contraseña «igual a la actual» y un cambio repetido por el camino.
    token = anotar(flujo.solicitar(cliente_api, f" {exitosa.correo.upper()} ")).json()["token"]
    codigo = flujo.codigo_enviado(correo_simulado)
    codigos.append(codigo)
    incorrecto = flujo.codigo_inventado(distinto_de=codigo)
    codigos.append(incorrecto)
    anotar(flujo.verificar(cliente_api, token, incorrecto))
    verificacion = anotar(flujo.verificar(cliente_api, token, codigo)).json()["verificationToken"]
    contrasenas.append(exitosa.contrasena)
    anotar(flujo.cambiar(cliente_api, verificacion, exitosa.contrasena))
    nueva = datos.generar_contrasena()
    contrasenas.append(nueva)
    anotar(flujo.cambiar(cliente_api, verificacion, nueva))
    anotar(flujo.cambiar(cliente_api, verificacion, nueva))  # la verificación ya se gastó: proceso vencido

    # 3. Cada resultado de la solicitud: límite, sin cuenta, inactiva, envío fallido.
    anotar(flujo.solicitar(cliente_api, bloqueada.correo))
    codigos.append(flujo.codigo_enviado(correo_simulado))
    anotar(flujo.solicitar(cliente_api, bloqueada.correo))
    anotar(flujo.solicitar(cliente_api, sin_cuenta))
    anotar(flujo.solicitar(cliente_api, inactiva.correo))
    correo_simulado.fallar()
    anotar(flujo.solicitar(cliente_api, envio_fallido.correo))
    codigos.append(flujo.codigo_enviado(correo_simulado))  # el correo que no llegó a salir también trae un código
    correo_simulado.responder_bien()

    # 4. El código invalidado por intentos.
    token_c = anotar(flujo.solicitar(cliente_api, cuenta_c.correo)).json()["token"]
    codigo_c = flujo.codigo_enviado(correo_simulado)
    codigos.append(codigo_c)
    for _ in range(5):
        equivocado = flujo.codigo_inventado(distinto_de=codigo_c)
        codigos.append(equivocado)
        anotar(flujo.verificar(cliente_api, token_c, equivocado))
    anotar(flujo.verificar(cliente_api, token_c, codigo_c))

    # 5. Servicio no disponible: Redis caído y clave de firma débil, en los tres pasos.
    redis_controlable.no_responde("conexion")
    anotar(flujo.solicitar(cliente_api, exitosa.correo))
    anotar(flujo.verificar(cliente_api, token, codigo))
    anotar(flujo.cambiar(cliente_api, verificacion, nueva))
    redis_controlable.responder_bien()
    with monkeypatch.context() as parche:
        parche.setenv("JWT_SECRET_KEY", secrets.token_hex(15))
        anotar(flujo.solicitar(cliente_api, exitosa.correo))
        anotar(flujo.verificar(cliente_api, token, codigo))

    # 6. La bitácora que falla (con el correo y un código en el texto de su error), en los tres pasos.
    clave_c = secrets.token_hex(8)
    contenido_del_error = f"PRUEBA fallo de la bitácora {con_bitacora_rota.correo} {clave_c}"

    def crear_roto(self, *args, **kwargs):
        raise RuntimeError(contenido_del_error)

    with monkeypatch.context() as parche:
        parche.setattr(BitacoraRepository, "crear", crear_roto)
        token_r = anotar(flujo.solicitar(cliente_api, con_bitacora_rota.correo)).json()["token"]
        codigo_r = flujo.codigo_enviado(correo_simulado)
        codigos.append(codigo_r)
        verificacion_r = anotar(flujo.verificar(cliente_api, token_r, codigo_r)).json()["verificationToken"]
        nueva_r = datos.generar_contrasena()
        contrasenas.append(nueva_r)
        anotar(flujo.cambiar(cliente_api, verificacion_r, nueva_r))

    # --- Lo que quedó a la vista ---
    salida = capsys.readouterr()
    registros = caplog.text
    filas = bitacora.filas()
    redis_controlable.responder_bien()
    en_redis = _contenido_de_redis(redis_controlable)
    cuerpos = [_cuerpo_sin_tokens(r) for r in respuestas]
    todos = list(contrasenas) + list(codigos)

    # Control positivo: la búsqueda no es en vacío.
    correos_enviados = [correo_simulado.contenido_real(i).texto for i in range(len(correo_simulado.intentos))]
    for codigo_enviado in (codigo, codigo_c, codigo_r):
        assert rastros.encontrar_en_rastros(codigo_enviado, correos=correos_enviados) == ["correos"]
    assert "Solicitud de recuperación atendida" in registros, "el registro del servidor de la recuperación no se capturó"
    assert enmascarar_correo(exitosa.correo) in registros, "los correos enmascarados deben estar en los registros"
    assert [f.resultado for f in filas] == (
        [ENVIADO, INCORRECTO, VERIFICADO, RECHAZADO, CAMBIADA, RECHAZADO]  # 2. éxito, «igual a la actual» y cambio repetido
        + [ENVIADO, LIMITE, NO_REGISTRADO, INACTIVA, ENVIO_FALLIDO]  # 3. cada resultado de la solicitud
        + [ENVIADO] + [INCORRECTO] * 4 + [INVALIDADO, INVALIDADO]  # 4. el código invalidado por intentos
        + [SERVICIO_NO_DISPONIBLE] * 5  # 5. Redis caído (3 pasos) y clave débil (2 pasos)
    ), "las filas de bitácora de la recuperación no son las del recorrido (la entrada inválida y la bitácora rota no dejan ninguna)"
    assert en_redis, "el Redis simulado debe tener estados de la recuperación"
    assert any(token_c.split(".")[1] in texto for texto in en_redis), "el contenido de Redis debe incluir la emisión de un token"

    # RNF-08.1: ningún código ni contraseña, en ninguna fuente.
    for secreto in todos:
        assert rastros.encontrar_en_rastros(
            secreto,
            salida=salida.out + salida.err,
            registros=registros,
            bitacora=[f.cruda for f in filas],
            respuestas=cuerpos,
            redis=en_redis,
        ) == [], "un código o una contraseña apareció en una fuente (no se muestra cuál)"

    # RNF-08.2: ninguna línea de registro lleva un correo completo ni el texto de un error de la bitácora.
    for correo in correos:
        assert correo.lower() not in registros.lower(), "un registro del servidor lleva un correo completo"
        assert correo.lower() not in (salida.out + salida.err).lower(), "la salida lleva un correo completo"
    # Lo que escribe el código de la recuperación y sus métodos de bitácora lleva solo el tipo de la excepción. (El servicio
    # general de bitácora, de la spec 003a, sí escribe el texto del error de su INSERT, con el correo ya enmascarado.)
    de_la_recuperacion = "\n".join(
        r.getMessage() for r in caplog.records
        if r.name in ("app.routes.auth", "app.services.recuperacion_service", "app.services.bitacora.auth_audit_service")
    )
    assert "No se pudo registrar el paso" in de_la_recuperacion, "control positivo: el fallo de la bitácora se registró"
    assert "fallo de la bitácora" not in de_la_recuperacion and clave_c not in de_la_recuperacion, (
        "el texto de un error no debe quedar en los registros de la recuperación"
    )
    assert not any(
        c.correo.lower() in cuerpo.lower() for c in (exitosa, bloqueada, cuenta_c, envio_fallido, con_bitacora_rota, inactiva)
        for cuerpo in cuerpos
    ), "una respuesta lleva un correo completo"
