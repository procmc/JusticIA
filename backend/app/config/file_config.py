# Configuración de archivos permitidos para ingesta
ALLOWED_FILE_TYPES = {
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/rtf': ['.rtf'],
    'text/plain': ['.txt'],
    'text/html': ['.html', '.htm'],
    'application/xhtml+xml': ['.xhtml'],
    'audio/mpeg': ['.mp3'],
    'audio/mp3': ['.mp3'],
    'audio/wav': ['.wav'],
    'audio/x-wav': ['.wav'],
    'audio/wave': ['.wav'],
    'audio/ogg': ['.ogg'],
    'application/ogg': ['.ogg'],
    'audio/mp4': ['.m4a'],
    'audio/x-m4a': ['.m4a']
}

# Límite de tamaño de archivo (1GB)
MAX_FILE_SIZE = 1024 * 1024 * 1024

# Extensiones permitidas
ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.rtf', '.txt', '.html', '.htm', '.xhtml', '.mp3', '.wav', '.ogg', '.m4a']

# Mapeo de extensiones a códigos numéricos para Milvus
FILE_TYPE_CODES = {
    '.txt': 1,
    '.pdf': 2,
    '.doc': 3,
    '.docx': 4,
    '.rtf': 5,
    '.html': 6,
    '.htm': 6,
    '.xhtml': 6,
    '.mp3': 10,
    '.wav': 11,
    '.ogg': 12,
    '.m4a': 13
}
