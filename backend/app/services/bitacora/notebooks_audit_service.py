"""
Servicio de auditoría de NotebookServIA y de los intentos sobre un notebook, documento o conversación no disponibles.

Registra, en la bitácora (RF-21):
    * Las acciones del usuario sobre sus notebooks (RF-21.30): crear, previsualizar un documento y quitarlo, con éxito o con
      fallo. La fila lleva el usuario, el tipo, la clave `NB-<id>` como tema (asociada al tema de la base si ya existe), el
      número del documento y el resultado; nunca el nombre del notebook ni del archivo, ni el texto de una excepción, y sin
      NUL ni caracteres de control (RNF-07.24).
    * Los intentos fallidos de usar algo que el usuario no puede usar: un notebook ajeno, inexistente o con una clave que no
      es de un notebook suyo (RF-21.32, RF-21.33). La fila lleva solo el motivo y su clasificación como error de acceso;
      nunca la clave, el nombre, la pregunta ni el identificador pedidos, porque pueden contener datos de otra persona
      (RNF-07.24). Para el usuario ajeno y el inexistente el registro es idéntico: la bitácora tampoco debe distinguirlos.

Si el registro falla, cada método devuelve None y la acción continúa (RF-21).

Ver también:
    * app.services.bitacora.archivos_audit_service: `registrar_descarga_rechazada`, el mismo tratamiento para la descarga
    * app.services.notebook_service: `clasificar_clave`, que decide si un tema es un notebook disponible
    * app.routes.rag: el chat, que lo usa para el tema con forma de clave de notebook
    * app.routes.notebooks: crear, listar, previsualizar y quitar documentos
"""
from datetime import datetime
from typing import Optional
import logging

from sqlalchemy.orm import Session

from app.constants.tipos_accion import TiposAccion
from app.db.models.bitacora import T_Bitacora
from app.repositories.expediente_repository import ExpedienteRepository
from app.services.documentos.file_management_service import _sin_control
from .bitacora_service import BitacoraService

logger = logging.getLogger(__name__)

# Los motivos de un intento fallido: iguales para lo ajeno y lo inexistente.
MOTIVO_NOTEBOOK_NO_DISPONIBLE = "notebook no disponible"
MOTIVO_DOCUMENTO_NO_DISPONIBLE = "documento no disponible"
MOTIVO_CONVERSACION_NO_DISPONIBLE = "conversación no disponible"


