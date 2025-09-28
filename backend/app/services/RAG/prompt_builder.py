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
    """Crea el prompt completo para JusticIA con validaciones anti-alucinación"""
    
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
        print(f"📋 Contexto recibido en prompt_builder: {len(conversation_context)} caracteres")
        print(f"📋 Primeros 200 caracteres del contexto: {conversation_context[:200]}...")
        prompt_parts.append(f"HISTORIAL DE CONVERSACIÓN PREVIA:\n{conversation_context}")
    
    # Expedientes solo para consultas no-saludo con validación
    if context and not is_greeting:
        # Validar que hay contenido relevante
        if len(context.strip()) > 50:  # Mínimo de contenido
            prompt_parts.append(f"EXPEDIENTES DISPONIBLES:\n{context}")
        else:
            # Si hay muy poco contexto, agregar advertencia
            prompt_parts.append("EXPEDIENTES DISPONIBLES: [CONTEXTO LIMITADO - SÉ ESPECÍFICO SI NO HAY INFORMACIÓN RELEVANTE]")
    elif not is_greeting and not context.strip():
        # No hay contexto para consulta legal - instrucción específica
        prompt_parts.append("INSTRUCCIÓN CRÍTICA: No hay documentos disponibles para esta consulta. Responde que no encuentras información sobre el tema solicitado y sugiere reformular la pregunta o verificar que el tema esté en la base de datos.")
    
    # Consulta del usuario con validación final
    prompt_parts.append(f"CONSULTA: {pregunta}")
    
    # Recordatorio final anti-alucinación
    if not is_greeting:
        prompt_parts.append("🚨 RECORDATORIO: SOLO usa información del contexto proporcionado. Si no hay información relevante sobre la consulta específica, di claramente que no encuentras información sobre ese tema.")
    
    return "\n\n".join(prompt_parts)