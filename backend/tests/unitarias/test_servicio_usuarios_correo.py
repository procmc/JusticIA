"""Pruebas de T5 (spec 003a): crear y resetear una cuenta no dejan la contraseña temporal ni el correo completo en los rastros.

Cubren RNF-08.1 (la contraseña temporal solo viaja en el correo) y RNF-08.2 (el correo de una persona no se escribe
en claro en los registros del servidor) para el servicio de usuarios, con el repositorio y la sesión simulados: no
hay base de datos. Cada flujo (crear y resetear) se prueba con el correo funcionando, con el servidor de correo en
fallo, con una excepción inesperada del envío y sin servicio de correo (`email_service = None`), y se busca el valor
en la salida capturada (`capfd`) y en los registros en nivel DEBUG (`caplog`).

Datos inventados (prefijo `PRUEBA`, dominio `.invalid`); la contraseña temporal la genera el servicio y la prueba la
lee de lo que recibió el repositorio simulado (nunca se imprime). Los casos de T6 y T7 (código HTTP, texto de la
respuesta, orden de guardado y envío) se suman a este archivo en esas tareas.
"""
import asyncio
import logging
from types import SimpleNamespace

import aiosmtplib
import pytest

from tests.soporte import rastros
from tests.soporte.datos import Contrasena

CEDULA = "PRUEBA900001"
CORREO = "prueba.persona@prueba.invalid"
CLAVE_DEL_SERVIDOR = "PRUEBA-clave-del-servidor-4417"
# Lo que diría un servidor de correo (o una excepción interna) al fallar: lleva el correo y una clave.
TEXTO_DEL_ERROR = f"535 PRUEBA-detalle-inventado {CORREO} clave={CLAVE_DEL_SERVIDOR}"


class RepositorioSimulado:
    """Hace de `UsuarioRepository` sin base de datos: devuelve un usuario inventado y guarda la contraseña que recibe.

    Acepta `**opciones` y los métodos de confirmar o descartar para que las pruebas de T6 y T7 reutilicen este archivo.
    """

    def __init__(self, correo: str):
        self.usuario = SimpleNamespace(
            CN_Id_usuario=CEDULA, CT_Nombre_usuario="PRUEBA_persona", CT_Nombre="PRUEBA", CT_Apellido_uno="Peña",
            CT_Apellido_dos="Núñez", CT_Correo=correo, CN_Id_rol=2, CN_Id_estado=1, CF_Ultimo_acceso=None,
            CF_Fecha_creacion=None, rol=SimpleNamespace(CN_Id_rol=2, CT_Nombre_rol="Usuario Judicial"),
            estado=SimpleNamespace(CN_Id_estado=1, CT_Nombre_estado="Activo"),
        )
        self.contrasenas = []  # las que el servicio quiso guardar, ya envueltas para que no se impriman
        # Lo que el servicio le pidió al repositorio (y el envío, que anotan las pruebas de T6), en orden.
        self.eventos = []
        self.error_al_confirmar = None  # si se define, `confirmar_cambios` lo lanza (el commit falló)
        self.expira_al_descartar = False  # como un `rollback` real: los atributos del usuario dejan de estar disponibles

    def crear_usuario(self, db, cedula, nombre_usuario, nombre, apellido_uno, apellido_dos, correo, contrasenna, id_rol):
        self.contrasenas.append(Contrasena(contrasenna))
        return self.usuario

    def obtener_usuario_por_id(self, db, usuario_id):
        return self.usuario

    def resetear_contrasenna(self, db, usuario_id, nueva_contrasenna, **opciones):
        self.contrasenas.append(Contrasena(nueva_contrasenna))
        self.eventos.append(f"guardar(confirmar={opciones.get('confirmar', True)})")
        return self.usuario

    def confirmar_cambios(self, db):
        self.eventos.append("confirmar")
        if self.error_al_confirmar is not None:
            raise self.error_al_confirmar

    def descartar_cambios(self, db):
        self.eventos.append("descartar")
        if self.expira_al_descartar and self.usuario is not None:
            self.usuario.CT_Correo = None


