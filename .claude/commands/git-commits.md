---
description: Prepara los commits de los cambios pendientes, uno por caso, para que Andrés los apruebe (no hace push)
argument-hint: [contexto opcional, p. ej. "solo la spec 002"]
agent: committer
---
Prepara los commits de los cambios pendientes del repositorio. Contexto adicional: $ARGUMENTS

El repositorio `procmc/JusticIA` es público y Andrés hace el push: tú solo agregas archivos y creas los commits, y únicamente después de que apruebe cada descripción.

## 1. Revisa el estado

Ejecuta `git branch --show-current`, `git status --short` y `git log --oneline -5` (para seguir el estilo de los commits anteriores).

## 2. Agrupa por caso

Un commit por caso, en este orden de dependencia: documentación → configuración de Claude (`CLAUDE.md`, `MEMORY.md`, `docs/constitution.md`, `.mcp.json`, `.claude/`) → cada spec (`specs/NNN-…/`) con el código que implementó → correcciones de errores aparte. Si hay algo que no encaja en ningún caso, pregunta.

## 3. Excluye siempre (y avísame si aparece)

- Credenciales y datos personales: `.env`, claves, tokens, `uploads/`, documentos cargados.
- Lo que Git ya ignora o no es del proyecto: `htr/dataset/`, `htr/resultados/`, `Registro_Indicaciones_2026/`, `.claude/settings.local.json`, `__pycache__/`.
- Material de terceros o con derechos de autor, y fotos o capturas con metadatos (por ejemplo `Documentacion/Pruebas/`).
- Nombres de personas o rutas del usuario que no deban ser públicos: antes de cada commit, busca en `git diff --cached` el nombre del tutor y rutas como `C:\Users\`.

Si algo sospechoso ya está versionable, no lo agregues y propón ignorarlo (el `.gitignore` lo modifica Andrés).

## 4. Agrega los archivos

- Por nombre o por carpeta concreta; nunca `git add .` ni `git add -A`.
- Para carpetas movidas, agrega juntas la vieja y la nueva (`git add -u <carpeta-vieja>` y `git add <carpeta-nueva>`), para que Git las detecte como movimientos.
- Después revisa `git diff --cached --name-status` y confirma que no entró nada de la sección 3.
- El hook de la terminal bloquea una línea que mezcla `git add` con la cadena `.env`, aunque sea en un `grep`: ejecuta esas verificaciones en comandos separados.

## 5. Describe y pide aprobación

Para cada commit, muéstrame los archivos agregados (resumen) y la descripción propuesta, y espera mi aprobación ANTES de crearlo:

- Título breve en imperativo, en español y sin tildes, como los commits anteriores.
- Cuerpo de máximo 70 palabras: qué se agrega o cambia y por qué.
- Sin pie de coautor ni mención de ningún autor (ni Claude ni Andrés).

## 6. Crea y verifica

Crea el commit con la descripción aprobada (`git commit -F -`), verifica con `git log --oneline -1` y pasa al siguiente. Al final muestra `git status --short` y lo que quedó sin versionar, con el motivo.

## Reglas

- Nunca `git push`, `--amend`, `rebase` ni reescribir el historial. Si un commit salió mal, no lo arregles solo: explícame qué pasó y qué opciones hay.
- Si el hook pide confirmación para `git commit`, es lo esperado: espera mi respuesta.
- Si una prueba o la suite estaba fallando antes de tocar nada, dilo; no la corrijas en este comando.
