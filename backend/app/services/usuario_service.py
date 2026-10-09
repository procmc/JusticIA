"""
Servicio de Lógica de Negocio para Gestión de Usuarios.

Este módulo implementa la capa de servicio para operaciones CRUD de usuarios,
incluye envío automático de credenciales por email, reseteo de contraseñas,
y mapeo de entidades a esquemas de respuesta.

Funciones principales:
    - obtener_todos_usuarios: Lista todos los usuarios del sistema
    - obtener_usuario: Obtiene un usuario por cédula (ID)
    - crear_usuario: Crea usuario con contraseña aleatoria y envío por email
    - editar_usuario: Actualiza datos de usuario incluyendo rol y estado
    - resetear_contrasenna_usuario: Resetea contraseña y envía nueva por email
    - actualizar_ultimo_acceso: Registra último acceso del usuario

Integración con Email:
    - Envío automático de credenciales al crear usuario
    - Notificación de contraseña reseteada
    - Configuración desde variables de entorno (Gmail, Outlook, etc.)
    - Graceful degradation si el servicio de email no está disponible

Mapeo de entidades:
    - Convierte T_Usuario (modelo DB) a UsuarioRespuesta (schema API)
    - Incluye información de relaciones (rol, estado)
    - Formato consistente para respuestas de API

Example:
    >>> service = UsuarioService()
    >>> nuevo_usuario = await service.crear_usuario(
    ...     db, '123456789', 'jperez', 'Juan', 'Pérez', 'Gómez',
    ...     'jperez@example.com', id_rol=2
    ... )
    >>> # Usuario creado y contraseña enviada por email

Note:
    - Las contraseñas se generan aleatoriamente (8 caracteres alfanuméricos)
    - El servicio de email es opcional (log warning si no está configurado)
    - Usar resetear_contrasenna_usuario solo desde endpoints de administrador
"""

import secrets
import string
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional
from sqlalchemy.orm import Session
from app.repositories.usuario_repository import UsuarioRepository
from app.db.models.usuario import T_Usuario
from app.schemas.usuario_schemas import UsuarioRespuesta, UsuarioCreadoRespuesta, RolInfo, EstadoInfo
from app.email import EmailService, get_email_config_from_env
from app.utils.enmascarar import enmascarar_correo
import logging

logger = logging.getLogger(__name__)

# Textos que el Administrador ve tal cual los devuelve la API (RF-02.1, RF-03.13, RF-03.14).
MENSAJE_CREACION_EXITOSA = "Usuario creado exitosamente"
MENSAJE_CREACION_ADVERTENCIA = (
    "Usuario creado, pero no se pudo enviar el correo con la contraseña temporal a {correo}. "
    'Use "Resetear Contraseña" cuando el servicio de correo esté disponible.'
)
MENSAJE_RESETEO_EXITOSO = "Contraseña reseteada exitosamente"
MENSAJE_RESETEO_FALLIDO = (
    "No se pudo enviar el correo a {correo}. La contraseña no fue modificada. "
    "Verifique el servicio de correo e inténtelo de nuevo."
)


def _generar_contrasenna_temporal() -> str:
    """Contraseña temporal de 8 letras o números con un generador criptográfico (RF-03.13): la única fuente de las temporales."""
    alfabeto = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alfabeto) for _ in range(8))


@dataclass(frozen=True)
class ResultadoReseteo:
    """Resultado de restablecer una contraseña: si el correo con la temporal se entregó y el texto para el Administrador."""

    entregada: bool
    mensaje: str


