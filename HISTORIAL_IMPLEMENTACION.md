# Implementación del Historial de Conversaciones Persistente

## 📋 Resumen
Se ha implementado un sistema completo de historial de conversaciones que persiste incluso después de cerrar sesión. Las conversaciones se guardan automáticamente en archivos JSON en el servidor y se pueden restaurar en cualquier momento.

## 🎯 Características Implementadas

### 1. **Persistencia en Backend**
- ✅ Conversaciones guardadas automáticamente en `backend/data/conversations/`
- ✅ Sincronización entre memoria y disco
- ✅ Carga automática al iniciar la aplicación
- ✅ Guardado automático al cerrar la aplicación
- ✅ Guardado incremental después de cada actualización

### 2. **API Endpoints Creados**
- `GET /rag/conversations` - Lista todas las conversaciones del usuario
- `GET /rag/conversations/{session_id}` - Obtiene detalles de una conversación
- `DELETE /rag/conversations/{session_id}` - Elimina una conversación
- `POST /rag/conversations/{session_id}/restore` - Restaura una conversación desde archivo
- `GET /rag/conversations-stats` - Estadísticas del sistema (debugging)

### 3. **Frontend Mejorado**
- ✅ Hook `useBackendConversations` para gestión de historial
- ✅ Servicio `conversationService` para llamadas API
- ✅ Componente `ConversationHistory` actualizado con carga desde backend
- ✅ Restauración completa de conversaciones con contexto
- ✅ Indicadores de carga y manejo de errores

## 🏗️ Arquitectura

### Backend
```
backend/
├── app/
│   ├── services/
│   │   └── RAG/
│   │       └── session_store.py          # ⭐ Actualizado con persistencia
│   └── routes/
│       └── rag.py                         # ⭐ Nuevos endpoints de historial
├── main.py                                # ⭐ Guardado al cerrar
└── data/
    └── conversations/                     # 📁 Conversaciones guardadas
        ├── session_user@example.com_1234.json
        └── ...
```

### Frontend
```
frontend/
├── services/
│   └── conversationService.js             # ⭐ Nuevo servicio
├── hooks/
│   └── useBackendConversations.js         # ⭐ Nuevo hook
└── components/
    └── consulta-datos/
        └── chat/
            ├── Chat.jsx                   # ⭐ Restauración de conversaciones
            └── ConversationHistory.jsx    # ⭐ UI actualizada
```

## 📝 Formato de Archivo JSON

Cada conversación se guarda con la siguiente estructura:

```json
{
  "metadata": {
    "session_id": "session_user@example.com_1760428318814",
    "user_id": "user@example.com",
    "created_at": "2025-10-14T07:52:08.311779",
    "updated_at": "2025-10-14T07:52:37.788082",
    "title": "hola",
    "message_count": 4,
    "expediente_number": null
  },
  "messages": [
    {
      "type": "human",
      "content": "hola",
      "timestamp": "2025-10-14T07:52:47.214151"
    },
    {
      "type": "ai",
      "content": "¡Hola! ¿En qué puedo ayudarte hoy?",
      "timestamp": "2025-10-14T07:52:47.214179"
    }
  ]
}
```

## 🔄 Flujo de Funcionamiento

### 1. **Al Iniciar la Aplicación**
```
1. Backend carga → session_store.__init__()
2. Lee todos los .json → _load_all_conversations()
3. Reconstruye índices de usuarios y metadatos
```

### 2. **Durante una Conversación**
```
1. Usuario envía mensaje → RAG procesa
2. Respuesta generada → Guardada en memoria
3. Metadata actualizada → update_metadata()
4. Archivo JSON actualizado → _save_conversation_to_file()
```

### 3. **Al Cerrar la Aplicación**
```
1. Evento shutdown → main.py
2. Guarda todas las conversaciones → save_all_conversations()
3. Archivos JSON sincronizados
```

### 4. **Restaurar Conversación**
```
Frontend                          Backend
   │                                 │
   ├─ Click en historial ─────────> │
   │                                 │
   │ <─── Lista conversaciones ───── ├─ GET /conversations
   │                                 │
   ├─ Click en conversación ──────> │
   │                                 │
   │ <──── Detalles + mensajes ───── ├─ GET /conversations/{id}
   │                                 │
   └─ Renderiza mensajes            │
```

## 🔧 Cambios Clave por Archivo

### `backend/app/services/RAG/session_store.py`
- ✨ Importación de `json`, `os`, `Path`
- ✨ Constante `CONVERSATIONS_DIR`
- ✨ Métodos nuevos:
  - `_get_conversation_file_path()`
  - `_save_conversation_to_file()`
  - `_load_conversation_from_file()`
  - `_load_all_conversations()`
  - `save_all_conversations()`
