import React from 'react';
import { Input, Select, SelectItem, Button, Card, CardBody, DatePicker, CardHeader } from '@heroui/react';
import { parseDate } from '@internationalized/date';
import { IoFunnel, IoSearch } from 'react-icons/io5';
import { PiBroomLight } from 'react-icons/pi';
import { SearchIcon } from '../../icons';

const FiltrosBitacora = ({ filtros, onFiltroChange, onLimpiarFiltros, onBuscar, disabled = false }) => {
    // Tipos de acción actualizados según el backend (8 tipos)
    const tiposAccion = [
        { key: '1', label: 'Consulta' },
        { key: '2', label: 'Carga de Documentos' },
        { key: '3', label: 'Búsqueda de Casos Similares' },
        { key: '4', label: 'Inicio de Sesión' },
        { key: '5', label: 'Creación de Usuario' },
        { key: '6', label: 'Edición de Usuario' },
        { key: '7', label: 'Consulta de Bitácora' },
        { key: '8', label: 'Exportación de Bitácora' }
    ];

    const handleInputChange = (campo, valor) => {
        onFiltroChange({ ...filtros, [campo]: valor });
    };

    const handleDateChange = (campo, date) => {
        // Convertir el objeto de fecha a string ISO para almacenamiento
        const dateString = date ? date.toString() : '';
        onFiltroChange({ ...filtros, [campo]: dateString });
    };

    // Verificar si hay contenido en los filtros
    const hasContent = () => {
        return Object.values(filtros).some(valor => valor !== '');
    };

    // Verificar si se puede buscar (al menos un filtro activo)
    const canSearch = () => {
        return hasContent();
    };

    const isButtonDisabled = !canSearch();

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
                            onPress={onBuscar}
                            color="primary"
                            size="md"
                            startContent={<IoSearch className="w-4 h-4" />}
                            isDisabled={isButtonDisabled || disabled}
                            className={`flex-1 sm:flex-none px-4 font-medium shadow-lg hover:shadow-xl transform transition-all duration-200 text-sm ${isButtonDisabled || disabled
                              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                              : 'bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 hover:scale-105'
                              }`}
                            radius="md"
                        >
                            Buscar
                        </Button>

                        <Button
                            onPress={onLimpiarFiltros}
                            color="default"
                            variant="flat"
                            size="md"
                            startContent={<PiBroomLight className="w-4 h-4" />}
                            isDisabled={!hasContent() || disabled}
                            className="px-4 font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 transition-all duration-200 text-sm"
                            radius="md"
                        >
                            Limpiar
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