class UsuarioService:
    """
    Servicio de lógica de negocio para gestión de usuarios.
    
    Coordina operaciones entre el repositorio de usuarios y el servicio
    de email. Aplica validaciones de negocio y transforma entidades.
    
    Attributes:
        repository (UsuarioRepository): Repositorio para acceso a datos.
        email_service (EmailService): Servicio de envío de correos (opcional).
    """
    
    def __init__(self):
        self.repository = UsuarioRepository()
        
        # Inicializar servicio de correo
        try:
            email_config = get_email_config_from_env()
            self.email_service = EmailService(email_config)
        except Exception as e:
            logger.warning(f"No se pudo inicializar el servicio de correo: {e}")
            self.email_service = None
    
    def _mapear_usuario_respuesta(self, usuario: T_Usuario) -> UsuarioRespuesta:
        """
        Mapea un usuario del modelo de BD a esquema de respuesta de API.
        
        Transforma T_Usuario (modelo SQLAlchemy) a UsuarioRespuesta (schema Pydantic)
        incluyendo información de relaciones (rol, estado).
        
        Args:
            usuario (T_Usuario): Modelo de usuario de la base de datos.
        
        Returns:
            UsuarioRespuesta: Schema de respuesta con datos del usuario.
        
        Note:
            - Método privado (uso interno del servicio)
            - Incluye objetos RolInfo y EstadoInfo anidados
        """
        return UsuarioRespuesta(
            CN_Id_usuario=usuario.CN_Id_usuario,
            CT_Nombre_usuario=usuario.CT_Nombre_usuario,
            CT_Nombre=usuario.CT_Nombre,
            CT_Apellido_uno=usuario.CT_Apellido_uno,
            CT_Apellido_dos=usuario.CT_Apellido_dos,
            CT_Correo=usuario.CT_Correo,
            CN_Id_rol=usuario.CN_Id_rol,
            CN_Id_estado=usuario.CN_Id_estado,
            CF_Ultimo_acceso=usuario.CF_Ultimo_acceso,
            CF_Fecha_creacion=usuario.CF_Fecha_creacion,
            rol=RolInfo(
                id=usuario.rol.CN_Id_rol,
                nombre=usuario.rol.CT_Nombre_rol
            ) if usuario.rol else None,
            estado=EstadoInfo(
                id=usuario.estado.CN_Id_estado,
                nombre=usuario.estado.CT_Nombre_estado
            ) if usuario.estado else None
        )
    
    def obtener_todos_usuarios(self, db: Session) -> List[UsuarioRespuesta]:
        """Obtiene todos los usuarios"""
        usuarios = self.repository.obtener_usuarios(db)
        return [self._mapear_usuario_respuesta(usuario) for usuario in usuarios]
    
    def obtener_usuario(self, db: Session, usuario_id: str) -> Optional[UsuarioRespuesta]:
        """Obtiene un usuario por ID (cédula)"""
        usuario = self.repository.obtener_usuario_por_id(db, usuario_id)
        if usuario:
            return self._mapear_usuario_respuesta(usuario)
        return None
    
    async def crear_usuario(self, db: Session, cedula: str, nombre_usuario: str, nombre: str, apellido_uno: str, apellido_dos: str, correo: str, id_rol: int) -> UsuarioCreadoRespuesta:
        """
        Crea un nuevo usuario con contraseña temporal y se la envía por correo (RF-02.1).
        
        Genera una contraseña temporal de 8 caracteres, crea el usuario en la base de datos (queda confirmado) y envía
        un correo con la contraseña. La cuenta se crea siempre: si el correo no sale (servidor en fallo, cuenta de
        correo sin configurar, sin servicio de correo o más de 15 segundos), la respuesta lo dice y lleva la advertencia
        para que el Administrador use «Resetear Contraseña» cuando el correo vuelva a funcionar.
        
        Args:
            db (Session): Sesión de base de datos SQLAlchemy.
            cedula (str): Cédula del usuario (ID único).
            nombre_usuario (str): Nombre de usuario para login.
            nombre (str): Primer nombre del usuario.
            apellido_uno (str): Primer apellido del usuario.
            apellido_dos (str): Segundo apellido del usuario.
            correo (str): Correo electrónico del usuario.
            id_rol (int): ID del rol a asignar (1=Admin, 2=Usuario Judicial).
        
        Returns:
            UsuarioCreadoRespuesta: datos del usuario creado (con rol y estado), si la notificación se entregó y el
                texto para el Administrador. Nunca lleva la contraseña temporal.
        
        Example:
            >>> creado = await service.crear_usuario(
            ...     db, '123456789', 'jperez', 'Juan', 'Pérez', 'Gómez',
            ...     'jperez@example.com', id_rol=2
            ... )
            >>> creado.notificacion_entregada, creado.mensaje
            (True, 'Usuario creado exitosamente')
        
        Note:
            - La contraseña es aleatoria de 8 caracteres y solo viaja en el correo (RNF-08.1)
            - El usuario queda en estado "Activo" por defecto
            - CF_Ultimo_acceso = NULL (requiere cambio de contraseña)
            - Un fallo del correo no deshace la cuenta; el resultado queda en la bitácora desde el router
        """
        # Generar contraseña temporal
        contrasenna = _generar_contrasenna_temporal()
        
        # Crear usuario en la base de datos (el repositorio confirma: la cuenta existe pase lo que pase con el correo)
        usuario = self.repository.crear_usuario(db, cedula, nombre_usuario, nombre, apellido_uno, apellido_dos, correo, contrasenna, id_rol)
        
        # Se mapea antes de enviar: el envío puede tardar hasta el tiempo máximo y la respuesta ya no depende de la sesión
        datos_de_la_cuenta = self._mapear_usuario_respuesta(usuario).model_dump()
        
        # Enviar correo con la contraseña y decidir el texto según su resultado
        entregada = await self._enviar(
            lambda servicio: servicio.send_password_email(to=correo, password=contrasenna, usuario_nombre=nombre_usuario)
        )
        if entregada:
            logger.info("Cuenta creada y correo enviado a %s", enmascarar_correo(correo))
            mensaje = MENSAJE_CREACION_EXITOSA
        else:
            logger.warning("Cuenta creada sin notificación: no se pudo enviar el correo a %s", enmascarar_correo(correo))
            mensaje = MENSAJE_CREACION_ADVERTENCIA.format(correo=correo)

        return UsuarioCreadoRespuesta(**datos_de_la_cuenta, notificacion_entregada=entregada, mensaje=mensaje)
    
    def editar_usuario(self, db: Session, usuario_id: str, nombre_usuario: str, nombre: str, apellido_uno: str, apellido_dos: str, correo: str, id_rol: int, id_estado: int) -> Optional[UsuarioRespuesta]:
        """Edita un usuario incluyendo rol y estado"""
        usuario = self.repository.editar_usuario(db, usuario_id, nombre_usuario, nombre, apellido_uno, apellido_dos, correo, id_rol, id_estado)
        if usuario:
            return self._mapear_usuario_respuesta(usuario)
        return None

    def actualizar_ultimo_acceso(self, db: Session, usuario_id: str) -> Optional[UsuarioRespuesta]:
        """Actualiza el último acceso del usuario"""
        usuario = self.repository.actualizar_ultimo_acceso(db, usuario_id)
        if usuario:
            return self._mapear_usuario_respuesta(usuario)
        return None

    async def _enviar(self, operacion: Callable[[EmailService], Awaitable[bool]]) -> bool:
        """Ejecuta un envío de correo y devuelve si el servidor lo aceptó; nunca lanza (una cancelación sí sigue).

        Sin servicio de correo (configuración inválida al arrancar) o con una excepción inesperada, el envío cuenta como
        fallido. Solo se registra el tipo de la excepción: su texto puede traer el correo o la clave del servidor (RNF-08.2).
        """
        if self.email_service is None:
            logger.warning("Correo no enviado: no hay servicio de correo configurado")
            return False
        try:
            return bool(await operacion(self.email_service))
        except Exception as error:
            logger.warning("Correo no enviado: error inesperado al enviarlo (%s)", type(error).__name__)
            return False

    async def resetear_contrasenna_usuario(self, db: Session, usuario_id: str) -> Optional[ResultadoReseteo]:
        """
        Resetea la contraseña de un usuario y le envía la temporal por correo (RF-03.13, RF-03.14).
        
        El orden evita dejar la contraseña cambiada si el correo no sale: guarda la nueva contraseña SIN confirmar
        (un fallo de la base se detecta antes de enviar), envía el correo y solo si el servidor lo aceptó confirma el
        cambio; si el envío falla (o se cancela) deshace el cambio y el usuario conserva su contraseña y su último acceso.
        Solo debe ser llamado por administradores.
        
        Args:
            db (Session): Sesión de base de datos SQLAlchemy.
            usuario_id (str): Cédula del usuario a resetear.
        
        Returns:
            Optional[ResultadoReseteo]: si el correo se entregó y el texto para el Administrador; `None` si el
                usuario no existe.
        
        Note:
            - CF_Ultimo_acceso se pone en NULL (fuerza cambio obligatorio) solo si el cambio se confirma
            - La temporal es aleatoria de 8 caracteres y solo viaja en el correo (RNF-08.1)
            - Si el commit falla después del envío, la excepción llega al router (500) y queda la contraseña anterior;
              lleva `correo_entregado = True` para que el router deje el intento en la bitácora
            - La fila del usuario queda bloqueada mientras se envía (hasta el tiempo máximo del envío)
        """
        # Obtener el usuario
        usuario = self.repository.obtener_usuario_por_id(db, usuario_id)
        if not usuario:
            return None
        
        # Se copian antes de tocar la sesión: un commit o un rollback expira los atributos del usuario
        correo = usuario.CT_Correo
        nombre_completo = " ".join(
            parte for parte in (usuario.CT_Nombre, usuario.CT_Apellido_uno, usuario.CT_Apellido_dos) if parte
        )
        
        # Guardar la nueva contraseña sin confirmar (hash + último acceso vacío, con flush)
        nueva_contrasenna = _generar_contrasenna_temporal()
        if not self.repository.resetear_contrasenna(db, usuario_id, nueva_contrasenna, confirmar=False):
            return None
        
        # Enviar el correo con la temporal (reseteo por administrador) y decidir según su resultado
        try:
            entregada = await self._enviar(
                lambda servicio: servicio.send_password_reset_email(
                    to_email=correo, user_name=nombre_completo, new_password=nueva_contrasenna
                )
            )
        except BaseException:
            # Cancelación u otra interrupción durante el envío: no se deja la transacción abierta
            self.repository.descartar_cambios(db)
            raise
        
        if entregada:
            try:
                self.repository.confirmar_cambios(db)
            except Exception as error:
                # El correo ya salió y la contraseña no se guardó: el repositorio revirtió y la excepción original sigue su
                # camino (500). Se le deja una marca para que el router registre el intento en la bitácora (RF-21.4).
                error.correo_entregado = True
                raise
            logger.info("Contraseña reseteada y correo enviado a %s", enmascarar_correo(correo))
            return ResultadoReseteo(entregada=True, mensaje=MENSAJE_RESETEO_EXITOSO)
        
        self.repository.descartar_cambios(db)
        logger.warning("Contraseña no modificada: no se pudo enviar el correo a %s", enmascarar_correo(correo))
        return ResultadoReseteo(entregada=False, mensaje=MENSAJE_RESETEO_FALLIDO.format(correo=correo))
