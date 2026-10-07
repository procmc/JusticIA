"""Resumen en español de cada corrida (spec 002, RA-02.1).

Funciones puras: reciben las estadísticas de pytest (`terminalreporter.stats`, un diccionario de
resultado a lista de informes) y devuelven los seis contadores, su texto y el código de salida.
El `conftest.py` raíz las engancha en `pytest_terminal_summary` y `pytest_sessionfinish`.

Con `xfail_strict = true`, pytest informa un fallo esperado que pasa como un FALLO con el texto
`[XPASS(strict)]`; aquí se reclasifica como XPASS para no mezclarlo con los fallos de verdad.

El resultado final depende también del código de salida de pytest: sin pruebas ejecutadas (código distinto
de 0 y 1) los seis ceros no son una «corrida correcta».
"""
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple

MARCA_XPASS_ESTRICTO = "[XPASS(strict)]"

# Códigos de salida de pytest con los que hubo pruebas ejecutadas: solo en esos el resultado sale de los contadores.
CODIGOS_CON_PRUEBAS_EJECUTADAS = (0, 1)

# Qué dice el resumen cuando el código de salida indica que NO hubo una corrida completa (M2 de T5).
RESULTADO_SIN_CORRIDA = {
    2: "la corrida se abortó o se interrumpió antes de terminar; las cifras son parciales",
    3: "error interno de pytest; la corrida no es fiable",
    4: "error de uso de pytest (opciones o rutas erróneas); no se ejecutaron pruebas",
    5: "no se ejecutó ninguna prueba: ninguna coincidió con el marcador, la ruta o el filtro pedido",
}


@dataclass(frozen=True)
class Resumen:
    """Los seis contadores de RA-02.1; `omitidas` guarda (prueba, motivo) de cada una."""

    pasan: int
    fallan: int
    fallos_esperados: int
    xpass: int
    errores: int
    omitidas: Tuple[Tuple[str, str], ...]


def _es_xpass_estricto(informe) -> bool:
    longrepr = getattr(informe, "longrepr", None)
    return isinstance(longrepr, str) and longrepr.startswith(MARCA_XPASS_ESTRICTO)


def _motivo_de_omitida(informe) -> str:
    """Motivo de una prueba omitida; pytest lo guarda como (archivo, línea, «Skipped: motivo»)."""
    longrepr = getattr(informe, "longrepr", None)
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        motivo = str(longrepr[2])
    else:
        motivo = str(longrepr) if longrepr else "sin motivo"
    return motivo.removeprefix("Skipped: ")


def calcular_resumen(estadisticas: Mapping[str, Sequence]) -> Resumen:
    """Cuenta los seis resultados a partir de las estadísticas de pytest."""
    fallos = list(estadisticas.get("failed", []))
    xpass_estrictos = [informe for informe in fallos if _es_xpass_estricto(informe)]
    return Resumen(
        pasan=len(estadisticas.get("passed", [])),
        fallan=len(fallos) - len(xpass_estrictos),
        fallos_esperados=len(estadisticas.get("xfailed", [])),
        xpass=len(xpass_estrictos) + len(estadisticas.get("xpassed", [])),
        errores=len(estadisticas.get("error", [])),
        omitidas=tuple(
            (getattr(informe, "nodeid", "?"), _motivo_de_omitida(informe))
            for informe in estadisticas.get("skipped", [])
        ),
    )


def codigo_salida(resumen: Resumen) -> int:
    """0 solo sin fallos, XPASS ni errores de preparación; las omitidas no lo afectan."""
    return 0 if resumen.fallan == 0 and resumen.xpass == 0 and resumen.errores == 0 else 1


def texto_resumen(
    resumen: Resumen, codigo_pytest: Optional[int] = None, motivo: Optional[str] = None, residuos: bool = False
) -> str:
    """Texto del resumen con los seis contadores y la última línea con el resultado.

    `codigo_pytest` es el código de salida con el que pytest cerró la corrida. Con 0 o 1 (hubo pruebas) el
    resultado sale de los contadores. Con cualquier otro (nada recolectado, aborto, interrupción, error
    interno o de uso) los seis ceros no significan éxito: el resumen dice que no hubo corrida completa y,
    si se conoce, el `motivo` (por ejemplo, el mensaje de aborto de una fixture). Sin código, solo cuentan
    los contadores. `residuos` es verdadero si al cerrar la sesión quedaron datos de prueba sin limpiar
    (RA-02.7): el cierre hace fallar la corrida aunque ninguna prueba haya fallado, y el resultado no debe
    anunciar éxito.
    """
    lineas = [
        f"  Pasan: {resumen.pasan}",
        f"  Fallan: {resumen.fallan}",
        f"  Fallos esperados: {resumen.fallos_esperados}",
        f"  XPASS (fallos esperados que pasan): {resumen.xpass}",
        f"  Errores de preparación: {resumen.errores}",
        f"  Omitidas: {len(resumen.omitidas)}",
    ]
    lineas += [f"    - {prueba}: {motivo_omitida}" for prueba, motivo_omitida in resumen.omitidas]
    if codigo_pytest is not None and int(codigo_pytest) not in CODIGOS_CON_PRUEBAS_EJECUTADAS:
        codigo = int(codigo_pytest)
        if motivo:
            lineas.append(f"Motivo: {motivo}")
        explicacion = RESULTADO_SIN_CORRIDA.get(codigo, "la corrida terminó con un código de salida inesperado")
        lineas.append(f"Resultado: {explicacion} (código de salida {codigo}).")
    elif codigo_salida(resumen) == 0 and residuos:
        lineas.append("Resultado: corrida con problemas (quedaron datos de prueba sin limpiar).")
    elif codigo_salida(resumen) == 0:
        lineas.append("Resultado: corrida correcta.")
    else:
        lineas.append("Resultado: corrida con problemas (hay fallos, XPASS o errores de preparación).")
    return "\n".join(lineas)
