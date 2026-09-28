from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.storage import Storage
from app.jobs.weather_ingestion_job import ingest_weather_for_parcel
from app.domain.disease_rules import evaluate_risk
from app.domain.raif_evidence import score_raif_evidence

logger = logging.getLogger(__name__)


async def refresh_all_parcel_weather() -> dict[str, int | str]:
    """Actualiza RIA para todas las parcelas almacenadas.

    Es idempotente a nivel de observación: SQLite reemplaza la misma
    combinación estación/fecha si vuelve a recibirse.
    """
    storage = Storage()
    parcels = storage.list_parcels()
    updated = 0
    failed = 0
    risks_recalculated = 0

    for parcel in parcels:
        try:
            result = await ingest_weather_for_parcel(
                parcel.latitude,
                parcel.longitude,
            )
            if result.get("status") == "ingested":
                updated += 1
                weather_context = storage.list_latest_weather_observations()
                raif_records = storage.list_georeferenced_source_records("raif_fitosanitario")
                for disease in ("repilo", "mildiu"):
                    if (disease == "repilo" and parcel.crop_type != "olivar") or (disease == "mildiu" and parcel.crop_type != "vinedo"):
                        continue
                    from app.domain.weather_context import build_weather_context
                    context = build_weather_context(parcel.latitude, parcel.longitude, weather_context)
                    evidence = score_raif_evidence(parcel.latitude, parcel.longitude, raif_records, disease)
                    risk = evaluate_risk(
                        parcel.id,
                        disease,
                        parcel.crop_type,
                        storage.latest_telemetry(parcel.id, parcel.owner_id),
                        raif_signal=float(evidence["signal"]),
                        weather=context["weather"] if context["available"] else None,
                    )
                    from app.schemas import RiskSnapshot
                    storage.save_risk_snapshot(RiskSnapshot(
                        parcel_id=parcel.id,
                        owner_id=parcel.owner_id,
                        disease_code=risk.disease_code,
                        risk_score=risk.risk_score,
                        risk_level=risk.risk_level,
                        calculated_at=risk.calculated_at,
                    ))
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
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
