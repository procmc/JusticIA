"""
Servicio especializado de auditoría para el módulo RAG (Consultas Inteligentes).
Registra consultas generales y consultas por expediente específico.
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.db.models.bitacora import T_Bitacora
from app.constants.tipos_accion import TiposAccion
from .bitacora_service import BitacoraService
from app.repositories.expediente_repository import ExpedienteRepository

logger = logging.getLogger(__name__)


class RAGAuditService:
    """Servicio especializado para auditoría esencial del módulo RAG"""
    
    def __init__(self):
        self.bitacora_service = BitacoraService()
        self.expediente_repo = ExpedienteRepository()
    
    async def registrar_consulta_rag(
        self,
        db: Session,
        usuario_id: str,
        pregunta: str,
        session_id: str,
        tipo_consulta: str,  # "general" o "expediente"
        expediente_numero: Optional[str] = None,
        tiempo_procesamiento: Optional[float] = None
    ) -> Optional[T_Bitacora]:
        """
        Registra una consulta RAG (general o por expediente específico).
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            pregunta: Pregunta/consulta completa del usuario
            session_id: ID de la sesión conversacional
            tipo_consulta: "general" o "expediente"
            expediente_numero: Número del expediente (solo si tipo_consulta="expediente")
            tiempo_procesamiento: Tiempo en segundos que tomó procesar
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            # Usar siempre CONSULTA_RAG (12) para ambos tipos
            tipo_accion_id = TiposAccion.CONSULTA_RAG
            
            # Determinar expediente_id y texto según el tipo de consulta
            if tipo_consulta == "expediente" and expediente_numero:
                # Para consultas de expediente específico:
                # 1. Asociar con el expediente real
                # 2. Incluir número de expediente en el texto
                texto = f"Consulta RAG expediente {expediente_numero}: {pregunta}"
                
                # Buscar el expediente en la base de datos
                expediente = self.expediente_repo.obtener_por_numero(db, expediente_numero)
                expediente_id = expediente.CN_Id_expediente if expediente else None
                
                if not expediente:
                    logger.warning(f"Expediente {expediente_numero} no encontrado en BD para auditoría")
                
            else:
                # Para consultas generales:
                # 1. No asociar expediente (NULL)
                # 2. Marcar como consulta general en el texto
                texto = f"Consulta RAG general: {pregunta}"
                expediente_id = None
            
            # Información adicional estructurada
            info_adicional = {
                "tipo_consulta": tipo_consulta,
                "session_id": session_id,
                "pregunta_completa": pregunta,
                "modulo": "rag_chat",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Agregar campos opcionales solo si existen
            if expediente_numero:
                info_adicional["expediente_numero"] = expediente_numero
            
            if tiempo_procesamiento is not None:
                info_adicional["tiempo_procesamiento_segundos"] = tiempo_procesamiento
            
            # Registrar usando el servicio base
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=tipo_accion_id,  # Siempre CONSULTA_RAG (12)
                texto=texto,
                expediente_id=expediente_id,  # NULL para general, ID_REAL para expediente
                info_adicional=info_adicional
            )
            
        except Exception as e:
            logger.warning(f"Error registrando consulta RAG: {e}")
            return None


# Instancia singleton del servicio especializado
rag_audit_service = RAGAuditService()