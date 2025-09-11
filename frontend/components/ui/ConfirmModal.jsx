import { Modal, ModalContent, ModalHeader, ModalBody, ModalFooter, Button, Spinner } from "@heroui/react";
import { FiAlertTriangle, FiCheckCircle, FiInfo, FiX } from "react-icons/fi";

const ConfirmModal = ({ 
  isOpen, 
  onClose, 
  title, 
  description, 
  confirmText = "Confirmar", 
  cancelText = "Cancelar",
  confirmColor = "danger",
  onConfirm,
  icon = null,
  size = "md", // Nuevo prop para tamaño
  showIcon = true, // Nuevo prop para mostrar/ocultar ícono
  centered = true, // Nuevo prop para centrar contenido
  customContent = null, // Nuevo prop para contenido personalizado
  isLoading = false, // Nuevo prop para estado de carga
  disableBackdropClose = false // Nuevo prop para deshabilitar cierre por backdrop
}) => {
  
  // Configuración de temas y estilos
  const themeConfig = {
    danger: {
      icon: <FiAlertTriangle className="w-8 h-8" />,
      iconBg: "bg-red-100",
      iconColor: "text-red-600",
      titleColor: "text-red-900",
      gradient: "bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700"
    },
    success: {
      icon: <FiCheckCircle className="w-8 h-8" />,
      iconBg: "bg-green-100", 
      iconColor: "text-green-600",
      titleColor: "text-green-900",
      gradient: "bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700"
    },
    primary: {
      icon: <FiInfo className="w-8 h-8" />,
      iconBg: "bg-blue-100",
      iconColor: "text-blue-600", 
      titleColor: "text-blue-900",
      gradient: "bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700"
    },
    warning: {
      icon: <FiAlertTriangle className="w-8 h-8" />,
      iconBg: "bg-yellow-100",
      iconColor: "text-yellow-600",
      titleColor: "text-yellow-900", 
      gradient: "bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700"
    },
    default: {
      icon: <FiInfo className="w-8 h-8" />,
      iconBg: "bg-gray-100",
      iconColor: "text-gray-600",
      titleColor: "text-gray-900",
      gradient: "bg-gradient-to-r from-gray-500 to-gray-600 hover:from-gray-600 hover:to-gray-700"
    }
  };

  // Configuración de tamaños
  const sizeConfig = {
    sm: "max-w-sm",
    md: "max-w-lg", 
    lg: "max-w-2xl",
    xl: "max-w-4xl"
  };

  const currentTheme = themeConfig[confirmColor] || themeConfig.default;
  const modalIcon = icon || currentTheme.icon;

  const handleConfirm = () => {
    if (!isLoading) {
      onConfirm();
      if (!isLoading) {
        onClose();
      }
    }
  };

  const handleClose = () => {
    if (!isLoading && !disableBackdropClose) {
      onClose();
    }
  };

  // Componente para el ícono y título juntos
  const IconTitleSection = () => (
    <div className="flex items-center space-x-3">
      {showIcon && (
        <div className={`${currentTheme.iconBg} ${currentTheme.iconColor} p-3 rounded-full shadow-lg ring-2 ring-white/50`}>
          {modalIcon}
        </div>
      )}
      <h3 className={`text-xl font-bold ${currentTheme.titleColor} leading-tight flex-1`}>
        {title}
      </h3>
    </div>
  );

  // Componente para el contenido
  const ContentSection = () => (
    <div className={centered ? 'text-center' : 'text-left'}>
      {customContent ? (
        customContent
      ) : (
        <p className="text-gray-600 leading-relaxed text-base whitespace-pre-line">
          {description}
        </p>
      )}
    </div>
  );

  // Componente para los botones
  const ButtonSection = () => (
    <div className={`flex gap-2 ${centered ? 'justify-center' : 'justify-end'}`}>
      {cancelText && !isLoading && (
        <Button 
          color="default" 
          variant="bordered"
          onPress={handleClose}
          className="px-4 py-2 font-medium border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 rounded-md text-sm"
          size="sm"
        >
          {cancelText}
        </Button>
      )}
      <Button 
        color={confirmColor} 
        onPress={handleConfirm}
        isDisabled={isLoading}
        className="px-4 py-2 font-medium text-white rounded-md text-sm"
        size="sm"
        style={{
          backgroundColor: confirmColor === 'success' ? '#22c55e' : 
                         confirmColor === 'danger' ? '#ef4444' : 
                         confirmColor === 'primary' ? '#3b82f6' :
                         confirmColor === 'warning' ? '#f59e0b' : '#6b7280',
          opacity: isLoading ? 0.8 : 1
        }}
      >
        {confirmText}
      </Button>
    </div>
  );  return (
    <Modal 
      isOpen={isOpen} 
      onClose={handleClose}
      isDismissable={!isLoading && !disableBackdropClose}
      placement="center"
      backdrop="blur"
      size={size}
      motionProps={{
        variants: {
          enter: {
            y: 0,
            opacity: 1,
            scale: 1,
            transition: {
              duration: 0.3,
              ease: "easeOut",
            },
          },
          exit: {
            y: -20,
            opacity: 0,
            scale: 0.95,
            transition: {
              duration: 0.2,
              ease: "easeIn",
            },
          },
        }
      }}
      classNames={{
        base: `${sizeConfig[size]} mx-4`,
        backdrop: "bg-gradient-to-t from-zinc-900/50 to-zinc-900/50",
        body: "py-8 px-6",
        footer: "px-6 py-4",
        closeButton: "hover:bg-white/5 active:bg-white/10 transition-colors",
      }}
    >
      <ModalContent className="bg-white/95 backdrop-blur-md shadow-2xl border border-white/20">
        <ModalHeader className="flex flex-col gap-1 px-6 pt-6 pb-2 border-b-0">
          <IconTitleSection />
        </ModalHeader>
        
        <ModalBody className={centered ? 'text-center' : ''}>
          <ContentSection />
        </ModalBody>
        
        <ModalFooter className="">
          <ButtonSection />
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ConfirmModal;