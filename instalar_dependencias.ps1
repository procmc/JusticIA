# ===============================================================================
# Script de Instalación de Dependencias del Sistema - JusticIA
# ===============================================================================
# Este script instala todas las dependencias del sistema necesarias para 
# ejecutar el proyecto JusticIA en una máquina virtual de Azure con Windows.
# 
# Dependencias incluidas:
# - Python 3.11+ (instalación automática si no está presente)
# - Node.js LTS (instalación automática si no está presente)
# - Ollama (LLM local)
# - Git (control de versiones)
# - Windows Terminal (opcional)
# - Verificación y actualización automática de versiones
# ===============================================================================

param(
    [switch]$SkipOptional,
    [switch]$Verbose
)

# Configurar preferencias
$ErrorActionPreference = "Continue"
if ($Verbose) { $VerbosePreference = "Continue" }

# Función para escribir con colores
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    } else {
        $input | Write-Output
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success { Write-ColorOutput Green $args }
function Write-Warning { Write-ColorOutput Yellow $args }
function Write-Error { Write-ColorOutput Red $args }
function Write-Info { Write-ColorOutput Cyan $args }

# Banner de inicio
Write-Host ""
Write-Success "==============================================================="
Write-Success "    INSTALADOR DE DEPENDENCIAS DEL SISTEMA - JusticIA"
Write-Success "==============================================================="
Write-Host ""

# Verificar privilegios de administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Warning "ADVERTENCIA: Recomendacion: Ejecutar como Administrador para mejor compatibilidad"
    Write-Info "   Continuando sin privilegios de administrador..."
}

# Verificar Winget
Write-Info "Verificando Winget..."
try {
    $wingetVersion = winget --version
    Write-Success "OK Winget disponible: $wingetVersion"
} catch {
    Write-Error "ERROR Winget no está disponible"
    Write-Error "   Por favor instala 'App Installer' desde Microsoft Store"
    Write-Error "   O descárgalo desde: https://github.com/microsoft/winget-cli/releases"
    exit 1
}

# Función para verificar si una aplicación está instalada
function Test-Command($command) {
    try {
        Get-Command $command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Función para instalar con winget
function Install-WithWinget($name, $id, $command) {
    Write-Info "Verificando $name..."
    
    if (Test-Command $command) {
        $version = & $command --version 2>$null
        Write-Success "OK $name ya está instalado: $version"
        return $true
    }
    
    Write-Info "Instalando $name..."
    try {
        winget install $id --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            Write-Success "OK $name instalado correctamente"
            return $true
        } else {
            Write-Warning "ADVERTENCIA Posible problema durante la instalación de $name"
            return $false
        }
    } catch {
        Write-Error "ERROR instalando $name`: $_"
        return $false
    }
}

# ===============================================================================
# VERIFICACIÓN DE DEPENDENCIAS CRÍTICAS
# ===============================================================================

Write-Info ""
Write-Info "VERIFICANDO DEPENDENCIAS CRITICAS..."
Write-Info "====================================="

# Verificar Python
Write-Info "Verificando Python..."
if (Test-Command python) {
    $pythonVersion = python --version 2>$null
    Write-Success "OK Python disponible: $pythonVersion"
    
    # Verificar versión específica
    $version = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
    if ([version]$version -ge [version]"3.11.0") {
        Write-Success "OK Version de Python es adecuada (3.11+)"
    } else {
        Write-Warning "ADVERTENCIA Version de Python es antigua. Se recomienda 3.11+"
        Write-Info "Instalando Python 3.11..."
        try {
            winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0) {
                Write-Success "OK Python 3.11 instalado correctamente"
                # Recargar PATH para detectar nueva instalación
                $env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            } else {
                Write-Warning "ADVERTENCIA Problema instalando Python 3.11"
            }
        } catch {
            Write-Warning "ADVERTENCIA Error instalando Python 3.11: $_"
        }
    }
} else {
    Write-Info "Python no está instalado. Instalando Python 3.11..."
    try {
        winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            Write-Success "OK Python 3.11 instalado correctamente"
            # Recargar PATH para detectar nueva instalación
            $env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            
            # Verificar que la instalación fue exitosa
            Start-Sleep 2
            if (Test-Command python) {
                $pythonVersion = python --version 2>$null
                Write-Success "OK Python verificado: $pythonVersion"
            } else {
                Write-Warning "ADVERTENCIA Python instalado pero no detectado en PATH"
                $pythonError = $true
            }
        } else {
            Write-Error "ERROR No se pudo instalar Python 3.11"
            $pythonError = $true
        }
    } catch {
        Write-Error "ERROR instalando Python 3.11: $_"
        Write-Error "   Por favor instala Python 3.11+ manualmente desde python.org"
        $pythonError = $true
    }
}

