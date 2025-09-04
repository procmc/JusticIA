from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models.expediente import T_Expediente
from datetime import datetime


class ExpedienteRepository:
    """Repositorio para operaciones CRUD de expedientes"""
    
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
