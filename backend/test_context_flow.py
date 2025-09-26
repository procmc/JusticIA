#!/usr/bin/env python3
"""
Script de prueba para verificar el manejo del contexto en JusticIA
Permite probar el flujo completo de contexto desde frontend hasta backend
"""

import json
import requests
import time

# Configuración
BACKEND_URL = "http://localhost:8000"
FRONTEND_CONTEXT_SIMULATION = {
    "user_messages": [
        "¿Cuáles son los expedientes de familia disponibles?",
        "¿Qué información contiene el primer expediente mencionado?",
        "¿Hay otros expedientes similares relacionados con el mismo tema?"
    ]
}

def simulate_conversation_context(messages_history):
    """Simula el contexto de conversación como lo haría el frontend"""
    context_lines = ['HISTORIAL DE CONVERSACIÓN PREVIA:']
    
    for i, entry in enumerate(messages_history, 1):
        context_lines.append(f'\n[Intercambio {i}]')
        context_lines.append(f'Usuario: {entry["user"]}')
        context_lines.append(f'Asistente: {entry["assistant"]}')
    
    context_lines.append('\n---\nNUEVA CONSULTA:')
    return '\n'.join(context_lines)

def test_context_flow():
    """Prueba el flujo completo de contexto"""
    print("🧪 Iniciando prueba de contexto...")
    conversation_history = []
    
    for i, user_message in enumerate(FRONTEND_CONTEXT_SIMULATION["user_messages"]):
        print(f"\n{'='*60}")
        print(f"📝 Pregunta {i+1}: {user_message}")
        
        # Simular el contexto como lo haría el frontend
        if conversation_history:
            context = simulate_conversation_context(conversation_history)
            full_query = f"{context}\n{user_message}"
            has_context = True
            print(f"📋 Enviando con contexto ({len(context)} caracteres)")
        else:
            full_query = user_message
            has_context = False
            print("📋 Primera pregunta - sin contexto")
        
        # Hacer la request al backend
        try:
            response = requests.post(
                f"{BACKEND_URL}/rag/consulta-general-stream",
                json={
                    "query": full_query,
                    "top_k": 5,
                    "has_context": has_context
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                # Simular la recepción de streaming (tomar solo los primeros chunks)
                assistant_response = ""
                lines = response.text.split('\n')
                for line in lines[:10]:  # Limitar para prueba
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if data.get('type') == 'chunk':
                                assistant_response += data.get('content', '')
                        except:
                            continue
                
                if assistant_response:
                    print(f"✅ Respuesta recibida ({len(assistant_response)} caracteres)")
                    print(f"📤 Respuesta: {assistant_response[:200]}...")
                    
                    # Agregar al historial para la siguiente iteración
                    conversation_history.append({
                        "user": user_message,
                        "assistant": assistant_response
                    })
                else:
                    print("❌ No se recibió respuesta válida")
            else:
                print(f"❌ Error HTTP: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                
        except Exception as e:
            print(f"❌ Error en request: {e}")
        
        time.sleep(1)  # Pausa entre requests
    
    print(f"\n{'='*60}")
    print(f"🏁 Prueba completada. Historial final: {len(conversation_history)} intercambios")
    
    # Mostrar resumen del contexto acumulado
    if conversation_history:
        final_context = simulate_conversation_context(conversation_history)
        print(f"📊 Contexto final: {len(final_context)} caracteres")
        print(f"📋 Vista previa: {final_context[:400]}...")

if __name__ == "__main__":
    test_context_flow()