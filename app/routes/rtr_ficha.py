from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.cfg_database import get_db
from app.core.cfg_auth import get_current_asesor
from app.schemas.sch_ficha import FichaOut, UbicacionIn
from app.repositories import rep_ficha

router = APIRouter()


@router.get("/{cliente_id}/ficha", response_model=FichaOut)
def ficha_cliente(
    cliente_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Ficha completa del cliente (M3 / HU-11)."""
    ficha = rep_ficha.obtener_ficha(db, cliente_id)
    if ficha is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return ficha


@router.get("/{cliente_id}/creditos")
def creditos_cliente(
    cliente_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Creditos del cliente."""
    rows = db.execute(
        text(
            """
            SELECT cr.id, cr.cod_cuenta_credito, cr.cliente_id, cr.producto,
                   cr.monto_desembolsado, cr.saldo_capital, cr.saldo_total,
                   cr.estado, cr.fecha_desembolso, cr.tea, cr.cuotas_total,
                   cr.cuotas_pagadas, cr.created_at,
                   (SELECT cg.monto_cuota FROM cr_cronograma_pagos cg
                    WHERE cg.cod_cuenta_credito = cr.cod_cuenta_credito
                      AND cg.estado_cuota = 'pendiente'
                    ORDER BY cg.nro_cuota ASC LIMIT 1) AS cuota_mensual,
                   (SELECT cg.fecha_vencimiento FROM cr_cronograma_pagos cg
                    WHERE cg.cod_cuenta_credito = cr.cod_cuenta_credito
                      AND cg.estado_cuota = 'pendiente'
                    ORDER BY cg.nro_cuota ASC LIMIT 1) AS proxima_fecha_pago
            FROM cr_creditos cr
            WHERE cr.cliente_id = :cid
            ORDER BY cr.fecha_desembolso DESC
            """
        ),
        {"cid": cliente_id},
    ).mappings().all()

    return [
        {
            "id": str(r["id"]),
            "cliente_id": str(r["cliente_id"]),
            "producto": r["producto"],
            "nombre_producto": r["producto"],
            "monto_original": float(r["monto_desembolsado"] or 0),
            "monto_pendiente": float(r["saldo_capital"] or r["saldo_total"] or 0),
            "cuota_mensual": float(r["cuota_mensual"] or 0),
            "proxima_fecha_pago": r["proxima_fecha_pago"].isoformat() if r["proxima_fecha_pago"] else None,
            "fecha_proximo_pago": r["proxima_fecha_pago"].isoformat() if r["proxima_fecha_pago"] else None,
            "tea": float(r["tea"] or 0),
            "tea_referencial": float(r["tea"] or 0),
            "estado": "activo" if r["estado"] == "vigente" else (r["estado"] or "desconocido"),
            "activo": r["estado"] == "vigente",
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


@router.post("/{cliente_id}/ubicacion")
def actualizar_ubicacion(
    cliente_id: str,
    body: UbicacionIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Actualiza las coordenadas del negocio del cliente (HU-10 / RF-25/26)."""
    ok = rep_ficha.actualizar_ubicacion(
        db, cliente_id, body.lat, body.lng, body.direccion
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"ok": True, "lat": body.lat, "lng": body.lng}