@pytest.fixture
def servicio(correo_simulado):
    """El servicio de usuarios real, con el repositorio simulado y el correo simulado (nada sale de la prueba)."""
    from app.services.usuario_service import UsuarioService

    servicio = UsuarioService()
    servicio.repository = RepositorioSimulado(CORREO)
    return servicio


def _preparar(escenario, servicio, correo_simulado, monkeypatch):
    """Deja el envío de correo en el escenario pedido."""
    if escenario == "fallo":
        correo_simulado.fallar(aiosmtplib.SMTPResponseException(535, TEXTO_DEL_ERROR))
    elif escenario == "excepcion":
        async def _lanza(*args, **kwargs):
            raise RuntimeError(TEXTO_DEL_ERROR)

        monkeypatch.setattr(servicio.email_service, "send_password_email", _lanza)
        monkeypatch.setattr(servicio.email_service, "send_password_reset_email", _lanza)
    elif escenario == "sin_servicio":
        servicio.email_service = None


def _ejecutar(operacion, servicio):
    """Corre el flujo completo; el resultado no importa aquí (lo prueban T6 y T7), solo lo que dejó en los rastros."""
    if operacion == "crear":
        asyncio.run(servicio.crear_usuario(None, CEDULA, "PRUEBA_persona", "PRUEBA", "Peña", "Núñez", CORREO, 2))
    else:
        asyncio.run(servicio.resetear_contrasenna_usuario(None, CEDULA))


ESCENARIOS = ["exito", "fallo", "excepcion", "sin_servicio"]
OPERACIONES = ["crear", "resetear"]


@pytest.mark.parametrize("operacion", OPERACIONES)
@pytest.mark.parametrize("escenario", ESCENARIOS)
def test_la_contrasena_temporal_no_queda_en_la_salida_ni_en_los_registros(
        escenario, operacion, servicio, correo_simulado, monkeypatch, capfd, caplog):
    """RNF-08.1: ni el flujo exitoso ni los fallidos escriben la contraseña temporal en la salida o en los registros (DEBUG).

    Con el correo funcionando o en fallo, el control positivo comprueba que la temporal sí está en el mensaje que el
    sistema armó: así la búsqueda no es una búsqueda en vacío.
    """
    caplog.set_level(logging.DEBUG)
    _preparar(escenario, servicio, correo_simulado, monkeypatch)

    _ejecutar(operacion, servicio)

    temporal = servicio.repository.contrasenas[-1]
    if escenario in ("exito", "fallo"):
        contenido = correo_simulado.contenido_real()
        assert rastros.encontrar_en_rastros(temporal, correo=[contenido.texto, contenido.html]) == ["correo"]
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(temporal, salida=salida.out + salida.err, registros=caplog.text)


@pytest.mark.parametrize("operacion", OPERACIONES)
@pytest.mark.parametrize("escenario", ESCENARIOS)
def test_el_correo_completo_y_el_texto_del_error_no_quedan_en_los_registros(
        escenario, operacion, servicio, correo_simulado, monkeypatch, capfd, caplog):
    """RNF-08.2, RF-03.17: el correo de la persona y el texto del error del servidor (que lo repite) no aparecen en claro en los registros."""
    caplog.set_level(logging.DEBUG)
    _preparar(escenario, servicio, correo_simulado, monkeypatch)

    _ejecutar(operacion, servicio)

    if escenario in ("exito", "fallo"):  # control positivo: el correo sí es el destinatario del mensaje armado
        assert rastros.encontrar_en_rastros(CORREO, correo=[correo_simulado.contenido_real().a]) == ["correo"]
    salida = capfd.readouterr()
    for secreto in (CORREO, CLAVE_DEL_SERVIDOR):
        rastros.buscar_en_rastros(secreto, salida=salida.out + salida.err, registros=caplog.text)


# --- T6: restablecimiento por el Administrador (RF-03.13, RF-03.14) -------------------------------------------------------
# El orden de los pasos (guardar sin confirmar, enviar y recién entonces confirmar o descartar) y los textos de la respuesta.
# La base real, el código HTTP y la bitácora se prueban en `tests/integracion/test_reseteo_por_administrador.py`.

