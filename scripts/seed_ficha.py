import sys, os, uuid
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.cfg_database import SessionLocal


def run():
    db = SessionLocal()
    try:
        ya = db.execute(text("SELECT COUNT(*) FROM clientes_creditos")).scalar()
        if ya and ya > 0:
            print("seed_ficha ya aplicado (clientes_creditos tiene datos). Nada que hacer.")
            return

        negocios = {
            "44455667": ("Bodega", "Bodega Maria", 48, "DUDOSO"),
            "41112233": ("Comercio", "Ferreteria Jose", 72, "NORMAL"),
            "42778899": ("Servicios", "Salon Rosa", 36, "CPP"),
            "43223344": ("Produccion", "Panaderia Pedro", 12, "NORMAL"),
            "40556677": ("Comercio", "Abarrotes Lucia", 60, "NORMAL"),
        }
        for doc, (tipo, nombre, ant, sbs) in negocios.items():
            db.execute(
                text(
                    """UPDATE clientes SET tipo_negocio=:t, nombre_negocio=:n,
                       antiguedad_negocio_meses=:a, calificacion_sbs=:s,
                       direccion=COALESCE(direccion,'Av. Los Andes 123')
                       WHERE numero_documento=:doc"""
                ),
                {"t": tipo, "n": nombre, "a": ant, "s": sbs, "doc": doc},
            )

        clientes = db.execute(
            text("SELECT id, numero_documento FROM clientes")
        ).mappings().all()
        idx = {c["numero_documento"]: str(c["id"]) for c in clientes}

        hoy = date.today()
        creditos = [
            ("44455667", "Microcredito", 10000, 6200, "activo", 42.5),
            ("44455667", "Microcredito", 5000, 0,    "pagado", 39.0),
            ("41112233", "Microcredito", 15000, 9000, "activo", 38.0),
            ("42778899", "Consumo",      6000, 3500,  "activo", 45.0),
            ("40556677", "Microcredito", 8000, 0,     "pagado", 40.0),
        ]
        for i, (doc, prod, original, pendiente, estado, tea) in enumerate(creditos):
            cid = idx.get(doc)
            if not cid:
                continue
            db.execute(
                text(
                    """INSERT INTO clientes_creditos
                       (id, cliente_id, producto, nombre_producto, monto_original,
                        monto_pendiente, cuota_mensual, proxima_fecha_pago,
                        tea_referencial, tea, progreso_pago, estado, activo, fecha_desembolso)
                       VALUES (:id,:cli,:prod,:prod,:original,:pend,:cuota,:prox,
                               :tea,:tea,0,:est,:act,:fec)"""
                ),
                {
                    "id": str(uuid.uuid4()),
                    "cli": cid,
                    "prod": prod,
                    "original": original,
                    "pend": pendiente,
                    "cuota": round(original / 12, 2),
                    "prox": hoy + timedelta(days=30),
                    "tea": tea,
                    "est": "activo" if estado == "activo" else "pagado",
                    "act": True if estado == "activo" else False,
                    "fec": hoy - timedelta(days=300 - i * 20),
                },
            )

        jose = idx.get("41112233")
        if jose:
            db.execute(
                text(
                    """INSERT INTO creditos_preaprobados
                       (id, cliente_id, monto_maximo, plazo_sugerido_meses,
                        tea_referencial, score_confianza, vigente, fecha_calculo, fecha_vencimiento)
                       VALUES (:id,:cli,:monto,:plazo,:tea,:score,TRUE,:fc,:fv)"""
                ),
                {
                    "id": str(uuid.uuid4()),
                    "cli": jose,
                    "monto": 20000,
                    "plazo": 24,
                    "tea": 36.0,
                    "score": 82,
                    "fc": hoy,
                    "fv": hoy + timedelta(days=30),
                },
            )

        db.commit()
        print("seed_ficha OK: creditos historicos + oferta preaprobada creados.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
