"""Pruebas de T2 (spec 007, RF-08.60 y RF-08.61): fragmentación configurable y páginas reales.

`store_in_vectorstore` divide el texto con el tamaño y el solapamiento de `contexto_config.CONFIGURACION`
(RF-08.60) y calcula la página de inicio y de fin de cada fragmento con su posición real en el texto original
(RF-08.61). El almacén vectorial se simula: solo se inspeccionan los documentos que recibiría.
"""
import asyncio
import dataclasses

import pytest

from app.config import contexto_config
from app.services.ingesta import refragmentado
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


class _AlmacenConIds:
    """Almacén falso que, a diferencia de `_AlmacenFalso`, acepta los identificadores propios de los puntos."""

    def __init__(self):
        self.documentos = []
        self.ids = "no se pasó"

    async def add_documents(self, documentos, ids=None):
        self.documentos.extend(documentos)
        self.ids = ids
        return list(ids) if ids else [str(i) for i in range(len(documentos))]


def test_ids_propios_y_fechas_originales(monkeypatch):
    """RF-08.63 (T10) · con `ids_propios`, el identificador de cada punto es su `id_chunk`; con las fechas originales,
    `fecha_carga` y `fecha_expediente_creacion` las conservan y `fecha_vectorizacion` sigue siendo la de ahora."""
    almacen = _AlmacenConIds()
    monkeypatch.setattr(storage, "get_vectorstore_backend", lambda: almacen)
    texto = " ".join(f"palabra{i:04d}" for i in range(700))

    ids, _ = asyncio.run(storage.store_in_vectorstore(
        texto=texto,
        metadatos={"nombre_archivo": "PRUEBA_ids.txt", "ruta_archivo": "PRUEBA/PRUEBA_ids.txt"},
        CT_Num_expediente="PRUEBA-IDS",
        id_expediente=1,
        id_documento=1,
        ids_propios=True,
        fecha_carga=111,
        fecha_expediente_creacion=222,
    ))

    assert len(almacen.documentos) > 1
    assert almacen.ids == [d.metadata["id_chunk"] for d in almacen.documentos] == ids
    assert len(set(ids)) == len(ids)
    assert {d.metadata["fecha_carga"] for d in almacen.documentos} == {111}
    assert {d.metadata["fecha_expediente_creacion"] for d in almacen.documentos} == {222}
    assert all(d.metadata["fecha_vectorizacion"] > 222 for d in almacen.documentos)


def test_sin_opciones_se_guarda_como_siempre(monkeypatch):
    """RF-08.63 (T10, protección) · sin `ids_propios` ni fechas, no se pasan identificadores al almacén y las fechas son las de ahora."""
    almacen = _AlmacenConIds()
    monkeypatch.setattr(storage, "get_vectorstore_backend", lambda: almacen)

    asyncio.run(storage.store_in_vectorstore(
        texto=" ".join(f"palabra{i:04d}" for i in range(300)),
        metadatos={"nombre_archivo": "PRUEBA_ids.txt", "ruta_archivo": "PRUEBA/PRUEBA_ids.txt"},
        CT_Num_expediente="PRUEBA-IDS",
        id_expediente=1,
        id_documento=1,
    ))

    assert almacen.ids is None
    assert all(d.metadata["fecha_carga"] > 1_000_000 for d in almacen.documentos)


def test_cli_exige_temas(monkeypatch):
    """RF-08.63 · el procedimiento exige al menos un `--tema`: sin él, o con una opción «todos», termina con error de uso
    y no corre nada; con temas, los pasa tal cual y la simulación se pide con `--simular`."""
    llamadas = []

    async def _falsa(temas, simular=False, confirmar_desarrollo=False):
        llamadas.append((list(temas), simular))
        return refragmentado.Informe(temas=list(temas), simulacion=simular)

    monkeypatch.setattr(refragmentado, "refragmentar", _falsa)

    for argumentos in ([], ["--simular"], ["--todos"], ["--tema"]):
        with pytest.raises(SystemExit) as salida:
            refragmentado.main(argumentos)
        assert salida.value.code == 2, argumentos
    assert llamadas == []

    assert refragmentado.main(["--tema", "PRUEBA-A", "--tema", "PRUEBA-B", "--simular"]) == 0
    assert llamadas == [(["PRUEBA-A", "PRUEBA-B"], True)]


def _entorno(monkeypatch, base, coleccion=None):
    """Hace que el procedimiento vea esa base y esa colección (por omisión, la misma)."""
    monkeypatch.setattr(refragmentado.config, "SQL_SERVER_DATABASE", base)
    monkeypatch.setattr(refragmentado.config, "QDRANT_COLLECTION_NAME", coleccion if coleccion is not None else base)


def test_cli_se_niega_en_desarrollo_sin_confirmar(monkeypatch, capsys):
    """RF-08.63 · seguro: fuera de `servia_pruebas`, la corrida real exige `--confirmar-desarrollo`; sin él (y sin
    `--simular`) el comando se niega con un mensaje en español y no llama a `refragmentar`."""
    llamadas = []

    async def _falsa(temas, simular=False, confirmar_desarrollo=False):
        llamadas.append((list(temas), simular, confirmar_desarrollo))
        return refragmentado.Informe(temas=list(temas), simulacion=simular)

    monkeypatch.setattr(refragmentado, "refragmentar", _falsa)

    for base, coleccion in (("db_ServIA", "justicia_docs"), ("servia_pruebas", "justicia_docs"),
                            ("db_ServIA", "servia_pruebas"), ("servia_pruebas_2", "servia_pruebas_2")):
        _entorno(monkeypatch, base, coleccion)
        with pytest.raises(SystemExit) as salida:
            refragmentado.main(["--tema", "X"])
        assert salida.value.code != 0, (base, coleccion)
        assert "--confirmar-desarrollo" in capsys.readouterr().err
    assert llamadas == []

    _entorno(monkeypatch, "db_ServIA", "justicia_docs")
    assert refragmentado.main(["--tema", "X", "--simular"]) == 0
    assert refragmentado.main(["--tema", "X", "--confirmar-desarrollo"]) == 0
    assert llamadas == [(["X"], True, False), (["X"], False, True)]

    _entorno(monkeypatch, "servia_pruebas")
    assert refragmentado.main(["--tema", "X"]) == 0
    assert llamadas[-1] == (["X"], False, False)


def test_refragmentar_se_niega_en_desarrollo_sin_confirmar(monkeypatch):
    """RF-08.63 · el seguro también vale al llamar a `refragmentar` desde código: fuera de `servia_pruebas` y sin
    simular, falla antes de leer o escribir nada, salvo con `confirmar_desarrollo=True`."""
    accedido = []
    monkeypatch.setattr(refragmentado, "_documentos_de", lambda temas: accedido.append(temas) or [])
    monkeypatch.setattr(refragmentado, "get_vectorstore_backend", lambda: object())
    _entorno(monkeypatch, "db_ServIA", "justicia_docs")

    with pytest.raises(refragmentado.EjecucionNoPermitida) as error:
        asyncio.run(refragmentado.refragmentar(["X"]))
    assert "confirmar_desarrollo" in str(error.value) or "--confirmar-desarrollo" in str(error.value)
    assert accedido == []

    assert asyncio.run(refragmentado.refragmentar(["X"], simular=True)).documentos == 0
    assert asyncio.run(refragmentado.refragmentar(["X"], confirmar_desarrollo=True)).documentos == 0
    _entorno(monkeypatch, "servia_pruebas")
    assert asyncio.run(refragmentado.refragmentar(["X"])).documentos == 0
