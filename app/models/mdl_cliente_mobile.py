import uuid
from sqlalchemy import (
    Column, String, Boolean, Integer, Numeric, Date, DateTime, Text, ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.cfg_database import Base


class UsuarioCliente(Base):
    __tablename__ = "usuarios_cliente"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id        = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False, unique=True)
    username          = Column(String(50), unique=True, nullable=False)
    password_hash     = Column(Text, nullable=False)
    token_fcm         = Column(Text)
    activo            = Column(Boolean, nullable=False, default=True)
    bloqueado         = Column(Boolean, nullable=False, default=False)
    intentos_fallidos = Column(Integer, nullable=False, default=0)
    ultimo_acceso     = Column(DateTime(timezone=True))
    created_at        = Column(DateTime(timezone=True), server_default=func.now())


class ClientesCuenta(Base):
    __tablename__ = "clientes_cuentas"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id        = Column(UUID(as_uuid=True), nullable=False)
    tipo_cuenta       = Column(String(40))
    moneda            = Column(String(3), default="PEN")
    saldo             = Column(Numeric(12, 2), default=0)
    saldo_disponible  = Column(Numeric(12, 2), default=0)
    saldo_contable    = Column(Numeric(12, 2), default=0)
    es_principal      = Column(Boolean, default=False)
    estado            = Column(String(20), default="activa")
    created_at        = Column(DateTime(timezone=True), server_default=func.now())


class ClientesCredito(Base):
    __tablename__ = "clientes_creditos"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id         = Column(UUID(as_uuid=True), nullable=False)
    producto           = Column(String(40))
    nombre_producto    = Column(String(100))
    monto_original     = Column(Numeric(12, 2))
    monto_pendiente    = Column(Numeric(12, 2))
    cuota_mensual      = Column(Numeric(10, 2))
    proxima_fecha_pago = Column(Date)
    fecha_proximo_pago = Column(Date)
    tea_referencial    = Column(Numeric(5, 2))
    tea                = Column(Numeric(5, 2))
    progreso_pago      = Column(Integer, default=0)
    estado             = Column(String(20), default="activo")
    activo             = Column(Boolean, default=True)
    fecha_desembolso   = Column(Date)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())


class ClientesCronogramaPago(Base):
    __tablename__ = "clientes_cronograma_pagos"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id        = Column(UUID(as_uuid=True), nullable=False)
    credito_id        = Column(UUID(as_uuid=True), ForeignKey("clientes_creditos.id"), nullable=False)
    numero_cuota      = Column(Integer, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    monto             = Column(Numeric(10, 2))
    estado            = Column(String(20), default="pendiente")
    fecha_pago        = Column(Date)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())


class ClientesMovimiento(Base):
    __tablename__ = "clientes_movimientos"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id      = Column(UUID(as_uuid=True), nullable=False)
    cuenta_id       = Column(UUID(as_uuid=True), ForeignKey("clientes_cuentas.id"))
    descripcion     = Column(String(200))
    categoria       = Column(String(40))
    referencia      = Column(String(60))
    monto           = Column(Numeric(12, 2), nullable=False)
    es_abono        = Column(Boolean, default=True)
    fecha           = Column(DateTime(timezone=True), nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())


class Tarjeta(Base):
    __tablename__ = "tarjetas"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id         = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    numero_enmascarado = Column(String(25), nullable=False)
    marca              = Column(String(20))
    linea_credito      = Column(Numeric(12, 2))
    saldo_utilizado    = Column(Numeric(12, 2))
    fecha_corte        = Column(Date)
    fecha_pago         = Column(Date)
    estado             = Column(String(20), default="activa")
    created_at         = Column(DateTime(timezone=True), server_default=func.now())


class ClientesOperacion(Base):
    __tablename__ = "clientes_operaciones"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id       = Column(UUID(as_uuid=True), nullable=False)
    tipo_operacion   = Column(String(30))
    monto            = Column(Numeric(12, 2), nullable=False)
    descripcion      = Column(String(200))
    numero_operacion = Column(String(40))
    estado           = Column(String(20), nullable=False, default="exitosa")
    fecha            = Column(DateTime(timezone=True), nullable=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destinatario_tipo = Column(String(10), nullable=False)
    asesor_id         = Column(UUID(as_uuid=True), ForeignKey("asesores_negocio.id"))
    cliente_id        = Column(UUID(as_uuid=True), ForeignKey("clientes.id"))
    titulo            = Column(String(120), nullable=False)
    cuerpo            = Column(Text)
    tipo              = Column(String(40))
    data_json         = Column(JSONB)
    leida             = Column(Boolean, nullable=False, default=False)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
