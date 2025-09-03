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

# Configurar entorno Python
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Ejecutar servidor
uvicorn main:app --reload