# Verificar Node.js
Write-Info "Verificando Node.js..."
if (Test-Command node) {
    $nodeVersion = node --version 2>$null
    Write-Success "OK Node.js disponible: $nodeVersion"
    
    # Verificar versión
    $versionNumber = $nodeVersion -replace 'v', ''
    if ([version]$versionNumber -ge [version]"18.0.0") {
        Write-Success "OK Version de Node.js es adecuada (18+)"
    } else {
        Write-Warning "ADVERTENCIA Version de Node.js es antigua. Se recomienda 18+"
        Write-Info "Instalando Node.js LTS..."
        try {
            winget install OpenJS.NodeJS --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0) {
                Write-Success "OK Node.js LTS instalado correctamente"
                # Recargar PATH
                $env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            } else {
                Write-Warning "ADVERTENCIA Problema instalando Node.js"
            }
        } catch {
            Write-Warning "ADVERTENCIA Error instalando Node.js: $_"
        }
    }
} else {
    Write-Info "Node.js no está instalado. Instalando Node.js LTS..."
    try {
        winget install OpenJS.NodeJS --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            Write-Success "OK Node.js LTS instalado correctamente"
            # Recargar PATH
            $env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            
            # Verificar que la instalación fue exitosa
            Start-Sleep 2
            if (Test-Command node) {
                $nodeVersion = node --version 2>$null
                Write-Success "OK Node.js verificado: $nodeVersion"
            } else {
                Write-Warning "ADVERTENCIA Node.js instalado pero no detectado en PATH"
                $nodeError = $true
            }
        } else {
            Write-Error "ERROR No se pudo instalar Node.js"
            $nodeError = $true
        }
    } catch {
        Write-Error "ERROR instalando Node.js: $_"
        Write-Error "   Por favor instala Node.js LTS manualmente desde nodejs.org"
        $nodeError = $true
    }
}

# Verificar npm
if (Test-Command npm) {
    $npmVersion = npm --version 2>$null
    Write-Success "OK npm disponible: $npmVersion"
} else {
    Write-Warning "ADVERTENCIA npm no está disponible (debería venir con Node.js)"
}

# Si hay errores críticos, salir
if ($pythonError -or $nodeError) {
    Write-Error ""
    Write-Error "ERROR DEPENDENCIAS CRITICAS FALTANTES"
    Write-Error "   Por favor instala Python 3.11+ y Node.js 18+ antes de continuar"
    Write-Error "   Luego ejecuta este script nuevamente"
    exit 1
}

# ===============================================================================
# INSTALACIÓN DE DEPENDENCIAS DEL SISTEMA
# ===============================================================================

Write-Info ""
Write-Info "INSTALANDO DEPENDENCIAS DEL SISTEMA..."
Write-Info "======================================"

# Ollama (LLM local)
Write-Info ""
if (-not (Install-WithWinget "Ollama" "Ollama.Ollama" "ollama")) {
    Write-Warning "ADVERTENCIA No se pudo instalar Ollama automáticamente"
    Write-Info "   Descárgalo manualmente desde: https://ollama.ai/"
}

# Git
Write-Info ""
if (-not (Install-WithWinget "Git" "Git.Git" "git")) {
    Write-Warning "ADVERTENCIA No se pudo instalar Git automáticamente"
    Write-Info "   Descárgalo manualmente desde: https://git-scm.com/"
}

# ===============================================================================
# HERRAMIENTAS OPCIONALES (mejorar experiencia de desarrollo)
# ===============================================================================