MENSAJE_EXITOSO = "Contraseña reseteada exitosamente"
MENSAJE_FALLIDO = (
    f"No se pudo enviar el correo a {CORREO}. La contraseña no fue modificada. "
    "Verifique el servicio de correo e inténtelo de nuevo."
)
GUARDAR_SIN_CONFIRMAR = "guardar(confirmar=False)"


def _anotar_el_envio(servicio, monkeypatch, entregado=True, error=None):
    """El envío del reseteo anota "enviar" en la lista de eventos del repositorio y devuelve lo que se pida (o lanza `error`).

    Devuelve la lista de lo que recibió el envío (destinatario, nombre y una `Contrasena`), para comprobar los argumentos.
    """
    recibidos = []

    async def _enviar(to_email, user_name, new_password):
        servicio.repository.eventos.append("enviar")
        recibidos.append({"to_email": to_email, "user_name": user_name, "new_password": Contrasena(new_password)})
        if error is not None:
            raise error
        return entregado

    monkeypatch.setattr(servicio.email_service, "send_password_reset_email", _enviar)
    return recibidos


def _resetear(servicio):
    return asyncio.run(servicio.resetear_contrasenna_usuario(None, CEDULA))


def test_reseteo_con_envio_exitoso_guarda_sin_confirmar_envia_y_confirma(servicio, monkeypatch):
    """RF-03.13, RF-03.14: el orden es guardar sin confirmar (flush) -> enviar -> confirmar; la respuesta trae el texto exacto."""
    from app.services.usuario_service import ResultadoReseteo

    _anotar_el_envio(servicio, monkeypatch, entregado=True)

    resultado = _resetear(servicio)

    assert servicio.repository.eventos == [GUARDAR_SIN_CONFIRMAR, "enviar", "confirmar"]
    assert resultado == ResultadoReseteo(entregada=True, mensaje=MENSAJE_EXITOSO)


def test_reseteo_con_envio_fallido_descarta_los_cambios_y_dice_que_la_contrasena_no_se_modifico(servicio, monkeypatch):
    """RF-03.14: si el envío falla (devuelve False) los cambios se descartan y el texto lleva el correo del usuario."""
    from app.services.usuario_service import ResultadoReseteo

    _anotar_el_envio(servicio, monkeypatch, entregado=False)

    resultado = _resetear(servicio)

    assert servicio.repository.eventos == [GUARDAR_SIN_CONFIRMAR, "enviar", "descartar"]
    assert resultado == ResultadoReseteo(entregada=False, mensaje=MENSAJE_FALLIDO)


def test_reseteo_con_una_excepcion_en_el_envio_se_trata_como_envio_fallido(servicio, monkeypatch):
    """RF-03.14, RF-03.17: una excepción inesperada del envío no se propaga: es un envío fallido y se descartan los cambios."""
    _anotar_el_envio(servicio, monkeypatch, error=RuntimeError(TEXTO_DEL_ERROR))

    resultado = _resetear(servicio)

    assert servicio.repository.eventos == [GUARDAR_SIN_CONFIRMAR, "enviar", "descartar"]
    assert resultado.entregada is False
    assert resultado.mensaje == MENSAJE_FALLIDO
    assert CLAVE_DEL_SERVIDOR not in resultado.mensaje


def test_reseteo_con_el_servicio_de_correo_ausente_descarta_los_cambios_sin_intentar_enviar(servicio, correo_simulado):
    """RF-03.14, RF-03.17: con `email_service = None` (configuración inválida al arrancar) el reseteo falla sin enviar nada."""
    servicio.email_service = None

    resultado = _resetear(servicio)

    assert servicio.repository.eventos == [GUARDAR_SIN_CONFIRMAR, "descartar"]
    assert resultado.entregada is False
    assert resultado.mensaje == MENSAJE_FALLIDO
    assert correo_simulado.intentos == []


