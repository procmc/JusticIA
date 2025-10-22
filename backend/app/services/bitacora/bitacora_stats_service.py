"""
Servicio especializado para ESTADÍSTICAS y REPORTES de bitácora.
Maneja todas las operaciones de consulta (read operations) para análisis y reportes.

Separado del bitacora_service.py para mantener:
- bitacora_service.py: Write operations (registrar)
- bitacora_stats_service.py: Read operations (consultas, estadísticas, reportes)
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json
import logging

from app.db.models.bitacora import T_Bitacora
from app.repositories.bitacora_repository import BitacoraRepository
from app.constants.tipos_accion import TiposAccion, DESCRIPCIONES_TIPOS_ACCION

logger = logging.getLogger(__name__)


class BitacoraStatsService:
    """Servicio para estadísticas, consultas y reportes de bitácora"""
    
    def __init__(self):
        self.repo = BitacoraRepository()
    
    # =====================================================================
    # CONSULTAS CON FILTROS
    # =====================================================================
    
    def obtener_con_filtros(
        self,
        db: Session,
        usuario_id: Optional[str] = None,
        tipo_accion_id: Optional[int] = None,
        expediente_numero: Optional[str] = None,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        limite: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Obtiene registros de bitácora con filtros múltiples y paginación.
        Compatible con FiltrosBitacora.jsx del frontend.
        
        Args:
            db: Sesión de base de datos
            usuario_id: Filtrar por usuario específico (nombre o correo)
            tipo_accion_id: Filtrar por tipo de acción
            expediente_numero: Filtrar por número de expediente
            fecha_inicio: Fecha de inicio del rango
            fecha_fin: Fecha de fin del rango
            limite: Número máximo de registros por página (default: 10)
            offset: Número de registros a saltar (default: 0)
            
        Returns:
            Dict con: items (lista de registros), total (count total), page (página actual), pages (total páginas)
        """
        try:
            registros, total_count = self.repo.obtener_con_filtros(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=tipo_accion_id,
                expediente_numero=expediente_numero,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                limite=limite,
                offset=offset
            )
            
            # Expandir información para el frontend
            items = [self._expandir_registro(r) for r in registros]
            
            # Calcular metadatos de paginación
            current_page = (offset // limite) + 1 if limite > 0 else 1
            total_pages = (total_count + limite - 1) // limite if limite > 0 else 1
            
            return {
                "items": items,
                "total": total_count,
                "page": current_page,
                "pages": total_pages,
                "limit": limite,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo bitácora con filtros: {e}")
            return {
                "items": [],
                "total": 0,
                "page": 1,
                "pages": 1,
                "limit": limite,
                "offset": 0
            }
    
    
    def obtener_por_usuario(
        self,
        db: Session,
        usuario_id: str,
        limite: int = 100,
        tipo_accion_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de acciones de un usuario específico.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario (cédula)
            limite: Número máximo de registros
            tipo_accion_id: Filtrar por tipo de acción (opcional)
            
        Returns:
            List[Dict]: Lista de registros expandidos
        """
        try:
            registros = self.repo.obtener_por_usuario(
                db=db,
                usuario_id=usuario_id,
                limite=limite,
                tipo_accion_id=tipo_accion_id
            )
            
            return [self._expandir_registro(r) for r in registros]
            
        except Exception as e:
            logger.error(f"Error obteniendo bitácora de usuario {usuario_id}: {e}")
            return []
    
    
    def obtener_por_expediente(
        self,
        db: Session,
        expediente_numero: str,
        limite: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de acciones de un expediente específico.
        
        Args:
            db: Sesión de base de datos
            expediente_numero: Número del expediente
            limite: Número máximo de registros
            
        Returns:
            List[Dict]: Lista de registros expandidos
        """
        try:
            registros = self.obtener_con_filtros(
                db=db,
                expediente_numero=expediente_numero,
                limite=limite
            )
            
            return registros
            
        except Exception as e:
            logger.error(f"Error obteniendo bitácora de expediente {expediente_numero}: {e}")
            return []
    
    
    # =====================================================================
    # ESTADÍSTICAS ESPECÍFICAS DE RAG
    # =====================================================================
    
    def obtener_estadisticas_rag(self, db: Session, dias: int = 30) -> Dict[str, Any]:
        """
        Obtiene estadísticas específicas para consultas RAG distinguiendo entre
        consultas generales y consultas por expediente específico.
        
        Args:
            db: Sesión de base de datos
            dias: Número de días hacia atrás para las estadísticas
            
        Returns:
            Dict con estadísticas de RAG segregadas por tipo
        """
        try:
            ahora = datetime.utcnow()
            inicio_periodo = ahora - timedelta(days=dias)
            
            # Obtener todas las consultas RAG del período
            registros_rag = self.repo.obtener_con_filtros(
                db=db,
                tipo_accion_id=TiposAccion.CONSULTA_RAG,
                fecha_inicio=inicio_periodo,
                fecha_fin=ahora,
                limite=10000  # Obtener todos para análisis
            )[0]  # Solo nos interesa la lista de registros
            
            # Analizar información adicional para clasificar consultas
            consultas_generales = 0
            consultas_expediente = 0
            expedientes_consultados = set()
            usuarios_activos_rag = set()
            
            for registro in registros_rag:
                usuarios_activos_rag.add(registro.CN_Id_usuario)
                
                # Determinar tipo de consulta basado en información adicional
                info_adicional = self.parsear_info_adicional(registro)
                if info_adicional:
                    tipo_consulta = info_adicional.get("tipo_consulta", "general")
                    expediente_numero = info_adicional.get("expediente_numero")
                    
                    if tipo_consulta == "expediente" and expediente_numero:
                        consultas_expediente += 1
                        expedientes_consultados.add(expediente_numero)
                    else:
                        consultas_generales += 1
                else:
                    # Si no hay información adicional, asumir general
                    consultas_generales += 1
            
            # Obtener expedientes más consultados via RAG
            expedientes_rag_top = []
            if expedientes_consultados:
                # Contar consultas por expediente
                conteo_expedientes = {}
                for registro in registros_rag:
                    info_adicional = self.parsear_info_adicional(registro)
                    if info_adicional:
                        expediente_numero = info_adicional.get("expediente_numero")
                        if expediente_numero:
                            conteo_expedientes[expediente_numero] = conteo_expedientes.get(expediente_numero, 0) + 1
                
                # Top 5 expedientes más consultados
                expedientes_rag_top = sorted(
                    [{"numero": exp, "cantidad": count} for exp, count in conteo_expedientes.items()],
                    key=lambda x: x["cantidad"],
                    reverse=True
                )[:5]
            
            # Estadísticas por día (últimos 7 días)
            inicio_7dias = ahora - timedelta(days=7)
            actividad_rag_diaria = self.repo.obtener_actividad_por_dia(
                db, inicio_7dias, ahora, tipo_accion_id=TiposAccion.CONSULTA_RAG
            )
            
            actividad_rag_por_dia = [
                {
                    "fecha": item["fecha"].isoformat() if item["fecha"] else None,
                    "cantidad": item["cantidad"]
                }
                for item in actividad_rag_diaria
            ]
            
            return {
                "totalConsultasRAG": len(registros_rag),
                "consultasGenerales": consultas_generales,
                "consultasExpediente": consultas_expediente,
                "porcentajeGenerales": round((consultas_generales / len(registros_rag)) * 100, 1) if registros_rag else 0,
                "porcentajeExpedientes": round((consultas_expediente / len(registros_rag)) * 100, 1) if registros_rag else 0,
                "usuariosActivosRAG": len(usuarios_activos_rag),
                "expedientesConsultadosRAG": len(expedientes_consultados),
                "expedientesMasConsultadosRAG": expedientes_rag_top,
                "actividadRAGPorDia": actividad_rag_por_dia,
                "periodo": {
                    "inicio": inicio_periodo.isoformat(),
                    "fin": ahora.isoformat(),
                    "dias": dias
                }
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas RAG: {e}")
            return {
                "totalConsultasRAG": 0,
                "consultasGenerales": 0,
                "consultasExpediente": 0,
                "porcentajeGenerales": 0,
                "porcentajeExpedientes": 0,
                "usuariosActivosRAG": 0,
                "expedientesConsultadosRAG": 0,
                "expedientesMasConsultadosRAG": [],
                "actividadRAGPorDia": [],
                "error": str(e)
            }

    # =====================================================================
    # ESTADÍSTICAS AGREGADAS
    # =====================================================================
    
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
            
            # Top 5 usuarios más activos
            usuarios_activos_raw = self.repo.obtener_usuarios_mas_activos(db, inicio_30dias, ahora, limite=5)
            usuarios_mas_activos = [
                {
                    "nombre": item["nombre"],
                    "cantidad": item["cantidad"]
                }
                for item in usuarios_activos_raw
            ]
            
            # Top 5 expedientes más consultados
            expedientes_raw = self.repo.obtener_expedientes_mas_consultados(db, inicio_30dias, ahora, limite=5)
            expedientes_mas_consultados = [
                {
                    "numero": item["numero"],
                    "cantidad": item["cantidad"]
                }
                for item in expedientes_raw
            ]
            
            # Actividad por día (últimos 7 días)
            actividad_diaria_raw = self.repo.obtener_actividad_por_dia(db, inicio_7dias, ahora)
            actividad_por_dia = [
                {
                    "fecha": item["fecha"].isoformat() if item["fecha"] else None,
                    "cantidad": item["cantidad"]
                }
                for item in actividad_diaria_raw
            ]
            
            return {
                "registrosHoy": registros_hoy,
                "registros7Dias": registros_7dias,
                "registros30Dias": registros_30dias,
                "totalRegistros": total_registros,
                "usuariosUnicos": usuarios_unicos,
                "expedientesUnicos": expedientes_unicos,
                "accionesPorTipo": acciones_por_tipo,
                "usuariosMasActivos": usuarios_mas_activos,
                "expedientesMasConsultados": expedientes_mas_consultados,
                "actividadPorDia": actividad_por_dia
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
                "accionesPorTipo": [],
                "usuariosMasActivos": [],
                "expedientesMasConsultados": [],
                "actividadPorDia": []
            }
    
    
    def obtener_metricas_dashboard(
        self,
        db: Session,
        periodo_dias: int = 30
    ) -> Dict[str, Any]:
        """
        Obtiene métricas específicas para dashboards administrativos.
        Incluye tendencias y comparaciones.
        
        Args:
            db: Sesión de base de datos
            periodo_dias: Días hacia atrás para análisis de tendencias
            
        Returns:
            Dict con métricas detalladas para dashboards
        """
        try:
            ahora = datetime.utcnow()
            inicio_periodo = ahora - timedelta(days=periodo_dias)
            inicio_periodo_anterior = inicio_periodo - timedelta(days=periodo_dias)
            
            # Métricas del período actual
            registros_periodo = self.repo.contar_por_periodo(db, inicio_periodo, ahora)
            
            # Métricas del período anterior (para comparación)
            registros_periodo_anterior = self.repo.contar_por_periodo(
                db, inicio_periodo_anterior, inicio_periodo
            )
            
            # Calcular tendencia
            tendencia_porcentaje = 0
            if registros_periodo_anterior > 0:
                tendencia_porcentaje = (
                    (registros_periodo - registros_periodo_anterior) / registros_periodo_anterior
                ) * 100
            
            # Usuarios más activos
            usuarios_activos = self.repo.obtener_usuarios_mas_activos(db, inicio_periodo, ahora, limite=10)
            
            # Expedientes más consultados
            expedientes_populares = self.repo.obtener_expedientes_mas_consultados(
                db, inicio_periodo, ahora, limite=10
            )
            
            # Distribución por hora del día (últimos 7 días)
            inicio_7dias = ahora - timedelta(days=7)
            distribucion_horaria = self.repo.obtener_distribucion_horaria(db, inicio_7dias, ahora)
            
            return {
                "periodo_dias": periodo_dias,
                "registros_periodo": registros_periodo,
                "registros_periodo_anterior": registros_periodo_anterior,
                "tendencia_porcentaje": round(tendencia_porcentaje, 2),
                "tendencia_direccion": "aumento" if tendencia_porcentaje > 0 else "disminucion" if tendencia_porcentaje < 0 else "estable",
                "usuarios_mas_activos": usuarios_activos,
                "expedientes_mas_consultados": expedientes_populares,
                "distribucion_horaria": distribucion_horaria
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas de dashboard: {e}")
            return {
                "periodo_dias": periodo_dias,
                "registros_periodo": 0,
                "registros_periodo_anterior": 0,
                "tendencia_porcentaje": 0,
                "tendencia_direccion": "estable",
                "usuarios_mas_activos": [],
                "expedientes_mas_consultados": [],
                "distribucion_horaria": []
            }
    
    
    # =====================================================================
    # REPORTES Y ANÁLISIS
    # =====================================================================
    
    def generar_reporte_usuario(
        self,
        db: Session,
        usuario_id: str,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Genera un reporte completo de actividad de un usuario.
        
        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario
            fecha_inicio: Fecha de inicio (opcional, default últimos 30 días)
            fecha_fin: Fecha de fin (opcional, default hoy)
            
        Returns:
            Dict con reporte completo de actividad del usuario
        """
        try:
            ahora = datetime.utcnow()
            fecha_fin = fecha_fin or ahora
            fecha_inicio = fecha_inicio or (ahora - timedelta(days=30))
            
            # Obtener todos los registros del usuario en el período
            registros = self.obtener_con_filtros(
                db=db,
                usuario_id=usuario_id,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                limite=1000  # Sin límite práctico para reportes
            )
            
            # Agrupar por tipo de acción
            acciones_por_tipo = {}
            for registro in registros:
                tipo = registro.get("tipoAccion", "Desconocido")
                acciones_por_tipo[tipo] = acciones_por_tipo.get(tipo, 0) + 1
            
            # Expedientes únicos tocados
            expedientes_unicos = set()
            for registro in registros:
                if registro.get("expediente"):
                    expedientes_unicos.add(registro["expediente"])
            
            return {
                "usuario_id": usuario_id,
                "periodo": {
                    "inicio": fecha_inicio.isoformat(),
                    "fin": fecha_fin.isoformat(),
                    "dias": (fecha_fin - fecha_inicio).days
                },
                "total_acciones": len(registros),
                "acciones_por_tipo": acciones_por_tipo,
                "expedientes_consultados": len(expedientes_unicos),
                "expedientes_unicos": list(expedientes_unicos),
                "promedio_acciones_por_dia": round(
                    len(registros) / max((fecha_fin - fecha_inicio).days, 1), 2
                ),
                "registros": registros[:100]  # Primeros 100 para el reporte
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte de usuario {usuario_id}: {e}")
            return {
                "usuario_id": usuario_id,
                "error": str(e),
                "total_acciones": 0
            }
    
    
    def generar_reporte_expediente(
        self,
        db: Session,
        expediente_numero: str
    ) -> Dict[str, Any]:
        """
        Genera un reporte completo de la historia de un expediente.
        
        Args:
            db: Sesión de base de datos
            expediente_numero: Número del expediente
            
        Returns:
            Dict con timeline completo del expediente
        """
        try:
            registros = self.obtener_por_expediente(
                db=db,
                expediente_numero=expediente_numero,
                limite=500
            )
            
            if not registros:
                return {
                    "expediente_numero": expediente_numero,
                    "total_acciones": 0,
                    "mensaje": "No se encontraron registros para este expediente"
                }
            
            # Extraer fechas clave
            primera_accion = registros[-1] if registros else None  # Último en lista (más antiguo)
            ultima_accion = registros[0] if registros else None  # Primero en lista (más reciente)
            
            # Contar por tipo de acción
            acciones_por_tipo = {}
            usuarios_involucrados = set()
            
            for registro in registros:
                tipo = registro.get("tipoAccion", "Desconocido")
                acciones_por_tipo[tipo] = acciones_por_tipo.get(tipo, 0) + 1
                
                if registro.get("usuario"):
                    usuarios_involucrados.add(registro["usuario"])
            
            return {
                "expediente_numero": expediente_numero,
                "total_acciones": len(registros),
                "primera_accion": primera_accion,
                "ultima_accion": ultima_accion,
                "acciones_por_tipo": acciones_por_tipo,
                "usuarios_involucrados": list(usuarios_involucrados),
                "total_usuarios": len(usuarios_involucrados),
                "timeline": registros  # Timeline completo ordenado por fecha
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte de expediente {expediente_numero}: {e}")
            return {
                "expediente_numero": expediente_numero,
                "error": str(e),
                "total_acciones": 0
            }
    
    
    # =====================================================================
    # UTILIDADES
    # =====================================================================
    
    def _expandir_registro(self, bitacora: T_Bitacora) -> Dict[str, Any]:
        """
        Expande un registro de bitácora con información de relaciones.
        Compatible con la estructura esperada por el frontend.
        
        Args:
            bitacora: Registro de bitácora
            
        Returns:
            Dict con información expandida
        """
        try:
            # Intentar acceder a las relaciones de forma segura
            usuario_nombre = None
            correo_usuario = None
            rol_usuario = None
            tipo_accion_nombre = None
            expediente_numero = None
            
            # Acceder a usuario
            try:
                if hasattr(bitacora, 'usuario') and bitacora.usuario:
                    # Construir nombre completo (Nombre Apellido1 Apellido2)
                    nombre_completo_partes = [bitacora.usuario.CT_Nombre]
                    if bitacora.usuario.CT_Apellido_uno:
                        nombre_completo_partes.append(bitacora.usuario.CT_Apellido_uno)
                    if bitacora.usuario.CT_Apellido_dos:
                        nombre_completo_partes.append(bitacora.usuario.CT_Apellido_dos)
                    usuario_nombre = " ".join(nombre_completo_partes)
                    
                    correo_usuario = bitacora.usuario.CT_Correo
                    # Acceder a rol
                    if hasattr(bitacora.usuario, 'rol') and bitacora.usuario.rol:
                        rol_usuario = bitacora.usuario.rol.CT_Nombre_rol
            except Exception as e:
                logger.warning(f"Error accediendo a usuario: {e}")
            
            # Acceder a tipo de acción desde el diccionario
            if bitacora.CN_Id_tipo_accion:
                tipo_accion_nombre = DESCRIPCIONES_TIPOS_ACCION.get(bitacora.CN_Id_tipo_accion)
            
            # Acceder a expediente
            try:
                if hasattr(bitacora, 'expediente') and bitacora.expediente:
                    expediente_numero = bitacora.expediente.CT_Num_expediente
            except Exception as e:
                logger.warning(f"Error accediendo a expediente: {e}")
            
            return {
                "id": bitacora.CN_Id_bitacora,
                "fechaHora": bitacora.CF_Fecha_hora.isoformat() if bitacora.CF_Fecha_hora else None,
                "texto": bitacora.CT_Texto,
                "informacionAdicional": bitacora.CT_Informacion_adicional,
                
                # IDs originales
                "idUsuario": bitacora.CN_Id_usuario,
                "idTipoAccion": bitacora.CN_Id_tipo_accion,
                "idExpediente": bitacora.CN_Id_expediente,
                
                # Información expandida
                "usuario": usuario_nombre,
                "correoUsuario": correo_usuario,
                "rolUsuario": rol_usuario,
                "tipoAccion": tipo_accion_nombre,
                "expediente": expediente_numero,
                
                # Estado (por defecto Procesado ya que se registró exitosamente)
                "estado": "Procesado"
            }
        except Exception as e:
            logger.error(f"Error expandiendo registro {bitacora.CN_Id_bitacora}: {e}")
            # Retornar estructura mínima en caso de error
            return {
                "id": bitacora.CN_Id_bitacora,
                "fechaHora": bitacora.CF_Fecha_hora.isoformat() if bitacora.CF_Fecha_hora else None,
                "texto": bitacora.CT_Texto,
                "informacionAdicional": bitacora.CT_Informacion_adicional,
                "idUsuario": bitacora.CN_Id_usuario,
                "idTipoAccion": bitacora.CN_Id_tipo_accion,
                "idExpediente": bitacora.CN_Id_expediente,
                "usuario": None,
                "correoUsuario": None,
                "rolUsuario": None,
                "tipoAccion": DESCRIPCIONES_TIPOS_ACCION.get(bitacora.CN_Id_tipo_accion) if bitacora.CN_Id_tipo_accion else None,
                "expediente": None,
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


# Instancia singleton del servicio de estadísticas
bitacora_stats_service = BitacoraStatsService()
