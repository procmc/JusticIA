# Dependencias del Sistema - JusticIA

## Requisitos
- Java 17+ (para Apache Tika)
- FFmpeg (para Whisper/Audio)

## Windows
```powershell
# Instalar Java
winget install Microsoft.OpenJDK.17

# Instalar FFmpeg
winget install "FFmpeg (Essentials Build)"

# Ejecutar proyecto
.\ejecutar.ps1
```

## Oracle Linux 8.8 (Producción)
```bash
# Instalar dependencias
sudo dnf install java-17-openjdk-devel ffmpeg

# Ejecutar proyecto
./ejecutar.sh
```

## Verificación
```bash
java -version
ffmpeg -version
```

## 📋 Requisitos Previos

### 🐍 Python
- **Versión requerida**: Python 3.11 o superior
- **Verificación**: `python --version`

### 🗃️ Base de Datos
- **SQL Server Azure**: Configurado y accesible
- **Milvus Cloud**: Instancia serverless configurada

---

## ☕ Java (Requerido para Apache Tika)

Apache Tika necesita Java para procesar documentos (PDF, DOC, DOCX, RTF).

### 🪟 Windows

#### Opción 1: Winget (Recomendado)
```powershell
# Verificar si Winget está disponible
winget --version

# Instalar OpenJDK
winget install Microsoft.OpenJDK.17
```

### 🐧 Linux

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install openjdk-17-jdk
```

### ✅ Verificación Java
```bash
java -version
# Debe mostrar: openjdk version "17.x.x" o similar
```

---

## 🎵 FFmpeg (Requerido para Whisper/Audio)

FFmpeg es necesario para procesar archivos de audio (MP3) con Whisper.

### 🪟 Windows

#### Opción 1: Winget (Recomendado)
```powershell
# Verificar Winget
winget --version

# Instalar FFmpeg
winget install "FFmpeg (Essentials Build)"

# Recargar PATH (en la misma sesión)
$env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

### 🐧 Linux

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

### ✅ Verificación FFmpeg
```bash
ffmpeg -version
# Debe mostrar información de FFmpeg
```

---

## 📝 Notas Importantes

- ⚠️ **Reiniciar terminal** después de instalar para recargar PATH
- ⚠️ **Reiniciar servidor FastAPI** para que tome las nuevas dependencias
- ⚠️ En **Docker** las dependencias se manejan automáticamente
- ⚠️ En **producción** considera usar contenedores para evitar problemas de dependencias

---