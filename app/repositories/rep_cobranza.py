from datetime import datetime, timezone
import uuid
from sqlalchemy import text
from sqlalchemy.orm import Session


def listar_mora(db: Session) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT cr.id, cr.id AS cod_cuenta_credito, cr.cliente_id, 0 AS dias_mora,
                   cr.monto_pendiente, c.nombres, c.apellidos, c.numero_documento,
                   c.telefono
            FROM clientes_creditos cr
            JOIN clientes c ON c.id = cr.cliente_id
            WHERE cr.estado = 'activo' AND cr.monto_pendiente > 0
            ORDER BY cr.monto_pendiente DESC
            """
        )
    ).mappings().all()
    return [
        {
            "id": str(r["id"]),
            "cod_cuenta_credito": str(r["cod_cuenta_credito"]),
            "cliente_id": str(r["cliente_id"]),
            "cliente_nombre": f"{r['nombres']} {r['apellidos']}",
            "documento": r["numero_documento"],
            "telefono": r["telefono"],
            "dias_mora": r["dias_mora"],
            "monto_vencido": float(r["monto_pendiente"] or 0),
        }
        for r in rows
    ]


def registrar_accion(db: Session, asesor_id: str, d: dict) -> None:
    db.execute(
        text(
            """
            INSERT INTO acciones_cobranza
              (id, asesor_id, cliente_id, cod_cuenta_credito, tipo_gestion,
               resultado, monto_pagado, fecha_compromiso, monto_compromiso,
               observaciones, lat, lng, timestamp_gestion)
            VALUES (:id,:asesor,:cli,:cod,:tipo,:res,:mp,:fc,:mc,:obs,:lat,:lng,:ts)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "asesor": asesor_id,
            "cli": d["cliente_id"],
            "cod": d.get("cod_cuenta_credito"),
            "tipo": d["tipo_gestion"],
            "res": d["resultado"],
            "mp": d.get("monto_pagado"),
            "fc": d.get("fecha_compromiso"),
            "mc": d.get("monto_compromiso"),
            "obs": d.get("observaciones", ""),
            "lat": d.get("lat"),
            "lng": d.get("lng"),
            "ts": datetime.now(timezone.utc),
        },
    )
    db.commit()
