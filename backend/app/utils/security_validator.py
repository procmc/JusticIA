"""
Módulo de seguridad y validación para JusticBot.
Implementa filtros de contenido, detección de prompt injection y validación de entradas.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class SecurityValidationResult:
    """Resultado de la validación de seguridad"""
    is_safe: bool
    risk_level: str  # 'low', 'medium', 'high'
    detected_issues: List[str]
    sanitized_text: str
    should_block: bool
    response_override: Optional[str] = None

class SecurityValidator:
    """Validador de seguridad para entradas de usuario"""
    
    def __init__(self):
        # Patrones de prompt injection
        self.injection_patterns = [
            # Intentos directos de cambio de rol
            r'(?i)(ignore|ignora|olvida|forget).*(previous|anterior|above|arriba|instruction|instrucción)',
            r'(?i)(act as|actúa como|pretend|pretende|simulate|simula|roleplay|rol)',
            r'(?i)(you are now|ahora eres|from now|a partir de ahora|new role|nuevo rol)',
            r'(?i)(system.?prompt|system.?message|configuración|configuration)',
            
            # Intentos de extracción de información del sistema
            r'(?i)(show|muestra|reveal|revela|tell me|dime).*(prompt|instruction|rule|regla)',
            r'(?i)(how.?(are|were).?you.?(made|created|trained|configured))',
            r'(?i)(what.?(is|are).?your.?(instruction|rule|prompt|configuration))',
            
            # Intentos de bypass
            r'(?i)(bypass|elude|skip|omit|omite|saltea)',
            r'(?i)(override|sobrescribe|replace|reemplaza)',
            r'(?i)(\{.*system.*\}|\[.*system.*\])',
            
            # Inyección de código
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'(?i)eval\s*\(',
            r'(?i)exec\s*\(',
        ]
        
        # Patrones de contenido inapropiado
        self.inappropriate_patterns = [
            # Lenguaje ofensivo (básico - se puede expandir)
            r'(?i)\b(idiota|estúpido|imbécil|pendejo|cabrón|hijo de puta)\b',
            r'(?i)\b(puto|puta|marica|joto|culero)\b',
            
            # Acoso o amenazas
            r'(?i)(te voy a|voy a.*tu|vas a morir|kill|matar)',
            r'(?i)(amenaza|threat|violence|violencia)',
            
            # Contenido sexual inapropiado
            r'(?i)(porn|porno|xxx|sex|sexo)(?!\w)',
        ]
        
        # Límites de entrada
        self.max_input_length = 10000  # caracteres
        self.max_repeated_chars = 50
        
    def validate_input(self, text: str) -> SecurityValidationResult:
        """
        Valida una entrada de usuario para detectar problemas de seguridad.
        
        Args:
            text: Texto a validar
            
        Returns:
            SecurityValidationResult con el análisis de seguridad
        """
        if not text:
            return SecurityValidationResult(
                is_safe=True,
                risk_level='low',
                detected_issues=[],
                sanitized_text='',
                should_block=False
            )
        
        issues = []
        risk_level = 'low'
        should_block = False
        response_override = None
        
        # 1. Verificar longitud
        if len(text) > self.max_input_length:
            issues.append('input_too_long')
            risk_level = 'medium'
            text = text[:self.max_input_length]
        
        # 2. Verificar caracteres repetidos excesivos
        if self._has_excessive_repetition(text):
            issues.append('excessive_repetition')
            risk_level = 'medium'
            text = self._clean_repetition(text)
        
        # 3. Detectar prompt injection
        injection_detected = self._detect_prompt_injection(text)
        if injection_detected:
            issues.append('prompt_injection')
            risk_level = 'high'
            should_block = True
            response_override = "Soy JusticBot, un asistente legal especializado. ¿En qué consulta jurídica puedo ayudarte?"
        
        # 4. Detectar contenido inapropiado
        inappropriate_detected = self._detect_inappropriate_content(text)
        if inappropriate_detected:
            issues.append('inappropriate_content')
            risk_level = 'high'
            should_block = True
            response_override = "Mantengo un ambiente profesional y respetuoso. ¿Puedo ayudarte con alguna consulta legal?"
        
        # 5. Sanitizar texto
        sanitized_text = self._sanitize_text(text)
        
        return SecurityValidationResult(
            is_safe=not should_block,
            risk_level=risk_level,
            detected_issues=issues,
            sanitized_text=sanitized_text,
            should_block=should_block,
            response_override=response_override
        )
    
    def _detect_prompt_injection(self, text: str) -> bool:
        """Detecta intentos de prompt injection"""
        for pattern in self.injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _detect_inappropriate_content(self, text: str) -> bool:
        """Detecta contenido inapropiado"""
        for pattern in self.inappropriate_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _has_excessive_repetition(self, text: str) -> bool:
        """Detecta repetición excesiva de caracteres"""
        # Buscar secuencias de caracteres repetidos
        for match in re.finditer(r'(.)\1{10,}', text):
            return True
        return False
    
    def _clean_repetition(self, text: str) -> str:
        """Limpia repeticiones excesivas"""
        # Reducir repeticiones de caracteres a máximo 3
        return re.sub(r'(.)\1{3,}', r'\1\1\1', text)
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitiza el texto removiendo elementos problemáticos"""
        # Remover caracteres de control peligrosos
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Remover secuencias de escape
        sanitized = re.sub(r'\\[ux][0-9a-fA-F]+', '', sanitized)
        
        # Remover HTML/XML tags
        sanitized = re.sub(r'<[^>]+>', '', sanitized)
        
        # Limpiar espacios múltiples
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    def is_legal_domain_query(self, text: str) -> bool:
        """
        Verifica si la consulta está relacionada con el dominio legal.
        Usado para redireccionar consultas fuera del ámbito.
        """
        legal_keywords = [
            'expediente', 'caso', 'juicio', 'demanda', 'sentencia', 'juzgado',
            'legal', 'jurídico', 'derecho', 'ley', 'código', 'artículo',
            'penal', 'civil', 'laboral', 'familia', 'comercial', 'administrativo',
            'tribunal', 'corte', 'audiencia', 'resolución', 'apelación',
            'recurso', 'prueba', 'testigo', 'evidencia', 'delito', 'falta',
            'contrato', 'obligación', 'responsabilidad', 'daños', 'perjuicios',
            'divorcio', 'custodia', 'alimentos', 'pensión', 'herencia',
            'sucesión', 'testamento', 'notario', 'registro', 'propiedad'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in legal_keywords)

