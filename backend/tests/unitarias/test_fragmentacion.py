"""Pruebas de T2 (spec 007, RF-08.60 y RF-08.61): fragmentación configurable y páginas reales.

`store_in_vectorstore` divide el texto con el tamaño y el solapamiento de `contexto_config.CONFIGURACION`
(RF-08.60) y calcula la página de inicio y de fin de cada fragmento con su posición real en el texto original
(RF-08.61). El almacén vectorial se simula: solo se inspeccionan los documentos que recibiría.
"""
import asyncio
import dataclasses

from app.config import contexto_config
from app.vectorstore import storage

CARACTERES_POR_PAGINA = 2500


class _AlmacenFalso:
    def __init__(self):
        self.documentos = []

    async def add_documents(self, documentos):
        self.documentos.extend(documentos)
        return [str(i) for i in range(len(documentos))]


def _guardar(monkeypatch, texto, tamano=None, solapamiento=None):
    """Guarda `texto` con un almacén falso y, si se pide, otra configuración; devuelve los documentos recibidos."""
    almacen = _AlmacenFalso()
    monkeypatch.setattr(storage, "get_vectorstore_backend", lambda: almacen)
    if tamano is not None:
        configuracion = dataclasses.replace(
            contexto_config.CONFIGURACION, fragmento_tamano_maximo=tamano, fragmento_solapamiento=solapamiento
        )
        monkeypatch.setattr(storage, "CONFIGURACION", configuracion, raising=False)
    asyncio.run(storage.store_in_vectorstore(
        texto=texto,
        metadatos={"nombre_archivo": "PRUEBA_fragmentos.txt", "ruta_archivo": "PRUEBA/PRUEBA_fragmentos.txt"},
        CT_Num_expediente="PRUEBA-FRAG",
        id_expediente=1,
        id_documento=1,
    ))
    return almacen.documentos


def test_tamano_y_solapamiento_configurados(monkeypatch):
    """RF-08.60 (regresión) · con otro tamaño configurado, ningún fragmento lo supera y dos consecutivos
    comparten el solapamiento. Hoy falla: el tamaño está fijo en 7.000 y el solapamiento en 500."""
    texto = " ".join(f"palabra{i:04d}" for i in range(700))  # ~7.700 caracteres, con espacios para cortar

    documentos = _guardar(monkeypatch, texto, tamano=1000, solapamiento=150)

    assert len(documentos) > 1
    assert all(len(d.page_content) <= 1000 for d in documentos)
    for anterior, siguiente in zip(documentos, documentos[1:]):
        compartido = anterior.page_content[-150:]
        # El solapamiento cae entre 1 y 150 caracteres (se corta en espacios): el final del anterior abre el siguiente.
        cola = next((anterior.page_content[-n:] for n in range(150, 0, -1)
                     if siguiente.page_content.startswith(anterior.page_content[-n:])), "")
        assert len(cola) >= 100, (compartido, siguiente.page_content[:150])


def test_por_omision_usa_los_valores_de_la_configuracion(monkeypatch):
    """RF-08.60 · sin configuración propia, el tamaño máximo es el de `CONFIGURACION` (1.500 por omisión)."""
    texto = " ".join(f"palabra{i:04d}" for i in range(700))

    documentos = _guardar(monkeypatch, texto)

    maximo = contexto_config.CONFIGURACION.fragmento_tamano_maximo
    assert len(documentos) > 1
    assert max(len(d.page_content) for d in documentos) <= maximo


def test_paginas_por_posicion_real(monkeypatch):
    """RF-08.61 · siete párrafos de 1.000 caracteres separados por «\\n\\n» (cada uno empieza en 1.002·k): la página de
    inicio y de fin de cada fragmento sale de la posición real de su primer y último carácter (2.500 por página).
    A mano: inicios 0, 1002, 2004, 3006, 4008, 5010, 6012 → páginas 1, 1, 1, 2, 2, 3, 3; último carácter
    999, 2001, 3003, 4005, 5007, 6009, 7011 → páginas 1, 1, 2, 2, 3, 3, 3."""
    texto = "\n\n".join(chr(97 + k) * 1000 for k in range(7))

    documentos = _guardar(monkeypatch, texto, tamano=1500, solapamiento=0)

    assert len(documentos) == 7
    inicio = [d.metadata["pagina_inicio"] for d in documentos]
    fin = [d.metadata["pagina_fin"] for d in documentos]
    assert inicio == [1, 1, 1, 2, 2, 3, 3]
    assert fin == [1, 1, 2, 2, 3, 3, 3]
    assert documentos[2].metadata["meta"]["estimated_pages"] == "1-2"
