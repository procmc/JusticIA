"""
Repositorio de Acceso a Datos para Estados de Procesamiento de Documentos.

Este módulo gestiona las operaciones de consulta sobre la tabla T_Estado_procesamiento,
que controla el ciclo de vida del procesamiento de documentos en el sistema de ingesta.

Estados del sistema:
    - "Pendiente": Documento en cola, esperando procesamiento
    - "Procesado": Documento procesado exitosamente y vectorizado
    - "Error": Falló el procesamiento (parse, embedding, Milvus, etc.)

Responsabilidades:
    - Consultar estados por nombre (para actualizar documentos)
    - Consultar estados por ID (para verificaciones)
    - NO crea ni modifica estados (tabla de catálogo estática)

Patrón de uso:
    1. Durante ingesta: Obtener ID de "Pendiente" para nuevos documentos
    2. Después de procesamiento exitoso: Cambiar a "Procesado"
    3. En caso de error: Marcar como "Error" con info adicional

Integración:
    - document_processor: Actualiza estados durante el flujo de procesamiento
    - celery_tasks: Marca errores cuando fallan tareas asíncronas
    - documento_repository: Lee estados para filtrar documentos procesados

Example:
    >>> repo = EstadoProcesamientoRepository()
    >>> estado_pendiente = repo.obtener_por_nombre(db, "Pendiente")
    >>> print(estado_pendiente.CN_Id_estado)
    1
    >>> documento.CN_Id_estado = estado_pendiente.CN_Id_estado
    >>> db.commit()

Note:
    - La tabla T_Estado_procesamiento es un catálogo estático (seed data)
    - No se deben insertar/eliminar estados en runtime
    - Los nombres de estados son case-sensitive

Ver también:
    - app.db.models.estado_procesamiento: Modelo SQLAlchemy
    - app.services.ingesta.file_management.document_processor: Consumidor principal
    - app.repositories.documento_repository: Actualiza estados de documentos

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0
"""
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
