"""
Paso de los documentos recuperados a fragmentos del armado (spec 007, RF-12.60).

Cada documento de LangChain que devuelve el recuperador (general, por tema o notebook) se convierte en un
`Fragmento` con su archivo, tema, ruta de descarga y páginas. El encabezado que ve el motor lo escribe
`presupuesto_contexto.encabezado` (sin encabezados de grupo por tema).

Ver también:
    * app.services.RAG.presupuesto_contexto: `Fragmento` y `encabezado`
    * app.services.RAG.general_chains: quien lo usa
"""
from langchain_core.documents import Document

from .presupuesto_contexto import Fragmento

# El motor nunca ve la imagen, solo el texto que reconoció el servicio de HTR: el encabezado lo avisa.
EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")


def a_fragmento(doc: Document) -> Fragmento:
    """Convierte un documento recuperado en un `Fragmento` (el nombre del archivo sale de la ruta si la hay)."""
    metadata = doc.metadata or {}
    ruta = (metadata.get("ruta_archivo") or "").strip()
    if ruta:
        archivo = ruta.split("/")[-1]
    else:
        archivo = metadata.get("nombre_archivo") or metadata.get("archivo") or "N/A"
    return Fragmento(
        texto=doc.page_content,
        archivo=archivo,
        tema=str(metadata.get("expediente_numero") or metadata.get("numero_expediente") or "N/A"),
        ruta=ruta,
        pagina_inicio=metadata.get("pagina_inicio") or None,
        pagina_fin=metadata.get("pagina_fin") or None,
        es_imagen=archivo.lower().endswith(EXTENSIONES_IMAGEN),
    )
