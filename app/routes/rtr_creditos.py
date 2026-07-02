from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.cfg_database import get_db
from app.core.cfg_auth import get_current_asesor

router = APIRouter()


@router.get("/{credito_id}/cronograma")
def cronograma(
    credito_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    row = db.execute(
        text(
            "SELECT id FROM clientes_creditos WHERE id = :id"
        ),
        {"id": credito_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Credito no encontrado")

    cuotas = db.execute(
        text(
            """
            SELECT id, credito_id, numero_cuota, fecha_vencimiento,
                   monto, estado, fecha_pago
            FROM clientes_cronograma_pagos
            WHERE credito_id = :cid
            ORDER BY numero_cuota ASC
            """
        ),
        {"cid": credito_id},
    ).mappings().all()

    return [
        {
            "id": str(c["id"]),
            "credito_id": str(c["credito_id"]),
            "numero_cuota": c["numero_cuota"],
            "fecha_vencimiento": c["fecha_vencimiento"].isoformat() if c["fecha_vencimiento"] else None,
            "monto": float(c["monto"] or 0),
            "capital": 0,
            "interes": 0,
            "saldo": 0,
            "estado": c["estado"],
            "fecha_pago": c["fecha_pago"].isoformat() if c["fecha_pago"] else None,
        }
        for c in cuotas
    ]
