import React, { useState } from 'react';
import { usePersistentChatContext } from '../../../hooks/conversacion/usePersistentChatContext';

const ConversationHistory = ({ isOpen, onClose, onConversationSelect }) => {
  const { 
    userConversations, 
    conversationId: currentConversationId,
    switchToConversation, 
    deleteConversation,
    startNewConversation 
  } = usePersistentChatContext();

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);

  const handleSelectConversation = (convId) => {
    switchToConversation(convId);
    onConversationSelect?.(convId);
    onClose();
  };

  const handleDeleteConversation = (convId, e) => {
    e.stopPropagation();
    if (showDeleteConfirm === convId) {
      deleteConversation(convId);
      setShowDeleteConfirm(null);
    } else {
      setShowDeleteConfirm(convId);
      setTimeout(() => setShowDeleteConfirm(null), 3000);
    }
  };

  const handleNewConversation = () => {
    startNewConversation();
    onClose();
  };

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 86400000) { // Menos de 24 horas
      return date.toLocaleTimeString('es-ES', { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } else if (diff < 604800000) { // Menos de 7 días
      return date.toLocaleDateString('es-ES', { weekday: 'short' });
    } else {
      return date.toLocaleDateString('es-ES', { 
        day: '2-digit', 
        month: '2-digit' 
      });
    }
  };

  const getPreviewText = (conversation) => {
    if (!conversation.lastMessage) return 'Conversación nueva';
    
    const { userMessage } = conversation.lastMessage;
    return userMessage.length > 50 
      ? userMessage.substring(0, 50) + '...'
      : userMessage;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/20 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Historial de Conversaciones
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Nueva conversación */}
        <div className="px-6 py-3 border-b border-gray-50">
          <button
            onClick={handleNewConversation}
            className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-blue-50 transition-colors border-2 border-dashed border-blue-200 hover:border-blue-300 group"
          >
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center group-hover:bg-blue-200 transition-colors">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </div>
            <div className="text-left">
              <div className="font-medium text-blue-900">Nueva Conversación</div>
              <div className="text-sm text-blue-600">Empezar desde cero</div>
            </div>
          </button>
        </div>

        {/* Lista de conversaciones */}
        <div className="overflow-y-auto max-h-96">
          {userConversations.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-500">
              <svg className="w-12 h-12 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <p>No hay conversaciones guardadas</p>
            </div>
          ) : (
            <div className="px-2 py-2 space-y-1">
              {userConversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`relative group cursor-pointer p-4 rounded-xl transition-all hover:bg-gray-50 ${
                    conv.id === currentConversationId 
                      ? 'bg-blue-50 border-2 border-blue-200' 
                      : 'border-2 border-transparent'
                  }`}
                  onClick={() => handleSelectConversation(conv.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-gray-900">
                          {getPreviewText(conv)}
                        </span>
                        {conv.id === currentConversationId && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>{formatDate(conv.lastUpdated)}</span>
                        <span>•</span>
                        <span>{conv.messageCount} mensajes</span>
                      </div>
                    </div>
                    
                    {/* Botón de eliminar */}
                    <button
                      onClick={(e) => handleDeleteConversation(conv.id, e)}
                      className={`p-1.5 rounded-lg transition-all opacity-0 group-hover:opacity-100 ${
                        showDeleteConfirm === conv.id
                          ? 'bg-red-100 text-red-600 hover:bg-red-200'
                          : 'hover:bg-gray-200 text-gray-400 hover:text-gray-600'
                      }`}
                      title={showDeleteConfirm === conv.id ? 'Hacer clic para confirmar' : 'Eliminar conversación'}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer con información */}
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-100">
          <p className="text-xs text-gray-500 text-center">
            Las conversaciones se guardan automáticamente en tu navegador
          </p>
        </div>
      </div>
    </div>
  );
};

export default ConversationHistory;