def test_si_se_cancela_el_envio_se_descartan_los_cambios_y_la_cancelacion_sigue(servicio, monkeypatch):
    """RF-03.14: un cierre de la petición (cancelación) mientras se envía no deja el cambio sin confirmar ni sin descartar."""

    async def _escenario():
        envio_en_curso = asyncio.Event()

        async def _cuelga(to_email, user_name, new_password):
            servicio.repository.eventos.append("enviar")
            envio_en_curso.set()
            await asyncio.get_running_loop().create_future()  # nadie lo resuelve: solo una cancelación lo termina

        monkeypatch.setattr(servicio.email_service, "send_password_reset_email", _cuelga)
        tarea = asyncio.ensure_future(servicio.resetear_contrasenna_usuario(None, CEDULA))
        await asyncio.wait_for(envio_en_curso.wait(), timeout=2)
        tarea.cancel()
        with pytest.raises(asyncio.CancelledError):
            await tarea

    asyncio.run(_escenario())

    assert servicio.repository.eventos == [GUARDAR_SIN_CONFIRMAR, "enviar", "descartar"]


def test_si_falla_la_confirmacion_el_error_llega_al_llamador(servicio, monkeypatch):
    """RF-03.14: el envío salió pero el commit falló: la excepción llega al router (500) y no se informa éxito."""
    _anotar_el_envio(servicio, monkeypatch, entregado=True)
    servicio.repository.error_al_confirmar = RuntimeError("PRUEBA el commit falló")

    with pytest.raises(RuntimeError, match="el commit falló"):
        _resetear(servicio)

    assert servicio.repository.eventos == [GUARDAR_SIN_CONFIRMAR, "enviar", "confirmar"]


def test_el_error_del_guardado_tras_un_envio_entregado_lleva_la_marca_para_el_router(servicio, monkeypatch):
    """RF-21.4, RF-03.14: si el commit falla después de un envío entregado, la excepción original (mismo tipo y texto) lleva
    `correo_entregado` en verdadero para que el router registre el intento en la bitácora."""
    _anotar_el_envio(servicio, monkeypatch, entregado=True)
    servicio.repository.error_al_confirmar = RuntimeError("PRUEBA el commit falló")

    with pytest.raises(RuntimeError, match="el commit falló") as excepcion:
        _resetear(servicio)

    assert excepcion.value.correo_entregado is True


def test_un_error_anterior_al_envio_no_lleva_la_marca_de_correo_entregado(servicio, monkeypatch):
    """RF-21.4: si falla el guardado previo al envío (el correo nunca salió), la excepción llega sin la marca: no se registra
    un «entregada» que no ocurrió."""
    enviados = _anotar_el_envio(servicio, monkeypatch, entregado=True)

    def _guardado_que_falla(db, usuario_id, nueva_contrasenna, **opciones):
        raise RuntimeError("PRUEBA el guardado falló")

    monkeypatch.setattr(servicio.repository, "resetear_contrasenna", _guardado_que_falla)

    with pytest.raises(RuntimeError, match="el guardado falló") as excepcion:
        _resetear(servicio)

    assert not hasattr(excepcion.value, "correo_entregado")
    assert enviados == []


def test_usuario_inexistente_devuelve_none_sin_guardar_ni_enviar(servicio, correo_simulado):
    """RF-03.13: un usuario que no existe devuelve `None` (404 en el router); no se guarda nada y no sale ningún correo."""
    servicio.repository.usuario = None

    assert _resetear(servicio) is None

    assert servicio.repository.eventos == []
    assert servicio.repository.contrasenas == []
    assert correo_simulado.intentos == []


def test_el_texto_de_fallo_usa_el_correo_copiado_antes_de_que_el_rollback_expire_al_usuario(servicio, monkeypatch):
    """RF-03.14: tras un `rollback` los atributos del usuario quedan expirados; el correo del mensaje se copió antes."""
    _anotar_el_envio(servicio, monkeypatch, entregado=False)
    servicio.repository.expira_al_descartar = True

    resultado = _resetear(servicio)

    assert servicio.repository.usuario.CT_Correo is None  # el simulado sí lo expiró
    assert resultado.mensaje == MENSAJE_FALLIDO


