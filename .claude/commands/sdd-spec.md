---
description: SDD · Entrevista y genera la spec (uso - /sdd-spec 001-nombre idea inicial)
argument-hint: <carpeta-de-la-spec> <idea inicial>
agent: planner
---
NO escribas código en ningún momento. Lee `docs/constitution.md` y `MEMORY.md`, y usa la skill `sdd`.

Carpeta de la spec: `specs/$1/`
Idea inicial (el texto que va después del nombre de la carpeta): $ARGUMENTS

Tu trabajo:
1. Ubica la idea en la documentación de planificación (`Documentacion/Documentacion_ServIA_2026/`): qué RF/RNF del ERS, historias de usuario y casos de uso toca, y si corresponde a un «Estado actual» pendiente. Si es algo nuevo que no está en la documentación, dímelo.
2. Hazme preguntas de UNA en UNA para eliminar ambigüedades (roles, casos límite, errores, qué queda fuera de esta versión). Máximo 15 preguntas.
3. Con mis respuestas, genera `specs/$1/spec.md` siguiendo la plantilla de la skill `sdd`: requisitos en EARS y en español, cada uno con el RF/RNF del ERS al que corresponde, y "Estado: borrador".
4. Solo el QUÉ y el POR QUÉ: nada de stack, arquitectura ni nombres de archivos. Usa el vocabulario del proyecto («tema», Usuario Gubernamental, Administrador).
