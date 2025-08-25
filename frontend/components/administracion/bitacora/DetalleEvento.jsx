import React from 'react';
import { 
  Modal, 
  ModalContent, 
  ModalHeader, 
  ModalBody, 
  ModalFooter, 
  Button, 
  Chip,
  Card,
  CardBody,
  Divider
} from '@heroui/react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

const DetalleEvento = ({ registro, isOpen, onClose }) => {
  if (!registro) return null;

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

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      size="2xl"
      scrollBehavior="inside"
      classNames={{
        backdrop: "bg-black/50 backdrop-opacity-40",
      }}
    >
      <ModalContent>
        <ModalHeader className="flex flex-col gap-1">
          <h3 className="text-xl font-semibold">
            Detalle del Evento #{registro.id}
          </h3>
        </ModalHeader>
        
        <ModalBody className="space-y-6">
          {/* Información Principal */}
          <Card>
            <CardBody>
              <h4 className="text-lg font-semibold mb-4">Información Principal</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-small font-medium text-default-600 mb-1">Fecha y Hora</p>
                  <div className="bg-default-100 p-3 rounded-medium">
                    <p className="font-medium">
                      {format(registro.fechaHora, 'EEEE, dd \'de\' MMMM \'de\' yyyy', { locale: es })}
                    </p>
                    <p className="text-default-600">
                      {format(registro.fechaHora, 'HH:mm:ss')}
                    </p>
                  </div>
                </div>

                <div>
                  <p className="text-small font-medium text-default-600 mb-1">Estado</p>
                  <div className="bg-default-100 p-3 rounded-medium">
                    <Chip 
                      color={obtenerColorEstado(registro.estado)}
                      variant="flat"
                      size="sm"
                    >
                      {registro.estado}
                    </Chip>
                  </div>
                </div>

                <div>
                  <p className="text-small font-medium text-default-600 mb-1">Tipo de Acción</p>
                  <div className="bg-default-100 p-3 rounded-medium">
                    <Chip 
                      color={obtenerColorTipoAccion(registro.tipoAccion)}
                      variant="flat"
                      size="sm"
                    >
                      {registro.tipoAccion}
                    </Chip>
                  </div>
                </div>

                <div>
                  <p className="text-small font-medium text-default-600 mb-1">Expediente</p>
                  <div className="bg-default-100 p-3 rounded-medium">
                    <code className="text-default-900 font-mono">
                      {registro.expediente}
                    </code>
                  </div>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* Información del Usuario */}
          <Card>
            <CardBody>
              <h4 className="text-lg font-semibold mb-4">Información del Usuario</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-small font-medium text-default-600 mb-1">Nombre</p>
                  <div className="bg-default-100 p-3 rounded-medium">
                    <p className="text-default-900">{registro.usuario}</p>
                  </div>
                </div>

                <div>
                  <p className="text-small font-medium text-default-600 mb-1">Correo Electrónico</p>
                  <div className="bg-default-100 p-3 rounded-medium">
                    <p className="text-default-900">{registro.correoUsuario}</p>
                  </div>
                </div>

                <div>
                  <p className="text-small font-medium text-default-600 mb-1">Rol</p>
                  <div className="bg-default-100 p-3 rounded-medium">
                    <p className="text-default-900">{registro.rolUsuario}</p>
                  </div>
                </div>

                <div>
                  <p className="text-small font-medium text-default-600 mb-1">Dirección IP</p>
                  <div className="bg-default-100 p-3 rounded-medium">
                    <code className="text-default-900 font-mono">{registro.ip}</code>
                  </div>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* Detalles de la Acción */}
          <Card>
            <CardBody>
              <h4 className="text-lg font-semibold mb-4">Detalles de la Acción</h4>
              <div className="space-y-4">
                <div>
                  <p className="text-small font-medium text-default-600 mb-1">Descripción</p>
                  <div className="bg-default-100 p-3 rounded-medium">
                    <p className="text-default-900">{registro.texto}</p>
                  </div>
                </div>

                {registro.informacionAdicional && (
                  <div>
                    <p className="text-small font-medium text-default-600 mb-1">Información Adicional</p>
                    <div className="bg-default-100 p-3 rounded-medium">
                      <p className="text-default-900">{registro.informacionAdicional}</p>
                    </div>
                  </div>
                )}
              </div>
            </CardBody>
          </Card>

          {/* Información Técnica */}
          <Card>
            <CardBody>
              <h4 className="text-lg font-semibold mb-4">Información Técnica</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-small font-medium text-default-600 mb-1">Navegador</p>
                  <div className="bg-default-100 p-3 rounded-medium">
                    <p className="text-default-900">{registro.navegador}</p>
                  </div>
                </div>

                <div>
                  <p className="text-small font-medium text-default-600 mb-1">Duración</p>
                  <div className="bg-default-100 p-3 rounded-medium">
                    <p className="text-default-900">{registro.duracion} ms</p>
                  </div>
                </div>
              </div>
            </CardBody>
          </Card>
        </ModalBody>
        
        <ModalFooter>
          <Button 
            color="primary" 
            variant="light" 
            onPress={onClose}
          >
            Cerrar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default DetalleEvento;
