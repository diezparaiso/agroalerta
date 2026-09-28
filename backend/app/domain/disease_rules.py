from datetime import datetime, timedelta, timezone
from typing import Literal

from app.schemas import DiseaseRisk, RiskVariable, TelemetryCreate


def evaluate_risk(
    parcel_id: str,
    disease: Literal["repilo", "mildiu"],
    crop_type: str,
    telemetry: TelemetryCreate | None = None,
) -> DiseaseRisk:
    now = datetime.now(timezone.utc)
    # MVP: deterministic placeholder fed by the normalized weather contract.
    # Real ingestion will replace these values without changing the API.
    rainfall = 12.2
    humidity_hours = telemetry.leaf_wetness_hours if telemetry else 18.0
    temperature = telemetry.temperature_c if telemetry else 18.4
    humidity = telemetry.relative_humidity if telemetry else 87.0
    score = min(1.0, 0.25 + rainfall / 40 + humidity_hours / 60)
    level = "alto" if score >= 0.7 else "medio" if score >= 0.4 else "bajo"
    name = "repilo" if disease == "repilo" and crop_type == "olivar" else "mildiu"
    return DiseaseRisk(
        parcel_id=parcel_id,
        disease_code=name,
        risk_score=round(score, 3),
        risk_level=level,
        confidence_level="estimada",
        recommendation_text="Revisar la parcela y consultar el registro MAPA vigente antes de aplicar cualquier tratamiento.",
        variables_used=[
            RiskVariable(name="lluvia_24h_mm", value=rainfall, date=now),
            RiskVariable(name="horas_mojado_foliar", value=humidity_hours, date=now),
            RiskVariable(name="temperatura_media_c", value=temperature, date=now),
            RiskVariable(name="humedad_relativa", value=humidity, date=now),
        ],
        calculated_at=now,
        valid_until=now + timedelta(hours=6),
    )
