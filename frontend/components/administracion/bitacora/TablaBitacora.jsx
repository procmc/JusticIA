import React, { useState } from 'react';
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

const TablaBitacora = ({ registros, onVerDetalle }) => {
  const [paginaActual, setPaginaActual] = useState(1);
  const registrosPorPagina = 10;

  // Calcular registros para la página actual
  const indiceInicio = (paginaActual - 1) * registrosPorPagina;
  const indiceFin = indiceInicio + registrosPorPagina;
  const registrosPagina = registros.slice(indiceInicio, indiceFin);
  const totalPaginas = Math.ceil(registros.length / registrosPorPagina);

  const obtenerColorEstado = (estado) => {
    switch (estado) {
      case 'Procesado':
        return 'success';
      case 'Pendiente':
        return 'warning';
      case 'Error':
        return 'danger';
      default:
        return 'default';
    }
  };

  const obtenerColorTipoAccion = (tipo) => {
    switch (tipo) {
      case 'Consulta':
        return 'primary';
      case 'Carga':
        return 'secondary';
      case 'Búsqueda similares':
        return 'warning';
      default:
        return 'default';
    }
  };

  const columns = [
    { key: "fechaHora", label: "FECHA Y HORA" },
    { key: "usuario", label: "USUARIO" },
    { key: "accion", label: "ACCIÓN" },
    { key: "expediente", label: "EXPEDIENTE" },
    { key: "estado", label: "ESTADO" },
    { key: "descripcion", label: "DESCRIPCIÓN" },
    { key: "acciones", label: "ACCIONES" },
  ];

  const renderCell = (registro, columnKey) => {
    switch (columnKey) {
      case "fechaHora":
        return (
          <div className="flex flex-col">
            <p className="font-medium text-small">
              {format(registro.fechaHora, 'dd/MM/yyyy', { locale: es })}
            </p>
            <p className="text-tiny text-default-400">
              {format(registro.fechaHora, 'HH:mm:ss')}
            </p>
          </div>
        );
      case "usuario":
        return (
          <div className="flex flex-col">
            <p className="font-medium text-small">{registro.usuario}</p>
            <p className="text-tiny text-default-400">{registro.rolUsuario}</p>
          </div>
        );
      case "accion":
        return (
          <Chip 
            color={obtenerColorTipoAccion(registro.tipoAccion)}
            size="sm"
            variant="flat"
          >
            {registro.tipoAccion}
          </Chip>
        );
      case "expediente":
        return (
          <code className="text-small font-mono">
            {registro.expediente}
          </code>
        );
      case "estado":
        return (
          <Chip 
            color={obtenerColorEstado(registro.estado)}
            size="sm"
            variant="flat"
          >
            {registro.estado}
          </Chip>
        );
      case "descripcion":
        return (
          <div className="max-w-xs">
            <p className="text-small truncate" title={registro.texto}>
              {registro.texto}
            </p>
          </div>
        );
      case "acciones":
        return (
          <Button
            isIconOnly
            size="sm"
            variant="light"
            onPress={() => onVerDetalle(registro)}
          >
            <EyeIcon className="h-6 w-6 text-default-400" />
          </Button>
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
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-md">
              <IoList className="w-5 h-5 text-white" />
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
        {registros.length === 0 ? (
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
                  <TableColumn key={column.key} className="text-start font-semibold">
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
      
      {/* Paginación mejorada */}
      {registros.length > 0 && totalPaginas > 1 && (
        <div className="flex w-full justify-between items-center px-6 py-4 border-t border-gray-200">
          <div className="text-small text-default-500">
            Mostrando {indiceInicio + 1} a {Math.min(indiceFin, registros.length)} de {registros.length} resultados
          </div>
          <Pagination
            isCompact
            showControls
            showShadow
            color="primary"
            page={paginaActual}
            total={totalPaginas}
            onChange={setPaginaActual}
            initialPage={1}
          />
        </div>
      )}
    </Card>
  );
};

export default TablaBitacora;

