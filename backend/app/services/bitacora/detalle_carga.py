"""
Detalle de un registro de carga de documentos para la bitácora completa (spec 004, RF-22.1).

Convierte lo que la bitácora guardó de una carga (la información adicional de la fila y su fecha) en lo que el
Administrador ve al abrir el registro: el nombre visible de su tipo y cada dato con su etiqueta en español, en el
orden de la tabla de RF-22.1. Son funciones puras: no tocan la base de datos ni cambian lo que se guarda.

Reglas que concentra, para que la pantalla solo presente la lista:
    * Solo se entregan los datos que aportan al Administrador. La tarea, la colección, el número de vectores, la fase
      interna y el texto crudo del error nunca salen (no aportan, o pueden llevar rutas).
    * La causa de un error es siempre una de la lista cerrada de la spec (`clasificar_causa`); el texto de la
      excepción no se devuelve nunca.
    * Un dato sin valor o con valor de relleno («N/A», «Error general», «Task <id>») se omite.
    * La hora guardada es UTC y el detalle la muestra en la hora de Costa Rica (UTC-6, sin horario de verano).

Ver también:
    * app.services.bitacora.ingesta_audit_service: quien escribe estas filas y define los motivos de rechazo
    * app.services.bitacora.bitacora_stats_service: `obtener_bitacora_completa` añade el detalle a cada registro
    * specs/004-red-de-seguridad-backend/spec.md: RF-22.1 y «Causa clasificada»
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .ingesta_audit_service import (
    MOTIVO_ARCHIVO_VACIO, MOTIVO_ERROR_INTERNO, MOTIVO_NO_SE_PUDO_GUARDAR, MOTIVO_NOMBRE_NO_VALIDO,
    MOTIVO_TEMA_NO_VALIDO,
)

# Causas del fallo del procesamiento (literales de la spec). «error interno» es también un motivo de rechazo.
CAUSA_FORMATO_O_TAMANO = "formato o tamaño no permitido"
CAUSA_NO_SE_PUDO_EXTRAER = "no se pudo extraer el texto"
CAUSA_SERVICIO_NO_DISPONIBLE = "servicio de procesamiento no disponible"
CAUSA_NO_SE_PUDO_GUARDAR_PARA_BUSQUEDA = "no se pudo guardar para la búsqueda"
CAUSA_ERROR_INTERNO = MOTIVO_ERROR_INTERNO

# Motivos de rechazo que se pueden mostrar; cualquier otro valor guardado se muestra como «error interno».
MOTIVOS_MOSTRABLES = (
    MOTIVO_TEMA_NO_VALIDO, MOTIVO_NOMBRE_NO_VALIDO, MOTIVO_ARCHIVO_VACIO, MOTIVO_NO_SE_PUDO_GUARDAR, MOTIVO_ERROR_INTERNO,
)

# Regla de clasificación (en minúsculas; gana la primera que se cumple).
_PREFIJOS_DE_FORMATO = ("formato no permitido", "tipo mime no permitido", "archivo demasiado grande", "extensión '", "tipo mime '")
_CONTIENE_DE_FORMATO = ("excede el límite",)
_PREFIJOS_DE_EXTRACCION = ("error extrayendo texto", "no se pudo extraer texto", "error transcribiendo audio",
                           "no se pudo transcribir", "no se pudo reconocer el manuscrito")
_SENALES_DE_SERVICIO_CAIDO = ("no disponible", "timeout", "timed out", "connection", "conexión", "falló después de")
_SENALES_DE_GUARDADO = ("qdrant", "vector", "embedding", "collection", "colección")

# Nombre visible de cada tipo, según la fase que guardó la fila.
_TIPO_POR_FASE = {
    "iniciado": "Carga iniciada",
    "inicio": "Inicio del procesamiento",
    "vectorstore_exitoso": "Documento almacenado",
    "completado": "Procesamiento terminado",
    "error": "Error de procesamiento",
    "cancelado": "Cancelación",
    "error_cancelacion": "Error de cancelación",
}
TIPO_CARGA_RECHAZADA = "Carga rechazada"
TIPO_OTRA_FASE = "Otra fase"

_RELLENO_DE_TEMA = "N/A"
_RELLENO_DE_ARCHIVO = "Error general"
_PREFIJO_DE_ARCHIVO_RELLENO = "Task "

_DESFASE_DE_COSTA_RICA = timedelta(hours=6)


def clasificar_causa(crudo: Optional[str]) -> str:
    """Causa clasificada del fallo del procesamiento a partir del error crudo guardado (RF-22.1).

    Se aplica sin distinguir mayúsculas y gana la primera regla que se cumple. Se usa el texto porque la extracción
    envuelve todos sus fallos en un mismo tipo de excepción y es la única señal; un nombre de archivo que contenga un
    patrón puede desviar la clasificación (aceptado en la spec). Sin error guardado, o con un texto que no encaje, es
    «error interno». Nunca devuelve el texto recibido.
    """
    texto = (crudo or "").strip().lower()
    if not texto:
        return CAUSA_ERROR_INTERNO
    if texto.startswith(_PREFIJOS_DE_FORMATO) or any(parte in texto for parte in _CONTIENE_DE_FORMATO):
        return CAUSA_FORMATO_O_TAMANO
    if texto.startswith(_PREFIJOS_DE_EXTRACCION):
        if any(senal in texto for senal in _SENALES_DE_SERVICIO_CAIDO):
            return CAUSA_SERVICIO_NO_DISPONIBLE
        return CAUSA_NO_SE_PUDO_EXTRAER
    if any(senal in texto for senal in _SENALES_DE_GUARDADO):
        return CAUSA_NO_SE_PUDO_GUARDAR_PARA_BUSQUEDA
    return CAUSA_ERROR_INTERNO


def hora_de_costa_rica(fecha: Optional[datetime]) -> str:
    """La hora guardada (UTC) en la de Costa Rica (UTC-6), con formato «dd/mm/aaaa hh:mm:ss»; vacío si no hay fecha."""
    if fecha is None:
        return ""
    if fecha.tzinfo is not None:
        fecha = fecha.astimezone(timezone.utc).replace(tzinfo=None)
    return (fecha - _DESFASE_DE_COSTA_RICA).strftime("%d/%m/%Y %H:%M:%S")


def _texto(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


def _tema(info: Dict[str, Any]) -> str:
    tema = _texto(info.get("expediente"))
    return "" if tema.upper() == _RELLENO_DE_TEMA else tema


def _archivo(info: Dict[str, Any]) -> str:
    archivo = _texto(info.get("archivo"))
    if archivo == _RELLENO_DE_ARCHIVO or archivo.startswith(_PREFIJO_DE_ARCHIVO_RELLENO):
        return ""
    return archivo


def _mayor_que_cero(valor: Any) -> bool:
    try:
        return int(valor) > 0
    except (TypeError, ValueError):
        return False


def _tipo(info: Dict[str, Any]) -> str:
    fase = info.get("fase")
    if not fase and "motivo" in info:
        return TIPO_CARGA_RECHAZADA
    return _TIPO_POR_FASE.get(fase, TIPO_OTRA_FASE)


def armar_detalle_carga(info: Any, fecha: Optional[datetime]) -> Dict[str, Any]:
    """Detalle de un registro de carga: `{"tipo": nombre visible, "datos": [{"etiqueta", "valor"}]}` (RF-22.1).

    Args:
        info: la información adicional ya leída de la fila (un diccionario); cualquier otra cosa se trata como vacía
            y el registro queda como «Otra fase» solo con su fecha, sin fallar.
        fecha: la fecha y hora guardada en la fila (UTC).

    Los datos van en el orden de la tabla de RF-22.1 y se omite toda etiqueta sin valor o con relleno. Los valores son
    siempre texto.
    """
    info = info if isinstance(info, dict) else {}
    tipo = _tipo(info)
    hora = hora_de_costa_rica(fecha)
    tema, archivo = _tema(info), _archivo(info)

    if tipo == TIPO_CARGA_RECHAZADA:
        motivo = _texto(info.get("motivo"))
        candidatos = [("Fecha y hora", hora), ("Motivo", motivo if motivo in MOTIVOS_MOSTRABLES else MOTIVO_ERROR_INTERNO)]
    else:
        candidatos = [("Tema", tema), ("Fecha y hora", hora)]
        if tipo == "Carga iniciada":
            candidatos.append(("Archivos aceptados", _texto(info.get("archivos_aceptados"))))
            if _mayor_que_cero(info.get("archivos_rechazados")):
                candidatos.append(("Archivos rechazados", _texto(info.get("archivos_rechazados"))))
        else:
            candidatos.append(("Archivo", archivo))
            if tipo == "Documento almacenado":
                candidatos.append(("Documento", _texto(info.get("documento_id"))))
                candidatos.append(("Fragmentos", _texto(info.get("num_chunks"))))
            elif tipo == "Error de procesamiento":
                candidatos.append(("Causa", clasificar_causa(info.get("error_details"))))

    datos: List[Dict[str, str]] = [{"etiqueta": etiqueta, "valor": valor} for etiqueta, valor in candidatos if valor]
    return {"tipo": tipo, "datos": datos}
