"""Servicio de la recuperación pública de contraseña por código: la solicitud, la verificación y el cambio (RF-03).

Aquí vive toda la decisión de los tres pasos; la ruta (`app/routes/auth.py`) solo llama, deja el envío para después de responder y
traduce los errores. Las capas son las del proyecto: ruta -> este servicio -> repositorios (`usuario_repository` para la cuenta y
`recuperacion_estado_repository` para el estado y los límites en Redis).

Lo que garantiza el paso 1 (solicitar):

- El código (6 dígitos, `secrets`) solo viaja por el correo: en Redis queda su HMAC y en la respuesta, un token que no
  lo contiene ni permite deducirlo (RF-03.1, 03.21).
- La respuesta es la misma exista o no la cuenta, esté Activa o Inactiva, falle el envío o se haya alcanzado un límite
  (RF-03.2). Solo una cuenta Activa recibe un correo (RF-03.4, 03.5). Los demás casos guardan un estado «señuelo» con el
  mismo aspecto, para que los pasos siguientes tampoco delaten qué cuentas existen (RF-03.8).
- Una solicitud por minuto y cinco por hora por correo normalizado, también para correos sin cuenta (RF-03.10 a 03.12).
- Si Redis no responde o la clave de firma no es válida, la recuperación queda inhabilitada con el error de servicio
  uniforme (RF-03.20, RNF-07.3): falla cerrada, y Redis se comprueba antes de mirar la cuenta.

`solicitar` responde sin enviar nada: devuelve la respuesta y una `SolicitudPendiente` con lo que falta hacer. El envío
del correo y el registro en la bitácora lo hace `completar_solicitud`, con su propia sesión de base de datos, porque la
sesión de la petición puede estar cerrada cuando corra. La ruta lo programa como tarea posterior (`BackgroundTasks`): la respuesta no
espera al servidor de correo (RF-03.3). El código y el correo no salen en el `repr` de lo pendiente (RNF-08).

Lo que garantizan los pasos 2 y 3 (`verificar` y `cambiar`):

- Todo lo que decide la respuesta sale de lo que Redis guardó en el paso 1, no de lo que manda el navegador: el código
  se compara por su HMAC, cada código admite cinco comprobaciones (el sexto intento ya no comprueba) y un código
  reemplazado responde como vencido (RF-03.4, 03.9). Un estado que Redis perdió se rechaza como vencido (RF-03.25).
- Un correo sin cuenta o una cuenta Inactiva recorren los mismos pasos con un estado señuelo, así que responden lo mismo
  que una cuenta Activa con un código incorrecto (RF-03.8). Solo quien acierta el código real llega a mirar la cuenta.
- La cuenta se vuelve a mirar al verificar y al cambiar: si dejó de estar Activa o el Administrador le cambió el correo
  o la contraseña, el vínculo guardado ya no coincide y el proceso responde como vencido, sin decir el motivo
  (RF-03.5, 03.6, 03.24). La verificación se gasta con un `DEL`: solo una petición cambia la contraseña (RF-03.7).
- Ningún error de estos pasos responde 401, 403 ni 404 (RF-03.22): la interfaz cerraría la sesión con un 401.
- Cada rechazo lleva el `resultado` que la ruta registra en la bitácora y la cédula de la cuenta cuando ya se conoce
  (RF-21.2); el éxito devuelve la cédula. La ruta pone la `referencia` con `referencia_de_token`.

Ver también: `app/utils/recuperacion_codigos.py`, `app/utils/clave_firma.py`,
`app/repositories/recuperacion_estado_repository.py` y `specs/003b-recuperacion-publica-segura/plan.md` §3.3.
"""
import asyncio
import hmac
import logging
import secrets
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple

from app.repositories import recuperacion_estado_repository as almacen
from app.repositories.recuperacion_estado_repository import AlmacenNoDisponible, TIEMPO_ESPERA_REDIS
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth_schemas import MensajeExito, SolicitarRecuperacionResponse, VerificarCodigoResponse
from app.services.bitacora.auth_audit_service import auth_audit_service
from app.services.usuario_service import UsuarioService
from app.utils import recuperacion_codigos as codigos
from app.utils.clave_firma import ClaveDeFirmaInvalida, leer_clave_firma
from app.utils.reloj import obtener_reloj

logger = logging.getLogger(__name__)

