from sqlalchemy.orm import Session
from app.models.mdl_clientes import Cliente
from app.models.mdl_cliente_mobile import (
    UsuarioCliente, ClientesCuenta, ClientesCredito, ClientesCronogramaPago,
    ClientesMovimiento, Tarjeta, ClientesOperacion, Notificacion,
)


def get_usuario_by_username(db: Session, username: str) -> UsuarioCliente | None:
    return db.query(UsuarioCliente).filter(
        UsuarioCliente.username == username
    ).first()


def get_cliente(db: Session, cliente_id: str) -> Cliente | None:
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()


def cuentas_ahorro(db: Session, cliente_id: str) -> list[ClientesCuenta]:
    return db.query(ClientesCuenta).filter(
        ClientesCuenta.cliente_id == cliente_id
    ).order_by(ClientesCuenta.created_at.asc()).all()


def creditos(db: Session, cliente_id: str) -> list[ClientesCredito]:
    return db.query(ClientesCredito).filter(
        ClientesCredito.cliente_id == cliente_id
    ).order_by(ClientesCredito.fecha_desembolso.desc().nullslast()).all()


def cronograma(db: Session, credito_id: str) -> list[ClientesCronogramaPago]:
    return db.query(ClientesCronogramaPago).filter(
        ClientesCronogramaPago.credito_id == credito_id
    ).order_by(ClientesCronogramaPago.numero_cuota.asc()).all()


def movimientos(db: Session, cliente_id: str, limit: int = 20) -> list[ClientesMovimiento]:
    return db.query(ClientesMovimiento).filter(
        ClientesMovimiento.cliente_id == cliente_id
    ).order_by(ClientesMovimiento.fecha.desc()).limit(limit).all()


def tarjetas(db: Session, cliente_id: str) -> list[Tarjeta]:
    return db.query(Tarjeta).filter(
        Tarjeta.cliente_id == cliente_id
    ).order_by(Tarjeta.created_at.asc()).all()


def notificaciones(db: Session, cliente_id: str, limit: int = 30) -> list[Notificacion]:
    return db.query(Notificacion).filter(
        Notificacion.destinatario_tipo == "cliente",
        Notificacion.cliente_id == cliente_id,
    ).order_by(Notificacion.created_at.desc()).limit(limit).all()


def crear_operacion(db: Session, cliente_id: str, data: dict) -> ClientesOperacion:
    op = ClientesOperacion(
        cliente_id=cliente_id,
        tipo_operacion=data.get("tipo", "OPERACION"),
        monto=data.get("monto", 0),
        descripcion=data.get("descripcion", ""),
        numero_operacion=data.get("numero_operacion"),
        estado="pendiente",
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    return op
