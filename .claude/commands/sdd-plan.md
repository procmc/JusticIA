---
description: SDD · Genera el plan técnico de una spec aprobada
argument-hint: <carpeta-de-la-spec>
agent: planner
---
Lee `docs/constitution.md`, `CLAUDE.md`, `specs/$1/spec.md` y el código que la spec afecta. Usa la skill `sdd`. NO escribas código.

Genera `specs/$1/plan.md` con:
- **Archivos** que se crean o modifican (backend, Worker, frontend, migraciones) y la responsabilidad de cada uno.
- **Lógica**: qué va en cada capa (router → servicio → repositorio) y qué depende de servicios externos (SQL Server, Qdrant, Ollama, Redis, HTR).
- **Algoritmo o flujo** en pseudocódigo.
- **Datos**: cambios de esquema (migración de Alembic), de metadatos en Qdrant o de lo guardado en Redis, y cómo se conservan los datos existentes.
- **Interfaz**: cómo se muestra, con qué roles y qué mensajes en español (incluido `ROUTE_PERMISSIONS` si hay páginas nuevas).
- **Bitácora**: qué acciones se registran (RF-21).
- **Decisiones técnicas** justificadas, cada una con su alternativa descartada.
- **Pruebas**: las unitarias, de integración y de extremo a extremo que cubren cada requisito (según `.claude/rules/testing.md`), con los datos que usan en el entorno aislado; y lo que no se pueda automatizar de forma fiable, con su justificación.
- **Verificación manual**: los pasos de punta a punta que se harán además de las pruebas.
- **Documentación**: qué documentos y diagramas de `Documentacion/Documentacion_ServIA_2026/` habrá que actualizar.

Todo debe respetar la constitución y cubrir todos los requisitos de la spec. Marca qué RF/RNF del ERS cubre cada parte.

Si la spec no está aprobada o tiene dudas abiertas (por ejemplo, de `/sdd-clarify`), para y avísame.
