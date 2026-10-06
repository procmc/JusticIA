#!/usr/bin/env bash
# validate-edit.sh — Hook PreToolUse del agente planner (Edit y Write): solo deja escribir dentro de specs/
# y en docs/constitution.md.
#
# Claude Code le pasa el evento en JSON por la entrada estándar.
# Respuesta: exit 0 = sigue el flujo normal de permisos; exit 2 = bloqueado (el motivo va por stderr a Claude).

bloquear() {
  echo "Bloqueado por validate-edit.sh: $1" >&2
  exit 2
}

# Leer la ruta del archivo y el directorio de trabajo del JSON (no hay jq en Git Bash; se usa node).
IFS=$'\t' read -r ruta cwd < <(node -e '
  let s = "";
  process.stdin.on("data", d => s += d).on("end", () => {
    try {
      const e = JSON.parse(s);
      process.stdout.write((e.tool_input.file_path || e.tool_input.notebook_path || "") + "\t" + (e.cwd || ""));
    } catch (err) {}
  });
')

[ -z "$ruta" ] && bloquear "no se pudo leer la ruta del archivo."

# Normalizar rutas de Windows y de Git Bash a la forma c:/usuarios/... en minúsculas.
normalizar() {
  printf '%s' "$1" | tr '\\' '/' | sed -E 's#^/([a-zA-Z])/#\1:/#; s#/+#/#g; s#/$##' | tr '[:upper:]' '[:lower:]'
}

proyecto="$(normalizar "${CLAUDE_PROJECT_DIR:-$(pwd)}")"
destino="$(normalizar "$ruta")"

# Ruta relativa: se resuelve desde el directorio de trabajo de la sesión.
case "$destino" in
  /*|[a-z]:/*) ;;
  *) destino="$(normalizar "${cwd:-$proyecto}")/$destino" ;;
esac

case "/$destino/" in
  */../*|*/./*) bloquear "la ruta no puede contener . ni .. («$ruta»)." ;;
esac

case "$destino" in
  "$proyecto/specs/"*|"$proyecto/docs/constitution.md") exit 0 ;;
  *) bloquear "el planner solo escribe dentro de specs/ y en docs/constitution.md («$ruta»). Si hace falta cambiar otro archivo, indícalo en tu respuesta." ;;
esac
