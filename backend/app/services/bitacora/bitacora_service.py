"""
Servicio GENERAL de bitácora de acciones del sistema.
Este es el servicio base que contiene la lógica genérica de registro.

Los servicios especializados (auth_audit_service, ingesta_audit_service, etc.)
utilizan este servicio para registrar con sus formatos específicos.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json
import logging

from app.db.models.bitacora import T_Bitacora
from app.repositories.bitacora_repository import BitacoraRepository
from app.constants.tipos_accion import TiposAccion, DESCRIPCIONES_TIPOS_ACCION

logger = logging.getLogger(__name__)


class BitacoraService:
    """Servicio GENERAL para manejo de bitácora de acciones del sistema"""
    
    def __init__(self):
        self.repo = BitacoraRepository()
    
    async def registrar(
        self,
        db: Session,
        usuario_id: Optional[str],
        tipo_accion_id: int,
        texto: str,
        expediente_id: Optional[int] = None,
        info_adicional: Optional[Dict[str, Any]] = None
    ) -> T_Bitacora:
        """
        Registra una acción GENÉRICA en la bitácora.
        
        Este es el método base que usan todos los servicios especializados.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario que realiza la acción (cédula) - Opcional para procesos automáticos
            tipo_accion_id: ID del tipo de acción (usar constantes de TiposAccion)
            texto: Descripción de la acción realizada
            expediente_id: ID del expediente relacionado (opcional)
            info_adicional: Información adicional en formato dict (se serializa a JSON)
            
        Returns:
            T_Bitacora: Registro de bitácora creado
        """
        try:
            # Serializar info_adicional a JSON si existe
            info_json = None
            if info_adicional:
                info_json = json.dumps(info_adicional, ensure_ascii=False)
            
            # Crear registro usando el repository
            bitacora = self.repo.crear(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=tipo_accion_id,
                texto=texto,
                expediente_id=expediente_id,
                info_adicional=info_json
            )
            
            logger.info(
                f"Bitácora registrada: Usuario={usuario_id or 'Sistema'}, "
                f"Tipo={DESCRIPCIONES_TIPOS_ACCION.get(tipo_accion_id, 'Desconocido')}, "
                f"Texto='{texto}'"
            )
            
            return bitacora
            
        except Exception as e:
            logger.error(f"Error registrando en bitácora: {e}")
            raise Exception(f"Error al registrar en bitácora: {str(e)}")


# Instancia singleton del servicio GENERAL
bitacora_service = BitacoraService()
