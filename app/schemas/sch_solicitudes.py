from pydantic import BaseModel
from typing import Optional


class SolicitudIn(BaseModel):
    # Solicitante / negocio
    numero_documento: str
    nombres: str = ""
    apellidos: str = ""
    telefono: Optional[str] = None
    tipo_negocio: Optional[str] = None
    nombre_negocio: Optional[str] = None
    ingresos_estimados: Optional[float] = None
    # Condiciones
    monto_solicitado: float
    plazo_meses: int
    moneda: str = "PEN"
    tipo_cuota: str = "mensual"
    garantia: str = "sin_garantia"
    destino_credito: Optional[str] = None
    cuota_estimada: Optional[float] = None
    tea_referencial: Optional[float] = None
    firma_cliente_base64: Optional[str] = None


class SolicitudCreada(BaseModel):
    id: str
    numero_expediente: str
    estado: str


class SolicitudResumen(BaseModel):
    id: str
    numero_expediente: str
    cliente_nombre: str
    monto_solicitado: float
    monto_aprobado: float
    estado: str
    created_at: Optional[str] = None


class CondicionarSolicitudIn(BaseModel):
    monto_aprobado: float
    condicion: str


class RechazarSolicitudIn(BaseModel):
    motivo: str


class SolicitudDetalleOut(BaseModel):
    id: str
    numero_expediente: str
    asesor_id: Optional[str] = None
    cliente_id: str
    solicitante_documento: Optional[str] = None
    solicitante_nombre: Optional[str] = None
    solicitante_telefono: Optional[str] = None
    monto_solicitado: float
    monto_aprobado: Optional[float] = None
    plazo_meses: int
    cuota_estimada: Optional[float] = None
    tea_referencial: Optional[float] = None
    ingresos_estimados: Optional[float] = None
    score_pre_evaluacion: Optional[int] = None
    elegibilidad: Optional[str] = None
    ratio_capacidad_pago: Optional[float] = None
    riesgo_asignado: Optional[str] = None
    motivo_pre_evaluacion: Optional[str] = None
    condicion_adicional: Optional[str] = None
    motivo_rechazo: Optional[str] = None
    estado: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    fecha_decision: Optional[str] = None