if (-not $SkipOptional) {
    Write-Info ""
    Write-Info "INSTALANDO HERRAMIENTAS OPCIONALES..."
    Write-Info "====================================="
    
    # Windows Terminal
    Write-Info ""
    if (-not (Install-WithWinget "Windows Terminal" "Microsoft.WindowsTerminal" "wt")) {
        Write-Info "INFO Windows Terminal no se instaló (es opcional)"
        Write-Info "   Puedes instalarlo desde Microsoft Store"
    }
} else {
    Write-Info "SALTANDO herramientas opcionales (--SkipOptional especificado)"
}

# ===============================================================================
# CONFIGURACIÓN POST-INSTALACIÓN
# ===============================================================================

Write-Info ""
Write-Info "CONFIGURACION POST-INSTALACION..."
Write-Info "================================="

# Recargar PATH
Write-Info "Recargando variables de entorno..."
$env:PATH = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Verificar Ollama si se instaló
if (Test-Command ollama) {
    Write-Info "Configurando Ollama..."
    Write-Info "   Iniciando servicio Ollama en segundo plano..."
    
    # Iniciar Ollama como proceso en segundo plano
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep 3
    
    Write-Info "   Descargando modelo recomendado (llama3.2:3b)..."
    Write-Info "   Esto puede tomar varios minutos dependiendo de tu conexion..."
    
    try {
        ollama pull llama3.2:3b
        if ($LASTEXITCODE -eq 0) {
            Write-Success "OK Modelo llama3.2:3b descargado correctamente"
        } else {
            Write-Warning "ADVERTENCIA Error descargando modelo. Puedes hacerlo manualmente después:"
            Write-Info "   ollama pull llama3.2:3b"
        }
    } catch {
        Write-Warning "ADVERTENCIA Error configurando Ollama: $_"
        Write-Info "   Puedes configurarlo manualmente después con:"
        Write-Info "   ollama serve"
        Write-Info "   ollama pull llama3.2:3b"
    }
}

# ===============================================================================
# VERIFICACIÓN FINAL
# ===============================================================================

Write-Info ""
Write-Info "VERIFICACION FINAL..."
Write-Info "===================="

$tools = @(
    @{Name="Python"; Command="python"; Version="--version"}
    @{Name="Node.js"; Command="node"; Version="--version"}
    @{Name="npm"; Command="npm"; Version="--version"}
    @{Name="Git"; Command="git"; Version="--version"}
    @{Name="Ollama"; Command="ollama"; Version="--version"}
)

# No agregamos herramientas opcionales ya que quitamos VS Code

Write-Info ""
foreach ($tool in $tools) {
    if (Test-Command $tool.Command) {
        try {
            $version = & $tool.Command $tool.Version 2>$null | Select-Object -First 1
            Write-Success "OK $($tool.Name): $version"
        } catch {
            Write-Success "OK $($tool.Name): Instalado"
        }
    } else {
        Write-Warning "ADVERTENCIA $($tool.Name): No disponible"
    }
}

# ===============================================================================
# INSTRUCCIONES FINALES
# ===============================================================================

Write-Info ""
Write-Success "INSTALACION COMPLETADA!"
Write-Success "======================="
Write-Info ""
Write-Info "PROXIMOS PASOS:"
Write-Info ""
Write-Info "1. Reinicia PowerShell/Terminal para cargar nuevas variables PATH"
Write-Info ""
Write-Info "2. Navega al directorio del proyecto:"
Write-Info "   cd C:\JusticIA"
Write-Info ""
Write-Info "3. Ejecuta el backend:"
Write-Info "   cd backend"
Write-Info "   .\ejecutar.ps1"
Write-Info ""
Write-Info "4. En otra terminal, ejecuta el frontend:"
Write-Info "   cd frontend"
Write-Info "   npm install"
Write-Info "   npm run dev"
Write-Info ""
Write-Info "5. Si Ollama esta instalado, verifica que este funcionando:"
Write-Info "   ollama list"
Write-Info "   ollama serve (si no esta ejecutandose automaticamente)"
Write-Info ""
Write-Warning "IMPORTANTE: Es recomendable reiniciar el terminal despues de esta instalacion"
Write-Info ""
Write-Success "Tu entorno esta listo para ejecutar JusticIA!"
Write-Info ""
