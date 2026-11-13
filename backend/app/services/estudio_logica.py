"""Lógica pura del Estudio del notebook (spec 010: RF-11.122, RF-11.125, RF-11.126, RF-12.120, RF-14.120, RF-14.122).

Módulo puro: no llama al motor, a Qdrant ni a la base de datos. Parte el contenido de las fuentes en «partes» que caben en la
ventana del modelo (RF-11.126), valida la estructura del mapa mental (RF-11.125), comprueba que un texto cite alguna fuente de la
selección (RF-12.120) y arma el título por omisión de un resultado (RF-14.120).

Ver también: `app.services.estudio_service` (quien lo usa) y `app.services.presupuesto_contexto` (el estimador de tokens).
"""
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence

from app.config.contexto_config import CONFIGURACION, ConfiguracionContexto
from app.services.RAG.presupuesto_contexto import tokens

TIPO_RESUMEN = "resumen"
TIPO_INFORME = "informe"
TIPO_MAPA = "mapa_mental"
TIPO_NOTA = "nota"
TIPOS_GENERABLES = (TIPO_RESUMEN, TIPO_INFORME, TIPO_MAPA)
ETIQUETAS: Dict[str, str] = {
    TIPO_RESUMEN: "Resumen", TIPO_INFORME: "Informe", TIPO_MAPA: "Mapa mental", TIPO_NOTA: "Nota",
}

# Límites del mapa mental (RF-11.122): tres niveles bajo el tema central. Los otros dos evitan un árbol ilegible.
MAX_NIVELES_MAPA = 3
MAX_RAMAS_POR_NODO = 8
MAX_NODOS_MAPA = 60
LARGO_MAXIMO_TITULO_NODO = 120

# Costa Rica no tiene horario de verano: UTC-6 todo el año.
_DESFASE_COSTA_RICA = timedelta(hours=-6)


@dataclass(frozen=True)
class Trozo:
    """Un fragmento de una fuente, con el nombre con que se muestra."""
    fuente: str
    texto: str


@dataclass
class Parte:
    """Un tramo del contenido de las fuentes que cabe en una llamada al motor."""
    texto: str
    fuentes: List[str] = field(default_factory=list)


def _encabezado(fuente: str) -> str:
    return f'### Fuente: "{fuente}"\n'


def _bloque(encabezado: str, texto: str) -> str:
    return encabezado + texto + "\n\n"


def partir(trozos: Sequence[Trozo], maximo_tokens: int, cfg: ConfiguracionContexto = CONFIGURACION) -> List[Parte]:
    """Reparte los trozos, en orden, en partes de a lo sumo `maximo_tokens` (RF-11.126).

    Cada fuente empieza con su encabezado; si una fuente se corta entre dos partes, su encabezado se repite en la siguiente para
    que el modelo sepa de dónde viene cada tramo. Los trozos vacíos se ignoran, y uno que por sí solo no cabe se recorta (los
    fragmentos miden como máximo `fragmento_tamano_maximo`, así que no debería ocurrir).
    """
    partes: List[Parte] = []
    bloques: List[str] = []
    fuentes: List[str] = []
    usados = 0
    ultima: Optional[str] = None

    def cerrar() -> None:
        nonlocal bloques, fuentes, usados, ultima
        if bloques:
            partes.append(Parte(texto="".join(bloques), fuentes=fuentes))
        bloques, fuentes, usados, ultima = [], [], 0, None

    for trozo in trozos:
        texto = trozo.texto.strip()
        if not texto:
            continue
        encabezado = _encabezado(trozo.fuente) if trozo.fuente != ultima else ""
        costo = tokens(_bloque(encabezado, texto), cfg)
        if bloques and usados + costo > maximo_tokens:
            cerrar()
            encabezado = _encabezado(trozo.fuente)
            costo = tokens(_bloque(encabezado, texto), cfg)
        if costo > maximo_tokens:
            permitido = max(1, int(maximo_tokens * cfg.caracteres_por_token) - len(encabezado) - 2)
            texto = texto[:permitido]
            costo = tokens(_bloque(encabezado, texto), cfg)
        bloques.append(_bloque(encabezado, texto))
        usados += costo
        ultima = trozo.fuente
        if trozo.fuente not in fuentes:
            fuentes.append(trozo.fuente)
    cerrar()
    return partes


