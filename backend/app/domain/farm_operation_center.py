"""Constructor del centro operativo de explotación: transforma el estado agregado de parcelas, sensores, telemetría y riesgos en tarjetas y eventos.

Este módulo contiene reglas de dominio puras o casi puras. Las rutas HTTP y la persistencia
se mantienen fuera para que los cálculos puedan probarse de forma aislada.
"""

from datetime import datetime, timezone
from typing import Any


def build_farm_center(parcels: list[Any], parcel_states: list[dict[str, Any]]) -> dict[str, Any]:
    cards = []
    events = []
    attention = 0
    sensors = 0

    for state in parcel_states:
        parcel = state["parcel"]
        telemetry = state.get("telemetry")
        devices = state.get("devices", [])
        risks = state.get("risks", [])
        sensors += len(devices)

        highest = "ninguno"
        rank = {"ninguno": 0, "bajo": 1, "medio": 2, "alto": 3}
        for risk in risks:
            if rank.get(risk.risk_level, 0) > rank[highest]:
                highest = risk.risk_level
            events.append({
                "parcel_id": parcel.id,
                "event_type": "riesgo",
                "title": f"Riesgo de {risk.disease_code}: {risk.risk_level}",
                "occurred_at": risk.calculated_at,
                "detail": f"Puntuación {risk.risk_score:.2f}; confianza {risk.confidence_level}.",
            })

        priority = "revisar" if highest == "alto" else "vigilar" if highest == "medio" else "normal"
        if priority != "normal":
            attention += 1

        if telemetry:
            events.append({
                "parcel_id": parcel.id,
                "event_type": "telemetria",
                "title": f"Telemetría de {parcel.label}",
                "occurred_at": telemetry.measured_at,
                "detail": f"Humedad suelo {telemetry.soil_moisture:.1f}%; humedad relativa {telemetry.relative_humidity:.1f}%.",
            })

        if devices:
            for device in devices:
                events.append({
                    "parcel_id": parcel.id,
                    "event_type": "sensor",
                    "title": f"Sensor {device.name}",
                    "occurred_at": device.registered_at,
                    "detail": f"Tipo {device.device_type}; {'activo' if device.active else 'inactivo'}.",
                })

        headline = (
            "Revisión prioritaria por riesgo fitosanitario"
            if priority == "revisar"
            else "Vigilar evolución fitosanitaria"
            if priority == "vigilar"
            else "Operación sin prioridad crítica"
        )
        cards.append({
            "parcel_id": parcel.id,
            "label": parcel.label,
            "crop_type": parcel.crop_type,
            "comarca": parcel.comarca,
            "device_count": len(devices),
            "telemetry_available": telemetry is not None,
            "telemetry_measured_at": telemetry.measured_at if telemetry else None,
            "soil_moisture": telemetry.soil_moisture if telemetry else None,
            "active_risk_count": sum(1 for risk in risks if risk.risk_level in ("medio", "alto")),
            "highest_risk": highest,
            "priority": priority,
            "headline": headline,
        })

    events.sort(key=lambda item: item["occurred_at"], reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc),
        "parcel_count": len(parcels),
        "parcel_attention_count": attention,
        "sensor_count": sensors,
        "parcels": cards,
        "recent_events": events[:30],
    }
