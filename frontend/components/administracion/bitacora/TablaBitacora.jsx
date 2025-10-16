import React, { useState, useEffect } from 'react';
import {
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Button,
  Chip,
  Pagination,
  Card,
  CardBody,
  CardHeader
} from '@heroui/react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { IoList, IoDocumentText } from 'react-icons/io5';
import { EyeIcon } from '../../icons';

const TablaBitacora = ({ registros, onVerDetalle, cargando = false, paginacion = null, onCambiarPagina = null }) => {
  // Si hay paginación server-side, usarla; si no, paginación client-side (legacy)
  const usarPaginacionServidor = paginacion && onCambiarPagina;
  
  // Paginación client-side (solo si no hay paginación server-side)
  const [paginaActualLocal, setPaginaActualLocal] = useState(1);
  const registrosPorPagina = 10;

  // Resetear a página 1 cuando cambien los registros (por filtros) - solo client-side
  useEffect(() => {
    if (!usarPaginacionServidor) {
      setPaginaActualLocal(1);
    }
  }, [registros.length, usarPaginacionServidor]);

  // Calcular registros para la página actual - solo client-side
  const indiceInicio = (paginaActualLocal - 1) * registrosPorPagina;
  const indiceFin = indiceInicio + registrosPorPagina;
  const registrosPagina = usarPaginacionServidor ? registros : registros.slice(indiceInicio, indiceFin);
  const totalPaginas = usarPaginacionServidor ? paginacion.pages : Math.ceil(registros.length / registrosPorPagina);
  const paginaActual = usarPaginacionServidor ? paginacion.page : paginaActualLocal;

  // Ajustar página si está fuera de rango - solo client-side
  useEffect(() => {
    if (!usarPaginacionServidor && totalPaginas > 0 && paginaActualLocal > totalPaginas) {
      setPaginaActualLocal(totalPaginas);
    }
  }, [totalPaginas, paginaActualLocal, usarPaginacionServidor]);

  const obtenerColorTipoAccion = (tipo) => {
    if (!tipo) return 'default';
    
    // Normalizar el tipo para comparación
    const tipoNormalizado = tipo.toLowerCase();
    
    if (tipoNormalizado.includes('consulta')) return 'primary';
    if (tipoNormalizado.includes('carga') || tipoNormalizado.includes('documento')) return 'secondary';
    if (tipoNormalizado.includes('búsqueda') || tipoNormalizado.includes('similares')) return 'warning';
    if (tipoNormalizado.includes('login') || tipoNormalizado.includes('sesión')) return 'success';
    if (tipoNormalizado.includes('usuario') || tipoNormalizado.includes('creación') || tipoNormalizado.includes('edición')) return 'primary';
    if (tipoNormalizado.includes('bitácora') || tipoNormalizado.includes('exportar')) return 'default';
    
    return 'default';
  };

  const columns = [
    { key: "fechaHora", label: "FECHA Y HORA" },
    { key: "usuario", label: "USUARIO" },
    { key: "accion", label: "ACCIÓN" },
    { key: "expediente", label: "EXPEDIENTE" },
    { key: "descripcion", label: "DESCRIPCIÓN" },
    { key: "acciones", label: "ACCIONES" },
  ];

  const renderCell = (registro, columnKey) => {
    switch (columnKey) {
      case "fechaHora":
        // Validar y convertir fecha de manera segura
        const fecha = registro.fechaHora ? new Date(registro.fechaHora) : null;
        const fechaValida = fecha && !isNaN(fecha.getTime());
        
        return (
          <div className="flex flex-col">
            <p className="font-medium text-small">
              {fechaValida ? format(fecha, 'dd/MM/yyyy', { locale: es }) : 'Fecha inválida'}
            </p>
            <p className="text-tiny text-default-700">
              {fechaValida ? format(fecha, 'HH:mm:ss') : '--:--:--'}
            </p>
          </div>
        );
      case "usuario":
        // Si no hay usuario, mostrar guión
        if (!registro.usuario && !registro.correoUsuario) {
          return (
            <span className="text-small text-gray-400 font-medium">-</span>
          );
        }
        
        return (
          <div className="flex flex-col">
            <p className="font-semibold text-small text-gray-900">
              {registro.usuario || '-'}
            </p>
            <p className="text-tiny text-gray-600 font-medium">
              {registro.correoUsuario || '-'}
            </p>
          </div>
        );
      case "accion":
        return (
          <Chip
            color={obtenerColorTipoAccion(registro.tipoAccion)}
            size="sm"
            variant="flat"
          >
            {registro.tipoAccion || 'Sin especificar'}
          </Chip>
        );
      case "expediente":
        return registro.expediente ? (
          <code className="text-small font-mono text-gray-700">
            {registro.expediente}
          </code>
        ) : (
          <span className="text-small text-gray-400 font-medium">-</span>
        );
      case "descripcion":
        return (
          <div className="max-w-xl">
            <p className="text-small" title={registro.texto}>
              {registro.texto}
            </p>
          </div>
        );
      case "acciones":
        return (
          <div className="flex justify-center">
            <Button
              isIconOnly
              size="sm"
              variant="light"
              onPress={() => onVerDetalle(registro)}
            >
              <EyeIcon className="h-6 w-6 text-default-600" />
            </Button>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <Card>
      <CardHeader className="bg-white px-8 pt-6 pb-6">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 w-full">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-primary rounded-xl flex items-center justify-center shadow-md">
              <IoList className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">Registros de Bitácora</h3>
              <p className="text-sm text-gray-600 mt-1">
                Historial completo de actividades del sistema
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-xl shadow-sm border border-gray-200/60">
              <IoDocumentText className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-semibold text-gray-700">
                {registros.length} registro{registros.length !== 1 ? 's' : ''} encontrado{registros.length !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardBody className="px-0 py-0">
        {cargando ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary mb-4"></div>
            <p className="text-gray-600 font-medium">Cargando registros...</p>
            <p className="text-sm text-gray-500 mt-2">Por favor, espera un momento</p>
          </div>
        ) : registros.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12">
            <div className="bg-gray-100 rounded-full p-6 mb-4">
              <svg
                className="w-14 h-14 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">No se encontraron registros</h3>
            <p className="text-sm text-gray-500 text-center max-w-sm">
              Intenta ajustar los filtros de búsqueda para encontrar los registros que necesitas.
            </p>
          </div>
        ) : (
          <div className="px-6">
            <Table
              aria-label="Tabla de registros de bitácora"
              removeWrapper
              isStriped
              classNames={{
                th: "bg-primary text-white first:rounded-l-lg last:rounded-r-lg",
                tbody: "divide-y divide-gray-200",
                tr: "hover:bg-gray-50 transition-colors duration-200",
              }}
            >
              <TableHeader columns={columns}>
                {(column) => (
                  <TableColumn
                    key={column.key}
                    className={`font-semibold ${column.key === 'acciones' ? 'text-center' : 'text-start'}`}
                  >
                    {column.label}
                  </TableColumn>
                )}
              </TableHeader>
              <TableBody items={registrosPagina}>
                {(registro) => (
                  <TableRow key={registro.id}>
                    {(columnKey) => (
                      <TableCell className="py-4">{renderCell(registro, columnKey)}</TableCell>
                    )}
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        )}
      </CardBody>

      {/* Paginación mejorada y responsive */}
      {!cargando && totalPaginas > 0 && (
        <div className="flex flex-col sm:flex-row w-full justify-between items-center gap-4 px-4 sm:px-6 py-4 border-t border-gray-200">
          {/* Información de resultados */}
          <div className="hidden sm:block text-small text-default-700">
            {usarPaginacionServidor ? (
              // Paginación server-side: mostrar total real de registros
              <>
                Mostrando {((paginacion.page - 1) * 10) + 1} a {Math.min(paginacion.page * 10, paginacion.total)} de <strong>{paginacion.total.toLocaleString()}</strong> resultados
              </>
            ) : (
              // Paginación client-side: mostrar registros locales
              <>Mostrando {indiceInicio + 1} a {Math.min(indiceFin, registros.length)} de {registros.length} resultados</>
            )}
          </div>
          
          {/* Información compacta para móvil */}
          <div className="block sm:hidden text-tiny text-default-700 text-center">
            {usarPaginacionServidor ? (
              <>{((paginacion.page - 1) * 10) + 1}-{Math.min(paginacion.page * 10, paginacion.total)} de {paginacion.total.toLocaleString()}</>
            ) : (
              <>{indiceInicio + 1}-{Math.min(indiceFin, registros.length)} de {registros.length}</>
            )}
          </div>
          
          {/* Paginación adaptativa */}
          <div className="flex justify-center w-full sm:w-auto">
            <Pagination
              isCompact
              showControls={totalPaginas > 3}
              showShadow
              color="primary"
              page={paginaActual}
              total={totalPaginas}
              onChange={usarPaginacionServidor ? onCambiarPagina : setPaginaActualLocal}
              initialPage={1}
              size="sm"
              siblings={1}
              boundaries={1}
            />
          </div>
        </div>
      )}
    </Card>
  );
};

export default TablaBitacora;

