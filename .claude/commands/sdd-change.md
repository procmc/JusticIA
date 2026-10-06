---
description: SDD · Nuevo requisito o cambio de uno existente — primero la spec, luego el código
argument-hint: <carpeta-de-la-spec> <descripción del requisito>
agent: planner
---
Nuevo requisito para la spec `specs/$1/` (el texto que va después del nombre de la carpeta): $ARGUMENTS

NO toques código. Usa la skill `sdd`.

1. Actualiza `specs/$1/spec.md`: el requisito nuevo (o el cambio de uno existente) en formato EARS y en español, con el RF/RNF del ERS al que corresponde, sus casos límite y lo que queda fuera de alcance.
2. Revisa que no contradiga la documentación de planificación (`Documentacion/Documentacion_ServIA_2026/`) ni las reglas de `CLAUDE.md` y `docs/constitution.md`; si contradice algo, señálalo.
3. Indica qué partes de `plan.md` y `tasks.md` habría que cambiar después, y qué documentos habría que actualizar (ERS, historias de usuario, casos de uso o diagramas).
4. Muéstrame el diff de la spec y espera mi aprobación.
