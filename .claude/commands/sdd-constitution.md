---
description: SDD · Propone la constitución del proyecto (principios innegociables)
argument-hint: [contexto adicional]
disallowed-tools: Edit, Write, NotebookEdit
agent: planner
---
Vamos a crear (o revisar, si ya existe) `docs/constitution.md`. Usa la skill `sdd`.

Antes de proponer nada, lee `CLAUDE.md`, `MEMORY.md`, las restricciones (RN, RT, RA) y los requisitos no funcionales del ERS (`Documentacion/Documentacion_ServIA_2026/`) y el código del proyecto.

Contexto adicional: $ARGUMENTS

Proponme 7 principios innegociables, cortos y verificables, que cubran:
1. Simplicidad del stack y de la arquitectura (monolito modular, sin servicios ni dependencias nuevas sin justificación).
2. Relación entre la documentación de planificación, la spec y el código.
3. Separación entre lógica e interfaz, y acceso a los datos solo por el núcleo del backend.
4. Política de verificación y pruebas.
5. Protección de los datos institucionales y del repositorio público.
6. Inteligencia artificial 100 % local y modelos permitidos.
7. Idioma del código y de los textos, y vocabulario gubernamental.

Para cada principio, indica de qué requisito o restricción del ERS sale. Máximo 20 líneas.

NO escribas el archivo todavía: espera mi aprobación.
