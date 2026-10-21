"""
Servicio de Lógica de Negocio para Notebooks (NotebookServIA).

Colección de documentos genérica, propiedad de un usuario, que se
puede consultar por chat de forma acotada a solo esos documentos —
el equivalente local a un notebook de NotebookLM.

Por debajo reutiliza la misma tubería de ingesta/Qdrant que ya existe
para expedientes (ver T_Notebook.clave_interna): el notebook nunca
aparece como "expediente" en ningún texto visible al usuario ni en los
prompts, solo internamente como clave de agrupación de documentos.

Funciones principales:
    - crear_notebook: Crea un notebook nuevo para un usuario
    - listar_notebooks_usuario: Lista los notebooks de un usuario
    - obtener_notebook_de_usuario: Busca un notebook validando propiedad
    - listar_documentos_de_notebook, obtener_archivo_de_documento, quitar_documento: Los documentos de un notebook propio
      (RF-17.33: las rutas no usan repositorios, Qdrant ni archivos; todo pasa por aquí)
    - clasificar_clave: Dice si un tema es la clave de un notebook propio, de uno no disponible o de ningún notebook
    - obtener_notebook_para_chat: El notebook propio que pide el chat de NotebookServIA, o None si no está disponible
    - ids_documentos_visibles: Qué documentos puede ver un usuario (la regla de aislamiento entre notebooks, RF-17.3)

Example:
    >>> service = NotebookService()
    >>> notebook = await service.crear_notebook(db, "Políticas MICITT", "119120969")
    >>> print(notebook.clave_interna)  # "NB-1"

Ver también:
    * app.repositories.notebook_repository: Acceso a datos
    * app.routes.notebooks: Endpoints REST
    * app.services.RAG.rag_chain_service: Consulta de chat acotada a notebook
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from app.db.models.documento import T_Documento
from app.db.models.notebook import T_Notebook
from app.repositories.documento_repository import DocumentoRepository
from app.repositories.expediente_repository import ExpedienteRepository
from app.repositories.notebook_repository import NotebookRepository
from app.services.bitacora.notebooks_audit_service import MOTIVO_DOCUMENTO_NO_DISPONIBLE, MOTIVO_NOTEBOOK_NO_DISPONIBLE
from app.services.documentos.file_management_service import file_management_service
from app.vectorstore import get_vectorstore_backend

# Un notebook usa como tema su clave `NB-<id>`; la base compara sin distinguir mayúsculas NI el ancho de los caracteres
# (`ＮＢ-5` es `NB-5` para SQL Server), así que el prefijo se lee en su forma de compatibilidad Unicode (NFKC). Solo es una clave
# válida con dígitos ASCII, TAL COMO SE ESCRIBIERON, y sin cero inicial: nada de normalizar con `int()` (aceptaría `+5`, ` 5 ` o
# dígitos Unicode, creando alias de `NB-5`), y un número fuera de rango no puede ser de ningún notebook.
_PREFIJO_DE_CLAVE = "nb-"
_NUMERO_DE_CLAVE = re.compile(r"[1-9][0-9]*", re.ASCII)
_ID_MAXIMO = 2**63 - 1       # un BIGINT de SQL Server
# El identificador que llega al chat del notebook sigue la misma regla, sin recortar espacios: `int()` aceptaría `+5`, ` 5 `, `05`
# y los dígitos Unicode, que serían alias del mismo notebook.
_ID_DE_NOTEBOOK = re.compile(r"[1-9][0-9]*", re.ASCII)

logger = logging.getLogger(__name__)

NO_ES_NOTEBOOK = "no_es_notebook"
PROPIO = "propio"
NO_DISPONIBLE = "no_disponible"


def _en_nfkc(texto: str) -> str:
    return unicodedata.normalize("NFKC", texto).casefold()


def _sin_formato(texto: str) -> str:
    """`texto` sin los caracteres de formato de Unicode (categoría Cf: guion blando U+00AD, ancho cero U+200B-U+200D, U+2060,
    U+FEFF…), que no se ven pero que la base ignora o quita al comparar o guardar (B2, vuelta 2)."""
    return "".join(c for c in texto if unicodedata.category(c) != "Cf")


def forma_de_clave(tema: Optional[str]) -> bool:
    """Indica si `tema` tiene forma de clave de notebook: sin espacios al inicio y al final, en su forma de compatibilidad
    Unicode (NFKC: `ＮＢ－5` se lee `NB-5`) y sin distinguir mayúsculas, empieza por `NB-`. Es solo la forma del texto: no dice
    si el notebook existe ni de quién es."""
    return isinstance(tema, str) and _en_nfkc(tema.strip()).startswith(_PREFIJO_DE_CLAVE)


def _resto_de_clave(tema: str) -> Optional[str]:
    """Lo que sigue al prefijo `NB-` de una forma de clave, TAL COMO SE ESCRIBIÓ (sin normalizarlo), o None si no se encuentra.
    El prefijo se lee en NFKC carácter a carácter, para que `ＮＢ-５` deje `５` y no `5`: el dígito de ancho completo no es un
    dígito ASCII (decisión 11 del plan)."""
    escrito = tema.strip()
    for largo in range(1, min(len(escrito), len(_PREFIJO_DE_CLAVE) * 4) + 1):
        leido = _en_nfkc(escrito[:largo])
        if leido == _PREFIJO_DE_CLAVE:
            return escrito[largo:]
        if len(leido) >= len(_PREFIJO_DE_CLAVE):
            return None
    return None


def id_de_notebook(texto: Optional[str]) -> Optional[int]:
    """El id de notebook que dice `texto` (solo dígitos ASCII, sin signo, espacios ni ceros a la izquierda y dentro del rango de
    la columna), o None si no es un identificador numérico canónico (RF-11.32)."""
    if not isinstance(texto, str) or not _ID_DE_NOTEBOOK.fullmatch(texto) or int(texto) > _ID_MAXIMO:
        return None
    return int(texto)


def _id_de_clave(tema: str) -> Optional[int]:
    """El id de notebook de una clave canónica (`NB-5`, en cualquier combinación de mayúsculas y con espacios alrededor, y con
    el prefijo en ancho completo), o None si el resto no es un número ASCII sin ceros a la izquierda y dentro del rango de la
    columna."""
    resto = _resto_de_clave(tema)
    if resto is None or not _NUMERO_DE_CLAVE.fullmatch(resto) or int(resto) > _ID_MAXIMO:
        return None
    return int(resto)


class RecursoNoDisponible(Exception):
    """Un notebook, documento o conversación que el usuario no puede usar: ajeno, inexistente o pedido con una forma que no es
    la suya. No distingue entre ellos: quien la atiende responde lo mismo (404 uniforme) y deja el intento fallido con `motivo`
    (RNF-07.6, RF-21.32). Su mensaje es solo el motivo: nunca lleva lo pedido."""

    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo


class DocumentoSinProcesar(Exception):
    """El documento del notebook todavía no terminó de procesarse: no se puede previsualizar aún. Lleva la clave del notebook y
    el número del documento para registrar el fallo en la bitácora (RF-21.30); nunca el nombre del archivo."""

    def __init__(self, clave: str, documento_id: int):
        super().__init__("Documento sin procesar")
        self.clave = clave
        self.documento_id = documento_id


class ArchivoNoEncontrado(Exception):
    """El archivo del documento ya no está en disco o su ubicación no es la permitida. Lleva la clave del notebook y el número
    del documento para registrar el fallo en la bitácora (RF-21.30); nunca el nombre del archivo ni la ruta."""

    def __init__(self, clave: str, documento_id: int):
        super().__init__("Archivo no encontrado")
        self.clave = clave
        self.documento_id = documento_id


class ErrorAlQuitar(Exception):
    """Falló alguna de las eliminaciones al quitar un documento de un notebook propio. Lleva la clave del notebook y el número
    del documento (para registrar el fallo en la bitácora) y la excepción original en `causa`; su mensaje no repite el texto
    de esa excepción, que puede traer rutas internas."""

    def __init__(self, clave: str, documento_id: int, causa: Exception):
        super().__init__("No se pudo quitar el documento")
        self.clave = clave
        self.documento_id = documento_id
        self.causa = causa


@dataclass(frozen=True)
class ClaveDeNotebook:
    """Qué es un tema para un usuario: `tipo` es NO_ES_NOTEBOOK, PROPIO (con su `notebook`) o NO_DISPONIBLE.

    No disponible reúne por igual lo ajeno, lo inexistente y toda forma de clave que no sea canónica: nada que permita
    distinguirlos hacia afuera (RNF-07.6)."""

    tipo: str
    notebook: Optional[T_Notebook] = None


class NotebookService:
    """Servicio de lógica de negocio para notebooks."""

    def __init__(self):
        self.notebook_repo = NotebookRepository()
        self.documento_repo = DocumentoRepository()
        self.expediente_repo = ExpedienteRepository()

    async def crear_notebook(self, db: Session, nombre: str, usuario_id: str) -> T_Notebook:
        """
        Crea un notebook nuevo, validado, para un usuario.

        Args:
            db: Sesión de base de datos.
            nombre: Nombre que el usuario le da al notebook.
            usuario_id: Cédula del usuario dueño.

        Returns:
            T_Notebook: Notebook creado.

        Raises:
            ValueError: Si el nombre está vacío (su mensaje es para el usuario, RF-17.1). Cualquier otra excepción es un
                error inesperado: quien atiende la petición no debe mostrar su texto (RF-17.30).
        """
        if not nombre or not nombre.strip():
            raise ValueError("El nombre del notebook no puede estar vacío")

        return self.notebook_repo.crear(db, nombre.strip(), usuario_id)

    async def _notebook_o_no_disponible(self, db: Session, notebook_id: int, usuario_id: str) -> T_Notebook:
        """El notebook del usuario, o `RecursoNoDisponible` si es ajeno, inexistente o su id no cabe en la columna (sin
        consultar la base: un id enorme daría un error de SQL que lo distinguiría de uno inexistente)."""
        if not 0 < notebook_id <= _ID_MAXIMO:
            raise RecursoNoDisponible(MOTIVO_NOTEBOOK_NO_DISPONIBLE)
        notebook = await self.obtener_notebook_de_usuario(db, notebook_id, usuario_id)
        if notebook is None:
            raise RecursoNoDisponible(MOTIVO_NOTEBOOK_NO_DISPONIBLE)
        return notebook

    def _documento_del_notebook(self, db: Session, notebook: T_Notebook, documento_id: int) -> T_Documento:
        """El documento si pertenece a `notebook`, o `RecursoNoDisponible` si es de otro tema, inexistente o su id no cabe."""
        documento = None
        if 0 < documento_id <= _ID_MAXIMO:
            documento = self.documento_repo.obtener_por_id(db, documento_id)
        if not documento or notebook.clave_interna not in [e.CT_Num_expediente for e in documento.expedientes]:
            raise RecursoNoDisponible(MOTIVO_DOCUMENTO_NO_DISPONIBLE)
        return documento

    async def listar_documentos_de_notebook(self, db: Session, notebook_id: int, usuario_id: str) -> List[T_Documento]:
        """Los documentos de un notebook del usuario (vacía si aún no se subió ninguno).

        Raises:
            RecursoNoDisponible: Si el notebook es ajeno o no existe (RNF-07.6).
        """
        notebook = await self._notebook_o_no_disponible(db, notebook_id, usuario_id)
        expediente = self.expediente_repo.obtener_por_numero(db, notebook.clave_interna)
        if not expediente:
            return []
        return self.documento_repo.listar_por_expediente(db, expediente)

    async def obtener_archivo_de_documento(
        self, db: Session, notebook_id: int, documento_id: int, usuario_id: str
    ) -> Tuple[T_Notebook, T_Documento, Path]:
        """El notebook, el documento y la ruta del archivo original de un documento procesado de un notebook del usuario.

        Raises:
            RecursoNoDisponible: Si el notebook es ajeno o no existe, o el documento no es de ese notebook (RNF-07.6, 07.32).
            DocumentoSinProcesar: Si el documento todavía no terminó de procesarse.
            ArchivoNoEncontrado: Si el archivo ya no está en disco o su ubicación no es la permitida (RNF-07.21).
        """
        notebook = await self._notebook_o_no_disponible(db, notebook_id, usuario_id)
        documento = self._documento_del_notebook(db, notebook, documento_id)
        if not self.documento_repo.verificar_esta_procesado(db, notebook.clave_interna, documento.CT_Nombre_archivo):
            raise DocumentoSinProcesar(notebook.clave_interna, documento.CN_Id_documento)
        ruta = file_management_service.obtener_ruta_archivo(notebook.clave_interna, documento.CT_Nombre_archivo)
        if not ruta:
            raise ArchivoNoEncontrado(notebook.clave_interna, documento.CN_Id_documento)
        return notebook, documento, ruta

    async def quitar_documento(self, db: Session, notebook_id: int, documento_id: int, usuario_id: str) -> T_Notebook:
        """Quita un documento de un notebook del usuario: sus fragmentos en Qdrant, su archivo y su registro (la excepción
        aprobada al borrado físico, RN-01). Devuelve el notebook.

        Raises:
            RecursoNoDisponible: Si el notebook es ajeno o no existe, o el documento no es de ese notebook (RNF-07.6, 07.32).
            ErrorAlQuitar: Si falla una de las eliminaciones; lleva la clave del notebook y el número del documento para
                registrar el fallo, y la causa original.
        """
        notebook = await self._notebook_o_no_disponible(db, notebook_id, usuario_id)
        documento = self._documento_del_notebook(db, notebook, documento_id)
        clave, nombre_archivo = notebook.clave_interna, documento.CT_Nombre_archivo
        # Cada paso es idempotente (RF-19.2): lo que ya no existe cuenta como eliminado, y cualquier otro error detiene el
        # borrado antes del registro, que sigue listado para que un nuevo intento complete lo que faltó.
        try:
            # 1. Fragmentos de Qdrant (cero puntos = éxito)
            await get_vectorstore_backend().delete_document_chunks(documento_id)

            # 2. Archivo físico en disco
            ruta = file_management_service.obtener_ruta_archivo(clave, nombre_archivo)
            if ruta:
                try:
                    ruta.unlink()
                except FileNotFoundError:
                    pass  # Ya no está: cuenta como eliminado (otro error, como un permiso, sí es un fallo)

            # 3. Registro en base de datos (y la fila de la tabla de unión)
            self.documento_repo.eliminar(db, documento)
        except Exception as causa:
            raise ErrorAlQuitar(clave, documento_id, causa) from causa
        return notebook

    async def listar_notebooks_usuario(self, db: Session, usuario_id: str) -> List[T_Notebook]:
        """Lista los notebooks de un usuario, más reciente primero."""
        return self.notebook_repo.listar_por_usuario(db, usuario_id)

    async def obtener_notebook_de_usuario(
        self, db: Session, notebook_id: int, usuario_id: str
    ) -> Optional[T_Notebook]:
        """Busca un notebook por ID, validando que pertenezca al usuario."""
        notebook = self.notebook_repo.obtener_por_id(db, notebook_id)
        if notebook and notebook.CN_Id_usuario == usuario_id:
            return notebook
        return None

    async def obtener_notebook_para_chat(
        self, db: Session, notebook_id: Optional[str], usuario_id: Optional[str]
    ) -> Optional[T_Notebook]:
        """El notebook que pide el chat de NotebookServIA si es del usuario, o None si no está disponible (ajeno, inexistente
        o con un identificador que no es numérico canónico: este último ni siquiera consulta la base, RF-11.32)."""
        id_notebook = id_de_notebook(notebook_id)
        if id_notebook is None:
            return None
        return await self.obtener_notebook_de_usuario(db, id_notebook, usuario_id)

    async def clasificar_clave(self, db: Session, tema: str, usuario_id: Optional[str]) -> ClaveDeNotebook:
        """Clasifica un tema para un usuario: no es forma de clave de notebook, es la de un notebook propio o no está
        disponible. Una forma de clave no canónica (`NB-05`, dígitos Unicode, fuera de rango) es no disponible sin
        consultar la base.

        Un tema sin forma de clave que la base iguala con el tema guardado de un notebook se trata como esa clave (RF-17.34):
        decide la comparación con que el sistema busca un tema guardado, sea cual sea la intercalación, y no una lista de
        grafías conocidas. Sin sesión de base de datos no hay con qué comparar."""
        if not forma_de_clave(tema):
            guardado = self._tema_que_iguala_la_base(db, tema)
            if guardado is None:
                return ClaveDeNotebook(NO_ES_NOTEBOOK)
            tema = guardado
        id_notebook = _id_de_clave(tema)
        if id_notebook is None:
            return ClaveDeNotebook(NO_DISPONIBLE)
        notebook = await self.obtener_notebook_de_usuario(db, id_notebook, usuario_id)
        return ClaveDeNotebook(PROPIO, notebook) if notebook else ClaveDeNotebook(NO_DISPONIBLE)

    async def es_tema_de_clave(self, db: Session, tema: Optional[str]) -> bool:
        """Si `tema` se trata como la clave de un notebook: tiene su forma o la base lo guardaría o iguala como una clave
        (RF-17.34). Es para el chat por tema y los temas similares, que atienden la clave como un tema sin documentos y no
        la registran. Si la base no responde, cuenta solo la forma: esas búsquedas ya excluyen lo ajeno por documento."""
        if forma_de_clave(tema):
            return True
        try:
            return self._tema_que_iguala_la_base(db, tema) is not None
        except Exception as error:
            logger.warning(f"No se pudo comprobar con la base si un tema equivale a una clave: {type(error).__name__}")
            return False

    def _tema_que_iguala_la_base(self, db: Session, tema: str) -> Optional[str]:
        """La clave de notebook con la que la base iguala `tema`, o None si no hay ninguna. Son dos preguntas a la base:

        1. Cómo guardaría `tema` la base en la columna VARCHAR del tema (B1 y B2, vueltas 1 y 2 de la revisión): el controlador
           cambia `ŃB-5` o `NB‐5` (U+2010) por `NB-5` y QUITA los caracteres de ancho cero (`NB-<U+200B>5`, U+2060, U+FEFF,
           combinantes…), de modo que un documento cargado con ellas quedaría unido al tema del notebook aunque este aún no
           tenga fila de tema (caso común: antes de su primera carga) y la primera carga de su dueño encontraría la fila de
           otro. Se pregunta a la base, con la conversión del INSERT y con la del `CAST` del servidor (que difieren con
           `NB−5`), y no se imita en Python (una lista de grafías no cubre las que no se conocen). Además se prueba el texto
           sin caracteres de formato (categoría Unicode Cf: guion blando, ancho cero…) porque algunos sobreviven a la
           conversión. No se rechaza ningún tema: solo cambia el trato de lo que quedaría o parecería una clave.
        2. Qué tema ya guardado iguala con `tema` según la comparación de la columna (la intercalación).

        Decisión 17 (Andrés, 20/10/2026, B): si lo escrito lleva dígitos que no son ASCII (`NB‐５`), no está disponible para
        nadie aunque la base lo guarde como `NB-5`: se devuelve la forma de clave sin número, que `_id_de_clave` no lee."""
        if db is None or not isinstance(tema, str) or not tema.strip():
            return None
        escrito = tema.strip()
        lecturas = (self.expediente_repo.como_lo_guarda_la_base(db, escrito),
                    self.expediente_repo.como_lo_convierte_el_servidor(db, escrito))
        for candidato in (*lecturas, _sin_formato(escrito), *(_sin_formato(lectura) for lectura in lecturas)):
            if forma_de_clave(candidato):
                if any(unicodedata.category(c) == "Nd" and not c.isascii() for c in escrito):
                    return _PREFIJO_DE_CLAVE
                return candidato.strip()
        guardado = self.expediente_repo.obtener_por_numero(db, escrito)
        if guardado is not None and forma_de_clave(guardado.CT_Num_expediente):
            return guardado.CT_Num_expediente
        return None

    async def ids_documentos_visibles(self, db: Session, usuario_id: Optional[str]) -> Set[int]:
        """Los documentos Procesados que `usuario_id` puede ver (RF-17.3): los que ninguno de sus temas tiene forma de clave de
        notebook, más los de sus propios notebooks.

        Decide con el tema que dice la base, no con el texto del fragmento: cubre cualquier grafía de la clave (`nb-5`,
        ` NB-5 `, `NB-05`) y los fragmentos de un notebook que no existe, sin tocar lo guardado en Qdrant. Un documento unido
        a un tema ajeno queda fuera aunque además esté en un tema general. Lo que la base no conoce nunca entra en la lista.
        """
        propios = set()
        if usuario_id is not None:
            propios = {notebook.CN_Id_notebook for notebook in self.notebook_repo.listar_por_usuario(db, usuario_id)}

        todos, ocultos = set(), set()
        for id_documento, tema in self.documento_repo.listar_procesados_con_temas(db):
            todos.add(id_documento)
            if forma_de_clave(tema) and _id_de_clave(tema) not in propios:
                ocultos.add(id_documento)
        return todos - ocultos
