"""Repositorio de Acceso a Datos de Usuarios del Sistema.

Este módulo implementa el patrón Repository para abstraer el acceso a datos
de usuarios del sistema JusticIA. Maneja operaciones CRUD, autenticación,
gestión de contraseñas con bcrypt, y avatares de usuario.

Arquitectura de usuarios:
    - Identificación: Cédula como Primary Key (CN_Id_usuario)
    - Roles: ADMINISTRADOR, USUARIO_JUDICIAL (RBAC)
    - Estados: ACTIVO, INACTIVO (control de acceso)
    - Contraseñas: Hash bcrypt con salt automático
    - Avatares: Soporte para uploads, iconos predefinidos, o iniciales

Operaciones principales:
    - crear_usuario: Crear con contraseña hasheada automáticamente
    - obtener_usuario_por_id: Buscar por cédula con relaciones cargadas
    - editar_usuario: Actualizar datos incluyendo rol y estado
    - resetear_contrasenna: Reset con limpieza de CF_Ultimo_acceso
    - actualizar_ultimo_acceso: Registro de login
    - Gestión de avatares: actualizar_avatar_ruta, actualizar_avatar_tipo, limpiar_avatar

Modelo de datos:
    T_Usuario:
        - CN_Id_usuario (str, PK): Cédula del usuario
        - CT_Nombre_usuario (str): Username único
        - CT_Nombre, CT_Apellido_uno, CT_Apellido_dos (str): Nombre completo
        - CT_Correo (str): Email único
        - CT_Contrasenna (str): Hash bcrypt de la contraseña
        - CN_Id_rol (int, FK): Rol del usuario (1=Admin, 2=Judicial)
        - CN_Id_estado (int, FK): Estado (1=Activo, 2=Inactivo)
        - CF_Ultimo_acceso (datetime, nullable): Último login (null = primer acceso)
        - CT_Avatar_ruta (str, nullable): Ruta imagen personalizada
        - CT_Avatar_tipo (str, nullable): Tipo de avatar ('default', 'upload', 'icon')

Seguridad de contraseñas:
    Utiliza passlib.CryptContext con bcrypt:
        - Hashing automático en crear_usuario y resetear_contrasenna
        - Salt único por contraseña
        - Costo de trabajo configurable (default: 12 rounds)
        - Algoritmos deprecated detectados automáticamente

Gestión de primer acceso:
    CF_Ultimo_acceso = null indica que el usuario debe cambiar su contraseña.
    Al resetear contraseña, se limpia este campo para forzar cambio.

Example:
    ```python
    from app.repositories.usuario_repository import UsuarioRepository
    from app.db.database import get_db
    
    repo = UsuarioRepository()
    db = next(get_db())
    
    # Crear usuario (contraseña se hashea automáticamente)
    usuario = repo.crear_usuario(
        db=db,
        cedula='123456789',
        nombre_usuario='jperez',
        nombre='Juan',
        apellido_uno='Pérez',
        apellido_dos='García',
        correo='jperez@example.com',
        contrasenna='password123',  # Se hashea internamente
        id_rol=2  # Usuario judicial
    )
    
    # Resetear contraseña (limpia CF_Ultimo_acceso)
    repo.resetear_contrasenna(db, '123456789', 'nueva_password')
    
    # Actualizar avatar
    repo.actualizar_avatar_ruta(db, '123456789', '/avatars/jperez.jpg')
    
    # Registrar login exitoso
    repo.actualizar_ultimo_acceso(db, '123456789')
    ```

Note:
    Todos los métodos que modifican datos usan eager loading (joinedload)
    para cargar relaciones (rol, estado) y evitar lazy loading issues.

See Also:
    - app.db.models.usuario.T_Usuario: Modelo SQLAlchemy
    - app.services.usuario_service.UsuarioService: Lógica de negocio
    - app.services.auth_service.AuthService: Autenticación y verificación de contraseñas
    - passlib.context.CryptContext: Librería de hashing de contraseñas
"""

from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.db.models.usuario import T_Usuario
from app.db.models.estado import T_Estado
from passlib.context import CryptContext
from datetime import datetime