def test_el_correo_recibe_la_temporal_que_se_guardo_el_destinatario_y_el_nombre_completo(servicio, monkeypatch):
    """RF-03.13: la contraseña del correo es la misma que se guardó; el destinatario es el correo del usuario y el nombre
    completo no trae `None` cuando falta el segundo apellido."""
    recibidos = _anotar_el_envio(servicio, monkeypatch, entregado=True)

    _resetear(servicio)
    servicio.repository.usuario.CT_Apellido_dos = None
    _resetear(servicio)

    assert [r["to_email"] for r in recibidos] == [CORREO, CORREO]
    assert [r["new_password"] for r in recibidos] == servicio.repository.contrasenas
    assert [r["user_name"] for r in recibidos] == ["PRUEBA Peña Núñez", "PRUEBA Peña"]


def test_la_temporal_tiene_8_caracteres_alfanumericos_y_sale_de_secrets(monkeypatch):
    """RF-03.13: `_generar_contrasenna_temporal()` es la única fuente de la contraseña temporal: 8 letras o números, con `secrets`."""
    import string

    from app.services import usuario_service as modulo

    elecciones = []
    original = modulo.secrets.choice

    def _elegir(alfabeto):
        elecciones.append(alfabeto)
        return original(alfabeto)

    monkeypatch.setattr(modulo.secrets, "choice", _elegir)

    temporal = modulo._generar_contrasenna_temporal()

    assert len(temporal) == 8 and temporal.isalnum() and temporal.isascii()
    assert elecciones == [string.ascii_letters + string.digits] * 8
    assert temporal != modulo._generar_contrasenna_temporal()  # 62^8 posibilidades: no se repite


# --- El repositorio: guardar sin confirmar, confirmar y descartar ----------------------------------------------------------------

class SesionAnotada:
    """Hace de `Session`: anota las llamadas que importan y puede hacer fallar el commit."""

    def __init__(self, error_en_commit=None):
        self.llamadas = []
        self._error_en_commit = error_en_commit

    def flush(self):
        self.llamadas.append("flush")

    def commit(self):
        self.llamadas.append("commit")
        if self._error_en_commit is not None:
            raise self._error_en_commit

    def refresh(self, objeto):
        self.llamadas.append("refresh")

    def rollback(self):
        self.llamadas.append("rollback")


@pytest.fixture
def repositorio_real(monkeypatch):
    """El repositorio real con un usuario inventado; el hash se simula para no pagar el costo de bcrypt en la prueba."""
    from app.repositories.usuario_repository import UsuarioRepository

    usuario = SimpleNamespace(CT_Contrasenna="hash-anterior", CF_Ultimo_acceso="fecha-anterior")
    repositorio = UsuarioRepository()
    monkeypatch.setattr(repositorio, "obtener_usuario_por_id", lambda db, usuario_id: usuario)
    monkeypatch.setattr(repositorio, "_hash_password", lambda texto: "hash-nuevo")
    return repositorio, usuario


def test_resetear_sin_confirmar_solo_hace_flush_y_deja_el_ultimo_acceso_vacio(repositorio_real):
    """RF-03.14: con `confirmar=False` el hash y el último acceso vacío se escriben en la transacción (flush) sin commit."""
    repositorio, usuario = repositorio_real
    sesion = SesionAnotada()

    resultado = repositorio.resetear_contrasenna(sesion, CEDULA, "PRUEBA-temporal", confirmar=False)

    assert resultado is usuario
    assert sesion.llamadas == ["flush"]
    assert usuario.CT_Contrasenna == "hash-nuevo" and usuario.CF_Ultimo_acceso is None


def test_resetear_por_omision_confirma_como_antes(repositorio_real):
    """Caracterización: sin `confirmar`, el repositorio confirma y refresca (el comportamiento de siempre)."""
    repositorio, usuario = repositorio_real
    sesion = SesionAnotada()

    repositorio.resetear_contrasenna(sesion, CEDULA, "PRUEBA-temporal")

    assert sesion.llamadas == ["commit", "refresh"]
    assert usuario.CT_Contrasenna == "hash-nuevo" and usuario.CF_Ultimo_acceso is None


