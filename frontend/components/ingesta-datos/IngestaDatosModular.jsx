import React, { useState, useRef } from 'react';
import { Card, CardBody, Input, Button } from '@heroui/react';
import { FiSave, FiCheck } from 'react-icons/fi';
import { motion } from 'framer-motion';
import ConfirmModal from '@/components/ui/ConfirmModal';
import { validarFormatoExpediente } from './funciones';
import { usarManejoArchivos } from './manejoArchivos';
import ZonaArrastre from './ZonaArrastre';
import ResumenArchivos from './ResumenArchivos';
import ListaArchivos from './ListaArchivos';
import InfoTiposArchivo from './InfoTiposArchivo';

const IngestaDatosModular = () => {
  // Estados para expediente
  const [numeroExpediente, setNumeroExpediente] = useState('');
  const [expedienteValido, setExpedienteValido] = useState(false);
  
  // Estados para modal
  const [modalAbierto, setModalAbierto] = useState(false);
  
  // Estados para UI
  const [guardadoExitoso, setGuardadoExitoso] = useState(false);
  
  // Hook personalizado para manejo de archivos
  const {
    archivos,
    arrastreActivo,
    subiendoArchivos,
    progreso,
    progresoIndividual,
    alEntrarArrastre,
    alSalirArrastre,
    alSobreArrastre,
    alSoltar,
    alSeleccionarArchivo,
    eliminarArchivo,
    simularSubida
  } = usarManejoArchivos();
  
  // Referencia para input de archivos
  const referenciaInput = useRef(null);

  // Validación de expediente
  const manejarCambioExpediente = (e) => {
    const valor = e.target.value;
    setNumeroExpediente(valor);
    setExpedienteValido(validarFormatoExpediente(valor));
  };

  // Funciones del modal
  const abrirModal = () => {
    if (archivos.length > 0 && expedienteValido) {
      setModalAbierto(true);
    }
  };

  const confirmarGuardado = async () => {
    setModalAbierto(false);
    await simularSubida();
    setGuardadoExitoso(true);
    setTimeout(() => setGuardadoExitoso(false), 3000);
  };

  const cancelarGuardado = () => {
    setModalAbierto(false);
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Título principal */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <h1 className="text-3xl font-bold text-tituloSeccion mb-2">
          Ingesta de Datos
        </h1>
        <p className="text-gray-600">
          Sube documentos y archivos de audio para procesamiento
        </p>
      </motion.div>

      {/* Información de tipos de archivo */}
      <InfoTiposArchivo />

      {/* Formulario de expediente */}
      <Card>
        <CardBody className="p-6">
          <h2 className="text-xl font-semibold text-tituloSeccion mb-4">
            Información del Expediente
          </h2>
          
          <div className="space-y-4">
            <Input
              label="Número de Expediente"
              placeholder="Ej: 2024,98-123456-7890-AB"
              value={numeroExpediente}
              onChange={manejarCambioExpediente}
              color={numeroExpediente ? (expedienteValido ? 'success' : 'danger') : 'default'}
              description="Formato: AAAA,98-XXXXXX-XXXX-XX (Año, código fijo, número, dígitos verificadores y letras)"
              className="max-w-md"
            />
            
            {numeroExpediente && !expedienteValido && (
              <p className="text-sm text-red-600">
                ⚠️ Formato incorrecto. Use: AAAA,98-XXXXXX-XXXX-XX
              </p>
            )}
            
            {expedienteValido && (
              <p className="text-sm text-green-600">
                ✅ Formato válido
              </p>
            )}
          </div>
        </CardBody>
      </Card>

      {/* Zona de arrastre */}
      <ZonaArrastre
        expedienteValido={expedienteValido}
        arrastreActivo={arrastreActivo}
        alEntrarArrastre={alEntrarArrastre}
        alSalirArrastre={alSalirArrastre}
        alSobreArrastre={alSobreArrastre}
        alSoltar={alSoltar}
        alSeleccionarArchivo={alSeleccionarArchivo}
        referenciaInput={referenciaInput}
      />

      {/* Resumen de archivos */}
      <ResumenArchivos
        archivos={archivos}
        subiendoArchivos={subiendoArchivos}
        progreso={progreso}
      />

      {/* Lista de archivos */}
      <ListaArchivos
        archivos={archivos}
        alEliminarArchivo={eliminarArchivo}
        subiendoArchivos={subiendoArchivos}
        progresoIndividual={progresoIndividual}
      />

      {/* Botón de guardar */}
      {archivos.length > 0 && expedienteValido && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-center"
        >
          <Button
            size="lg"
            color={guardadoExitoso ? 'success' : 'primary'}
            onClick={abrirModal}
            disabled={subiendoArchivos}
            startContent={guardadoExitoso ? <FiCheck /> : <FiSave />}
            className="px-8"
          >
            {guardadoExitoso 
              ? '¡Guardado exitoso!' 
              : subiendoArchivos 
                ? 'Guardando...' 
                : 'Guardar archivos'
            }
          </Button>
        </motion.div>
      )}

      {/* Modal de confirmación */}
      <ConfirmModal
        isOpen={modalAbierto}
        onConfirm={confirmarGuardado}
        onCancel={cancelarGuardado}
        title="Confirmar ingesta de datos"
        message={`¿Estás seguro de que deseas procesar ${archivos.length} archivo(s) para el expediente ${numeroExpediente}?`}
        details={[
          `Expediente: ${numeroExpediente}`,
          `Total de archivos: ${archivos.length}`,
          `Documentos: ${archivos.filter(a => a.tipo === 'documento').length}`,
          `Audios: ${archivos.filter(a => a.tipo === 'audio').length}`,
          `Tamaño total: ${(archivos.reduce((total, archivo) => total + archivo.tamaño, 0) / (1024 * 1024)).toFixed(2)} MB`
        ]}
        confirmText="Sí, procesar archivos"
        cancelText="Cancelar"
        confirmColor="primary"
      />
    </div>
  );
};

export default IngestaDatosModular;
