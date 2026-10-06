---
description: Planifica una nueva funcionalidad de ServIA antes de tocar código
argument-hint: <descripción de la funcionalidad>
agent: planner
---
Quiero añadir esta funcionalidad: $ARGUMENTS

Antes de escribir código, prepárame un plan con:

1. **Requisitos**: qué RF/RNF del ERS, historias de usuario y casos de uso cubre (están en `Documentacion/Documentacion_ServIA_2026/`). Si la funcionalidad no está en la documentación, dímelo: primero se agrega ahí, porque los documentos definen el producto.
2. **Implementación**: cómo la vas a hacer respetando las reglas de `CLAUDE.md` (router → servicio → repositorio, acceso a datos por el núcleo, registro en la bitácora, `ROUTE_PERMISSIONS`, vocabulario «tema» y textos en español).
3. **Archivos**: qué archivos vas a modificar o crear (backend, Worker, frontend, migraciones) y qué cambia en cada uno.
4. **Datos**: si toca el esquema de SQL Server, los metadatos de Qdrant o lo guardado en Redis, y cómo se conservan los datos existentes.
5. **Casos límite y dudas** que debo decidir yo antes de empezar (roles, errores y qué se registra en la bitácora).
6. **Pruebas y verificación**: las pruebas automatizadas que escribirás primero (unitarias, de integración y de extremo a extremo, según `.claude/rules/testing.md`) y cómo la vas a verificar de punta a punta, según la sección «Verificación» de `CLAUDE.md`.
7. **Documentación**: qué actualizarías en el ERS (o su «Estado actual»), las historias de usuario, los casos de uso y los diagramas, y en `CLAUDE.md` y `MEMORY.md`.

Ten en cuenta el estado actual del proyecto: @MEMORY.md

No modifiques ningún archivo hasta que apruebe el plan.
