"""
Construcción de prompts para JusticIA
"""
import os

def load_system_prompt():
    """Carga el system prompt desde archivo"""
    try:
        system_prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "config", "system_prompt.txt"
        )
        with open(system_prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except:
        return "Eres JusticIA, asistente virtual especializado en documentos legales del Poder Judicial de Costa Rica."

def create_justicia_prompt(pregunta: str, context: str = "", conversation_context: str = "") -> str:
    """Crea el prompt completo para JusticIA"""
    
    # Detectar saludos simples
    is_greeting = pregunta.lower().strip() in [
        "hola", "buenos días", "buenas tardes", "buenas noches", 
        "¿cómo estás?", "hola!", "hi", "hello"
    ]
    
    prompt_parts = []
    
    # Instrucciones especiales para saludos
    if is_greeting:
        if conversation_context:
            prompt_parts.append("INSTRUCCIÓN: Saluda familiarmente sin buscar expedientes.")
        else:
            prompt_parts.append("INSTRUCCIÓN: Preséntate como JusticIA sin buscar expedientes.")
    
    # System prompt base
    prompt_parts.append(load_system_prompt())
    
    # Historial si existe
    if conversation_context:
        prompt_parts.append(f"HISTORIAL DE CONVERSACIÓN PREVIA:\n{conversation_context}")
    
    # Expedientes solo para consultas no-saludo
    if context and not is_greeting:
        prompt_parts.append(f"EXPEDIENTES DISPONIBLES:\n{context}")
    
    # Consulta del usuario
    prompt_parts.append(f"CONSULTA: {pregunta}")
    
    return "\n\n".join(prompt_parts)