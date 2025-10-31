import React, { useState, useEffect } from 'react';
import { Input, Select, SelectItem, Button, Card, CardBody, DatePicker, CardHeader } from '@heroui/react';
import { parseDate, today, getLocalTimeZone } from '@internationalized/date';
import { IoFunnel, IoSearch } from 'react-icons/io5';
import { PiBroomLight } from 'react-icons/pi';
import { SearchIcon } from '../../icons';
import { TIPOS_ACCION } from '@/common/tiposAccion';

const FiltrosBitacora = ({ filtros, onBuscar, onLimpiarFiltros, disabled = false }) => {
    
    const [filtrosLocales, setFiltrosLocales] = useState(filtros);
    // Estado para mostrar el día actual en el calendario (solo fecha, sin hora)
    const [currentDate] = useState(today(getLocalTimeZone()));

    // Sincronizar filtros locales cuando el padre los limpie
    useEffect(() => {
        setFiltrosLocales(filtros);
    }, [filtros]);

    const handleInputChange = (campo, valor) => {
        setFiltrosLocales({ ...filtrosLocales, [campo]: valor });
    };

    const handleBuscarClick = () => {
        // Enviar filtros locales directamente al callback de búsqueda
        onBuscar(filtrosLocales);
    };

    const handleLimpiarClick = () => {
        // Limpiar filtros locales y notificar al padre
        const filtrosVacios = {
            usuario: '',
            tipoAccion: '',
            expediente: '',
            fechaInicio: '',
            fechaFin: '',
            page: 1,
            limit: 10
        };
        setFiltrosLocales(filtrosVacios);
        onLimpiarFiltros();
    };

    const handleDateChange = (campo, date) => {
        // Convertir el objeto de fecha a string ISO para el backend
        // El DatePicker devuelve un objeto CalendarDate de @internationalized/date
        if (date) {
            // Construir fecha ISO: YYYY-MM-DD
            const year = date.year;
            const month = String(date.month).padStart(2, '0');
            const day = String(date.day).padStart(2, '0');
            const isoString = `${year}-${month}-${day}`;
            
            // Validar que fechaFin no sea menor que fechaInicio
            if (campo === 'fechaFin' && filtrosLocales.fechaInicio) {
                if (isoString < filtrosLocales.fechaInicio) {
                    // No permitir fecha fin menor que fecha inicio
                    return;
                }
            }
            
            // Validar que fechaInicio no sea mayor que fechaFin
            if (campo === 'fechaInicio' && filtrosLocales.fechaFin) {
                if (isoString > filtrosLocales.fechaFin) {
                    // Si fecha inicio es mayor, limpiar fecha fin
                    setFiltrosLocales({ ...filtrosLocales, [campo]: isoString, fechaFin: '' });
                    return;
                }
            }
            
            setFiltrosLocales({ ...filtrosLocales, [campo]: isoString });
        } else {
            setFiltrosLocales({ ...filtrosLocales, [campo]: '' });
        }
    };

    // Verificar si hay contenido en los filtros locales
    const hasContent = () => {
        return Object.values(filtrosLocales).some(valor => valor !== '');
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
                            onPress={handleBuscarClick}
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
                            onPress={handleLimpiarClick}
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
                                placeholder="Nombre, apellido o correo"
                                color="primary"
                                value={filtrosLocales.usuario}
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
                                value={filtrosLocales.expediente}
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
                                selectedKeys={filtrosLocales.tipoAccion ? [filtrosLocales.tipoAccion.toString()] : []}
                                onSelectionChange={(keys) => {
                                    const selectedKey = Array.from(keys)[0];
                                    // Enviar el ID numérico (1-8) en lugar del label
                                    handleInputChange('tipoAccion', selectedKey ? parseInt(selectedKey) : '');
                                }}
                                variant="bordered"
                                size="lg"
                                className="w-full"
                            >
                                {TIPOS_ACCION.map((tipo) => (
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
                                granularity="day"
                                value={filtrosLocales.fechaInicio ? parseDate(filtrosLocales.fechaInicio) : null}
                                placeholderValue={currentDate}
                                onChange={(date) => handleDateChange('fechaInicio', date)}
                                variant="bordered"
                                color='primary'
                                size="lg"
                                showMonthAndYearPickers
                                maxValue={filtrosLocales.fechaFin ? parseDate(filtrosLocales.fechaFin) : undefined}
                                calendarProps={{
                                    classNames: {
                                        base: "datepicker-calendar"
                                    }
                                }}
                                className="w-full"
                            />
                        </div>

                        {/* Filtro por Fecha Fin */}
                        <div className="w-full xl:col-span-2 2xl:col-span-1">
                            <DatePicker
                                label="Fecha Fin"
                                labelPlacement='outside'
                                granularity="day"
                                value={filtrosLocales.fechaFin ? parseDate(filtrosLocales.fechaFin) : null}
                                placeholderValue={currentDate}
                                onChange={(date) => handleDateChange('fechaFin', date)}
                                variant="bordered"
                                color='primary'
                                size="lg"
                                showMonthAndYearPickers
                                minValue={filtrosLocales.fechaInicio ? parseDate(filtrosLocales.fechaInicio) : undefined}
                                calendarProps={{
                                    classNames: {
                                        base: "datepicker-calendar"
                                    }
                                }}
                                className="w-full"
                            />
                        </div>
                    </div>
            </CardBody>
        </Card>
    );
};

export default FiltrosBitacora;