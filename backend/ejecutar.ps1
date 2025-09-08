# Verificar e instalar dependencias
if (!(Get-Command java -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando Java..."
    winget install Microsoft.OpenJDK.17
}

if (!(Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando FFmpeg..."
    winget install "FFmpeg (Essentials Build)"
    $env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Configurar entorno Python con Python 3.11.9
if (!(Test-Path ".venv")) {
    Write-Host "Creando entorno virtual con Python 3.11.9..."
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: No se pudo crear el entorno virtual con Python 3.11"
        Write-Host "Verificando si Python 3.11 esta instalado..."
        py -3.11 --version
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Python 3.11 no esta instalado. Usando Python por defecto..."
            python -m venv .venv
        }
    }
} else {
    Write-Host "Entorno virtual ya existe."
}

Write-Host "Activando entorno virtual..."
& .\.venv\Scripts\Activate.ps1

# Verificar activacion
if ($env:VIRTUAL_ENV) {
    Write-Host "Entorno virtual activado correctamente"
    Write-Host "Ruta del entorno: $env:VIRTUAL_ENV"
} else {
    Write-Host "Advertencia: El entorno virtual puede no estar activado correctamente"
}

Write-Host "Version de Python:" (python --version)

# Actualizar pip primero
Write-Host "Actualizando pip..."
python -m pip install --upgrade pip

# Instalar dependencias esenciales primero
Write-Host "Instalando dependencias esenciales..."
python -m pip install wheel setuptools

# Instalar dependencias principales
Write-Host "Instalando todas las dependencias..."
python -m pip install -r requirements.txt

# Ejecutar servidor
uvicorn main:app --reload
