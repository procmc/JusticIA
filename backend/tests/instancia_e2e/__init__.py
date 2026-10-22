"""Instancia del backend para las pruebas de extremo a extremo (spec 005a).

Un segundo proceso del contenedor `backend` (`python -m tests.instancia_e2e`) que sirve la aplicación real en el puerto
8100 con su propia base y colección (`servia_pruebas_e2e`), Redis, Ollama, HTR, audio y correo simulados y un router de
control que solo existe aquí. Ver también: `tests/soporte/` (la protección y los simulados de la spec 002).
"""
