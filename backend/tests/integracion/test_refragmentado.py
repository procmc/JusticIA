"""Pruebas de integración de la spec 007.

T2 (RF-08.60): un documento `PRUEBA` deja en Qdrant fragmentos de a lo sumo 1.500 caracteres, con su tema, su archivo y
sus páginas. T10 (RF-08.63, RN-01.60): el procedimiento de re-fragmentado vuelve a fragmentar desde el archivo guardado
solo los documentos Procesado de los temas indicados. Usan la base y la colección `servia_pruebas` y el modelo de
embeddings real; los archivos van a una carpeta temporal.
"""
import asyncio
import dataclasses

import pytest
from qdrant_client.models import FieldCondition, Filter, MatchValue

from tests.soporte.nombres import NOMBRE_PRUEBAS, PREFIJO_DATOS


def _crear_tema_con_documento(tema_numero, nombre_archivo):
    from app.db.database import SessionLocal
    from app.db.models import T_Documento, T_Estado_procesamiento, T_Expediente

    with SessionLocal() as db:
        procesado = db.query(T_Estado_procesamiento).filter(T_Estado_procesamiento.CT_Nombre_estado == "Procesado").one()
        tema = T_Expediente(CT_Num_expediente=tema_numero)
        documento = T_Documento(CT_Nombre_archivo=nombre_archivo, CT_Tipo_archivo="txt", CN_Id_estado=procesado.CN_Id_estado)
        tema.documentos.append(documento)
        db.add(tema)
        db.commit()
        return tema.CN_Id_expediente, documento.CN_Id_documento


def test_documento_prueba_fragmentos_de_1500(embeddings_reales, destino_de_pruebas, registro_de_datos):
    """RF-08.60 · un texto inventado de ~7.000 caracteres se guarda en fragmentos de ≤ 1.500 caracteres, cada uno con
    tema, archivo y página de inicio y de fin (pagina_fin ≥ pagina_inicio ≥ 1)."""
    from app.vectorstore.storage import store_in_vectorstore

    tema_numero = f"{PREFIJO_DATOS}-TEMA-FRAGMENTOS"
    nombre_archivo = f"{PREFIJO_DATOS}_fragmentos.txt"
    id_tema, id_documento = _crear_tema_con_documento(tema_numero, nombre_archivo)
    texto = f"{PREFIJO_DATOS}: " + " ".join(f"oración inventada número {i:04d} sobre el archivo ficticio." for i in range(140))
    assert len(texto) > 5000

    ids, cantidad = asyncio.run(store_in_vectorstore(
        texto=texto,
        metadatos={"nombre_archivo": nombre_archivo, "ruta_archivo": f"{PREFIJO_DATOS}/{nombre_archivo}", "tipo": "TXT"},
        CT_Num_expediente=tema_numero,
        id_expediente=id_tema,
        id_documento=id_documento,
    ))
    for identificador in ids:
        registro_de_datos.registrar_punto(identificador)

    puntos, _ = destino_de_pruebas.qdrant.scroll(
        NOMBRE_PRUEBAS,
        scroll_filter=Filter(must=[FieldCondition(key="metadata.numero_expediente", match=MatchValue(value=tema_numero))]),
        with_payload=True,
        limit=100,
    )
    assert cantidad == len(ids) == len(puntos) >= 4
    for punto in puntos:
        metadatos = punto.payload["metadata"]
        assert len(punto.payload["page_content"]) <= 1500
        assert metadatos["nombre_archivo"] == nombre_archivo
        assert metadatos["id_documento"] == id_documento
        assert 1 <= metadatos["pagina_inicio"] <= metadatos["pagina_fin"]


# --- T10 · RF-08.63: re-fragmentado ----------------------------------------------------------------------------------

CONSERVADOS = ("id_documento", "id_expediente", "numero_expediente", "nombre_archivo", "fecha_carga", "fecha_expediente_creacion")


def _texto(marca):
    return f"{PREFIJO_DATOS} {marca}: " + " ".join(
        f"oración inventada número {i:04d} sobre el archivo ficticio {marca}." for i in range(130))


def _tema(numero):
    from app.db.database import SessionLocal
    from app.db.models import T_Expediente

    with SessionLocal() as db:
        tema = T_Expediente(CT_Num_expediente=numero)
        db.add(tema)
        db.commit()
        return tema.CN_Id_expediente