def test_confirmar_cambios_hace_commit_y_si_falla_revierte_y_relanza(repositorio_real):
    """RF-03.14: si el commit falla, el repositorio revierte y la excepción llega al servicio (queda la contraseña anterior)."""
    repositorio, _ = repositorio_real
    bien, mal = SesionAnotada(), SesionAnotada(error_en_commit=RuntimeError("PRUEBA commit"))

    repositorio.confirmar_cambios(bien)
    with pytest.raises(RuntimeError, match="PRUEBA commit"):
        repositorio.confirmar_cambios(mal)

    assert bien.llamadas == ["commit"]
    assert mal.llamadas == ["commit", "rollback"]


def test_descartar_cambios_hace_rollback(repositorio_real):
    """RF-03.14: descartar es un `rollback` de la transacción abierta por el flush."""
    repositorio, _ = repositorio_real
    sesion = SesionAnotada()

    repositorio.descartar_cambios(sesion)

    assert sesion.llamadas == ["rollback"]


# --- T7: creación de cuenta (RF-02.1, RF-21.4, RNF-08.1, RNF-08.2) -------------------------------------------------------------
# La cuenta se crea aunque el correo falle; la respuesta dice si la notificación se entregó y lleva el texto exacto. La base
# real, el código HTTP y la bitácora se prueban en `tests/integracion/test_creacion_de_cuenta.py`.

MENSAJE_CREACION_EXITOSA = "Usuario creado exitosamente"
ADVERTENCIA_DE_CREACION = (
    f"Usuario creado, pero no se pudo enviar el correo con la contraseña temporal a {CORREO}. "
    'Use "Resetear Contraseña" cuando el servicio de correo esté disponible.'
)
NOMBRE_DE_USUARIO = "PRUEBA Peña Núñez"


class RepositorioDeCreacion(RepositorioSimulado):
    """Igual que el simulado, pero anota la creación en `eventos` para comprobar que ocurre antes del envío."""

    def crear_usuario(self, db, cedula, nombre_usuario, nombre, apellido_uno, apellido_dos, correo, contrasenna, id_rol):
        self.eventos.append("crear")
        return super().crear_usuario(db, cedula, nombre_usuario, nombre, apellido_uno, apellido_dos, correo, contrasenna, id_rol)


@pytest.fixture
def servicio_de_creacion(servicio):
    """El servicio de la fixture `servicio`, con un repositorio que anota la creación."""
    servicio.repository = RepositorioDeCreacion(CORREO)
    return servicio


def _crear(servicio):
    return asyncio.run(servicio.crear_usuario(None, CEDULA, NOMBRE_DE_USUARIO, "PRUEBA", "Peña", "Núñez", CORREO, 2))


def _anotar_el_envio_de_creacion(servicio, monkeypatch, entregado=True, error=None):
    """Como `_anotar_el_envio`, para el correo de la cuenta nueva: anota "enviar" y devuelve lo que recibió el envío."""
    recibidos = []

    async def _enviar(to, password, usuario_nombre="Usuario"):
        servicio.repository.eventos.append("enviar")
        recibidos.append({"to": to, "usuario_nombre": usuario_nombre, "password": Contrasena(password)})
        if error is not None:
            raise error
        return entregado

    monkeypatch.setattr(servicio.email_service, "send_password_email", _enviar)
    return recibidos


def test_creacion_con_envio_exitoso_crea_la_cuenta_antes_de_enviar_y_dice_que_se_entrego(servicio_de_creacion, monkeypatch):
    """RF-02.1: la cuenta se crea primero (queda confirmada); el correo sale a la dirección de la cuenta con la misma
    temporal que se guardó; la respuesta dice «entregada» con el texto de éxito y conserva los datos de la cuenta."""
    from app.schemas.usuario_schemas import UsuarioCreadoRespuesta

    servicio = servicio_de_creacion
    recibidos = _anotar_el_envio_de_creacion(servicio, monkeypatch, entregado=True)

    resultado = _crear(servicio)

    assert isinstance(resultado, UsuarioCreadoRespuesta)
    assert servicio.repository.eventos == ["crear", "enviar"]
    assert resultado.notificacion_entregada is True
    assert resultado.mensaje == MENSAJE_CREACION_EXITOSA
    assert resultado.CN_Id_usuario == CEDULA and resultado.CT_Correo == CORREO and resultado.estado.nombre == "Activo"
    assert [r["to"] for r in recibidos] == [CORREO]
    assert [r["usuario_nombre"] for r in recibidos] == [NOMBRE_DE_USUARIO]
    assert [r["password"] for r in recibidos] == servicio.repository.contrasenas


