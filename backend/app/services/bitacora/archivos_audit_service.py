"""
Servicio especializado de auditoría para el módulo de ARCHIVOS.
Registra acciones de descarga, listado y visualización de archivos.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.db.models.bitacora import T_Bitacora
from app.constants.tipos_accion import TiposAccion
from .bitacora_service import BitacoraService

logger = logging.getLogger(__name__)


class ArchivosAuditService:
    """Servicio especializado para auditoría del módulo de ARCHIVOS"""
    
    def __init__(self):
        self.bitacora_service = BitacoraService()
    
    async def registrar_descarga_archivo(
        self,
        db: Session,
        usuario_id: Optional[str],
        nombre_archivo: str,
        expediente_numero: Optional[str] = None,
        ruta_archivo: Optional[str] = None,
        tamaño_bytes: Optional[int] = None,
        exito: bool = True,
        error: Optional[str] = None
    ) -> Optional[T_Bitacora]:
        """
        Registra descarga de archivos en la bitácora.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario que descarga - Opcional para procesos automáticos
            nombre_archivo: Nombre del archivo descargado
            expediente_numero: Número del expediente (si aplica)
            ruta_archivo: Ruta del archivo descargado
            tamaño_bytes: Tamaño del archivo en bytes
            exito: Si la descarga fue exitosa o no
            error: Mensaje de error (si hubo error)
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            from app.repositories.expediente_repository import ExpedienteRepository
            
            # Si no se proporciona expediente_numero, intentar extraerlo de la ruta
            if not expediente_numero and ruta_archivo:
                expediente_numero = self._extraer_expediente_de_ruta(ruta_archivo)
            
            # Obtener ID del expediente si se proporciona número
            expediente_db_id = None
            if expediente_numero:
                exp_obj = ExpedienteRepository().obtener_por_numero(db, expediente_numero)
                if exp_obj:
                    expediente_db_id = exp_obj.CN_Id_expediente
            
            # Construir información adicional
            info = {
                "nombre_archivo": nombre_archivo,
                "expediente_numero": expediente_numero,
                "ruta_archivo": ruta_archivo,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Agregar información de tamaño si está disponible
            if tamaño_bytes is not None:
                info["tamaño_bytes"] = tamaño_bytes
                info["tamaño_legible"] = self._formatear_tamaño(tamaño_bytes)
            
            # Construir texto del registro
            if exito:
                if expediente_numero:
                    texto_registro = f"Descarga de archivo: {nombre_archivo} (expediente: {expediente_numero})"
                else:
                    texto_registro = f"Descarga de archivo: {nombre_archivo}"
            else:
                # Agregar información de error
                info["error"] = error
                info["tipo_error"] = "acceso" if "no encontrado" in error.lower() or "404" in error else "interno"
                texto_registro = f"Error descargando archivo: {nombre_archivo} - {error[:100]}"
            
            # Registrar en bitácora usando el servicio general
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=TiposAccion.DESCARGAR_ARCHIVO,
                texto=texto_registro,
                expediente_id=expediente_db_id,
                info_adicional=info
            )
            
        except Exception as e:
            logger.warning(f"Error registrando descarga de archivo en bitácora: {e}")
            return None
    
    async def registrar_listado_archivos(
        self,
        db: Session,
        usuario_id: Optional[str],
        expediente_numero: str,
        total_archivos: int,
        exito: bool = True,
        error: Optional[str] = None
    ) -> Optional[T_Bitacora]:
        """
        Registra listado de archivos de expediente en la bitácora.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario que lista
            expediente_numero: Número del expediente
            total_archivos: Total de archivos encontrados
            exito: Si el listado fue exitoso o no
            error: Mensaje de error (si hubo error)
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            from app.repositories.expediente_repository import ExpedienteRepository
            
            # Obtener ID del expediente
            expediente_db_id = None
            exp_obj = ExpedienteRepository().obtener_por_numero(db, expediente_numero)
            if exp_obj:
                expediente_db_id = exp_obj.CN_Id_expediente
            
            # Construir información adicional
            info = {
                "expediente_numero": expediente_numero,
                "total_archivos": total_archivos,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Construir texto del registro
            if exito:
                texto_registro = f"Listado de archivos del expediente: {expediente_numero} ({total_archivos} archivos)"
            else:
                # Agregar información de error
                info["error"] = error
                info["tipo_error"] = "acceso" if "no encontrado" in error.lower() else "interno"
                texto_registro = f"Error listando archivos del expediente: {expediente_numero} - {error[:100]}"
            
            # Registrar en bitácora usando el servicio general
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=TiposAccion.LISTAR_ARCHIVOS,
                texto=texto_registro,
                expediente_id=expediente_db_id,
                info_adicional=info
            )
            
        except Exception as e:
            logger.warning(f"Error registrando listado de archivos en bitácora: {e}")
            return None
    
    def _formatear_tamaño(self, bytes_size: int) -> str:
        """Convierte bytes a formato legible (KB, MB, GB)"""
        if bytes_size < 1024:
            return f"{bytes_size} B"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f} KB"
        elif bytes_size < 1024 * 1024 * 1024:
            return f"{bytes_size / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_size / (1024 * 1024 * 1024):.1f} GB"
    
    def _extraer_expediente_de_ruta(self, ruta_archivo: str) -> Optional[str]:
        """
        Extrae el número de expediente de la ruta del archivo.
        
        Las rutas típicamente tienen el formato:
        uploads/2024-641391-8667-LA/archivo.txt
        
        Args:
            ruta_archivo: Ruta completa del archivo
            
        Returns:
            str: Número de expediente o None si no se puede extraer
        """
        try:
            import re
            from pathlib import Path
            
            # Convertir a Path para facilitar manipulación
            path = Path(ruta_archivo)
            
            # Buscar en los componentes de la ruta un patrón de expediente
            for part in path.parts:
                # Patrón típico: YYYY-NNNNNN-NNNN-XX (ej: 2024-641391-8667-LA)
                if re.match(r'^\d{4}-\d{6}-\d{4}-[A-Z]{2}$', part):
                    return part
                
                # Otros patrones posibles (agregar según necesidad)
                # Patrón con menos dígitos: YY-NNNNNN-NNNN-XX
                if re.match(r'^\d{2}-\d{6}-\d{4}-[A-Z]{2}$', part):
                    return part
            
            # Si no encuentra patrón exacto, buscar en el nombre del archivo
            filename = path.name
            # Buscar patrón en el nombre: 2024_641391_8667_LA.txt
            match = re.search(r'(\d{4}[-_]\d{6}[-_]\d{4}[-_][A-Z]{2})', filename)
            if match:
                # Normalizar el formato (convertir _ a -)
                return match.group(1).replace('_', '-')
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extrayendo expediente de ruta {ruta_archivo}: {e}")
            return None


# Instancia singleton del servicio especializado
archivos_audit_service = ArchivosAuditService()