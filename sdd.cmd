@echo off
rem Abre Claude Code con el agente coordinador como hilo principal (flujo SDD).
rem El coordinador solo lee y reparte el trabajo entre planner, implementer y reviewer:
rem no tiene terminal ni edita archivos. Para operar (docker, git, editar) abra una sesion normal con "claude".
cd /d "%~dp0"
claude --agent coordinator %*
