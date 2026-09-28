from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.schemas import DiseaseRisk, RiskVariable, TelemetryCreate


def evaluate_risk(
    parcel_id: str,
    disease: Literal["repilo", "mildiu"],
    crop_type: str,
    telemetry: TelemetryCreate | None = None,
    raif_signal: float = 0.0,
    weather: dict[str, Any] | None = None,
) -> DiseaseRisk:
    now = datetime.now(timezone.utc)
    weather = weather or {}
    rainfall = float(weather.get("rainfall_mm_24h", 12.2))
    humidity_hours = telemetry.leaf_wetness_hours if telemetry else float(weather.get("leaf_wetness_hours", 18.0))
    temperature = telemetry.temperature_c if telemetry else float(weather.get("temperature_c", 18.4))
    humidity = telemetry.relative_humidity if telemetry else float(weather.get("relative_humidity", 87.0))
    base_score = min(1.0, 0.25 + rainfall / 40 + humidity_hours / 60)
    score = min(1.0, base_score + min(0.20, max(0.0, raif_signal) * 0.20))
    level = "alto" if score >= 0.7 else "medio" if score >= 0.4 else "bajo"
    name = "repilo" if disease == "repilo" and crop_type == "olivar" else "mildiu"
    return DiseaseRisk(
        parcel_id=parcel_id,
        disease_code=name,
        risk_score=round(score, 3),
        risk_level=level,
        confidence_level="estimada",
        recommendation_text=("Hay evidencia RAIF cercana; " if raif_signal > 0 else "") + "Revisar la parcela y consultar el registro MAPA vigente antes de aplicar cualquier tratamiento.",
        variables_used=[
            RiskVariable(name="lluvia_24h_mm", value=rainfall, date=now),
            RiskVariable(name="horas_mojado_foliar", value=humidity_hours, date=now),
            RiskVariable(name="temperatura_media_c", value=temperature, date=now),
            RiskVariable(name="humedad_relativa", value=humidity, date=now),
        ],
        calculated_at=now,
        valid_until=now + timedelta(hours=6),
    )
