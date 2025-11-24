"""
Servicio especializado de auditoría para el módulo de BÚSQUEDA DE SIMILARES.

Este módulo maneja el registro de auditoría para el sistema de búsqueda de casos
similares y generación de resúmenes con IA. Registra tanto búsquedas exitosas como
errores, capturando metadata de resultados y parámetros de búsqueda.

Funcionalidades auditadas:
    * BÚSQUEDA DE SIMILARES (TiposAccion.BUSQUEDA_SIMILARES):
      - Búsqueda por descripción de texto libre
      - Búsqueda por expediente de referencia
      - Parámetros: límite, umbral de similitud
      - Resultados: total, precisión, top expedientes
    
    * GENERACIÓN DE RESÚMENES IA (TiposAccion.GENERAR_RESUMEN):
      - Resúmenes automáticos de expedientes con LLM
      - Análisis de documentos del expediente
      - Metadata: longitud, palabras clave, factores similitud

Modos de búsqueda:
    * "descripcion": Búsqueda vectorial por texto libre del usuario
    * "expediente": Búsqueda de expedientes similares a uno de referencia

Información registrada en búsquedas:
    * Modo de búsqueda y texto/expediente consultado
    * Parámetros: límite, umbral de similitud
    * Resultados: total_resultados, tiempo_busqueda, precision_promedio
    * Top 5 expedientes encontrados
    * Errores: tipo (validación/interno), mensaje

Información registrada en resúmenes:
    * Expediente resumido
    * Documentos analizados
    * Tiempo de generación
    * Estadísticas del resumen: longitud, palabras clave, factores

Integración:
    * app.services.similarity_service: Llama a este servicio después de búsquedas
    * app.routes.similarity: Endpoints que registran operaciones

Example:
    >>> from app.services.bitacora.similarity_audit_service import similarity_audit_service
    >>> 
    >>> # Registrar búsqueda exitosa por descripción
    >>> await similarity_audit_service.registrar_busqueda_similares(
    ...     db=db,
    ...     usuario_id="112340567",
    ...     modo_busqueda="descripcion",
    ...     texto_consulta="Divorcio por mutuo acuerdo",
    ...     limite=10,
    ...     umbral_similitud=0.20,
    ...     exito=True,
    ...     resultado={
    ...         "total_resultados": 8,
    ...         "tiempo_busqueda_segundos": 1.2,
    ...         "precision_promedio": 0.85,
    ...         "casos_similares": [...]
    ...     }
    ... )
    >>> 
    >>> # Registrar error de validación
    >>> await similarity_audit_service.registrar_busqueda_similares(
    ...     db=db,
    ...     usuario_id="112340567",
    ...     modo_busqueda="expediente",
    ...     numero_expediente="24-INVALID",
    ...     exito=False,
    ...     error="Número de expediente inválido"
    ... )
    >>> 
    >>> # Registrar generación de resumen
    >>> await similarity_audit_service.registrar_resumen_ia(
    ...     db=db,
    ...     usuario_id="112340567",
    ...     numero_expediente="24-000123-0001-PE",
    ...     exito=True,
    ...     resultado={
    ...         "total_documentos_analizados": 5,
    ...         "tiempo_generacion_segundos": 8.5,
    ...         "resumen_ia": {
    ...             "resumen": "...",
    ...             "palabras_clave": ["divorcio", "mutuo acuerdo"],
    ...             "factores_similitud": [...],
    ...             "conclusion": "..."
    ...         }
    ...     }
    ... )

Note:
    * usuario_id es opcional (None para procesos automáticos)
    * Dos tipos de acciones: BUSQUEDA_SIMILARES (1) y GENERAR_RESUMEN (13)
    * Registra tanto éxitos como errores para análisis completo
    * Errores se clasifican: "validacion" vs "interno"
    * Top 5 expedientes se extraen de casos_similares
    * Errores de registro se loggean como WARNING
    * Asocia expediente automáticamente por número

Ver también:
    * app.services.bitacora.bitacora_service: Servicio base
    * app.services.similarity_service: Servicio de búsqueda
    * app.constants.tipos_accion: BUSQUEDA_SIMILARES, GENERAR_RESUMEN

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0 - Auditoría de búsqueda y resúmenes IA
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
                tipo_accion_id=TiposAccion.GENERAR_RESUMEN,
                texto=texto_registro,
                expediente_id=expediente_db_id,
                info_adicional=info
            )
            
        except Exception as e:
            logger.warning(f"Error registrando resumen IA en bitácora: {e}")
            return None


# Instancia singleton del servicio especializado
similarity_audit_service = SimilarityAuditService()