def _documento(tema_numero, nombre, estado="Procesado"):
    from app.db.database import SessionLocal
    from app.db.models import T_Documento, T_Estado_procesamiento, T_Expediente

    with SessionLocal() as db:
        id_estado = db.query(T_Estado_procesamiento).filter(T_Estado_procesamiento.CT_Nombre_estado == estado).one().CN_Id_estado
        tema = db.query(T_Expediente).filter(T_Expediente.CT_Num_expediente == tema_numero).one()
        documento = T_Documento(CT_Nombre_archivo=nombre, CT_Tipo_archivo="txt", CN_Id_estado=id_estado)
        tema.documentos.append(documento)
        db.commit()
        return tema.CN_Id_expediente, documento.CN_Id_documento


def _filas(tema_numero):
    """Las filas del tema: (id del documento, nombre, estado), para comprobar que el procedimiento no las toca."""
    from app.db.database import SessionLocal
    from app.db.models import T_Expediente

    with SessionLocal() as db:
        tema = db.query(T_Expediente).filter(T_Expediente.CT_Num_expediente == tema_numero).one()
        return sorted((d.CN_Id_documento, d.CT_Nombre_archivo, d.estado_procesamiento.CT_Nombre_estado) for d in tema.documentos)


def _escribir(carpeta, tema, nombre, texto):
    destino = carpeta / "uploads" / tema
    destino.mkdir(parents=True, exist_ok=True)
    (destino / nombre).write_text(texto, encoding="utf-8")


def _guardar_antiguos(monkeypatch, texto, tema, id_tema, id_documento, nombre, veces=1):
    """Deja en Qdrant los fragmentos «de antes» (7.000 caracteres, como la fragmentación anterior) de un documento.
    Con `veces` > 1 repite la inserción: los duplicados de una corrida que no pudo borrar."""
    from app.config import contexto_config
    from app.vectorstore import storage

    antigua = dataclasses.replace(contexto_config.CONFIGURACION, fragmento_tamano_maximo=7000, fragmento_solapamiento=500)
    with monkeypatch.context() as parche:
        parche.setattr(storage, "CONFIGURACION", antigua, raising=False)
        for _ in range(veces):
            asyncio.run(storage.store_in_vectorstore(
                texto=texto,
                metadatos={"nombre_archivo": nombre, "ruta_archivo": f"{PREFIJO_DATOS}/{tema}/{nombre}", "tipo": "TXT"},
                CT_Num_expediente=tema,
                id_expediente=id_tema,
                id_documento=id_documento,
            ))


def _puntos(destino, id_documento):
    puntos, _ = destino.qdrant.scroll(
        NOMBRE_PRUEBAS,
        scroll_filter=Filter(must=[FieldCondition(key="metadata.id_documento", match=MatchValue(value=id_documento))]),
        with_payload=True,
        limit=500,
    )
    return puntos


def _ids(puntos):
    return {str(p.id) for p in puntos}


def _montar(monkeypatch, carpeta, destino, tema, nombre, marca, estado="Procesado", archivo=True, veces=1, tema_existente=False):
    """Un documento con su fila, su archivo guardado y sus fragmentos «de antes»; devuelve (id_tema, id_documento, texto)."""
    texto = _texto(marca)
    if not tema_existente:
        _tema(tema)
    id_tema, id_documento = _documento(tema, nombre, estado)
    if archivo:
        _escribir(carpeta, tema, nombre, texto)
    _guardar_antiguos(monkeypatch, texto, tema, id_tema, id_documento, nombre, veces)
    assert len(_puntos(destino, id_documento)) >= veces
    return id_tema, id_documento, texto


@pytest.fixture
def refragmentar(embeddings_reales, destino_de_pruebas, carpeta_archivos):
    from app.services.ingesta import refragmentado

    def _correr(temas, simular=False):
        return asyncio.run(refragmentado.refragmentar(temas, simular=simular))
    return _correr


