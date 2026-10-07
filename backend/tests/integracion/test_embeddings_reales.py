"""Pruebas de T5 (spec 002, RA-02.6): el modelo de embeddings real de la integración.

La fixture `embeddings_reales` carga el modelo una sola vez por sesión y solo cuando una prueba la pide
(plan, decisión 6). Que no se cargue cuando nadie la pide lo comprueba `tests/infraestructura/`.
"""
import math

DIMENSION = 1024  # multilingual-e5-large


def test_los_embeddings_reales_devuelven_vectores_de_1024_dimensiones(embeddings_reales):
    """RA-02.6: el modelo real (no el falso de las unitarias) vectoriza consultas y documentos en 1024 dimensiones."""
    consulta = embeddings_reales.embed_query("PRUEBA consulta inventada sobre un tema ficticio")
    documentos = embeddings_reales.embed_documents(["PRUEBA primer fragmento inventado", "PRUEBA segundo fragmento inventado"])

    assert len(consulta) == DIMENSION
    assert len(documentos) == 2 and all(len(vector) == DIMENSION for vector in documentos)
    assert all(math.isfinite(valor) for valor in consulta)


def test_los_embeddings_reales_aplican_el_prefijo_e5_segun_sea_consulta_o_documento(embeddings_reales):
    """CLAUDE.md (LLM y RAG): E5 necesita `query: ` o `passage: `; el mismo texto da vectores distintos según el uso."""
    texto = "PRUEBA texto inventado para comparar el prefijo"
    como_consulta = embeddings_reales.embed_query(texto)
    como_documento = embeddings_reales.embed_documents([texto])[0]

    assert como_consulta != como_documento
    producto = sum(a * b for a, b in zip(como_consulta, como_documento))
    assert 0.5 < producto < 1.0  # se parecen (mismo texto), pero no son idénticos
