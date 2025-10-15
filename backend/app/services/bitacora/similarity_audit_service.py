"""
Servicio especializado de auditoría para el módulo de BÚSQUEDA DE SIMILARES.
Registra acciones de búsqueda de casos similares y generación de resúmenes con IA.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import logging

from app.db.models.bitacora import T_Bitacora
from app.constants.tipos_accion import TiposAccion
from .bitacora_service import BitacoraService

logger = logging.getLogger(__name__)


class SimilarityAuditService:
    """Servicio especializado para auditoría del módulo de BÚSQUEDA DE SIMILARES"""
    
    def __init__(self):
        self.bitacora_service = BitacoraService()
    
    async def registrar_busqueda_similares(
        self,
        db: Session,
        usuario_id: Optional[str],
        modo_busqueda: str,
        texto_consulta: Optional[str] = None,
        numero_expediente: Optional[str] = None,
        limite: Optional[int] = None,
        umbral_similitud: Optional[float] = None,
        exito: bool = True,
        error: Optional[str] = None,
        resultado: Optional[Dict[str, Any]] = None
    ) -> Optional[T_Bitacora]:
        """
        Registra búsquedas de casos similares en la bitácora.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario que realiza la búsqueda - Opcional para procesos automáticos
            modo_busqueda: Modo de búsqueda ("descripcion" o "expediente")
            texto_consulta: Texto de consulta (para modo descripción)
            numero_expediente: Número de expediente (para modo expediente)
            limite: Límite de resultados solicitados
            umbral_similitud: Umbral de similitud usado
            exito: Si la búsqueda fue exitosa o no
            error: Mensaje de error (si hubo error)
            resultado: Datos del resultado (si fue exitoso)
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            from app.repositories.expediente_repository import ExpedienteRepository
            
            # Determinar el texto de búsqueda para el registro
            texto_busqueda = texto_consulta if modo_busqueda == "descripcion" else numero_expediente
            
            # Obtener ID del expediente si estamos buscando por expediente
            expediente_db_id = None
            if modo_busqueda == "expediente" and numero_expediente:
                exp_obj = ExpedienteRepository().obtener_por_numero(db, numero_expediente)
                if exp_obj:
                    expediente_db_id = exp_obj.CN_Id_expediente
            
            # Construir información adicional
            info = {
                "modo_busqueda": modo_busqueda,
                "texto_consulta": texto_consulta,
                "numero_expediente": numero_expediente,
                "limite": limite,
                "umbral_similitud": umbral_similitud,
            }
            
            # Si hubo error, agregar información del error
            if not exito and error:
                info["error"] = error
                info["tipo_error"] = "validacion" if "validación" in error.lower() or "requerido" in error.lower() else "interno"
                texto_registro = f"Error en búsqueda de casos similares: {error[:150]}"
            
            # Si fue exitoso, agregar resultados
            elif exito and resultado:
                info["total_resultados"] = resultado.get("total_resultados")
                info["tiempo_busqueda_segundos"] = resultado.get("tiempo_busqueda_segundos")
                info["precision_promedio"] = resultado.get("precision_promedio")
                
                # Top expedientes encontrados (primeros 5)
                casos_similares = resultado.get("casos_similares", [])
                if casos_similares:
                    info["top_expedientes"] = [
                        caso.get("CT_Num_expediente") 
                        for caso in casos_similares[:5]
                        if isinstance(caso, dict) and caso.get("CT_Num_expediente")
                    ]
                
                texto_registro = f"Búsqueda de casos similares ({modo_busqueda}): '{texto_busqueda[:200] if texto_busqueda else 'N/A'}'"
            
            else:
                texto_registro = f"Búsqueda de casos similares ({modo_busqueda}): '{texto_busqueda[:200] if texto_busqueda else 'N/A'}'"
            
            # Registrar en bitácora usando el servicio general
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=TiposAccion.BUSQUEDA_SIMILARES,
                texto=texto_registro,
                expediente_id=expediente_db_id,
                info_adicional=info
            )
            
        except Exception as e:
            logger.warning(f"Error registrando búsqueda similares en bitácora: {e}")
            return None
    
    
    async def registrar_resumen_ia(
        self,
        db: Session,
        usuario_id: Optional[str],
        numero_expediente: str,
        exito: bool = True,
        error: Optional[str] = None,
        resultado: Optional[Dict[str, Any]] = None
    ) -> Optional[T_Bitacora]:
        """
        Registra generación de resúmenes de IA en la bitácora.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario que solicita el resumen - Opcional para procesos automáticos
            numero_expediente: Número del expediente a resumir
            exito: Si la generación fue exitosa o no
            error: Mensaje de error (si hubo error)
            resultado: Datos del resultado (si fue exitoso)
            
        Returns:
            T_Bitacora: Registro creado o None si hubo error
        """
        try:
            from app.repositories.expediente_repository import ExpedienteRepository
            
            # Obtener ID del expediente
            expediente_db_id = None
            exp_obj = ExpedienteRepository().obtener_por_numero(db, numero_expediente)
            if exp_obj:
                expediente_db_id = exp_obj.CN_Id_expediente
            
            # Construir información adicional
            info = {
                "numero_expediente": numero_expediente,
            }
            
            # Si hubo error, agregar información del error
            if not exito and error:
                info["error"] = error
                info["tipo_error"] = "validacion" if "validación" in error.lower() or "requerido" in error.lower() or "no existe" in error.lower() else "interno"
                texto_registro = f"Error al generar resumen IA: {numero_expediente} - {error[:150]}"
            
            # Si fue exitoso, agregar estadísticas del resumen
            elif exito and resultado:
                info["resumen_generado"] = True
                info["documentos_analizados"] = resultado.get("total_documentos_analizados")
                info["tiempo_generacion_segundos"] = resultado.get("tiempo_generacion_segundos")
                
                # Información del resumen generado
                resumen_ia = resultado.get("resumen_ia")
                if resumen_ia and isinstance(resumen_ia, dict):
                    info["longitud_resumen"] = len(resumen_ia.get("resumen", ""))
                    info["total_palabras_clave"] = len(resumen_ia.get("palabras_clave", []))
                    info["total_factores_similitud"] = len(resumen_ia.get("factores_similitud", []))
                    info["tiene_conclusion"] = bool(resumen_ia.get("conclusion"))
                
                texto_registro = f"Resumen IA generado para expediente: {numero_expediente}"
            
            else:
                texto_registro = f"Resumen IA para expediente: {numero_expediente}"
            
            # Registrar en bitácora usando el servicio general
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=TiposAccion.BUSQUEDA_SIMILARES,  # Usamos el mismo tipo ya que está relacionado
                texto=texto_registro,
                expediente_id=expediente_db_id,
                info_adicional=info
            )
            
        except Exception as e:
            logger.warning(f"Error registrando resumen IA en bitácora: {e}")
            return None


# Instancia singleton del servicio especializado
similarity_audit_service = SimilarityAuditService()
