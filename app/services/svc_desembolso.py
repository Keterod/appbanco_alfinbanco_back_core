import uuid
from datetime import datetime, timezone, date
from calendar import monthrange
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.repositories.rep_solicitudes import normalizar_estado


def _generar_numero_operacion() -> str:
    return "OP-" + uuid.uuid4().hex[:12].upper()


def _generar_referencia() -> str:
    return "REF-" + uuid.uuid4().hex[:8].upper()


def _sumar_meses(fecha: date, meses: int) -> date:
    mes = fecha.month - 1 + meses
    anio = fecha.year + mes // 12
    mes = mes % 12 + 1
    dia = min(fecha.day, monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def _calcular_tem(tea: float) -> float:
    return (1 + tea / 100) ** (1 / 12) - 1


def _calcular_cuota(monto: float, tem: float, plazo_meses: int) -> float:
    if plazo_meses <= 0:
        raise ValueError("Plazo invalido")
    if tem <= 0:
        return round(monto / plazo_meses, 2)
    return round(monto * tem / (1 - (1 + tem) ** (-plazo_meses)), 2)


def desembolsar(db: Session, solicitud_id: str, asesor_id: str) -> dict:
    now = datetime.now(timezone.utc)
    hoy = now.date()

    row = db.execute(
        text(
            """
            SELECT s.id, s.numero_expediente, s.cliente_id, s.created_by_auth_id,
                   s.asesor_id, s.estado, s.monto_solicitado, s.monto_aprobado,
                   s.plazo_meses, s.tea_referencial, s.moneda, s.destino_credito,
                   s.tipo_negocio, s.nombre_negocio,
                   c.numero_documento, c.nombres, c.apellidos
            FROM solicitudes_credito s
            JOIN clientes c ON c.id = s.cliente_id
            WHERE s.id = :sid
            """
        ),
        {"sid": solicitud_id},
    ).mappings().first()

    if not row:
        return {"error": "not_found"}

    estado = normalizar_estado(row["estado"])
    asesor_actual = str(row["asesor_id"]) if row["asesor_id"] else None
    cliente_app_id = str(row["created_by_auth_id"]) if row["created_by_auth_id"] else str(row["cliente_id"])
    monto_solicitado = float(row["monto_solicitado"] or 0)
    monto_aprobado = float(row["monto_aprobado"]) if row["monto_aprobado"] else None
    plazo_meses = row["plazo_meses"]
    tea = float(row["tea_referencial"]) if row["tea_referencial"] else 0
    moneda = row["moneda"] or "PEN"
    numero_expediente = row["numero_expediente"]

    if asesor_actual is not None and asesor_actual != asesor_id:
        return {"error": "conflict"}
    if estado not in ("aprobada", "condicionada"):
        return {"error": "invalid_state", "detail": f"Estado '{estado}' no permite desembolso"}

    ya_desembolsada = db.execute(
        text("SELECT id FROM clientes_creditos WHERE id = :sid"),
        {"sid": solicitud_id},
    ).first()
    if ya_desembolsada:
        return {"error": "duplicate", "detail": "Esta solicitud ya fue desembolsada"}

    monto_final = monto_aprobado if (monto_aprobado is not None and monto_aprobado > 0) else monto_solicitado
    if estado == "condicionada" and (monto_aprobado is None or monto_aprobado <= 0):
        return {"error": "invalid_monto", "detail": "Solicitud condicionada requiere monto_aprobado"}
    if monto_final <= 0:
        return {"error": "invalid_monto", "detail": "Monto invalido para desembolso"}

    tem = _calcular_tem(tea) if tea > 0 else 0
    cuota = _calcular_cuota(monto_final, tem, plazo_meses)

    credito_id = solicitud_id
    proxima_fecha = _sumar_meses(hoy, 1)

    db.execute(
        text(
            """
            INSERT INTO clientes_creditos
                (id, cliente_id, producto, nombre_producto,
                 monto_original, monto_pendiente, cuota_mensual,
                 proxima_fecha_pago, fecha_proximo_pago,
                 tea_referencial, tea, progreso_pago,
                 estado, activo)
            VALUES
                (:id, :cli, :prod, :nom_prod,
                 :monto, :monto, :cuota,
                 :prox_pago, :prox_pago,
                 :tea, :tea, 0,
                 'activo', TRUE)
            """
        ),
        {
            "id": credito_id,
            "cli": cliente_app_id,
            "prod": "Crédito Empresarial Alfin",
            "nom_prod": "Crédito Empresarial - Microempresa",
            "monto": monto_final,
            "cuota": round(cuota, 2),
            "prox_pago": proxima_fecha,
            "tea": tea,
        },
    )

    for n in range(1, plazo_meses + 1):
        fecha_venc = _sumar_meses(hoy, n)
        db.execute(
            text(
                """
                INSERT INTO clientes_cronograma_pagos
                    (id, cliente_id, credito_id, numero_cuota,
                     fecha_vencimiento, monto, estado)
                VALUES
                    (:id, :cli, :cred_id, :nro,
                     :fvenc, :monto, 'pendiente')
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "cli": cliente_app_id,
                "cred_id": credito_id,
                "nro": n,
                "fvenc": fecha_venc,
                "monto": round(cuota, 2),
            },
        )

    referencia = _generar_referencia()
    db.execute(
        text(
            """
            INSERT INTO clientes_movimientos
                (id, cliente_id, cuenta_id, descripcion,
                 categoria, referencia, monto, es_abono, fecha)
            VALUES
                (:id, :cli, NULL, :desc,
                 'Crédito', :ref, :monto, TRUE, :fecha)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "cli": cliente_app_id,
            "desc": "Desembolso de crédito empresarial",
            "ref": referencia,
            "monto": monto_final,
            "fecha": now,
        },
    )

    numero_op = _generar_numero_operacion()
    db.execute(
        text(
            """
            INSERT INTO clientes_operaciones
                (id, cliente_id, tipo_operacion, monto,
                 descripcion, numero_operacion, estado, fecha)
            VALUES
                (:id, :cli, 'DESEMBOLSO', :monto,
                 :desc, :num_op, 'exitosa', :fecha)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "cli": cliente_app_id,
            "monto": monto_final,
            "desc": f"Desembolso - {numero_expediente}",
            "num_op": numero_op,
            "fecha": now,
        },
    )

    cuenta = db.execute(
        text(
            """
            SELECT id, saldo, saldo_disponible, saldo_contable
            FROM clientes_cuentas
            WHERE cliente_id = :cli AND es_principal = TRUE
            LIMIT 1
            """
        ),
        {"cli": cliente_app_id},
    ).mappings().first()

    if cuenta:
        saldo_anterior = float(cuenta["saldo"] or 0)
        disp_anterior = float(cuenta["saldo_disponible"] or 0)
        cont_anterior = float(cuenta["saldo_contable"] or 0)
        db.execute(
            text(
                """
                UPDATE clientes_cuentas
                SET saldo = :saldo,
                    saldo_disponible = :disp,
                    saldo_contable = :cont
                WHERE id = :cid
                """
            ),
            {
                "saldo": saldo_anterior + monto_final,
                "disp": disp_anterior + monto_final,
                "cont": cont_anterior + monto_final,
                "cid": cuenta["id"],
            },
        )
    else:
        cta_id = str(uuid.uuid4())
        db.execute(
            text(
                """
                INSERT INTO clientes_cuentas
                    (id, cliente_id, tipo_cuenta, moneda,
                     saldo, saldo_disponible, saldo_contable,
                     es_principal, estado)
                VALUES
                    (:id, :cli, 'Ahorros', 'PEN',
                     :saldo, :disp, :cont,
                     TRUE, 'activa')
                """
            ),
            {
                "id": cta_id,
                "cli": cliente_app_id,
                "saldo": monto_final,
                "disp": monto_final,
                "cont": monto_final,
            },
        )

    db.execute(
        text(
            """
            UPDATE solicitudes_credito
            SET estado = 'desembolsada',
                asesor_id = COALESCE(asesor_id, :asesor_id),
                monto_aprobado = COALESCE(monto_aprobado, monto_solicitado),
                fecha_decision = COALESCE(fecha_decision, :now),
                fecha_desembolso = :now,
                updated_at = :now
            WHERE id = :sid
            """
        ),
        {
            "asesor_id": asesor_id,
            "now": now,
            "sid": solicitud_id,
        },
    )

    db.commit()

    return {
        "id": solicitud_id,
        "numero_expediente": numero_expediente,
        "estado": "desembolsada",
        "monto_aprobado": monto_final,
        "credito_id": credito_id,
        "cuotas_generadas": plazo_meses,
        "mensaje": "Desembolso realizado correctamente",
    }
