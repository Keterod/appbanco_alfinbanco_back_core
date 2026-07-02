from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.cfg_database import get_db
from app.core.cfg_auth import get_current_asesor
from app.schemas.sch_solicitudes import (
    SolicitudIn, SolicitudCreada,
    CondicionarSolicitudIn, RechazarSolicitudIn,
)
from app.repositories import rep_solicitudes
from app.services import svc_desembolso

router = APIRouter()


class NotaIn(BaseModel):
    contenido: str


class NotaOut(BaseModel):
    contenido: str
    created_at: str | None = None


@router.post("", response_model=SolicitudCreada)
def crear_solicitud(
    data: SolicitudIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Registra una solicitud de credito (M5 / HU-17)."""
    return rep_solicitudes.crear(
        db, asesor["asesor_id"], asesor.get("agencia_id"), data.model_dump()
    )


@router.get("")
def listar_solicitudes(
    request: Request,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Historial de solicitudes del mes (HU-20) y tablero de estado (M9)."""
    # --- DEBUG temporal: contexto de la peticion ---
    print(f"[DEBUG GET /solicitudes] URL: {request.url}")
    print(f"[DEBUG GET /solicitudes] Origen (client): {request.client}")

    masked_headers = {}
    for key, value in request.headers.items():
        if isinstance(value, str) and value.count(".") == 2 and len(value) > 12:
            # Valor suelto con forma de JWT
            masked_headers[key] = f"{value[:4]}...{value[-4:]}"
        elif (
            isinstance(value, str)
            and key.lower() == "authorization"
            and len(value) > 12
        ):
            parts = value.split(" ", 1)
            if len(parts) == 2 and parts[1].count(".") == 2:
                token = parts[1]
                masked_headers[key] = f"{parts[0]} {token[:4]}...{token[-4:]}"
            else:
                masked_headers[key] = f"{value[:4]}...{value[-4:]}"
        else:
            masked_headers[key] = value
    print(f"[DEBUG GET /solicitudes] Headers: {masked_headers}")

    # --- DEBUG temporal: contexto de la base de datos ---
    sa_url = db.bind.url
    db_url_str = str(sa_url)
    if sa_url.username:
        db_url_str = db_url_str.replace(sa_url.username, "****")
    if sa_url.password:
        db_url_str = db_url_str.replace(sa_url.password, "****")
    print(f"[DEBUG GET /solicitudes] DATABASE_URL: {db_url_str}")

    row_db_schema = db.execute(text("SELECT current_database(), current_schema();")).fetchone()
    print(f"[DEBUG GET /solicitudes] current_database/current_schema: {tuple(row_db_schema)}")

    row_count = db.execute(text("SELECT COUNT(*) FROM solicitudes_credito;")).fetchone()
    print(f"[DEBUG GET /solicitudes] COUNT(solicitudes_credito): {row_count[0]}")

    print(f"[DEBUG GET /solicitudes] asesor_id del JWT: {asesor.get('asesor_id')}")
    print(f"[DEBUG GET /solicitudes] perfil del JWT: {asesor.get('perfil')}")
    return rep_solicitudes.listar(db, asesor["asesor_id"])


@router.get("/{solicitud_id}")
def obtener_solicitud(
    solicitud_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Detalle completo de una solicitud."""
    solicitud = rep_solicitudes.obtener(db, solicitud_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return solicitud


@router.post("/{solicitud_id}/reclamar")
def reclamar_solicitud(
    solicitud_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Reclama el expediente: asigna asesor actual si aun no tiene."""
    result = rep_solicitudes.reclamar(db, solicitud_id, asesor["asesor_id"])
    if result is None:
        estado, asesor_actual = rep_solicitudes.verificar_asesor(db, solicitud_id, asesor["asesor_id"])
        if estado == "not_found":
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        raise HTTPException(
            status_code=409,
            detail=f"La solicitud ya fue reclamada por otro asesor",
        )
    return result


@router.post("/{solicitud_id}/aprobar")
def aprobar_solicitud(
    solicitud_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Aprueba la solicitud."""
    result = rep_solicitudes.aprobar(db, solicitud_id, asesor["asesor_id"])
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if result.get("error") == "conflict":
        raise HTTPException(status_code=409, detail="La solicitud pertenece a otro asesor")
    return result


@router.post("/{solicitud_id}/condicionar")
def condicionar_solicitud(
    solicitud_id: str,
    data: CondicionarSolicitudIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Condiciona la solicitud con monto aprobado menor."""
    if data.monto_aprobado <= 0:
        raise HTTPException(status_code=422, detail="monto_aprobado debe ser mayor a 0")
    if not data.condicion.strip():
        raise HTTPException(status_code=422, detail="condicion no puede estar vacia")
    result = rep_solicitudes.condicionar(db, solicitud_id, asesor["asesor_id"], data.monto_aprobado, data.condicion)
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if result.get("error") == "conflict":
        raise HTTPException(status_code=409, detail="La solicitud pertenece a otro asesor")
    if result.get("error") == "invalid_monto":
        raise HTTPException(status_code=422, detail="monto_aprobado debe ser menor al monto_solicitado")
    return result


@router.post("/{solicitud_id}/rechazar")
def rechazar_solicitud(
    solicitud_id: str,
    data: RechazarSolicitudIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Rechaza la solicitud con motivo."""
    if not data.motivo.strip():
        raise HTTPException(status_code=422, detail="motivo no puede estar vacio")
    result = rep_solicitudes.rechazar(db, solicitud_id, asesor["asesor_id"], data.motivo)
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if result.get("error") == "conflict":
        raise HTTPException(status_code=409, detail="La solicitud pertenece a otro asesor")
    return result


@router.post("/{solicitud_id}/desembolsar")
def desembolsar_solicitud(
    solicitud_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Desembolsa la solicitud: crea credito, cronograma, movimiento, operacion y actualiza saldo."""
    result = svc_desembolso.desembolsar(db, solicitud_id, asesor["asesor_id"])
    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if result.get("error") == "conflict":
        raise HTTPException(status_code=409, detail="La solicitud pertenece a otro asesor")
    if result.get("error") == "invalid_state":
        raise HTTPException(status_code=422, detail=result["detail"])
    if result.get("error") == "duplicate":
        raise HTTPException(status_code=409, detail=result["detail"])
    if result.get("error") == "invalid_monto":
        raise HTTPException(status_code=422, detail=result["detail"])
    return result


@router.post("/{solicitud_id}/notas")
def agregar_nota(
    solicitud_id: str,
    data: NotaIn,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Agrega una nota interna a la solicitud (RF-72)."""
    return rep_solicitudes.agregar_nota(
        db, solicitud_id, asesor["asesor_id"], data.contenido
    )


@router.get("/{solicitud_id}/notas", response_model=list[NotaOut])
def listar_notas(
    solicitud_id: str,
    db: Session = Depends(get_db),
    asesor: dict = Depends(get_current_asesor),
):
    """Notas internas de la solicitud (RF-72)."""
    return rep_solicitudes.listar_notas(db, solicitud_id)
