from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class WeatherEvidence:
    temperature_c: float | None
    relative_humidity: float | None
    rainfall_mm_24h: float | None
    observed_at: datetime | None
    source: str
    station: str | None = None
    confidence: str = "estimada"


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _first(mapping: dict[str, Any], *names: str) -> Any:
    lowered = {str(k).lower().replace("_", ""): v for k, v in mapping.items()}
    for name in names:
        if name.lower().replace("_", "") in lowered:
            return lowered[name.lower().replace("_", "")]
    return None


def normalize_ria_daily(data: Any, station: str | None = None) -> WeatherEvidence | None:
    """Normaliza una observacion diaria RIA sin asumir un esquema único."""
    rows = _extract_rows(data)
    if not isinstance(rows, list) or not rows:
        return None
    row = rows[-1]
    if not isinstance(row, dict):
        return None
    return WeatherEvidence(
        temperature_c=_number(_first(row, "temperatura_media", "temperaturamedia", "tm", "tmedia", "temperatura", "temp", "temperature")),
        relative_humidity=_number(_first(row, "humedad_relativa_media", "humedadrelativamedia", "hr", "humedad", "humedad_relativa", "relativehumidity", "rh")),
        rainfall_mm_24h=_number(_first(row, "precipitacion", "precipitacion_mm", "precipitacion24h", "lluvia", "rainfall")),
        observed_at=_parse_datetime(_first(row, "fecha", "date", "fechadato", "fecha_dato", "datetime", "timestamp")),
        source="ria_ifapa",
        station=station,
        confidence="alta",
    )


def _extract_rows(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("datos", "data", "results", "result", "items", "registros"):
        value = data.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _extract_rows(value)
            if nested:
                return nested
    return []

def normalize_aemet_daily(data: Any) -> WeatherEvidence | None:
    """Extrae una observacion diaria de la respuesta municipal de AEMET."""
    if not isinstance(data, list) or not data:
        return None
    municipality = data[0]
    if not isinstance(municipality, dict):
        return None
    days = municipality.get("prediccion", {}).get("dia", [])
    if not isinstance(days, list) or not days:
        return None
    day = days[0]
    if not isinstance(day, dict):
        return None
    temp = day.get("temperatura", {})
    humidity = day.get("humedadRelativa")
    rain = day.get("precipitacion", [])
    rain_value = _number(rain[0].get("value")) if isinstance(rain, list) and rain and isinstance(rain[0], dict) else None
    return WeatherEvidence(
        temperature_c=_number(temp.get("temperaturaMedia")),
        relative_humidity=_number(humidity[0]) if isinstance(humidity, list) and humidity else _number(humidity),
        rainfall_mm_24h=rain_value,
        observed_at=_parse_datetime(day.get("fecha")),
        source="aemet",
        confidence="alta",
    )


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
