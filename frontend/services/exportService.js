import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

/**
 * Servicio para exportar reportes de bitácora en formato PDF y CSV
 */

/**
 * Exporta los registros de bitácora a formato PDF
 * @param {Array} registros - Array de registros a exportar
 * @param {Object} filtros - Filtros aplicados para el título del reporte
 */
export const exportarBitacoraPDF = (registros, filtros = {}) => {
  const doc = new jsPDF('l', 'mm', 'a4'); // Landscape para más columnas
  
  // Configuración de colores corporativos
  const colorPrimario = [59, 130, 246]; // Azul
  const colorSecundario = [100, 116, 139]; // Gris
  const colorAcento = [239, 68, 68]; // Rojo
  const colorExito = [34, 197, 94]; // Verde
  
  // ==================== PORTADA ====================
  const pageWidth = doc.internal.pageSize.width;
  const pageHeight = doc.internal.pageSize.height;
  
  // Fondo decorativo superior
  doc.setFillColor(...colorPrimario);
  doc.rect(0, 0, pageWidth, 50, 'F');
  
  // Título principal en portada
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(32);
  doc.setFont(undefined, 'bold');
  doc.text('JusticIA', pageWidth / 2, 25, { align: 'center' });
  
  doc.setFontSize(18);
  doc.setFont(undefined, 'normal');
  doc.text('Reporte de Bitácora del Sistema', pageWidth / 2, 38, { align: 'center' });
  
  // Fecha de generación en portada
  doc.setTextColor(...colorSecundario);
  doc.setFontSize(12);
  const fechaGeneracion = format(new Date(), "dd 'de' MMMM 'de' yyyy, HH:mm", { locale: es });
  doc.text(`Generado el: ${fechaGeneracion}`, pageWidth / 2, 60, { align: 'center' });
  
  // ==================== RESUMEN EJECUTIVO ====================
  doc.setFontSize(16);
  doc.setTextColor(...colorPrimario);
  doc.setFont(undefined, 'bold');
  doc.text('Resumen Ejecutivo', 20, 80);
  
  // Calcular estadísticas
  const totalRegistros = registros.length;
  const usuariosUnicos = [...new Set(registros.map(r => r.usuario).filter(Boolean))].length;
  const tiposAccionUnicos = [...new Set(registros.map(r => r.tipoAccion).filter(Boolean))].length;
  const expedientesUnicos = [...new Set(registros.map(r => r.expediente).filter(Boolean))].length;
  
  // Rango de fechas
  const fechas = registros.map(r => new Date(r.fechaHora)).sort((a, b) => a - b);
  const fechaInicio = fechas[0] ? format(fechas[0], 'dd/MM/yyyy', { locale: es }) : 'N/A';
  const fechaFin = fechas[fechas.length - 1] ? format(fechas[fechas.length - 1], 'dd/MM/yyyy', { locale: es }) : 'N/A';
  
  // Cuadros de estadísticas
  const statsY = 90;
  const statsBoxWidth = 60;
  const statsBoxHeight = 25;
  const statsGap = 8;
  
  // Total de registros
  doc.setFillColor(220, 237, 252); // Azul claro
  doc.roundedRect(20, statsY, statsBoxWidth, statsBoxHeight, 3, 3, 'F');
  doc.setDrawColor(...colorPrimario);
  doc.setLineWidth(0.5);
  doc.roundedRect(20, statsY, statsBoxWidth, statsBoxHeight, 3, 3, 'S');
  doc.setFontSize(24);
  doc.setTextColor(...colorPrimario);
  doc.setFont(undefined, 'bold');
  doc.text(totalRegistros.toString(), 50, statsY + 12, { align: 'center' });
  doc.setFontSize(9);
  doc.setTextColor(...colorSecundario);
  doc.setFont(undefined, 'normal');
  doc.text('Total de Registros', 50, statsY + 20, { align: 'center' });
  
  // Usuarios únicos
  doc.setFillColor(220, 252, 231); // Verde claro
  doc.roundedRect(20 + statsBoxWidth + statsGap, statsY, statsBoxWidth, statsBoxHeight, 3, 3, 'F');
  doc.setDrawColor(...colorExito);
  doc.roundedRect(20 + statsBoxWidth + statsGap, statsY, statsBoxWidth, statsBoxHeight, 3, 3, 'S');
  doc.setFontSize(24);
  doc.setTextColor(...colorExito);
  doc.setFont(undefined, 'bold');
  doc.text(usuariosUnicos.toString(), 50 + statsBoxWidth + statsGap, statsY + 12, { align: 'center' });
  doc.setFontSize(9);
  doc.setTextColor(...colorSecundario);
  doc.setFont(undefined, 'normal');
  doc.text('Usuarios Activos', 50 + statsBoxWidth + statsGap, statsY + 20, { align: 'center' });
  
  // Tipos de acción
  doc.setFillColor(254, 226, 226); // Rojo claro
  doc.roundedRect(20 + (statsBoxWidth + statsGap) * 2, statsY, statsBoxWidth, statsBoxHeight, 3, 3, 'F');
  doc.setDrawColor(...colorAcento);
  doc.roundedRect(20 + (statsBoxWidth + statsGap) * 2, statsY, statsBoxWidth, statsBoxHeight, 3, 3, 'S');
  doc.setFontSize(24);
  doc.setTextColor(...colorAcento);
  doc.setFont(undefined, 'bold');
  doc.text(tiposAccionUnicos.toString(), 50 + (statsBoxWidth + statsGap) * 2, statsY + 12, { align: 'center' });
  doc.setFontSize(9);
  doc.setTextColor(...colorSecundario);
  doc.setFont(undefined, 'normal');
  doc.text('Tipos de Acción', 50 + (statsBoxWidth + statsGap) * 2, statsY + 20, { align: 'center' });
  
  // Expedientes únicos
  doc.setFillColor(237, 233, 254); // Morado claro
  doc.roundedRect(20 + (statsBoxWidth + statsGap) * 3, statsY, statsBoxWidth, statsBoxHeight, 3, 3, 'F');
  doc.setDrawColor(168, 85, 247);
  doc.roundedRect(20 + (statsBoxWidth + statsGap) * 3, statsY, statsBoxWidth, statsBoxHeight, 3, 3, 'S');
  doc.setFontSize(24);
  doc.setTextColor(168, 85, 247);
  doc.setFont(undefined, 'bold');
  doc.text(expedientesUnicos.toString(), 50 + (statsBoxWidth + statsGap) * 3, statsY + 12, { align: 'center' });
  doc.setFontSize(9);
  doc.setTextColor(...colorSecundario);
  doc.setFont(undefined, 'normal');
  doc.text('Expedientes', 50 + (statsBoxWidth + statsGap) * 3, statsY + 20, { align: 'center' });
  
  // Período del reporte
  doc.setFontSize(11);
  doc.setTextColor(...colorSecundario);
  doc.setFont(undefined, 'bold');
  doc.text('Período del Reporte:', 20, statsY + 40);
  doc.setFont(undefined, 'normal');
  doc.text(`Del ${fechaInicio} al ${fechaFin}`, 70, statsY + 40);
  
  // Filtros aplicados
  let yPos = statsY + 50;
  if (Object.keys(filtros).length > 0 && (filtros.usuario || filtros.tipoAccion || filtros.expediente || filtros.fechaInicio || filtros.fechaFin)) {
    doc.setFontSize(11);
    doc.setTextColor(...colorPrimario);
    doc.setFont(undefined, 'bold');
    doc.text('Filtros Aplicados:', 20, yPos);
    
    doc.setFontSize(9);
    doc.setTextColor(...colorSecundario);
    doc.setFont(undefined, 'normal');
    yPos += 7;
    
    if (filtros.usuario) {
      doc.text(`• Usuario: ${filtros.usuario}`, 25, yPos);
      yPos += 5;
    }
    if (filtros.tipoAccion) {
      doc.text(`• Tipo de Acción: ${filtros.tipoAccion}`, 25, yPos);
      yPos += 5;
    }
    if (filtros.expediente) {
      doc.text(`• Expediente: ${filtros.expediente}`, 25, yPos);
      yPos += 5;
    }
    if (filtros.fechaInicio) {
      doc.text(`• Desde: ${format(new Date(filtros.fechaInicio), 'dd/MM/yyyy')}`, 25, yPos);
      yPos += 5;
    }
    if (filtros.fechaFin) {
      doc.text(`• Hasta: ${format(new Date(filtros.fechaFin), 'dd/MM/yyyy')}`, 25, yPos);
      yPos += 5;
    }
    yPos += 5;
  }
  
  // Top 5 usuarios más activos
  const actividadUsuarios = {};
  registros.forEach(reg => {
    if (reg.usuario) {
      actividadUsuarios[reg.usuario] = (actividadUsuarios[reg.usuario] || 0) + 1;
    }
  });
  const topUsuarios = Object.entries(actividadUsuarios)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  
  if (topUsuarios.length > 0) {
    doc.setFontSize(11);
    doc.setTextColor(...colorPrimario);
    doc.setFont(undefined, 'bold');
    doc.text('Usuarios Más Activos:', 20, yPos);
    yPos += 7;
    
    doc.setFontSize(9);
    doc.setTextColor(...colorSecundario);
    doc.setFont(undefined, 'normal');
    
    topUsuarios.forEach(([usuario, cantidad], index) => {
      const porcentaje = ((cantidad / totalRegistros) * 100).toFixed(1);
      doc.text(`${index + 1}. ${usuario}: ${cantidad} registros (${porcentaje}%)`, 25, yPos);
      yPos += 5;
    });
    yPos += 5;
  }
  
  // Agregar nueva página para la tabla
  doc.addPage();
  yPos = 20;
  
  // Encabezado de sección de datos
  doc.setFillColor(...colorPrimario);
  doc.rect(0, 0, pageWidth, 35, 'F');
  
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(18);
  doc.setFont(undefined, 'bold');
  doc.text('Detalle de Registros', 20, 15);
  
  doc.setFontSize(10);
  doc.setFont(undefined, 'normal');
  doc.text(`Total: ${totalRegistros} ${totalRegistros === 1 ? 'registro' : 'registros'}`, 20, 25);
  
  yPos = 45;
  
  // Preparar datos para la tabla
  const tableData = registros.map(reg => {
    // El backend envía "texto" no "detalles" - Mostramos el detalle completo
    const detalles = reg.texto || '-';
    
    return [
      format(new Date(reg.fechaHora), 'dd/MM/yyyy HH:mm', { locale: es }),
      reg.usuario || '-',
      reg.tipoAccion || '-',
      reg.expediente || '-',
      detalles // Detalle completo sin truncar
    ];
  });
  
  // Variable para almacenar la posición Y final
  let finalY = yPos + 50;
  
  // Generar tabla
  autoTable(doc, {
    head: [['Fecha y Hora', 'Usuario', 'Acción', 'Expediente', 'Detalles']],
    body: tableData,
    startY: yPos,
    theme: 'striped',
    headStyles: {
      fillColor: colorPrimario,
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      halign: 'center',
      fontSize: 9,
      cellPadding: 4
    },
    styles: {
      fontSize: 8,
      cellPadding: { top: 4, right: 3, bottom: 4, left: 3 },
      overflow: 'linebreak',
      valign: 'top',
      lineColor: [220, 220, 220],
      lineWidth: 0.1,
      textColor: [50, 50, 50]
    },
    columnStyles: {
      0: { cellWidth: 35, halign: 'center', valign: 'middle', fontStyle: 'bold', textColor: colorPrimario },
      1: { cellWidth: 42, fontStyle: 'normal' },
      2: { cellWidth: 38, fontStyle: 'normal' },
      3: { cellWidth: 38, halign: 'center', fontStyle: 'italic', textColor: [100, 100, 100] },
      4: { cellWidth: 'auto', minCellHeight: 10 }
    },
    alternateRowStyles: {
      fillColor: [248, 250, 252]
    },
    margin: { left: 14, right: 14 },
    didDrawPage: (data) => {
      const currentPage = doc.internal.getCurrentPageInfo().pageNumber;
      const pageSize = doc.internal.pageSize;
      const pageHeight = pageSize.height ? pageSize.height : pageSize.getHeight();
      
      // Pie de página con diseño mejorado
      doc.setDrawColor(220, 220, 220);
      doc.setLineWidth(0.3);
      doc.line(14, pageHeight - 15, pageWidth - 14, pageHeight - 15);
      
      doc.setFontSize(8);
      doc.setTextColor(120, 120, 120);
      doc.setFont(undefined, 'normal');
      
      // Información izquierda
      doc.text(
        `Página ${currentPage}`,
        data.settings.margin.left,
        pageHeight - 8
      );
      
      // Información central
      doc.text(
        'Reporte Confidencial - JusticIA',
        pageWidth / 2,
        pageHeight - 8,
        { align: 'center' }
      );
      
      // Información derecha
      doc.text(
        `© ${new Date().getFullYear()}`,
        pageWidth - 14,
        pageHeight - 8,
        { align: 'right' }
      );
      
      // Guardar la posición Y final
      if (data.cursor) {
        finalY = data.cursor.y;
      }
    }
  });
  
  // Página final con resumen
  const paginasTotales = doc.internal.getNumberOfPages();
  
  // Resumen en la última página de tabla
  if (finalY + 40 < pageHeight - 20) {
    // Hay espacio en la página actual
    yPos = finalY + 15;
  } else {
    // Nueva página para resumen
    doc.addPage();
    yPos = 20;
  }
  
  // Línea separadora
  doc.setDrawColor(...colorPrimario);
  doc.setLineWidth(0.5);
  doc.line(14, yPos, pageWidth - 14, yPos);
  yPos += 10;
  
  // Resumen final
  doc.setFontSize(14);
  doc.setTextColor(...colorPrimario);
  doc.setFont(undefined, 'bold');
  doc.text('Resumen del Reporte', 14, yPos);
  yPos += 10;
  
  doc.setFontSize(10);
  doc.setTextColor(...colorSecundario);
  doc.setFont(undefined, 'normal');
  
  doc.text(`- Total de registros exportados: ${totalRegistros}`, 20, yPos);
  yPos += 7;
  doc.text(`- Usuarios únicos: ${usuariosUnicos}`, 20, yPos);
  yPos += 7;
  doc.text(`- Tipos de acción: ${tiposAccionUnicos}`, 20, yPos);
  yPos += 7;
  doc.text(`- Expedientes involucrados: ${expedientesUnicos}`, 20, yPos);
  yPos += 7;
  doc.text(`- Período: ${fechaInicio} - ${fechaFin}`, 20, yPos);
  yPos += 10;
  
  // Nota al pie
  doc.setFontSize(8);
  doc.setTextColor(150, 150, 150);
  doc.setFont(undefined, 'italic');
  doc.text(
    'Este reporte ha sido generado automáticamente por el Sistema JusticIA.',
    14,
    yPos
  );
  doc.text(
    'La información contenida es confidencial y de uso exclusivo autorizado.',
    14,
    yPos + 5
  );
  
  // Actualizar números de página con el total correcto
  const totalPages = doc.internal.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    const pageSize = doc.internal.pageSize;
    const pageHeight = pageSize.height ? pageSize.height : pageSize.getHeight();
    
    // Actualizar solo el número de página
    doc.setFontSize(8);
    doc.setTextColor(120, 120, 120);
    doc.text(
      `Página ${i} de ${totalPages}`,
      14,
      pageHeight - 8
    );
  }
  
  // Guardar el archivo
  const nombreArchivo = `bitacora_${format(new Date(), 'yyyyMMdd_HHmmss')}.pdf`;
  doc.save(nombreArchivo);
};

/**
 * Exporta los registros de bitácora a formato CSV
 * @param {Array} registros - Array de registros a exportar
 */
export const exportarBitacoraCSV = (registros) => {
  // Encabezados
  const headers = ['Fecha y Hora', 'Usuario', 'Correo', 'Acción', 'Expediente', 'Detalles'];
  
  // Convertir registros a filas CSV
  const rows = registros.map(reg => [
    format(new Date(reg.fechaHora), 'dd/MM/yyyy HH:mm', { locale: es }),
    reg.usuario || '',
    reg.correoUsuario || '',
    reg.tipoAccion || '',
    reg.expediente || '',
    reg.texto ? reg.texto.replace(/"/g, '""').replace(/\n/g, ' ') : ''
  ]);
  
  // Construir contenido CSV
  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
  ].join('\n');
  
  // Agregar BOM para compatibilidad con Excel y caracteres especiales
  const BOM = '\uFEFF';
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
  
  // Crear enlace de descarga
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  const nombreArchivo = `Bitacora_${format(new Date(), 'yyyyMMdd_HHmmss')}.csv`;
  
  link.setAttribute('href', url);
  link.setAttribute('download', nombreArchivo);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
