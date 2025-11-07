"""
Constantes relacionadas con el sistema de avatares de usuarios.
"""

from typing import List

# Tipos de avatar permitidos
AVATAR_TYPES = {
    "initials": "initials",  # Avatar generado con iniciales
    "hombre": "hombre",      # Avatar predefinido masculino
    "mujer": "mujer"         # Avatar predefinido femenino
}

# Rutas de avatares predefinidos
AVATAR_PREDEFINED_PATHS = {
    "hombre": "/img/profile/male-default.svg",
    "mujer": "/img/profile/female-default.svg"
}

# Configuración de archivos de imagen
MAX_AVATAR_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]

# Directorio de almacenamiento
AVATAR_UPLOAD_DIR = "uploads/profiles"
