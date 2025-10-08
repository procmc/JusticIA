"""
Schemas Pydantic para bitácora de acciones.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class BitacoraBase(BaseModel):
    """Schema base de bitácora"""
    texto: str = Field(..., description="Descripción de la acción realizada")
    expediente_id: Optional[int] = Field(None, description="ID del expediente relacionado")
    info_adicional: Optional[Dict[str, Any]] = Field(None, description="Información adicional")


class BitacoraRegistrar(BitacoraBase):
    """Schema para registrar una nueva acción en bitácora"""
    tipo_accion_id: int = Field(..., description="ID del tipo de acción", ge=1, le=8)


class BitacoraRespuesta(BaseModel):
    """Schema de respuesta de bitácora"""
    id_bitacora: int = Field(..., alias="CN_Id_bitacora")
    fecha_hora: datetime = Field(..., alias="CF_Fecha_hora")
    texto: str = Field(..., alias="CT_Texto")
    info_adicional: Optional[str] = Field(None, alias="CT_Informacion_adicional")
    
    # IDs relacionados
    id_usuario: str = Field(..., alias="CN_Id_usuario")
    id_tipo_accion: Optional[int] = Field(None, alias="CN_Id_tipo_accion")
    id_expediente: Optional[int] = Field(None, alias="CN_Id_expediente")
    
    # Datos relacionados (opcional, para respuestas expandidas)
    nombre_usuario: Optional[str] = None
    nombre_tipo_accion: Optional[str] = None
    numero_expediente: Optional[str] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True


class BitacoraConsultaFiltros(BaseModel):
    """Filtros para consulta de bitácora"""
    fecha_inicio: Optional[datetime] = Field(None, description="Fecha de inicio del rango")
    fecha_fin: Optional[datetime] = Field(None, description="Fecha de fin del rango")
    tipo_accion_id: Optional[int] = Field(None, description="Filtrar por tipo de acción", ge=1, le=8)
    limite: int = Field(100, description="Número máximo de registros", ge=1, le=500)


class EstadisticasBitacora(BaseModel):
    """Estadísticas de bitácora"""
    total_acciones: int = Field(..., description="Total de acciones registradas")
    acciones_por_tipo: Dict[str, int] = Field(..., description="Conteo de acciones por tipo")
    usuarios_activos: int = Field(..., description="Número de usuarios con actividad")
    fecha_primera_accion: Optional[datetime] = Field(None, description="Fecha de la primera acción registrada")
    fecha_ultima_accion: Optional[datetime] = Field(None, description="Fecha de la última acción registrada")