class UsuarioRepository:
    """Repositorio de acceso a datos para usuarios del sistema.
    
    Gestiona usuarios con autenticación bcrypt, roles, estados, y avatares.
    Implementa operaciones CRUD y consultas especializadas.
    
    Attributes:
        pwd_context (CryptContext): Contexto de bcrypt para hashing de contraseñas.
    """
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def _hash_password(self, password: str) -> str:
        """Encripta la contraseña"""
        return self.pwd_context.hash(password)
    
    def obtener_usuarios(self, db: Session) -> List[T_Usuario]:
        """Obtiene todos los usuarios"""
        return (
            db.query(T_Usuario)
            .options(joinedload(T_Usuario.rol), joinedload(T_Usuario.estado))
            .all()
        )
    
    def obtener_usuario_por_id(self, db: Session, usuario_id: str) -> Optional[T_Usuario]:
        """Obtiene un usuario por su ID (cédula)"""
        return (
            db.query(T_Usuario)
            .options(joinedload(T_Usuario.rol), joinedload(T_Usuario.estado))
            .filter(T_Usuario.CN_Id_usuario == usuario_id)
            .first()
        )
    
    def editar_usuario(self, db: Session, usuario_id: str, nombre_usuario: str, nombre: str, apellido_uno: str, apellido_dos: str, correo: str, id_rol: int, id_estado: int) -> Optional[T_Usuario]:
        """Edita los datos de un usuario incluyendo rol y estado"""
        usuario = self.obtener_usuario_por_id(db, usuario_id)
        if not usuario:
            return None
        
        usuario.CT_Nombre_usuario = nombre_usuario
        usuario.CT_Nombre = nombre
        usuario.CT_Apellido_uno = apellido_uno
        usuario.CT_Apellido_dos = apellido_dos
        usuario.CT_Correo = correo
        usuario.CN_Id_rol = id_rol
        usuario.CN_Id_estado = id_estado
        
        db.commit()
        db.refresh(usuario)
        return usuario
    
    def crear_usuario(self, db: Session, cedula: str, nombre_usuario: str, nombre: str, apellido_uno: str, apellido_dos: str, correo: str, contrasenna: str, id_rol: int) -> T_Usuario:
        """Crea un nuevo usuario"""
        try:
            # Encriptar contraseña
            contrasenna_hash = self._hash_password(contrasenna)
            
            # Buscar el estado "Activo" (asumiendo que tiene ID 1)
            estado_activo = db.query(T_Estado).filter(T_Estado.CT_Nombre_estado == "Activo").first()
            if not estado_activo:
                estado_activo = db.query(T_Estado).first()  # Si no encuentra "Activo", toma el primero
            
            if not estado_activo:
                raise ValueError("No hay estados disponibles en la base de datos")
            
            nuevo_usuario = T_Usuario(
                CN_Id_usuario=cedula,  # Usar cédula como PK
                CT_Nombre_usuario=nombre_usuario,
                CT_Nombre=nombre,
                CT_Apellido_uno=apellido_uno,
                CT_Apellido_dos=apellido_dos,
                CT_Correo=correo,
                CT_Contrasenna=contrasenna_hash,
                CN_Id_rol=id_rol,
                CN_Id_estado=estado_activo.CN_Id_estado
            )
            
            db.add(nuevo_usuario)
            db.commit()
            db.refresh(nuevo_usuario)
            
            # Cargar las relaciones
            usuario_completo = (
                db.query(T_Usuario)
                .options(joinedload(T_Usuario.rol), joinedload(T_Usuario.estado))
                .filter(T_Usuario.CN_Id_usuario == nuevo_usuario.CN_Id_usuario)
                .first()
            )
            
            return usuario_completo
        
        except Exception as e:
            db.rollback()
            print(f"Error al crear usuario: {e}")
            raise

    def actualizar_ultimo_acceso(self, db: Session, usuario_id: str) -> Optional[T_Usuario]:
        """Actualiza el último acceso del usuario"""
        usuario = self.obtener_usuario_por_id(db, usuario_id)
        if not usuario:
            return None
        
        usuario.CF_Ultimo_acceso = datetime.now()
        db.commit()
        db.refresh(usuario)
        return usuario

    def resetear_contrasenna(self, db: Session, usuario_id: str, nueva_contrasenna: str) -> Optional[T_Usuario]:
        """Resetea la contraseña de un usuario"""
        usuario = self.obtener_usuario_por_id(db, usuario_id)
        if not usuario:
            return None
        
        # Encriptar la nueva contraseña
        contrasenna_hash = self._hash_password(nueva_contrasenna)
        usuario.CT_Contrasenna = contrasenna_hash
        
        # Limpiar fecha de último acceso para forzar cambio de contraseña obligatorio
        usuario.CF_Ultimo_acceso = None
        
        db.commit()
        db.refresh(usuario)
        return usuario

    def actualizar_avatar_ruta(self, db: Session, usuario_id: str, ruta_avatar: str) -> Optional[T_Usuario]:
        """Actualiza la ruta del avatar de un usuario"""
        try:
            usuario = self.obtener_usuario_por_id(db, usuario_id)
            if not usuario:
                return None
            
            usuario.CT_Avatar_ruta = ruta_avatar
            usuario.CT_Avatar_tipo = None  # Limpia preferencia de avatar predefinido
            
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception as e:
            db.rollback()
            raise

    def actualizar_avatar_tipo(self, db: Session, usuario_id: str, tipo_avatar: str) -> Optional[T_Usuario]:
        """Actualiza el tipo de avatar de un usuario (predefinido o iniciales)"""
        try:
            usuario = self.obtener_usuario_por_id(db, usuario_id)
            if not usuario:
                return None
            
            usuario.CT_Avatar_tipo = tipo_avatar
            usuario.CT_Avatar_ruta = None  # Limpia imagen personalizada
            
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception as e:
            db.rollback()
            raise

    def limpiar_avatar(self, db: Session, usuario_id: str) -> Optional[T_Usuario]:
        """Limpia tanto la ruta como el tipo de avatar de un usuario"""
        try:
            usuario = self.obtener_usuario_por_id(db, usuario_id)
            if not usuario:
                return None
            
            usuario.CT_Avatar_ruta = None
            usuario.CT_Avatar_tipo = None
            
            db.commit()
            db.refresh(usuario)
            return usuario
        except Exception as e:
            db.rollback()
            raise
