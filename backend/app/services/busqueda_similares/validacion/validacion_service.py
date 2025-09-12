"""
Servicio de validación de datos y parámetros.

Este módulo maneja la validación de entrada de datos para las operaciones
de búsqueda de similares, incluyendo parámetros y formatos de datos.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.similarity_schemas import SimilaritySearchRequest

logger = logging.getLogger(__name__)


class ValidacionService:
    """Servicio para validar datos de entrada y parámetros."""
    
    def __init__(self):
        self.max_top_k = 100
        self.min_top_k = 1
        self.max_similarity_threshold = 1.0
        self.min_similarity_threshold = 0.0
    
    def validar_solicitud_busqueda(
        self,
        request: SimilaritySearchRequest
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida una solicitud de búsqueda de similares.
        
        Args:
            request: Solicitud de búsqueda a validar
            
        Returns:
            Tupla con (es_valido, mensaje_error)
        """
        try:
            # Validar search_mode
            if request.search_mode not in ["description", "expedient"]:
                return False, "search_mode debe ser 'description' o 'expedient'"
            
            # Validar según el modo de búsqueda
            if request.search_mode == "expedient":
                if not request.expedient_number or not request.expedient_number.strip():
                    return False, "expedient_number es requerido cuando search_mode es 'expedient'"
                
                if not self._validar_formato_expedient_id(request.expedient_number):
                    return False, "Formato de expedient_number inválido"
            
            elif request.search_mode == "description":
                if not request.query_text or not request.query_text.strip():
                    return False, "query_text es requerido cuando search_mode es 'description'"
                
                if len(request.query_text) > 2000:
                    return False, "query_text no puede exceder 2000 caracteres"
            
            # Validar limit
            if request.limit is not None:
                if not isinstance(request.limit, int):
                    return False, "limit debe ser un número entero"
                
                if request.limit < 1 or request.limit > 100:
                    return False, "limit debe estar entre 1 y 100"
            
            # Validar similarity_threshold
            if request.similarity_threshold is not None:
                if not isinstance(request.similarity_threshold, (int, float)):
                    return False, "similarity_threshold debe ser un número"
                
                threshold = float(request.similarity_threshold)
                if threshold < 0.0 or threshold > 1.0:
                    return False, "similarity_threshold debe estar entre 0.0 y 1.0"
            
            expedient_ref = request.expedient_number if request.search_mode == "expedient" else "descripción"
            logger.debug(f"Solicitud de búsqueda validada exitosamente para: {expedient_ref}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error validando solicitud de búsqueda: {e}")
            return False, f"Error interno de validación: {str(e)}"
    
    def _validar_formato_expedient_id(self, expedient_id: str) -> bool:
        """
        Valida el formato del expedient_id.
        
        Args:
            expedient_id: ID del expediente a validar
            
        Returns:
            True si el formato es válido, False en caso contrario
        """
        try:
            # Patrón para IDs de expedientes (ajustar según formato real)
            # Ejemplo: "98-003287-0166-LA", "2025-CR0001-014521"
            pattern = r'^[0-9]{2,4}-[A-Z0-9]{6,8}-[0-9]{4,6}(-[A-Z]{1,2})?$'
            
            return bool(re.match(pattern, expedient_id.strip()))
            
        except Exception as e:
            logger.error(f"Error validando formato de expedient_id: {e}")
            return False
    
    def validar_parametros_embedding(
        self,
        text: str,
        max_length: int = 10000
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida parámetros para generación de embeddings.
        
        Args:
            text: Texto a validar
            max_length: Longitud máxima permitida
            
        Returns:
            Tupla con (es_valido, mensaje_error)
        """
        try:
            if not text:
                return False, "El texto no puede estar vacío"
            
            if not isinstance(text, str):
                return False, "El texto debe ser una cadena de caracteres"
            
            if len(text.strip()) == 0:
                return False, "El texto no puede contener solo espacios en blanco"
            
            if len(text) > max_length:
                return False, f"El texto excede la longitud máxima de {max_length} caracteres"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validando parámetros de embedding: {e}")
            return False, f"Error interno de validación: {str(e)}"
    
    def validar_resultados_milvus(
        self,
        results: List[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida los resultados devueltos por Milvus.
        
        Args:
            results: Lista de resultados de Milvus
            
        Returns:
            Tupla con (es_valido, mensaje_error)
        """
        try:
            if not isinstance(results, list):
                return False, "Los resultados deben ser una lista"
            
            for i, result in enumerate(results):
                if not isinstance(result, dict):
                    return False, f"Resultado {i} debe ser un diccionario"
                
                # Validar campos requeridos
                required_fields = ["expedient_id", "similarity_score"]
                for field in required_fields:
                    if field not in result:
                        return False, f"Campo requerido '{field}' faltante en resultado {i}"
                
                # Validar tipos de datos
                if not isinstance(result.get("similarity_score"), (int, float)):
                    return False, f"similarity_score en resultado {i} debe ser numérico"
                
                score = float(result["similarity_score"])
                if score < 0 or score > 1:
                    return False, f"similarity_score en resultado {i} debe estar entre 0 y 1"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validando resultados de Milvus: {e}")
            return False, f"Error interno de validación: {str(e)}"
    
    def validar_datos_expediente(
        self,
        expedient_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida los datos de un expediente.
        
        Args:
            expedient_data: Datos del expediente a validar
            
        Returns:
            Tupla con (es_valido, mensaje_error)
        """
        try:
            if not isinstance(expedient_data, dict):
                return False, "Los datos del expediente deben ser un diccionario"
            
            # Validar campos esenciales
            if not expedient_data.get("expedient_id"):
                return False, "expedient_id es requerido en los datos del expediente"
            
            # Validar estructura de documentos si está presente
            documents = expedient_data.get("documents")
            if documents is not None:
                if not isinstance(documents, list):
                    return False, "Los documentos deben ser una lista"
                
                for i, doc in enumerate(documents):
                    if not isinstance(doc, dict):
                        return False, f"Documento {i} debe ser un diccionario"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validando datos del expediente: {e}")
            return False, f"Error interno de validación: {str(e)}"
    
    def sanitizar_texto(self, text: str) -> str:
        """
        Sanitiza un texto para uso seguro.
        
        Args:
            text: Texto a sanitizar
            
        Returns:
            Texto sanitizado
        """
        try:
            if not text:
                return ""
            
            # Remover caracteres de control y espacios extra
            sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
            sanitized = re.sub(r'\s+', ' ', sanitized)
            
            return sanitized.strip()
            
        except Exception as e:
            logger.error(f"Error sanitizando texto: {e}")
            return text if isinstance(text, str) else ""
    
    def obtener_limites_configurados(self) -> Dict[str, Any]:
        """
        Obtiene los límites de validación configurados.
        
        Returns:
            Diccionario con los límites configurados
        """
        return {
            "max_top_k": self.max_top_k,
            "min_top_k": self.min_top_k,
            "max_similarity_threshold": self.max_similarity_threshold,
            "min_similarity_threshold": self.min_similarity_threshold
        }
