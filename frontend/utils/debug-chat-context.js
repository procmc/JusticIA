/**
 * Utilidad para depurar el contexto de conversación en el navegador
 * Ejecutar en la consola del navegador para verificar el estado del contexto
 */

// Función para inspeccionar el localStorage del contexto
function debugChatContext() {
    console.log('🔍 DEBUGGING CHAT CONTEXT');
    console.log('========================');
    
    // Buscar todas las claves relacionadas con el chat
    const chatKeys = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && (key.includes('chat_') || key.includes('conversation') || key.includes('context'))) {
            chatKeys.push(key);
        }
    }
    
    console.log(`📋 Claves encontradas en localStorage: ${chatKeys.length}`);
    chatKeys.forEach(key => {
        console.log(`🔑 ${key}`);
    });
    
    // Analizar el contenido de cada clave
    chatKeys.forEach(key => {
        try {
            const value = localStorage.getItem(key);
            if (value) {
                console.log(`\n📂 Contenido de ${key}:`);
                
                if (key.includes('conversations')) {
                    // Lista de conversaciones
                    const conversations = JSON.parse(value);
                    console.log(`   💬 Conversaciones: ${conversations.length}`);
                    conversations.forEach((conv, i) => {
                        console.log(`   ${i + 1}. ID: ${conv.id}, Mensajes: ${conv.messageCount}, Última actualización: ${conv.lastUpdated}`);
                    });
                } else if (key.includes('context')) {
                    // Contexto de una conversación específica
                    const context = JSON.parse(value);
                    console.log(`   🗨️ Intercambios en contexto: ${context.length}`);
                    context.forEach((entry, i) => {
                        console.log(`   ${i + 1}. Usuario: "${entry.userMessage.substring(0, 50)}..."`);
                        console.log(`      Asistente: ${entry.assistantResponse.length} caracteres`);
                        console.log(`      Timestamp: ${entry.timestamp}`);
                    });
                } else {
                    // Otros datos
                    console.log(`   📄 Contenido (${value.length} chars): ${value.substring(0, 100)}...`);
                }
            }
        } catch (error) {
            console.error(`❌ Error parseando ${key}:`, error);
        }
    });
    
    return chatKeys;
}

// Función para limpiar el contexto (útil para pruebas)
function clearChatContext() {
    console.log('🧹 Limpiando contexto de chat...');
    
    const chatKeys = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && (key.includes('chat_') || key.includes('conversation') || key.includes('context'))) {
            chatKeys.push(key);
        }
    }
    
    chatKeys.forEach(key => {
        localStorage.removeItem(key);
        console.log(`🗑️ Eliminado: ${key}`);
    });
    
    console.log(`✅ ${chatKeys.length} claves eliminadas`);
    return chatKeys.length;
}

// Función para simular el guardado de contexto
function simulateContextSave(userMessage, assistantResponse) {
    console.log('🧪 Simulando guardado de contexto...');
    
    const mockEntry = {
        id: Date.now(),
        userMessage: userMessage,
        assistantResponse: assistantResponse,
        timestamp: new Date().toISOString(),
        conversationId: 'test_conversation_123'
    };
    
    // Simular la lógica del hook
    const key = 'chat_user_test_context_test_conversation_123';
    const existing = localStorage.getItem(key);
    let context = existing ? JSON.parse(existing) : [];
    
    context.push(mockEntry);
    context = context.slice(-15); // Mantener últimos 15
    
    localStorage.setItem(key, JSON.stringify(context));
    
    console.log('✅ Contexto simulado guardado');
    console.log('📊 Estado actual:', context.length, 'intercambios');
    
    return mockEntry;
}

// Función para verificar el formato del contexto para envío
function testContextFormatting() {
    console.log('🧪 Probando formateo de contexto...');
    
    // Buscar contexto existente
    const contextKeys = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.includes('context')) {
            contextKeys.push(key);
        }
    }
    
    if (contextKeys.length === 0) {
        console.log('❌ No hay contexto para probar');
        return;
    }
    
    const key = contextKeys[0];
    const context = JSON.parse(localStorage.getItem(key));
    
    if (context.length === 0) {
        console.log('❌ Contexto vacío');
        return;
    }
    
    // Simular el formateo del hook
    const contextLines = ['HISTORIAL DE CONVERSACIÓN PREVIA:'];
    const recentHistory = context.slice(-4);
    
    recentHistory.forEach((entry, index) => {
        contextLines.push(`\n[Intercambio ${index + 1}]`);
        contextLines.push(`Usuario: ${entry.userMessage}`);
        
        const response = entry.assistantResponse.length > 5000 
            ? entry.assistantResponse.substring(0, 5000) + '...[respuesta truncada - contenido adicional disponible]'
            : entry.assistantResponse;
        
        contextLines.push(`Asistente: ${response}`);
    });
    
    contextLines.push('\n---\nNUEVA CONSULTA:');
    const formattedContext = contextLines.join('\n');
    
    console.log('📤 Contexto formateado:');
    console.log(`   📏 Tamaño: ${formattedContext.length} caracteres`);
    console.log(`   📊 Intercambios incluidos: ${recentHistory.length}`);
    console.log(`   📋 Vista previa: ${formattedContext.substring(0, 500)}...`);
    
    return formattedContext;
}

// Exportar funciones para uso global
window.debugChatContext = debugChatContext;
window.clearChatContext = clearChatContext;
window.simulateContextSave = simulateContextSave;
window.testContextFormatting = testContextFormatting;

console.log('🛠️ Utilidades de debug cargadas:');
console.log('   - debugChatContext(): Inspeccionar estado actual');
console.log('   - clearChatContext(): Limpiar todo el contexto');
console.log('   - simulateContextSave(userMsg, assistantMsg): Simular guardado');
console.log('   - testContextFormatting(): Probar formateo para backend');