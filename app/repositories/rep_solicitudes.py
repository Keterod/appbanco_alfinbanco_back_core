import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session


def normalizar_estado(valor):
    if not valor:
        return "enviada"
    v = str(valor).strip()
    mapa = {
        "enviado": "enviada",
        "en_evaluacion": "enviada",
        "aprobado": "aprobada",
        "condicionado": "condicionada",
        "rechazado": "rechazada",
        "desembolsado": "desembolsada",
    }
    return mapa.get(v, v)


def normalizar_elegibilidad(valor):
    if not valor:
        return None
    v = str(valor).strip().upper()
    mapa = {
        "OBSERVADO": "CONDICIONADO",
        "REVISAR": "CONDICIONADO",
        "NO_PROCEDE": "NO APTO",
        "NO PROCEDE": "NO APTO",
        "NO_APTO": "NO APTO",
    }
    return mapa.get(v, v)


def _upsert_cliente(db: Session, d: dict) -> str:
    row = db.execute(
        text("SELECT id FROM clientes WHERE numero_documento = :doc"),
        {"doc": d["numero_documento"]},
    ).first()
    if row:
        return str(row[0])
    cid = str(uuid.uuid4())
    db.execute(
        text(
            """INSERT INTO clientes (id, numero_documento, nombres, apellidos,
                   telefono, tipo_negocio, nombre_negocio, es_prospecto)
               VALUES (:id,:doc,:nom,:ape,:tel,:tn,:nn,TRUE)"""
        ),
        {
            "id": cid,
            "doc": d["numero_documento"],
            "nom": d.get("nombres", ""),
            "ape": d.get("apellidos", ""),
            "tel": d.get("telefono"),
            "tn": d.get("tipo_negocio"),
            "nn": d.get("nombre_negocio"),
        },
    )
    return cid


def crear(db: Session, asesor_id: str, agencia_id: str | None, d: dict) -> dict:
    cliente_id = _upsert_cliente(db, d)
    sol_id = str(uuid.uuid4())
    expediente = "EXP-" + sol_id.replace("-", "")[:8].upper()
    db.execute(
        text(
            """INSERT INTO solicitudes_credito
                 (id, numero_expediente, asesor_id, cliente_id, agencia_id,
                  canal, tipo_negocio, nombre_negocio, ingresos_estimados,
                  monto_solicitado, plazo_meses, moneda, tipo_cuota, garantia,
                  destino_credito, cuota_estimada, tea_referencial,
                  firma_cliente_base64, estado)
               VALUES
                 (:id,:exp,:asesor,:cli,:ag,'asesor',:tn,:nn,:ing,
                  :monto,:plazo,:mon,:tc,:gar,:dest,:cuota,:tea,:firma,'enviada')"""
        ),
        {
            "id": sol_id,
            "exp": expediente,
            "asesor": asesor_id,
            "cli": cliente_id,
            "ag": agencia_id,
            "tn": d.get("tipo_negocio"),
            "nn": d.get("nombre_negocio"),
            "ing": d.get("ingresos_estimados"),
            "monto": d["monto_solicitado"],
            "plazo": d["plazo_meses"],
            "mon": d.get("moneda", "PEN"),
            "tc": d.get("tipo_cuota", "mensual"),
            "gar": d.get("garantia", "sin_garantia"),
            "dest": d.get("destino_credito"),
            "cuota": d.get("cuota_estimada"),
            "tea": d.get("tea_referencial"),
            "firma": d.get("firma_cliente_base64"),
        },
    )
    payload = {
        "numero_documento": d["numero_documento"],
        "nombres": d.get("nombres", ""),
        "apellidos": d.get("apellidos", ""),
        "monto_solicitado": float(d["monto_solicitado"]),
        "plazo_meses": int(d["plazo_meses"]),
        "numero_expediente": expediente,
    }
    db.execute(
        text(
            """INSERT INTO sync_outbox (id, entidad, entidad_id, operacion, payload, estado)
               VALUES (:id, 'solicitudes_credito', :eid, 'create', CAST(:payload AS jsonb), 'pendiente')"""
        ),
        {
            "id": str(uuid.uuid4()),
            "eid": sol_id,
            "payload": json.dumps(payload),
        },
    )
    db.commit()
    return {"id": sol_id, "numero_expediente": expediente, "estado": "enviada"}


