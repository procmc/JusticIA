from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.db.models.usuario import T_Usuario
from app.db.models.estado import T_Estado
from passlib.context import CryptContext
from datetime import datetime


class UsuarioRepository:
    """Repositorio simple para operaciones CRUD de usuarios"""
    
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
        
        db.commit()
        db.refresh(usuario)
        return usuario
