from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.domain.weather_station_selection import WeatherStationCandidate, rank_weather_stations


def build_weather_context(
    parcel_latitude: float,
    parcel_longitude: float,
    observations: list[dict[str, object]],
    max_stations: int = 3,
    max_distance_km: float = 80.0,
    max_age_hours: float = 72.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Construye contexto meteorologico espacial para una parcela.

    Usa observaciones RIA ya persistidas. La interpolacion es inversa a la
    distancia y solo combina datos suficientemente recientes.
    """
    reference_time = now or datetime.now(timezone.utc)
    fresh_observations = [
        item for item in observations
        if _age_hours(item.get("observed_at"), reference_time) <= max_age_hours
    ]
    stations = rank_weather_stations(
        parcel_latitude,
        parcel_longitude,
        fresh_observations,
        max_stations=max_stations,
        max_distance_km=max_distance_km,
    )

    selected = []
    for station in stations:
        observation = _find_observation(fresh_observations, station)
        if observation is None:
            continue
        weight = 1.0 / max(station.distance_km, 0.5)
        selected.append({
            "source_code": station.source_code,
            "station_code": station.station_code,
            "distance_km": station.distance_km,
            "weight": round(weight, 4),
            "observed_at": observation.get("observed_at"),
            "temperature_c": _number(observation.get("temperature_c")),
            "relative_humidity": _number(observation.get("relative_humidity")),
            "rainfall_mm_24h": _number(observation.get("rainfall_mm_24h")),
            "confidence": observation.get("confidence") or "estimada",
        })

    if not selected:
        return {
            "available": False,
            "source": "none",
            "confidence": "estimada",
            "stations": [],
            "weather": {},
        }

    total_weight = sum(float(item["weight"]) for item in selected)
    weather: dict[str, float] = {}
    for field in ("temperature_c", "relative_humidity", "rainfall_mm_24h"):
        values = [
            (float(item[field]), float(item["weight"]))
            for item in selected
            if item[field] is not None
        ]
        if values:
            field_weight = sum(weight for _, weight in values)
            weather[field] = round(sum(value * weight for value, weight in values) / field_weight, 3)

    nearest_distance = float(selected[0]["distance_km"])
    return {
        "available": bool(weather),
        "source": "ria_ifapa",
        "confidence": _confidence(nearest_distance, selected),
        "station_distance_km": round(nearest_distance, 2),
        "observed_at": selected[0]["observed_at"],
        "stations": selected,
        "weather": weather,
    }


def _find_observation(
    observations: list[dict[str, object]],
    station: WeatherStationCandidate,
) -> dict[str, object] | None:
    for observation in observations:
        if (
            str(observation.get("source_code")) == station.source_code
            and str(observation.get("station_code")) == station.station_code
        ):
            return observation
    return None


def _age_hours(value: object, now: datetime) -> float:
    if not value:
        return float("inf")
    try:
        observed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return float("inf")
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return max(0.0, (now - observed).total_seconds() / 3600)


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _confidence(distance_km: float, selected: list[dict[str, object]]) -> str:
    if distance_km <= 20 and len(selected) >= 2:
        return "alta"
    if distance_km <= 40:
        return "media"
    return "baja"
