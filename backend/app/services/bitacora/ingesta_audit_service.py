"""
Servicio especializado de auditoría para el módulo de INGESTA.

Este módulo maneja el registro de auditoría para todas las operaciones del proceso
de ingesta y procesamiento de documentos. Registra eventos del ciclo de vida completo
de los documentos desde la carga hasta el almacenamiento vectorial.

Responsabilidades:
    * Registrar inicio, progreso y finalización de ingestas
    * Registrar almacenamiento exitoso en Milvus (vectorstore)
    * Registrar errores y cancelaciones de procesamiento
    * Asociar registros con usuario, expediente y documento

Fases del proceso de ingesta registradas:
    * "inicio": Documento recibido, iniciando procesamiento
    * "completado": Procesamiento exitoso, documento almacenado
    * "vectorstore_exitoso": Chunks almacenados en Milvus
    * "cancelado": Procesamiento cancelado por usuario
    * "error": Error durante procesamiento

Integración:
    * tasks.py: Tareas Celery que procesan documentos llaman a este servicio
    * archivos_service: Usa este servicio para registrar eventos de carga
    * Usa bitacora_service como base (patrón Facade)

Example:
    >>> from app.services.bitacora.ingesta_audit_service import ingesta_audit_service
    >>> 
    >>> # Registrar inicio de ingesta
    >>> await ingesta_audit_service.registrar_ingesta(
    ...     db=db,
    ...     usuario_id="112340567",
    ...     expediente_num="24-000123-0001-PE",
    ...     filename="demanda.pdf",
    ...     task_id="abc123-celery-task",
    ...     fase="inicio"
    ... )
    >>> 
    >>> # Registrar almacenamiento vectorial exitoso
    >>> await ingesta_audit_service.registrar_almacenamiento_vectorial(
    ...     db=db,
    ...     usuario_id="112340567",
    ...     expediente_num="24-000123-0001-PE",
    ...     filename="demanda.pdf",
    ...     documento_id=456,
    ...     num_chunks=15
    ... )

Note:
    * usuario_id es opcional (None para procesos automáticos)
    * Tipo de acción siempre es TiposAccion.CARGA_DOCUMENTOS (2)
    * info_adicional incluye task_id, fase, documento_id, num_chunks
    * Errores en registro se loggean como WARNING pero no fallan el proceso
    * Asocia automáticamente el expediente mediante su número

Ver también:
    * app.services.bitacora.bitacora_service: Servicio base
    * tasks.process_pdf_task: Tarea que usa este servicio
    * app.services.archivos_service: Orquestador de ingesta

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0 - Auditoría de ingesta y procesamiento
"""
from typing import Optional
from sqlalchemy.orm import Session
import logging

from app.db.models.bitacora import T_Bitacora
from app.constants.tipos_accion import TiposAccion
from .bitacora_service import BitacoraService

logger = logging.getLogger(__name__)


class IngestaAuditService:
    """Servicio especializado para auditoría del módulo de INGESTA"""
    
    def __init__(self):
        self.bitacora_service = BitacoraService()
    
    async def registrar_ingesta(
        self,
        db: Session,
        usuario_id: Optional[str],
        expediente_num: str,
        filename: str,
        task_id: str,
        fase: str,
        documento_id: Optional[str] = None,
        error_details: Optional[str] = None
    ) -> Optional[T_Bitacora]:
        """
        Registra eventos de ingesta de documentos en la bitácora.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario que inició la ingesta - Opcional para procesos automáticos
            expediente_num: Número del expediente
            filename: Nombre del archivo
            task_id: ID de la tarea Celery
            fase: Fase del proceso ("inicio", "completado", "cancelado", "error", etc.)
            documento_id: ID del documento procesado (opcional)
            error_details: Detalles del error si fase="error" (opcional)
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            from app.repositories.expediente_repository import ExpedienteRepository
            
            # Obtener ID del expediente
            expediente_id = None
            exp_obj = ExpedienteRepository().obtener_por_numero(db, expediente_num)
            if exp_obj:
                expediente_id = exp_obj.CN_Id_expediente
            
            # Construir info adicional
            info = {
                "task_id": task_id,
                "expediente": expediente_num,
                "archivo": filename,
                "fase": fase
            }
            if documento_id:
                info["documento_id"] = documento_id
            if error_details:
                info["error_details"] = error_details
            
            # Registrar en bitácora usando el servicio general
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=TiposAccion.CARGA_DOCUMENTOS,
                texto=f"{fase.capitalize()}: {filename}",
                expediente_id=expediente_id,
                info_adicional=info
            )
            
        except Exception as e:
            logger.warning(f"Error registrando ingesta en bitácora ({fase}): {e}")
            return None
    
    
    async def registrar_almacenamiento_vectorial(
        self,
        db: Session,
        usuario_id: Optional[str],
        expediente_num: str,
        filename: str,
        documento_id: int,
        num_chunks: int,
        fase: str = "vectorstore_exitoso"
    ) -> Optional[T_Bitacora]:
        """
        Registra el almacenamiento exitoso de documentos en Milvus (vectorstore).
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario que inició la ingesta - Opcional para procesos automáticos
            expediente_num: Número del expediente
            filename: Nombre del archivo
            documento_id: ID del documento en BD
            num_chunks: Cantidad de chunks/vectores almacenados
            fase: Fase del proceso (default: "vectorstore_exitoso")
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            from app.repositories.expediente_repository import ExpedienteRepository
            
            # Obtener ID del expediente
            expediente_id = None
            exp_obj = ExpedienteRepository().obtener_por_numero(db, expediente_num)
            if exp_obj:
                expediente_id = exp_obj.CN_Id_expediente
            
            # Construir info adicional
            info = {
                "expediente": expediente_num,
                "archivo": filename,
                "documento_id": documento_id,
                "num_chunks": num_chunks,
                "num_vectores": num_chunks,
                "collection": "documentos",
                "fase": fase
            }
            
            # Registrar en bitácora usando el servicio general
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=TiposAccion.CARGA_DOCUMENTOS,
                texto=f"Almacenado en vectorstore: {filename} ({num_chunks} chunks)",
                expediente_id=expediente_id,
                info_adicional=info
            )
            
        except Exception as e:
            logger.warning(f"Error registrando almacenamiento vectorial en bitácora: {e}")
            return None


# Instancia singleton del servicio especializado
ingesta_audit_service = IngestaAuditService()
