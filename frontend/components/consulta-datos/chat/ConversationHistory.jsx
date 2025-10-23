import React, { useState, useEffect } from 'react';
import { useBackendConversations } from '../../../hooks/useBackendConversations';
import { formatearSoloHoraCostaRica, formatearSoloFechaCostaRica } from '../../../utils/dateUtils';

const ConversationHistory = ({ isOpen, onClose, onConversationSelect, onNewConversation }) => {
  const { 
    conversations,
    isLoading,
    error,
    hasConversations,
    fetchConversations,
    deleteConversation,
    getConversationDetail,
    restoreConversation
  } = useBackendConversations();

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);
  const [loadingAction, setLoadingAction] = useState(null);

  // Recargar conversaciones cuando se abre el modal
  useEffect(() => {
    if (isOpen) {
      fetchConversations();
    }
  }, [isOpen, fetchConversations]);

  const handleSelectConversation = async (sessionId) => {
    setLoadingAction(sessionId);
    
    try {
      // Obtener detalles completos de la conversación
      const conversation = await getConversationDetail(sessionId);
      
      if (conversation) {
        // Notificar al componente padre para que cargue la conversación
        onConversationSelect?.(sessionId, conversation);
        onClose();
      } else {
        console.error('No se pudieron obtener los detalles de la conversación');
        // Intentar restaurar la conversación
        const restored = await restoreConversation(sessionId);
        if (restored) {
          onConversationSelect?.(sessionId, restored);
          onClose();
        }
      }
    } catch (err) {
      console.error('Error seleccionando conversación:', err);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleDeleteConversation = async (sessionId, e) => {
    e.stopPropagation();
    
    if (showDeleteConfirm === sessionId) {
      setLoadingAction(sessionId);
      
      try {
        const success = await deleteConversation(sessionId);
        
        if (success) {
          setShowDeleteConfirm(null);
          console.log('✅ Conversación eliminada');
        } else {
          console.error('No se pudo eliminar la conversación');
        }
      } catch (err) {
        console.error('Error eliminando conversación:', err);
      } finally {
        setLoadingAction(null);
      }
    } else {
      setShowDeleteConfirm(sessionId);
      setTimeout(() => setShowDeleteConfirm(null), 3000);
    }
  };

  const handleNewConversation = () => {
    onNewConversation?.();
    onClose();
  };

  const formatDate = (isoString) => {
    const fechaOriginal = new Date(isoString);
    
    // Obtener fecha actual en Costa Rica (formato YYYY-MM-DD)
    const hoyCostaRica = new Date().toLocaleDateString("sv-SE", {timeZone: "America/Costa_Rica"});
    // Obtener fecha del mensaje en Costa Rica (formato YYYY-MM-DD)  
    const fechaMensajeCostaRica = fechaOriginal.toLocaleDateString("sv-SE", {timeZone: "America/Costa_Rica"});
    
    if (hoyCostaRica === fechaMensajeCostaRica) { // Mismo día en Costa Rica
      return formatearSoloHoraCostaRica(fechaOriginal);
    } else {
      // Calcular diferencia en días usando fechas de Costa Rica
      const diffTime = new Date(hoyCostaRica) - new Date(fechaMensajeCostaRica);
      const diffDias = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      if (diffDias > 0 && diffDias <= 7) { // Entre 1-7 días - mostrar día de semana
        const opcionesdia = {
          timeZone: 'America/Costa_Rica',
          weekday: 'short'
        };
        return new Intl.DateTimeFormat('es-CR', opcionesdia).format(fechaOriginal);
      } else { // Más de 7 días - mostrar fecha completa
        return formatearSoloFechaCostaRica(fechaOriginal);
      }
    }
  };

  const getPreviewText = (conversation) => {
    if (!conversation.title || conversation.title === 'Nueva conversación') {
      return 'Conversación sin título';
    }
    
    return conversation.title;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/20 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              Historial de Conversaciones
            </h3>
            {hasConversations && (
              <p className="text-xs text-gray-500 mt-1">
                {conversations.length} conversación{conversations.length !== 1 ? 'es' : ''} guardada{conversations.length !== 1 ? 's' : ''}
              </p>
            )}
          </div>
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
          {isLoading ? (
            <div className="px-6 py-8 text-center">
              <div className="w-12 h-12 mx-auto mb-4 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
              <p className="text-gray-500">Cargando conversaciones...</p>
            </div>
          ) : error ? (
            <div className="px-6 py-8 text-center text-red-500">
              <svg className="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p>{error}</p>
              <button 
                onClick={() => fetchConversations()}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Reintentar
              </button>
            </div>
          ) : !hasConversations ? (
            <div className="px-6 py-8 text-center text-gray-500">
              <svg className="w-12 h-12 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <p>No hay conversaciones guardadas</p>
              <p className="text-sm text-gray-400 mt-2">
                Inicia una nueva conversación para comenzar
              </p>
            </div>
          ) : (
            <div className="px-2 py-2 space-y-1">
              {conversations.map((conv) => (
                <div
                  key={conv.session_id}
                  className={`relative group cursor-pointer p-4 rounded-xl transition-all hover:bg-gray-50 border-2 border-transparent hover:border-blue-100 ${
                    loadingAction === conv.session_id ? 'opacity-50 pointer-events-none' : ''
                  }`}
                  onClick={() => handleSelectConversation(conv.session_id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-gray-900 truncate">
                          {getPreviewText(conv)}
                        </span>
                        {conv.expediente_number && (
                          <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
                            {conv.expediente_number}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>{formatDate(conv.updated_at)}</span>
                        <span>•</span>
                        <span>{conv.message_count} mensajes</span>
                      </div>
                    </div>
                    
                    {/* Botón de eliminar */}
                    <button
                      onClick={(e) => handleDeleteConversation(conv.session_id, e)}
                      disabled={loadingAction === conv.session_id}
                      className={`p-1.5 rounded-lg transition-all opacity-0 group-hover:opacity-100 ${
                        showDeleteConfirm === conv.session_id
                          ? 'bg-red-100 text-red-600 hover:bg-red-200'
                          : 'hover:bg-gray-200 text-gray-400 hover:text-gray-600'
                      }`}
                      title={showDeleteConfirm === conv.session_id ? 'Hacer clic para confirmar' : 'Eliminar conversación'}
                    >
                      {loadingAction === conv.session_id ? (
                        <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
                      ) : (
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      )}
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
            Las conversaciones se guardan automáticamente en el servidor
          </p>
        </div>
      </div>
    </div>
  );
};

export default ConversationHistory;