def test_tema_indicado_queda_en_fragmentos_de_1500_con_las_mismas_filas_y_metadatos(
        monkeypatch, refragmentar, carpeta_archivos, destino_de_pruebas):
    """RF-08.63 · el documento Procesado del tema indicado queda con fragmentos de ≤ 1.500 caracteres, reemplaza a los
    anteriores y conserva su fila, su estado y los metadatos (documento, tema, archivo, fechas y ruta originales)."""
    tema, nombre = f"{PREFIJO_DATOS}-REFRAG-A", f"{PREFIJO_DATOS}_a.txt"
    _, id_documento, _ = _montar(monkeypatch, carpeta_archivos, destino_de_pruebas, tema, nombre, "a")
    antes = _puntos(destino_de_pruebas, id_documento)
    filas = _filas(tema)

    informe = refragmentar([tema])

    despues = sorted(_puntos(destino_de_pruebas, id_documento), key=lambda p: p.payload["metadata"]["indice_chunk"])
    assert informe.documentos == 1 and informe.fallidos == []
    assert informe.fragmentos_actuales == len(antes) and informe.fragmentos_nuevos == len(despues) >= 4
    assert _ids(antes).isdisjoint(_ids(despues))
    assert all(len(p.payload["page_content"]) <= 1500 for p in despues)
    assert [p.payload["metadata"]["indice_chunk"] for p in despues] == list(range(len(despues)))
    for punto in despues:
        for clave in CONSERVADOS:
            assert punto.payload["metadata"][clave] == antes[0].payload["metadata"][clave], clave
        assert punto.payload["metadata"]["meta"]["ruta_archivo"] == antes[0].payload["metadata"]["meta"]["ruta_archivo"]
    assert _filas(tema) == filas


def test_otro_tema_y_otro_estado_quedan_intactos(monkeypatch, refragmentar, carpeta_archivos, destino_de_pruebas):
    """RF-08.63 · un tema que no se indicó, y un documento en Error del tema indicado, conservan los mismos fragmentos."""
    tema, otro = f"{PREFIJO_DATOS}-REFRAG-B", f"{PREFIJO_DATOS}-REFRAG-C"
    _, id_procesado, _ = _montar(monkeypatch, carpeta_archivos, destino_de_pruebas, tema, f"{PREFIJO_DATOS}_b1.txt", "b1")
    _, id_error, _ = _montar(monkeypatch, carpeta_archivos, destino_de_pruebas, tema, f"{PREFIJO_DATOS}_b2.txt", "b2",
                             estado="Error", tema_existente=True)
    _, id_ajeno, _ = _montar(monkeypatch, carpeta_archivos, destino_de_pruebas, otro, f"{PREFIJO_DATOS}_c.txt", "c")
    ajeno, error = _puntos(destino_de_pruebas, id_ajeno), _puntos(destino_de_pruebas, id_error)

    informe = refragmentar([tema])

    assert informe.documentos == 1
    assert _ids(_puntos(destino_de_pruebas, id_ajeno)) == _ids(ajeno)
    assert _ids(_puntos(destino_de_pruebas, id_error)) == _ids(error)
    assert len(_puntos(destino_de_pruebas, id_procesado)) >= 4


def test_archivo_faltante_conserva_los_anteriores_y_sigue(monkeypatch, refragmentar, carpeta_archivos, destino_de_pruebas):
    """RF-08.63 · si falta el archivo guardado, el documento conserva sus fragmentos anteriores, se informa y el
    siguiente documento del tema se procesa igual."""
    tema = f"{PREFIJO_DATOS}-REFRAG-D"
    _, id_sin_archivo, _ = _montar(monkeypatch, carpeta_archivos, destino_de_pruebas, tema, f"{PREFIJO_DATOS}_d1.txt", "d1", archivo=False)
    _, id_bueno, _ = _montar(monkeypatch, carpeta_archivos, destino_de_pruebas, tema, f"{PREFIJO_DATOS}_d2.txt", "d2", tema_existente=True)
    antes, bueno_antes = _puntos(destino_de_pruebas, id_sin_archivo), _puntos(destino_de_pruebas, id_bueno)

    informe = refragmentar([tema])

    assert informe.documentos == 2
    assert [f.id_documento for f in informe.fallidos] == [id_sin_archivo]
    assert informe.fallidos[0].causa
    assert _ids(_puntos(destino_de_pruebas, id_sin_archivo)) == _ids(antes)
    nuevos = _puntos(destino_de_pruebas, id_bueno)
    assert len(nuevos) >= 4 and _ids(nuevos).isdisjoint(_ids(bueno_antes))


