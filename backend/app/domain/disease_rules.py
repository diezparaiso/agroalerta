from datetime import datetime, timedelta, timezone
from typing import Literal

from app.schemas import DiseaseRisk, RiskVariable, TelemetryCreate


DiseaseCode = Literal["repilo", "mildiu"]


def evaluate_risk(
    parcel_id: str,
    disease: DiseaseCode,
    crop_type: str,
    telemetry: TelemetryCreate | None = None,
) -> DiseaseRisk:
    """Calcula un riesgo MVP trazable a partir de observaciones de la parcela.

    No es un diagnóstico fitosanitario. Las reglas son deliberadamente
    conservadoras y deterministas hasta disponer de calibración histórica.
    """
    now = datetime.now(timezone.utc)
    inputs = _inputs_from_telemetry(telemetry)

    if disease == "repilo" and crop_type != "olivar":
        raise ValueError("El repilo solo aplica a parcelas de olivar")
    if disease == "mildiu" and crop_type != "vinedo":
        raise ValueError("El mildiu solo aplica a parcelas de viñedo")

    if disease == "repilo":
        score, recommendation = _repilo_score(inputs)
    else:
        score, recommendation = _mildiu_score(inputs)

    confidence = "alta" if telemetry is not None else "estimada"
    return DiseaseRisk(
        parcel_id=parcel_id,
        disease_code=disease,
        risk_score=round(score, 3),
        risk_level=_risk_level(score),
        confidence_level=confidence,
        recommendation_text=recommendation,
        variables_used=[
            RiskVariable(name="lluvia_24h_mm", value=inputs["rainfall_mm_24h"], date=now),
            RiskVariable(name="horas_mojado_foliar", value=inputs["leaf_wetness_hours"], date=now),
            RiskVariable(name="temperatura_media_c", value=inputs["temperature_c"], date=now),
            RiskVariable(name="humedad_relativa", value=inputs["relative_humidity"], date=now),
            RiskVariable(name="humedad_suelo", value=inputs["soil_moisture"], date=now),
        ],
        calculated_at=now,
        valid_until=now + timedelta(hours=6),
    )


def _inputs_from_telemetry(telemetry: TelemetryCreate | None) -> dict[str, float]:
    if telemetry is None:
        return {
            "rainfall_mm_24h": 0.0,
            "leaf_wetness_hours": 0.0,
            "temperature_c": 18.0,
            "relative_humidity": 70.0,
            "soil_moisture": 0.0,
        }
    return {
        "rainfall_mm_24h": telemetry.rainfall_mm_24h,
        "leaf_wetness_hours": telemetry.leaf_wetness_hours,
        "temperature_c": telemetry.temperature_c,
        "relative_humidity": telemetry.relative_humidity,
        "soil_moisture": telemetry.soil_moisture,
    }


def _repilo_score(values: dict[str, float]) -> tuple[float, str]:
    humidity = _ramp(values["relative_humidity"], 70, 95)
    wetness = _ramp(values["leaf_wetness_hours"], 4, 16)
    rain = _ramp(values["rainfall_mm_24h"], 2, 20)
    temperature = _bell(values["temperature_c"], 10, 16, 24)
    score = 0.30 * humidity + 0.30 * wetness + 0.20 * rain + 0.20 * temperature
    return score, "Vigila hojas y zonas húmedas; contrasta la alerta con observación de campo y el registro oficial vigente."


def _mildiu_score(values: dict[str, float]) -> tuple[float, str]:
    humidity = _ramp(values["relative_humidity"], 75, 98)
    wetness = _ramp(values["leaf_wetness_hours"], 3, 12)
    rain = _ramp(values["rainfall_mm_24h"], 2, 15)
    temperature = _bell(values["temperature_c"], 12, 20, 28)
    soil = _ramp(values["soil_moisture"], 55, 90)
    score = 0.25 * humidity + 0.25 * wetness + 0.20 * rain + 0.20 * temperature + 0.10 * soil
    return score, "Revisa hojas y racimos tras humedad persistente; valida la situación con observación de campo y fuentes oficiales."


def _risk_level(score: float) -> Literal["bajo", "medio", "alto"]:
    if score >= 0.70:
        return "alto"
    if score >= 0.40:
        return "medio"
    return "bajo"


def _ramp(value: float, start: float, end: float) -> float:
    if value <= start:
        return 0.0
    if value >= end:
        return 1.0
    return (value - start) / (end - start)


def _bell(value: float, low: float, optimum: float, high: float) -> float:
    if value <= low or value >= high:
        return 0.0
    if value <= optimum:
        return (value - low) / (optimum - low)
    return (high - value) / (high - optimum)
