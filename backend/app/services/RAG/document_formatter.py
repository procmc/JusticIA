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
    """Convierte un documento recuperado en un `Fragmento`.

    El nombre que ve el modelo (y que cita) es `nombre_archivo`: es el que se actualiza al renombrar una fuente (RF-19.104).
    La ruta conserva el nombre interno, que es el del archivo en disco; solo sirve de respaldo para documentos sin nombre.
    """
    metadata = doc.metadata or {}
    ruta = (metadata.get("ruta_archivo") or "").strip()
    archivo = (metadata.get("nombre_archivo") or metadata.get("archivo") or (ruta.split("/")[-1] if ruta else "") or "N/A")
    return Fragmento(
        texto=doc.page_content,
        archivo=archivo,
        tema=str(metadata.get("expediente_numero") or metadata.get("numero_expediente") or "N/A"),
        ruta=ruta,
        pagina_inicio=metadata.get("pagina_inicio") or None,
        pagina_fin=metadata.get("pagina_fin") or None,
        es_imagen=archivo.lower().endswith(EXTENSIONES_IMAGEN),
    )
