"""Motor de decisión agronómica explicable: combina riesgo, telemetría, clima, reportes de campo y señal RAIF; nunca prescribe dosis/productos.

Este módulo contiene reglas de dominio puras o casi puras. Las rutas HTTP y la persistencia
se mantienen fuera para que los cálculos puedan probarse de forma aislada.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def make_agronomic_decision(
    parcel_id: str,
    disease_code: str,
    risk: dict[str, Any],
    telemetry: dict[str, Any] | None = None,
    weather: dict[str, Any] | None = None,
    field_reports: list[dict[str, Any]] | None = None,
    raif_signal: float | None = None,
) -> dict[str, Any]:
    """Combina señales heterogéneas en una decisión explicable.

    No recomienda productos ni dosis. Prioriza seguimiento y revisión de campo.
    """
    evidence = []
    score = float(risk.get("risk_score", 0))
    evidence.append({
        "source": "disease_risk",
        "key": "risk_score",
        "value": f"{score:.2f}",
        "weight": 0.40,
    })

    if telemetry:
        humidity = float(telemetry.get("relative_humidity", 0))
        wetness = float(telemetry.get("leaf_wetness_hours", 0))
        if humidity >= 85:
            score += 0.08
            evidence.append({"source": "telemetry", "key": "relative_humidity", "value": f"{humidity:.1f}%", "weight": 0.08})
        if wetness >= 8:
            score += 0.08
            evidence.append({"source": "telemetry", "key": "leaf_wetness_hours", "value": f"{wetness:.1f} h", "weight": 0.08})

    if weather:
        # AEMET devuelve null en lluvia/humedad cuando no tiene dato (verificado
        # en vivo el 2026-10-05): se trata como ausencia de señal, nunca como 0 real.
        rain = float(weather.get("rainfall_mm_24h") or 0)
        humidity = float(weather.get("relative_humidity") or 0)
        if rain >= 5:
            score += 0.08
            evidence.append({"source": "weather", "key": "rainfall_mm_24h", "value": f"{rain:.1f} mm", "weight": 0.08})
        if humidity >= 85:
            score += 0.05
            evidence.append({"source": "weather", "key": "relative_humidity", "value": f"{humidity:.1f}%", "weight": 0.05})

    reports = field_reports or []
    recent_symptoms = sum(1 for item in reports if item.get("type") == "sintoma")
    if recent_symptoms:
        boost = min(0.15, recent_symptoms * 0.05)
        score += boost
        evidence.append({"source": "field_report", "key": "recent_symptoms", "value": str(recent_symptoms), "weight": boost})

    if raif_signal is not None:
        boost = min(0.15, max(0.0, raif_signal) * 0.15)
        score += boost
        evidence.append({"source": "raif", "key": "regional_signal", "value": f"{raif_signal:.2f}", "weight": boost})

    score = min(1.0, round(score, 3))
    priority = "revisar" if score >= 0.70 else "vigilar" if score >= 0.40 else "informativa"
    confidence = _confidence(risk, telemetry, weather, recent_symptoms, raif_signal)

    if priority == "revisar":
        headline = f"Revisar parcela por señal de {disease_code}"
        explanation = "Varias señales independientes elevan el nivel de atención; confirma la situación mediante inspección de campo."
        next_steps = ["Inspeccionar zonas húmedas y órganos sensibles.", "Registrar síntomas u observaciones.", "Consultar fuentes oficiales antes de cualquier tratamiento."]
    elif priority == "vigilar":
        headline = f"Vigilar condiciones favorables a {disease_code}"
        explanation = "Existe una combinación de condiciones favorables, pero la señal no justifica por sí sola una intervención."
        next_steps = ["Revisar evolución meteorológica.", "Observar la parcela durante las próximas horas.", "Registrar cualquier síntoma."]
    else:
        headline = f"Seguimiento ordinario de {disease_code}"
        explanation = "Las señales disponibles no muestran una combinación suficientemente fuerte para elevar la prioridad."
        next_steps = ["Mantener observación habitual.", "Actualizar telemetría y observaciones de campo."]

    return {
        "parcel_id": parcel_id,
        "disease_code": disease_code,
        "priority": priority,
        "decision_score": score,
        "confidence": confidence,
        "headline": headline,
        "explanation": explanation,
        "next_steps": next_steps,
        "evidence": evidence,
        "calculated_at": datetime.now(timezone.utc),
    }


def _confidence(
    risk: dict[str, Any],
    telemetry: dict[str, Any] | None,
    weather: dict[str, Any] | None,
    symptoms: int,
    raif_signal: float | None,
) -> str:
    sources = 1
    sources += int(telemetry is not None)
    sources += int(weather is not None)
    sources += int(symptoms > 0)
    sources += int(raif_signal is not None)
    if sources >= 4 and risk.get("confidence_level") == "alta":
        return "alta"
    if sources >= 2:
        return "media"
    return "baja"
