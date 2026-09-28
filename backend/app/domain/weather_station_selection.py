from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from app.domain.geospatial import haversine_km


@dataclass(frozen=True)
class WeatherStationCandidate:
    source_code: str
    station_code: str
    latitude: float
    longitude: float
    distance_km: float


def rank_weather_stations(
    parcel_latitude: float,
    parcel_longitude: float,
    observations: list[dict[str, object]],
    max_stations: int = 3,
    max_distance_km: float = 80.0,
) -> list[WeatherStationCandidate]:
    """Devuelve las estaciones con observacion reciente mas proximas a la parcela.

    Se deduplica por fuente/estacion y se ignoran coordenadas invalidas.
    """
    latest_by_station: dict[tuple[str, str], dict[str, object]] = {}

    for observation in observations:
        source_code = str(observation.get("source_code") or "")
        station_code = str(observation.get("station_code") or "")
        latitude = _coordinate(observation.get("latitude"))
        longitude = _coordinate(observation.get("longitude"))
        if not source_code or not station_code or latitude is None or longitude is None:
            continue

        key = (source_code, station_code)
        current = latest_by_station.get(key)
        if current is None or str(observation.get("observed_at") or "") > str(current.get("observed_at") or ""):
            latest_by_station[key] = observation

    candidates: list[WeatherStationCandidate] = []
    for observation in latest_by_station.values():
        latitude = _coordinate(observation.get("latitude"))
        longitude = _coordinate(observation.get("longitude"))
        if latitude is None or longitude is None:
            continue
        distance_km = haversine_km(parcel_latitude, parcel_longitude, latitude, longitude)
        if distance_km <= max_distance_km:
            candidates.append(
                WeatherStationCandidate(
                    source_code=str(observation["source_code"]),
                    station_code=str(observation["station_code"]),
                    latitude=latitude,
                    longitude=longitude,
                    distance_km=round(distance_km, 3),
                )
            )

    candidates.sort(key=lambda item: item.distance_km)
    return candidates[:max_stations]


def _coordinate(value: object) -> float | None:
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None