# Textos que ve la persona (los fija la spec y el ERS; la interfaz los muestra tal cual).
MENSAJE_DE_LA_SOLICITUD = "Si el correo existe en nuestro sistema, recibirás un email con las instrucciones"
MENSAJE_CORREO_INVALIDO = "Ingresa un correo electrónico válido"
MENSAJE_SERVICIO_NO_DISPONIBLE = (
    "El servicio de recuperación de contraseña no está disponible por el momento. Inténtalo de nuevo más tarde."
)
MENSAJE_CODIGO_INVALIDO = "El código debe tener exactamente 6 dígitos"
MENSAJE_FALTAN_DATOS = "Token y nueva contraseña son requeridos"
MENSAJE_CONTRASENA_CORTA = "La nueva contraseña debe tener al menos 6 caracteres"
MENSAJE_TOKEN_NO_RECONOCIDO = "Token inválido. El enlace de recuperación no es válido"
MENSAJE_CODIGO_INCORRECTO = "Código de verificación incorrecto"
MENSAJE_CODIGO_VENCIDO = "El código ha expirado. Por favor, solicita un nuevo código de recuperación"
MENSAJE_CODIGO_INVALIDADO = (
    "Superaste el número de intentos permitidos. Solicita un nuevo código de recuperación. "
    "Si lo pediste hace menos de un minuto, espera un momento antes de volver a pedirlo."
)
MENSAJE_CODIGO_VERIFICADO = "Código verificado correctamente"
MENSAJE_PROCESO_VENCIDO = "El token de verificación ha expirado. Por favor, inicia el proceso de recuperación nuevamente"
MENSAJE_IGUAL_A_LA_ACTUAL = "La nueva contraseña debe ser diferente a la actual"
MENSAJE_CONTRASENA_CAMBIADA = "Contraseña recuperada exitosamente"

# El mínimo heredado de la nueva contraseña; el de 8 caracteres es RNF-08, de la spec de autenticación.
LARGO_MINIMO_CONTRASENA = 6

# Los resultados que quedan en la bitácora (RF-21.1 y RF-21.2): son un conjunto fijo. `completar_solicitud` conoce los de
# la solicitud; los de los pasos 2 y 3 salen de `verificar` y `cambiar`, y la ruta registra «servicio no disponible».
RESULTADO_ENVIADO = "código enviado"
RESULTADO_ENVIO_FALLIDO = "envío fallido"
RESULTADO_NO_REGISTRADO = "correo no registrado"
RESULTADO_INACTIVA = "cuenta inactiva"
RESULTADO_LIMITE = "límite alcanzado"
RESULTADO_SERVICIO_NO_DISPONIBLE = "servicio no disponible"
RESULTADO_CODIGO_VERIFICADO = "código verificado"
RESULTADO_CODIGO_INCORRECTO = "código incorrecto"
RESULTADO_CODIGO_VENCIDO = "código vencido"
RESULTADO_CODIGO_INVALIDADO = "código invalidado por intentos"
RESULTADO_CONTRASENA_CAMBIADA = "contraseña cambiada"
RESULTADO_CAMBIO_RECHAZADO = "cambio rechazado"

ESTADO_ACTIVO = "activo"


class ErrorDeRecuperacion(Exception):
    """Un error de la recuperación que la ruta traduce a su código HTTP, con un mensaje en español sin datos de la cuenta.

    `registrar` dice si el error debe dejar una fila en la bitácora: la entrada inválida no (RF-03.22). Si la deja,
    `resultado` es lo que dice la fila (RF-21.1, RF-21.2) y `cedula` la cuenta cuando ya se conocía al rechazar (`None` si
    no existe, es un señuelo o todavía no se sabía). `correo` y `referencia` solo los llena la solicitud con servicio no
    disponible: es la única que no tiene token del que sacar la referencia ni una respuesta que los lleve.
    """

    def __init__(
        self, estado: int, mensaje: str, registrar: bool = True, resultado: Optional[str] = None,
        cedula: Optional[str] = None, correo: Optional[str] = None, referencia: Optional[str] = None,
    ):
        super().__init__(mensaje)
        self.estado = estado
        self.mensaje = mensaje
        self.registrar = registrar
        self.resultado = resultado
        self.cedula = cedula
        self.correo = correo
        self.referencia = referencia


