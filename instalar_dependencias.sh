#!/usr/bin/env bash
# ==============================================================================
# Script de Instalación de Dependencias del Sistema - JusticIA (Debian/Ubuntu)
# ==============================================================================
# Este script instala las dependencias del sistema necesarias para ejecutar
# el proyecto JusticIA en Debian / Ubuntu.
# - Python 3.11+
# - Node.js 18+ (LTS)
# - Ollama (si está disponible para la distro)
# - Git
# - ODBC Driver 18 for SQL Server (msodbcsql18)
# - Verificación y recomendaciones similares al script de PowerShell
#
# Uso: sudo ./instalar_dependencias.sh [--skip-optional] [--verbose]
#
set -o errexit
set -o pipefail

SKIP_OPTIONAL=0
VERBOSE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-optional) SKIP_OPTIONAL=1; shift ;;
    --verbose) VERBOSE=1; shift ;;
    -h|--help)
      cat <<EOF
Uso: sudo $0 [--skip-optional] [--verbose]
Instala dependencias para JusticIA en Debian/Ubuntu.
EOF
      exit 0
      ;;
    *) echo "Parámetro desconocido: $1"; exit 1 ;;
  esac
done

# Colores
GREEN="\e[32m"
YELLOW="\e[33m"
RED="\e[31m"
CYAN="\e[36m"
RESET="\e[0m"

info() { echo -e "${CYAN}[INFO]${RESET} $*"; }
success() { echo -e "${GREEN}[OK]${RESET} $*"; }
warn() { echo -e "${YELLOW}[WARN]${RESET} $*"; }
error() { echo -e "${RED}[ERROR]${RESET} $*"; }

if [[ $VERBOSE -eq 1 ]]; then
  set -x
fi

# Comprobar apt/apt-get
if ! command -v apt-get >/dev/null 2>&1; then
  error "Este script requiere apt/apt-get. Está pensado para Debian/Ubuntu."
  exit 1
fi

# Requiere privilegios root para instalar paquetes
SUDO=""
if [[ $EUID -ne 0 ]]; then
  warn "No se detectan privilegios root: usaré 'sudo' donde sea necesario."
  SUDO="sudo"
fi

echo ""
success "==============================================================="
success "    INSTALADOR DE DEPENDENCIAS DEL SISTEMA - JusticIA (Linux)"
success "==============================================================="
echo ""

# Helper para comprobar comando
has_cmd() { command -v "$1" >/dev/null 2>&1; }

