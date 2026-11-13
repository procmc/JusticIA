"""Repositorio de acceso a datos de los resultados de estudio de un notebook (spec 010).

Operaciones: crear, listar los visibles de un notebook (más reciente primero), obtener uno visible y marcarlo como quitado
(baja lógica: la fila se conserva, RN-01.120).

Ver también:
    - app.db.models.resultado_estudio.T_Resultado_Estudio: Modelo SQLAlchemy
    - app.services.estudio_service.EstudioService: Lógica de negocio
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.resultado_estudio import T_Resultado_Estudio


class ResultadoEstudioRepository:
    """Repositorio de acceso a datos para T_Resultado_Estudio."""

    def crear(self, db: Session, notebook_id: int, usuario_id: str, tipo: str, titulo: str, contenido: str,
              fuentes: str) -> T_Resultado_Estudio:
        """Guarda un resultado nuevo; si falla, deshace y relanza."""
        try:
            resultado = T_Resultado_Estudio(
                CN_Id_notebook=notebook_id, CN_Id_usuario=usuario_id, CT_Tipo=tipo, CT_Titulo=titulo,
                CT_Contenido=contenido, CT_Fuentes=fuentes, CF_Fecha_creacion=datetime.utcnow(),
            )
            db.add(resultado)
            db.commit()
            db.refresh(resultado)
            return resultado
        except Exception:
            db.rollback()
            raise

    def listar_visibles(self, db: Session, notebook_id: int) -> List[T_Resultado_Estudio]:
        """Los resultados no quitados de un notebook, del más reciente al más antiguo."""
        consulta = (
            select(T_Resultado_Estudio)
            .where(T_Resultado_Estudio.CN_Id_notebook == notebook_id, T_Resultado_Estudio.CF_Fecha_eliminacion.is_(None))
            .order_by(T_Resultado_Estudio.CF_Fecha_creacion.desc(), T_Resultado_Estudio.CN_Id_resultado.desc())
        )
        return list(db.execute(consulta).scalars().all())

    def obtener_visible(self, db: Session, notebook_id: int, resultado_id: int) -> Optional[T_Resultado_Estudio]:
        """Un resultado no quitado de ese notebook, o None (inexistente, de otro notebook o ya quitado)."""
        consulta = select(T_Resultado_Estudio).where(
            T_Resultado_Estudio.CN_Id_resultado == resultado_id,
            T_Resultado_Estudio.CN_Id_notebook == notebook_id,
            T_Resultado_Estudio.CF_Fecha_eliminacion.is_(None),
        )
        return db.execute(consulta).scalar_one_or_none()

    def marcar_quitado(self, db: Session, resultado: T_Resultado_Estudio) -> T_Resultado_Estudio:
        """Baja lógica: solo anota la fecha; si falla, deshace y relanza."""
        try:
            resultado.CF_Fecha_eliminacion = datetime.utcnow()
            db.commit()
            return resultado
        except Exception:
            db.rollback()
            raise
