from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.usuario_schemas import (
    UsuarioCrear, 
    UsuarioActualizar, 
    UsuarioCambiarEstado,
    UsuarioRespuesta,
    UsuarioLista,
    RolBase,
    EstadoBase
)
import math


class UsuarioService:
    """Servicio para la lógica de negocio de usuarios"""
    
    def __init__(self):
        self.usuario_repo = UsuarioRepository()
    
    def obtener_usuario_por_id(self, db: Session, usuario_id: int) -> UsuarioRespuesta:
        """Obtiene un usuario por su ID"""
        usuario = self.usuario_repo.obtener_usuario_por_id(db, usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {usuario_id} no encontrado"
            )
        return UsuarioRespuesta.from_orm(usuario)
    
    def obtener_usuarios(
        self, 
        db: Session, 
        pagina: int = 1, 
        tamaño_pagina: int = 10,
        filtro_busqueda: Optional[str] = None,
        id_estado: Optional[int] = None,
        id_rol: Optional[int] = None
    ) -> UsuarioLista:
        """Obtiene una lista paginada de usuarios con filtros"""
        # Validar parámetros de paginación
        if pagina < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El número de página debe ser mayor a 0"
            )
        
        if tamaño_pagina < 1 or tamaño_pagina > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El tamaño de página debe estar entre 1 y 100"
            )
        
        skip = (pagina - 1) * tamaño_pagina
        usuarios, total = self.usuario_repo.obtener_usuarios(
            db, skip=skip, limit=tamaño_pagina, 
            filtro_busqueda=filtro_busqueda,
            id_estado=id_estado,
            id_rol=id_rol
        )
        
        usuarios_respuesta = [UsuarioRespuesta.from_orm(usuario) for usuario in usuarios]
        total_paginas = math.ceil(total / tamaño_pagina) if total > 0 else 0
        
        return UsuarioLista(
            usuarios=usuarios_respuesta,
            total=total,
            pagina=pagina,
            tamaño_pagina=tamaño_pagina,
            total_paginas=total_paginas
        )
    
    def crear_usuario(self, db: Session, usuario_crear: UsuarioCrear) -> UsuarioRespuesta:
        """Crea un nuevo usuario"""
        # Verificar si el usuario ya existe
        if not self.usuario_repo.verificar_usuario_unico(
            db, usuario_crear.correo, usuario_crear.nombre_usuario
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un usuario con ese correo electrónico o nombre de usuario"
            )
        
        # Validar que el rol existe si se proporciona
        if usuario_crear.id_rol:
            roles = self.usuario_repo.obtener_roles(db)
            if not any(rol.CN_Id_rol == usuario_crear.id_rol for rol in roles):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El rol con ID {usuario_crear.id_rol} no existe"
                )
        
        # Validar que el estado existe si se proporciona
        if usuario_crear.id_estado:
            estados = self.usuario_repo.obtener_estados(db)
            if not any(estado.CN_Id_estado == usuario_crear.id_estado for estado in estados):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El estado con ID {usuario_crear.id_estado} no existe"
                )
        
        try:
            usuario = self.usuario_repo.crear_usuario(db, usuario_crear)
            return UsuarioRespuesta.from_orm(usuario)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear el usuario: {str(e)}"
            )
    
    def actualizar_usuario(self, db: Session, usuario_id: int, usuario_actualizar: UsuarioActualizar) -> UsuarioRespuesta:
        """Actualiza un usuario existente"""
        # Verificar que el usuario existe
        usuario_existente = self.usuario_repo.obtener_usuario_por_id(db, usuario_id)
        if not usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {usuario_id} no encontrado"
            )
        
        # Verificar unicidad si se actualiza correo o nombre de usuario
        if usuario_actualizar.correo or usuario_actualizar.nombre_usuario:
            correo = usuario_actualizar.correo or usuario_existente.CT_Correo
            nombre_usuario = usuario_actualizar.nombre_usuario or usuario_existente.CT_Nombre_usuario
            
            if not self.usuario_repo.verificar_usuario_unico(db, correo, nombre_usuario, usuario_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe otro usuario con ese correo electrónico o nombre de usuario"
                )
        
        # Validar que el rol existe si se proporciona
        if usuario_actualizar.id_rol:
            roles = self.usuario_repo.obtener_roles(db)
            if not any(rol.CN_Id_rol == usuario_actualizar.id_rol for rol in roles):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El rol con ID {usuario_actualizar.id_rol} no existe"
                )
        
        # Validar que el estado existe si se proporciona
        if usuario_actualizar.id_estado:
            estados = self.usuario_repo.obtener_estados(db)
            if not any(estado.CN_Id_estado == usuario_actualizar.id_estado for estado in estados):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El estado con ID {usuario_actualizar.id_estado} no existe"
                )
        
        try:
            usuario = self.usuario_repo.actualizar_usuario(db, usuario_id, usuario_actualizar)
            if not usuario:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Usuario con ID {usuario_id} no encontrado"
                )
            return UsuarioRespuesta.from_orm(usuario)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar el usuario: {str(e)}"
            )
    
    def cambiar_estado_usuario(self, db: Session, usuario_id: int, cambio_estado: UsuarioCambiarEstado) -> UsuarioRespuesta:
        """Cambia el estado de un usuario (en lugar de eliminarlo)"""
        # Verificar que el usuario existe
        usuario_existente = self.usuario_repo.obtener_usuario_por_id(db, usuario_id)
        if not usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {usuario_id} no encontrado"
            )
        
        # Validar que el estado existe
        estados = self.usuario_repo.obtener_estados(db)
        if not any(estado.CN_Id_estado == cambio_estado.id_estado for estado in estados):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El estado con ID {cambio_estado.id_estado} no existe"
            )
        
        try:
            usuario = self.usuario_repo.cambiar_estado_usuario(db, usuario_id, cambio_estado.id_estado)
            if not usuario:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Usuario con ID {usuario_id} no encontrado"
                )
            return UsuarioRespuesta.from_orm(usuario)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al cambiar el estado del usuario: {str(e)}"
            )
    
    def obtener_roles(self, db: Session) -> List[RolBase]:
        """Obtiene todos los roles disponibles"""
        try:
            roles = self.usuario_repo.obtener_roles(db)
            return [RolBase(id=rol.CN_Id_rol, nombre=rol.CT_Nombre_rol) for rol in roles]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener los roles: {str(e)}"
            )
    
    def obtener_estados(self, db: Session) -> List[EstadoBase]:
        """Obtiene todos los estados disponibles"""
        try:
            estados = self.usuario_repo.obtener_estados(db)
            return [EstadoBase(id=estado.CN_Id_estado, nombre=estado.CT_Nombre_estado) for estado in estados]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener los estados: {str(e)}"
            )
    
    def autenticar_usuario(self, db: Session, correo: str, contrasenna: str) -> Optional[UsuarioRespuesta]:
        """Autentica un usuario por correo y contraseña"""
        usuario = self.usuario_repo.obtener_usuario_por_correo(db, correo)
        if not usuario:
            return None
        
        if not self.usuario_repo.verificar_contrasenna(contrasenna, usuario.CT_Contrasenna):
            return None
        
        return UsuarioRespuesta.from_orm(usuario)
