from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.usuario_repository import UsuarioRepository
from app.db.models.usuario import T_Usuario


class UsuarioService:
    """Servicio simple para usuarios"""
    
    def __init__(self):
        self.repository = UsuarioRepository()
    
    def obtener_todos_usuarios(self, db: Session) -> List[T_Usuario]:
        """Obtiene todos los usuarios"""
        return self.repository.obtener_usuarios(db)
    
    def obtener_usuario(self, db: Session, usuario_id: int) -> Optional[T_Usuario]:
        """Obtiene un usuario por ID"""
        return self.repository.obtener_usuario_por_id(db, usuario_id)
    
    def crear_usuario(self, db: Session, nombre_usuario: str, correo: str, contrasenna: str, id_rol: int) -> T_Usuario:
        """Crea un nuevo usuario"""
        return self.repository.crear_usuario(db, nombre_usuario, correo, contrasenna, id_rol)
    
    def editar_usuario(self, db: Session, usuario_id: int, nombre_usuario: str, correo: str, id_rol: int) -> Optional[T_Usuario]:
        """Edita un usuario"""
        return self.repository.editar_usuario(db, usuario_id, nombre_usuario, correo, id_rol)
    
    def deshabilitar_usuario(self, db: Session, usuario_id: int) -> bool:
        """Deshabilita un usuario"""
        return self.repository.deshabilitar_usuario(db, usuario_id)
