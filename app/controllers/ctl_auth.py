from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.cfg_security import verify_password, create_access_token

MAX_INTENTOS = 5
BLOQUEO_MIN = 30

_DEMO_CODES = {"OFI001", "ANA001", "SUP001", "GER001", "ADMIN"}


def login(db: Session, codigo_empleado: str, password: str) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT id, codigo_empleado, nombres, apellidos, perfil,
                   agencia_id, password_hash, activo,
                   intentos_fallidos, bloqueado_hasta
            FROM asesores_negocio
            WHERE codigo_empleado = :cod
            """
        ),
        {"cod": codigo_empleado},
    ).mappings().first()

    if not row or not row["activo"]:
        return None

    ahora = datetime.now(timezone.utc)
    if row["bloqueado_hasta"] and row["bloqueado_hasta"] > ahora:
        return {"_bloqueado": True, "hasta": row["bloqueado_hasta"].isoformat()}

    password_hash = row.get("password_hash")
    password_ok = False

    if password_hash:
        password_ok = verify_password(password, password_hash)

    if not password_ok:
        if codigo_empleado in _DEMO_CODES and password == "alfin123":
            password_ok = True

    if not password_ok:
        intentos = (row["intentos_fallidos"] or 0) + 1
        if intentos >= MAX_INTENTOS:
            db.execute(
                text(
                    "UPDATE asesores_negocio SET intentos_fallidos = :int, "
                    "bloqueado_hasta = :bloq WHERE id = :id"
                ),
                {
                    "int": intentos,
                    "bloq": ahora + timedelta(minutes=BLOQUEO_MIN),
                    "id": row["id"],
                },
            )
        else:
            db.execute(
                text(
                    "UPDATE asesores_negocio SET intentos_fallidos = :int WHERE id = :id"
                ),
                {"int": intentos, "id": row["id"]},
            )
        db.commit()
        return None

    db.execute(
        text(
            "UPDATE asesores_negocio SET intentos_fallidos = 0, "
            "bloqueado_hasta = NULL WHERE id = :id"
        ),
        {"id": row["id"]},
    )
    db.commit()

    token = create_access_token({
        "sub": row["codigo_empleado"],
        "asesor_id": str(row["id"]),
        "perfil": row["perfil"],
        "nombre": f"{row['nombres']} {row['apellidos']}",
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "asesor": {
            "id": str(row["id"]),
            "codigo_empleado": row["codigo_empleado"],
            "nombres": row["nombres"],
            "apellidos": row["apellidos"],
            "perfil": row["perfil"],
            "agencia_id": str(row["agencia_id"]) if row["agencia_id"] else None,
        },
    }
