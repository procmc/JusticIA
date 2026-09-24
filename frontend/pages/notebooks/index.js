import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import {
  Card, CardBody, Button, Input, Spinner, Chip,
  Modal, ModalContent, ModalHeader, ModalBody
} from '@heroui/react';
import { FiPlus, FiUpload, FiFile, FiSend, FiBookOpen, FiX } from 'react-icons/fi';

import notebookService from '@/services/notebookService';
import ingestaService from '@/services/ingestaService';
import Toast from '@/components/ui/CustomAlert';
import consultaService from '@/services/consultaService';
import MessageList from '@/components/consulta-datos/chat/MessageList';
import {
  createUserMessage,
  createEmptyAssistantMessage,
  createStreamingCallbacks,
  saveNotebookChatToSessionStorage,
  restoreNotebookChatFromSessionStorage
} from '@/utils/chat/messageUtils';

/**
 * NotebookServIA — v1
 *
 * Colección de documentos genérica ("notebook") que el usuario crea y
 * nombra, con chat acotado SOLO a los documentos de ese notebook.
 *
 * Reutiliza por debajo la misma tubería de ingesta y RAG que ya existe
 * para expedientes (ver backend/app/db/models/notebook.py), pero sin
 * exponer nunca vocabulario ni formato de expediente judicial en la UI.
 */
