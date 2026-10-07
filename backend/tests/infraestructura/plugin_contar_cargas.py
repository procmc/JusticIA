"""Plugin de la corrida hija que anota cuándo se carga el modelo de embeddings (spec 002, RA-02.6; T5).

Se carga con `-p tests.infraestructura.plugin_contar_cargas` en un proceso hijo de `pytest` (no lo
recolecta ninguna corrida: su nombre no empieza por `test_`). Cada vez que alguien crea un
`SentenceTransformer` (el modelo real), agrega al archivo que indica `RUTA_REGISTRO_CARGAS` la prueba
que estaba en curso. Así el padre comprueba que el modelo se carga una sola vez y solo cuando una
prueba pide `embeddings_reales`. No cambia el comportamiento del modelo.
"""
import os

import sentence_transformers

_iniciar_original = sentence_transformers.SentenceTransformer.__init__


def _iniciar_y_anotar(self, *args, **kwargs):
    ruta = os.environ.get("RUTA_REGISTRO_CARGAS")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as registro:
            registro.write(os.environ.get("PYTEST_CURRENT_TEST", "(fuera de una prueba)") + "\n")
    _iniciar_original(self, *args, **kwargs)


sentence_transformers.SentenceTransformer.__init__ = _iniciar_y_anotar
