"""Repositorio de Acceso a Datos de Expedientes Judiciales.

Este módulo implementa el patrón Repository para abstraer el acceso a datos
de expedientes judiciales almacenados en SQL Server. Proporciona operaciones
CRUD y consultas especializadas para la tabla T_Expediente.

Patrón Repository:
    Separa la lógica de negocio de la lógica de acceso a datos,
    facilitando testing, mantenimiento y cambios de persistencia.

Operaciones principales:
    - obtener_por_numero: Buscar expediente por número único
    - crear: Crear nuevo expediente
    - buscar_o_crear: Obtener existente o crear nuevo (idempotente)
    - obtener_expedientes_similares: Búsqueda múltiple por IDs
    - validar_expediente_existe: Verificación ligera de existencia

Modelo de datos:
    T_Expediente:
        - CN_Id_expediente (int, PK): ID autoincremental
        - CT_Num_expediente (str, unique): Número de expediente (formato: XX-XXXXXX-XXXX-YY)
        - CF_Fecha_creacion (datetime): Fecha de creación del registro
        - documentos (relationship): Documentos asociados al expediente

Example:
    ```python
    from app.repositories.expediente_repository import ExpedienteRepository
    from app.db.database import get_db
    
    repo = ExpedienteRepository()
    db = next(get_db())
    
    # Buscar o crear expediente
    expediente = repo.buscar_o_crear(db, '00-000123-0456-PE')
    print(f"ID: {expediente.CN_Id_expediente}")
    
    # Validar existencia sin carga completa
    existe = repo.validar_expediente_existe(db, '00-000123-0456-PE')
    
    # Obtener múltiples expedientes para similitud
    expedientes = repo.obtener_expedientes_similares(db, [1, 2, 3], limit=10)
    ```

Note:
    Todos los métodos que modifican datos soportan auto_commit=False
    para transacciones más complejas manejadas por servicios.

See Also:
    - app.db.models.expediente.T_Expediente: Modelo SQLAlchemy
    - app.services.expediente_service.ExpedienteService: Lógica de negocio
    - app.repositories.documento_repository.DocumentoRepository: Documentos del expediente
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models.expediente import T_Expediente
from datetime import datetime


class ExpedienteRepository:
    """Repositorio de acceso a datos para expedientes judiciales.
    
    Implementa operaciones CRUD y consultas especializadas sobre la tabla
    T_Expediente en SQL Server, abstrayendo la complejidad de SQLAlchemy.
    
    Attributes:
        Ninguno. Todas las operaciones son stateless y reciben la sesión db como parámetro.
    """
    
    def obtener_por_numero(self, db: Session, numero_expediente: str) -> Optional[T_Expediente]:
        """
        Busca un expediente por su número.
        
        Args:
            db: Sesión de base de datos
            numero_expediente: Número del expediente
            
        Returns:
            Optional[T_Expediente]: Expediente encontrado o None
        """
        stmt = select(T_Expediente).where(T_Expediente.CT_Num_expediente == numero_expediente)
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def crear(self, db: Session, numero_expediente: str, auto_commit: bool = True) -> T_Expediente:
        """
        Crea un nuevo expediente.
        
        Args:
            db: Sesión de base de datos
            numero_expediente: Número del expediente
            auto_commit: Si hacer commit automáticamente
            
        Returns:
            T_Expediente: Expediente creado
            
        Raises:
            Exception: Si hay error en la creación
        """
        try:
            expediente = T_Expediente(
                CT_Num_expediente=numero_expediente,
                CF_Fecha_creacion=datetime.utcnow()
            )
            db.add(expediente)
            
            if auto_commit:
                db.commit()
                db.refresh(expediente)
            else:
                db.flush()
            
            return expediente
            
        except Exception as e:
            if auto_commit:
                db.rollback()
            raise Exception(f"Error creando expediente: {str(e)}")
    
    def buscar_o_crear(self, db: Session, numero_expediente: str, auto_commit: bool = True) -> T_Expediente:
        """
        Busca un expediente existente o crea uno nuevo.
        
        Args:
            db: Sesión de base de datos
            numero_expediente: Número del expediente
            auto_commit: Si hacer commit automáticamente
            
        Returns:
            T_Expediente: Expediente encontrado o creado
        """
        # Buscar expediente existente
        expediente = self.obtener_por_numero(db, numero_expediente)
        
        if expediente:
            return expediente
        
        # Crear nuevo expediente
        return self.crear(db, numero_expediente, auto_commit)
    
    def obtener_expedientes_similares(
        self, 
        db: Session, 
        expediente_ids: List[int], 
        limit: int = 50
    ) -> List[T_Expediente]:
        """
        Obtiene múltiples expedientes por sus IDs para búsqueda de similares.
        
        Args:
            db: Sesión de base de datos
            expediente_ids: Lista de IDs de expedientes
            limit: Límite de expedientes a retornar
            
        Returns:
            List[T_Expediente]: Lista de expedientes encontrados
        """
        try:
            stmt = select(T_Expediente).where(
                T_Expediente.CN_Id_expediente.in_(expediente_ids)
            ).limit(limit)
            
            result = db.execute(stmt)
            return list(result.scalars().all())
            
        except Exception as e:
            raise Exception(f"Error obteniendo expedientes similares: {str(e)}")
    
    def obtener_expedientes_por_numeros(
        self, 
        db: Session, 
        numeros_expediente: List[str]
    ) -> List[T_Expediente]:
        """
        Obtiene múltiples expedientes por sus números.
        
        Args:
            db: Sesión de base de datos
            numeros_expediente: Lista de números de expedientes
            
        Returns:
            List[T_Expediente]: Lista de expedientes encontrados
        """
        try:
            stmt = select(T_Expediente).where(
                T_Expediente.CT_Num_expediente.in_(numeros_expediente)
            )
            
            result = db.execute(stmt)
            return list(result.scalars().all())
            
        except Exception as e:
            raise Exception(f"Error obteniendo expedientes por números: {str(e)}")
    
    def validar_expediente_existe(self, db: Session, numero_expediente: str) -> bool:
        """
        Valida si un expediente existe sin cargarlo completamente.
        
        Args:
            db: Sesión de base de datos
            numero_expediente: Número del expediente
            
        Returns:
            bool: True si existe, False si no
        """
        try:
            stmt = select(T_Expediente.CN_Id_expediente).where(
                T_Expediente.CT_Num_expediente == numero_expediente
            )
            result = db.execute(stmt)
            return result.scalar_one_or_none() is not None
            
        except Exception:
            return False
