import { Table, TableHeader, TableColumn, TableBody, TableRow, TableCell, Tooltip, Button, Pagination, Input, Dropdown, DropdownItem, DropdownTrigger, DropdownMenu, Chip, Spinner } from "@heroui/react";
import React, { useState, useCallback, useMemo } from "react";
import { SearchIcon } from "./icons/SearchIcon";
import { ChevronDownIcon } from "./icons/ChevronDownIcon";
import { PlusIcon } from "./icons/PlusIcon";

const TablaDinamica = ({ columns, data, acciones = [], setAccion = null, onOpen, onOpenChange, ocultarAgregar = false, mostrarAcciones = true, filterOptions = [], loading = false }) => {
    const [currentPage, setCurrentPage] = useState(1);
    const [filterValue, setFilterValue] = useState("");
    const [selectedFilters, setSelectedFilters] = useState({});
    const [visibleColumns, setVisibleColumns] = useState(new Set(columns.map((col) => col.uid)));
    const numElementos = 7;

    // Componente personalizado para el mensaje de tabla vacía
    const EmptyTableMessage = () => (
        <div className="flex flex-col items-center justify-center py-12 px-6">
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
                        d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                    />
                </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">
                No hay datos disponibles
            </h3>
            <p className="text-sm text-gray-500 text-center max-w-sm">
                No se encontraron registros que coincidan con los criterios de búsqueda.
            </p>
        </div>
    );

    // Componente personalizado para el spinner de carga
    const LoadingTableMessage = () => (
        <div className="flex flex-col items-center justify-center py-16 px-6">
            <Spinner
                size="lg"
                color="primary"
                label="Cargando datos..."
                labelColor="primary"
                className="mb-4"
            />
            <p className="text-sm text-gray-500 text-center">
                Por favor espere mientras se cargan los datos
            </p>
        </div>
    );


    const abrirDrawer = useCallback((accion = 0) => {
        if (setAccion !== null) {
            if (accion !== 0) {
                setAccion(accion);
            }
        }
        onOpen();
    }, [setAccion, onOpen]);

    const getEstadoLabel = (estado) => {
        const labels = {
            1: "Inactivo",
            2: "Activo"
        };
        return labels[estado] || estado;
    };

    // Función para capitalizar texto correctamente
    const capitalizarTexto = (texto) => {
        if (!texto) return '';
        return texto.toLowerCase()
            .split(' ')
            .map(palabra => palabra.charAt(0).toUpperCase() + palabra.slice(1))
            .join(' ');
    };

    const renderCell = useCallback((item, index, columnKey) => {
        const estadosColors = {
            1: "danger",   // Inactivo
            2: "success",  // Activo
            "Inactivo": "danger",
            "Activo": "success"
        };
        
        let cellValue = item[columnKey];
        switch (columnKey) {
            case "nombreCompleto":
                // Construir nombres automáticamente desde los campos individuales
                const nombreCorto = `${capitalizarTexto(item.nombre)} ${capitalizarTexto(item.apellidoUno)}`.trim();
                const nombreCompleto = `${capitalizarTexto(item.nombre)} ${capitalizarTexto(item.apellidoUno)} ${capitalizarTexto(item.apellidoDos)}`.trim();

                return (
                    <Tooltip content={nombreCompleto} delay={300}>
                        <span className="text-sm font-medium cursor-help">
                            {nombreCorto}
                        </span>
                    </Tooltip>
                );

            case "especialidadCorta":
                // Mostrar especialidad corta con tooltip de la especialidad completa (capitalizada)
                const especialidadCompleta = capitalizarTexto(item.especialidadNombre || '');
                const especialidadTruncada = capitalizarTexto(cellValue || '');
                return (
                    <Tooltip content={especialidadCompleta} delay={300} color="primary">
                        <Chip
                            size="sm"
                            variant="flat"
                            color="primary"
                            className="cursor-help max-w-[120px]"
                        >
                            <span className="truncate">
                                {especialidadTruncada}
                            </span>
                        </Chip>
                    </Tooltip>
                );

            case "correo":
                // Truncar correos largos
                const correoTruncado = cellValue && cellValue.length > 20
                    ? cellValue.substring(0, 20) + '...'
                    : cellValue;
                return (
                    <Tooltip content={cellValue} delay={300}>
                        <span className="text-sm cursor-help">
                            {correoTruncado}
                        </span>
                    </Tooltip>
                );

            case "telefono":
                // Formatear teléfono para Costa Rica (XXXX-XXXX)
                const formatearTelefono = (numero) => {
                    if (!numero) return numero;
                    // Limpiar el número (solo dígitos)
                    const soloNumeros = numero.toString().replace(/\D/g, '');

                    // Formatear según la longitud
                    if (soloNumeros.length === 8) {
                        // Formato: XXXX-XXXX
                        return `${soloNumeros.slice(0, 4)}-${soloNumeros.slice(4)}`;
                    }
                    // Si no coincide con ningún formato esperado, devolver original
                    return numero;
                };

                const telefonoFormateado = formatearTelefono(cellValue);
                return (
                    <Tooltip content={telefonoFormateado} delay={300}>
                        <span className="text-sm cursor-help">
                            {telefonoFormateado}
                        </span>
                    </Tooltip>
                );

            case "estadoTexto":
                // Mostrar estado con chip colorido
                const estadoColor = cellValue === "Activo" ? "success" : "danger";
                return (
                    <Chip
                        size="sm"
                        variant="flat"
                        color={estadoColor}
                    >
                        {cellValue}
                    </Chip>
                );

            case "acciones":
                if (mostrarAcciones) {
                    return (
                        <div className="flex items-center justify-center">
                            <Dropdown>
                                <DropdownTrigger>
                                    <Button isIconOnly variant="flat" className="bg-transparent">
                                        <span className="text-lg text-gray-600">⋮</span>
                                    </Button>
                                </DropdownTrigger>
                                <DropdownMenu aria-label="Acciones">
                                    {acciones.map((accion, i) => (
                                        <DropdownItem
                                            key={i}
                                            onPress={() => accion.handler(item)}
                                            className="capitalize"
                                        >
                                            <div className="flex items-center gap-2">
                                                {accion.icon}
                                                <span>{accion.tooltip}</span>
                                            </div>
                                        </DropdownItem>
                                    ))}
                                </DropdownMenu>
                            </Dropdown>
                        </div>
                    );
                } else {
                    const accion = acciones[0];
                    return (
                        <button
                            onClick={() => accion.handler(item)}
                            className="text-blue-500 hover:text-blue-700"
                        >
                            {accion.icon}
                        </button>
                    );
                }

            case "estado": {
                // Definir color de texto según el estado
                let textColor = "";
                if (cellValue === 2 || cellValue === "Activo") textColor = "text-green-700";
                else if (cellValue === 1 || cellValue === "Inactivo") textColor = "text-red-600";
                else if (cellValue === "Paused") textColor = "text-pink-600";
                else if (cellValue === "Vacation") textColor = "text-yellow-700";
                else textColor = "text-gray-700";

                return (
                    <Chip
                        className={`capitalize border-none gap-1 px-3 py-1 text-sm font-semibold bg-opacity-80 ${textColor}`}
                        color={estadosColors[cellValue]}
                        size="sm"
                        variant="flat"
                    >
                        {getEstadoLabel(cellValue)}
                    </Chip>
                );
            }

            default:
                return cellValue;
        }
    }, [acciones, mostrarAcciones]);

    const topContent = useMemo(() => {
        return (
            <div className="flex flex-col gap-4">
                <div className="flex justify-between gap-3 items-end">
                    <Input
                        isClearable
                        className="w-full sm:max-w-[44%]"
                        placeholder="Buscar..."
                        startContent={<SearchIcon className="text-gray-500" />}
                        value={filterValue}
                        onClear={() => setFilterValue("")}
                        onValueChange={(value) => setFilterValue(value)}
                    />
                    <div className="flex gap-3">

                        {filterOptions.map(({ field, label, values, labels }) => (
                            <Dropdown key={field}>
                                <DropdownTrigger>
                                    <Button endContent={<ChevronDownIcon className="text-small" />} variant="flat">
                                        {label}
                                    </Button>
                                </DropdownTrigger>
                                <DropdownMenu
                                    aria-label={`Filtrar por ${label}`}
                                    closeOnSelect={false}
                                    selectionMode="multiple"
                                    selectedKeys={selectedFilters[field] || []}
                                    onSelectionChange={(keys) =>
                                        setSelectedFilters((prev) => ({
                                            ...prev,
                                            [field]: [...keys],
                                        }))
                                    }
                                >
                                    {values.map((value) => (
                                        <DropdownItem key={value} className="capitalize">
                                            {labels ? capitalizarTexto(labels[value]) : capitalizarTexto(value)}
                                        </DropdownItem>
                                    ))}
                                </DropdownMenu>
                            </Dropdown>
                        ))}

                        <Dropdown>
                            <DropdownTrigger className="hidden sm:flex">
                                <Button endContent={<ChevronDownIcon className="text-small" />} variant="flat">
                                    Columnas
                                </Button>
                            </DropdownTrigger>
                            <DropdownMenu
                                disallowEmptySelection
                                aria-label="Table Columns"
                                closeOnSelect={false}
                                selectedKeys={visibleColumns}
                                selectionMode="multiple"
                                onSelectionChange={setVisibleColumns}
                            >
                                {columns.map((column) => (
                                    <DropdownItem key={column.uid} className="capitalize">
                                        {column.name}
                                    </DropdownItem>
                                ))}
                            </DropdownMenu>
                        </Dropdown>
                        {!ocultarAgregar && (
                            <Button className="bg-primario text-white" onPress={() => { abrirDrawer(2) }} endContent={<PlusIcon />}>
                                Agregar
                            </Button>
                        )}
                    </div>
                </div>
            </div>
        );
    }, [filterValue, visibleColumns, columns, ocultarAgregar, abrirDrawer, filterOptions, selectedFilters]);

    // Datos filtrados
    const filteredData = useMemo(() => {
        let filtered = data || [];

        // Aplicar filtro de búsqueda por texto
        if (filterValue) {
            filtered = filtered.filter((item) =>
                columns.some((column) => {
                    const value = item[column.uid];
                    return value && value.toString().toLowerCase().includes(filterValue.toLowerCase());
                })
            );
        }

        // Aplicar filtros por categorías
        Object.entries(selectedFilters).forEach(([field, values]) => {
            if (values.length > 0) {
                filtered = filtered.filter((item) => values.includes(item[field]));
            }
        });

        return filtered;
    }, [data, filterValue, selectedFilters, columns]);

    // Datos paginados
    const datosPaginados = useMemo(() => {
        const start = (currentPage - 1) * numElementos;
        return filteredData.slice(start, start + numElementos);
    }, [filteredData, currentPage, numElementos]);

    const bottomContent = useMemo(() => {
        return (
            <div className="flex w-full justify-center mt-6">
                <Pagination
                    isCompact
                    showControls
                    showShadow
                    color="primary"
                    page={currentPage}
                    total={Math.max(1, Math.ceil(filteredData.length / numElementos))}
                    onChange={(page) => setCurrentPage(page)}
                    initialPage={1}
                />
            </div>
        );
    }, [filteredData, currentPage, numElementos]);

    return (
        <Table
            isHeaderSticky
            className="text-gray-800"
            isStriped
            topContent={topContent}
            bottomContent={bottomContent}
            bottomContentPlacement="outside"
            classNames={{
                wrapper: "max-h-[700px]",
                th: "bg-primario text-white",
            }}
            color="danger"
        >
            <TableHeader columns={columns.filter((col) => visibleColumns.has(col.uid))}>
                {(column) => (
                    <TableColumn key={column.uid} align="center">
                        {column.name}
                    </TableColumn>
                )}
            </TableHeader>
            <TableBody emptyContent={loading ? <LoadingTableMessage /> : <EmptyTableMessage />}>
                {loading ? [] : datosPaginados.map((item, index) => (
                    <TableRow key={item.id || index} className="hover:bg-gray-200 hover:rounded-full transition duration-300">
                        {columns
                            .filter((col) => visibleColumns.has(col.uid))
                            .map((column) => (
                                <TableCell key={column.uid}>
                                    {renderCell(item, index, column.uid)}
                                </TableCell>
                            ))}
                    </TableRow>
                ))}
            </TableBody>
        </Table>
    );
};

export default TablaDinamica;