import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import {
  Card, CardBody, Button, Input, Spinner, Chip, Alert, Tooltip,
  Modal, ModalContent, ModalHeader, ModalBody
} from '@heroui/react';
import { FiPlus, FiUpload, FiFile, FiSend, FiBookOpen, FiX, FiChevronLeft, FiChevronRight } from 'react-icons/fi';
import DivisorDeColumna from '@/components/notebooks/DivisorDeColumna';
import useAnchosDeColumnas, { COLUMNAS } from '@/hooks/notebooks/useAnchosDeColumnas';

import notebookService from '@/services/notebookService';
import ingestaService from '@/services/ingestaService';
import Toast from '@/components/ui/CustomAlert';
import ConfirmModal from '@/components/ui/ConfirmModal';
import consultaService from '@/services/consultaService';
import { armarAvisoCarga } from '@/utils/ingesta-datos/iconos';
import ItemNotebook from '@/components/notebooks/ItemNotebook';
import FuenteNotebook from '@/components/notebooks/FuenteNotebook';
import PanelEstudio from '@/components/notebooks/PanelEstudio';
import useEstudio from '@/hooks/notebooks/useEstudio';
import MessageList from '@/components/consulta-datos/chat/MessageList';
import {
  createUserMessage,
  createEmptyAssistantMessage,
  createStreamingCallbacks,
  markMessageAsCanceled,
  saveNotebookChatToSessionStorage,
  restoreNotebookChatFromSessionStorage
} from '@/utils/chat/messageUtils';

