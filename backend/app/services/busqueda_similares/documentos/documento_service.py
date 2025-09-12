"""
Servicio de manejo de documentos y metadatos.

Este módulo maneja la recuperación y organización de documentos y expedientes
desde la base de datos SQL Server usando repositories.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from contextlib import contextmanager
from app.db.database import SessionLocal
from app.repositories.expediente_repository import ExpedienteRepository
from app.repositories.documento_repository import DocumentoRepository

logger = logging.getLogger(__name__)


class DocumentoService:
    """Servicio para manejo de documentos y expedientes usando repositories."""
    
    def __init__(self):
        self.expediente_repo = ExpedienteRepository()
        self.documento_repo = DocumentoRepository()
    
    @staticmethod
    @contextmanager
    def get_db_session():
        """Context manager para obtener una sesión de base de datos."""
        if not SessionLocal:
            raise Exception("Base de datos no disponible. Revisa la configuración.")
        
        db = SessionLocal()
        try:
            yield db
        except Exception as e:
            logger.error(f"Error en sesión de base de datos: {e}")
            db.rollback()
            raise e
        finally:
            db.close()
    
    async def obtener_expediente_completo(
        self,
        expedient_id: str,
        incluir_documentos: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene información completa de un expediente usando repository.
        
        Args:
            expedient_id: ID del expediente
            incluir_documentos: Si incluir documentos en el resultado
            
        Returns:
            Diccionario con datos completos del expediente o None si no existe
        """
        try:
            with self.get_db_session() as db:
                # Usar el repository para obtener el expediente
                expediente = self.expediente_repo.obtener_por_numero(db, expedient_id)
                
                if not expediente:
                    logger.warning(f"Expediente {expedient_id} no encontrado")
                    return None
                
                # Convertir modelo a diccionario
                expedient_data = {
                    "expedient_id": expediente.CT_Num_expediente,
                    "expedient_name": expediente.CT_Num_expediente,  # Usar número como nombre por defecto
                    "created_date": expediente.CF_Fecha_creacion.isoformat() if expediente.CF_Fecha_creacion else None,
                    "status": "activo",  # Valor por defecto
                    "created_by": None,
                    "updated_date": expediente.CF_Fecha_modificacion.isoformat() if expediente.CF_Fecha_modificacion else None,
                    "updated_by": None,
                    "documents": []
                }
                
                # Obtener documentos si se solicita
                if incluir_documentos:
                    expedient_data["documents"] = await self._obtener_documentos_expediente(
                        db, expediente.CN_Id_expediente
                    )
                
                logger.info(f"Expediente {expedient_id} obtenido exitosamente")
                return expedient_data
                
        except Exception as e:
            logger.error(f"Error obteniendo expediente {expedient_id}: {e}")
            raise
    
    async def _obtener_documentos_expediente(
        self,
        db: Session,
        expediente_id: int
    ) -> List[Dict[str, Any]]:
        """
        Obtiene documentos de un expediente usando repository.
        
        Args:
            db: Sesión de base de datos
            expediente_id: ID numérico del expediente
            
        Returns:
            Lista de documentos con sus metadatos
        """
        try:
            # Primero obtener el expediente por ID
            from sqlalchemy import select
            from app.db.models.expediente import T_Expediente
            
            stmt = select(T_Expediente).where(T_Expediente.CN_Id_expediente == expediente_id)
            result = db.execute(stmt)
            expediente = result.scalar_one_or_none()
            
            if not expediente:
                logger.warning(f"Expediente con ID {expediente_id} no encontrado")
                return []
                
            # Usar el repository para obtener documentos
            documentos = self.documento_repo.listar_por_expediente(db, expediente)
            
            documents = []
            for doc in documentos:
                document = {
                    "id": doc.CN_Id_documento,
                    "document_name": doc.CT_Nombre_archivo,
                    "file_path": doc.CT_Ruta_archivo,
                    "upload_date": doc.CF_Fecha_creacion.isoformat() if doc.CF_Fecha_creacion else None,
                    "content_preview": getattr(doc, 'CT_Contenido_preview', None),  # Puede no existir
                    "file_size": getattr(doc, 'CN_Tamaño', None),  # Puede no existir
                    "file_type": doc.CT_Tipo_archivo,
                    "created_by": getattr(doc, 'CT_Creado_por', None),  # Puede no existir
                    "updated_date": doc.CF_Fecha_modificacion.isoformat() if doc.CF_Fecha_modificacion else None
                }
                documents.append(document)
            
            logger.debug(f"Obtenidos {len(documents)} documentos para expediente ID {expediente_id}")
            return documents
            
        except Exception as e:
            logger.error(f"Error obteniendo documentos del expediente ID {expediente_id}: {e}")
            return []
    
    async def obtener_expedientes_batch(
        self,
        expedient_ids: List[str],
        incluir_documentos: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Obtiene múltiples expedientes en una sola operación.
        
        Args:
            expedient_ids: Lista de IDs de expedientes
            incluir_documentos: Si incluir documentos en los resultados
            
        Returns:
            Lista de expedientes con sus datos
        """
        try:
            if not expedient_ids:
                return []
            
            expedientes = []
            for expedient_id in expedient_ids:
                expediente = await self.obtener_expediente_completo(
                    expedient_id, incluir_documentos
                )
                if expediente:
                    expedientes.append(expediente)
            
            logger.info(f"Obtenidos {len(expedientes)} expedientes en batch")
            return expedientes
            
        except Exception as e:
            logger.error(f"Error obteniendo expedientes en batch: {e}")
            raise
    
    async def verificar_existencia_expediente(self, expedient_id: str) -> bool:
        """
        Verifica si un expediente existe en la base de datos usando repository.
        
        Args:
            expedient_id: ID del expediente a verificar
            
        Returns:
            True si existe, False en caso contrario
        """
        try:
            with self.get_db_session() as db:
                # Usar el método del repository
                exists = self.expediente_repo.validar_expediente_existe(db, expedient_id)
                
                logger.debug(f"Expediente {expedient_id} existe: {exists}")
                return exists
                
        except Exception as e:
            logger.error(f"Error verificando existencia del expediente {expedient_id}: {e}")
            return False
    
    async def obtener_metadatos_documento(
        self,
        document_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene metadatos de un documento específico usando repository.
        
        Args:
            document_id: ID del documento
            
        Returns:
            Diccionario con metadatos del documento o None si no existe
        """
        try:
            with self.get_db_session() as db:
                # Usar el repository para obtener el documento
                documento = self.documento_repo.obtener_por_id(db, document_id)
                
                if not documento:
                    return None
                
                # Obtener información del expediente si está disponible
                expedient_name = None
                if documento.expediente:
                    expedient_name = documento.expediente.CT_Num_expediente
                
                return {
                    "id": documento.CN_Id_documento,
                    "document_name": documento.CT_Nombre_archivo,
                    "expedient_id": documento.CN_Id_expediente,
                    "expedient_name": expedient_name,
                    "file_path": documento.CT_Ruta_archivo,
                    "upload_date": documento.CF_Fecha_creacion.isoformat() if documento.CF_Fecha_creacion else None,
                    "content_preview": getattr(documento, 'CT_Contenido_preview', None),
                    "file_size": getattr(documento, 'CN_Tamaño', None),
                    "file_type": documento.CT_Tipo_archivo
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo metadatos del documento {document_id}: {e}")
            return None