class ServicioNoDisponible(ErrorDeRecuperacion):
    """La recuperación no puede funcionar por una causa del sistema (Redis o clave de firma): el error de servicio uniforme.

    Es el mismo 503 y el mismo mensaje para las dos causas y para cualquier cuenta; la `causa` solo sirve a quien opera.
    """

    def __init__(self, causa: str):
        super().__init__(503, MENSAJE_SERVICIO_NO_DISPONIBLE, resultado=RESULTADO_SERVICIO_NO_DISPONIBLE)
        self.causa = causa


@dataclass(frozen=True)
class EnvioPendiente:
    """Lo que hace falta para enviar el código por correo. Nada de esto sale en un `repr`, una traza ni un registro."""

    correo: str = field(repr=False)
    nombre: str = field(repr=False)
    codigo: str = field(repr=False)


@dataclass(frozen=True)
class SolicitudPendiente:
    """Lo que queda por hacer después de responder: enviar el correo (si corresponde) y registrar la solicitud.

    `resultado` es `None` cuando hay un envío (se sabe al terminarlo) y, si no, el motivo por el que no lo hay.
    """

    correo: str = field(repr=False)
    cedula: Optional[str] = field(repr=False)
    referencia: str  # los 8 primeros caracteres de la huella: seguir los pasos de una solicitud sin revelar el correo
    resultado: Optional[str]
    envio: Optional[EnvioPendiente]


@dataclass(frozen=True)
class ResultadoSolicitud:
    """La respuesta uniforme para la persona y lo pendiente para después de responder."""

    respuesta: SolicitarRecuperacionResponse
    pendiente: SolicitudPendiente


