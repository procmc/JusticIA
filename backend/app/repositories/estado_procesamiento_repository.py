from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models.estado_procesamiento import T_Estado_procesamiento


class EstadoProcesamientoRepository:
    """Repositorio para operaciones CRUD de estados de procesamiento"""
    
    def obtener_por_nombre(self, db: Session, nombre_estado: str) -> Optional[T_Estado_procesamiento]:
        """
        Obtiene un estado de procesamiento por su nombre.
        
        Args:
            db: Sesión de base de datos
            nombre_estado: Nombre del estado ('Pendiente', 'Procesado', 'Error')
            
        Returns:
            Optional[T_Estado_procesamiento]: Estado encontrado o None
        """
        stmt = select(T_Estado_procesamiento).where(T_Estado_procesamiento.CT_Nombre_estado == nombre_estado)
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def obtener_por_id(self, db: Session, estado_id: int) -> Optional[T_Estado_procesamiento]:
        """
        Obtiene un estado de procesamiento por su ID.
        
        Args:
            db: Sesión de base de datos
            estado_id: ID del estado
            
        Returns:
            Optional[T_Estado_procesamiento]: Estado encontrado o None
        """
        stmt = select(T_Estado_procesamiento).where(T_Estado_procesamiento.CN_Id_estado == estado_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()
