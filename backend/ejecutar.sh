#!/usr/bin/env bash
set -euo pipefail

# ejecutar.sh - preparar entorno del backend y crear .venv con Python 3.11.9
# Este script intentará usar Python 3.11.9 del sistema; si no está, instalará
# pyenv (en $HOME/.pyenv) y compilará/instalará Python 3.11.9, luego creará
# el virtualenv en .venv usando exactamente esa versión.

PY_TARGET="3.11.9"
VENV_DIR=".venv"

# Detectar gestor de paquetes
PKG_MANAGER=""
if command -v apt-get >/dev/null 2>&1; then
	PKG_MANAGER="apt"
elif command -v dnf >/dev/null 2>&1; then
	PKG_MANAGER="dnf"
fi

install_pkg() {
	if [ "$PKG_MANAGER" = "apt" ]; then
		sudo apt-get install -y "$@"
	elif [ "$PKG_MANAGER" = "dnf" ]; then
		sudo dnf install -y "$@"
	else
		echo "[WARN] Gestor de paquetes no soportado: $*" >&2
		return 1
	fi
}

info(){ echo "[INFO] $*"; }
warn(){ echo "[WARN] $*"; }
err(){ echo "[ERROR] $*"; }

find_system_python() {
	for p in python3.11 python3; do
		if command -v "$p" >/dev/null 2>&1; then
			ver=$($p -c 'import sys; print("{}.{}.{}".format(*sys.version_info[:3]))' 2>/dev/null || true)
			if [ "$ver" = "$PY_TARGET" ]; then
				command -v "$p"
				return 0
			fi
		fi
	done
	return 1
}

install_pyenv_build_deps() {
	info "Instalando dependencias de compilación para pyenv/Python"
	if [ "$PKG_MANAGER" = "apt" ]; then
		sudo apt-get update || true
		install_pkg make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libffi-dev libncurses5-dev libncursesw5-dev xz-utils tk-dev liblzma-dev libgdbm-dev libnss3-dev || true
	elif [ "$PKG_MANAGER" = "dnf" ]; then
		install_pkg make gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel libffi-devel xz-devel tk-devel libuuid-devel || true
	else
		warn "No se instalarán dependencias automáticamente (gestor no soportado)"
	fi
}

ensure_pyenv() {
	export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
	export PATH="$PYENV_ROOT/bin:$PATH"
	if command -v pyenv >/dev/null 2>&1; then
		info "pyenv ya instalado"
		return 0
	fi
	info "Instalando pyenv en $PYENV_ROOT"
	if [ ! -d "$PYENV_ROOT" ]; then
		if ! command -v git >/dev/null 2>&1; then
			install_pkg git || warn "git no disponible: no se podrá instalar pyenv automáticamente"
		fi
		git clone https://github.com/pyenv/pyenv.git "$PYENV_ROOT" || { err "No se pudo clonar pyenv"; return 1; }
	fi
	export PATH="$PYENV_ROOT/bin:$PATH"
	return 0
}

ensure_python_target() {
	if sys_py=$(find_system_python); then
		info "Encontrado Python exacto en sistema: $sys_py"
		PY_EXEC="$sys_py"
		return 0
	fi

	info "Python $PY_TARGET no encontrado en sistema: intentaremos pyenv"
	install_pyenv_build_deps
	ensure_pyenv || return 1

	# usar pyenv desde su binario (evita depender de eval/initialization)
	PYENV_BIN="$PYENV_ROOT/bin/pyenv"
	if [ ! -x "$PYENV_BIN" ]; then
		err "No se encontró $PYENV_BIN"
		return 1
	fi

	if "$PYENV_BIN" versions --bare 2>/dev/null | grep -qx "$PY_TARGET"; then
		info "pyenv ya tiene la versión $PY_TARGET"
	else
		info "Instalando Python $PY_TARGET con pyenv (esto puede tardar varios minutos)"
		# pyenv install -s soporta usar versión ya instalada
		if ! "$PYENV_BIN" install -s "$PY_TARGET"; then
			err "Fallo al instalar Python $PY_TARGET con pyenv"
			return 1
		fi
	fi

	PY_EXEC="$PYENV_ROOT/versions/$PY_TARGET/bin/python3"
	if [ ! -x "$PY_EXEC" ]; then
		PY_EXEC="$PYENV_ROOT/versions/$PY_TARGET/bin/python"
	fi
	if [ ! -x "$PY_EXEC" ]; then
		err "No se encontró el ejecutable Python $PY_TARGET después de la instalación"
		return 1
	fi
	info "Usaremos $PY_EXEC para crear el venv"
	return 0
}

