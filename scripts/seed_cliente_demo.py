import sys, os
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.cfg_database import SessionLocal
from app.core.cfg_security import hash_password
from app.models.mdl_asesores import Agencia, Asesor
from app.models.mdl_clientes import Cliente
from app.models.mdl_cliente_mobile import (
    UsuarioCliente, ClientesCuenta, ClientesCredito, ClientesCronogramaPago,
    ClientesMovimiento, Tarjeta, Notificacion,
)

DNI = "12345678"


def run():
    db = SessionLocal()
    try:
        if db.query(UsuarioCliente).filter(UsuarioCliente.username == DNI).first():
            print(f"El seed de cliente ya fue aplicado (DNI {DNI} existe). Nada que hacer.")
            return

        cliente = db.query(Cliente).filter(Cliente.numero_documento == DNI).first()
        if not cliente:
            cliente = Cliente(
                cod_cliente="C0001",
                numero_documento=DNI,
                tipo_documento="DNI",
                nombres="Guillermo Eduardo",
                apellidos="Peña Garcia",
                telefono="999993868",
                email="nag@pucp.edu.pe",
                tipo_negocio="bodega",
                nombre_negocio="Bodega Independencia",
                ingresos_estimados=11032.62,
            )
            db.add(cliente)
            db.flush()

        db.add(UsuarioCliente(
            cliente_id=cliente.id,
            username=DNI,
            password_hash=hash_password("1234"),
            activo=True,
        ))

        db.add(ClientesCuenta(
            cliente_id=cliente.id,
            tipo_cuenta="Cuenta Independencia Andino",
            moneda="PEN",
            saldo=24.64,
            saldo_disponible=24.64,
            saldo_contable=24.64,
            es_principal=True,
            estado="activa",
        ))

        credito = ClientesCredito(
            cliente_id=cliente.id,
            producto="Crédito Consumo",
            nombre_producto="Crédito Consumo",
            monto_original=102122.43,
            monto_pendiente=68238.06,
            cuota_mensual=1999.96,
            tea_referencial=18.50,
            tea=18.50,
            progreso_pago=30,
            estado="activo",
            activo=True,
            fecha_desembolso=date(2023, 10, 10),
        )
        db.add(credito)
        db.flush()

        cuota_total = 1999.96
        saldo = 69562.15
        for nro in range(29, 39):
            saldo = round(saldo - 1324.09, 2)
            pagada = nro <= 30
            db.add(ClientesCronogramaPago(
                credito_id=credito.id,
                cliente_id=cliente.id,
                numero_cuota=nro,
                fecha_vencimiento=date(2026, 3 + (nro - 29), 10) if (3 + (nro - 29)) <= 12
                else date(2027, (3 + (nro - 29)) - 12, 10),
                monto=cuota_total,
                estado="pagada" if pagada else "pendiente",
                fecha_pago=date(2026, 1 + (nro - 29), 8) if pagada else None,
            ))

        movs = [
            ("Abono inmediato 808 guillermo",     "Crédito", 106.00, True,  datetime(2026, 4, 30, 9, 5, tzinfo=timezone.utc)),
            ("Transf inmediata al 808 852979",    "Crédito", 160.00, False, datetime(2026, 4, 29, 18, 20, tzinfo=timezone.utc)),
            ("Electrocentro",                      "Crédito", 55.90,  False, datetime(2026, 4, 28, 11, 0, tzinfo=timezone.utc)),
            ("Movistar cuenta financiera",        "Crédito", 83.90,  False, datetime(2026, 4, 28, 10, 45, tzinfo=timezone.utc)),
            ("Movistar movil",                     "Crédito", 39.90,  False, datetime(2026, 4, 28, 10, 30, tzinfo=timezone.utc)),
            ("ITF",                                "Crédito", 0.15,   False, datetime(2026, 4, 27, 9, 0, tzinfo=timezone.utc)),
            ("Yape Pena Garcia",                   "Crédito", 150.00, True,  datetime(2026, 4, 18, 14, 10, tzinfo=timezone.utc)),
        ]
        for desc, cat, monto, abono, fecha in movs:
            db.add(ClientesMovimiento(
                cliente_id=cliente.id,
                descripcion=desc,
                categoria=cat,
                monto=monto,
                es_abono=abono,
                fecha=fecha,
            ))

        db.add(Tarjeta(
            cliente_id=cliente.id,
            numero_enmascarado="**** **** **** 1649",
            marca="visa",
            linea_credito=5000.00,
            saldo_utilizado=0.00,
            fecha_corte=date(2026, 5, 18),
            fecha_pago=date(2026, 6, 5),
            estado="apagada",
        ))

        notifs = [
            ("Compra con tarjeta", "Consumo Claude.ai por S/ 72.57 (pendiente de procesar).", "compra"),
            ("Recordatorio de pago", "Tu cuota 31 de 72 vence el 10 may 2026 por S/ 1,999.96.", "recordatorio"),
            ("Oferta para ti", "Depósito a plazo hasta 3.85% TREA a 6 meses. ¡Haz crecer tus ahorros!", "oferta"),
        ]
        for titulo, cuerpo, tipo in notifs:
            db.add(Notificacion(
                destinatario_tipo="cliente",
                cliente_id=cliente.id,
                titulo=titulo,
                cuerpo=cuerpo,
                tipo=tipo,
                leida=False,
            ))

        db.commit()
        print(f"Seed cliente OK. Login en la app:  DNI={DNI}  password=1234")
    finally:
        db.close()


if __name__ == "__main__":
    run()
