/**
 * Utilidades para procesamiento de Markdown y manejo de archivos
 * Consolida toda la lógica de procesamiento de contenido de MessageBubble.jsx
 */

// ============================================
// PROCESAMIENTO DE ARCHIVOS
// ============================================

/**
 * Procesa una ruta de archivo completa y extrae información útil
 */
export const processFilePath = (rutaCompleta) => {
  const rutaLimpia = rutaCompleta.trim();
  const fileName = decodeURIComponent(rutaLimpia.split('/').pop() || 'archivo');
  const base64Path = Buffer.from(rutaLimpia).toString('base64');
  return { fileName, base64Path, rutaLimpia };
};

/**
 * Limpia las rutas de archivo del texto para copiar
 */
export const cleanFilePathsForCopy = (text) => {
  if (!text) return '';
  
  return text
    // Patrón 1: Limpiar rutas dentro de paréntesis (uploads/...)
    .replace(/\(([^)]*uploads\/[^)]+)\)/g, (match, ruta) => {
      const { fileName } = processFilePath(ruta);
      return `(${fileName})`;
    })
    // Patrón 2: Limpiar rutas sueltas uploads/ en el texto
    .replace(/uploads\/[^\s\[\]()]+/g, (match) => {
      const { fileName } = processFilePath(match);
      return fileName;
    });
};

/**
 * Convierte rutas de archivo en enlaces descargables con formato Markdown
 */
export const processFileLinks = (text) => {
  return text
    // Patrón 1: Formato correcto con paréntesis (uploads/...)
    .replace(/\(([^)]*uploads\/[^)]+)\)/g, (match, ruta) => {
      const { fileName, base64Path } = processFilePath(ruta);
      return `([${fileName}](#download-${base64Path}))`;
    })
    // Patrón 2: Cualquier ruta uploads/ suelta en el texto
    .replace(/(uploads\/[^\s\[\]()]+)/g, (match, ruta) => {
      // Solo convertir si no está ya dentro de un enlace markdown
      if (text.indexOf(`#download-`) !== -1 && text.indexOf(ruta) > text.lastIndexOf(`#download-`)) {
        return match;
      }
      const { fileName, base64Path } = processFilePath(ruta);
      return `[${fileName}](#download-${base64Path})`;
    });
};

// ============================================
// PREPROCESAMIENTO DE MARKDOWN
// ============================================

/**
 * Limpia tags HTML del LLM y prepara el contenido para renderizado
 */
export const preprocessMarkdown = (text) => {
  return text
    // Reemplazar <br> y <br/> y <br /> con saltos de línea Markdown
    .replace(/<br\s*\/?>/gi, '  \n')
    // Reemplazar múltiples <br> consecutivos con doble salto (nuevo párrafo)
    .replace(/(<br\s*\/?>\s*){2,}/gi, '\n\n')
    // Eliminar otros tags HTML comunes que el LLM pueda generar
    .replace(/<\/?strong>/gi, '**')
    .replace(/<\/?b>/gi, '**')
    .replace(/<\/?em>/gi, '*')
    .replace(/<\/?i>/gi, '*')
    // Limpiar cualquier otro tag HTML residual
    .replace(/<[^>]+>/g, '')
    // CRÍTICO: Prevenir auto-numeración de listas en streaming
    // Agregar zero-width space antes de números que empiezan línea
    .replace(/^(\d+)\.\s/gm, '\u200B$1. ')
    .replace(/^(\d+)\)\s/gm, '\u200B$1) ');
};

/**
 * Procesa el contenido completo: limpia HTML y convierte enlaces de archivos
 */
export const processMarkdownContent = (content) => {
  if (!content) return '';
  return processFileLinks(preprocessMarkdown(content));
};

// ============================================
// CONVERSIÓN MARKDOWN → HTML
// ============================================

/**
 * Convierte Markdown a HTML para copiar con formato
 */
export const markdownToHtml = (text) => {
  if (!text) return '';
  
  let html = text
    // Convertir negritas
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/__(.+?)__/g, '<strong>$1</strong>')
    // Convertir itálicas
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/_(.+?)_/g, '<em>$1</em>')
    // Convertir encabezados
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Convertir enlaces [texto](url) -> texto
    .replace(/\[(.+?)\]\(.+?\)/g, '$1')
    // Convertir bloques de código inline
    .replace(/`(.+?)`/g, '<code>$1</code>')
    // Convertir citas en bloque
    .replace(/^>\s+(.+)$/gm, '<blockquote>$1</blockquote>')
    // Convertir listas con viñetas (detectar líneas que empiezan con -, *, +)
    .replace(/^\s*[-*+]\s+(.+)$/gm, '<li>$1</li>')
    // Convertir listas numeradas
    .replace(/^\s*\d+\.\s+(.+)$/gm, '<li>$1</li>')
    // Convertir saltos de línea
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');
  
  // Envolver listas en <ul>
  html = html.replace(/(<li>.*?<\/li>)/gs, (match) => {
    return `<ul>${match}</ul>`;
  });
  
  // Envolver en párrafos si no tiene tags de bloque
  if (!html.includes('<h') && !html.includes('<ul>') && !html.includes('<blockquote>')) {
    html = `<p>${html}</p>`;
  }
  
  return html;
};

/**
 * Convierte Markdown a texto plano (sin formato)
 */
export const markdownToPlainText = (text) => {
  if (!text) return '';
  
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^\s*[-*+]\s+/gm, '• ')
    .replace(/\[(.+?)\]\(.+?\)/g, '$1');
};

// ============================================
// COPIADO AL PORTAPAPELES
// ============================================

/**
 * Copia texto al portapapeles con formato HTML y texto plano
 */
export const copyToClipboard = async (text) => {
  if (!text) return false;

  try {
    // Limpiar las rutas del texto antes de copiar
    const cleanedText = cleanFilePathsForCopy(text);
    
    const html = markdownToHtml(cleanedText);
    const plainText = markdownToPlainText(cleanedText);
    
    // Crear blobs
    const blob = new Blob([html], { type: 'text/html' });
    const blobPlain = new Blob([plainText], { type: 'text/plain' });
    
    // Usar ClipboardItem para copiar con formato
    const clipboardItem = new ClipboardItem({
      'text/html': blob,
      'text/plain': blobPlain
    });
    
    await navigator.clipboard.write([clipboardItem]);
    return true;
  } catch (err) {
    // Fallback a texto plano si falla
    try {
      const cleanedText = cleanFilePathsForCopy(text);
      await navigator.clipboard.writeText(cleanedText);
      return true;
    } catch (fallbackErr) {
      return false;
    }
  }
};