const NotebooksPage = () => {
  const { data: session } = useSession();

  const [notebooks, setNotebooks] = useState([]);
  const [loadingNotebooks, setLoadingNotebooks] = useState(true);
  const [nuevoNombre, setNuevoNombre] = useState('');
  const [creando, setCreando] = useState(false);

  const [notebookActivo, setNotebookActivo] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  // Chat
  const [messages, setMessages] = useState([]);
  const [texto, setTexto] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [streamingMessageIndex, setStreamingMessageIndex] = useState(null);
  const currentRequestRef = useRef(null);
  const retryCountRef = useRef(0);

  // Ingesta
  const fileInputRef = useRef(null);
  const [archivosSeleccionados, setArchivosSeleccionados] = useState([]); // File[] — en revisión, aún no subidos
  const [archivosSubiendo, setArchivosSubiendo] = useState([]); // [{nombre, taskId, status}] — subida en curso
  const [documentosNotebook, setDocumentosNotebook] = useState([]); // documentos ya persistidos (backend)
  const [eliminandoId, setEliminandoId] = useState(null);
  const pollingRef = useRef(new Set());

  const formatearTamano = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleSeleccionarArchivos = (fileList) => {
    if (!fileList) return;
    setArchivosSeleccionados(prev => [...prev, ...Array.from(fileList)]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleQuitarSeleccionado = (index) => {
    setArchivosSeleccionados(prev => prev.filter((_, i) => i !== index));
  };

  const cargarNotebooks = useCallback(async () => {
    setLoadingNotebooks(true);
    const result = await notebookService.listarNotebooks();
    if (result.success) {
      setNotebooks(result.notebooks);
    }
    setLoadingNotebooks(false);
  }, []);

  useEffect(() => {
    cargarNotebooks();
  }, [cargarNotebooks]);

  const handleCrearNotebook = async () => {
    if (!nuevoNombre.trim()) return;
    setCreando(true);
    const result = await notebookService.crearNotebook(nuevoNombre.trim());
    setCreando(false);
    if (result.success) {
      setNuevoNombre('');
      setNotebooks(prev => [result.notebook, ...prev]);
      seleccionarNotebook(result.notebook);
    }
  };

  const cargarDocumentos = useCallback(async (notebookId) => {
    const result = await notebookService.listarDocumentos(notebookId);
    if (result.success) {
      setDocumentosNotebook(result.documentos);
    }
  }, []);

  const seleccionarNotebook = (notebook) => {
    setNotebookActivo(notebook);
    setArchivosSubiendo([]);
    setArchivosSeleccionados([]);
    setDocumentosNotebook([]);

    // Restaurar la conversación si ya existía (guardada en sessionStorage
    // la última vez que se salió de este notebook). Si no hay nada
    // guardado, es la primera vez que se abre: sesión nueva.
    const restaurado = restoreNotebookChatFromSessionStorage(notebook.id);
    if (restaurado) {
      setSessionId(restaurado.sessionId);
      setMessages(restaurado.messages);
    } else {
      const userId = session?.user?.email || 'anonimo';
      setSessionId(`session_notebook_${notebook.id}_${userId}_${Date.now()}`);
      setMessages([]);
    }

    cargarDocumentos(notebook.id);
  };

  // Guardar la conversación en sessionStorage cada vez que cambia, para
  // poder restaurarla si el usuario cambia de notebook y vuelve, o
  // recarga la página.
  useEffect(() => {
    if (notebookActivo && sessionId) {
      saveNotebookChatToSessionStorage(notebookActivo.id, sessionId, messages);
    }
  }, [messages, sessionId, notebookActivo]);

  const handleEliminarDocumento = async (documentoId) => {
    if (!notebookActivo) return;
    setEliminandoId(documentoId);
    const result = await notebookService.eliminarDocumento(notebookActivo.id, documentoId);
    if (result.success) {
      setDocumentosNotebook(prev => prev.filter(d => d.id !== documentoId));
    }
    setEliminandoId(null);
  };

  // Previsualización: click en un documento ya procesado abre su archivo
  // original (imagen o PDF) para verificar qué dice contra la respuesta del chat.
  const [preview, setPreview] = useState(null); // { url, tipo, nombre } | null
  const [cargandoPreviewId, setCargandoPreviewId] = useState(null);

  const handleVerArchivo = async (doc, e) => {
    // El botón "x" de cerrar vive dentro del mismo Chip que este onClick:
    // si el click vino de ahí, es para eliminar el documento, no para verlo.
    if (e?.target?.closest('[aria-label="close chip"]')) return;
    if (!notebookActivo || doc.estado !== 'Procesado' || cargandoPreviewId) return;
    setCargandoPreviewId(doc.id);
    const result = await notebookService.obtenerArchivoPreview(notebookActivo.id, doc.id);
    if (result.success) {
      setPreview({ url: result.url, tipo: result.tipo, nombre: doc.nombre_archivo });
    }
    setCargandoPreviewId(null);
  };

  const cerrarPreview = () => {
    if (preview?.url) URL.revokeObjectURL(preview.url);
    setPreview(null);
  };

  // ===================== Ingesta =====================

  const pollTaskProgress = (taskId, nombreArchivo, notebookId) => {
    if (pollingRef.current.has(taskId)) return;
    pollingRef.current.add(taskId);

    const check = async () => {
      const data = await ingestaService.consultarProgresoTarea(taskId);
      setArchivosSubiendo(prev => prev.map(a => (
        a.taskId === taskId ? { ...a, status: data.status, progress: data.progress } : a
      )));

      if (data.ready) {
        pollingRef.current.delete(taskId);
        // Quitar de "subiendo" y refrescar la lista persistida del notebook
        setArchivosSubiendo(prev => prev.filter(a => a.taskId !== taskId));
        cargarDocumentos(notebookId);
        return;
      }
      setTimeout(check, 3000);
    };

    check();
  };

  const [confirmandoSubida, setConfirmandoSubida] = useState(false);

  // Sube archivos directo al notebook activo, sin pasar por la lista de
  // revisión — usado para pegar/arrastrar una imagen en el chat, donde el
  // propio gesto de pegar ya es la confirmación (igual que ChatGPT).
  const subirArchivosDirecto = async (archivos) => {
    if (!notebookActivo || !archivos || archivos.length === 0) return;
    try {
      const resultado = await ingestaService.subirArchivos(notebookActivo.clave_interna, archivos);
      const nuevos = archivos.map((file, i) => ({
        nombre: file.name,
        taskId: resultado.task_ids[i],
        status: 'procesando',
        progress: 0
      }));
      setArchivosSubiendo(prev => [...prev, ...nuevos]);
      nuevos.forEach(a => pollTaskProgress(a.taskId, a.nombre, notebookActivo.id));
    } catch (error) {
      console.error('Error subiendo archivos al notebook:', error);
      Toast.error('Error al subir', error.message || 'No se pudo subir el archivo. Intentá de nuevo.');
    }
  };

  const handleConfirmarSubida = async () => {
    if (!notebookActivo || archivosSeleccionados.length === 0) return;
    setConfirmandoSubida(true);
    await subirArchivosDirecto(archivosSeleccionados);
    setArchivosSeleccionados([]);
    setConfirmandoSubida(false);
  };

  // Pegar una imagen directamente en el chat (Ctrl+V) la sube sola al notebook
  const handlePasteImagen = (e) => {
    if (!notebookActivo) return;
    const items = Array.from(e.clipboardData?.items || []);
    const imagenes = items
      .filter(item => item.type.startsWith('image/'))
      .map(item => item.getAsFile())
      .filter(Boolean);

    if (imagenes.length > 0) {
      e.preventDefault();
      subirArchivosDirecto(imagenes);
    }
  };

  // Arrastrar una imagen sobre el chat también la sube sola
  const [arrastrandoImagen, setArrastrandoImagen] = useState(false);

  const handleDropImagen = (e) => {
    e.preventDefault();
    setArrastrandoImagen(false);
    if (!notebookActivo) return;
    const archivos = Array.from(e.dataTransfer?.files || []);
    if (archivos.length > 0) {
      subirArchivosDirecto(archivos);
    }
  };

  // ===================== Chat =====================

  const handleEnviarMensaje = async () => {
    const query = texto.trim();
    if (!query || !notebookActivo || !sessionId) return;
    setTexto('');

    const userMessage = createUserMessage(query, 'notebook');
    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    const assistantMessage = createEmptyAssistantMessage();
    setMessages(prev => [...prev, assistantMessage]);

    const messageIndex = messages.length + 1;
    setStreamingMessageIndex(messageIndex);
    setIsTyping(false);

    const requestId = Date.now();
    currentRequestRef.current = { active: true, id: requestId };
    retryCountRef.current = 0;

    const retryFunction = () => consultaService.consultaGeneralStreaming(
      query, callbacks.onChunk, callbacks.onComplete, callbacks.onError,
      null, sessionId, null, String(notebookActivo.id)
    );

    const callbacks = createStreamingCallbacks(
      messageIndex, currentRequestRef, requestId,
      setMessages, setStreamingMessageIndex, setIsTyping,
      retryCountRef, retryFunction
    );

    try {
      await consultaService.consultaGeneralStreaming(
        query, callbacks.onChunk, callbacks.onComplete, callbacks.onError,
        null, sessionId, null, String(notebookActivo.id)
      );
    } catch (error) {
      setStreamingMessageIndex(null);
      setIsTyping(false);
      currentRequestRef.current = null;
    }
  };

  return (
    <div className="h-full flex bg-gray-50">
      {/* Panel lateral: lista de notebooks */}
      <div className="w-72 border-r border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-[#003d82] flex items-center gap-2">
            <FiBookOpen /> NotebookServIA
          </h2>
          <p className="text-xs text-gray-500 mt-1">Tus colecciones de documentos</p>
        </div>

        <div className="p-3 border-b border-gray-200 flex gap-2">
          <Input
            size="sm"
            placeholder="Nombre del notebook"
            value={nuevoNombre}
            onValueChange={setNuevoNombre}
            onKeyDown={(e) => e.key === 'Enter' && handleCrearNotebook()}
          />
          <Button
            isIconOnly
            size="sm"
            color="primary"
            isLoading={creando}
            onPress={handleCrearNotebook}
            aria-label="Crear notebook"
          >
            <FiPlus />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loadingNotebooks ? (
            <div className="flex justify-center p-4"><Spinner size="sm" /></div>
          ) : notebooks.length === 0 ? (
            <p className="text-sm text-gray-400 text-center p-4">Todavía no tenés notebooks. Creá uno arriba.</p>
          ) : (
            notebooks.map(nb => (
              <button
                key={nb.id}
                onClick={() => seleccionarNotebook(nb)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  notebookActivo?.id === nb.id ? 'bg-blue-50 text-[#003d82] font-medium' : 'hover:bg-gray-50 text-gray-700'
                }`}
              >
                {nb.nombre}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Área principal */}
      <div className="flex-1 flex flex-col min-w-0">
        {!notebookActivo ? (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <FiBookOpen className="mx-auto mb-2" size={32} />
              <p>Elegí o creá un notebook para empezar</p>
            </div>
          </div>
        ) : (
          <>
            {/* Carga de documentos */}
            <div className="p-4 border-b border-gray-200 bg-white">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-800">{notebookActivo.nombre}</h3>
                <Button
                  size="sm"
                  variant="flat"
                  startContent={<FiUpload />}
                  onPress={() => fileInputRef.current?.click()}
                >
                  Subir documentos
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={(e) => handleSeleccionarArchivos(e.target.files)}
                />
              </div>

              {/* Archivos seleccionados, en revisión antes de subir */}
              {archivosSeleccionados.length > 0 && (
                <div className="mb-2 border border-gray-200 rounded-lg p-3 bg-gray-50">
                  <p className="text-xs text-gray-500 mb-2">
                    {archivosSeleccionados.length} archivo(s) seleccionado(s) — revisá antes de subir:
                  </p>
                  <div className="space-y-1 mb-2">
                    {archivosSeleccionados.map((file, i) => (
                      <div key={`${file.name}-${i}`} className="flex items-center justify-between text-sm bg-white rounded px-2 py-1 border border-gray-100">
                        <span className="flex items-center gap-2 truncate">
                          <FiFile className="text-gray-400 shrink-0" />
                          <span className="truncate">{file.name}</span>
                          <span className="text-gray-400 text-xs shrink-0">({formatearTamano(file.size)})</span>
                        </span>
                        <button
                          onClick={() => handleQuitarSeleccionado(i)}
                          className="text-gray-400 hover:text-red-500 shrink-0"
                          aria-label={`Quitar ${file.name}`}
                        >
                          <FiX />
                        </button>
                      </div>
                    ))}
                  </div>
                  <Button
                    size="sm"
                    color="primary"
                    isLoading={confirmandoSubida}
                    onPress={handleConfirmarSubida}
                  >
                    Confirmar y subir a "{notebookActivo.nombre}"
                  </Button>
                </div>
              )}

              {/* Documentos ya subidos y procesados — se pueden quitar */}
              {documentosNotebook.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {documentosNotebook.map(doc => (
                    <Chip
                      key={doc.id}
                      size="sm"
                      startContent={<FiFile className="ml-1" />}
                      color={doc.estado === 'Procesado' ? 'success' : doc.estado === 'Error' ? 'danger' : 'default'}
                      variant="flat"
                      onClose={() => handleEliminarDocumento(doc.id)}
                      isDisabled={eliminandoId === doc.id}
                      onClick={(e) => handleVerArchivo(doc, e)}
                      className={doc.estado === 'Procesado' ? 'cursor-pointer' : ''}
                      title={doc.estado === 'Procesado' ? 'Click para ver el archivo original' : undefined}
                    >
                      {cargandoPreviewId === doc.id ? 'Abriendo…' : doc.nombre_archivo}
                    </Chip>
                  ))}
                </div>
              )}

              {/* Subidas en curso (todavía no aparecen en la lista persistida) */}
              {archivosSubiendo.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {archivosSubiendo.map(a => (
                    <Chip
                      key={a.taskId}
                      size="sm"
                      startContent={<FiFile className="ml-1" />}
                      color="default"
                      variant="flat"
                    >
                      {a.nombre} — {`${a.progress || 0}%`}
                    </Chip>
                  ))}
                </div>
              )}
            </div>

            {/* Chat — acepta pegar (Ctrl+V) o arrastrar una imagen, se sube sola al notebook */}
            <div
              className="flex-1 flex flex-col min-h-0 relative"
              onDragOver={(e) => { e.preventDefault(); setArrastrandoImagen(true); }}
              onDragLeave={() => setArrastrandoImagen(false)}
              onDrop={handleDropImagen}
            >
              {arrastrandoImagen && (
                <div className="absolute inset-0 z-10 bg-blue-50/90 border-2 border-dashed border-blue-400 rounded-lg flex items-center justify-center pointer-events-none">
                  <p className="text-blue-700 font-medium">Soltá la imagen para subirla a "{notebookActivo.nombre}"</p>
                </div>
              )}
              <MessageList
                messages={messages}
                isTyping={isTyping}
                streamingMessageIndex={streamingMessageIndex}
                onRetry={() => {}}
              />
              <div className="p-3 border-t border-gray-200 bg-white flex gap-2">
                <Input
                  placeholder={`Preguntale algo a "${notebookActivo.nombre}"... (podés pegar una imagen con Ctrl+V)`}
                  value={texto}
                  onValueChange={setTexto}
                  onKeyDown={(e) => e.key === 'Enter' && handleEnviarMensaje()}
                  onPaste={handlePasteImagen}
                />
                <Button
                  isIconOnly
                  color="primary"
                  onPress={handleEnviarMensaje}
                  isDisabled={isTyping || streamingMessageIndex !== null}
                  aria-label="Enviar"
                >
                  <FiSend />
                </Button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Previsualización del archivo original — verificar qué dice contra la respuesta del chat */}
      <Modal isOpen={!!preview} onClose={cerrarPreview} size="3xl" scrollBehavior="inside">
        <ModalContent>
          <ModalHeader>{preview?.nombre}</ModalHeader>
          <ModalBody className="pb-6">
            {preview?.tipo?.startsWith('image/') ? (
              <img src={preview.url} alt={preview.nombre} className="max-w-full h-auto mx-auto" />
            ) : preview?.tipo === 'application/pdf' ? (
              <iframe src={preview.url} title={preview.nombre} className="w-full h-[75vh] border-0" />
            ) : (
              <p className="text-gray-500 text-center py-8">
                Vista previa no disponible para este tipo de archivo.
              </p>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </div>
  );
};

export default NotebooksPage;
