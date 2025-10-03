"""
Servicio para analizar si una consulta se refiere al contexto previo
o requiere nueva búsqueda en la base de datos.
Enfoque inspirado en ChatGPT: análisis semántico flexible.
"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ContextAnalyzer:
    """Analiza consultas usando heurísticas semánticas flexibles como ChatGPT"""
    
    def __init__(self):
        # Palabras que típicamente indican referencia al contexto
        self.context_indicators = {
            'pronouns': ['este', 'ese', 'esta', 'esa', 'esto', 'eso', 'aquí', 'ahí'],
            'temporal': ['último', 'anterior', 'reciente', 'previo', 'previa'],
            'definite_articles': ['el caso', 'la consulta', 'el expediente', 'el documento'],
            'continuations': ['y', 'además', 'también', 'pero', 'sin embargo', 'aunque']
        }
        
        # Palabras que típicamente indican nueva búsqueda
        self.new_search_indicators = {
            'question_words': ['qué', 'cuál', 'cuáles', 'cómo', 'dónde', 'cuándo', 'por qué', 'para qué'],
            'search_verbs': ['busca', 'encuentra', 'muestra', 'lista', 'dame', 'quiero'],
            'existence_queries': ['hay', 'existe', 'tienes', 'conoces'],
            'general_terms': ['todos', 'algunos', 'varios', 'casos', 'expedientes']
        }
    
    def analyze_query_intent(self, query: str, has_context: bool = False) -> Dict[str, Any]:
        """
        Analiza la intención usando heurísticas semánticas flexibles.
        Similar al enfoque de ChatGPT para entender el contexto conversacional.
        """
        if not query.strip():
            return self._create_result('new_search', 1.0, 'Consulta vacía')
        
        # Si no hay contexto previo, siempre es nueva búsqueda
        if not has_context:
            return self._create_result('new_search', 1.0, 'Sin contexto previo')
        
        query_clean = query.strip().lower()
        
        # Análisis semántico basado en múltiples señales
        context_signals = self._analyze_context_signals(query_clean)
        search_signals = self._analyze_search_signals(query_clean)
        conversation_flow = self._analyze_conversation_flow(query_clean)
        
        # Decisión basada en señales combinadas
        return self._make_decision(context_signals, search_signals, conversation_flow, query_clean)
    
    def _analyze_context_signals(self, query: str) -> Dict[str, Any]:
        """Analiza señales que indican referencia al contexto"""
        signals = {
            'pronoun_count': 0,
            'temporal_count': 0,
            'definite_references': 0,
            'continuation_words': 0,
            'total_score': 0.0
        }
        
        # Contar pronombres demostrativos
        for pronoun in self.context_indicators['pronouns']:
            if pronoun in query:
                signals['pronoun_count'] += query.count(pronoun)
        
        # Contar referencias temporales
        for temporal in self.context_indicators['temporal']:
            if temporal in query:
                signals['temporal_count'] += query.count(temporal)
        
        # Contar artículos definidos + sustantivos específicos
        for definite in self.context_indicators['definite_articles']:
            if definite in query:
                signals['definite_references'] += 1
        
        # Contar palabras de continuación (especialmente al inicio)
        query_start = query[:20]  # Primeras 20 caracteres
        for continuation in self.context_indicators['continuations']:
            if query_start.startswith(continuation):
                signals['continuation_words'] += 2  # Más peso si está al inicio
            elif continuation in query:
                signals['continuation_words'] += 1
        
        signals['total_score'] = (
            signals['pronoun_count'] * 2 +
            signals['temporal_count'] * 2 +
            signals['definite_references'] * 1.5 +
            signals['continuation_words'] * 1
        )
        
        return signals
    
    def _analyze_search_signals(self, query: str) -> Dict[str, Any]:
        """Analiza señales que indican nueva búsqueda"""
        signals = {
            'question_words': 0,
            'search_verbs': 0,
            'existence_queries': 0,
            'general_terms': 0,
            'total_score': 0.0
        }
        
        # Palabras interrogativas (más peso si están al inicio)
        query_start = query[:30]
        for q_word in self.new_search_indicators['question_words']:
            if query_start.startswith(q_word):
                signals['question_words'] += 2
            elif q_word in query:
                signals['question_words'] += 1
        
        # Verbos de búsqueda
        for verb in self.new_search_indicators['search_verbs']:
            if verb in query:
                signals['search_verbs'] += query.count(verb)
        
        # Consultas de existencia
        for existence in self.new_search_indicators['existence_queries']:
            if existence in query:
                signals['existence_queries'] += 1
        
        # Términos generales
        for general in self.new_search_indicators['general_terms']:
            if general in query:
                signals['general_terms'] += 1
        
        signals['total_score'] = (
            signals['question_words'] * 1.5 +
            signals['search_verbs'] * 2 +
            signals['existence_queries'] * 1.5 +
            signals['general_terms'] * 1
        )
        
        return signals
    
    def _analyze_conversation_flow(self, query: str) -> Dict[str, Any]:
        """Analiza el flujo conversacional para determinar continuidad"""
        flow_signals = {
            'is_follow_up': False,
            'is_clarification': False,
            'is_elaboration': False,
            'confidence': 0.0
        }
        
        # Patrones de seguimiento
        follow_up_patterns = [
            r'^(y|pero|además|también|asimismo)',
            r'(más|otro|otra)\s+(información|detalle|pregunta)',
            r'(me puedes|puedes|podrías)\s+(decir|explicar|dar)',
        ]
        
        for pattern in follow_up_patterns:
            if re.search(pattern, query):
                flow_signals['is_follow_up'] = True
                flow_signals['confidence'] += 0.3
        
        # Patrones de clarificación
        clarification_patterns = [
            r'(qué significa|que es|cómo se|por qué)',
            r'(explica|aclara|especifica)',
            r'(no entiendo|no comprendo)',
        ]
        
        for pattern in clarification_patterns:
            if re.search(pattern, query):
                flow_signals['is_clarification'] = True
                flow_signals['confidence'] += 0.2
        
        # Patrones de elaboración
        elaboration_patterns = [
            r'(detalle|detalla|amplía|profundiza)',
            r'(más información|más detalles)',
            r'(completo|completa|todo sobre)',
        ]
        
        for pattern in elaboration_patterns:
            if re.search(pattern, query):
                flow_signals['is_elaboration'] = True
                flow_signals['confidence'] += 0.4
        
        return flow_signals
    
    def _make_decision(self, context_signals: Dict, search_signals: Dict, 
                      conversation_flow: Dict, query: str) -> Dict[str, Any]:
        """Toma la decisión final basada en todas las señales"""
        
        context_score = context_signals['total_score']
        search_score = search_signals['total_score']
        flow_score = conversation_flow['confidence']
        
        # Logging para debugging
        logger.info(f"Análisis de señales - Contexto: {context_score}, Búsqueda: {search_score}, Flujo: {flow_score}")
        
        # Decisión con lógica flexible
        if conversation_flow['is_elaboration'] and context_score > 0:
            # Si es elaboración con referencias contextuales, podría necesitar búsqueda BD
            return self._create_result('new_search', 0.8, 
                                     'Elaboración que requiere información detallada')
        
        elif context_score > search_score and (context_score > 2 or flow_score > 0.3):
            # Fuerte indicación de referencia al contexto
            confidence = min(0.9, 0.6 + (context_score * 0.1) + flow_score)
            return self._create_result('context_only', confidence, 
                                     f'Referencias contextuales dominantes (score: {context_score})')
        
        elif search_score > context_score and search_score > 2:
            # Fuerte indicación de nueva búsqueda
            confidence = min(0.9, 0.6 + (search_score * 0.1))
            return self._create_result('new_search', confidence,
                                     f'Indicadores de búsqueda dominantes (score: {search_score})')
        
        else:
            # Caso ambiguo - usar heurísticas adicionales
            return self._fallback_decision(query, context_score, search_score)
    
    def _fallback_decision(self, query: str, context_score: float, search_score: float) -> Dict[str, Any]:
        """Decisión de fallback para casos ambiguos"""
        
        # Heurísticas simples
        word_count = len(query.split())
        
        if word_count <= 3 and any(word in query for word in ['sí', 'no', 'bien', 'ok', 'gracias']):
            return self._create_result('context_only', 0.7, 'Respuesta corta conversacional')
        
        elif word_count <= 5 and context_score > 0:
            return self._create_result('context_only', 0.6, 'Pregunta corta con referencias contextuales')
        
        elif '?' in query and search_score == 0:
            return self._create_result('context_only', 0.5, 'Pregunta simple sin indicadores de búsqueda')
        
        else:
            return self._create_result('new_search', 0.5, 'Caso ambiguo - default a nueva búsqueda')
    
    def _create_result(self, intent: str, confidence: float, reasoning: str) -> Dict[str, Any]:
        """Crea un resultado estandarizado"""
        return {
            'intent': intent,
            'confidence': confidence,
            'reasoning': reasoning
        }

# Instancia global para mantener compatibilidad con importaciones existentes
context_analyzer = ContextAnalyzer()