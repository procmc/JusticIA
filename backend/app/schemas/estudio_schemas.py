"""Esquemas del Estudio del notebook (spec 010): generar, listar, abrir, guardar notas y quitar resultados.

Los campos van en español y en snake_case (convención de la API). El contenido de un resultado depende de su tipo: texto
Markdown (resumen e informe), árbol {"titulo", "ramas"} (mapa mental) o {"pregunta", "respuesta"} (nota).
"""
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, StrictInt


class FuenteDeResultado(BaseModel):
    id: Optional[int] = None  # null en una nota: las citas del chat solo traen el nombre
    nombre: str


class ResultadoResumen(BaseModel):
    id: int
    tipo: Literal["resumen", "informe", "mapa_mental", "nota"]
    titulo: str
    fecha_creacion: str  # ISO 8601 en UTC, con «Z»
    fuentes: List[FuenteDeResultado]
    fuentes_faltantes: bool  # alguna fuente con que se generó ya no está en el notebook (RF-14.123)


class ResultadoDetalle(ResultadoResumen):
    contenido: Any


class GenerarRequest(BaseModel):
    tipo: Literal["resumen", "informe", "mapa_mental"]
    # Fuentes marcadas (RF-11.120): ausente = todas las Procesado. StrictInt: "5" o 5.5 no valen, como en el chat (RF-11.105).
    documentos: Optional[List[StrictInt]] = None


class NotaCrearRequest(BaseModel):
    pregunta: str = Field(..., max_length=4000)
    respuesta: str = Field(..., max_length=30000)
    fuentes: List[str] = Field(default_factory=list, max_length=50)


class MensajeResultado(BaseModel):
    mensaje: str
    id: int
