import React from 'react';
import { 
  Card, 
  CardBody, 
  CardHeader, 
  Input, 
  Select, 
  SelectItem, 
  Button 
} from '@heroui/react';
import { IoSearch, IoFilter, IoRefresh } from 'react-icons/io5';
import { roles, estadosUsuario } from '../../../data/mockUsuarios';

const FiltrosUsuarios = ({ 
  filtros, 
  setFiltros, 
  onAplicarFiltros, 
  onLimpiarFiltros 
}) => {
  const handleFiltroChange = (campo, valor) => {
    setFiltros(prev => ({
      ...prev,
      [campo]: valor
    }));
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      onAplicarFiltros();
    }
  };

  return (
    <Card>
      <CardHeader className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <IoFilter className="text-lg text-primary" />
          <h3 className="text-lg font-semibold">Filtros de Búsqueda</h3>
        </div>
      </CardHeader>
      
      <CardBody className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Filtro por nombre/usuario */}
          <Input
            label="Nombre o Usuario"
            placeholder="Buscar por nombre o nombre de usuario..."
            value={filtros.nombre}
            onValueChange={(valor) => handleFiltroChange('nombre', valor)}
            onKeyPress={handleKeyPress}
            startContent={<IoSearch className="text-gray-400" />}
            clearable
            variant="bordered"
          />

          {/* Filtro por correo */}
          <Input
            label="Correo Electrónico"
            placeholder="Buscar por correo..."
            value={filtros.correo}
            onValueChange={(valor) => handleFiltroChange('correo', valor)}
            onKeyPress={handleKeyPress}
            clearable
            variant="bordered"
          />

          {/* Filtro por cargo */}
          <Input
            label="Cargo"
            placeholder="Buscar por cargo..."
            value={filtros.cargo}
            onValueChange={(valor) => handleFiltroChange('cargo', valor)}
            onKeyPress={handleKeyPress}
            clearable
            variant="bordered"
          />

          {/* Filtro por rol */}
          <Select
            label="Rol"
            placeholder="Seleccionar rol"
            selectedKeys={filtros.rol ? [filtros.rol] : []}
            onSelectionChange={(keys) => {
              const valor = Array.from(keys)[0] || '';
              handleFiltroChange('rol', valor);
            }}
            variant="bordered"
          >
            {roles.map((rol) => (
              <SelectItem key={rol.nombre} value={rol.nombre}>
                {rol.nombre}
              </SelectItem>
            ))}
          </Select>

          {/* Filtro por estado */}
          <Select
            label="Estado"
            placeholder="Seleccionar estado"
            selectedKeys={filtros.estado ? [filtros.estado] : []}
            onSelectionChange={(keys) => {
              const valor = Array.from(keys)[0] || '';
              handleFiltroChange('estado', valor);
            }}
            variant="bordered"
          >
            {estadosUsuario.map((estado) => (
              <SelectItem key={estado.nombre} value={estado.nombre}>
                {estado.nombre}
              </SelectItem>
            ))}
          </Select>
        </div>

        {/* Botones de acción */}
        <div className="flex flex-wrap gap-3 justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
          <Button
            variant="flat"
            color="default"
            startContent={<IoRefresh className="text-lg" />}
            onPress={onLimpiarFiltros}
          >
            Limpiar Filtros
          </Button>
          
          <Button
            color="primary"
            startContent={<IoSearch className="text-lg" />}
            onPress={onAplicarFiltros}
          >
            Aplicar Filtros
          </Button>
        </div>
      </CardBody>
    </Card>
  );
};

export default FiltrosUsuarios;