class RecuperacionService:
    """Los tres pasos de la recuperación de contraseña por código: solicitar, verificar y cambiar."""

    def __init__(self, usuarios: Optional[UsuarioRepository] = None, servicio_de_usuarios: Optional[UsuarioService] = None):
        """Acepta el repositorio de usuarios y el servicio que envía el correo para poder simularlos en las pruebas."""
        self.usuarios = usuarios if usuarios is not None else UsuarioRepository()
        self.servicio_de_usuarios = servicio_de_usuarios if servicio_de_usuarios is not None else UsuarioService()

    # --- Paso 1: solicitar el código ---------------------------------------------------------------------------------

    async def solicitar(self, db, correo_crudo: Optional[str]) -> ResultadoSolicitud:
        """Decide la solicitud y guarda su estado; devuelve la respuesta uniforme y lo pendiente. No envía nada.

        Orden: entrada, clave de firma, límites en Redis y recién entonces la cuenta (una sola consulta, exista o no),
        para que con Redis caído no se consulte la base y para que todos los casos hagan el mismo trabajo (RF-03.2, 03.20).
        """
        correo = codigos.normalizar_correo(correo_crudo)
        if not codigos.es_correo_valido(correo):
            raise ErrorDeRecuperacion(400, MENSAJE_CORREO_INVALIDO, registrar=False)  # no cuenta para los límites
        huella = None
        try:
            claves = self._claves()
            huella = codigos.huella_de_correo(claves.huella, correo)
            aceptada = await self._almacen(almacen.aceptar_solicitud, huella)

            usuario = self.usuarios.obtener_usuario_por_correo(db, correo)
            activa = usuario is not None and self._esta_activa(usuario)
            emision = codigos.generar_emision()
            resultado: Optional[str] = None
            envio: Optional[EnvioPendiente] = None

            if not aceptada:
                resultado = RESULTADO_LIMITE  # no se guarda nada: el código vigente, si hay, sigue valiendo
            else:
                if activa:
                    codigo = codigos.generar_codigo()
                    hash_codigo = codigos.hash_de_codigo(claves.codigo, huella, codigo)
                    vinculo = self._vinculo(claves, usuario)
                    envio = EnvioPendiente(
                        correo=(usuario.CT_Correo or correo).strip(), nombre=self._nombre_completo(usuario), codigo=codigo
                    )
                else:
                    # Estado señuelo: mismo aspecto que uno real, pero ningún código puede acertar su resumen (RF-03.8).
                    hash_codigo, vinculo = secrets.token_hex(32), secrets.token_hex(32)
                    resultado = RESULTADO_INACTIVA if usuario is not None else RESULTADO_NO_REGISTRADO
                cedula_guardada = usuario.CN_Id_usuario if usuario is not None else ""
                await self._almacen(almacen.guardar_estado, huella, hash_codigo, emision, cedula_guardada, vinculo)

            respuesta = SolicitarRecuperacionResponse(
                success=True, message=MENSAJE_DE_LA_SOLICITUD, token=codigos.crear_token_solicitud(huella, emision)
            )
            pendiente = SolicitudPendiente(
                correo=correo, cedula=usuario.CN_Id_usuario if usuario is not None else None,
                referencia=huella[:8], resultado=resultado, envio=envio,
            )
            return ResultadoSolicitud(respuesta, pendiente)
        except ServicioNoDisponible as error:
            # La ruta registra «servicio no disponible» con el correo normalizado; sin usuario, porque no se mira la cuenta.
            error.correo = correo
            error.referencia = huella[:8] if huella else None  # sin clave de firma válida no hay huella
            raise

    async def completar_solicitud(self, pendiente: SolicitudPendiente) -> None:
        """Envía el correo (si corresponde) y registra la solicitud. Nunca lanza: la respuesta ya se dio (RF-21.5).

        Abre su propia sesión de base de datos (importada aquí: las pruebas unitarias no cargan `database.py`). De
        cualquier error solo queda en el registro del servidor el tipo de la excepción: su texto puede traer el correo.
        """
        try:
            resultado = pendiente.resultado
            if pendiente.envio is not None:
                envio = pendiente.envio
                entregado = await self.servicio_de_usuarios._enviar(
                    lambda servicio: servicio.send_recovery_code_email(
                        to_email=envio.correo, user_name=envio.nombre, recovery_code=envio.codigo
                    )
                )
                resultado = RESULTADO_ENVIADO if entregado else RESULTADO_ENVIO_FALLIDO

            from app.db.database import SessionLocal

            with SessionLocal() as db:
                await auth_audit_service.registrar_recuperacion_solicitud(
                    db=db, email=pendiente.correo, resultado=resultado, usuario_id=pendiente.cedula,
                    referencia=pendiente.referencia,
                )
            logger.info("Solicitud de recuperación atendida: %s (referencia %s)", resultado, pendiente.referencia)
        except Exception as error:
            logger.error("La solicitud de recuperación no pudo completarse (%s)", type(error).__name__)

    # --- Paso 2: verificar el código ---------------------------------------------------------------------------------

    async def verificar(self, db, token: Optional[str], codigo: Optional[str]) -> Tuple[VerificarCodigoResponse, str]:
        """Verifica el código con el token de la solicitud; devuelve el token de verificación y la cédula de la cuenta.

        Una entrada inválida (código que no son 6 dígitos, token vacío) se resuelve antes de contar nada: no gasta
        intentos. Después, cada comprobación cuenta un intento atómico en Redis; la sexta ya no comprueba (RF-03.9).
        Un token de otra solicitud (reemplazada) o un estado perdido responden como código vencido (RF-03.4, 03.25).
        """
        if not codigos.es_codigo_valido(codigo) or not token:
            raise ErrorDeRecuperacion(400, MENSAJE_CODIGO_INVALIDO, registrar=False)
        claves = self._claves()
        partes = codigos.partir_token(token)
        if partes is None:
            raise ErrorDeRecuperacion(400, MENSAJE_TOKEN_NO_RECONOCIDO, resultado=RESULTADO_CODIGO_VENCIDO)
        huella, emision = partes

        intento = await self._almacen(almacen.registrar_intento, huella)
        if intento is None:  # Redis perdió el estado: ya no se sabe de quién era
            raise ErrorDeRecuperacion(400, MENSAJE_CODIGO_VENCIDO, resultado=RESULTADO_CODIGO_VENCIDO)
        numero, estado = intento
        cedula = estado.cedula or None  # vacía para un correo sin cuenta (señuelo)
        if numero > almacen.MAXIMO_INTENTOS:
            raise ErrorDeRecuperacion(429, MENSAJE_CODIGO_INVALIDADO, resultado=RESULTADO_CODIGO_INVALIDADO, cedula=cedula)
        if not hmac.compare_digest(emision, estado.emision):
            raise ErrorDeRecuperacion(400, MENSAJE_CODIGO_VENCIDO, resultado=RESULTADO_CODIGO_VENCIDO, cedula=cedula)
        if not hmac.compare_digest(codigos.hash_de_codigo(claves.codigo, huella, codigo), estado.hash_codigo):
            if numero >= almacen.MAXIMO_INTENTOS:  # el quinto fallo invalida el código
                raise ErrorDeRecuperacion(
                    429, MENSAJE_CODIGO_INVALIDADO, resultado=RESULTADO_CODIGO_INVALIDADO, cedula=cedula
                )
            raise ErrorDeRecuperacion(400, MENSAJE_CODIGO_INCORRECTO, resultado=RESULTADO_CODIGO_INCORRECTO, cedula=cedula)

        # El código es correcto: solo una cuenta Activa real puede haber llegado hasta aquí (un señuelo no tiene un código
        # que se pueda acertar). Se vuelve a mirar la cuenta por si cambió después de pedir el código.
        usuario = self._cuenta_vigente(db, claves, estado.cedula, estado.vinculo)
        if usuario is None:
            raise ErrorDeRecuperacion(400, MENSAJE_CODIGO_VENCIDO, resultado=RESULTADO_CODIGO_VENCIDO, cedula=cedula)
        secreto = codigos.generar_secreto()
        await self._almacen(
            almacen.guardar_verificacion, huella, codigos.hash_de_secreto(claves.verificacion, secreto),
            estado.cedula, estado.vinculo,
        )
        respuesta = VerificarCodigoResponse(
            success=True, message=MENSAJE_CODIGO_VERIFICADO,
            verificationToken=codigos.crear_token_verificacion(huella, secreto),
        )
        return respuesta, usuario.CN_Id_usuario

    # --- Paso 3: cambiar la contraseña -------------------------------------------------------------------------------

    async def cambiar(
        self, db, token_de_verificacion: Optional[str], nueva_contrasenna: Optional[str]
    ) -> Tuple[MensajeExito, str]:
        """Define la contraseña nueva con el token de verificación; devuelve el mensaje y la cédula de la cuenta.

        La verificación se lee sin gastarla, así «igual a la actual» deja reintentar con la misma. Solo se gasta (con un
        `DEL`, que devuelve 1 a una sola petición) justo antes de guardar. Cualquier causa de rechazo del proceso responde
        el mismo mensaje de proceso vencido, sin decir cuál fue (RF-03.5, 03.6, 03.24, 03.25).
        """
        if not token_de_verificacion or not nueva_contrasenna:
            raise ErrorDeRecuperacion(400, MENSAJE_FALTAN_DATOS, registrar=False)
        if len(nueva_contrasenna) < LARGO_MINIMO_CONTRASENA:
            raise ErrorDeRecuperacion(400, MENSAJE_CONTRASENA_CORTA, registrar=False)
        claves = self._claves()
        partes = codigos.partir_token(token_de_verificacion)
        if partes is None:
            raise ErrorDeRecuperacion(400, MENSAJE_PROCESO_VENCIDO, resultado=RESULTADO_CAMBIO_RECHAZADO)
        huella, secreto = partes

        guardada = await self._almacen(almacen.leer_verificacion, huella)
        if guardada is None:  # caducó o se perdió: ya no se sabe de quién era
            raise ErrorDeRecuperacion(400, MENSAJE_PROCESO_VENCIDO, resultado=RESULTADO_CAMBIO_RECHAZADO)
        cedula = guardada.cedula or None
        if not hmac.compare_digest(codigos.hash_de_secreto(claves.verificacion, secreto), guardada.hash_secreto):
            raise ErrorDeRecuperacion(400, MENSAJE_PROCESO_VENCIDO, resultado=RESULTADO_CAMBIO_RECHAZADO, cedula=cedula)
        usuario = self._cuenta_vigente(db, claves, guardada.cedula, guardada.vinculo)
        if usuario is None:
            raise ErrorDeRecuperacion(400, MENSAJE_PROCESO_VENCIDO, resultado=RESULTADO_CAMBIO_RECHAZADO, cedula=cedula)
        if self.usuarios.pwd_context.verify(nueva_contrasenna, usuario.CT_Contrasenna):
            raise ErrorDeRecuperacion(400, MENSAJE_IGUAL_A_LA_ACTUAL, resultado=RESULTADO_CAMBIO_RECHAZADO, cedula=cedula)

        nuevo_hash = self.usuarios._hash_password(nueva_contrasenna)
        if await self._almacen(almacen.consumir_verificacion, huella) != 1:  # otra petición ya gastó la verificación
            raise ErrorDeRecuperacion(400, MENSAJE_PROCESO_VENCIDO, resultado=RESULTADO_CAMBIO_RECHAZADO, cedula=cedula)
        self.usuarios.actualizar_contrasenna_recuperacion(db, usuario, nuevo_hash)
        return MensajeExito(success=True, message=MENSAJE_CONTRASENA_CAMBIADA), usuario.CN_Id_usuario

    # --- Apoyo -----------------------------------------------------------------------------------------------------

    @staticmethod
    def referencia_de_token(token: Optional[str]) -> Optional[str]:
        """La referencia de un token (los 8 primeros caracteres de la huella del correo) o `None` si no tiene el formato.

        Los dos tokens que el navegador devuelve en los pasos 2 y 3 empiezan por la huella, así que la bitácora une los tres
        pasos de una solicitud sin guardar el correo en Redis ni en las filas de los pasos 2 y 3 (RF-21.2).
        """
        partes = codigos.partir_token(token)
        return partes[0][:8] if partes is not None else None

    @staticmethod
    def _claves() -> codigos.ClavesDeRecuperacion:
        """Las claves derivadas de la clave de firma; si esta no cumple las reglas, la recuperación queda inhabilitada.

        `leer_clave_firma` deja en el registro el nombre de la variable y el motivo (nunca el valor).
        """
        try:
            return codigos.derivar_claves_de_recuperacion(leer_clave_firma())
        except ClaveDeFirmaInvalida:
            raise ServicioNoDisponible("clave de firma") from None

    @staticmethod
    async def _almacen(operacion: Callable, *argumentos):
        """Ejecuta una operación del almacén de Redis con el tiempo de espera fijo; si falla o se agota, falla cerrada.

        Va en un hilo para que un Redis colgado no frene el resto de la API, y con el límite del reloj del sistema para
        que una prueba lo controle sin esperar (RF-03.20, RA-02.9). El 503 es el mismo cualquiera sea la cuenta.
        """
        try:
            return await obtener_reloj().con_limite(asyncio.to_thread(operacion, *argumentos), TIEMPO_ESPERA_REDIS)
        except (TimeoutError, AlmacenNoDisponible) as error:
            logger.error(
                "El almacén de la recuperación no respondió (%s): la recuperación de contraseña no está disponible",
                type(error).__name__,
            )
            raise ServicioNoDisponible("redis") from None

    @staticmethod
    def _esta_activa(usuario) -> bool:
        estado = getattr(usuario, "estado", None)
        return estado is not None and (estado.CT_Nombre_estado or "").strip().lower() == ESTADO_ACTIVO

    @staticmethod
    def _vinculo(claves: codigos.ClavesDeRecuperacion, usuario) -> str:
        """Une el proceso con el estado actual de la cuenta (RF-03.24): si cambia, el código y el cambio pendientes no valen."""
        return codigos.vinculo_de_cuenta(
            claves.vinculo, usuario.CN_Id_usuario, usuario.CT_Correo, usuario.estado.CT_Nombre_estado, usuario.CT_Contrasenna
        )

    def _cuenta_vigente(self, db, claves: codigos.ClavesDeRecuperacion, cedula: str, vinculo_guardado: str):
        """La cuenta del proceso si sigue igual que al emitirlo, o `None`.

        «Igual» es: existe, está Activa y su vínculo (cédula, correo, estado y contraseña) coincide con el que se guardó
        al pedir el código. Una cuenta desactivada, con otro correo o con otra contraseña (aunque sea la que dejó este
        mismo proceso) deja de servir (RF-03.5, 03.6, 03.24).
        """
        if not cedula:
            return None
        usuario = self.usuarios.obtener_usuario_por_id(db, cedula)
        if usuario is None or not self._esta_activa(usuario):
            return None
        if not hmac.compare_digest(self._vinculo(claves, usuario), vinculo_guardado):
            return None
        return usuario

    @staticmethod
    def _nombre_completo(usuario) -> str:
        return " ".join(
            parte for parte in (usuario.CT_Nombre, usuario.CT_Apellido_uno, usuario.CT_Apellido_dos) if parte
        )
