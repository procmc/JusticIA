from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.usuario_repository import UsuarioRepository
from app.db.models.usuario import T_Usuario
from app.schemas.usuario_schemas import UsuarioRespuesta, RolInfo, EstadoInfo


class UsuarioService:
    """Servicio para usuarios"""
    
    def __init__(self):
        self.repository = UsuarioRepository()
    
    def _mapear_usuario_respuesta(self, usuario: T_Usuario) -> UsuarioRespuesta:
        """Mapea un usuario del modelo a la respuesta con objetos de rol y estado"""
        return UsuarioRespuesta(
            CN_Id_usuario=usuario.CN_Id_usuario,
            CT_Nombre_usuario=usuario.CT_Nombre_usuario,
            CT_Correo=usuario.CT_Correo,
            CN_Id_rol=usuario.CN_Id_rol,
            CN_Id_estado=usuario.CN_Id_estado,
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
    
    def obtener_usuario(self, db: Session, usuario_id: int) -> Optional[UsuarioRespuesta]:
        """Obtiene un usuario por ID"""
        usuario = self.repository.obtener_usuario_por_id(db, usuario_id)
        if usuario:
            return self._mapear_usuario_respuesta(usuario)
        return None
    
    def crear_usuario(self, db: Session, nombre_usuario: str, correo: str, contrasenna: str, id_rol: int) -> UsuarioRespuesta:
        """Crea un nuevo usuario"""
        usuario = self.repository.crear_usuario(db, nombre_usuario, correo, contrasenna, id_rol)
        return self._mapear_usuario_respuesta(usuario)
    
    def editar_usuario(self, db: Session, usuario_id: int, nombre_usuario: str, correo: str, id_rol: int) -> Optional[UsuarioRespuesta]:
        """Edita un usuario"""
        usuario = self.repository.editar_usuario(db, usuario_id, nombre_usuario, correo, id_rol)
        if usuario:
            return self._mapear_usuario_respuesta(usuario)
        return None
    
    def deshabilitar_usuario(self, db: Session, usuario_id: int) -> bool:
        """Deshabilita un usuario"""
        return self.repository.deshabilitar_usuario(db, usuario_id)