def agregar_nota(db: Session, solicitud_id: str, asesor_id: str, contenido: str) -> dict:
    nid = str(uuid.uuid4())
    db.execute(
        text(
            """INSERT INTO solicitudes_notas_internas
                 (id, solicitud_id, asesor_id, contenido)
               VALUES (:id,:sol,:asesor,:cont)"""
        ),
        {"id": nid, "sol": solicitud_id, "asesor": asesor_id, "cont": contenido[:500]},
    )
    db.commit()
    return {"id": nid}


def listar_notas(db: Session, solicitud_id: str) -> list[dict]:
    rows = db.execute(
        text(
            """SELECT contenido, created_at
               FROM solicitudes_notas_internas
               WHERE solicitud_id = :sol
               ORDER BY created_at DESC"""
        ),
        {"sol": solicitud_id},
    ).mappings().all()
    return [
        {
            "contenido": r["contenido"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


def listar(db: Session, asesor_id: str) -> list[dict]:
    sql = """
        SELECT s.id, s.numero_expediente, s.cliente_id, s.created_by_auth_id,
               s.asesor_id, s.monto_solicitado, s.monto_aprobado,
               s.estado, s.created_at, s.updated_at,
               s.score_pre_evaluacion, s.elegibilidad, s.riesgo_asignado,
               s.ratio_capacidad_pago, s.motivo_pre_evaluacion,
               c.numero_documento, c.nombres, c.apellidos, c.telefono
        FROM solicitudes_credito s
        JOIN clientes c ON c.id = s.cliente_id
        WHERE (s.asesor_id = :asesor OR s.asesor_id IS NULL)
          AND date_trunc('month', s.created_at) = date_trunc('month', now())
        ORDER BY s.created_at DESC
        """
    params = {"asesor": asesor_id}
    try:
        compiled = text(sql).bindparams(**params).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
        print(f"[DEBUG rep_solicitudes.listar] SQL final: {compiled}")
    except Exception as exc:
        print(f"[DEBUG rep_solicitudes.listar] SQL (plantilla): {sql.strip()}")
        print(f"[DEBUG rep_solicitudes.listar] no se pudo renderizar SQL final: {exc}")
    print(f"[DEBUG rep_solicitudes.listar] parámetros enviados: {params}")
    rows = db.execute(text(sql), params).mappings().all()
    print(f"[DEBUG rep_solicitudes.listar] filas devueltas: {len(rows)}")
    return [
        {
            "id": str(r["id"]),
            "numero_expediente": r["numero_expediente"],
            "cliente_id": str(r["cliente_id"]),
            "created_by_auth_id": str(r["created_by_auth_id"]) if r.get("created_by_auth_id") else None,
            "asesor_id": str(r["asesor_id"]) if r["asesor_id"] else None,
            "cliente_nombre": f"{r['nombres']} {r['apellidos']}",
            "solicitante_nombre": f"{r['nombres']} {r['apellidos']}",
            "solicitante_documento": r["numero_documento"],
            "solicitante_telefono": r["telefono"],
            "monto_solicitado": float(r["monto_solicitado"] or 0),
            "monto_aprobado": float(r["monto_aprobado"] or 0),
            "score_pre_evaluacion": r["score_pre_evaluacion"],
            "elegibilidad": normalizar_elegibilidad(r["elegibilidad"]),
            "riesgo_asignado": r["riesgo_asignado"],
            "ratio_capacidad_pago": float(r["ratio_capacidad_pago"]) if r["ratio_capacidad_pago"] else None,
            "motivo_pre_evaluacion": r["motivo_pre_evaluacion"],
            "estado": normalizar_estado(r["estado"]),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        }
        for r in rows
    ]


def obtener(db: Session, solicitud_id: str) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT s.id, s.numero_expediente, s.asesor_id, s.cliente_id,
                   s.created_by_auth_id,
                   s.monto_solicitado, s.monto_aprobado, s.plazo_meses,
                   s.cuota_estimada, s.tea_referencial, s.ingresos_estimados,
                   s.gastos_mensuales,
                   s.score_pre_evaluacion, s.elegibilidad, s.ratio_capacidad_pago,
                   s.riesgo_asignado, s.motivo_pre_evaluacion,
                   s.destino_credito, s.garantia,
                   s.condicion_adicional, s.motivo_rechazo,
                   s.estado_buro, s.deuda_total, s.dias_mayor_mora,
                   s.en_lista_inhabilitados,
                   s.observacion_evaluador,
                   s.estado, s.created_at, s.updated_at, s.fecha_decision, s.fecha_desembolso,
                   c.numero_documento, c.nombres, c.apellidos, c.telefono
            FROM solicitudes_credito s
            JOIN clientes c ON c.id = s.cliente_id
            WHERE s.id = :sid
            """
        ),
        {"sid": solicitud_id},
    ).mappings().first()
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "numero_expediente": row["numero_expediente"],
        "asesor_id": str(row["asesor_id"]) if row["asesor_id"] else None,
        "cliente_id": str(row["cliente_id"]),
        "created_by_auth_id": str(row["created_by_auth_id"]) if row.get("created_by_auth_id") else None,
        "solicitante_documento": row["numero_documento"],
        "solicitante_nombre": f"{row['nombres']} {row['apellidos']}",
        "solicitante_telefono": row["telefono"],
        "monto_solicitado": float(row["monto_solicitado"] or 0),
        "monto_aprobado": float(row["monto_aprobado"]) if row["monto_aprobado"] else None,
        "plazo_meses": row["plazo_meses"],
        "cuota_estimada": float(row["cuota_estimada"]) if row["cuota_estimada"] else None,
        "tea_referencial": float(row["tea_referencial"]) if row["tea_referencial"] else None,
        "ingresos_estimados": float(row["ingresos_estimados"]) if row["ingresos_estimados"] else None,
        "gastos_mensuales": float(row["gastos_mensuales"]) if row.get("gastos_mensuales") else None,
        "score_pre_evaluacion": row["score_pre_evaluacion"],
        "elegibilidad": normalizar_elegibilidad(row["elegibilidad"]),
        "ratio_capacidad_pago": float(row["ratio_capacidad_pago"]) if row["ratio_capacidad_pago"] else None,
        "riesgo_asignado": row["riesgo_asignado"],
        "motivo_pre_evaluacion": row["motivo_pre_evaluacion"],
        "destino_credito": row["destino_credito"],
        "garantia": row["garantia"],
        "condicion_adicional": row["condicion_adicional"],
        "motivo_rechazo": row["motivo_rechazo"],
        "estado_buro": row["estado_buro"],
        "deuda_total": float(row["deuda_total"]) if row.get("deuda_total") else None,
        "dias_mayor_mora": row["dias_mayor_mora"],
        "en_lista_inhabilitados": row["en_lista_inhabilitados"],
        "observacion_evaluador": row["observacion_evaluador"],
        "estado": normalizar_estado(row["estado"]),
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "fecha_decision": row["fecha_decision"].isoformat() if row["fecha_decision"] else None,
        "fecha_desembolso": row["fecha_desembolso"].isoformat() if row["fecha_desembolso"] else None,
    }


def reclamar(db: Session, solicitud_id: str, asesor_id: str) -> dict | None:
    now = datetime.now(timezone.utc)
    result = db.execute(
        text(
            """
            UPDATE solicitudes_credito
            SET asesor_id = :asesor_id,
                updated_at = :now
            WHERE id = :sid
              AND asesor_id IS NULL
            RETURNING id, asesor_id, estado
            """
        ),
        {"asesor_id": asesor_id, "now": now, "sid": solicitud_id},
    ).mappings().first()
    if not result:
        return None
    db.commit()
    return {
        "id": str(result["id"]),
        "asesor_id": str(result["asesor_id"]),
        "estado": normalizar_estado(result["estado"]),
    }


def verificar_asesor(db: Session, solicitud_id: str, asesor_id: str) -> tuple[str, str | None]:
    row = db.execute(
        text("SELECT estado, asesor_id FROM solicitudes_credito WHERE id = :sid"),
        {"sid": solicitud_id},
    ).mappings().first()
    if not row:
        return "not_found", None
    estado = row["estado"]
    asesor_actual = str(row["asesor_id"]) if row["asesor_id"] else None
    return estado, asesor_actual


def aprobar(db: Session, solicitud_id: str, asesor_id: str) -> dict | None:
    estado, asesor_actual = verificar_asesor(db, solicitud_id, asesor_id)
    if estado == "not_found":
        return {"error": "not_found"}
    if asesor_actual is not None and asesor_actual != asesor_id:
        return {"error": "conflict"}
    now = datetime.now(timezone.utc)
    result = db.execute(
        text(
            """
            UPDATE solicitudes_credito
            SET estado = 'aprobada',
                asesor_id = COALESCE(asesor_id, :asesor_id),
                monto_aprobado = COALESCE(monto_aprobado, monto_solicitado),
                fecha_decision = :now,
                updated_at = :now
            WHERE id = :sid
            RETURNING id, estado, monto_aprobado, fecha_decision
            """
        ),
        {"asesor_id": asesor_id, "now": now, "sid": solicitud_id},
    ).mappings().first()
    db.commit()
    return {
        "id": str(result["id"]),
        "estado": normalizar_estado(result["estado"]),
        "monto_aprobado": float(result["monto_aprobado"] or 0),
        "fecha_decision": result["fecha_decision"].isoformat() if result["fecha_decision"] else None,
    }


def condicionar(db: Session, solicitud_id: str, asesor_id: str, monto_aprobado: float, condicion: str) -> dict | None:
    estado, asesor_actual = verificar_asesor(db, solicitud_id, asesor_id)
    if estado == "not_found":
        return {"error": "not_found"}
    if asesor_actual is not None and asesor_actual != asesor_id:
        return {"error": "conflict"}

    datos = db.execute(
        text(
            "SELECT tea_referencial, plazo_meses, ingresos_estimados, monto_solicitado FROM solicitudes_credito WHERE id = :sid"
        ),
        {"sid": solicitud_id},
    ).mappings().first()
    if not datos:
        return {"error": "not_found"}

    monto_sol = float(datos["monto_solicitado"] or 0)
    if monto_aprobado >= monto_sol:
        return {"error": "invalid_monto"}

    tea = float(datos["tea_referencial"]) if datos["tea_referencial"] else 0
    plazo = datos["plazo_meses"]
    ingresos = float(datos["ingresos_estimados"] or 0)

    tem = (1 + tea / 100) ** (1 / 12) - 1 if tea > 0 else 0
    if tem <= 0 or plazo <= 0:
        cuota_estimada = round(monto_aprobado / plazo, 2) if plazo > 0 else 0
    else:
        cuota_estimada = round(monto_aprobado * tem / (1 - (1 + tem) ** (-plazo)), 2)

    capacidad_neta = ingresos
    ratio = round(cuota_estimada / capacidad_neta, 2) if capacidad_neta > 0 else 999

    now = datetime.now(timezone.utc)
    result = db.execute(
        text(
            """
            UPDATE solicitudes_credito
            SET estado = 'condicionada',
                asesor_id = COALESCE(asesor_id, :asesor_id),
                monto_aprobado = :monto,
                cuota_estimada = :cuota,
                ratio_capacidad_pago = :ratio,
                condicion_adicional = :condicion,
                fecha_decision = :now,
                updated_at = :now
            WHERE id = :sid
              AND monto_solicitado > :monto
            RETURNING id, estado, monto_aprobado, monto_solicitado, cuota_estimada, ratio_capacidad_pago, fecha_decision
            """
        ),
        {
            "asesor_id": asesor_id,
            "monto": monto_aprobado,
            "cuota": cuota_estimada,
            "ratio": ratio,
            "condicion": condicion,
            "now": now,
            "sid": solicitud_id,
        },
    ).mappings().first()
    if not result:
        return {"error": "invalid_monto"}
    db.commit()
    return {
        "id": str(result["id"]),
        "estado": normalizar_estado(result["estado"]),
        "monto_aprobado": float(result["monto_aprobado"] or 0),
        "cuota_estimada": float(result["cuota_estimada"] or 0),
        "ratio_capacidad_pago": float(result["ratio_capacidad_pago"] or 0) if result["ratio_capacidad_pago"] else None,
        "fecha_decision": result["fecha_decision"].isoformat() if result["fecha_decision"] else None,
    }


def rechazar(db: Session, solicitud_id: str, asesor_id: str, motivo: str) -> dict | None:
    estado, asesor_actual = verificar_asesor(db, solicitud_id, asesor_id)
    if estado == "not_found":
        return {"error": "not_found"}
    if asesor_actual is not None and asesor_actual != asesor_id:
        return {"error": "conflict"}
    now = datetime.now(timezone.utc)
    result = db.execute(
        text(
            """
            UPDATE solicitudes_credito
            SET estado = 'rechazada',
                asesor_id = COALESCE(asesor_id, :asesor_id),
                motivo_rechazo = :motivo,
                fecha_decision = :now,
                updated_at = :now
            WHERE id = :sid
            RETURNING id, estado, motivo_rechazo, fecha_decision
            """
        ),
        {"asesor_id": asesor_id, "motivo": motivo, "now": now, "sid": solicitud_id},
    ).mappings().first()
    db.commit()
    return {
        "id": str(result["id"]),
        "estado": normalizar_estado(result["estado"]),
        "motivo_rechazo": result["motivo_rechazo"],
        "fecha_decision": result["fecha_decision"].isoformat() if result["fecha_decision"] else None,
    }
