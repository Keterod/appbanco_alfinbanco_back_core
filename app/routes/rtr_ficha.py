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
    rows = db.execute(
        text(
            """
            SELECT cr.id, cr.cliente_id, cr.producto, cr.nombre_producto,
                   cr.monto_original, cr.monto_pendiente, cr.cuota_mensual,
                   cr.proxima_fecha_pago, cr.fecha_proximo_pago,
                   cr.tea_referencial, cr.tea, cr.progreso_pago,
                   cr.estado, cr.activo, cr.fecha_desembolso, cr.created_at
            FROM clientes_creditos cr
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
            "nombre_producto": r["nombre_producto"] or r["producto"],
            "monto_original": float(r["monto_original"] or 0),
            "monto_pendiente": float(r["monto_pendiente"] or 0),
            "cuota_mensual": float(r["cuota_mensual"] or 0),
            "proxima_fecha_pago": r["proxima_fecha_pago"].isoformat() if r["proxima_fecha_pago"] else None,
            "fecha_proximo_pago": r["fecha_proximo_pago"].isoformat() if r["fecha_proximo_pago"] else None,
            "tea": float(r["tea"] or 0),
            "tea_referencial": float(r["tea_referencial"] or 0),
            "estado": "activo" if r["activo"] else (r["estado"] or "desconocido"),
            "activo": bool(r["activo"]),
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
    ok = rep_ficha.actualizar_ubicacion(
        db, cliente_id, body.lat, body.lng, body.direccion
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"ok": True, "lat": body.lat, "lng": body.lng}
