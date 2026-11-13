"""
Servicio del Estudio del notebook (spec 010): generar un resumen, un informe o un mapa mental con las fuentes marcadas, guardar
notas del chat y listar, abrir y quitar los resultados guardados.

Funciones principales:
    - preparar_generacion: Valida y arma las partes del contenido (404 uniforme, selección vacía, tamaño, una a la vez)
    - ejecutar: Genera por partes y luego une, con avance, tope de tiempo y un reintento ante una salida inválida
    - guardar_nota, listar_resultados, obtener_resultado, quitar_resultado

Cada generación recorre TODO el contenido de las fuentes marcadas (RF-11.126): lo parte en tramos que caben en la ventana del
modelo, toma notas de cada uno y las une hasta que caben en una última llamada que redacta el resultado. Nada se guarda si la
generación se cancela, falla o se pasa del tiempo (RF-11.128, RF-11.130). Los resultados no son fuentes: no se indexan ni los
recupera ningún chat (RF-14.125).

Ver también:
    * app.services.estudio_logica: Partes, validación del mapa mental, citas y títulos (puro)
    * app.services.RAG.prompts.estudio_prompt: Instrucciones fijas (RF-11.123)
    * app.routes.estudio: Endpoints REST
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, Dict, List, Optional, Set

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.config import config
from app.config.contexto_config import CONFIGURACION
from app.db.database import SessionLocal
from app.db.models.resultado_estudio import T_Resultado_Estudio
from app.llm.llm_service import get_llm
from app.repositories.documento_repository import DocumentoRepository
from app.repositories.expediente_repository import ExpedienteRepository
from app.repositories.resultado_estudio_repository import ResultadoEstudioRepository
from app.services import estudio_logica as logica
from app.services.RAG import presupuesto_contexto as pc
from app.services.RAG.prompts import estudio_prompt as prompts
from app.services.bitacora.notebooks_audit_service import MOTIVO_RESULTADO_NO_DISPONIBLE
from app.services.notebook_service import (
    NotebookService, RecursoNoDisponible, SeleccionVacia, id_de_notebook, nombre_mostrado
)
from app.vectorstore import get_vectorstore_backend

logger = logging.getLogger(__name__)

MARGEN_TOKENS = 150           # holgura de cada llamada: el estimador de tokens es aproximado
RONDAS_DE_UNION_MAXIMAS = 5   # pasos de unión antes de recortar lo que no quepa
FRAGMENTOS_LEIDOS_MAXIMOS = 1000  # lo que lee Qdrant de una vez: si se llega, las fuentes no caben en una generación
LARGO_MAXIMO_NOMBRES_EN_LA_INSTRUCCION = 40  # cuántas fuentes se nombran al modelo como citables

MENSAJE_SIN_FUENTES = "Marque al menos una fuente para generar un resultado."
MENSAJE_EN_CURSO = "Hay una generación en curso. Espere o cancélela."
MENSAJE_DEMASIADO_EXTENSAS = "Las fuentes marcadas son demasiado extensas. Desmarque algunas e intente de nuevo."
MENSAJE_TIEMPO = "La generación tardó demasiado y se detuvo. Desmarque algunas fuentes e intente de nuevo."
MENSAJE_SALIDA_INVALIDA = "No se pudo generar el resultado. Intente de nuevo."
MENSAJE_MOTOR = "No se pudo generar el resultado. Verifique que el motor de lenguaje esté disponible e intente de nuevo."
MENSAJE_INESPERADO = "Error interno del servidor"

# Quién está generando ahora (RF-11.131): usuario -> hasta cuándo vale la marca. El vencimiento evita que una marca quede para
# siempre si la respuesta nunca empezó a enviarse. Un solo proceso atiende la API.
_generando: Dict[str, float] = {}


class GeneracionEnCurso(Exception):
    """El usuario ya tiene una generación en curso (RF-11.131)."""


class FuentesDemasiadoExtensas(Exception):
    """Las fuentes marcadas superan el tamaño máximo de una generación (RF-11.129)."""


class TiempoAgotado(Exception):
    """La generación superó el tiempo máximo (RF-11.130)."""


class SalidaInvalida(Exception):
    """El modelo no dio una salida válida ni en el reintento (RF-11.125)."""


class MotorNoDisponible(Exception):
    """Falló la llamada al motor de lenguaje (RF-11.132). No lleva el texto del error original."""


def hay_generacion_en_curso(usuario_id: Optional[str]) -> bool:
    """Si el usuario tiene una generación del Estudio en curso (RF-11.131)."""
    if usuario_id is None:
        return False
    vence = _generando.get(usuario_id)
    if vence is None:
        return False
    if vence < time.monotonic():
        _generando.pop(usuario_id, None)
        return False
    return True


@dataclass
class Preparacion:
    """Todo lo necesario para generar, ya validado."""
    notebook_id: int
    clave: str
    usuario_id: str
    tipo: str
    partes: List[logica.Parte]
    fuentes: List[dict]  # [{"id", "nombre"}] de las fuentes con contenido
    sistema_final: str
    maximo_union: int
    maximo_final: int


class EstudioService:
    """Lógica de negocio del Estudio del notebook."""

    def __init__(self):
        self.notebooks = NotebookService()
        self.resultados = ResultadoEstudioRepository()
        self.documento_repo = DocumentoRepository()
        self.expediente_repo = ExpedienteRepository()

    # --- generar -----------------------------------------------------------------------------------------------------------

    async def preparar_generacion(
        self, db: Session, texto_notebook: str, tipo: str, documentos: Optional[List[int]], usuario_id: str
    ) -> Preparacion:
        """Valida la petición y arma las partes del contenido; marca al usuario como «generando».

        Raises:
            RecursoNoDisponible: Notebook ajeno, inexistente, eliminado o con id no canónico (404 uniforme).
            GeneracionEnCurso: El usuario ya tiene una generación en curso (RF-11.131).
            SeleccionVacia: Ninguna fuente Procesado marcada, o sin contenido que leer (RF-11.121).
            FuentesDemasiadoExtensas: Las fuentes marcadas no caben en el máximo de partes (RF-11.129).
        """
        notebook = await self.notebooks.notebook_propio(db, texto_notebook, usuario_id)
        if hay_generacion_en_curso(usuario_id):
            raise GeneracionEnCurso()

        nombres_por_id = self._procesados_del_notebook(db, notebook.clave_interna)
        seleccion = set(nombres_por_id) if documentos is None else set(documentos) & set(nombres_por_id)
        if not seleccion:
            raise SeleccionVacia()

        trozos, fuentes = await self._leer_contenido(notebook.clave_interna, seleccion, nombres_por_id)
        if not trozos:
            raise SeleccionVacia()

        nombres = [f["nombre"] for f in fuentes]
        sistema_final = self._sistema_final(tipo, nombres)
        presupuesto = CONFIGURACION.presupuesto
        maximo_union = presupuesto - pc.tokens(prompts.UNION) - MARGEN_TOKENS
        maximo_final = presupuesto - pc.tokens(sistema_final) - MARGEN_TOKENS
        maximo_parte = presupuesto - max(pc.tokens(prompts.NOTAS), pc.tokens(prompts.UNION), pc.tokens(sistema_final)) - MARGEN_TOKENS
        partes = logica.partir(trozos, maximo_parte)
        if not partes or len(partes) > config.ESTUDIO_PARTES_MAXIMAS:
            if not partes:
                raise SeleccionVacia()
            raise FuentesDemasiadoExtensas()

        # Sin ningún `await` entre la comprobación de arriba y esta marca: dos peticiones a la vez no pasan las dos.
        _generando[usuario_id] = time.monotonic() + config.ESTUDIO_TIEMPO_MAXIMO_SEGUNDOS + 60
        return Preparacion(notebook.CN_Id_notebook, notebook.clave_interna, usuario_id, tipo, partes, fuentes, sistema_final,
                           maximo_union, maximo_final)

    def _procesados_del_notebook(self, db: Session, clave: str) -> Dict[int, str]:
        """Las fuentes Procesado del notebook: id -> nombre mostrado."""
        tema = self.expediente_repo.obtener_por_numero(db, clave)
        if tema is None:
            return {}
        return {d.CN_Id_documento: nombre_mostrado(d)
                for d in self.documento_repo.listar_por_expediente(db, tema, solo_procesados=True)}

    async def _leer_contenido(self, clave: str, seleccion: Set[int], nombres_por_id: Dict[int, str]):
        """Los fragmentos de las fuentes seleccionadas, en orden de fuente y de fragmento, con el nombre mostrado."""
        documentos = await get_vectorstore_backend().get_expedient_documents(clave, documentos_visibles=set(seleccion))
        if len(documentos) >= FRAGMENTOS_LEIDOS_MAXIMOS:
            raise FuentesDemasiadoExtensas()  # puede haber más de lo leído: no se genera con cobertura parcial
        por_documento: Dict[int, list] = {}
        for fragmento in documentos:
            id_documento = fragmento.metadata.get("id_documento")
            if isinstance(id_documento, int) and id_documento in seleccion:
                por_documento.setdefault(id_documento, []).append(fragmento)
        trozos: List[logica.Trozo] = []
        fuentes: List[dict] = []
        for id_documento in sorted(por_documento):
            nombre = nombres_por_id.get(id_documento) or por_documento[id_documento][0].metadata.get("archivo") or "documento"
            fuentes.append({"id": id_documento, "nombre": nombre})
            for fragmento in sorted(por_documento[id_documento], key=lambda f: f.metadata.get("indice_chunk", 0)):
                trozos.append(logica.Trozo(fuente=nombre, texto=fragmento.page_content))
        return trozos, fuentes

    @staticmethod
    def _sistema_final(tipo: str, nombres: List[str]) -> str:
        base = prompts.FINAL_POR_TIPO[tipo]
        if tipo == logica.TIPO_MAPA:
            return base
        citables = ", ".join(f"[{n}]" for n in nombres[:LARGO_MAXIMO_NOMBRES_EN_LA_INSTRUCCION])
        return f"{base}\n\nFuentes que puede citar (solo estas): {citables}"

    async def ejecutar(self, prep: Preparacion) -> AsyncIterator[dict]:
        """Genera el resultado y lo guarda. Emite eventos: `progreso` (etapa, actual, total), y al final `resultado` (el resultado
        guardado) o `error` (código y mensaje), siempre seguido de `done`. Cancelarlo (cerrar la conexión) no guarda nada."""
        inicio = time.monotonic()
        try:
            llm = await get_llm()
            total = len(prep.partes)
            if total == 1:
                yield {"type": "progreso", "etapa": "Generando el resultado", "actual": 1, "total": 1}
                base = prep.partes[0].texto
            else:
                notas: List[str] = []
                for numero, parte in enumerate(prep.partes, 1):
                    yield {"type": "progreso", "etapa": f"Analizando parte {numero} de {total}", "actual": numero, "total": total}
                    notas.append(await self._llamar(llm, prompts.NOTAS, parte.texto, inicio))
                base = None
                rondas = 0
                while base is None:
                    combinado = "\n\n".join(notas)
                    if pc.tokens(combinado) <= prep.maximo_final:
                        base = combinado
                        break
                    grupos = logica.agrupar(notas, prep.maximo_union)
                    rondas += 1
                    if len(grupos) >= len(notas) or rondas > RONDAS_DE_UNION_MAXIMAS:
                        base = combinado[: int(prep.maximo_final * CONFIGURACION.caracteres_por_token)]
                        break
                    nuevas = []
                    for numero, grupo in enumerate(grupos, 1):
                        yield {"type": "progreso", "etapa": "Uniendo resultados", "actual": numero, "total": len(grupos)}
                        nuevas.append(await self._llamar(llm, prompts.UNION, "\n\n".join(grupo), inicio))
                    notas = nuevas
                yield {"type": "progreso", "etapa": "Redactando el resultado", "actual": total, "total": total}

            nombres = [f["nombre"] for f in prep.fuentes]
            contenido = None
            for _intento in (1, 2):  # un reintento ante una salida inválida (RF-11.125)
                salida = await self._llamar(llm, prep.sistema_final, base, inicio)
                contenido = self._validar(prep.tipo, salida, nombres)
                if contenido is not None:
                    break
            if contenido is None:
                raise SalidaInvalida()

            resultado = self._guardar(prep, contenido)
            yield {"type": "resultado", "resultado": self.describir(resultado, con_contenido=True)}
        except TiempoAgotado:
            yield {"type": "error", "codigo": "tiempo", "mensaje": MENSAJE_TIEMPO}
        except SalidaInvalida:
            yield {"type": "error", "codigo": "salida_invalida", "mensaje": MENSAJE_SALIDA_INVALIDA}
        except MotorNoDisponible:
            yield {"type": "error", "codigo": "motor", "mensaje": MENSAJE_MOTOR}
        except asyncio.CancelledError:
            raise  # cancelar no guarda nada y no se registra (RF-11.128)
        except Exception as e:
            logger.error("Error generando un resultado de estudio (%s)", type(e).__name__, exc_info=True)
            yield {"type": "error", "codigo": "interno", "mensaje": MENSAJE_INESPERADO}
        finally:
            _generando.pop(prep.usuario_id, None)
        yield {"type": "done"}

    async def _llamar(self, llm, sistema: str, texto: str, inicio: float) -> str:
        """Una llamada al motor, con lo que quede del tiempo máximo de la generación (RF-11.130)."""
        restante = config.ESTUDIO_TIEMPO_MAXIMO_SEGUNDOS - (time.monotonic() - inicio)
        if restante <= 0:
            raise TiempoAgotado()

        async def consumir() -> str:
            trozos: List[str] = []
            async for trozo in llm.astream([SystemMessage(content=sistema), HumanMessage(content=texto)]):
                trozos.append(str(getattr(trozo, "content", trozo) or ""))
            return "".join(trozos).strip()

        try:
            return await asyncio.wait_for(consumir(), timeout=restante)
        except asyncio.TimeoutError:
            raise TiempoAgotado()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Falló la llamada al motor de lenguaje (%s)", type(e).__name__)
            raise MotorNoDisponible() from None

    @staticmethod
    def _validar(tipo: str, salida: str, nombres: List[str]) -> Optional[str]:
        """El contenido a guardar si la salida es válida, o None (RF-11.125, RF-12.120). Un Resumen o un Informe sin citas se guarda
        con las fuentes de la selección al final (`asegurar_fuentes`); solo una salida vacía se rechaza."""
        if tipo == logica.TIPO_MAPA:
            mapa = logica.analizar_mapa(salida)
            return None if mapa is None else json.dumps(mapa, ensure_ascii=False)
        if not salida.strip():
            return None
        return logica.asegurar_fuentes(salida.strip(), nombres)

    def _guardar(self, prep: Preparacion, contenido: str) -> T_Resultado_Estudio:
        """Guarda el resultado con su propia sesión: la de la petición ya se cerró al empezar el envío."""
        with SessionLocal() as db:
            return self.resultados.crear(
                db, prep.notebook_id, prep.usuario_id, prep.tipo, logica.titulo_por_omision(prep.tipo, datetime.utcnow()),
                contenido, json.dumps(prep.fuentes, ensure_ascii=False))

    # --- notas, listar, abrir, quitar ---------------------------------------------------------------------------------------

    async def guardar_nota(self, db: Session, texto_notebook: str, usuario_id: str, pregunta: str, respuesta: str,
                           fuentes: List[str]) -> T_Resultado_Estudio:
        """Guarda una respuesta del chat como nota (RF-14.127). No llama al modelo.

        Raises:
            RecursoNoDisponible: Notebook ajeno, inexistente o con id no canónico.
            ValueError: La respuesta está vacía.
        """
        notebook = await self.notebooks.notebook_propio(db, texto_notebook, usuario_id)
        if not respuesta.strip():
            raise ValueError("La respuesta no puede estar vacía.")
        nombres = []
        for nombre in fuentes:
            limpio = nombre.strip()
            if limpio and limpio not in nombres:
                nombres.append(limpio[:500])
        return self.resultados.crear(
            db, notebook.CN_Id_notebook, usuario_id, logica.TIPO_NOTA, logica.titulo_por_omision(logica.TIPO_NOTA, datetime.utcnow()),
            json.dumps({"pregunta": pregunta.strip(), "respuesta": respuesta.strip()}, ensure_ascii=False),
            json.dumps([{"id": None, "nombre": n} for n in nombres], ensure_ascii=False))

    def _fuentes_actuales(self, db: Session, clave: str):
        tema = self.expediente_repo.obtener_por_numero(db, clave)
        documentos = self.documento_repo.listar_por_expediente(db, tema) if tema else []
        return {d.CN_Id_documento for d in documentos}, {nombre_mostrado(d) for d in documentos}

    async def listar_resultados(self, db: Session, texto_notebook: str, usuario_id: str) -> List[dict]:
        notebook = await self.notebooks.notebook_propio(db, texto_notebook, usuario_id)
        ids, nombres = self._fuentes_actuales(db, notebook.clave_interna)
        return [self.describir(r, ids, nombres) for r in self.resultados.listar_visibles(db, notebook.CN_Id_notebook)]

    async def _resultado_propio(self, db: Session, texto_notebook: str, texto_resultado: str, usuario_id: str):
        notebook = await self.notebooks.notebook_propio(db, texto_notebook, usuario_id)
        id_resultado = id_de_notebook(texto_resultado)
        resultado = None if id_resultado is None else self.resultados.obtener_visible(db, notebook.CN_Id_notebook, id_resultado)
        if resultado is None:
            raise RecursoNoDisponible(MOTIVO_RESULTADO_NO_DISPONIBLE)
        return notebook, resultado

    async def obtener_resultado(self, db: Session, texto_notebook: str, texto_resultado: str, usuario_id: str) -> dict:
        notebook, resultado = await self._resultado_propio(db, texto_notebook, texto_resultado, usuario_id)
        ids, nombres = self._fuentes_actuales(db, notebook.clave_interna)
        return self.describir(resultado, ids, nombres, con_contenido=True)

    async def quitar_resultado(self, db: Session, texto_notebook: str, texto_resultado: str, usuario_id: str):
        """Baja lógica (RF-14.124): el resultado deja de listarse y la fila se conserva. Devuelve (notebook, resultado)."""
        notebook, resultado = await self._resultado_propio(db, texto_notebook, texto_resultado, usuario_id)
        self.resultados.marcar_quitado(db, resultado)
        return notebook, resultado

    @staticmethod
    def describir(resultado: T_Resultado_Estudio, ids: Optional[Set[int]] = None, nombres: Optional[Set[str]] = None,
                  con_contenido: bool = False) -> dict:
        """El resultado como lo devuelve la API. `ids` y `nombres` son las fuentes que hoy tiene el notebook (para el aviso de
        RF-14.123); sin ellos no se calcula el aviso."""
        fuentes = json.loads(resultado.CT_Fuentes)
        faltantes = False
        if ids is not None and nombres is not None:
            faltantes = any(
                (f.get("id") not in ids) if f.get("id") is not None else (f["nombre"] not in nombres) for f in fuentes)
        datos = {
            "id": resultado.CN_Id_resultado,
            "tipo": resultado.CT_Tipo,
            "titulo": resultado.CT_Titulo,
            "fecha_creacion": resultado.CF_Fecha_creacion.isoformat() + "Z",
            "fuentes": fuentes,
            "fuentes_faltantes": faltantes,
        }
        if con_contenido:
            if resultado.CT_Tipo in (logica.TIPO_MAPA, logica.TIPO_NOTA):
                datos["contenido"] = json.loads(resultado.CT_Contenido)
            else:
                datos["contenido"] = resultado.CT_Contenido
        return datos


estudio_service = EstudioService()
