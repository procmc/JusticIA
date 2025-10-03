# 🔗 Mapa de Conexiones de Archivos - Asistente JusticIA

## 📊 Diagrama de Conexiones Principal

```
┌─────────────────────────────────────────────────────────────────┐
│                           FRONTEND                              │
├─────────────────────────────────────────────────────────────────┤
│  📄 pages/consulta-datos/chat/index.js                        │
│           │                                                     │
│           ▼                                                     │
│  🧩 components/consulta-datos/chat/Chat.jsx ◄──────────────────┐│
│           │                                                    ││
│           ├── MessageList.jsx                                  ││
│           ├── ChatInput.jsx                                    ││
│           ├── SearchScopeSelector.jsx                          ││
│           └── ConversationHistory.jsx                          ││
│           │                                                    ││
│           ▼                                                    ││
│  🔧 hooks/conversacion/useChatContext.js ◄────────────────────┘│
│           │                                                     │
│           ▼                                                     │
│  📡 services/consultaService.js                                │
│           │                                                     │
│           ├── httpService.js (dependencia)                     │
│           │                                                     │
│           ▼ POST /rag/consulta-general-stream                   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼ HTTP Request
┌─────────────────────────────────────────────────────────────────┐
│                          BACKEND                                │
├─────────────────────────────────────────────────────────────────┤
│  🛣️  app/routes/rag.py                                         │
│           │                                                     │
│           ├── Valida entrada                                   │
│           ├── Extrae contexto                                  │
│           ├── Detecta expedientes                              │
│           │                                                     │
│           ▼                                                     │
│  ⚙️  app/services/RAG/rag_chain_service.py                     │
│           │                                                     │
│           ├── Analiza intención                                │
│           ├── Calcula parámetros                               │
│           │                                                     │
│           ▼                                                     │
│  🔍 app/services/RAG/retriever.py                              │
│           │                                                     │
│           ├── Búsqueda vectorial                               │
│           ├── Resolución contextual                            │
│           ├── Filtrado por expediente                          │
│           │                                                     │
│           ▼ search_by_text() / get_expedient_documents()        │
│  💾 app/vectorstore/vectorstore.py                             │
│           │                                                     │
│           ├── 🗄️  Milvus Vector DB                             │
│           └── 🗄️  PostgreSQL                                   │
│           │                                                     │
│           ▼ documentos relevantes                               │
│  📝 app/services/RAG/context_formatter.py                      │
│           │                                                     │
│           ├── Formatea documentos                              │
│           ├── Extrae fuentes                                   │
│           │                                                     │
│           ▼                                                     │
│  🏗️  app/services/RAG/prompt_builder.py                       │
│           │                                                     │
│           ├── Combina: pregunta + contexto + historial         │
│           │                                                     │
│           ▼                                                     │
│  🤖 app/llm/llm_service.py                                     │
│           │                                                     │
│           ├── Conecta con Ollama                               │
│           ├── Streaming response                               │
│           │                                                     │
│           ▼ Server-Sent Events                                  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼ Streaming Response
┌─────────────────────────────────────────────────────────────────┐
│                    RESPUESTA AL USUARIO                        │
│                                                                 │
│  Frontend recibe chunks → actualiza UI → muestra respuesta     │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Archivos por Categoría y Sus Conexiones

### 🎨 **FRONTEND - Interfaz de Usuario**

#### **1. Página Principal**
```
📄 pages/consulta-datos/chat/index.js
└── 🧩 components/consulta-datos/chat/Chat.jsx
```

#### **2. Componente Principal del Chat**
```
🧩 components/consulta-datos/chat/Chat.jsx
├── 📨 MessageList.jsx (renderiza mensajes)
├── ⌨️  ChatInput.jsx (input del usuario)  
├── 🎛️  SearchScopeSelector.jsx (general/específico)
├── 📚 ConversationHistory.jsx (historial)
├── 🔧 hooks/conversacion/useChatContext.js (contexto)
└── 📡 services/consultaService.js (API calls)
```

#### **3. Servicios de Comunicación**
```
📡 services/consultaService.js
├── 🌐 httpService.js (HTTP client base)
└── POST → /rag/consulta-general-stream
```

#### **4. Hook de Contexto**
```
🔧 hooks/conversacion/useChatContext.js
├── addToContext() - Agregar intercambio
├── getFormattedContext() - Formatear para backend
├── clearContext() - Limpiar historial
└── hasContext() - Verificar si hay contexto
```

### ⚙️ **BACKEND - API y Procesamiento**

#### **1. Ruta Principal**
```
🛣️ app/routes/rag.py
├── @router.post("/consulta-general-stream")
├── validate_user_input() → app/utils/security_validator.py
└── get_rag_service() → app/services/RAG/rag_chain_service.py
```

#### **2. Orquestador RAG**
```
⚙️ app/services/RAG/rag_chain_service.py
├── consulta_general_streaming()
├── responder_solo_con_contexto()
├── 🔍 retriever.py (búsqueda)
├── 📝 context_formatter.py (formateo)
├── 🏗️ prompt_builder.py (construcción prompt)
└── 🤖 app/llm/llm_service.py (LLM)
```

#### **3. Sistema de Búsqueda (Retriever)**
```
🔍 app/services/RAG/retriever.py
├── DynamicJusticIARetriever
├── _aget_relevant_documents()
├── 💾 app/vectorstore/vectorstore.py
│   ├── search_by_text() (búsqueda general)
│   └── get_expedient_documents() (búsqueda específica)
└── 🧠 app/services/context_analyzer.py (análisis intención)
```

#### **4. Base de Datos Vectorial**
```
💾 app/vectorstore/vectorstore.py
├── 🗄️ Milvus Vector Database (embeddings)
├── 🗄️ PostgreSQL (metadatos)
├── search_by_text() - Búsqueda semántica
├── get_expedient_documents() - Docs por expediente
└── similarity_search() - Búsqueda por similitud
```

#### **5. Formateo y Construcción**
```
📝 app/services/RAG/context_formatter.py
├── format_documents_context_adaptive()
├── calculate_optimal_retrieval_params()
├── extract_document_sources()
└── extract_unique_expedientes()

