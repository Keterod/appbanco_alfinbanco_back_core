from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.cfg_database import get_db
from app.core.cfg_auth import get_current_asesor
from app.schemas.sch_auth import LoginIn, TokenOut
from app.controllers import ctl_auth
from app.repositories import rep_asesores

router = APIRouter()

@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    result = ctl_auth.login(db, data.codigo_empleado, data.password)
    if result and result.get("_bloqueado"):
        raise HTTPException(
            status_code=423,
            detail=f"Cuenta bloqueada por intentos fallidos hasta {result['hasta']}",
        )
    if not result:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    return result


@router.get("/me")
def me(
    db: Session = Depends(get_db),
    current_asesor: dict = Depends(get_current_asesor),
):
    asesor = rep_asesores.get_by_id(db, current_asesor["asesor_id"])
    if not asesor:
        raise HTTPException(status_code=404, detail="Asesor no encontrado")
    return {
        "asesor": {
            "id": str(asesor.id),
            "codigo_empleado": asesor.codigo_empleado,
            "nombres": asesor.nombres,
            "apellidos": asesor.apellidos,
            "perfil": asesor.perfil,
            "agencia_id": str(asesor.agencia_id) if asesor.agencia_id else None,
        }
    }
