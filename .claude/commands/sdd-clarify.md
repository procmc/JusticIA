---
description: SDD · Revisa la spec como un QA (solo detecta, no resuelve)
argument-hint: <carpeta-de-la-spec>
disallowed-tools: Edit, Write, NotebookEdit
agent: reviewer
---
Revisa `specs/$1/spec.md` como si fueras un QA muy profesional. Usa la skill `sdd`.

Lista:
1. Ambigüedades restantes (requisitos que no se pueden verificar ni comprobar con una prueba automatizada).
2. Contradicciones entre requisitos.
3. Casos límite no cubiertos.
4. Conflictos con `docs/constitution.md` o con las reglas de `CLAUDE.md`.
5. Conflictos con la documentación de planificación (ERS, historias de usuario, casos de uso) y requisitos que no indican su RF/RNF del ERS.

No propongas soluciones todavía: solo detecta. Formato: lista numerada, indicando en cada punto el requisito o la sección de la spec a la que se refiere.
