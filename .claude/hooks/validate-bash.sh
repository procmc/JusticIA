#!/usr/bin/env bash
# validate-bash.sh — Hook PreToolUse de ServIA para los comandos de terminal (Bash y PowerShell).
#
# Claude Code le pasa el evento en JSON por la entrada estándar. Dos modos:
#   validate-bash.sh            General (settings.json, todos los agentes): bloquea lo «Nunca» de
#                               CLAUDE.md y pide confirmación para lo «Pregunta antes» de la terminal.
#   validate-bash.sh reviewer   Revisor (frontmatter de reviewer.md): además, solo deja pasar
#                               comandos de consulta.
#
# Respuesta: exit 0 sin salida = sigue el flujo normal de permisos (no aprueba nada por sí solo);
# exit 2 = bloqueado (el motivo va por stderr a Claude); JSON con "ask" = se le pregunta al usuario.

modo="${1:-general}"

bloquear() {
  echo "Bloqueado por validate-bash.sh: $1" >&2
  exit 2
}

preguntar() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

# contiene <texto> <ERE> (GNU grep); contiene_i ignora mayúsculas.
contiene() { printf '%s' "$1" | grep -qE -- "$2"; }
contiene_i() { printf '%s' "$1" | grep -qiE -- "$2"; }

# Leer el comando del JSON (no hay jq en Git Bash; se usa node). Los saltos de línea
# separan comandos, así que se convierten en «;».
comando="$(node -e '
  let s = "";
  process.stdin.on("data", d => s += d).on("end", () => {
    try { process.stdout.write(String(JSON.parse(s).tool_input.command || "").replace(/\r?\n/g, " ; ")); } catch (e) {}
  });
')"

if [ -z "$comando" ]; then
  # En modo general no se bloquea el trabajo por un fallo del hook; en modo revisor, sí.
  [ "$modo" = "reviewer" ] && bloquear "no se pudo leer el comando."
  exit 0
fi

inicio='(^|[;&|({[:space:]])'  # el comando empieza al inicio o después de un separador

# --- ❌ Nunca (CLAUDE.md) --------------------------------------------------------------------

contiene "$comando" "${inicio}git[[:space:]]+push([[:space:]].*)?[[:space:]](--force(-with-lease)?|-[a-zA-Z]*f\b|\+[^[:space:]]+)" \
  && bloquear "git push forzado: CLAUDE.md lo prohíbe (Nunca)."

contiene "$comando" "${inicio}git[[:space:]]+(rebase|filter-branch|filter-repo)\b" \
  && bloquear "reescribir el historial de Git: CLAUDE.md lo prohíbe (Nunca)."

contiene "$comando" "${inicio}git[[:space:]]+commit\b.*--amend" \
  && bloquear "git commit --amend reescribe el historial: CLAUDE.md lo prohíbe (Nunca)."

contiene "$comando" "${inicio}git[[:space:]]+add\b.*([[:space:]]-[a-zA-Z]*f\b|[[:space:]]--force\b|\.env([[:space:]\"']|$))" \
  && bloquear "git add forzado o de un .env: el repositorio es público y no se suben credenciales (Nunca)."

# --- ⚠️ Pregunta antes (CLAUDE.md) -----------------------------------------------------------

contiene "$comando" "${inicio}git[[:space:]]+(commit|push)\b" \
  && preguntar "CLAUDE.md: hacer commit o push requiere la confirmación de Andrés."

contiene "$comando" "${inicio}git[[:space:]]+(reset[[:space:]].*--hard|clean[[:space:]]+-[a-zA-Z]*f|checkout[[:space:]].*--[[:space:]]|restore\b)" \
  && preguntar "Este comando descarta cambios locales sin respaldo; confirme que es lo que quiere."

contiene "$comando" "${inicio}docker([[:space:]]+compose|-compose)[[:space:]]+down\b.*([[:space:]]-v\b|--volumes)|${inicio}docker[[:space:]]+(volume[[:space:]]+(rm|prune)|system[[:space:]]+prune)\b" \
  && preguntar "CLAUDE.md: borrar volúmenes elimina los datos de SQL Server, Qdrant o Redis."

contiene "$comando" "${inicio}alembic[[:space:]]+downgrade\b" \
  && preguntar "CLAUDE.md: revertir una migración cambia el esquema de la base de datos."

contiene_i "$comando" "${inicio}(rm|rmdir|del|rd|remove-item)[[:space:]].*uploads" \
  && preguntar "CLAUDE.md: borrar archivos de uploads/ requiere confirmación."

contiene_i "$comando" "delete[[:space:]]+from|drop[[:space:]]+(table|database)|truncate[[:space:]]+table" \
  && preguntar "CLAUDE.md: borrar datos de SQL Server requiere confirmación."

