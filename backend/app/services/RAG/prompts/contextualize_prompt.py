"""
Instrucción de reformulación (spec 007, RF-11.66; plan §6.4).

Texto único para los tres chats: reescribe la última pregunta como una consulta de búsqueda autónoma, con solo los
dos últimos mensajes. Solo sirve para buscar; la respuesta recibe la pregunta del usuario.

Ver también:
    * app.services.RAG.general_chains: la usa en `CadenaArmada`
    * app.services.RAG.presupuesto_contexto: `mensajes_para_reformular`
"""

INSTRUCCION_REFORMULACION = """Reescribe la última pregunta del usuario como una consulta de búsqueda autónoma, en español, para recuperar fragmentos de documentos.
- Usa los mensajes previos solo para resolver referencias como «el primero», «ese documento» o «lo anterior»; reemplázalas por el nombre del archivo, el tema o el asunto concreto.
- Si la pregunta no depende de los mensajes previos o cambia de asunto, devuélvela casi igual.
- Conserva exactos los identificadores, números, siglas y nombres de archivo. Puedes añadir la forma completa de una sigla o uno o dos sinónimos clave.
- Si el mensaje incluye un documento largo (una plantilla) seguido de una solicitud, reescribe solo la solicitud.
- No respondas la pregunta ni añadas explicaciones: devuelve solo la consulta, en una línea."""
