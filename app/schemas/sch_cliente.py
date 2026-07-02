from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class LoginClienteIn(BaseModel):
    numero_documento: str
    password: str


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cod_cliente: str | None = None
    numero_documento: str
    nombres: str
    apellidos: str
    email: str | None = None
    telefono: str | None = None


class TokenClienteOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    cliente: ClienteOut


class CuentaAhorroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tipo_cuenta: str | None = None
    moneda: str | None = None
    saldo: float | None = None
    saldo_disponible: float | None = None
    saldo_contable: float | None = None
    es_principal: bool | None = None
    estado: str | None = None


class CreditoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    producto: str | None = None
    nombre_producto: str | None = None
    monto_original: float | None = None
    monto_pendiente: float | None = None
    cuota_mensual: float | None = None
    proxima_fecha_pago: date | None = None
    tea_referencial: float | None = None
    tea: float | None = None
    estado: str | None = None
    activo: bool | None = None
    fecha_desembolso: date | None = None


class CuotaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    credito_id: UUID
    numero_cuota: int
    fecha_vencimiento: date
    monto: float | None = None
    estado: str | None = None
    fecha_pago: date | None = None


class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cuenta_id: UUID | None = None
    descripcion: str | None = None
    categoria: str | None = None
    referencia: str | None = None
    monto: float
    es_abono: bool | None = None
    fecha: datetime


class TarjetaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    numero_enmascarado: str
    marca: str | None = None
    linea_credito: float | None = None
    saldo_utilizado: float | None = None
    fecha_corte: date | None = None
    fecha_pago: date | None = None
    estado: str | None = None


class NotificacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    titulo: str
    cuerpo: str | None = None
    tipo: str | None = None
    leida: bool = False
    created_at: datetime


class OperacionIn(BaseModel):
    cod_cuenta_origen: str | None = None
    cod_cuenta_destino: str | None = None
    tipo: str = "OPERACION"
    monto: float
    moneda: str = "PEN"


class OperacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tipo_operacion: str | None = None
    monto: float
    descripcion: str | None = None
    numero_operacion: str | None = None
    estado: str
    created_at: datetime
