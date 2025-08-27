import React from 'react';
import { Input, Select, SelectItem, Button, Card, CardBody, DatePicker, CardHeader } from '@heroui/react';
import { parseDate } from '@internationalized/date';
import { IoFunnel, IoSearch } from 'react-icons/io5';
import { SearchIcon } from '../../icons';

const FiltrosBitacora = ({ filtros, onFiltroChange, onLimpiarFiltros, onBuscar }) => {
    const tiposAccion = [
        { key: 'consulta', label: 'Consulta' },
        { key: 'carga', label: 'Carga' },
        { key: 'busqueda-similares', label: 'Búsqueda similares' }
    ];

    const estados = [
        { key: 'pendiente', label: 'Pendiente' },
        { key: 'procesado', label: 'Procesado' },
        { key: 'error', label: 'Error' }
    ];

    const handleInputChange = (campo, valor) => {
        onFiltroChange({ ...filtros, [campo]: valor });
    };

    const handleDateChange = (campo, date) => {
        // Convertir el objeto de fecha a string ISO para almacenamiento
        const dateString = date ? date.toString() : '';
        onFiltroChange({ ...filtros, [campo]: dateString });
    };

    return (
        <Card className="mb-8">
            <CardHeader className="bg-white px-8 pt-6 pb-3">
                <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 w-full">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-primary rounded-xl flex items-center justify-center shadow-md">
                            <IoFunnel className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">Filtros de Búsqueda</h2>
                            <p className="text-sm text-gray-600 mt-1">
                                Personaliza tu búsqueda para encontrar registros específicos
                            </p>
                        </div>
                    </div>
                    
                    {/* Botones de acción en el header */}
                    <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 w-full lg:w-auto">
                        <Button
                            type="button"
                            color="default"
                            variant="bordered"
                            onPress={onLimpiarFiltros}
                            size="md"
                            className="w-full sm:w-auto px-4 sm:px-6 font-medium"
                        >
                            Limpiar Filtros
                        </Button>
                        <Button
                            onPress={onBuscar}
                            color="primary"
                            startContent={<SearchIcon className="h-4 w-4" />}
                            size="md"
                            className="w-full sm:w-auto px-4 sm:px-6 font-medium"
                        >
                            Buscar
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardBody className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-6 gap-4 items-end w-full">
                        {/* Filtro por Usuario */}
                        <div className="w-full xl:col-span-1 2xl:col-span-1">
                            <Input
                                label="Usuario"
                                labelPlacement='outside'
                                placeholder="Nombre del usuario"
                                color="primary"
                                value={filtros.usuario}
                                onChange={(e) => handleInputChange('usuario', e.target.value)}
                                variant="bordered"
                                size="lg"
                                className="w-full"
                            />
                        </div>

                        {/* Filtro por Expediente */}
                        <div className="w-full xl:col-span-1 2xl:col-span-1">
                            <Input
                                label="Expediente"
                                labelPlacement='outside'
                                placeholder="Número de expediente"
                                color='primary'
                                value={filtros.expediente}
                                onChange={(e) => handleInputChange('expediente', e.target.value)}
                                variant="bordered"
                                size="lg"
                                className="w-full"
                            />
                        </div>

                        {/* Filtro por Tipo de Acción */}
                        <div className="w-full xl:col-span-1 2xl:col-span-1">
                            <Select
                                label="Tipo de Acción"
                                labelPlacement='outside'
                                placeholder="Selecciona un tipo"
                                color='primary'
                                selectedKeys={filtros.tipoAccion ? [filtros.tipoAccion.toLowerCase().replace(' ', '-')] : []}
                                onSelectionChange={(keys) => {
                                    const selectedKey = Array.from(keys)[0];
                                    const selectedLabel = tiposAccion.find(t => t.key === selectedKey)?.label || '';
                                    handleInputChange('tipoAccion', selectedLabel);
                                }}
                                variant="bordered"
                                size="lg"
                                className="w-full"
                            >
                                {tiposAccion.map((tipo) => (
                                    <SelectItem key={tipo.key} value={tipo.key}>
                                        {tipo.label}
                                    </SelectItem>
                                ))}
                            </Select>
                        </div>

                        {/* Filtro por Estado */}
                        <div className="w-full xl:col-span-1 2xl:col-span-1">
                            <Select
                                label="Estado"
                                labelPlacement='outside'
                                placeholder="Selecciona un estado"
                                color='primary'
                                selectedKeys={filtros.estado ? [filtros.estado.toLowerCase()] : []}
                                onSelectionChange={(keys) => {
                                    const selectedKey = Array.from(keys)[0];
                                    const selectedLabel = estados.find(e => e.key === selectedKey)?.label || '';
                                    handleInputChange('estado', selectedLabel);
                                }}
                                variant="bordered"
                                size="lg"
                                className="w-full"
                            >
                                {estados.map((estado) => (
                                    <SelectItem key={estado.key} value={estado.key}>
                                        {estado.label}
                                    </SelectItem>
                                ))}
                            </Select>
                        </div>

                        {/* Filtro por Fecha Inicio */}
                        <div className="w-full xl:col-span-2 2xl:col-span-1">
                            <DatePicker
                                label="Fecha Inicio"
                                labelPlacement='outside'
                                value={filtros.fechaInicio ? parseDate(filtros.fechaInicio) : null}
                                onChange={(date) => handleDateChange('fechaInicio', date)}
                                variant="bordered"
                                color='primary'
                                size="lg"
                                showMonthAndYearPickers
                                className="w-full"
                            />
                        </div>

                        {/* Filtro por Fecha Fin */}
                        <div className="w-full xl:col-span-2 2xl:col-span-1">
                            <DatePicker
                                label="Fecha Fin"
                                labelPlacement='outside'
                                value={filtros.fechaFin ? parseDate(filtros.fechaFin) : null}
                                onChange={(date) => handleDateChange('fechaFin', date)}
                                variant="bordered"
                                color='primary'
                                size="lg"
                                showMonthAndYearPickers
                                className="w-full"
                            />
                        </div>
                    </div>
            </CardBody>
        </Card>
    );
};

export default FiltrosBitacora;
