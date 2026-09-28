from datetime import datetime, timezone
from typing import Any


def build_activity_timeline(
    activities: list[Any],
    risks: list[Any],
    telemetry: Any | None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    events = [
        {
            "event_type": "actividad",
            "title": item.title,
            "occurred_at": item.occurred_at,
            "detail": item.detail or item.activity_type,
            "activity_type": item.activity_type,
        }
        for item in activities
    ]
    events.extend(
        {
            "event_type": "riesgo",
            "title": f"Riesgo {risk.disease_code}: {risk.risk_level}",
            "occurred_at": risk.calculated_at,
            "detail": f"Puntuación {risk.risk_score:.2f}",
            "activity_type": None,
        }
        for risk in risks
    )
    if telemetry:
        events.append({
            "event_type": "telemetria",
            "title": "Lectura de sensores",
            "occurred_at": telemetry.measured_at,
            "detail": f"Suelo {telemetry.soil_moisture:.1f}% · HR {telemetry.relative_humidity:.1f}%",
            "activity_type": None,
        })
    events.sort(key=lambda item: item["occurred_at"], reverse=True)
    return events[:limit]