const CLAVE_PANELES_PLEGADOS = 'notebooks_paneles_plegados';
// Fuentes cuya vista previa es una vista de texto del servidor (spec 009b, II1): texto plano, Word y HTML. El RTF no es un formato
// permitido (spec 006, FFF1).
const EXTENSIONES_VISTA_DE_TEXTO = ['.txt', '.doc', '.docx', '.html', '.htm', '.xhtml'];
// El navegador no muestra TIFF: el servidor lo convierte a PNG (RF-18.108).
const EXTENSIONES_VISTA_DE_IMAGEN = ['.tif', '.tiff'];

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
  const [errorCreacion, setErrorCreacion] = useState(''); // rechazo del servidor al crear (RF-17.85), bajo el campo
  const [notebookPorEliminar, setNotebookPorEliminar] = useState(null); // notebook que se pide confirmar (RF-17.86)
  const eliminacionRef = useRef(null); // el mismo notebook; se vacía en el primer «Eliminar» (envío único)

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
  // Fuentes que el usuario dejó fuera del chat (RF-11.100). Guardar las desmarcadas, y no las marcadas, hace que lo nuevo
  // entre marcado. Vive solo en la página abierta y se vacía al abrir un notebook (RF-11.103).
  const [desmarcadas, setDesmarcadas] = useState(() => new Set());
  const [eliminandoIds, setEliminandoIds] = useState(() => new Set()); // documentos con su «quitar» en curso (cada uno, el suyo)
  const quitandoRef = useRef(new Set()); // lo mismo, sin esperar al render: defensa para no enviar dos DELETE del mismo documento
  const reintentandoRef = useRef(new Set()); // fuentes con un reintento en camino: un doble clic envía una sola solicitud (RF-07.67)
  const [documentoPorQuitar, setDocumentoPorQuitar] = useState(null); // {id, nombre} mientras se pide confirmar (RF-19.40)
  const confirmacionRef = useRef(null); // el mismo documento; se vacía en el primer «Quitar» para absorber el doble clic (RF-19.70)
  const pollingRef = useRef(new Set());
  const [avisoCarga, setAvisoCarga] = useState(null); // aviso fijo de la última carga (RF-05.23); lo cierra el usuario

  // Estudio (spec 010): a 1366 px los tres paneles se ven a la vez; en pantalla pequeña, uno solo con pestañas (RNF-04.120).
  const [panelVisible, setPanelVisible] = useState('fuentes');
  // Paneles laterales plegados (a partir de lg): el chat toma ese ancho. Se recuerda en este navegador, sin que nada dependa de ello.
  const [plegados, setPlegados] = useState({ lista: false, fuentes: false, estudio: false });
  useEffect(() => {
    try {
      const guardado = JSON.parse(localStorage.getItem(CLAVE_PANELES_PLEGADOS) || 'null');
      if (guardado && typeof guardado === 'object') {
        setPlegados({ lista: !!guardado.lista, fuentes: !!guardado.fuentes, estudio: !!guardado.estudio });
      }
    } catch { /* sin almacenamiento: queda con todo desplegado */ }
  }, []);
  const alternarPanel = (clave) => setPlegados((previo) => {
    const siguiente = { ...previo, [clave]: !previo[clave] };
    try { localStorage.setItem(CLAVE_PANELES_PLEGADOS, JSON.stringify(siguiente)); } catch { /* idem */ }
    return siguiente;
  });
  // Ancho ajustable de las columnas arrastrando la línea que las divide, desde lg (spec 010, JJ1; RNF-04.124 a RNF-04.129).
  const { anchos, contenedorRef, controlesDe } = useAnchosDeColumnas(plegados);
  const divisor = (id) => (
    <DivisorDeColumna etiqueta={COLUMNAS[id].etiqueta} valor={anchos[id]} minimo={COLUMNAS[id].minimo} maximo={COLUMNAS[id].maximo}
      controles={controlesDe(id)} />
  );
  // Las fuentes marcadas, en cualquier estado: el servidor solo usa las Procesado, como en el chat (RF-11.106).
  const estudio = useEstudio(
    notebookActivo?.id ?? null,
    documentosNotebook.filter((d) => !desmarcadas.has(d.id)).map((d) => d.id)
  );
  const generandoResultado = Boolean(estudio.generando); // el chat espera mientras se genera (RF-11.131)
  const guardandoNotaRef = useRef(false); // un doble clic en «Guardar en notas» guarda una sola nota (RF-14.127)

  const formatearTamano = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleSeleccionarArchivos = (fileList) => {
    if (!fileList) return;
    // Se copia antes de vaciar el input: el FileList es vivo y React puede ejecutar la actualización después.
    const archivos = Array.from(fileList);
    setArchivosSeleccionados(prev => [...prev, ...archivos]);
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
      setErrorCreacion('');
      setNuevoNombre('');
      setNotebooks(prev => [result.notebook, ...prev]);
      seleccionarNotebook(result.notebook);
    } else if (result.status === 400) {
      setErrorCreacion(result.message);
    } else {
      Toast.error('Error al crear', 'No se pudo crear el notebook. Intente de nuevo.');
    }
  };

  // Quita de la lista (y cierra si estaba abierto) un notebook que ya no existe o se eliminó, sin guardar su chat.
  const retirarNotebook = (id) => {
    if (notebookActivo?.id === id) {
      cancelarEnCurso();
      try {
        sessionStorage.removeItem(`notebook_chat_session_${id}`);
        sessionStorage.removeItem(`notebook_chat_messages_${id}`);
      } catch (error) {
        // sessionStorage inaccesible: no es crítico
      }
      setNotebookActivo(null);
      setSessionId(null);
      setMessages([]);
      setDocumentosNotebook([]);
      setArchivosSeleccionados([]);
      setArchivosSubiendo([]);
    }
    setNotebooks(prev => prev.filter(n => n.id !== id));
  };

  // RF-17.80: 400 devuelve el mensaje del servidor para el campo; 404 retira la fila (RF-17.92); lo demás, un aviso.
  const handleRenombrarNotebook = async (nb, nombre) => {
    const result = await notebookService.renombrarNotebook(nb.id, nombre);
    if (result.success) {
      setNotebooks(prev => prev.map(n => (n.id === nb.id ? { ...n, nombre: result.notebook.nombre } : n)));
      setNotebookActivo(prev => (prev?.id === nb.id ? { ...prev, nombre: result.notebook.nombre } : prev));
      return { success: true };
    }
    if (result.status === 400) return { message: result.message };
    if (result.status === 404) {
      retirarNotebook(nb.id);
      Toast.warning('El notebook ya no está disponible.');
      return { success: true };
    }
    Toast.error('Error al renombrar', 'No se pudo renombrar el notebook. Intente de nuevo.');
    return {};
  };

  const pedirConfirmacionDeEliminar = (nb) => {
    const pendiente = { id: nb.id, nombre: nb.nombre };
    eliminacionRef.current = pendiente;
    setNotebookPorEliminar(pendiente);
  };

  const confirmarEliminar = async () => {
    const pendiente = eliminacionRef.current;
    eliminacionRef.current = null;
    if (!pendiente) return;
    const result = await notebookService.eliminarNotebook(pendiente.id);
    if (result.success) {
      const estabaAbierto = notebookActivo?.id === pendiente.id;
      retirarNotebook(pendiente.id);
      if (estabaAbierto) Toast.info('Notebook eliminado.');
    } else if (result.status === 404) {
      retirarNotebook(pendiente.id);
      Toast.warning('El notebook ya no está disponible.');
    } else {
      Toast.error('Error al eliminar', 'No se pudo eliminar el notebook. Intente de nuevo.');
    }
  };

  const cargarDocumentos = useCallback(async (notebookId) => {
    const result = await notebookService.listarDocumentos(notebookId);
    if (result.success) {
      setDocumentosNotebook(result.documentos);
    }
  }, []);

  const seleccionarNotebook = (notebook) => {
    // RF-17.70: abrir otro notebook con una respuesta en curso la cancela; la conversación cancelada se guarda bajo el
    // notebook anterior antes de cambiar (el efecto de abajo ya correría con el notebook nuevo).
    if (notebookActivo && sessionId && hayEnCurso()) {
      saveNotebookChatToSessionStorage(notebookActivo.id, sessionId, cancelarEnCurso());
    }
    setNotebookActivo(notebook);
    setArchivosSubiendo([]);
    setArchivosSeleccionados([]);
    setDocumentosNotebook([]);
    setDesmarcadas(new Set());
    setAvisoCarga(null);
    setPanelVisible('fuentes');

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

  // RF-19.102: 400 devuelve el mensaje del servidor para el campo; 200 vuelve a leer la lista (RF-19.103); 404 retira la
  // fuente (RF-19.109); lo demás, un aviso.
  const handleRenombrarFuente = async (doc, nombre) => {
    if (!notebookActivo) return {};
    const notebookId = notebookActivo.id;
    const result = await notebookService.renombrarDocumento(notebookId, doc.id, nombre);
    if (result.success) {
      await cargarDocumentos(notebookId);
      return { success: true };
    }
    if (result.status === 400) return { message: result.message };
    if (result.status === 404) {
      setDocumentosNotebook(prev => prev.filter(d => d.id !== doc.id));
      Toast.warning('La fuente ya no está disponible.');
      return { success: true };
    }
    Toast.error('Error al cambiar el nombre', 'No se pudo cambiar el nombre de la fuente. Intente de nuevo.');
    return {};
  };

  // RF-07.61: «Reintentar» en una fuente en Error. 200: la fuente vuelve a «en proceso» y se sigue su avance como el de una carga;
  // 404 la retira (RF-07.66); 409 (ya no está en Error o falta su archivo original) avisa con el mensaje del servidor y vuelve a leer
  // la lista; lo demás, un aviso (RF-07.68).
  const handleReintentarFuente = async (doc) => {
    if (!notebookActivo || reintentandoRef.current.has(doc.id)) return;
    reintentandoRef.current.add(doc.id);
    const notebookId = notebookActivo.id;
    const result = await notebookService.reintentarDocumento(notebookId, doc.id);
    reintentandoRef.current.delete(doc.id);
    if (result.success) {
      setDocumentosNotebook(prev => prev.map(d => (d.id === doc.id ? { ...d, estado: result.documento.estado } : d)));
      const tarea = { nombre: doc.nombre_archivo, taskId: result.documento.id_tarea, status: 'procesando', progress: 0 };
      setArchivosSubiendo(prev => [...prev, tarea]);
      pollTaskProgress(tarea.taskId, tarea.nombre, notebookId);
      return;
    }
    if (result.status === 404) {
      setDocumentosNotebook(prev => prev.filter(d => d.id !== doc.id));
      Toast.warning('La fuente ya no está disponible.');
      return;
    }
    if (result.status === 409) {
      Toast.warning(result.message);
      cargarDocumentos(notebookId);
      return;
    }
    Toast.error('Error al reintentar', result.message);
  };

  const handleEliminarDocumento = async (documentoId) => {
    if (!notebookActivo || quitandoRef.current.has(documentoId)) return;
    quitandoRef.current.add(documentoId);
    setEliminandoIds(prev => new Set(prev).add(documentoId));
    const result = await notebookService.eliminarDocumento(notebookActivo.id, documentoId);
    if (result.success) {
      setDocumentosNotebook(prev => prev.filter(d => d.id !== documentoId));
    } else {
      // El documento sigue en la lista: el servidor no lo quitó del todo y un nuevo intento completa lo que faltó.
      Toast.error('Error al quitar el documento', result.message);
    }
    quitandoRef.current.delete(documentoId);
    setEliminandoIds(prev => {
      const siguiente = new Set(prev);
      siguiente.delete(documentoId);
      return siguiente;
    });
  };

  const pedirConfirmacionDeQuitar = (doc) => {
    const pendiente = { id: doc.id, nombre: doc.nombre_archivo };
    confirmacionRef.current = pendiente;
    setDocumentoPorQuitar(pendiente);
  };

  const confirmarQuitar = () => {
    const pendiente = confirmacionRef.current;
    confirmacionRef.current = null;
    if (pendiente) handleEliminarDocumento(pendiente.id);
  };

  // Previsualización: click en un documento ya procesado abre su archivo
  // original (imagen o PDF) para verificar qué dice contra la respuesta del chat.
  // La ventana de vista previa (RF-18): { modo: 'archivo', url, tipo, nombre } para imagen, PDF y audio; { modo: 'texto', texto,
  // truncado, conLinea, nombre } para `.txt`, Word y HTML; { modo: 'error', nombre } si la vista de texto falló.
  const [preview, setPreview] = useState(null);
  const [cargandoPreviewId, setCargandoPreviewId] = useState(null);

  const handleVerArchivo = async (doc) => {
    if (!notebookActivo || doc.estado !== 'Procesado' || cargandoPreviewId) return;
    setCargandoPreviewId(doc.id);
    const extension = (doc.extension || '').toLowerCase();
    if (EXTENSIONES_VISTA_DE_TEXTO.includes(extension)) {
      // `.txt`, Word y HTML: el servidor entrega el texto (RF-18.100, RF-18.106); un `.txt` no lleva la línea de «vista de texto».
      const vista = await notebookService.obtenerVistaTexto(notebookActivo.id, doc.id);
      // Un 404 (la fuente ya no está, quitada en otra pestaña) no abre nada, como con el archivo; otro fallo muestra su aviso (RF-18.107).
      if (vista.success) {
        setPreview({ modo: 'texto', nombre: doc.nombre_archivo, texto: vista.texto, truncado: vista.truncado, conLinea: extension !== '.txt' });
      } else if (vista.status !== 404) {
        setPreview({ modo: 'error', nombre: doc.nombre_archivo });
      }
    } else if (EXTENSIONES_VISTA_DE_IMAGEN.includes(extension)) {
      const vista = await notebookService.obtenerVistaImagen(notebookActivo.id, doc.id);
      if (vista.success) {
        setPreview({ modo: 'imagen', nombre: doc.nombre_archivo, imagen: vista.imagen, paginas: vista.paginas });
      } else if (vista.status !== 404) {
        setPreview({ modo: 'error', nombre: doc.nombre_archivo });
      }
    } else {
      const result = await notebookService.obtenerArchivoPreview(notebookActivo.id, doc.id);
      if (result.success) {
        setPreview({ modo: 'archivo', url: result.url, tipo: result.tipo, nombre: doc.nombre_archivo });
      }
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
      // Un aviso por respuesta, con los motivos tal cual; solo los aceptados siguen a procesamiento (sin polling de los rechazados).
      setAvisoCarga({ id: Date.now(), tema: notebookActivo.nombre, ...armarAvisoCarga(resultado, archivos.map(f => f.name)) });
      const nuevos = (resultado.aceptados?.tareas || []).map(t => ({
        nombre: archivos[t.posicion - 1]?.name,
        taskId: t.id_tarea,
        status: 'procesando',
        progress: 0
      }));
      setArchivosSubiendo(prev => [...prev, ...nuevos]);
      nuevos.forEach(a => pollTaskProgress(a.taskId, a.nombre, notebookActivo.id));
    } catch (error) {
      console.error('Error subiendo archivos al notebook:', error);
      Toast.error('Error al subir', error.message || 'No se pudo subir el archivo. Intente de nuevo.');
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

  // Hay una respuesta en curso si la consulta sigue activa, si hay una burbuja en streaming o si está en la pausa del
  // reintento automático («Reintentando obtener respuesta...»).
  const hayEnCurso = () => Boolean(
    currentRequestRef.current?.active
    || streamingMessageIndex !== null
    || messages.some((m) => m.isRetrying)
  );

  // Cancela la respuesta en curso (RF-15.72, RF-15.73, RF-17.70): cierra la conexión, deja la burbuja con su texto parcial y el
  // aviso, y libera el envío. La marca inactiva no es `null`: con `null` el temporizador del reintento automático relanzaría
  // la consulta (messageUtils.js, `currentRequestRef.current === null`). Devuelve los mensajes ya marcados.
  const cancelarEnCurso = () => {
    if (!hayEnCurso()) return messages;
    consultaService.cancelConsulta();
    currentRequestRef.current = { active: false, id: 'cancelada' };
    const marcados = messages.map((m, i) => {
      if (i !== streamingMessageIndex && !m.isRetrying) return m;
      const base = m.isRetrying ? { ...m, text: '', isRetrying: false } : m;
      return { ...markMessageAsCanceled(base), etapa: undefined };
    });
    setMessages(marcados);
    setStreamingMessageIndex(null);
    setIsTyping(false);
    return marcados;
  };

  // Enter se bloquea con la misma condición que el botón de enviar (RF-17.71): el texto escrito se conserva.
  // Se envían los identificadores de las fuentes marcadas, en cualquier estado: el servidor solo usa las Procesado (RF-11.106).
  const alternarFuente = (id, marcada) => setDesmarcadas((prev) => {
    const siguiente = new Set(prev);
    if (marcada) siguiente.delete(id); else siguiente.add(id);
    return siguiente;
  });
  const sinFuenteMarcada = !documentosNotebook.some((d) => d.estado === 'Procesado' && !desmarcadas.has(d.id));

  const handleEnviarMensaje = () => {
    const query = texto.trim();
    if (!query || hayEnCurso() || sinFuenteMarcada || generandoResultado) return; // RF-11.104: el texto escrito se conserva
    setTexto('');
    enviarPregunta(query);
  };

  // «Guardar en notas» (RF-14.126, RF-14.127): la pregunta que la originó, la respuesta y las fuentes del notebook que nombra.
  const handleGuardarNota = async (indice) => {
    const respuesta = messages[indice];
    if (!respuesta || respuesta.notaGuardada || guardandoNotaRef.current) return;
    guardandoNotaRef.current = true;
    let anterior = indice - 1;
    while (anterior >= 0 && !messages[anterior].isUser) anterior -= 1;
    const pregunta = anterior >= 0 ? messages[anterior].text : '';
    const fuentes = documentosNotebook.map((d) => d.nombre_archivo).filter((nombre) => respuesta.text.includes(nombre));
    const guardada = await estudio.guardarNota({ pregunta, respuesta: respuesta.text, fuentes });
    if (guardada) setMessages((prev) => prev.map((m, i) => (i === indice ? { ...m, notaGuardada: true } : m)));
    guardandoNotaRef.current = false;
  };

  // Reintentar usa el texto de la pregunta original y no lee ni cambia el campo de texto (RF-15.70, RF-15.71).
  const reintentar = (textoPregunta) => {
    cancelarEnCurso();
    enviarPregunta(textoPregunta);
  };

  const enviarPregunta = async (query) => {
    if (!query || !notebookActivo || !sessionId) return;

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

    // La selección se toma al enviar: marcar o desmarcar después no cambia una respuesta en curso (RF-11.102).
    const documentos = documentosNotebook.filter((d) => !desmarcadas.has(d.id)).map((d) => d.id);

    const retryFunction = () => consultaService.consultaGeneralStreaming(
      query, callbacks.onChunk, callbacks.onComplete, callbacks.onError,
      null, sessionId, null, String(notebookActivo.id), callbacks.alRecibir, documentos
    );

    const callbacks = createStreamingCallbacks(
      messageIndex, currentRequestRef, requestId,
      setMessages, setStreamingMessageIndex, setIsTyping,
      retryCountRef, retryFunction
    );

    try {
      await consultaService.consultaGeneralStreaming(
        query, callbacks.onChunk, callbacks.onComplete, callbacks.onError,
        null, sessionId, null, String(notebookActivo.id), callbacks.alRecibir, documentos
      );
    } catch (error) {
      setStreamingMessageIndex(null);
      setIsTyping(false);
      currentRequestRef.current = null;
    }
  };

  return (
    <div
      ref={contenedorRef}
      className="h-full flex bg-gray-50"
      style={{ '--ancho-lista': `${anchos.lista}px`, '--ancho-fuentes': `${anchos.fuentes}px`, '--ancho-estudio': `${anchos.estudio}px` }}
    >
      {/* Panel lateral: lista de notebooks */}
      <div data-testid="columna-lista" className={`${plegados.lista ? 'w-12' : 'w-56 lg:w-[var(--ancho-lista)]'} border-r border-gray-200 bg-white flex flex-col shrink-0`}>
        {plegados.lista && (
          <div className="flex flex-col items-center gap-3 py-3">
            <Button isIconOnly size="sm" variant="light" aria-label="Mostrar lista de notebooks" onPress={() => alternarPanel('lista')}>
              <FiChevronRight />
            </Button>
            <FiBookOpen className="text-[#003d82]" aria-hidden="true" />
          </div>
        )}
        <div className={plegados.lista ? 'hidden' : 'contents'}>
        <div className="p-4 border-b border-gray-200 flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-[#003d82] flex items-center gap-2">
              <FiBookOpen /> NotebookServIA
            </h2>
            <p className="text-xs text-gray-500 mt-1">Tus colecciones de documentos</p>
          </div>
          <Button isIconOnly size="sm" variant="light" className="shrink-0" aria-label="Plegar lista de notebooks" onPress={() => alternarPanel('lista')}>
            <FiChevronLeft />
          </Button>
        </div>

        <div className="p-3 border-b border-gray-200 flex gap-2">
          <Input
            size="sm"
            placeholder="Nombre del notebook"
            value={nuevoNombre}
            onValueChange={(v) => { setNuevoNombre(v); setErrorCreacion(''); }}
            isInvalid={!!errorCreacion}
            errorMessage={errorCreacion}
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
            <p className="text-sm text-gray-400 text-center p-4">Todavía no tiene notebooks. Cree uno arriba.</p>
          ) : (
            notebooks.map(nb => (
              <ItemNotebook
                key={nb.id}
                notebook={nb}
                activo={notebookActivo?.id === nb.id}
                onSeleccionar={() => seleccionarNotebook(nb)}
                onRenombrar={(nombre) => handleRenombrarNotebook(nb, nombre)}
                onEliminar={() => pedirConfirmacionDeEliminar(nb)}
              />
            ))
          )}
        </div>
        </div>
      </div>

      {!plegados.lista && divisor('lista')}

      {/* Área principal */}
      <div className="flex-1 flex flex-col min-w-0">
        {!notebookActivo ? (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <FiBookOpen className="mx-auto mb-2" size={32} />
              <p>Elija o cree un notebook para empezar</p>
            </div>
          </div>
        ) : (
          <>
            {/* Pestañas de pantalla pequeña: un panel a la vez (RNF-04.120); a partir de lg se ven los tres */}
            <div role="tablist" aria-label="Paneles del notebook" className="flex border-b border-gray-200 bg-white lg:hidden">
              {[['fuentes', 'Fuentes'], ['chat', 'Chat'], ['estudio', 'Estudio']].map(([clave, etiqueta]) => (
                <button
                  key={clave}
                  type="button"
                  role="tab"
                  aria-selected={panelVisible === clave}
                  onClick={() => setPanelVisible(clave)}
                  className={`flex-1 px-3 py-2 text-sm font-medium border-b-2 ${
                    panelVisible === clave ? 'border-primary text-primary' : 'border-transparent text-gray-500'
                  }`}
                >
                  {etiqueta}
                  {clave === 'estudio' && generandoResultado && <span className="ml-1 text-xs text-primary">(generando…)</span>}
                </button>
              ))}
            </div>

            <div className="flex-1 flex min-h-0">
            {/* Fuentes: carga de documentos y lista */}
            <aside
              aria-label="Fuentes"
              data-testid="columna-fuentes"
              className={`${panelVisible === 'fuentes' ? 'flex' : 'hidden'} lg:flex flex-col w-full ${plegados.fuentes ? 'lg:w-11 lg:p-1 lg:items-center' : 'lg:w-[var(--ancho-fuentes)]'} lg:shrink-0 min-h-0 overflow-y-auto p-4 border-r border-gray-200 bg-white`}
            >
              <div className={`hidden lg:block ${plegados.fuentes ? '' : 'self-end -mb-7 -mt-2 -mr-2 relative z-10'}`}>
                <Button
                  isIconOnly
                  size="sm"
                  variant="light"
                  aria-label={plegados.fuentes ? 'Mostrar Fuentes' : 'Plegar Fuentes'}
                  onPress={() => alternarPanel('fuentes')}
                >
                  {plegados.fuentes ? <FiChevronRight /> : <FiChevronLeft />}
                </Button>
              </div>
              {plegados.fuentes && (
                <span className="hidden lg:block mt-3 text-xs text-gray-500 [writing-mode:vertical-rl]">Fuentes</span>
              )}
              <div className={plegados.fuentes ? 'contents lg:hidden' : 'contents'}>
              <div className="flex flex-col gap-2 mb-2">
                <h3 className="font-semibold text-gray-800 break-words lg:pr-7">{notebookActivo.nombre}</h3>
                <Button
                  size="sm"
                  variant="flat"
                  className="self-start"
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
              <p className="text-xs text-gray-500 mb-2">
                Las imágenes deben contener texto impreso o tipeado: la escritura a mano no se reconoce de forma confiable.
              </p>

              {/* Archivos seleccionados, en revisión antes de subir */}
              {archivosSeleccionados.length > 0 && (
                <div className="mb-2 border border-gray-200 rounded-lg p-3 bg-gray-50">
                  <p className="text-xs text-gray-500 mb-2">
                    {archivosSeleccionados.length} archivo(s) seleccionado(s) — revise antes de subir:
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
                    Confirmar y subir a &quot;{notebookActivo.nombre}&quot;
                  </Button>
                </div>
              )}

              {/* Aviso fijo de la última carga: confirmación y motivo de cada rechazado; se cierra a mano */}
              {avisoCarga && (
                <Alert
                  key={avisoCarga.id}
                  className="mb-2"
                  color={avisoCarga.tipo}
                  variant="flat"
                  isClosable
                  onClose={() => setAvisoCarga(null)}
                  // `grow-0 shrink-0`: la alerta de HeroUI trae `flex-grow` y, en esta columna, se estiraba hasta llenar el panel.
                  // Sin icono y con menos relleno: el panel es angosto y el texto necesita el ancho; así mide solo lo que ocupa.
                  hideIcon
                  classNames={{
                    base: 'grow-0 shrink-0 min-w-0 py-2 px-3',
                    mainWrapper: 'min-w-0 min-h-0 ms-0',
                    title: 'text-default-800 font-medium break-words',
                    description: 'text-default-700',
                  }}
                  title={`${avisoCarga.tema}: ${avisoCarga.mensaje}`}
                  description={avisoCarga.motivos.length > 0 && (
                    <ul className="list-none space-y-0.5 break-words">
                      {avisoCarga.motivos.map((motivo, i) => <li key={i}>{motivo}</li>)}
                    </ul>
                  )}
                />
              )}

              {/* Documentos ya subidos y procesados — se pueden quitar */}
              {documentosNotebook.length > 0 && (
                <ul aria-label="Fuentes del notebook" className="flex flex-col gap-1 mt-2 list-none p-0">
                  {documentosNotebook.map(doc => (
                    <FuenteNotebook
                      key={doc.id}
                      fuente={doc}
                      marcada={!desmarcadas.has(doc.id)}
                      onAlternar={(marcada) => alternarFuente(doc.id, marcada)}
                      abriendo={cargandoPreviewId === doc.id}
                      quitando={eliminandoIds.has(doc.id)}
                      onAbrir={() => handleVerArchivo(doc)}
                      onQuitar={() => pedirConfirmacionDeQuitar(doc)}
                      onRenombrar={(nombre) => handleRenombrarFuente(doc, nombre)}
                      onReintentar={() => handleReintentarFuente(doc)}
                    />
                  ))}
                </ul>
              )}

              {/* Subidas en curso (todavía no aparecen en la lista persistida) */}
              {archivosSubiendo.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2 min-w-0">
                  {archivosSubiendo.map(a => (
                    // RF-19.117: una línea, nombre recortado con «…», porcentaje siempre visible y el nombre completo en el aviso
                    <Tooltip
                      key={a.taskId}
                      delay={0}
                      closeDelay={0}
                      placement="top"
                      content={<div className="max-w-xs break-all text-small">{a.nombre} — {`${a.progress || 0}%`}</div>}
                    >
                      <span
                        tabIndex={0}
                        role="group"
                        data-testid="subida-en-curso"
                        aria-label={`${a.nombre} — ${a.progress || 0}%`}
                        className="inline-flex max-w-full min-w-0 rounded-full"
                      >
                        <Chip
                          size="sm"
                          startContent={<FiFile className="ml-1" />}
                          color="default"
                          variant="flat"
                          classNames={{ base: 'max-w-full min-w-0', content: 'flex items-center gap-1 min-w-0' }}
                        >
                          <span className="truncate min-w-0">{a.nombre}</span>
                          <span className="shrink-0">{`— ${a.progress || 0}%`}</span>
                        </Chip>
                      </span>
                    </Tooltip>
                  ))}
                </div>
              )}
              </div>
            </aside>

            {!plegados.fuentes && divisor('fuentes')}

            {/* Chat — acepta pegar (Ctrl+V) o arrastrar una imagen, se sube sola al notebook */}
            <section
              aria-label="Chat"
              data-testid="columna-chat"
              className={`${panelVisible === 'chat' ? 'flex' : 'hidden'} lg:flex flex-1 flex-col min-h-0 min-w-0 relative`}
              onDragOver={(e) => { e.preventDefault(); setArrastrandoImagen(true); }}
              onDragLeave={() => setArrastrandoImagen(false)}
              onDrop={handleDropImagen}
            >
              {arrastrandoImagen && (
                <div className="absolute inset-0 z-10 bg-blue-50/90 border-2 border-dashed border-blue-400 rounded-lg flex items-center justify-center pointer-events-none">
                  <p className="text-blue-700 font-medium">Suelte la imagen para subirla a &quot;{notebookActivo.nombre}&quot;</p>
                </div>
              )}
              <MessageList
                compacto
                messages={messages}
                isTyping={isTyping}
                streamingMessageIndex={streamingMessageIndex}
                onRetry={reintentar}
                onGuardarNota={handleGuardarNota}
              />
              {sinFuenteMarcada && (
                <p role="status" className="px-3 pt-2 text-xs text-warning-700 bg-white">Marque al menos una fuente para consultar.</p>
              )}
              {generandoResultado && (
                <p role="status" className="px-3 pt-2 text-xs text-warning-700 bg-white">Hay una generación en curso. Espere o cancélela.</p>
              )}
              <div className="p-3 border-t border-gray-200 bg-white flex gap-2">
                <Input
                  placeholder={`Pregúntele algo a "${notebookActivo.nombre}"... (puede pegar una imagen con Ctrl+V)`}
                  value={texto}
                  onValueChange={setTexto}
                  onKeyDown={(e) => e.key === 'Enter' && handleEnviarMensaje()}
                  onPaste={handlePasteImagen}
                />
                <Button
                  isIconOnly
                  color="primary"
                  onPress={handleEnviarMensaje}
                  isDisabled={isTyping || streamingMessageIndex !== null || sinFuenteMarcada || generandoResultado}
                  aria-label="Enviar"
                >
                  <FiSend />
                </Button>
              </div>
            </section>

            {!plegados.estudio && divisor('estudio')}

            {/* Estudio: generar y consultar resultados guardados (spec 010) */}
            <aside
              aria-label="Panel Estudio"
              data-testid="columna-estudio"
              className={`${panelVisible === 'estudio' ? 'flex' : 'hidden'} lg:flex flex-col w-full ${plegados.estudio ? 'lg:w-11 lg:items-center' : 'lg:w-[var(--ancho-estudio)]'} lg:shrink-0 min-h-0 border-l border-gray-200 bg-white relative`}
            >
              <div className={`hidden lg:block ${plegados.estudio ? 'mt-1' : 'absolute top-2 right-2 z-10'}`}>
                <Button
                  isIconOnly
                  size="sm"
                  variant="light"
                  aria-label={plegados.estudio ? 'Mostrar Estudio' : 'Plegar Estudio'}
                  onPress={() => alternarPanel('estudio')}
                >
                  {plegados.estudio ? <FiChevronLeft /> : <FiChevronRight />}
                </Button>
              </div>
              {plegados.estudio && (
                <span className="hidden lg:block mt-3 text-xs text-gray-500 [writing-mode:vertical-rl]">Estudio</span>
              )}
              <div className={plegados.estudio ? 'contents lg:hidden' : 'contents'}>
                <PanelEstudio estudio={estudio} sinFuenteMarcada={sinFuenteMarcada} />
              </div>
            </aside>
            </div>
          </>
        )}
      </div>

      {/* Previsualización del archivo original — verificar qué dice contra la respuesta del chat */}
      <Modal isOpen={!!preview} onClose={cerrarPreview} size="3xl" scrollBehavior="inside">
        <ModalContent>
          <ModalHeader>{preview?.nombre}</ModalHeader>
          <ModalBody className="pb-6">
            {preview?.modo === 'texto' ? (
              <div>
                {preview.conLinea && (
                  <p className="text-xs text-gray-500 mb-2">Vista de texto: no conserva el formato ni las imágenes del original.</p>
                )}
                {preview.texto === '' ? (
                  <p className="text-gray-500 text-center py-8">
                    {preview.conLinea ? 'El documento no tiene texto que mostrar.' : 'El archivo está vacío.'}
                  </p>
                ) : (
                  // El texto va como hijo (nunca como HTML) y respeta los saltos de línea (RF-18.100, RF-19.118).
                  <pre className="whitespace-pre-wrap break-words max-h-[70vh] overflow-auto text-sm font-sans">{preview.texto}</pre>
                )}
                {preview.truncado && (
                  <p className="text-xs text-gray-500 mt-2">Se muestran los primeros 200.000 caracteres del archivo.</p>
                )}
              </div>
            ) : preview?.modo === 'imagen' ? (
              <div>
                <img src={`data:image/png;base64,${preview.imagen}`} alt={preview.nombre} className="max-w-full h-auto mx-auto" />
                {preview.paginas > 1 && <p className="text-xs text-gray-500 mt-2 text-center">Se muestra la primera página.</p>}
              </div>
            ) : preview?.modo === 'error' ? (
              <p className="text-gray-500 text-center py-8">No se pudo mostrar el documento. Intente de nuevo.</p>
            ) : preview?.tipo?.startsWith('audio/') ? (
              // Reproductor del navegador: barra de progreso que se mueve, tiempo transcurrido y duración (m:ss, y h:mm:ss desde
              // una hora). Sin reproducción automática (RF-18.101, RF-18.102); al cerrar la ventana se desmonta y se detiene.
              preview.audioConError ? (
                <p className="text-gray-500 text-center py-8">Su navegador no puede reproducir este audio.</p>
              ) : (
                <audio
                  controls
                  preload="metadata"
                  src={preview.url}
                  className="w-full"
                  onError={() => setPreview((actual) => (actual ? { ...actual, audioConError: true } : actual))}
                />
              )
            ) : preview?.tipo?.startsWith('image/') ? (
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

      <ConfirmModal
        isOpen={!!notebookPorEliminar}
        onClose={() => setNotebookPorEliminar(null)}
        onConfirm={confirmarEliminar}
        title="Eliminar notebook"
        description={`¿Eliminar "${notebookPorEliminar?.nombre ?? ''}"? Dejará de estar disponible, con sus documentos y su conversación.`}
        confirmText="Eliminar"
        cancelText="Cancelar"
        confirmColor="danger"
      />

      <ConfirmModal
        isOpen={!!documentoPorQuitar}
        onClose={() => setDocumentoPorQuitar(null)}
        onConfirm={confirmarQuitar}
        title="Quitar documento"
        description={`¿Desea eliminar "${documentoPorQuitar?.nombre ?? ''}" de este notebook de forma definitiva?`}
        confirmText="Quitar"
        cancelText="Cancelar"
        confirmColor="danger"
      />
    </div>
  );
};

export default NotebooksPage;
