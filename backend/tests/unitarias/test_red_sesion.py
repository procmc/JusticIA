"""Red de seguridad del inicio de sesión (spec 004, T5): las dos comprobaciones que no necesitan servicios.

- RF-01.1: sin configuración de la vigencia del token, el sistema usa 60 minutos.
- RF-01.2: la comparación contra el hash de la contraseña corre exactamente una vez en los tres casos de credenciales
  inválidas (correo no registrado, contraseña incorrecta y cuenta Inactiva), para que el tiempo de la respuesta no
  revele el caso. Es una prueba estructural; los tiempos reales se miden en la verificación manual.

Lo que el sistema hoy no cumple va como `xfail` estricto con la etiqueta del requisito y del módulo.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.soporte.nombres import PREFIJO_DATOS

RUTA_DE_LA_CONFIGURACION = Path(__file__).resolve().parents[2] / "app" / "config" / "config.py"
VARIABLES_DE_VIGENCIA = ("ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_EXPIRE_HOURS")


def _vigencia_leida_por_la_configuracion(monkeypatch, **entorno) -> int:
    """Ejecuta una copia de `config.py` con solo las variables dadas y sin leer el `.env` de desarrollo.

    Se ejecuta aparte (sin registrarla como módulo) para no alterar la configuración que ya tomó el sistema, y se anula
    `load_dotenv` porque, de lo contrario, devolvería al entorno la vigencia del archivo de desarrollo.
    """
    for variable in VARIABLES_DE_VIGENCIA:
        monkeypatch.delenv(variable, raising=False)
    for variable, valor in entorno.items():
        monkeypatch.setenv(variable, valor)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    especificacion = importlib.util.spec_from_file_location(f"{PREFIJO_DATOS}_config_aislada", RUTA_DE_LA_CONFIGURACION)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo.JWT_EXPIRE_MINUTES


# --- RF-01.1: vigencia del token ------------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-01.1")
def test_vigencia_configurada_se_respeta(monkeypatch):
    """RF-01.1 (control): con la vigencia configurada en minutos, el token dura esos minutos."""
    assert _vigencia_leida_por_la_configuracion(monkeypatch, ACCESS_TOKEN_EXPIRE_MINUTES="45") == 45


@pytest.mark.requisito("RF-01.1")
@pytest.mark.xfail(strict=True, raises=AssertionError, reason="RF-01.1 · autenticación")
def test_vigencia_por_omision_60_min(monkeypatch):
    """RF-01.1: sin configuración de la vigencia, el token dura 60 minutos."""
    assert _vigencia_leida_por_la_configuracion(monkeypatch) == 60


# --- RF-01.2: una sola comparación de hash --------------------------------------------------------------------------------

class ContextoContador:
    """Sustituye al contexto de bcrypt: cuenta las comparaciones contra un hash y devuelve un resultado fijo."""

    def __init__(self, resultado: bool):
        self.resultado = resultado
        self.comparaciones = 0

    def verify(self, secreto, hash_guardado) -> bool:
        self.comparaciones += 1
        return self.resultado


class BaseSimulada:
    """Una sesión de base de datos mínima: `query(Modelo).filter(...).first()` devuelve lo que corresponde al modelo."""

    def __init__(self, por_modelo: dict):
        self.por_modelo = por_modelo

    def query(self, modelo):
        encontrado = self.por_modelo.get(modelo.__name__)
        return SimpleNamespace(filter=lambda *condiciones: SimpleNamespace(first=lambda: encontrado))


def _caso(nombre: str, marcas=()):
    return pytest.param(nombre, id=nombre, marks=list(marcas))


CASOS_DE_CREDENCIALES_INVALIDAS = [
    _caso("correo no registrado", [pytest.mark.xfail(strict=True, raises=AssertionError, reason="RF-01.2 · autenticación")]),
    _caso("contraseña incorrecta"),
    _caso("cuenta inactiva"),
]


@pytest.mark.requisito("RF-01.2")
@pytest.mark.parametrize("caso", CASOS_DE_CREDENCIALES_INVALIDAS)
def test_una_sola_comparacion_de_hash(caso):
    """RF-01.2: en los tres casos de credenciales inválidas la comparación contra un hash corre exactamente una vez
    (con un hash de relleno si el correo no existe), así el tiempo no revela el caso."""
    from app.services.auth_service import AuthService

    usuario = SimpleNamespace(
        CN_Id_usuario=f"{PREFIJO_DATOS}000001", CT_Correo="prueba@prueba.invalid", CT_Contrasenna="hash-de-prueba",
        CN_Id_estado=1, CF_Ultimo_acceso=None,
    )
    estado = SimpleNamespace(CN_Id_estado=1, CT_Nombre_estado="Inactivo" if caso == "cuenta inactiva" else "Activo")
    base = BaseSimulada({"T_Usuario": None if caso == "correo no registrado" else usuario, "T_Estado": estado})
    servicio = AuthService()
    contexto = ContextoContador(resultado=caso != "contraseña incorrecta")
    servicio.usuario_repo.pwd_context = contexto

    import asyncio

    with pytest.raises(ValueError) as error:
        asyncio.run(servicio.autenticar_usuario(base, usuario.CT_Correo, "PRUEBA-clave-de-prueba"))

    assert str(error.value) == "Credenciales inválidas"
    assert contexto.comparaciones == 1, f"la comparación contra un hash corrió {contexto.comparaciones} veces y debía correr una"
