"""
Repository para operaciones de base de datos de bitácora.
Maneja todas las consultas y operaciones CRUD sobre T_Bitacora.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc, func
import logging

from app.db.models.bitacora import T_Bitacora

logger = logging.getLogger(__name__)


class BitacoraRepository:
    """Repository para operaciones CRUD de bitácora"""
    
    def crear(
        self,
        db: Session,
        usuario_id: str,
        tipo_accion_id: int,
        texto: str,
        expediente_id: Optional[int] = None,
        info_adicional: Optional[str] = None
    ) -> T_Bitacora:
        """
        Crea un nuevo registro de bitácora en la base de datos.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            tipo_accion_id: ID del tipo de acción
            texto: Descripción de la acción
            expediente_id: ID del expediente relacionado (opcional)
            info_adicional: JSON string con información adicional (opcional)
            
        Returns:
            T_Bitacora: Registro de bitácora creado
        """
        try:
            bitacora = T_Bitacora(
                CN_Id_usuario=usuario_id,
                CN_Id_tipo_accion=tipo_accion_id,
                CT_Texto=texto,
                CN_Id_expediente=expediente_id,
                CT_Informacion_adicional=info_adicional,
                CF_Fecha_hora=datetime.utcnow()
            )
            
            db.add(bitacora)
            db.commit()
            db.refresh(bitacora)
            
            return bitacora
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creando registro de bitácora: {e}")
            raise
    
    
    def obtener_por_usuario(
        self,
        db: Session,
        usuario_id: str,
        limite: int = 100,
        tipo_accion_id: Optional[int] = None
    ) -> List[T_Bitacora]:
        """
        Obtiene registros de bitácora de un usuario específico.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            limite: Número máximo de registros a retornar
            tipo_accion_id: Filtrar por tipo de acción (opcional)
            
        Returns:
            List[T_Bitacora]: Lista de registros ordenados por fecha descendente
        """
        try:
            query = select(T_Bitacora).where(T_Bitacora.CN_Id_usuario == usuario_id)
            
            if tipo_accion_id:
                query = query.where(T_Bitacora.CN_Id_tipo_accion == tipo_accion_id)
            
            query = query.order_by(desc(T_Bitacora.CF_Fecha_hora)).limit(limite)
            
            result = db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error obteniendo bitácora de usuario {usuario_id}: {e}")
            raise
    
    
    def obtener_por_expediente(
        self,
        db: Session,
        expediente_id: int,
        limite: int = 100
    ) -> List[T_Bitacora]:
        """
        Obtiene registros de bitácora de un expediente específico.
        
        Args:
            db: Sesión de base de datos
            expediente_id: ID del expediente
            limite: Número máximo de registros a retornar
            
        Returns:
            List[T_Bitacora]: Lista de registros ordenados por fecha descendente
        """
        try:
            query = (
                select(T_Bitacora)
                .where(T_Bitacora.CN_Id_expediente == expediente_id)
                .order_by(desc(T_Bitacora.CF_Fecha_hora))
                .limit(limite)
            )
            
            result = db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error obteniendo bitácora de expediente {expediente_id}: {e}")
            raise
    
    
    def obtener_con_filtros(
        self,
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        tipo_accion_id: Optional[int] = None,
        usuario_id: Optional[str] = None,
        limite: int = 200
    ) -> List[T_Bitacora]:
        """
        Obtiene registros de bitácora con múltiples filtros.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango (opcional)
            fecha_fin: Fecha de fin del rango (opcional)
            tipo_accion_id: Filtrar por tipo de acción (opcional)
            usuario_id: Filtrar por usuario (opcional)
            limite: Número máximo de registros a retornar
            
        Returns:
            List[T_Bitacora]: Lista de registros ordenados por fecha descendente
        """
        try:
            query = select(T_Bitacora)
            
            # Construir condiciones de filtro
            conditions = []
            if fecha_inicio:
                conditions.append(T_Bitacora.CF_Fecha_hora >= fecha_inicio)
            if fecha_fin:
                conditions.append(T_Bitacora.CF_Fecha_hora <= fecha_fin)
            if tipo_accion_id:
                conditions.append(T_Bitacora.CN_Id_tipo_accion == tipo_accion_id)
            if usuario_id:
                conditions.append(T_Bitacora.CN_Id_usuario == usuario_id)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(desc(T_Bitacora.CF_Fecha_hora)).limit(limite)
            
            result = db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error obteniendo bitácora con filtros: {e}")
            raise
    
    
    def obtener_por_id(self, db: Session, bitacora_id: int) -> Optional[T_Bitacora]:
        """
        Obtiene un registro de bitácora por su ID.
        
        Args:
            db: Sesión de base de datos
            bitacora_id: ID del registro de bitácora
            
        Returns:
            Optional[T_Bitacora]: Registro encontrado o None
        """
        try:
            stmt = select(T_Bitacora).where(T_Bitacora.CN_Id_bitacora == bitacora_id)
            result = db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error obteniendo bitácora por ID {bitacora_id}: {e}")
            raise
    
    
    def contar_por_usuario(
        self,
        db: Session,
        usuario_id: str,
        tipo_accion_id: Optional[int] = None
    ) -> int:
        """
        Cuenta el número de registros de bitácora de un usuario.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            tipo_accion_id: Filtrar por tipo de acción (opcional)
            
        Returns:
            int: Número de registros
        """
        try:
            query = select(func.count(T_Bitacora.CN_Id_bitacora)).where(
                T_Bitacora.CN_Id_usuario == usuario_id
            )
            
            if tipo_accion_id:
                query = query.where(T_Bitacora.CN_Id_tipo_accion == tipo_accion_id)
            
            result = db.execute(query)
            return result.scalar()
            
        except Exception as e:
            logger.error(f"Error contando registros de usuario {usuario_id}: {e}")
            raise
    
    
    def contar_por_tipo_accion(
        self,
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> List[tuple]:
        """
        Cuenta registros agrupados por tipo de acción.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango (opcional)
            fecha_fin: Fecha de fin del rango (opcional)
            
        Returns:
            List[tuple]: Lista de (tipo_accion_id, conteo)
        """
        try:
            query = select(
                T_Bitacora.CN_Id_tipo_accion,
                func.count(T_Bitacora.CN_Id_bitacora)
            )
            
            conditions = []
            if fecha_inicio:
                conditions.append(T_Bitacora.CF_Fecha_hora >= fecha_inicio)
            if fecha_fin:
                conditions.append(T_Bitacora.CF_Fecha_hora <= fecha_fin)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.group_by(T_Bitacora.CN_Id_tipo_accion)
            
            result = db.execute(query)
            return result.all()
            
        except Exception as e:
            logger.error(f"Error contando por tipo de acción: {e}")
            raise
    
    
    def obtener_ultima_accion_usuario(
        self,
        db: Session,
        usuario_id: str,
        tipo_accion_id: Optional[int] = None
    ) -> Optional[T_Bitacora]:
        """
        Obtiene la última acción registrada de un usuario.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            tipo_accion_id: Filtrar por tipo de acción (opcional)
            
        Returns:
            Optional[T_Bitacora]: Último registro o None
        """
        try:
            query = (
                select(T_Bitacora)
                .where(T_Bitacora.CN_Id_usuario == usuario_id)
            )
            
            if tipo_accion_id:
                query = query.where(T_Bitacora.CN_Id_tipo_accion == tipo_accion_id)
            
            query = query.order_by(desc(T_Bitacora.CF_Fecha_hora)).limit(1)
            
            result = db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error obteniendo última acción de usuario {usuario_id}: {e}")
            raise


# Instancia singleton del repository
bitacora_repository = BitacoraRepository()
