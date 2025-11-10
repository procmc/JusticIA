import React, { useState, useRef, useEffect } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import ConversationHistory from './ConversationHistory';
import consultaService from '../../../services/consultaService';
import { useSessionId } from '../../../hooks/conversacion/useSessionId';
import { formatearSoloHoraCostaRica } from '../../../utils/dateUtils';
import {
  EXPEDIENTE_WELCOME_MESSAGE,
  isValidExpediente,
  normalizeExpediente,
  shouldChangeExpediente,
  createExpedienteMessages,
  createNoExpedienteMessage,
  createUserMessage,
  createEmptyAssistantMessage,
  createWelcomeMessage,
  createStreamingCallbacks,
  saveToSessionStorage,
  restoreFromSessionStorage,
  markMessageAsCanceled
} from '../../../utils/chat/messageUtils';

const ConsultaChat = ({ initialMode }) => {
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [streamingMessageIndex, setStreamingMessageIndex] = useState(null);
  const [isRestoringSession, setIsRestoringSession] = useState(true); // Estado para controlar la restauración
  const stopStreamingRef = useRef(false);
  const currentRequestRef = useRef(null);
  const retryCountRef = useRef(0);

  // Estados para el alcance de búsqueda
  const [searchScope, setSearchScope] = useState('general');
  const [consultedExpediente, setConsultedExpediente] = useState(null); // Para rastrear el expediente consultado

  // Efecto para manejar el modo inicial desde la URL
  useEffect(() => {
    if (initialMode === 'expediente') {
      setSearchScope('expediente');
      setMessages([createWelcomeMessage()]);
    }
  }, [initialMode]);

  // Función personalizada para cambiar el scope y limpiar cuando sea necesario
  const handleSearchScopeChange = (newScope) => {
    if (newScope !== searchScope) {
      setMessages([]);
      setConsultedExpediente(null);
      newSession();
      setSearchScope(newScope);
      setIsRestoringSession(false);

      if (newScope === 'expediente') {
        setMessages([createWelcomeMessage()]);
      }
    }
  };

  // Estado para el modal de historial
  const [showHistory, setShowHistory] = useState(false);

  // Hook para gestión de session_id (backend gestiona el historial automáticamente)
  const { sessionId, newSession, restoreSession, isReady } = useSessionId();

  // Efecto para restaurar conversación SOLO si venimos de un reload (no de navegación)
  useEffect(() => {
    if (!sessionId || !isReady) return;
    
    const restoreIfReloaded = () => {
      const restored = restoreFromSessionStorage(sessionId);
      
      if (restored) {
        setMessages(restored.messages);
        setSearchScope(restored.scope);
        if (restored.expediente) {
          setConsultedExpediente(restored.expediente);
        }
      }
      
      setIsRestoringSession(false);
    };

    restoreIfReloaded();
    
    // Cleanup: Limpiar sessionStorage al desmontar (cuando navegas a otra página)
    return () => {
      // Limpiar datos del chat cuando el componente se desmonta
      sessionStorage.removeItem('current_chat_session');
      sessionStorage.removeItem('current_chat_messages');
      sessionStorage.removeItem('current_chat_scope');
      sessionStorage.removeItem('current_chat_expediente');
    };
  }, [sessionId, isReady]);

  // Guardar el estado actual en sessionStorage cada vez que cambian los mensajes
  useEffect(() => {
    saveToSessionStorage(sessionId, messages, searchScope, consultedExpediente);
  }, [messages, sessionId, searchScope, consultedExpediente]);

  const handleStopGeneration = () => {
    stopStreamingRef.current = true;
    setIsTyping(false);
    
    const canceledMessageIndex = streamingMessageIndex;
    setStreamingMessageIndex(null);

    if (currentRequestRef.current) {
      currentRequestRef.current.active = false;
      currentRequestRef.current = null;
    }

    consultaService.cancelConsulta();

    if (canceledMessageIndex !== null) {
      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        if (updatedMessages[canceledMessageIndex]) {
          updatedMessages[canceledMessageIndex] = markMessageAsCanceled(updatedMessages[canceledMessageIndex]);
        }
        return updatedMessages;
      });
    }
  };

  const handleSendMessage = async (text) => {
    // Cancelar cualquier consulta en progreso primero
    if (currentRequestRef.current?.active) {
      stopStreamingRef.current = true;
      currentRequestRef.current.active = false;
      consultaService.cancelConsulta();
      // Esperar un poco para asegurar que la cancelación se complete
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    // Si estamos en modo expediente específico
    if (searchScope === 'expediente') {
      // Verificar si el texto es un número de expediente (nuevo o cambio de expediente)
      if (isValidExpediente(text)) {
        const newExpediente = normalizeExpediente(text);

        // Si es un expediente diferente al actual, cambiarlo
        if (shouldChangeExpediente(text, consultedExpediente)) {
          setConsultedExpediente(newExpediente);

          const { userMessage, assistantMessage } = createExpedienteMessages(
            newExpediente, 
            consultedExpediente !== null
          );

          setMessages(prev => [...prev, userMessage, assistantMessage]);

          // Actualizar el contexto en el backend
          const action = consultedExpediente ? 'change' : 'set';
          consultaService.updateExpedienteContext(sessionId, newExpediente, action)
            .catch(() => {});
          return;
        }
      }
      // Si no tenemos expediente consultado y el texto no es un número válido
      else if (!consultedExpediente) {
        const { userMessage, assistantMessage } = createNoExpedienteMessage(text);
        setMessages(prev => [...prev, userMessage, assistantMessage]);
        return;
      }
    }

    // Resetear flag de parada y contador de reintentos
    stopStreamingRef.current = false;
    retryCountRef.current = 0;

    const requestId = Date.now();
    currentRequestRef.current = { active: true, id: requestId };

    // Crear y agregar mensaje del usuario
    const userMessage = createUserMessage(text, searchScope, consultedExpediente);
    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    // Crear y agregar mensaje vacío del asistente
    const assistantMessage = createEmptyAssistantMessage();
    setMessages(prev => [...prev, assistantMessage]);

    const messageIndex = messages.length + 1;
    setStreamingMessageIndex(messageIndex);
    setIsTyping(false);

    if (!sessionId) {
      setIsTyping(false);
      setStreamingMessageIndex(null);
      return;
    }

    // ======= MODO STREAMING MEJORADO =======
    try {
      // Crear función de reintento
      const retryFunction = () => {
        return consultaService.consultaGeneralStreaming(
          text,
          callbacks.onChunk,
          callbacks.onComplete,
          callbacks.onError,
          null,
          sessionId,
          searchScope === 'expediente' ? consultedExpediente : null
        );
      };

      // Crear callbacks usando utilidad
      const callbacks = createStreamingCallbacks(
        messageIndex,
        currentRequestRef,
        requestId,
        setMessages,
        setStreamingMessageIndex,
        setIsTyping,
        retryCountRef,
        retryFunction
      );

      // Llamar al servicio con gestión automática de historial
      await consultaService.consultaGeneralStreaming(
        text,
        callbacks.onChunk,
        callbacks.onComplete,
        callbacks.onError,
        null,
        sessionId,
        searchScope === 'expediente' ? consultedExpediente : null
      );

    } catch (error) {
      setStreamingMessageIndex(null);
      setIsTyping(false);
      currentRequestRef.current = null;

      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        if (updatedMessages[messageIndex]) {
          let errorMessage = 'Lo siento, ocurrió un error al procesar tu consulta.';

          const errorText = typeof error === 'string' ? error : (error.message || error.toString() || 'Error desconocido');

          if (errorText.includes('No se puede conectar con el servidor backend')) {
            errorMessage = '**Error de Conexión**\n\nNo se puede conectar con el servidor backend. Por favor verifica que:\n\n• El servidor backend esté ejecutándose en el puerto 8000\n• Ollama esté activo en el puerto 11434\n• No haya problemas de red\n\nIntenta nuevamente en unos momentos.';
          } else if (errorText.includes('Failed to fetch')) {
            errorMessage = '**Error de Red**\n\nNo se puede conectar con el servidor. Verifica tu conexión y que los servicios estén activos.';
          }

          updatedMessages[messageIndex] = {
            ...updatedMessages[messageIndex],
            text: errorMessage,
            isError: true,
            timestamp: formatearSoloHoraCostaRica(new Date())
          };
        }
        return updatedMessages;
      });
    }
    // ======= FIN MODO STREAMING =======
  };

  return (
    <div className="h-full flex flex-col bg-white relative">
      {/* Controles de chat */}
      <div className="absolute top-3 right-3 z-20 flex items-center gap-1.5">
        {/* Botón de historial */}
        <button
          onClick={() => setShowHistory(true)}
          className="group flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:text-blue-700 bg-white/50 hover:bg-white/90 rounded-md transition-colors duration-150"
          title="Ver historial de conversaciones"
          aria-label="Ver historial de conversaciones"
        >
          <svg
            className="w-3.5 h-3.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="hidden sm:inline">Historial</span>
        </button>

        {/* Botón de nueva conversación */}
        {messages.length > 0 && (
          <button
            onClick={() => {
              newSession();
              setMessages([]);
              setIsRestoringSession(false);
              
              if (searchScope === 'expediente') {
                setConsultedExpediente(null);
                setTimeout(() => setMessages([createWelcomeMessage()]), 0);
              }
            }}
            className="group flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:text-blue-700 bg-white/50 hover:bg-white/90 rounded-md transition-colors duration-150"
            title="Nueva conversación"
            aria-label="Iniciar nueva conversación"
          >
            <svg
              className="w-3.5 h-3.5 transition-transform group-hover:rotate-90 duration-200"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            <span className="hidden sm:inline">Nueva</span>
          </button>
        )}
      </div>

      {/* Chat Area - Sin header para más espacio */}
      <div className="flex-1 flex flex-col min-h-0">
        {isRestoringSession ? (
          // Mostrar un loader mientras se restaura la sesión
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#003d82] mx-auto mb-4"></div>
              <p className="text-gray-500">Cargando conversación...</p>
            </div>
          </div>
        ) : (
          <>
            <MessageList
              messages={messages}
              isTyping={isTyping}
              streamingMessageIndex={streamingMessageIndex}
              onRetry={handleSendMessage}
        />

            <ChatInput
              onSendMessage={handleSendMessage}
              onStopGeneration={handleStopGeneration}
              isDisabled={false} // El chat siempre está disponible
              isLoading={isTyping || streamingMessageIndex !== null}
              searchScope={searchScope}
              setSearchScope={handleSearchScopeChange}
              consultedExpediente={consultedExpediente}
            />
          </>
        )}
      </div>

      {/* Modal de historial de conversaciones */}
      <ConversationHistory
        isOpen={showHistory}
        onClose={() => setShowHistory(false)}
        onConversationSelect={(selectedSessionId, conversation) => {
          // Restaurar conversación seleccionada
          if (conversation && conversation.messages) {
            // 🎯 CRÍTICO: Restaurar el session_id original ANTES de cargar los mensajes
            restoreSession(selectedSessionId);
            
            // Convertir mensajes del backend al formato del frontend
            const restoredMessages = conversation.messages.map((msg, index) => ({
              text: msg.content,
              isUser: msg.role === 'user',
              // Usar timestamp original si existe, sino usar timestamp con pequeño offset para diferenciación
              timestamp: msg.timestamp 
                ? formatearSoloHoraCostaRica(new Date(msg.timestamp))
                : formatearSoloHoraCostaRica(new Date(Date.now() - (conversation.messages.length - index) * 1000))
            }));
            
            setMessages(restoredMessages);
            
            // Si la conversación tiene un expediente asociado, restaurar el contexto
            if (conversation.expediente_number) {
              setConsultedExpediente(conversation.expediente_number);
              setSearchScope('expediente');

            } else {
              setSearchScope('general');
              setConsultedExpediente(null);
            }
          }
        }}
        onNewConversation={() => {
          newSession();
          setMessages([]);
          setConsultedExpediente(null);
          setIsRestoringSession(false);
          
          if (searchScope === 'expediente') {
            setMessages([createWelcomeMessage()]);
          }
        }}
      />
    </div>
  );
};

export default ConsultaChat;
