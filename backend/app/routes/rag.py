from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.schemas.rag_schemas import (
    ConsultaRAGRequest, ConsultaGeneralRAGResponse,
    ConsultaExpedienteRAGRequest, ConsultaExpedienteRAGResponse,
    BusquedaSimilaresRAGRequest, BusquedaSimilaresRAGResponse,
    AnalisisExpedienteRAGRequest, AnalisisExpedienteRAGResponse,
    BusquedaAvanzadaRAGRequest, SugerenciaLegalRAGRequest, SugerenciaLegalRAGResponse
)
from app.services.rag_chain_service import get_rag_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG - Consultas Inteligentes"])

@router.post("/consulta-general", response_model=ConsultaGeneralRAGResponse)
async def consulta_general_rag(
    request: ConsultaRAGRequest,
    rag_service = Depends(get_rag_service)
):
    """
    Realiza una consulta general inteligente en todos los expedientes usando RAG Chain.
    
    Esta función permite hacer preguntas en lenguaje natural que serán respondidas
    analizando el contenido de todos los expedientes en la base de datos.
    
    Ejemplos de consultas:
    - "¿Cuántos casos de divorcio tuvimos en 2024?"
    - "Expedientes donde se haya solicitado medida cautelar"
    - "Casos penales con sobreseimiento en los últimos años"
    """
    try:
        logger.info(f"Consulta general RAG: {request.pregunta}")
        
        resultado = await rag_service.consulta_general(
            pregunta=request.pregunta,
            top_k=request.top_k
        )
        
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])
        
        return ConsultaGeneralRAGResponse(**resultado)
        
    except Exception as e:
        logger.error(f"Error en consulta general RAG: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")

@router.post("/consulta-expediente", response_model=ConsultaExpedienteRAGResponse)
async def consulta_expediente_rag(
    request: ConsultaExpedienteRAGRequest,
    rag_service = Depends(get_rag_service)
):
    """
    Realiza una consulta específica sobre un expediente usando RAG Chain.
    
    Permite hacer preguntas detalladas sobre un expediente particular,
    analizando todos los documentos asociados.
    
    Ejemplos:
    - "¿Cuál es el estado actual del proceso?"
    - "¿Qué alegatos presentó la defensa?"
    - "Resume las actuaciones más importantes"
    """
    try:
        logger.info(f"Consulta expediente {request.expediente_numero}")
        
        resultado = await rag_service.consulta_expediente(
            pregunta=request.pregunta,
            expediente_numero=request.expediente_numero,
            top_k=request.top_k
        )
        
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])
        
        return ConsultaExpedienteRAGResponse(**resultado)
        
    except Exception as e:
        logger.error(f"Error en consulta expediente RAG: {e}")
        raise HTTPException(status_code=500, detail=f"Error consultando expediente: {str(e)}")

@router.post("/buscar-similares", response_model=BusquedaSimilaresRAGResponse)
async def buscar_casos_similares_rag(
    request: BusquedaSimilaresRAGRequest,
    rag_service = Depends(get_rag_service)
):
    """
    Busca casos similares usando RAG Chain.
    
    Analiza la descripción proporcionada y encuentra expedientes con
    situaciones jurídicas similares, proporcionando un análisis comparativo.
    
    Útil para:
    - Encontrar precedentes
    - Identificar estrategias exitosas
    - Comparar casos similares
    """
    try:
        logger.info(f"Búsqueda de casos similares")
        
        resultado = await rag_service.buscar_casos_similares(
            descripcion_caso=request.descripcion_caso,
            expediente_excluir=request.expediente_excluir,
            top_k=request.top_k
        )
        
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])
        
        return BusquedaSimilaresRAGResponse(**resultado)
        
    except Exception as e:
        logger.error(f"Error en búsqueda de similares RAG: {e}")
        raise HTTPException(status_code=500, detail=f"Error buscando casos similares: {str(e)}")

