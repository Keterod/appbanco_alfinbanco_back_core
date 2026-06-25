from sqlalchemy import text
from sqlalchemy.orm import Session


def resumen(db: Session, asesor_id: str) -> dict:
    row = db.execute(
        text(
            """
            SELECT
                COUNT(*)::int                                          AS solicitudes_total,
                COUNT(*) FILTER (WHERE s.estado = 'enviada')::int      AS solicitudes_enviadas,
                COUNT(*) FILTER (WHERE s.estado = 'aprobada')::int     AS solicitudes_aprobadas,
                COUNT(*) FILTER (WHERE s.estado = 'condicionada')::int AS solicitudes_condicionadas,
                COUNT(*) FILTER (WHERE s.estado = 'rechazada')::int    AS solicitudes_rechazadas,
                COUNT(*) FILTER (WHERE s.estado = 'desembolsada')::int AS solicitudes_desembolsadas,
                COUNT(*) FILTER (WHERE s.asesor_id IS NULL)::int       AS solicitudes_libres,
                COUNT(*) FILTER (WHERE s.asesor_id = :asesor)::int     AS mis_expedientes,
                COALESCE(SUM(s.monto_aprobado) FILTER (WHERE s.estado = 'desembolsada'), 0)::float AS monto_desembolsado_total,
                COALESCE(SUM(s.monto_aprobado) FILTER (WHERE s.estado = 'desembolsada'
                    AND date_trunc('month', s.fecha_desembolso) = date_trunc('month', now())), 0)::float AS monto_desembolsado_mes,
                COALESCE((SELECT COUNT(*)::int FROM cr_creditos WHERE estado = 'vigente'), 0) AS creditos_activos,
                COALESCE((SELECT COUNT(DISTINCT s2.cliente_id)::int FROM solicitudes_credito s2), 0) AS clientes_atendidos
            FROM solicitudes_credito s
            """
        ),
        {"asesor": asesor_id},
    ).mappings().first()

    return {
        "solicitudes_total": row["solicitudes_total"],
        "solicitudes_enviadas": row["solicitudes_enviadas"],
        "solicitudes_aprobadas": row["solicitudes_aprobadas"],
        "solicitudes_condicionadas": row["solicitudes_condicionadas"],
        "solicitudes_rechazadas": row["solicitudes_rechazadas"],
        "solicitudes_desembolsadas": row["solicitudes_desembolsadas"],
        "solicitudes_libres": row["solicitudes_libres"],
        "mis_expedientes": row["mis_expedientes"],
        "monto_desembolsado_total": row["monto_desembolsado_total"],
        "monto_desembolsado_mes": row["monto_desembolsado_mes"],
        "creditos_activos": row["creditos_activos"],
        "clientes_atendidos": row["clientes_atendidos"],
    }
