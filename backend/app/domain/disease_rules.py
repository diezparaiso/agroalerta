"""Conservative and explainable preliminary disease-risk indicators.

A single sensor reading cannot prove continuous leaf wetness or a disease
incubation period. These indicators are not validated forecasts.
"""
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.schemas import DiseaseRisk, RiskVariable, TelemetryCreate

SUPPORTED_CROPS = {"repilo": "olivar", "mildiu": "vinedo"}


def evaluate_risk(
    parcel_id: str,
    disease: Literal["repilo", "mildiu"],
    crop_type: str,
    telemetry: TelemetryCreate | None = None,
) -> DiseaseRisk:
    if disease not in SUPPORTED_CROPS:
        raise ValueError(f"Enfermedad no soportada: {disease}")

    now = datetime.now(timezone.utc)
    status: Literal["insuficiente", "preliminar"] = "insuficiente"
    score = 0.0
    level: Literal["bajo", "medio", "alto"] = "bajo"
    variables: list[RiskVariable] = []
    explanation = (
        "Datos insuficientes para estimar el riesgo. Este resultado no significa "
        "que no exista riesgo; falta una serie meteorológica validada."
    )

    if crop_type != SUPPORTED_CROPS[disease]:
        explanation = "La regla solicitada no corresponde al cultivo de esta parcela."
    elif telemetry is not None:
        measured_at = telemetry.measured_at
        if measured_at.tzinfo is None:
            measured_at = measured_at.replace(tzinfo=timezone.utc)
        age_hours = (now - measured_at.astimezone(timezone.utc)).total_seconds() / 3600
        if 0 <= age_hours <= 24:
            status = "preliminar"
            variables = [
                RiskVariable(name="temperatura_c", value=telemetry.temperature_c, date=measured_at),
                RiskVariable(name="humedad_relativa_pct", value=telemetry.relative_humidity, date=measured_at),
                RiskVariable(name="horas_mojado_reportadas", value=telemetry.leaf_wetness_hours, date=measured_at),
            ]
            if disease == "repilo":
                # Architecture v2 gives an approximate 24-36 h reference;
                # this single reading still cannot establish continuity.
                if 15 <= telemetry.temperature_c <= 20 and telemetry.leaf_wetness_hours >= 24:
                    score, level = 0.6, "medio"
                    explanation = (
                        "Indicador preliminar compatible con condiciones favorables; "
                        "debe verificarse el mojado foliar continuo."
                    )
                else:
                    explanation = (
                        "La lectura aislada no confirma condiciones de incubación "
                        "del repilo; falta una serie temporal de mojado y temperatura."
                    )
            elif (
                10 <= telemetry.temperature_c <= 25
                and telemetry.relative_humidity >= 85
                and telemetry.leaf_wetness_hours >= 6
            ):
                # Provisional signal only; threshold requires agronomic validation.
                score, level = 0.5, "medio"
                explanation = (
                    "Indicador preliminar de condiciones húmedas compatibles con mildiu; "
                    "no es una predicción validada."
                )
            else:
                explanation = (
                    "La lectura aislada no aporta evidencia suficiente de condiciones "
                    "favorables para mildiu durante un periodo de incubación."
                )
        else:
            explanation = (
                "La telemetría está fuera de la ventana de 24 horas o tiene fecha futura; "
                "no se utiliza para estimar el riesgo."
            )

    return DiseaseRisk(
        parcel_id=parcel_id,
        disease_code=disease,
        risk_score=score,
        risk_level=level,
        confidence_level="estimada",
        recommendation_text=(
            explanation + " Inspeccione el cultivo y consulte fuentes técnicas oficiales; "
            "no aplique tratamientos basándose únicamente en este indicador."
        ),
        variables_used=variables,
        calculated_at=now,
        valid_until=now + timedelta(hours=1 if status == "preliminar" else 0),
        data_status=status,
    )
