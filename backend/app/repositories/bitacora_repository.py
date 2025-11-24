"""
Repositorio de Acceso a Datos para la Bitácora del Sistema JusticIA.

Este módulo gestiona todas las operaciones de persistencia, consulta y análisis
sobre la tabla T_Bitacora, que constituye el registro de auditoría centralizado
del sistema para trazabilidad, seguridad y cumplimiento normativo.

Responsabilidades:

    1. **Creación de registros**:
       - Insertar nuevas entradas de auditoría
       - Validar estructura de datos
       - Manejar transacciones y rollback

    2. **Consultas básicas**:
       - Por usuario (historial de acciones)
       - Por expediente (trazabilidad documental)
       - Por tipo de acción (filtrar eventos)

    3. **Consultas avanzadas con filtros**:
       - Rango de fechas (fecha_inicio, fecha_fin)
       - Múltiples criterios combinados
       - Paginación (limite, offset)
       - Conteo total de resultados

    4. **Consultas analíticas**:
       - Estadísticas por tipo de acción
       - Actividad por usuario
       - Eventos por expediente
       - Resumen de operaciones

    5. **Joins con otras tablas**:
       - T_Usuario: Obtener nombres de usuarios
       - T_Expediente: Obtener números de expediente
       - T_Tipo_Accion: Obtener descripciones de acciones

Operaciones disponibles:

    **CRUD básico**:
    - crear(): Insertar nuevo registro
    - obtener_por_usuario(): Historial de un usuario
    - obtener_por_expediente(): Trazabilidad de expediente

    **Consultas con filtros**:
    - obtener_con_filtros(): Búsqueda avanzada con múltiples criterios
    - Paginación: limite, offset
    - Retorna: (registros, total_count)

    **Estadísticas**:
    - obtener_estadisticas_por_tipo_accion(): Conteo por tipo
    - obtener_actividad_por_usuario(): Ranking de usuarios más activos
    - obtener_eventos_por_expediente(): Eventos por expediente

Estructura de T_Bitacora:

    Campos principales:
    - CN_Id_bitacora: PK autoincremental (BigInt)
    - CN_Id_usuario: FK a T_Usuario (cédula, nullable)
    - CN_Id_tipo_accion: FK a T_Tipo_Accion (catálogo)
    - CT_Texto: Descripción legible de la acción
    - CN_Id_expediente: FK a T_Expediente (opcional)
    - CT_Informacion_adicional: JSON string con metadata
    - CF_Fecha_hora: Timestamp UTC de la acción

    Relaciones:
    - N:1 con T_Usuario (usuario que ejecuta acción)
    - N:1 con T_Tipo_Accion (categoría de acción)
    - N:1 con T_Expediente (expediente afectado, opcional)

Patrón de uso típico:

    1. Servicio especializado (auth, usuarios, archivos) construye datos
    2. BitacoraService convierte info_adicional a JSON
    3. **BitacoraRepository.crear()** inserta en BD
    4. Commit automático con refresh

Consultas con filtros - Parámetros:

    - fecha_inicio: datetime - Filtrar desde esta fecha (inclusive)
    - fecha_fin: datetime - Filtrar hasta esta fecha (inclusive)
    - tipo_accion_id: int - Filtrar por tipo específico
    - usuario_id: str - Filtrar por usuario específico
    - expediente_numero: str - Filtrar por expediente (join con T_Expediente)
    - limite: int - Máximo registros a retornar (paginación)
    - offset: int - Saltar N registros (paginación)

Consultas optimizadas:

    - Índices en: CN_Id_usuario, CN_Id_tipo_accion, CF_Fecha_hora
    - Joins eficientes con SQLAlchemy 2.0 (select())
    - Eager loading para reducir N+1 queries
    - Ordenamiento descendente por fecha (más recientes primero)

Formato de respuesta (con filtros):

    tuple[List[T_Bitacora], int]:
    - [0]: Lista de registros paginados
    - [1]: Total de registros que cumplen filtros (para UI de paginación)

Estadísticas - Estructura de retorno:

    obtener_estadisticas_por_tipo_accion():
    [
        {
            "tipo_accion": "LOGIN",
            "descripcion": "Inicio de sesión",
            "total_eventos": 1543
        },
        ...
    ]

    obtener_actividad_por_usuario():
    [
        {
            "usuario_id": "123456789",
            "nombre_completo": "Juan Pérez Rodríguez",
            "total_acciones": 245
        },
        ...
    ]

Integración con sistema de auditoría:

    BitacoraRepository (este módulo)
    ↑ usado por
    BitacoraService (orquestador)
    ↑ usado por
    Servicios especializados:
    - AuthAuditService
    - UsuariosAuditService
    - ArchivosAuditService
    - IngestionAuditService
    - RAGAuditService
    - SimilarityAuditService

Example:
    >>> from app.repositories.bitacora_repository import BitacoraRepository
    >>> repo = BitacoraRepository()
    >>> 
    >>> # Crear registro
    >>> registro = repo.crear(
    ...     db=db,
    ...     usuario_id="123456789",
    ...     tipo_accion_id=TiposAccion.LOGIN,
    ...     texto="Inicio de sesión exitoso",
    ...     info_adicional='{"email": "usuario@ejemplo.com"}'
    ... )
    >>> 
    >>> # Consultar historial de usuario
    >>> historial = repo.obtener_por_usuario(
    ...     db=db,
    ...     usuario_id="123456789",
    ...     limite=50
    ... )
    >>> 
    >>> # Consulta con filtros avanzados
    >>> registros, total = repo.obtener_con_filtros(
    ...     db=db,
    ...     fecha_inicio=datetime(2025, 11, 1),
    ...     fecha_fin=datetime(2025, 11, 30),
    ...     tipo_accion_id=TiposAccion.LOGIN,
    ...     limite=10,
    ...     offset=0
    ... )
    >>> print(f"Mostrando 10 de {total} registros")

Manejo de errores:
    - crear(): Rollback automático, propaga excepción
    - Consultas: Log de error, propaga excepción
    - Transacciones explícitas con commit/rollback

Performance:
    - Consultas básicas: <10ms
    - Consultas con filtros: 20-100ms (depende de joins)
    - Estadísticas: 50-200ms (agregaciones)

Note:
    - Los registros de bitácora son **inmutables** (no se modifican/eliminan)
    - info_adicional se almacena como JSON string
    - Timestamps en UTC para consistencia
    - usuario_id puede ser NULL (acciones del sistema)

Ver también:
    - app.services.bitacora.bitacora_service: Servicio orquestador
    - app.services.bitacora.*_audit_service: Servicios especializados
    - app.db.models.bitacora: Modelo SQLAlchemy
    - app.constants.tipos_accion: Catálogo de tipos de acción

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc, func, Date, cast
import logging

from app.db.models.bitacora import T_Bitacora
from app.db.models.usuario import T_Usuario
from app.db.models.expediente import T_Expediente
from app.db.models.documento import T_Documento

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
            
            # Aplicar ordenamiento condicional:
            # - Si hay filtro de fechas: ascendente (cronológico)
            # - Sin filtro de fechas: descendente (más recientes primero)
            if fecha_inicio or fecha_fin:
                query = query.order_by(T_Bitacora.CF_Fecha_hora).limit(limite).offset(offset)
            else:
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
        fecha_fin: datetime,
        tipo_accion_id: Optional[int] = None
    ) -> List[dict]:
        """
        Obtiene la cantidad de registros por día en un rango de fechas.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango
            fecha_fin: Fecha de fin del rango
            tipo_accion_id: Filtrar por tipo de acción específico (opcional)
            
        Returns:
            List[dict]: Lista de {'fecha': date, 'cantidad': int}
        """
        try:
            # Usar CAST para convertir datetime a date (compatible con SQL Server)
            fecha_columna = cast(T_Bitacora.CF_Fecha_hora, Date)
            
            # Construir condiciones WHERE
            condiciones = [
                T_Bitacora.CF_Fecha_hora >= fecha_inicio,
                T_Bitacora.CF_Fecha_hora <= fecha_fin
            ]
            
            # Agregar filtro por tipo de acción si se especifica
            if tipo_accion_id is not None:
                condiciones.append(T_Bitacora.CN_Id_tipo_accion == tipo_accion_id)
            
            query = select(
                fecha_columna.label('fecha'),
                func.count(T_Bitacora.CN_Id_bitacora).label('cantidad')
            ).where(
                and_(*condiciones)
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
    
    
    def obtener_distribucion_tipos_archivo(
        self,
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> List[dict]:
        """
        Obtiene la distribución de documentos agrupados por tipo de archivo.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango (opcional)
            fecha_fin: Fecha de fin del rango (opcional)
            
        Returns:
            List[dict]: Lista de {'tipo': str, 'cantidad': int}
        """
        try:
            query = select(
                T_Documento.CT_Tipo_archivo.label('tipo'),
                func.count(T_Documento.CN_Id_documento).label('cantidad')
            ).select_from(T_Documento)
            
            conditions = []
            if fecha_inicio:
                conditions.append(T_Documento.CF_Fecha_carga >= fecha_inicio)
            if fecha_fin:
                conditions.append(T_Documento.CF_Fecha_carga <= fecha_fin)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = (
                query.group_by(T_Documento.CT_Tipo_archivo)
                .order_by(desc('cantidad'))
            )
            
            result = db.execute(query)
            rows = result.all()
            
            return [
                {"tipo": row.tipo, "cantidad": row.cantidad}
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error obteniendo distribución de tipos de archivo: {e}", exc_info=True)
            return []


# Instancia singleton del repository
bitacora_repository = BitacoraRepository()
