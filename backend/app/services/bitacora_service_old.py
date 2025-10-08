"""
Servicio para gestión de bitácora de acciones del sistema.
Registra todas las acciones de usuarios para auditoría y trazabilidad.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import json
import logging

from app.db.models.bitacora import T_Bitacora
from app.repositories.bitacora_repository import BitacoraRepository
from app.constants.tipos_accion import TiposAccion, DESCRIPCIONES_TIPOS_ACCION

logger = logging.getLogger(__name__)


class BitacoraService:
    """Servicio para manejo de bitácora de acciones del sistema"""
    
    def __init__(self):
        self.repository = BitacoraRepository()
    
    async def registrar(
        self,
        db: Session,
        usuario_id: str,
        tipo_accion_id: int,
        texto: str,
        expediente_id: Optional[int] = None,
        info_adicional: Optional[Dict[str, Any]] = None
    ) -> T_Bitacora:
        """
        Registra una acción en la bitácora.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario que realiza la acción (cédula)
            tipo_accion_id: ID del tipo de acción (usar constantes de TiposAccion)
            texto: Descripción de la acción realizada
            expediente_id: ID del expediente relacionado (opcional)
            info_adicional: Información adicional en formato dict (se serializa a JSON)
            
        Returns:
            T_Bitacora: Registro de bitácora creado
            
        Example:
            await bitacora_service.registrar(
                db=db,
                usuario_id="123456789",
                tipo_accion_id=TiposAccion.CARGA_DOCUMENTOS,
                texto="Ingesta exitosa de 5 archivos",
                expediente_id=123,
                info_adicional={"total_archivos": 5, "expediente": "19-000123-0456-CI"}
            )
        """
        try:
            # Serializar info_adicional a JSON si existe
            info_json = None
            if info_adicional:
                info_json = json.dumps(info_adicional, ensure_ascii=False)
            
            # Usar repository para crear el registro
            bitacora = self.repository.crear(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=tipo_accion_id,
                texto=texto,
                expediente_id=expediente_id,
                info_adicional=info_json
            )
            
            logger.info(
                f"Bitácora registrada: Usuario={usuario_id}, "
                f"Tipo={DESCRIPCIONES_TIPOS_ACCION.get(tipo_accion_id, 'Desconocido')}, "
                f"Texto='{texto}'"
            )
            
            return bitacora
            
        except Exception as e:
            logger.error(f"Error registrando en bitácora: {e}")
            raise Exception(f"Error al registrar en bitácora: {str(e)}")
    
    
    def obtener_bitacora_usuario(
        self,
        db: Session,
        usuario_id: str,
        limite: int = 100,
        tipo_accion_id: Optional[int] = None
    ) -> List[T_Bitacora]:
        """
        Obtiene el historial de bitácora de un usuario específico.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            limite: Número máximo de registros a retornar
            tipo_accion_id: Filtrar por tipo de acción específico (opcional)
            
        Returns:
            List[T_Bitacora]: Lista de registros de bitácora ordenados por fecha (más reciente primero)
        """
        try:
            return self.repository.obtener_por_usuario(
                db=db,
                usuario_id=usuario_id,
                limite=limite,
                tipo_accion_id=tipo_accion_id
            )
        except Exception as e:
            logger.error(f"Error obteniendo bitácora de usuario {usuario_id}: {e}")
            return []
    
    
    def obtener_bitacora_expediente(
        self,
        db: Session,
        expediente_id: int,
        limite: int = 100
    ) -> List[T_Bitacora]:
        """
        Obtiene el historial de bitácora de un expediente específico.
        
        Args:
            db: Sesión de base de datos
            expediente_id: ID del expediente
            limite: Número máximo de registros a retornar
            
        Returns:
            List[T_Bitacora]: Lista de registros de bitácora ordenados por fecha (más reciente primero)
        """
        try:
            return self.repository.obtener_por_expediente(
                db=db,
                expediente_id=expediente_id,
                limite=limite
            )
        except Exception as e:
            logger.error(f"Error obteniendo bitácora de expediente {expediente_id}: {e}")
            return []
    
    
    def obtener_bitacora_general(
        self,
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        tipo_accion_id: Optional[int] = None,
        usuario_id: Optional[str] = None,
        limite: int = 200
    ) -> List[T_Bitacora]:
        """
        Obtiene registros de bitácora con filtros generales (para administradores).
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango (opcional)
            fecha_fin: Fecha de fin del rango (opcional)
            tipo_accion_id: Filtrar por tipo de acción (opcional)
            usuario_id: Filtrar por usuario (opcional)
            limite: Número máximo de registros a retornar
            
        Returns:
            List[T_Bitacora]: Lista de registros de bitácora
        """
        try:
            return self.repository.obtener_con_filtros(
                db=db,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                tipo_accion_id=tipo_accion_id,
                usuario_id=usuario_id,
                limite=limite
            )
        except Exception as e:
            logger.error(f"Error obteniendo bitácora general: {e}")
            return []
    
    
    def parsear_info_adicional(self, bitacora: T_Bitacora) -> Optional[Dict[str, Any]]:
        """
        Parsea el campo CT_Informacion_adicional de JSON a dict.
        
        Args:
            bitacora: Registro de bitácora
            
        Returns:
            Optional[Dict]: Información adicional parseada o None si está vacía o hay error
        """
        if not bitacora.CT_Informacion_adicional:
            return None
        
        try:
            return json.loads(bitacora.CT_Informacion_adicional)
        except json.JSONDecodeError as e:
            logger.warning(f"Error parseando info_adicional de bitácora {bitacora.CN_Id_bitacora}: {e}")
            return None
    
    
    def obtener_estadisticas(
        self,
        db: Session,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas agregadas de la bitácora.
        
        Args:
            db: Sesión de base de datos
            fecha_inicio: Fecha de inicio del rango (opcional)
            fecha_fin: Fecha de fin del rango (opcional)
            
        Returns:
            Dict: Estadísticas con conteos por tipo de acción
        """
        try:
            conteos = self.repository.contar_por_tipo_accion(
                db=db,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            
            # Convertir a dict con nombres legibles
            estadisticas = {
                "acciones_por_tipo": {
                    DESCRIPCIONES_TIPOS_ACCION.get(tipo_id, f"Tipo {tipo_id}"): conteo
                    for tipo_id, conteo in conteos
                },
                "total_acciones": sum(conteo for _, conteo in conteos),
                "fecha_inicio": fecha_inicio.isoformat() if fecha_inicio else None,
                "fecha_fin": fecha_fin.isoformat() if fecha_fin else None
            }
            
            return estadisticas
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de bitácora: {e}")
            return {
                "acciones_por_tipo": {},
                "total_acciones": 0,
                "error": str(e)
            }
    
    
    def obtener_ultima_accion_usuario(
        self,
        db: Session,
        usuario_id: str,
        tipo_accion_id: Optional[int] = None
    ) -> Optional[T_Bitacora]:
        """
        Obtiene la última acción registrada de un usuario.
        Útil para verificar actividad reciente o última sesión.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            tipo_accion_id: Filtrar por tipo de acción (opcional)
            
        Returns:
            Optional[T_Bitacora]: Último registro o None
        """
        try:
            return self.repository.obtener_ultima_accion_usuario(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=tipo_accion_id
            )
        except Exception as e:
            logger.error(f"Error obteniendo última acción de usuario {usuario_id}: {e}")
            return None


# Instancia singleton del servicio
bitacora_service = BitacoraService()
