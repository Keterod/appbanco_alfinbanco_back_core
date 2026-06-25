from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.cfg_database import get_db
from app.core.cfg_auth import get_current_asesor
from app.repositories import rep_dashboard

router = APIRouter()


@router.get("/resumen")
def resumen(
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Resumen del dashboard para el asesor autenticado."""
    return rep_dashboard.resumen(db, asesor["asesor_id"])
