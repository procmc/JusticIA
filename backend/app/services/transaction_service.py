"""
Servicio simple de transacciones para JusticIA.
"""

from contextlib import asynccontextmanager
from sqlalchemy.orm import Session


class TransactionManager:
    """Manejo simple de transacciones de base de datos."""
    
    @asynccontextmanager
    async def atomic_transaction(self, db: Session):
        """
        Context manager simple para transacciones.
        
        Usage:
            async with TransactionManager().atomic_transaction(db):
                # hacer operaciones
                # si algo falla, rollback automático
        """
        try:
            yield
            db.commit()
        except Exception:
            db.rollback()
            raise