def test_creacion_con_el_servidor_en_fallo_crea_la_cuenta_y_lleva_la_advertencia_de_la_spec(servicio_de_creacion, correo_simulado):
    """RF-02.1 (regresión): con el servidor de correo en fallo la cuenta se crea igual; la respuesta dice «no entregada» y lleva el
    texto completo con el correo, sin el texto del error del servidor ni la temporal."""
    servicio = servicio_de_creacion
    correo_simulado.fallar(aiosmtplib.SMTPResponseException(535, TEXTO_DEL_ERROR))

    resultado = _crear(servicio)

    assert servicio.repository.eventos == ["crear"]
    assert len(servicio.repository.contrasenas) == 1
    assert resultado.notificacion_entregada is False
    assert resultado.mensaje == ADVERTENCIA_DE_CREACION
    assert resultado.CN_Id_usuario == CEDULA
    temporal = servicio.repository.contrasenas[-1]
    # control positivo: la temporal sí viajó en el mensaje que el sistema armó, así que la búsqueda en la respuesta no es en vacío
    assert rastros.encontrar_en_rastros(temporal, correo=[correo_simulado.contenido_real().texto]) == ["correo"]
    rastros.buscar_en_rastros(temporal, respuesta=resultado.model_dump_json())
    assert CLAVE_DEL_SERVIDOR not in resultado.model_dump_json()


def test_creacion_con_una_excepcion_en_el_envio_se_trata_como_envio_fallido(servicio_de_creacion, monkeypatch):
    """RF-02.1, RF-03.17: una excepción inesperada del envío no se propaga ni deshace la cuenta: advertencia, sin el texto del error."""
    servicio = servicio_de_creacion
    _anotar_el_envio_de_creacion(servicio, monkeypatch, error=RuntimeError(TEXTO_DEL_ERROR))

    resultado = _crear(servicio)

    assert servicio.repository.eventos == ["crear", "enviar"]
    assert resultado.notificacion_entregada is False
    assert resultado.mensaje == ADVERTENCIA_DE_CREACION
    assert CLAVE_DEL_SERVIDOR not in resultado.model_dump_json()


def test_creacion_con_el_servicio_de_correo_ausente_crea_la_cuenta_sin_intentar_enviar(servicio_de_creacion, correo_simulado):
    """RF-02.1, RF-03.17: con `email_service = None` (configuración inválida al arrancar) la cuenta se crea y la respuesta es la advertencia."""
    servicio = servicio_de_creacion
    servicio.email_service = None

    resultado = _crear(servicio)

    assert servicio.repository.eventos == ["crear"]
    assert resultado.notificacion_entregada is False
    assert resultado.mensaje == ADVERTENCIA_DE_CREACION
    assert correo_simulado.intentos == []


def test_creacion_con_envio_que_devuelve_falso_es_envio_fallido(servicio_de_creacion, monkeypatch):
    """RF-02.1, RF-03.17: el booleano de `send_password_email` manda: `False` (tiempo agotado, rechazo...) es «no entregada»."""
    servicio = servicio_de_creacion
    _anotar_el_envio_de_creacion(servicio, monkeypatch, entregado=False)

    resultado = _crear(servicio)

    assert resultado.notificacion_entregada is False
    assert resultado.mensaje == ADVERTENCIA_DE_CREACION
    assert resultado.mensaje != MENSAJE_CREACION_EXITOSA


def test_la_respuesta_de_la_creacion_nunca_lleva_la_temporal(servicio_de_creacion, correo_simulado):
    """RF-02.1, RNF-08.1: ni con el correo funcionando ni con el servidor en fallo la respuesta trae la temporal; solo viaja en el correo."""
    servicio = servicio_de_creacion

    exitosa = _crear(servicio)
    correo_simulado.fallar(aiosmtplib.SMTPConnectError("PRUEBA servidor caído"))
    fallida = _crear(servicio)

    assert exitosa.notificacion_entregada is True and fallida.notificacion_entregada is False
    assert len(servicio.repository.contrasenas) == 2
    for temporal in servicio.repository.contrasenas:
        rastros.buscar_en_rastros(temporal, exitosa=exitosa.model_dump_json(), fallida=fallida.model_dump_json())
    # control positivo: la primera temporal viajó en el correo
    assert rastros.encontrar_en_rastros(servicio.repository.contrasenas[0], correo=[correo_simulado.contenido_real(0).texto]) == ["correo"]


