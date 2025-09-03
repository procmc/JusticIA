from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.db.models.usuario import T_Usuario
from app.db.models.estado import T_Estado
from passlib.context import CryptContext


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
    
    def obtener_usuario_por_id(self, db: Session, usuario_id: int) -> Optional[T_Usuario]:
        """Obtiene un usuario por su ID"""
        return (
            db.query(T_Usuario)
            .options(joinedload(T_Usuario.rol), joinedload(T_Usuario.estado))
            .filter(T_Usuario.CN_Id_usuario == usuario_id)
            .first()
        )
    
    def editar_usuario(self, db: Session, usuario_id: int, nombre_usuario: str, correo: str, id_rol: int) -> Optional[T_Usuario]:
        """Edita los datos básicos de un usuario"""
        usuario = self.obtener_usuario_por_id(db, usuario_id)
        if not usuario:
            return None
        
        usuario.CT_Nombre_usuario = nombre_usuario
        usuario.CT_Correo = correo
        usuario.CN_Id_rol = id_rol
        
        db.commit()
        db.refresh(usuario)
        return usuario
    
    def deshabilitar_usuario(self, db: Session, usuario_id: int) -> bool:
        """Deshabilita un usuario cambiando su estado a inactivo"""
        usuario = self.obtener_usuario_por_id(db, usuario_id)
        if not usuario:
            return False
        
        # Buscar el estado "Inactivo" (asumiendo que tiene ID 2)
        estado_inactivo = db.query(T_Estado).filter(T_Estado.CT_Nombre_estado == "Inactivo").first()
        if estado_inactivo:
            usuario.CN_Id_estado = estado_inactivo.CN_Id_estado
            db.commit()
            return True
        
        return False
    
    def crear_usuario(self, db: Session, nombre_usuario: str, correo: str, contrasenna: str, id_rol: int) -> T_Usuario:
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
                CT_Nombre_usuario=nombre_usuario,
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