@router.post("/analizar-expediente", response_model=AnalisisExpedienteRAGResponse)
async def analizar_expediente_completo(
    request: AnalisisExpedienteRAGRequest,
    rag_service = Depends(get_rag_service)
):
    """
    Realiza un análisis completo de un expediente usando RAG Chain.
    
    Proporciona un análisis estructurado que incluye:
    - Resumen del caso
    - Partes involucradas
    - Estado procesal
    - Documentos principales
    - Próximas actuaciones
    """
    try:
        logger.info(f"Análisis completo de expediente {request.expediente_numero}")
        
        # Usar consulta predefinida para análisis completo
        pregunta_analisis = f"""
        Realiza un análisis completo y estructurado del expediente {request.expediente_numero}.
        
        Incluye:
        1. Resumen del caso y tipo de proceso
        2. Partes involucradas (demandante, demandado, etc.)
        3. Estado procesal actual
        4. Documentos principales identificados
        5. Próximas actuaciones o pendientes mencionados
        6. Cronología de eventos importantes
        
        Estructura la respuesta de manera clara y profesional.
        """
        
        resultado = await rag_service.consulta_expediente(
            pregunta=pregunta_analisis,
            expediente_numero=request.expediente_numero,
            top_k=20  # Más documentos para análisis completo
        )
        
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])
        
        # Transformar resultado a formato de análisis
        return AnalisisExpedienteRAGResponse(
            respuesta=resultado["respuesta"],
            expediente=resultado["expediente"],
            # Los campos específicos se extraerían del análisis del LLM
            # por ahora retornamos la respuesta completa
        )
        
    except Exception as e:
        logger.error(f"Error en análisis completo de expediente: {e}")
        raise HTTPException(status_code=500, detail=f"Error analizando expediente: {str(e)}")

@router.get("/busqueda-avanzada")
async def busqueda_avanzada_rag(
    consulta: str = Query(..., min_length=3, description="Consulta de búsqueda"),
    tipo_proceso: Optional[str] = Query(None, description="Filtrar por tipo: PN, FA, CV, etc."),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    top_k: int = Query(20, ge=1, le=100, description="Número de resultados"),
    rag_service = Depends(get_rag_service)
):
    """
    Búsqueda avanzada con filtros usando RAG Chain.
    
    Permite realizar búsquedas con filtros específicos como:
    - Tipo de proceso
    - Rango de fechas
    - Número de resultados
    """
    try:
        logger.info(f"Búsqueda avanzada: {consulta}")
        
        # Construir filtros de Milvus si se proporcionan
        filtros_milvus = []
        
        if tipo_proceso:
            # Asumir que tienes campo tipo_proceso en metadata
            filtros_milvus.append(f'tipo_proceso == "{tipo_proceso}"')
        
        # Para fechas, necesitarías tener campos de fecha en tu esquema de Milvus
        # if fecha_desde and fecha_hasta:
        #     filtros_milvus.append(f'fecha >= "{fecha_desde}" and fecha <= "{fecha_hasta}"')
        
        filtro_final = " and ".join(filtros_milvus) if filtros_milvus else None
        
        # Modificar temporalmente el retriever para usar filtros
        resultado = await rag_service.consulta_general(
            pregunta=consulta,
            top_k=top_k
        )
        
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])
        
        return {
            "success": True,
            "data": resultado,
            "filtros_aplicados": {
                "tipo_proceso": tipo_proceso,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta
            }
        }
        
    except Exception as e:
        logger.error(f"Error en búsqueda avanzada RAG: {e}")
        raise HTTPException(status_code=500, detail=f"Error en búsqueda avanzada: {str(e)}")

