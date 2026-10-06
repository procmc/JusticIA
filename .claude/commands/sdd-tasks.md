---
description: SDD · Divide el plan en tareas pequeñas y verificables
argument-hint: <carpeta-de-la-spec>
agent: planner
---
A partir de `specs/$1/spec.md` y `specs/$1/plan.md`, genera `specs/$1/tasks.md` siguiendo el formato de la skill `sdd`. NO escribas código.

- Tareas pequeñas (máx. 20-30 min cada una), en orden de dependencia (por ejemplo: migración → backend → Worker → frontend → verificación). Cada tarea empieza por sus pruebas.
- Cada una con los RF/RNF del ERS que cubre, una línea "Pruebas:" (las que se escriben primero) y una línea "Hecho cuando:" verificable: esas pruebas y la suite completa pasan, y el resultado concreto que se comprueba de punta a punta.
- Marca las tareas que tocan algo de la lista «Pregunta antes» de `CLAUDE.md` (esquema de la base de datos, prompts, modelos, `docker-compose.yml`…).
- La última tarea actualiza la documentación de planificación afectada (ERS y su «Estado actual», historias de usuario, casos de uso y diagramas).
- Checkboxes.
- Intenta que no sean más de 10: si salen más, propón dividir la spec.

Si el plan no está aprobado o tiene dudas abiertas, para y avísame.
