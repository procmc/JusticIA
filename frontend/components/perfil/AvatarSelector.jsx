import React, { useState, useRef } from 'react';
import { Modal, ModalContent, ModalHeader, ModalBody, ModalFooter, Button, Tabs, Tab } from '@heroui/react';
import Image from 'next/image';
import { IoCamera, IoGrid, IoCloudUpload, IoRefresh, IoCheckmarkCircle } from 'react-icons/io5';
import Toast from '@/components/ui/CustomAlert';

/**
 * Componente para seleccionar o cargar un avatar personalizado
 * Opciones: Masculino, Femenino, Iniciales, o subir foto propia
 */
const AvatarSelector = ({ isOpen, onClose, currentAvatar, onSave, userName = '', userLastName = '' }) => {
  const [selectedAvatar, setSelectedAvatar] = useState(currentAvatar);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null); // Nuevo: guardar archivo real
  const [isUploading, setIsUploading] = useState(false);
  const [activeTab, setActiveTab] = useState('predefined');
  const fileInputRef = useRef(null);

  // Lista de avatares predefinidos disponibles
  const predefinedAvatars = [
    { id: 'male', label: 'Avatar Masculino', path: '/usser hombre.png' },
    { id: 'female', label: 'Avatar Femenino', path: '/usser mujer.png' },
    { id: 'initials', label: 'Mis Iniciales', path: 'initials' }, // Se genera dinámicamente
  ];

  /**
   * Generar avatar con iniciales
   */
  const generateInitialsAvatar = () => {
    const firstName = userName?.trim() || '';
    const lastName = userLastName?.trim() || '';
    const initials = `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase() || 'U';
    
    // Crear SVG con iniciales usando el mismo azul que los otros avatares
    const svg = `data:image/svg+xml,${encodeURIComponent(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
        <circle cx="100" cy="100" r="100" fill="#1B5E9F"/>
        <text x="100" y="100" font-family="Arial, sans-serif" font-size="80" font-weight="bold" 
              fill="white" text-anchor="middle" dominant-baseline="central">${initials}</text>
      </svg>
    `)}`;
    
    return svg;
  };

  /**
   * Manejar selección de avatar predefinido
   */
  const handleSelectPredefined = (avatar) => {
    if (avatar.id === 'initials') {
      const initialsAvatar = generateInitialsAvatar();
      setSelectedAvatar(initialsAvatar);
    } else {
      setSelectedAvatar(avatar.path);
    }
    setUploadedImage(null); // Limpiar imagen subida si existe
    setUploadedFile(null); // Limpiar archivo
  };

  /**
   * Manejar carga de imagen personalizada
   */
  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validar tipo de archivo
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      Toast.error('Formato no válido. Use JPG, PNG, GIF o WebP');
      return;
    }

    // Validar tamaño (máximo 5MB)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      Toast.error('La imagen es muy grande. Tamaño máximo: 5MB');
      return;
    }

    setIsUploading(true);
    setUploadedFile(file); // Guardar archivo real

    // Leer el archivo como Data URL para preview
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result;
      setUploadedImage(dataUrl);
      setSelectedAvatar(dataUrl);
      setIsUploading(false);
      Toast.success('Imagen cargada correctamente');
    };
    reader.onerror = () => {
      Toast.error('Error al cargar la imagen');
      setIsUploading(false);
    };
    reader.readAsDataURL(file);
  };

  /**
   * Abrir selector de archivos
   */
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  /**
   * Guardar avatar seleccionado
   */
  const handleSave = async () => {
    // Si hay un archivo subido, enviarlo
    const avatarToSave = uploadedFile || selectedAvatar;
    const success = await onSave(avatarToSave);
    if (success) {
      Toast.success('Avatar actualizado correctamente');
      onClose();
    } else {
      Toast.error('Error al guardar el avatar');
    }
  };

  /**
   * Resetear al avatar por defecto
   */
  const handleReset = () => {
    setSelectedAvatar('/usser hombre.png');
    setUploadedImage(null);
    setUploadedFile(null);
  };

  /**
   * Obtener vista previa del avatar
   */
  const getAvatarPreview = () => {
    return selectedAvatar;
  };

  /**
   * Verificar si es el avatar de iniciales
   */
  const isInitialsAvatar = (avatarPath) => {
    return avatarPath?.includes('data:image/svg') && avatarPath?.includes('circle');
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      size="2xl"
      scrollBehavior="inside"
      classNames={{
        base: "bg-white",
        header: "border-b border-gray-200",
        body: "py-6",
        footer: "border-t border-gray-200"
      }}
    >
      <ModalContent>
        {(onCloseModal) => (
          <>
            <ModalHeader className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <IoCamera className="text-primary text-2xl" />
                <h2 className="text-xl font-semibold">Cambiar Avatar</h2>
              </div>
              <p className="text-sm text-gray-500 font-normal">
                Personaliza tu imagen de perfil
              </p>
            </ModalHeader>

            <ModalBody>
              {/* Vista previa del avatar seleccionado */}
              <div className="flex flex-col items-center mb-6">
                <div className="relative">
                  <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-primary shadow-lg bg-white">
                    {getAvatarPreview().startsWith('data:') ? (
                      <img
                        src={getAvatarPreview()}
                        alt="Avatar Preview"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <Image
                        src={getAvatarPreview()}
                        alt="Avatar Preview"
                        width={128}
                        height={128}
                        className="object-cover w-full h-full"
                        onError={(e) => {
                          e.target.src = '/usser hombre.png';
                        }}
                      />
                    )}
                  </div>
                  {selectedAvatar !== currentAvatar && (
                    <div className="absolute -bottom-2 -right-2 bg-green-500 rounded-full p-2 shadow-lg">
                      <IoCheckmarkCircle className="text-white text-xl" />
                    </div>
                  )}
                </div>
                <p className="text-sm text-gray-600 mt-3">
                  {selectedAvatar === '/usser hombre.png' ? 'Avatar por defecto' : 'Avatar personalizado'}
                </p>
              </div>

              {/* Tabs para avatares predefinidos y subir imagen */}
              <Tabs 
                aria-label="Avatar options"
                selectedKey={activeTab}
                onSelectionChange={setActiveTab}
                variant="underlined"
                classNames={{
                  tabList: "gap-6",
                  cursor: "bg-primary",
                  tab: "px-0",
                }}
              >
                {/* Tab de Avatares Predefinidos */}
                <Tab
                  key="predefined"
                  title={
                    <div className="flex items-center gap-2">
                      <IoGrid />
                      <span>Avatares</span>
                    </div>
                  }
                >
                  <div className="grid grid-cols-3 gap-4 mt-4">
                    {predefinedAvatars.map((avatar) => {
                      const isInitials = avatar.id === 'initials';
                      const isSelected = isInitials 
                        ? isInitialsAvatar(selectedAvatar)
                        : selectedAvatar === avatar.path;

                      return (
                        <button
                          key={avatar.id}
                          onClick={() => handleSelectPredefined(avatar)}
                          className={`relative rounded-lg overflow-hidden transition-all hover:scale-105 flex flex-col items-center justify-center p-4 ${
                            isSelected
                              ? 'ring-4 ring-primary shadow-lg bg-primary/5' 
                              : 'ring-2 ring-gray-200 hover:ring-primary/50 bg-white'
                          }`}
                        >
                          {isInitials ? (
                            <div className="w-full flex flex-col items-center justify-center gap-2">
                              <div className="w-20 h-20 rounded-full bg-[#1B5E9F] flex items-center justify-center">
                                <span className="text-white text-2xl font-bold">
                                  {`${userName?.charAt(0) || 'U'}${userLastName?.charAt(0) || 'S'}`.toUpperCase()}
                                </span>
                              </div>
                              <span className="text-xs text-gray-600 text-center">{avatar.label}</span>
                            </div>
                          ) : (
                            <>
                              <div className="w-20 h-20 rounded-full overflow-hidden">
                                <Image
                                  src={avatar.path}
                                  alt={avatar.label}
                                  width={80}
                                  height={80}
                                  className="object-cover w-full h-full"
                                  onError={(e) => {
                                    e.target.src = '/usser hombre.png';
                                  }}
                                />
                              </div>
                              <span className="text-xs text-gray-600 mt-2 text-center">{avatar.label}</span>
                            </>
                          )}
                          
                          {isSelected && (
                            <div className="absolute top-2 right-2 bg-primary rounded-full p-1">
                              <IoCheckmarkCircle className="text-white text-xl" />
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </Tab>

                {/* Tab de Subir Imagen */}
                <Tab
                  key="upload"
                  title={
                    <div className="flex items-center gap-2">
                      <IoCloudUpload />
                      <span>Subir Foto</span>
                    </div>
                  }
                >
                  <div className="mt-4">
                    <div
                      onClick={handleUploadClick}
                      className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-primary hover:bg-primary/5 transition-all"
                    >
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                      
                      <IoCloudUpload className="text-5xl text-gray-400 mx-auto mb-3" />
                      
                      <p className="text-base font-medium text-gray-700 mb-1">
                        {isUploading ? 'Cargando...' : 'Haz clic para cargar una imagen'}
                      </p>
                      
                      <p className="text-sm text-gray-500">
                        JPG, PNG, GIF o WebP (máx. 5MB)
                      </p>
                    </div>

                    {uploadedImage && (
                      <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-center gap-2 text-green-700">
                          <IoCheckmarkCircle className="text-xl" />
                          <span className="text-sm font-medium">
                            Imagen cargada correctamente
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </Tab>
              </Tabs>
            </ModalBody>

            <ModalFooter>
              <div className="flex items-center justify-between w-full">
                <Button
                  color="danger"
                  variant="light"
                  onPress={handleReset}
                  startContent={<IoRefresh />}
                  size="sm"
                >
                  Restablecer
                </Button>
                
                <div className="flex gap-2">
                  <Button
                    color="default"
                    variant="light"
                    onPress={onCloseModal}
                  >
                    Cancelar
                  </Button>
                  <Button
                    color="primary"
                    onPress={handleSave}
                    isDisabled={selectedAvatar === currentAvatar}
                  >
                    Guardar Avatar
                  </Button>
                </div>
              </div>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
};

export default AvatarSelector;
