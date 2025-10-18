import React from 'react';
import { Chip } from '@heroui/react';

/**
 * InformacionAdicionalRenderer
 * 
 * Componente especializado para renderizar la información adicional de cada tipo de acción
 * de forma estructurada y legible según el contexto del módulo.
 * 
 * Tipos de acción soportados:
 * 1. CONSULTA (1) - Consultas generales
 * 2. CARGA_DOCUMENTOS (2) - Ingesta de documentos
 * 3. BUSQUEDA_SIMILARES (3) - Búsqueda de casos similares
 * 4. LOGIN (4) - Autenticación
 * 5. CREAR_USUARIO (5) - Creación de usuarios
 * 6. EDITAR_USUARIO (6) - Edición de usuarios
 * 7. CONSULTAR_BITACORA (7) - Consultas de bitácora
 * 8. EXPORTAR_BITACORA (8) - Exportación de bitácora
 */

const InformacionAdicionalRenderer = ({ informacionAdicional, tipoAccionId }) => {
  if (!informacionAdicional || typeof informacionAdicional !== 'object') {
    return (
      <div className="bg-gray-50 p-3 rounded-lg">
        <p className="text-sm text-gray-400 italic">Sin información adicional</p>
      </div>
    );
  }

  // Función helper para formatear nombres de campos
  const formatearNombreCampo = (key) => {
    return key
      .replace(/_/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Función helper para renderizar un campo simple
  const renderizarCampo = (label, valor, options = {}) => {
    const { 
      fullWidth = false, 
      isArray = false, 
      isObject = false,
      highlight = false,
      badge = false,
      codigo = false
    } = options;

    // Si el valor es null o undefined
    if (valor === null || valor === undefined || valor === '') {
      return (
        <div key={label} className={`flex flex-col space-y-1 bg-gray-50 p-3 rounded-lg ${fullWidth ? 'col-span-2' : ''}`}>
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            {label}
          </span>
          <span className="text-sm text-gray-400 italic">Sin información</span>
        </div>
      );
    }

    // Si es un array
    if (isArray || Array.isArray(valor)) {
      return (
        <div key={label} className={`flex flex-col space-y-2 bg-gray-50 p-3 rounded-lg ${fullWidth ? 'col-span-2' : ''}`}>
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            {label}
          </span>
          <div className="flex flex-wrap gap-2">
            {valor.length > 0 ? (
              valor.map((item, idx) => (
                <Chip key={idx} size="sm" variant="flat" color="primary">
                  {item}
                </Chip>
              ))
            ) : (
              <span className="text-sm text-gray-400 italic">Vacío</span>
            )}
          </div>
        </div>
      );
    }

    // Si es un objeto, expandirlo en sub-campos
    if (isObject || typeof valor === 'object') {
      return (
        <div key={label} className={`flex flex-col space-y-2 bg-gray-50 p-3 rounded-lg ${fullWidth ? 'col-span-2' : ''}`}>
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            {label}
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {Object.entries(valor).map(([subKey, subValue]) => (
              <div key={subKey} className="bg-white p-2 rounded border border-gray-200">
                <div className="text-xs text-gray-500 font-medium mb-1">
                  {formatearNombreCampo(subKey)}
                </div>
                <div className="text-sm text-gray-900 font-medium">
                  {subValue !== null && subValue !== undefined && subValue !== ''
                    ? (typeof subValue === 'object' 
                        ? JSON.stringify(subValue) 
                        : String(subValue))
                    : <span className="text-gray-400 italic text-xs">-</span>
                  }
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    // Valor simple
    return (
      <div key={label} className={`flex flex-col space-y-1 bg-gray-50 p-3 rounded-lg ${fullWidth ? 'col-span-2' : ''}`}>
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          {label}
        </span>
        {badge ? (
          <Chip size="sm" variant="flat" color={highlight ? "success" : "default"}>
            {String(valor)}
          </Chip>
        ) : codigo ? (
          <code className="text-sm font-mono text-gray-900 bg-white px-2 py-1 rounded border border-gray-200">
            {String(valor)}
          </code>
        ) : (
          <span className={`text-sm font-medium ${highlight ? 'text-primary-600 font-semibold' : 'text-gray-900'}`}>
            {String(valor)}
          </span>
        )}
      </div>
    );
  };

  // Renderizado específico según tipo de acción
  const renderizarPorTipo = () => {
    switch (tipoAccionId) {
      
      // ============================================
      // BUSQUEDA_SIMILARES (1) - Búsqueda de casos similares
      // ============================================
      case 1: {
        const { 
          modo_busqueda, texto_consulta, numero_expediente, 
          limite, umbral_similitud, total_resultados,
          tiempo_busqueda_segundos, precision_promedio, top_expedientes,
          error, tipo_error
        } = informacionAdicional;
        
        return (
          <>
            {modo_busqueda && renderizarCampo('Modo de Búsqueda', modo_busqueda, { badge: true })}
            {texto_consulta && renderizarCampo('Texto de Consulta', texto_consulta, { fullWidth: true })}
            {numero_expediente && renderizarCampo('Número de Expediente', numero_expediente, { codigo: true })}
            {limite && renderizarCampo('Límite de Resultados', limite)}
            {umbral_similitud && renderizarCampo('Umbral de Similitud', umbral_similitud)}
            {total_resultados !== undefined && renderizarCampo('Total de Resultados', total_resultados, { highlight: true })}
            {tiempo_busqueda_segundos && renderizarCampo('Tiempo de Búsqueda (seg)', tiempo_busqueda_segundos, { highlight: true })}
            {precision_promedio && renderizarCampo('Precisión Promedio', precision_promedio, { highlight: true })}
            {top_expedientes && renderizarCampo('Top Expedientes Encontrados', top_expedientes, { isArray: true, fullWidth: true })}
            {error && renderizarCampo('Error', error, { fullWidth: true })}
            {tipo_error && renderizarCampo('Tipo de Error', tipo_error, { badge: true })}
          </>
        );
      }

      // ============================================
      // CARGA_DOCUMENTOS (2) - Ingesta de documentos
      // ============================================
      case 2: {
        const { 
          task_id, expediente, archivo, fase, documento_id,
          num_chunks, num_vectores, collection
        } = informacionAdicional;
        
        return (
          <>
            {expediente && renderizarCampo('Expediente', expediente, { codigo: true, highlight: true })}
            {archivo && renderizarCampo('Archivo', archivo, { fullWidth: true })}
            {fase && renderizarCampo('Fase', fase, { badge: true })}
            {task_id && renderizarCampo('Task ID', task_id, { codigo: true, fullWidth: true })}
            {documento_id && renderizarCampo('ID del Documento', documento_id)}
            {num_chunks && renderizarCampo('Número de Chunks', num_chunks, { highlight: true })}
            {num_vectores && renderizarCampo('Número de Vectores', num_vectores, { highlight: true })}
            {collection && renderizarCampo('Colección', collection, { badge: true })}
          </>
        );
      }

      // ============================================
      // LOGIN (3) - Autenticación
      // ============================================
      case 3: {
        const { email, rol, resultado, motivo, timestamp } = informacionAdicional;
        
        return (
          <>
            {renderizarCampo('Email', email)}
            {resultado && renderizarCampo('Resultado', resultado, { badge: true, highlight: resultado === 'exitoso' })}
            {rol && renderizarCampo('Rol', rol, { badge: true })}
            {motivo && renderizarCampo('Motivo', motivo)}
            {timestamp && renderizarCampo('Timestamp', timestamp)}
          </>
        );
      }

      // ============================================
      // LOGOUT (4) - Cierre de sesión
      // ============================================
      case 4: {
        const { usuario, duracion_sesion, ip, timestamp } = informacionAdicional;
        
        return (
          <>
            {usuario && renderizarCampo('Usuario', usuario)}
            {duracion_sesion && renderizarCampo('Duración de Sesión', duracion_sesion)}
            {ip && renderizarCampo('Dirección IP', ip, { codigo: true })}
            {timestamp && renderizarCampo('Timestamp', timestamp)}
          </>
        );
      }

      // ============================================
      // CAMBIO_CONTRASENA (5) - Cambio de contraseña
      // ============================================
      case 5: {
        const { usuario, tipo, forzado, ip, timestamp } = informacionAdicional;
        
        return (
          <>
            {usuario && renderizarCampo('Usuario', usuario)}
            {tipo && renderizarCampo('Tipo', tipo, { badge: true })}
            {forzado !== undefined && renderizarCampo('Forzado', forzado ? 'Sí' : 'No', { badge: true, highlight: forzado })}
            {ip && renderizarCampo('Dirección IP', ip, { codigo: true })}
            {timestamp && renderizarCampo('Timestamp', timestamp)}
          </>
        );
      }

      // ============================================
      // RECUPERACION_CONTRASENA (6) - Recuperación de contraseña
      // ============================================
      case 6: {
        const { email, metodo, codigo_enviado, expiracion, timestamp } = informacionAdicional;
        
        return (
          <>
            {email && renderizarCampo('Email', email)}
            {metodo && renderizarCampo('Método', metodo, { badge: true })}
            {codigo_enviado !== undefined && renderizarCampo('Código Enviado', codigo_enviado ? 'Sí' : 'No', { badge: true })}
            {expiracion && renderizarCampo('Expiración', expiracion)}
            {timestamp && renderizarCampo('Timestamp', timestamp)}
          </>
        );
      }

      // ============================================
      // CREAR_USUARIO (7) - Creación de usuarios
      // ============================================
      case 7: {
        const { usuario_creado_cedula, nombre_usuario, email, rol_id, nombre_completo, modulo, timestamp } = informacionAdicional;
        
        return (
          <>
            {renderizarCampo('Cédula del Usuario Creado', usuario_creado_cedula, { codigo: true })}
            {nombre_completo && renderizarCampo('Nombre Completo', nombre_completo, { highlight: true })}
            {nombre_usuario && renderizarCampo('Nombre de Usuario', nombre_usuario)}
            {email && renderizarCampo('Correo Electrónico', email)}
            {rol_id && renderizarCampo('ID del Rol', rol_id, { badge: true })}
            {modulo && renderizarCampo('Módulo', modulo, { badge: true })}
            {timestamp && renderizarCampo('Timestamp', timestamp, { fullWidth: true })}
          </>
        );
      }

      // ============================================
      // EDITAR_USUARIO (8) - Edición de usuarios
      // ============================================
      case 8: {
        const { usuario_editado_id, cambios, campos_modificados, accion, usuario_reseteado_id, tipo_reseteo, modulo, timestamp } = informacionAdicional;
        
        return (
          <>
            {usuario_editado_id && renderizarCampo('Usuario Editado (Cédula)', usuario_editado_id, { codigo: true })}
            {usuario_reseteado_id && renderizarCampo('Usuario Reseteado (Cédula)', usuario_reseteado_id, { codigo: true })}
            {accion && renderizarCampo('Acción', accion, { badge: true })}
            {tipo_reseteo && renderizarCampo('Tipo de Reseteo', tipo_reseteo, { badge: true })}
            {campos_modificados && renderizarCampo('Campos Modificados', campos_modificados, { isArray: true, fullWidth: true })}
            {cambios && renderizarCampo('Cambios Realizados', cambios, { isObject: true, fullWidth: true })}
            {modulo && renderizarCampo('Módulo', modulo, { badge: true })}
            {timestamp && renderizarCampo('Timestamp', timestamp, { fullWidth: true })}
          </>
        );
      }

      // ============================================
      // CONSULTAR_USUARIOS (9) - Consulta de usuarios
      // ============================================
      case 9: {
        const { accion, usuario_consultado_id, modulo, timestamp } = informacionAdicional;
        
        return (
          <>
            {accion && renderizarCampo('Acción', accion, { badge: true })}
            {usuario_consultado_id && renderizarCampo('Usuario Consultado', usuario_consultado_id, { codigo: true })}
            {modulo && renderizarCampo('Módulo', modulo, { badge: true })}
            {timestamp && renderizarCampo('Timestamp', timestamp)}
          </>
        );
      }

      // ============================================
      // DESCARGAR_ARCHIVO (10) - Descarga de archivos
      // ============================================
      case 10: {
        const { expediente, archivo, tamanio_bytes, tipo_mime, tipo, timestamp } = informacionAdicional;
        
        return (
          <>
            {expediente && renderizarCampo('Expediente', expediente, { codigo: true })}
            {archivo && renderizarCampo('Archivo', archivo, { fullWidth: true })}
            {tipo && renderizarCampo('Tipo de Acceso', tipo, { badge: true })}
            {tamanio_bytes && renderizarCampo('Tamaño (bytes)', tamanio_bytes)}
            {tipo_mime && renderizarCampo('Tipo MIME', tipo_mime, { badge: true })}
            {timestamp && renderizarCampo('Timestamp', timestamp)}
          </>
        );
      }

      // ============================================
      // LISTAR_ARCHIVOS (11) - Listar archivos de expediente
      // ============================================
      case 11: {
        const { expediente, cantidad_archivos, timestamp } = informacionAdicional;
        
        return (
          <>
            {expediente && renderizarCampo('Expediente', expediente, { codigo: true })}
            {cantidad_archivos !== undefined && renderizarCampo('Cantidad de Archivos', cantidad_archivos, { highlight: true })}
            {timestamp && renderizarCampo('Timestamp', timestamp)}
          </>
        );
      }

      // ============================================
      // CONSULTA_RAG (12) - Consultas conversacionales IA
      // ============================================
      case 12: {
        const { pregunta, session_id, expediente, top_k, documentos_recuperados, tiempo_respuesta_segundos, timestamp } = informacionAdicional;
        
        return (
          <>
            {pregunta && renderizarCampo('Pregunta', pregunta, { fullWidth: true })}
            {session_id && renderizarCampo('Session ID', session_id, { codigo: true })}
            {expediente && renderizarCampo('Expediente', expediente, { codigo: true })}
            {top_k && renderizarCampo('Top K Documentos', top_k)}
            {documentos_recuperados !== undefined && renderizarCampo('Documentos Recuperados', documentos_recuperados, { highlight: true })}
            {tiempo_respuesta_segundos && renderizarCampo('Tiempo de Respuesta (seg)', tiempo_respuesta_segundos, { highlight: true })}
            {timestamp && renderizarCampo('Timestamp', timestamp)}
          </>
        );
      }

      // ============================================
      // GENERAR_RESUMEN (13) - Generación de resúmenes con IA
      // ============================================
      case 13: {
        const { expedientes, cantidad_expedientes, tipo_resumen, tiempo_generacion_segundos, timestamp } = informacionAdicional;
        
        return (
          <>
            {expedientes && renderizarCampo('Expedientes', expedientes, { isArray: true, fullWidth: true })}
            {cantidad_expedientes !== undefined && renderizarCampo('Cantidad de Expedientes', cantidad_expedientes, { highlight: true })}
            {tipo_resumen && renderizarCampo('Tipo de Resumen', tipo_resumen, { badge: true })}
            {tiempo_generacion_segundos && renderizarCampo('Tiempo de Generación (seg)', tiempo_generacion_segundos, { highlight: true })}
            {timestamp && renderizarCampo('Timestamp', timestamp)}
          </>
        );
      }

      // ============================================
      // CONSULTAR_BITACORA (14) - Consultas de bitácora
      // ============================================
      case 14: {
        const { filtros_aplicados, total_registros, timestamp } = informacionAdicional;
        
        return (
          <>
            {total_registros !== undefined && renderizarCampo('Total de Registros', total_registros, { highlight: true })}
            {filtros_aplicados && renderizarCampo('Filtros Aplicados', filtros_aplicados, { isObject: true, fullWidth: true })}
            {timestamp && renderizarCampo('Timestamp', timestamp)}
          </>
        );
      }

      // ============================================
      // EXPORTAR_BITACORA (15) - Exportación de bitácora
      // ============================================
      case 15: {
        const { formato, total_registros, filtros_aplicados, timestamp } = informacionAdicional;
        
        return (
          <>
            {formato && renderizarCampo('Formato de Exportación', formato, { badge: true })}
            {total_registros !== undefined && renderizarCampo('Total de Registros', total_registros, { highlight: true })}
            {filtros_aplicados && renderizarCampo('Filtros Aplicados', filtros_aplicados, { isObject: true, fullWidth: true })}
            {timestamp && renderizarCampo('Timestamp', timestamp, { fullWidth: true })}
          </>
        );
      }

      // ============================================
      // DEFAULT - Renderizado genérico para tipos no específicamente manejados
      // ============================================
      default: {
        // Renderizado genérico para tipos no específicamente manejados
        return Object.entries(informacionAdicional).map(([key, value]) => {
          const esArray = Array.isArray(value);
          const esObjeto = typeof value === 'object' && !esArray && value !== null;
          const fullWidth = key.includes('consulta') || key.includes('texto') || key.includes('descripcion') || esObjeto || esArray;
          
          return renderizarCampo(
            formatearNombreCampo(key),
            value,
            { 
              isArray: esArray,
              isObject: esObjeto,
              fullWidth: fullWidth
            }
          );
        });
      }
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {renderizarPorTipo()}
    </div>
  );
};

export default InformacionAdicionalRenderer;
