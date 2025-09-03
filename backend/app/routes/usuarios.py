from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.usuario_service import UsuarioService
from app.schemas.usuario_schemas import (
    UsuarioCrear,
    UsuarioActualizar,
    UsuarioCambiarEstado,
    UsuarioRespuesta,
    UsuarioLista,
    RolBase,
    EstadoBase,
    MensajeRespuesta
)

router = APIRouter()
usuario_service = UsuarioService()


@router.get("/", response_model=UsuarioLista, summary="Obtener usuarios")
async def obtener_usuarios(
    pagina: int = Query(1, ge=1, description="Número de página"),
    tamaño_pagina: int = Query(10, ge=1, le=100, description="Cantidad de usuarios por página"),
    filtro_busqueda: Optional[str] = Query(None, description="Filtro de búsqueda por nombre o correo"),
    id_estado: Optional[int] = Query(None, description="Filtrar por ID de estado"),
    id_rol: Optional[int] = Query(None, description="Filtrar por ID de rol"),
    db: Session = Depends(get_db)
):
    """
    Obtiene una lista paginada de usuarios con filtros opcionales.
    
    - **pagina**: Número de página (mínimo 1)
    - **tamaño_pagina**: Cantidad de usuarios por página (1-100)
    - **filtro_busqueda**: Búsqueda por nombre de usuario o correo
    - **id_estado**: Filtrar usuarios por estado específico
    - **id_rol**: Filtrar usuarios por rol específico
    """
    return usuario_service.obtener_usuarios(
        db=db,
        pagina=pagina,
        tamaño_pagina=tamaño_pagina,
        filtro_busqueda=filtro_busqueda,
        id_estado=id_estado,
        id_rol=id_rol
    )


@router.get("/{usuario_id}", response_model=UsuarioRespuesta, summary="Obtener usuario por ID")
async def obtener_usuario(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene un usuario específico por su ID.
    
    - **usuario_id**: ID único del usuario
    """
    return usuario_service.obtener_usuario_por_id(db=db, usuario_id=usuario_id)


@router.post("/", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED, summary="Crear usuario")
async def crear_usuario(
    usuario: UsuarioCrear,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo usuario en el sistema.
    
    - **nombre_usuario**: Nombre de usuario único (3-50 caracteres)
    - **correo**: Dirección de correo electrónico válida
    - **contrasenna**: Contraseña (mínimo 6 caracteres)
    - **id_rol**: ID del rol asignado (opcional)
    - **id_estado**: ID del estado inicial (opcional)
    """
    return usuario_service.crear_usuario(db=db, usuario_crear=usuario)


@router.put("/{usuario_id}", response_model=UsuarioRespuesta, summary="Actualizar usuario")
async def actualizar_usuario(
    usuario_id: int,
    usuario: UsuarioActualizar,
    db: Session = Depends(get_db)
):
    """
    Actualiza un usuario existente.
    
    - **usuario_id**: ID del usuario a actualizar
    - **Campos opcionales**: nombre_usuario, correo, contrasenna, id_rol, id_estado
    """
    return usuario_service.actualizar_usuario(
        db=db, 
        usuario_id=usuario_id, 
        usuario_actualizar=usuario
    )


@router.patch("/{usuario_id}/estado", response_model=UsuarioRespuesta, summary="Cambiar estado del usuario")
async def cambiar_estado_usuario(
    usuario_id: int,
    cambio_estado: UsuarioCambiarEstado,
    db: Session = Depends(get_db)
):
    """
    Cambia el estado de un usuario (alternativa a la eliminación).
    
    - **usuario_id**: ID del usuario
    - **id_estado**: Nuevo ID del estado del usuario
    """
    return usuario_service.cambiar_estado_usuario(
        db=db,
        usuario_id=usuario_id,
        cambio_estado=cambio_estado
    )


@router.get("/catalogo/roles", response_model=List[RolBase], summary="Obtener roles disponibles")
async def obtener_roles(db: Session = Depends(get_db)):
    """
    Obtiene todos los roles disponibles en el sistema.
    """
    return usuario_service.obtener_roles(db=db)


@router.get("/catalogo/estados", response_model=List[EstadoBase], summary="Obtener estados disponibles")
async def obtener_estados(db: Session = Depends(get_db)):
    """
    Obtiene todos los estados disponibles en el sistema.
    """
    return usuario_service.obtener_estados(db=db)


# Ruta adicional para autenticación (si es necesaria)
@router.post("/autenticar", response_model=UsuarioRespuesta, summary="Autenticar usuario")
async def autenticar_usuario(
    correo: str,
    contrasenna: str,
    db: Session = Depends(get_db)
):
    """
    Autentica un usuario con correo y contraseña.
    
    - **correo**: Correo electrónico del usuario
    - **contrasenna**: Contraseña del usuario
    """
    usuario = usuario_service.autenticar_usuario(db=db, correo=correo, contrasenna=contrasenna)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    return usuario


# Endpoints de información adicional
@router.get("/{usuario_id}/estado", response_model=EstadoBase, summary="Obtener estado actual del usuario")
async def obtener_estado_usuario(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene el estado actual de un usuario específico.
    """
    usuario = usuario_service.obtener_usuario_por_id(db=db, usuario_id=usuario_id)
    if not usuario.estado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no tiene un estado asignado"
        )
    return usuario.estado


@router.get("/{usuario_id}/rol", response_model=RolBase, summary="Obtener rol actual del usuario")
async def obtener_rol_usuario(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene el rol actual de un usuario específico.
    """
    usuario = usuario_service.obtener_usuario_por_id(db=db, usuario_id=usuario_id)
    if not usuario.rol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no tiene un rol asignado"
        )
    return usuario.rol
