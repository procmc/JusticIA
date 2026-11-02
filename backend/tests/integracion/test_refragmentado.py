"""Prueba de integración de T2 (spec 007, RF-08.60): un documento `PRUEBA` deja en Qdrant fragmentos de a lo sumo
1.500 caracteres, con su tema, su archivo y sus páginas. Usa la colección `servia_pruebas` y el modelo de embeddings real.
"""
import asyncio

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
