"""Marcador de cada prueba según su carpeta (spec 002, RA-02.1).

Funciones puras, sin pytest ni servicios: el `conftest.py` raíz las usa al recolectar para que
nadie tenga que acordarse de decorar cada prueba (`marcador_por_ruta`) y para la opción
`--orden-inverso` (`ordenar_pruebas`). Ver también: `backend/pytest.ini`.
"""
from pathlib import PurePath, PureWindowsPath
from typing import List, Sequence, Union

# Carpeta bajo `tests/` -> marcador registrado en `pytest.ini`.
MARCADOR_POR_CARPETA = {
    "unitarias": "unitaria",
    "integracion": "integracion",
    "infraestructura": "infraestructura",
}


def marcador_por_ruta(ruta: Union[str, PurePath]) -> str:
    """Devuelve el marcador de la carpeta bajo `tests/` que contiene la ruta.

    Decide la primera carpeta que sigue a un componente `tests` (así las subcarpetas, como
    `infraestructura/ejemplos_resumen/`, heredan el marcador de su carpeta de primer nivel).
    Lanza `ValueError` si la ruta no está en ninguna de las tres carpetas: una prueba fuera de
    ellas no debe quedar sin marcador en silencio.
    """
    # PureWindowsPath acepta tanto `\` como `/`, por lo que sirve en Linux y en Windows.
    partes = PureWindowsPath(str(ruta)).parts
    for indice, parte in enumerate(partes[:-1]):
        if parte == "tests" and partes[indice + 1] in MARCADOR_POR_CARPETA:
            return MARCADOR_POR_CARPETA[partes[indice + 1]]
    raise ValueError(
        f"La prueba '{ruta}' no está en tests/unitarias, tests/integracion ni tests/infraestructura."
    )


def ordenar_pruebas(pruebas: Sequence, inverso: bool) -> List:
    """Devuelve las pruebas en el orden en que se ejecutarán: el de pytest, o el contrario con `--orden-inverso`.

    Función pura (no modifica la lista que recibe). Ejecutarlas al revés, incluso dentro de cada archivo, comprueba que
    ninguna depende de lo que dejó otra (RA-02.7). Ver también: `conftest.py`, `pytest_collection_modifyitems`.
    """
    return list(reversed(pruebas)) if inverso else list(pruebas)
