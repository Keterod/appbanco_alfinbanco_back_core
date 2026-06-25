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
    """Cronograma de pagos de un credito. Acepta id o cod_cuenta_credito."""
    row = db.execute(
        text(
            "SELECT id, cod_cuenta_credito FROM cr_creditos WHERE id = :id OR cod_cuenta_credito = :id"
        ),
        {"id": credito_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Credito no encontrado")

    cod = row["cod_cuenta_credito"]
    cuotas = db.execute(
        text(
            """
            SELECT id, cod_cuenta_credito, nro_cuota, fecha_vencimiento,
                   monto_cuota, monto_capital, monto_interes, saldo,
                   estado_cuota, fecha_pago
            FROM cr_cronograma_pagos
            WHERE cod_cuenta_credito = :cod
            ORDER BY nro_cuota ASC
            """
        ),
        {"cod": cod},
    ).mappings().all()

    return [
        {
            "id": str(c["id"]),
            "credito_id": cod,
            "numero_cuota": c["nro_cuota"],
            "fecha_vencimiento": c["fecha_vencimiento"].isoformat() if c["fecha_vencimiento"] else None,
            "monto": float(c["monto_cuota"] or 0),
            "capital": float(c["monto_capital"] or 0),
            "interes": float(c["monto_interes"] or 0),
            "saldo": float(c["saldo"] or 0),
            "estado": c["estado_cuota"],
            "fecha_pago": c["fecha_pago"].isoformat() if c["fecha_pago"] else None,
        }
        for c in cuotas
    ]
