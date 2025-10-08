"""
Servicio para gestión de bitácora de acciones del sistema.
Registra todas las acciones de usuarios para auditoría y trazabilidad.
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
    """Servicio para manejo de bitácora de acciones del sistema"""
    
    def __init__(self):
        self.repo = BitacoraRepository()
    
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
                f"Bitácora registrada: Usuario={usuario_id}, "
                f"Tipo={DESCRIPCIONES_TIPOS_ACCION.get(tipo_accion_id, 'Desconocido')}, "
                f"Texto='{texto}'"
            )
            
            return bitacora
            
        except Exception as e:
            logger.error(f"Error registrando en bitácora: {e}")
            raise Exception(f"Error al registrar en bitácora: {str(e)}")
    
    
    def obtener_con_filtros(
        self,
        db: Session,
        usuario_id: Optional[str] = None,
        tipo_accion_id: Optional[int] = None,
        expediente_numero: Optional[str] = None,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        limite: int = 200
    ) -> list:
        """
        Obtiene registros de bitácora con filtros múltiples.
        Compatible con FiltrosBitacora.jsx del frontend.
        
        Args:
            db: Sesión de base de datos
            usuario_id: Filtrar por usuario específico (nombre o correo)
            tipo_accion_id: Filtrar por tipo de acción
            expediente_numero: Filtrar por número de expediente
            fecha_inicio: Fecha de inicio del rango
            fecha_fin: Fecha de fin del rango
            limite: Número máximo de registros
            
        Returns:
            list: Lista de registros de bitácora con información expandida
        """
        try:
            registros = self.repo.obtener_con_filtros(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=tipo_accion_id,
                expediente_numero=expediente_numero,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                limite=limite
            )
            
            # Expandir información para el frontend
            return [self._expandir_registro(r) for r in registros]
            
        except Exception as e:
            logger.error(f"Error obteniendo bitácora con filtros: {e}")
            return []
    
    
    def obtener_estadisticas(self, db: Session, dias: int = 30) -> Dict[str, Any]:
        """
        Obtiene estadísticas agregadas de la bitácora.
        Compatible con DashboardEstadisticas.jsx del frontend.
        
        Args:
            db: Sesión de base de datos
            dias: Número de días hacia atrás para las estadísticas
            
        Returns:
            Dict con estadísticas completas para el dashboard
        """
        try:
            ahora = datetime.utcnow()
            inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
            inicio_7dias = ahora - timedelta(days=7)
            inicio_30dias = ahora - timedelta(days=30)
            
            # Total de registros
            total_registros = self.repo.contar_total(db)
            
            # Registros por período
            registros_hoy = self.repo.contar_por_periodo(db, inicio_hoy, ahora)
            registros_7dias = self.repo.contar_por_periodo(db, inicio_7dias, ahora)
            registros_30dias = self.repo.contar_por_periodo(db, inicio_30dias, ahora)
            
            # Contadores únicos
            usuarios_unicos = self.repo.contar_usuarios_unicos(db, inicio_30dias, ahora)
            expedientes_unicos = self.repo.contar_expedientes_unicos(db, inicio_30dias, ahora)
            
            # Acciones por tipo (con nombres legibles)
            acciones_por_tipo_raw = self.repo.obtener_acciones_por_tipo(db, inicio_30dias, ahora)
            acciones_por_tipo = [
                {
                    "tipo": DESCRIPCIONES_TIPOS_ACCION.get(item["tipo_id"], f"Tipo {item['tipo_id']}"),
                    "cantidad": item["cantidad"]
                }
                for item in acciones_por_tipo_raw
            ]
            
            return {
                "registrosHoy": registros_hoy,
                "registros7Dias": registros_7dias,
                "registros30Dias": registros_30dias,
                "totalRegistros": total_registros,
                "usuariosUnicos": usuarios_unicos,
                "expedientesUnicos": expedientes_unicos,
                "accionesPorTipo": acciones_por_tipo
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                "registrosHoy": 0,
                "registros7Dias": 0,
                "registros30Dias": 0,
                "totalRegistros": 0,
                "usuariosUnicos": 0,
                "expedientesUnicos": 0,
                "accionesPorTipo": []
            }
    
    
    def _expandir_registro(self, bitacora: T_Bitacora) -> Dict[str, Any]:
        """
        Expande un registro de bitácora con información de relaciones.
        Compatible con la estructura esperada por el frontend.
        
        Args:
            bitacora: Registro de bitácora
            
        Returns:
            Dict con información expandida
        """
        return {
            "id": bitacora.CN_Id_bitacora,
            "fechaHora": bitacora.CF_Fecha_hora.isoformat() if bitacora.CF_Fecha_hora else None,
            "texto": bitacora.CT_Texto,
            "informacionAdicional": bitacora.CT_Informacion_adicional,
            
            # IDs originales
            "idUsuario": bitacora.CN_Id_usuario,
            "idTipoAccion": bitacora.CN_Id_tipo_accion,
            "idExpediente": bitacora.CN_Id_expediente,
            
            # Información expandida (si existe)
            "usuario": bitacora.usuario.CT_Nombre_usuario if bitacora.usuario else None,
            "correoUsuario": bitacora.usuario.CT_Correo if bitacora.usuario else None,
            "rolUsuario": bitacora.usuario.rol.CT_Nombre_rol if bitacora.usuario and bitacora.usuario.rol else None,
            "tipoAccion": DESCRIPCIONES_TIPOS_ACCION.get(bitacora.CN_Id_tipo_accion) if bitacora.CN_Id_tipo_accion else None,
            "expediente": bitacora.expediente.CT_Num_expediente if bitacora.expediente else None,
            
            # Estado (por defecto Procesado ya que se registró exitosamente)
            "estado": "Procesado"
        }
    
    
    def parsear_info_adicional(self, bitacora: T_Bitacora) -> Optional[Dict[str, Any]]:
        """
        Parsea el campo CT_Informacion_adicional de JSON a dict.
        
        Args:
            bitacora: Registro de bitácora
            
        Returns:
            Optional[Dict]: Información adicional parseada o None
        """
        if not bitacora.CT_Informacion_adicional:
            return None
        
        try:
            return json.loads(bitacora.CT_Informacion_adicional)
        except json.JSONDecodeError as e:
            logger.warning(f"Error parseando info_adicional de bitácora {bitacora.CN_Id_bitacora}: {e}")
            return None


# Instancia singleton del servicio
bitacora_service = BitacoraService()
