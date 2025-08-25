import React from 'react';
import { Input, Select, SelectItem, Button, Card, CardBody, Form, DatePicker } from '@heroui/react';
import { parseDate } from '@internationalized/date';
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

    const handleSubmit = (e) => {
        e.preventDefault();
        onBuscar();
    };

    return (
        <Card className="mb-8">
            <CardBody className="p-6">
                <h2 className="text-xl font-semibold text-gray-800 mb-6">Filtros de Búsqueda</h2>

                <Form onSubmit={handleSubmit} className="space-y-6">
                    {/* Grid responsive que se adapta automáticamente */}
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

                    {/* Botones de Acción */}
                    <div className="flex flex-wrap gap-4 pt-4 border-t border-gray-200">
                        <Button
                            type="submit"
                            color="primary"
                            startContent={<SearchIcon className="h-4 w-4" />}
                            size="lg"
                            className="min-w-40 px-6"
                        >
                            Buscar
                        </Button>

                        <Button
                            type="button"
                            color="default"
                            variant="bordered"
                            onClick={onLimpiarFiltros}
                            size="lg"
                            className="min-w-40 px-6"
                        >
                            Limpiar Filtros
                        </Button>
                    </div>
                </Form>
            </CardBody>
        </Card>
    );
};

export default FiltrosBitacora;