contiene_i "$comando" "(-X|--request)[[:space:]]*DELETE.*:6333|:6333.*(-X|--request)[[:space:]]*DELETE|:6333[^[:space:]]*/points/delete" \
  && preguntar "CLAUDE.md: borrar datos de Qdrant requiere confirmación."

[ "$modo" = "reviewer" ] || exit 0

# --- Modo revisor: solo comandos de consulta ---------------------------------------------------

# Estructura del comando: sin redirecciones inofensivas y sin el contenido entre comillas.
estructura="$(printf '%s' "$comando" \
  | sed -E 's/[0-9]?>&[0-9]//g; s#[0-9]?>[[:space:]]*/dev/null##g' \
  | sed -E "s/'[^']*'/''/g; s/\"[^\"]*\"/\"\"/g")"

case "$estructura" in
  *'>'*) bloquear "el revisor no escribe archivos: no uses redirecciones de salida (>)." ;;
  *'$('*|*'`'*|*'<('*) bloquear "el revisor no usa sustitución de comandos (\$( ), <( ) o comillas invertidas)." ;;
esac

contiene "$estructura" '(^|[[:space:]])--output\b' \
  && bloquear "el revisor no escribe archivos (--output)."

permitido='^((cd|pwd|ls|cat|head|tail|wc|grep)'
permitido+='|git (status|diff|log|show|ls-files|blame|rev-parse|branch --show-current)'
permitido+='|docker (ps|logs|images|stats --no-stream)'
permitido+='|docker compose (ps|logs|images|top)'
permitido+='|docker compose exec( -T)? backend (alembic (current|history|heads|check)|pytest)'
permitido+='|docker compose exec( -T)? servidor-htr (python -m )?pytest'
permitido+='|docker compose exec( -T)? ollama ollama (list|ps)'
permitido+='|curl|nvidia-smi|pytest|python -m pytest'
permitido+='|npm (run (build|lint)|test)|npm --prefix [^ ]+ run (build|lint))( |$)'

# Número de partes no vacías de los comandos encadenados (&&, ||, ;, |, &).
total_partes="$(printf '%s\n' "$estructura" | sed -E 's/(&&|\|\||;|\||&)/\n/g' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' | grep -c .)"

# Cada parte de los comandos encadenados (&&, ||, ;, |, &) debe estar en la lista.
while IFS= read -r parte; do
  parte="$(printf '%s' "$parte" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//; s/^([A-Za-z_][A-Za-z0-9_]*=[^ ]*[[:space:]]+)+//; s/[[:space:]]+/ /g')"
  [ -z "$parte" ] && continue
  # Único comando de «docker compose config» permitido: solo la lista de servicios (T10, RA-02.8). Debe ir
  # exacto y solo, sin encadenar: «docker compose config» a secas expande las variables del entorno y puede
  # imprimir credenciales, y con un encadenado («; cat .env», «| cat») se podría leer lo que no debe.
  if [ "$parte" = "docker compose config --services" ]; then
    [ "$total_partes" -eq 1 ] \
      || bloquear "«docker compose config --services» solo se permite como único comando, sin encadenar."
    continue
  fi
  contiene "$parte" "$permitido" \
    || bloquear "el revisor solo ejecuta comandos de consulta (git status/diff/log/show, docker compose ps/logs/config --services, curl local, npm run build/lint, pruebas). No permitido: «$parte»."
done < <(printf '%s\n' "$estructura" | sed -E 's/(&&|\|\||;|\||&)/\n/g')

# curl: solo servicios locales, sin escribir archivos y sin modificar datos.
while IFS= read -r parte; do
  parte="$(printf '%s' "$parte" | sed -E 's/^[[:space:]]+//; s/^([A-Za-z_][A-Za-z0-9_]*=[^ ]*[[:space:]]+)+//')"
  case "$parte" in curl|curl\ *) ;; *) continue ;; esac
  printf '%s' "$parte" | grep -oE "https?://[^[:space:]\"']+" | grep -vqE '^https?://(localhost|127\.0\.0\.1)([:/]|$)' \
    && bloquear "el revisor solo consulta los servicios locales (localhost)."
  contiene "$parte" '[[:space:]](-o|-O|--remote-name|-T|--upload-file)\b' \
    && bloquear "el revisor no descarga ni sube archivos con curl."
  contiene_i "$parte" '(-X|--request)[[:space:]]*(DELETE|PUT|PATCH)' \
    && bloquear "el revisor no modifica datos: solo GET, o POST de lectura a Qdrant."
  if contiene_i "$parte" '(-X|--request)[[:space:]]*POST|[[:space:]](-d|--data[a-z-]*|-F|--form|--json)\b'; then
    contiene "$parte" ':6333/collections/[^[:space:]]+/points/(scroll|count|search|query)' \
      || bloquear "el revisor solo hace POST de lectura a Qdrant (points/scroll, count, search o query)."
  fi
done < <(printf '%s\n' "$comando" | sed -E 's/(&&|\|\||;|\|)/\n/g')

exit 0