class ContextManager:
    """Gestor de contexto para conversaciones largas"""
    
    def __init__(self, max_context_tokens: int = 4000):
        self.max_context_tokens = max_context_tokens
        
    def truncate_context(self, conversation_context: str, current_query: str) -> str:
        """
        Trunca el contexto de conversación si es demasiado largo.
        Mantiene las partes más relevantes y recientes.
        """
        if not conversation_context:
            return conversation_context
        
        # Estimación básica: ~4 caracteres por token
        estimated_tokens = len(conversation_context) / 4
        
        if estimated_tokens <= self.max_context_tokens:
            return conversation_context
        
        # Dividir en intercambios
        exchanges = self._parse_conversation(conversation_context)
        
        # Mantener solo los intercambios más recientes que quepan
        truncated_exchanges = []
        current_tokens = len(current_query) / 4
        
        for exchange in reversed(exchanges):
            exchange_tokens = len(exchange) / 4
            if current_tokens + exchange_tokens <= self.max_context_tokens:
                truncated_exchanges.insert(0, exchange)
                current_tokens += exchange_tokens
            else:
                break
        
        # Reconstruir contexto
        if truncated_exchanges:
            return "HISTORIAL DE CONVERSACIÓN PREVIA:\n" + "\n".join(truncated_exchanges)
        
        return ""
    
    def _parse_conversation(self, context: str) -> List[str]:
        """Parsea el contexto en intercambios individuales"""
        if "HISTORIAL DE CONVERSACIÓN PREVIA:" not in context:
            return [context]
        
        # Extraer solo la parte del historial
        history_part = context.split("HISTORIAL DE CONVERSACIÓN PREVIA:")[1]
        
        # Dividir por intercambios
        exchanges = re.split(r'\n\[Intercambio \d+\]', history_part)
        
        # Limpiar y filtrar intercambios vacíos
        return [exchange.strip() for exchange in exchanges if exchange.strip()]

# Instancia global del validador
security_validator = SecurityValidator()
context_manager = ContextManager()

def validate_user_input(text: str) -> SecurityValidationResult:
    """Función de conveniencia para validar entrada de usuario"""
    return security_validator.validate_input(text)

def should_redirect_off_topic(text: str) -> bool:
    """Determina si la consulta debe ser redirigida por estar fuera del tema legal"""
    if not text or len(text.strip()) < 10:
        return False
    
    # Si no contiene palabras clave legales y no es un saludo, podría estar fuera del tema
    is_greeting = any(greeting in text.lower() for greeting in ['hola', 'buenos días', 'buenas tardes', 'hi', 'hello'])
    
    if is_greeting:
        return False
    
    return not security_validator.is_legal_domain_query(text)

def get_off_topic_response() -> str:
    """Respuesta para consultas fuera del ámbito legal"""
    return """Soy JusticBot, especializado en temas legales y judiciales del sistema costarricense.

Para consultas sobre otros temas, te recomiendo contactar el servicio apropiado.

¿Puedo ayudarte con alguna consulta legal como:
• Búsqueda de expedientes
• Información sobre procesos judiciales  
• Consultas sobre derecho costarricense
• Análisis de casos similares?"""