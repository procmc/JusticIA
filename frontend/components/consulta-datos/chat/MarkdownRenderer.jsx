/**
 * Componente independiente para renderizar contenido Markdown con estilos personalizados
 * Incluye componentes de ReactMarkdown y manejo de enlaces de descarga
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { processMarkdownContent } from '../../../utils/chat/markdownUtils';

/**
 * Componentes personalizados para elementos Markdown
 */
const markdownComponents = {
  // Párrafos con justificación
  p: ({ children }) => (
    <p className="mb-4 leading-relaxed text-gray-800 last:mb-0 text-justify">
      {children}
    </p>
  ),
  
  // Encabezados con mejor espaciado
  h1: ({ children }) => (
    <h1 className="text-lg font-bold text-gray-900 mb-3 mt-4 first:mt-0 text-left">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-base font-semibold text-gray-900 mb-2 mt-3 first:mt-0 text-left">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-semibold text-gray-900 mb-2 mt-3 first:mt-0 text-left">
      {children}
    </h3>
  ),
  
  // Listas con bullets justificadas
  ul: ({ children }) => (
    <ul className="list-disc list-outside mb-4 space-y-2 ml-6">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-outside mb-4 space-y-2 ml-6">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="text-gray-800 leading-relaxed text-justify">
      {children}
    </li>
  ),
  
  // Texto en negrita
  strong: ({ children }) => (
    <strong className="font-semibold text-gray-900">
      {children}
    </strong>
  ),
  
  // Texto en cursiva
  em: ({ children }) => (
    <em className="italic text-gray-800">
      {children}
    </em>
  ),
  
  // Código inline
  code: ({ children, className, ...props }) => {
    // Si no tiene className, es código inline
    if (!className) {
      return (
        <code className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-sm font-mono">
          {children}
        </code>
      );
    }
    // Si tiene className, es un bloque de código
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
  
  // Bloques de código
  pre: ({ children }) => (
    <pre className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4 overflow-x-auto">
      {children}
    </pre>
  ),
  
  // Enlaces
  a: ({ href, children }) => {
    // Si es un enlace de descarga de archivo (hash especial #download-)
    if (href && href.startsWith('#download-')) {
      return (
        <a 
          href={href}
          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 underline hover:bg-blue-50 px-2 py-1 rounded transition-colors cursor-pointer"
          title="Hacer clic para descargar el archivo"
        >
          {children}
        </a>
      );
    }
    
    // Enlace normal
    return (
      <a 
        href={href} 
        className="text-blue-600 hover:text-blue-800 underline"
        target="_blank"
        rel="noopener noreferrer"
      >
        {children}
      </a>
    );
  },
  
  // Citas/blockquotes
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-blue-200 pl-4 italic text-gray-700 mb-4 text-justify">
      {children}
    </blockquote>
  ),
  
  // Líneas horizontales con mejor espaciado
  hr: () => (
    <hr className="border-t-2 border-gray-300 my-6" />
  ),
  
  // Tablas
  table: ({ children }) => (
    <div className="overflow-x-auto mb-4">
      <table className="min-w-full border border-gray-200 rounded-lg">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-gray-50">
      {children}
    </thead>
  ),
  th: ({ children }) => (
    <th className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-900">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border border-gray-200 px-3 py-2 text-gray-800">
      {children}
    </td>
  ),
};

/**
 * Componente principal para renderizar Markdown
 */
const MarkdownRenderer = ({ content, forceKey, onMessageClick }) => {
  if (!content) return null;

  // Procesar el contenido (limpiar HTML y convertir enlaces de archivos)
  const cleanContent = processMarkdownContent(content);

  return (
    <div className="markdown-content" onClick={onMessageClick}>
      <ReactMarkdown 
        key={`markdown-${forceKey}-${content.length}`}
        remarkPlugins={[remarkGfm]}
        components={markdownComponents}
      >
        {cleanContent}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;
