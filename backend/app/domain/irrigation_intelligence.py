from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def build_irrigation_intelligence(
    parcel_id: str,
    irrigation_events: list[dict[str, Any]],
    latest_telemetry: dict[str, Any] | None,
    window_days: int = 7,
) -> dict[str, Any]:
    """Resume consumo y estado hídrico sin convertirlo en una prescripción de riego.

    El módulo usa eventos registrados y la última observación de humedad del suelo.
    Los umbrales son de monitorización, no una recomendación agronómica de dosis.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    recent = [event for event in irrigation_events if _parse_date(event.get("started_at")) >= cutoff]

    volumes = [
        float(event["water_liters"])
        for event in recent
        if event.get("water_liters") is not None
    ]
    total_water = round(sum(volumes), 2)
    daily = round(total_water / window_days, 2)

    soil = _number((latest_telemetry or {}).get("soil_moisture"))
    soil_status = _soil_status(soil)
    water_use_level = _water_use_level(daily, len(recent))
    action, explanation = _action(soil_status, water_use_level, bool(recent))

    evidence = [
        f"{len(recent)} evento(s) de riego en {window_days} días",
        f"{total_water:.1f} L registrados con volumen" if volumes else "No hay volúmenes de agua registrados",
    ]
    if soil is not None:
        evidence.append(f"Humedad de suelo más reciente: {soil:.1f}%")

    latest = max((_parse_date(event.get("started_at")) for event in recent), default=None)
    return {
        "parcel_id": parcel_id,
        "window_days": window_days,
        "event_count": len(recent),
        "total_water_liters": total_water,
        "average_daily_water_liters": daily,
        "latest_irrigation_at": latest,
        "latest_soil_moisture": soil,
        "water_use_level": water_use_level,
        "soil_status": soil_status,
        "action": action,
        "explanation": explanation,
        "evidence": evidence,
    }


def _soil_status(value: float | None) -> str:
    if value is None:
        return "sin_datos"
    if value < 30:
        return "seco"
    if value > 75:
        return "humedo"
    return "adecuado"


def _water_use_level(daily_liters: float, event_count: int) -> str:
    if event_count == 0:
        return "sin_datos"
    if daily_liters >= 5000:
        return "alto"
    if daily_liters >= 1500:
        return "moderado"
    return "bajo"


def _action(soil_status: str, water_use_level: str, has_events: bool) -> tuple[str, str]:
    if not has_events:
        return "registrar", "No hay riegos recientes registrados; registra los eventos para construir un histórico útil."
    if soil_status == "seco":
        return "revisar", "La humedad de suelo reciente es baja; revisa el estado del cultivo y la programación de riego antes de actuar."
    if soil_status == "humedo" and water_use_level == "alto":
        return "revisar", "Hay humedad elevada y un consumo registrado alto; revisa drenaje, frecuencia y mediciones del sensor."
    if soil_status == "sin_datos":
        return "vigilar", "Hay histórico de riego, pero falta una lectura reciente de humedad de suelo."
    return "vigilar", "El histórico de riego y la lectura de humedad no muestran una señal que requiera revisión inmediata."


def _parse_date(value: object) -> datetime:
    if isinstance(value, datetime):
        date = value
    else:
        try:
            date = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return datetime.min.replace(tzinfo=timezone.utc)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return date


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