class NotebooksAuditService:
    """Servicio de auditoría de los notebooks y de los intentos sobre recursos no disponibles."""

    def __init__(self):
        self.bitacora_service = BitacoraService()
        self.expediente_repo = ExpedienteRepository()

    def _id_del_tema(self, db: Session, clave: str) -> Optional[int]:
        """El id del tema `clave` si ya existe en la base (un notebook sin documentos todavía no tiene fila de tema)."""
        tema = self.expediente_repo.obtener_por_numero(db, clave)
        return tema.CN_Id_expediente if tema else None

    async def _registrar_accion(
        self,
        db: Session,
        usuario_id: Optional[str],
        tipo_accion_id: int,
        texto: str,
        clave: str,
        info: dict
    ) -> Optional[T_Bitacora]:
        """Escribe la fila de una acción sobre el notebook `clave`; el tema también queda en `info_adicional.tema`."""
        info = {"tema": clave, **info, "timestamp": datetime.utcnow().isoformat()}
        return await self.bitacora_service.registrar(
            db=db,
            usuario_id=usuario_id,
            tipo_accion_id=tipo_accion_id,
            texto=texto,
            expediente_id=self._id_del_tema(db, clave),
            info_adicional=info
        )

    async def registrar_creacion(
        self,
        db: Session,
        usuario_id: Optional[str],
        clave_notebook: str
    ) -> Optional[T_Bitacora]:
        """
        Registra la creación de un notebook (RF-21.30), solo con su clave `NB-<id>`: el nombre que le dio el usuario no se guarda.

        Returns:
            T_Bitacora: Registro creado o None si hubo error (la acción continúa, RF-21)
        """
        try:
            clave = _sin_control(clave_notebook)
            return await self._registrar_accion(
                db, usuario_id, TiposAccion.CREAR_NOTEBOOK, f"Notebook creado: {clave}", clave,
                {"resultado": "exitoso", "accion": "crear_notebook"})
        except Exception as e:
            logger.warning(f"Error registrando la creación de un notebook en bitácora: {type(e).__name__}")
            return None

    async def registrar_previsualizacion(
        self,
        db: Session,
        usuario_id: Optional[str],
        clave_notebook: str,
        documento_id: int
    ) -> Optional[T_Bitacora]:
        """
        Registra la previsualización de un documento de un notebook (RF-21.30), con la clave y el número del documento: el
        nombre del archivo no se guarda. Usa el tipo «Descargar Archivo» (descarga o visualización).

        Returns:
            T_Bitacora: Registro creado o None si hubo error (la acción continúa, RF-21)
        """
        try:
            clave = _sin_control(clave_notebook)
            return await self._registrar_accion(
                db, usuario_id, TiposAccion.DESCARGAR_ARCHIVO,
                f"Previsualización de un documento del notebook {clave} (documento {int(documento_id)})", clave,
                {"documento_id": int(documento_id), "resultado": "exitoso", "accion": "previsualizar_documento"})
        except Exception as e:
            logger.warning(f"Error registrando la previsualización de un documento en bitácora: {type(e).__name__}")
            return None

    async def registrar_previsualizacion_fallida(
        self,
        db: Session,
        usuario_id: Optional[str],
        clave_notebook: str,
        documento_id: int,
        motivo: str,
        tipo_error: str
    ) -> Optional[T_Bitacora]:
        """
        Registra que no se pudo previsualizar un documento propio de un notebook (RF-21.30): tipo «Descargar Archivo», con la
        clave, el número del documento, el motivo fijo («documento sin procesar» como «validacion»; «archivo no encontrado»
        como «interno») y sin el nombre del archivo, la ruta ni el texto de ninguna excepción.

        Returns:
            T_Bitacora: Registro creado o None si hubo error (la acción continúa, RF-21)
        """
        try:
            clave = _sin_control(clave_notebook)
            numero = int(documento_id)
            return await self._registrar_accion(
                db, usuario_id, TiposAccion.DESCARGAR_ARCHIVO,
                f"Error al previsualizar un documento del notebook {clave} (documento {numero}): {_sin_control(motivo)}", clave,
                {"documento_id": numero, "resultado": "error", "tipo_error": tipo_error, "motivo": motivo,
                 "accion": "previsualizar_documento"})
        except Exception as e:
            logger.warning(f"Error registrando un fallo de previsualización en bitácora: {type(e).__name__}")
            return None

    async def registrar_quitar(
        self,
        db: Session,
        usuario_id: Optional[str],
        clave_notebook: str,
        documento_id: int,
        exito: bool,
        tipo_error: Optional[str] = None
    ) -> Optional[T_Bitacora]:
        """
        Registra que un documento se quitó de un notebook, o que no se pudo quitar (RF-21.30), con la clave y el número del
        documento. Un fallo lleva solo su clasificación (`tipo_error`, «interno» si es inesperado): el texto de la excepción
        no se guarda porque puede traer rutas internas.

        Returns:
            T_Bitacora: Registro creado o None si hubo error (la acción continúa, RF-21)
        """
        try:
            clave = _sin_control(clave_notebook)
            numero = int(documento_id)
            info = {"documento_id": numero, "accion": "quitar_documento"}
            if exito:
                info["resultado"] = "exitoso"
                texto = f"Documento quitado del notebook {clave} (documento {numero})"
            else:
                info["resultado"] = "error"
                info["tipo_error"] = tipo_error or "interno"
                texto = f"Error al quitar un documento del notebook {clave} (documento {numero})"
            return await self._registrar_accion(db, usuario_id, TiposAccion.QUITAR_DOCUMENTO_NOTEBOOK, texto, clave, info)
        except Exception as e:
            logger.warning(f"Error registrando que se quitó un documento en bitácora: {type(e).__name__}")
            return None

    async def registrar_intento_fallido(
        self,
        db: Session,
        usuario_id: Optional[str],
        tipo_accion_id: int,
        motivo: str
    ) -> Optional[T_Bitacora]:
        """
        Registra el intento de usar un recurso no disponible (RF-21.32), solo con su motivo y como error de acceso.

        Args:
            db: Sesión de base de datos
            usuario_id: ID del usuario que lo intentó
            tipo_accion_id: Tipo de la acción intentada (consulta, carga, descarga, quitar...), de `TiposAccion`
            motivo: «notebook no disponible», «documento no disponible» o «conversación no disponible»

        Returns:
            T_Bitacora: Registro creado o None si hubo error (la acción continúa, RF-21)
        """
        try:
            return await self.bitacora_service.registrar(
                db=db,
                usuario_id=usuario_id,
                tipo_accion_id=tipo_accion_id,
                texto=f"Intento fallido: {motivo}",
                info_adicional={
                    "motivo": motivo,
                    "error": "intento fallido",
                    "tipo_error": "acceso",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Error registrando un intento fallido en bitácora: {type(e).__name__}")
            return None


# Instancia singleton del servicio especializado
notebooks_audit_service = NotebooksAuditService()
