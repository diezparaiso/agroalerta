from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.storage import Storage
from app.jobs.weather_ingestion_job import ingest_weather_for_parcel
from app.domain.disease_rules import evaluate_risk
from app.domain.raif_evidence import score_raif_evidence
from app.domain.risk_alert_engine import decide_risk_alert
from app.domain.push_notifications import send_alert_push
from app.schemas import RiskSnapshot

logger = logging.getLogger(__name__)


async def refresh_all_parcel_weather(owner_id: str | None = None) -> dict[str, int | str]:
    """Actualiza RIA para todas las parcelas almacenadas.

    Es idempotente a nivel de observación: SQLite reemplaza la misma
    combinación estación/fecha si vuelve a recibirse.
    """
    storage = Storage()
    parcels = storage.list_parcels(owner_id)
    updated = 0
    failed = 0
    risks_recalculated = 0
    alerts_created = 0

    for parcel in parcels:
        try:
            result = await ingest_weather_for_parcel(
                parcel.latitude,
                parcel.longitude,
            )
            if result.get("status") == "ingested":
                updated += 1
                weather_context = storage.list_latest_weather_observations()
                from app.domain.weather_context import build_weather_context
                context = build_weather_context(parcel.latitude, parcel.longitude, weather_context)
                if not context["available"]:
                    logger.warning(
                        "No se recalcula riesgo por falta de meteorologia reciente: parcela=%s",
                        parcel.id,
                    )
                    continue
                raif_records = storage.list_georeferenced_source_records("raif_fitosanitario")
                for disease in ("repilo", "mildiu"):
                    if (disease == "repilo" and parcel.crop_type != "olivar") or (disease == "mildiu" and parcel.crop_type != "vinedo"):
                        continue
                    evidence = score_raif_evidence(parcel.latitude, parcel.longitude, raif_records, disease)
                    risk = evaluate_risk(
                        parcel.id,
                        disease,
                        parcel.crop_type,
                        storage.latest_telemetry(parcel.id, parcel.owner_id),
                        raif_signal=float(evidence["signal"]),
                        weather=context["weather"] if context["available"] else None,
                    )
                    previous_snapshot = storage.get_latest_risk_snapshot(
                        parcel.id,
                        parcel.owner_id,
                        risk.disease_code,
                    )
                    snapshot = RiskSnapshot(
                        parcel_id=parcel.id,
                        owner_id=parcel.owner_id,
                        disease_code=risk.disease_code,
                        risk_score=risk.risk_score,
                        risk_level=risk.risk_level,
                        calculated_at=risk.calculated_at,
                    )
                    storage.save_risk_snapshot(snapshot)

                    decision = decide_risk_alert(risk, previous_snapshot)
                    if decision.should_create:
                        alert = storage.save_alert(
                            parcel_id=parcel.id,
                            owner_id=parcel.owner_id,
                            disease_code=risk.disease_code,
                            alert_type=decision.alert_type,
                            risk_level=risk.risk_level,
                            risk_score=risk.risk_score,
                            message=decision.message,
                            created_at=risk.calculated_at,
                            valid_until=risk.valid_until,
                            dedup_key=(
                                f"{parcel.id}:{risk.disease_code}:"
                                f"{decision.reason_code}:{risk.risk_level}:"
                                f"{previous_snapshot.calculated_at.isoformat() if previous_snapshot else 'initial'}"
                            ),
                        )
                        if alert is not None:
                            alerts_created += 1
                            delivery = send_alert_push(
                                alert,
                                storage.list_push_tokens(parcel.owner_id),
                            )
                            if delivery.sent > 0:
                                storage.mark_alert_notified(alert.id)
                            logger.info(
                                "alert_push parcel=%s disease=%s status=%s sent=%s failed=%s",
                                parcel.id,
                                risk.disease_code,
                                delivery.status,
                                delivery.sent,
                                delivery.failed,
                            )
                    risks_recalculated += 1
            else:
                failed += 1
        except Exception:
            failed += 1
            logger.exception("Error actualizando meteorología de parcela %s", parcel.id)

    return {
        "status": "completed",
        "parcels": len(parcels),
        "updated": updated,
        "failed": failed,
        "risks_recalculated": risks_recalculated,
        "alerts_created": alerts_created,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