# --- La auditoría de la creación: el resultado de la notificación y un fallo que no filtra el correo --------------------------------

class BitacoraAnotada:
    """Hace de `BitacoraService`: guarda lo que se le pide registrar o lanza el error indicado."""

    def __init__(self, error=None):
        self.registros = []
        self._error = error

    async def registrar(self, **argumentos):
        if self._error is not None:
            raise self._error
        self.registros.append(argumentos)
        return SimpleNamespace(CN_Id_bitacora=1)


def _registrar_creacion(auditoria, notificacion_entregada=True):
    return asyncio.run(auditoria.registrar_creacion_usuario(
        db=None, usuario_admin_id="PRUEBA000001", usuario_creado_cedula=CEDULA,
        datos_usuario={"nombre_usuario": NOMBRE_DE_USUARIO, "nombre_completo": "PRUEBA Peña Núñez", "correo": CORREO, "id_rol": 2},
        notificacion_entregada=notificacion_entregada,
    ))


@pytest.fixture
def auditoria(monkeypatch):
    """El servicio de auditoría de usuarios con una bitácora anotada (sin base de datos)."""
    from app.services.bitacora.usuarios_audit_service import usuarios_audit_service

    bitacora = BitacoraAnotada()
    monkeypatch.setattr(usuarios_audit_service, "bitacora_service", bitacora)
    return usuarios_audit_service, bitacora


@pytest.mark.parametrize("entregada, valor, dice", [(True, "entregada", "notificación por correo: entregada"),
                                                    (False, "no entregada", "notificación por correo: no entregada")])
def test_el_registro_de_la_creacion_lleva_el_resultado_de_la_notificacion(entregada, valor, dice, auditoria):
    """RF-21.4: el registro de la creación guarda `notificacion_correo` y lo dice en el texto; conserva la cédula y el correo (la
    bitácora sí los guarda) y no trae ninguna contraseña."""
    servicio_de_auditoria, bitacora = auditoria

    _registrar_creacion(servicio_de_auditoria, notificacion_entregada=entregada)

    assert len(bitacora.registros) == 1
    registro = bitacora.registros[0]
    assert registro["info_adicional"]["notificacion_correo"] == valor
    assert registro["info_adicional"]["usuario_creado_cedula"] == CEDULA and registro["info_adicional"]["email"] == CORREO
    assert CEDULA in registro["texto"] and dice in registro["texto"]
    assert "contrase" not in " ".join(str(v).lower() for k, v in registro["info_adicional"].items() if k != "notificacion_correo")


def test_si_falla_el_registro_de_la_creacion_la_accion_sigue_y_el_registro_solo_dice_el_tipo_del_error(monkeypatch, caplog, capfd):
    """RF-21.4, RNF-08.2 (regresión): con la bitácora fallando, la auditoría devuelve `None` sin propagar, y el error del INSERT (que
    lista el correo de la cuenta) no queda en claro en los registros del servidor: solo el tipo de la excepción."""
    from app.services.bitacora.usuarios_audit_service import usuarios_audit_service

    error = RuntimeError(f"INSERT fallido, parámetros: ('{CORREO}', 'PRUEBA')")
    monkeypatch.setattr(usuarios_audit_service, "bitacora_service", BitacoraAnotada(error=error))
    caplog.set_level(logging.DEBUG)

    resultado = _registrar_creacion(usuarios_audit_service)

    assert resultado is None
    assert "RuntimeError" in caplog.text  # control positivo: el fallo sí se registró, solo su tipo
    salida = capfd.readouterr()
    rastros.buscar_en_rastros(CORREO, salida=salida.out + salida.err, registros=caplog.text)
