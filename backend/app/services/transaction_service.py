"""
Servicio simple de transacciones para JusticIA.
"""

from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from typing import AsyncGenerator


class TransactionManager:
    """Manejo simple de transacciones de base de datos."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def __aenter__(self):
        """Entrada del context manager"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Salida del context manager con manejo de transacciones"""
        if exc_type is None:
            # Sin excepción - hacer commit
            self.db.commit()
        else:
            # Con excepción - hacer rollback
            self.db.rollback()
    
    async def execute(self, operation):
        """Ejecuta una operación en la transacción"""
        return await operation()


# Función helper sin decorador para casos simples
async def run_in_transaction(db: Session, operation):
    """
    Ejecuta una operación en una transacción.
    
    Usage:
        await run_in_transaction(db, async_operation)
    """
    try:
        result = await operation()
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
