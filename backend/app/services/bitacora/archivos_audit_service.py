"""
Servicio Especializado de Auditoría para el Módulo de Gestión de Archivos.

Este módulo registra todas las operaciones relacionadas con acceso, visualización
y descarga de archivos y documentos judiciales en el sistema JusticIA, proporcionando
trazabilidad completa para seguridad, cumplimiento normativo y control de acceso
a información sensible.

Eventos auditados:

    1. **Descarga de archivo** (TiposAccion.DESCARGAR_ARCHIVO):
       - Usuario descarga documento judicial
       - Registra: usuario_id, nombre_archivo, expediente, tamaño
       - Info adicional: ruta, tamaño_bytes, resultado (exitoso/error)
       - **Crítico**: Documentos legales sensibles

    2. **Listado de archivos** (TiposAccion.LISTAR_ARCHIVOS):
       - Usuario consulta lista de documentos de un expediente
       - Registra: usuario_id, expediente_numero, total_archivos
       - Info adicional: total_archivos, tipo_consulta

    3. **Visualización de archivo** (TiposAccion.VER_ARCHIVO):
       - Usuario visualiza documento sin descargar
       - Registra: usuario_id, nombre_archivo, expediente
       - Info adicional: ruta, tipo_visualizacion (preview/completo)

Arquitectura de auditoría:

    ArchivosAuditService (este módulo)
    └─> BitacoraService (orquestador general)
        └─> BitacoraRepository (acceso a datos)
            └─> T_Bitacora + T_Expediente (enlace)

Responsabilidades:

    **Este servicio**:
    - Registrar acceso a documentos judiciales
    - Capturar metadata de archivos (tamaño, ruta, tipo)
    - Enlazar descarga con expediente (si aplica)
    - Manejar descargas exitosas y fallidas
    - Resolver expediente_id desde número de expediente

    **BitacoraService**:
    - Convertir info_adicional a JSON
    - Validar tipos de acción

    **BitacoraRepository**:
    - Insertar registros con expediente_id

Estructura de info_adicional (JSON):

    Descarga exitosa:
    {
        "nombre_archivo": "demanda.pdf",
        "expediente_numero": "24-000123-0001-LA",
        "ruta": "uploads/expedientes/24-000123-0001-LA/demanda.pdf",
        "tamaño_bytes": 1245680,
        "resultado": "exitoso",
        "tipo_accion": "descarga",
        "timestamp": "2025-11-24T10:30:00Z"
    }

    Descarga fallida:
    {
        "nombre_archivo": "documento.pdf",
        "expediente_numero": "24-000123-0001-LA",
        "resultado": "error",
        "error": "Archivo no encontrado",
        "tipo_accion": "descarga",
        "timestamp": "2025-11-24T10:30:00Z"
    }

    Listado de archivos:
    {
        "expediente_numero": "24-000123-0001-LA",
        "total_archivos": 15,
        "tipo_consulta": "listar_documentos",
        "timestamp": "2025-11-24T10:30:00Z"
    }

Flujo de descarga con auditoría:

    1. Usuario solicita descarga de documento
    2. Sistema valida permisos
    3. Se obtiene archivo del storage
    4. **Antes de enviar**: Registrar en bitácora
    5. Enviar archivo al usuario
    6. Si falla: Registrar error en bitácora

Casos especiales manejados:

    1. **Descarga sin usuario autenticado**:
       - usuario_id = None (opcional)
       - Posible para procesos automáticos

    2. **Archivo sin expediente asociado**:
       - expediente_numero = None
       - expediente_id = None
       - Ejemplo: avatares de usuarios

    3. **Error en descarga**:
       - exito = False
       - error = mensaje descriptivo
       - Se registra igual para auditoría

    4. **Resolución de expediente_id**:
       - Busca en BD usando expediente_numero
       - Si no existe: expediente_id = None
       - No falla, solo registra sin enlace

Integración con otros módulos:
    - Routes (archivos.py): Endpoints de descarga/listado
    - FileManagementService: Gestión física de archivos
    - ExpedienteRepository: Resolución de expediente_id

Casos de uso de seguridad:

    1. **Auditoría de acceso a expedientes**:
       - Quién descargó qué documentos
       - Cuándo se accedió a información sensible

    2. **Detección de accesos sospechosos**:
       - Descargas masivas
       - Acceso a expedientes no autorizados

    3. **Cumplimiento GDPR**:
       - Registro de acceso a datos personales
       - Trazabilidad de información sensible

    4. **Control de distribución**:
       - Rastreo de documentos descargados
       - Evidencia de cadena de custodia

    5. **Monitoreo de errores**:
       - Archivos faltantes o corruptos
       - Problemas de permisos

Example:
    >>> from app.services.bitacora.archivos_audit_service import archivos_audit_service
    >>> 
    >>> # Descarga exitosa
    >>> await archivos_audit_service.registrar_descarga_archivo(
    ...     db=db,
    ...     usuario_id="123456789",
    ...     nombre_archivo="demanda.pdf",
    ...     expediente_numero="24-000123-0001-LA",
    ...     ruta_archivo="uploads/expedientes/.../demanda.pdf",
    ...     tamaño_bytes=1245680,
    ...     exito=True
    ... )
    >>> 
    >>> # Descarga fallida
    >>> await archivos_audit_service.registrar_descarga_archivo(
    ...     db=db,
    ...     usuario_id="123456789",
    ...     nombre_archivo="documento.pdf",
    ...     expediente_numero="24-000123-0001-LA",
    ...     exito=False,
    ...     error="Archivo no encontrado en el servidor"
    ... )
    >>> 
    >>> # Listado de archivos
    >>> await archivos_audit_service.registrar_listado_archivos(
    ...     db=db,
    ...     usuario_id="123456789",
    ...     expediente_numero="24-000123-0001-LA",
    ...     total_archivos=15
    ... )

Manejo de errores:
    - Captura excepciones y retorna None
    - Logging de errores (warning level)
    - No propaga errores (auditoría no rompe flujo)
    - Si falla resolución de expediente_id: Registra sin enlace

Note:
    - Descarga de documentos es operación crítica (sensible)
    - Los registros permiten rastrear acceso a información judicial
    - Timestamps en UTC para consistencia internacional
    - usuario_id puede ser None para procesos automáticos
    - Singleton: Use instancia global `archivos_audit_service`

Ver también:
    - app.services.bitacora.bitacora_service: Servicio base
    - app.services.documentos.file_management_service: Gestión de archivos
    - app.repositories.expediente_repository: Resolución de IDs
    - app.constants.tipos_accion: Catálogo de acciones

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0
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