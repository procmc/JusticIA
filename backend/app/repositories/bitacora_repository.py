"""
Repository para operaciones de base de datos de bitácora.
Maneja todas las consultas y operaciones CRUD sobre T_Bitacora.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc, func, Date, cast
import logging

from app.db.models.bitacora import T_Bitacora
from app.db.models.usuario import T_Usuario
from app.db.models.expediente import T_Expediente

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
        expediente_numero: Optional[str] = None,
        limite: int = 10,
        offset: int = 0
    ) -> tuple[List[T_Bitacora], int]:
        """
        Obtiene registros de bitácora con múltiples filtros y paginación.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango (opcional)
            fecha_fin: Fecha de fin del rango (opcional)
            tipo_accion_id: Filtrar por tipo de acción (opcional)
            usuario_id: Filtrar por usuario (opcional)
            expediente_numero: Filtrar por número de expediente (opcional)
            limite: Número máximo de registros por página (default: 10)
            offset: Número de registros a saltar para paginación (default: 0)
            
        Returns:
            tuple[List[T_Bitacora], int]: (Lista de registros, Total de registros que coinciden con filtros)
        """
        try:
            from sqlalchemy.orm import joinedload
            from app.db.models.usuario import T_Usuario
            from app.db.models.expediente import T_Expediente
            from app.db.models.tipo_accion import T_Tipo_accion
            
            # Si se busca por número de expediente, primero obtener el ID
            expediente_id = None
            if expediente_numero:
                from app.repositories.expediente_repository import ExpedienteRepository
                exp_repo = ExpedienteRepository()
                expediente_obj = exp_repo.obtener_por_numero(db, expediente_numero)
                if expediente_obj:
                    expediente_id = expediente_obj.CN_Id_expediente
                else:
                    # Si no se encuentra el expediente, retornar vacío
                    return []
            
            # Query con eager loading de relaciones
            query = select(T_Bitacora).options(
                joinedload(T_Bitacora.usuario).joinedload(T_Usuario.rol),
                joinedload(T_Bitacora.expediente),
                joinedload(T_Bitacora.tipo_accion)
            )
            
            # Construir condiciones de filtro
            conditions = []
            if fecha_inicio:
                conditions.append(T_Bitacora.CF_Fecha_hora >= fecha_inicio)
            if fecha_fin:
                conditions.append(T_Bitacora.CF_Fecha_hora <= fecha_fin)
            if tipo_accion_id:
                conditions.append(T_Bitacora.CN_Id_tipo_accion == tipo_accion_id)
            if usuario_id:
                # Buscar por ID exacto (cédula), correo o nombre del usuario
                # Para nombres compuestos, buscar cada palabra en cualquier campo de nombre
                terminos_busqueda = usuario_id.strip().split()
                
                condiciones_usuario = [
                    T_Usuario.CN_Id_usuario == usuario_id,  # Búsqueda exacta por cédula
                    T_Usuario.CT_Correo.ilike(f"%{usuario_id}%")  # Búsqueda por correo
                ]
                
                # Si hay múltiples términos (nombre compuesto), buscar que todos estén presentes
                if len(terminos_busqueda) > 1:
                    # Concatenar nombre completo y buscar todos los términos
                    nombre_completo = func.concat(
                        func.coalesce(T_Usuario.CT_Nombre, ''), ' ',
                        func.coalesce(T_Usuario.CT_Apellido_uno, ''), ' ',
                        func.coalesce(T_Usuario.CT_Apellido_dos, '')
                    )
                    
                    # Verificar que TODOS los términos estén presentes en el nombre completo
                    for termino in terminos_busqueda:
                        condiciones_usuario.append(nombre_completo.ilike(f"%{termino}%"))
                        
                else:
                    # Búsqueda simple: en cualquier campo de nombre
                    condiciones_usuario.extend([
                        T_Usuario.CT_Nombre.ilike(f"%{usuario_id}%"),
                        T_Usuario.CT_Apellido_uno.ilike(f"%{usuario_id}%"),
                        T_Usuario.CT_Apellido_dos.ilike(f"%{usuario_id}%")
                    ])
                
                usuario_subquery = select(T_Usuario.CN_Id_usuario).where(
                    or_(*condiciones_usuario)
                )
                conditions.append(T_Bitacora.CN_Id_usuario.in_(usuario_subquery))
            if expediente_id:
                conditions.append(T_Bitacora.CN_Id_expediente == expediente_id)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Contar total de registros que coinciden con los filtros (antes de limit/offset)
            count_query = select(func.count()).select_from(T_Bitacora)
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_count = db.execute(count_query).scalar() or 0
            
            # Aplicar ordenamiento, paginación
            query = query.order_by(desc(T_Bitacora.CF_Fecha_hora)).limit(limite).offset(offset)
            
            # IMPORTANTE: usar unique() para manejar los joins correctamente
            result = db.execute(query)
            registros = result.unique().scalars().all()
            
            return registros, total_count
            
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
    
    
    def contar_total(
        self,
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> int:
        """
        Cuenta el total de registros de bitácora.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango (opcional)
            fecha_fin: Fecha de fin del rango (opcional)
            
        Returns:
            int: Número total de registros
        """
        try:
            query = select(func.count(T_Bitacora.CN_Id_bitacora))
            
            conditions = []
            if fecha_inicio:
                conditions.append(T_Bitacora.CF_Fecha_hora >= fecha_inicio)
            if fecha_fin:
                conditions.append(T_Bitacora.CF_Fecha_hora <= fecha_fin)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            result = db.execute(query)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error contando total de registros: {e}")
            return 0
    
    
    def contar_usuarios_unicos(
        self,
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> int:
        """
        Cuenta el número de usuarios únicos que tienen actividad.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango (opcional)
            fecha_fin: Fecha de fin del rango (opcional)
            
        Returns:
            int: Número de usuarios únicos
        """
        try:
            query = select(func.count(func.distinct(T_Bitacora.CN_Id_usuario)))
            
            conditions = []
            if fecha_inicio:
                conditions.append(T_Bitacora.CF_Fecha_hora >= fecha_inicio)
            if fecha_fin:
                conditions.append(T_Bitacora.CF_Fecha_hora <= fecha_fin)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            result = db.execute(query)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error contando usuarios únicos: {e}")
            return 0
    
    
    def contar_expedientes_unicos(
        self,
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> int:
        """
        Cuenta el número de expedientes únicos con actividad.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango (opcional)
            fecha_fin: Fecha de fin del rango (opcional)
            
        Returns:
            int: Número de expedientes únicos
        """
        try:
            query = select(func.count(func.distinct(T_Bitacora.CN_Id_expediente))).where(
                T_Bitacora.CN_Id_expediente.isnot(None)
            )
            
            conditions = []
            if fecha_inicio:
                conditions.append(T_Bitacora.CF_Fecha_hora >= fecha_inicio)
            if fecha_fin:
                conditions.append(T_Bitacora.CF_Fecha_hora <= fecha_fin)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            result = db.execute(query)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error contando expedientes únicos: {e}")
            return 0
    
    
    def contar_por_periodo(
        self,
        db: Session,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> int:
        """
        Cuenta registros en un período específico.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del período
            fecha_fin: Fecha de fin del período
            
        Returns:
            int: Número de registros en el período
        """
        try:
            query = select(func.count(T_Bitacora.CN_Id_bitacora)).where(
                and_(
                    T_Bitacora.CF_Fecha_hora >= fecha_inicio,
                    T_Bitacora.CF_Fecha_hora <= fecha_fin
                )
            )
            
            result = db.execute(query)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error contando registros por período: {e}")
            return 0
    
    
    def obtener_acciones_por_tipo(
        self,
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> List[dict]:
        """
        Obtiene el conteo de acciones agrupadas por tipo.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango (opcional)
            fecha_fin: Fecha de fin del rango (opcional)
            
        Returns:
            List[dict]: Lista de {'tipo_id': int, 'cantidad': int}
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
            
            return [
                {"tipo_id": row[0], "cantidad": row[1]}
                for row in result.all()
            ]
            
        except Exception as e:
            logger.error(f"Error obteniendo acciones por tipo: {e}")
            return []
    
    
    def obtener_usuarios_mas_activos(
        self,
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        limite: int = 10
    ) -> List[dict]:
        """
        Obtiene los usuarios más activos con su conteo de acciones.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango (opcional)
            fecha_fin: Fecha de fin del rango (opcional)
            limite: Número máximo de usuarios a retornar
            
        Returns:
            List[dict]: Lista de {'nombre': str, 'cantidad': int}
        """
        try:
            # Concatenar nombre completo
            nombre_completo = func.concat(
                T_Usuario.CT_Nombre,
                ' ',
                func.coalesce(T_Usuario.CT_Apellido_uno, ''),
                ' ',
                func.coalesce(T_Usuario.CT_Apellido_dos, '')
            ).label('nombre')
            
            query = select(
                nombre_completo,
                func.count(T_Bitacora.CN_Id_bitacora).label('cantidad')
            ).select_from(T_Bitacora).join(
                T_Usuario,
                T_Bitacora.CN_Id_usuario == T_Usuario.CN_Id_usuario
            )
            
            conditions = []
            if fecha_inicio:
                conditions.append(T_Bitacora.CF_Fecha_hora >= fecha_inicio)
            if fecha_fin:
                conditions.append(T_Bitacora.CF_Fecha_hora <= fecha_fin)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = (
                query.group_by(T_Usuario.CN_Id_usuario, T_Usuario.CT_Nombre, T_Usuario.CT_Apellido_uno, T_Usuario.CT_Apellido_dos)
                .order_by(desc('cantidad'))
                .limit(limite)
            )
            
            result = db.execute(query)
            
            return [
                {"nombre": row.nombre.strip(), "cantidad": row.cantidad}
                for row in result.all()
            ]
            
        except Exception as e:
            logger.error(f"Error obteniendo usuarios más activos: {e}")
            return []
    
    
    def obtener_expedientes_mas_consultados(
        self,
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        limite: int = 10
    ) -> List[dict]:
        """
        Obtiene los expedientes más consultados con su conteo.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango (opcional)
            fecha_fin: Fecha de fin del rango (opcional)
            limite: Número máximo de expedientes a retornar
            
        Returns:
            List[dict]: Lista de {'numero': str, 'cantidad': int}
        """
        try:
            query = select(
                T_Expediente.CT_Num_expediente.label('numero'),
                func.count(T_Bitacora.CN_Id_bitacora).label('cantidad')
            ).select_from(T_Bitacora).join(
                T_Expediente,
                T_Bitacora.CN_Id_expediente == T_Expediente.CN_Id_expediente
            ).where(
                T_Bitacora.CN_Id_expediente.isnot(None)
            )
            
            conditions = []
            if fecha_inicio:
                conditions.append(T_Bitacora.CF_Fecha_hora >= fecha_inicio)
            if fecha_fin:
                conditions.append(T_Bitacora.CF_Fecha_hora <= fecha_fin)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = (
                query.group_by(T_Expediente.CN_Id_expediente, T_Expediente.CT_Num_expediente)
                .order_by(desc('cantidad'))
                .limit(limite)
            )
            
            result = db.execute(query)
            
            return [
                {"numero": row.numero, "cantidad": row.cantidad}
                for row in result.all()
            ]
            
        except Exception as e:
            logger.error(f"Error obteniendo expedientes más consultados: {e}")
            return []
    
    
    def obtener_actividad_por_dia(
        self,
        db: Session,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> List[dict]:
        """
        Obtiene la cantidad de registros por día en un rango de fechas.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango
            fecha_fin: Fecha de fin del rango
            
        Returns:
            List[dict]: Lista de {'fecha': date, 'cantidad': int}
        """
        try:
            # Usar CAST para convertir datetime a date (compatible con SQL Server)
            fecha_columna = cast(T_Bitacora.CF_Fecha_hora, Date)
            
            query = select(
                fecha_columna.label('fecha'),
                func.count(T_Bitacora.CN_Id_bitacora).label('cantidad')
            ).where(
                and_(
                    T_Bitacora.CF_Fecha_hora >= fecha_inicio,
                    T_Bitacora.CF_Fecha_hora <= fecha_fin
                )
            ).group_by(
                fecha_columna
            ).order_by(
                fecha_columna
            )
            
            result = db.execute(query)
            
            return [
                {"fecha": row.fecha, "cantidad": row.cantidad}
                for row in result.all()
            ]
            
        except Exception as e:
            logger.error(f"Error obteniendo actividad por día: {e}")
            return []


# Instancia singleton del repository
bitacora_repository = BitacoraRepository()
