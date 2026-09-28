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
    stations: list[dict[str, object]],
    max_stations: int = 3,
    max_distance_km: float = 80.0,
) -> list[WeatherStationCandidate]:
    """Devuelve las estaciones catalogadas mas proximas a la parcela.

    Las coordenadas proceden del catálogo oficial; la frescura de la
    observación se controla en la capa de contexto meteorológico.
    """
    latest_stations: dict[tuple[str, str], dict[str, object]] = {}
    for station in stations:
        source_code = str(station.get("source_code") or "")
        station_code = str(station.get("station_code") or "")
        key = (source_code, station_code)
        previous = latest_stations.get(key)
        if previous is None or _observed_at(station) >= _observed_at(previous):
            latest_stations[key] = station

    candidates: list[WeatherStationCandidate] = []
    for station in latest_stations.values():
        source_code = str(station.get("source_code") or "")
        station_code = str(station.get("station_code") or "")
        latitude = _coordinate(station.get("latitude"))
        longitude = _coordinate(station.get("longitude"))
        if latitude is None or longitude is None:
            continue
        distance_km = haversine_km(parcel_latitude, parcel_longitude, latitude, longitude)
        if distance_km <= max_distance_km:
            candidates.append(
                WeatherStationCandidate(
                    source_code=source_code,
                    station_code=station_code,
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


def _observed_at(station: dict[str, object]) -> str:
    """Ordena observaciones de la misma estación por fecha descendente."""
    return str(station.get("observed_at") or "")