def agrupar(notas: Sequence[str], maximo_tokens: int, cfg: ConfiguracionContexto = CONFIGURACION) -> List[List[str]]:
    """Junta las notas, en orden, en grupos que caben en `maximo_tokens` al unirlas con una línea en blanco (paso de unión,
    RF-11.126). Una nota que por sí sola no cabe va en su propio grupo."""
    grupos: List[List[str]] = []
    actual: List[str] = []
    for nota in notas:
        candidato = actual + [nota]
        if actual and tokens("\n\n".join(candidato), cfg) > maximo_tokens:
            grupos.append(actual)
            actual = [nota]
        else:
            actual = candidato
    if actual:
        grupos.append(actual)
    return grupos


def citas_validas(texto: str, nombres: Sequence[str]) -> bool:
    """Si `texto` nombra al menos una de las fuentes de la selección (RF-12.120), con o sin extensión y sin distinguir
    mayúsculas. Se comprueba sobre los nombres citados, no sobre lo que dice el modelo."""
    leido = (texto or "").casefold()
    if not leido.strip():
        return False
    for nombre in nombres:
        completo = nombre.casefold()
        base = completo.rsplit(".", 1)[0] if "." in completo[1:] else completo
        if completo in leido or (len(base) >= 3 and base in leido):
            return True
    return False


def asegurar_fuentes(texto: str, nombres: Sequence[str]) -> str:
    """Devuelve `texto` con la sección de fuentes garantizada (RF-12.120): si ya nombra alguna fuente de la selección, tal cual; si
    no, le agrega al final las fuentes de la selección. Con texto de imágenes mal reconocido el modelo a veces no cita ninguna, y
    descartar el resultado por eso dejaba al usuario sin Informe; la lista siempre es de la selección, nunca inventada."""
    if citas_validas(texto, nombres):
        return texto
    fuentes = ", ".join(f"[{nombre}]" for nombre in nombres)
    return f"{texto}\n\n**Fuentes consultadas:** {fuentes}"


def _limpio(valor) -> str:
    if not isinstance(valor, str):
        return ""
    return re.sub(r"\s+", " ", valor).strip()[:LARGO_MAXIMO_TITULO_NODO]


def _ramas(lista, nivel: int, contador: List[int]) -> List[dict]:
    if not isinstance(lista, list) or nivel > MAX_NIVELES_MAPA:
        return []
    ramas = []
    for rama in lista[:MAX_RAMAS_POR_NODO]:
        if contador[0] >= MAX_NODOS_MAPA:
            break
        if isinstance(rama, str):
            rama = {"titulo": rama, "ramas": []}
        if not isinstance(rama, dict):
            continue
        titulo = _limpio(rama.get("titulo"))
        if not titulo:
            continue
        contador[0] += 1
        ramas.append({"titulo": titulo, "ramas": _ramas(rama.get("ramas"), nivel + 1, contador)})
    return ramas


def analizar_mapa(salida: str) -> Optional[dict]:
    """El mapa mental que describe la salida del modelo, normalizado y podado a los límites, o None si no tiene la estructura
    exigida (RF-11.125): un tema central y al menos una rama. Acepta el JSON rodeado de texto o de cercas de código."""
    if not salida or not salida.strip():
        return None
    inicio, fin = salida.find("{"), salida.rfind("}")
    if inicio < 0 or fin <= inicio:
        return None
    try:
        crudo = json.loads(salida[inicio:fin + 1])
    except ValueError:
        return None
    if not isinstance(crudo, dict):
        return None
    titulo = _limpio(crudo.get("titulo"))
    if not titulo:
        return None
    ramas = _ramas(crudo.get("ramas"), 1, [1])
    if not ramas:
        return None
    return {"titulo": titulo, "ramas": ramas}


def texto_de_mapa(mapa: dict) -> str:
    """El mapa como lista de ideas anidada, para copiarlo (RF-14.122): el tema central y, debajo, una viñeta por rama."""
    lineas = [mapa["titulo"]]

    def recorrer(ramas: List[dict], nivel: int) -> None:
        for rama in ramas:
            lineas.append("  " * nivel + "- " + rama["titulo"])
            recorrer(rama.get("ramas", []), nivel + 1)

    recorrer(mapa.get("ramas", []), 0)
    return "\n".join(lineas)


def titulo_por_omision(tipo: str, ahora_utc: datetime) -> str:
    """«<Tipo> · dd/mm/aaaa hh:mm», con la hora de Costa Rica (RF-14.120)."""
    local = ahora_utc + _DESFASE_COSTA_RICA
    return f"{ETIQUETAS[tipo]} · {local:%d/%m/%Y %H:%M}"
