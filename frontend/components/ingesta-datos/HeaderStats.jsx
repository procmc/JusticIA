/**
 * Componente del header con estadísticas
 * Extraído del componente principal
 */
import React from 'react';
import { Card, CardBody } from '@heroui/react';
import { IoCloudUpload } from 'react-icons/io5';
import { formatearTamano } from '@/utils/ingesta-datos/funciones';

const HeaderStats = ({
  files,
  pendingFiles,
  successFiles,
  errorFiles
}) => {
  return (
    <Card className="bg-primary text-white shadow-lg border-none">
      <CardBody className="p-4 sm:p-6 lg:p-8">
        <div className="space-y-6">
          {/* Fila superior: Título */}
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="p-2 sm:p-3 bg-white/15 rounded-xl border border-white/20 flex-shrink-0">
              <IoCloudUpload className="text-2xl sm:text-3xl lg:text-4xl text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white mb-1 sm:mb-2 truncate">
                Ingesta de Datos
              </h1>
              <p className="text-white/80 text-sm sm:text-base">
                Carga y procesamiento de documentos jurídicos
              </p>
            </div>
          </div>

          {/* Estadísticas siempre visibles */}
          <div className="pt-2">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              {/* Total de archivos */}
              <div className="flex items-center gap-1.5 bg-white/10 hover:bg-white/15 px-2 py-1.5 rounded-md border border-white/20 h-8 sm:h-9">
                <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-blue-400 flex-shrink-0"></div>
                <div className="flex items-center gap-1">
                  <span className="text-white/90 font-semibold text-xs sm:text-sm">{files.length}</span>
                  <span className="text-white/70 text-xs font-medium uppercase hidden sm:inline">Archivos</span>
                  <span className="text-white/70 text-xs font-medium uppercase sm:hidden">Arch</span>
                </div>
              </div>

              {/* Archivos pendientes */}
              <div className="flex items-center gap-1.5 bg-white/10 hover:bg-white/15 px-2 py-1.5 rounded-md border border-white/20 h-8 sm:h-9">
                <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-yellow-400 flex-shrink-0"></div>
                <div className="flex items-center gap-1">
                  <span className="text-white/90 font-semibold text-xs sm:text-sm">{pendingFiles}</span>
                  <span className="text-white/70 text-xs font-medium uppercase hidden sm:inline">Pendientes</span>
                  <span className="text-white/70 text-xs font-medium uppercase sm:hidden">Pend</span>
                </div>
              </div>

              {/* Archivos completados */}
              <div className="flex items-center gap-1.5 bg-white/10 hover:bg-white/15 px-2 py-1.5 rounded-md border border-white/20 h-8 sm:h-9">
                <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-emerald-400 flex-shrink-0"></div>
                <div className="flex items-center gap-1">
                  <span className="text-white/90 font-semibold text-xs sm:text-sm">{successFiles}</span>
                  <span className="text-white/70 text-xs font-medium uppercase hidden sm:inline">Completados</span>
                  <span className="text-white/70 text-xs font-medium uppercase sm:hidden">Comp</span>
                </div>
                {files.length > 0 && (
                  <div className="hidden sm:block px-1 py-0.5 bg-emerald-500/20 rounded-full border border-emerald-400/30 flex-shrink-0">
                    <span className="text-emerald-200 text-xs font-bold">{Math.round((successFiles / files.length) * 100)}%</span>
                  </div>
                )}
              </div>

              {/* Archivos con error */}
              <div className="flex items-center gap-1.5 bg-white/10 hover:bg-white/15 px-2 py-1.5 rounded-md border border-white/20 h-8 sm:h-9">
                <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-red-400 flex-shrink-0"></div>
                <div className="flex items-center gap-1">
                  <span className="text-white/90 font-semibold text-xs sm:text-sm">{errorFiles}</span>
                  <span className="text-white/70 text-xs font-medium uppercase hidden sm:inline">Errores</span>
                  <span className="text-white/70 text-xs font-medium uppercase sm:hidden">Err</span>
                </div>
                {files.length > 0 && (
                  <div className="hidden sm:block px-1 py-0.5 bg-red-500/20 rounded-full border border-red-400/30 flex-shrink-0">
                    <span className="text-red-200 text-xs font-bold">{Math.round((errorFiles / files.length) * 100)}%</span>
                  </div>
                )}
              </div>

              {/* Tamaño total */}
              <div className="flex items-center gap-1.5 bg-white/10 hover:bg-white/15 px-2 py-1.5 rounded-md border border-white/20 h-8 sm:h-9">
                <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-purple-400 flex-shrink-0"></div>
                <div className="flex items-center gap-1">
                  <span className="text-white/90 font-semibold text-xs sm:text-sm">
                    {files.length > 0 ? formatearTamano(files.reduce((total, archivo) => total + (archivo.size || 0), 0)) : '0 B'}
                  </span>
                  <span className="text-white/70 text-xs font-medium uppercase hidden sm:inline">Tamaño Total</span>
                  <span className="text-white/70 text-xs font-medium uppercase sm:hidden">Total</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

export default HeaderStats;
