import uuid
from datetime import datetime, timezone, date
from calendar import monthrange
from sqlalchemy import text
from sqlalchemy.orm import Session


def _generar_cod_cuenta_credito() -> str:
    return "CRE-" + uuid.uuid4().hex[:8].upper()


def _generar_cod_operacion() -> str:
    return "MOV-" + uuid.uuid4().hex[:12].upper()


def _generar_cod_cuenta_ahorro() -> str:
    return "CTA-" + uuid.uuid4().hex[:8].upper()


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
            SELECT s.id, s.numero_expediente, s.cliente_id, s.asesor_id,
                   s.estado, s.monto_solicitado, s.monto_aprobado, s.plazo_meses,
                   s.tea_referencial, s.moneda, s.destino_credito, s.tipo_negocio,
                   s.nombre_negocio, s.producto_credito,
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

    estado = row["estado"]
    asesor_actual = str(row["asesor_id"]) if row["asesor_id"] else None
    cliente_id = str(row["cliente_id"])
    monto_solicitado = float(row["monto_solicitado"] or 0)
    monto_aprobado = float(row["monto_aprobado"]) if row["monto_aprobado"] else None
    plazo_meses = row["plazo_meses"]
    tea = float(row["tea_referencial"]) if row["tea_referencial"] else 0
    moneda = row["moneda"] or "PEN"
    producto = row.get("producto_credito") or "Credito Empresarial"
    numero_expediente = row["numero_expediente"]

    if estado == "not_found":
        return {"error": "not_found"}
    if asesor_actual is not None and asesor_actual != asesor_id:
        return {"error": "conflict"}
    if estado not in ("aprobada", "condicionada"):
        return {"error": "invalid_state", "detail": f"Estado '{estado}' no permite desembolso"}

    ya_desembolsada = db.execute(
        text("SELECT id FROM cr_creditos WHERE id = :sid_for_dup"),
        {"sid_for_dup": solicitud_id},
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

    cod_credito = _generar_cod_cuenta_credito()

    db.execute(
        text(
            """
            INSERT INTO cr_creditos
                (id, cod_cuenta_credito, cliente_id, producto,
                 monto_desembolsado, saldo_capital, saldo_total,
                 dias_mora, calificacion_interna, estado,
                 fecha_desembolso, tea, cuotas_total, cuotas_pagadas)
            VALUES
                (:id, :cod, :cli, :prod,
                 :monto, :saldo, :saldo,
                 0, 'normal', 'vigente',
                 :fecha, :tea, :cuotas, 0)
            """
        ),
        {
            "id": solicitud_id,
            "cod": cod_credito,
            "cli": cliente_id,
            "prod": producto,
            "monto": monto_final,
            "saldo": monto_final,
            "fecha": hoy,
            "tea": tea,
            "cuotas": plazo_meses,
        },
    )

    saldo_restante = monto_final
    for n in range(1, plazo_meses + 1):
        interes = saldo_restante * tem if tem > 0 else 0
        capital_pagado = cuota - interes
        saldo_restante = max(0, saldo_restante - capital_pagado)
        fecha_venc = _sumar_meses(hoy, n)
        db.execute(
            text(
                """
                INSERT INTO cr_cronograma_pagos
                    (id, cod_cuenta_credito, nro_cuota, fecha_vencimiento,
                     monto_cuota, monto_capital, monto_interes,
                     saldo, estado_cuota)
                VALUES
                    (:id, :cod, :nro, :fvenc,
                     :monto, :cap, :int,
                     :saldo, 'pendiente')
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "cod": cod_credito,
                "nro": n,
                "fvenc": fecha_venc,
                "monto": round(cuota, 2),
                "cap": round(capital_pagado, 2) if capital_pagado > 0 else 0,
                "int": round(interes, 2) if interes > 0 else 0,
                "saldo": round(saldo_restante, 2),
            },
        )

    cod_mov = _generar_cod_operacion()
    db.execute(
        text(
            """
            INSERT INTO cr_movimientos
                (id, cod_operacion, cliente_id, cod_cuenta,
                 tipo, concepto, canal, monto, moneda, fecha_operacion)
            VALUES
                (:id, :cod, :cli, :cod_cta,
                 'CRE', :concepto, 'APP', :monto, :mon, :fecha)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "cod": cod_mov,
            "cli": cliente_id,
            "cod_cta": cod_credito,
            "concepto": f"Desembolso de credito - {producto}",
            "monto": monto_final,
            "mon": moneda,
            "fecha": now,
        },
    )

    cuenta_existente = db.execute(
        text("SELECT id, cod_cuenta_ahorro, saldo_capital FROM cr_cuentas_ahorro WHERE cliente_id = :cli LIMIT 1"),
        {"cli": cliente_id},
    ).mappings().first()

    if cuenta_existente:
        cod_cuenta_ahorro = cuenta_existente["cod_cuenta_ahorro"]
        saldo_anterior = float(cuenta_existente["saldo_capital"] or 0)
        db.execute(
            text("UPDATE cr_cuentas_ahorro SET saldo_capital = :nuevo_saldo WHERE id = :cid"),
            {"nuevo_saldo": saldo_anterior + monto_final, "cid": cuenta_existente["id"]},
        )
    else:
        cod_cuenta_ahorro = _generar_cod_cuenta_ahorro()
        db.execute(
            text(
                """
                INSERT INTO cr_cuentas_ahorro
                    (id, cod_cuenta_ahorro, cliente_id, tipo_cuenta,
                     moneda, saldo_capital, saldo_interes, tea, estado)
                VALUES
                    (:id, :cod, :cli, 'Cuenta Corriente',
                     :mon, :saldo, 0, 0, 'activa')
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "cod": cod_cuenta_ahorro,
                "cli": cliente_id,
                "mon": moneda,
                "saldo": monto_final,
            },
        )

    cod_op = _generar_cod_operacion()
    db.execute(
        text(
            """
            INSERT INTO operaciones_cliente
                (id, cliente_id, cod_cuenta_origen, cod_cuenta_destino,
                 tipo, monto, moneda, estado)
            VALUES
                (:id, :cli, :cod_origen, :cod_destino,
                 'DESEMBOLSO', :monto, :mon, 'exitosa')
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "cli": cliente_id,
            "cod_origen": cod_credito,
            "cod_destino": cod_cuenta_ahorro,
            "monto": monto_final,
            "mon": moneda,
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

    print(f"[DESEMBOLSO] solicitud={solicitud_id} asesor={asesor_id} "
          f"cliente={cliente_id} monto={monto_final} "
          f"credito={cod_credito} cuotas={plazo_meses}")

    return {
        "id": solicitud_id,
        "numero_expediente": numero_expediente,
        "estado": "desembolsada",
        "monto_aprobado": monto_aprobado if monto_aprobado else monto_solicitado,
        "credito_id": cod_credito,
        "cuotas_generadas": plazo_meses,
        "mensaje": "Desembolso realizado correctamente",
    }
