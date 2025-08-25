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
            <EyeIcon className="h-4 w-4" />
          </Button>
        );
      default:
        return null;
    }
  };

  return (
    <Card>
      <CardHeader className="flex justify-between items-center">
        <div className="flex flex-col">
          <h3 className="text-lg font-semibold">Registros de Bitácora</h3>
        </div>
        <div className="text-small text-default-500">
          {registros.length} registro{registros.length !== 1 ? 's' : ''} encontrado{registros.length !== 1 ? 's' : ''}
        </div>
      </CardHeader>
      <CardBody className="p-0">
        {registros.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8">
            <div className="text-default-400 text-large mb-2">No se encontraron registros</div>
            <div className="text-default-300 text-small">Intenta ajustar los filtros de búsqueda</div>
          </div>
        ) : (
          <>
            <Table 
              aria-label="Tabla de registros de bitácora"
              removeWrapper
              classNames={{
                th: "bg-default-100",
              }}
            >
              <TableHeader columns={columns}>
                {(column) => (
                  <TableColumn key={column.key} className="text-start">
                    {column.label}
                  </TableColumn>
                )}
              </TableHeader>
              <TableBody items={registrosPagina}>
                {(registro) => (
                  <TableRow key={registro.id} className="hover:bg-default-50">
                    {(columnKey) => (
                      <TableCell>{renderCell(registro, columnKey)}</TableCell>
                    )}
                  </TableRow>
                )}
              </TableBody>
            </Table>
            
            {/* Paginación */}
            {totalPaginas > 1 && (
              <div className="flex justify-between items-center px-4 py-4">
                <div className="text-small text-default-500">
                  Mostrando {indiceInicio + 1} a {Math.min(indiceFin, registros.length)} de {registros.length} resultados
                </div>
                <Pagination
                  total={totalPaginas}
                  page={paginaActual}
                  onChange={setPaginaActual}
                  showControls
                  size="sm"
                />
              </div>
            )}
          </>
        )}
      </CardBody>
    </Card>
  );
};

export default TablaBitacora;

