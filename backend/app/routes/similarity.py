"""
Endpoints de Búsqueda de Casos Similares por Similitud Semántica.

Este módulo expone los endpoints de la API para buscar expedientes similares
usando búsqueda vectorial en Milvus y generar resúmenes de IA con análisis
de factores de similitud.

Endpoints principales:
    POST /similarity/search: Busca expedientes similares
    POST /similarity/generate-summary: Genera resumen de IA de expediente

Modos de búsqueda:
    - 'texto': Búsqueda por fragmento de texto libre
    - 'expediente': Búsqueda por número de expediente específico
    
Arquitectura de similitud:
    1. Usuario ingresa texto o número de expediente
    2. Si es texto: se genera embedding con modelo BGE-M3-ES-Legal
    3. Si es expediente: se recuperan todos sus embeddings de Milvus
    4. Búsqueda vectorial en Milvus con cosine similarity
    5. Filtrado por umbral de similitud (default: 0.7)
    6. Agrupación por expediente y cálculo de score promedio
    7. Retorno de resultados ordenados por relevancia

Generación de resúmenes:
    - Recupera todos los documentos del expediente
    - Analiza contenido con LLM (Ollama)
    - Genera resumen estructurado con:
      * Resumen ejecutivo
      * Palabras clave
      * Factores de similitud (hechos, tipo de caso, partes)
      * Conclusión

Auditoría:
    - Registra todas las búsquedas en bitácora (T_Bitacora_acciones_similares)
    - Incluye: usuario, modo, parámetros, resultados, errores
    - Registra generación de resúmenes (T_Bitacora_resumen_ia)

Example:
    >>> # Búsqueda por texto
    >>> response = requests.post('/similarity/search', json={
    ...     'modo_busqueda': 'texto',
    ...     'texto_consulta': 'homicidio culposo',
    ...     'limite': 10,
    ...     'umbral_similitud': 0.7
    ... })
    >>> print(response.json()['total_resultados'])
    15
    >>> 
    >>> # Generar resumen
    >>> response = requests.post('/similarity/generate-summary', json={
    ...     'numero_expediente': '00-001234-0567-PE'
    ... })
    >>> print(response.json()['resumen_ia']['resumen'])

Note:
    - umbral_similitud válido: 0.0 a 1.0 (default: 0.7)
    - limite máximo recomendado: 50 resultados
    - La generación de resúmenes puede tardar varios segundos
    - Requiere autenticación JWT (usuario judicial)
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.similarity_schemas import (
    SimilaritySearchRequest,
    RespuestaBusquedaSimilitud,
    GenerateResumenRequest,
    RespuestaGenerarResumen,
)
from app.services.busqueda_similares.similarity_service import SimilarityService
from app.services.bitacora.similarity_audit_service import similarity_audit_service
from app.auth.jwt_auth import require_usuario_judicial
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/search", response_model=RespuestaBusquedaSimilitud)
async def search_similar_cases(
    data: SimilaritySearchRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
) -> RespuestaBusquedaSimilitud:
    """
    Busca expedientes similares por contenido textual o número de expediente.
    
    Realiza búsqueda vectorial en Milvus para encontrar expedientes con
    similitud semántica. Soporta dos modos: búsqueda por texto libre o
    por número de expediente específico.
    
    Args:
        data (SimilaritySearchRequest): Parámetros de búsqueda:
            - modo_busqueda: 'texto' o 'expediente'
            - texto_consulta: Texto para modo 'texto' (opcional)
            - numero_expediente: Número para modo 'expediente' (opcional)
            - limite: Cantidad máxima de resultados (default: 10)
            - umbral_similitud: Umbral mínimo de similitud 0-1 (default: 0.7)
        db (Session): Sesión de base de datos.
        current_user (dict): Usuario autenticado (JWT).
    
    Returns:
        RespuestaBusquedaSimilitud: Resultados de búsqueda con:
            - casos_similares: Lista de expedientes encontrados con score
            - total_resultados: Cantidad de resultados
            - tiempo_busqueda_segundos: Tiempo de procesamiento
            - precision_promedio: Score promedio de resultados
    
    Raises:
        HTTPException 400: Si los parámetros son inválidos
        HTTPException 500: Si hay error interno en la búsqueda
    
    Example:
        >>> # Búsqueda por texto
        >>> POST /similarity/search
        >>> {
        ...   "modo_busqueda": "texto",
        ...   "texto_consulta": "homicidio culposo con arma de fuego",
        ...   "limite": 20,
        ...   "umbral_similitud": 0.75
        ... }
        >>> 
        >>> # Búsqueda por expediente
        >>> POST /similarity/search
        >>> {
        ...   "modo_busqueda": "expediente",
        ...   "numero_expediente": "00-001234-0567-PE",
        ...   "limite": 10
        ... }
    
    Note:
        - La búsqueda se registra en bitácora para auditoría
        - Los resultados están ordenados por score (mayor a menor)
        - El score representa similitud de coseno (0-1)
    """
    try:
        similarity_service = SimilarityService()
        result = await similarity_service.search_similar_cases(data, db)  # Pasar db
        
        # Registrar búsqueda exitosa en bitácora
        await similarity_audit_service.registrar_busqueda_similares(
            db=db,
            usuario_id=current_user["user_id"],
            modo_busqueda=data.modo_busqueda,
            texto_consulta=data.texto_consulta,
            numero_expediente=data.numero_expediente,
            limite=data.limite,
            umbral_similitud=data.umbral_similitud,
            exito=True,
            resultado={
                "total_resultados": result.total_resultados,
                "tiempo_busqueda_segundos": result.tiempo_busqueda_segundos,
                "precision_promedio": result.precision_promedio,
                "casos_similares": [
                    {"CT_Num_expediente": caso.CT_Num_expediente} 
                    for caso in (result.casos_similares[:5] if result.casos_similares else [])
                ]
            }
        )
        
        return result
        
    except ValueError as e:
        # Errores de validación (400 Bad Request)
        logger.warning(f"Error de validación en búsqueda: {e}")
        
        # Registrar error en bitácora
        await similarity_audit_service.registrar_busqueda_similares(
            db=db,
            usuario_id=current_user["user_id"],
            modo_busqueda=data.modo_busqueda,
            texto_consulta=data.texto_consulta,
            numero_expediente=data.numero_expediente,
            limite=data.limite,
            umbral_similitud=data.umbral_similitud,
            exito=False,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
        
    except Exception as e:
        # Errores internos del servidor (500 Internal Server Error)
        logger.error(f"Error interno en búsqueda: {e}", exc_info=True)
        
        # Registrar error en bitácora
        await similarity_audit_service.registrar_busqueda_similares(
            db=db,
            usuario_id=current_user["user_id"],
            modo_busqueda=data.modo_busqueda,
            texto_consulta=data.texto_consulta,
            numero_expediente=data.numero_expediente,
            limite=data.limite,
            umbral_similitud=data.umbral_similitud,
            exito=False,
            error=f"Error interno del servidor: {str(e)}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno del servidor al realizar la búsqueda"
        )


@router.post("/generate-summary", response_model=RespuestaGenerarResumen)
async def generate_case_summary(
    data: GenerateResumenRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
) -> RespuestaGenerarResumen:
    """Generar resumen de IA para un expediente específico."""
    try:
        similarity_service = SimilarityService()
        result = await similarity_service.generate_case_summary(data.numero_expediente)
        
        # Registrar generación de resumen exitosa en bitácora
        await similarity_audit_service.registrar_resumen_ia(
            db=db,
            usuario_id=current_user["user_id"],
            numero_expediente=data.numero_expediente,
            exito=True,
            resultado={
                "total_documentos_analizados": result.total_documentos_analizados,
                "tiempo_generacion_segundos": result.tiempo_generacion_segundos,
                "resumen_ia": {
                    "resumen": result.resumen_ia.resumen if result.resumen_ia else "",
                    "palabras_clave": result.resumen_ia.palabras_clave if result.resumen_ia else [],
                    "factores_similitud": result.resumen_ia.factores_similitud if result.resumen_ia else [],
                    "conclusion": result.resumen_ia.conclusion if result.resumen_ia else ""
                }
            }
        )
        
        return result
        
    except ValueError as e:
        # Errores de validación (400 Bad Request)
        logger.warning(f"Error de validación en resumen: {e}")
        
        # Registrar error en bitácora
        await similarity_audit_service.registrar_resumen_ia(
            db=db,
            usuario_id=current_user["user_id"],
            numero_expediente=data.numero_expediente,
            exito=False,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
        
    except Exception as e:
        # Errores internos del servidor (500 Internal Server Error)
        logger.error(f"Error interno en resumen: {e}", exc_info=True)
        
        # Registrar error en bitácora
        await similarity_audit_service.registrar_resumen_ia(
            db=db,
            usuario_id=current_user["user_id"],
            numero_expediente=data.numero_expediente,
            exito=False,
            error=f"Error interno del servidor: {str(e)}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error interno del servidor al generar el resumen"
        )