create_venv() {
	if [ -d "$VENV_DIR" ]; then
		info "$VENV_DIR ya existe. Verificando versión de Python dentro del venv."
		if [ -x "$VENV_DIR/bin/python" ]; then
			vver=$($VENV_DIR/bin/python -c 'import sys; print("{}.{}.{}".format(*sys.version_info[:3]))') || vver=""
			if [ "$vver" = "$PY_TARGET" ]; then
				info "El venv ya usa Python $PY_TARGET. Nada que hacer."
				return 0
			else
				warn "El venv existe pero usa Python $vver (no $PY_TARGET). Elimina $VENV_DIR para recrearlo si lo deseas."
				return 1
			fi
		else
			warn "$VENV_DIR existe pero no contiene bin/python ejecutable. Eliminándolo y recreando."
			rm -rf "$VENV_DIR"
		fi
	fi

	info "Creando venv con $PY_EXEC"
	"$PY_EXEC" -m venv "$VENV_DIR" || { err "Fallo al crear el entorno virtual con $PY_EXEC"; return 1; }
	"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel || true
	info "Entorno virtual creado exitosamente en $VENV_DIR usando $($VENV_DIR/bin/python --version 2>&1)"
	return 0
}

install_system_dependencies() {
	info "Verificando/instalando dependencias del sistema: Java y FFmpeg"
	# Java
	if ! command -v java >/dev/null 2>&1; then
		warn "Java no encontrado. Instalando OpenJDK 17"
		if [ "$PKG_MANAGER" = "apt" ]; then
			install_pkg openjdk-17-jdk || install_pkg default-jre || warn "No se pudo instalar OpenJDK via apt"
		elif [ "$PKG_MANAGER" = "dnf" ]; then
			install_pkg java-17-openjdk || warn "No se pudo instalar OpenJDK via dnf"
		else
			warn "Gestor de paquetes no soportado: no se instalará Java automáticamente"
		fi
	else
		info "Java ya instalado: $(java -version 2>&1 | head -n1)"
	fi

	# FFmpeg
	if ! command -v ffmpeg >/dev/null 2>&1; then
		warn "ffmpeg no encontrado. Instalando ffmpeg"
		if [ "$PKG_MANAGER" = "apt" ]; then
			install_pkg ffmpeg || warn "No se pudo instalar ffmpeg via apt"
		elif [ "$PKG_MANAGER" = "dnf" ]; then
			install_pkg ffmpeg || warn "No se pudo instalar ffmpeg via dnf"
		else
			warn "Gestor de paquetes no soportado: no se instalará ffmpeg automáticamente"
		fi
	else
		info "ffmpeg ya instalado: $(ffmpeg -version | head -n1)"
	fi
}

install_python_dependencies_and_run() {
	PY_BIN="$VENV_DIR/bin/python"
	PIP_BIN="$VENV_DIR/bin/pip"

	if [ ! -x "$PY_BIN" ]; then
		err "No se encontró $PY_BIN para instalar dependencias Python"
		return 1
	fi

	info "Actualizando pip, setuptools y wheel en el venv"
	"$PY_BIN" -m pip install --upgrade pip setuptools wheel || warn "Fallo al actualizar pip/setuptools/wheel"

	info "Instalando dependencias desde requirements.txt si existe"
	if [ -f requirements.txt ]; then
		# Ejecutar pip install y manejar el error correctamente; evitar ambigüedad de operadores
		"$PIP_BIN" install -r requirements.txt || { err "Fallo al instalar requirements.txt"; return 1; }
	else
		warn "No se encontró requirements.txt en el directorio actual"
	fi

	# Asegurar que uvicorn está disponible para ejecutar el servidor
	if ! "$PY_BIN" -m uvicorn --version >/dev/null 2>&1; then
		info "uvicorn no encontrado en el venv. Instalando uvicorn"
		"$PIP_BIN" install uvicorn || warn "Fallo al instalar uvicorn"
	fi

	info "Lanzando servidor: uvicorn main:app --reload (usando el venv)"
	# Ejecutar el servidor con el python del venv (esto bloqueará hasta que se detenga)
	exec "$PY_BIN" -m uvicorn main:app --reload
}

main() {
	if ! ensure_python_target; then
		err "No se pudo garantizar Python $PY_TARGET"
		exit 1
	fi

	if ! create_venv; then
		err "No se pudo crear el venv con Python $PY_TARGET"
		exit 1
	fi

	# Instalar dependencias del sistema que el script de Windows instala (Java, FFmpeg)
	install_system_dependencies || warn "Problemas instalando dependencias del sistema"

	info "Todo listo. El script ahora activará el venv e instalará dependencias Python y lanzará el servidor."
	info "Activa el entorno manualmente con: source $VENV_DIR/bin/activate"

	# Instalar dependencias Python e iniciar el servidor (reemplaza lo que hace el .ps1)
	install_python_dependencies_and_run
}

main "$@"

