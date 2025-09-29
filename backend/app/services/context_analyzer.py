"""
Servicio para analizar si una consulta se refiere al contexto previo
o requiere nueva búsqueda en la base de datos.
"""
import re
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

class ContextAnalyzer:
    """Analiza consultas para determinar si requieren búsqueda en BD o solo contexto"""
    
    def __init__(self):
        # Patrones que indican referencia al contexto previo
        self.context_patterns = [
            # Referencias directas
            r'\b(el|la|los|las)\s+(primer|segundo|tercer|cuarto|quinto)\s+(caso|expediente|ejemplo)',
            r'\b(primer|segundo|tercer|cuarto|quinto)\s+(caso|expediente|ejemplo)',
            r'\b(este|ese|aquel)\s+(caso|expediente|ejemplo)',
            r'\b(el|la)\s+(anterior|mencionado|citado)',
            r'\bmás\s+(información|detalles)\s+(sobre|del|de la)',
            
            # Pronombres demostrativos
            r'\bestó[sn]?\b',
            r'\besá[sn]?\b', 
            r'\baquell[oa]s?\b',
            
            # Referencias numéricas ordinales
            r'\b(1º|2º|3º|4º|5º|primer|segundo|tercer|cuarto|quinto)\b',
            
            # Preguntas de seguimiento
            r'^\s*(y|pero|además|también|asimismo)',
            r'\b(me puedes|puedes|podrías)\s+(dar|decir|mostrar|explicar)\s+(más|mejor)',
            
            # Referencias temporales contextuales
            r'\bel\s+(que|caso|expediente)\s+(mencionaste|dijiste|mostraste)',
            r'\ben\s+(ese|este|aquel)\s+(caso|expediente)',
            
            # Patrones específicos del dominio legal
            r'\bdel\s+(expediente|caso)\s+(que\s+)?(mencionaste|dijiste|citaste)',
            r'\bsobre\s+(el|ese|este)\s+(expediente|caso)',
        ]
        
        # Patrones que indican nueva búsqueda
        self.new_search_patterns = [
            # Preguntas generales
            r'^\s*(tienes|hay|existe|conoces)\s+(conocimiento|información|casos)',
            r'^\s*(qué|cuál|cuáles|cómo|dónde|cuándo|por qué)',
            r'^\s*(busca|encuentra|muestra|lista)',
            
            # Solicitudes de información nueva
            r'\btodos\s+los\s+casos\b',
            r'\bexpedientes\s+(de|sobre|relacionados)',
            r'\bcasos\s+(similares|parecidos|relacionados)',
            
            # Números de expediente específicos (formato YYYY-NNNNNN-NNNN-XX)
            r'\b\d{4}-\d{6}-\d{4}-[A-Z]{2}\b',
        ]
        
        # Compilar patrones para eficiencia
        self.context_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.context_patterns]
        self.new_search_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.new_search_patterns]
    
    def analyze_query_intent(self, query: str, has_context: bool = False) -> Dict[str, Any]:
        """
        Analiza la intención de una consulta.
        
        Returns:
            Dict con:
            - intent: 'context_only', 'new_search', o 'hybrid'
            - confidence: float 0-1
            - reasoning: str explicando la decisión
        """
        if not query.strip():
            return {
                'intent': 'new_search',
                'confidence': 1.0,
                'reasoning': 'Consulta vacía'
            }
        
        query_clean = query.strip().lower()
        
        # Si no hay contexto previo, siempre es nueva búsqueda
        if not has_context:
            return {
                'intent': 'new_search',
                'confidence': 1.0,
                'reasoning': 'No hay contexto previo disponible'
            }
        
        # Buscar patrones de referencia al contexto
        context_matches = []
        for pattern in self.context_regex:
            matches = pattern.findall(query_clean)
            if matches:
                context_matches.extend(matches)
        
        # Buscar patrones de nueva búsqueda
        new_search_matches = []
        for pattern in self.new_search_regex:
            matches = pattern.findall(query_clean)
            if matches:
                new_search_matches.extend(matches)
        
        context_score = len(context_matches)
        new_search_score = len(new_search_matches)
        
        logger.info(f"Análisis de intención - Contexto: {context_score}, Nueva búsqueda: {new_search_score}")
        logger.info(f"Matches contexto: {context_matches}")
        logger.info(f"Matches nueva búsqueda: {new_search_matches}")
        
        # Lógica de decisión
        if context_score > 0 and new_search_score == 0:
            # Solo referencias al contexto
            confidence = min(0.9, 0.6 + (context_score * 0.1))
            return {
                'intent': 'context_only',
                'confidence': confidence,
                'reasoning': f'Detectadas {context_score} referencias al contexto previo'
            }
        elif new_search_score > 0 and context_score == 0:
            # Solo nueva búsqueda
            confidence = min(0.9, 0.6 + (new_search_score * 0.1))
            return {
                'intent': 'new_search',
                'confidence': confidence,
                'reasoning': f'Detectados {new_search_score} indicadores de nueva búsqueda'
            }
        elif context_score > 0 and new_search_score > 0:
            # Ambos tipos - decidir por mayoría
            if context_score > new_search_score:
                return {
                    'intent': 'context_only',
                    'confidence': 0.7,
                    'reasoning': f'Más referencias a contexto ({context_score}) que nueva búsqueda ({new_search_score})'
                }
            else:
                return {
                    'intent': 'new_search',
                    'confidence': 0.7,
                    'reasoning': f'Más indicadores de nueva búsqueda ({new_search_score}) que contexto ({context_score})'
                }
        else:
            # Sin patrones claros - heurísticas adicionales
            return self._fallback_analysis(query_clean)
    
    def _fallback_analysis(self, query: str) -> Dict[str, Any]:
        """Análisis de fallback cuando no hay patrones claros"""
        
        # Heurísticas adicionales
        if len(query.split()) <= 3:
            # Preguntas muy cortas tienden a ser referencias al contexto
            return {
                'intent': 'context_only',
                'confidence': 0.6,
                'reasoning': 'Consulta muy corta, probablemente referencia al contexto'
            }
        
        # Buscar palabras clave de seguimiento
        followup_words = ['más', 'detalles', 'información', 'específico', 'particular']
        if any(word in query for word in followup_words):
            return {
                'intent': 'context_only',
                'confidence': 0.65,
                'reasoning': 'Contiene palabras de seguimiento típicas del contexto'
            }
        
        # Por defecto, nueva búsqueda
        return {
            'intent': 'new_search',
            'confidence': 0.5,
            'reasoning': 'Sin patrones claros, por defecto nueva búsqueda'
        }

# Instancia global
context_analyzer = ContextAnalyzer()