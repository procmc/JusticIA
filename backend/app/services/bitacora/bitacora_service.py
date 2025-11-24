"""
Servicio GENERAL de bitácora de acciones del sistema.

Este módulo proporciona el servicio base para el registro de todas las acciones
del sistema en la bitácora de auditoría. Es el servicio fundamental que utilizan
todos los servicios especializados (auth_audit_service, ingesta_audit_service,
rag_audit_service, etc.) para realizar el registro efectivo en la base de datos.

El servicio implementa el patrón Repository, delegando operaciones de base de datos
al BitacoraRepository y enfocándose en la lógica de negocio de auditoría.

Arquitectura:
    * BitacoraService: Servicio base con método genérico registrar()
    * Servicios especializados: Usan BitacoraService con formatos específicos
    * BitacoraRepository: Capa de acceso a datos
    * T_Bitacora: Modelo SQLAlchemy

Tipos de acciones soportadas (TiposAccion):
    * LOGIN (3), LOGOUT (4)
    * BUSQUEDA_SIMILARES (1)
    * CARGA_DOCUMENTOS (2)
    * CONSULTA_RAG (12)
    * GENERAR_RESUMEN (13)
    * Y más (ver constants/tipos_accion.py)

Example:
    >>> from app.services.bitacora.bitacora_service import bitacora_service
    >>> from app.constants.tipos_accion import TiposAccion
    >>> 
    >>> # Registro genérico desde servicio base
    >>> registro = await bitacora_service.registrar(
    ...     db=db,
    ...     usuario_id="112340567",
    ...     tipo_accion_id=TiposAccion.CONSULTA_RAG,
    ...     texto="Consulta RAG: ¿Qué es la prescripción?",
    ...     info_adicional={"session_id": "abc123"}
    ... )

Note:
    * Este servicio NO debe usarse directamente en la mayoría de casos
    * Preferir servicios especializados (auth_audit_service, rag_audit_service, etc.)
    * Los servicios especializados proveen métodos con nombres descriptivos y
      parámetros específicos al dominio
    * usuario_id es opcional para soportar procesos automáticos/sistema
    * info_adicional se serializa automáticamente a JSON

Ver también:
    * app.services.bitacora.auth_audit_service: Auditoría de autenticación
    * app.services.bitacora.rag_audit_service: Auditoría de consultas RAG
    * app.services.bitacora.bitacora_stats_service: Consultas y estadísticas
    * app.repositories.bitacora_repository: Capa de datos

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0 - Sistema unificado de auditoría
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
    """
    Servicio GENERAL para manejo de bitácora de acciones del sistema.
    
    Implementa el registro genérico de acciones de auditoría. Todos los servicios
    especializados utilizan este servicio como base.
    
    Attributes:
        repo (BitacoraRepository): Repositorio para operaciones de base de datos.
    """
    
    def __init__(self):
        """Inicializa el servicio con el repositorio de bitácora."""
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
        Serializa automáticamente info_adicional a JSON y maneja errores de registro.
        
        Args:
            db (Session): Sesión de base de datos SQLAlchemy.
            usuario_id (Optional[str]): ID del usuario (cédula). None para procesos del sistema.
            tipo_accion_id (int): ID del tipo de acción (usar constantes TiposAccion).
            texto (str): Descripción legible de la acción realizada.
            expediente_id (Optional[int]): ID del expediente relacionado si aplica.
            info_adicional (Optional[Dict[str, Any]]): Metadata adicional (se serializa a JSON).
            
        Returns:
            T_Bitacora: Registro de bitácora creado con CN_Id_bitacora y CF_Fecha_hora.
        
        Raises:
            Exception: Si falla la creación del registro en base de datos.
        
        Example:
            >>> registro = await bitacora_service.registrar(
            ...     db=db,
            ...     usuario_id="112340567",
            ...     tipo_accion_id=TiposAccion.CONSULTA_RAG,
            ...     texto="Consulta RAG: ¿Qué es la prescripción?",
            ...     expediente_id=123,
            ...     info_adicional={
            ...         "session_id": "abc123",
            ...         "tipo_consulta": "general"
            ...     }
            ... )
            >>> print(registro.CN_Id_bitacora)
            456
        
        Note:
            * Se registra automáticamente en logs con nivel INFO
            * Usuario None se muestra como "Sistema" en logs
            * info_adicional se serializa con ensure_ascii=False para UTF-8
            * No falla silenciosamente, propaga excepciones
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
