---
description: SDD · Implementa UNA tarea, con la verificación definida primero (uso - /sdd-implement 001-nombre T3)
argument-hint: <carpeta-de-la-spec> <tarea>
agent: implementer
---
Implementa SOLO la tarea $2 de `specs/$1/tasks.md`, siguiendo `specs/$1/plan.md`, `docs/constitution.md`, `CLAUDE.md` y la skill `sdd`.

1. Antes del código, define cómo se comprueba la tarea:
   - Escribe primero sus pruebas automatizadas (las de la línea "Pruebas:") y comprueba que fallan. En una spec retroactiva, las pruebas siguen al ERS: si el código no lo cumple, márcalas como fallo esperado (`xfail`) con su referencia. Si corriges un error, empieza por su prueba de regresión.
   - Escribe también los pasos de verificación manual de punta a punta y el resultado esperado.
   - Si la infraestructura de pruebas todavía no existe, solo se implementan tareas de esa spec: si la tarea es de otra, detente y avísame.
2. Escribe el código hasta que las pruebas pasen. Si la tarea pide algo de la lista «Pregunta antes» de `CLAUDE.md` que el plan no haya aprobado (esquema de la base de datos, prompts, modelos, `docker-compose.yml`, commits…), detente y pregúntame.
3. Ejecuta las pruebas de la tarea, la suite completa (ninguna prueba existente puede romperse) y la verificación manual de la sección «Verificación» de `CLAUDE.md`, y muéstrame el resultado.
4. Marca $2 como hecha en `tasks.md` e indica qué RF/RNF del ERS cubre.
5. Actualiza `MEMORY.md` si la tarea cambió el estado del proyecto o dejó una decisión o un aprendizaje.

Después PÁRATE. No empieces la siguiente tarea.
