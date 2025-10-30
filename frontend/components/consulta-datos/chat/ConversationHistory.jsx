import React, { useState, useEffect } from 'react';
import { useBackendConversations } from '../../../hooks/useBackendConversations';
import { formatearSoloHoraCostaRica, formatearSoloFechaCostaRica, formatearFechaHoraHistorial } from '../../../utils/dateUtils';
import DrawerGeneral from '../../ui/DrawerGeneral';

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
    // Siempre mostrar fecha y hora completa en el historial
    return formatearFechaHoraHistorial(isoString);
  };

  const getPreviewText = (conversation) => {
    if (!conversation.title || conversation.title === 'Nueva conversación') {
      return 'Conversación sin título';
    }
    
    return conversation.title;
  };

  return (
    <DrawerGeneral
      isOpen={isOpen}
      onOpenChange={(open) => !open && onClose()}
      titulo="Historial de Conversaciones"
      size="lg"
      botonCerrar={{
        mostrar: true,
        texto: "Cerrar"
      }}
      botonAccion={{
        texto: "Nueva Conversación",
        onPress: handleNewConversation,
        color: "primary"
      }}
    >
      <div className="space-y-4">
        {/* Información del historial */}
        {hasConversations && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-sm text-blue-700">
              {conversations.length} conversación{conversations.length !== 1 ? 'es' : ''} guardada{conversations.length !== 1 ? 's' : ''}
            </p>
          </div>
        )}

        {/* Lista de conversaciones */}
        <div className="space-y-2">
          {isLoading ? (
            <div className="py-8 text-center">
              <div className="w-12 h-12 mx-auto mb-4 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
              <p className="text-gray-500">Cargando conversaciones...</p>
            </div>
          ) : error ? (
            <div className="py-8 text-center text-red-500">
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
            <div className="py-8 text-center text-gray-500">
              <svg className="w-12 h-12 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <p>No hay conversaciones guardadas</p>
              <p className="text-sm text-gray-400 mt-2">
                Inicia una nueva conversación para comenzar
              </p>
            </div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.session_id}
                className={`relative group cursor-pointer p-4 rounded-xl transition-all hover:bg-gray-50 border-2 border-transparent hover:border-blue-100 ${
                  loadingAction === conv.session_id ? 'opacity-50 pointer-events-none' : ''
                }`}
                onClick={() => handleSelectConversation(conv.session_id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-col gap-1 mb-1">
                      <span className="text-sm font-medium text-gray-900 truncate">
                        {getPreviewText(conv)}
                      </span>
                      {conv.expediente_number && (
                        <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded font-mono w-fit">
                          Expediente: {conv.expediente_number}
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
            ))
          )}
        </div>
      </div>
    </DrawerGeneral>
  );
};

export default ConversationHistory;