- 🔄 Métodos actualizados:
  - `__init__()` - Carga conversaciones al iniciar
  - `update_metadata()` - Guarda al actualizar
  - `auto_generate_title()` - Guarda al generar título
  - `delete_session()` - Elimina archivo JSON

### `backend/app/routes/rag.py`
- ✨ 5 nuevos endpoints de gestión de historial
- ✨ Autenticación con `require_usuario_judicial`
- ✨ Validación de permisos por usuario

### `backend/main.py`
- ✨ Importación de `conversation_store`
- 🔄 `shutdown_event()` - Guarda conversaciones al cerrar

### `frontend/services/conversationService.js`
- ✨ Servicio completo con 5 métodos para API de historial

### `frontend/hooks/useBackendConversations.js`
- ✨ Hook personalizado para gestión de historial
- ✨ Cache de 30 segundos para evitar llamadas repetidas
- ✨ Estados de carga y errores

### `frontend/components/consulta-datos/chat/ConversationHistory.jsx`
- 🔄 Migrado de `usePersistentChatContext` a `useBackendConversations`
- ✨ Indicadores de carga mejorados
- ✨ Manejo de errores con retry
- ✨ Muestra número de expediente si está asociado

### `frontend/components/consulta-datos/chat/Chat.jsx`
- 🔄 Handler `onConversationSelect` mejorado
- ✨ Restaura mensajes completos
- ✨ Restaura contexto de expediente
- ✨ Handler `onNewConversation` para limpiar estado

## 🚀 Cómo Usar

### Para el Usuario Final

1. **Ver Historial**
   - Click en botón "Historial" en el chat
   - Se muestran todas tus conversaciones guardadas

2. **Restaurar Conversación**
   - Click en cualquier conversación del historial
   - Se cargan todos los mensajes y contexto

3. **Nueva Conversación**
   - Click en "Nueva Conversación" en el modal de historial
   - O click en el botón "Nueva" en el chat

4. **Eliminar Conversación**
   - Hover sobre una conversación
   - Click en icono de eliminar
   - Click de nuevo para confirmar

### Para Desarrolladores

```javascript
// Obtener conversaciones
import { useBackendConversations } from '@/hooks/useBackendConversations';

const { conversations, fetchConversations } = useBackendConversations();

// Cargar conversación específica
const conversation = await getConversationDetail(sessionId);

// Eliminar conversación
await deleteConversation(sessionId);
```

## ⚠️ Consideraciones Importantes

1. **Seguridad**
   - ✅ Autenticación requerida en todos los endpoints
   - ✅ Validación de permisos por usuario
   - ✅ Solo puedes acceder a tus propias conversaciones

2. **Rendimiento**
   - ✅ Carga diferida: archivos JSON se leen solo al iniciar
   - ✅ Cache en memoria durante ejecución
   - ✅ Guardado asíncrono para no bloquear

3. **Límites**
   - No hay límite de conversaciones por usuario
   - Cada archivo JSON tiene su propia conversación
   - Se recomienda limpiar conversaciones antiguas periódicamente

## 🐛 Debugging

### Ver estadísticas del sistema
```bash
curl http://localhost:8000/rag/conversations-stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Ver conversaciones guardadas
```bash
ls backend/data/conversations/
```

### Ver contenido de una conversación
```bash
cat backend/data/conversations/session_USER_TIMESTAMP.json | jq
```

## 📊 Mejoras Futuras Sugeridas

1. **Búsqueda en Historial**
   - Buscar por contenido de mensajes
   - Filtrar por fecha o expediente

2. **Exportar Conversaciones**
   - Descargar en PDF
   - Exportar a formato texto

3. **Límite de Conversaciones**
   - Política de retención (ej. 30 días)
   - Auto-archivado de conversaciones antiguas

4. **Compartir Conversaciones**
   - Compartir con otros usuarios
   - Control de permisos

## ✅ Testing

### Backend
```bash
# Iniciar backend
cd backend
python main.py

# Verificar que carga conversaciones existentes
# Debe aparecer en logs: "X conversaciones cargadas"
```

### Frontend
```bash
# Iniciar frontend
cd frontend
npm run dev

# Probar:
1. Iniciar conversación
2. Enviar varios mensajes
3. Cerrar y reabrir navegador
4. Abrir historial - debe aparecer la conversación
5. Click en conversación - debe restaurarse
```

## 📚 Documentación API

Ver documentación completa en:
```
http://localhost:8000/docs#/RAG%20-%20Consultas%20Inteligentes
```

---

**Implementado por:** GitHub Copilot  
**Fecha:** 14 de octubre de 2025  
**Estado:** ✅ Completado y funcional
