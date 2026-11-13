"""Propiedad `esta_quitado` del modelo de documento (spec 009b, cambio GG1; RF-19.111, RF-19.113). Sin base de datos."""
from datetime import datetime

import pytest

from app.db.models.documento import T_Documento


@pytest.mark.requisito("RF-19.111")
def test_un_documento_sin_fecha_de_baja_no_esta_quitado():
    documento = T_Documento(CT_Nombre_archivo="PRUEBA_a.pdf", CT_Tipo_archivo="application/pdf")
    assert documento.CF_Fecha_baja is None and documento.esta_quitado is False


@pytest.mark.requisito("RF-19.111")
def test_un_documento_con_fecha_de_baja_esta_quitado():
    documento = T_Documento(CT_Nombre_archivo="PRUEBA_a.pdf", CT_Tipo_archivo="application/pdf",
                            CF_Fecha_baja=datetime(2026, 11, 11, 10, 5), CN_Id_usuario_baja="000000000")
    assert documento.esta_quitado is True