def test_insercion_fallida_conserva_los_anteriores_sin_restos(monkeypatch, refragmentar, carpeta_archivos, destino_de_pruebas):
    """RF-08.63 · si la inserción falla después de haber guardado fragmentos nuevos, el documento queda solo con los
    anteriores (los nuevos se borran) y se informa."""
    from app.services.ingesta import refragmentado
    from app.vectorstore import storage

    tema = f"{PREFIJO_DATOS}-REFRAG-E"
    _, id_documento, _ = _montar(monkeypatch, carpeta_archivos, destino_de_pruebas, tema, f"{PREFIJO_DATOS}_e.txt", "e")
    antes = _puntos(destino_de_pruebas, id_documento)
    original = storage.store_in_vectorstore

    async def _inserta_y_falla(*argumentos, **opciones):
        await original(*argumentos, **opciones)
        raise RuntimeError("falla simulada tras insertar")

    monkeypatch.setattr(refragmentado, "store_in_vectorstore", _inserta_y_falla)

    informe = refragmentar([tema])

    assert [f.id_documento for f in informe.fallidos] == [id_documento]
    assert "falla simulada" in informe.fallidos[0].causa
    assert _ids(_puntos(destino_de_pruebas, id_documento)) == _ids(antes)


def test_dos_corridas_dejan_lo_mismo(monkeypatch, refragmentar, carpeta_archivos, destino_de_pruebas):
    """RF-08.63 · idempotente: la segunda corrida deja el mismo número de fragmentos, con el mismo texto y sin duplicados."""
    tema = f"{PREFIJO_DATOS}-REFRAG-F"
    _, id_documento, _ = _montar(monkeypatch, carpeta_archivos, destino_de_pruebas, tema, f"{PREFIJO_DATOS}_f.txt", "f")

    primera = refragmentar([tema])
    textos_1 = sorted(p.payload["page_content"] for p in _puntos(destino_de_pruebas, id_documento))
    segunda = refragmentar([tema])
    puntos = _puntos(destino_de_pruebas, id_documento)

    assert primera.fragmentos_nuevos == segunda.fragmentos_nuevos == len(puntos) >= 4
    assert segunda.fragmentos_actuales == primera.fragmentos_nuevos
    assert sorted(p.payload["page_content"] for p in puntos) == textos_1
    assert len({p.payload["metadata"]["indice_chunk"] for p in puntos}) == len(puntos)


def test_simulacion_informa_y_no_cambia_nada(monkeypatch, refragmentar, carpeta_archivos, destino_de_pruebas):
    """RF-08.63 · la simulación informa cuántos documentos y fragmentos tocaría, sin tocar Qdrant ni las filas."""
    tema = f"{PREFIJO_DATOS}-REFRAG-G"
    _, id_documento, _ = _montar(monkeypatch, carpeta_archivos, destino_de_pruebas, tema, f"{PREFIJO_DATOS}_g.txt", "g")
    antes = _puntos(destino_de_pruebas, id_documento)
    filas = _filas(tema)

    informe = refragmentar([tema], simular=True)

    assert informe.simulacion is True
    assert informe.documentos == 1 and informe.fragmentos_actuales == len(antes)
    assert informe.fragmentos_nuevos == 0 and informe.fallidos == []
    despues = _puntos(destino_de_pruebas, id_documento)
    assert {str(p.id): p.payload for p in despues} == {str(p.id): p.payload for p in antes}
    assert _filas(tema) == filas


def test_duplicados_de_una_corrida_fallida_se_limpian(monkeypatch, refragmentar, carpeta_archivos, destino_de_pruebas):
    """RF-08.63 · si el documento quedó con fragmentos repetidos (una corrida que no pudo borrar), la siguiente deja
    una sola serie: los repetidos desaparecen."""
    tema = f"{PREFIJO_DATOS}-REFRAG-H"
    _, id_documento, _ = _montar(monkeypatch, carpeta_archivos, destino_de_pruebas, tema, f"{PREFIJO_DATOS}_h.txt", "h", veces=3)
    antes = _puntos(destino_de_pruebas, id_documento)
    assert len({p.payload["metadata"]["indice_chunk"] for p in antes}) < len(antes)

    informe = refragmentar([tema])

    despues = _puntos(destino_de_pruebas, id_documento)
    assert informe.fragmentos_actuales == len(antes)
    assert _ids(antes).isdisjoint(_ids(despues))
    assert sorted(p.payload["metadata"]["indice_chunk"] for p in despues) == list(range(len(despues)))
    assert len(despues) == informe.fragmentos_nuevos >= 4
