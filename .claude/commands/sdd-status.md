---
description: SDD · Dónde estamos - fase actual y siguiente paso de una spec
argument-hint: [carpeta-de-la-spec]
disallowed-tools: Edit, Write, NotebookEdit
agent: planner
---
Lee `specs/$1/` (`spec.md`, `plan.md` y `tasks.md`, los que existan) y `MEMORY.md`. Si no indico una carpeta, haz lo mismo con cada spec de `specs/` y dame una línea por spec.

Dime en pocas líneas:
1. En qué fase del flujo SDD está esta spec y su estado (borrador, aprobada, en implementación o implementada).
2. Tareas hechas y pendientes (x de y).
3. Qué RF/RNF del ERS cubre y cuáles ya quedaron implementados.
4. El siguiente paso exacto, con el comando `/sdd-*` que debo ejecutar.

No modifiques ningún archivo.