🏗️ app/services/RAG/prompt_builder.py
├── create_justicia_prompt()
├── Combina: pregunta + contexto recuperado + historial
└── Aplica plantilla específica para derecho costarricense
```

#### **6. Servicio LLM**
```
🤖 app/llm/llm_service.py
├── get_llm() - Singleton Ollama
├── consulta_general_streaming() - Streaming response
├── 🔗 Ollama API (modelo local)
└── StreamingResponse → Frontend
```

## 🔄 Flujo de Datos Detallado

### **Consulta General**
```
1. Usuario escribe → Chat.jsx
2. Chat.jsx → useChatContext.js (obtener historial)
3. Chat.jsx → consultaService.js
4. consultaService.js → POST /rag/consulta-general-stream
5. rag.py → validate_user_input()
6. rag.py → rag_chain_service.py
7. rag_chain_service.py → retriever.py
8. retriever.py → vectorstore.py → Milvus/PostgreSQL
9. vectorstore.py → documentos relevantes → retriever.py
10. retriever.py → context_formatter.py
11. context_formatter.py → prompt_builder.py
12. prompt_builder.py → llm_service.py
13. llm_service.py → Ollama → streaming chunks
14. Chunks → rag.py → consultaService.js → Chat.jsx → Usuario
```

### **Consulta Específica por Expediente**
```
1. Usuario → "2022-063557-6597-LA" → Chat.jsx
2. Chat.jsx → isExpedienteNumber() ✓ → setConsultedExpediente()
3. Chat.jsx → "Expediente establecido" → Usuario
4. Usuario → "¿Cuál es la bitácora?" → Chat.jsx
5. Chat.jsx → consultaService.js (con expediente_number)
6. rag.py → detecta expediente → expediente_filter
7. rag_chain_service.py → retriever.py (con filtro)
8. retriever.py → get_expedient_documents(expediente_específico)
9. Resto del flujo igual que consulta general
```

## 📋 Dependencias Críticas

### **Frontend**
```
Chat.jsx depende de:
├── useChatContext.js (contexto)
├── consultaService.js (API)
├── MessageList.jsx (UI)
├── ChatInput.jsx (UI)
└── SearchScopeSelector.jsx (UI)

consultaService.js depende de:
├── httpService.js (HTTP client)
└── Backend API /rag/consulta-general-stream

useChatContext.js depende de:
├── next-auth/react (sesión)
├── next/router (navegación)
└── localStorage/sessionStorage (persistencia)
```

### **Backend**
```
rag.py depende de:
├── rag_chain_service.py (procesamiento principal)
├── security_validator.py (validación)
└── context_analyzer.py (análisis intención)

rag_chain_service.py depende de:
├── retriever.py (búsqueda)
├── context_formatter.py (formateo)
├── prompt_builder.py (prompts)
└── llm_service.py (LLM)

retriever.py depende de:
├── vectorstore.py (base de datos)
├── context_analyzer.py (análisis)
└── Milvus + PostgreSQL

llm_service.py depende de:
├── Ollama API (modelo local)
├── config.py (configuración)
└── ChatOllama (LangChain)
```

## 🔑 Archivos Más Críticos (núcleo del sistema)

### **🎯 Top 5 Archivos Críticos:**

1. **`components/consulta-datos/chat/Chat.jsx`** - ⭐⭐⭐⭐⭐
   - Interfaz principal del usuario
   - Maneja ambas modalidades (general/específica)
   - Coordina todo el frontend

2. **`services/consultaService.js`** - ⭐⭐⭐⭐⭐
   - Punto de comunicación con backend
   - Maneja streaming y contexto
   - Crítico para funcionamiento

3. **`app/routes/rag.py`** - ⭐⭐⭐⭐⭐
   - Endpoint principal del backend
   - Validación y procesamiento inicial
   - Punto de entrada de todas las consultas

4. **`app/services/RAG/rag_chain_service.py`** - ⭐⭐⭐⭐⭐
   - Orquestador principal del RAG
   - Coordina toda la lógica de negocio
   - Núcleo del sistema inteligente

5. **`app/services/RAG/retriever.py`** - ⭐⭐⭐⭐⭐
   - Búsqueda inteligente en base de datos
   - Resolución contextual
   - Diferenciación general vs específica

### **🔧 Archivos de Soporte Importantes:**

- `hooks/conversacion/useChatContext.js` - Gestión de contexto
- `app/vectorstore/vectorstore.py` - Acceso a base de datos
- `app/llm/llm_service.py` - Interfaz con modelo de IA
- `app/services/RAG/prompt_builder.py` - Construcción de prompts
- `app/services/RAG/context_formatter.py` - Formateo de contexto

## 🧪 Archivos de Pruebas y Debugging

```
Backend Testing:
├── test_context_flow.py (flujo de contexto)
├── test_context_memory.py (memoria contextual)
└── test_contextual_retriever.py (retriever contextual)

Frontend Utils:
├── utils/chatContextUtils.js (utilidades contexto)
└── utils/debug-chat-context.js (debugging contexto)
```

---

**🎯 Este mapa muestra exactamente cómo se conectan todos los archivos del asistente JusticIA, desde que el usuario escribe hasta que recibe la respuesta.**