@router.post("/sugerencias-legales", response_model=SugerenciaLegalRAGResponse)
async def obtener_sugerencias_legales(
    request: SugerenciaLegalRAGRequest,
    rag_service = Depends(get_rag_service)
):
    """
    Obtiene sugerencias legales basadas en precedentes usando RAG Chain.
    
    Analiza la situación legal proporcionada y:
    - Encuentra precedentes relevantes
    - Sugiere estrategias legales
    - Identifica documentos modelo
    - Proporciona recomendaciones basadas en casos similares
    """
    try:
        logger.info(f"Solicitud de sugerencias legales")
        
        # Buscar casos similares primero
        casos_similares = await rag_service.buscar_casos_similares(
            descripcion_caso=request.situacion_legal,
            top_k=15
        )
        
        # Generar consulta para sugerencias específicas
        consulta_sugerencias = f"""
        Basándote en los casos similares encontrados y la situación legal descrita,
        proporciona sugerencias legales específicas:
        
        Situación: {request.situacion_legal}
        
        Proporciona:
        1. Estrategias legales recomendadas
        2. Precedentes aplicables
        3. Documentos que podrían servir como modelo
        4. Argumentos legales que han sido exitosos en casos similares
        5. Posibles obstáculos y cómo abordarlos
        
        Basa tus recomendaciones en los casos encontrados en la base de datos.
        """
        
        resultado_sugerencias = await rag_service.consulta_general(
            pregunta=consulta_sugerencias,
            top_k=20
        )
        
        if "error" in resultado_sugerencias:
            raise HTTPException(status_code=500, detail=resultado_sugerencias["error"])
        
        # Extraer precedentes de casos similares
        precedentes = casos_similares.get("casos_similares", [])[:5]
        
        return SugerenciaLegalRAGResponse(
            respuesta=resultado_sugerencias["respuesta"],
            sugerencias=[],  # Se extraerían del análisis del LLM
            precedentes=precedentes,
            estrategias_recomendadas=[],  # Se extraerían del análisis del LLM
            documentos_modelo=resultado_sugerencias.get("fuentes", [])[:5]
        )
        
    except Exception as e:
        logger.error(f"Error en sugerencias legales RAG: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo sugerencias: {str(e)}")

@router.get("/estadisticas")
async def obtener_estadisticas_rag(
    periodo: Optional[str] = Query(None, description="Período para análisis (ej: '2024', 'últimos 6 meses')"),
    tipo_proceso: Optional[str] = Query(None, description="Filtrar por tipo de proceso"),
    rag_service = Depends(get_rag_service)
):
    """
    Obtiene estadísticas y análisis de tendencias usando RAG Chain.
    
    Proporciona insights sobre:
    - Distribución de casos por tipo
    - Tendencias temporales
    - Análisis de patrones
    - Estadísticas de éxito/resolución
    """
    try:
        logger.info(f"Solicitud de estadísticas RAG")
        
        consulta_estadisticas = f"""
        Analiza las estadísticas y tendencias de los expedientes en la base de datos.
        
        Proporciona:
        1. Distribución de casos por tipo de proceso
        2. Tendencias temporales {f'para el período {periodo}' if periodo else ''}
        3. Tipos de casos más comunes
        4. Patrones identificados en resoluciones
        5. Insights relevantes para la práctica legal
        
        {f'Enfócate en casos de tipo {tipo_proceso}' if tipo_proceso else ''}
        
        Presenta la información de manera estructurada y con datos específicos extraídos de los expedientes.
        """
        
        resultado = await rag_service.consulta_general(
            pregunta=consulta_estadisticas,
            top_k=50  # Más documentos para análisis estadístico
        )
        
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])
        
        return {
            "success": True,
            "data": {
                "analisis_completo": resultado["respuesta"],
                "expedientes_analizados": resultado["expedientes_consultados"],
                "total_documentos": resultado["total_documentos"],
                "periodo_analizado": periodo,
                "tipo_proceso_filtrado": tipo_proceso
            }
        }
        
    except Exception as e:
        logger.error(f"Error en estadísticas RAG: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")