# Eliminar archivos de sources.list.d que referencien packages.microsoft.com duplicados,
# dejando sólo microsoft-prod.list (si existe) o el primer archivo válido.
dedupe_microsoft_repos() {
  local files
  files=( $(grep -lR "packages.microsoft.com" /etc/apt/sources.list.d 2>/dev/null || true) )
  if [[ ${#files[@]} -le 1 ]]; then
    return 0
  fi
  info "Se detectaron entradas de repositorio Microsoft duplicadas: ${files[*]}"
  # preferir microsoft-prod.list
  local keep=""
  for f in "${files[@]}"; do
    if [[ $(basename "$f") == "microsoft-prod.list" ]]; then
      keep="$f"
      break
    fi
  done
  if [[ -z "$keep" ]]; then
    keep="${files[0]}"
  fi
  info "Manteniendo: $(basename "$keep")  (backup de los demás)"
  for f in "${files[@]}"; do
    if [[ "$f" != "$keep" ]]; then
      sudo cp "$f" "/root/$(basename "$f").bak_from_installer" || true
      sudo rm -f "$f" || true
      info "Eliminado archivo duplicado: $(basename "$f")"
    fi
  done
}

# INSTALAR/VERIFICAR Python 3.11+
info "Verificando Python..."
PY_ERROR=0
if has_cmd python3; then
  PY_VER_FULL=$(python3 -c 'import sys; print("{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro))')
  info "Python detectado: $PY_VER_FULL"
  PY_VER_SHORT=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  if [[ $(printf '%s\n' "$PY_VER_SHORT" "3.11" | sort -V | head -n1) = "3.11" ]] && [[ "$PY_VER_SHORT" != "3.11" ]]; then
    : # version > 3.11
  fi
  # simple check: if version < 3.11 -> install
  if python3 - <<'PY' 2>/dev/null
import sys
print(sys.version_info >= (3,11))
PY
  then
    success "OK Python3 >= 3.11 disponible"
  else
    warn "Python3 < 3.11 detectado. Se intentará instalar Python3.11 (deadsnakes)."
    $SUDO apt-get update
    $SUDO apt-get install -y software-properties-common curl
    $SUDO add-apt-repository -y ppa:deadsnakes/ppa || warn "No se pudo agregar ppa:deadsnakes, continuar..."
    $SUDO apt-get update
    if $SUDO apt-get install -y python3.11 python3.11-venv python3.11-distutils; then
      success "Python3.11 instalado correctamente"
    else
      error "No se pudo instalar Python3.11 automáticamente. Instálalo manualmente."
      PY_ERROR=1
    fi
  fi
else
  info "Python3 no está instalado. Instalando Python3.11..."
  $SUDO apt-get update
  $SUDO apt-get install -y software-properties-common curl
  $SUDO add-apt-repository -y ppa:deadsnakes/ppa || warn "No se pudo agregar ppa:deadsnakes, continuar..."
  $SUDO apt-get update
  if $SUDO apt-get install -y python3.11 python3.11-venv python3.11-distutils; then
    success "Python3.11 instalado correctamente"
  else
    error "No se pudo instalar Python3.11 automáticamente. Instálalo manualmente desde python.org o usa un paquete adecuado para tu distro."
    PY_ERROR=1
  fi
fi

# INSTALAR/VERIFICAR Node.js 18+
info "Verificando Node.js..."
NODE_ERROR=0
if has_cmd node; then
  NODE_VER=$(node -v 2>/dev/null || true)
  success "Node.js disponible: $NODE_VER"
  # comprobar versión >=18
  NODE_VNUM=$(echo "$NODE_VER" | sed 's/^v//')
  if ! printf '%s\n' "$NODE_VNUM" "18.0.0" | sort -V | head -n1 | grep -q "18.0.0"; then
    info "Instalando Node.js 18 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | $SUDO bash -
    $SUDO apt-get install -y nodejs || NODE_ERROR=1
  fi
else
  info "Node.js no está instalado. Instalando Node.js 18 LTS..."
  curl -fsSL https://deb.nodesource.com/setup_18.x | $SUDO bash -
  if $SUDO apt-get install -y nodejs; then
    success "Node.js instalado correctamente"
  else
    error "No se pudo instalar Node.js automáticamente. Instálalo manualmente desde nodejs.org"
    NODE_ERROR=1
  fi
fi

# npm
if has_cmd npm; then
  NPM_VER=$(npm -v 2>/dev/null || true)
  success "npm disponible: $NPM_VER"
else
  warn "npm no está disponible. Debería venir con nodejs."
fi

# Git
info "Verificando Git..."
if has_cmd git; then
  GIT_VER=$(git --version 2>/dev/null || true)
  success "Git detectado: $GIT_VER"
else
  info "Git no está instalado. Instalando..."
  if $SUDO apt-get update && $SUDO apt-get install -y git; then
    success "Git instalado correctamente"
  else
    warn "No se pudo instalar Git automáticamente. Instálalo manualmente."
  fi
fi

# ODBC Driver 18 for SQL Server (msodbcsql18)
info "Verificando ODBC Driver 18 for SQL Server (msodbcsql18)..."
ODBC_OK=0
if dpkg -l | grep -q msodbcsql18; then
  success "msodbcsql18 ya instalado"
  ODBC_OK=1
else
  info "Intentando instalar msodbcsql18 desde repositorios de Microsoft..."
  # Preparar repositorio de Microsoft
  $SUDO apt-get install -y curl apt-transport-https ca-certificates gnupg
  DISTRO_CODENAME=$(lsb_release -cs || echo "$(sed -n 's/^VERSION_CODENAME=//p' /etc/os-release || true)")
  if [[ -z "$DISTRO_CODENAME" ]]; then
    DISTRO_CODENAME="focal"
  fi
  # Importar key y agregar repo de forma robusta (sin prompts)
  TMP_GPG="/tmp/microsoft.gpg.$$"
  curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > "$TMP_GPG" || true
  if [[ -f "$TMP_GPG" ]]; then
    $SUDO mv -f "$TMP_GPG" /etc/apt/trusted.gpg.d/microsoft.gpg || true
  else
    warn "No se pudo descargar la clave GPG de Microsoft; continuando de todos modos"
  fi

  REPO_FILE="/etc/apt/sources.list.d/mssql-release.list"
  PROD_LIST_URL_BASE="https://packages.microsoft.com/config/ubuntu"

  # Obtener VERSION_ID (p.ej. 22.04, 24.04)
  VERSION_ID=$(grep '^VERSION_ID' /etc/os-release 2>/dev/null | cut -d '"' -f2 || true)
  if [[ -z "$VERSION_ID" ]]; then
    VERSION_ID=$(lsb_release -sr 2>/dev/null || true)
  fi

  # Versiones soportadas por Microsoft (según la documentación): 18.04 20.04 22.04 24.04 24.10
  SUPPORTED="18.04 20.04 22.04 24.04 24.10"
  if ! [[ " $SUPPORTED " == *" $VERSION_ID "* ]]; then
    warn "Ubuntu $VERSION_ID no está en la lista de versiones soportadas oficialmente por el instalador automático de Microsoft. Intentaremos usar la versión más cercana disponible (22.04/20.04)."
  else
    info "Detected supported Ubuntu VERSION_ID: $VERSION_ID"
  fi

  # Intenta descargar e instalar packages-microsoft-prod.deb para VERSION_ID o para una fallback list
  CAND=("$VERSION_ID" "22.04" "20.04")
  INSTALLED_DEB=0
  for c in "${CAND[@]}"; do
    if [[ -z "$c" ]]; then
      continue
    fi
    DEB_URL="$PROD_LIST_URL_BASE/$c/packages-microsoft-prod.deb"
    if curl -fsSLI "$DEB_URL" >/dev/null 2>&1; then
      info "Descargando e instalando packages-microsoft-prod.deb para: $c"
      TMP_DEB="/tmp/packages-microsoft-prod.$c.deb"
      if curl -fsSL "$DEB_URL" -o "$TMP_DEB"; then
        if $SUDO dpkg -i "$TMP_DEB"; then
          INSTALLED_DEB=1
          success "packages-microsoft-prod.deb instalado para $c"
        else
          warn "dpkg -i devolvió error, intentando reparar dependencias..."
          $SUDO apt-get install -f -y || true
          # reintentar dpkg -i
          $SUDO dpkg -i "$TMP_DEB" || true
        fi
        rm -f "$TMP_DEB" || true
        break
      else
        warn "No se pudo descargar $DEB_URL"
      fi
    else
      info "No existe packages-microsoft-prod.deb para: $c"
    fi
  done

  if [[ $INSTALLED_DEB -eq 0 ]]; then
    warn "No se pudo configurar el repositorio de Microsoft automáticamente. Consulta la documentación oficial: https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server"
  fi

  $SUDO apt-get update || true

  # Limpiar posibles repos duplicados de Microsoft
  dedupe_microsoft_repos || true

  # Aceptar el EULA creando el archivo requerido (a partir de 18.4 se permite crear el archivo)
  if [[ $INSTALLED_DEB -eq 1 ]]; then
    info "Creando /opt/microsoft/msodbcsql18/ACCEPT_EULA para aceptar el CLUF automáticamente"
    $SUDO mkdir -p /opt/microsoft/msodbcsql18 || true
    $SUDO touch /opt/microsoft/msodbcsql18/ACCEPT_EULA || true
  fi

  # Instalar msodbcsql18
  if [[ $INSTALLED_DEB -eq 1 ]]; then
    if [[ -n "$SUDO" ]]; then
      if $SUDO apt-get install -y msodbcsql18; then
        success "msodbcsql18 instalado correctamente"
        ODBC_OK=1
      else
        warn "No se pudo instalar msodbcsql18 automáticamente con apt-get"
      fi
    else
      if apt-get install -y msodbcsql18; then
        success "msodbcsql18 instalado correctamente"
        ODBC_OK=1
      else
        warn "No se pudo instalar msodbcsql18 automáticamente con apt-get"
      fi
    fi
  else
    warn "No se intentó instalar msodbcsql18 porque no se configuró el repo de Microsoft"
  fi

  # Instalar msodbcsql18 (manejar correctamente sudo + variable de entorno ACCEPT_EULA)
  if [[ -n "$SUDO" ]]; then
    # Cuando usamos sudo hay que ejecutar el comando como una sola cadena para que
    # la variable de entorno se aplique al proceso que ejecuta apt-get.
    if $SUDO bash -c "ACCEPT_EULA=Y apt-get install -y msodbcsql18"; then
      success "msodbcsql18 instalado correctamente"
      ODBC_OK=1
    else
      warn "No se pudo instalar msodbcsql18 automáticamente. Revisa las instrucciones oficiales: https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server"
    fi
  else
    if ACCEPT_EULA=Y apt-get install -y msodbcsql18; then
      success "msodbcsql18 instalado correctamente"
      ODBC_OK=1
    else
      warn "No se pudo instalar msodbcsql18 automáticamente. Revisa las instrucciones oficiales: https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server"
    fi
  fi
fi

# Ollama (intento de instalación simple) - si hay instrucciones oficiales para Linux
info "Verificando Ollama..."
if has_cmd ollama; then
  success "Ollama detectado"
else
  info "Ollama no detectado. Intentando instalación mediante script oficial..."
  # Intento de instalación por script oficial (si existe)
  if curl --version >/dev/null 2>&1; then
    OLLAMA_INSTALL_URL="https://ollama.com/install.sh"
    if curl -fsSLI "$OLLAMA_INSTALL_URL" >/dev/null 2>&1; then
      info "Descargando y ejecutando instalador de Ollama desde $OLLAMA_INSTALL_URL"
      # Ejecutar de forma segura: descargar y revisar antes de ejecutar
      TMP_OLLAMA="/tmp/ollama_install.sh"
      if curl -fsSL "$OLLAMA_INSTALL_URL" -o "$TMP_OLLAMA"; then
        chmod +x "$TMP_OLLAMA"
        # Ejecutar con sudo si es necesario
        if [[ -n "$SUDO" ]]; then
          $SUDO sh "$TMP_OLLAMA" || warn "El instalador de Ollama devolvió error, revisa $TMP_OLLAMA"
        else
          sh "$TMP_OLLAMA" || warn "El instalador de Ollama devolvió error, revisa $TMP_OLLAMA"
        fi
        rm -f "$TMP_OLLAMA" || true
        success "Intento de instalación de Ollama realizado (verifica manualmente)"
      else
        warn "No se pudo descargar $OLLAMA_INSTALL_URL"
      fi
    else
      warn "El instalador oficial de Ollama no está disponible en $OLLAMA_INSTALL_URL (404). Consulta https://ollama.com para instrucciones."
    fi
  else
    warn "curl no disponible; no puedo intentar instalar Ollama automáticamente."
  fi
fi

# Opcionales
if [[ $SKIP_OPTIONAL -eq 0 ]]; then
  info "Instalando herramientas opcionales..."
  # No añadimos terminales gráficos; dejamos opcional: install htop, unzip, build-essential
  $SUDO apt-get update
  $SUDO apt-get install -y htop unzip build-essential || warn "No se pudieron instalar algunos paquetes opcionales"
else
  info "Saltando paquetes opcionales (--skip-optional)"
fi

# Recarga de PATH no es necesaria en Linux para este script, pero mostramos verificación final
echo ""
info "VERIFICACIÓN FINAL..."

for tool in python3 node npm git ollama; do
  if has_cmd "$tool"; then
    ver=$($tool --version 2>/dev/null || $tool -v 2>/dev/null || echo "instalado")
    success "$tool: $ver"
  else
    warn "$tool: No disponible"
  fi
done

if [[ $ODBC_OK -eq 1 ]]; then
  success "ODBC Driver 18 for SQL Server: Instalado"
else
  warn "ODBC Driver 18 for SQL Server: No instalado o no verificado"
fi

if [[ $PY_ERROR -eq 1 || $NODE_ERROR -eq 1 ]]; then
  error "Hay dependencias críticas faltantes. Instala Python3.11 y Node.js 18+ manualmente y vuelve a ejecutar el script."
  exit 1
fi

echo ""
success "INSTALACIÓN COMPLETADA"
info "Próximos pasos:"
info "  1. Reinicia tu terminal si se actualizaron variables de entorno"
info "  2. Navega al directorio del proyecto: cd $(pwd)"
info "  3. Ejecuta el backend: cd backend && ./ejecutar.sh  (o el script correspondiente)"
info "  4. Ejecuta el frontend: cd frontend && npm install && npm run dev"
info "  5. Si instalaste Ollama, verifica: ollama list  y ollama serve"
info "  6. Para msodbcsql18 revisa la configuración de tu conexión a Azure SQL"

exit 0